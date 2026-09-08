# Project State Report 1 — Fault-Tolerant Nanosatellite Attitude Control via Reinforcement Learning

**Student:** Pouria Zarei — M.Sc. Control Engineering, University of Tehran
**Advisor:** Prof. Mohammad Javad Yazdanpanah
**Date:** 2026-09-08
**Status:** Phase 1 (M0 + M1) validated — config-driven simulator + LQR nadir acquisition over random initial conditions.

---

## 1. What we want (goal) & what the proposal defines

### 1.1 The problem
CubeSats / nanosatellites use cheap COTS parts, so they are more likely to suffer actuator
(reaction-wheel) and sensor failures, and there is **no on-orbit repair**. The ADCS must
stay **stable and accurate even when a reaction wheel degrades/fails or a sensor drifts** —
**including failure modes never seen during training**. This is the core thesis claim:
*fault-tolerant, autonomous attitude control that generalizes to unseen faults.*

### 1.2 The approved proposal (form 1405/03/02)
- **Title (EN):** *Fault-Tolerant Attitude Control of Nanosatellites Using Reinforcement Learning: From Simulation to Hardware-in-the-Loop Implementation*
- **Scope:** applied + developmental (کاربردی + توسعه‌ای)
- **Development chain:** **MIL → SIL → HIL**
  - **MIL:** nonlinear satellite dynamics; state = quaternion/MRP + angular velocity + tracking error; action = actuator torques; reward balances pointing accuracy vs. energy; random fault injection during training so a **PPO/SAC** agent learns a fault-tolerant policy.
  - **SIL:** compress the policy (quantization/pruning), verify inference time on ARM/FPGA.
  - **HIL:** deploy to embedded hardware with signal-level fault injection.
- **Sensors (proposal):** magnetometer, sun sensor, gyro, GPS. (Refined for attitude control to **star tracker + sun sensor + gyro + magnetometer**, GPS stays for orbit/nadir reference.)
- **Actuators:** magnetorquers + reaction wheels.

### 1.3 The extension (from `PROJECT_BRIEF.md`)
A three-way comparison is the core scientific result:
1. **Baseline C** — fault-randomized PPO/SAC policy (the approved approach).
2. **Baseline B** — frozen JEPA-style latent world model + MPC (no adaptation).
3. **Contribution** — an **AdaJEPA-style adaptive world model + MPC** with a safety gate, tested on **faults unseen during training** (novel severities/combinations). Because the attitude state is low-dimensional, the encoder can be a small MLP → deployable on CubeSat ARM/FPGA.

**Phase-1 objective (revised, adopted):** *Autonomous post-release attitude recovery — detumble → nadir/LVLH acquisition → Earth-pointing — from randomized initial conditions, on a configuration-driven high-fidelity simulator, validated with LQR first, then RL.*

---

## 2. Read articles (literature base)

All reference papers were placed in `papers/` and read/extracted. They cluster into five themes aligned with the thesis.

### 2.1 RL fault-tolerant attitude control (core FTC)
| # | Paper | Venue / Year | Why it matters |
|---|---|---|---|
| 1 | Yang, Jin, Rao — *RL-based attitude FTC with unknown system model* | J. Franklin Inst. 2025 | = proposal ref [4]; NN observer + approximate-optimal policy, multiplicative actuator faults |
| 2 | Lu et al. — *Safe RL agile attitude control, constraints + actuator faults* | Aerospace Sci. & Tech. 2026 | closest to our problem; forbidden-zone/rate/torque constraints + faults |
| 3 | Jin & Yang — *Prescribed-performance RL FTC* | BUAA J. 2024 (CN) | = proposal ref [7] |
| 4 | El Hariry et al. — *DRL for underactuated attitude control* | arXiv 2025 | = proposal ref [5]; underactuated (failed-wheel) control |

### 2.2 DRL attitude / guidance control (robustness)
| # | Paper | Venue / Year | Why it matters |
|---|---|---|---|
| 5 | Retagne, Dauer, Waxenegger-Wilfing (DLR) — *varying-mass DRL attitude control* | Front. Robot. AI 2024 | inertia/mass-uncertainty robustness |
| 6 | Oghim et al. (KAIST) — *DRL attitude with control-moment gyros* | Acta Astronautica 2024 | CMG steering |
| 7 | Brandonisio et al. — *DRL guidance under state uncertainty* | Acta Astronautica 2023 | uncertainty-aware guidance |
| 8 | Ma et al. — *RL stabilization for non-cooperative target capture* | Sensors 2018 | discrete-torque NN, mass-change robustness |
| 9 | Elkins — *Autonomous ADCS via deep RL* | IAC 2020 | classic DRL-ADCS |
| 10 | Rogers et al. — *Modern control vs. RL for proximity ops* | IFAC 2025 | classical-vs-RL comparison |

### 2.3 ADCS heritage & magnetic control (real-baseline literature)
| # | Paper | Venue / Year |
|---|---|---|
| 11 | Porras-Hermoso et al. — *on-orbit magnetic control (UPMSat-2)* | Measurement 2024 |
| 12 | Zamorano et al. — *UPMSAT-2 ACS design/implementation* | IFAC 2017 |
| 13 | de la Puente et al. — *model-driven real-time satellite software* | IFAC 2016 |
| 14 | Thinsat adaptive control | Eng. Sci. 2023 (= ref [1]) |
| 15 | ITU pSAT-II high-precision ADCS | RAST 2011 (= ref [2]) |

### 2.4 Deployment, real-time & HIL
| # | Paper | Venue / Year |
|---|---|---|
| 16 | Pérez-Muñoz et al. — *DRL for real-time satellite attitude* | J. Systems Architecture 2025 |
| 17 | Sakal et al. — *reaction-wheel HIL platform* | AAS 25-778 2025 |
| 18 | Tammam & Aouf — *hierarchical DRL cubesat guidance & control* | Control Eng. Practice |
| 19 | Zahedi, Roshanian, Mirshams (KNTU) — *onboard DRL CubeSat* | MDPI 2026 |
| 20 | Ballabriga et al. — *OTAWA WCET analysis toolbox* | Springer 2011 |

### 2.5 Assurance standards for ML in space
| # | Paper | Venue / Year |
|---|---|---|
| 21 | **EASA CoDANN** — design assurance for neural networks | EASA |
| 22 | **ECSS-E-HB-40-02A** — Machine Learning Handbook | ECSS, Nov 2024 |

### 2.6 Stray / misc
| # | Paper | Note |
|---|---|---|
| 23 | Kim — *book review of "Deep Learning"* | accidental download, not research |
| — | `SatelliteServicesLtd…pdf` | **duplicate** of Lu et al. (identical content); proposal ref [3] paper actually **missing** |

> **Gaps to fix:** proposal refs [3] (Sat Services Ltd), [6] (MATA-RL), [8] (Liu & Liang ISAC), [9] (CalPoly HIL), [10] (Vedant IEEE Aero) are **not present** as files.

---

## 3. Step-by-step work done (with results & figures)

### Step 1 — Project folder inventory
Read the proposal (persian form), the IranDoc plagiarism certificate, and mapped all 25 papers. Confirmed the thesis is at the literature-gathering stage (no code existed; `codes/` empty; git repo had no commits).

### Step 2 — Restructure the codebase
Created a phase-aligned structure under `codes/` with a **shared simulation core** used by every phase, so the 3-way comparison is apples-to-apples:
```
codes/
├── simulation/   ★ shared simulation core (envs, dynamics, faults, scenarios, configs)
├── rl/           Phase 1 baseline RL (PPO/SAC)
├── baselines/    classical controllers (PID/LQR/adaptive)
├── world_models/ Phase 2 (JEPA)
├── mpc/          MPC planners
├── adaptive/     Phase 3 (AdaJEPA + safety gate)
├── sil/  hil/    Phase 4a / 4b
├── evaluation/   metrics + unseen-fault harness
├── scripts/      entrypoints
└── utils/  tests/
```

### Step 3 — Environment setup
Built a Python 3.14 venv with **Basilisk 2.11.1 + bsk_rl 1.3.0 + stable-baselines3 2.9 + torch 2.14**. First-run Basilisk support-data download (NASA ephemeris via backup mirror) completed and is cached.

### Step 4 — Phase-1 attitude env (`simulation/envs/adcs_env.py`)
`ADCSSatellite` (bsk_rl) + `FaultToleranceWrapper` (reward + RW-lock & sensor-bias fault injection). Verified: **smoke test OK, `check_env` PASS**. Random rollout figure:

![Phase-1 ADCS random rollout](../results/first_simulation.png)

### Step 5 — Visualization of the attitude dynamics
Animated the satellite body tumbling in 3D from the simulated MRP state:

![Attitude animation](../results/satellite_animation.gif)

### Step 6 — Orbit-around-Earth animation (ADCS env)
Earth + orbit path + satellite with body-fixed attitude axes (fixed a km→m unit bug; orbit at ~1.08 RE):

![Orbit + attitude](../results/orbit_attitude.gif)

### Step 7 — Earth-observing mission env (`simulation/envs/eo_imaging_env.py`)
Faithful port of the **Nagano & Schaub** tasking environment onto the bsk_rl 1.3.0 API: imaging + charge actions, power/battery tracking, target-opportunity observations, `UniqueImageReward`, 50 targets. Verified: `Box(14)` obs, `Discrete(4)` actions, battery drains/recharges, episode truncates at the time limit.

![Earth-observing satellite orbit + targets](../results/eo_orbit.gif)

### Step 8 — Vizard live 3D pipeline
Confirmed `vizFound=True`; bsk_rl writes Protobuf `.bin` viz logs (`viz_output/`); downloaded and extracted the **Vizard Unity app** (`D:\Vizard\Vizard\Vizard.exe`, 133 MB) and launched it — it opened windows on the machine and rendered the 3D scene. Helper script `scripts/gen_vizard.py` regenerates `.bin` replays.

### Step 9 — Custom config-driven ADCS simulator (M0)
Because the end controller is **RL** (needs fast rollouts + full control of RW/MTQ/sensor/fault models), built a lightweight, Gymnasium-compatible simulator `satellite_adcs/`:
- **Config (YAML):** satellite (24U, 35 kg, `J=diag(0.38,0.73,0.58)`), orbit (500 km LEO, 51.6°), actuators (3 RW 10 mN·m/6000 rpm + 3 MTQ 1 A·m²), sensors (ST/sun/gyro/mag/GPS), disturbances, simulation.
- **Dynamics:** rigid-body Euler + quaternion kinematics, Keplerian orbit, gravity-gradient, tilted-dipole B-field, RK4.
- **Sensors:** star tracker, sun sensor, gyro (noise/bias), magnetometer, GPS.
- **Guidance:** nadir/**LVLH** reference (time-varying, from orbit state) — the correct formulation (nadir is *not* a fixed attitude).
- **Controller:** LQR (designed via CARE) + B-dot detumble (MTQ) + RW/MTQ allocation.
- **Estimator:** star-tracker-driven attitude (see §3.10).
- **Env + runners:** `satellite_adcs/environment/adcs_env.py`, `simulate.py`, `scripts/run_m1_validation.py`.

Debugging milestones: fixed `ClassicElements`/DCM-convention bugs, a transposed LVLH DCM, and an estimator timing mismatch (estimator now propagates in lockstep with dynamics).

### Step 10 — M1 validation: LQR nadir acquisition over random conditions
LQR + star-tracker estimator slews the satellite from random release to nadir. **60 random initial conditions, 900 s each:**

| Metric | Value |
|---|---|
| Success rate (settle <1° in 900 s) | **73.3%** |
| Settling time | mean **143 s** · median **103 s** · p90 **153 s** |
| Final pointing error | mean **0.81°** |

![M1 validation summary](../results/m1_validation_60/summary.png)

Single-episode trajectory (pointing error over time, log scale):

![Nadir acquisition episode](../results/nadir_acquisition_0.png)

> **Honest deviation from plan:** the full MEKF with gyro-bias estimation was unstable during large-angle acquisition (attitude/bias observability coupling). M1 uses the **star tracker attitude directly** (0.003° accuracy at the 4 Hz control rate) with the gyro for rate. A fused MEKF with bias estimation is deferred to Phase 2. The ~27% non-settling cases are dominated by **reaction-wheel momentum saturation** — the next step is MTQ momentum management.

---

## 4. Next phases to reach the final goal

```
MIL ──────────────────────────────────────────────▶ SIL ─▶ HIL
 │
 ├─ [DONE] M0: config-driven simulator
 ├─ [DONE] M1: LQR nadir acquisition (73% success, ~0.8°)
 ├─ [NEXT] Phase 1B: fault-tolerance experiment
 │        • RW1 health = 0.5 (50% torque) and 0.0 (failed)
 │        • MTQ compensates the lost magnetic/rotational authority
 │        • first look at actuator-fault recovery
 ├─ [NEXT] Phase 2: RL baselines (Baseline C)
 │        • PPO then SAC on the same simulator
 │        • learning curves + fault-recovery evaluation
 │        • unseen-fault-severity generalization test
 ├─ [NEXT] Phase 3: world models (Baseline B)
 │        • frozen JEPA-style latent world model + MPC
 ├─ [NEXT] Phase 4: adaptive contribution
 │        • AdaJEPA-style plan-execute-adapt-replan + safety gate
 │        • the 3-way comparison table (PID/LQR/PPO/SAC/JEPA-MPC/Adaptive)
 ├─ [NEXT] Phase 5: SIL — compress policy (quantization/pruning), verify inference time
 └─ [FINAL] Phase 6: HIL — embedded deployment + signal-level fault injection
```

**Final goal:** a learning-based, fault-tolerant attitude controller that (a) acquires and holds nadir pointing, (b) recovers under reaction-wheel degradation/failure and sensor faults, (c) generalizes to faults unseen during training, and (d) is validated through the full **MIL → SIL → HIL** chain — with the **adaptive world-model + MPC** as the novel contribution versus the PPO/SAC and frozen-MPC baselines.
