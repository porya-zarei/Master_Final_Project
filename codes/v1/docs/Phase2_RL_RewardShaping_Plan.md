# Phase 2 — RL Reward Shaping Plan
**Goal:** make the PPO policy match LQR's fine-pointing precision (< 1°) instead of stalling at ~4°.

---

## 1. Observed problem (measured, not guessed)

`eval_rl_vs_lqr.py`, n=6, T=900 s, 1 M-step PPO model (`results/rl_1m/`):

| case | RL success | RL final pe | LQR success | LQR final pe |
|---|---|---|---|---|
| healthy   | 0% | 4.07° | 83.3% | 0.68° |
| rw1_50pct | 0% | 4.17° | 83.3% | 0.68° |
| rw1_failed| 0% | 68.0° |  0.0% | 40.8° |

Also: 1 M beats the 300 k model (11° → 4°), and the learning curve is **flat after episode ~750** → *more steps will not help*.

## 2. Diagnosis (`scripts/diag_rl.py`, healthy, 900 s)

Settled phase (last 100 control steps):

- pointing error ≈ **4°**
- **|action| ≈ 0.007** (out of ±1) → the policy commands ~zero torque
- wheel speed 6–21 % of max → **not saturated**, no authority problem
- θ² ≈ 0.006, control cost ≈ 0

**Interpretation:** the policy learned *"slew to ~4° then coast"*. It is a **reward-induced local optimum**, not a physical limit (LQR reaches 0.68° with the same plant/allocator).

Contributing factors:
1. **Reward dominated by the acquisition transient** — the huge initial error (~90°) sets the return scale; the fine-pointing regime contributes almost nothing.
2. **`VecNormalize(norm_reward=True)`** further flattens the late-stage signal (normalising by a return std set by the transient) → ~zero gradient pressure at θ ≈ 4°.
3. **Control penalty `1e-2·|u|²`** discourages the sustained torque that fine pointing requires.
4. **Training horizon 300 s ≠ evaluation 900 s** → the settled regime is under-trained (distribution shift).

## 3. Proposed changes

### 3.1 Reward shaping (core fix)
Add an explicit **precision incentive** so the gradient does not vanish near the target. Options:

- **(A) Tolerance bonus** (recommended, simplest):
  `r = -(θ² + 0.1·ω² + 1e-2·|u|²) + b·1[|θ| < θ_tol]`, with `θ_tol = 1°`, `b ≈ 0.5–2.0` per step.
  → directly rewards *being in spec*, aligns reward with the success metric.
- **(B) Log-shaped error** (smooth alternative):
  `r = -log(1 + (θ/θ_tol)²) - 0.1·ω² - 1e-2·|u|²`
  → steep gradient near zero, flat far away (helps both phases).
- **(C) Precision re-weighting**: raise the θ weight and/or decay the control penalty as `‖θ‖ → 0`.

**Recommendation:** implement (A) with a knob (`reward_tol_deg`, `reward_tol_bonus`) and optionally (B) behind a flag, so we can compare shapes in the thesis.

### 3.2 Horizon match
Train with `episode_time = 900 s` (or evaluate at the training horizon). Preferred: **train at 900 s**.

### 3.3 Normalization
Keep `VecNormalize` for obs, but set `norm_reward=False` (or clip) so the shaped precision signal survives.

## 4. Config-driven (per project rule)
All new knobs go in the YAML `rl:` block, not hard-coded:
```yaml
rl:
  reward_tol_deg: 1.0
  reward_tol_bonus: 1.0
  reward_shape: "bonus"   # bonus | log | quad
```

## 5. Validation plan
1. Retrain 1 M steps with shaping (~6 min at 2638 steps/s, 8 envs).
2. Re-run `eval_rl_vs_lqr.py` (n=8) on healthy / rw1_50pct / rw1_failed.
3. Re-run `diag_rl.py` → expect settled `|a| > 0.05` and pe < 1°.
4. Report: success rate, final pe, settling time, RMS — all three faults, RL vs LQR.
5. Only if still short: SAC and/or residual-RL-on-LQR.

## 6. Budget
1 M steps ≈ 6 min (no GPU — measured CPU win). 2 M ≈ 12 min if needed.

## 7. Implemented (this session)

**Files changed**
- **`satellite_adcs/config/rl.yaml`** *(new)* — config-driven RL block: `control_hz`, `episode_time_s`, `tau_scale`, `fault_mode`, `health_range`, `reward_shape`, `reward_theta_weight`, `reward_rate_weight`, `reward_control_weight`, `reward_tol_deg`, `reward_tol_bonus`.
- **`config/__init__.py`** — loads `rl.yaml` into `cfg["rl"]`.
- **`adcs_env.py`** — all env/reward knobs now come from `cfg["rl"]`; new `_reward()` with `quad | log | bonus` shapes and a `reward_components` info dict. **Control period is now `n_sub*dt`** (exact) instead of `1/control_hz`, so the simulated horizon equals `episode_time`.
- **`train_rl.py`** — env defaults from `rl.yaml`; new flags `--control_hz`, `--episode_time`, `--fault_mode`, `--norm_reward` (**default 0**, so the shaped precision signal is not normalized away).
- **`eval_rl_vs_lqr.py`** — time axis uses `env.control_period` (was hard-coded 0.5 s); env rate taken from config.
- **`simulate.py`** — **time-axis bug fixed**: it advanced `t` by `1/control_hz` (0.25 s) while stepping only `round(0.25/0.1)=2` substeps (0.2 s), so a "900 s" LQR run simulated 720 s and settling times were inflated ~25 %. Now `ctrl_period = nctrl*dt`.
- **`simulation.yaml`** — `control_hz: 4` → `5.0` (the *true* effective rate; `design_lqr` is continuous-time so the gain is unaffected).

**Verified before training**
- `ADCSEnv()` → rate 5.00 Hz, period 0.20 s, 4500 steps = exactly 900 s ✅
- LQR `control_period` = 0.20 s → **same rate as the RL env** ✅
- Reward components log correctly; `in_tol` flag works ✅
- 8192-step PPO smoke run on 2 envs completes and saves ✅

**⚠️ Consequence:** the M1 / Phase-1B numbers in `report-state-1.md` were produced with the old inflated time axis, so their **settling times are ~25 % too large** (pointing errors are unaffected). Those need regenerating.

---
*Status: implemented and smoke-tested. Awaiting training run by the user.*

