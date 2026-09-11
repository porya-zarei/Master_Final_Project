"""Attitude estimator: star-tracker attitude + gyro rate.

NOT an MEKF. This is a placeholder: the class name is kept for interface symmetry
with a future estimator, but `propagate()` is a no-op and `update_vector()` returns
`self` -- there is no attitude/bias state and no covariance.

M1 uses a star tracker that provides an absolute, high-accuracy attitude
(noise ~5e-5 rad). The attitude estimate is therefore taken directly from the star
tracker and, because `SensorSuite.measure()` is invoked once per control step, it is
refreshed at the CONTROL rate (5 Hz) -- not at the `simulation.estimator_hz` value,
which no code path currently reads. The gyro supplies the angular-rate estimate
(omega_hat = measured gyro); the gyro bias is NOT estimated and is neglected here.

This avoids the attitude/bias observability coupling that can make a fused MEKF
unstable during large-angle acquisition. A full MEKF with gyro-bias estimation is a
later milestone (see docs/PhaseC_to_F_Master_Plan.md, SS C-I).
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
