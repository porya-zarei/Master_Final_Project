"""Controllers: B-dot detumble (MTQ) + LQR nadir acquisition (RW) + allocator."""
from __future__ import annotations
import numpy as np
from scipy.linalg import solve_continuous_are

from .quaternion import quat_error, theta_vec, quat_to_dcm
from .guidance import NadirGuidance


def design_lqr(J: np.ndarray, Q: np.ndarray, R: np.ndarray):
    """LQR gain K (3x6) for x=[theta(3); omega(3)], u=tau.

    Linear model: d/dt[theta;omega] = [[0, I],[0,0]][theta;omega] + [[0],[J^-1]] tau
    """
    n = 6
    A = np.zeros((n, n))
    A[0:3, 3:6] = np.eye(3)
    B = np.vstack([np.zeros((3, 3)), np.linalg.inv(J)])
    P = solve_continuous_are(A, B, Q, R)
    K = np.linalg.inv(R) @ B.T @ P
    return K


class ADCSController:
    """Phase manager: B-dot detumble then LQR nadir pointing."""

    def __init__(self, cfg: dict, J: np.ndarray, mu: float, a: float, rng):
        self.cfg = cfg
        self.rng = rng
        sim = cfg["simulation"]
        rw = cfg["actuators"]["reaction_wheels"]
        mtq = cfg["actuators"]["magnetorquers"]
        self.rw_max_torque = rw["max_torque_Nm"]
        self.mtq_max_dipole = mtq["max_dipole_Am2"]
        self.n_rw = rw["count"]

        # LQR weights
        self.Q = np.diag([1.0, 1.0, 1.0, 0.3, 0.3, 0.3])
        self.R = np.eye(3) * (1.0 / 0.010**2)  # penalize torque relative to max
        self.K = design_lqr(J, self.Q, self.R)

        self.guidance = NadirGuidance(mu, a)

        # detumble params
        self.detumble_enabled = sim.get("detumble_enabled", True)
        self.detumble_threshold_deg = 0.3  # deg/s -> switch to LQR
        self.bdot_gain = 1.0e4
        self._B_prev = None
        self._B_dt = 0.0

        self.phase = "detumble"
        self.control_hz = sim["control_hz"]
        self.control_period = 1.0 / self.control_hz

    # ---------------------------------------------------------------- B-dot
    def _bdot_dipole(self, B_meas, dt):
        """m = -k * dB/dt (B-dot detumble)."""
        if self._B_prev is None:
            dB = np.zeros(3)
        else:
            dB = (B_meas - self._B_prev) / max(dt, 1e-6)
        self._B_prev = B_meas.copy()
        m = -self.bdot_gain * dB
        return np.clip(m, -self.mtq_max_dipole, self.mtq_max_dipole)

    # ---------------------------------------------------------------- control
    def control(self, meas, est, dyn, t, dt):
        """Return (tau_rw, m_mtq) given measurements and estimator state."""
        gyro = meas["gyro"]
        omega_hat = est.gyro_rate(gyro)

        omega_norm_deg = np.degrees(np.linalg.norm(omega_hat))

        if self.phase == "detumble":
            B_meas = meas.get("mag", np.zeros(3))
            m = self._bdot_dipole(B_meas, dt)
            if (not self.detumble_enabled) or omega_norm_deg < self.detumble_threshold_deg:
                self.phase = "pointing"
                self._B_prev = None
                m = np.zeros(3)
            return np.zeros(self.n_rw), m

        # ---- pointing: LQR on LVLH reference
        q_ref, omega_ref_lvlh = self.guidance.reference(dyn.r, dyn.v)
        q_err = quat_error(est.q_hat, q_ref)
        theta = theta_vec(q_err)
        # omega_ref in actual body frame = C(q_err) @ omega_ref_lvlh
        C_e = quat_to_dcm(q_err)
        omega_ref_body = C_e @ omega_ref_lvlh
        omega_err = omega_hat - omega_ref_body
        x = np.concatenate([theta, omega_err])
        tau_des = -(self.K @ x)
        tau_rw = np.clip(tau_des, -self.rw_max_torque, self.rw_max_torque)
        return tau_rw, np.zeros(3)
