"""C.1 — reaction-wheel speed sensing (tachometer model), DEFAULT OFF.

WHY THIS EXISTS
  Every estimator result so far (E-15…E-20, M3.4) fed the estimator the PLANT's exact
  `omega_w`. That is the single most favourable assumption in the fault-awareness chain: the
  RLS regressand is `J_w * d(omega_w)/dt`, a derivative, so wheel-speed measurement error is
  amplified by `J_w/dt` before it ever reaches the estimator. At this plant's numbers
  (`J_w = 2e-4`, `dt = 0.02 s`) a 0.05 rad/s sample error becomes ~7e-4 N·m of apparent
  torque -- several times the Coulomb friction (2e-4 N·m) the estimator is supposed to find.
  Whether the estimator survives that is an experiment, not an opinion; this module supplies
  the sensor so the experiment can be run.

CHAIN (order matters, and it is the physical order)
    true omega_w -> full-scale clamp -> quantise to the encoder LSB -> additive read-out noise
                 -> zero-order hold for `sample_period_s`
  Quantising before the noise is correct: the encoder quantises the real speed, and the
  read-out noise is downstream of it. Clamping first models a sensor that saturates.

DEFAULT OFF
  `sensors.tachometer.enabled: false` ships in the repo. `make_wheel_sensor(cfg)` then
  returns None, `run_episode(wheel_sensor=None)` passes `dyn.omega_w` through unchanged, and
  every historical number reproduces bit-identically.
"""
from __future__ import annotations
import numpy as np


class TachometerModel:
    """Callable wheel-speed sensor: `meas = model(dyn.omega_w)`.

    Parameters are in `sensors.tachometer` (see `config/sensors.yaml`).

    `dt_s` is the CONTROL period: the zero-order hold updates every
    `max(1, round(sample_period_s / dt_s))` calls. With the shipped 5 Hz control and a 5 Hz
    sample period the hold is a no-op, which is the honest default (a tachometer is usually
    sampled at the control rate, not slower).
    """

    def __init__(self, noise_std: float = 0.05, quant: float = 5e-3,
                 sample_period_s: float = 0.2, dt_s: float = 0.2,
                 max_speed: float = 628.3, n_rw: int = 3, rng=None):
        self.noise_std = float(noise_std)
        self.quant = float(quant)
        self.max_speed = float(max_speed)
        self.n_rw = int(n_rw)
        self.rng = np.random.default_rng(0) if rng is None else rng
        self.hold = max(1, int(round(float(sample_period_s) / float(dt_s))))
        self._n = 0
        self._held = np.zeros(self.n_rw)

    def reset(self):
        self._n = 0
        self._held = np.zeros(self.n_rw)
        return self

    def sample(self, omega_w) -> np.ndarray:
        """One sensor read: clamp -> quantise -> noise."""
        w = np.asarray(omega_w, dtype=float).reshape(self.n_rw)
        w = np.clip(w, -self.max_speed, self.max_speed)
        if self.quant > 0.0:
            w = self.quant * np.round(w / self.quant)
        if self.noise_std > 0.0:
            w = w + self.rng.normal(0.0, self.noise_std, self.n_rw)
        return w

    def __call__(self, omega_w) -> np.ndarray:
        """Measured speed, zero-order held between sample instants."""
        if self._n % self.hold == 0:
            self._held = self.sample(omega_w)
        self._n += 1
        return self._held.copy()

    def describe(self) -> dict:
        return {"noise_std_rad_s": self.noise_std, "quant_rad_s": self.quant,
                "hold_steps": self.hold, "max_speed_rad_s": self.max_speed}


def make_wheel_sensor(cfg, seed: int = 0):
    """Build the sensor from config, or None when it is disabled (the shipped default).

    Returns None for absent/disabled config so callers can pass the result straight into
    `run_episode(wheel_sensor=...)` without a branch.
    """
    spec = (cfg.get("sensors") or {}).get("tachometer") or {}
    if not spec.get("enabled", False):
        return None
    rw = cfg["actuators"]["reaction_wheels"]
    # the model is applied once per CONTROL update, so its time base is the control period
    ctrl_dt = 1.0 / float(cfg["simulation"]["control_hz"])
    # explicit null in YAML means "use the actuator full scale"; .get() would NOT fall back
    # because the key exists with value None
    max_speed = spec.get("max_speed_rad_s")
    if max_speed is None:
        max_speed = rw["max_speed_rad_s"]
    return TachometerModel(
        noise_std=float(spec.get("noise_std_rad_s", 0.05)),
        quant=float(spec.get("quant_rad_s", 5e-3)),
        sample_period_s=float(spec.get("sample_period_s", ctrl_dt)),
        dt_s=ctrl_dt,
        max_speed=float(max_speed),
        n_rw=int(rw["count"]),
        rng=np.random.default_rng(seed),
    )
