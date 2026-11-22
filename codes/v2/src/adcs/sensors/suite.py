"""Configurable sensor suite (gyro, star tracker, magnetometer, RW tachometers) with fault hooks."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np

from adcs.interfaces.types import FloatArray, SensorMeasurement, SpacecraftTruthState
from adcs.utils.quaternion import quat_from_rotvec, quat_multiply, quat_normalize
from adcs.utils.seeding import SeedManager


@dataclass(frozen=True)
class SensorSuiteConfig:
    """Nominal sensor noise, bias, and sampling characteristics (SI units)."""

    gyro_noise_std_rad_s: float = 2.0e-4  # ARW per step (~0.011 deg/s)
    gyro_bias_init_std_rad_s: float = 5.0e-4  # Initial turn-on bias (~0.029 deg/s)
    gyro_bias_rw_std_rad_s_sqrt_s: float = 1.0e-5  # Bias random walk
    star_tracker_noise_std_rad: float = 5.0e-4  # ~0.03 deg (103 arcsec) 1-sigma per axis
    star_tracker_rate_divider: int = 1  # Update every N control steps
    mag_noise_std_t: float = 3.0e-7  # 300 nT 1-sigma
    rw_speed_noise_std_rad_s: float = 0.05  # ~0.5 rpm tachometer noise


@dataclass
class SensorFaultParams:
    """Instantaneous sensor fault state (Scenario S6 / S8)."""

    gyro_extra_bias_rad_s: FloatArray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    gyro_drift_rate_rad_s2: FloatArray = field(
        default_factory=lambda: np.zeros(3, dtype=np.float64)
    )
    gyro_scale_factor: FloatArray = field(default_factory=lambda: np.ones(3, dtype=np.float64))
    gyro_noise_mult: float = 1.0
    gyro_dropout: bool = False

    star_tracker_dropout: bool = False
    star_tracker_delay_steps: int = 0
    star_tracker_bias_rotvec_rad: FloatArray = field(
        default_factory=lambda: np.zeros(3, dtype=np.float64)
    )
    star_tracker_noise_mult: float = 1.0
    star_tracker_invalid_glitch: bool = False

    mag_bias_t: FloatArray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    mag_noise_mult: float = 1.0
    mag_dropout: bool = False

    rw_speed_bias_rad_s: FloatArray | None = None
    rw_speed_noise_mult: float = 1.0
    rw_speed_dropout: tuple[bool, ...] | None = None


class SensorSuite:
    """Deterministic onboard sensor simulator separating truth state from measurements."""

    def __init__(self, config: SensorSuiteConfig | None = None, n_rw: int = 3) -> None:
        self.cfg = SensorSuiteConfig() if config is None else config
        self.n_rw = n_rw
        self._rng = SeedManager(0).spawn_rng("sensor_noise")
        self._gyro_bias = np.zeros(3, dtype=np.float64)
        self._step_count = 0
        self._last_valid_st_time = 0.0
        self._last_st_q = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
        self._st_queue: deque[tuple[float, FloatArray]] = deque()
        self._fault_start_time: float | None = None

    def reset(self, seed: int = 0, q_ib_init: FloatArray | None = None) -> None:
        self._rng = SeedManager(seed).spawn_rng("sensor_noise")
        self._gyro_bias = self._rng.normal(0.0, self.cfg.gyro_bias_init_std_rad_s, size=3)
        self._step_count = 0
        self._last_valid_st_time = 0.0
        self._last_st_q = (
            np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
            if q_ib_init is None
            else quat_normalize(q_ib_init)
        )
        self._st_queue = deque([(0.0, self._last_st_q.copy())])

    @property
    def true_gyro_bias_rad_s(self) -> FloatArray:
        return self._gyro_bias.copy()

    def measure(
        self,
        truth: SpacecraftTruthState,
        dt_s: float,
        faults: SensorFaultParams | None = None,
    ) -> SensorMeasurement:
        """Sample noisy, potentially faulted onboard measurements from truth state."""
        f = SensorFaultParams() if faults is None else faults
        self._step_count += 1

        # 1. Gyroscope: scale * true + bias + RW + drift + white noise
        self._gyro_bias = (
            self._gyro_bias
            + f.gyro_drift_rate_rad_s2 * dt_s
            + self._rng.normal(0.0, self.cfg.gyro_bias_rw_std_rad_s_sqrt_s * np.sqrt(dt_s), size=3)
        )
        if f.gyro_dropout:
            gyro_meas = np.zeros(3, dtype=np.float64)
            gyro_valid = False
        else:
            gyro_noise = self._rng.normal(
                0.0, self.cfg.gyro_noise_std_rad_s * f.gyro_noise_mult, size=3
            )
            gyro_meas = (
                f.gyro_scale_factor * truth.omega_body_rad_s
                + self._gyro_bias
                + f.gyro_extra_bias_rad_s
                + gyro_noise
            )
            gyro_valid = True

        # 2. Star tracker: attitude + noise + bias + delay + dropout/invalid glitch
        st_noise_vec = self._rng.normal(
            0.0, self.cfg.star_tracker_noise_std_rad * f.star_tracker_noise_mult, size=3
        )
        q_st_now = quat_normalize(
            quat_multiply(
                truth.q_ib, quat_from_rotvec(st_noise_vec + f.star_tracker_bias_rotvec_rad)
            )
        )
        self._st_queue.append((truth.time_s, q_st_now))
        max_q_len = max(1, int(f.star_tracker_delay_steps) + 1)
        while len(self._st_queue) > max_q_len:
            self._st_queue.popleft()

        st_due = (self._step_count % max(1, self.cfg.star_tracker_rate_divider)) == 0
        if f.star_tracker_dropout or not st_due:
            st_valid = False
            st_q = self._last_st_q.copy()
            st_age = max(0.0, truth.time_s - self._last_valid_st_time)
        elif f.star_tracker_invalid_glitch:
            # Corrupt quaternion (wild jump) flagged valid=True to test innovation gate
            st_valid = True
            st_q = quat_normalize(
                quat_multiply(truth.q_ib, quat_from_rotvec(np.array([1.2, -0.8, 0.5])))
            )
            st_age = 0.0
        else:
            t_meas, st_q = self._st_queue[0]
            st_valid = True
            self._last_st_q = st_q.copy()
            self._last_valid_st_time = t_meas
            st_age = max(0.0, truth.time_s - t_meas)

        # 3. Magnetometer
        if f.mag_dropout:
            mag_meas = np.zeros(3, dtype=np.float64)
            mag_valid = False
        else:
            mag_noise = self._rng.normal(0.0, self.cfg.mag_noise_std_t * f.mag_noise_mult, size=3)
            mag_meas = truth.b_field_body_t + f.mag_bias_t + mag_noise
            mag_valid = True

        # 4. RW tachometers
        rw_noise = self._rng.normal(
            0.0, self.cfg.rw_speed_noise_std_rad_s * f.rw_speed_noise_mult, size=self.n_rw
        )
        rw_bias = (
            np.zeros(self.n_rw, dtype=np.float64)
            if f.rw_speed_bias_rad_s is None
            else f.rw_speed_bias_rad_s
        )
        rw_drop = (
            (False,) * self.n_rw if f.rw_speed_dropout is None else f.rw_speed_dropout
        )
        rw_meas = truth.wheel_speed_rad_s + rw_bias + rw_noise
        rw_valid = tuple(not d for d in rw_drop)
        for i, d in enumerate(rw_drop):
            if d:
                rw_meas[i] = 0.0

        return SensorMeasurement(
            time_s=truth.time_s,
            gyro_rad_s=gyro_meas,
            gyro_valid=gyro_valid,
            star_tracker_q_ib=st_q,
            star_tracker_valid=st_valid,
            star_tracker_age_s=st_age,
            mag_body_t=mag_meas,
            mag_valid=mag_valid,
            rw_speed_rad_s=rw_meas,
            rw_speed_valid=rw_valid,
        )
