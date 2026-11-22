"""Milestone C2: does the LQR's Coulomb-friction failure survive a larger n?

Milestone C found 0% success at friction_coulomb_Nm = 2e-4 with n=6. That is the
central justification for residual RL, so it must not rest on one assumed magnitude
and a small sample. This sweeps the magnitude at n=16 paired episodes and reports
the full distribution (never a bare median).

If the LQR only fails at exactly 2e-4, the justification is fragile and must be
stated that way. If it degrades monotonically with the magnitude, the claim is
robust and can be made with the magnitude attached.
"""
from __future__ import annotations
import sys, os, json, copy
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from satellite_adcs.config import load_config
from simulate import run_episode, make_ic_bias

T_EP = 900.0
TOL = 1.0
MAGS = [0.0, 1e-4, 2e-4, 3e-4]


def metrics(t, pe):
    below = pe < TOL
    idx = np.where(below)[0]
    tail = pe[t >= (t[-1] - 30.0)]
    return {
        "t_first": float(t[idx[0]]) if len(idx) else None,
        "ever_entered": bool(len(idx)),
        "final": float(pe[-1]),
        "success30": float(np.mean(tail < TOL)),
    }


def main(n=16):
    base = load_config()
    out = {}
    print(f"Milestone C2: LQR vs Coulomb-friction magnitude, n={n} paired\n")
    print(f"{'coulomb_Nm':>11} {'success30':>10} {'final med':>10} "
          f"{'ever entered':>13} {'t_first med':>12}")
    for m in MAGS:
        cfg = copy.deepcopy(base)
        cfg["actuators"]["reaction_wheels"]["friction_coulomb_Nm"] = m
        rows = []
        for ep in range(n):
            q0, w0, bias = make_ic_bias(ep)
            r = run_episode(cfg, seed=ep, T=T_EP, ic=(q0, w0), gyro_bias=bias,
                            controller="lqr")
            rows.append(metrics(r["t"], r["pe"]))
        succ = 100 * float(np.mean([x["success30"] for x in rows]))
        fin = float(np.median([x["final"] for x in rows]))
        ever = 100 * float(np.mean([x["ever_entered"] for x in rows]))
        tf = sorted(x["t_first"] for x in rows if x["t_first"] is not None)
        med = float(np.median(tf)) if tf else None
        out[str(m)] = {
            "n": n, "success30": succ, "final_median": fin,
            "pct_ever_entered": ever, "t_first_median": med,
            "t_first_all": [round(v, 1) for v in tf],
            "finals": [round(x["final"], 3) for x in rows],
        }
        print(f"{m:>11.1e} {succ:>9.1f}% {fin:>9.3f}° {ever:>12.1f}% "
              f"{('never' if med is None else f'{med:.1f}s'):>12}")
    os.makedirs("results/milestone_c2", exist_ok=True)
    with open("results/milestone_c2/coulomb_sweep.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\nfinal-error distributions:")
    for k, v in out.items():
        print(f"  {k:>8}: {v['finals']}")
    print("saved results/milestone_c2/coulomb_sweep.json")


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 16
    main(n)
