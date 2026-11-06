# CLAIMS TABLE — every thesis claim → artifact → status

**Purpose:** the seed of Phase F, and a hard prerequisite of the architecture-freeze gate. A claim may
be written into the thesis only at the status its artifact supports. Statuses:

- **SUPPORTED** — artifact in `EXPERIMENT_REGISTRY.md` as VALID, claim matches the measurement.
- **PARTIAL** — artifact exists but the sample, the design or the baseline is insufficient for the
  strong form; the caveat must travel with the claim.
- **OPEN** — not yet measured (the phase that will decide it is named).
- **REFUTED** — measured and found false; may only be reported as a negative result.
- **FORBIDDEN** — may not be claimed at all, on any evidence currently held.

Last updated: 2026-11-06 (after D.3).

| id | claim | artifact / registry | status | what would upgrade it |
|---|---|---|---|---|
| **C-01** | Attitude frame conventions are correct (`quat_to_dcm` returns `C_BN`) | E-01, 12 tests, cross-checked vs scipy | **SUPPORTED** | — |
| **C-02** | A 6-state MEKF estimates attitude **and** gyro bias (bias converged to 3.8e-6) | E-03 | **SUPPORTED** | — |
| **C-03** | Coulomb friction at ≥ 2e-4 N·m makes the tuned LQR fail the 1° requirement completely (0/16) | E-05 | **SUPPORTED** | — |
| **C-04** | That failure is a systematic stick-slip **bias** (tight clustering across ICs), i.e. a structured error, not scatter | E-05 (n=16 × 4 magnitudes) | **SUPPORTED** | — |
| **C-05** | Perfect actuator-health knowledge is worth **≤ 0.06°** on multiplicative faults and **exactly 0** on additive ones | E-20 + M3.4 Addendum A1 | **SUPPORTED** | — |
| **C-06** | The friction failure is **information-invariant** (h = 1 ⇒ the allocator has nothing to invert; oracle ≡ unity bit-identically) | E-20 | **SUPPORTED** (structural, not empirical) | — |
| **C-07** | A residual RL layer restores 1° pointing where the LQR fails completely under friction | E-13 | **PARTIAL** — 6–8/12 vs 0/12 at **3 seeds**; the `p < 0.001` is retracted (D-05) | Phase B: 5 seeds, paired McNemar, both holds |
| **C-08** | The residual layer **costs** nominal precision (a trade-off, not a free win) | E-13 | **PARTIAL** — same 3-seed limitation | Phase B |
| **C-09** | Residual RL beats a **strong, fair** classical baseline (LQR + oracle allocation) | — | **OPEN** — Phase B; this is the central question | Phase B report |
| **C-10** | The loop is fault-tolerant **without ground-truth health** | — | **FORBIDDEN** until Phase C — the allocator reads `rw_health` truth (G13/D-03) | a coverage-validated detector (C.4) |
| **C-11** | The joint `(h, tau_f)` estimator provides a usable confidence/health decision | E-19, E-20, M3.4 | **REFUTED** — estimates accurate, but the gate never opens (0/192 episodes); `sigma_h` is dimensionally invalid | Phase C replaces the confidence model |
| **C-12** | The safety filter **guarantees** stability or safety | — | **FORBIDDEN** — D-04/word ban; only a *performance filter* may be claimed, with an intervention rate | Phase D.2 |
| **C-13** | The architecture generalises to fault families **not seen in training** | — | **OPEN** — Phase D.4; D.3 now provides the flags (locked / ramp / intermittent / sensor) but nothing has been run | Phase D.4 |
| **C-14** | Timing/quantisation robustness survives an independent software implementation | — | **OPEN** — Phase E-2 (authorised, after the freeze) | SIL-5 parity |
| **C-15** | Hardware-in-the-loop validation was performed | — | **FORBIDDEN** — E-4 not authorised; no hardware claim of any kind | explicit GO at the HIL gate |
| **C-16** | Aerodynamic / SRP / residual-dipole disturbances are modelled | — | **FORBIDDEN** — the flags are no-ops (G9) | implement them, or justify omission by order of magnitude |
| **C-17** | The controller is robust to plant uncertainty | — | **FORBIDDEN** as a general claim; only the measured statement is allowed: ±20 % inertia costs ≤ 11 % and never the criterion (E-09) | Phase D.4 held-out draws |
| **C-18** | Disturbance/actuator nonlinearities are handled (deadzone, viscous, quantisation, rate limit) | E-04 | **SUPPORTED** for the *measured* set; rate limit had **no effect** at all | — |

## Rules

1. A claim's status is set by its artifact, never by the argument around it.
2. Downgrading a status requires only this table; upgrading requires a new registry row.
3. C-09 is the thesis's central question. Until it is settled, no sentence may assert RL superiority.
4. C-10 and C-15 are the two claims an examiner will test first, because the thesis *title* implies them.
