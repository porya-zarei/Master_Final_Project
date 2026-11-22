"""Two-body Keplerian orbit propagator and LVLH nadir-pointing reference geometry."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from adcs.interfaces.types import FloatArray, ReferenceState
from adcs.utils.config import OrbitConfig
from adcs.utils.quaternion import dcm_to_quat


@dataclass(frozen=True)
class OrbitState:
    """Spacecraft ECI position and velocity at time t."""

    time_s: float
    position_eci_m: FloatArray
    velocity_eci_m_s: FloatArray
    true_anomaly_rad: float
    mean_motion_rad_s: float


class KeplerianOrbit:
    """Deterministic two-body Keplerian orbit propagator (supports circular & elliptical)."""

    def __init__(self, cfg: OrbitConfig) -> None:
        self.cfg = cfg
        self.a = cfg.semi_major_axis_m
        self.e = cfg.eccentricity
        self.mu = cfg.gravitational_parameter_m3_s2
        self.inc = np.deg2rad(cfg.inclination_deg)
        self.raan = np.deg2rad(cfg.raan_deg)
        self.argp = np.deg2rad(cfg.argument_of_perigee_deg)
        self.mean_motion = float(np.sqrt(self.mu / (self.a**3)))
        self._r_pqw_to_eci = self._compute_pqw_to_eci()

    def _compute_pqw_to_eci(self) -> FloatArray:
        co, so = np.cos(self.raan), np.sin(self.raan)
        ci, si = np.cos(self.inc), np.sin(self.inc)
        cw, sw = np.cos(self.argp), np.sin(self.argp)
        return np.array(
            [
                [co * cw - so * sw * ci, -co * sw - so * cw * ci, so * si],
                [so * cw + co * sw * ci, -so * sw + co * cw * ci, -co * si],
                [sw * si, cw * si, ci],
            ],
            dtype=np.float64,
        )

    def _nu_to_mean_anomaly(self, nu: float) -> float:
        if self.e < 1e-12:
            return nu
        ea = 2.0 * np.arctan2(
            np.sqrt(1.0 - self.e) * np.sin(0.5 * nu),
            np.sqrt(1.0 + self.e) * np.cos(0.5 * nu),
        )
        return float(ea - self.e * np.sin(ea))

    def _solve_kepler(self, mean_anomaly: float) -> float:
        m = float(np.mod(mean_anomaly, 2.0 * np.pi))
        if self.e < 1e-12:
            return m
        ea = m
        for _ in range(12):
            f = ea - self.e * np.sin(ea) - m
            fp = 1.0 - self.e * np.cos(ea)
            delta = f / fp
            ea -= delta
            if abs(delta) < 1e-13:
                break
        return ea

    def state_at(self, time_s: float, true_anomaly_deg_init: float | None = None) -> OrbitState:
        """Compute exact ECI position and velocity at `time_s`."""
        nu0 = np.deg2rad(
            self.cfg.true_anomaly_deg_initial
            if true_anomaly_deg_init is None
            else true_anomaly_deg_init
        )
        m0 = self._nu_to_mean_anomaly(float(nu0))
        m_t = m0 + self.mean_motion * float(time_s)
        ea = self._solve_kepler(m_t)

        cos_e = np.cos(ea)
        sin_e = np.sin(ea)
        r_mag = self.a * (1.0 - self.e * cos_e)
        fac = np.sqrt(1.0 - self.e * self.e)
        nu = float(np.arctan2(fac * sin_e, cos_e - self.e))

        r_pqw = np.array([self.a * (cos_e - self.e), self.a * fac * sin_e, 0.0], dtype=np.float64)
        v_scale = np.sqrt(self.mu * self.a) / r_mag
        v_pqw = np.array([-v_scale * sin_e, v_scale * fac * cos_e, 0.0], dtype=np.float64)

        r_eci = self._r_pqw_to_eci @ r_pqw
        v_eci = self._r_pqw_to_eci @ v_pqw
        return OrbitState(
            time_s=float(time_s),
            position_eci_m=r_eci,
            velocity_eci_m_s=v_eci,
            true_anomaly_rad=nu,
            mean_motion_rad_s=self.mean_motion,
        )


def compute_lvlh_reference(
    time_s: float,
    position_eci_m: FloatArray,
    velocity_eci_m_s: FloatArray,
    prev_x_eci: FloatArray | None = None,
) -> tuple[ReferenceState, FloatArray]:
    """Compute nadir-pointing LVLH reference frame (spacecraft_config.yaml §attitude_reference).

    Definition:
    - +z_R points to Earth nadir: z_R = -r_ECI / ||r_ECI||
    - +x_R aligns with orbital velocity projected perpendicular to z_R
    - +y_R = z_R x x_R (completes right-handed orthogonal triad: x_R x y_R = z_R)
    - R_IR = [x_R, y_R, z_R] maps vectors from LVLH (R) to ECI (I).
    - omega_ref_R = R_IR^T @ ((r x v) / ||r||^2) is LVLH angular rate wrt ECI expressed in R.
    """
    r = np.asarray(position_eci_m, dtype=np.float64)
    v = np.asarray(velocity_eci_m_s, dtype=np.float64)
    r_norm = float(np.linalg.norm(r))
    if r_norm <= 1e-9:
        raise ValueError("Degenerate zero position vector in LVLH reference")

    z_hat = -r / r_norm
    v_proj = v - float(np.dot(v, z_hat)) * z_hat
    v_proj_norm = float(np.linalg.norm(v_proj))

    if v_proj_norm > 1e-9:
        x_hat = v_proj / v_proj_norm
    elif prev_x_eci is not None:
        x_proj = prev_x_eci - float(np.dot(prev_x_eci, z_hat)) * z_hat
        x_norm = float(np.linalg.norm(x_proj))
        if x_norm <= 1e-9:
            raise ValueError("Degenerate LVLH fallback x-axis parallel to nadir")
        x_hat = x_proj / x_norm
    else:
        # Fallback arbitrary orthogonal axis
        trial = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        if abs(float(np.dot(trial, z_hat))) > 0.9:
            trial = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        x_proj = trial - float(np.dot(trial, z_hat)) * z_hat
        x_hat = x_proj / float(np.linalg.norm(x_proj))

    y_hat = np.cross(z_hat, x_hat)
    y_hat = y_hat / float(np.linalg.norm(y_hat))
    x_hat = np.cross(y_hat, z_hat)

    r_ir = np.column_stack((x_hat, y_hat, z_hat))
    q_ir = dcm_to_quat(r_ir)

    omega_orb_eci = np.cross(r, v) / (r_norm * r_norm)
    omega_ref_in_r = r_ir.T @ omega_orb_eci

    ref = ReferenceState(
        time_s=float(time_s),
        q_ir=q_ir,
        omega_ref_inertial_in_ref_rad_s=omega_ref_in_r,
        valid=True,
    )
    return ref, x_hat
