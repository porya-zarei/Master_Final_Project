"""Train a fault-tolerant attitude controller with PPO.

Run only after the manual smoke test passes once on your machine (i.e. after
the first-run Basilisk support-data download has succeeded).

Run from the `codes/` root:
    source venv/Scripts/activate
    python -m rl.train_ppo
"""

import sys
from pathlib import Path

# Make `simulation` importable regardless of cwd when run as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stable_baselines3 import PPO

from simulation.envs.adcs_env import make_env, FaultToleranceWrapper

env = FaultToleranceWrapper(make_env(), seed=0)

# Uncomment once a manual rollout works -- this runs Gymnasium's API-compliance
# checks and catches shape/dtype mismatches early instead of failing deep inside
# PPO's rollout collection.
# from stable_baselines3.common.env_checker import check_env
# check_env(env)

model = PPO(
    "MlpPolicy",
    env,
    verbose=1,
    n_steps=2048,
    batch_size=64,
    learning_rate=3e-4,
    tensorboard_log="./tb_logs",
)

model.learn(total_timesteps=200_000)
model.save("adcs_fault_tolerant_ppo")

print("Done. Load later with: PPO.load('adcs_fault_tolerant_ppo')")
