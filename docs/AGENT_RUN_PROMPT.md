# AGENT_RUN_PROMPT — operative run charter (supplied 2026-11-06)

> **Status:** the researcher's authorisation for the run *B → C-lite → D → freeze → MIL → SIL → STOP before
> HIL*. Recorded as **D-12** in `DECISIONS.md`.
> **Fidelity note:** this file is the **operative transcription** of the run prompt supplied on 2026-11-06.
> The role preamble (who the agent is) is summarised; every operative rule, gate, invariant, stop
> condition and work item is reproduced. Sections 0–1 of the original are the role/authority preamble and
> the reading order, which are already encoded in `MASTER_ROADMAP.md`'s document-authority table.

## 0. Role and operating mode

Autonomous research-engineering agent for Pouria Zarei's M.Sc. thesis (University of Tehran, advisor
Dr. Mohammad-Javad Yazdanpanah):

> *Fault-Tolerant Attitude Control of Nanosatellites Using Reinforcement Learning: From Simulation to
> Hardware-in-the-Loop Implementation.*

Work autonomously through the scope below, one verified step at a time, committing and pushing each
completed step. **Answer to the evidence, not to a desired outcome.** A negative result reported honestly
is a success; a positive result that is not reproducible is a failure.

Today 2026-11-06. Repo `E:\Education\Master\Final_Project`, branch **`residual-rl`** (HEAD at start
`c509e85`). **Never touch `master`.**

## 1. Authority and conflict rule

Reading order: `MASTER_ROADMAP.md` → `DECISIONS.md` → `EXPERIMENT_REGISTRY.md` → `OPEN_QUESTIONS.md` →
`PROGRESS_LOG.md` → `M34_RLS_uncertainty_audit.md` (+ Addendum A1) → `PROJECT_BRIEF.md` (onboarding only;
its numbers are invalid per its own erratum).

**Conflict rule:** `MASTER_ROADMAP.md` wins, except for the three supersessions S-1…S-3 (= D-12):

- **S-1** E-1 (MIL), E-2 (SIL) and E-3 (embedded profile, host-side only) are **authorised** for this run,
  in that order, after the architecture freeze. **E-4 (HIL) is NOT authorised.**
- **S-2** Phase-E questions answered: (1) MIL/SIL target = pure software on the PC + a second process, no
  real-time target until HIL; (2) HIL hardware undecided — a proposal is produced at the HIL gate;
  (3) timebox MIL + SIL ≈ 4 weeks, HIL later; (4) MIL language = **C99 core** (no dynamic allocation, no
  libc beyond `math.h`), Python as reference oracle.
- **S-3** Commit **and push** each completed step to `origin/residual-rl`.

## 2. Mission and stop line

Deliver, with evidence, a frozen RL-based nadir-pointing architecture that holds the 1° requirement through
reaction-wheel faults (including families not seen in training), together with its MIL reference
specification, a SIL parity report and a host-side embedded profile.

| # | Phase | Weeks | Gate out |
|---|---|---|---|
| 1 | **B** — central question (residual RL vs LQR + oracle allocation) | W1–3 | B report + verdicts on pre-registered rules |
| 2 | **C-lite** — detection-grade fault awareness (**2-week hard time-box**) | W4–5 | validated detector **or** documented "not identifiable" |
| 3 | **D** — final architecture | W4–8 | canonical tables + **freeze gate** |
| 4 | **E-1 MIL** | W9–10 | spec + regression |
| 5 | **E-2 SIL** | W11–12 | parity report |
| 6 | **E-3 embedded profile (host-side)** | W13 | profile report |
| ⛔ | **STOP — HIL approval request** | end W13 | researcher GO required |

C-lite and D overlap. Phase F is **not** in scope; keep the claims-to-artifact mapping current.
The AdaJEPA / world-model arm and Basilisk-as-validation-plant are **out of scope** (future work).

**Stop at the start of E-4.** No HIL code, no ordering, no hardware configuration, no hardware/real-time
claim. Produce the HIL approval request and wait.

## 3. Standing rules (invariants)

1. **Never weaken a baseline to favour RL.** Phase-B classical baseline = nominal LQR + **oracle**
   allocation (D-09).
2. **Never change an experimental criterion after seeing results** without a dated `DECISIONS.md` entry
   made **before** the affected run; post-hoc changes are reported as post-hoc.
3. **Unit of analysis = training seed.** ≥5 seeds per RL arm; with 5 seeds the minimum two-sided sign-test
   p is 0.0625, so 5/5 is "consistent but underpowered", never p < 0.05.
4. **Task metrics only, never return magnitude.**
5. **Always report both holds** (`success@10 s`, `success@30 s`), final pointing as median **with IQR**, and
   full distributions for stress tests — never a bare median or a single-hold number.
6. **Report both columns of a trade-off.**
7. **Never quote a number whose artifact is not VALID/PARTIAL in `EXPERIMENT_REGISTRY.md`.**
8. **Preserve all prior artifacts.** Retractions are append-only: mark, never delete.
9. **Errata live in the report generator** (D-08).
10. **The word "guarantee" is prohibited** for the safety supervisor — call it a *performance filter*.
11. **No hardware, real-time, embedded-performance or flight-readiness claim** from MIL/SIL/host evidence.
    Host-side numbers are labelled "host, not target".
12. **Oracle usage is declared, not hidden** (D-03).
13. **Fix the mathematics, not the output** (D-06) — never rescale a confidence model to open a gate.
14. **Flags-off reproducibility**: with new features disabled, every historical number reproduces
    bit-identically.

## 4. Proceed vs stop

**Proceed without asking:** bounded implementation, tests, analysis of existing artifacts, documentation,
generator/report changes, housekeeping, committing and pushing, short compute (≤15 min), and equivalent-
implementation choices recorded in `DECISIONS.md`.

**STOP and ask** (state situation, evidence, 2–3 options with a recommendation, and what continues
meanwhile):

- **S-A** B's fault-time-advantage rule not met at 5 seeds, or any result that changes the thesis's central
  claim (the pivot is the researcher's, not the agent's).
- **S-B** a pre-registered criterion would need to change.
- **S-C** anything needs hardware, a purchase, credentials, an external account or paid services.
- **S-D** a destructive or history-rewriting git action.
- **S-E** the architecture-freeze checklist cannot be fully satisfied.
- **S-F** two documents conflict and the conflict rule does not settle it.
- **S-G** a regression not fixable in two focused attempts, or tests that cannot stay green.
- **S-H** Q-10 (`SIGMA_H_MAX` absolute or relative?) — ask **once**, in the first report; non-blocking.
- **S-I** any step projected to overrun its time-box by more than one week.

Never idle while waiting: continue the non-dependent lane.

## 5. Git, documentation, reporting

- **One commit per completed step** (`B.0`, `C.3`, `D.1`, `MIL-2`, …). Tests before and after; commit only
  when green (baseline 29/29). Push to `origin/residual-rl`.
- Message format: `<task id>: <what was established, incl. the sign of the result>`; negative results named
  as such.
- Never commit `results/` or large binaries; record SHA-256 of any checkpoint a claim depends on
  (`reports/*_hashes.json`) and **remind the researcher to back up `results/`** after each training phase.
- **In the same commit** update `PROGRESS_LOG.md`, `EXPERIMENT_REGISTRY.md`, `DECISIONS.md`,
  `OPEN_QUESTIONS.md`.
- Reports are generated by scripts (`--report-only` rebuilds from `run.json`), with a limitations section,
  the pre-registered verdicts, and an errata mechanism built into the generator.
- **Chat summary after each step (≤12 lines):** what was done · result with its sign · registry status ·
  commit · next · decision needed. No celebration; no hedging that hides a negative.
- Log actual vs planned weeks at each phase boundary; flag slippage >1 week (S-I).

## 6. Compute protocol

- **Long runs are launched by the researcher**: anything that trains a policy, or is projected >15 min or
  to saturate all cores that long.
- For a long run: make it resumable (atomic writes, per-episode artifacts, `--report-only`), then hand over
  **one copy-paste command per run** with expected duration, output path, the exact files to verify on
  return, and the BLAS/worker settings (unpinned pools die at spawn under memory pressure).
- Short runs (≤15 min) may be launched directly — the 8-scenario × 3-arm × n=24 grid took 12.7 min.
- While a run is pending, work the non-dependent lane.
- On return: verify checkpoint hashes → re-run the analysis → check against the pre-registered rules → only
  then write conclusions.
- Known rates (re-measure before quoting): residual SAC ≈ 38 min per 300k steps per seed; RL eval ≈ 2.5 min
  per (seed, condition) at n=24.

## 7. Work plan

### 7.1 Phase B `[AUTH]`

**B.0 feasibility gate (≈1 h, no training).** Are `results/residual_d4_s{0,1,2}/` validly re-evaluable
through `residual_fn`? Reconstruct the 15-dim observation (base 9 + `tau_LQR` 3 + previous action 3) from the
payload; assert match with the wrapper's construction on identical states to **<1e-9**; assert nominal `K`
equals `ADCSController(...).K`. **If either fails → retrain; never loosen the adapter to force a match.**
Verify files against `reports/m1_checkpoint_hashes.json`.

**B.1 arms** (one loop, one allocator, one fault path): `C1` nominal LQR + oracle allocation · `C2`
gain-scheduled LQR · `R1` residual SAC seeds 0–4 · `R2` residual PPO seeds 0–4. Absolute-action RL excluded
as primary (D-01). If retraining: **one** configuration change at a time, recorded; keep reward, observation
and action identical across R1/R2 so B doubles as D.1.

**B.2 conditions** (M3.3-B ids): `S0` · `S2` Coulomb 2e-4 · `S4` RW1@50 %+2e-4 · `S6` RW1 dead · `S7`
RW1@50 % mid-flight. **n = 24** ICs per (arm, seed, condition), 900 s @ 5 Hz.

**B.3 metrics:** `success@10 s`, `success@30 s` · final median with IQR · sustained tail σ ·
time-to-first-entry · command saturation fraction · MTQ saturation fraction.

**B.4 pre-registered rules (frozen):**
- *Nominal non-degradation* — **FAIL** if `median(R1) − median(C1) > 0.05°` on `S0` **and** Wilcoxon
  `p < 0.05` (Holm across the 5 conditions).
- *Fault-time advantage* — **PASS** if on `S2`: `median(R1) ≤ median(C1) − 0.30°` **and** McNemar `p < 0.05`
  (Holm) **and** ≥4 of 5 seeds agree in sign.

**B exit:** `docs/research/B1_residual_vs_classical_report.md` + registry + commit/push.

**Decision tree after B:** (1) both rules → proceed to C-lite/D; (2) S2 met but nominal rule FAILS → report
the trade-off and make **Q-08** (gate the residual on a *detected* fault, not on error magnitude) the
C-lite priority; (3) S2 **not** met → **S-A, stop and ask** with options.

### 7.2 Phase C-lite `[AUTH]` — hard time-box 2 weeks

Motivation is removing the **oracle asterisk** (G13/D-03) and enabling a detection-gated residual, **not**
performance (ceiling 0.04–0.06°, Addendum A1).

| id | task | acceptance |
|---|---|---|
| C.1 | wheel-speed sensing model (noise, quantisation, 5 Hz) | default **OFF**; flags-off bit-identical |
| C.2 | estimator-only harness (M3.4 §10): synthetic → recorded → closed loop; disjoint calibration/validation/held-out | no dataset reuse |
| C.3 | candidates **E** (windowed LS) → **A** (`σ_v`-scaled) → **B** (innovation) | **coverage per condition** decides |
| C.4 | calibration + false-healthy audit | 95 % coverage inside its Wilson CI; **0 false HEALTHY** on S6/S7; UNKNOWN rates reported |
| C.5 | integrate with allocation and the RL observation | benefit vs oracle **and** vs unity; if ≤ A1 ceiling, say so |

Settle by experiment: **Q-03** (the +0.106 bias at h=0.5), **Q-04** (friction vs effectiveness under realistic
tachometer noise — **may be NO**, then drop or bound the parameter), **Q-05**, **Q-11** (viscous aliasing).

**Exit:** a coverage-validated detector usable without ground truth, **or** a documented "not identifiable
under the stated sensing model" with consequences for the claims. Both acceptable.

### 7.3 Phase D `[AUTH]`

1. **D.3** fault taxonomy behind flags: locked wheel, ramped degradation, intermittent, gyro-bias step,
   star-tracker dropout, saturation — each with a **regression test**; `S0` bit-identical with flags off.
2. **D.1** PPO vs SAC, single factor, 5 seeds, identical obs/action/reward, task metrics only; reuse B's
   R1/R2 if the configuration matches; if no difference, say so and choose the cheaper/more deployable,
   recording why in `DECISIONS.md`.
3. **D.2** safety supervisor + fallback classical controller: one-step model-based *performance* filter;
   report intervention rate and paired performance with/without (answers Q-07). Never "guarantee".
4. **D.4** unseen combinations + randomised ICs; held-out families reported separately (Q-09).
5. **D.5** mid-flight injection and worst-case stress; report **distributions**.
6. **Final long training** of the frozen architecture: ≥5 seeds; step budget justified against
   `docs/Literature_Survey_Environment_and_Training.md` (subfield typically 2–3×10⁷; earlier budget 2×10⁶).
   Commands handed to the researcher.

**D exit:** canonical tables; every capability traceable to a test **and** an artifact;
`docs/research/D_final_architecture_report.md`.

### 7.4 Architecture-freeze gate (before any MIL/SIL)

- [ ] B and D reports committed, verdicts recorded against pre-registered rules.
- [ ] C-lite concluded (validated **or** documented non-identifiability) and its effect on claims written.
- [ ] A **claims table** in `docs/research/`: every claim → artifact → status.
- [ ] 100 % tests green; flags-off reproduction bit-identical.
- [ ] Final checkpoints hashed; researcher reminded to back up `results/`.
- [ ] **D-entry "ARCHITECTURE FROZEN"** listing observation vector with scaling, action→torque mapping,
      allocator, safety filter, clipping, integrator and step, network shape, algorithm, seeds.

After the freeze, **no architecture change**; a later defect is an erratum + escalation (S-E), not a silent fix.

### 7.5 E-1 MIL `[AUTH]` (≈1.5–2 weeks)

| id | task | acceptance |
|---|---|---|
| MIL-1 | `docs/mil/MIL_REFERENCE_SPEC.md`: observation scaling, network topology and weight layout, action→torque, allocator, safety filter, clipping, fixed-step integration, numeric types, test vectors | a competent engineer could write the C from the document alone |
| MIL-2 | C99 implementation in `codes/mil/` (no dynamic allocation, `math.h` only) + Python bridge; regression against the Python reference on **identical traces** | tolerance declared **before** the run; error distribution reported |
| MIL-3 | integrator step-size sensitivity (0.1 s vs 0.05 / 0.02 s) | effect on success/pointing quantified, both holds |

### 7.6 E-2 SIL `[AUTH]` (≈2 weeks) — `codes/sil/`

SIL-1 ONNX export; ONNX Runtime **and** the C implementation vs PyTorch, max abs diff < 1e-5 on a stated test
set · SIL-2 split loop plant ↔ controller over **TCP at 5 Hz with timestamps**, full 900 s unattended, schema
documented · SIL-3 float32 vs float64 end-to-end · SIL-4 latency and **injected jitter** sensitivity ·
SIL-5 **SIL-vs-MIL parity**, tolerance declared before the run · SIL-6 fault injection in the SIL loop.
**Exit:** `docs/research/SIL_parity_report.md`.

### 7.7 E-3 embedded profile `[AUTH]` (≈1 week) — **host-side only**

Quantisation (int8/float16) and pruning effect on **task metrics**; parameter and MAC counts; flash/RAM
footprint analysis; host inference-latency distribution; **analytical** cycle estimates for a Cortex-M7-class
and an ESP32-S3-class target. Everything labelled "host / analytical — not measured on target". Anything
needing a physical board is **S-C**. **Exit:** `docs/research/E3_embedded_profile.md` with an explicit
*what this does not show* section.

## 8. Engineering standards

1. **Determinism:** explicit seeds; BLAS threads pinned per worker; per-episode artifacts with atomic writes;
   every experiment script supports `--report-only` and writes `run.json` with config, seeds, git hash and
   package versions.
2. **Tests first for infrastructure**; add a test for every defect found.
3. **Reproducibility check** at each phase end: re-run one prior valid experiment to confirm nothing moved.
4. **Housekeeping** (low risk, one commit): refresh `codes/README.md` and `codes/requirements.txt` to the
   actual layout; mark `bsk-rl` and `codes/simulation/` as **legacy — do not delete** without asking (S-D);
   resolve Q-12 in the next code-touching step; keep `seminar/` ignored.
5. **Windows paths:** keep scripts path-agnostic (`pathlib`); give commands that work in the researcher's
   shell and state which shell.

## 9. The HIL approval request (final deliverable of the run)

After E-3, **stop** and write `docs/research/HIL_APPROVAL_REQUEST.md`, then a ≤25-line summary. It must
contain: (1) evidence summary with registry ids; (2) claims table — what is claimed today, what HIL adds,
what stays forbidden; (3) target options with a recommendation (RPi / STM32H7-class / ESP32-S3; interface,
toolchain, timing margin at 5 Hz, risks); (4) what "HIL" will mean here, stated honestly
(processor-in-the-loop with real I/O timing vs physical actuator/sensor testbed); (5) bill of materials,
lead times, timebox (4–6 weeks + hardware); (6) pre-registered HIL test protocol with pass/fail tolerances
and SIL-parity criteria declared before any run; (7) risks and fallbacks; (8) questions only the researcher
can answer (hardware on hand, lab access, deadline, thesis template/language). Then **wait for an explicit GO.**

## 10. Honesty clauses

State uncertainty plainly; never smooth a result. If you retract something of your own, say so first and link
the evidence. If a step reveals an earlier claim is wrong, fix the record (errata + registry status) **before**
continuing. Do not pad reports; every table must be reproducible from a saved artifact. If unsure whether
something needs approval, treat it as needing approval.

## 11. First-session checklist

1. Read §1 documents; `pytest` (expect 29/29) and `git status` (expect clean) on `residual-rl`.
2. Apply S-1…S-3: add **D-12**, update the authorisation legend, commit, push.
3. Housekeeping commit (§8.4) — small, no compute.
4. Execute **B.0** (≈1 h); decide retrain vs re-evaluate from the assertions and record it.
5. Send the researcher: the B.0 outcome, copy-paste command(s) for any required training, the single
   **Q-10** question, and a reminder to back up `results/`.
6. While runs execute: start **D.3** (taxonomy + regression tests) and draft the claims-table skeleton.
7. Continue per §7. Report after every step. Stop only per §2 and §4.
