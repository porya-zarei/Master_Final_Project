"""Diagnose the trained RL policy: why does it stall above the pointing threshold?

Rolls the policy out on the healthy satellite for 900 s and logs
  - pointing error
  - |action| (control effort)
  - wheel speed (momentum accumulation / saturation)
  - reward components (theta^2, 0.1*omega^2, 1e-2*u^2)

Run from `codes/`:
    python scripts/diag_rl.py --model results/rl_1m/ppo_adcs.zip \
        --vecnorm results/rl_1m/vecnormalize.pkl --n 3
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
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="results/rl_1m/ppo_adcs.zip")
    p.add_argument("--vecnorm", default="results/rl_1m/vecnormalize.pkl")
    p.add_argument("--n", type=int, default=3)
    p.add_argument("--T", type=float, default=900.0)
    p.add_argument("--out", default="results/rl_diag")
    a = p.parse_args()

    os.makedirs(a.out, exist_ok=True)
    model = PPO.load(a.model, device="cpu")
    vn = VecNormalize.load(a.vecnorm, DummyVecEnv([lambda: ADCSEnv()]))
    env = ADCSEnv(fault_mode="none", control_hz=2.0, episode_time=a.T, seed=0)

    fig, ax = plt.subplots(4, 1, figsize=(10, 11), sharex=True)
    for ep in range(a.n):
        env.reset(seed=ep)
        env.dyn.set_rw_health(np.ones(3))
        pe, amag, wspd, t2, o2, u2 = [], [], [], [], [], []
        done = False
        while not done:
            o = env._obs()
            on = np.clip((o - vn.obs_rms.mean) / np.sqrt(vn.obs_rms.var + 1e-8), -10, 10)
            act, _ = model.predict(on, deterministic=True)
            _, _, term, trunc, info = env.step(act)
            pe.append(info["pointing_error_deg"])
            amag.append(float(np.linalg.norm(act)))
            wspd.append(float(np.linalg.norm(env.dyn.omega_w)))
            th = info["theta_rad"]
            t2.append(th * th)
            u2.append(1e-2 * float(np.asarray(act) @ np.asarray(act)))
            done = term or trunc
        t = np.arange(1, len(pe) + 1) * 0.5
        pe = np.array(pe); wspd = np.array(wspd)
        print(f"ep{ep}: final_pe={pe[-1]:6.2f} deg | settled(last 100 steps): "
              f"pe={np.mean(pe[-100:]):5.2f} deg, |a|={np.mean(amag[-100:]):.3f}, "
              f"|w|={np.mean(wspd[-100:]):6.1f}/{env.rw_max_speed:.0f} rad/s "
              f"({100*np.mean(wspd[-100:])/env.rw_max_speed:4.1f}% of max) | "
              f"theta^2={np.mean(t2[-100:]):.5f}, u^2term={np.mean(u2[-100:]):.5f}")
        ax[0].plot(t, pe, label=f"ep{ep}")
        ax[1].plot(t, amag)
        ax[2].plot(t, wspd)
        ax[3].plot(t, np.array(t2), label="theta^2")
        ax[3].plot(t, np.array(u2), label="1e-2*u^2")
    env.close()

    ax[0].axhline(1.0, color="r", ls="--", lw=1, label="1 deg target")
    ax[0].set_ylabel("pointing error [deg]"); ax[0].legend(); ax[0].set_yscale("log")
    ax[1].set_ylabel("|action| (-1..1)")
    ax[2].axhline(env.rw_max_speed, color="r", ls="--", lw=1, label="wheel max")
    ax[2].set_ylabel("|wheel speed| [rad/s]"); ax[2].legend()
    ax[3].set_ylabel("reward terms"); ax[3].set_xlabel("time [s]"); ax[3].legend()
    for x in ax:
        x.grid(alpha=0.3)
    fig.suptitle("RL policy diagnostic (healthy satellite, 900 s)")
    fig.tight_layout()
    fig.savefig(os.path.join(a.out, "rl_diag.png"), dpi=120)
    print("saved:", os.path.join(a.out, "rl_diag.png"))


if __name__ == "__main__":
    main()
