"""Classical LQR/PD attitude controller backbone (B5, Arm A0).

Solves the continuous-time Algebraic Riccati Equation offline at initialization (no online
Riccati solves in the control loop) and includes gyroscopic feedforward plus optional
back-calculation anti-windup integral action.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.linalg import solve_continuous_are

from adcs.control.allocation import ActuatorAllocator, AllocationConfig
from adcs.control.reference import compute_attitude_error
from adcs.interfaces.types import (
    ActuatorCapabilityState,
    ActuatorCommand,
    ControlStepOutput,
    EstimatorOutput,
    FloatArray,
    GateDecision,
    ReferenceState,
    SensorMeasurement,
    SupervisorMode,
)
from adcs.utils.config import SpacecraftConfig


@dataclass(frozen=True)
class ClassicalLQRConfig:
    """Tunable LQR weights and feedforward/anti-windup parameters."""

    q_attitude: float = 1.0  # Weight on attitude error vector (rad^-2)
    q_rate: float = 80.0  # Weight on angular rate error (s^2 / rad^2)
    r_torque: float = 4.0  # Weight on body control torque (N^-2 m^-2)
    gyroscopic_feedforward: bool = True
    ki_attitude: float = 0.0  # Optional integral gain (N*m / (rad*s)); 0 for pure LQR
    integral_limit_rad_s: float = 0.2  # Clamping limit for attitude error integral
    anti_windup_gain: float = 2.0  # Back-calculation anti-windup gain
    max_slew_rate_rad_s: float = 0.08  # Smooth eigenaxis slew-rate cap for large angles
    max_torque_request_nm: float | None = None  # Default: 3.0 * nominal RW torque limit

    @classmethod
    def from_spacecraft(
        cls,
        sc_config: SpacecraftConfig,
        *,
        natural_freq_rad_s: float | None = None,
        damping_ratio: float = 1.05,
    ) -> ClassicalLQRConfig:
        """Auto-scale LQR weights & torque caps for ANY spacecraft inertia and RW torque limit.

        Picks a physically matched closed-loop bandwidth omega_n from sqrt(tau_lim / J_mean)
        so both a 4 kg CubeSat and a 500 kg smallsat achieve critically damped response.
        """
        j_mean = float(np.mean(np.diag(sc_config.inertia_matrix_kg_m2)))
        tau_lim = sc_config.reaction_wheels.torque_limit_nominal_nm
        # Characteristic angular acceleration alpha_max = tau_lim / j_mean
        alpha_max = tau_lim / max(j_mean, 1e-9)
        # For reference cube (J=16.67, tau=0.15 -> alpha=0.009): wn ~ 0.173 rad/s
        wn = (
            float(np.clip(1.82 * np.sqrt(alpha_max), 0.05, 0.8))
            if natural_freq_rad_s is None
            else float(natural_freq_rad_s)
        )
        # Choose r_torque = 1 / tau_lim^2-scaled so CARE yields Kp = J*wn^2, Kd = 2*zeta*J*wn:
        # CARE double-integrator identities: Kp = sqrt(q_att/r), Kd = sqrt(q_rate/r + 2*J*Kp)
        kp_target = j_mean * (wn**2)
        kd_target = 2.0 * damping_ratio * j_mean * wn
        r_t = 1.0 / max(kp_target**2, 1e-12)
        q_att = 1.0
        q_rate = max(1e-6, r_t * max(0.0, kd_target**2 - 2.0 * j_mean * kp_target))
        slew_cap = float(np.clip(0.85 * np.sqrt(alpha_max), 0.04, 0.25))
        return cls(
            q_attitude=q_att,
            q_rate=q_rate,
            r_torque=r_t,
            max_slew_rate_rad_s=slew_cap,
            max_torque_request_nm=3.0 * tau_lim,
        )


def compute_lqr_gains(
    inertia_kg_m2: FloatArray,
    q_attitude: float,
    q_rate: float,
    r_torque: float,
) -> tuple[FloatArray, FloatArray]:
    """Compute offline infinite-horizon LQR gains (K_p, K_d) for linearized rigid-body plant."""
    j_inv = np.linalg.inv(inertia_kg_m2)
    a_mat = np.zeros((6, 6), dtype=np.float64)
    a_mat[:3, 3:] = np.eye(3, dtype=np.float64)
    b_mat = np.zeros((6, 3), dtype=np.float64)
    b_mat[3:, :] = j_inv

    q_mat = np.diag([q_attitude] * 3 + [q_rate] * 3).astype(np.float64)
    r_mat = np.diag([r_torque] * 3).astype(np.float64)
    p_mat = solve_continuous_are(a_mat, b_mat, q_mat, r_mat)
    k_lqr = np.linalg.solve(r_mat, b_mat.T @ p_mat)
    return k_lqr[:, :3].copy(), k_lqr[:, 3:].copy()


def apply_underactuated_magnetic_axis_law(
    sc_cfg: SpacecraftConfig,
    theta_err_body_rad: FloatArray,
    omega_err_body_rad_s: FloatArray,
    omega_body_rad_s: FloatArray,
    wheel_momentum_nms: FloatArray,
    tau_base_nm: FloatArray,
    dead_axis: FloatArray,
) -> FloatArray:
    """Replace dead RW axis torque with energy-optimal saturated magnetic braking law.

    Automatically scales to any spacecraft inertia and MTQ dipole rating, prevents
    overshoot/oscillation under weak magnetic authority, and includes gyroscopic
    feedforward compensation along the dead axis.
    """
    d_hat = np.asarray(dead_axis, dtype=np.float64)
    j_mat = sc_cfg.inertia_matrix_kg_m2
    j_d = max(float(d_hat @ j_mat @ d_hat), 1e-6)
    m_max = float(sc_cfg.magnetorquers.dipole_limit_per_axis_am2)
    tau_mtq_typ = max(m_max * 3.5e-5, 1e-7)  # typical LEO B ~ 35 uT
    a_mtq = tau_mtq_typ / j_d
    # Conservative braking acceleration accounts for time-varying B-field projection
    a_brake = 0.30 * a_mtq

    theta_d = float(np.dot(theta_err_body_rad, d_hat))
    omega_d = float(np.dot(omega_err_body_rad_s, d_hat))
    theta_lin = 0.04  # ~2.3 deg smooth linear blend zone
    omega_max_mag = min(0.015, math.sqrt(2.0 * a_brake * 0.6))
    omega_lin_edge = math.sqrt(2.0 * a_brake * theta_lin)

    if abs(theta_d) <= theta_lin:
        omega_des_d = -(omega_lin_edge / theta_lin) * theta_d
    else:
        omega_des_d = -math.copysign(
            min(omega_max_mag, math.sqrt(2.0 * a_brake * abs(theta_d))),
            theta_d,
        )

    # Smooth proportional rate-tracking torque (saturates MTQ cleanly for |w_err| > 0.01 deg/s)
    k_d_mag = tau_mtq_typ / max(0.00018, 0.25 * omega_lin_edge)
    h_tot = j_mat @ omega_body_rad_s + sc_cfg.reaction_wheels.axis_matrix_body @ wheel_momentum_nms
    gyro_ff_d = float(np.dot(np.cross(omega_body_rad_s, h_tot), d_hat))
    tau_d_mag = -k_d_mag * (omega_d - omega_des_d) + gyro_ff_d
    # Cap dead-axis request to avoid distorting healthy-axis norm clipping
    tau_d_mag = float(np.clip(tau_d_mag, -4.0 * tau_mtq_typ, 4.0 * tau_mtq_typ))

    tau_out = np.asarray(tau_base_nm, dtype=np.float64).copy()
    tau_out = tau_out - float(np.dot(tau_out, d_hat)) * d_hat + tau_d_mag * d_hat
    return tau_out


class ClassicalLQRController:
    """Strong deterministic classical LQR attitude controller (Arm A0 / B5 backbone)."""

    def __init__(
        self,
        sc_config: SpacecraftConfig,
        lqr_config: ClassicalLQRConfig | None = None,
        alloc_config: AllocationConfig | None = None,
        *,
        name: str = "A0_classical_lqr",
    ) -> None:
        self.sc_cfg = sc_config
        self.cfg = (
            ClassicalLQRConfig.from_spacecraft(sc_config) if lqr_config is None else lqr_config
        )
        self._max_tau_req = (
            3.0 * sc_config.reaction_wheels.torque_limit_nominal_nm
            if self.cfg.max_torque_request_nm is None
            else self.cfg.max_torque_request_nm
        )
        self._name = name
        self.inertia = sc_config.inertia_matrix_kg_m2.copy()
        self.a_rw = sc_config.reaction_wheels.axis_matrix_body.copy()
        self.rw_rotor_j = sc_config.reaction_wheels.rotor_inertia_kg_m2
        self.kp, self.kd = compute_lqr_gains(
            self.inertia,
            self.cfg.q_attitude,
            self.cfg.q_rate,
            self.cfg.r_torque,
        )
        self.allocator = ActuatorAllocator(sc_config, alloc_config)
        self._err_integral = np.zeros(3, dtype=np.float64)

    @property
    def name(self) -> str:
        return self._name

    def reset(self) -> None:
        self._err_integral = np.zeros(3, dtype=np.float64)

    def compute_base_torque(
        self,
        estimator_out: EstimatorOutput,
        reference: ReferenceState,
        wheel_momentum_nms: FloatArray,
        dt_s: float,
        *,
        kp_scale: float = 1.0,
        kd_scale: float = 1.0,
    ) -> tuple[FloatArray, dict[str, float]]:
        """Compute nominal desired body torque tau_base_nm (B5 contract)."""
        att_err = compute_attitude_error(
            estimator_out.q_ib_est,
            estimator_out.omega_body_est_rad_s,
            reference,
        )

        # Smooth slew-rate limiting for large attitude errors without distorting small-angle LQR:
        # Equivalent to capping the proportional position-commanded rate -K_d^{-1} K_p e_theta.
        kp_eff = kp_scale * self.kp
        kd_eff = kd_scale * self.kd
        tau_p = -(kp_eff @ att_err.rotvec_rad)
        if self.cfg.max_slew_rate_rad_s > 0.0:
            # Desired rate from proportional term: w_des = -K_d^{-1} K_p e_theta
            w_des = np.linalg.solve(kd_eff, tau_p)
            w_des_norm = float(np.linalg.norm(w_des))
            if w_des_norm > self.cfg.max_slew_rate_rad_s:
                w_des = w_des * (self.cfg.max_slew_rate_rad_s / w_des_norm)
                tau_p = kd_eff @ w_des

        tau_d = -(kd_eff @ att_err.omega_err_body_rad_s)
        tau_i = -self.cfg.ki_attitude * self._err_integral

        tau_ff = np.zeros(3, dtype=np.float64)
        if self.cfg.gyroscopic_feedforward:
            w_est = estimator_out.omega_body_est_rad_s
            h_tot_est = self.inertia @ w_est + self.a_rw @ wheel_momentum_nms
            tau_ff = np.cross(w_est, h_tot_est)

        tau_base = tau_p + tau_d + tau_i + tau_ff
        tau_norm = float(np.linalg.norm(tau_base))
        if tau_norm > self._max_tau_req:
            tau_base = tau_base * (self._max_tau_req / tau_norm)

        # Update integral with clamping (back-calculation applied after allocation)
        if self.cfg.ki_attitude > 0.0 and estimator_out.valid:
            self._err_integral = np.clip(
                self._err_integral + att_err.rotvec_rad * dt_s,
                -self.cfg.integral_limit_rad_s,
                self.cfg.integral_limit_rad_s,
            )

        diag = {
            "geodesic_err_rad": att_err.geodesic_angle_rad,
            "rate_err_norm_rad_s": float(np.linalg.norm(att_err.omega_err_body_rad_s)),
            "tau_base_norm_nm": float(np.linalg.norm(tau_base)),
        }
        return tau_base, diag

    def apply_anti_windup(
        self, tau_request_nm: FloatArray, tau_allocated_nm: FloatArray, dt_s: float
    ) -> None:
        """Back-calculation anti-windup when allocator saturates requested torque."""
        if self.cfg.ki_attitude > 0.0:
            sat_err = tau_allocated_nm - tau_request_nm
            self._err_integral = np.clip(
                self._err_integral
                + (self.cfg.anti_windup_gain / self.cfg.ki_attitude) * sat_err * dt_s,
                -self.cfg.integral_limit_rad_s,
                self.cfg.integral_limit_rad_s,
            )

    def compute(
        self,
        *,
        estimator_out: EstimatorOutput,
        reference: ReferenceState,
        capability: ActuatorCapabilityState,
        measurement: SensorMeasurement,
        dt_s: float,
    ) -> ControlStepOutput:
        wheel_h_est = self.rw_rotor_j * measurement.rw_speed_rad_s
        tau_base, diag = self.compute_base_torque(
            estimator_out, reference, wheel_h_est, dt_s
        )
        b_meas = measurement.mag_body_t if measurement.mag_valid else np.zeros(3, dtype=np.float64)
        alloc = self.allocator.allocate(
            tau_base,
            wheel_momentum_nms=wheel_h_est,
            b_field_body_t=b_meas,
            capability=capability,
        )
        self.apply_anti_windup(tau_base, alloc.tau_total_allocated_nm, dt_s)

        cmd = ActuatorCommand(
            rw_torque_cmd_nm=alloc.rw_torque_cmd_nm,
            mtq_dipole_cmd_am2=alloc.mtq_dipole_cmd_am2,
            tau_request_nm=alloc.tau_request_nm,
            tau_allocated_nm=alloc.tau_total_allocated_nm,
        )
        gate_disabled = GateDecision(
            rho=0.0,
            alpha=0.0,
            directional_gain_xyz=np.zeros(3, dtype=np.float64),
            tau_rl_raw_nm=np.zeros(3, dtype=np.float64),
            tau_rl_gated_nm=np.zeros(3, dtype=np.float64),
            rl_enabled=False,
            rejected_reason="classical_baseline_no_rl",
            mode=SupervisorMode.M0_NOMINAL,
        )
        return ControlStepOutput(
            command=cmd,
            tau_base_nm=tau_base,
            gate_decision=gate_disabled,
            mode=SupervisorMode.M0_NOMINAL,
            diagnostics={
                **diag,
                "infeasible_torque_norm_nm": float(np.linalg.norm(alloc.infeasible_residual_nm)),
                "rw_saturated": alloc.rw_saturated,
                "mtq_saturated": alloc.mtq_saturated,
            },
        )
