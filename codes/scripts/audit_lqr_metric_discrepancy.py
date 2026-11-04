"""Milestone A: resolve the 241.3 s vs 67.2 s LQR acquisition-time discrepancy.

Two numbers were reported for the same controller:
  report-3 section 12:  median 241.3 s
  report-3 section 13:  median  67.2 s

There are TWO candidate causes, and they must be separated, not assumed:
  (a) the METRIC differs -- section 12 used settling_time(hold=10 s) (sustained
      below tolerance), section 13 used TIME-TO-FIRST-ENTRY (< 1 deg once);
  (b) the HARNESS differs -- section 12 used simulate.run_episode (classical
      loop), section 13 drove the LQR through ADCSEnv as an action.

This computes every metric on the SAME episodes from the SAME harness, so any
remaining difference is the metric alone. It also counts tolerance crossings,
which distinguishes "slow to arrive" from "arrives but does not stay".
"""
from __future__ import annotations
import sys, os, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from satellite_adcs.config import load_config
from simulate import run_episode, make_ic_bias, settling_time

T_EP = 900.0
TOL = 1.0


def metrics(t, pe):
    below = pe < TOL
    first = float(t[np.argmax(below)]) if np.any(below) else None
    # count entries into tolerance: >1 means it leaves and re-enters
    entries = int(np.sum(np.diff(below.astype(int)) == 1))
    return {
        "t_first": first,
        "settle10": settling_time(t, pe, threshold=TOL, hold=10.0),
        "settle30": settling_time(t, pe, threshold=TOL, hold=30.0),
        "entries": entries,
        "final": float(pe[-1]),
        "frac_below": float(np.mean(below)),
    }


def main(n=8):
    cfg = load_config()
    rows = []
    for ep in range(n):
        q0, w0, bias = make_ic_bias(ep)
        r = run_episode(cfg, seed=ep, T=T_EP, ic=(q0, w0), gyro_bias=bias,
                        controller="lqr")
        m = metrics(r["t"], r["pe"])
        m["seed"] = ep
        rows.append(m)
        f = lambda v: "never" if v is None else f"{v:6.1f}"
        print(f"seed {ep}: first_entry {f(m['t_first'])}s  "
              f"settle10 {f(m['settle10'])}s  settle30 {f(m['settle30'])}s  "
              f"entries {m['entries']:2d}  below {100*m['frac_below']:4.1f}%  "
              f"final {m['final']:5.2f}deg")

    def med(key):
        v = [r[key] for r in rows if r[key] is not None]
        return float(np.median(v)) if v else None

    print(f"\nSAME episodes, SAME harness (run_episode), n={n}:")
    print(f"  median t_first   = {med('t_first')}")
    print(f"  median settle10  = {med('settle10')}")
    print(f"  median settle30  = {med('settle30')}")
    print(f"  median entries   = {med('entries')}")
    print(f"  median frac below tolerance = {np.median([r['frac_below'] for r in rows]):.3f}")

    os.makedirs("results/audit", exist_ok=True)
    with open("results/audit/lqr_metric_discrepancy.json", "w") as fh:
        json.dump(rows, fh, indent=2)
    print("saved results/audit/lqr_metric_discrepancy.json")


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 8
    main(n)
