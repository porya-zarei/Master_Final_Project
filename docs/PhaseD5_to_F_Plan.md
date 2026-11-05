# Phase D5 → F Master Plan (post-D4)

**Status at writing:** branch `residual-rl` @ `c1007f9`. Phase C evidence is complete
enough to state a claim; the friction gate (D5) is designed but not implemented.

**The claim D4 supports:** under Coulomb breakaway friction the residual policy
reaches sub-degree median pointing (0.665°, 0.841°) with 58–67 % success, where a
tuned LQR achieves **0/12** and parks at 1.578° (*p* ≤ 0.007). Its cost: degraded
nominal precision (75–100 % success vs 100 %, worse on 2 of 3 seeds).

**The open defect:** the policy spends ~30 % of its residual authority at 0.5–1°
even with no friction. D5 must remove that without losing the Coulomb gain.

---

## Phase C (remaining) — D5, D6, freeze

### D5 — friction-gated residual

**Objective.** Close the residual when no friction is present, open it when there is,
using a *physics-based* detector rather than a network or an error threshold.
§11 of `docs/Milestone_B_Actuator_Model.md` falsifies the error-magnitude gate:
the same 30–47 % authority at 0.5–1° is required under friction and harmful without.

**The detector.** Per wheel, compare commanded torque against the torque implied by
the observed wheel-speed response:

```
tau_achieved ≈ -(J_w * d(omega_w)/dt)          (per wheel, from encoder/tachometer)
slip_i       = |tau_cmd_i - tau_achieved_i|
enable       = any(slip_i > threshold)
tau_des      = tau_LQR + alpha * delta_tau * enable
```

**Reason this is defensible:** the quantity already exists. `health_estimation.py`
identifies `h` from precisely this residual (C2-h: `h = 0` in 3.2 s once commanded).
D5 reuses a measured, validated estimator instead of inventing a new one.

**Milestones**

| ID | deliverable | pass criterion |
|---|---|---|
| D5.1 | detector implemented behind a flag, default OFF | unit test: ideal wheel → gate closed; deadband wheel → gate open; historical results bit-identical with flag off |
| D5.2 | **threshold pre-registered** in writing, before any measurement | threshold and pass criteria committed *before* the run |
| D5.3 | paired evaluation, n = 24, 3 seeds, both plants | see below |
| D5.4 | gate false-open rate reported | reported, whatever it is |

**D5.3 pass criteria (pre-registered)**

- **Nominal:** success ≥ 95 % AND median ≤ 0.30° (LQR: 100 %, 0.147°).
- **Coulomb:** success ≥ 50 % AND median < 1.0° (LQR: 0 %, 1.578°).
- **Both must hold.** Restoring nominal precision by disabling the residual
  (nominal passes, Coulomb fails) is a **FAIL**, not a partial win — it would mean the
  gate simply switched off the contribution of §10.

**Risk: the detector cannot see friction at rest.** At zero wheel speed a stick-slip
wheel and a healthy one both deliver ~0 torque; slip is only observable while
commanding. Mitigation: a short excitation pulse, or accept that the gate opens only
after the error has already grown past the deadband (which is when it is needed
anyway). **This must be measured, not assumed.**

---

### D6 — confirmation and ablation

| ID | work |
|---|---|
| D6.1 | ablation: gate OFF / gate ON / always-on residual — same seeds, paired |
| D6.2 | n ≥ 24, **5 seeds** (up from 3), both plants |
| D6.3 | seed-variance report: per-seed success and final error, never only the mean |
| D6.4 | threshold sensitivity: ±1 decade, to show the result is not a tuned artefact |

**Decision point.** If D6 shows the nominal cost is not removed, the honest fallback
is to report the gate as a *partial* mitigation and keep the D4 trade-off statement.
The thesis does not depend on D5 succeeding; D4 already carries the claim.

### C-freeze

After D6: freeze the numbers, write the canonical results table, and stop changing the
plant. Everything in Phase D consumes this frozen policy.

---

## Phase D — HIL / MCU (ESP32-S3)

**Scope note.** ESP32-S3 is the experimental MCU, **not a flight-qualified OBC**. The
thesis claims a bench HIL demonstration, not flight readiness.

| ID | deliverable | risk |
|---|---|---|
| D.1 | freeze one policy, export a fixed-step forward pass (no framework, plain C or TFLite-Micro) | policy is 128×128 MLP ≈ 35 k params ≈ 140 KB fp32 — fits S3 PSRAM, tight in SRAM |
| D.2 | host↔MCU protocol at 5 Hz (UART/USB), timestamps both ends | latency budget 200 ms/step; a 5 Hz loop is comfortable |
| D.3 | **HIL: MCU computes torque, plant simulates on host** | the sim must run real-time or slower-than-real-time with a clock; currently it runs ~2000× faster, so a paced loop is required |
| D.4 | latency/jitter measurement: mean, 95th percentile, worst case | report honestly; a missed deadline is a result |
| D.5 | fault-injection in the loop (wheel dead at t = 300 s) | exercises the allocator + gate together |

**Order matters:** D.1 (does it even fit?) before D.3 (the full loop). If the policy
does not fit, the fallback is a smaller MLP retrained at D6 — which is why D6 must
precede Phase D.

---

## Phase E — thesis and defence

| ID | deliverable |
|---|---|
| E.1 | canonical results tables: every number traceable to a `reports/*.json` |
| E.2 | figures: Coulomb sweep, RL-vs-LQR paired bars with CIs, gate ROC |
| E.3 | the *negative* results section: the 1e8 LQR-weight bug, the flat-reward episode, the falsified error gate — these are methodological contributions, not embarrassments |
| E.4 | limitations: assumed friction magnitude, n = 12–24, single spacecraft model, no Basilisk cross-validation |

## Phase F — AdaJEPA (optional, never gating)

Only if D and E are complete. Would replace the fixed residual with an adaptive latent
world model. **Must not gate D or E** (standing decision).

---

## Decisions requested

1. **D5 go:** implement the friction detector and pre-register the threshold.
2. **D6 depth:** 3 seeds (faster, ~2 h) vs **5 seeds** (recommended, ~3.5 h) — the
   D4 result rested on 3 seeds with visible spread (35–67 % success).
3. **Threshold source:** (a) derive from the C2-h estimator's measured noise floor
   (recommended — defensible), (b) set from the friction magnitude (2e-4) directly,
   (c) sweep and report, which risks looking tuned.

## Recommended next action

**D5.1 + D5.2 only**: implement the detector behind a default-OFF flag, and commit the
pre-registration. No measurement until the threshold is written down. That keeps the
project's rule that a criterion is never chosen after seeing the number.

---

## D5.1 feasibility result — the naive slip differentiator FAILS

Measured before any performance run, as required. `tau_achieved = J_w * d(omega_w)/dt`
with `J_w = 2e-4 kg m^2`, period 0.2 s, LQR-only arm (a = 0), seed 2:

| plant | median slip | p95 | max | gate open @ 1e-5 |
|---|---|---|---|---|
| **ideal (no friction)** | **1.34e-4** | 1.46e-3 | 1.9e-2 | **100 %** |
| Coulomb 2e-4 | 2.27e-4 | 1.28e-3 | 1.9e-2 | 100 % |
| Coulomb 3e-4 | 3.28e-4 | 1.18e-3 | 1.9e-2 | 100 % |

**Separation between a healthy wheel and the friction to be detected: 1.7x. The
distributions overlap completely.** At any threshold that opens on Coulomb it also
opens on ideal, i.e. the gate cannot do its job.

### Root cause: the detector does not model the plant

`J_w * d(omega_w)/dt` is not equal to `tau_cmd` even on a PERFECTLY healthy wheel,
because the wheel is dynamically coupled to the body through `-omega x H_w`, and the
finite difference over a 0.2 s period (2 substeps of 0.1 s) aliases that coupling
into a spurious "slip". The estimator was measuring unmodelled dynamics and calling
it friction.

### Consequence

The D5 design in section 11 (slot 4) is **correct in principle but wrong in
implementation**: the discriminating quantity is not a raw torque-vs-speed
difference, it is the *model-based* residual. That quantity already exists and has
already been validated in this project:

- `health_estimation.py` regresses `h` from commanded torque against wheel-speed
  response using the correct model, with four guards, and was measured in C2-h:
  `h = 0.5` identified in 1.8 s, `h = 0` in 3.2 s, healthy estimate error 0.000-0.002.

**Revised D5.1:** gate on the health estimator rather than a hand-rolled difference:

    enable = (1 - mean(h_hat)) > eps_gate

with `eps_gate` pre-registered from the C2-h measured healthy error (0.002), i.e.
`eps_gate = 0.05` -- 25x above the measured healthy error and 10x below the smallest
fault (h = 0.5). This is a *measured* margin on both sides, not a tuned one.

Known limitation carried forward: like the naive version, the health estimator needs
excitation, so a wheel dead from t = 0 is unobservable (G13). The gate will therefore
open only after a command has been issued -- which is when it is needed, but this
must be reported as a property of the gate, not hidden.
