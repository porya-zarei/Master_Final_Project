# EXPERIMENT_REGISTRY — every experiment, its artifact, and whether it may be quoted

**Status vocabulary:** `VALID` may be quoted · `RETRACTED` must not be quoted (reason given) ·
`PARTIAL` usable with the stated caveat · `ANALYTICAL` derivation, no experiment run.

Repo facts at creation: branch `residual-rl`, HEAD `c9a4aa5`, 72 tracked Python files, 37 scripts,
54 result directories, 29/29 tests passing.

## Classical / infrastructure

| id | experiment | script | artifact | n | status |
|---|---|---|---|---|---|
| E-01 | Frame-convention audit (`C_BN` semantics) | `audit_frame_convention.py` | `reports/frame_audit_output.txt` | 12 tests | **VALID** — 12/12, cross-checked against scipy |
| E-02 | Classical baseline regeneration (post time-axis fix) | `c1_regeneration.py` | `results/c1_regeneration/`, `results/c1_rerun.log` | 60 | **VALID** — 88.3 %, median settle 77.2 s, 0.733 deg |
| E-03 | MEKF with gyro-bias estimation (C2-e) | in `tests/test_estimation.py` + probe | — | 3 tests | **VALID** — bias convergence 3.8e-6 |
| E-04 | Actuator-nonlinearity benchmark | `milestone_c_classical_benchmark.py` | `reports/milestone_c_classical_benchmark.json` | 6 paired | **VALID** — Coulomb 0 % success; the decisive lever |
| E-05 | Coulomb magnitude sweep | `milestone_c2_coulomb_sweep.py` | `reports/milestone_c_classical_benchmark.json` | 16 × 4 levels | **VALID** — monotonic; 0/16 at ≥2e-4; threshold ≈1.5e-4 |
| E-06 | Reward attribution study (C4.1) | `c4_1_attribution.py` | `results/c4_1/` | per arm | **VALID** — budget ∧ tolerance bonus ∧ normalisation-off |
| E-07 | Reward-shape study (C4.2) | `c4_2_reward_study.py` | `results/c4_2/` | per arm | **VALID** — `log` chosen |

## Lever closure (the reason training was not spent)

| id | experiment | script | artifact | status |
|---|---|---|---|---|
| E-08 | L1 oracle vs estimated health | `m1_oracle_vs_hat.py` | `reports/m1_oracle_vs_hat.json` | **VALID — L1 CLOSED** |
| E-09 | L3 inertia mismatch ±20 % | `l3_inertia_mismatch.py` | `reports/l3_inertia_mismatch.json` | **VALID — L3 CLOSED** |
| E-10 | L4 time-optimal headroom + bang-bang gate | `l4_time_optimal_headroom.py`, `l4_bangbang_gate.py` | `reports/l4_headroom.json`, `reports/l4_bangbang_gate.json` | **VALID** — 2.71×, 1.25× the bound |

## Residual RL

| id | experiment | artifact | status |
|---|---|---|---|
| E-11 | D2 residual SAC, quadratic reward | `reports/d2_residual_vs_lqr.json` | **RETRACTED as a performance claim** — reward had no gradient in the band (2.4 units vs 1400 acquisition cost). Valid as a reward-geometry finding. |
| E-12 | D3 residual SAC, `tol_norm` | `reports/d3_residual_vs_lqr.json` | **RETRACTED** — far-field scale ~1e6, ill-conditioned critic |
| E-13 | **D4** residual SAC, `log` + friction `U(0,3e-4)`, 3 seeds | `reports/d4_residual_vs_lqr.json`; checkpoints `results/residual_d4_s{0,1,2}/` (889 KB each) | **PARTIAL** — the Coulomb advantage (6–8/12 vs 0/12) and the nominal cost are real; the `p < 0.001` is **RETRACTED** (D-05, unit of analysis). Checkpoints only on disk, SHA-256 in `reports/m1_checkpoint_hashes.json`. |
| E-14 | Checkpoint hashes | `reports/m1_checkpoint_hashes.json` | **VALID** — makes the untracked policies identifiable |

## Audit trail M1–M3.4

| id | experiment | script | artifact | status |
|---|---|---|---|---|
| E-15 | M1-A signal audit — the correct wheel residual | `m1a_signal_audit.py` | `results/m1/m1a_signal_audit.json` (+ 492 KB timeseries) | **VALID** — `tau_f = tau_cmd + J_w dw/dt` to 5e-18; **retracts D5's "excitation limit"** |
| E-16 | M1-B D4 statistics re-analysis | `m1b_d4_statistics.py` | `reports/m1b_d4_statistics.json` | **VALID** — produces the D-05 retraction |
| E-17 | M1-C LQR path parity | `m1c_lqr_path_parity.py` | `reports/m1c_lqr_parity.json` | **FAIL by design** — the discrepancy it found produced D-02 |
| E-18 | M2 classical baselines (B1/B2/B3) | `m2_classical_baselines.py` | `reports/m2_classical_baselines.json` | **PARTIAL** — B2's "win" (100 %/0.366 deg) is **RETRACTED**: `h_hat → [0,0,0]` saturated every wheel; floor sweep 0.366 → 0.920 → 1.386 |
| E-19 | M3 joint `(h, tau_f)` estimator validation | `m3_fault_injection_validation.py` | `results/m3/fault_injection_validation.json` | **VALID** — `h` and `tau_f` both exact under verified injection |
| E-20 | **M3.3-B state-aware allocation grid** | `m33b_state_aware_allocation.py` | `results/m33b/run.json` (576 episodes), 24 episode files, 6 timeseries, `reports/m33b_state_aware_allocation.json`, `docs/research/M33B_allocation_report.md` | **VALID** — 8 scenarios × 3 arms × 24 seeds, 12.7 min. Result: estimator-driven arm bit-identical to no-knowledge in 192/192 cells; 0 DEGRADED wheel-steps |
| E-21 | Patch bit-identity (pre/post `simulate.py` hooks) | inline capture | `reports/m33b_parity_pre_post.json` | **VALID** — max abs diff 0.0e+00 |
| E-22 | M3.4 RLS uncertainty audit | none (analytical + recomputation on E-20 traces) | `docs/research/M34_RLS_uncertainty_audit.md` | **ANALYTICAL** — no new experiment |

## Phase B

| id | experiment | script | artifact | status |
|---|---|---|---|---|
| E-23 | **B.0 checkpoint-reusability gate** — D4 policies: hash match, wrapper-vs-classical controller identity, 15-dim observation reconstruction, command-level equivalence over 40 perturbed states, SB3 load test | `scripts/b0_checkpoint_reuse.py` | `results/b0/b0_checkpoint_reuse.json`, `reports/b0_checkpoint_reuse.json` | **VALID** — command equivalence **0.000e+00**; hashes match; `K` identical (0.000e+00); all 3 policies load. Verdict: re-evaluable for h = 1 cells only (D-13). A *trajectory* comparison is meaningless here — the harnesses draw their own orbit/noise (7.6 km apart at t=1 s) |
| E-24 | **B.1 classical pass** — 5 conditions × {C1 oracle LQR, C2 gain-scheduled} × n=24, 900 s, both holds | `scripts/b1_residual_vs_classical.py` | `results/b1/run.json` (240 rows), `results/b1/episodes/`, `reports/b1_residual_vs_classical.json` | **PARTIAL** — classical arms only; no RL arm scored yet, so the B.4 verdicts are not evaluable. Cross-check: reproduces the M3.3-B oracle cells **exactly** (S0 0.243, S2 1.570/8.3 %, S4 1.570/8.3 %, S6 91.342, S7 0.243) |

## CCR v2 Platform & Confirmatory Benchmark (`codes/v2`)

*(Note: `E-01..E-24` above live under the archived `codes/v1/` tree; `E-25..E-29` below live under `codes/v2/` at commit `ee67ba3`.)*

| id | experiment | script | artifact | n | status |
|---|---|---|---|---|---|
| E-25 | **`E001_ccr_v2_benchmark` (Pilot 1)** — 14 arms, 12,000 SAC steps × 1 train seed (`42`) × 6 test seeds × 9 scenarios (`S0..S8`) | `codes/v2/scripts/run_phase9_10_experiments.py` | `codes/v2/experiments/E001_ccr_v2_benchmark/analysis/` (`summary_heldout_test.csv`, `cpu_profile.json`) | 756 test / 1,260 total ep | **PARTIAL (Pilot — superseded by E-29)** — single training seed (`42`), dipole-IGRF placeholder, pre-fix RLS covariance and pre-normalization infeasibility metric. Retained frozen for pipeline provenance |
| E-26 | **`E002_ccr_v2_igrf14_rlsfix` (Pilot 2)** — 15 arms (adds `A7_ccr_v2_eso`), 15,000 SAC steps × 1 train seed (`42`) × 6 test seeds × 9 scenarios (`S0..S8`), degree-13 IGRF-14 + RLS directional forgetting | `codes/v2/scripts/run_phase9_10_experiments.py` | `codes/v2/experiments/E002_ccr_v2_igrf14_rlsfix/analysis/` (`summary_heldout_test.csv`, `paired_test_vs_A3.csv`, `paired_test_ablations_vs_A7.csv`, `cpu_profile.json`) | 810 test / 1,350 total ep | **PARTIAL (Pilot — superseded by E-29)** — single training seed (`42`); validated IGRF-14 + RLS directional-forgetting + ESO integration prior to multi-seed confirmatory run |
| E-27 | **Live Basilisk `2.12.2` 8-regime cross-validation matrix** — open-loop (`R1, R4, R6, R8`) and closed-loop (`R2, R3, R5, R7`) parity between `fast_rk4` and `BasiliskBackend` (`spacecraft_reference_001`, Python 3.11 `.venv_bsk`) | `codes/v2/tests/integration/test_phase3_basilisk.py` | `codes/v2/docs/agent_reports/PHASE_3_REPORT.md` | 5 pytest tests covering 8 regimes (`R1..R8`) | **VALID** — **5 passed, 0 failed (`8/8` regimes PASS)**: open-loop (`R1` 10 s: `9.313e-09 m` / `9.31 nm` pos, `0.0086 deg` att, `8.39 nT` B-field; `R4` sat `0.0682 deg`; `R6` MTQ sat `tau·B ~ 1.995e-14`; `R8` 600 s: `0.197 um` pos, `0.2870 deg` att) + closed-loop (`R2` 90° slew `0.6744 deg` / diff `0.0000 deg`; `R3` 10°/s detumble `0.4241 vs 0.4211 deg` / diff `0.0225 deg`; `R5` RW0 50%+0.015 N·m `0.1062 vs 0.1047 deg` / diff `0.0260 deg`; `R7` 20 s ST dropout `0.0938 vs 0.1014 deg` / diff `0.0105 deg`) |
| E-28 | **Stage 1–4 physics, estimator, zero-oracle-leakage, and evaluation invariant test suites** (`codes/v2` commit `ee67ba3`, Python 3.14.6) | `pytest` & `ruff` across `codes/v2/src`, `codes/v2/tests`, `codes/v2/scripts` | `codes/v2/tests/physics/test_stage1_invariants.py`, `codes/v2/tests/regression/test_phase9_10_eval_and_profiling.py` | 49 tests (`47 passed, 2 skipped`), `ruff` 0 errors | **VALID** — verifies momentum conservation, frame semantics, zero oracle `h_true` leakage into deployed controllers, RLS `S4` additive bias-vs-gain separation & unexcited confidence cap `<= 0.85`, MEKF discrete `Q_d` scaling & post-dropout reset, and 3-metric infeasibility breakdown |
| E-29 | **`E003_ccr_v2_confirmatory` (Multi-seed confirmatory benchmark & desktop Python CPU profile)** — 15 arms, 30,000 SAC steps × 3 independent train seeds (`42, 107, 211`, 18 policies) × 10 held-out test seeds (`100..109`) × 9 scenarios (`S0..S8`) | `codes/v2/scripts/run_phase9_10_experiments.py` | `codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/` (`summary_heldout_controllable.csv`, `summary_heldout_test.csv`, `summary_test_by_category.csv`, `summary_controllable_by_train_seed.csv`, `failure_breakdown_heldout.csv`, `paired_test_controllable_ablations_vs_A7.csv`, `paired_test_controllable_vs_A3.csv`, `paired_test_controllable_vs_A0.csv`, `paired_test_ablations_vs_A7.csv`, `paired_test_vs_A3.csv`, `paired_test_vs_A0.csv`, `cpu_profile.json`), `codes/v2/docs/FINAL_RESEARCH_REPORT.md` | 3,330 held-out test episodes (`n_pairs = 70` controllable / `90` all; 500 CPU cycles) | **VALID (with explicit caveats `D-17, D-18`)** — `A7_ccr_v2_full`, `A7_ccr_v2_eso`, and `Abl_A7_clean_trained` achieve **0.00% Controllable-7 LoC (`0/210`)** and **100.0% S2/S3 infeasibility response (`60/60`)**. `A7_ccr_v2_eso` lowest Controllable-7 mean (`0.2087°` vs `A3` `0.2315°`); `Abl_A7_clean_trained` lowest Controllable-7 median (`0.0970°`, beating `A7_ccr_v2_full` `p_Holm = 3.05e-05` and `A3` `p_Holm = 0.02453`). All 4 CCR v2 ablations survive Holm-Bonferroni on Controllable-7 (`Abl_A7_no_rho` `p_Holm = 5.72e-08`, `Abl_A7_no_alpha` `p_Holm = 7.31e-06`, `Abl_A7_no_G` `p_Holm = 0.00939`, `Abl_A7_no_supervisor` `p_Holm = 0.01312`). Desktop Python CPU timing: `5.703 ms` mean / `9.964 ms` p99 onboard (`0.045 ms` / `0.106 ms` p99 `B6` MLP). *Caveats:* (1) `n_train = 3 < 5` training seeds (mitigated via policy-averaged paired scenario-seed tests `n_pairs = 70/90` + 5,000-sample bootstrap CIs); (2) desktop Python timing verifies host Python feasibility only, not embedded C99/HIL real-time qualification (`C-15 FORBIDDEN`) |

## Rules

- A number may be quoted only if its row here reads `VALID` or `PARTIAL` **with** the caveat.
- A `RETRACTED` row stays in the table forever; the retraction is the record.
- New experiments are appended with their script, artifact path, n and status **before** the number is
  used in any report.
