"""Attitude estimator: star-tracker attitude + gyro rate.

M1 uses a star tracker that provides an absolute, high-accuracy attitude
(noise ~5e-5 rad) at the control rate (4 Hz). The attitude estimate is therefore
taken directly from the star tracker; the gyro provides the angular-rate
estimate (omega_hat = measured gyro, bias small and neglected here).

This avoids the attitude/bias observability coupling that can make a fused MEKF
unstable during large-angle acquisition. A full MEKF with gyro-bias estimation
can be layered in later (Phase 2) once the acquisition loop is validated.
"""
from __future__ import annotations
import numpy as np

from .quaternion import quat_normalize


class MEKF:
    def __init__(self, cfg: dict, **kwargs):
        self.cfg = cfg["sensors"]
        self.q_hat = np.array([1.0, 0, 0, 0])

    def propagate(self, omega_meas, dt):
        """No-op for attitude (ST overrides); kept for interface symmetry."""
        return self

    def update_star_tracker(self, q_meas):
        self.q_hat = quat_normalize(q_meas)
        return self

    def update_vector(self, v_meas, v_ref_inertial, r):
        return self

    def update(self, meas, dyn_or_r=None):
        if "st" in meas:
            self.q_hat = quat_normalize(meas["st"])
        return self

    def gyro_rate(self, omega_meas):
        return np.asarray(omega_meas)
