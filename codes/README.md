# Fault-Tolerant Nanosatellite ADCS — Codebase

M.Sc. thesis: **Fault-Tolerant Attitude Control of Nanosatellites Using Reinforcement
Learning: From Simulation to Hardware-in-the-Loop** (Pouria Zarei, Univ. of Tehran).

This repository is organized around the three research pillars of the thesis
(fault-randomized RL, frozen world-model MPC, adaptive world-model MPC) and the
MIL → SIL → HIL development chain. Each phase is its own top-level package so
results are reproducible and the 3-way comparison stays clean.

## Layout

```
codes/
├── README.md                # this file
├── requirements.txt
├── venv/                    # single shared virtualenv (created on first setup)
│
├── simulation/              # ★ SHARED SIMULATION CORE (MIL) — used by every phase
│   ├── envs/                #   Gymnasium environments (adcs_env.py: ADCSSatellite,
│   │                        #   make_env, FaultToleranceWrapper)
│   ├── dynamics/            #   Basilisk dyn/fsw model selection & satellite params
│   ├── faults/              #   fault models: RW lock, sensor bias, dropout, ...
│   ├── scenarios/           #   mission scenarios (nadir / sun / custom target)
│   └── configs/             #   yaml configs for env + scenarios
│
├── rl/                      # Phase 1 — baseline RL (fault-randomized PPO / SAC)
│   └── train_ppo.py
├── baselines/               # classical controllers for comparison (PID / LQR / adaptive)
├── world_models/            # Phase 2 — JEPA-style latent world model (offline, frozen)
├── mpc/                     # MPC planners used on top of world models
├── adaptive/                # Phase 3 — AdaJEPA-style test-time adaptation + safety gate
├── sil/                     # Phase 4a — model compression (quantization/pruning) + SIL
├── hil/                     # Phase 4b — hardware-in-the-loop, embedded (ARM/FPGA) deploy
│
├── evaluation/              # metrics + the "unseen-fault generalization" test harness
├── utils/                   # logging, plotting, replay buffers
├── scripts/                 # entrypoints (manual_test.py, run_comparison.py, ...)
└── tests/                   # pytest
```

## Setup

```bash
cd codes
python -m venv venv
# Windows:  venv\Scripts\activate     (bash/git-bash: source venv/Scripts/activate)
pip install -r requirements.txt
```

First run needs internet: Basilisk downloads support data (ephemeris + gravity
model) on first use and caches it under `~/.cache/bsk_support_data`.

## Try this first (Phase 1 smoke test)

```bash
python scripts/manual_test.py
```

Confirms the env + fault injection run end-to-end before you spend time on PPO.

## Phase status

- **Phase 1 (rl):** in progress — env written, smoke test is the next gate.
- **Phases 2–4:** scaffolding only.
