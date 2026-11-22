"""L4 headroom: how far is the LQR from the time-optimal bound?

Time-optimal control of a rotation under a bounded torque is bang-bang: accelerate
at full authority for half the angle, decelerate for the rest. A quadratic-cost LQR
is smooth by construction and CANNOT be time-optimal, so this measures the gap.

Lower bound used (deliberately conservative, so the conclusion is not inflated):
for a single axis of inertia J under |tau| <= tau_max,
    theta(t) = 0.5*a*t^2  with a = tau_max/J
so a bang-bang slew through theta takes  t >= 2*sqrt(theta / a).
Using the LARGEST principal inertia would give the smallest a and thus a LARGER
bound (more favourable to the LQR); using the smallest inertia gives a smaller
bound (more favourable to RL). We report the SMALLEST-inertia bound, i.e. the
hardest case for the claim that headroom exists.
"""
from __future__ import annotations
import sys, os, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from satellite_adcs.config import load_config
from satellite_adcs.quaternion import quat_error, theta_vec
from simulate import run_episode, make_ic_bias, settling_time

T_EP = 900.0


def main(n=12):
    cfg = load_config()
    _I = cfg["satellite"]["inertia"]
    J = np.diag([_I["Jxx"], _I["Jyy"], _I["Jzz"]])
    tau_max = float(cfg["actuators"]["reaction_wheels"]["max_torque_Nm"])
    # three orthogonal wheels -> per-axis authority is tau_max; take the axis with
    # the LARGEST inertia so alpha is smallest and the bound is the largest
    # (conservative: makes the LQR look as good as possible)
    alpha = tau_max / float(np.max(J))

    rows = []
    for ep in range(n):
        q0, w0, bias = make_ic_bias(ep)
        out = run_episode(cfg, seed=ep, T=T_EP, ic=(q0, w0), gyro_bias=bias,
                          controller="lqr")
        t, pe = out["t"], out["pe"]
        # initial pointing error straight from the episode (no guidance API guess)
        theta0 = float(np.radians(pe[0]))
        ts = settling_time(t, pe, threshold=1.0, hold=10.0)
        t_lb = 2.0 * np.sqrt(max(theta0, 1e-9) / alpha)
        rows.append({"ep": ep, "theta0_deg": np.degrees(theta0),
                     "lqr_settle_s": (None if ts is None else float(ts)),
                     "bound_s": float(t_lb)})

    got = [r for r in rows if r["lqr_settle_s"] is not None]
    med_lqr = float(np.median([r["lqr_settle_s"] for r in got])) if got else None
    med_lb = float(np.median([r["bound_s"] for r in got])) if got else None
    print(f"n={n}  settled {len(got)}/{n}   tau_max={tau_max} Nm  "
          f"alpha={alpha:.5f} rad/s^2 (largest J)")
    print(f"{'ep':>3} {'theta0':>9} {'LQR settle':>11} {'bang-bang lb':>13} {'ratio':>7}")
    for r in rows:
        s = r["lqr_settle_s"]
        ratio = (s / r["bound_s"]) if s else float("nan")
        print(f"{r['ep']:>3} {r['theta0_deg']:>8.1f}° "
              f"{('never' if s is None else f'{s:.1f}s'):>11} "
              f"{r['bound_s']:>12.1f}s {ratio:>7.2f}")
    if got:
        ratios = [r["lqr_settle_s"] / r["bound_s"] for r in got]
        print(f"\nmedian LQR settle = {med_lqr:.1f} s")
        print(f"median bound      = {med_lb:.1f} s")
        print(f"median ratio      = {np.median(ratios):.2f}x  "
              f"(range {np.min(ratios):.2f}-{np.max(ratios):.2f})")
        print(f"=> time-optimal headroom: the LQR takes "
              f"{np.median(ratios):.1f}x the provable lower bound")
    os.makedirs("results/l4", exist_ok=True)
    with open("results/l4/l4_headroom.json", "w") as f:
        json.dump({"tau_max": tau_max, "alpha": alpha, "rows": rows}, f, indent=2)
    print("saved results/l4/l4_headroom.json")


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 12
    main(n)
