# adcs-rl — Fault-Tolerant Spacecraft ADCS & CCR v2 Research Platform

A modular, reproducible spacecraft attitude determination and control system (ADCS) research platform for evaluating **Capability-Informed, Uncertainty-Aware, Directionally Gated Residual Reinforcement Learning (CCR v2)** against strong classical fault-tolerant baselines.

## Repository Layout

- `AGENT_MISSION.md` — Mission workflow and phase gates.
- `CONTROL_ARCHITECTURE.md` — CCR v2 control and fault-tolerance architecture specification.
- `RESEARCH_PROTOCOL.md` — Experimental hypotheses, scenario catalog (S0–S8), comparison arms (A0–A8), ablations, and statistical reporting rules.
- `spacecraft_config.yaml` — Reference 100 kg spacecraft plant configuration (`spacecraft_reference_001`).
- `src/adcs/` — Installable Python package (dynamics, fast/Basilisk backends, sensors, estimation, capability/AMS, classical controllers, allocation, supervisor, deterministic authority gate, residual RL, evaluation).
- `tests/` — Unit, physics, controller, fault-injection, integration, and regression tests.
- `configs/` — Scenario, controller, sensor, fault, and experiment YAML configurations.
- `docs/agent_reports/` — Phase-by-phase verification reports.

## Installation & Verification

```bash
pip install --no-build-isolation --no-deps -e .
pytest
ruff check src tests
```
