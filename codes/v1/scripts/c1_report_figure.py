"""C1 report figure: pre-fix vs corrected time base, paired on identical initial conditions.

Reads results/c1_regeneration/pe_series.npz (per-episode pointing-error series for the
same seeds under both time bases) and writes reports/figures/c1_timebase_ab.png.

The point of the figure is that the pre-fix time base was a PURE 1.25x label stretch:
the paired settling-time ratio collapses onto exactly 0.8.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)
import simulate

RES = os.path.join(_ROOT, "results", "c1_regeneration")
OUT = os.path.normpath(os.path.join(_ROOT, "..", "reports", "figures",
                                    "c1_timebase_ab.png"))
CASES = ["healthy", "rw1_50pct", "rw1_failed"]
N = {"healthy": 60, "rw1_50pct": 30, "rw1_failed": 30}
LABEL = {"healthy": "healthy", "rw1_50pct": "RW1 @ 50 %", "rw1_failed": "RW1 dead"}
HOLD = 10.0
PERIOD = {"fixed": 0.2, "legacy": 0.25}


def settle_time(d, case, variant, seed):
    pe = d[f"{case}|{variant}|{seed}"]
    t = np.arange(1, len(pe) + 1) * PERIOD[variant]
    st = simulate.settling_time(t, pe, threshold=1.0, hold=HOLD)
    return float(st) if np.isfinite(st) else None


def main():
    d = np.load(os.path.join(RES, "pe_series.npz"))
    rep = json.load(open(os.path.join(RES, "c1_regeneration.json"), encoding="utf-8"))

    # paired settling times
    paired = {}
    for case in CASES:
        rows = []
        for s in range(N[case]):
            fx, lg = settle_time(d, case, "fixed", s), settle_time(d, case, "legacy", s)
            rows.append((lg, fx))
        paired[case] = rows

    fig, ax = plt.subplots(2, 2, figsize=(13.5, 9))

    # (a) paired ratio histogram
    ratios = [fx / lg for case in ("healthy", "rw1_50pct") for lg, fx in paired[case]
              if lg is not None and fx is not None]
    ax[0, 0].hist(ratios, bins=np.arange(0.75, 1.35, 0.025), color="tab:blue",
                  edgecolor="k", alpha=0.85)
    ax[0, 0].axvline(0.8, color="crimson", lw=2,
                     label=f"predicted 0.8  ({sum(abs(r-0.8)<1e-9 for r in ratios)}"
                           f"/{len(ratios)} pairs exactly)")
    ax[0, 0].set_xlabel("paired settling-time ratio   fixed / legacy")
    ax[0, 0].set_ylabel("episodes")
    ax[0, 0].set_title("(a) the time-base fix is a pure x1.25 label stretch")
    ax[0, 0].legend(fontsize=8)
    ax[0, 0].grid(alpha=0.3)

    # (b) paired scatter
    for case, color in zip(("healthy", "rw1_50pct"), ("tab:green", "tab:orange")):
        pts = [(lg, fx) for lg, fx in paired[case] if lg is not None and fx is not None]
        if pts:
            ax[0, 1].scatter([p[0] for p in pts], [p[1] for p in pts], s=22, color=color,
                             label=f"{LABEL[case]} (n={len(pts)})", alpha=0.8)
    lim = 900
    ax[0, 1].plot([0, lim], [0, lim * 0.8], "r--", lw=1.6, label="y = 0.8 x")
    ax[0, 1].plot([0, lim], [0, lim], "k:", lw=1, label="y = x")
    ax[0, 1].set_xlim(0, lim)
    ax[0, 1].set_ylim(0, lim * 0.8)
    ax[0, 1].set_xlabel("settling time on the PRE-FIX labelled axis [s]")
    ax[0, 1].set_ylabel("settling time on the corrected axis [s]")
    ax[0, 1].set_title("(b) paired settling times, identical initial conditions")
    ax[0, 1].legend(fontsize=8)
    ax[0, 1].grid(alpha=0.3)

    # (c) success rates
    x = np.arange(len(CASES))
    for k, (hold, alpha) in enumerate((("hold10_s", 0.95), ("hold30_s", 0.45))):
        w = 0.38
        lg = [rep["cases"][c]["legacy"][hold]["success_pct"] for c in CASES]
        fx = [rep["cases"][c]["fixed"][hold]["success_pct"] for c in CASES]
        ax[1, 0].bar(x + (k - 0.5) * w, lg, w * 0.9, color="tab:gray", alpha=alpha,
                     label=f"pre-fix ({hold.split('_')[0]} hold)")
        ax[1, 0].bar(x + (k + 0.5) * w, fx, w * 0.9, color="tab:blue", alpha=alpha,
                     label=f"corrected ({hold.split('_')[0]} hold)")
    for i, c in enumerate(CASES):
        lg = rep["cases"][c]["legacy"]["hold10_s"]["success_pct"]
        fx = rep["cases"][c]["fixed"]["hold10_s"]["success_pct"]
        ax[1, 0].text(i - 0.19, lg + 1.5, f"{lg:.0f}", ha="center", fontsize=8)
        ax[1, 0].text(i + 0.19, fx + 1.5, f"{fx:.0f}", ha="center", fontsize=8)
    ax[1, 0].set_xticks(x)
    ax[1, 0].set_xticklabels([LABEL[c] for c in CASES])
    ax[1, 0].set_ylabel("success rate [%]")
    ax[1, 0].set_ylim(0, 105)
    ax[1, 0].set_title("(c) success is threshold-based: it does NOT drop\n"
                       "(the corrected base also runs 900 s instead of 720 s)")
    ax[1, 0].legend(fontsize=7.5)
    ax[1, 0].grid(alpha=0.3, axis="y")

    # (d) final pointing error
    lg = [rep["cases"][c]["legacy"]["final_pe_deg"]["mean"] for c in CASES]
    fx = [rep["cases"][c]["fixed"]["final_pe_deg"]["mean"] for c in CASES]
    ax[1, 1].bar(x - 0.19, lg, 0.36, color="tab:gray", label="pre-fix (720 s physics)")
    ax[1, 1].bar(x + 0.19, fx, 0.36, color="tab:blue", label="corrected (900 s physics)")
    for i in range(len(CASES)):
        ax[1, 1].text(i - 0.19, lg[i] + 1.2, f"{lg[i]:.2f}", ha="center", fontsize=8)
        ax[1, 1].text(i + 0.19, fx[i] + 1.2, f"{fx[i]:.2f}", ha="center", fontsize=8)
    ax[1, 1].set_xticks(x)
    ax[1, 1].set_xticklabels([LABEL[c] for c in CASES])
    ax[1, 1].set_ylabel("final pointing error [deg]")
    ax[1, 1].set_title("(d) final pointing error: ~unchanged when converged;\n"
                       "the dead-wheel case DRIFTS further with the longer horizon")
    ax[1, 1].legend(fontsize=8)
    ax[1, 1].grid(alpha=0.3, axis="y")

    fig.suptitle("C1 - regeneration on the corrected time base (identical seeds, paired A/B)",
                 fontsize=13)
    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=130)
    plt.close(fig)
    print("wrote:", OUT)
    print("ratio stats: n=%d  exactly-0.8=%d  min=%.4f  max=%.4f  median=%.4f"
          % (len(ratios), sum(abs(r - 0.8) < 1e-9 for r in ratios),
             min(ratios), max(ratios), float(np.median(ratios))))


if __name__ == "__main__":
    main()
