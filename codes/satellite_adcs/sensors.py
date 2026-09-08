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

    def measure(self, dyn):
        """Return a dict of measurements from the true state."""
        s = self.cfg
        rng = self.rng
        out = {}
        C = dyn.C

        if s["gyro"]["enabled"]:
            out["gyro"] = dyn.omega + self.gyro_bias + \
                rng.normal(0.0, s["gyro"]["noise_std_rad_s"], 3)

        if s["magnetometer"]["enabled"]:
            out["mag"] = dyn.B_body + rng.normal(0.0, s["magnetometer"]["noise_std_T"], 3)

        if s["sun_sensor"]["enabled"]:
            sun_meas = C @ dyn.sun_inertial() + \
                rng.normal(0.0, s["sun_sensor"]["noise_std_rad"], 3)
            out["sun"] = sun_meas / np.linalg.norm(sun_meas)

        if s["star_tracker"]["enabled"]:
            dq = _small_rotation(rng, s["star_tracker"]["noise_std_rad"])
            out["st"] = quat_normalize(quat_mult(dq, dyn.q))

        if s["gps"]["enabled"]:
            out["gps_r"] = dyn.r + rng.normal(0.0, s["gps"]["position_noise_m"], 3)
            out["gps_v"] = dyn.v + rng.normal(0.0, s["gps"]["velocity_noise_ms"], 3)

        return out
