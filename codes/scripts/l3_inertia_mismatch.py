"""L3/M4 gate: how much does the LQR degrade when its inertia model is wrong?

The plant uses J*(1+delta) on every principal axis; the controller always uses the
NOMINAL J. That is the realistic case -- an onboard model does not know the true
inertia -- and it is the regime where a policy trained across the distribution has
a structural advantage over a fixed-gain controller.

If the LQR barely degrades, L3 is closed and there is nothing for RL to win here.
If it degrades sharply, that is the opening.
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
FACTORS = [0.8, 0.9, 1.0, 1.1, 1.2]


def _t_first(t, pe):
    idx = np.where(pe < TOL)[0]
    return float(t[idx[0]]) if len(idx) else None


def main(n=6):
    cfg = load_config()
    out = {}
    print(f"n={n} per factor, T={T_EP}s, controller always uses NOMINAL J\n")
    print(f"{'J scale':>8} {'t_first med':>12} {'final med':>10} {'success h30':>12}")
    for f in FACTORS:
        plant = copy.deepcopy(cfg)
        I = plant["satellite"]["inertia"]
        for k in ("Jxx", "Jyy", "Jzz"):
            I[k] = cfg["satellite"]["inertia"][k] * f
        tf, fin, succ = [], [], []
        for ep in range(n):
            q0, w0, bias = make_ic_bias(ep)
            r = run_episode(cfg, seed=ep, T=T_EP, ic=(q0, w0), gyro_bias=bias,
                            controller="lqr",
                            plant_cfg=(plant if f != 1.0 else None))
            t, pe = r["t"], r["pe"]
            v = _t_first(t, pe)
            if v is not None:
                tf.append(v)
            fin.append(float(pe[-1]))
            m = t >= (t[-1] - 30.0)
            succ.append(float(np.mean(pe[m] < TOL)))
        mt = float(np.median(tf)) if tf else None
        out[str(f)] = {"t_first_median": mt, "t_first_all": tf,
                       "final_median": float(np.median(fin)),
                       "success30": float(100 * np.mean(succ)), "n": n}
        print(f"{f:>8.2f} {('never' if mt is None else f'{mt:.1f}s'):>12} "
              f"{np.median(fin):>9.2f}° {100*np.mean(succ):>11.1f}%")
    os.makedirs("results/l3", exist_ok=True)
    with open("results/l3/inertia_mismatch.json", "w") as fh:
        json.dump({"factors": FACTORS, "results": out}, fh, indent=2)
    base = out["1.0"]["t_first_median"]
    if base:
        print("\ndegradation vs nominal (t_first):")
        for k, v in out.items():
            if v["t_first_median"]:
                print(f"  J x{k:>4}: {v['t_first_median']/base:>.2f}x "
                      f"{'slower' if v['t_first_median']/base > 1 else 'faster'}")
    print("saved results/l3/inertia_mismatch.json")


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 6
    main(n)
