# PROGRESS_LOG — chronological, newest first

Short entries only: what was done, what it changed, and the commit. Detail lives in the linked reports.

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
