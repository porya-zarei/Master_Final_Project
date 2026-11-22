"""M3.3-A unit tests: state-aware conservative allocation (same code the controller calls)."""
import numpy as np
from satellite_adcs.allocation_policy import (
    allocate_conservative, UNKNOWN, HEALTHY, DEGRADED, H_FLOOR)
import satellite_adcs.allocation_conservative as shim

TAU_MAX = 0.01
ok = []


def check(name, cond, detail=""):
    ok.append(bool(cond))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}  {detail}")


def one(tau, h, st):
    return allocate_conservative([tau] * 3, [h] * 3, [st] * 3, TAU_MAX)


t, i = one(1e-3, 1.0, HEALTHY)
check("1 HEALTHY h=1 nominal", np.allclose(t, 1e-3) and not i["compensated"], str(t))
t, i = one(1e-3, 0.0, UNKNOWN)
check("2 UNKNOWN h=0 no comp", np.allclose(t, 1e-3), str(t))
t, i = one(1e-3, 0.2, UNKNOWN)
check("3 UNKNOWN h=0.2 no comp", np.allclose(t, 1e-3), str(t))
t, i = one(1e-3, 0.5, DEGRADED)
check("4 DEGRADED h=0.5 -> 2x", np.allclose(t, 2e-3), str(t))
t, i = one(1e-3, 0.25, DEGRADED)
check("5 DEGRADED h=0.25 floored", np.allclose(t, 2e-3) and np.allclose(i["h_used"], H_FLOOR), str(t))
t, i = one(1e-3, 0.0, DEGRADED)
check("6 DEGRADED h=0 finite", np.allclose(t, 2e-3) and np.all(np.isfinite(t)), str(t))
for n, h in (("7 DEGRADED NaN", np.nan), ("8 DEGRADED Inf", np.inf)):
    t, i = one(1e-3, h, DEGRADED)
    check(n + " -> UNKNOWN", np.allclose(t, 1e-3) and i["state_name"][0] == "UNKNOWN", str(t))
t, i = allocate_conservative([1e-3]*3, None, None, TAU_MAX)
check("9 missing estimate -> UNKNOWN", np.allclose(t, 1e-3), str(t))
t, i = allocate_conservative([1e-3]*3, [0.5]*3, None, TAU_MAX)
check("10 missing state -> UNKNOWN", np.allclose(t, 1e-3), str(t))
t, i = allocate_conservative([1e-3]*3, [0.5]*3, [99]*3, TAU_MAX)
check("10b invalid state -> UNKNOWN", np.allclose(t, 1e-3), str(t))
t, i = one(0.1, 0.5, DEGRADED)
check("11 clip unconditional", np.allclose(t, TAU_MAX) and i["clipped"], str(t))
t, i = allocate_conservative([1e-3]*3, [0.0, 1.0, 0.5], [UNKNOWN, HEALTHY, DEGRADED], TAU_MAX)
check("12 mixed per-wheel", np.allclose(t, [1e-3, 1e-3, 2e-3]), f"{t} {i['h_used']}")
check("13 shim is canonical", shim.allocate_conservative is allocate_conservative)
t, i = allocate_conservative([1e-3]*3, [-0.5]*3, [DEGRADED]*3, TAU_MAX)
check("14 neg effectiveness -> UNKNOWN", np.allclose(t, 1e-3), str(t))
t, i = allocate_conservative([np.nan, 1e-3, 1e-3], [1.0]*3, [HEALTHY]*3, TAU_MAX)
check("15 non-finite tau_des -> 0", np.allclose(t[0], 0.0) and np.all(np.isfinite(t)), str(t))
t, i = allocate_conservative([1e-3]*2, [1.0]*2, [HEALTHY]*2, TAU_MAX, n_rw=3)
check("16 shape mismatch tolerated", t.shape == (3,) and np.all(np.isfinite(t)), str(t))

print(f"\n{sum(ok)}/{len(ok)} passing")
assert all(ok), "FAILURES PRESENT"
