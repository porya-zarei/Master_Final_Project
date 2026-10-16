"""Compare the classical baselines on the FIXED plant, with paired conditions.

Variants
  lqr               the published fixed-gain baseline
  scheduled(eps)    the gain-scheduled LQR (satellite_adcs/gain_scheduled.py)

All variants share one initial condition + gyro bias per episode index
(simulate.make_ic_bias), so the comparison is paired and the LQR-vs-LQR contrast
is not confounded by different starts.

Usage:
  cd codes && PYTHONPATH=. ./venv/Scripts/python.exe scripts/compare_lqr_variants.py \
      --n 8 --T 900 --out results/lqr_variants
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from satellite_adcs.config import load_config
from simulate import make_ic_bias, run_episode, settling_time

SETTLE_DEG = 1.0
HOLDS = (10.0, 30.0)
CASES = {
    "healthy":    [1.0, 1.0, 1.0],
    "rw1_50pct":  [0.5, 1.0, 1.0],
    "rw1_failed": [0.0, 1.0, 1.0],
}
VARIANTS = [("lqr", dict(controller="lqr")),
            ("sched_eps0.05", dict(controller="scheduled", sched_eps=0.05)),
            ("sched_eps0.20", dict(controller="scheduled", sched_eps=0.20))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--T", type=float, default=900.0)
    ap.add_argument("--out", default="results/lqr_variants")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cfg = load_config()
    ics = [make_ic_bias(k, cfg) for k in range(a.n)]

    report = {"study": "classical baselines on the fixed (post-G14) plant",
              "n": a.n, "T": a.T, "holds": list(HOLDS), "cases": {}}
    for case, health in CASES.items():
        report["cases"][case] = {}
        for name, kw in VARIANTS:
            fin, settled = [], {float(h): [] for h in HOLDS}
            for k in range(a.n):
                q0, w0, b0 = ics[k]
                res = run_episode(cfg, seed=k, T=a.T, rw_health=health,
                                  ic=(q0, w0), gyro_bias=b0, **kw)
                for h in HOLDS:
                    st = settling_time(res["t"], res["pe"],
                                       threshold=SETTLE_DEG, hold=float(h))
                    settled[float(h)].append(not np.isinf(st))
                fin.append(res["pe"][-1])
            blk = {"final_mean_deg": round(float(np.mean(fin)), 4),
                   "final_median_deg": round(float(np.median(fin)), 4),
                   **{f"success_hold{int(h)}s": round(100.0 * float(np.mean(settled[float(h)])), 2)
                      for h in HOLDS}}
            report["cases"][case][name] = blk
            print(f"[{case:11s}] {name:15s} h10={blk['success_hold10s']:5.1f}% "
                  f"h30={blk['success_hold30s']:5.1f}%  final={blk['final_mean_deg']:8.3f} deg",
                  flush=True)

    p = os.path.join(a.out, "lqr_variants.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nsaved {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
