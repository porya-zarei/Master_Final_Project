"""Sensor models: star tracker, sun sensor, gyro, magnetometer, GPS."""
from __future__ import annotations
import numpy as np

from .quaternion import quat_mult, quat_normalize


def _small_rotation(rng, std):
    """Small random rotation quaternion with axis-angle of ~N(0, std)."""
    axis = rng.normal(size=3)
    n = np.linalg.norm(axis)
    if n < 1e-12:
        return np.array([1.0, 0, 0, 0])
    axis /= n
    ang = abs(rng.normal(0.0, std))
    c, s = np.cos(ang / 2), np.sin(ang / 2)
    return np.array([c, s * axis[0], s * axis[1], s * axis[2]])


class SensorSuite:
    def __init__(self, cfg: dict, rng: np.random.Generator):
        self.cfg = cfg["sensors"]
        self.rng = rng
        self.gyro_bias = np.array([
            self.cfg["gyro"]["bias_rad_s"],
            self.cfg["gyro"]["bias_rad_s"],
            self.cfg["gyro"]["bias_rad_s"],
        ]) * self.rng.normal(size=3)
        # D.3: sensor faults (bias step, star-tracker dropout). None = none.
        self.faults = None

    def set_bias(self, bias):
        """Force an explicit gyro bias (used by the paired evaluation harness so
        that RL and LQR see the SAME bias, and by tests)."""
        self.gyro_bias = np.asarray(bias, dtype=float).copy()
        return self

    def set_faults(self, faults):
        """Attach D.3 sensor faults (None = none, and the measurement path is unchanged).

        `faults` is a `fault_taxonomy.SensorFaults`. Ground truth in the sensor only --
        no consumer may read it (D-03).
        """
        self.faults = faults
        return self

    def _gyro_bias_at(self, t):
        if self.faults is None:
            return self.gyro_bias
        return self.gyro_bias + self.faults.bias_offset(t)

    def measure(self, dyn):
        """Return a dict of measurements from the true state."""
        s = self.cfg
        rng = self.rng
        out = {}
        C = dyn.C

        if s["gyro"]["enabled"]:
            out["gyro"] = dyn.omega + self._gyro_bias_at(dyn.t) + \
                rng.normal(0.0, s["gyro"]["noise_std_rad_s"], 3)

        if s["magnetometer"]["enabled"]:
            out["mag"] = dyn.B_body + rng.normal(0.0, s["magnetometer"]["noise_std_T"], 3)

        if s["sun_sensor"]["enabled"]:
            sun_meas = C @ dyn.sun_inertial() + \
                rng.normal(0.0, s["sun_sensor"]["noise_std_rad"], 3)
            out["sun"] = sun_meas / np.linalg.norm(sun_meas)

        if s["star_tracker"]["enabled"]:
            # D.3: a dropout window means the channel is ABSENT, not noisy -- the MEKF
            # keys off `"st" in meas`, so absence is the correct signal.
            if self.faults is None or self.faults.st_available(dyn.t):
                dq = _small_rotation(rng, s["star_tracker"]["noise_std_rad"])
                out["st"] = quat_normalize(quat_mult(dq, dyn.q))

        if s["gps"]["enabled"]:
            out["gps_r"] = dyn.r + rng.normal(0.0, s["gps"]["position_noise_m"], 3)
            out["gps_v"] = dyn.v + rng.normal(0.0, s["gps"]["velocity_noise_ms"], 3)

        return out
