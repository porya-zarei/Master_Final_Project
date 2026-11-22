# Phase 9 Report — Research Evaluation and Monte Carlo

**Phase:** 9 — Research Evaluation and Monte Carlo  
**Status:** `COMPLETE`  
**Date:** 2026-11-21  

---

## 1. Experiment Summary (`E001_ccr_v2_benchmark`)

- **Command run:** `python scripts/run_phase9_10_experiments.py --out-dir ".../scratch/E001_ccr_v2_benchmark" --train-steps 12000 --n-seeds 6 --workers 12 --train-seed 42`
- **Training:** 5 distinct SAC residual policies (`A4_unstructured_rl`, `A5_rl_need_rho`, `A6_rl_oracle_gate`, `A7_ccr_v2_full`, `A7_clean_trained`), `12,000` steps each (`30` randomized episodes strictly from the disjoint training region), parallelized across 5 workers (`165–171 s` each).
- **Paired Monte Carlo evaluation:** `1,260` total episodes (`14` arms × `15` validation & held-out test scenarios across `S0–S8` × `6` paired seeds `100–105`), completed in `702.2 s`.
  - Held-out test split: `9` unseen fault scenarios (`S0–S8`) × `6` seeds = **`54` paired held-out episodes per arm**.
- **Generated artifacts:**
  - Machine-readable summaries, paired bootstrap CIs (`n_boot = 5000`), Cohen's $d_z$, Wilcoxon $p$-values, and `manifest.json` persisted to `experiments/E001_ccr_v2_benchmark/`.
  - All 12 required protocol plots (`01` through `12`) generated and visually verified in `C:\Users\ASUS\.gemini\antigravity-cli\brain\65affd91-4f5b-41ee-b6bc-1a64c8142955\scratch\E001_ccr_v2_benchmark\plots\`.

---

## 2. Key Verified Findings (Held-Out Test Split, N = 54 Pairs/Arm)

| Arm | Mean RMS (deg) | Median RMS (deg) | LoC Rate (%) | Controllable LoC (7 sc.) | Median Recov. (s) | Mean RW Effort (N·m·s) | Mean RL Torque (N·m) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `A0_classical_lqr` | 21.584 | 0.284 | 29.6% | 9.5% (4/42) | 9.1 | 2.961 | 0.0000 |
| `A1_classical_oracle_alloc` *(oracle)* | 21.124 | 0.128 | 25.9% | 4.8% (2/42) | 10.1 | 2.961 | 0.0000 |
| `A2_classical_dob_eso` | 21.443 | 0.188 | 22.2% | **0.0%** (0/42) | 9.6 | 2.943 | 0.0000 |
| `A3_strong_classical` | 21.388 | 0.169 | 22.2% | **0.0%** (0/42) | 11.1 | 3.053 | 0.0000 |
| `A4_unstructured_rl` | 24.898 | 3.529 | 33.3% | 14.3% (6/42) | 12.9 | 3.425 | 0.0346 |
| `A5_rl_need_rho` | 25.639 | 4.072 | 42.6% | 26.2% (11/42) | 30.0 | 3.567 | 0.0335 |
| `A6_rl_oracle_gate` *(oracle)* | 22.336 | 0.656 | 35.2% | 16.7% (7/42) | 17.3 | 3.002 | 0.0168 |
| **`A7_ccr_v2_full`** | **21.197** | **0.159** | **22.2%** | **0.0%** (0/42) | 11.4 | 3.070 | 0.0029 |
| `Abl_A7_no_G` | 21.025 | 0.242 | 22.2% | 0.0% | 13.2 | 3.097 | 0.0071 |
| `Abl_A7_no_alpha` | 20.973 | 0.372 | 22.2% | 0.0% | 15.8 | 3.174 | 0.0104 |
| `Abl_A7_no_rho` | 21.219 | 0.169 | 22.2% | 0.0% | 11.4 | 3.085 | 0.0031 |
| `Abl_A7_no_supervisor` | 21.142 | 0.171 | 22.2% | 0.0% | 11.8 | 3.042 | 0.0040 |
| `Abl_A7_geom_G` | 21.071 | 0.168 | 22.2% | 0.0% | 11.8 | 3.166 | 0.0027 |
| `Abl_A7_clean_trained` | 20.891 | 0.139 | 22.2% | 0.0% | 9.8 | 3.096 | 0.0029 |

- **Physical infeasibility separated cleanly:** All 12/54 (`22.2%`) failures for `A2`, `A3`, and `A7` occur exclusively in `S2_rw1_stuck_torque_test` (+0.04 N·m stuck torque vs. `< 8e-5` N·m MTQ authority) and `S3_momentum_sat_test` (wheels saturated in 15 s under persistent 0.02 N·m disturbance). Every controllable fault scenario (`S0, S1, S4, S5, S6, S7, S8`) has **`0%` LoC** for `A2`, `A3`, and `A7`.
- **Full scientific interpretation & limitations** are documented in `docs/FINAL_RESEARCH_REPORT.md`.

---

## 3. Verification Commands & Outcomes

- `python -m ruff check --no-cache src tests scripts` → `All checks passed!`
- `python scripts/run_phase9_10_experiments.py ...` → Exit code `0`, `1,260` episodes + `12` plots + `cpu_profile.json` + `manifest.json`.
- `python -m pytest -v -p no:cacheprovider tests/regression/test_phase9_10_eval_and_profiling.py` → **2 passed, 0 failed**.

---

## 4. Follow-Up Benchmark Addendum (`E002_ccr_v2_igrf14_rlsfix`, 2026-11-22)

- **Upgrades included:** Official degree-13 IGRF-14 (`configs/igrf14coeffs.txt`), directional RLS forgetting fix in `OnlineCapabilityEstimator`, config-general spacecraft scaling (`--spacecraft-config`), new `A7_ccr_v2_eso` arm (`15` arms total, `1,350` paired episodes, `15,000` SAC steps).
- **Verified ablation significance vs `A7_ccr_v2_full` (all 95% CIs strictly > 0 for `rho`, `alpha`, `G`):**
  - `Abl_A7_no_rho`: `+0.199°`, CI `[+0.112°, +0.286°]`, $p = 2.4\times 10^{-7}$ (`A7` wins `88.9%`).
  - `Abl_A7_no_alpha`: `+1.281°`, CI `[+0.512°, +2.221°]`, $p = 1.7\times 10^{-5}$ (`A7` wins `77.8%`).
  - `Abl_A7_no_G`: `+1.270°`, CI `[+0.089°, +3.199°]`, $p = 1.5\times 10^{-5}$ (`A7` wins `83.3%`).
  - `Abl_A7_no_supervisor`: `+0.062°`, $p = 5.3\times 10^{-4}$ (`A7` wins `74.1%`).
- **`S4` torque-bias gap closed:** `A7_ccr_v2_eso` achieved `0.422°` mean RMS (`1.66 N·m·s`) on `S4_rw_bias_stiction_test` vs `A3_strong_classical` (`0.525°`, `1.79 N·m·s`) and `A7_ccr_v2_full` (`1.856°`).
- **Persisted summaries:** `experiments/E002_ccr_v2_igrf14_rlsfix/`.
