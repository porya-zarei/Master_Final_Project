# RESEARCH_PROTOCOL.md — CCR v2 Experimental Protocol

**Status:** Initial protocol; hypotheses and primary metrics should be frozen before final test runs.  
**Purpose:** Define how the proposed control architecture is scientifically evaluated.  
**Relationship:** `CONTROL_ARCHITECTURE.md` defines the system; `AGENT_MISSION.md` defines implementation workflow; this document defines the research questions, experiments, metrics, comparison rules, and reporting requirements.

---

## 1. Research question

Does capability-derived, uncertainty-aware, directionally gated residual learning (CCR v2) improve fault-tolerant spacecraft attitude control compared with a strong classical controller and simpler residual-RL variants—particularly in degraded, uncertain, and held-out fault conditions—without excessive actuator effort, unstable behavior, or unacceptable computational burden?

The goal is not to make RL win every scenario. Identify where RL helps, where it is neutral, and where it hurts.

## 2. Hypotheses

### H1 — Capability-mediated authority
Using actuator capability to restrict residual authority improves performance or reduces unsafe/inappropriate residual action under actuator degradation relative to residual RL without directional capability gating.

### H2 — Need/trust separation
Separating correction need (`rho`) from policy trust (`alpha`) produces better behavior than a single unconstrained residual or one opaque confidence score.

### H3 — Estimation robustness
Training and evaluation with realistic estimator uncertainty, sensor validity, and gate behavior improves robustness to sensor faults and state uncertainty compared with clean-state training.

### H4 — Fault generalization
The full architecture improves robustness on held-out fault severities, timings, combinations, and parameter variations, not merely the exact training scenarios.

### H5 — Computational practicality
The controller/gate/allocation stack can execute within the target CPU timing budget at the configured control rate with deterministic fallback when policy inference is unavailable.

These are hypotheses to test. They must not be reported as proven before results exist.

## 3. Primary and secondary outcomes

Freeze primary outcome(s) before final training/tuning. Suggested primary outcomes:

1. **Attitude error:** RMS geodesic attitude error during a predefined evaluation window.
2. **Fault recovery time:** time from fault onset to return within the defined attitude/rate performance envelope for a sustained interval.
3. **Loss-of-control rate:** percentage of episodes failing predefined pointing, rate, constraint, or recovery criteria.

Suggested secondary outcomes:

- peak attitude error;
- 95th/99th percentile attitude error;
- settling time after maneuver;
- angular-rate RMS and peak;
- wheel torque and momentum/speed constraint violations;
- MTQ dipole constraint violations;
- actuator effort/energy proxy;
- saturation time/fraction;
- requested-versus-achieved torque error;
- RL residual magnitude and authority (`rho`, `alpha`, `G`);
- gate rejection/disable events;
- supervisor transitions and false transitions;
- inference and total control-cycle latency;
- estimator innovation / uncertainty behavior.

Define units and evaluation windows for every metric in code and documentation. Do not mix transient acquisition with steady-state pointing results without reporting both.

## 4. Scenario taxonomy

Build a scenario catalog with stable IDs and parameterized profiles. Every episode must be reproducible from a scenario config and seed.

### S0 — Nominal
- no injected faults;
- nominal actuator/sensor parameters;
- initial attitude and angular-rate perturbations;
- target acquisition and steady nadir pointing.

### S1 — Reaction-wheel effectiveness degradation
- gradual or abrupt gain reduction;
- severity levels spanning mild through near-loss;
- single-wheel and multiple-wheel cases.

### S2 — Reaction-wheel hard failure / lock / stuck output
Model each fault distinctly. Do not conflate zero effectiveness with wheel lock, stuck torque, or momentum lock; they have different dynamics.

### S3 — Wheel saturation / momentum constraint
- initial momentum offsets;
- speed-limit approach;
- prolonged disturbance loading;
- cases where requested torque is infeasible.

### S4 — Actuator bias / friction / stiction / dead-zone
Include one effect at a time and selected combinations, only after each primitive model is validated.

### S5 — MTQ degradation and field geometry
- dipole effectiveness loss;
- axis degradation;
- field variation along orbit;
- instantaneous torque limitation;
- cases with low instantaneous authority but adequate orbit-average authority and vice versa.

### S6 — Sensor faults
- gyro bias, drift, scale factor, noise increase;
- star-tracker dropout, delay, bias, invalid output;
- magnetometer disturbance/bias;
- sun-sensor faults if used by the estimator;
- intermittent and persistent faults.

### S7 — Model/environment mismatch
- inertia mismatch;
- disturbance magnitude/uncertainty;
- actuator time constant mismatch;
- timing/latency;
- selected environmental perturbations.

### S8 — Combined and unknown faults
- sensor plus actuator faults;
- multiple wheel degradation;
- unfamiliar combinations;
- fault timing/severity combinations withheld from training.

Avoid implausible randomization. Every parameter range must have a documented physical or engineering rationale.

## 5. Fault-manifold benchmark

Construct a test matrix across:

- fault type;
- fault severity;
- fault onset time;
- fault duration or persistence;
- affected actuator/sensor;
- initial attitude/rate;
- orbit/field geometry;
- plant parameter mismatch;
- estimator uncertainty.

Use a training/validation/test split by *scenario regions*, not just random episode splits. For example, train on selected degradation levels and fault timings, validate on nearby but distinct cases, and reserve severity levels, combinations, or timings for held-out test.

Keep test configurations inaccessible to tuning decisions until the final evaluation. Document any leakage and rerun a clean test if tuning touched test outcomes.

## 6. Controller comparison arms

Use the following comparison arms where applicable. Keep shared plant, initial conditions, random seeds, faults, references, and evaluation windows paired.

| ID | Controller | Purpose |
|---|---|---|
| A0 | Classical LQR/PD | Basic baseline |
| A1 | Classical + oracle allocation/capability | Isolates benefit from ideal capability knowledge |
| A2 | Classical + disturbance observer (DOB/ESO) | Strong conventional disturbance/mismatch baseline |
| A3 | Strongest tuned classical controller | Fair practical baseline; include justified capability allocation/gain schedule |
| A4 | Unstructured residual RL | Does residual RL help without proposed gate? |
| A5 | Residual RL + need `rho` | Is need-based attenuation useful? |
| A6 | Residual RL + `rho` + oracle capability/trust gate | Is the gate mechanism useful with ideal information? |
| A7 | Full CCR v2 with estimated capability/uncertainty | Proposed complete architecture |
| A8 | Optional RMA/latent adaptation approach | Secondary comparator only; do not delay core experiments |

A0–A3 are not straw men. Tune each on the same development budget and never intentionally degrade them. A1 is an oracle diagnostic, not a deployable baseline.

## 7. Ablations

Ablate one architectural factor at a time from A7:

- remove `rho` (need);
- remove `alpha` (trust);
- remove `G` (directional capability gate);
- replace estimated capability with oracle capability;
- remove estimator-error/gate-in-loop training;
- disable validity ladder/supervisor;
- remove symptom history/temporal features if present;
- optional diagonal gate versus geometry-aware approach.

State the exact code/config difference for each ablation. Do not combine several removals under one label unless it is explicitly a grouped ablation.

## 8. Episode design and reproducibility

### Paired evaluation

For every controller arm in a comparison, use identical:

- initial conditions;
- orbit/environment configuration;
- fault type, severity, onset and duration;
- sensor-noise realization where possible;
- random seed;
- mission/reference timeline.

If stochastic policy sampling differs, record policy RNG separately while keeping the environment seed paired.

### Seeds and sample size

Start with a pilot to estimate variance and runtime. Then determine sample size for meaningful confidence intervals or a power/effect-size target. Do not use a small convenient number of seeds as definitive evidence.

Record:

- episode count;
- seeds;
- configuration hash;
- software commit;
- model/policy checkpoint hash;
- simulator version;
- controller parameters;
- evaluation timestamp.

## 9. Episode success and loss-of-control definitions

Define success criteria before final test. A suggested template (values must be selected and justified for the spacecraft/mission):

- attitude error below `theta_success`;
- body angular rate below `omega_success`;
- constraints respected;
- conditions sustained for `T_success`;
- recovered by deadline `T_recovery`.

An episode is a loss/failure if any predeclared criterion occurs, e.g.:

- pointing/rate threshold exceeded for a defined duration;
- failure to recover by deadline;
- persistent actuator constraint violation;
- invalid/numerical state;
- inability to maintain the mission objective.

Distinguish mission infeasibility due to physically insufficient actuator authority from controller failure. Report both; do not quietly exclude difficult episodes.

## 10. Statistical analysis

Use paired comparisons where possible.

For each primary outcome:

- report mean and standard deviation;
- median and interquartile range when skewed;
- 95% confidence interval;
- paired difference between arms;
- effect size;
- failure counts and rates;
- per-scenario breakdown.

Recommended methods:

- bootstrap confidence intervals on paired episode differences;
- paired tests only after checking assumptions and reporting effect size;
- survival/time-to-recovery analysis if episodes often fail to recover before cutoff;
- correction or careful interpretation for multiple secondary comparisons.

Avoid significance-only conclusions. A tiny statistically significant difference may not matter engineering-wise. Report practical magnitude and cost.

## 11. Fairness and tuning rules

- Use the same plant and sensor/fault realizations for paired arms.
- Provide comparable tuning effort and parameter budgets.
- Freeze final evaluation configs and checkpoints.
- Do not tune on held-out test results.
- Do not omit failed episodes or controller resets.
- Keep metric definitions identical.
- If a controller has extra information (oracle capability, truth state, privileged critic), label it and do not compare as if it were deployable.
- Report computational cost and actuation effort alongside pointing performance.
- Document all changes after protocol freeze.

## 12. Required plots and tables

At minimum, generate:

1. Attitude-error time histories with fault onset.
2. Angular-rate error time histories.
3. Requested, allocated, and achieved torque.
4. Wheel torque, speed/momentum, and saturation.
5. MTQ command and field-dependent torque.
6. `tau_RL_raw`, `rho`, `alpha`, `G`, and accepted residual.
7. Capability estimate and conservative bound versus true capability (truth for analysis only).
8. Supervisor modes and transitions.
9. Recovery-time distribution.
10. Performance-versus-effort comparison.
11. Failure-rate by fault type/severity.
12. Ablation summary with paired effect sizes and confidence intervals.

Plots must have readable units, legends, fault onset annotations, and consistent axes for direct comparisons. Do not cherry-pick only successful or favorable episodes.

## 13. Experiment record format

Each experiment should contain an immutable config snapshot and machine-readable summary, for example:

```text
experiments/
└── E007_ccr_full_wheel_degradation/
    ├── experiment.yaml
    ├── manifest.json
    ├── run_index.csv
    ├── logs/
    ├── metrics/
    ├── plots/
    ├── analysis/
    └── report.md
```

`manifest.json` should capture at least:

- experiment ID and description;
- git commit;
- config hashes;
- simulator/backend version;
- controller arm;
- policy/checkpoint hash;
- seed list;
- run date;
- metric schema version.

Results must never overwrite previous final runs. Use a unique experiment/run ID and preserve raw data.

## 14. Required final research report

The final report must answer:

1. What was the strongest classical baseline and how was it tuned?
2. In which regimes did RL improve performance?
3. In which regimes was RL neutral or worse?
4. Did capability-derived directional gating improve outcomes relative to ungated and oracle variants?
5. Did need/trust separation add value?
6. How did estimation uncertainty and sensor faults change residual authority?
7. What was the generalization performance on held-out faults?
8. Did the full architecture reduce failures or recovery time without excessive pointing degradation, effort, or latency?
9. Which results are statistically and practically meaningful?
10. What limitations, negative results, and follow-up experiments remain?

The report must include reproducible configs, plots, tables, statistical analysis, and limitations. It must not overstate novelty or safety.

## 15. Agent implementation instructions

- Read this protocol before building experiment or evaluation infrastructure.
- Keep scenarios, controller arms, metrics, and experiment metadata configuration-driven.
- Implement metric definitions once and use them for every arm.
- Build paired-run orchestration and deterministic seeding.
- Separate training/validation/test scenario regions.
- Do not start large RL sweeps until the plant, classical controller, fault models, and residual gate are validated.
- Use a pilot to estimate variance and compute realistic sample size.
- Treat the protocol as a living document before freeze; record proposed revisions and their rationale.
- Never change primary metrics, test scenarios, or success thresholds after seeing final test results without explicitly marking the evaluation exploratory and establishing a new untouched test set.

---

## 16. Research integrity

The expected result may be that CCR v2 helps only under some faults, that a simpler method is better, or that the proposed gate does not improve performance. All are valid scientific outcomes.

The goal is a defensible thesis with a clean codebase and reproducible evidence—not a demo engineered to guarantee a positive result.
