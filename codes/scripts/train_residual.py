"""Milestone D2: residual SAC on the Coulomb-friction plant.

    tau_des = tau_LQR + alpha * delta_tau_RL

The LQR does the work; the policy learns only the correction. This is trained on the
plant where the LQR scored 0/16 successes at the 1 deg requirement (Milestone C2),
because a structured, systematic offset (the stick-slip deadband) is exactly the
error a residual can cancel.

Usage:
    python scripts/train_residual.py --steps 200000 --algo sac --seed 0 \
        --coulomb 2e-4 --alpha 0.2 --out results/residual_sac
"""
from __future__ import annotations
import sys, os, argparse, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from satellite_adcs.environment.adcs_env import ADCSEnv
from satellite_adcs.environment.residual_env import ResidualADCSEnv
from satellite_adcs.config import load_config


def make_env(seed, coulomb, alpha, episode_time, control_hz,
             reward_shape="tol_norm"):
    overrides = {"actuators": {"reaction_wheels": {
        "friction_coulomb_Nm": float(coulomb)}},
        "rl": {"reward_shape": reward_shape}}
    base = ADCSEnv(fault_mode="none", episode_time=episode_time,
                   control_hz=control_hz, seed=seed, overrides=overrides)
    return ResidualADCSEnv(base, alpha=alpha)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--steps", type=int, default=200000)
    p.add_argument("--algo", default="sac", choices=["sac", "ppo"])
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--coulomb", type=float, default=2e-4)
    p.add_argument("--alpha", type=float, default=0.2)
    p.add_argument("--reward_shape", default="tol_norm",
                   choices=["quad", "log", "bonus", "tol_norm"])
    p.add_argument("--episode_time", type=float, default=900.0)
    p.add_argument("--control_hz", type=float, default=5.0)
    p.add_argument("--device", default="cpu")
    p.add_argument("--out", default="results/residual_sac")
    a = p.parse_args()

    os.makedirs(a.out, exist_ok=True)
    env = make_env(a.seed, a.coulomb, a.alpha, a.episode_time, a.control_hz,
                   reward_shape=a.reward_shape)

    cfg = {"seed": a.seed, "coulomb": a.coulomb, "alpha": a.alpha,
           "steps": a.steps, "algo": a.algo, "control_hz": a.control_hz,
           "episode_time": a.episode_time}
    with open(os.path.join(a.out, "config.json"), "w") as f:
        json.dump(cfg, f, indent=2)

    if a.algo == "sac":
        from stable_baselines3 import SAC
        model = SAC("MlpPolicy", env, verbose=1, seed=a.seed, device=a.device,
                    learning_rate=3e-4, buffer_size=200000, learning_starts=2000,
                    batch_size=256, tau=0.005, gamma=0.99,
                    policy_kwargs=dict(net_arch=[128, 128]))
    else:
        from stable_baselines3 import PPO
        model = PPO("MlpPolicy", env, verbose=1, seed=a.seed, device=a.device,
                    n_steps=2048, batch_size=256, learning_rate=3e-4,
                    policy_kwargs=dict(net_arch=[128, 128]))

    print(f"[residual] algo={a.algo} alpha={a.alpha} coulomb={a.coulomb} "
          f"obs={env.observation_space.shape} act={env.action_space.shape}")
    model.learn(total_timesteps=a.steps, log_interval=10)
    path = os.path.join(a.out, "policy.zip")
    model.save(path)
    print(f"saved {path}")


if __name__ == "__main__":
    main()
