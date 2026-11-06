# DECISIONS — research decision record

Append-only. Each entry: what was decided, why, the evidence, and whether it is still in force.
A decision that is superseded is marked, never deleted.

| id | date | decision | evidence / rationale | status |
|---|---|---|---|---|
| **D-01** | 2026-11 | **Residual RL is the primary architecture** — `tau_des = tau_LQR + alpha * delta_tau_RL` — not absolute-action RL | absolute RL must relearn allocation, limits and actuator geometry; the audit's architecture review rejects it as primary. LQR is baseline/reference/fallback | in force |
| **D-02** | 2026-11 | **One loop for every arm.** The residual executes *inside* the classical loop via `residual_fn`; a zero residual is bit-identical by construction | M1-C failed: hosting the classical controller inside the RL wrapper gave a "baseline" that applied LQR from t=0 while the true controller ran a detumble phase (median diff 0.032 deg). Inversion gives parity by construction (0.0e+00 over 8 runs) | in force |
| **D-03** | 2026-11 | **The oracle allocator is declared, not hidden.** `allocate_torque(health=None)` inverts *ground-truth* health (G13) | each privileged read of truth state is an explicit scope item; without this the "fault-tolerant" claim carries an unstated asterisk | in force — asterisk removed only by Phase C |
| **D-04** | 2026-11 | **L1 and L3 levers are CLOSED; L4 is live but captured; do not fund training on them** | `LQR(h_hat) == LQR(h_true)` in every case (L1); ±20 % inertia costs ≤11 % and never the criterion (L3); bang-bang is 2.71× faster than LQR but a one-line rule already captures it (L4) | in force |
| **D-05** | 2026-11 | **D4 is reported as a TRADE-OFF, and its `p < 0.001` is RETRACTED** | episodes from one policy are not independent; the unit of analysis is the training seed (n=3 → minimum attainable two-sided p = 0.25). Effect is large and consistently signed but not established at method level | in force |
| **D-06** | 2026-11 | **The confidence model is NOT to be rescaled.** Fix the mathematics, not the output; audit before implementing | audit: `sigma_h` has units (N·m)⁻¹, equals `std(h)/sigma_v` with implicit `sigma_v = 1 N·m` (100 × tau_max); the same physics reports 11.55 in N·m and 0.0124 in mN·m. Rescaling would open the gate on a biased estimate (+0.106 at h=0.5) and convert inertness into a false HEALTHY | in force |
| **D-07** | 2026-11 | **HIL RETURNS TO SCOPE, scheduled strictly last** — MIL → SIL → embedded profiling → HIL | researcher decision. Supersedes `1967326` *on scheduling only*. The claims restriction stands: no hardware / real-time / flight-readiness claim from MIL/SIL evidence | in force |
| **D-08** | 2026-11 | **Errata live in the report GENERATOR**, not only in the rendered file | the M3.3-B report is machine-generated; a pointer added only to the markdown is destroyed by the next `--report-only`. 8 lines added, 0 removed, on regeneration | in force |
| **D-09** | 2026-11 | **The Phase-B classical baseline is nominal LQR + ORACLE allocation** | A1: perfect health knowledge is worth 0.04–0.06 deg on multiplicative faults and exactly 0 on additive ones. The oracle arm is therefore the *hardest* fair baseline and is available without waiting for Phase C | in force |
| **D-10** | 2026-11 | **≥5 training seeds per arm; task metrics only, never return magnitude** | 5 is the floor for a two-sided sign test (min p = 0.0625); returns are comparable only within one reward function and horizon | in force |
| **D-11** | 2026-11 | **Multiplicative and additive fault families are treated as structurally different, not as one "fault"** | under pure friction the allocator has nothing to invert, so S2's oracle and unity arms are bit-identical — the friction failure is information-invariant | in force |
| **D-12** | 2026-11-06 | **Run authorisation for the B → C-lite → D → freeze → MIL → SIL run** (`docs/AGENT_RUN_PROMPT.md`). Supersedes the roadmap where they conflict: **S-1** Phase E items **E-1 (MIL), E-2 (SIL), E-3 (embedded profile, host-side only)** are AUTHORISED in that order after the architecture freeze; **E-4 (HIL) is NOT authorised**. **S-2** the four Phase-E questions are answered for this run: (1) MIL/SIL target = pure software on this PC + a second process, no real-time target until HIL; (2) HIL hardware undecided — a proposal is produced at the HIL gate; (3) timebox MIL + SIL ≈ 4 weeks, HIL a later stage; (4) MIL-1 language = **C99 core** (no dynamic allocation, no libc beyond `math.h`) with the Python implementation as reference oracle. **S-3** commit **and push** each completed step to `origin/residual-rl` (supersedes "local only") | researcher instruction. Phase F remains `[PLANNED]`; the AdaJEPA/world-model arm and Basilisk-as-validation-plant stay out of scope | in force |

## Standing prohibitions (not decisions, invariants)

- Never weaken a baseline to favour RL.
- Never change an experimental criterion after seeing results without a dated entry here.
- Never quote a number whose artifact is not in `EXPERIMENT_REGISTRY.md` as valid.
- Never claim hardware validation before hardware experiments exist.
