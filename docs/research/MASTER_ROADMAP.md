# MASTER_ROADMAP — execution authority

**Authoritative from:** 2026-11-06
**Repository:** `E:\Education\Master\Final_Project` · branch `residual-rl` · HEAD at creation `c9a4aa5`
**Thesis:** *Fault-Tolerant Attitude Control of Nanosatellites Using Reinforcement Learning: From
Simulation to Hardware-in-the-Loop Implementation.*

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
