"""Milestone D2 evaluation: does residual SAC fix what the LQR cannot?

Two experiments, in order, because the first is a GATE:

  1. NOMINAL (ideal actuator). The hybrid must not degrade the LQR. If it does, the
     architecture is invalid and the friction result would be meaningless.
  2. FRICTION (coulomb = 2e-4), where the LQR scored 0/16 at the 1 deg requirement.

The LQR arm is produced by THIS harness (residual action = 0), which is provably
identical to the nominal controller (test: state match < 1e-9), so the comparison is
paired by construction: same ICs, same gyro-bias draws, same plant, same allocator.
"""
from __future__ import annotations
import sys, os, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from satellite_adcs.environment.adcs_env import ADCSEnv
from satellite_adcs.environment.residual_env import ResidualADCSEnv
from simulate import make_ic_bias

T_EP = 900.0
TOL = 1.0
SEEDS = [0, 1, 2]


def _env(coulomb, alpha, seed=0):
    ov = {"actuators": {"reaction_wheels": {"friction_coulomb_Nm": float(coulomb)}}}
    base = ADCSEnv(fault_mode="none", episode_time=T_EP, control_hz=5.0,
                   seed=seed, overrides=ov)
    return ResidualADCSEnv(base, alpha=alpha)


def _episode(kind, policy_path, coulomb, alpha, coin):
    env = _env(coulomb, alpha, seed=coin)
    q0, w0, bias = make_ic_bias(coin)
    obs, _ = env.reset(seed=coin, options={"q": q0, "omega": w0, "gyro_bias": bias})
    if kind == "policy":
        from stable_baselines3 import SAC
        model = SAC.load(policy_path, device="cpu")
    else:
        model = None
    pes, done = [], False
    while not done:
        act = np.zeros(3) if model is None else model.predict(obs, deterministic=True)[0]
        obs, r, term, trunc, info = env.step(act)
        pes.append(env.unwrapped.pointing_error_deg())
        done = term or trunc
    pe = np.asarray(pes)
    return {"final": float(pe[-1]),
            "success30": float(np.mean(pe[-30:] < TOL)),
            "max": float(np.max(pe))}


def main(n=12):
    out = {}
    for cond, coulomb in (("ideal", 0.0), ("coulomb_2e4", 2e-4)):
        print(f"\n=== {cond} (coulomb={coulomb}) ===")
        lqr = [_episode("lqr", None, coulomb, 0.2, s) for s in range(n)]
        l_fin = float(np.median([x["final"] for x in lqr]))
        l_succ = 100 * float(np.mean([x["success30"] for x in lqr]))
        print(f"  LQR (a=0)      success={l_succ:5.1f}%  final med={l_fin:6.3f}deg")
        out[cond] = {"lqr": {"success30": l_succ, "final_median": l_fin,
                             "finals": [round(x["final"], 3) for x in lqr]}}
        for s in SEEDS:
            path = f"results/residual_d4_s{s}/policy.zip"
            if not os.path.exists(path):
                print(f"  seed {s}: MISSING {path}"); continue
            rows = [_episode("policy", path, coulomb, 0.2, k) for k in range(n)]
            fin = float(np.median([x["final"] for x in rows]))
            succ = 100 * float(np.mean([x["success30"] for x in rows]))
            out[cond][f"seed{s}"] = {"success30": succ, "final_median": fin,
                                     "finals": [round(x["final"], 3) for x in rows]}
            print(f"  seed {s}         success={succ:5.1f}%  final med={fin:6.3f}deg")
    os.makedirs("results/d2_eval", exist_ok=True)
    with open("results/d2_eval/residual_vs_lqr.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\nsaved results/d2_eval/residual_vs_lqr.json")


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 12
    main(n)
