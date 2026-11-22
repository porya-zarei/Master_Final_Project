"""C4.2 arm verification -- WHY the form-vs-magnitude question is well posed.

Runs BEFORE any training.  Calls ADCSEnv._reward() directly with a synthetic attitude
error (zero rate, zero control) so the printed numbers are the real reward landscape of
each arm, taken from the environment itself rather than from a reading of the YAML.

The point it establishes
------------------------
`bonus` is `quad` PLUS a constant +1.0 per step while ||theta|| < 1 deg.  A constant
contributes no gradient.  Therefore BASE and A1 differ ONLY by a discontinuous step:

    arm              r(1 deg)     r(0.5 deg)   dr/dtheta @0.5deg   max episode
    BASE bonus +1.0  -3.046e-04   +9.999e-01   -0.0175 / rad       +4499.66
    A1   quad        -3.046e-04   -7.615e-05   -0.0175 / rad          -0.34

so the Phase-B gain cannot be a gradient effect.  That is what makes C4.2's three
candidate mechanisms (form / magnitude / gradient) separable by the chosen arms.

Writes: reports/figures/c4_2_reward_landscape.png (if matplotlib is available).
Usage:  cd codes && PYTHONPATH=. ./venv/Scripts/python.exe scripts/c4_2_reward_check.py
"""
from __future__ import annotations

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from satellite_adcs.environment.adcs_env import ADCSEnv

TOL_DEG = 1.0
TOL2 = float(np.radians(TOL_DEG)) ** 2
HZ, T = 5.0, 900.0
N_STEPS = int(HZ * T)                      # 4500

ARMS = [
    ("BASE   bonus +1.0", "bonus", {}),
    ("A1     quad",       "quad",  {}),
    ("S1     log",        "log",   {}),
    ("S2     bonus 0.1",  "bonus", {"reward_tol_bonus": 0.1}),
    ("S3     bonus tol^2", "bonus", {"reward_tol_bonus": TOL2}),
]


def build(shape, over):
    ov = {"rl": {"reward_shape": shape}}
    ov["rl"].update(over)
    return ADCSEnv(overrides=ov)


def main():
    print(f"tol = {TOL_DEG:.4f} deg | tol^2 = {TOL2:.6e}")
    print(f"(a near-target quad penalty at 1 deg is -{TOL2:.3e}; that is the scale S3 matches)")
    print()
    hdr = f"{'arm':22s}{'shape':8s}" + "".join(f"{d:>12s}" for d in
                                               ("5 deg", "1 deg", "0.5 deg", "0.1 deg"))
    print(hdr)
    print("-" * len(hdr))
    curves, geo = [], []
    for name, shape, over in ARMS:
        env = build(shape, over)
        row = []
        for deg in (5.0, 1.0, 0.5, 0.1):
            r, _ = env._reward(np.array([np.radians(deg), 0.0, 0.0]),
                               np.zeros(3), np.zeros(3))
            row.append(float(r))
        r_half = row[2]
        geo.append((name, r_half, r_half * N_STEPS))
        curves.append((name, env))
        print(f"{name:22s}{shape:8s}" + "".join(f"{v:>12.6f}" for v in row))
    print()

    print("Per-step reward near target and its max contribution over a full "
          f"{N_STEPS}-step episode:")
    for name, r, tot in geo:
        print(f"  {name:22s}: r_in_tol = {r:+.6e}  ->  max episode = {tot:+.4f}")
    print()

    print("Gradient of the error term w.r.t. theta at 0.5 deg (central difference, per rad):")
    for name, env in curves:
        h = 1e-7
        f = lambda x: env._reward(np.array([x, 0.0, 0.0]), np.zeros(3), np.zeros(3))[0]
        g = (f(np.radians(0.5) + h) - f(np.radians(0.5) - h)) / (2 * h)
        print(f"  {name:22s}: dr/dtheta_x = {g:+12.6f} per rad"
              f"   ({g * np.radians(1.0):+.3e} per deg)")
    print()

    save_figure(curves)
    return 0


def save_figure(curves):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:                                     # pragma: no cover
        print(f"[figure] skipped: {e}")
        return
    figdir = os.path.join(os.path.dirname(_ROOT), "reports", "figures")
    if not os.path.isdir(figdir):
        figdir = os.path.join(_ROOT, "reports", "figures")
    os.makedirs(figdir, exist_ok=True)

    th_deg = np.linspace(0.0, 5.0, 400)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.6))

    for name, env in curves:
        r = [env._reward(np.array([np.radians(d), 0.0, 0.0]), np.zeros(3), np.zeros(3))[0]
             for d in th_deg]
        ax1.plot(th_deg, r, lw=1.7, label=name)
    ax1.axvline(TOL_DEG, color="k", ls=":", lw=1, label="tolerance (1 deg)")
    ax1.axhline(0.0, color="k", lw=.6, alpha=.4)
    ax1.set_xlabel("attitude error [deg]")
    ax1.set_ylabel("per-step reward")
    ax1.set_title("reward landscape (rate and control terms = 0)")
    ax1.set_ylim(-1.6, 1.35)
    ax1.grid(alpha=.3)
    ax1.legend(fontsize=7)

    names = [n for n, _ in curves]
    tot = []
    for name, env in curves:
        r = env._reward(np.array([np.radians(0.5), 0.0, 0.0]), np.zeros(3), np.zeros(3))[0]
        tot.append(float(r) * N_STEPS)
    colors = ["tab:green" if v > 100 else "tab:gray" if v > 0 else "tab:red" for v in tot]
    ax2.bar(names, tot, color=colors)
    ax2.set_yscale("symlog", linthresh=1.0)
    ax2.axhline(0.0, color="k", lw=.8)
    ax2.set_ylabel(f"max episode contribution  (r(0.5 deg) x {N_STEPS})")
    ax2.set_title("magnitude of the near-target term, symlog scale")
    ax2.tick_params(axis="x", rotation=20, labelsize=8)
    ax2.grid(alpha=.3, axis="y")

    fig.suptitle("C4.2 -- why form vs magnitude is separable: the bonus adds a step, not a gradient",
                 fontsize=10.5)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    p = os.path.join(figdir, "c4_2_reward_landscape.png")
    fig.savefig(p, dpi=140)
    print(f"[figure] saved {p}")


if __name__ == "__main__":
    sys.exit(main())
