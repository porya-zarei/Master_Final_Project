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


def eval_rl(model, vecnorm, health, n, T=300.0):
    """Roll the policy on the env with a fixed wheel health; return metrics."""
    env = ADCSEnv(fault_mode="none", episode_time=T, seed=0)
    pes, settled = [], []
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
        st = settling_time(t, pe_series, threshold=SETTLE_DEG, hold=10.0)
        pes.append(pe_series[-1])
        settled.append(not np.isinf(st))
    env.close()
    return dict(success=100.0 * np.mean(settled), final_mean=float(np.mean(pes)))


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
        # LQR on the same fault
        rms, fin, ts = [], [], []
        ok = 0
        for seed in range(a.n):
            res = run_episode(cfg, seed=seed, T=a.lqr_T, rw_health=health)
            st = settling_time(res["t"], res["pe"])
            fin.append(res["pe"][-1]); ok += int(not np.isinf(st))
        lqr = dict(success=100.0 * ok / a.n, final_mean=float(np.mean(fin)))
        results[name] = {"rl": rl, "lqr": lqr}
        print(f"[{name:11s}] RL: success={rl['success']:5.1f}% final={rl['final_mean']:5.2f}deg"
              f"   |   LQR: success={lqr['success']:5.1f}% final={lqr['final_mean']:5.2f}deg")

    with open(os.path.join(a.out, "rl_vs_lqr.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    names = list(results)
    x = np.arange(len(names)); w = 0.35
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    ax[0].bar(x - w / 2, [results[n]["rl"]["success"] for n in names], w, label="RL", color="tab:purple")
    ax[0].bar(x + w / 2, [results[n]["lqr"]["success"] for n in names], w, label="LQR", color="tab:gray")
    ax[0].set_title("success rate [%]"); ax[0].legend()
    ax[1].bar(x - w / 2, [results[n]["rl"]["final_mean"] for n in names], w, label="RL", color="tab:purple")
    ax[1].bar(x + w / 2, [results[n]["lqr"]["final_mean"] for n in names], w, label="LQR", color="tab:gray")
    ax[1].set_title("final pointing error [deg]"); ax[1].legend()
    for axi in ax:
        axi.set_xticks(x); axi.set_xticklabels(names, rotation=15); axi.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(a.out, "rl_vs_lqr.png"), dpi=120)
    print("saved:", os.path.join(a.out, "rl_vs_lqr.png"))


if __name__ == "__main__":
    main()
