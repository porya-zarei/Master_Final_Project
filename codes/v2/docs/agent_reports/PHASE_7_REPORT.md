# Phase 7 Report — RL Environment and Residual Controller

**Phase:** 7 — RL Environment and Residual Controller  
**Status:** `COMPLETE`  
**Date:** 2026-11-21  

---

## 1. Implemented Changes

- `src/adcs/control/residual_rl/policy.py`:
  - `ObservationBuilder`: constructs a documented, bounded 30-dimensional onboard-only observation vector `z` (`rotvec`, `rate_err`, `tau_base`, `prev_tau_rl_gated`, `h_est`, `B_meas`, conservative AMS `directional_margin_xyz`, estimated `g_hat`, `gamma_obs`, `cap_conf`, torque residuals, `att_std_rms`). Zero ground-truth state or fault labels are exposed.
  - `TorchMLPResidualPolicy` & `NumpyMLPWeights`: lightweight `30 -> 64 -> 64 -> 3` Tanh-bounded residual actor with pure-NumPy deterministic inference and SHA-256 checkpointing (`policy_weights.npz` + `policy_meta.json`).
  - `ZeroResidualPolicy`: deterministic zero-action diagnostic policy.
- `src/adcs/training/env.py`: `ADCSResidualEnv(gymnasium.Env)` running the deployed estimator, capability estimator, and deterministic gate in the training loop, with disjoint training-region scenario randomization (`S0`, `S1` wheels 0–1 `eff in [0.40, 0.80]`, `S4` wheel 0 bias/friction, `S7` ±15% inertia, `S6` 8–18 s ST dropout, `S3` moderate momentum) strictly isolated from held-out `test` scenarios, plus explicit `clean_state_training` ablation flag for H3.
- `src/adcs/training/sac.py`: deterministic self-contained PyTorch Soft Actor-Critic (`train_sac`) with twin Q-critics, Polyak target averaging, automatic entropy tuning, near-zero final-layer actor initialization (preserving baseline stability at step 0), JSONL learning-curve logging, and full metadata/hash checkpointing.
- `tests/integration/test_phase7_8_rl_and_ccr.py`: Gymnasium API, replay determinism, bounded action, SAC smoke training, and checkpoint reload tests.

---

## 2. Environment Issue Caught & Fixed

- **PyTorch Inductor cache directory inside sandbox:** Importing `torch.optim.Adam` triggered `torch._dynamo` to call `makedirs` on a host user path (`~/.unsloth/studio`) blocked by sandbox permissions. Resolved cleanly in `src/adcs/training/sac.py` by setting `TORCH_COMPILE_DISABLE=1` and routing `TORCHINDUCTOR_CACHE_DIR` to `tempfile.gettempdir()` prior to `import torch`.

---

## 3. Verification Commands & Outcomes

- `python -m ruff check --no-cache src tests` → `All checks passed!`
- `python -m pytest -v -p no:cacheprovider tests/integration/test_phase7_8_rl_and_ccr.py` → **2 passed, 0 failed**.
- Verified bit-identical env replay for identical seed, finite bounded observations & actions, clean SAC smoke training (300 steps), and bit-identical policy reload without training side effects.

---

## 4. Next Phase

Proceed to **Phase 8 — CCR v2 Integration and Ablations** (verified alongside Gate C3/C4 and integrated controller fallback tests).
