# AGENT_MISSION.md
## Autonomous ADCS-RL Research and Implementation Mission

This file is the **master entry point and execution contract** for the coding agent working in this repository.

The mission is to implement, validate, and experimentally evaluate a fault-tolerant spacecraft attitude-control research platform, with a credible comparison between a strong classical controller and reinforcement-learning-assisted control. The agent must deliver working, tested software and evidence—not just plans, scaffolding, or claims.

---

## 1. Required Reading and Authority

Before modifying code, inspect the repository and read these documents completely:

1. `AGENT_MISSION.md` — mission, workflow, phase gates, agent conduct.
2. `CONTROL_ARCHITECTURE.md` — proposed CCR v2 controller architecture and technical constraints.
3. `RESEARCH_PROTOCOL.md` — hypotheses, scenarios, baselines, metrics, ablations, statistics, and reporting.
4. `pyproject.toml` — packaging, dependencies, and tooling.
5. All relevant spacecraft, orbit, sensor, actuator, controller, and scenario configuration files (YAML/TOML/JSON).

Also inspect existing source code, tests, Git status/history, and available runtime/tooling before making changes.

### Document authority and conflict handling

- This mission file governs the **workflow and phase gates**.
- `CONTROL_ARCHITECTURE.md` governs the proposed **control and fault-tolerance architecture**.
- `RESEARCH_PROTOCOL.md` governs the **scientific experiment and evaluation methodology**.
- Configuration files govern configured parameters, unless a document explicitly identifies a parameter as a fixed research assumption.
- If documents conflict, do not silently choose or overwrite one. Identify the conflict, determine its technical implications, propose a resolution, and update the affected document(s) with a concise rationale before proceeding.
- Treat CCR v2 as a proposed research architecture to implement and critically validate—not as a proven controller or guaranteed source of stability.
- Preserve research objectives and essential architecture elements. A simplification or replacement is permitted only when technically justified, recorded, and reflected in the specification.

---

## 2. Mission Objectives

Build a modular, reproducible ADCS research framework that supports:

1. A physically credible spacecraft attitude and orbit/environment model.
2. Reaction-wheel and magnetorquer actuation, including realistic limitations and fault behavior.
3. Sensor models, sensor faults, estimation, and observability/uncertainty interfaces.
4. A strong, independently validated classical attitude-control baseline.
5. A modular fault injection and scenario framework.
6. Gymnasium-compatible RL training/evaluation interfaces.
7. CCR v2 residual-control architecture with deterministic authority/trust/safety logic.
8. Fair comparison, ablation, Monte Carlo, held-out fault evaluation, and statistical reporting.
9. A fast simulation backend for training and a Basilisk-based truth/validation backend.
10. A path toward later SIL/HIL and embedded implementation without prematurely implementing deployment code.

The research question is **whether and under what conditions RL provides a measurable benefit over a strong classical controller**. Do not assume that RL must outperform the baseline. Negative or mixed results are valid if the experiments are rigorous and correctly interpreted.

---

## 3. Engineering Principles

- **Validate physics before algorithms.** Verify units, frames, quaternion conventions, signs, actuator mapping, conservation behavior, and numerical integration before controller development.
- **Baseline before RL.** Build and tune a credible classical controller before training learned policies.
- **Independent verification.** Use tests, analytical checks, backend comparisons, and reproducible experiments. A passing unit test alone is not proof of physical validity.
- **Fail visibly.** Do not hide exceptions, invalid data, NaNs, failed simulations, or unsupported configurations behind silent defaults.
- **No premature complexity.** Implement only the components needed for the current phase, but preserve the interfaces and architecture needed for later phases.
- **Configuration-driven experiments.** Avoid hard-coded mission, spacecraft, actuator, sensor, fault, and experiment parameters.
- **Reproducibility.** Fix and record seeds, software versions, configuration hashes, and experiment metadata.
- **Clean boundaries.** Simulator-specific APIs must remain inside backend adapters. Controller logic must not depend on Basilisk internals.
- **Research integrity.** Do not cherry-pick seeds, tune on held-out tests, suppress failures, or claim guarantees unsupported by analysis.
- **Evidence-based completion.** Mark work complete only after running the relevant checks and recording the results.

---

## 4. Target Architecture

Implement incrementally, keeping clean interfaces between:

- Configuration and experiment definitions
- Shared state, observation, command, and simulator interfaces
- Spacecraft/orbit/environment dynamics
- Actuators and actuator allocation/capability estimation
- Sensors, fault models, estimation, observability, and uncertainty
- Reference generation and classical control
- Residual policy, authority/trust gate, safety filtering, and supervisory logic
- Training and evaluation
- Logging, metrics, plots, and experiment records
- Fast simulation and Basilisk simulation backends

Use the architecture specified in `CONTROL_ARCHITECTURE.md`; do not invent a competing controller structure without documenting why the specified design must change.

Suggested package layout (adapt to the existing repository where sensible; do not create empty directories or unnecessary abstractions):

```text
src/adcs/
  interfaces/
  simulation/
    fast/
    basilisk/
  dynamics/
  sensors/
  actuators/
  estimation/
  control/
    reference/
    classical/
    allocation/
    residual_rl/
    safety/
    supervisor/
  faults/
  training/
  evaluation/
  utils/
tests/
  unit/
  integration/
  physics/
  controller/
  fault_injection/
  regression/
configs/
experiments/
results/
docs/
scripts/
```

---

## 5. Phase-Based Execution

Execute phases in order. Each phase must produce tangible implementation, tests, and a short evidence report. Do not skip gates because later work is exciting or convenient.

### Phase 0 — Repository and Environment Audit

- Inspect repository, Git status, existing implementation, tests, docs, configs, and available compute.
- Check Python version and dependency installation.
- Identify available Basilisk installation and importability; do not assume it is installed.
- Identify missing documents/configs and architecture mismatches.
- Create an implementation plan grounded in the actual repository, with risks and dependency order.
- Preserve existing work; do not destructively rewrite or reset user files.

**Exit gate:** audit report and actionable plan; repository state understood; baseline checks run where possible.

### Phase 1 — Package Foundation and Interfaces

- Establish or repair package structure, packaging, lint/type/test configuration, and dependency boundaries.
- Define shared types/interfaces for state, observation, actuator command, simulator, controller, and configuration.
- Add deterministic seed handling and structured logging.
- Add config validation and clear error messages.
- Add a minimal smoke test for package import and config loading.

**Exit gate:** installable package, interface tests, config validation, reproducible smoke test.

### Phase 2 — Physics and Fast Simulator

- Implement/verify quaternion and frame utilities, rigid-body rotational dynamics, orbit/environment inputs, and numerical integration.
- Implement reaction-wheel and magnetorquer dynamics with saturation and relevant physical constraints.
- Add disturbances incrementally, initially isolating terms.
- Build the fast backend through shared simulator interfaces.
- Add analytical/physics tests: free rigid-body behavior, torque response, quaternion normalization, sign/frame tests, momentum accounting, saturation, and convergence checks.

**Exit gate:** core physics tests pass; numerical behavior is documented; fast simulator produces deterministic, stable runs for validated conditions.

### Phase 3 — Basilisk Truth/Validation Backend

- Build the Basilisk adapter and modular spacecraft model using its native dynamics, actuator, sensor, environment, process/task/message conventions as appropriate.
- Keep Basilisk-specific code inside the adapter.
- Verify setup and runtime availability; if Basilisk is unavailable, implement the adapter boundary and tests that can run, but clearly mark backend validation blocked—do not pretend simulations ran.
- Compare common scenarios against the fast backend, explain expected model differences, and identify discrepancies.

**Exit gate:** Basilisk smoke run succeeds when available; backend interface tests pass; comparison report documents validated and unvalidated physics.

### Phase 4 — Reference, Classical Controller, and Actuator Allocation

- Implement the nadir-pointing reference and attitude/rate error conventions.
- Implement and tune a robust classical controller (e.g., PD/LQR as supported by the model) with a clear actuator allocation path.
- Add actuator saturation, momentum limits, anti-windup where relevant, and requested-versus-achieved torque logging.
- Implement an allocator that handles the actual actuator geometry and constraints.
- Establish nominal and disturbance/fault-free performance.

**Exit gate:** controller meets defined nominal tracking/recovery criteria; frame/sign and actuator allocation tests pass; baseline is documented and reproducible.

### Phase 5 — Sensors, Estimation, Fault Injection, and Capability

- Implement configurable sensor models and noise/bias/validity characteristics.
- Implement estimator interfaces and a validated attitude estimator appropriate to available sensors.
- Implement fault catalog, injection timing, severity, persistence, and combined faults.
- Implement actuator capability and uncertainty interfaces; separate truth/privileged information from onboard-estimated information.
- Add fault detection/residual and observability/uncertainty signals as supported and validated.
- Verify fault injection independently before integrating compensation.

**Exit gate:** sensor/actuator faults can be injected deterministically; fault tests confirm expected behavior; estimator outputs and uncertainty/validity semantics are documented.

### Phase 6 — Strong Classical Fault-Tolerant Baselines

- Build and evaluate the baseline arms specified in `RESEARCH_PROTOCOL.md`.
- Add disturbance-observer/ESO or equivalent only after the core baseline is validated.
- Add capability-aware allocation and classical fault accommodation.
- Tune using training/validation scenarios only; preserve held-out test scenarios.
- Log metrics and failures consistently across all arms.

**Exit gate:** credible classical baselines run on common scenarios and seeds; metrics, failures, and configuration are reproducible. No RL training yet unless all prior gates are met and a documented dependency exception is approved.

### Phase 7 — RL Environment and Residual Controller

- Create Gymnasium environment(s) using the shared simulator/controller interfaces.
- Define observations, action scaling, reward, termination/truncation, reset distributions, and wrappers explicitly.
- Train an initial residual policy against the classical controller (SAC as primary if supported by the research design; alternatives are comparisons, not silent replacements).
- Ensure the policy receives only onboard-available information for deployment-relevant experiments.
- Separate privileged critic/training-only information from actor/deployment observations and label experiments accordingly.
- Train with the deployed gate/filter and relevant estimator imperfections in the loop.
- Save checkpoints, normalization state, training curves, seeds, configs, and version metadata.

**Exit gate:** RL training/evaluation is reproducible; policy actions are bounded; reset/step API and tests pass; the learned controller can be evaluated without training code side effects.

### Phase 8 — CCR v2 Integration and Ablations

Implement and validate the architecture in `CONTROL_ARCHITECTURE.md`, including the essential blocks and explicit fallback behavior.

- Keep classical control as the backbone.
- Keep residual need/authority and trust/confidence distinct.
- Use capability-derived directional information, with the documented limitations of the capability model.
- Implement deterministic gate logic, validity checks, supervisor modes, recovery behavior, and safety/command filtering.
- Ensure unknown, stale, invalid, NaN, or unsafe information triggers documented conservative behavior.
- Validate gate monotonicity, bounds, timing, and mode transitions.
- Evaluate oracle and estimated capability separately.
- Run ablations defined by the research protocol.

**Exit gate:** component and integration tests pass; gate/supervisor invariants hold; fallback behavior is demonstrated; oracle/estimated experiments are clearly distinguished.

### Phase 9 — Research Evaluation and Monte Carlo

- Run the comparison arms and ablations in `RESEARCH_PROTOCOL.md`.
- Use paired seeds/initial conditions where applicable.
- Separate training, validation, and held-out test fault/scenario regions.
- Run pilot experiments to estimate variability and select defensible sample sizes.
- Report effect sizes, confidence intervals, scenario-level results, failures, and computational cost.
- Generate the required plots, tables, and machine-readable results.
- Do not tune against held-out test results.

**Exit gate:** results are traceable to experiment configs and seeds; statistical and scientific claims are supported; incomplete runs are clearly labeled.

### Phase 10 — CPU, SIL/HIL Readiness, and Final Documentation

- Profile simulator, controller, gate, estimator, and inference latency on available CPU hardware.
- Identify bottlenecks and memory use.
- Keep deployment interfaces clean and document candidate C/C99 boundaries, but do not implement embedded deployment prematurely.
- Define SIL/HIL interfaces, timing assumptions, I/O, fault injection points, and test plan.
- Produce final technical report with limitations, failed hypotheses, and recommended next steps.

**Exit gate:** benchmark evidence, deployment-readiness assessment, reproducible instructions, and final research report.

---

## 6. Validation Rules and Stop Conditions

At every phase:

1. Run targeted tests after each meaningful change.
2. Run the full relevant test suite before phase completion.
3. Inspect failures and fix root causes; do not weaken tests merely to get green.
4. Add regression tests for discovered bugs.
5. Check code quality, typing, lint, and package installation as configured.
6. Verify config examples and scripts from a clean invocation.
7. Record commands, outputs, and known limitations in the phase report.

Stop and investigate rather than proceed if:
- physical units, frames, signs, or quaternion conventions are ambiguous;
- actuator allocation or achieved torque is inconsistent;
- a backend cannot run or its output is not validated;
- a baseline is unstable or not credible;
- fault injection is not deterministic or verified;
- data leakage or unfair comparison is found;
- gate/safety assumptions are violated;
- results cannot be reproduced.

A blocked phase may still deliver useful work (e.g., adapter implementation or tests), but it must be labeled **BLOCKED/NOT VALIDATED**, and dependent phases must not be presented as validated.

---

## 7. Experiment and Result Management

- Keep code, configs, and raw results versioned appropriately.
- Avoid committing large generated artifacts/checkpoints unless repository policy requires it; use documented storage locations.
- Each experiment must record at minimum: experiment ID, timestamp, Git commit, software versions, config snapshot/hash, seed, backend, controller arm, scenario/fault, metrics, termination status, and logs/artifact paths.
- Preserve failed episodes and explain failure categories.
- Use a consistent metric implementation across arms.
- Report the primary metrics and all relevant failure/safety outcomes, not only averages.
- Follow the sample-size, statistics, fairness, and reporting requirements in `RESEARCH_PROTOCOL.md`.

---

## 8. Agent Work Cycle

For each phase, follow this loop:

1. **Inspect:** read relevant files and current state; identify assumptions.
2. **Plan:** list small concrete tasks and acceptance checks.
3. **Implement:** write actual code/config/docs, avoiding unnecessary scaffolding.
4. **Test:** run focused tests, then broader tests as appropriate.
5. **Debug:** inspect failures, determine root cause, fix, and rerun.
6. **Review:** check architecture compliance, edge cases, physics, and regressions.
7. **Document:** record what changed, commands run, evidence, limitations, and remaining tasks.
8. **Commit checkpoint (optional):** only if Git state and project conventions permit; never commit without checking what is staged and respecting the user's existing work.

Do not end a phase with only a TODO list if implementation is feasible in the environment.

---

## 9. Required Phase Report

At the end of each phase, create or update a concise report in `docs/agent_reports/PHASE_<N>_REPORT.md` containing:

- Phase and status: `COMPLETE`, `PARTIAL`, or `BLOCKED`
- Summary of implemented changes
- Key design decisions and deviations from architecture/spec
- Tests and exact commands run
- Test outcomes (counts and failures)
- Simulation/experiment evidence, if applicable
- Known limitations and risks
- Next phase and concrete prerequisites

Do not label a phase `COMPLETE` if required checks were not run or if core behavior remains unvalidated.

---

## 10. Final Deliverables

By mission completion, repository should contain:

- Installable, documented codebase with clear module boundaries.
- Validated fast simulator and Basilisk backend (or explicit limitation if unavailable).
- Credible classical controller and fault-tolerant baselines.
- Configurable sensors, actuators, faults, estimator, and scenarios.
- RL training and evaluation pipeline.
- CCR v2 implementation with tests, fallback behavior, and documented limitations.
- Reproducible experiments, raw/processed results, figures, and statistical analysis.
- Comparison and ablation report that answers the research hypotheses without overstating results.
- CPU profiling and SIL/HIL readiness assessment.
- Updated documentation and phase reports.

---

## 11. Mission Start Instruction

Start with **Phase 0**. Do not begin by generating a large codebase in one pass.

Audit the actual repository and environment first, verify the documents and configs are present, then create a phase plan. Proceed through the phases in order, implementing and validating each one. Use the existing project state as the source of truth for what already exists, and preserve all user work.

The agent's final response for any work session must state:
- what it actually changed;
- what tests/simulations it actually ran;
- the observed results;
- what is still incomplete or blocked;
- the exact next action.

**Do not claim success without evidence.**
