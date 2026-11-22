"""Milestone C: classical benchmark under the new actuator nonlinearities.

This is the gate before any RL. If actuator nonlinearity does not degrade a
well-tuned LQR, then lever L2 is closed (like L1 and L3 were) and there is nothing
for residual learning to fix. If it does degrade it, THAT is the measured
justification for residual RL -- not an assumption.

Also detects limit cycles / stick-slip: a deadzone or Coulomb friction can leave a
linear controller oscillating around the target. Measured as the standard deviation
of the pointing error over the last 30 % of the episode, and the number of times
the error crosses the tolerance boundary.
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

BASE = {"deadzone_Nm": 1e-4, "friction_viscous_Nms": 2e-6,
        "friction_coulomb_Nm": 2e-4, "rate_limit_Nm_per_s": 0.05,
        "quant_step_Nm": 1e-4}

CONFIGS = {
    "ideal": {},
    "deadzone": {"deadzone_Nm": BASE["deadzone_Nm"]},
    "viscous": {"friction_viscous_Nms": BASE["friction_viscous_Nms"]},
    "coulomb": {"friction_coulomb_Nm": BASE["friction_coulomb_Nm"]},
    "rate_limit": {"rate_limit_Nm_per_s": BASE["rate_limit_Nm_per_s"]},
    "quantised": {"quant_step_Nm": BASE["quant_step_Nm"]},
    "combined": dict(BASE),
}


def metrics(t, pe):
    below = pe < TOL
    idx = np.where(below)[0]
    t_first = float(t[idx[0]]) if len(idx) else None
    tail = pe[t >= (t[-1] - 0.3 * (t[-1] - t[0]))]
    return {
        "t_first": t_first,
        "final": float(pe[-1]),
        "success30": float(100 * np.mean(pe[t >= (t[-1] - 30.0)] < TOL)),
        "pe_std_tail": float(np.std(tail)),
        "pe_max_tail": float(np.max(tail)),
        "entries": int(np.sum(np.diff(below.astype(int)) == 1)),
    }


def main(n=6):
    base_cfg = load_config()
    out = {}
    print(f"Milestone C: LQR under actuator nonlinearities, n={n} paired, T={T_EP}s\n")
    print(f"{'config':>11} {'t_first med':>12} {'final med':>10} {'succ30':>7} "
          f"{'pe_std tail':>12} {'entries':>8}")
    for name, params in CONFIGS.items():
        cfg = copy.deepcopy(base_cfg)
        cfg["actuators"]["reaction_wheels"].update(params)
        rows = []
        for ep in range(n):
            q0, w0, bias = make_ic_bias(ep)
            r = run_episode(cfg, seed=ep, T=T_EP, ic=(q0, w0), gyro_bias=bias,
                            controller="lqr")
            rows.append(metrics(r["t"], r["pe"]))
        tf = [x["t_first"] for x in rows if x["t_first"] is not None]
        mt = float(np.median(tf)) if tf else None
        out[name] = {
            "params": params, "n": n,
            "t_first_median": mt,
            "t_first_all": sorted(round(v, 1) for v in tf),
            "final_median": float(np.median([x["final"] for x in rows])),
            "success30": float(np.mean([x["success30"] for x in rows])),
            "pe_std_tail_median": float(np.median([x["pe_std_tail"] for x in rows])),
            "entries_median": float(np.median([x["entries"] for x in rows])),
        }
        o = out[name]
        print(f"{name:>11} {('never' if mt is None else f'{mt:.1f}s'):>12} "
              f"{o['final_median']:>9.3f}° {o['success30']:>6.1f}% "
              f"{o['pe_std_tail_median']:>12.4f} {o['entries_median']:>8.1f}")

    os.makedirs("results/milestone_c", exist_ok=True)
    with open("results/milestone_c/classical_benchmark.json", "w") as f:
        json.dump({"configs": out}, f, indent=2)
    print("\nfull t_first distributions (medians hide the bimodality):")
    for k, v in out.items():
        print(f"  {k:>11}: {v['t_first_all']}")
    print("saved results/milestone_c/classical_benchmark.json")


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 6
    main(n)
