# Fault-Tolerant Attitude Control of Nanosatellites Using Reinforcement Learning (M.Sc. Thesis)

**Author:** Pouria Zarei (M.Sc. Control Engineering, University of Tehran)  
**Advisor:** Dr. Mohammad-Javad Yazdanpanah  
**Active Platform:** `codes/v2/` (`adcs-rl`, commit `ee67ba3`) — Capability-Informed, Uncertainty-Aware, Directionally Gated Residual Reinforcement Learning (**CCR v2**)

---

## 1. Repository Structure

| Path | Status | Description |
|---|---|---|
| [`codes/v2/`](codes/v2/) | **ACTIVE** | Validated **CCR v2** spacecraft ADCS research platform (`spacecraft_reference_001`, 100 kg, 4-wheel pyramid RW + 3-axis MTQ, 5 Hz control / 100 Hz RK4 `fast_rk4`, official degree-13 IAGA IGRF-14, 6-state MEKF, online RLS capability estimator, shared box-constrained `cap_alloc`, live Basilisk 2.12.2 cross-validation) |
| [`codes/v1/`](codes/v1/) | **ARCHIVED** | Initial prototype (`satellite_adcs`) and Phase A–D.3 audit scripts (`E-01..E-24`), preserved verbatim for historical provenance |
| [`docs/research/`](docs/research/) | **LIVING DOCS** | Authoritative research records: [`MASTER_ROADMAP.md`](docs/research/MASTER_ROADMAP.md), [`PROGRESS_LOG.md`](docs/research/PROGRESS_LOG.md), [`DECISIONS.md`](docs/research/DECISIONS.md), [`EXPERIMENT_REGISTRY.md`](docs/research/EXPERIMENT_REGISTRY.md), [`CLAIMS_TABLE.md`](docs/research/CLAIMS_TABLE.md), [`OPEN_QUESTIONS.md`](docs/research/OPEN_QUESTIONS.md) |
| [`papers/`](papers/) | **REFERENCE** | Literature corpus and survey references |
| [`reports/`](reports/) | **HISTORICAL** | Historical `v1` milestone reports (`report-state-1..3.md`) and checkpoint SHA-256 manifests |

### Key `codes/v2/` Documentation
- [`codes/v2/README.md`](codes/v2/README.md) — Package layout and quickstart
- [`codes/v2/CONTROL_ARCHITECTURE.md`](codes/v2/CONTROL_ARCHITECTURE.md) — CCR v2 law (`tau_cmd = tau_classical + rho * alpha * G * tau_rl`), `M3_UNKNOWN_INVALID_UNSAFE` supervisor latch, and `A3_strong_classical` (CARE LQR + gyro FF + 0.08 rad/s slew limiter + 3-axis nonlinear ESO/DOB + `cap_alloc` + observability schedule + MTQ unloading)
- [`codes/v2/RESEARCH_PROTOCOL.md`](codes/v2/RESEARCH_PROTOCOL.md) — Scenarios `S0..S8`, arms `A0..A7` + ablations, and statistical protocol
- [`codes/v2/docs/FINAL_RESEARCH_REPORT.md`](codes/v2/docs/FINAL_RESEARCH_REPORT.md) — Complete confirmatory `E003_ccr_v2_confirmatory` analysis
- [`codes/v2/docs/agent_reports/PHASE_3_REPORT.md`](codes/v2/docs/agent_reports/PHASE_3_REPORT.md) — Live Basilisk `2.12.2` 8-regime cross-validation report (`8/8` PASS)
- [`codes/v2/docs/SIL_HIL_READINESS.md`](codes/v2/docs/SIL_HIL_READINESS.md) — Static C99 interface boundary and desktop CPU profiling summary

---

## 2. Headline Confirmatory Results (`E003_ccr_v2_confirmatory`, Registry `E-29`)

Evaluated across **15 controller arms**, `30,000` SAC training steps × `3` independent training seeds (`42, 107, 211`, 18 trained policies) × `10` held-out test seeds (`100..109`) × `9` held-out scenarios (`S0..S8`) = **3,330 held-out test episodes** (`7` controllable scenarios → `n = 70` classical / `210` learned; `2` physically infeasible `S2, S3` → `n = 20` classical / `60` learned). Paired tests aggregate across the 3 training seeds per `(scenario_id, eval_seed)` (`n_pairs = 70` controllable / `90` all) with 5,000-sample bootstrap CIs and step-down Holm-Bonferroni correction (`wilcoxon_p_holm`).

| Controller Arm | Controllable-7 Mean (°) | Controllable-7 Median (IQR) (°) | Median Recovery (s) | Impulse (N·m·s) | Controllable-7 LoC (%) | S2/S3 Infeasibility Response (%) |
|---|---:|---:|---:|---:|---:|---:|
| `A7_ccr_v2_eso` | **0.2087** | 0.1518 (0.1124) | 12.80 | 1.6968 | **0.00%** (0/210) | **100.0%** (60/60) |
| `A3_strong_classical` | 0.2315 | 0.1306 (0.1261) | 12.40 | 1.6824 | **0.00%** (0/70) | 0.0% (0/20) |
| `Abl_A7_clean_trained` | 0.2780 | **0.0970** (0.0995) | **7.80** | 1.6643 | **0.00%** (0/210) | **100.0%** (60/60) |
| `A7_ccr_v2_full` | 0.3258 | 0.1288 (0.1192) | 11.40 | 1.6214 | **0.00%** (0/210) | **100.0%** (60/60) |
| `A4_unstructured_rl` | 0.8699 | 0.5667 (0.3689) | 4.40 | 2.7374 | 7.62% (16/210) | 0.0% (0/60) |
| `A6_rl_oracle_gate` | 0.6293 | 0.1216 (0.3040) | 9.70 | 1.7545 | 8.57% (18/210) | 100.0% (60/60) |
| `A0_classical_lqr` | 1.0637 | 0.1650 (2.1573) | 10.40 | 1.5032 | 12.86% (9/70) | 0.0% (0/20) |

- **All 4 CCR v2 ablations survive Holm-Bonferroni on Controllable-7 (`vs A7_ccr_v2_full`, `n_pairs = 70`):** `Abl_A7_no_rho` (`+0.2256°` mean / `+0.1729°` med diff, `p_Holm = 5.72e-08`), `Abl_A7_no_alpha` (`+0.1579°` mean / `+0.0354°` med diff, `p_Holm = 7.31e-06`), `Abl_A7_no_G` (`+0.0122°` med diff, `+46.5%` mean RL torque, `p_Holm = 0.00939`), and `Abl_A7_no_supervisor` (`+0.0301°` mean / `+0.0048°` med diff, `p_Holm = 0.01312`, S2/S3 infeasibility response `100% -> 0%`).
- **Clean-trained curriculum discovery:** `Abl_A7_clean_trained` significantly outperforms both `A7_ccr_v2_full` (`-0.0372°` med diff, `p_Holm = 3.05e-05`, `78.57%` wins) and `A3_strong_classical` (`-0.0326°` med diff, `p_Holm = 0.02453`, `71.43%` wins) on Controllable-7.

---

## 3. Verification & Test Suites

Run from `E:\Education\Master\Final_Project\codes\v2`:

```powershell
# 1. Static lint & core unit/physics/regression suite (Python 3.14.6) -> 47 passed, 2 skipped
python -m ruff check --no-cache src tests scripts
python -m pytest -v -p no:cacheprovider

# 2. Live Basilisk 2.12.2 8-regime cross-validation (Python 3.11 .venv_bsk) -> 5 passed, 0 failed (8/8 regimes PASS)
.venv_bsk\Scripts\python.exe -m pytest -v -p no:cacheprovider tests/integration/test_phase3_basilisk.py
```

---

## 4. Scientific Scope & Deferred Hardware Phases

1. **Deterministic residual-authority regulation (`C-12 FORBIDDEN`):** CCR v2 provides deterministic residual-authority regulation and conservative command filtering via `rho * alpha * G` and the `M3` supervisor latch; it does **not** claim a formal Lyapunov or CBF closed-loop stability proof.
2. **Statistical seed note (`D-10 / D-17`):** `E003` used `n_train = 3` independent training seeds (`42, 107, 211`), below `D-10`'s 5-seed pure sign-test floor, mitigated by policy-averaged paired scenario-seed tests (`n_pairs = 70 / 90`) with 5,000-sample paired bootstrap CIs and step-down Holm-Bonferroni correction.
3. **Embedded C99 / HIL deferred (`C-15 FORBIDDEN`):** Desktop Python CPU timing (`5.703 ms` mean / `9.964 ms` p99 total onboard per `200 ms` `5 Hz` step; `0.045 ms` mean / `0.106 ms` p99 for `30->64->64->3` NumPy MLP inference, `24.76 KB` `float32`) verifies desktop host Python feasibility only. Target C99 / SIL / HIL implementation on **Raspberry Pi CM5** and **STM32H563ZIT** is deferred to subsequent hardware phases.
