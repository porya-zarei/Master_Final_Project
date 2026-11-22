# Control Architecture Specification — CCR v2

**Document:** `CONTROL_ARCHITECTURE.md`  
**Status:** Research proposal / implementation specification (not validated flight software)  
**Authority:** This document defines the intended control architecture and research contribution. `AGENT_MISSION.md` defines project workflow and phase gates. If implementation convenience conflicts with this document, preserve the architecture and report the conflict rather than silently redesigning it.

---

## 1. Mission and design objective

Implement and evaluate a fault-tolerant attitude-control architecture for a nanosatellite ADCS. The architecture combines:

- a strong deterministic classical controller as the primary control backbone;
- actuator capability estimation that describes what torque can actually be produced;
- sensor-state and estimator-quality awareness;
- a learned residual policy that proposes *additional* control, never replaces the baseline controller;
- a deterministic authority mechanism that limits the learned residual based on control need, trust, directional capability, uncertainty, and control validity;
- actuator allocation, command limits, and supervisory fallback.

The research question is not simply whether RL can control a spacecraft. It is:

> Can capability-informed, uncertainty-aware, directionally constrained residual learning improve fault recovery and generalization over a strong classical controller, while preserving deterministic fallback and remaining computationally practical?

The project must test this claim against strong baselines and ablations. Do not present it as established fact or claim formal stability/safety unless the implemented analysis actually proves it.

### Primary objective

Show a measurable benefit from the proposed architecture over a carefully tuned classical baseline across nominal conditions, actuator degradation/failure, sensor faults, model mismatch, and held-out fault combinations.

### Secondary objectives

- keep the architecture interpretable and modular;
- avoid expensive online optimization or online Riccati solves in the control loop;
- support CPU inference and later C/C99 portability;
- allow the same controller interfaces to run with fast simulation, Basilisk, and eventually HIL.

---

## 2. Architectural invariants

These principles must remain true in the implementation.

1. **Physics determines feasible control.** The learned policy cannot create actuator authority that does not physically exist.
2. **Classical control remains the backbone.** RL is a bounded residual correction, not a replacement controller.
3. **Need and trust are separate.** A large control error can create a need for correction but does not imply the RL policy is trustworthy. High trust does not imply a correction is needed.
4. **Capability and confidence are different quantities.** Estimated actuator capability describes achievable control; confidence describes how reliable that estimate is.
5. **The gate is deterministic and non-learned.** The policy proposes a residual. Deterministic logic decides how much may pass.
6. **Allocation is authoritative for feasibility.** The gate is not a full actuator feasibility solver. The allocator and downstream command checks enforce physical constraints.
7. **Unknown or invalid state fails conservatively.** NaN, stale estimates, invalid sensor state, or an unsupported supervisor mode must not increase RL authority.
8. **The deployed gate must be in the training loop.** Train the policy with the same gate/authority logic intended for evaluation and deployment.
9. **No fault labels are required by the policy at runtime.** Fault hypotheses may be used by a supervisor/diagnostic module, not leaked as privileged labels to the policy observation unless a separate experiment explicitly tests this.
10. **Fallback remains executable without the learned policy.** RL disabled, unavailable, invalid, or rejected must still yield a valid baseline command.

---

## 3. Control-stack overview

```text
Reference / Mission Target
          |
          v
Attitude & Rate Error ---------------------+
          |                               |
          v                               v
 State Estimator                    Sensor / Estimator
 (attitude, rates, uncertainty)      Validity & Observability
          |                               |
          +---------------+-----------------+
                          |
                          v
                Control Validity / Supervisor
                          |
             +------------+----------------------+
             |                                   |
             v                                   v
  Classical Backbone                    Capability Estimator
  LQR / PD + optional DOB/ESO           RW + MTQ achievable authority
             |                                   |
             v                                   |
      Nominal Torque tau_base                  |
             |                                   |
             +------------------+------------------+
                               |
                               v
                      RL Residual Policy
                      proposes tau_RL_raw
                               |
                               v
                Deterministic Authority Gate
             need rho × trust alpha × directional G
                               |
                               v
                    Gated Residual tau_RL
                               |
                               v
                  Torque Combination / Limits
                  tau_request = tau_base + tau_RL
                               |
                               v
                    Actuator Allocator
                  RW torque + MTQ dipole
                               |
                               v
                 Command Safety / Rate / Saturation
                               |
                               v
                       Actuator Dynamics
                               |
                               v
                     Spacecraft Plant
```

The exact ordering of allocation, actuator-space filtering, anti-windup, and achieved-torque feedback must be made consistent. Do not implement separate filters that unknowingly fight one another.

---

## 4. Signals and conventions

Create explicit typed interfaces for at least the following.

### State and error

- attitude estimate (quaternion);
- angular velocity estimate;
- reference attitude and reference angular velocity;
- attitude error representation;
- rate error;
- estimator covariance or selected uncertainty summary;
- observability / sensor-validity indicators;
- previous applied command and actuator feedback.

### Capability

Per actuator and/or actuator group:

- nominal effectiveness/gain estimate;
- conservative lower and upper bounds;
- bias estimate and bound;
- friction/stiction or dead-zone information when modeled;
- saturation and rate limits;
- confidence/uncertainty;
- stale/invalid/abstaining status.

### Control diagnostics

Log every control cycle (or at a defined decimated rate):

- `tau_base`;
- `tau_rl_raw`;
- need scalar `rho`;
- trust scalar `alpha`;
- directional gate `G`;
- gated residual;
- requested torque;
- allocator output;
- actuator command and achieved output;
- validity/mode;
- rejected-command reason;
- estimator and capability confidence.

Keep truth-state data out of the controller observation. Truth is for reward calculation, debugging, and evaluation unless an explicit privileged-training experiment is defined.

---

## 5. B1 — Estimation, observability, and confidence

The estimator provides the control state and uncertainty; it must not silently turn sensor failure into a confident state.

### Responsibilities

- estimate attitude and angular rate;
- track sensor validity, bias, timing, and consistency;
- provide covariance or conservative uncertainty metrics;
- expose observability/validity metrics to the deterministic gate and supervisor;
- support sensor-fault injection and estimator recovery.

An MEKF is a candidate implementation. The architecture does not require one specific estimator if another is justified and validated.

### Required outputs

A typed estimator output should include state, covariance/uncertainty summary, per-sensor status, timestamp/age, and a validity flag.

### Observability confidence

Define a bounded scalar or vector `gamma_obs` in `[0, 1]`, or an explicit validity/quality representation. It must be based on documented measurable estimator/sensor conditions, not an arbitrary hard-coded “healthy” value.

Document:

- definition and inputs;
- calibration and thresholds;
- monotonic behavior (worse observability cannot increase RL authority);
- stale-data and invalid-data behavior;
- fallback when confidence cannot be computed.

Sensor validity and actuator capability are separate. A good actuator estimate does not make an unobservable attitude state trustworthy.

---

## 6. B2 — Fault symptoms and diagnostic interface

The policy should not depend on a fault label such as “wheel 2 failed” by default.

Build a fault-symptom interface from measurable information, potentially including:

- requested versus achieved torque residual;
- actuator command versus measured actuator response;
- momentum/speed and saturation indicators;
- rate/attitude response mismatch;
- sensor innovation and consistency metrics;
- temporal summaries of symptoms.

Use a normalized, documented vector `s`. Avoid duplicating information without reason. Any learned symptom encoder must be versioned and tested.

Fault-hypothesis classification belongs to the supervisor/diagnostics, not the residual policy. It may support mode transitions and recovery strategies. Hypothesis uncertainty must be represented; uncertain diagnosis must not be treated as confirmed fault truth.

---

## 7. B3 — Actuator capability and Attainable Moment Set (AMS)

This block estimates *achievable torque*, not a percentage health score.

### 7.1 Reaction wheels

Represent each wheel's axis, torque bounds, momentum/speed bounds, dynamics, effectiveness, bias, and uncertainty. Do not assume a wheel is characterized adequately by one scalar health value.

For a simplified wheel torque model, effectiveness may be represented by a gain `g_i`, with uncertainty interval `[g_i_min, g_i_max]`. Bias, friction, stiction, dead-zone, dynamics, and momentum constraints must be represented separately where applicable. The simplified effectiveness-only model is valid only for scenarios that explicitly exclude those effects.

Wheel momentum/speed constraints can reduce available torque in a direction or over a time horizon. The capability calculation must state whether it is instantaneous, horizon-limited, or based on a simplified envelope.

### 7.2 Magnetorquers

For magnetic torque:

\[
\tau_{MTQ} = m \times B
\]

where `m` is commanded magnetic dipole and `B` is the estimated local magnetic field.

MTQ authority is field-dependent and cannot be treated as a fixed three-axis torque box. The instantaneous torque lies in the plane perpendicular to the magnetic field. Evaluate instantaneous allocation and, separately, orbit-averaged authority/margin for longer-horizon assessment. Do not use orbit-average authority to claim instantaneous feasibility.

### 7.3 AMS representation

For a simplified bounded linear actuator model:

\[
\tau = B u,\qquad |u_i|\le u_{max,i}
\]

the attainable moment set is:

\[
\mathcal{T} = \{Bu : |u_i|\le u_{max,i}\}
\]

and its directional support function is:

\[
h_{\mathcal{T}}(v)=\sum_i |(B^T v)_i|u_{max,i}.
\]

Use conservative bounds where capability is uncertain. A directional margin may be defined relative to a nominal capability:

\[
m_{dir}(v)=\frac{h_{cons}(v)}{h_{nom}(v)}
\]

with numerically safe handling when the denominator is near zero.

**Important limitations:** the support function gives directional extent; it does not guarantee that an arbitrary multi-axis torque vector is realizable. The AMS model is also not automatically equivalent to a dynamic actuator with bias, stiction, momentum limits, or delay. Those require separate modeling or a richer feasible set. The allocator is responsible for finding a feasible command (or reporting infeasibility).

### Outputs

- conservative capability representation;
- directional capability/margin;
- uncertainty/confidence;
- saturation/constraint state;
- stale or invalid status;
- diagnostic details for logging.

### Validation

Test known geometry and bounds, compare predicted capability against sampled actuator commands, test degraded and failed actuators, test near-singular geometry, and verify conservative estimates do not overstate authority.

---

## 8. B4 — Fault hypothesis supervisor (supervisor-only)

Maintain discrete fault hypotheses or modes only where they help supervisory decisions.

Examples include:

- nominal;
- suspected degradation;
- confirmed degradation;
- unknown/invalid;
- recovery.

Hypotheses may use diagnostic evidence, persistence, and confidence. Do not make an uncertain hypothesis equivalent to a confirmed fault. The policy remains fault-label-free by default.

The supervisor must have:

- explicit transition table;
- transition guards;
- persistence/hysteresis;
- entry/exit actions;
- reset/recovery criteria;
- behavior for contradictory or missing evidence.

Avoid a large hand-built fault taxonomy until experiments justify it.

---

## 9. B5 — Classical control backbone

The baseline must be strong, tuned, and independently validated before RL is allowed to claim benefit.

Candidate:

- quaternion-based attitude error;
- rate feedback;
- LQR or a justified PD/LQR formulation;
- optional disturbance observer (DOB/ESO) for measurable disturbances/model mismatch;
- a small set of precomputed gain schedules if justified by operating conditions.

No online Riccati solution is required in the control loop. Gain schedules must be deterministic, bounded, documented, and tested.

### Controller contract

Input: estimated state, reference, and only the capability/validity data required by the baseline.

Output: nominal desired body torque `tau_base`, diagnostics, and controller status.

The classical controller must run when RL is disabled. This is the baseline for all research comparisons.

Do not weaken or under-tune the baseline to make RL appear beneficial.

---

## 10. B6 — Residual RL policy

The policy proposes a correction:

\[
\tau_{RL,raw} = \pi_\theta(z)
\]

where `z` is a documented observation composed of permitted estimates, errors, symptoms, actuator feedback, capability information, and a short history if needed.

Candidate observation fields (justify and ablate):

- attitude error representation;
- angular rate and rate error;
- reference/mission context;
- normalized requested and achieved torque;
- wheel momentum/speed and saturation;
- MTQ state and magnetic field;
- actuator capability and uncertainty summaries;
- sensor/estimator validity;
- fault symptoms;
- previous applied residual/command;
- supervisor mode only if appropriate.

Use a compact observation and avoid feeding raw truth. A privileged critic may be used during training only as a clearly separate experiment; it must not leak truth to the deployed actor.

SAC is a candidate algorithm, not an architectural requirement. Compare algorithm choice only if the comparison answers a research question.

### Policy output

Prefer a bounded, normalized residual action. Convert it to torque using explicit configured scales. The policy must not directly command actuator hardware.

### Reward

Reward should reflect mission control performance, actuator effort, constraint violations, and recovery. Do not reward simulator-specific artifacts. Document terms, units, weights, and sensitivity. Avoid hiding safety constraints inside a reward alone.

---

## 11. B7 — Deterministic residual authority gate (core proposed contribution)

The RL output is a proposal, not an accepted command. A deterministic gate decides the permitted correction.

Separate three concepts:

### A. Need — `rho`

`rho ∈ [0,1]` represents how much correction is needed because the baseline controller is insufficient for the current state/performance condition.

Candidate inputs include:

- attitude error / Lyapunov-like error measure;
- rate error;
- baseline tracking performance;
- disturbance or model mismatch indicators;
- saturation or achieved-versus-requested discrepancy.

The exact formula, scaling, thresholds, filtering, and hysteresis must be derived, documented, and tested. Do not equate large attitude error with permission to use large RL action unconditionally.

### B. Trust — `alpha`

`alpha ∈ [0,1]` describes how much trust to place in the learned residual and the information supporting it.

Potential factors:

- estimator uncertainty;
- observability confidence `gamma_obs`;
- capability-estimation uncertainty;
- policy operating-domain / OOD indicator, if implemented;
- supervisor mode and data validity.

Define each factor operationally. If trust is composed from multiple factors, specify the combination rule (e.g. conservative minimum, product, or justified alternative), its monotonicity, and behavior for missing/invalid data. Do not use vague confidence values with no measurable definition.

### C. Directional gate — `G`

`G` limits correction in directions where the system has insufficient or uncertain capability.

A diagonal gate `G = diag(g_x,g_y,g_z)` is a computationally cheap heuristic, not a full representation of skewed actuator geometry or coupled feasible sets. Define how each axis value is calculated from capability and uncertainty. Test the diagonal gate against arbitrary wheel-axis geometry and, if needed, compare it with a geometry-aware projection or allocator-based gate.

### 11.1 Gate combination

A baseline proposed form is:

\[
\tau_{RL} = \rho\,\alpha\,G\,\tau_{RL,raw}
\]

where:

- `rho` controls *need*;
- `alpha` controls *trust*;
- `G` controls *directional capability*.

This is a research hypothesis, not a proven stability result. The exact order and dimensional interpretation must be consistent. If `G` is a matrix, ensure the vector multiplication and frame are defined. Torque residuals must be in the same body/reference frame as the baseline torque.

### 11.2 Deterministic behavior

The gate must:

- be independent of the learned policy;
- be deterministic for a given input;
- be bounded;
- monotonically reduce authority when uncertainty/validity worsens;
- rapidly decrease authority on invalidity or detected danger;
- restore authority conservatively (slew/hysteresis);
- reject NaN/Inf and stale data;
- have explicit safe fallback behavior.

Define and test asymmetric slew: authority can decrease rapidly but recover more slowly, if justified. Do not allow a stale or invalid state to increase authority.

### 11.3 What the gate does not guarantee

The gate alone does not prove stability, safety, or actuator feasibility. It does not replace:

- command limits;
- actuator allocation;
- anti-windup;
- safety filter;
- supervisory fallback;
- closed-loop validation.

Do not call it a safety guarantee without a formal analysis.

---

## 12. B8 — Control validity and operating modes

Implement a control-validity representation based on measurable conditions rather than a single opaque “health” score.

Candidate validity factors:

- effective actuator rank/authority;
- instantaneous MTQ feasibility and orbit-averaged margin (kept distinct);
- estimator observability/uncertainty;
- sensor validity and data freshness;
- capability estimate validity;
- model residual / unexpected response;
- saturation;
- numerical validity;
- policy validity and inference status.

Proposed supervisory modes (names may be changed only with documented rationale):

- **M0 — Nominal:** classical backbone + RL residual permitted within nominal gate.
- **M1 — Suspected degradation:** conservative authority and diagnostic monitoring.
- **M2 — Confirmed degradation:** capability-aware control/allocation; residual permitted only within validated conditions.
- **M3 — Unknown/invalid/unsafe:** RL residual disabled; use deterministic fallback and safe operating logic.
- **M4 — Recovery:** gradual re-enable with hysteresis after evidence of recovery.

Mode behavior must be explicitly defined. Unknown status must not be interpreted as healthy. The architecture should support reduced pointing performance or safe-mode behavior when the physical system cannot achieve the requested objective.

---

## 13. B9 — Allocation and command path

The control path is:

1. classical controller computes `tau_base`;
2. policy proposes `tau_RL_raw`;
3. deterministic gate produces `tau_RL`;
4. combine and validate `tau_request = tau_base + tau_RL`;
5. allocator maps requested body torque into RW torque and MTQ dipole commands;
6. actuator-space limits, rates, and safety constraints are enforced;
7. actuator dynamics generate achieved torque;
8. feedback (command/achieved torque and saturation) is returned to estimator, symptoms, controller anti-windup, capability estimator, and logs.

### Allocation considerations

- RW torque, speed, momentum, and rate limits;
- MTQ dipole limits and field-dependent torque;
- actuator effectiveness and uncertainty;
- feasible allocation objective and priorities;
- numerical failure and infeasibility handling;
- achieved-torque calculation.

Do not assume RW and MTQ can provide equivalent instantaneous torque. MTQ torque is field-dependent and constrained by `m × B`. Momentum unloading is a longer-horizon objective and must not be confused with instantaneous attitude torque allocation.

Use one coherent constraint enforcement path. Ensure requested, allocated, commanded, and achieved torque are logged separately.

---

## 14. B10 — Optional slow recalibration

Optional online recalibration is outside the first working architecture.

If later implemented, it must:

- run at a slower timescale than attitude control;
- have bounded parameter updates;
- be frozen on low confidence, invalid sensing, or supervisor fallback;
- log before/after parameters and reasons;
- support rollback to validated parameters;
- not alter the safety gate in an unreviewed manner.

Do not add this block merely to make the architecture look adaptive.

---

## 15. Training and evaluation requirements

Training must include the deployed observation interface and gate logic. The policy should experience estimator errors, gate reductions, actuator saturation, and relevant delays during training.

Use separate training, validation, and held-out test distributions. Randomize parameters only within physically justified ranges. Preserve seeds and configuration snapshots.

### Required comparison arms

| ID | Controller |
|---|---|
| A0 | Classical LQR/PD baseline |
| A1 | Classical + oracle allocation/capability (where meaningful) |
| A2 | Classical + DOB/ESO |
| A3 | Strongest classical baseline (capability-aware allocation/gain scheduling as justified) |
| A4 | Unstructured RL residual |
| A5 | RL residual + need `rho` |
| A6 | RL residual + `rho` + oracle capability/trust gate |
| A7 | Full proposed CCR architecture using estimated capability/uncertainty |
| A8 | Optional RMA-style latent/adaptation approach (secondary comparison) |

### Ablations

At minimum, isolate:

- no directional gate `G`;
- no trust/uncertainty `alpha`;
- no need scalar `rho`;
- no estimator-error/gate-in-loop training;
- no supervisory validity ladder;
- estimated capability versus oracle capability.

### Required reporting

- pointing error (RMS, percentile, maximum);
- settling time and recovery time;
- overshoot;
- angular-rate error;
- actuator effort/energy proxy;
- saturation duration/frequency;
- requested versus achieved torque error;
- failure / loss-of-control rate;
- residual authority time history;
- mode transitions and false transitions;
- computation/inference latency.

Use paired seeds and identical initial conditions/fault timelines across controller arms. Report sample counts, uncertainty intervals, effect sizes, and negative results. Predefine primary metrics and criteria before tuning on the held-out set.

---

## 16. Required test and validation gates

### Gate C0 — mathematical / unit tests

- quaternion convention and error direction;
- frame consistency;
- rigid-body equations;
- torque sign;
- actuator bounds;
- AMS support-function correctness;
- gate bounds and monotonicity;
- invalid/stale/NaN fail-conservative behavior.

### Gate C1 — classical nominal control

- nominal nadir-pointing closed-loop convergence;
- disturbance response;
- actuator saturation behavior;
- no RL in the loop;
- baseline metrics reproducible.

### Gate C2 — capability validation

- nominal, degraded, failed, biased, and uncertain actuator cases;
- predicted conservative authority versus sampled achievable torque;
- MTQ field dependence;
- near-singular actuator geometry;
- estimator uncertainty affects confidence correctly.

### Gate C3 — fault and supervisor validation

- sensor faults;
- RW degradation/failure;
- contradictory symptoms;
- unknown fault;
- stale data;
- mode transitions and hysteresis;
- recovery and fallback.

### Gate C4 — residual gate validation

- `rho`, `alpha`, and `G` independently tested;
- monotonic reductions under worsening uncertainty;
- fast authority decrease;
- bounded/slew-limited recovery;
- RL-disabled fallback;
- gate and allocator do not conflict.

### Gate C5 — RL readiness

Do not start full RL training until:

- plant validation is adequate;
- baseline is tuned;
- interfaces are frozen;
- reward and observation are documented;
- fault scenarios and metrics are reproducible;
- gate runs in the environment;
- tests C0–C4 pass.

### Gate C6 — Basilisk cross-validation

Validate fast simulation against Basilisk in deterministic matched cases. Compare attitude, angular rate, torque, wheel states, and actuator response. Document expected differences; do not hide mismatches by tuning the fast model only to RL outcomes.

---

## 17. Research hypotheses and novelty discipline

Potential contributions to investigate (not claims to make without literature review and experiments):

- **H1 / N1:** Capability-derived directional residual authority, separated from need and trust, improves recovery and reduces inappropriate learned action under actuator degradation.
- **H2 / N2:** A fault-manifold benchmark and regime map reveal where residual learning helps, fails, or is unnecessary across fault severity, observability, and actuator geometry.
- **H3 / N3:** A unified interface for sensor and actuator faults enables systematic evaluation without policy dependence on fault labels.
- **H4 / N4:** A control-validity ladder with explicit abstention/fallback improves robustness to unknown or invalid conditions.

Compare against prior work in residual RL, adaptive control, fault-tolerant allocation, stability-aligned RL, observer-based disturbance rejection, and safe/robust RL. Do not claim novelty based only on combining familiar blocks. Novelty must be established by literature review, a precise distinction, and empirical evidence.

---

## 18. Implementation rules for the coding agent

1. Read this document fully before implementing any control or RL component.
2. Translate every block into a small module with a typed contract and unit tests.
3. Implement the architecture incrementally; do not build the entire CCR stack in one PR.
4. Implement and validate the plant and classical baseline first.
5. Keep controller modules independent of Basilisk objects and simulator internals.
6. Keep policy output as a residual proposal; do not allow direct actuator commands from the policy.
7. Implement the gate as deterministic, separately tested code.
8. Keep capability estimation, confidence, and actuator feasibility distinct.
9. Make all thresholds, scales, limits, and schedules configurable; avoid unexplained magic constants.
10. Record equations, units, frames, assumptions, thresholds, and tuning provenance.
11. Never silently substitute a simpler design for a proposed block. If a simplified implementation is necessary, document the approximation, impact, and follow-up.
12. Avoid adding dependencies or abstractions without a clear need.
13. Add diagnostic logs sufficient to reconstruct every residual-gate and allocation decision.
14. Preserve a valid classical fallback at all times.
15. Report test commands and actual results. Never claim a test passed if it was not run.

---

## 19. Required deliverables

The implementation should ultimately provide:

- validated configuration for the spacecraft, orbit, sensors, actuators, controller, gate, and scenarios;
- a reproducible Basilisk truth backend;
- a fast training backend validated against Basilisk;
- estimator and observability interfaces;
- actuator capability/AMS estimator and validation;
- deterministic supervisor and control-validity logic;
- classical controller and allocator;
- residual RL policy and deployed gate;
- Gymnasium environment and training pipeline;
- benchmark runner, Monte Carlo evaluation, ablations, and statistical analysis;
- CPU inference/latency report and HIL readiness assessment;
- architecture documentation and experiment records.

The architecture is considered implemented only when the interfaces, equations, tests, diagnostics, and validation evidence exist—not merely when folders or class names have been created.

---

## 20. Initial implementation order

Follow this sequence, and do not skip validation gates:

1. Define units, frames, quaternion convention, and typed interfaces.
2. Implement and test rigid-body and actuator primitives.
3. Build the Basilisk reference spacecraft and repeatable scenarios.
4. Implement the classical controller and allocator.
5. Validate nominal pointing and matched fast-sim/Basilisk cases.
6. Add sensor/actuator fault injection.
7. Add estimator quality, capability, and AMS validation.
8. Implement supervisor/control validity and deterministic gate with no RL dependency.
9. Test gate and fallback behavior.
10. Add Gymnasium and train an unstructured residual baseline.
11. Add need `rho`, trust `alpha`, and directional gate `G` as separately ablatable features.
12. Run the preregistered benchmark, ablations, held-out tests, and statistical analysis.
13. Assess CPU deployment and HIL interfaces.

---

## Final instruction

This architecture is the research design to implement and test. Do not optimize for rapid code generation or an impressive demo. Optimize for a clean, auditable, reproducible system whose experiments can determine whether the proposed capability-mediated residual architecture is genuinely useful.
