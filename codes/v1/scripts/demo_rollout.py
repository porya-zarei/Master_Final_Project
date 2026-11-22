"""Run a longer Phase-1 rollout and visualize the simulation.

Shows the 9-dim state (MRP sigma, body rate omega, wheel speeds), the reward,
and when a fault triggers -- demonstrating the environment behaves as designed.

Run from `codes/`:
    python scripts/demo_rollout.py [episodes] [seconds_per_episode]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from simulation.envs.adcs_env import make_env, FaultToleranceWrapper

LABELS = ["sigma_1", "sigma_2", "sigma_3", "omega_1", "omega_2", "omega_3",
          "wheel_1", "wheel_2", "wheel_3"]


def run_episode(seed: int, seconds: int):
    env = FaultToleranceWrapper(make_env(), seed=seed)
    obs, info = env.reset(seed=seed)
    n = int(seconds)  # sim_rate=1.0 -> one step per second
    sig = np.full((n + 1, 9), np.nan)
    rew = np.full(n + 1, np.nan)
    fault_t = np.zeros(n + 1)
    sig[0] = obs
    t_obs = np.arange(n + 1)
    for i in range(n):
        obs, r, term, trunc, info = env.step(env.action_space.sample())
        sig[i + 1] = obs
        rew[i + 1] = r
        fault_t[i + 1] = 1.0 if info["fault_active"] else 0.0
        if term or trunc:
            sig = sig[: i + 2]
            rew = rew[: i + 2]
            fault_t = fault_t[: i + 2]
            t_obs = t_obs[: i + 2]
            break
    fk = info["fault_kind"]
    env.close()
    return t_obs, sig, rew, fault_t, fk


def main(episodes: int = 2, seconds: int = 250):
    fig, axes = plt.subplots(4, 1, figsize=(11, 11), sharex=True)

    for ep in range(episodes):
        t, sig, rew, ft, fk = run_episode(seed=ep, seconds=seconds)

        # Fault band (filled where active)
        for ax in axes:
            ax.fill_between(t, -1, 1, where=ft > 0, color="red", alpha=0.12,
                            label="fault active" if ep == 0 else None)

        ax = axes[0]
        for j in range(3):
            ax.plot(t, sig[:, j], label=LABELS[j])
        ax.set_ylabel("MRP  σ")
        ax.legend(loc="upper right", fontsize=8)

        ax = axes[1]
        for j in range(3, 6):
            ax.plot(t, sig[:, j], label=LABELS[j])
        ax.set_ylabel("body rate ω [rad/s]")
        ax.legend(loc="upper right", fontsize=8)

        ax = axes[2]
        for j in range(6, 9):
            ax.plot(t, sig[:, j], label=LABELS[j])
        ax.set_ylabel("wheel speed [rad/s]")
        ax.legend(loc="upper right", fontsize=8)

        ax = axes[3]
        ax.plot(t, rew, label=f"ep{ep} reward", color="tab:blue")
        ax.set_ylabel("reward")
        ax.set_xlabel("simulation time [s]")
        ax.legend(loc="upper right", fontsize=8)

        print(f"episode {ep}: fault_kind={fk!r}  "
              f"fault_triggered={bool(np.any(ft>0))}  steps={len(t)-1}")

    axes[0].set_title("Phase 1 simulation — random-attitude rollout "
                      "(red band = fault active)")
    fig.tight_layout()
    out = Path("results") / "first_simulation.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=130)
    print("saved:", out.resolve())


if __name__ == "__main__":
    ep = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    sec = int(sys.argv[2]) if len(sys.argv) > 2 else 250
    main(ep, sec)
