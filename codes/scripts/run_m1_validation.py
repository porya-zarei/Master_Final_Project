"""M1 validation: LQR + MEKF nadir acquisition over N random initial conditions.

Run from `codes/`:
    python scripts/run_m1_validation.py --n 1000 --T 900
"""
from __future__ import annotations
import argparse
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from satellite_adcs.config import load_config
from simulate import run_episode, settling_time


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=200)
    p.add_argument("--T", type=float, default=900.0)
    p.add_argument("--out", default="results/m1_validation")
    a = p.parse_args()

    cfg = load_config()
    rms, mx, ts, success, fin = [], [], [], [], []
    for seed in range(a.n):
        res = run_episode(cfg, seed=seed, T=a.T)
        pe = res["pe"]
        st = settling_time(res["t"], pe)
        rms.append(np.sqrt(np.mean(pe**2)))
        mx.append(pe.max())
        ts.append(st)
        success.append(not np.isinf(st))
        fin.append(pe[-1])

    rms = np.array(rms); mx = np.array(mx); ts = np.array(ts); fin = np.array(fin)
    ok = success
    print("=" * 60)
    print(f"Episodes: {a.n}   Episode time: {a.T}s")
    print(f"Success rate (settle <1° within {a.T}s): {100*np.mean(ok):.1f}%")
    print(f"Settling time [s]:   mean={np.mean(ts[ok]):.1f}  median={np.median(ts[ok]):.1f}"
          f"  p90={np.percentile(ts[ok],90):.1f}")
    print(f"RMS pointing err [deg]: mean={np.mean(rms):.3f}  max={np.max(rms):.3f}")
    print(f"Max pointing err [deg]: mean={np.mean(mx):.3f}  p95={np.percentile(mx,95):.2f}")
    print(f"Final pointing err [deg]: mean={np.mean(fin):.3f}")

    os.makedirs(a.out, exist_ok=True)
    fig, ax = plt.subplots(1, 3, figsize=(15, 4))
    ax[0].hist(ts[ok], bins=30); ax[0].set_title("settling time [s] (successes)")
    ax[1].hist(rms, bins=30); ax[1].set_title("RMS pointing error [deg]")
    ax[2].hist(mx, bins=30); ax[2].set_title("max pointing error [deg]")
    fig.tight_layout()
    fig.savefig(os.path.join(a.out, "summary.png"), dpi=120)
    np.savez(os.path.join(a.out, "metrics.npz"), rms=rms, mx=mx, ts=ts, ok=np.array(ok))
    print("saved:", os.path.join(a.out, "summary.png"))


if __name__ == "__main__":
    main()
