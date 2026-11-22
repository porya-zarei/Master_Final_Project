"""M1 (D-C2h-1a): oracle allocator vs estimated allocator, with a MID-FLIGHT fault.

Question this answers: what does it cost a classical controller when it must
allocate from an estimated wheel health instead of being handed the truth?

The fault is applied at T_FAULT (not t=0) because a fault present from the first
step is already masked by the allocator; the interesting regime is the transient
after a mid-flight failure, where the estimator has to learn h from the response.

Both arms get identical initial conditions and an identical gyro bias (paired),
the same estimator, the same controller gains and the same actuator model. The
ONLY difference is what the allocator is told about wheel health.
"""
from __future__ import annotations
import sys, os, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from satellite_adcs.config import load_config
from simulate import run_episode, make_ic_bias

T_FAULT = 300.0
T_EP = 900.0
TOL = 1.0
HOLD = 30.0

CASES = {
    "healthy": None,
    "rw1_50pct": np.array([0.5, 1.0, 1.0]),
    "rw1_failed": np.array([0.0, 1.0, 1.0]),
}


def _success(t, pe, hold):
    m = t >= (t[-1] - hold)
    return float(np.mean(pe[m] < TOL))


def _recovery(t, pe, fault_at, hold=HOLD):
    """Seconds from the fault until pe stays < TOL for `hold` s; None if never.

    A fault applied to an already-settled satellite does not knock it out of
    tolerance immediately, so a naive "first interval below TOL" reports a fake
    0 s. The excursion is located first: recovery is measured only if the error
    actually LEAVES the band after the fault. Returns 0.0 for "never disturbed".
    """
    after = t >= fault_at
    tt, pp = t[after], pe[after]
    dt = float(np.median(np.diff(t)))
    n = max(1, int(round(hold / dt)))
    exc = np.where(pp > TOL)[0]
    if len(exc) == 0:
        return 0.0                      # the fault did not disturb the pointing
    for i in range(int(exc[0]), len(pp) - n + 1):
        if np.all(pp[i:i + n] < TOL):
            return float(tt[i] - fault_at)
    return None


def _overshoot(t, pe, fault_at, window=60.0):
    m = (t >= fault_at) & (t <= fault_at + window)
    return float(np.max(pe[m])) if np.any(m) else float("nan")


def main(n=8):
    cfg = load_config()
    results = {}

    for case, health in CASES.items():
        arms = {}
        for arm in ("lqr_true", "lqr_hat"):
            finals, s10, s30, rec, over, hfin = [], [], [], [], [], []
            for ep in range(n):
                q0, w0, bias = make_ic_bias(ep)   # single source of truth
                ic = (q0, w0)
                out = run_episode(
                    cfg, seed=ep, T=T_EP,
                    rw_health=health,
                    fault_at=(T_FAULT if health is not None else None),
                    health_source=("hat" if arm == "lqr_hat" else "true"),
                    ic=ic, gyro_bias=bias, controller="lqr",
                )
                t, pe = out["t"], out["pe"]
                finals.append(float(pe[-1]))
                s10.append(_success(t, pe, 10.0))
                s30.append(_success(t, pe, 30.0))
                if health is not None:
                    rec.append(_recovery(t, pe, T_FAULT))
                    over.append(_overshoot(t, pe, T_FAULT))
                if out["h_est"] is not None:
                    hfin.append(np.asarray(out["h_est"].h).ravel())
            got = [r for r in rec if r is not None]
            arms[arm] = {
                "n": n,
                "final_mean": float(np.mean(finals)),
                "success_hold10s": float(100 * np.mean(s10)),
                "success_hold30s": float(100 * np.mean(s30)),
                "recovered": len(got),
                "recovery_median_s": (float(np.median(got)) if got else None),
                "overshoot_max_deg": (float(np.nanmax(over)) if over else None),
                "h_hat_final_mean": (np.round(np.mean(hfin, axis=0), 3).tolist()
                                     if hfin else None),
            }
        results[case] = arms
        print(f"\n[{case}]  (fault at {T_FAULT if health is not None else '-'} s)")
        for arm, m in arms.items():
            r = (f"{m['recovery_median_s']:.0f}s" if m['recovery_median_s'] is not None
                 else "never")
            print(f"  {arm:9s} success h10={m['success_hold10s']:5.1f}% "
                  f"h30={m['success_hold30s']:5.1f}%  final={m['final_mean']:6.2f}deg  "
                  f"recovered {m['recovered']}/{n} in {r}  "
                  f"peak={m['overshoot_max_deg'] if m['overshoot_max_deg'] is None else round(m['overshoot_max_deg'],1)}deg  "
                  f"h_hat={m['h_hat_final_mean']}")

    os.makedirs("results/m1_hat", exist_ok=True)
    with open("results/m1_hat/m1_oracle_vs_hat.json", "w") as f:
        json.dump({"T_fault": T_FAULT, "T_episode": T_EP, "cases": results}, f, indent=2)
    print("\nsaved results/m1_hat/m1_oracle_vs_hat.json")


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 8
    main(n)
