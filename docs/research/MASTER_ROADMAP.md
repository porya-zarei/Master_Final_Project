# MASTER_ROADMAP — execution authority

**Last updated:** 2026-11-22 (CCR v2 platform complete at `codes/v2` commit `ee67ba3`, `codes/v1` archived, merged to `master`)  
**Originally authoritative from:** 2026-11-06  
**Repository:** `E:\Education\Master\Final_Project` · branch `residual-rl` → `master`  
**Thesis:** *Fault-Tolerant Attitude Control of Nanosatellites Using Reinforcement Learning: From
Simulation to Hardware-in-the-Loop Implementation.*

---

## Current State (2026-11-22) — `codes/v2` CCR v2 Complete & Merged to `master`

### 1. Platform Consolidation (`D-15..D-19`)
- **`v1` Archival (`D-15`):** All historical `v1` code and scripts (`codes/satellite_adcs/`, `codes/scripts/`, `codes/tests/`, `codes/simulation/`) were moved verbatim into [`codes/v1/`](../../codes/v1/). All historical `v1` experiments (`E-01..E-24`), retractions, and errata remain preserved in this folder.
- **Active `v2` Platform (`D-15, D-16`):** [`codes/v2/`](../../codes/v2/) (`adcs-rl`, commit `ee67ba3`) is the authoritative thesis codebase implementing **Capability-Informed, Uncertainty-Aware, Directionally Gated Residual Reinforcement Learning (CCR v2)** on reference plant `spacecraft_reference_001`:
  - **Plant & Environment:** 100 kg spacecraft, 4-wheel pyramid reaction wheel cluster + 3-axis magnetorquers (MTQ), `5 Hz` control cycle (`200 ms` period), `100 Hz` RK4 plant integration (`fast_rk4`), official degree-13 IAGA **IGRF-14** geomagnetic field, gravity gradient, aerodynamic drag, SRP, and residual magnetic dipole disturbances.
  - **Estimation & Capability (`B1, B3`):** 6-state MEKF with discrete `Q_d` scaling and post-dropout covariance reset; online RLS capability estimator with directional forgetting, `S4` additive bias-vs-gain separation, `unverified_unexcited` flag, and unexcited confidence cap `<= 0.85`; shared box-constrained `cap_alloc` (`B9`) across `A4..A7` and all `Abl_A7_*` arms (zero oracle `h_true` leakage).
  - **CCR v2 Control Law & Strong Classical Baseline (`B4..B8`):** `tau_cmd = tau_classical + rho * alpha * G * tau_rl` separating intervention need (`rho`, with tachometer noise floor and attitude/rate deadzones forcing nominal `S0` mean `||tau_rl_gated|| < 1e-4 N*m`), trust (`alpha`), directional capability (`G`), and deterministic safety supervisor (`M3_UNKNOWN_INVALID_UNSAFE` latch setting `rl_permitted = False` / `tau_rl_gated = 0` under star-tracker dropout or persistent `authority_infeasible`). Evaluated against `A3_strong_classical` (CARE LQR + gyro feedforward + `0.08 rad/s` slew limiter + 3-axis nonlinear ESO/DOB + `cap_alloc` + observability gain schedule + MTQ assist/unloading).

### 2. Completed Verification & Experimental Gates (`[DONE]`)

| Gate / ID | Milestone | Evidence & Verified Result | Status |
|---|---|---|---|
| **Stage 1–4 (`E-28`)** | Physics invariants, zero-oracle-leakage, RLS/MEKF fixes, infeasibility metrics, test & lint suite | `python -m ruff check --no-cache src tests scripts` → **All checks passed!**; `python -m pytest -v -p no:cacheprovider` (Python 3.14.6) → **47 passed, 2 skipped** | `[DONE]` |
| **Phase 3 (`E-27`)** | Live **Basilisk `2.12.2`** 8-regime independent truth cross-validation (`test_phase3_basilisk.py`, Python 3.11 `.venv_bsk`) | **5 passed, 0 failed (`8/8` regimes PASS)**: Open-loop (`R1` 10 s: `9.313e-09 m` / `9.31 nm` pos, `0.0086 deg` att, `8.39 nT` B-field; `R4` sat `0.0682 deg`; `R6` MTQ sat `tau·B ~ 1.995e-14`; `R8` 600 s: `0.197 um` pos, `0.2870 deg` att) + Closed-loop (`R2` 90° slew `0.6744 deg` / diff `0.0000 deg`; `R3` 10°/s detumble `0.4241 vs 0.4211 deg` / diff `0.0225 deg`; `R5` RW0 50%+0.015 N·m `0.1062 vs 0.1047 deg` / diff `0.0260 deg`; `R7` 20 s ST dropout `0.0938 vs 0.1014 deg` / diff `0.0105 deg`) | `[DONE]` |
| **Pilots (`E-25, E-26`)** | Frozen pilot benchmarks `E001_ccr_v2_benchmark` (756 test ep) & `E002_ccr_v2_igrf14_rlsfix` (810 test ep) | Architecture iteration, IGRF-14 + RLS directional-forgetting validation; preserved as frozen single-seed pilots (`PARTIAL`), superseded for thesis claims by `E003` | `[DONE]` |
| **Confirmatory (`E-29`)** | **`E003_ccr_v2_confirmatory`** (15 arms × 30k SAC steps × 3 train seeds `42, 107, 211` × 10 test seeds `100..109` × 9 scenarios `S0..S8` = **3,330 held-out test episodes**, `n_pairs = 70 / 90`, 5,000-sample bootstrap CI + Holm-Bonferroni) | • **0.00% Controllable-7 LoC (`0/210`)** & **100.0% S2/S3 infeasibility response (`60/60`)** for `A7_ccr_v2_full`, `A7_ccr_v2_eso`, and `Abl_A7_clean_trained` (vs `A0` 12.86%, `A4` 7.62% / 0% infeas, `A6` 8.57%).<br>• `A7_ccr_v2_eso` achieves lowest Controllable-7 mean (**`0.2087°`** vs `A3` `0.2315°`, beating `A3` on `S4` `0.3818° vs 0.4904°` and `S8` `0.2934° vs 0.4037°`).<br>• `Abl_A7_clean_trained` achieves lowest Controllable-7 median (**`0.0970°`**, `7.80 s` recovery), significantly beating `A7_ccr_v2_full` (`-0.0372°`, `p_Holm = 3.05e-05`) and `A3_strong_classical` (`-0.0326°`, `p_Holm = 0.02453`).<br>• **All 4 CCR v2 ablations survive Holm-Bonferroni on Controllable-7 (`n_pairs = 70`):** `Abl_A7_no_rho` (`p_Holm = 5.72e-08`), `Abl_A7_no_alpha` (`p_Holm = 7.31e-06`), `Abl_A7_no_G` (`p_Holm = 0.00939`), `Abl_A7_no_supervisor` (`p_Holm = 0.01312`).<br>• **Desktop Python CPU profile:** `5.703 ms` mean / `9.964 ms` p99 total onboard (`2.851%` / `4.982%` of 200 ms cycle); `B6` MLP (`30->64->64->3`, `6,339` params, `24.76 KB` float32) `0.045 ms` mean / `0.106 ms` p99. | `[DONE]` |

### 3. Next Steps & Remaining Authorization Gates
1. **Phase F — Thesis Assembly (`[AUTH]`):** Integrate `E-27..E-29` tables, plots (`codes/v2/experiments/E003_ccr_v2_confirmatory/analysis/`), and `CLAIMS_TABLE.md` (`C-01..C-23`) into the M.Sc. thesis chapters, explicitly stating the `n_train = 3 < 5` training-seed limitation (`D-10, D-17`) and strict claim boundaries (`D-18`).
2. **Optional Follow-Up Experiment (`[PLANNED]`, `Q-14`):** Evaluate `A7_ccr_v2_eso_clean_trained` (combining the 3-axis nonlinear ESO backbone of `A7_ccr_v2_eso` with the clean training curriculum of `Abl_A7_clean_trained`) across `>= 5` independent training seeds to close `S4` bias error (`1.2567° -> ~0.38°`) and satisfy `D-10`'s 5-seed sign-test floor.
3. **Target C99 / SIL / HIL Implementation on Raspberry Pi CM5 & STM32H563ZIT (`[NEEDS-APPROVAL]`, `Q-15`):** Cross-compilation of static C99 onboard blocks (`B1..B9`), `float32` precision verification, DWT hardware WCET profiling, and processor-in-the-loop / HIL validation on **Raspberry Pi CM5** and **STM32H563ZIT** remain deferred until explicit researcher approval. Until completed, **`C-12` (formal stability guarantee) and `C-15` (HIL validation) remain strictly `FORBIDDEN`**.

---

## Historical `v1` Execution Roadmap Record (2026-11-06, Archived under `codes/v1/`)

> *Preserved verbatim below for historical provenance. The `v1` phases below reference the archived `codes/v1/` tree prior to the `codes/v2` CCR v2 platform.*

## Document authority

| document | status |
|---|---|
| **this file** | **AUTHORITATIVE** for execution, scope and authorisation |
| `docs/research/IMPROVED_RESEARCH_ROADMAP.md` | **historical for M1–M3** (all executed); its M4–M9 are folded into B–F below. Not an execution authority. |
| `docs/research/M34_RLS_uncertainty_audit.md` | authoritative **for the estimator question only** |
| `docs/research/M33B_allocation_report.md` | generated evidence; carries a durable errata banner |
| `docs/PhaseC_to_F_Master_Plan.md`, `docs/PhaseD5_to_F_Plan.md`, `docs/PhaseC_*_Plan.md` | **historical** (superseded scope). Retained for provenance, never implemented from. |
| `docs/Milestone_A_Audit.md`, `docs/Milestone_B_Actuator_Model.md` | historical, numbers still cited |

## Authorisation legend

`[DONE]` executed with evidence · `[AUTH]` authorised now, may run · `[GATE]` blocking, needs a decision ·
`[NEEDS-APPROVAL]` prepared, must not start without an explicit researcher GO · `[PLANNED]` described only

**Current authorisation (updated 2026-11-06 by D-12):** Phases **A, B, C, D are `[AUTH]`**. Phase **E is
`[AUTH]` for E-1 (MIL), E-2 (SIL) and E-3 (embedded profile, host-side only)** — in that order, and only
after the architecture-freeze gate — while **E-4 (HIL) remains `[NEEDS-APPROVAL]`**. Phase **F is
`[PLANNED]`**.

**The four Phase-E approval questions are answered for this run (D-12 / S-2):**
(1) MIL/SIL target = **pure software on this PC + a second process**, no real-time target until HIL;
(2) HIL hardware **undecided** — a proposal with a bill of materials is produced at the HIL gate;
(3) timebox **MIL + SIL ≈ 4 weeks**, HIL a later stage;
(4) MIL-1 language = **C99 core**, no dynamic allocation, no libc beyond `math.h`, with the Python
implementation as the reference oracle.

## Scope decision recorded this session

**HIL stays in the thesis title and returns to scope, scheduled strictly last.** Commit `1967326`
("Scope: MIL and SIL only — HIL deferred indefinitely") is **superseded on scheduling** by this
document: MIL → SIL → embedded profiling → HIL, in that order, with HIL beginning only after MIL and SIL
are complete and a validated model exists. The *claims* restriction from `1967326` remains in force until
real hardware experiments exist: **no hardware, real-time or flight-readiness claim may be made from
MIL/SIL evidence.** Recorded in `DECISIONS.md` as D-07.

---

## Phase A — Foundation `[AUTH]` (in progress)

| id | task | acceptance |
|---|---|---|
| A1 | Estimator-ceiling documentation | **done** — Addendum A1 in `M34_RLS_uncertainty_audit.md`, append-only (736 original lines byte-identical) |
| A2 | Dated errata pointer on M3.3-B | **done** — emitted by the report *generator*, so regeneration cannot lose it; report regenerated with 8 added lines, 0 removed |
| A3 | Living documentation (this file + `DECISIONS`, `EXPERIMENT_REGISTRY`, `OPEN_QUESTIONS`, `PROGRESS_LOG`) | five files, synchronised with repo state |
| A4 | Strongest reproducible baseline pinned | **done** — nominal LQR + **oracle** allocation; M3.3-B grid, n=24, 576 episodes |
| A5 | Test suite green | 29/29 before and after the phase |

**Exit:** all five documents exist, tests green, tree committed and pushed, and the ceiling argument
(0.04–0.06 deg multiplicative, structurally 0 additive) is recorded as the justification for B before C.

---

## Phase B — The central research question `[AUTH]`

> **Does residual reinforcement learning genuinely improve fault-tolerant attitude control over a strong
> classical controller, under reaction-wheel Coulomb friction?**

### B.0 Feasibility gate — are the D4 checkpoints validly re-evaluable? (~1 h, no compute beyond loading)

D4's policies were trained inside `ResidualADCSEnv` (15-dim obs = base 9 + `tau_LQR` 3 + previous action
3). The residual now executes **inside** the classical loop via `residual_fn`, and M1-C showed the
wrapper's nominal gain had been wrong. Therefore:

- reconstruct the 15-dim observation from the `residual_fn` payload;
- assert it matches the wrapper's construction on identical states to < 1e-9;
- assert the nominal `K` equals `ADCSController(...).K`;
- **falsification:** if either assertion fails, **retrain** — do not loosen the adapter to force a match.

Outcome decides B's cost: **re-evaluate (≈1 h)** vs **retrain (≈3–4 h of your machine time)**.

### B.1 Arms (one loop, one allocator, one fault path — `simulate.run_episode`)

| arm | controller | allocation | role |
|---|---|---|---|
| **C1** | nominal LQR (phase manager) | **oracle** | strongest fair classical baseline |
| C2 | LQR | gain-scheduled (existing) | second classical variant; must not be a straw man |
| **R1** | residual SAC, seeds 0–4 | oracle | the claim |
| R2 | residual PPO, seeds 0–4 | oracle | algorithm challenger (also feeds D.1) |

Absolute-action (non-residual) RL is **excluded** as primary: it must relearn allocation, limits and
geometry, and was rejected in the audit's architecture review.

### B.2 Conditions (identical ids to M3.3-B for comparability)

`S0` nominal · `S2` Coulomb 2e-4 · `S4` rw1@50 % + Coulomb 2e-4 · `S6` rw1 dead · `S7` rw1@50 % mid-flight.

### B.3 Metrics (both holds always; never one)

`success@10 s`, `success@30 s` (1° threshold) · final pointing median **with IQR** · tail σ (sustained) ·
time-to-first-entry · command saturation fraction · MTQ saturation fraction.

### B.4 Pre-registered decision rules (written before the run; changing them later requires a dated DECISIONS entry)

- **Nominal non-degradation** — FAIL if `median(R1) − median(C1) > 0.05 deg` on `S0` **and** Wilcoxon
  `p < 0.05` (Holm-corrected across the 5 conditions).
- **Fault-time advantage** — PASS if on `S2`: `median(R1) ≤ median(C1) − 0.30 deg` **and** McNemar
  `p < 0.05` (Holm) **and** ≥4 of 5 training seeds agree in sign.
- **Unit of analysis is the training seed.** With 5 seeds the minimum attainable two-sided sign-test
  `p` is 0.0625, so a 5/5 sign agreement is reported as consistent-but-underpowered, never as `p < 0.05`.
- **Both columns are reported, always.** A trade-off (nominal cost for fault-time gain) is a valid,
  publishable outcome; a one-sided report is forbidden.
- **n = 24** episode-level ICs per (arm, seed, condition), 900 s — the same design as M3.3-B so the
  classical arm doubles as a cross-check of the grid.

### B.5 Compute budget

| item | measured rate | estimate |
|---|---|---|
| SAC retrain, 300 k steps, 4500-step episodes | ~38 min/seed | 5 seeds ≈ 3.2 h |
| RL evaluation, 24 episodes/cell | 0.165 ep/s single-process | ≈ 2.5 min per (seed, condition) → ≈ 1 h for the grid |
| Classical arms (C1, C2) | 1.43 ep/s at 6 procs | minutes |

Training runs are **handed to the researcher as a copy-paste command**, not launched by the agent.

**Exit:** `docs/research/B1_residual_vs_classical_report.md` with the paired table, both holds, the five
seeds, the pre-registered verdicts and an explicit limitations section.

---

## Phase C — Fault-awareness, detection grade `[AUTH]`, runs **after** B

Bounded by A1: the ceiling on allocation information is 0.04–0.06 deg, so this phase is justified by the
**oracle asterisk** (G13) and by detection — not by expecting a performance gain.

| id | task | acceptance |
|---|---|---|
| C.1 | Wheel-speed sensing model (noise, quantisation, 5 Hz sampling) | **DONE 2026-11-06** — `wheel_sensor.py` (clamp → quantise → noise → ZOH), 9 tests, `enabled: false` shipped. Measured: one control period of sensor error = **7.1e-5 N·m = 35 %** of the 2e-4 N·m Coulomb friction |
| C.2 | Estimator-only harness per audit §10: synthetic → recorded traces → closed loop; calibration / validation / held-out splits | three disjoint datasets; no reuse |
| C.3 | Candidates **E** (window LS) → **A** (`σ_v`-scaled) → **B** (innovation) | coverage is the deciding metric, *per condition* |
| C.4 | Confidence calibration + false-healthy audit | 95 % nominal coverage inside its Wilson CI; 0 false HEALTHY on S6/S7; UNKNOWN rate reported at slew and settled |
| C.5 | Integrate detection with allocation and with the RL observation | measured benefit vs oracle **and** vs unity; state it plainly if the benefit is ≤ A1's ceiling |

**Exit:** detection usable without ground truth; the G13 asterisk replaced by a measured statement.

---

## Phase D — Final control architecture `[AUTH]`

| id | task | acceptance |
|---|---|---|
| D.1 | PPO vs SAC, single-factor, 5 seeds each, identical obs/action/reward | task metrics only, never returns; one algorithm nominated with evidence |
| D.2 | Safety supervisor + fallback classical controller | intervention rate reported; one-step model-based *performance* filter — **the word "guarantee" is prohibited** |
| D.3 | Fault taxonomy behind flags: locked wheel, ramped degradation, intermittent, gyro-bias step, star-tracker dropout, saturation | **DONE 2026-11-06** — `fault_taxonomy.py`, 13 regression tests, flags-off reproduction **0.000e+00** |
| D.4 | Unseen fault combinations + randomised ICs; held-out families reported separately | no test on a severity used in training |
| D.5 | Mid-flight injection and worst-case stress | reported as distributions, never as a bare median |

**Exit:** canonical comparison tables for the thesis; every capability traceable to a test and an artifact.

---

## Phase E — MIL → SIL → embedded → HIL

**Authorisation (D-12):** `[AUTH]` for **E-1 MIL**, **E-2 SIL**, **E-3 embedded profile (host-side only)**,
in that order, and only after the architecture-freeze gate (§ Phase D). **`[NEEDS-APPROVAL]` for E-4 HIL** —
HIL does not start without an explicit researcher GO, and no hardware, real-time or flight-readiness claim
may be made before it exists.
MIL-1 must precede SIL, otherwise a SIL discrepancy cannot be attributed to the software rather than the
specification, and the result is untraceable.

### E-1 MIL (≈1.5–2 weeks)

| id | task |
|---|---|
| MIL-1 | Reference specification, writable as C from the document alone: observation scaling, action→torque, allocator, safety filter, clipping, fixed-step integration |
| MIL-2 | Regression of the MIL controller against the Python reference on identical traces |
| MIL-3 | Integrator step-size sensitivity (0.1 s nominal vs 0.05 / 0.02) |

### E-2 SIL (≈2 weeks)

| id | task |
|---|---|
| SIL-1 | ONNX export, equivalence to PyTorch < 1e-5 |
| SIL-2 | Split loop over TCP at 5 Hz with timestamps; separate processes |
| SIL-3 | float32 vs float64 numerics quantified end-to-end |
| SIL-4 | Latency and injected-jitter sensitivity |
| SIL-5 | SIL-vs-MIL parity, tolerance declared **before** the run |
| SIL-6 | Fault injection inside the SIL loop |

### E-3 Embedded profiling (≈1–2 weeks)

ESP32-S3 (or equivalent) deployment profile only: quantisation, pruning, inference latency, memory.
Explicitly **not** a flight qualification.

### E-4 HIL (≈3–4 weeks + hardware)

Real-time target + representative actuator/sensor interfaces. Requires hardware on hand and is where the
title's "Hardware-in-the-Loop" is earned. **Claims restriction from `1967326` remains until this exists.**

### E approval request (answer needed before any E work)

1. **Target for MIL/SIL**: pure-software on this PC + a second process, or is a real-time target (RPi /
   STM32 / ESP32-S3) needed from the start of SIL?
2. **Hardware available now** for HIL (which board, which interface), or does it need ordering?
3. **Timebox for E**: is MIL + SIL (≈4 weeks) the near-term target with HIL a later stage (my
   recommendation), or must HIL be inside this term?
4. **Language for MIL-1**: C (portable to any target) or C++ (faster to write around the existing
   Eigen-style numerics)?

---

## Phase F — Thesis assembly `[PLANNED]`

Comparative tables, publication-quality figures, methodology, assumptions, limitations, statistics; every
claim mapped to an artifact; gaps against the approved proposal; reproducible research package.

---

## Gates and standing rules

| gate | condition |
|---|---|
| **G-B** | B does not conclude before the 5-seed design runs; a single-seed result is never a claim |
| **G-C** | C does not start before B's report exists (C must not delay the central claim) |
| **G-D** | D.1 does not start before B nominates an algorithm |
| **G-E** | **explicit researcher approval**, four answers above |
| **G-F** | F starts only when B–D each have a committed report |

Standing: never weaken a baseline to favour RL · never change a criterion after seeing results without a
dated `DECISIONS` entry · preserve all prior artifacts · commit and push each completed step · long
training runs are launched by the researcher · negative results are reported, not buried.
