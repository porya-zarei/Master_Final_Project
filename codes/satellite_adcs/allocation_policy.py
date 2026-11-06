"""Canonical state-aware conservative allocation (M3.3-A).

Single implementation. The controller calls this directly; the old module
`allocation_conservative.py` re-exports it so the two names cannot diverge.

POLICY
    UNKNOWN  -> h_used = 1.0                      (no compensation)
    HEALTHY  -> h_used = 1.0                      (nominal)
    DEGRADED -> h_used = max(h_hat, H_FLOOR)      (bounded compensation)
    tau_cmd  = clip(tau_des / h_used, -tau_max, +tau_max)

WHY UNKNOWN GETS NO COMPENSATION
An unconverged, missing or invalid estimate carries no information. Dividing by it is
exactly what turned the M2 baseline into a saturation artefact (h_hat -> 0 gave
tau_des/0 -> full torque limit on every wheel, with a falsely excellent result).
"No compensation" is the only choice that cannot manufacture performance.

WHY DEGRADED IS FLOORED
A verified low effectiveness still has estimation error; the floor bounds the command
to tau_des / H_FLOOR and guarantees a finite result even at h = 0.

INVALID INPUTS (NaN, +-inf, h <= 0, h > 1.5, wrong size, unknown state) are rejected
PER WHEEL and demoted to UNKNOWN. Output is always finite and within +-tau_max.
Magnetorquers are untouched: tau_MT = m x B is computed by the caller.
"""
from __future__ import annotations
import numpy as np

UNKNOWN, HEALTHY, DEGRADED = 0, 1, 2
STATE_NAME = {UNKNOWN: "UNKNOWN", HEALTHY: "HEALTHY", DEGRADED: "DEGRADED"}

H_FLOOR = 0.5
H_MAX = 1.5


def _vec(x, n, fill):
    if x is None:
        return np.full(n, fill, dtype=float)
    a = np.asarray(x, dtype=float).ravel()
    if a.size != n:
        return np.full(n, fill, dtype=float)
    return a


def valid_effectiveness(h):
    h = np.asarray(h, dtype=float)
    # h == 0 is a VALID but extreme estimate: it means "no effectiveness", and the
    # DEGRADED floor exists precisely to bound the command in that case. Negative,
    # NaN and infinite values are not physical and are demoted to UNKNOWN instead.
    return np.isfinite(h) & (h >= 0.0) & (h <= H_MAX)


def resolve_effectiveness(h_hat, state, n_rw=3, h_floor=H_FLOOR):
    """Return (h_used, effective_state). Invalid DEGRADED -> demoted to UNKNOWN."""
    h = _vec(h_hat, n_rw, np.nan)
    if state is None:
        st = np.full(n_rw, UNKNOWN, dtype=int)
    else:
        raw = np.asarray(state).ravel()
        st = (np.full(n_rw, UNKNOWN, dtype=int) if raw.size != n_rw
              else raw.astype(int))
    st = np.where(np.isin(st, (UNKNOWN, HEALTHY, DEGRADED)), st, UNKNOWN)

    ok = valid_effectiveness(h)
    h_used = np.ones(n_rw, dtype=float)
    eff = st.copy()
    degraded = (st == DEGRADED) & ok
    h_used[degraded] = np.maximum(h[degraded], float(h_floor))
    eff[(st == DEGRADED) & (~ok)] = UNKNOWN
    return h_used, eff


def allocate_conservative(tau_des, h_hat, state, tau_max, n_rw=3, h_floor=H_FLOOR):
    """State-aware allocation. Returns (tau_cmd, info); output always finite."""
    tau_des = _vec(tau_des, n_rw, 0.0)
    tau_des = np.where(np.isfinite(tau_des), tau_des, 0.0)
    h_used, eff = resolve_effectiveness(h_hat, state, n_rw=n_rw, h_floor=h_floor)
    raw = tau_des / h_used
    tau_max = float(tau_max)
    tau_cmd = np.clip(raw, -tau_max, tau_max)
    return tau_cmd, {
        "h_used": h_used,
        "state_effective": eff,
        "state_name": [STATE_NAME[int(s)] for s in eff],
        "compensated": bool(np.any(h_used != 1.0)),
        "clipped": bool(np.any(np.abs(raw) > tau_max)),
        "max_amplification": float(np.max(1.0 / h_used)),
    }
