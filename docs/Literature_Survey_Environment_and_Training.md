# Literature Survey — Environment, Training and Simulation Practice in RL Spacecraft ADCS

**Purpose.** Answer two questions from the evidence: *what environment do other papers build*, and
*how do they train and simulate within it*. This document is the cross-cutting synthesis; the
per-paper detail (full schema for all 28 documents) lives in `papers/extracted/*.md`.

**Corpus.** 30 markdown files in `papers/markdowns/` → **29 distinct documents** (one duplicate:
`Safe reinforcement learning … (copy).md`). **28 were extracted**; the excluded one is
`Deep Learning Book Review.md` (a book review, out of scope). Coverage by batch:

| Batch | File | Documents |
|---|---|---|
| A | `papers/extracted/A_attitude_core.md` | Elkins IAC-20; Pérez-Muñoz (UPMSat-2 magnetic ACS, JSA 2025); El-Dalahmeh arXiv 2507.03686 |
| B | `papers/extracted/B_fault_tolerant.md` | Jin Lei (J. BUAA); Yang/Jin/Rao (JFI 2025); Lu et al. (AST 2026); Frontiers Robot. AI 2024 |
| C | `papers/extracted/C_onboard_hil.md` | El Hariry (NeurIPS 2021); Tammam & Aouf (CEP 2025); Zahedi (Eng. Proc. 2026); Sakal (AAS 25-778) |
| D | `papers/extracted/D_cmg_proximity.md` | CMG/SAC; PPO-vs-LQR proximity; DQN capture; POMDP shape reconstruction |
| E | `papers/extracted/E_framework_worldmodel.md` | Basilisk (JAIS 2022); AdaJEPA; Nagano & Schaub AAS 25-637 / AAS 25-159 |
| F | `papers/extracted/F_standards_assurance.md` | ECSS-E-HB-40-02A; CoDANN |
| G | `papers/extracted/G_real_missions_rtos.md` | ITU pSAT II; UPMSAT-2 ACS; UPMSAT-2 on-orbit; Thinsat; Model-Driven Design; OTAWA |

**Evidence rule.** Numbers below are quoted from the extractions. Where the source is silent the
field reads "not stated" — never guessed. Three source-conversion defects are flagged where they
occur (Lu Tables 5–7; Zahedi's 2 s vs 6 s units; doc-5 Table 3 column collapse).

---

## 1. The headline answer

**1. Custom, single-purpose Python simulators dominate — this is the mainstream, not a shortcut.**
Of the 17 RL/control papers, ~11 use a hand-written simulator (Python/Gym or MATLAB), 2 use
Basilisk (A3 as the plant, B4 as the full stack), 2 use MATLAB/Simulink (A2's UPMSat-2 flight model,
C3's physical stand), and STK appears **only as a truth/reference model** (B3 for ephemeris; G1 as
the HIL truth source), never as the training plant. **No paper uses Gazebo.** A thesis built on a
custom 6-DOF NumPy plant is squarely inside the norm.

**2. Fidelity is deliberately low, and almost nobody models the orbit and the attitude together.**
Most are attitude-only rigid-body 6-DOF: no orbit, no gravity gradient, no drag/SRP, no magnetic
torque, no wheel friction. The only exceptions are A2 (orbit + gravity + magnetic residual + aero +
SRP — but a magnetorquer-only ACS), B3 (orbit from STK, environmental torques absent) and B4 (orbit
via `gravityEffector`, aero/SRP/GG-attitude absent). **Aero/SRP/magnetic-residual flags that do
nothing are the norm; the honest form is to say "perturbations neglected" in the text** — which is
a documentation fix, not a physics fix (§12.6).

**3. Sensor realism is nearly absent, and no RL paper in the corpus has an attitude estimator.**
Perfect state feedback is the default (A1 states it explicitly: *"attitude sensor models, such as
star trackers or inertial guidance units, were not used"*). Only B3 models gyro noise (0.1 % +
0.01 % of |ω|), only C4 models sensors at realistic rates with an EKF, and only D4 injects a full
POMDP observation error (position ±10 m, velocity ±0.1 m/s, attitude σ = 2°). **Zero papers
implement an MEKF/UKF for the policy.** A deployed policy fed by an estimated state is, in this
corpus, unprecedented — and it is exactly what the thesis's redline decision #9 requires.

**4. The fault grammar is tiny and repetitive: one multiplicative loss-of-effectiveness plus one
additive bias, injected abruptly at a fixed time.** B1: `e=0.5`, `u=−0.2 N·m` on the x-wheel at
t=20 s. B2: `e=0.5`, `u=−0.1 N·m`. B3: `e~U[0,1]` and `u~U[±0.15] N·m` per axis, re-drawn every
episode. A3: RW0 fully dead at t=3000 s of an 8000 s run, fixed. C1: one wheel dead, with **ten
specialised policies — one per fault case** (so the policy effectively *knows* the fault). B4:
**no faults at all.** No gradual/incipient faults, no lock, no multi-fault sequences anywhere.

**5. Only one paper randomises faults during training, and none tests an unseen fault type.**
B3 is the sole fault-randomising study (and it re-estimates faults at test). Every other fault
paper trains on one or a few hand-picked cases and tests the same family. **The thesis's per-episode
`h ~ U[0.5, 1]` across all three wheels is already the most rigorous fault model in the corpus, and
its dead-wheel case (h = 0, outside the training distribution by construction) is precisely the
unseen-fault generalisation test that the standards demand and the literature omits.** That is the
novelty claim, and it is defensible on evidence.

**6. Training budgets are 10× smaller here than the state of the art in this subfield.**
The Basilisk/BSK-RL lineage (E3/E4, Nagano & Schaub) trains RLlib APPO with **32 workers for
2–3×10⁷ steps**; B3 uses 3×10⁶ OmniSafe steps on an RTX 4090. The thesis baseline is **2×10⁶ steps
with 8 envs**. At the measured 2,269 fps that is ≈2.4 h for 20 M steps — the budget can be raised
cheaply, or the shortfall stated. See §12.2.

**7. Evaluation rigour is the weakest dimension in the literature — and the cheapest thing to beat.**
A2 and A3 each evaluate **one deterministic scenario**. B1/B2 evaluate **one initial condition**.
D2 evaluates four fixed cases. Only C1 (10,000 episodes/controller), D4 (5,000 Monte Carlo
episodes) and B4 (1,000 episodes with SD and 95 % CI) run real campaigns. **No paper performs a
paired RL-vs-classical study with matched tuning and compute.** The thesis's bit-identical paired
A/B (C1) and 60/30-IC studies already exceed the published norm.

**8. Sim-to-hardware is nearly virgin territory, and there is no direct precedent for this thesis's
Phase D.** Nine of the twelve RL papers stop at software. The precedents that matter are A2 (MIL →
PIL on an STM32F407 with a WCET measured against a deadline), C2 (an ESP32 hosting a policy in a
real air-bearing 3-RW rig, with a PD baseline that fails there), C3 (whose network **did not fit
its MCU**, forcing ground-station inference and costing 3× settling time), and C4 (the MIL/SIL/HIL-a/b/c
staging matrix plus a real-time execution budget). See §9.

---

## 2. Environment stack by paper

| Paper | Plant | Language / framework | Integrator & step | Control rate |
|---|---|---|---|---|
| A1 Elkins IAC-20 | custom | Python + Numba, custom PyTorch RL | RK4, Δt = 1/240 s, frameskip 20 | ≈11.43 Hz (eval 40 Hz) |
| A2 Pérez-Muñoz JSA 2025 | UPMSat-2 flight model | MATLAB/Simulink R2024b + MathWorks RL Toolbox | sim step 0.1 s | 2 s cycle, 100 ms RL deadline |
| A3 El-Dalahmeh 2025 | Basilisk + custom Gym wrapper | Python, SB3 | not stated | not stated |
| B1 Jin Lei (BUAA) | custom | not named | not stated | = sim step |
| B2 Yang/Jin/Rao JFI 2025 | custom | not named (ADP, hand-coded) | not stated | not stated |
| B3 Lu AST 2026 | custom + STK (orbit) | Python + **OmniSafe** (WCSAC) | **RK4**, 1 s control / 0.1 s FDI | 1 Hz |
| B4 Frontiers 2024 | **Basilisk** + Gym | Python + **RLlib** | dt = 10 s, 60-step episode | 0.1 Hz |
| C1 El Hariry NeurIPS 2021 | custom | Python/Gym, custom PPO | Euler | 2 Hz |
| C2 Tammam CEP 2025 | custom | Python/Gym (TF + PyTorch) | substep 0.01 s | 10 Hz |
| C3 Zahedi 2026 | physical stand | MATLAB R2021b | n/a (1-DOF rig) | gyro 100 Hz |
| C4 Sakal AAS 25-778 | Simulink + ROS2 + Jetson | MATLAB/Simulink (not RL) | forward Euler | 10 Hz (100 ms budget) |
| D1 CMG/SAC | custom | not named | not stated | 10 Hz (0.1 s, 300-step episode) |
| D2 PPO vs LQR | custom | Python, CW 2-D in-plane | not stated | 1 Hz |
| D3 DQN capture | custom | Python + TensorFlow | not stated | not stated |
| D4 POMDP guidance | custom | Python, Inalhan LVLH | not stated | 1 s guidance / 10 s imaging |
| E3/E4 Nagano & Schaub | **Basilisk/BSK-RL** | Python + RLlib (APPO) | Basilisk | 34 discrete actions, 60 s fixed blocks |

**Frameworks that were *not* used anywhere: Gazebo, GMAT (as a plant), STK (as a plant), digital
twins.** Basilisk is the only heavyweight framework used as a training plant (2 papers), and it is
also the only one with a published architecture paper (E1) — worth citing when justifying a
framework choice.

---

## 3. Dynamics fidelity matrix

| Paper | 6-DOF attitude | Orbit | Gravity gradient | Drag / SRP | Magnetic torque | Wheel friction / jitter |
|---|---|---|---|---|---|---|
| A1 | ✅ | ✗ (explicitly) | ✗ | ✗ | ✗ | ✗ |
| A2 | ✅ | ✅ | ✅ | ✅ | ✅ (residual) | n/a (no wheels) |
| A3 | ✅ | via Basilisk, not itemised | not stated | not stated | not stated | not stated |
| B1/B2 | ✅ | ✗ | ✗ | ✗ | ✗ | ✗ |
| B3 | ✅ | ✅ (STK) | ✗ | ✗ | ✗ | ✗ |
| B4 | ✅ | ✅ | ✗ | ✗ | ✗ | ✗ |
| C1 | ✅ | ✗ | ✗ | ✗ | ✗ | ✗ |
| C2 | ✅ + CW relative orbit | ✅ (relative) | ✗ | ✗ | ✅ (torque, no MTQ) | ✗ |
| C4 | ✅ | ✗ | ✗ (named as a model–reality gap) | ✗ | ✗ | ✗ |
| D1 | ✅ (3-DOF) | ✗ | ✗ | ✗ | ✗ | ✗ |
| D3 | ✅ (3-DOF) | ✗ | ✗ | ✗ | ✗ | ✗ |
| D4 | ✅ + relative translation | ✅ (LVLH) | ✗ | ✗ | ✗ | ✗ |
| **This thesis** | ✅ | ✅ (nadir/LVLH) | ✅ | flags present but **no-op** | ✅ (3 MTQ + B-field) | ✗ |

**Reading.** The thesis's plant is **at or above the corpus median on every axis except orbit
disturbances** — and it is the only one in the corpus with *both* a gravity-gradient/nadir target
*and* a magnetorquer loop *and* wheel desaturation. The single integrity problem is that
`dynamics.py` carries aero/SRP/magnetic-residual flags that are silently inert (lines 71–73): the
literature's honest form is an explicit "perturbations neglected" statement.

---

## 4. Sensors, estimation and observation design

| Paper | Sensors modelled | Estimator | Uncertainty handling |
|---|---|---|---|
| A1 | **none** (explicit) | none | none |
| A2 | 3× fluxgate magnetometer, 12-bit ADC | none | averaged readings; noise values not stated |
| A3 | none | none | none |
| B1 | **none** (*"measurement error = 0"*) | adaptive estimate of lumped disturbance | bounded-disturbance assumption |
| B2 | not stated | **NN observer** for B̂ and δ̂ | observer + feedforward |
| B3 | gyro (0.1 % + 0.01 % of \|ω\|) | **bi-LSTM + CBAM FDI** on 6-vector | fault estimated at test, true in training |
| C1 | none | none | **random loop delay U[0.5, 1] s** + last torque in obs |
| C3 | real gyro, UART @100 Hz | none | none stated |
| C4 | gyro 10 Hz, magnetometer 2 Hz, sun 2 Hz | **EKF on the host** | realistic sensor rates |
| D1 | none in main study; noise in robustness | none | noise-augmented obs, no belief state |
| D4 | **POMDP**: position ±10 m, velocity ±0.1 m/s, attitude σ = 2° | none | **noise-augmented obs + train-with-noise** |

**The gap.** Nobody estimates attitude for the policy. The thesis's planned MEKF-before-deployment
is genuinely ahead of the field — and note the corpus supplies two independent justifications:
D4's train-with-noise ablation (**69.22 % → 85 % success, +16 points**) proves that matching the
observation model to the deployment noise distribution is where the performance is; and C4's
architecture (realistic sensor rates + EKF on the host, migration on-board as future work) is the
honest intermediate step.

⚠ **Implementation status note.** The thesis's `estimation.py` is currently a star-tracker
passthrough + gyro with a `propagate()` no-op and no bias state. That means the Phase-2 observation
is, in practice, ≈ perfect attitude + noisy rate — i.e. **exactly what most of this corpus uses**.
So Phase-2 results are *comparable to* the literature, and the MEKF is what will make Phase D/E
credible. Both statements should appear in the thesis; neither alone is honest.

---

## 5. Actuators, allocation and the action space

| Paper | Actuators | Action | Allocation / desaturation |
|---|---|---|---|
| A1 | 3 abstract torque levels | **19 discrete**, near-impulsive, one body axis at a time | none |
| A2 | 3 magnetorquers, PWM duty 0–500 ms | **125 of 1331** duty combos (Pareto-pruned) | n/a |
| A3 | 4× Honeywell HR16 RW, pyramid | 4 continuous torques | online redistribution weights λᵢ, λ=0 for a dead wheel |
| B1 | 3 flywheels, skewed matrix C | pseudo-inverse u_c = C⁺T_w | none |
| B2 | 4 RWs (3 orth + 1 skewed) | continuous | none |
| B3 | 3 RWs, ±0.5 N·m/axis | continuous | none (no momentum mgmt) |
| B4 | 3 RWs, ±0.2 N·m, Ω_max 6000 rpm | continuous | none |
| C1 | 3 RWs, I 1.82e-5 kg·m², 0.004 N·m, 7000 rpm | continuous, clipped to ±2 mN·m | none |
| C2 | 3 RWs, 7000 rpm, PWM + PD wheel loop | continuous | none |
| D1 | 4 CMGs, pyramid, h = 1000 N·m·s | **4 gimbal rates** | GSRI in the classical phase only |
| **This thesis** | 3 RW + **3 MTQ** | **3-dim desired body torque** | **shared physics-based fault-tolerant allocator + MTQ desaturation** |

**Reading.** Two patterns are worth noting. First, **most papers never model the actuator** — the
action *is* torque, with no wheel dynamics, no limits to respect and no moment management. Second,
where authors want an easier problem they **simplify the action space** (A1's 19 near-impulsive
torques; A2's 125-of-1331 duty combos): a legitimate precedent if a discrete action space is ever
needed. The thesis's design — policy emits *desired body torque*, a shared allocator maps it to
3 RW + 3 MTQ with desaturation — is more complete than any RL paper in the corpus, and it is the
direct answer to C1's anti-pattern (one specialised policy per fault case, so the policy knows the
fault). **State explicitly in the thesis that no per-fault policy specialisation is used and that
reconfiguration is delegated to the allocator plus health estimate.**

---

## 6. The fault grammar

| Paper | Fault | Injection | Randomised? | Controller told? | Tested unseen? |
|---|---|---|---|---|---|
| A3 | RW0 dead (T = 0) at t = 3000 s of 8000 s | abrupt, fixed | ✗ | via initialisation ("incl. RW faults") | ✗ |
| B1 | x-wheel LOE 0.5 + bias −0.2 N·m at t = 20 s | abrupt, fixed | ✗ | ✗ (adaptive estimate) | ✗ |
| B2 | x-wheel LOE 0.5 + bias −0.1 N·m at t = 20 s | abrupt, fixed | ✗ | ✗ (observer) | ✗ |
| B3 | E = diag(e_l), e_l ~ U[0,1] (e=1 dead) + u_a ~ U[±0.15] N·m | abrupt, constant within episode | **✅ every episode** | true in training, **estimated at test** | partial (same family) |
| B4 | **none** | — | — | — | — |
| C1 | one RW dead (9 cases) | fixed per agent | ✗ | **yes** (policy selected per fault) | ✗ |
| E3/E4 | RW power limit, Coulomb friction ×N, encoder off/stuck, battery capacity | at episode start, **physics level** | swept, not randomised | fault *index* only (in `Fault-num`) | sweep, not distribution shift |
| **This thesis** | h ∈ [0.5, 1] per wheel per episode; dead wheel = h = 0 at test | continuous, multip. | **✅ every episode** | ✗ (h_hat only) | **✅ dead wheel out of train dist.** |

**Findings that matter for the thesis:**

1. **The thesis's fault model is a superset of the literature's.** Continuous `h ∈ [0.5, 1]` for all
   three wheels subsumes the 50 %-LOE cases (B1, B2), matches the intent of B3's `e~U[0,1]`, and
   additionally randomises *which* wheel. No paper randomises across wheels and health levels.
2. **Explicit fault information helps less than expected, and sometimes hurts** (E3/E4): a binary
   fault flag *underperformed* the continual-learning baseline, the LSTM variant failed to
   converge within budget, and on severe faults **shutting the faulty wheel down and running the
   nominal policy beat the fault-aware trained policy**. Only the *fault index* observation helped.
   → This is strong external support for the thesis's design (allocator handles reconfiguration,
   policy sees no fault flag) and it pre-empts the obvious examiner question.
3. **E3/E4's severity sweep is the right evaluation protocol** and the thesis should copy it: fixed
   shared seed set, ~50 trials per configuration, metrics relative to nominal, a "alive rate" style
   survival metric, and a severity axis (power {0.001…10 W}, friction ×{10…1000}, battery {10…90 %}).
4. ⚠ **A structural caveat the thesis must argue.** E3/E4's "shut the wheel down" escape exists
   because their satellite has 4 wheels (3 axis + 1 tilted). A 3-wheel satellite has **no
   shutdown escape and no redundancy**: the honest framing is *re-allocated classical control vs
   fault-conditioned RL*, and for a fully dead wheel the question is recoverability, not
   reconfiguration. This is already the thesis's C7-lite plan and should be stated as a
   consequence of the architecture, not discovered as a failure.

---

## 7. Training: algorithms, networks, budgets, compute

| Paper | Algorithm(s) | Library | Network | Budget | Hardware / wall-clock |
|---|---|---|---|---|---|
| A1 | PPO-clip | **custom PyTorch** | 400-300 actor, 400-300 critic | 4,340 epochs | RTX 2070 Super, **1 d 20 h** |
| A2 | PPO | MathWorks RL Toolbox | 400-256-200-200 | 1,000 ep × 4,000 steps | i9-13900, iGPU (no discrete GPU) |
| A3 | TD3-HER (+PPO, A2C, TD3) | **SB3** | 256 hidden, 4 actor heads | not stated | not stated |
| B1 | continuous-time actor–critic | hand-coded | tanh critic + 9-term polynomial actor | n/a (online) | n/a |
| B2 | ADP / policy iteration | hand-coded | 21 quadratic-basis critic | 500 random ICs, 4–5 iters | not stated |
| B3 | **WCSAC** | **OmniSafe** | not stated | **3×10⁶ steps** | EPYC 7453 + RTX 4090, "a few hours" |
| B4 | SAC & PPO | **RLlib** | 256 hidden | not stated | RTX 3090 |
| C1 | PPO | custom PyTorch | **2×64** | ≈26 h per batch of 10 policies | **CPU only** (Threadripper 1920X) |
| C2 | D-TD3 / C-TD3 / H-DDPG | TF + PyTorch | 3 FC ReLU | not stated | not stated |
| C3 | DDQN | MATLAB | several ReLU FC | not stated | not stated |
| D1 | SAC (+TD3, PPO) | not stated | 5 networks | not stated | not stated |
| D2 | PPO | not stated | not stated | not stated | not stated |
| D3 | DQN | TensorFlow | 1024 + 2048 | 3,000 iterations | not stated |
| D4 | PPO | not stated | 12-256-256 actor/critic | 30k / 40k episodes | not stated |
| E3/E4 | **APPO** | **RLlib** | 2×512 MLP (+LSTM) | **2–3×10⁷ steps, 32 workers** | not stated |
| **This thesis** | **PPO** (SAC optional) | **SB3** | 2×64 (default) | **2×10⁶ steps, 8 envs** | CPU, ≈15 min |

**Reading.** (i) **PPO is the default choice** (8 of 15 papers), so the Baseline-C selection is
mainstream rather than idiosyncratic. (ii) **Networks are tiny** — 2×64 (C1) to 2×512 (E3/E4);
SB3's default MLP is in-range, so no architecture justification is needed. (iii) **Budgets are
poorly reported and wildly variable**, with the strongest studies in this subfield using
**10–15× the thesis's step count with 4× the workers** — the single most attackable number in the
thesis (§12.2). (iv) **Very few papers state parallel envs at all** (the D batch reports that
vectorisation is *never* mentioned) — so the thesis's `SubprocVecEnv(8)` + `VecNormalize` is more
disciplined than most, and its CPU-vs-GPU measurement (992 vs 618 steps/s) is a reproducibility
contribution in itself.

---

## 8. Simulation workflow: randomisation, reward shaping, curriculum, termination

**Domain randomisation.** Only four papers randomise anything meaningful: B3 (faults + initial pose
and rate, every episode), B4 (mass ~ U[10, 1000] kg per episode, fixed IC), D3 (per-episode
inertia perturbation as a capture proxy), D4 (**train-with-noise**: 69.22 % → 85 %, ≈ +16 points).
The rest train on random initial conditions only. → The thesis's `h ~ U[0.5,1]` randomisation sits
with the strongest four, and D4's ablation is the citable justification that it *works*.

**Reward shaping — the convergent design.** A1: `exp(−φ/0.88 rad)`, ±50 terminals, +9 at 0.25°.
A3: dense progress `e_prev − e_cur`, −10 if |ω| > 1, +0.01 at 0.25°. A2: `1 − exp(2πα)`, and —
the single most transferable finding — **a 100 s moving-average filter on the reward was the one
change that made the policy converge**. B4: per-axis tolerance bonuses + wheel-speed penalty +
spin-out penalty. D1: log-rate term to kill residual rate error. → Every paper shapes; none
succeeds with a raw quadratic cost. The thesis's own history reproduces this exactly (quadratic
cost → plateau at 4.07°; a `bonus` shape → 0.170°), which is now **corroborated, not anecdotal**.
The 100 s reward low-pass filter (A2) is a technique the thesis has never tried and that directly
targets the acquisition-transient/fine-pointing mixing problem.

**Curriculum.** C1 (initial angle ∈ [30°, 180°], biased small early), C2 (two-stage:
disturbance-free → disturbed), A2 (three design iterations: continuous → discrete → filtered
reward). Sparse but real precedent for a phased curriculum.

**Termination.** A1 terminates after 500 actions or |ω| > 0.5 rad/s; C1 on horizon *or* |ω| > 0.1
rad/s; A3 on horizon. Rate-violation termination is common and is a **safety mechanism**: the
policy can never be rewarded for tumbling. The thesis currently has **no early termination** — a
legitimate choice, but it means nothing forbids a high-rate solution, and it is worth either adding
a rate guard or stating the reason it is unnecessary (the rate term in the reward).

---

## 9. Sim-to-hardware: the MIL/SIL/HIL precedents

Nine of twelve RL papers stop at software. The five precedents that matter:

| Work | Stage ladder | Platform | Numbers that matter |
|---|---|---|---|
| A2 Pérez-Muñoz | MIL (Simulink) → **PIL (STM32F407)** → HIL future | Cortex-M4 168 MHz, 1 MB flash, 192 KB SRAM, Ada/Open-Ravenscar | **WCET 12,421,975 cycles = 73.9 ms < 100 ms deadline** (OTAWA); generated C99 callPredict.c 43,303 LOC ≈ 370 kB vs 2 MB OBC; measured max inference 9.72 ms |
| C1 El Hariry | HIL only | ArgoMoon OBC + real ADCS, dynamics simulated (RDP); net ported to C in the RTOS | 2 Hz loop, tens of experiments, pass = 0.01 rad; **no MCU clock/RAM/latency reported** |
| C2 Tammam | HIL | **ESP32-DevKitC V2**, MPU-6050, 3 RWs, 6-bar air bearing; 10 Hz | First ESP32-hosts-policy precedent; **PD baseline fails attitude in sim *and* HIL**; clock/RAM/flash/quantisation **not stated** |
| C3 Zahedi | bench + HIL | 12×12×12 cm rig, gyro UART 100 Hz, H-bridge PWM | **"direct implementation of the trained neural network on the microcontroller is not feasible due to its size"** → ground-station inference; **3× degradation (2 s sim → 6 s hardware)** from PWM dead zone ≈ 30, battery sag, unmodelled disturbance |
| C4 Sakal | **MIL → SIL → HIL-a/b/c** | Jetson Nano + ROS2 + 4 Maxon EC60/EPOS4 | **exec 3.86 ms avg / 6.62 ms max / σ 0.20 vs a 100 ms budget ≈ 26× margin**; CPU 14.7/10.3 %; RAM 16.6 → 19.6 %; **~300 mA current deadband broke torque-mode commands** → commanding wheel angular velocity fixed it; sim torques exceeded real RW limits → K_ICL cut 10× |

**From the real-mission literature (G):** G2/G3 (UPMSAT-2) publish the canonical ladder
**MIL → PIL (TRL 4) → HIL (TRL 8)**, with HIL driving real ADC/digital I/O lines against
magnetometer-voltage and H-bridge models; G1 (ITU pSAT II) adds an air-bearing table and Helmholtz
coils and tests an MTQ failure and a wheel failure; G5 fixes a periodic task at **Period 1000 ms /
Deadline 100 ms** and validates timing with MAST + RapiTime; G3 validates on orbit by an
independent route (ESATAN-TMS thermal model correlated to 4,004 temperature points, ±3 °C) and
reports **mean pointing deviation 2.2° measured vs 2.5° predicted**.

**Two hard constraints for Phase D:**

- **OTawa (G6) has no Xtensa backend** (ISAs: PowerPC, ARM, TriCore, HCS12, Sparc). A **static
  WCET bound for the ESP32-S3 is therefore not obtainable with the standard tool**; the defensible
  substitute is measurement-based worst-case over a stress input set (the RapiTime-style approach
  used in G5/G6's MERASA study), reported against a fixed period/deadline pair.
- **C3 is the cautionary case the thesis must answer explicitly**: quantise (int8), measure the
  footprint in bytes, measure on-target inference time, and model the actuator dead zone.

---

## 10. Standards and assurance (what is actually required)

**ECSS-E-HB-40-02A "Machine Learning Handbook" (15 Nov 2024) is a *Handbook* — informative, not
normative.** The word "shall" appears 7 times, nearly all inside quoted material. It should be
cited as *recommended practice*. What it does say, and where:

- **§6.4.1 Data quality** — relevance, completeness, accuracy, balance/representativeness; the
  **operational design domain (ODD)** must be characterised; dataset documentation required.
- **§6.4.2 Model development** — names **data leakage**, "time-traveling", and
  over/under-sampling-before-splitting as explicit pitfalls; RL is treated as a distinct paradigm
  (reward design, exploration, simulator dependence).
- **§6.4.3 V&V** — adversarial testing, statistical testing, **SEU/bit-flip testing**, unintended-behaviour
  detection, and **§6.4.3.1.4 target-specific testing**: hardware-dependent metrics such as
  *"inference time or power consumption … cannot be evaluated in the development machine"*.
- **§6.4.4 Deployment** — software criticality A–E; **"safety cage" architecture with the rule
  "Do not mitigate ML with more ML"**; on-board constraint monitoring; data- and behaviour-drift
  monitoring; **on-orbit retraining discouraged** (retrain on the ground, re-upload).
- **Simulation** — the handbook defines **no simulation verification level**; simulators appear as
  *data sources* (a digital twin, or an *"operational simulator"* running the real flight software
  on a *"processor emulator"*) and as a domain risk.
- **`hardware-in-the-loop`, `processor-in-the-loop`, `software-in-the-loop`, `MIL/SIL/HIL` do not
  appear in ECSS-E-HB-40-02A at all.** The MIL→SIL→HIL naming is the thesis's own (correct and
  defensible) convention and must be justified from the verification logic of ECSS-E-ST-10-03 /
  Q-ST-80, plus CoDANN §7.2.2 — not cited to the ML handbook.

**CoDANN (Airbus + Daedalean for an EASA IPC agreement, 2019–2020)** is a *concept* study, not an
approved means of compliance. Its transferable content:

- A **W-shaped lifecycle** overlaying a data-driven development stream on the classical V-model, and
  the concept of **"Learning Assurance"** as the data/ML counterpart of development assurance.
- **PLAC — Property to be Learned, Assumptions and Constraints** — the requirement analogue for a
  learned component; the model is assured *only within its ODD*.
- **§6.2 Data management** — quality characteristics, ODD definition, sampling strategy, an
  **input-distribution discriminator** to detect out-of-ODD inputs, and independence of
  train/validation/test: *"The validation and test datasets need to be large enough such that good
  model performance on these leads to adequate guarantees on the required operational
  performance."*
- **§6.3 Training** — reproducible training framework and **training curves as design-phase
  artifacts**, plus a reproducibility criterion.
- **§6.7 Artifact checklist** (the only explicit checklist in either document): **PLAC, dataset
  specs, design-phase details including training curves, the end model, the input-distribution
  discriminator, the OOD dataset, error metrics.**
- **§7.2 Synthesized data** — *"synthetic data should never be used without proper analysis and
  mitigation of the domain biases, no matter how realistic it looks"* and *"testing using
  synthesized data can only supplement testing using actual data … and not … replace it."*
- **§9.3/§9.4 Safety assessment** — architectural mitigations, and *"Dissimilarity between the
  outputs shall be verified through a statistical test to demonstrate the independence of their
  errors."*
- **Ch. 11 explicitly not covered** — inference-phase verification, hardware accelerators,
  **adaptive/on-line learning**, explainability, post-certification change management.

**Three verbatim hits on thesis decisions:**

| Thesis decision | External support |
|---|---|
| Safety governor is **physics-based, not another NN** (redline #7) | ECSS §6.4.4.3.2: **"Do not mitigate ML with more ML."** |
| Deployed policy **never receives `h_true`** (redline #9) | C4 estimates Φ̂ online and is never told the fault; ECSS/CoDANN require ODD-consistent inputs |
| MEKF before deployment, sim-to-real argument required | D4's train-with-noise ablation; CoDANN §7.2.2 (synthetic evidence supplements, never replaces, hardware evidence) |

---

## 11. Where this thesis sits

| Dimension | Corpus norm | This thesis | Verdict |
|---|---|---|---|
| Plant | custom Python/MATLAB; 2 papers use Basilisk | custom NumPy 6-DOF, config-driven YAML | **at norm** (mainstream; no need to migrate to Basilisk) |
| Integrator / step documented | frequently not stated | `dt_s` 0.1, substeps, 5 Hz, 4500×0.2 s = 900 s | **above norm** |
| Orbit + GG + magnetic + desaturation together | none do all four | all four present | **above norm** |
| Aero/SRP/residual flags | either absent or honestly declared absent | present but silently inert | **below norm** — fix by implementing or deleting + stating |
| Sensor model | mostly perfect state | star-tracker passthrough + noisy gyro (≈ perfect attitude) | **at norm** (MEKF unimplemented) |
| Estimator feeding the policy | **zero papers** | MEKF planned, not implemented; h_hat-only rule is a design commitment | **would be above norm once implemented** |
| Actuator model + allocation + desaturation | rare | 3 RW + 3 MTQ, shared allocator, desaturation | **above norm** |
| Fault model richness | one LOE + one bias, fixed, single wheel | h ∈ [0.5,1] per wheel, continuous, per-episode | **above norm — strongest in corpus** |
| Unseen-fault test | **no paper does it** | dead wheel (h = 0) is out of training distribution by construction | **unique** |
| Algorithm | PPO dominant | PPO (SAC optional challenger) | **at norm** |
| Network size | 2×64 … 2×512 | 2×64 | **at norm** |
| Parallel envs | rarely stated | SubprocVecEnv(8) + VecNormalize, saved stats | **above norm** |
| Training budget | 2–3×10⁷ steps / 32 workers (subfield SOTA); 3×10⁶ (best comparable) | **2×10⁶ / 8 envs** | **below norm — the most attackable number** |
| Reward shaping | universal; A2's 100 s low-pass decisive | bonus/quad shape validated (4.07° → 0.170°) | **at norm, corroborated** |
| Evaluation rigour | mostly 1–5 cases; best 10,000 episodes | 60/30-IC paired A/B, bit-identical replica, 4-s.f. archive reproduction | **above norm** |
| Paired RL-vs-classical with matched tuning | **no paper** | C1 paired protocol; LQR re-tuned per case is planned | **unique** (must be finished carefully) |
| HIL | 4 precedents; none for a 3-RW/3-MTQ fault-tolerant RL policy on an ESP32-S3 | Phase D planned | **would be first-of-kind — risk *and* claim** |
| Standards mapping | not attempted anywhere in corpus | ECSS/CoDANN not yet mapped into the thesis | **opportunity** |

---

## 12. Actionable recommendations (ranked by value ÷ effort)

1. **Write the environment specification as a document** (this is CoDANN §6.2 / ECSS §6.4.1
   compliance and it is cheap): initial-attitude distribution, sensor noise and rate models,
   actuator limits, allocation and desaturation law, fault set and its *training* distribution,
   episode termination, reward terms and weights, and what lies **outside** the ODD. Note that the
   ODD currently *excludes* h = 0, which is precisely why the dead-wheel case is a generalisation
   test. → *Deliverable: `docs/Environment_Specification.md`.*
2. **Raise the training budget or state the limitation.** 20 M steps ≈ 2.4 h at the measured
   2,269 fps — affordable, and it moves the thesis from 10× below the subfield norm to at-par with
   the best comparable study (B3's 3×10⁶). If it is not raised, the thesis must say so and justify
   it (episode-count reasoning: 2 M / 8 envs at 4,500 steps/episode = 55 episodes per worker).
3. **Add the unseen-fault test as a first-class, pass/fail scenario** with explicit criteria
   (attitude error back below θ within T s, wheel speeds below ω_max, no NaN/unbounded action) and
   report **failures as well as successes**. This is the single strongest examinable requirement
   (CoDANN §6.4 / ECSS §6.4.3) and no paper in the corpus satisfies it.
4. **Adopt E3/E4's severity-sweep evaluation protocol** for the fault chapter: fixed shared seed
   set, ~50 trials per configuration, metrics relative to nominal, plus a survival/"alive rate"
   metric. This is the published norm in the exact subfield lineage (BSK-RL) the thesis builds on.
5. **Fix the documentation-integrity defects before an examiner finds them:** (i) the two
   same-named `adcs_env.py` files with different backends — rename the Basilisk one and header
   both; (ii) `PROJECT_BRIEF.md` describes the abandoned Basilisk lineage as *the* codebase and
   says Phase 1 has not started; (iii) `estimator_hz` is dead config; (iv) `eval_rl_vs_lqr.py`
   scores RL with `hold=10.0` but LQR with `hold=30.0`; (v) the inert aero/SRP/residual flags.
6. **Implement the MEKF, then re-run the headline numbers with the estimated state** — and report
   both (h_true upper bound vs h_hat deployment) as the O1-H/O1-E split already plans. This is the
   change that moves the thesis above the entire corpus.
7. **Try A2's 100 s moving-average reward filter** as a single-factor variant (after C4.1 closes) —
   it is the one reward technique in the corpus that has been shown to flip a non-converging policy
   to converging, and it targets the acquisition-transient/fine-pointing mixing that forced the
   earlier reward redesign.
8. **For Phase D, copy C4's staged matrix and A2's timing table.** Report on the ESP32-S3:
   inference time avg/max/σ against a fixed period and deadline, RAM and flash footprint in bytes,
   quantisation scheme (int8), and the dead-zone/saturation behaviour of the actuator interface.
   Pre-empt C3's finding by measuring the deployment footprint *before* claiming on-board
   feasibility. State honestly that no static WCET tool covers Xtensa (OTawa), so the timing claim
   is measurement-based.
9. **Quantise the sim-to-real argument in the thesis**: use D4's train-with-noise result and
   CoDANN §7.2.2 to justify *why* randomised training is the right methodology, and state that
   simulated evidence supplements rather than replaces hardware evidence.
10. **Build the assurance-case sketch** (claims → evidence → limitations) and the CoDANN §6.7
    artifact list into an appendix; note explicitly that MIL/SIL/HIL is the thesis's own convention,
    not an ECSS term.
11. **Consider adding a rate-violation termination** (A1: |ω| > 0.5 rad/s; C1: > 0.1 rad/s) or
    documenting why it is unnecessary — it is the standard guard against a tumbling solution.
12. **Cite Basilisk (E1) and BSK-RL (E3/E4) for context, but do not migrate mid-thesis.** Basilisk
    buys a credible plant, RL precedent and a published SWIL split matching the ESP32 topology; it
    costs a C++/SWIG toolchain and its magnetorquer module is undocumented in the paper. A
    cross-validation of one scenario against Basilisk would be a strong, contained use.

---

## 13. Citation map

| Claim in the thesis | Cite |
|---|---|
| Custom Gym plant is normal practice | A1, C1, C2, D1–D4 |
| PPO is the mainstream algorithm for ADCS | A1, A2, C1, D2, D4 |
| Fault randomisation + estimated fault at test | **B3 (Lu)** |
| Train-with-noise measurably improves success (69 → 85 %) | **D4** |
| Fault-blind training barely helps; fault *index* obs helps; binary flag hurts | **E3/E4 (Nagano & Schaub)** |
| Severity-sweep evaluation protocol, ~50 trials, fixed seeds | **E3/E4** |
| Reward low-pass filtering was decisive | **A2** |
| Reward shaping is universal; raw quadratic cost plateaus | A1, A2, A3, B4, D1 + thesis's own 4.07°→0.170° |
| Action-space simplification is an accepted design choice | **A1 (19 torques), A2 (125/1331)** |
| Never specialise one policy per fault (the anti-pattern) | **C1** |
| Actuator dead zone broke the sim-to-real transfer (3× degradation) | **C3** |
| MIL→SIL→HIL-a/b/c staging matrix; real-time budget 3.86/6.62 ms vs 100 ms | **C4** |
| PIL on an MCU with WCET vs deadline (73.9 ms < 100 ms) | **A2** |
| ESP32 can host a policy in a real 3-RW rig; PD baseline fails on hardware | **C2** |
| Two-stage sim-to-real: MIL → PIL → HIL, TRL 4 → 8 | **G2/G3 (UPMSAT-2)** |
| HIL with air bearing + Helmholtz coils; fault-injection test cases | **G1 (pSAT II)** |
| On-orbit validation by an independent cross-check (thermal, 4,004 points) | **G3** |
| WCET analysis is a static, target-specific discipline | **G5, G6 (OTAWA)** |
| No static WCET tool covers Xtensa/ESP32 | **G6 (OTawa ISA list)** |
| Simulators as data sources; operational simulator + processor emulator | **F1 (ECSS §6.4.1)** |
| **"Do not mitigate ML with more ML"** → physics-based safety cage | **F1 (ECSS §6.4.4.3.2)** |
| Target-specific testing: inference time/power cannot be measured off-target | **F1 (ECSS §6.4.3.1.4)** |
| PLAC, learning assurance, artifact checklist, input-distribution discriminator | **F2 (CoDANN)** |
| Synthetic data supplements, never replaces, hardware evidence | **F2 (CoDANN §7.2.2)** |
| Monitors must be statistically shown to be dissimilar/independent | **F2 (CoDANN §9.4)** |
| Basilisk architecture, Task Group Interface, SWIL split, 365× speedup | **E1** |
| Adaptive latent world model + MPC; adaptation cost 0.01–0.03 s | **E2 (AdaJEPA)** |
| Dead wheel changes the rank of the allocation map (why AdaJEPA's parameter-shift results do not transfer) | **E2** + thesis's own allocation analysis |

---

## 14. Honest limitations of this survey

- Three source conversions are defective and are flagged rather than repaired: Lu (B3) Tables 5–7
  and B2's P(0); Zahedi's (C3) 2 s vs 6 s unit inconsistency; doc-5 (E4) Table 3 column collapse.
  Where a number was illegible, the extraction says so.
- Two of the four "environment" groupings mix paradigms: C4 and G4/G5/G6 are **not** RL papers. They
  were included deliberately for their HIL, timing and verification architecture, which the RL
  papers lack.
- E3/E4 are the closest methodological siblings (same Basilisk/BSK-RL lineage, same fault concern)
  and are the strongest external benchmark for the thesis's evaluation protocol — but they solve
  **task scheduling**, not attitude control, so their numbers are not comparably transferable;
  only their *method* transfers.
- E2 (AdaJEPA) is a manipulation/navigation world model with **no rigid-body control, no actuator
  fault and no embedded target**. Its reported shifts are parameter perturbations (mass ×0.2,
  damping ×20), whereas a dead reaction wheel changes the *rank* of the allocation map — so Phase F
  should be scoped to degraded (50 %) wheels or to estimation/shielding, and this survey finds no
  evidence supporting a stronger claim.
