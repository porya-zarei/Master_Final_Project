# A — Core attitude-control RL papers: environment / training / simulation extraction

Scope: ENVIRONMENT, TRAINING and SIMULATION setup for three spacecraft-attitude RL papers, extracted
against a fixed schema. "not stated" = the paper does not say it (no inference, no invented numbers).
Thesis context of the reader: 24U nanosat, ~35 kg, J = diag(0.38, 0.73, 0.58) kg·m², 3 RWs + 3 MTQs,
star tracker + sun sensor + gyro + magnetometer (+GPS), nadir pointing from random attitude/rate,
faults = one of three RWs dead or limited to 50 % torque, SB3 PPO 8 parallel envs, 5 Hz, 900 s episodes,
roadmap MIL → SIL → HIL (ESP32-S3).

Sources (markdown conversions; OCR/multi-column artifacts ignored):
1. Elkins, Sood, Rumpf, *Autonomous Spacecraft Attitude Control Using Deep Reinforcement Learning*,
   IAC-20-C1.9.8, 71st IAC, 2020. (UA / NASA Ames)
2. Pérez-Muñoz, López-García, García-Villoria, Alonso, Porras-Hermoso, Pérez, *Feasibility of Deep
   Reinforcement Learning for the real-time attitude control of a satellite system*,
   Journal of Systems Architecture 167 (2025) 103513. (UPM / UPMSat-2 → UPMSat-3)
3. El-Dalahmeh, Jabbarpour, Vo, Kowalczyk, *Intelligent Control of Spacecraft Reaction Wheel Attitude
   Using Deep Reinforcement Learning*, arXiv:2507.03686v1 (preprint submitted to Elsevier, Jul 2025).
   (Swinburne / South Australia / IBS PAN)

---

## Paper 1 — Elkins, Sood & Rumpf (IAC-20-C1.9.8, 2020): discrete-torque PPO slew controller

**Simulator / environment**
- Custom simulation of spacecraft rotational dynamics, written in Python (neural networks in **PyTorch**);
  Numba acceleration used for the simulation loop. No physics engine, no Gazebo/Basilisk/STK/GMAT.
- Open source: **not stated** (no code/data availability statement).
- Integrator: **4th-order Runge–Kutta**, applied to Euler's rotational equations + quaternion kinematics;
  integration fidelity **Δt = 1/240 s** (stated as similar to Bullet).
- Control frequency: agent acts **once every 20 timesteps** ("frameskip", a variant of the Atari
  frameskip idea); action applied over the next timestep, then 20 free-rotation steps →
  control frequency **240/21 ≈ 11.43 Hz** during training. Evaluation statistics computed with
  frameskip 5 → **40 Hz**. Paper notes frameskip can be decreased at implementation time, which
  "will generally increase agent control accuracy".
- No sensor models in the loop; no orbit propagation.

**Dynamics fidelity**
- 6-DOF rigid body: **attitude only** (Euler equations `M = I ω̇ + ω×Iω`, skew-symmetric cross-product
  form, quaternion kinematics `q̇e = ½ Ω(ω) qe`), error quaternion renormalized after each integration.
- Spacecraft model: inertia tensor of the **Lockheed Martin LM50** bus, taken from their earlier
  work [13]. Numeric inertia values: **not stated** in this paper.
- Orbit propagation: **no**. Gravity gradient: **no** (spacecraft "initialized at rest, with no
  perturbation or gravitational torques"). Drag / SRP / magnetic field model: **no**. Wheel friction /
  RW jitter: **no** (commanded moments are applied directly; no wheel dynamics).
- Rotation is about body-fixed principal axes; the controlled moment is the only external torque.

**Sensors & estimation**
- **No sensors and no estimator.** Explicit: "attitude sensor models, such as star trackers or inertial
  guidance units, were not used for the attitude representation."
- State vector `s_t = {qe, q̇e, ω}` (error quaternion, its derivative, body angular velocity) — i.e.
  **perfect/noiseless full-state feedback**.
- Noise / bias numbers: **not stated** (none exist in the setup).
- Two reported implementation tricks: normalize state components to order-1 (weight-init mismatch
  cripples learning), and prefer relative representations (error quaternion vs. absolute frame).

**Actuators**
- Direct commanded **moment vectors**, magnitudes **0.5 / 0.05 / 0.005 N·m** on ±x, ±y, ±z, plus a zero
  action → **19 discrete actions**. Only one body axis can be actuated per timestep ("highly
  constrained control problem"). Magnitudes chosen to sit inside typical RW max-torque bounds for the
  modelled bus; smaller values give the agent stabilisation authority.
- RW dynamics, torque allocation, momentum management/desaturation: **not stated** (no wheels modelled).
- Relationship to the real actuator loop (e.g. wheel-torque command conversion): not stated.

**Fault model**
- **None.** No actuator or sensor faults; no degradation, no partial loss, no fault-injection study.

**RL setup**
- Algorithm: **PPO-clip variant** (their own implementation; not SB3/Ray/TF-Agents).
- Networks (both MLP, no shared parameters, ReLU hidden): policy **400 → 300 → 19** (output LogSoftmax);
  value **400 → 300 → 1**. Architecture inherited from the TD3 paper of [13] for comparability.
- Hyperparameters (Appendix A, Table 4): γ = **0.99**; batch size **128**; minibatch **30**;
  learning rate **3×10⁻⁴ → 1×10⁻⁵ linearly annealed** (annealing "critical" for success);
  clip ε = **0.2**; entropy coefficient c = **0.0001** (high values 0.001/0.01 caused instability);
  Adam optimizer; separate policy/value losses; advantage = return − V(s).
- Parallel envs: **not stated** (single environment implied). Vectorization: not stated.
- Training: **4,340 epochs**, stopped when episode reward plateaued near **2500**.
  Wall-clock **≈ 1 day 20 h** (with Numba acceleration).
- Hardware: **NVIDIA RTX 2070 Super** GPU for all neural-network computation (same rig as [13]);
  "without the need for high-performance computing" is claimed in the abstract.

**Simulation workflow**
- Vectorization: not stated. Domain randomization: **no** (only randomised initial conditions).
  Curriculum: not stated / none.
- Initial conditions: initial **error quaternion sampled on SO(3)** — random rotation axis (uniform unit
  vector in spherical coordinates) with rotation angle **φ ∈ [30°, 150°]** (so "large-angle slew"
  = 30–150°), spacecraft **at rest**.
- Reward (Eqs. 12–13, the paper's main contribution):
  `r_a = exp(−φ/(0.14·2π))` if `q_s,t > q_s,t−1`, else `exp(−φ/(0.14·2π)) − 1`;
  `r_t = r_a + 9` if `φ ≤ 0.25°`, else `r_a`. Scale constant 0.14 chosen so the exponential returns
  ≈0.001 at φ = 180°; the +9 bonus is deliberately ~1 order of magnitude above the shaped reward
  ("crucial for successful training").
- Terminal rewards: **+50** if terminal φ ≤ 0.25°, else 0; **−50** if |ω| > 0.5 rad/s.
- Episode termination: **after 500 agent actions (43.75 s of real time)** or when **|ω| > 0.5 rad/s**.
- Reported design lesson: the simple binary shaped reward of [13] failed with discrete PPO because the
  entropy term collapsed once the agent sat in a local optimum; a dense continuous reward fixed it.

**Evaluation protocol**
- **5,000 simulated episodes** at 40 Hz control frequency; no Monte-Carlo statement beyond that count.
- Metrics: angular error φ at the "closest state" (min φ over episode) and at the "terminal state";
  |ω| at both states. Success criterion: reaching and holding the desired attitude within the goal
  tolerance φ ≤ 0.25°.
- Baselines: qualitative comparison with the authors' earlier continuous-TD3 work [13] ("maximum angular
  error decreased by two orders of magnitude") and against the **tabulated pointing accuracies of the
  LM50 bus** (industry requirement). No classical controller run in this same environment.
- Statistical treatment: mean, std. dev., min, Q1/Q2/Q3, max (Table 2). No confidence intervals or
  hypothesis tests.
- Additional qualitative demos: three **100° slews** with rotation axes `[±0.57735, ±0.57735, 0.57735]`
  (one per octant), full orientation/error/rate histories in Appendix B.

**Sim-to-hardware**
- No MIL/SIL/HIL stage; no real-time constraint analysis; no embedded target. Deployment target
  remains the GPU/Python simulator. Future work = distributed RL / online learning, not hardware.

**Key quantitative results**
- All **5,000/5,000** evaluation episodes reached and maintained the desired attitude.
- Closest-state angular error: mean **0.000380°**, std **0.000233°**, min **0.000007°**, median
  **0.000335°**, max **0.001980°**. Terminal-state φ: mean **0.001954°**, std **0.000705°**, max
  **0.004558°**.
- Angular velocity: closest-state |ω| mean **0.001976 rad/s** (max 0.019339), terminal-state mean
  **0.001752 rad/s** (max 0.018723).
- Training: 4,340 epochs ≈ **1 d 20 h** on one RTX 2070 Super.
- Vs. [13]: max angular error improved by **~2 orders of magnitude**.

**Directly reusable for the 24U fault-tolerant thesis**
- Dense, exponentially-scaled attitude-error reward with an order-of-magnitude in-tolerance bonus
  (and the documented failure of sparse/binary rewards under PPO) — and the frame-skip idea that lets
  a low *commanded* control rate (11–40 Hz) ride on a much finer integration step (240 Hz).

---

## Paper 2 — Pérez-Muñoz et al. (J. Systems Architecture, 2025): magnetic ACS with PIL validation

**Simulator / environment**
- **MATLAB/Simulink R2024b** (Windows) model of the **UPMSat-2** ACS, inherited from the mission's
  model-driven-engineering design (ACS validated in orbit, 50 kg-class satellite, 530 km SSO,
  95-min period). Blocks: **Sun** (solar radiation), **Earth** (magnetic field), **Satellite**
  (magnetometers + magnetorquers), **Perturbations**, **Dynamics**, **Outputs**.
- RL framework: **MATLAB Reinforcement Learning Toolbox** (chosen because the plant was already in
  Simulink and because Embedded Coder can auto-generate C from the agent).
- Open source: **not stated** (proprietary toolchain; paper itself is CC-BY).
- Integrator: **not stated** (Simulink solver not named). **Simulation step 0.1 s**, chosen to comply
  with the minimum intervals of the control cycle. Simulated horizon **30,000 s = first 5 orbital
  periods** after launcher separation.
- Control cycle (from the flight design): **period 2000 ms**, magnetometer readings every 200 ms
  (5 samples/s), RL control law executes with **deadline 100 ms**, magnetorquer actuation 0–500 ms,
  then ≥500 ms with no actuation (magnetometer/magnetorquer interference avoidance). So the RL
  controller runs at **0.5 Hz** with a hard 100 ms response deadline.

**Dynamics fidelity**
- Attitude + **orbit** (5 orbits simulated). Perturbations modelled explicitly: **gravitational
  (gravity-gradient) torque, magnetic residual torque, aerodynamic and solar-radiation-pressure
  forces and torques**.
- Earth magnetic field model: provided by the Simulink Earth block; specific model (IGRF/dipole):
  **not stated**.
- 6-DOF: attitude dynamics with orbit; rigid body. Reaction wheels: none (magnetic-only ACS), so wheel
  friction/jitter and RW saturation are out of scope.

**Sensors & estimation**
- Sensors: **3 redundant flux-gate magnetometers** (3-axis), read through a **12-bit ADC**, 5 readings
  per second per axis (→ 15 raw values per control cycle). No star tracker / gyro in this ACS.
- Estimation: **no attitude estimator (no EKF/MEKF/UKF)** — this is a magnetic B-dot-derived control
  law; the observation is the magnetic field only.
- State vector **x ∈ R⁹**: (i) derivative of the magnetometer readings `Ḃ` (range ±8×10⁶ nT/s),
  (ii) averaged readings `B̄` (range ±5×10⁵ nT), (iii) angular-velocity error `ω_d − ω` (0–0.25 rad/s).
  Min–max normalised to [0, 1] (x_norm = (x−x_min)/(x_max−x_min)).
- Noise handling: they average the 5 in-cycle magnetometer samples "to filter out part of the noise".
  **Exact noise/bias magnitudes: not stated** (only the field-value ranges above).

**Actuators**
- **Three single-axis orthogonal magnetorquers**, magnetic moment `m` [A·m²]; control torque
  `T_c = m × B`. No reaction wheels, no CMGs, no thrusters.
- PWM discretisation of each axis (no DACs on the OBC): duty cycles ±{0, 100, 200, 300, 400, 500} ms,
  mapped from |m| bins of 0–0.05 / 0.05–0.15 / 0.15–0.25 / 0.25–0.35 / 0.35–0.45 / 0.45–2 A·m².
- Allocation: n/a (one torquer per axis). Desaturation: n/a (magnetic actuators cannot saturate
  angular momentum). Actuation is inherently bounded by the field-B cross-product geometry.

**Fault model**
- **None.** No actuator faults, no sensor faults, no degradation study; robustness is only implicit
  (unseen initial conditions, perturbations, non-linearities).

**RL setup**
- Algorithm: **PPO** (MathWorks RL Toolbox, actor–critic, MLP). Selected because it supports both
  discrete and continuous action spaces (needed for PWM-driven magnetorquers) and for stable
  learning; the paper also notes PPO was shown to beat traditional controllers [15] and TD3 in
  discrete/constrained spaces [9].
- Networks: Actor MLP hidden layers **400, 256, 200, 200 (ReLU)** + linear output; Critic MLP
  **400, 200, 200 (ReLU)** + linear output. Separate actor/critic learning rates.
- Hyperparameters (Table 4): number of episodes **1000**; steps per episode **4000 (= 8000 s)**;
  clip ε **0.2**; entropy-loss weight **2×10⁻⁴**; experience horizon **1024**; minibatch **512**;
  γ **0.99**; advantage estimate **GAE (factor 0.95)**; actor lr **1×10⁻⁵**; critic lr **1×10⁻⁴**
  (actor deliberately slower so the critic trains first).
- Parallel envs / vectorisation: **not stated** (single Simulink model). Buffer: n/a (on-policy).
- Training hardware: **Intel i9-13900, 32 GB RAM, integrated Intel UHD Graphics 770** (no discrete GPU).
  Wall-clock training time: **not stated**.
- Extra experiment: 5,000 episodes × 5,000 steps (10,000 s) **did not** improve performance; horizon and
  minibatch sizes (1024/512) were limited by training-hardware memory.

**Simulation workflow**
- **Iterative design loop** (3 documented iterations): (1) continuous action space; (2) discrete action
  space; (3) filtered reward. Each iteration = reward/action design → train → evaluate on metrics and
  plots → decide next iteration.
- Action-space construction (iteration 2): full discrete combination set = 11³ = **1331** duty-cycle
  combos; pruned to 5³ = **125** actions using a **Pareto chart of the nominal UPMSat-2 ACS** action
  usage (three most-used duty cycles covered >85 % of occurrences) → 125 output neurons.
- Reward (iteration 1/2 base): errors `[X,Y,Z]_error = ω_d − ω`; `α = Σ|x_error|`;
  `R_base = 1 − exp(2πα)` (exponential decay chosen for sensitivity to small α, monotone worse-for-
  larger-error behaviour, and precedent in Elkins et al. [9]).
- Reward (iteration 3): **low-pass moving-average filter over the reward**, window **n = 100 s**
  (covers one oscillation period), `R_filter(ω_t) = (1/n) Σ_{k=t−n}^{t} R_base(ω_k)` — introduced
  because at high initial rates the raw reward oscillated and blocked learning.
- Domain randomization: **none**. Curriculum: **none** (but two training-rate configurations were
  tested and training at lower initial rate was easier).
- Episode/termination rules: episodes of a fixed **4000 steps = 8000 s**; evaluation extends to
  30,000 s (5 orbits) to test generalisation beyond the training horizon. Failed stabilisation is
  handled by scoring the whole 30,000 s (`t_set = ∞`).

**Evaluation protocol**
- Deterministic per-iteration evaluation in a single scenario (number of Monte-Carlo runs/repeats:
  **not stated** — effectively one 30,000 s run per configuration); metrics sampled at 1 s
  (angular velocity ω, third-Euler-angle misalignment θ).
- Validity conditions: initial `ω0 = [0, 0, 0.1] rad/s` (and, for iteration 2 config 2, training at
  `[0.05, −0.05, −0.05] rad/s`), initial Euler angles `[φ0, θ0, ψ0] = [0, 30, 60]°` — training and
  evaluation at *different* rates is explicitly used as a generalisation argument.
- Metrics: **MAE, MSE, RMSE per axis** on the angular-velocity error (`e = ω − ω_d`) and **settling time
  t_set** defined as the time for |ω| to stay within 5 % of the steady-state value. Metrics are also
  reported separately for the **detumbling** and **stabilisation** phases.
- Baselines / references: the mission's **nominal B-dot magnetic control law** (used for the action
  Pareto analysis and as the behavioural reference), the system requirement
  `ω_d = [0, 0, 0.1] rad/s`; iteration-to-iteration comparison stands in for a classical-controller
  benchmark. No statistical hypothesis testing.

**Sim-to-hardware**
- Explicit staged validation, on a **real embedded platform** (processor-in-the-loop, which the paper
  itself calls "commonly known as PIL"): **STM32F407**, ARM **Cortex-M4 @ 168 MHz, 1 MB flash,
  192 KB SRAM** (chosen for similarity to the UPMSat-3 processor). Board runs a representative OBSW
  (Ada, Open Ravenscar Real-Time Kernel port) with Housekeeping (1000 ms), TTC (10,000 ms) and ACS
  (period 2000 ms, deadline 100 ms) tasks; it exchanges state/actions with the Simulink host over
  **UART**; magnetometers/magnetorquers (MGM/MGT) are on the simulation side.
- Code generation: **Embedded Coder** → standalone **C99**, configured to **MISRA C:2012**, with
  protection against arithmetic exceptions; 12 generated files.
- Timing/resource analysis (ECSS-driven): **WCET via OTAWA** = 12,421,975 cycles @168 MHz =
  **73.9 ms** (theoretical worst path) vs. 100 ms deadline → `R_ACS = 73.9 ms < D_ACS`, schedulable;
  **measured average maximum inference execution time 9.72 ms** (dynamic test, thousands of
  inferences). Executable size **≈ 370 kB** vs. UPMSat-2's 2 MB OBC (UPMSat-3 has up to 32 MB).
- Static metrics: `callPredict.c` **43,303 LOC** (vs. 50–75 in the ECSS-Q-HB-80-04A reference range),
  max complexity **15** (satisfies criticality category C), max nesting depth **5** (satisfies all
  levels). Tool qualification still required for a safety system.
- HIL: **not yet** — explicitly future work (dynamic test bed at IDR-UPM being prepared for UPMSat-3).

**Key quantitative results**
- Iteration 1 (continuous actions): MAE = 5.8×10⁻² (X), 4.9×10⁻² (Y), 3.5×10⁻¹ rad/s (Z);
  settling time **∞** on all axes → unusable. Diagnosis: 64-bit continuous outputs (≈2⁶⁴ values per
  neuron) prevent convergence.
- Iteration 2 (discrete, config 1, trained at 0.1 rad/s): MAE 1.1×10⁻¹ / 1.2×10⁻¹ / 1.8×10⁻¹ rad/s,
  t_set = ∞ everywhere. Config 2 (trained at 0.05 rad/s): MAE **1.4×10⁻² / 1.3×10⁻² / 3.2×10⁻² rad/s**,
  t_set 8000 s on X and Y, ∞ on Z.
- Iteration 3 (base reward + 100 s moving-average filter, trained at 0.1 rad/s, evaluated 30,000 s):
  full-run MAE **1.6×10⁻² / 1.5×10⁻² / 2.2×10⁻² rad/s**, RMSE 3.8×10⁻² / 3.6×10⁻² / 4.5×10⁻² rad/s,
  t_set **8000 / 8000 / 6500 s** (Z best). Detumbling-phase MAE ≈ 5.9×10⁻² / 5.6×10⁻² / 5.9×10⁻³ rad/s.
  Stabilisation-phase MAE **8.5×10⁻⁴ / 8.6×10⁻⁴ / 7.6×10⁻³ rad/s** and RMSE
  **1.1×10⁻³ / 1.1×10⁻³ / 9.2×10⁻³ rad/s** (X/Y vs. Z). Iteration 3 met the attitude requirements.
- PIL (STM32F407) reproduced simulation behaviour: three axes stabilised to `ω_d`, Z-axis oscillation
  confined to ±0.05 rad/s. WCET 73.9 ms vs 100 ms deadline; ~370 kB code.

**Directly reusable for the 24U fault-tolerant thesis**
- The closest published precedent for the MIL → SIL → HIL roadmap: a control rate far slower than the
  simulation step (0.5 Hz control on a 0.1 s step) with an explicit deadline verified by WCET, plus
  the report-template for embedded budgeting (LOC, complexity, depth, code size, cycles) that the
  thesis's ESP32-S3 phase can mirror; and the documentation of reward iteration (continuous →
  discrete → filtered) as academic justification for reward design decisions.

---

## Paper 3 — El-Dalahmeh et al. (arXiv:2507.03686v1, 2025): TD3-HER-DWC vs. one dead RW

**Simulator / environment**
- **Basilisk Astrodynamics Simulation Framework** (open source, Kenneally/Piggott/Schaub 2020) for the
  small-satellite LEO kinematics/dynamics, wrapped in a **custom Python environment written to the
  OpenAI Gym standard** for the RL agent ("for training the neural networks, a custom simulation
  environment is created in Python, adhering to the OpenAI Gym standards").
- Integrator, simulation timestep and control frequency: **not stated** anywhere in the paper.
- Runtime/telemetry horizon: **8000 s** of simulated data per run; orbit: LEO small satellite/CubeSat.
- RL library: **Stable-Baselines3** (PyTorch) for TD3-HD, TD3, PPO and A2C.

**Dynamics fidelity**
- Kinematics in **Modified Rodrigues Parameters**: `ρ̇ = G_ρ ω`; rigid-body rotational dynamics
  `J ω̇ − S(ω)Jω = u_t` (i.e. 6-DOF attitude with the gyroscopic coupling term included).
- Orbit propagation: **not stated** (Basilisk provides it, but the paper does not configure or describe
  it). Gravity gradient, drag, SRP, magnetic-field model: **not stated / not itemised**.
- Wheel friction / jitter: **not stated**. RW model: speed range **±1500 rpm**, wheel inertia
  **4.67×10⁻⁴ kg·m²**; four **Honeywell HR16** wheels in a **pyramid configuration**.
- Attitude representation chosen for the *agent* is MRP error (compact, no singularities, no reliance
  on an arbitrary inertial reference frame).

**Sensors & estimation**
- Observation = state `s_t = {MRP_error, ω}` — MRP attitude error (current vs. desired orientation)
  and body angular velocity. Effectively **perfect state feedback**: no sensor models, no noise, no
  bias, no dropout, and **no estimator (no EKF/MEKF/UKF)** are described.
- The paper motivates including ω in the state ("allows the control system to make corrections") but
  gives **no noise/bias numbers**.

**Actuators**
- **4 reaction wheels** (pyramid) → redundant 4-wheel/3-axis actuation, so a single-wheel failure is
  recoverable; action `a_t = {τ1, τ2, τ3, τ4}` (one torque per wheel, continuous).
- Control torque assembly: `T = Σ_{i=0..3} λ_i RW_i`, where `λ_i` is a per-wheel weighting factor,
  equal in nominal conditions; on a fault the failed wheel's `λ_i` is set to **zero** and the remaining
  weights are **renormalised** over the operational wheels. A **backup wheel is activated only when
  necessary** (the paper notes ground telecommand/retuning is what the PD controller would need).
- Torque limits: not given numerically (DWC thresholds are "calibrated to … physical constraints of each
  reaction wheel, including maximum torque capacity", but no values). Momentum management/desaturation:
  **not stated** (no magnetorquers in this setup).

**Fault model**
- Fault studied: **one wheel (RW0) becomes unresponsive** (total failure — its torque drops to zero),
  injected **abruptly at t = 3000 s** inside the 8000 s run.
- Injection details: **fixed wheel and fixed injection time** in the reported experiments ("an RW
  failure is simulated by disabling one of the wheels at 3000th second"); partial/degraded-RW faults
  and randomised fault parameters/times are **not stated**.
- Seen during training? Algorithm 1 says the satellite dynamics model is loaded "including RW faults or
  unresponsive scenarios" and each episode initialises states "including RW faults"; the text also
  frames HER as the mechanism that "improves the agent's adaptability to fault scenarios" → faults are
  expected during training, but the paper **never states the fault schedule, probability, or whether a
  no-fault ablation was run**.

**RL setup**
- Algorithms: proposed **TD3-HD = TD3 + Hindsight Experience Replay (HER) + Dimension-Wise Clipping
  (DWC)**, with **TD3, PPO, A2C** as DRL baselines and **PD** as the classical baseline. All DRL
  implementations via **Stable-Baselines3** (PyTorch).
- TD3-HD actor: **four actor sub-networks** `λ_i` (one per RW) outputting Gaussian parameters
  `(µ_i, σ_i)` sampled to per-wheel torque actions; critic = TD3 twin Q-networks; **Importance Sampling
  (IS) weights ρ_t** and an **IS-weighted policy loss `J_IS` based on KL divergence** are used to
  correct behaviour-vs-target policy mismatch; parameter update `λ ← λ + ζ ∇_λ J_IS(λ)`.
- Training parameters (Table 6): learning rate ζ = **3×10⁻⁴**; replay buffer size **1,000,000**;
  batch size M = **128**; target update interval **2**; DWC clipping thresholds **0.2**; hidden units
  **256**; importance-sampling factor α_IS = **1**; trajectory size N = **100**; actor sub-networks 4.
  Also: HER buffer `E` with **future-goal sampling** strategy; γ, entropy/exploration settings,
  network depth, epochs K and iterations L are **named but never given numeric values**.
- Parallel envs / vectorisation: **not stated**. Total training steps or episodes: **not stated**.
  Wall-clock training time: **not stated**. Training hardware (CPU/GPU): **not stated**.
- Note: the paper claims these standard hyperparameters worked "without the need for extensive tuning",
  which it attributes to HER + DWC.

**Simulation workflow**
- Vectorisation: not stated. Domain randomisation: **not stated/none described**. Curriculum: **none**
  (explicitly discussed as an alternative to HER that "requires careful manual tuning").
  Sparse-reward mitigation is HER with future-goal relabelling rather than reward shaping alone.
- Reward (Eqs. 8–11, `reward = r1 + r2 + r3`):
  - `r1 = e_previous − e_current` (attitude-error reduction between consecutive steps — dense progress
    term),
  - `r2 = −10` if `|ω| > 1` rad/s, else 0 (angular-velocity/instability penalty),
  - `r3 = +0.01` if `e_current < 0.25°`, else `−0.01` (accuracy incentive).
- Threshold justification: **0.25°** selected from industry high-precision pointing practice;
  validation showed 0.1° caused excessive control effort and oscillations with no steady-state gain,
  while 0.5° gave insufficient precision; 0.25° also matches modern star-tracker/IMU detection ranges.
- Episode length and termination rules: **not stated** (the 8000 s figure is the telemetry/run horizon).
- DWC details: policy-gradient components clipped **per action dimension** to `[−c_i, c_i]`, with `c_i`
  adapted from per-dimension gradient-variance history, wheel torque capacity, and expected operating
  range — motivated by the zero-gradient problem of uniform clipping in high-dimensional action spaces.

**Evaluation protocol**
- One scenario per controller: **RW0 fails at 3000 s**, run to **8000 s**; no Monte-Carlo runs, no
  randomised initial conditions, no repeat runs, **no statistical treatment**.
- Metrics: pointing/attitude error angle (between the body-fixed and inertial frames), attitude-error
  history per axis, angular velocity traces and per-wheel torque histories; comparison is largely
  graphical (error metrics figures 5–14).
- Baselines: **PD controller** (fails after the fault, needs manual retuning/telecommand and does not
  activate the backup wheel), **PPO**, **A2C**, **standard TD3** — all under the same fault scenario.
- Success criterion: implicit (low, stable post-fault error; near-zero angular velocity; smooth torque
  redistribution), not stated as a numeric threshold.

**Sim-to-hardware**
- **None.** No MIL/SIL/HIL, no embedded deployment, no WCET/memory analysis, no MCU or GPU target. The
  paper only argues the method is "a powerful, fault-tolerant, on-board AI solution"; future work is
  multi-satellite constellations/distributed DRL.

**Key quantitative results (numbers the paper actually gives)**
- Physics/hardware numbers: RW speed range **±1500 rpm**; RW inertia **4.67×10⁻⁴ kg·m²**; 4 HR16 wheels
  in pyramid; fault at **t = 3000 s**; horizon **8000 s**; accuracy threshold **0.25°**; velocity
  penalty threshold **1 rad/s**; hyperparameters as in Table 6 (lr 3×10⁻⁴, buffer 10⁶, batch 128,
  target-update 2, DWC 0.2, hidden 256, α_IS 1, N = 100).
- Results are comparative/qualitative in text (no error magnitudes quoted): PD fails to adapt after
  3000 s (large deviations, persistent angular-velocity oscillations, manual retuning required);
  PPO adapts but stabilises more slowly with oscillatory torque; A2C redistributes torque effectively
  but converges more slowly with higher fluctuations (the paper also has a sentence attributing
  slowness to "PPO" inside the A2C discussion — an internal inconsistency); TD3 is the strongest of the
  three baselines ("quickest reduction in errors across all axes", near-zero post-fault error) but needs
  more compute and converges gradually due to sparse rewards; **TD3-HD is reported best overall** —
  rapid alignment, lowest/stable error, near-immediate angular-velocity alignment, smoothest torque
  redistribution (DWC prevented overcompensation) with RW0 torque → 0 and RW1–RW3 sharing the load.
- Recurring literature figures cited for context (not this paper's results): SMC + adaptive momentum
  distribution reduced attitude errors to **0.001°** in micro-satellite RWA-jitter work; DRL adaptive
  control validated for masses **10–1000 kg** in Basilisk.

**Directly reusable for the 24U fault-tolerant thesis**
- The scenario is the thesis scenario: an RW stops responding mid-run and the remaining wheels must
  absorb the task; reusable specifics are the **SB3/OpenAI-Gym+Bazilisk** stack, the **4-wheel pyramid
  (one-fault-tolerant) actuation with λ-weighted renormalised torque redistribution**, **per-wheel
  dimension-wise action clipping** so a dead wheel's channel cannot destabilise training, and the
  composite reward (progress term + velocity penalty + 0.25° accuracy bonus); also a citable statement
  that plain TD3/PPO/A2C under-deliver on fault tolerance, and a clear gap the thesis can beat —
  paper 3 reports **no** training cost, no randomisation and no HIL.

---

## Cross-cutting patterns

- **Rigid-body attitude only, orbit almost never.** Only paper 2 propagates an orbit and models
  gravity-gradient, magnetic-residual, aerodynamic and SRP torques; paper 1 explicitly has "no
  perturbation or gravitational torques"; paper 3 leaves the Basilisk environment configuration
  undescribed. A NumPy 6-DOF simulator without orbit is therefore in line with the field, and adding
  gravity gradient/SRP would already exceed papers 1 and 3.
- **Perfect state feedback dominates; estimation is the exception.** Papers 1 and 3 feed the true error
  quaternion/MRP and true body rate and use no sensors at all; paper 2 is the only one whose observation
  comes from a real sensor channel (5 magnetometer samples/cycle, noise partly removed by averaging).
  **No paper implements an EKF/MEKF/UKF, and none reports noise or bias numbers** — so a thesis that
  documents sensor noise explicitly (star tracker/sun sensor/gyro/magnetometer) is ahead of all three.
- **Reward shape, not algorithm class, is what the papers report as decisive.** Both PPO papers converge
  on an exponentially scaled attitude-error term with an in-tolerance bonus around **0.25°** (paper 1:
  `exp(−φ/0.14·2π)` + 9 bonus, terminal ±50; paper 3: error-reduction term + velocity penalty + ±0.01
  within 0.25°), and paper 2 shows an extra reward-domain fix (100 s moving-average low-pass) was
  required before the agent met requirements at all. Reward iteration is presented as legitimate,
  reportable research output.
- **Discretised/simplified action spaces beat continuous ones in both PPO studies**, while remaining
  continuous in the TD3 study: paper 1 → 19 near-impulsive torque actions on one axis at a time, with a
  20-step frameskip decoupling command rate (11.43 Hz) from integration (240 Hz); paper 2 → 125 of
  1331 PWM combinations pruned by actuator-usage Pareto analysis. Action-space reduction is the
  accepted way to make PPO converge; continuous 3–4 torque channels work with TD3-family methods.
- **Evaluation is thin everywhere: one deterministic scenario is the norm.** Paper 1 is the most
  thorough (5,000 episodes with mean/std/min/quartiles, all successful, mean pointing error
  3.8×10⁻⁴°); paper 2 evaluates one 30,000 s run per iteration; paper 3 runs a single 8000 s
  fault scenario per controller. Randomized initial conditions appear only in paper 1 (uniform SO(3)
  axis + φ ∈ [30°, 150°], at rest); randomized *disturbances*, curricula and explicit statistical tests
  are absent from all three. Paper 3 injects faults but never randomizes or perturbs them.
- **Hardware-in-the-loop is nearly unexplored — the gap the thesis targets.** Papers 1 and 3 stop at
  simulation; the only embedded evidence in the set is paper 2's processor-in-the-loop on an
  **STM32F407** (Cortex-M4 @168 MHz) with auto-generated MISRA C99, **WCET 73.9 ms vs a 100 ms
  deadline**, measured worst-case inference **9.72 ms** and a **~370 kB** footprint — and even that is
  a magnetorquer controller, with HIL itself still future work. A PPO controller for a 3-RW/3-MTQ
  nanosat, sized for an ESP32-S3 with measured inference latency and a fault-randomized policy,
  has no direct precedent among these three papers.
- **Fault tolerance is asserted more often than it is engineered.** Only paper 3 actually trains/evaluates
  a hardware fault (one unresponsive wheel); papers 1 and 2 model no faults at all, yet the thesis
  requirement (one of three wheels dead **or** limited to 50 % torque, randomized per episode as
  h ∈ [0.5, 1]) is a strictly stronger and more testable fault setting than anything reported here —
  paper 3 does not even state that its faults are randomised, partial, or replicated.
