# rl/ — Phase 1: baseline fault-tolerant RL

Trains a PPO (later SAC) agent on the `simulation` environment with randomized
fault injection during training. This is **Baseline C** in the thesis's 3-way
comparison (fault-randomized policy).

## Files
- `train_ppo.py` — SB3 PPO, `MlpPolicy`, 200k timesteps (adjust as needed).

## Run
```bash
cd codes && source venv/Scripts/activate
python -m rl.train_ppo
```

## Notes
- Seed and hyperparameters are placeholders; tune after the manual rollout works.
- Policy output is an `AttitudeSetpoint` command (Basilisk steering law computes
  torques). The proposal's raw-torque action space is a later refinement.
