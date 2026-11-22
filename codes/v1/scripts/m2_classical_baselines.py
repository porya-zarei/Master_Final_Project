"""M2: classical baseline comparison on the fault grid.

Arms
  B1  nominal LQR, oracle allocation        controller="lqr",     health_source="true"
  B2  fault-aware LQR, estimated allocation controller="lqr",     health_source="hat"
  B3  gain-scheduled LQR                    controller="scheduled", sched_eps=0.05

All arms run through the SAME loop, allocator, limits and fault injection, with one
initial condition + gyro bias per episode index (paired by construction).

B4 (MPC) is NOT in this run -- see the M2 report.
"""
from __future__ import annotations
import argparse, json, os, sys
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from satellite_adcs.config import load_config
from simulate import make_ic_bias, run_episode

TOL = 1.0
CASES = {
    "coulomb_2e4":      dict(health=[1.0, 1.0, 1.0], coulomb=2e-4),
    "rw1_50pct":        dict(health=[0.5, 1.0, 1.0], coulomb=0.0),
    "rw1_50pct+coul2e4": dict(health=[0.5, 1.0, 1.0], coulomb=2e-4),
}
ARMS = {
    "B1_lqr_oracle":    dict(controller="lqr", health_source="true"),
    "B2_lqr_hat":       dict(controller="lqr", health_source="hat"),
    "B3_sched_hat":     dict(controller="scheduled", health_source="hat", sched_eps=0.05),
}


def metrics(res):
    pe = np.asarray(res["pe"], float)
    return {"final": float(pe[-1]),
            "success30": float(np.mean(pe[-30:] < TOL)),
            "rms": float(np.sqrt(np.mean(pe[-300:] ** 2)))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--T", type=float, default=900.0)
    a = ap.parse_args()

    out = {}
    print(f"M2 classical baselines  n={a.n}  T={a.T}s  tol={TOL} deg\n")
    for case, spec in CASES.items():
        cfg = load_config({"actuators": {"reaction_wheels": {
            "friction_coulomb_Nm": float(spec["coulomb"])}}})
        print(f"=== {case}  (health={spec['health']}, coulomb={spec['coulomb']}) ===")
        out[case] = {}
        for arm, kw in ARMS.items():
            rows = []
            for k in range(a.n):
                q0, w0, b = make_ic_bias(k)
                r = run_episode(cfg, seed=k, T=a.T, ic=(q0, w0), gyro_bias=b,
                                rw_health=spec["health"], **kw)
                rows.append(metrics(r))
            succ = 100 * float(np.mean([x["success30"] for x in rows]))
            fin = float(np.median([x["final"] for x in rows]))
            rms = float(np.median([x["rms"] for x in rows]))
            out[case][arm] = {"success30": succ, "final_median": fin, "rms_median": rms,
                              "finals": [round(x["final"], 3) for x in rows]}
            print(f"  {arm:18s} success={succ:5.1f}%  final={fin:6.3f} deg  rms300={rms:6.3f}")
        print()

    os.makedirs("results/m2", exist_ok=True)
    with open("results/m2/classical_baselines.json", "w") as f:
        json.dump(out, f, indent=2)
    print("saved results/m2/classical_baselines.json")


if __name__ == "__main__":
    main()
