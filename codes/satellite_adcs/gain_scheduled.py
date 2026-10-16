"""Gain-scheduled LQR: the credible classical competitor for the fault cases.

WHY THIS EXISTS
---------------
The published baseline is a FIXED-gain LQR. An examiner can object that such a
baseline is a straw man once a fault arrives, because its control weighting was
tuned for a healthy satellite. This module provides the honest classical
competitor so the RL claim is measured against something defensible.

WHAT IS SCHEDULED, AND WHY IT IS NOT ARBITRARY
----------------------------------------------
The allocation layer already inverts health (`tau_cmd = tau_des / h`, G13), so
for 0 < h <= 1 the loop gain from the commanded torque to the delivered torque is
UNCHANGED and the authority is ample (a typical command is ~1e-3 N.m against
h*tau_max >= 5e-3). Scheduling on h there would needlessly detune a working loop.

The genuinely lost case is h -> 0: the allocator gives up on that wheel and routes
the residual to the magnetorquers, which deliver only ~2.7e-5 N.m (measured) --
about 370x short. The axis is effectively uncontrolled, and a fixed-gain LQR keeps
demanding torque it cannot get, which also consumes the magnetorquers that are
needed for momentum dumping.

So the scheduled quantity is the REMAINING AUTHORITY per axis, and the design rule
follows the same normalisation the fixed baseline already uses
(`R == I / tau_max^2`): keep that logic per axis, with tau_max replaced by the
authority actually available on that axis,

    R_ii(h) = R0_ii / max(h_i, eps)          eps floors the blow-up at h = 0

which is exactly R0 when healthy, mild at partial health, and strongly detuning on
a lost axis -- i.e. "stop fighting for the axis you no longer have; spend the
effort where it still does something". eps is the single tuning knob and is swept
in the comparison run rather than tuned by hand.

CAVEAT, STATED PLAINLY: `h` here is the TRUE health, matching the allocator's own
oracle (G13). This compares like with like against the fixed baseline. The
`h_hat` variant is the separate deployment-realism ablation (D-C2h-1a).
"""
from __future__ import annotations

import numpy as np

from .controllers import ADCSController, design_lqr


def scheduled_R(R0: np.ndarray, h, eps: float = 0.05) -> np.ndarray:
    """Per-axis control weighting inversely proportional to remaining authority."""
    a = np.clip(np.asarray(h, dtype=float).reshape(3), eps, 1.0)
    return np.diag(np.diag(R0) / a)


def scheduled_K(J: np.ndarray, Q: np.ndarray, R0: np.ndarray, h, eps: float = 0.05):
    """LQR gain scheduled on the per-axis remaining control authority."""
    return design_lqr(J, Q, scheduled_R(R0, h, eps))


class ScheduledLQRController(ADCSController):
    """`ADCSController` whose LQR gain is re-solved from the authority per axis.

    Behaviour is IDENTICAL to the fixed-gain baseline when healthy (h = 1 gives
    R == R0 by construction), so this is a strict generalisation of it rather than
    a different controller.
    """

    def __init__(self, cfg, J, mu, a, rng, eps: float = 0.05):
        super().__init__(cfg, J, mu, a, rng)
        self.J = np.asarray(J, dtype=float)
        self.R0 = self.R.copy()
        self.eps = float(eps)
        self.n_resolves = 0

    def control(self, meas, est, dyn, t, dt, h_hat=None):
        h = dyn.rw_health if h_hat is None else h_hat
        R = scheduled_R(self.R0, h, self.eps)
        if not np.allclose(R, self.R):
            self.R = R
            self.K = design_lqr(self.J, self.Q, self.R)
            self.n_resolves += 1
        return super().control(meas, est, dyn, t, dt)
