"""Phase-1 smoke test: run a short random rollout on the fault-tolerant env.

Confirms the environment + fault injection run end-to-end (and that Basilisk's
first-run support-data download succeeds) BEFORE spending time on PPO training.

Run from the `codes/` root:
    source venv/Scripts/activate
    python -m scripts.manual_test          # or: python scripts/manual_test.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulation.envs.adcs_env import make_env, FaultToleranceWrapper


def main(seed: int = 0, steps: int = 20) -> None:
    env = FaultToleranceWrapper(make_env(), seed=seed)
    obs, info = env.reset(seed=seed)
    print(f"obs shape: {obs.shape}  obs[:6]: {obs[:6]}  info: {info}")

    for i in range(steps):
        obs, reward, terminated, truncated, info = env.step(env.action_space.sample())
        print(
            f"step {i:2d}: reward={reward:8.4f} "
            f"fault_kind={info['fault_kind']:<10} fault_active={info['fault_active']}"
        )
        if terminated or truncated:
            print("episode ended early")
            break
    env.close()
    print("Smoke test OK.")


if __name__ == "__main__":
    main()
