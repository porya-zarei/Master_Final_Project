# Fault-Tolerant Nanosatellite ADCS — Codebase

M.Sc. thesis: **Fault-Tolerant Attitude Control of Nanosatellites Using Reinforcement
Learning: From Simulation to Hardware-in-the-Loop** (Pouria Zarei, Univ. of Tehran).

> **Execution authority for this repository is `docs/research/MASTER_ROADMAP.md`.**
> What may be quoted from past results is `docs/research/EXPERIMENT_REGISTRY.md`.
> This README describes the *code layout only*.

## What the code actually is

The training and evaluation path is a **custom NumPy/Gymnasium plant** in
`satellite_adcs/`, driven by YAML configuration and trained with stable-baselines3
(PPO/SAC). It is **not** a Basilisk project: the Basilisk/`bsk_rl` prototype in
`simulation/` is an abandoned lineage that produced none of the thesis results (see
*Legacy* below).

## Layout

```
codes/
├── satellite_adcs/          # ★ THE PLANT AND CONTROLLERS (everything runs from here)
│   ├── dynamics.py          #   RK4 rigid body + 3 RW + 3 MTQ, gravity gradient, friction
│   ├── environment/
│   │   ├── adcs_env.py      #   ADCSEnv — the RL training path (9-dim obs, 3-dim action)
│   │   └── residual_env.py  #   ResidualADCSEnv — LQR + bounded learned residual (15 obs)
│   ├── controllers.py       #   B-dot / LQR phase manager + allocate_torque()
│   ├── gain_scheduled.py    #   authority-scheduled LQR baseline
│   ├── allocation_policy.py #   state-aware allocation (UNKNOWN / HEALTHY / DEGRADED)
│   ├── friction_estimation.py  # joint per-wheel RLS on (h, tau_f)
│   ├── health_estimation.py #   older h-only RLS (diagnostic only)
│   ├── estimation.py        #   6-state MEKF with gyro-bias state
│   ├── sensors.py           #   gyro / mag / sun / star tracker / GPS (NO wheel tachometer)
│   ├── guidance.py          #   nadir / LVLH reference
│   ├── quaternion.py        #   conversions; quat_to_dcm returns C_BN (verified)
│   └── config/*.yaml        #   satellite, orbit, actuators, sensors, simulation, rl
│
├── simulate.py              # classical closed loop: run_episode(), settling_time()
├── scripts/                 # one script per experiment (see EXPERIMENT_REGISTRY.md)
├── tests/                   # pytest — must stay green
├── sil/                     # E-2 SIL: split loop over TCP (placeholder)
├── hil/                     # E-4 HIL: NOT AUTHORISED — placeholder only
├── results/                 # GITIGNORED experiment artifacts (evidence, not code)
└── simulation/              # ⚠ LEGACY — see below, do not import
```

## Legacy — `simulation/` and `bsk-rl` (do not use, do not delete)

`simulation/` is the abandoned Basilisk/`bsk_rl` prototype from the project's first
weeks. It contains a **second file named `adcs_env.py`** that shares no physics code with
the real one; its own docstring says it was never verified end to end, and it produced no
thesis number. It is retained for provenance and must not be imported, edited or described
as "the simulation core". `bsk-rl==1.3.0` also pins `pytest==7.3.1`, which breaks the suite
on Python ≥ 3.12 — see `requirements.txt`.

## Setup

```bash
cd codes
python -m venv venv
# Windows PowerShell:  .\venv\Scripts\Activate.ps1
# git-bash:            source venv/Scripts/activate
python -m pip install -r requirements.txt     # pytest must be >= 8.3
```

No internet and no support-data download are needed: the plant is self-contained
(gravity gradient only; the aero / SRP / residual-dipole flags are unimplemented no-ops).

## Verify in one minute

```bash
cd codes
python -m pytest tests -q                    # must be green
python simulate.py --seed 0 --T 600          # classical closed loop, prints pointing error
```

## Reproduce a headline result

The allocation grid (8 scenarios × 3 arms × 24 seeds = 576 episodes, ≈13 min):

```bash
cd codes
python scripts/m33b_state_aware_allocation.py --n 24 --procs 4
# writes results/m33b/ and regenerates docs/research/M33B_allocation_report.md
```

Process pools need `OMP_NUM_THREADS=1` (pinned in-script): unpinned workers exhaust memory
at spawn on a 16 GB machine and die with `OpenBLAS error: Memory allocation still failed`,
which looks like a code fault and is not one.

## Where the evidence lives

- `codes/results/**` — raw artifacts, **gitignored**. Back these up: the trained policies
  exist only there. Checkpoint SHA-256 lives in `reports/*_hashes.json`.
- `reports/*.json` — compact *tracked* copies of each experiment's numbers.
- `docs/research/` — `MASTER_ROADMAP`, `DECISIONS`, `EXPERIMENT_REGISTRY`,
  `OPEN_QUESTIONS`, `PROGRESS_LOG`, plus per-milestone reports and the RLS audit.

## Status

Phase A closed (2026-11-06). Phase B (residual RL vs LQR + oracle allocation) in
progress. E-1 MIL and E-2 SIL are authorised after the architecture freeze; **E-4 HIL is
not authorised** and no hardware or real-time claim may be made before it runs.
