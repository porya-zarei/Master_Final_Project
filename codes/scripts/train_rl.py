"""Phase 2: train a fault-tolerant ADCS policy (PPO or SAC).

Training randomizes reaction-wheel health per episode (fault-randomized policy
= Baseline C). All environment/reward settings are config-driven
(`satellite_adcs/config/rl.yaml`); CLI flags override them.

Run from `codes/`:
    python scripts/train_rl.py --algo ppo --steps 1000000 --n_envs 8 --out results/rl_1m_shape
"""
from __future__ import annotations
import argparse
import os
import sys

import numpy as np
import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from satellite_adcs.config import load_config
from satellite_adcs.environment.adcs_env import ADCSEnv
from stable_baselines3 import PPO, SAC
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecNormalize


def make_env(seed, control_hz, episode_time, fault_mode, health_lo, health_hi):
    return ADCSEnv(fault_mode=fault_mode, health_range=(health_lo, health_hi),
                   control_hz=control_hz, episode_time=episode_time, seed=seed)


class EpisodeRewardLogger(BaseCallback):
    """Track per-environment episode returns (works with 1..N vectorized envs)."""

    def __init__(self, n_envs=1):
        super().__init__()
        self.n_envs = n_envs
        self.ep_rewards = []
        self._cur = np.zeros(n_envs, dtype=float)

    def _on_step(self):
        rew = self.locals.get("rewards")
        if rew is not None:
            self._cur += np.asarray(rew, dtype=float).ravel()[:self.n_envs]
        done = self.locals.get("dones")
        if done is not None:
            for i, d in enumerate(np.asarray(done).ravel()[:self.n_envs]):
                if bool(d):
                    self.ep_rewards.append(float(self._cur[i]))
                    self._cur[i] = 0.0
        return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--algo", default="ppo", choices=["ppo", "sac"])
    p.add_argument("--steps", type=int, default=40000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--n_envs", type=int, default=1,
                   help="parallel simulator processes (use CPU cores, not GPU)")
    p.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    p.add_argument("--out", default="results/rl")
    # --- config-driven env/reward overrides (defaults from rl.yaml) ----------
    p.add_argument("--control_hz", type=float, default=None,
                   help="control rate; default from rl.yaml (matches LQR)")
    p.add_argument("--episode_time", type=float, default=None,
                   help="episode horizon [s]; default from rl.yaml")
    p.add_argument("--fault_mode", default=None,
                   choices=["none", "random_health", "random_discrete", "dead_wheel"])
    p.add_argument("--norm_reward", type=int, default=0, choices=[0, 1],
                   help="VecNormalize reward normalization (0 = keep shaped signal)")
    a = p.parse_args()

    os.makedirs(a.out, exist_ok=True)

    rl = load_config().get("rl", {}) or {}
    control_hz = a.control_hz if a.control_hz is not None else float(rl.get("control_hz", 4.0))
    episode_time = a.episode_time if a.episode_time is not None else float(rl.get("episode_time_s", 900.0))
    fault_mode = a.fault_mode or rl.get("fault_mode", "random_health")
    h_lo, h_hi = rl.get("health_range", [0.5, 1.0])
    print(f"rl cfg: control_hz={control_hz} | episode_time={episode_time}s | "
          f"fault_mode={fault_mode} | health=[{h_lo},{h_hi}] | "
          f"reward_shape={rl.get('reward_shape')} | tol={rl.get('reward_tol_deg')}deg "
          f"(+{rl.get('reward_tol_bonus')}/step) | norm_reward={bool(a.norm_reward)}")

    if a.device == "auto":
        # Measured on this machine (RTX 5060, n_envs=8): PPO+MlpPolicy = ~992 steps/s on
        # CPU vs ~618 steps/s on GPU (cf. SB3 issue DLR-RM#1245). Small MLPs lose more to
        # CPU<->GPU transfer than they gain, so CPU is the faster default here.
        # Use --device cuda for CNN / large networks (e.g. Phase-3 world models).
        device = "cpu"
    else:
        device = a.device
    print(f"device: {device} | torch {torch.__version__} | cuda {torch.version.cuda} "
          f"| n_envs={a.n_envs}")

    mk = lambda i: make_env(a.seed + i, control_hz, episode_time, fault_mode, h_lo, h_hi)
    if a.n_envs > 1:
        raw = SubprocVecEnv([lambda i=i: mk(i) for i in range(a.n_envs)])
    else:
        raw = DummyVecEnv([lambda: mk(0)])
    env = VecNormalize(raw, norm_obs=True, norm_reward=bool(a.norm_reward), clip_obs=10.0)

    if a.algo == "ppo":
        model = PPO("MlpPolicy", env, verbose=1, n_steps=2048, batch_size=256,
                    learning_rate=3e-4, gamma=0.99, ent_coef=1e-3, seed=a.seed,
                    device=device)
    else:
        model = SAC("MlpPolicy", env, verbose=1, learning_rate=3e-4,
                    buffer_size=200_000, batch_size=256, seed=a.seed, device=device)

    cb = EpisodeRewardLogger(n_envs=a.n_envs)
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
        ax.set_title(f"{a.algo.upper()} — fault-randomized ADCS "
                     f"(shape={rl.get('reward_shape')})")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(a.out, f"{a.algo}_learning_curve.png"), dpi=120)
        print("episodes:", len(cb.ep_rewards),
              "| first/last mean:",
              round(float(np.mean(cb.ep_rewards[:5])), 1),
              round(float(np.mean(cb.ep_rewards[-5:])), 1))


if __name__ == "__main__":
    main()
