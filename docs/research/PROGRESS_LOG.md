# PROGRESS_LOG — chronological, newest first

Short entries only: what was done, what it changed, and the commit. Detail lives in the linked reports.

---

## 2026-11-22 — codes/v2 CCR v2 Platform, Stage 1–4 Hardening, Basilisk 2.12.2 Cross-Validation, Confirmatory E003, codes/v1 Archival & Merge to master

**Done.** Completed and verified the full **CCR v2** research platform in [`codes/v2/`](../../codes/v2/) (`adcs-rl`, commit `ee67ba3`), archived the historical `v1` codebase (`codes/*` → [`codes/v1/`](../../codes/v1/)) (`D-15`), and synchronized all outer repository governance documents (`D-15..D-19`, `E-25..E-29`, `C-08..C-23`, `Q-01..Q-15`) for merge of `residual-rl` into `master`. Full detail in [`codes/v2/docs/FINAL_RESEARCH_REPORT.md`](../../codes/v2/docs/FINAL_RESEARCH_REPORT.md) and [`codes/v2/docs/agent_reports/PHASE_3_REPORT.md`](../../codes/v2/docs/agent_reports/PHASE_3_REPORT.md).

**Architecture & Stage 1–4 Hardening (`E-28`)**
- **Reference plant (`spacecraft_reference_001`):** 100 kg spacecraft, 4-wheel pyramid RW + 3-axis MTQ, `5 Hz` control (`200 ms` period), `100 Hz` RK4 (`fast_rk4`), official degree-13 IAGA **IGRF-14**, 6-state MEKF with discrete `Q_d` scaling and post-dropout covariance reset, online RLS capability estimator with directional forgetting, `S4` additive bias-vs-gain separation, `unverified_unexcited` flag, and unexcited confidence cap `<= 0.85`; shared box-constrained `cap_alloc` across `A4..A7` and all `Abl_A7_*` arms (zero oracle `h_true` leakage).
- **CCR v2 control law:** `tau_cmd = tau_classical + rho * alpha * G * tau_rl` separating intervention need (`rho`, with tachometer noise floor + attitude/rate deadzones forcing nominal `S0` mean `||tau_rl_gated|| < 1e-4 N*m`), trust (`alpha`), directional capability (`G`), and deterministic safety supervisor (`M3_UNKNOWN_INVALID_UNSAFE` latch setting `rl_permitted = False` / `tau_rl_gated = 0` under star-tracker dropout or persistent `authority_infeasible`).
- **Strong classical baseline (`A3_strong_classical`):** CARE LQR + gyro feedforward + `0.08 rad/s` slew limiter + 3-axis nonlinear ESO/DOB + `cap_alloc` + observability gain schedule + MTQ assist/unloading.
- **Core test verification:** `python -m ruff check --no-cache src tests scripts` → **All checks passed!**; `python -m pytest -v -p no:cacheprovider` (Python 3.14.6) → **47 passed, 2 skipped**.

**Live Basilisk 2.12.2 8-Regime Cross-Validation (`E-27`, [`PHASE_3_REPORT.md`](../../codes/v2/docs/agent_reports/PHASE_3_REPORT.md))**
- Executed `tests/integration/test_phase3_basilisk.py` in Python 3.11 `.venv_bsk` against live **Basilisk `2.12.2`**: **5 passed, 0 failed (`8/8` regimes PASS)**.
- **Open-loop plant:** `R1` 10 s (`9.313e-09 m` / `9.31 nm` pos, `0.0086 deg` att, `8.39 nT` B-field), `R4` wheel saturation (`0.0682 deg`), `R6` MTQ saturation orthogonality (`tau·B ~ 1.995e-14`), `R8` 600 s long-horizon (`0.197 um` pos, `0.2870 deg` att).
- **Closed-loop parity (`fast_rk4` vs `basilisk`):** `R2` 90° slew (`0.6744 deg` / diff `0.0000 deg`), `R3` 10°/s detumble (`0.4241 vs 0.4211 deg` / diff `0.0225 deg`), `R5` RW0 50%+0.015 N·m (`0.1062 vs 0.1047 deg` / diff `0.0260 deg`), `R7` 20 s star-tracker dropout (`0.0938 vs 0.1014 deg` / diff `0.0105 deg`).

**Frozen Pilots (`E-25, E-26`) & Confirmatory Benchmark `E003_ccr_v2_confirmatory` (`E-29`, [`FINAL_RESEARCH_REPORT.md`](../../codes/v2/docs/FINAL_RESEARCH_REPORT.md))**
- Pilots preserved: `E001_ccr_v2_benchmark` (`12k` steps × 1 train seed × 6 test seeds × 9 scenarios, 756 test / 1,260 total ep) and `E002_ccr_v2_igrf14_rlsfix` (`15k` steps × 1 train seed × 6 test seeds × 9 scenarios, 810 test / 1,350 total ep).
- Confirmatory `E003_ccr_v2_confirmatory`: **15 arms**, `30,000` SAC steps × `3` independent training seeds (`42, 107, 211`, 18 policies) × `10` held-out test seeds (`100..109`) × `9` held-out scenarios (`S0..S8`) = **3,330 held-out test episodes** (`7` controllable scenarios → `n = 70` classical / `210` learned; `2` physically infeasible `S2, S3` → `n = 20` classical / `60` learned). Policy-averaged paired scenario-seed tests (`n_pairs = 70` controllable / `90` all), 5,000-sample paired bootstrap CIs, two-sided Wilcoxon with step-down Holm-Bonferroni (`wilcoxon_p_holm`).
- **Failure & Infeasibility (`failure_breakdown_heldout.csv`):** `A7_ccr_v2_full`, `A7_ccr_v2_eso`, and `Abl_A7_clean_trained` achieve **0.00% Controllable-7 LoC (`0/210`)** across all 3 seeds and **100.0% Infeasibility Detected & Correct Infeasibility Response (`60/60`)** on `S2/S3` (`||tau_rl_gated|| < 1e-6 N*m`, `M3` latch). Comparators: `A0` 12.86% (9/70), `A1` 8.57% (6/70), `A2` 0.00% (0/70), `A3` 0.00% (0/70), `A4` 7.62% (16/210, 0% infeas resp), `A5` 1.43% (3/210, 0% infeas resp), `A6` 8.57% (18/210: 46.67% on `S5`, 13.33% on `S4`; 100% infeas resp), `Abl_A7_no_alpha` 0.48% (1/210), `Abl_A7_no_supervisor` 0.00% controllable LoC / 0.0% infeas resp. (All arms 100.0% LoC on physically infeasible `S2 ~104.4°` and `S3 ~66.6-74.7°`.)
- **Controllable-7 Summary & Paired Tests (`n_pairs = 70`):**
  - `A3_strong_classical`: `0.2315°` mean / `0.1306°` median (IQR `0.1261°`), `12.40 s` med recovery, `1.6824 N·m·s`.
  - `A7_ccr_v2_eso`: **`0.2087°` mean** (lowest of all 15 arms) / `0.1518°` median (IQR `0.1124°`), `12.80 s` recovery, `1.6968 N·m·s`; beats `A3` on `S4` (`0.3818° vs 0.4904°`) and `S8` (`0.2934° vs 0.4037°`); vs `A3` paired mean diff `-0.0228°`, `p_Holm = 0.6591`.
  - `A7_ccr_v2_full`: `0.3258°` mean / `0.1288°` median (IQR `0.1192°`), `11.40 s` recovery, `1.6214 N·m·s`; matches `A3` on `S0` (`0.1414° vs 0.1415°`), cuts `S8` 3.3x (`0.1227° vs 0.4037°`), beats `A0` (`p_Holm = 0.01490` vs A0 table / `0.00948` in ablations-vs-A7 table) and `A4` (`p_Holm = 4.32e-05`), ties `A3` overall (`52.86%` wins, `p_Holm = 1.0000`), trails `A3` on `S4` (`1.4394°` mean, LQR-only backbone).
  - `Abl_A7_clean_trained`: `0.2780°` mean / **`0.0970°` median** (IQR `0.0995°`), `7.80 s` recovery, `0.00%` LoC; significantly beats both `A7_ccr_v2_full` (`-0.0372°` med diff, `p_Holm = 3.05e-05`, `78.57%` wins) and `A3_strong_classical` (`-0.0326°` med diff, `p_Holm = 0.02453`, `71.43%` wins); `S4` mean still `1.2567°` without ESO.
  - **All 4 CCR v2 ablations survive Holm-Bonferroni on Controllable-7 (`vs A7_ccr_v2_full`, `n_pairs = 70`):**
    1. `Abl_A7_no_rho`: `+0.2256°` mean diff `[95% CI +0.1465°, +0.3022°]`, `+0.1729°` med diff, `p_Holm = 5.72e-08` (`A7` wins `94.3%`; All-9 `p_Holm = 7.99e-09`)
    2. `Abl_A7_no_alpha`: `+0.1579°` mean diff `[95% CI +0.0680°, +0.2534°]`, `+0.0354°` med diff, `p_Holm = 7.31e-06` (`A7` wins `75.7%`; All-9 `p_Holm = 8.11e-04`)
    3. `Abl_A7_no_G`: `+0.0122°` med diff (`+46.5%` mean RL torque `0.00268 -> 0.00393 N·m`, `S8` `0.1227° -> 0.2928°`), `p_Holm = 0.00939` (`A7` wins `72.9%`; All-9 `p_Holm = 0.0904` raw `0.0181`)
    4. `Abl_A7_no_supervisor`: `+0.0301°` mean diff, `+0.0048°` med diff, `p_Holm = 0.01312` (`A7` wins `71.4%`, infeas response drops `100% -> 0%`; All-9 `p_Holm = 0.0525` raw `0.00657`)
- **Desktop Python CPU Profile (`cpu_profile.json`, Windows 11, Python 3.14.6, NumPy 2.5.0, degree-13 IGRF-14):** `onboard_total_B1_B3_CCR_v2` = **`5.703 ms` mean / `9.964 ms` p99** (`2.851%` mean / `4.982%` p99 of `200 ms` `5 Hz` step); `B6_PolicyInference_NumPy` (`30->64->64->3`, `6,339` params, `24.76 KB` float32) = `0.045 ms` mean / `0.106 ms` p99.
- **Honest boundaries enforced (`D-17, D-18`):** `n_train = 3 < 5` training-seed limitation explicitly noted; `C-12` (formal stability guarantee) and `C-15` (HIL validation) remain strictly `FORBIDDEN`; target C99/HIL deployment on **Raspberry Pi CM5** and **STM32H563ZIT** is deferred.

---

## 2026-11-06 — C.1: wheel-speed sensing (default off), and how favourable the old assumption was

**Done.** `satellite_adcs/wheel_sensor.py` — `TachometerModel` (clamp → quantise → noise → zero-order
hold, in that physical order) and `make_wheel_sensor(cfg)`; `sensors.yaml` gains a `tachometer` block with
**`enabled: false`**. `tests/test_wheel_sensor.py` (9 tests). Tests **45 → 54**.

**Why it matters.** Every estimator result to date (E-15…E-20, M3.4) fed the RLS the plant's exact
`omega_w`. The regressand is `J_w·d(omega_w)/dt` — a derivative — so wheel-speed error is amplified by
`J_w/dt` before the estimator sees it. That was the single most favourable assumption in the
fault-awareness chain and it was never stated as one.

**Measured, not asserted:** at the shipped spec (σ = 50 mrad/s, 5 Hz, `J_w = 2e-4`), one control period
of sensing error is worth **7.1e-5 N·m** = **35 %** of the 2e-4 N·m Coulomb friction. Same order of
magnitude — it cannot be dismissed, and it is not dominant either.

**A correction to my own first estimate.** I initially computed `J_w·σ/dt` with the *integrator* step
(0.1 s) and told the researcher the error was "several times the friction". Measured with the estimator's
actual time base (the 0.2 s control period) it is 0.7× → **0.35×**. The test now pins 0.2 < ratio < 2.0
and the docstring records why the first number was wrong.

**Interface facts learned by running, not by reading:**
- `h_hat` is only populated under `health_source="hat"`; the default `"true"` path records zeros by design.
- `friction_coulomb_Nm` is an *optional* key (`.get(..., 0.0)`): scenarios inject it, the shipped
  `actuators.yaml` does not carry it, so reading it directly raises `KeyError`.
- `max_speed_rad_s: null` in YAML means "use actuator full scale" — `.get()` does **not** fall back when
  the key exists with a `None` value.

**Housekeeping:** a mistyped path created `E:\Education\Master\First_Project\codes\tests\…`; the file was
moved to the correct tree and the stray directory (one file, created by that write) removed.

**Next:** C.2 — rerun the estimator validation with the tachometer ON, i.e. turn "the estimator works" into
"the estimator works at this sensor quality, or it does not".

---

## 2026-11-06 — B.1 harness + classical pass (cross-check reproduces M3.3-B exactly)

**Done.** `scripts/b1_residual_vs_classical.py`: 5 conditions × {C1 oracle LQR, C2 gain-scheduled,
R1 SAC, R2 PPO}, n=24, 900 s, both holds, paired McNemar per seed, Holm across seeds, per-seed sign
agreement, per-episode artifacts, `--report-only`, `--append`. It reuses the **verified** B.0
observation adapter rather than re-implementing it.

**Cross-check PASSED.** The classical pass reproduces the M3.3-B oracle cells *exactly*: S0 0.243,
S2 1.570 / 8.3 %, S4 1.570 / 8.3 %, S6 91.342, S7 0.243. The new harness scores identically to the
earlier grid, so the two are comparable.

**240 classical episodes, 18.8 min** (S0/S2/S4/S6/S7 × C1/C2 × 24).

**Finding — `C2_gain_sched` is not a second baseline where the claim lives.** It is *identical* to C1 on
every h = 1 cell by construction (re-solving R from the authority returns R0 when healthy). It diverges
only where health ≠ 1: on S4 it is **worse** (1.918 vs 1.570 deg) and on S6 **better but still failing**
(66.8 vs 91.3 deg, 0 % success either way). It must not be presented as an independent baseline for the
friction claim.

**Two of my own bugs, caught by running:** `--arms` silently added both classical arms regardless of the
filter, and `--append` had a duplicate `rows = []` that discarded the merged rows.

**Host constraint (recorded):** 4 workers now die with `numpy._ArrayMemoryError` / `WinError 1455` —
the system *commit limit*, not free RAM (2.4 GB free). Classical pass runs at 2 workers; RL arms load
torch and must run **separately at `--procs 1`**, merging with `--append`.

**Pending:** the RL pass (handed to the researcher). Until it lands, B.1 is a baseline table and the
report says so in a banner. Q-01 stays OPEN.

**Next:** RL pass → verdicts; then C-lite.

---

## 2026-11-06 — D.3: fault taxonomy behind flags (45 tests, flags-off bit-identical)

**Done.** `satellite_adcs/fault_taxonomy.py` + plumbing in `dynamics.py`, `sensors.py`, `simulate.py`;
`tests/test_fault_taxonomy.py` (13 tests). Tests **32 → 45**, all green. Historical default path
**0.000e+00** unchanged (reproducibility guard re-run).

**Families implemented, all default OFF**
- wheel: `dead`, `locked`, `ramp` (h = max(floor, 1 − rate·(t−t₀))), `intermittent` (period/duty/depth);
- sensor: gyro **bias step**, **star-tracker dropout** (channel absent, not noisy — the MEKF keys off
  `"st" in meas`);
- saturation was already present (wheel-speed clip, G12) and is now exercised by a test.

**The modelling decision that matters (D-14):** `locked` ≠ `dead`. A dead wheel free-spins under bearing
friction and still reacts on the structure; a jammed wheel does neither. Conflating them with a single
`h = 0` would have been wrong, and the regression test discriminates the two on wheel speed.

**Implementation risk contained:** the lock mask is applied only when `locked_any` is true, so with no
locked wheel the old expression is evaluated byte-for-byte. That is why the guard still reads
0.000e+00 rather than "close enough".

**Three of my own test expectations were wrong and caught by running them** — the gravity gradient means a
body with all wheels locked is *not* perfectly still (only the wheel contribution vanishes); I commanded
the locked wheel instead of a healthy one; and I had the wheel-speed sign inverted (`J_w·dω/dt = −τ_eff +
τ_f`, so a positive command drives the wheel negative). Each is now asserted with the correct physics.

**Also created:** `docs/research/CLAIMS_TABLE.md` — 18 claims, each mapped to an artifact and a status
(SUPPORTED / PARTIAL / OPEN / REFUTED / FORBIDDEN). C-09 (the central question) is OPEN; C-10, C-15, C-16
are FORBIDDEN. Freeze-gate prerequisite.

**Next:** B.1 evaluation harness (classical arms runnable now; RL arms wait on the training runs).

---

## 2026-11-06 — B.0: D4 checkpoints ARE re-evaluable (friction cells)

**Done.** `scripts/b0_checkpoint_reuse.py` — hash verification, controller identity, observation
reconstruction, command-level equivalence, SB3 load test. Results in `results/b0/` +
`reports/b0_checkpoint_reuse.json`.

**Result**
- **Hashes MATCH** all six files against `reports/m1_checkpoint_hashes.json`.
- **Wrapper `K` ≡ `ADCSController.K`: 0.000e+00**; scale identical; LVLH reference identical. (M1-C's
  mis-weighted-wrapper defect is genuinely fixed, not just declared.)
- **Command-level equivalence: 0.000e+00 over 40 perturbed states** — the 15-dim observation rebuilt from
  a `residual_fn` payload reproduces the classical command exactly.
- All three D4 policies **load and predict** under the current SB3.

**Two test-design corrections, both mine, both caught by measurement**
1. A *trajectory* comparison is impossible: the two harnesses draw their own orbit anomaly and noise
   stream, so they start 7.6 km / 8.4 m/s apart at t = 1 s. It measures the RNG, not the controller.
   The criterion was changed to command-level equivalence and that change is recorded in **D-13**.
2. The first state in the sweep returned `tau = [0,0,0]` from the classical path — the phase manager's
   documented one-call zero command while it flips `detumble → pointing`. Warmed past it; the remaining
   40 states match to zero.

**Verdict: RE-EVALUATE for h = 1 cells (S0, S2).** h ≠ 1 cells must be **retrained**, because the wrapper
adds the residual to `tau_des` *before* the allocator (health-inverted) while `run_episode` adds it to the
**already-allocated** wheel torque. Retraining those cells is step B.1.

**Reproducibility gap found:** D4's `config.json` predates the c7fa879 fix and records neither
`reward_shape` nor `friction_range` (**Q-13**). The training configuration is only recoverable from the
commit record: `--reward_shape log --friction_max 3e-4`.

**Next:** B.1 — 5 seeds × {SAC, PPO} with the flags above, plus the classical arms.

---

## 2026-11-06 — Run charter recorded; housekeeping (D-12, Q-12)

**Done**
- **D-12 recorded** — authorisation for the B → C-lite → D → freeze → MIL → SIL run. **S-1** E-1 (MIL),
  E-2 (SIL), E-3 (embedded profile, host-side only) authorised in that order after the freeze;
  **E-4 (HIL) not authorised**. **S-2** four Phase-E answers: software-only MIL/SIL target (no real-time
  target until HIL), HIL hardware undecided → proposal produced at the HIL gate, MIL+SIL ≈ 4 weeks,
  **C99 core** with the Python implementation as reference oracle. **S-3** commit **and push** each step.
  Charter filed as `docs/AGENT_RUN_PROMPT.md`; `MASTER_ROADMAP` authorisation legend updated.
- **Q-12 resolved** — two latent defects, both fixed with the default path bit-identical:
  - `initial_speed_rad_s` was documented in `config/actuators.yaml` and **read by nothing**; the wheels
    always started at rest. Now honoured by `SpacecraftDynamics.reset()` (default `0.0`).
  - `FrictionHealthEstimator.prime()` ran **before** `dyn.reset()`, so the first innovation used a
    pre-reset wheel speed. Moved after it. Numerically harmless today (zero reference + the `tau_min`
    guard both absorb it), latent at any non-zero initial wheel speed.
- **Housekeeping** — `codes/README.md` rewritten to the actual layout (it claimed `simulation/` was the
  shared MIL core and that Phase 1 was at the smoke-test gate); `requirements.txt` refreshed and
  `bsk-rl==1.3.0` marked **LEGACY** because it pins `pytest==7.3.1` and breaks the suite on Python ≥ 3.12.
- **Tests 29 → 32** (`tests/test_config_honoured.py`), all green. **Reproducibility guard:** the four
  parity cases reproduce the pre-hook capture to **0.000e+00** — no default number moved.

**Schedule:** on plan (Phase A + housekeeping inside week 0).

**Next:** Phase B.0 — D4 checkpoint reusability.

---

## 2026-11-06 — Phase A: foundation closed

**Done**
- **Estimator ceiling documented** (A1). Addendum A1 appended to `M34_RLS_uncertainty_audit.md` —
  append-only, proven: 736 original lines byte-identical (md5 `22a14be4…`), 60 lines added. Establishes
  that perfect fault knowledge is worth **0.04–0.06 deg / ≈4 pp** on multiplicative faults, **exactly 0**
  on additive ones (oracle ≡ unity bit-identically), and **−0.825 deg** for a dead wheel.
- **Durable errata** (A2). The M3.3-B errata is now emitted by the report *generator*
  (`write_report()`), so no regeneration can lose it. Report rebuilt from the saved `run.json`:
  **8 lines added, 0 removed**, all 576-episode numbers unchanged.
- **Living documentation** (A3): `MASTER_ROADMAP.md` (authoritative, with authorisation legend),
  `DECISIONS.md` (D-01…D-11), `EXPERIMENT_REGISTRY.md` (E-01…E-22 with valid/retracted status),
  `OPEN_QUESTIONS.md` (Q-01…Q-12).
- **Scope decision D-07**: HIL returns to the thesis on the researcher's instruction, scheduled strictly
  after MIL → SIL → architecture. `1967326` is superseded on scheduling only; the claims restriction
  stands.
- Tests: **29/29 passing** after the phase.

**Changed state:** three statements in the M3.3-B report are now formally superseded (the "estimates are
good" line, `P1 = PASS` as vacuous, and "threshold too tight" as the root cause). Nothing historical was
deleted.

**Next autonomous action:** Phase B.0 — check whether the D4 checkpoints are validly re-evaluable through
`residual_fn`, which decides whether Phase B costs ~1 h (re-evaluate) or ~3–4 h of training.

---

## 2026-11-06 — M3.4: RLS uncertainty audit (read-only)

**Done.** `M34_RLS_uncertainty_audit.md` (736 lines, 13 sections). No source, threshold or artifact
modified; one new file.

**Findings**
- The stored matrix **is** the inverse information matrix — verified to 4 dp against recorded traces
  (11.5499 vs 11.5505; 12.0673/12.0674; 16.5432/16.5432).
- `sigma_h = 1/sqrt(Σ(τ−τ̄)²)`, units **(N·m)⁻¹**, equal to `std(h)/sigma_v` with implicit
  `sigma_v = 1 N·m` — 100 × `tau_max`, 3896 × the observed residual.
- The gate is **dimensionally invalid**: same physics reports **11.55** in N·m and **0.0124** in mN·m.
- The mis-scaling is also an **adaptation** defect (`P` *is* the gain): from a t=0 fault `h` stalls at
  0.602 (truth 0.50); mid-flight it does not move at all (0.9997 vs 0.5) while batch LS on the same
  recorded data returns **0.4807**.
- **Correction to my own earlier reading:** over 24 seeds the h=0.5 estimate is **biased +0.106**
  (max error 0.308, min 0.533). A single-seed value had suggested otherwise.
- Refuted: the large condition number (`6e5–1.2e6`) is a **scale** artifact, not collinearity
  (`corr(h, tau_f) ≈ +0.14…+0.20`); normalising by `tau_max` would **not** open the gate (0.124–0.194).
- Blocking fact: **no wheel-speed sensor exists** (`sensors.py`), and the wheel equation is otherwise
  exact — so any valid covariance needs a sensing model plus a model-error budget.

**Verdict:** CONDITIONAL GO.

---

## 2026-11-06 — M3.3-B: state-aware allocation grid (n = 24)

**Done.** `scripts/m33b_state_aware_allocation.py` — the saved harness that was missing. 8 scenarios ×
3 arms (oracle / estimated / unity) × 24 seeds = **576 episodes, 12.7 min**. Per-episode artifacts, atomic
writes, `--report-only`, BLAS pinned per worker (unpinned, the pool dies at spawn at 2.1 GB free).

**Result:** the state-aware policy is **inert**. Estimated arm bit-identical to the no-knowledge arm in
**192/192** paired cells; **0** DEGRADED wheel-steps; `sigma_h` never below 1.66 against a 0.1 gate.

**Retraction:** "RW1 50 % is certified DEGRADED and improves 0.577 → 0.441 deg" — both numbers reproduce
exactly at T=300 s **with `state = UNKNOWN`**, and a forcibly-set DEGRADED gives 0.568. The gain was the
no-compensation arm during a transient.

**Preserved:** n=1 preflight and both parity captures archived under `results/m33b_preflight_n1/`.

---

## 2026-11-05 and earlier — M1 → M3 (condensed; see `IMPROVED_RESEARCH_ROADMAP.md`)

- **M1-A** correct wheel residual `tau_f = tau_cmd + J_w dw/dt` (5e-18 vs the plant); retracted D5's
  "excitation limit" (it had been measured with the controller switched off).
- **M1-B** retracted the D4 `p < 0.001` (unit of analysis).
- **M1-C** LQR path parity **FAILED** → produced D-02 (residual moved inside the classical loop).
- **M2** B2's "win" retracted after mechanism check (false-dead `h_hat` saturated every wheel).
- **M3** joint `(h, tau_f)` RLS validated under verified fault injection.
- **Levers:** L1 closed, L3 closed, L4 live but captured by a one-line rule.
- **D4:** residual RL restores 1° under Coulomb where LQR gets 0/12, at a measured nominal cost — a
  trade-off, 3 seeds.
