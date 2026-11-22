"""Phase 1B fault experiment: reaction-wheel degradation & failure.

Compares nadir-acquisition performance across actuator-health cases on identical
random initial conditions (same seeds):
    healthy   : tau = 1.0 * tau_cmd   (all wheels)
    rw1_50pct : RW1 delivers 50% torque
    rw1_failed: RW1 delivers 0 torque (dead wheel) -- MTQ must compensate

Run from `codes/`:
    python scripts/run_fault_experiment.py --n 40 --T 900
"""
from __future__ import annotations
import argparse
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from satellite_adcs.config import load_config
from simulate import run_episode, settling_time

CASES = {
    "healthy":    [1.0, 1.0, 1.0],
    "rw1_50pct":  [0.5, 1.0, 1.0],
    "rw1_failed": [0.0, 1.0, 1.0],
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=40)
    p.add_argument("--T", type=float, default=900.0)
    p.add_argument("--out", default="results/fault_experiment")
    a = p.parse_args()

    cfg = load_config()
    os.makedirs(a.out, exist_ok=True)
    results = {}

    for name, health in CASES.items():
        rms, fin, ts, ow = [], [], [], []
        ok = 0
        for seed in range(a.n):
            res = run_episode(cfg, seed=seed, T=a.T, rw_health=health)
            pe = res["pe"]
            st = settling_time(res["t"], pe)
            rms.append(np.sqrt(np.mean(pe**2)))
            fin.append(pe[-1])
            ts.append(st)
            ok += int(not np.isinf(st))
            ow.append(res["ow"].max())
        ts = np.array(ts)
        settled = ts[~np.isinf(ts)]
        results[name] = dict(
            success=100.0 * ok / a.n,
            settle_mean=float(np.mean(settled)) if settled.size else float("nan"),
            final_mean=float(np.mean(fin)),
            rms_mean=float(np.mean(rms)),
            wheel_max=float(np.max(ow)),
        )
        r = results[name]
        print(f"[{name:11s}] success={r['success']:5.1f}%  "
              f"settle={r['settle_mean']:6.0f}s  final={r['final_mean']:6.2f}deg  "
              f"rms={r['rms_mean']:6.1f}deg  wheel_max={r['wheel_max']:5.0f}")

    with open(os.path.join(a.out, "fault_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    names = list(results)
    x = np.arange(len(names))
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    ax[0].bar(x, [results[n]["success"] for n in names], color="tab:green")
    ax[0].set_title("success rate [%]")
    ax[1].bar(x, [results[n]["final_mean"] for n in names], color="tab:orange")
    ax[1].set_title("final pointing error [deg]")
    ax[2].bar(x, [results[n]["settle_mean"] for n in names], color="tab:blue")
    ax[2].set_title("settling time [s]")
    for axi in ax:
        axi.set_xticks(x)
        axi.set_xticklabels(names, rotation=15)
        axi.grid(alpha=0.3)
    fig.suptitle("Phase 1B — nadir acquisition under reaction-wheel faults")
    fig.tight_layout()
    fig.savefig(os.path.join(a.out, "fault_summary.png"), dpi=120)
    print("saved:", os.path.join(a.out, "fault_summary.png"))


if __name__ == "__main__":
    main()
