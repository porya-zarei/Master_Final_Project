"""D.3 fault taxonomy — every family behind a flag, ALL DEFAULT OFF.

Reason for this module rather than more edits inside `dynamics.py`: the plant's
historical numbers must stay bit-identical unless a fault is explicitly requested
(invariant "flags-off reproducibility"), so the schedules live here and the plant
consults them only when `set_wheel_faults()` has been called. With no schedule the
plant executes exactly the code it executed before.

FAMILIES
  wheel:
    dead          h -> 0 after t0.  The motor delivers nothing, so the wheel cannot be
                  driven -- but bearing friction can still rotate it, and the reaction
                  torque still reaches the structure.  This is an effectiveness loss.
    locked        h -> 0 after t0 AND the wheel is mechanically jammed: it cannot rotate
                  at all and transmits nothing to the structure.  Physically different
                  from `dead` (a dead wheel spins freely under friction), and the
                  difference is observable in the wheel speed -- see the regression test.
    ramp          h(t) = max(floor, 1 - rate*(t - t0)): gradual degradation.
    intermittent  h toggles between 1 and `depth` with period `period`, degraded for the
                  first `duty` fraction of each period: a bearing that sticks and frees.
  sensor:
    gyro bias step   the bias jumps by `bias_step_delta` at `bias_step_at`.
    star-tracker dropout   the "st" measurement is ABSENT inside each window (the MEKF
                  keys off `"st" in meas`, so absence is the correct signal, not a large
                  noise value).

TRUTH DISCIPLINE (D-03): a schedule is ground truth in the plant. It must never be read
by a controller or an estimator; the only legitimate consumers are diagnostics and the
fault-injection harness.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np

NONE = "none"
DEAD = "dead"
LOCKED = "locked"
RAMP = "ramp"
INTERMITTENT = "intermittent"
WHEEL_KINDS = (NONE, DEAD, LOCKED, RAMP, INTERMITTENT)


@dataclass(frozen=True)
class WheelFault:
    """One wheel's fault. `t0` is the onset time in seconds (0 = present from the start)."""
    wheel: int
    kind: str = NONE
    t0: float = 0.0
    rate: float = 0.10          # ramp: health lost per second
    floor: float = 0.50         # ramp: health never goes below this
    period: float = 60.0        # intermittent
    duty: float = 0.50          # intermittent: fraction of each period spent degraded
    depth: float = 0.50         # intermittent: health while degraded

    def __post_init__(self):
        if self.kind not in WHEEL_KINDS:
            raise ValueError(f"unknown wheel fault kind {self.kind!r}; "
                             f"expected one of {WHEEL_KINDS}")
        if not 0.0 <= self.depth <= 1.0:
            raise ValueError("depth must be in [0, 1]")
        if not 0.0 <= self.duty <= 1.0:
            raise ValueError("duty must be in [0, 1]")

    def health(self, t: float) -> float:
        if t < self.t0 or self.kind == NONE:
            return 1.0
        if self.kind in (DEAD, LOCKED):
            return 0.0
        if self.kind == RAMP:
            return float(max(self.floor, 1.0 - self.rate * (t - self.t0)))
        if self.kind == INTERMITTENT:
            phase = ((t - self.t0) % self.period) / self.period
            return float(self.depth) if phase < self.duty else 1.0
        return 1.0

    def is_locked(self, t: float) -> bool:
        return self.kind == LOCKED and t >= self.t0


class WheelFaultSchedule:
    """Per-wheel health and lock state as a function of time."""

    def __init__(self, faults=(), n_rw: int = 3):
        self.faults = list(faults)
        self.n_rw = int(n_rw)
        for f in self.faults:
            if not 0 <= f.wheel < self.n_rw:
                raise ValueError(f"wheel index {f.wheel} outside 0..{self.n_rw-1}")

    def __len__(self):
        return len(self.faults)

    def health(self, t: float) -> np.ndarray:
        h = np.ones(self.n_rw, dtype=float)
        for f in self.faults:
            h[f.wheel] = f.health(t)
        return h

    def locked(self, t: float) -> np.ndarray:
        m = np.zeros(self.n_rw, dtype=bool)
        for f in self.faults:
            if f.is_locked(t):
                m[f.wheel] = True
        return m

    def describe(self) -> list:
        out = []
        for f in self.faults:
            d = {"wheel": f.wheel, "kind": f.kind, "t0": f.t0}
            if f.kind == RAMP:
                d.update(rate=f.rate, floor=f.floor)
            elif f.kind == INTERMITTENT:
                d.update(period=f.period, duty=f.duty, depth=f.depth)
            out.append(d)
        return out


@dataclass(frozen=True)
class SensorFaults:
    """Sensor-side faults. Both default off."""
    bias_step_at: float | None = None
    bias_step_delta: tuple = (0.0, 0.0, 0.0)
    st_dropouts: tuple = ()      # ((t0, t1), ...) half-open windows

    def bias_offset(self, t: float) -> np.ndarray:
        if self.bias_step_at is None or t < self.bias_step_at:
            return np.zeros(3)
        return np.asarray(self.bias_step_delta, dtype=float)

    def st_available(self, t: float) -> bool:
        return not any(t0 <= t < t1 for (t0, t1) in self.st_dropouts)
