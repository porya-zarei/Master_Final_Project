# Final Research Report — Experimental Evaluation of CCR v2 Fault-Tolerant Spacecraft ADCS

**Experiment IDs:**
- **Confirmatory Multi-Seed Campaign:** `E003_ccr_v2_confirmatory` (`30,000` SAC steps × `3` training seeds `[42, 107, 211]` × `10` held-out test seeds `[100..109]` × `9` held-out scenarios = `3,330` episodes; allocator confounder removed; pseudoreplication-free paired testing with step-down Holm-Bonferroni correction; 3-metric physical infeasibility breakdown)
- **Frozen Pilot Campaigns:** `E001_ccr_v2_benchmark` (initial baseline pilot, `1,260` episodes, tilted-dipole fallback, 12k SAC steps) and `E002_ccr_v2_igrf14_rlsfix` (upgraded single-train-seed pilot, `1,350` episodes, official degree-13 IGRF-14 + directional RLS forgetting + `A7_ccr_v2_eso`, 15k SAC steps)

**Date:** 2026-11-22  
**Primary Backend:** `fast_rk4` (`spacecraft_reference_001`, 100 kg, 5 Hz control, 100 Hz RK4, official IAGA IGRF-14 degree-13)  
**Basilisk Cross-Validation Status:** **`VALIDATED_GATE_C6_8_REGIME`** — Live Basilisk `2.12.2` Gate C6 and 8-regime validation matrix PASSED (`8/8` regimes: `R1, R4, R6, R8` open-loop plant validation with `max_pos_diff = 9.31 nm`, `max_att_diff = 0.0086°` over 10 s and `0.2870°` over 600 s; `R2, R3, R5, R7` closed-loop controller validation across `90°` slew, `10°/s` detumble, RW effectiveness+bias fault, and `20 s` star-tracker dropout).  
**Architectural Scope & Framing:** **CCR v2** provides **deterministic residual-authority regulation and conservative command filtering** around a classical LQR or LQR+ESO backbone. It does **not** claim a formal closed-loop Lyapunov or Control Barrier Function (CBF) stability proof, nor does it claim universal RL superiority over strong classical control (`A3_strong_classical`) across every fault regime. All CPU timing metrics reported below verify **desktop Python computational feasibility** within a `200 ms` (`5 Hz`) control period; embedded real-time qualification on Raspberry Pi CM5 and STM32H563ZIT hardware-in-the-loop (HIL) targets is intentionally deferred to subsequent hardware phases.

---

## 1. Executive Summary

We implemented, hardened across four scientific verification stages, and benchmarked a config-general spacecraft attitude determination and control (ADCS) research platform comparing classical baselines (`A0–A3`), residual-RL architectures (`A4–A7`, culminating in **CCR v2** with both LQR and ESO backbones), and six single-factor ablations. Following two frozen exploratory pilot campaigns (`E001_ccr_v2_benchmark` and `E002_ccr_v2_igrf14_rlsfix`), we executed the confirmatory multi-seed campaign **`E003_ccr_v2_confirmatory`** ([manifest.json](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/manifest.json)).

### Headline Scientific Conclusions (Confirmatory `E003_ccr_v2_confirmatory` Campaign)

1. **Zero Controllable Loss-of-Control (`0.0%`) and `100.0%` Correct Infeasibility Response:**
   Across `210` controllable held-out test episodes per learned arm (`7` controllable scenarios `S0, S1, S4, S5, S6, S7, S8` × `10` evaluation seeds × `3` training seeds), both **`A7_ccr_v2_full`** and **`A7_ccr_v2_eso`** achieved **`0.0%` Controllable LoC** (matching `A2` and `A3`, and improving over `A0` at `12.86%`, `A1` at `8.57%`, `A6` at `8.57%`, `A4` at `7.62%`, and `A5` at `1.43%`). On the `2` physically infeasible held-out scenarios (`S2_rw1_stuck_torque_test` and `S3_momentum_sat_test`, `60` episodes per learned arm), `A7_ccr_v2_full` and `A7_ccr_v2_eso` achieved **`100.0%` Infeasibility Detection** and **`100.0%` Correct Infeasibility Response** (latching supervisor mode `M3_UNKNOWN_INVALID_UNSAFE` and driving gated RL torque `||tau_rl_gated|| < 1e-6 N·m`), whereas `A4`, `A5`, and `Abl_A7_no_supervisor` achieved **`0.0%`** detection and response.
2. **All 4 Single-Factor CCR v2 Gating Ablations Survive Holm-Bonferroni Correction on Controllable Scenarios (`n_pairs = 70`, $p_{\text{Holm}} < 0.015$):**
   Aggregating across the `3` independent training seeds within each `(scenario_id, eval_seed)` first (`n_pairs = 70` pseudoreplication-free controllable pairs) and applying step-down **Holm-Bonferroni** correction against `A7_ccr_v2_full`:
   - Removing `rho` (`Abl_A7_no_rho`): **`+0.2256°`** mean diff (`95% CI [+0.1465°, +0.3022°]`, median diff `+0.1729°`, $d_z = 0.669$, raw $p = 4.77 \times 10^{-9}$, **$p_{\text{Holm}} = 5.72 \times 10^{-8}$**, `A7` wins `94.3%` of pairs).
   - Removing `alpha` (`Abl_A7_no_alpha`): **`+0.1579°`** mean diff (`95% CI [+0.0680°, +0.2534°]`, median diff `+0.0354°`, $d_z = 0.396$, raw $p = 6.65 \times 10^{-7}$, **$p_{\text{Holm}} = 7.31 \times 10^{-6}$**, `A7` wins `75.7%` of pairs; controllable LoC rises `0.0% -> 0.48%`).
   - Removing `G` (`Abl_A7_no_G`): **`+0.0122°`** median diff (median RMS `0.1288° -> 0.1632°`, mean RL torque `+46.5%` from `0.00268` to `0.00393 N·m`, raw $p = 0.00117$, **$p_{\text{Holm}} = 0.00939$**, `A7` wins `72.9%` of pairs).
   - Removing supervisor (`Abl_A7_no_supervisor`): **`+0.0301°`** mean diff (median diff `+0.0048°`, median RMS `0.1288° -> 0.1441°`, raw $p = 0.00219$, **$p_{\text{Holm}} = 0.01312$**, `A7` wins `71.4%` of pairs, and correct infeasibility response drops from `100.0%` to **`0.0%`**).
   - When the `20` physically infeasible `~67–104°` `S2`/`S3` pairs are pooled into all `90` held-out pairs, `Abl_A7_no_rho` ($p_{\text{Holm}} = 7.99 \times 10^{-9}$) and `Abl_A7_no_alpha` ($p_{\text{Holm}} = 8.11 \times 10^{-4}$) remain highly significant, whereas `Abl_A7_no_supervisor` (raw $p = 0.00657$, $p_{\text{Holm}} = 0.0525$) and `Abl_A7_no_G` (raw $p = 0.0181$, $p_{\text{Holm}} = 0.0904$) are partially diluted by the identical `~104°` physical ceiling in `S2`/`S3`.
3. **Closing the Nominal Variance Gap & Fault-Regime Gains vs. `A3_strong_classical`:**
   - **`A7_ccr_v2_eso`** achieved the **lowest Controllable-7 mean RMS error of all 15 arms (`0.2087°`)**, improving over `A3_strong_classical` (`0.2315°`, paired mean diff `-0.0228°`) and `A0_classical_lqr` (`1.0637°`, paired mean diff `-0.8549°`), outperforming `A3` on both **`S4_rw_bias_stiction_test` (`0.3818°` vs. `0.4904°`)** and **`S8_combined_rw_sensor_test` (`0.2934°` vs. `0.4037°`)** with `0.0%` LoC (overall controllable Wilcoxon $p_{\text{Holm}} = 0.659$ vs. `A3`).
   - **`A7_ccr_v2_full`** completely eliminated the `E002` pilot's nominal pointing variance gap on **`S0_nominal_test` (`0.1414°` mean / `0.1384°` median vs. `A3` `0.1415°` mean / `0.1444°` median)**, beat `A3` on controllable median RMS (`0.1288°` vs. `0.1306°`, `52.9%` win rate, $p_{\text{Holm}} = 1.0$), reduced RW actuation effort (`1.621` vs. `1.682 N·m·s`), accelerated median recovery (`11.4 s` vs. `12.4 s`), and cut **`S8` combined multi-fault mean RMS by `3.3x` (`0.1227°` vs. `0.4037°`)**, while exhibiting higher `S4` mean error (`1.4394°`) because its LQR-only backbone lacks ESO integral bias rejection.
4. **Notable Finding on `Abl_A7_clean_trained`:**
   Training the SAC residual policy on clean state observations while deploying it behind the full noisy `B1+B3+B4/B8` CCR v2 gate (**`Abl_A7_clean_trained`**) achieved **`0.0970°` controllable median RMS** (`0.2780°` mean RMS, `7.8 s` median recovery, `0.0%` controllable LoC, `100.0%` infeasibility response), statistically significantly outperforming **both** noise-trained `A7_ccr_v2_full` ($p_{\text{Holm}} = 3.05 \times 10^{-5}$, `78.6%` win rate) and **`A3_strong_classical`** ($p_{\text{Holm}} = 0.0245$, raw $p = 0.00223$, `71.4%` win rate). Because `Abl_A7_clean_trained` uses an LQR-only backbone, its `S4` mean error (`1.2567°`) still trails ESO-backed `A7_ccr_v2_eso` (`0.3818°`), making a **clean-trained SAC policy paired with the ESO backbone** an immediate high-priority candidate for future work.

---

## 2. Campaign Progression: Frozen Pilots (`E001`, `E002`) vs. Confirmatory Campaign (`E003`)

To maintain strict scientific hygiene, `E001` and `E002` are preserved as frozen **Pilot Campaigns**, while all confirmatory statistical claims are drawn from **`E003_ccr_v2_confirmatory`**:

| Campaign | Role | SAC Budget & Seeds | Held-Out Test Eval | Key Methodological & Architectural Advances |
|---|---|---|---|---|
| **`E001_ccr_v2_benchmark`** ([manifest.json](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E001_ccr_v2_benchmark/manifest.json)) | **Frozen Pilot 1** | `12,000` steps × `1` train seed (`42`) | `14` arms × `9` test scenarios × `6` seeds (`756` test / `1,260` total episodes) | Initial paired evaluation harness; tilted-dipole geomagnetic fallback; `A4` used naive pseudoinverse allocation while `A5–A7` used `cap_alloc`. |
| **`E002_ccr_v2_igrf14_rlsfix`** ([manifest.json](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E002_ccr_v2_igrf14_rlsfix/manifest.json)) | **Frozen Pilot 2** | `15,000` steps × `1` train seed (`42`) | `15` arms × `9` test scenarios × `6` seeds (`810` test / `1,350` total episodes) | Official degree-13 IAGA IGRF-14 ([igrf14coeffs.txt](file:///E:/Education/Master/Final_Project/codes/v2/configs/igrf14coeffs.txt)); directional RLS forgetting fix; config-general auto-scaling; added `A7_ccr_v2_eso`. |
| **`E003_ccr_v2_confirmatory`** ([manifest.json](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/manifest.json)) | **Confirmatory Campaign** | `30,000` steps × `3` train seeds (`42, 107, 211`; `18` trained policies) | `15` arms × `9` test scenarios × `10` seeds `100..109` (`3,330` test episodes) | **1)** Allocator confounder removed (`A4, A5, A6, A7, Abl_A7_*` all use `cap_alloc`). **2)** Stage 1–2 physics, MEKF, RLS confidence-cap, nominal-suppression, and `M3` infeasibility invariants hardened. **3)** Pseudoreplication-free paired testing (`n_pairs = 70` controllable / `90` all) with step-down **Holm-Bonferroni** (`wilcoxon_p_holm`). **4)** Oracle-normalized 3-metric failure & infeasibility breakdown. |

---

## 3. Stage 1–4 Scientific Hardening & Cross-Validation Verification

### 3.1 Stage 1–2 Physics, Estimation, Supervisor & RLS Invariants

All four core physical and architectural invariant groups are verified by automated regression tests in [test_stage1_invariants.py](file:///E:/Education/Master/Final_Project/codes/v2/tests/physics/test_stage1_invariants.py) and [test_phase9_10_eval_and_profiling.py](file:///E:/Education/Master/Final_Project/codes/v2/tests/regression/test_phase9_10_eval_and_profiling.py):

1. **Post-Clip RW Bearing Friction, Stiction Deadband & Internal Angular Momentum Conservation (`test_rw_bearing_friction_stiction_and_momentum_conservation`):**
   - In [backend.py](file:///E:/Education/Master/Final_Project/codes/v2/src/adcs/simulation/fast/backend.py), electrical motor torque `tau_elec` is clipped to `±tau_max` *before* subtracting mechanical bearing losses (Coulomb + viscous friction and stiction deadband), ensuring bearing drag physically adds to motor braking torque (`max_achieved_braking_tau0 > tau_lim + 0.01 N·m`) rather than being masked by the electrical limiter.
   - When `|omega_wheel| < 1e-3 rad/s` and `|tau_elec| <= stiction_band_nm`, the rotor remains strictly stationary (`dh_w = 0`, `|wheel_momentum_nms| < 1e-15 N·m·s`) even while the first-order motor lag state is non-zero.
   - In the absence of external environmental torques, total inertial angular momentum $\mathbf{H}_{\text{tot}}^{\mathcal{I}} = \mathbf{R}_{\mathcal{B}}^{\mathcal{I}}(\mathbf{J}\boldsymbol{\omega} + \mathbf{A}_{\text{rw}}\mathbf{h}_w)$ is conserved to **`< 1e-10 N·m·s`** (`atol = 1e-10`).
2. **MEKF Discrete Noise Propagation, Dropout Re-Acquisition & Nominal Residual Suppression (`test_nominal_residual_suppression_invariant`):**
   - In [mekf.py](file:///E:/Education/Master/Final_Project/codes/v2/src/adcs/estimation/mekf.py), discrete-time process noise covariance $\mathbf{Q}_d$ scales properly with `dt_s` and star-tracker re-acquisition after extended dropouts resets attitude covariance cleanly without filter divergence.
   - In [gate.py](file:///E:/Education/Master/Final_Project/codes/v2/src/adcs/control/safety/gate.py) and [controller.py](file:///E:/Education/Master/Final_Project/codes/v2/src/adcs/control/residual_rl/controller.py), even when paired with an adversarial constant residual policy (`u_rl = [0.8, -0.8, 0.8]`), CCR v2 suppresses post-transient (`t >= 40 s`) residual torque on nominal pointing (`S0_nominal_val`) to **`mean ||tau_rl_gated_nm|| < 1e-4 N·m`** and matches `StrongClassicalController` steady-state pointing (`t >= 70 s`) within **`< 0.02°`**.
3. **Online RLS Capability Stress Matrix (`test_online_rls_capability_stress_matrix`):**
   - **Unexcited steady pointing (`60 s` zero torque):** [capability.py](file:///E:/Education/Master/Final_Project/codes/v2/src/adcs/estimation/capability.py) flags `unverified_unexcited = True`, caps unexcited confidence at **`0.70 < confidence <= 0.85`** (preventing over-confident `confidence -> 1.0` drift while keeping directional margins `> 0.75`), and triggers **`0` false underactuated-axis detections** in [allocator.py](file:///E:/Education/Master/Final_Project/codes/v2/src/adcs/control/allocation/allocator.py).
   - **High vs. low excitation delay (`60%` loss on RW0):** High excitation (`0.08 N·m`) detects `effectiveness_nom < 0.55` in **`< 6.0 s`** and converges faster than low excitation (`0.011 N·m`), while maintaining higher confidence on actively excited healthy wheels than on `> 10 s` unexcited wheels.
   - **`S4` torque bias vs. multiplicative gain separation:** Under a `-0.03 N·m` additive bias on a healthy wheel (`effectiveness = 1.0`), RLS estimates **`bias_est_nm` within `±0.01 N·m` of `-0.03 N·m`** while preserving estimated multiplicative effectiveness **`> 0.75`**.
   - **Fault-removal recovery:** Restoring RW0 effectiveness from `0.40` back to `1.0` at `t = 8 s` recovers `effectiveness_nom > 0.85` within `12 s`.
4. **Physical Authority Infeasibility Detection & Instantaneous RL Shutdown (`test_supervisor_infeasibility_detection_and_rl_shutdown`):**
   - On `S2_rw1_stuck_torque_test` (`0.04 N·m` stuck wheel torque, `475/600` oracle zero-margin steps) and `S3_momentum_sat_test` (`0.02 N·m` persistent external disturbance at wheel momentum saturation, `527/600` oracle zero-margin steps), the supervisor ([supervisor.py](file:///E:/Education/Master/Final_Project/codes/v2/src/adcs/control/supervisor/supervisor.py)) detects `authority_infeasible = True`, transitions immediately to `SupervisorMode.M3_UNKNOWN_INVALID_UNSAFE`, sets `rl_permitted = False` (`gate_decision.rl_enabled = False`), and forces **`tau_rl_gated_nm = [0.0, 0.0, 0.0] N·m`**.
   - In [controller.py](file:///E:/Education/Master/Final_Project/codes/v2/src/adcs/control/residual_rl/controller.py) and [metrics.py](file:///E:/Education/Master/Final_Project/codes/v2/src/adcs/evaluation/metrics.py), `authority_infeasible` is gated by `bool(self.gate.cfg.use_supervisor and sup_status.authority_infeasible)` and `physically_infeasible` is normalized per `(scenario_id, seed)` from the reference classical baselines (`A1`/`A3`) in [run_phase9_10_experiments.py](file:///E:/Education/Master/Final_Project/codes/v2/scripts/run_phase9_10_experiments.py) so that an ungated controller (`A4`) that destabilizes a controllable scenario (`S5` seed 105) cannot excuse its own Loss-of-Control as physically infeasible.

### 3.2 Stage 3 Comprehensive 8-Regime Fast-vs-Basilisk `2.12.2` Validation Matrix

Executed in `.venv_bsk` (Python 3.11.15, live **AVS Lab Basilisk `2.12.2`**) via [test_phase3_basilisk.py](file:///E:/Education/Master/Final_Project/codes/v2/tests/integration/test_phase3_basilisk.py) and documented in [PHASE_3_REPORT.md](file:///E:/Education/Master/Final_Project/codes/v2/docs/agent_reports/PHASE_3_REPORT.md), the 8-regime matrix explicitly separates **Plant Validation** (`R1, R4, R6, R8`: matched open-loop trajectory discrepancy via [comparison.py](file:///E:/Education/Master/Final_Project/codes/v2/src/adcs/simulation/comparison.py)) from **Closed-Loop Controller Validation** (`R2, R3, R5, R7`: `StrongClassicalController` + `MultiplicativeEKF` + `OnlineCapabilityEstimator` + `SensorSuite` running identically on [FastSimulatorBackend](file:///E:/Education/Master/Final_Project/codes/v2/src/adcs/simulation/fast/backend.py) and [BasiliskBackend](file:///E:/Education/Master/Final_Project/codes/v2/src/adcs/simulation/basilisk/backend.py)):

| # | Regime | Validation Type | Duration / Steps | Measured `FastSimulatorBackend` vs. `Basilisk 2.12.2` Outcome | Pass Criterion |
|---|---|---|---|---|---|
| **R1** | Nominal 3-axis orbit + RW + MTQ dynamics | **Plant Validation** | `10 s` (`50` steps) | `max_pos_diff = 9.313e-09 m`, `max_att_diff = 1.507e-04 rad` (**`0.0086 deg`**), `max_omega_diff = 3.830e-05 rad/s`, `max_rw_h_diff = 6.587e-04 N·m·s` | `att_diff < 5e-3 rad`, `pos_diff < 1.0 m` (**PASS**) |
| **R2** | Large `90 deg` attitude slew to nadir | **Closed-Loop Controller Validation** | `50 s` (`250` steps) | Fast final error = **`0.6744 deg`**, Basilisk final error = **`0.6744 deg`**, terminal Fast-vs-Basilisk attitude diff = **`0.0000 deg`** | Both `< 1.0 deg`, diff `< 2.0 deg` (**PASS**) |
| **R3** | High angular rate `10 deg/s` detumble + acquisition | **Closed-Loop Controller Validation** | `60 s` (`300` steps) | Fast final error = **`0.4241 deg`**, Basilisk final error = **`0.4211 deg`**, terminal Fast-vs-Basilisk attitude diff = **`0.0225 deg`** | Both `< 1.0 deg`, diff `< 2.0 deg` (**PASS**) |
| **R4** | RW torque saturation (`0.25 > 0.15 N·m`) & high wheel momentum (`5.95 N·m·s`) | **Plant Validation** | `5 s` (`25` steps) | `max_att_diff = 1.190e-03 rad` (**`0.0682 deg`**), `max_omega_diff = 3.231e-04 rad/s`, `max_rw_h_diff = 5.386e-03 N·m·s` | `rw_h_diff < 1e-2 N·m·s`, `att_diff < 5e-3 rad` (**PASS**) |
| **R5** | RW0 `50%` effectiveness loss + `+0.015 N·m` bias fault (`set_rw_fault`) | **Closed-Loop Controller Validation** | `50 s` (`250` steps) | Fast final error = **`0.1062 deg`**, Basilisk final error = **`0.1047 deg`**, terminal Fast-vs-Basilisk attitude diff = **`0.0260 deg`** | Both converge `< 1.0 deg` (**PASS**) |
| **R6** | MTQ dipole saturation (`±5.0 -> ±2.0 A·m²`) & $\tau_{\text{MTQ}} \perp \mathbf{B}_{\text{body}}$ | **Plant Validation** | `4 s` (`20` steps) | `max_att_diff = 0.000e+00 rad`, `max_b_diff = 2.135e-09 T`, $\|\tau_{\text{MTQ}} \cdot \mathbf{B}\|_{\text{Fast}} = 2.585\times 10^{-26}$, $\|\tau_{\text{MTQ}} \cdot \mathbf{B}\|_{\text{Bsk}} = 1.995\times 10^{-14}$ | Clip at `±2.0 A·m²`, $\|\tau \cdot B\| < 10^{-12}$ (**PASS**) |
| **R7** | `20 s` star-tracker dropout (`t = 15..35 s`) + recovery | **Closed-Loop Controller Validation** | `60 s` (`300` steps) | Fast post-recovery error = **`0.0938 deg`**, Basilisk post-recovery error = **`0.1014 deg`**, terminal Fast-vs-Basilisk attitude diff = **`0.0105 deg`** | Both recover `< 1.0 deg` after ST return (**PASS**) |
| **R8** | Long-duration `600 s` orbit & attitude propagation | **Plant Validation** | `600 s` (`3000` steps) | `max_pos_diff = 1.971e-07 m` (`0.197 µm`), `max_omega_diff = 1.949e-05 rad/s`, `max_att_diff = 5.010e-03 rad` (**`0.2870 deg`**), `max_rw_h_diff = 3.164e-04 N·m·s` | `pos_diff < 1.0 m`, `att_diff < 0.05 rad` (**PASS**) |

---

## 4. Confirmatory Campaign (`E003_ccr_v2_confirmatory`) Quantitative Results

### 4.1 Three-Metric Failure & Physical Infeasibility Breakdown (`E003` Held-Out Test Split)

Source: [failure_breakdown_heldout.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/failure_breakdown_heldout.csv). Classical arms are evaluated across `10` held-out test seeds × `9` scenarios (`n_total = 90`: `n_controllable = 70` across `S0, S1, S4, S5, S6, S7, S8`; `n_infeasible = 20` across `S2, S3`). Learned and ablation arms are evaluated across `3` training seeds (`42, 107, 211`) × `10` held-out test seeds × `9` scenarios (`n_total = 270`: `n_controllable = 210`; `n_infeasible = 60`).

| Controller Arm | `n_total` | Overall LoC % | Controllable-7 LoC (`n`) | **Controllable-7 LoC %** | Infeasible-2 LoC (`n`) | **Infeasible-2 LoC %** | **Infeasibility Detected %** | **Correct Infeasibility Response %** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `A0_classical_lqr` | 90 | 32.22% | 9 / 70 | **12.86%** | 20 / 20 | 100.0% | 0.0% | 0.0% |
| `A1_classical_oracle_alloc` | 90 | 28.89% | 6 / 70 | **8.57%** | 20 / 20 | 100.0% | 0.0% | 0.0% |
| `A2_classical_dob_eso` | 90 | 22.22% | 0 / 70 | **0.00%** | 20 / 20 | 100.0% | 0.0% | 0.0% |
| `A3_strong_classical` | 90 | 22.22% | 0 / 70 | **0.00%** | 20 / 20 | 100.0% | 0.0% | 0.0% |
| `A4_unstructured_rl` | 270 | 28.15% | 16 / 210 | **7.62%** | 60 / 60 | 100.0% | **0.0%** | **0.0%** |
| `A5_rl_need_rho` | 270 | 23.33% | 3 / 210 | **1.43%** | 60 / 60 | 100.0% | **0.0%** | **0.0%** |
| `A6_rl_oracle_gate` | 270 | 28.89% | 18 / 210 | **8.57%** | 60 / 60 | 100.0% | 100.0% | 100.0% |
| **`A7_ccr_v2_eso`** | 270 | 22.22% | **0 / 210** | **0.00%** | 60 / 60 | 100.0% | **100.0%** | **100.0%** |
| **`A7_ccr_v2_full`** | 270 | 22.22% | **0 / 210** | **0.00%** | 60 / 60 | 100.0% | **100.0%** | **100.0%** |
| **`Abl_A7_clean_trained`** | 270 | 22.22% | **0 / 210** | **0.00%** | 60 / 60 | 100.0% | **100.0%** | **100.0%** |
| `Abl_A7_geom_G` | 270 | 22.22% | 0 / 210 | **0.00%** | 60 / 60 | 100.0% | 100.0% | 100.0% |
| `Abl_A7_no_G` | 270 | 22.22% | 0 / 210 | **0.00%** | 60 / 60 | 100.0% | 100.0% | 100.0% |
| `Abl_A7_no_alpha` | 270 | 22.59% | 1 / 210 | **0.48%** | 60 / 60 | 100.0% | 100.0% | 100.0% |
| `Abl_A7_no_rho` | 270 | 22.22% | 0 / 210 | **0.00%** | 60 / 60 | 100.0% | 100.0% | 100.0% |
| `Abl_A7_no_supervisor` | 270 | 22.22% | 0 / 210 | **0.00%** | 60 / 60 | 100.0% | **0.0%** | **0.0%** |

**Key Failure & Infeasibility Insights:**
- **`A7_ccr_v2_full`, `A7_ccr_v2_eso`, and `Abl_A7_clean_trained` combine `0.00%` Controllable LoC with `100.0%` Correct Infeasibility Response:** When physical actuator authority is lost on `S2` and `S3`, the `B4/B8` supervisor detects `authority_infeasible`, latches `M3`, and shuts down residual RL injection (`||tau_rl_gated|| < 1e-6 N·m`).
- **Why `A4`, `A5`, and `Abl_A7_no_supervisor` score `0.0%` on Infeasibility Response:** Without active supervisor gating (`use_supervisor = False`), these arms continue injecting nonzero RL residual torque (`mean_rl_torque_nm` on `S3`: `0.0598 N·m` for `A4`, `0.0594 N·m` for `A5`, `0.0065 N·m` for `Abl_A7_no_supervisor`) into a physically saturated plant.
- **Why Oracle-Gated `A6` suffers `8.57%` Controllable LoC (`18/210` episodes):** Because `A6` receives oracle `confidence = 1.0` (`mean_alpha = 0.820` on controllable scenarios vs. `0.238` for `A7_ccr_v2_full`), it over-exposes the closed-loop system to RL policy errors on `S5_mtq_degraded_test` (`14/30 = 46.67%` LoC) and `S4_rw_bias_stiction_test` (`4/30 = 13.33%` LoC). Similarly, removing `alpha` (`Abl_A7_no_alpha`, `mean_alpha = 0.924`) causes `1/30` (`3.33%`) LoC on `S5`.

### 4.2 Controllable-7 Performance Summary (`E003`, `n = 70` Classical / `n = 210` Learned)

Source: [summary_heldout_controllable.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/summary_heldout_controllable.csv) (covering controllable held-out scenarios `S0, S1, S4, S5, S6, S7, S8`; full 9-scenario summary including `S2` and `S3` is in [summary_heldout_test.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/summary_heldout_test.csv)):

| Controller Arm | `n` | Mean RMS (`deg`) | Std RMS (`deg`) | Median RMS (`deg`) | IQR RMS (`deg`) | Recovery Rate | Median Recovery (`s`) | Controllable LoC % | Mean RW Effort (`N·m·s`) | Mean `rho` | Mean `alpha` | Mean RL Torque (`N·m`) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `A0_classical_lqr` | 70 | 1.0637 | 1.5631 | 0.1650 | 2.1573 | 87.14% | 10.40 | 12.86% | 1.5032 | 0.000 | 0.000 | 0.00000 |
| `A1_classical_oracle_alloc` | 70 | 0.5019 | 0.9757 | 0.0987 | 0.0682 | 91.43% | 11.60 | 8.57% | 1.5035 | 0.000 | 0.000 | 0.00000 |
| `A2_classical_dob_eso` | 70 | 0.2246 | 0.1910 | 0.1389 | 0.1327 | 100.00% | 10.40 | **0.00%** | 1.5851 | 0.000 | 0.000 | 0.00000 |
| **`A3_strong_classical`** | 70 | **0.2315** | 0.2888 | **0.1306** | 0.1261 | 100.00% | **12.40** | **0.00%** | **1.6824** | 0.000 | 0.000 | 0.00000 |
| `A4_unstructured_rl` | 210 | 0.8699 | 1.1560 | 0.5667 | 0.3689 | 92.38% | 4.40 | 7.62% | 2.7374 | 1.000 | 1.000 | 0.02029 |
| `A5_rl_need_rho` | 210 | 0.7984 | 6.2383 | 0.1759 | 0.3210 | 99.52% | 9.80 | 1.43% | 1.9246 | 0.252 | 1.000 | 0.00946 |
| `A6_rl_oracle_gate` | 210 | 0.6293 | 1.0765 | 0.1216 | 0.3040 | 91.43% | 9.70 | 8.57% | 1.7545 | 0.317 | 0.820 | 0.00939 |
| **`A7_ccr_v2_eso`** | 210 | **0.2087** | **0.2243** | **0.1518** | **0.1124** | **100.00%** | **12.80** | **0.00%** | **1.6968** | 0.232 | 0.253 | **0.00259** |
| **`A7_ccr_v2_full`** | 210 | **0.3258** | 0.6169 | **0.1288** | **0.1192** | **100.00%** | **11.40** | **0.00%** | **1.6214** | 0.233 | 0.238 | **0.00268** |
| **`Abl_A7_clean_trained`** | 210 | **0.2780** | 0.5632 | **0.0970** | **0.0995** | **100.00%** | **7.80** | **0.00%** | **1.6643** | 0.214 | 0.232 | **0.00271** |
| `Abl_A7_geom_G` | 210 | 0.3381 | 0.6376 | 0.1288 | 0.1335 | 100.00% | 11.50 | **0.00%** | 1.6329 | 0.235 | 0.239 | 0.00264 |
| `Abl_A7_no_G` | 210 | 0.3264 | 0.5321 | 0.1632 | 0.1577 | 100.00% | 11.50 | **0.00%** | 1.6500 | 0.235 | 0.246 | 0.00393 |
| `Abl_A7_no_alpha` | 210 | 0.4837 | 0.7181 | 0.1894 | 0.2749 | 99.52% | 13.00 | 0.48% | 1.8682 | 0.258 | 0.924 | 0.00906 |
| `Abl_A7_no_rho` | 210 | 0.5514 | 0.5910 | 0.3775 | 0.3310 | 100.00% | 11.40 | **0.00%** | 1.6508 | 0.925 | 0.239 | 0.00519 |
| `Abl_A7_no_supervisor` | 210 | 0.3559 | 0.6098 | 0.1441 | 0.1562 | 100.00% | 11.50 | **0.00%** | 1.6657 | 0.260 | 0.313 | 0.00390 |

### 4.3 Per-Scenario Mean & Median Pointing Error Breakdown (`S0–S8`, `E003`)

Source: [summary_test_by_category.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/summary_test_by_category.csv) (`Mean° (Median°)` across `10` episodes/scenario for classical arms and `30` episodes/scenario for learned arms):

| Scenario | `A0_lqr` | `A3_strong` | `A4_unstruct` | `A6_oracle` | `A7_ccr_v2_full` | `A7_ccr_v2_eso` | `Abl_A7_clean_trained` |
|---|---|---|---|---|---|---|---|
| **`S0_nominal_test`** | 0.1390° (0.1404°) | **0.1415°** (0.1444°) | 0.3599° (0.3727°) | 0.0994° (0.0927°) | **0.1414° (0.1384°)** | 0.1506° (0.1576°) | **0.1037° (0.0934°)** |
| **`S1_rw2_severe25_test`** | 0.2890° (0.2945°) | 0.0982° (0.1000°) | 0.6107° (0.6641°) | 0.0679° (0.0642°) | 0.1047° (0.0948°) | 0.1099° (0.1099°) | **0.0671° (0.0626°)** |
| **`S2_rw1_stuck_torque_test`** *(infeasible)* | 104.44° (104.23°) | 104.43° (104.23°) | 104.59° (104.60°) | 104.49° (104.47°) | 104.43° (104.30°) | 104.42° (104.28°) | 104.51° (104.41°) |
| **`S3_momentum_sat_test`** *(infeasible)* | 66.70° (77.59°) | 66.61° (56.29°) | 74.68° (78.44°) | 66.85° (72.11°) | 67.71° (78.86°) | 67.39° (57.38°) | 67.23° (77.52°) |
| **`S4_rw_bias_stiction_test`** | 4.3949° (`70% LoC`) | 0.4904° (0.4852°) | 0.4744° (0.4648°) | 1.7787° (`13.3% LoC`) | 1.4394° (1.6365°) | **0.3818° (0.3935°)** | 1.2567° (1.3516°) |
| **`S5_mtq_degraded_test`** | 0.0802° (0.0814°) | 0.0831° (0.0822°) | 2.9022° (`53.3% LoC`) | 2.0742° (`46.7% LoC`) | 0.1046° (0.0940°) | 0.1048° (0.0901°) | **0.0979°** (0.1019°) |
| **`S6_sensor_fault_test`** | 0.1543° (0.1618°) | 0.2814° (0.2899°) | 0.6330° (0.6067°) | 0.1991° (0.2012°) | 0.2639° (0.2549°) | 0.2859° (0.2942°) | **0.2011° (0.2093°)** |
| **`S7_inertia_mismatch_test`** | 0.0978° (0.0949°) | 0.1221° (0.1233°) | 0.3977° (0.4173°) | 0.0816° (0.0852°) | 0.1035° (0.0933°) | 0.1345° (0.1395°) | **0.0710° (0.0719°)** |
| **`S8_combined_rw_sensor_test`** | 2.2904° (`20% LoC`) | 0.4037° (0.1661°) | 0.7116° (0.6695°) | 0.1043° (0.0967°) | **0.1227° (0.1174°)** | **0.2934°** (0.1667°) | **0.1485° (0.0863°)** |

### 4.4 Paired Statistical Tests with Step-Down Holm-Bonferroni Correction (`n_pairs = 70` Controllable & `n_pairs = 90` All)

To prevent multi-seed pseudoreplication, paired comparisons average across the `3` `train_seed` policies within each `(scenario_id, seed)` pair before running 5,000-sample paired bootstrap confidence intervals and two-sided Wilcoxon signed-rank tests with step-down **Holm-Bonferroni** family-wise error correction (`wilcoxon_p_holm`). Negative `mean_diff` / `median_diff` means the candidate `arm` has **lower (better)** RMS error than `reference_arm`; positive means the candidate `arm` has **higher (worse)** RMS error than `reference_arm`.

#### Table 4.4a: Single-Factor Ablations & Baselines vs. `A7_ccr_v2_full` on Controllable-7 (`n_pairs = 70`) and All-9 (`n_pairs = 90`)

Sources: [paired_test_controllable_ablations_vs_A7.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/paired_test_controllable_ablations_vs_A7.csv) (`n_pairs = 70`) and [paired_test_ablations_vs_A7.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/paired_test_ablations_vs_A7.csv) (`n_pairs = 90`):

| Candidate Arm (`vs. A7_ccr_v2_full`) | Controllable Mean Diff (`deg`) | Controllable 95% Bootstrap CI | Controllable Median Diff (`deg`) | Cohen's $d_z$ (`n=70`) | Raw Wilcoxon $p$ (`n=70`) | **Holm-Bonferroni $p_{\text{Holm}}$ (`n=70`)** | Candidate Win Rate (`n=70`) | All-9 $p_{\text{Holm}}$ (`n=90`) |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| **`Abl_A7_no_rho`** | **`+0.2256°`** | `[+0.1465°, +0.3022°]` | **`+0.1729°`** | `0.6690` | `4.77e-09` | **`5.72e-08`** | `5.71%` (`A7` wins `94.3%`) | **`7.99e-09`** |
| **`Abl_A7_no_alpha`** | **`+0.1579°`** | `[+0.0680°, +0.2534°]` | **`+0.0354°`** | `0.3956` | `6.65e-07` | **`7.31e-06`** | `24.29%` (`A7` wins `75.7%`) | **`8.11e-04`** |
| **`Abl_A7_no_G`** | `+0.0007°` | `[-0.0705°, +0.0750°]` | **`+0.0122°`** | `0.0022` | `0.00117` | **`0.00939`** | `27.14%` (`A7` wins `72.9%`) | `0.0904` (raw `0.0181`) |
| **`Abl_A7_no_supervisor`** | **`+0.0301°`** | `[-0.0311°, +0.0966°]` | **`+0.0048°`** | `0.1140` | `0.00219` | **`0.01312`** | `28.57%` (`A7` wins `71.4%`) | `0.0525` (raw `0.00657`) |
| `Abl_A7_geom_G` | `+0.0124°` | `[-0.0557°, +0.0901°]` | `-0.0015°` | `0.0388` | `0.00994` | **`0.04970`** | `64.29%` | `0.0801` (raw `0.0114`) |
| **`Abl_A7_clean_trained`** | **`-0.0477°`** | `[-0.1277°, +0.0303°]` | **`-0.0372°`** | `-0.1408` | `3.05e-06` | **`3.05e-05`** | **`78.57%`** | **`8.11e-04`** |
| `A7_ccr_v2_eso` | **`-0.1170°`** | `[-0.2276°, -0.0207°]` | `+0.0083°` | `-0.2594` | `0.2478` | `0.7433` | `38.57%` | `1.0000` |
| `A4_unstructured_rl` | **`+0.5442°`** | `[+0.2950°, +0.8023°]` | **`+0.3667°`** | `0.4924` | `4.80e-06` | **`4.32e-05`** | `14.29%` (`A7` wins `85.7%`) | **`7.17e-06`** |
| `A5_rl_need_rho` | `+0.4727°` | `[-0.0295°, +1.3560°]` | `+0.0134°` | `0.1364` | `0.0463` | `0.1852` | `47.14%` | `0.1260` |
| `A6_rl_oracle_gate` | **`+0.3036°`** | `[+0.1362°, +0.4920°]` | `-0.0257°` | `0.3966` | `0.6418` | `1.0000` | `64.29%` | `1.0000` |
| `A0_classical_lqr` | **`+0.7379°`** | `[+0.4713°, +1.0298°]` | `+0.0127°` | `0.6172` | `0.00135` | **`0.00948`** | `41.43%` (`A7` wins `58.6%`) | `0.0890` |
| `A3_strong_classical` | `-0.0943°` | `[-0.2050°, +0.0146°]` | `+0.0019°` | `-0.1997` | `0.8906` | `1.0000` | `47.14%` (`A7` wins `52.9%`) | `1.0000` |

#### Table 4.4b: Paired Comparisons vs. `A3_strong_classical` and `A0_classical_lqr` on Controllable-7 (`n_pairs = 70`)

Sources: [paired_test_controllable_vs_A3.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/paired_test_controllable_vs_A3.csv), [paired_test_vs_A3.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/paired_test_vs_A3.csv), and [paired_test_controllable_vs_A0.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/paired_test_controllable_vs_A0.csv):

| Candidate Arm | vs. Reference Arm | `n_pairs` | Mean Diff (`deg`) | 95% Bootstrap CI | Median Diff (`deg`) | Cohen's $d_z$ | Raw Wilcoxon $p$ | **Holm-Bonferroni $p_{\text{Holm}}$** | Candidate Win Rate |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| **`A7_ccr_v2_eso`** | `A3_strong_classical` | 70 | **`-0.0228°`** | `[-0.0994°, +0.0313°]` | `+0.0082°` | `-0.0788` | `0.1318` | `0.6591` | `30.00%` |
| **`A7_ccr_v2_full`** | `A3_strong_classical` | 70 | `+0.0943°` | `[-0.0146°, +0.2050°]` | **`-0.0019°`** | `0.1997` | `0.8906` | `1.0000` | **`52.86%`** |
| **`Abl_A7_clean_trained`** | `A3_strong_classical` | 70 | `+0.0465°` | `[-0.0619°, +0.1628°]` | **`-0.0326°`** | `0.0965` | `0.00223` | **`0.02453`** | **`71.43%`** |
| `A4_unstructured_rl` | `A3_strong_classical` | 70 | **`+0.6384°`** | `[+0.4240°, +0.8751°]` | `+0.3201°` | `0.6521` | `5.48e-11` | **`7.67e-10`** | `10.00%` |
| `A5_rl_need_rho` | `A3_strong_classical` | 70 | **`+0.5669°`** | `[+0.0566°, +1.4759°]` | `+0.0146°` | `0.1571` | `0.00255` | **`0.02555`** | `44.29%` |
| `A6_rl_oracle_gate` | `A3_strong_classical` | 70 | **`+0.3978°`** | `[+0.1933°, +0.6134°]` | `-0.0301°` | `0.4426` | `0.9603` | `1.0000` | `65.71%` |
| `A0_classical_lqr` | `A3_strong_classical` | 70 | **`+0.8322°`** | `[+0.5168°, +1.1810°]` | `-0.0005°` | `0.5757` | `0.00782` | `0.06255` | `51.43%` |
| **`A7_ccr_v2_eso`** | `A0_classical_lqr` | 70 | **`-0.8549°`** | `[-1.2071°, -0.5342°]` | `+0.0037°` | `-0.5770` | `0.01553` | `0.07763` | `48.57%` |
| **`A7_ccr_v2_full`** | `A0_classical_lqr` | 70 | **`-0.7379°`** | `[-1.0298°, -0.4713°]` | **`-0.0127°`** | `-0.6172` | `0.00135` | **`0.01490`** | **`58.57%`** |
| **`Abl_A7_clean_trained`** | `A0_classical_lqr` | 70 | **`-0.7857°`** | `[-1.0869°, -0.5085°]` | **`-0.0418°`** | `-0.6332` | `1.07e-06` | **`1.50e-05`** | **`74.29%`** |

### 4.5 Multi-Seed Training Reproducibility (`train_seed in {42, 107, 211}`, `n = 70` Controllable Episodes/Seed)

Source: [summary_controllable_by_train_seed.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/summary_controllable_by_train_seed.csv). Every independently trained seed (`42, 107, 211`) of `A7_ccr_v2_eso`, `A7_ccr_v2_full`, and `Abl_A7_clean_trained` achieved **`0.00%` Controllable LoC** (`100.0%` recovery rate) with tight seed-to-seed consistency, whereas `A4_unstructured_rl` (`14.29%, 0.00%, 8.57%` LoC), `A5_rl_need_rho` (`1.43%` LoC on every seed; seed `211` std RMS `10.79°`), and `A6_rl_oracle_gate` (`8.57%, 17.14%, 0.00%` LoC) suffered severe seed-dependent instability:

| Learned Controller Arm | Train Seed `42` Mean / Median RMS (`LoC %`) | Train Seed `107` Mean / Median RMS (`LoC %`) | Train Seed `211` Mean / Median RMS (`LoC %`) | All 3 Seeds Pooled (`n = 210`) Mean / Median RMS (`LoC %`) |
|---|---|---|---|---|
| `A4_unstructured_rl` | `1.2191°` / `0.5980°` (**`14.29% LoC`**) | `0.6092°` / `0.5858°` (`0.00% LoC`) | `0.7815°` / `0.5105°` (**`8.57% LoC`**) | `0.8699°` / `0.5667°` (**`7.62% LoC`**) |
| `A5_rl_need_rho` | `0.4362°` / `0.1685°` (**`1.43% LoC`**) | `0.4255°` / `0.2043°` (**`1.43% LoC`**) | `1.5336°` / `0.1377°` (**`1.43% LoC`**) | `0.7984°` / `0.1759°` (**`1.43% LoC`**) |
| `A6_rl_oracle_gate` | `0.6236°` / `0.1261°` (**`8.57% LoC`**) | `0.8981°` / `0.1398°` (**`17.14% LoC`**) | `0.3662°` / `0.0990°` (`0.00% LoC`) | `0.6293°` / `0.1216°` (**`8.57% LoC`**) |
| **`A7_ccr_v2_eso`** | **`0.1917°` / `0.1214°` (`0.00% LoC`)** | **`0.2005°` / `0.1629°` (`0.00% LoC`)** | **`0.2340°` / `0.1520°` (`0.00% LoC`)** | **`0.2087°` / `0.1518°` (`0.00% LoC`)** |
| **`A7_ccr_v2_full`** | **`0.3326°` / `0.1365°` (`0.00% LoC`)** | **`0.3074°` / `0.1281°` (`0.00% LoC`)** | **`0.3373°` / `0.1276°` (`0.00% LoC`)** | **`0.3258°` / `0.1288°` (`0.00% LoC`)** |
| **`Abl_A7_clean_trained`** | **`0.2459°` / `0.0965°` (`0.00% LoC`)** | **`0.3074°` / `0.0943°` (`0.00% LoC`)** | **`0.2808°` / `0.0999°` (`0.00% LoC`)** | **`0.2780°` / `0.0970°` (`0.00% LoC`)** |

---

## 5. Desktop Python Computational Feasibility Profile (`E003`)

Source: [cpu_profile.json](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/cpu_profile.json) (`500` timed calls per component on `Windows-11`, Python `3.14.6`, NumPy `2.5.0`, official degree-13 IGRF-14 enabled).

> [!IMPORTANT]
> The timings below demonstrate **desktop Python computational feasibility** inside the `200.0 ms` (`5 Hz`) control period (`2.851%` mean / `4.982%` p99 budget utilization). They do **not** constitute embedded real-time qualification; C99/C++ fixed-rate verification on Raspberry Pi CM5 and STM32H563ZIT hardware-in-the-loop (HIL) is deferred to subsequent hardware deployment phases (see [SIL_HIL_READINESS.md](file:///E:/Education/Master/Final_Project/codes/v2/docs/SIL_HIL_READINESS.md)).

| Onboard Component | Calls | Mean (`ms`) | p50 (`ms`) | p95 (`ms`) | p99 (`ms`) | Max (`ms`) | % of `200 ms` Budget (Mean / p99) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `B1_MEKF` (with degree-13 IGRF-14) | 500 | `1.014` | `1.083` | `1.723` | `1.843` | `2.057` | `0.507%` / `0.922%` |
| `B3_OnlineCapability` (RLS + margins) | 500 | `2.300` | `2.416` | `3.785` | `4.038` | `4.547` | `1.150%` / `2.019%` |
| `B6_PolicyInference_NumPy` (`30->64->64->3` MLP) | 500 | **`0.045`** | `0.047` | `0.079` | **`0.106`** | `0.187` | `0.023%` / `0.053%` |
| `CCR_v2_Controller_Step` (`B2+B4+B6+B7+B8`) | 500 | `2.389` | `2.481` | `4.042` | `4.213` | `4.591` | `1.195%` / `2.106%` |
| `A3_StrongClassical_Step` (`B2+ESO+B7`) | 500 | `1.431` | `1.556` | `2.409` | `2.621` | `2.876` | `0.715%` / `1.310%` |
| **`onboard_total_B1_B3_CCR_v2`** | 500 | **`5.703`** | `5.741` | `9.472` | **`9.964`** | `10.869` | **`2.851%` / `4.982%`** |

- **Memory Footprint:** `6,339` MLP parameters = **`24.76 KB`** in `float32`; peak traced Python memory during profiling = `145.99 KB` (`131.60 KB` current).

---

## 6. Answers to the 10 Required Research Questions ([RESEARCH_PROTOCOL.md](file:///E:/Education/Master/Final_Project/codes/v2/RESEARCH_PROTOCOL.md) §14)

### 1. What was the strongest classical baseline and how was it tuned?
- **`A3_strong_classical`** ([baselines.py](file:///E:/Education/Master/Final_Project/codes/v2/src/adcs/control/classical/baselines.py)) combines:
  1. Config-general CARE-solved LQR (`ClassicalLQRConfig.from_spacecraft(sc_cfg)`, giving $K_p \approx 0.50\,\mathrm{N\cdot m/rad}$, $K_d \approx 6.06\,\mathrm{N\cdot m\cdot s/rad}$ on `spacecraft_reference_001`) with gyroscopic feedforward and `0.08 rad/s` eigenaxis slew-rate limiting.
  2. 3-axis nonlinear **Extended State Observer (`ESO/DOB`)** ($\omega_o = 0.75\,\mathrm{rad/s}$, disturbance bound `0.8 * tau_lim`, frozen when `gamma_obs < 0.35`).
  3. **Onboard capability-aware box-constrained allocator (`cap_alloc`)** compensating estimated wheel effectiveness and torque bias, plus dual-role MTQ assist and momentum unloading (`mtq_unload_gain = 0.004`).
  4. **Deterministic observability gain schedule** (`kp_scale = 0.45 + 0.55 * gamma_obs`).
- Tuned exclusively on `train`/`val` splits; held-out `test` scenarios were untouched. In `E003`, `A3` achieved **`0.0%` Controllable LoC** across all `70` controllable held-out episodes (`0.2315°` mean RMS, `0.1306°` median RMS).

### 2. In which regimes did RL / CCR v2 improve performance?
- **Torque bias + stiction (`S4_rw_bias_stiction_test`, `E003`):** `A7_ccr_v2_eso` achieved **`0.3818°`** mean RMS (`0.3935°` median, `1.736 N·m·s` effort, `0.0%` LoC), outperforming `A3_strong_classical` (`0.4904°` mean, `0.4852°` median, `1.769 N·m·s`), `A7_ccr_v2_full` (`1.4394°`), `A6` (`1.7787°`, `13.3%` LoC), `A5` (`3.6196°`, `3.3%` LoC), and `A0` (`4.3949°`, `70.0%` LoC).
- **Combined held-out multi-fault (`S8_combined_rw_sensor_test`, `E003`):** `A7_ccr_v2_full` achieved **`0.1227°`** mean RMS (`0.1174°` median, `1.287 N·m·s` effort, `9.9 s` recovery), cutting mean RMS by **`3.3x`** relative to `A3_strong_classical` (`0.4037°` mean, `0.1661°` median, `1.472 N·m·s` effort, `11.0 s` recovery) and beating `A2` (`0.6625°`), `A4` (`0.7116°`), and `A0` (`2.2904°`, `20.0%` LoC). `A7_ccr_v2_eso` (`0.2934°` mean) and `Abl_A7_clean_trained` (`0.1485°` mean, `0.0863°` median) also outperformed `A3` on `S8`.
- **Overall Controllable-7 Mean & Median Pointing (`E003`):** `A7_ccr_v2_eso` achieved the lowest overall controllable mean RMS (**`0.2087°`** vs. `A3` `0.2315°` and `A0` `1.0637°`), while `Abl_A7_clean_trained` achieved the lowest controllable median RMS (**`0.0970°`** vs. `A3` `0.1306°`, $p_{\text{Holm}} = 0.0245$, `71.4%` win rate) and fastest median recovery (`7.8 s` vs. `12.4 s`).

### 3. In which regimes was RL neutral or worse?
- **Unstructured RL (`A4`) and need-only RL (`A5`) were worse than `A3` even with the allocator confounder removed (`cap_alloc` shared across all learned arms):** On Controllable-7 (`n_pairs = 70`), `A4` degraded mean RMS by `+0.6384°` ($p_{\text{Holm}} = 7.67 \times 10^{-10}$, `7.62%` controllable LoC, `53.3%` LoC on `S5`) and `A5` degraded mean RMS by `+0.5669°` ($p_{\text{Holm}} = 0.0255$, `1.43%` controllable LoC).
- **LQR-backed `A7_ccr_v2_full` on additive torque bias (`S4_rw_bias_stiction_test`):** Without the ESO disturbance observer in its classical backbone, `A7_ccr_v2_full` (`1.4394°` mean RMS) and `Abl_A7_clean_trained` (`1.2567°` mean RMS) trailed `A3_strong_classical` (`0.4904°`) and `A7_ccr_v2_eso` (`0.3818°`) on `S4`, although both maintained `0.0%` LoC (unlike `A0` at `70%` LoC, `A1` at `60%` LoC, and `A6` at `13.3%` LoC).
- **Physically infeasible authority loss (`S2_rw1_stuck_torque_test` and `S3_momentum_sat_test`):** All 15 arms experienced `100.0%` LoC (`~104.4°` on `S2`, `~66.6–74.7°` on `S3`) because `0.04 N·m` stuck wheel torque and `0.02 N·m` persistent disturbance at wheel momentum saturation exceed MTQ authority (`< 8e-5 N·m`) by more than two orders of magnitude. Here, the scientific differentiator is **correct infeasibility response**: `A7_ccr_v2_full` and `A7_ccr_v2_eso` detected infeasibility and zeroed gated RL torque on `100.0%` of `S2`/`S3` episodes.

### 4. Did capability-derived directional gating (`G`) improve outcomes relative to ungated and oracle variants? (**Hypothesis H1**)
- **Supported after Holm-Bonferroni correction on Controllable-7 (`Abl_A7_no_G` vs. `A7_ccr_v2_full`, $p_{\text{Holm}} = 0.00939$):** Removing `G` degraded controllable median RMS from `0.1288°` to `0.1632°` (paired median diff `+0.0122°`, `A7` won `72.86%` of controllable pairs, raw $p = 0.00117$) and increased mean gated residual torque by **`46.5%`** (`0.00268 -> 0.00393 N·m`). On `S8_combined_rw_sensor_test`, removing `G` more than doubled mean RMS error (`0.1227° -> 0.2928°`).
- **Diagonal `G` vs. Geometry-Aware Projection (`Abl_A7_geom_G`):** Both achieved `0.0%` controllable LoC and identical controllable median RMS (`0.1288°`), with `Abl_A7_geom_G` generalizing directly to non-orthogonal N-wheel pyramid geometries.
- **Online `A7_ccr_v2_full` vs. Oracle `A6_rl_oracle_gate`:** Online `A7_ccr_v2_full` reduced controllable mean RMS from `0.6293°` (`A6`) to `0.3258°` (paired mean diff `-0.3036°`, 95% CI `[-0.4920°, -0.1362°]`) and eliminated `A6`'s `8.57%` controllable LoC (`46.67%` LoC on `S5` and `13.33%` LoC on `S4`), proving that conservative online RLS confidence (`alpha ~ 0.24`) is safer than oracle `confidence = 1.0` (`alpha ~ 0.82`) when gating finite-budget RL policies.

### 5. Did need/trust separation (`rho` vs. `alpha`) add value? (**Hypothesis H2**)
- **Decisively supported after Holm-Bonferroni correction (`E003`, `n_pairs = 70` and `n_pairs = 90`):**
  - Removing `rho` (`Abl_A7_no_rho`): **`+0.2256°`** controllable mean degradation (95% CI `[+0.1465°, +0.3022°]`, median RMS `0.1288° -> 0.3775°`, $d_z = 0.669$, **$p_{\text{Holm}} = 5.72 \times 10^{-8}$** on Controllable-7; **$p_{\text{Holm}} = 7.99 \times 10^{-9}$** on All-9, `A7` wins `94.29%` of controllable pairs).
  - Removing `alpha` (`Abl_A7_no_alpha`): **`+0.1579°`** controllable mean degradation (95% CI `[+0.0680°, +0.2534°]`, median RMS `0.1288° -> 0.1894°`, $d_z = 0.396$, **$p_{\text{Holm}} = 7.31 \times 10^{-6}$** on Controllable-7; **$p_{\text{Holm}} = 8.11 \times 10^{-4}$** on All-9, `A7` wins `75.71%` of controllable pairs, controllable LoC increases from `0.0%` to `0.48%`, and mean residual torque increases `3.38x` from `0.00268` to `0.00906 N·m`).
  - Need-only `A5_rl_need_rho` (`rho` without `alpha`, `G`, or supervisor): suffered `1.43%` controllable LoC, `0.0%` infeasibility response, and `+0.4727°` higher controllable mean RMS than `A7_ccr_v2_full`.

### 6. How did estimation uncertainty and sensor faults change residual authority? (**Hypothesis H3**)
- **Deterministic supervisor & gate behavior verified (`Abl_A7_no_supervisor` vs. `A7_ccr_v2_full`):** During star-tracker dropouts (`S6` 35 s dropout, `S8` 20 s dropout, and R7 in Basilisk) and physical authority loss (`S2`, `S3`), the `B4/B8` supervisor transitions to `M3_UNKNOWN_INVALID_UNSAFE`, forcing `alpha = 0` and `tau_rl_gated = 0.0 N·m`. Removing the supervisor (`Abl_A7_no_supervisor`) significantly degraded controllable pointing ($p_{\text{Holm}} = 0.01312$, `A7` won `71.43%` of pairs; `S8` mean RMS worsened `0.1227° -> 0.1930°`) and dropped `S2`/`S3` infeasibility response from `100.0%` to **`0.0%`**.
- **Significant positive finding on `Abl_A7_clean_trained` (`E003`, 30k steps × 3 seeds):** Unlike the 15k-step single-seed pilot (`E002`, where `Abl_A7_clean_trained` vs. `A7` had $p = 0.140$), scaling to `30,000` steps across `3` seeds in `E003` revealed that **training the SAC residual policy on clean state observations while deploying it behind the full noisy `B1+B3+B4/B8` CCR v2 gate (`Abl_A7_clean_trained`) significantly outperformed noise-trained `A7_ccr_v2_full`** (`0.0970°` vs. `0.1288°` controllable median RMS, `7.8 s` vs. `11.4 s` median recovery, **$p_{\text{Holm}} = 3.05 \times 10^{-5}$**, `78.57%` win rate) **and beat `A3_strong_classical`** (**$p_{\text{Holm}} = 0.0245$**, `71.43%` win rate). Clean-state critic targets reduce TD value-estimation variance during SAC training, while the deterministic `B4/B8` gate and supervisor handle test-time sensor noise and dropouts without requiring the MLP policy itself to be trained on noisy MEKF states.

### 7. What was the generalization performance on held-out faults? (**Hypothesis H4**)
- Across unseen wheel axes (`RW2`), unseen degradation severities (`75%` loss in `S1`), unseen additive bias + stiction (`S4`), unseen MTQ degradation (`S5`), unseen sensor glitches + 35 s dropouts (`S6`), unseen inertia mismatch (`S7`), and unseen combined multi-faults (`S8`), every trained seed (`42, 107, 211`) of `A7_ccr_v2_full`, `A7_ccr_v2_eso`, and `Abl_A7_clean_trained` achieved **`0.00%` Controllable LoC** (`210/210` controllable episodes recovered per arm) and **`100.0%` Correct Infeasibility Response** on `S2`/`S3`.

### 8. Did the full architecture reduce failures or recovery time without excessive effort or latency?
- **Failures:** Eliminated controllable held-out LoC from `12.86%` (`A0`), `8.57%` (`A1`, `A6`), `7.62%` (`A4`), and `1.43%` (`A5`) to **`0.00%`** across all `3` training seeds (`A7_ccr_v2_full`, `A7_ccr_v2_eso`, `Abl_A7_clean_trained`).
- **Recovery time:** On controllable scenarios, `A7_ccr_v2_full` (`11.40 s` median) and `Abl_A7_clean_trained` (`7.80 s` median) recovered faster than `A3_strong_classical` (`12.40 s` median).
- **Actuation effort:** On controllable scenarios, `A7_ccr_v2_full` (`1.621 N·m·s`) and `Abl_A7_clean_trained` (`1.664 N·m·s`) used **less** RW torque-time integral than `A3_strong_classical` (`1.682 N·m·s`) and `40.8%` less than `A4_unstructured_rl` (`2.737 N·m·s`), while `A7_ccr_v2_eso` (`1.697 N·m·s`) matched `A3` within `0.9%`.
- **Desktop CPU feasibility (`H5`):** Full onboard `B1 + B3 + CCR v2` with degree-13 IGRF-14 executes in **`5.703 ms` mean (`9.964 ms` p99)** — **`2.851%` mean / `4.982%` p99** of the `200 ms` (`5 Hz`) control period (`0.045 ms` NumPy MLP inference, `24.76 KB` float32 weights).

### 9. Which results are statistically and practically meaningful?
- **Statistically significant after Holm-Bonferroni correction and practically meaningful (`E003`, `n_pairs = 70` Controllable-7):**
  - All 4 single-factor CCR v2 ablations against `A7_ccr_v2_full`: `Abl_A7_no_rho` ($p_{\text{Holm}} = 5.72 \times 10^{-8}$), `Abl_A7_no_alpha` ($p_{\text{Holm}} = 7.31 \times 10^{-6}$), `Abl_A7_no_G` ($p_{\text{Holm}} = 0.00939$), and `Abl_A7_no_supervisor` ($p_{\text{Holm}} = 0.01312$, plus `0.0%` vs. `100.0%` infeasibility response).
  - `A7_ccr_v2_full` over `A4_unstructured_rl` ($p_{\text{Holm}} = 4.32 \times 10^{-5}$, `0.0%` vs. `7.62%` controllable LoC) and `A0_classical_lqr` ($p_{\text{Holm}} = 0.00948$, `0.0%` vs. `12.86%` controllable LoC).
  - `Abl_A7_clean_trained` over `A7_ccr_v2_full` ($p_{\text{Holm}} = 3.05 \times 10^{-5}$, `78.57%` win rate), `A3_strong_classical` ($p_{\text{Holm}} = 0.02453$, `71.43%` win rate), and `A0_classical_lqr` ($p_{\text{Holm}} = 1.50 \times 10^{-5}$, `74.29%` win rate).
  - Live Basilisk `2.12.2` Gate C6 and 8-regime plant/controller validation (`8/8` regimes passed).
- **Practically meaningful regime-specific trade-offs (statistically neutral overall vs. `A3`):**
  - Across all 70 controllable pairs, `A7_ccr_v2_eso` achieves the lowest mean RMS (`0.2087°` vs. `A3` `0.2315°`, paired mean diff `-0.0228°`, $p_{\text{Holm}} = 0.659$) and beats `A3` on `S4` (`0.3818°` vs. `0.4904°`) and `S8` (`0.2934°` vs. `0.4037°`), while `A7_ccr_v2_full` matches `A3` on `S0` (`0.1414°` vs. `0.1415°`), beats `A3` on `S8` (`0.1227°` vs. `0.4037°`), and ties `A3` overall ($p_{\text{Holm}} = 1.0$, `52.86%` win rate), but trails `A3` on `S4` (`1.4394°`) due to its LQR-only backbone.

### 10. Limitations, Negative Results, and Recommended Next Steps
1. **Combining `Abl_A7_clean_trained` with the ESO backbone (`A7_ccr_v2_eso_clean_trained`):** `E003` showed that clean-state SAC training (`Abl_A7_clean_trained`) achieves the best controllable median RMS (`0.0970°`) and beats `A3_strong_classical` ($p_{\text{Holm}} = 0.0245$), while the ESO backbone (`A7_ccr_v2_eso`) achieves the best `S4` additive bias + stiction performance (`0.3818°`) and lowest overall controllable mean RMS (`0.2087°`). Combining clean-state SAC training with the ESO backbone is the highest-ROI algorithmic next step.
2. **Dilution of `no_G` and `no_supervisor` $p_{\text{Holm}}$ when pooling physically infeasible `S2`/`S3` episodes:** Because `S2` and `S3` exceed physical actuator authority for all controllers (`~67–104°` RMS), pooling those `20` infeasible pairs with the `70` controllable pairs dilutes `Abl_A7_no_G` ($p_{\text{Holm}} = 0.00939 \to 0.0904$) and `Abl_A7_no_supervisor` ($p_{\text{Holm}} = 0.01312 \to 0.0525$). Reporting Controllable-7 (`n_pairs = 70`) alongside the 3-metric failure/infeasibility table (`failure_breakdown_heldout.csv`) is therefore essential for scientifically transparent evaluation.
3. **Deferred Embedded HIL Qualification (Raspberry Pi CM5 & STM32H563ZIT):** While `cpu_profile.json` verifies desktop Python computational feasibility (`5.703 ms` mean / `9.964 ms` p99, `24.76 KB` float32 MLP weights), deploying onto ARM Cortex-A76 (RPi CM5 RT-PREEMPT) and ARM Cortex-M33 @ 250 MHz (STM32H563ZIT C99/FreeRTOS) requires static-allocation C99 code generation, float32 numerical verification of MEKF/RLS, and hardware-in-the-loop timing qualification as specified in [SIL_HIL_READINESS.md](file:///E:/Education/Master/Final_Project/codes/v2/docs/SIL_HIL_READINESS.md).

---

## 7. Reproducibility & Persisted Artifacts

- **`E003_ccr_v2_confirmatory` (Confirmatory Multi-Seed Campaign — Primary Reference):**
  - Manifest (`30,000` steps × `3` train seeds `42, 107, 211` × `10` eval seeds `100..109`, `18` policy hashes): [manifest.json](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/manifest.json)
  - 3-Metric failure & infeasibility breakdown: [failure_breakdown_heldout.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/failure_breakdown_heldout.csv)
  - Controllable-7 summary (`n = 70` classical / `210` learned): [summary_heldout_controllable.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/summary_heldout_controllable.csv)
  - All-9 held-out summary (`n = 90` classical / `270` learned): [summary_heldout_test.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/summary_heldout_test.csv)
  - Per-scenario breakdown (`S0–S8`): [summary_test_by_category.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/summary_test_by_category.csv)
  - Multi-seed reproducibility table (`train_seed in {42, 107, 211}`): [summary_controllable_by_train_seed.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/summary_controllable_by_train_seed.csv)
  - Paired statistical tests (`n_pairs = 70` controllable & `n_pairs = 90` all, with step-down Holm-Bonferroni `wilcoxon_p_holm`):
    - [paired_test_controllable_ablations_vs_A7.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/paired_test_controllable_ablations_vs_A7.csv)
    - [paired_test_controllable_vs_A3.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/paired_test_controllable_vs_A3.csv)
    - [paired_test_controllable_vs_A0.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/paired_test_controllable_vs_A0.csv)
    - [paired_test_ablations_vs_A7.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/paired_test_ablations_vs_A7.csv)
    - [paired_test_vs_A3.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/paired_test_vs_A3.csv)
    - [paired_test_vs_A0.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/paired_test_vs_A0.csv)
  - Desktop Python CPU profile: [cpu_profile.json](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/cpu_profile.json)
- **Stage 1–2 Invariant & Evaluation Test Suites:**
  - [test_stage1_invariants.py](file:///E:/Education/Master/Final_Project/codes/v2/tests/physics/test_stage1_invariants.py)
  - [test_phase9_10_eval_and_profiling.py](file:///E:/Education/Master/Final_Project/codes/v2/tests/regression/test_phase9_10_eval_and_profiling.py)
  - [test_igrf14_and_config_generality.py](file:///E:/Education/Master/Final_Project/codes/v2/tests/physics/test_igrf14_and_config_generality.py)
- **Stage 3 Basilisk `2.12.2` Gate C6 & 8-Regime Cross-Validation:**
  - Report: [PHASE_3_REPORT.md](file:///E:/Education/Master/Final_Project/codes/v2/docs/agent_reports/PHASE_3_REPORT.md)
  - Test suite: [test_phase3_basilisk.py](file:///E:/Education/Master/Final_Project/codes/v2/tests/integration/test_phase3_basilisk.py)
- **Frozen Pilot Campaigns (`E001` & `E002`):**
  - `E002` (IGRF-14 + RLS Fix + ESO-CCR v2 Single-Seed Pilot): [manifest.json](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E002_ccr_v2_igrf14_rlsfix/manifest.json), [summary_heldout_test.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E002_ccr_v2_igrf14_rlsfix/analysis/summary_heldout_test.csv), [paired_test_ablations_vs_A7.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E002_ccr_v2_igrf14_rlsfix/analysis/paired_test_ablations_vs_A7.csv), [paired_test_vs_A3.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E002_ccr_v2_igrf14_rlsfix/analysis/paired_test_vs_A3.csv), [cpu_profile.json](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E002_ccr_v2_igrf14_rlsfix/analysis/cpu_profile.json)
  - `E001` (Baseline Pilot): [manifest.json](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E001_ccr_v2_benchmark/manifest.json), [summary_heldout_test.csv](file:///E:/Education/Master/Final_Project/codes/v2/experiments/E001_ccr_v2_benchmark/analysis/summary_heldout_test.csv)
- **SIL/HIL Readiness Specification:** [SIL_HIL_READINESS.md](file:///E:/Education/Master/Final_Project/codes/v2/docs/SIL_HIL_READINESS.md)
