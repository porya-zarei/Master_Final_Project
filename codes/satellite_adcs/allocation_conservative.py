"""M3.1: conservative allocation under UNKNOWN wheel health.

DESIGN (documented before implementation)

For each wheel i, the health state is HEALTHY / DEGRADED / UNKNOWN (see
friction_estimation.STATE_NAME). The allocation rule is

    h_used[i] = 1.0                    if state == UNKNOWN
    h_used[i] = max(h_hat[i], H_FLOOR) if state == DEGRADED
    tau_cmd   = clip( tau_des / h_used , -tau_max, +tau_max )

Properties, and why each one matters:

1. No division by an unverified estimate. UNKNOWN -> h_used = 1 -> tau_cmd = tau_des,
   i.e. the wheel is treated as nominal for COMMANDING purposes (it is not assumed
   healthy for decision purposes; it simply receives no compensation).
2. No unbounded compensation. DEGRADED divides by at least H_FLOOR, so the commanded
   torque never exceeds tau_des / H_FLOOR before the hard clip. A zero or near-zero
   estimate can therefore never produce an enormous command -- this is the exact
   failure that made B2 invalid in M2 (h_hat -> 0, tau_des/h -> saturation).
3. Torque limit is enforced unconditionally, independent of the health logic.
4. Magnetorquer allocation is untouched: tau_MT = m x B, computed by the caller.

KNOWN LIMITATION, stated up front: if a wheel is dead and its health is UNKNOWN, the
craft under-actuates -- the command is issued and not delivered. This degrades pointing
but cannot destabilise the loop numerically. It trades performance for safety, and the
degradation must be measured, not assumed.
"""
from __future__ import annotations
import numpy as np

H_FLOOR = 0.5   # lower bound on effectiveness used for DIVISION; 2x amplification cap


def allocate_conservative(tau_des, h_hat, state, tau_max, h_floor=H_FLOOR,
                          unknown_state=0):
    """Conservative allocation. Returns (tau_cmd, info).

    Parameters
    ----------
    tau_des : (3,) desired body torque
    h_hat   : (3,) estimated effectiveness (ignored where state == UNKNOWN)
    state   : (3,) integer health state, UNKNOWN == unknown_state
    tau_max : scalar per-wheel torque limit
    """
    tau_des = np.asarray(tau_des, float).reshape(3)
    h_hat = np.asarray(h_hat, float).reshape(3)
    state = np.asarray(state, dtype=int).reshape(3)

    is_unknown = state == unknown_state
    h_used = np.where(is_unknown, 1.0, np.maximum(h_hat, float(h_floor)))

    raw = tau_des / h_used
    tau_cmd = np.clip(raw, -tau_max, tau_max)

    return tau_cmd, {
        "h_used": h_used,
        "unknown_mask": is_unknown,
        "amplification": h_used,
        "clipped": bool(np.any(np.abs(raw) > tau_max)),
        "max_amplification": float(np.max(1.0 / h_used)),
    }


def main():
    """Isolated safety tests (no closed loop)."""
    tau_max = 0.01
    UNK = 0
    print("M3.1 conservative allocation -- isolated safety tests\n")
    ok = True

    # 1. all UNKNOWN -> no compensation
    t, i = allocate_conservative([1e-3, 2e-3, 3e-3], [1, 0, 1], [UNK]*3, tau_max)
    p = np.allclose(t, [1e-3, 2e-3, 3e-3]); ok &= p
    print(f"1 all-UNKNOWN            h_used={i['h_used']} tau={np.round(t,6)} "
          f"max_amp={i['max_amplification']:.2f} -> {'OK' if p else 'FAIL'}")

    # 2. UNKNOWN with h_hat = 0 (the M2 failure mode) must NOT blow up
    t, i = allocate_conservative([1e-3]*3, [0.0, 0.0, 0.0], [UNK]*3, tau_max)
    p = np.allclose(t, [1e-3]*3); ok &= p
    print(f"2 UNKNOWN, h_hat=0       tau={np.round(t,6)} (was saturation in M2) "
          f"-> {'OK' if p else 'FAIL'}")

    # 3. DEGRADED h=0.5 -> 2x compensation, within limit
    t, i = allocate_conservative([1e-3]*3, [0.5]*3, [2]*3, tau_max)
    p = np.allclose(t, [2e-3]*3); ok &= p
    print(f"3 DEGRADED h=0.5         tau={np.round(t,6)} -> {'OK' if p else 'FAIL'}")

    # 4. DEGRADED h=0 -> floored at H_FLOOR, not infinite
    t, i = allocate_conservative([1e-3]*3, [0.0]*3, [2]*3, tau_max)
    p = np.allclose(t, [2e-3]*3); ok &= p
    print(f"4 DEGRADED h=0           tau={np.round(t,6)} h_used={i['h_used']} "
          f"(floor) -> {'OK' if p else 'FAIL'}")

    # 5. torque limit enforced regardless of health
    t, i = allocate_conservative([0.1]*3, [0.1]*3, [2]*3, tau_max)
    p = np.allclose(t, [tau_max]*3) and i["clipped"]; ok &= p
    print(f"5 limit enforced         tau={np.round(t,6)} clipped={i['clipped']} "
          f"-> {'OK' if p else 'FAIL'}")

    # 6. mixed unknown / degraded / healthy
    t, i = allocate_conservative([1e-3]*3, [0.5, 1.0, 0.25], [UNK, 1, 2], tau_max)
    # wheel 3 has h_hat=0.25, BELOW H_FLOOR, so h_used = 0.5 -> 2x not 4x
    p = np.allclose(t, [1e-3, 1e-3, 2e-3]) and np.allclose(i["h_used"], [1.0, 1.0, 0.5]); ok &= p
    print(f"6 mixed states           tau={np.round(t,6)} h_used={i['h_used']} "
          f"-> {'OK' if p else 'FAIL'}")

    # 7. NaN / invalid estimate must not propagate
    t, i = allocate_conservative([1e-3]*3, [np.nan, np.nan, np.nan], [UNK]*3, tau_max)
    p = np.all(np.isfinite(t)); ok &= p
    print(f"7 NaN estimates, UNKNOWN tau={np.round(t,6)} finite={np.all(np.isfinite(t))} "
          f"-> {'OK' if p else 'FAIL'}")

    print("\nALL OK" if ok else "\nSOME TESTS FAILED")


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------- M3.3-A shim
# Compatibility only. The canonical implementation is allocation_policy.py; importing
# it here REBINDS the names above, so exactly one implementation exists and the two
# files cannot silently diverge. test_allocation_policy asserts the identity.
from .allocation_policy import (  # noqa: E402,F401
    allocate_conservative, resolve_effectiveness, valid_effectiveness,
    UNKNOWN, HEALTHY, DEGRADED, STATE_NAME, H_FLOOR, H_MAX,
)
