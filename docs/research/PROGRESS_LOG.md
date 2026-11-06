# PROGRESS_LOG — chronological, newest first

Short entries only: what was done, what it changed, and the commit. Detail lives in the linked reports.

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
