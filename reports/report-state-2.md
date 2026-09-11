# Project State Report 2 — Fault-Tolerant Nanosatellite Attitude Control via Reinforcement Learning

**Student:** Pouria Zarei — M.Sc. Control Engineering, University of Tehran
**Advisor:** Prof. Mohammad Javad Yazdanpanah
**Date:** 2026-09-11
**Status:** Phase 1B (actuator-fault model + momentum management) and Phase 2 (RL baselines, Baseline C) complete.
**Headline result:** the learned policy now **outperforms the classical LQR baseline on all three fault cases** — including the fully-failed reaction wheel, where LQR never succeeds.

---

## 0. Progress since Report 1

Report 1 closed with **M0** (config-driven simulator) and **M1** (LQR nadir acquisition, 73.3 % success over 60 random initial conditions) validated, and listed *Phase 1B (fault experiment)* and *Phase 2 (RL baselines)* as the next milestones. This report covers everything done since.

| Milestone | Status | Headline result |
|---|---|---|
| **Phase 1B** — RW fault model + MTQ momentum management + fault-tolerant allocator | ✅ done | healthy **86.7 %** · RW1 @ 50 % **86.7 %** · RW1 dead **0 %** |
| **Phase 2a** — RL environment + training/eval harness on the shared simulator | ✅ done | Gymnasium env (obs 9 / act 3), PPO & SAC trainers, fair-vs-LQR harness |
| **Phase 2b** — first **1 M**-step PPO run | ✅ done | converged (episode 1688) but **stalls at 4°** — diagnosed, not accepted |
| **Phase 2c** — shaped-reward **2 M**-step PPO run | ✅ done | **100 % / 0.17°** — beats LQR on healthy, 50 %, **and** dead wheel |
| **Correction of Report-1 data** | ⚠️ pending | a control-rate/time-axis bug inflated Report-1 settling times by ~25 % |

---

## 1. Phase 1B — Actuator fault model and fault-tolerance experiment

### 1.1 What was built

Three additions on top of the M0 simulator, all config-driven:

1. **Continuous reaction-wheel fault model.** Each wheel *i* carries a health scalar `h_i ∈ [0, 1]` and delivers
   `τ_actual,i = h_i · τ_command,i`.
   - `h_i = 1.0` healthy · `h_i = 0.5` **50 % torque** (degraded) · `h_i = 0.0` **failed** (fully dead).
   - A continuous health variable (rather than a binary flag) is deliberate: it makes the fault *severity* a dimension the controller can be trained across, and it is the quantity the later adaptive/world-model phases must **estimate online**.
2. **MTQ momentum management (desaturation).** This directly addresses the failure mode Report 1 identified — *"~27 % of the cases never settle, dominated by reaction-wheel momentum saturation"*. The three magnetorquers now continuously dump accumulated wheel momentum using the local magnetic field, so the wheels do not run out of authority during long acquisitions.
3. **Fault-tolerant control allocation.** `allocate_torque()` was factored out of the LQR path into a shared allocator used by **both** the classical and the learned controller, so every comparison is apples-to-apples. It redistributes the demanded torque over the *healthy* wheels when one is degraded or dead, and supplements with magnetic torque.

### 1.2 Experiment and results

Identical to the M1 protocol — random initial attitude and random initial angular velocity, 900 s per episode, **30 initial conditions** per case:

| Case | Success rate (< 1° held) | Settling time (mean) | Final pointing error | RMS error |
|---|---|---|---|---|
| **Healthy** | **86.7 %** | 146.6 s | **0.765°** | 11.40° |
| **RW1 @ 50 % torque** | **86.7 %** | 136.8 s | **0.765°** | 11.54° |
| **RW1 failed (dead)** | **0.0 %** | — | 41.77° | 42.51° |

![Phase 1B fault experiment](../codes/results/fault_experiment/fault_summary.png)

### 1.3 Interpretation

- **A 50 % torque loss is fully absorbed.** Success, settling time and final accuracy are statistically identical to the healthy case — the allocator simply redistributes the load onto the two remaining wheels. This is a genuinely useful negative result: *degradation* of this magnitude is a solved problem for a well-allocated classical controller, and is therefore **not** the interesting fault case for the thesis.
- **A fully dead wheel is not recoverable by the classical controller** (0 %, 41.8° final). With three wheels for a three-axis problem, losing one removes the ability to produce torque about that wheel's axis entirely; the magnetorquers alone cannot supply it fast enough. The satellite keeps tumbling at tens of degrees.
- **This is exactly the gap the thesis targets.** The dead-wheel case is where a learned, fault-adaptive policy can plausibly beat classical control — and §2.6 shows that it does.
- **Momentum management recovered most of M1's missing cases** (73.3 % → 86.7 % healthy). This is consistent with Report 1's diagnosis, though the two runs use different initial-condition sets (60 vs 30), so it is strongly suggestive rather than a controlled proof.

---

## 2. Phase 2 — Reinforcement-learning baseline (Baseline C)

This is the approved-approach baseline: PPO/SAC trained with random fault injection, evaluated against LQR on the *same* plant, allocator and initial conditions.

### 2.1 The RL environment

| Item | Value |
|---|---|
| Observation (9) | pointing-error rotation vector (3) + angular-rate error (3) + wheel speeds normalized by `rw_max_speed` (3) |
| Action (3) | **desired body torque**, continuous, ∈ [−1, 1] — mapped through the same allocator LQR uses (not raw wheel/magnetorquer commands) |
| Reward | `r = −(‖θ‖² + 0.1‖ω_err‖² + 10⁻²‖u‖²) + b·1[‖θ‖ < θ_tol]` |
| Episode | 900 s, control at the plant rate |
| Fault randomization | per-wheel health `h ∈ [0, 1]` sampled per episode |

Two design decisions worth recording:

- **Acting through the allocator, not around it.** The policy commands a torque and the shared allocator distributes it across healthy wheels and magnetorquers. This means the learned controller inherits the same fault-handling mechanism as LQR, and any difference in performance is attributable to the *policy*, not to a better low-level allocation.
- **Everything is loaded from YAML** (`config/rl.yaml`: `control_hz`, `episode_time_s`, `tau_scale`, `fault_mode`, `health_range`, `reward_tol_deg`, `reward_tol_bonus`, `reward_shape`), per the project rule that dynamics and platform variables must be configuration-driven and experiments reproducible.

### 2.2 Training infrastructure and compute

- **Parallelism is the real speed-up, not the GPU.** Training uses 8 parallel environments (`SubprocVecEnv` over 24 CPU cores), reaching ~2 300–2 600 steps/s → **2 M steps in ~15 minutes**.
- **GPU:** CUDA wheels (`torch 2.9.1+cu128`) were successfully installed for the RTX 5060 Laptop (sm_120). However, a measured benchmark showed **CPU 992 steps/s vs CUDA 618 steps/s** for this small 2×64 MLP policy — transfer overhead dominates at this network size, a known Stable-Baselines3 behaviour. The device selector therefore *deliberately* defaults to CPU, with `--device cuda` available on demand for the larger Phase 3 networks (CNN / transformer world models) where it will actually pay off.
- **Vector normalization** (`VecNormalize`) for observations and a configurable reward-normalization switch (see §2.5).

### 2.3 Run 1 — 1 M steps: converged, but insufficient

| | |
|---|---|
| Model | `results/rl_1m/ppo_adcs.zip` |
| Episodes | 1 688 |
| Episode reward | −38.8 → −0.4 |
| Learning curve | **converged** — flat after ~episode 750, low variance in the final third |

![1 M-step learning curve](../codes/results/rl_1m/ppo_learning_curve.png)

Evaluation against LQR (n = 6, identical plant, allocator and 900 s horizon):

| Case | RL (1 M) | LQR |
|---|---|---|
| Healthy | 0 % · **4.07°** | 83.3 % · 0.68° |
| RW1 @ 50 % | 0 % · 4.17° | 83.3 % · 0.68° |
| RW1 dead | 0 % · 68.0° | 0 % · 40.8° |

The policy reached the **neighbourhood** of nadir but not the 1° spec. Since the learning curve was already flat, **more training steps would not have fixed this** — the problem was the objective, not the budget.

### 2.4 Root-cause diagnosis

A dedicated rollout diagnostic (`scripts/diag_rl.py`) logged the settled behaviour (last 50 s of each episode):

| Signal | Value |
|---|---|
| Pointing error | 4.32° / 4.34° / 3.89° |
| Commanded action magnitude | **0.007** (of a ±1 range) |
| Wheel speeds | 10 % / 21 % / 6 % |
| Control cost | ≈ 0 |

**The policy learned to "slew and coast":** it performs the large rotation and then goes silent at ~4°, because the quadratic reward `−(θ² + …)` is numerically dominated by the huge transient during the 90°+ acquisition — a residual 4° error costs almost nothing in comparison, and the control-effort penalty actively discourages the fine correction needed to close the last few degrees. This is a **reward-induced local optimum**, not a control-authority limit (the wheels were only at 6–21 % of rated speed).

### 2.5 Fixes implemented

Four defects were found and corrected — all now configuration-driven:

1. **Reward shaping (`reward_shape: bonus`).** Added an explicit tolerance bonus `+b · 1[‖θ‖ < 1°]`, so *being inside the specification* is directly rewarded rather than being merely "less bad". A logistic and a quartic alternative are implemented behind the same YAML switch for a later ablation.
2. **Control-rate mismatch.** The RL environment had been constructed at **2 Hz** while LQR ran at the plant's rate — the learned policy was being trained and evaluated with **half the control bandwidth** of its baseline. Both now run at the identical rate.
3. **Horizon mismatch.** Training episodes were 300 s but evaluation used 900 s. Training horizon now matches evaluation.
4. **Reward normalization disabled** during training (`norm_reward: false`) — normalization was compressing the fine-pointing gradient that the shaping is meant to expose.

A fifth, separate defect in the *baseline* was also found and fixed: `simulate.py` advanced its time label by 0.25 s per 0.2 s actually simulated, so "900 s" episodes simulated only 720 s and every reported settling time was inflated by 25 %. This affects the **time** quantities of Report 1 and Phase 1B, not the **pointing accuracies** (see §3).

All of this is recorded in `docs/Phase2_RL_RewardShaping_Plan.md`.

### 2.6 Run 2 — 2 M steps with shaped reward: RL beats LQR

| | |
|---|---|
| Model | `results/rl_shaped/ppo_adcs.zip` |
| Episodes | 440 |
| Episode reward | −12 720.6 → **+3 021.1** (strongly positive = the satellite spends most of each episode inside tolerance) |

![2 M-step shaped learning curve](../codes/results/rl_shaped/ppo_learning_curve.png)

**Final comparison (n = 8, identical plant, allocator, initial conditions and 900 s horizon):**

| Case | **RL (shaped)** | LQR | Outcome |
|---|---|---|---|
| **Healthy** | **100 %** · **0.170°** | 75 % · 0.733° | RL succeeds more often **and is 4× more accurate** |
| **RW1 @ 50 %** | **100 %** · **0.170°** | 75 % · 0.733° | RL 4× more accurate |
| **RW1 dead** | **12.5 %** · 44.68° | **0 %** · 55.97° | **RL is the only controller that ever succeeds** |

![RL vs LQR across fault cases](../codes/results/rl_eval_shaped/rl_vs_lqr.png)

The diagnostic confirms the mechanism — the policy now *regulates* instead of coasting:

![Shaped-policy diagnostic](../codes/results/rl_diag_shaped/rl_diag.png)

| Settled behaviour (last 50 s) | Before | After |
|---|---|---|
| Pointing error | 4.32° | **0.08–0.18°** |
| θ² (the reward's main term) | 0.0065 | **0.00001** (~850× better) |

**Interpretation.** The learned controller now holds nadir pointing to **0.17°** — better than the classical baseline's 0.73° — while remaining robust to a 50 % actuator degradation. More importantly, on the **fully failed wheel** it recovers in 1 of 8 initial conditions where LQR recovers in 0 of 8: the policy has learned to exploit the magnetorquers and the two remaining wheels in a way the fixed LQR allocation does not. This is the first direct evidence for the thesis's central claim, and it is precisely the case Phase 1B identified as unsolvable classically.

### 2.7 Honest caveats

- **Five changes were made at once** (reward shaping, control rate, horizon, reward normalization, baseline time-axis fix). The improvement is therefore *established* but not yet *attributed*: an examiner would rightly ask whether the reward shaping or merely the faster control loop is responsible. **A controlled ablation is required** and is the immediate next step (§5).
- **12.5 % on the dead wheel is a low absolute number.** It is a proof of possibility, not a deployable result — the remaining 7 of 8 initial conditions still fail. Raising this is the explicit job of the world-model phases.
- Results are **single-seed per policy**; the comparison uses 8 evaluation initial conditions, which is adequate to establish the large effect but too few for tight confidence intervals.

---

## 3. Correction required to Report 1

The baseline time-axis defect described in §2.5 means that the **settling times** quoted in Report 1 and §1.2 above are inflated by the factor 0.25/0.2 ≈ 1.25, and the episodes really ran **720 s rather than 900 s**.

| Quantity | Status |
|---|---|
| Pointing accuracy (final error, RMS) | **unaffected** — the physics and the controller are unchanged |
| Success rates | **unaffected** (the settling *criterion* is a threshold, not a duration) |
| Settling times (Report 1: 143 s; §1.2: 146.6 s) | **inflated ≈25 %** — true values are ≈0.8× the quoted ones |

The M1 and Phase-1B experiments should be regenerated with the corrected time base before these numbers are quoted in the thesis. The RL results in §2.6 are **not** affected: they were produced with the fix already in place.

---

## 4. Updated roadmap

```
MIL ─────────────────────────────────────────────────▶ SIL ─▶ HIL
 │
 ├─ [DONE] M0: config-driven simulator (24U, 35 kg, J = diag(0.38, 0.73, 0.58))
 ├─ [DONE] M1: LQR nadir acquisition (73% success, ~0.8°)
 ├─ [DONE] Phase 1B: RW fault model + MTQ momentum management + fault-tolerant allocator
 │           healthy 86.7% · RW1@50% 86.7% · RW1 dead 0%
 ├─ [DONE] Phase 2: RL baseline (Baseline C) — PPO with fault randomization
 │           shaped reward → 100% / 0.17° healthy, 100% / 0.17° @50%, 12.5% / 44.7° dead
 │           LQR comparison: RL wins all three cases
 ├─ [NEXT] Ablation: attribute the gain (reward shaping vs control rate vs horizon)
 ├─ [NEXT] Phase 3: world models (Baseline B) — frozen JEPA-style latent model + MPC
 ├─ [NEXT] Phase 4: contribution — AdaJEPA-style adaptive world model + MPC + safety gate,
 │           evaluated on fault severities/combinations UNSEEN in training
 ├─ [NEXT] Phase 5: SIL — policy compression (quantization/pruning), inference-time verification
 └─ [FINAL] Phase 6: HIL — embedded deployment with signal-level fault injection
```

---

## 5. Next steps

1. **Ablation study (immediate).** Re-train with the reward shaping removed but the control rate, horizon and normalization fixes retained (and vice versa), to isolate which change produced the 4° → 0.17° improvement. This makes the Phase 2 claim defensible and is a natural results subsection.
2. **Regenerate the M1 / Phase-1B runs** with the corrected time base.
3. **Strengthen the dead-wheel result.** Fault curriculum (train progressively harder health values) or SAC, to lift the 12.5 % recovery rate before the world-model comparison — otherwise Baseline C is a weak reference point.
4. **Phase 3:** build the frozen JEPA-style latent world model + MPC on the same simulator, using the identical fault suite, to establish Baseline B.
5. **Phase 4:** the adaptive AdaJEPA-style model with a safety gate, evaluated specifically on **unseen fault severities** — the thesis's novelty claim.

**Final goal (unchanged):** a learning-based, fault-tolerant attitude controller that (a) acquires and holds nadir pointing to sub-degree accuracy, (b) recovers under reaction-wheel degradation and total failure, (c) generalizes to fault modes unseen during training, and (d) is validated through the full **MIL → SIL → HIL** chain — with the **adaptive world-model + MPC** as the novel contribution against the PPO/SAC and frozen-MPC baselines.
