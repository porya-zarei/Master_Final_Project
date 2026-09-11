"""Evaluate a trained RL policy against the LQR baseline across fault cases.

Run from `codes/`:
    python scripts/eval_rl_vs_lqr.py --model results/rl/ppo_adcs.zip \
        --vecnorm results/rl/vecnormalize.pkl --n 10
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
from satellite_adcs.environment.adcs_env import ADCSEnv
from simulate import run_episode, settling_time
from stable_baselines3 import PPO, SAC
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

CASES = {
    "healthy":    [1.0, 1.0, 1.0],
    "rw1_50pct":  [0.5, 1.0, 1.0],
    "rw1_failed": [0.0, 1.0, 1.0],
}
SETTLE_DEG = 1.0
# A settling hold is a CRITERION, not a property of a controller: both controllers must
# be scored under the SAME holds, and BOTH holds must be reported so the claim is
# hold-robust. Historic defect: the RL side was scored at hold=10 s while the LQR side
# silently inherited simulate.settling_time's default hold=30 s -- a 3x stricter
# criterion for LQR, which flattered the RL success rate.
HOLDS = (10.0, 30.0)


def eval_rl(model, vecnorm, health, n, T=300.0, holds=HOLDS):
    """Roll the policy on the env with a fixed wheel health; return metrics."""
    env = ADCSEnv(fault_mode="none", episode_time=T, seed=0)
    pes = []
    settled = {float(h): [] for h in holds}
    for ep in range(n):
        env.reset(seed=ep)
        env.dyn.set_rw_health(np.array(health, dtype=float))  # force the fault case
        done = False
        pe_series = []
        if vecnorm is not None:
            vecnorm.training = False
        while not done:
            o = env._obs()
            if vecnorm is not None:
                o = np.clip((o - vecnorm.obs_rms.mean) /
                            np.sqrt(vecnorm.obs_rms.var + 1e-8), -10, 10)
            a, _ = model.predict(o, deterministic=True)
            _, _, term, trunc, info = env.step(a)
            pe_series.append(info["pointing_error_deg"])
            done = term or trunc
        pe_series = np.array(pe_series)
        step = env.control_period
        t = np.arange(1, len(pe_series) + 1) * step
        for h in holds:
            st = settling_time(t, pe_series, threshold=SETTLE_DEG, hold=float(h))
            settled[float(h)].append(not np.isinf(st))
        pes.append(pe_series[-1])
    env.close()
    return dict(final_mean=float(np.mean(pes)),
                **{f"success_hold{int(h)}s": 100.0 * float(np.mean(settled[float(h)]))
                   for h in holds})


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="results/rl/ppo_adcs.zip")
    p.add_argument("--vecnorm", default="results/rl/vecnormalize.pkl")
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--out", default="results/rl_eval")
    p.add_argument("--lqr_T", type=float, default=900.0)
    a = p.parse_args()

    os.makedirs(a.out, exist_ok=True)
    cfg = load_config()
    model = (PPO.load(a.model, device="cpu") if "ppo" in a.model.lower()
             else SAC.load(a.model, device="cpu"))
    vecnorm = VecNormalize.load(a.vecnorm, DummyVecEnv([lambda: ADCSEnv()])) \
        if os.path.exists(a.vecnorm) else None

    results = {}
    for name, health in CASES.items():
        rl = eval_rl(model, vecnorm, health, a.n, T=a.lqr_T)
        # LQR on the same fault, scored under the SAME holds as the RL side
        fin = []
        settled = {float(h): [] for h in HOLDS}
        for seed in range(a.n):
            res = run_episode(cfg, seed=seed, T=a.lqr_T, rw_health=health)
            for h in HOLDS:
                st = settling_time(res["t"], res["pe"],
                                   threshold=SETTLE_DEG, hold=float(h))
                settled[float(h)].append(not np.isinf(st))
            fin.append(res["pe"][-1])
        lqr = dict(final_mean=float(np.mean(fin)),
                   **{f"success_hold{int(h)}s": 100.0 * float(np.mean(settled[float(h)]))
                      for h in HOLDS})
        results[name] = {"rl": rl, "lqr": lqr}
        print(f"[{name:11s}] RL: success(h10)={rl['success_hold10s']:5.1f}% "
              f"h30={rl['success_hold30s']:5.1f}% final={rl['final_mean']:5.2f}deg"
              f"   |   LQR: success(h10)={lqr['success_hold10s']:5.1f}% "
              f"h30={lqr['success_hold30s']:5.1f}% final={lqr['final_mean']:5.2f}deg")

    with open(os.path.join(a.out, "rl_vs_lqr.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    names = list(results)
    x = np.arange(len(names)); w = 0.35

    def bars(axi, key, title):
        axi.bar(x - w / 2, [results[nm]["rl"][key] for nm in names], w,
                label="RL", color="tab:purple")
        axi.bar(x + w / 2, [results[nm]["lqr"][key] for nm in names], w,
                label="LQR", color="tab:gray")
        axi.set_title(title); axi.legend(); axi.grid(alpha=0.3)
        axi.set_xticks(x); axi.set_xticklabels(names, rotation=15)

    fig, ax = plt.subplots(1, 3, figsize=(16, 4.2))
    bars(ax[0], "success_hold10s", "success rate [%] (hold 10 s)")
    bars(ax[1], "success_hold30s", "success rate [%] (hold 30 s)")
    bars(ax[2], "final_mean", "final pointing error [deg]")
    fig.suptitle(f"RL vs LQR -- matched criterion (settle < {SETTLE_DEG:g} deg), "
                 f"horizon {a.lqr_T:g} s, n={a.n}")
    fig.tight_layout(); fig.savefig(os.path.join(a.out, "rl_vs_lqr.png"), dpi=120)
    print("saved:", os.path.join(a.out, "rl_vs_lqr.png"))


if __name__ == "__main__":
    main()
