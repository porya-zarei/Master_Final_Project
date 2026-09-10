"""Phase 2: train a fault-tolerant ADCS policy (PPO or SAC).

Training randomizes reaction-wheel health per episode (fault-randomized policy
= Baseline C). Run from `codes/`:

    python scripts/train_rl.py --algo ppo --steps 40000
    python scripts/train_rl.py --algo sac --steps 60000
"""
from __future__ import annotations
import argparse
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from satellite_adcs.environment.adcs_env import ADCSEnv
from stable_baselines3 import PPO, SAC
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize


def make_env(seed=0, fault_mode="random_health", health_lo=0.5, health_hi=1.0):
    return ADCSEnv(fault_mode=fault_mode, health_range=(health_lo, health_hi),
                   control_hz=2.0, episode_time=300.0, seed=seed)


class EpisodeRewardLogger(BaseCallback):
    def __init__(self):
        super().__init__()
        self.ep_rewards = []
        self._cur = 0.0

    def _on_step(self):
        rew = self.locals.get("rewards")
        if rew is not None:
            self._cur += float(np.sum(rew))
        done = self.locals.get("dones")
        if done is not None and bool(np.any(done)):
            self.ep_rewards.append(self._cur)
            self._cur = 0.0
        return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--algo", default="ppo", choices=["ppo", "sac"])
    p.add_argument("--steps", type=int, default=40000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", default="results/rl")
    a = p.parse_args()

    os.makedirs(a.out, exist_ok=True)
    raw = DummyVecEnv([lambda: make_env(a.seed)])
    env = VecNormalize(raw, norm_obs=True, norm_reward=True, clip_obs=10.0)

    if a.algo == "ppo":
        model = PPO("MlpPolicy", env, verbose=1, n_steps=2048, batch_size=256,
                    learning_rate=3e-4, gamma=0.99, ent_coef=1e-3, seed=a.seed)
    else:
        model = SAC("MlpPolicy", env, verbose=1, learning_rate=3e-4,
                    buffer_size=200_000, batch_size=256, seed=a.seed)

    cb = EpisodeRewardLogger()
    model.learn(total_timesteps=a.steps, callback=cb)
    model_path = os.path.join(a.out, f"{a.algo}_adcs")
    model.save(model_path)
    env.save(os.path.join(a.out, "vecnormalize.pkl"))
    print("saved model:", model_path + ".zip")

    if cb.ep_rewards:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(cb.ep_rewards, marker=".", ms=3)
        ax.set_xlabel("episode")
        ax.set_ylabel("episode reward")
        ax.set_title(f"{a.algo.upper()} — fault-randomized ADCS learning curve")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(a.out, f"{a.algo}_learning_curve.png"), dpi=120)
        print("episodes:", len(cb.ep_rewards),
              "| first/last mean:",
              round(float(np.mean(cb.ep_rewards[:5])), 1),
              round(float(np.mean(cb.ep_rewards[-5:])), 1))


if __name__ == "__main__":
    main()
