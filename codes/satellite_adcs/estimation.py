"""Attitude estimator: MEKF with gyro-bias estimation (C2-e).

Replaces the stub that was here (star-tracker passthrough + RAW gyro; no bias
state, no covariance). That stub was not cosmetic debt: measured 2026-10-16 it
pinned the achievable pointing error at ~1.0 deg -- exactly the reward and
success tolerance -- because the unestimated 1e-3 rad/s gyro bias produces a
steady-state attitude offset through the rate feedback. A classical LQR could do
no better than 1.001 deg and spent only 36 % of an episode inside the 1 deg band;
with the bias zeroed the same controller reached 0.295 deg and 91 %. See plan
section 1.5.

MODEL
  q_hat : estimate of q_BN (full quaternion, propagated nonlinearly)
  b_hat : gyro bias [rad/s]
  omega_hat = omega_meas - b_hat

  Propagation (body-frame / right-multiplicative error convention, chosen so it
  matches the 0.5*q x [0,omega] kinematics and the star-tracker residual below):
        q_hat_dot = 0.5 * q_hat x [0, omega_hat]
        d/dt[dtheta; db] = [[-[omega_hat]x, -I], [0, 0]] [dtheta; db] + noise

  Star-tracker update (absolute attitude, noise ~5e-5 rad):
        dtheta_meas = 2 * vec( q_hat^-1 x q_meas )
        H = [I 0],  K = P H' (H P H' + R)^-1
        q_hat <- q_hat x dq_hat,   b_hat <- b_hat + dx_b
  with the Joseph form for P (numerically safer than (I-KH)P, keeps it SPD).

INTERFACE COMPATIBILITY
  `q_hat`, `P`, `gyro_rate()`, `propagate()`, `update()` keep the names the env,
  the classical controller and every script already use. `P` is now 6x6 with a
  property setter that accepts a 3x3 block, so the existing
  `est.P = np.eye(3) * 1e-2` calls keep working (they set the attitude block).
"""
from __future__ import annotations

import numpy as np

from .quaternion import quat_mult, quat_inv, quat_normalize


def _skew(v):
    return np.array([[0.0, -v[2], v[1]], [v[2], 0.0, -v[0]], [-v[1], v[0], 0.0]])


class MEKF:
    """6-state multiplicative EKF: [attitude error (3); gyro bias (3)]."""

    def __init__(self, cfg: dict, **kwargs):
        sens = cfg["sensors"]
        g = sens.get("gyro", {})
        self.sigma_gyro = float(g.get("noise_std_rad_s", 1e-4))     # [rad/s]
        self.bias0_std = float(g.get("bias_rad_s", 1e-3))           # bias prior
        self.sigma_st = float(sens.get("star_tracker", {}).get(
            "noise_std_rad", 5e-5))                                 # ST noise [rad]
        # The bias is CONSTANT per run in this simulator, so a tight random-walk
        # prior is honest and keeps the filter calm. kwargs let a test widen it.
        self.sigma_bias_rw = float(kwargs.get("sigma_bias_rw", 1e-7))
        self._P = None
        self.reset()

    # ------------------------------------------------------------------ state
    def reset(self):
        self.q_hat = np.array([1.0, 0.0, 0.0, 0.0])
        self.b_hat = np.zeros(3)
        # attitude prior is deliberately large: a reset attitude is unknown.
        self._P = np.diag(np.concatenate([np.full(3, 1.0),
                                          np.full(3, self.bias0_std ** 2)]))
        return self

    @property
    def P(self):
        return self._P

    @P.setter
    def P(self, value):
        """Accept a full 6x6, or a 3x3 block meaning 'the attitude block'."""
        v = np.asarray(value, dtype=float)
        P = self._P.copy() if self._P is not None else np.eye(6)
        if v.shape == (6, 6):
            self._P = v
        elif v.shape == (3, 3):
            P[:3, :3] = v
            self._P = P
        else:                                    # scalar / 1-D -> attitude block
            P[:3, :3] = np.eye(3) * float(np.ravel(v)[0])
            self._P = P

    @property
    def bias(self):
        return self.b_hat.copy()

    # ------------------------------------------------------------ propagation
    def propagate(self, omega_meas, dt):
        """Inertial propagation, called once per integrator substep."""
        w = np.asarray(omega_meas, dtype=float) - self.b_hat
        qd = 0.5 * quat_mult(self.q_hat, np.array([0.0, w[0], w[1], w[2]]))
        self.q_hat = quat_normalize(self.q_hat + dt * qd)
        F = np.zeros((6, 6))
        F[:3, :3] = -_skew(w)
        F[:3, 3:] = -np.eye(3)
        A = np.eye(6) + F * dt
        Q = np.diag(np.concatenate([np.full(3, self.sigma_gyro ** 2),
                                    np.full(3, self.sigma_bias_rw ** 2)])) * dt
        self._P = A @ self._P @ A.T + Q
        return self

    # ----------------------------------------------------------------- update
    def update_star_tracker(self, q_meas):
        """MEKF measurement update from an absolute attitude measurement."""
        q_m = quat_normalize(np.asarray(q_meas, dtype=float))
        dq = quat_mult(quat_inv(self.q_hat), q_m)       # estimate -> measurement
        if dq[0] < 0.0:                                 # shortest arc (double cover)
            dq = -dq
        dtheta = 2.0 * dq[1:4]                          # residual, body frame
        H = np.hstack([np.eye(3), np.zeros((3, 3))])
        R = np.eye(3) * self.sigma_st ** 2
        K = self._P @ H.T @ np.linalg.inv(self._P[:3, :3] + R)     # 6x3
        dx = K @ dtheta
        dq_hat = quat_normalize(np.concatenate([[1.0], 0.5 * dx[:3]]))
        self.q_hat = quat_normalize(quat_mult(self.q_hat, dq_hat))
        self.b_hat = self.b_hat + dx[3:]
        IKH = np.eye(6) - K @ H
        self._P = IKH @ self._P @ IKH.T + K @ R @ K.T
        self._P = 0.5 * (self._P + self._P.T)
        return self

    def update_vector(self, v_meas, v_ref_inertial, r):
        """Sun/magnetometer vector update: not used. The star tracker is absolute,
        accurate and available every control step in this sensor model. Kept for
        interface symmetry."""
        return self

    def update(self, meas, dyn_or_r=None):
        if "st" in meas:
            self.update_star_tracker(meas["st"])
        return self

    def gyro_rate(self, omega_meas):
        """Bias-corrected rate -- this is what removes the ~1 deg pointing floor."""
        return np.asarray(omega_meas, dtype=float) - self.b_hat
