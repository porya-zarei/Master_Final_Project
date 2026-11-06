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

## Rules

- A number may be quoted only if its row here reads `VALID` or `PARTIAL` **with** the caveat.
- A `RETRACTED` row stays in the table forever; the retraction is the record.
- New experiments are appended with their script, artifact path, n and status **before** the number is
  used in any report.
