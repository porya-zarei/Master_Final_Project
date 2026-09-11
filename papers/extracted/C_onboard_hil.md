# Batch C — Environment, Training, Onboard Deployment & HIL Setup

Extraction of 4 papers on underactuated / hierarchical / onboard RL attitude control and RW hardware-in-the-loop.
Compiled for: M.Sc. thesis *"Fault-Tolerant Attitude Control of Nanosatellites Using Reinforcement Learning: From Simulation to Hardware-in-the-Loop"* (University of Tehran).
Target system: 24U nanosat, ~35 kg, `J = diag(0.38, 0.73, 0.58)` kg·m², 3 RW + 3 MTQ, star tracker + sun sensor + gyro + magnetometer + GPS. Roadmap MIL → SIL → HIL with ESP32-S3 as the HIL target (explicitly not a flight-qualified OBC).

Convention: `not stated` = the paper does not report it. Where a paper prints an internally inconsistent value or an implausible unit, it is reported verbatim and flagged `[as printed; possible typo]` — nothing is corrected by inference.

---

## C1. Deep Reinforcement Learning Policies for Underactuated Satellite Attitude Control

El Hariry, Cini, Mellone, Balossino (Argotec srl). 35th NeurIPS 2021 (Sydney). Reference platform: ArgoMoon (6U, deep-space small satellite).

### Simulator / environment
- Custom environment built on the **OpenAI Gym interface**, in **Python**, modelling satellite attitude dynamics "while in orbit"; ArgoMoon used as the reference platform. Explicitly *not* MATLAB/Simulink, Gazebo or Basilisk.
- Integrator: **Euler method** for a fixed Δt which "corresponds to the system response time, i.e., the elapsed time between sending the command and receiving the telemetry (containing the new attitude information)". Appendix A.2: kinematics + Eq. (1) integrated with the Euler method "with a step size of **100**" `[as printed; units not stated — ambiguous]`.
- Command granularity: each action applies a **continuous torque for δt = 0.5 s** per body axis.
- **Control frequency: 2 Hz** (agent observes and acts at 2 Hz) — deliberately low "to not starve the other ongoing process in the satellite on-board computer".
- Real-time simulator: **yes, at HIL only** — a "Real Dynamic Processor" (RDP) propagates the attitude in real time (see HIL section).

### Dynamics fidelity
- 6-DOF rigid body: **attitude only** (Euler's rotation equations `M = I ω̇ + ω×Iω`). **No orbit propagation** — assumed already in final orbit; no detumbling.
- Disturbances: **none modelled** ("we do not consider … presence of external disturbances or variations in the system's inertial mass").
- Magnetic field: **not modelled**. No MTQ.
- Initial condition: **zero wheel speed and zero angular momentum**, assumed for both simulation and HIL.
- Underactuated cases: **yes** — 3 RWs nominal, 2 RWs after one failure.

### Sensors & estimation
- **Perfect state.** Observation = current attitude quaternion `(q0,q1,q2,q3)` + body rates `(ωx,ωy,ωz)` + RW speeds `(rwx,rwy,rwz)`, plus (after the delay-robustness change) the **last control torque command** appended to the state vector.
- No noise/bias numbers on the state. No estimator (no EKF/UKF). Sensor uncertainty is not modelled other than by delay injection.
- State uncertainty handled by **random delay injection in the control loop: delays sampled uniformly in [0.5, 1] s**, plus the last-torque-in-state trick.

### Actuators
- **3 reaction wheels**. RW inertia `1.82e-5 kg·m²`; **max RW torque 0.004 N·m**; **RW saturation speed 7000 rpm (hard constraint)**.
- Command space: 3-D torque vector; **limited to [−2, +2] mN·m = 50% of the maximum applicable torque**, chosen to reduce energy use and early RW saturation.
- Allocation/desaturation: not stated. No MTQ for desaturation.
- When one RW unavailable: the failed wheel outputs **constant zero torque along its predefined axis regardless of the agent's control signal** (total loss of response); control continues on the remaining two axes.

### Fault / underactuation model
- **Complete actuator failure** ("complete lack of response to the input signals"), injected by forcing zero torque on the failed axis.
- Cases: failure on **x, y, or z** (3 cases) × 3 alignment objectives (align satellite x, y or z axis to target) = **9 underactuated controllers + 1 nominal controller = 10 total**.
- Training vs test: the failure is **fixed per specialised agent** (each agent is trained for one failure+alignment combination); the paper states the failure "is simulated randomly along with one of the axes" at the set level (axis chosen per agent), not randomly per episode within one agent.
- **Is the policy told the fault?** Effectively **yes, implicitly** — each policy is specialised for one failure axis, so fault identity is baked into the policy selection (a supervisory switch is implied). The policy does *not* observe an explicit fault flag, and the authors state the agents "could reach the target **without prior knowledge of satellite parameters or working condition of the actuators**".

### RL setup
- Algorithm: **custom policy-gradient algorithm based on PPO**. Library: **PyTorch**.
- Network: **feed-forward, 2 hidden layers × 64 neurons** (actor–critic training; actor used deterministically at test time).
- Hyperparameters: **γ = 0.99; KL target = 0.035; 40 epochs; lr = 0.0003; batch size = 150; minibatch = 32; clip ε = 0.2**.
- Parallel envs: **not stated** (no vectorisation described).
- Training budget: **40 training epochs**, each epoch = **15 000 env steps**; episode length **500 steps (nominal)** / **800 steps (underactuated)**. **10 agents trained with different seeds** per final controller, best selected by highest reward over the 40 epochs.
- Wall-clock: **≈ 26 hours to train a batch of ten controllers**.
- Hardware: **AMD Ryzen Threadripper 1920X CPU** (no GPU mentioned).

### Simulation workflow
- Vectorisation: not stated. Domain randomisation: random starting orientation at every env reset; random control-loop delays [0.5, 1] s; "injected random noise" stated in the conclusion.
- Curriculum/staged: **yes, light** — initial pointing angle θ sampled in **[30°, 180°]**, with sampling **biased toward smaller angles during the first episodes**.
- Reward (dense, bounded [0, 0.5], non-episodic setting):
  - **−1** if any |ω| > 0.1 rad/s;
  - **+1** if angular distance θ < threshold (pointing accuracy achieved), per step;
  - **0.5·(1 − ((θ − thrs)/π)^0.6) − p** otherwise, where **p is a penalty proportional to the sum of applied torques** (energy-efficiency term).
- Termination: horizon reached **or |ω| > 0.1 rad/s** ("in practice would imply the failure of the attitude determination system").

### Evaluation protocol
- In-simulation evaluation: **10 000 episodes per controller** (nominal and each of the 9 underactuated); performance evaluated over **3000 steps**; test episodes of **1600 steps = 800 s**.
- Test ICs deliberately harder: starting angles drawn from **[144°, 180°]** about any rotation axis.
- Metrics: convergence time to target, steady-state pointing accuracy; **threshold 0.01 rad = 0.57°** (0.05 rad for the harder underactuated combinations).
- **Statistical treatment: mean performance per step (blue line) + standard deviation (blue band) + worst-case envelope per step across all episodes (red band)** — an explicitly risk-averse presentation motivated by "the space industry is particularly risk adverse" and the impossibility of proving NN convergence/stability.
- Baselines: **none** (no classical controller comparison).

### Results (numbers)
- Mean cumulative reward: best **950.77** (x-failed / align-x), worst **891.28** (z-failed / align-y); reported reward variances 17.88 and 3.67 respectively `[text calls 17.88 the "smallest" variance while 3.67 is numerically smaller — internal inconsistency in the paper]`.
- Table 2 (10 000 simulated episodes) — accuracy / convergence time / horizon:
  - x-fail align-x: **0.01 rad / 72.95 s / 500 s**; x-fail align-y: 0.05 / 1367.84 / 800; x-fail align-z: 0.05 / 987.06 / 800
  - y-fail align-x: 0.05 / 1218.91 / 800; y-fail align-y: **0.01 / 75.37 / 500**; y-fail align-z: 0.05 / 1185.04 / 800
  - z-fail align-x: 0.05 / 1463.03 / 800; z-fail align-y: 0.05 / 1510.54 / 800; z-fail align-z: **0.01 / 142.71 / 500**
  - → accuracy is ~5× better (0.01 vs 0.05 rad) when the aligned axis *is* the failed axis; convergence differs by ~20× across inertia axes.
- Nominal case: both mean and worst-case trajectories converge to the 0.01 rad threshold **in less than 100 s** (statistics over 10 000 runs).

### ONBOARD / HIL DETAILS
- **Hardware platform:** ArgoMoon **On Board Computer (OBC)** — the real flight ground-model OBC — plus an **ADCS** (implements attitude commands, generates telemetries) and a **Real Dynamic Processor (RDP)** which "simulates the satellite's dynamics in space with a very high degree of accuracy".
- MCU model, clock speed, RAM, flash: **not stated**. **Inference latency in ms: not stated.** **Network memory footprint: not stated.** **Quantisation/pruning/compilation toolchain: not stated** — but the networks and control scheme were **"ported to the C language and integrated in the satellite's real-time operating system"** (RTOS).
- Bus/interfaces: **not stated** (no I2C/SPI/CAN/UART details).
- Real-time loop rate: the same **2 Hz** loop rate as training (0.5 s per command), with the loop closed in real time through OBC ↔ ADCS ↔ RDP.
- **HIL architecture — what is real vs simulated:** REAL = OBC (runs the policy), ADCS (command implementation + telemetry). SIMULATED = satellite dynamics on the **RDP**. The policy network receives state from the ADCS and outputs actions, which the RDP uses to propagate attitude, returning the new state — "closing a full real-time step in a continuous loop, which is either stopped by reaching the target precision or by meeting the exit conditions".
- Test procedure: an experiment is started by supplying a list of values — starting and target position, episode time-limit, exit conditions, and working mode (nominal or failure on one of the three axes). Then "tens of experiments" were run on the HiL testbench across all control policies.
- Pass criteria: reaching the target precision (0.01 rad class threshold) or meeting the exit conditions.
- Outcome: offline-trained networks, thanks to the injected random delays, "were able to generalise well and manage to lead the attitude trajectory towards the target regions"; trajectories for a nominal and an x-failure maneuver are shown with quaternion, body rates, RW speeds and commanded torques.

### Sim-to-real techniques
- Domain randomisation: random initial attitude; **random delays sampled in [0.5, 1] s** injected into the training control loop (the key enabler, explicitly credited for HIL generalisation); last torque command appended to the state (delay compensation); "injected random noise" into the environment (conclusion; no magnitudes given).
- Latency modelling: yes — the actuation/telemetry delay is modelled as the training Δt and by explicit delay randomisation.
- Actuator modelling: RW inertia, 50% torque cap, 7000 rpm hard saturation. Torque command held 0.5 s.
- Robustness tests: the *same* deployed C-code policies were run on real OBC/ADCS hardware with the RDP in the loop; adaptability to different inertia was observed ("great adaptive abilities … on the target hardware").

### Key quantitative results
- 10 controllers: 1 nominal + 9 underactuated; **0.01 rad (0.57°) pointing accuracy** on the aligned-axis cases, 0.05 rad otherwise; convergence **72.95–1510.54 s** depending on failure/aligned axis; nominal converges to threshold **< 100 s** worst case over 10 000 episodes; ~26 h training per batch of 10; 2 Hz control; ±2 mN·m (50% of 4 mN·m max); 7000 rpm.

### Directly reusable for the 24U thesis / ESP32-S3 HIL
The **tiny 2×64 MLP at 2 Hz** is a proven-feasible footprint for an ESP32-S3-class MCU, and the **C-port + RTOS integration** plus **delay randomisation [0.5, 1] s as the sim-to-real mechanism** are directly transferable — but note the architecture *specialises* a policy per fault axis (fault identity is effectively known via policy selection), which contradicts the thesis requirement that the deployed policy never see the true fault variable.

---

## C2. Hierarchical Deep Reinforcement Learning for cubesat guidance and control

Tammam & Aouf (City, University of London). *Control Engineering Practice* **156** (2025) 106213. DOI 10.1016/j.conengprac.2024.106213. Chaser: generic 1U CubeSat in LEO.

### Simulator / environment
- **Python** environment created with **OpenAI's Gym API**. A custom simulation (no Gazebo/Basilisk/Simulink for training); the HIL platform is custom-built hardware.
- Timestep / integrator: "each training episode lasting a maximum of **2000 timesteps**, where each timestep lasts **0.1 s**, and the spacecraft dynamics are propagated every **0.01 s**". Integrator type not named (fixed-step 0.01 s substeps).
- **Control frequency: 10 Hz** (0.1 s).
- Real-time simulator: at HIL, the **central PC** closes the rendezvous loop at 0.1 s (10 Hz) using a Kinova Gen3 arm.

### Dynamics fidelity
- **Full 6-DOF across two coupled problems:** (a) attitude — quaternion kinematics + rigid-body dynamics with 3 RWs (`ω̇ = I⁻¹(Td − L̇rw − ω×(Iω + Lrw))`); (b) relative orbital motion — **Clohessy–Wiltshire (CW) equations** in the Hill frame, LTI form `ẋ = Ax + Bu`.
- Disturbances: **four types considered** — gravity gradient (`Tgrav = (3μ/R³) ue × I ue`), aerodynamic drag (`Tareo = ½ρV²Cd A (uv × rcp)`), solar radiation pressure (discussed, considered small at LEO), and **magnetic field disturbance** (`B = (B0/R³)√(1+sin²γ)`, `Tmag = D·B` with residual dipole D).
- Training environment is **disturbance-free**; the testing environment adds disturbance forces + actuator noise.
- Magnetic field: **yes, as a disturbance torque only** — there are no magnetorquers.
- Underactuated cases: **not stated** (no RW failure modelling).

### Sensors & estimation
- Observation space = attitude part (**angular rate ω = [ωx,ωy,ωz]** and **error quaternion qe = [qe,w,qe,x,qe,y,qe,z]**) + rendezvous part (**relative position r = [rx,ry,rz]** and **velocity v = [vx,vy,vz]**); combined for the centralised agent, separate for the decentralised agents.
- No estimator and no noise/bias numbers in training. The test environment introduces "actuator noise" and disturbances, magnitudes **not stated**. In HIL, IMU noise is real (see below) but not quantified.

### Actuators
- **3 reaction wheels**, one on each of three perpendicular faces of the mock CubeSat, 3-axis control. Wheel mass **53 g each**, outer diameter **50 mm**, max height **7 mm**, stainless steel (`8e3 kg/m³` as printed), in-house disc design with raised rim.
- Wheel inertia `I_disk = 3.87e-6`, `I_ring = 6.30e-4`, **`I_total = 6.34e-4 kg·m²`** (`[paper prints "6.34 kg/m2" — typo]`). Max speed **7000 rpm** → **max angular momentum L_rw,max = 0.077 kg·m²·s⁻¹**. Estimated **minimum 3.896 s to rotate the CubeSat 90°**.
- Command limits: **force ≤ 0.1 N, torque ≤ 0.001 N·m**. Motors: **3 Faulhaber brushless DC motors with integrated speed controllers**, driven directly with **PWM** (no external speed controllers).
- Allocation path (HIL): controller torque → **Δω_rw = −T_c·Δt / I_rw** → target wheel speed → **simple PD controller tracks wheel angular velocity error** via PWM; Hall sensors measure the wheel's current angular velocity.
- No MTQ; no desaturation logic. When one wheel is unavailable: not stated.

### Fault / underactuation model
- **not stated** — no RW failure, degradation or underactuation is modelled or injected in either training or test.

### RL setup
- Algorithms: **D-TD3** (decentralised: two independent TD3 agents — D-TD3-R for rendezvous, D-TD3-A for attitude), **C-TD3** (one centralised TD3 agent fusing both reward functions and observation spaces), and **H-DDPG** (HDRL: two DDPG-based **Hierarchical Actor-Critic (HAC)** agents, H-DDPG-A and H-DDPG-R, with **UVFA** goal-conditioned Q-functions and **Hindsight Experience Replay**).
- Libraries: **TD3 implemented in TensorFlow**; **HAC/DDPG implemented in PyTorch** (HAC code adapted from Levy, Konidaris et al., 2017).
- Architecture: "**three fully connected hidden layers employing ReLU**" activation; Adam optimiser. (FC node counts in Tables 2–3.)
- Hyperparameters:
  - D-TD3: lr **0.001**, batch size **10⁶**, minibatch **512**, Adam, **γ = 0.995**, FC1 **64**, FC2 **128**
  - C-TD3: lr **0.001**, batch size **10⁶**, minibatch **512**, Adam, **γ = 0.995**, FC1 **512**, FC2 **1024**
  - H-DDPG: lr **0.0001**, batch size **10⁷**, minibatch **1024**, Adam, **γ = 0.95**, FC1 **64**, FC2 **64**
  - `[batch sizes are printed as "106"/"107" — almost certainly 10⁶/10⁷ rendered as superscripts]`
- Hyperparameters "hand selected through an iterative process", starting from RLzoo-style benchmark values, then fine-tuned; **layer node counts were reduced incrementally until performance degraded**, to keep networks "computationally efficient".
- Parallel envs: **not stated**. Total training steps / episodes: **not stated** — "training ceases when the total episode rewards plateau or the maximum achievable episode reward is reached". Wall-clock: **not stated**. Training hardware: **not stated**.

### Simulation workflow
- Vectorisation: not stated. Domain randomisation: minimal — fixed test ICs used to compare frameworks; testing env adds disturbances + actuator noise.
- Staged/scheduled training: **two-stage** — train in a **disturbance-free** environment, then evaluate in a **disturbed** environment with actuator noise.
- Reward: two-part (rendezvous + attitude), initially **binary ±0.1** (rendezvous: +0.1 if "distance to target decreased" — Eq. 24 as printed; attitude: +0.1 if `q̇e,w ≥ 0`), switching to continuous: rendezvous `rr = exp(distance/45)` below **25 m**, attitude `ra = q²e,w − q²e,x − q²e,y − q²e,z` below **10°** angular error. **Bonus +4** when within **10 m** or angular error **< 5°**. **Terminal −100** and episode stop if angular rate exceeds **90°/s** or relative distance exceeds **250 m**.
- Termination: max 2000 timesteps; early stop on the two terminal conditions above.

### Evaluation protocol
- Goals/performance criteria: bring angular rate and angular error **below 1°/s and 5°** respectively, and come within **5 m** of the target.
- Test ICs (identical for all frameworks to allow comparison): relative position error **[10 m, 45 m, 100 m]** (initialised ~100 m from the target during training) and angular error **[5°, 30°, 10°]**; training ICs: angular error **10°–90°**, zero angular velocity, small relative velocity.
- Metrics: time to correct attitude error, time/path to reach ~5 m, final errors per axis, commanded force/torque magnitude and chattering.
- Baselines: **classical PD controller**, simulated under the same conditions, and tested on the same HIL platform.
- Statistical treatment: **not stated** (single representative runs/plots; no confidence intervals or episode counts).

### Results (numbers)
- **D-TD3**: attitude error corrected in **< 5 s** (D-TD3-A); guidance converges to **~5 m** with a shorter path.
- **C-TD3**: takes **> 100 s** to correct attitude — used as evidence that one centralised agent solving both problems is inefficient; guidance performance comparable to D-TD3 (~5 m).
- **H-DDPG**: meets both tolerances; commands **substantially less control force and much less chattering** than D-TD3; slightly less smooth attitude correction but comparable timeframe.
- **PD baseline (simulation)**: matched H-DDPG-R on relative position (lower final error) but with significant force chattering; **failed to stabilise attitude** — satellite tumbled on yaw with roll/pitch oscillating between **0° and 50°** (attributed to external disturbances, actuator nonlinearities and RW torque constraints).

### ONBOARD / HIL DETAILS
- This is **the closest precedent to an ESP32-S3 HIL target in this batch.** The mock CubeSat's flight-software component is explicitly **"An ESP32 Microcontroller … [which] will contain the HDRL model, gather sensor data from the IMU, and transmit that data to the motors in the case of attitude testing or to a central computer for the case of rendezvous testing. It is a low-cost low-power microcontroller with both Wi-Fi and Bluetooth capabilities."** (The board cited is the **ESP32-DevKitC V2**.)
- **MCU model: ESP32 (DevKitC V2).** Clock speed, RAM, flash: **not stated**. **Inference latency in ms: not stated.** **Memory footprint: not stated.** **Quantisation/pruning/compilation toolchain: not stated** (plain trained weights used for inference — "the saved weights and biases from the fully trained models are used during inference in the testing phase").
- Real-time loop rate: **10 Hz (0.1 s)** — every 0.1 s the central PC gathers the arm end-effector position/velocity and runs the H-DDPG-R agent; the attitude policy runs on the ESP32 inside the mock CubeSat.
- **HIL architecture — real vs simulated (three independent sub-platforms):**
  1. **Mock 1U CubeSat** — real hardware, 3D-printed two-part split housing, bound to **10 × 10 × 10 cm** and **≤ 1 kg**; powered by a **3S 11.1 V LiPo battery**; sensing by a **6-DoF MPU-6050 IMU** (3-axis gyroscope + 3-axis accelerometer); policy on the **ESP32**; actuation by 3 in-house RWs driven by Faulhaber BLDC motors, commanded over **PWM**.
  2. **Attitude dynamics testing platform** — a **hemispherical air bearing**: 3D-printed two-piece stator (bottom half Onyx FFF printer, top half Formlabs Fuse 1 SLS), purchased **acrylic hemisphere**, compressed air at up to **6 bar** through a circular pattern of openings in a channel around the stator face (following Jovanovic et al. 2019), with pneumatic fittings/hosing/regulator. Provides frictionless rotation so the *real* CubeSat attitude dynamics (real RWs, real IMU) close the loop. Small-to-medium slew manoeuvres only; upgradable to a two-part sphere.
  3. **Rendezvous mission simulator** — a **Kinova Gen3 6-DoF robotic arm** acting as the "thruster": a central PC polls end-effector state every 0.1 s, runs H-DDPG-R, converts the force command to **joint torques via the robot Jacobian**, and actuates the arm; a 3D-printed attachment couples the mock CubeSat + air-bearing platform to the arm's end effector for simultaneous guidance + attitude testing.
  - So: **real = CubeSat structure, RWs + motors, IMU, ESP32 policy, air bearing, robot arm**. **Simulated = essentially nothing in the attitude loop** (the air bearing + real RWs make the attitude loop physical); the rendezvous dynamics are emulated by the arm.
- Test procedure & pass criteria: run the controllers on the hardware platform against the same objectives used in simulation (angular rate < 1°/s, angular error < 5°, within 5 m); compare against the PD controller on the same rig.
- **HIL results:**
  - **D-TD3**: significant angular errors at the start, oscillation and overshoot; final angular errors **< 5° on pitch and roll, ≈ 7.5° on yaw**; guidance reached **within 5 m in < 120 s**; persistent force chattering (also seen in simulation). Disturbances became more pronounced below **20 m** relative distance.
  - **H-DDPG**: angular errors **< 5° within 25 s** with lower final error on all axes; **5 m in < 90 s**; less fluctuation and lower commanded forces → judged overall superior.
  - **PD controller on hardware**: like in simulation, **failed to correct the CubeSat's attitude**, and performed comparably to HDRL on guidance.
  - Dominant noise source: **vibrations from the reaction-wheel motors and movements of the robotic arm's end effector caused the IMU to output noisy data** on the attitude platform.

### Sim-to-real techniques
- Domain randomisation ranges: **not stated** (no randomisation tables). Robustness is obtained instead by **hardware-in-the-loop itself** plus the train-disturbance-free / test-with-disturbances split.
- Noise injection: disturbance forces + actuator noise in the testing environment (magnitudes not stated); real IMU noise at HIL.
- Latency modelling: **not stated** (0.1 s loop period used consistently in simulation and HIL).
- Actuator modelling: RW design parameters, max speed, torque/force saturation, and the torque→Δω→PWM wheel-speed command chain with a PD inner loop; the 3.896 s minimum 90° slew as a sanity bound.
- Robustness tests: the same policies evaluated in a disturbed simulation and then in a real 3-RW air-bearing CubeSat testbed with a robotic-arm rendezvous emulator.

### Key quantitative results
- 1U chaser: **Ixx=Iyy=Izz=0.001** (`[unit printed as "kgm−2" — typo for kg·m²]`), **mass 0.5 kg**; force limit **0.1 N**, torque limit **0.001 N·m**; RW **53 g, 50 mm OD, 7000 rpm, L_max 0.077 kg·m²/s, I_total 6.34e-4 kg·m², min 3.896 s per 90°**; control **10 Hz** (0.1 s), dynamics substep **0.01 s**, episode **2000 steps = 200 s**; HIL: **5 m / <90 s (H-DDPG) vs <120 s (D-TD3); <5° in 25 s; yaw 7.5° (D-TD3); air bearing 6 bar; 1 kg / 10 cm CubeSat**; PD fails attitude in both simulation and HIL.

### Directly reusable for the 24U thesis / ESP32-S3 HIL
The strongest single precedent: an **ESP32 hosts the deployed policy inside a real 3-RW air-bearing CubeSat** with a 10 Hz loop and noisy IMU, and it quantifies that a classical **PD baseline fails attitude control on the same rig** — but it reports **no latency, no memory footprint, no quantisation** and injects **no faults**, so the thesis must supply those missing pieces itself.

---

## C3. Onboard Deep Reinforcement Learning: Deployment and Testing for CubeSat Attitude Control

Zahedi, Roshanian, Mirshams, Georgiev (K. N. Toosi University + TU Sofia). *Eng. Proc.* **2026, 121, 26**; BulTrans-2025, Sozopol. DOI 10.3390/engproc2025121026. Single-axis CubeSat testbed.

### Simulator / environment
- **Custom MATLAB (R2021b) scripts** for the RL environment and controllers; the plant is the measured single-axis test-stand dynamics `Jrw·θ̈rw = JCS·θ̈CS + Md`. No Gazebo/Basilisk/Simulink. The HIL "simulator" is the physical air-bearing stand plus a disturbance stand.
- Dynamics equation (1): `Jrw θ̈rw = Jcs θ̈cs + Md`. Integrator type and fixed timestep: **not stated**. Control frequency: **not stated** in Hz (the loop runs continuously; gyro sampled at 100 Hz).
- Real-time simulator: no software real-time simulator — the plant is physical hardware.

### Dynamics fidelity
- **1 DOF only** — rotation about a single (vertical) axis on the air-bearing stand. **Not 6-DOF**, no orbit, no translational dynamics, no gyroscopic cross-coupling.
- Disturbances: **yes** — four masses suspended symmetrically around the disk generate a torque as the disk rotates ("destabilise the system … leading to undesired angular deviations"); the **disturbance moment Md has no fixed/known value and is assigned randomly during simulations** to cover unpredictable external torques. Actual experimental disturbances were found **larger than anticipated** in code.
- Magnetic field / MTQ: not modelled, not used.
- Underactuated cases: **not stated** (single wheel, single axis — inherently 1-actuator/1-DOF).

### Sensors & estimation
- **Real gyroscope sensor**, communicating with the microcontroller over **UART**, capturing orientation at **100 measurements per second (100 Hz)**. Inputs to the network: **angular velocity and orientation (attitude)** of the CubeSat — only two state variables.
- No estimator (no Kalman filter); direct gyro readings. Sensor noise magnitudes: **not stated** (noise appears implicitly in hardware results).

### Actuators
- **1 reaction wheel** on a **DC motor** (aluminium inner core + brass outer rim, higher-density brass rim used to increase moment of inertia); driven through an **H-bridge motor driver** which "relays control signals from the microcontroller to the motor … provides voltage regulation and safeguards the motor from electrical faults".
- **J_rw = 7.597e-5 kg·m²**; total system inertia (CubeSat + test disk) **J_surface = 0.034055 kg·m²** (computed from `Jrod = 3.920625e-4`, `Jweight = 6.1578e-3`, `Jplane = 6.3495e-3`, `Jcube = 1.506314e-3` via the parallel-axis theorem). Masses (in grams as tabulated): bar/weight-hanger 20, hanging weight 311, total disk without CubeSat **1884.4**, CubeSat **617.3**, reaction wheel **68.2**; CubeSat unit **12 × 12 × 12 cm, 0.67 kg**.
- Controller output is a **reaction-wheel velocity command issued as a PWM signal** to the DC motor. Torque/torque-rate limits: **not stated**. No MTQ, no desaturation.
- **Motor dead zone is a hard physical constraint**: the motor "prevents movement below a certain PWM threshold (e.g., **30**)".
- When the wheel is unavailable: not stated.

### Fault / underactuation model
- **not stated** — no fault or degradation is injected; disturbances are the only perturbation. (Future work lists 3-DOF CubeSats with three reaction wheels.)

### RL setup
- Algorithm: **Double Deep Q-Network (DDQN)** — online network selects actions, target network evaluates them, to reduce overestimation bias. Discrete action space. Chosen over DDPG/PPO/HDRL partly because it "requires less computation" and uses experience replay.
- Library: **MATLAB (R2021b)** — network built with MATLAB Deep Learning/RL tooling. Reward and network both defined in MATLAB scripts.
- Architecture: **feature input layer** matching the input dimension (angular velocity + orientation), followed by **several fully connected layers with ReLU activations**, and a final fully connected layer producing outputs "compatible with the defined action space". Exact layer sizes/parameter count: **not stated**. The network is described as "lightweight … well-suited for potential deployment in embedded environments with limited computational resources" — but see the deployment failure below.
- Key hyperparameters: **epsilon 0.9** (initial), **epsilon decay 0.005**, **min epsilon 0.01**; **L2-norm** regularisation applied "to prevent over-gradient issues"; optimiser **ADAM**; **learning rate 0.01**; **mini-batch size 64**; **target smooth factor 0.001**; **discount factor 0.95**; **experience buffer length 10 000** while the replay memory is described as **50 000 units** `[two different values printed in the same section — internal inconsistency]`.
- Parallel envs: **not stated**. Total training steps/episodes, wall-clock, training hardware: **not stated**.
- Reward (4): **`Reward = 10 − |eθ|` if `|eθ| < 3°`, else `Reward = 0`**, where `eθ = (θdes − θ)CS` — i.e. a sparse threshold-gated reward after testing multiple reward function shapes.
- Termination: **not stated**; desired angles are generated randomly in each episode.

### Simulation workflow
- Vectorisation: not stated. Domain randomisation: **random disturbance moment Md assigned randomly during simulations**; **random desired angles generated each episode** to prepare the system for "any command".
- Curriculum/staged: not stated.
- Baselines: **PID** controller, tuned with the **Cohen–Coon** method (chosen over **Ziegler–Nichols** because of the sensitivity of the system — excessive oscillations could cause instability or physical damage; Cohen–Coon uses a first-order-plus-time-delay approximation of the open-loop step response).

### Evaluation protocol
- Metrics: **response time, accuracy, resilience to disturbances**; overshoot; steady-state oscillation; settling time.
- ICs/maneuvers: simulation tests a **110° rotation** with disturbances for both DDQN and PID; hardware tests a **140° rotation (PID)** and a **150° rotation (DDQN)**; desired angles randomised across episodes during training.
- Baselines: PID tuned in simulation with the *same optimised coefficients applied directly to the hardware controller*.
- Statistical treatment: **not stated** (single representative responses/plots).

### Results (numbers)
- **Simulation:** DDQN successfully rotated the system **110°** under disturbances and stabilised in **under 2 s**; DDQN controlled the system "in a shorter time with less overshoot" than PID. Caveat stated by the authors: these plots will differ from hardware because of physical limitations (battery voltage drop, DC motors not reaching the desired angular velocity).
- **Hardware (PID, 140°):** significant initial overshoot, then convergence, but **very minor residual oscillations** at the target → failed to achieve perfect stability.
- **Hardware (DDQN, 150°):** **slower response dynamics than PID but precise attitude control with no overshoot**; superior steady-state accuracy; complete elimination of overshoot; the high-frequency terminal oscillations of the PID are absent; **comparable settling times, both reaching the target at approximately t = 6 s**.
- **Sim-to-hardware gap (explicitly quantified):** DDQN stabilised in **< 2 s in simulation vs 6 s on hardware — a 3× degradation**. Root causes given: (1) **motor dead zone** (no movement below PWM threshold ≈ **30**), which simulation did not capture; (2) **battery voltage drops** preventing the motor from reaching desired speeds; (3) **test platform disturbances larger than modelled**.

### ONBOARD / HIL DETAILS
- **Hardware platform:** a custom CubeSat (**12 × 12 × 12 cm, 0.67 kg**) with three sections — battery, DC motor + reaction wheel, and electronics. Power: **3-cell lithium-ion pack, 4 V per cell, 12 V total**, with a **Battery Management System (BMS)** for balanced charge/discharge and protection against over/under-charge and short circuits. Sensing: **gyro, UART, 100 Hz**. Comms: **wireless NRF module over SPI** for bidirectional CubeSat↔ground-station telemetry and commands. Motor drive: **H-bridge**. MCU model: **"microcontroller" only — model, clock speed, RAM, flash: not stated**.
- **THE CENTRAL ONBOARD FINDING:** "**direct implementation of the trained neural network on the microcontroller is not feasible due to its size**". Consequently the DDQN ran **ground-station-in-the-loop**: the satellite transmits its current state to the ground station, the ground station processes it through the neural network and sends the resulting action back to the microcontroller, which executes it on the motor. (The PID, by contrast, ran on the microcontroller with simulation-tuned gains.)
- **Inference latency in ms: not stated** (the round-trip ground-station link latency is not quantified, though it is visible as slower response dynamics). **Memory footprint: not stated.** **Quantisation/pruning/compilation toolchain: none used** — this is precisely the gap that forced the off-board fallback.
- Bus/interfaces: **UART** (gyro), **SPI** (NRF wireless module); motor via PWM through an H-bridge. No I2C/CAN stated.
- Real-time loop rate: not stated numerically; the gyro provides 100 Hz measurements and the closed loop "runs continuously".
- **HIL architecture — real vs simulated:** essentially **hardware-in-the-loop in the physical-plant sense**: REAL = CubeSat structure, battery + BMS, DC motor + RW, H-bridge, microcontroller, gyro, wireless link, and the **air-bearing + disturbance stand** (a disk holding the CubeSat with four mechanical clamps for centre-of-mass adjustment over a hemispherical structure on an air-bearing platform; pumping air eliminates friction for near-frictionless single-axis rotation). SIMULATED = the satellite dynamics are *not* simulated during hardware runs; the only simulation is offline for training/validation. The disturbance generator is **four masses suspended symmetrically** around the disk producing real gravity-induced disturbance torque.
- Test procedure & pass criteria: receive a desired angle from the ground station, compare with gyro attitude to form the error, run the controller (DDQN or PID), output an RW velocity command as PWM to the DC motor, keep the loop closed; ground station plots angular data in real time and sends desired attitude targets. Pass criteria are qualitative: reach and hold the target angle without overshoot/oscillation and compare against PID.
- Monitoring/telemetry: "The ground station receives attitude data from the CubeSat and plots the angular values in real time."

### Sim-to-real techniques
- Domain randomisation ranges: **random disturbance moment Md** during simulation (range not stated); **random desired angles per episode** for generalisation to any command.
- Noise injection: **none added in simulation** (no sensor-noise model) — and this is implicated in the gap.
- Latency modelling: **none** — and the ground-station-in-the-loop architecture *adds* unmodelled latency in the DDQN hardware runs, visible as slower response.
- Actuator modelling: actuator limitations are acknowledged as *absent* from the model and named explicitly as causes of the gap: **motor dead zone (~PWM 30)**, **battery voltage sag**, non-achievable commanded angular velocities. No dead-zone or voltage model was implemented.
- Robustness tests: hardware runs with **real suspended-mass disturbance torques** under a **140°** (PID) and **150°** (DDQN) manoeuvre.

### Key quantitative results
- CubeSat **12 × 12 × 12 cm, 0.67 kg**; **Jsurface = 0.034055 kg·m²**, **Jrw = 7.597e-5 kg·m²**; gyro **100 Hz over UART**; **12 V** 3-cell Li-ion + BMS; **epsilon 0.9 → min 0.01 (decay 0.005); lr 0.01; mini-batch 64; γ = 0.95; target smoothing 0.001; buffer 10 000 / replay memory 50 000**; reward `10 − |eθ|` gated at **3°**; simulation **110°** maneuver, stabilised **< 2 s**; hardware PID **140°** with overshoot and residual oscillation; hardware DDQN **150°** no overshoot, both settling at **t ≈ 6 s**; **2 s → 6 s (3×) sim-to-hardware degradation**; **PWM dead-zone threshold ≈ 30**; **network could NOT fit on the microcontroller → ground-station-in-the-loop**.

### Directly reusable for the 24U thesis / ESP32-S3 HIL
The most valuable **cautionary** result in the batch: an un-quantised MATLAB-trained network was **too large for the flight MCU**, forcing a ground-station-in-the-loop workaround, and the unmodelled **PWM dead zone (~30), battery sag and under-estimated disturbance** cost a **3× slowdown (2 s → 6 s)** — directly motivating an int8-quantised, footprint-measured ESP32-S3 deployment and a dead-zone-aware actuator model inside the thesis HIL.

---

## C4. Real-Time Testing of Satellite Attitude Control with a Reaction Wheel Hardware-in-the-Loop Platform

Sakal, Nehma, Riano-Rios, Tiwari (Florida Institute of Technology). AAS 25-778 (preprint). Adaptive Lyapunov + integral concurrent learning (ICL) controller with RW health estimation — **not an RL controller**; included here for its HIL architecture.

### Simulator / environment
- **MATLAB/Simulink** IEEE "Satellite Simulator" (node `SatSimNode`) running on a **Linux PC** (host), simulating **satellite dynamics, environment, actuator models and sensor models**. Communication with the embedded computer over **ROS2 middleware** on a local network.
- **Real-time simulator: yes** — the Simulink model runs in real time as the plant, exchanging ROS2 topics with the embedded computer.
- Integrator: **forward-Euler** used for integration of the adaptation law and for the velocity-command generation (explicitly named, "proved to be sufficient"). Base timestep value: **not stated**.
- Control loop: **100 ms loop limit (10 Hz)**; measured controller execution time **3.86 ms** (≈26× margin). RW actuator-state feedback published at **20 Hz**.

### Dynamics fidelity
- **6-DOF rigid-body attitude** with N reaction wheels: `J ω̇ = −ω×(Jω + JRW GΩ) + GΦu`, MRP kinematics `σ̇ = ¼[(1−σᵀσ)I₃ + 2σ× + 2σσᵀ]ω`. Relative orbital dynamics: **not modelled** (attitude only; configuration matrix G is a 4-wheel pyramid).
- Disturbances: attitude perturbations are **mentioned as neglected** in the controller development, causing disparity between model and hardware ("some parts of the simulation model, such as attitude perturbations were neglected"). No disturbance torque model values given.
- Magnetic field: **not modelled**; no magnetorquers.
- Underactuated cases: **partially** — degraded/faulty wheels are injected (see below) but the RWA remains a 4-wheel pyramid; arrays of **4 and 6 RWs** with a varying number of degraded RWs and varying degradation levels were studied in the previous (simulation) work.
- Sensor models: **sun sensors, magnetometers and gyroscopes modelled by adding noise at realistic sampling rates — gyroscope 10 Hz, magnetometer 2 Hz, sun sensors 2 Hz**.
- Attitude determination: **Extended Kalman Filter (EKF) based on the multiplicative quaternion**, estimating inertial angular velocity ω and quaternion → MRPs σ. The EKF runs **on the satellite simulator (host)**, not on the embedded computer — moving it onboard is listed as future work.
- **Two satellite configurations are reported side by side (Table 1, "Simulation vs HIL")**, which is an unusually explicit statement of the model-reality parameter gap:

| Parameter | Simulation | HIL | Units |
|---|---|---|---|
| m | 65 | 20 | kg |
| J | diag{0.44, 0.70, 0.70} | diag{0.30, 0.42, 0.42} | kg·m² |
| G | 4-wheel pyramid (0.5774 entries) | same pyramid | – |
| Max RW torque | 50e-3 | 20e-3 | N·m |
| Max Ω | 3.66e2 | 1.04e3 | rad/s |

### Actuators
- **4 Maxon EC 60 flat brushless DC motors** emulating RWs, each driven by a **Maxon EPOS4 Compact 50/5 CAN digital position controller**, communicating over **USB/CAN bus using the CANopen protocol**.
- The motor drivers offer two modes: **torque (current) command** and **angular velocity command**.
- Allocation: control torques recovered via the **Moore–Penrose pseudo-inverse of the health-weighted configuration matrix**, `u = (G Φ̂)† u_d`, where `Φ = diag{ϕ₁…ϕ_N}` is the **uncertain RW health matrix** and `Φ̂` comes from integrating the adaptation law.
- Torque → current conversion: `I_cmd = Kt · τ_cmd` (Kt from the motor datasheet). Torque → velocity conversion: `Ω̇_cmd = τ_cmd / J_RW` integrated with forward-Euler, plus **torque and velocity saturation** to the motor specs.
- Wheel state feedback: **built-in current sensor** reports actual current; **Hall-effect sensor** measures angular velocity.
- Desaturation: not stated (4-wheel RWA, no MTQ described).
- What happens when one is unavailable: the controller estimates the health of each wheel online and re-allocates through the pseudo-inverse; physical failure induced as described below.

### Fault / underactuation model
- Faults are **artificially induced on real hardware**, two mechanisms:
  1. **Full failure** — "the power stage of the failing RW can be disconnected";
  2. **Partial failure / degradation** — "manipulating the amount of effort that is sent as command to the motor controller with respect to the effort output by the main attitude controller… normally a scaling factor applied to the required control effort".
- Fault modes in the HIL run: **degraded wheel factor 0 → 0.5** (i.e. a **50% loss** on RW#3) — the only change made to the previous simulation scenario, alongside a gain reduction.
- Injected during training vs test only: this controller **learns/estimates online at run time** (adaptive ICL), so "training" is not applicable; faults are injected at test time on hardware.
- **Is the policy told the fault?** **No.** The true health vector `θ = [ϕ₁…ϕ_N]` is unknown; the controller **estimates** `θ̂` from input-output data via the adaptation law (Eq. 5) and uses `Φ̂` in the pseudo-inverse. Convergence of the health estimate is guaranteed once a finite-excitation condition is met (measured by the scalar λ crossing a threshold).
- Known limitation: because the EoMs required an angular-acceleration profile consistent with measurement, **physically inducing RW failures was prevented in this configuration** — failures in the reported HIL test were therefore induced by command manipulation, not by physically degrading the wheel. The authors state that on a spherical air-bearing testbed no such artefact would be needed and **physically induced failures would become possible**.

### RL setup
- **Not applicable — the controller under test is not RL.** It is a Lyapunov-based adaptive controller with an **integral concurrent learning (ICL)** adaptive update law, guaranteeing exponential convergence of error states and RW health estimates. Gains (Table 2, Simulation → HIL): **K_ICL 10 → 1**; **K 5×10⁻¹ → 1×10⁻²**; **α 3×10⁻² → 3×10⁻²**; **β 5×10⁻³ → 5×10⁻³**; **γ 100·I₄ → 100·I₄**; **λ̄ 1×10⁻⁷ → 1×10⁻⁷**.

### Evaluation protocol
- Scenario (identical to the authors' previous work, used for comparability): the satellite **starts aligned with the ECI frame**, then **alternates between its initial orientation and nadir-pointing three times**; the **scenario lasts 4000 s**, switching orientation **every 12 minutes**, then **maintains nadir-pointing after 2000 s**.
- Metrics reported: attitude tracking performance (error MRP, body angular velocity), **RW health estimate `θ̂` vs true health**, the **verifiable excitation level λ vs its threshold (1e-7)**, RW angular-velocity measurements, and — unusually — **computer performance metrics: execution time per step, CPU load, memory usage**.
- Baseline/statistical treatment: **not stated** (no Monte Carlo; single 4000 s run; the earlier work provides the simulation comparison).

### Results (numbers)
- Attitude tracking and guidance commands were followed successfully throughout the run.
- **RW health estimation converged to the true value**; the **verifiable excitation level λ reached its threshold earlier than in purely simulated tests**; estimating accuracy was **better for the degraded RW#3 than for the non-degraded wheels**, with **overshoot on the RW#3 estimate** and a steady-state error attributed partly to **forward-Euler integration error** and partly to **neglected attitude perturbations** in the model.
- Because **K_ICL had to be reduced 10 → 1**, convergence was slower; the gradient term in Eq. (5) accelerated it as more manoeuvres were performed.
- **Computer performance (Table 3, Jetson Nano):** Execution time **avg 3.86 ms / max 6.62 ms / std 0.20 ms** against a **100 ms** loop budget; CPU usage **ControllerNode (CPU2) avg 14.7%, max 100%, std 4.4**; **RWNode (CPU3) avg 10.3%, max 100%, std 5.0**; **CPU0 avg 2.7%, max 6.90, std 0.9**; **CPU1 avg 0.3%, max 3.00, std 0.5**; **Memory (RAM %) — idle baseline avg 16.6% / max 16.7 / std 0.01, HIL avg 19.6% / max 19.8 / std 0.6** → **only ~3% additional RAM** is required to execute the control algorithms. Max 100% CPU load is expected at node initialisation.

### ONBOARD / HIL DETAILS
- **Hardware platform:** **NVIDIA Jetson Nano** embedded computer (with Wi-Fi adapter) as the onboard computer, executing **two ROS2 nodes**: `ControllerNode` in **Python (rclpy)** and `RwNode` in **C++ (rclcpp)**. Host: a **Linux PC** running the MATLAB/Simulink satellite simulator. A **dedicated power supply unit** powers the electronics.
- **Clock speed, RAM, flash of the Jetson Nano: not stated** (only the OS-level percentages above). **Inference latency in ms: not applicable/not an NN controller** — but the **per-step execution time 3.86 ± 0.20 ms** is exactly the real-time metric a thesis HIL chapter should report. **Network memory footprint: not applicable.** **Quantisation/pruning/compilation toolchain: not stated** — the controller and the EPOS command library are compiled C++/Python; no DNN toolchain involved. The EPOS command library used to drive the wheels is written in **C++**.
- Bus/interfaces: **USB** (Jetson Nano ↔ one digital motor controller, and EPOS ↔ PC), **CAN bus with CANopen protocol** (remaining motor drivers interconnected), **ROS2 topics over Wi-Fi / local network** for host ↔ embedded communication.
- Real-time loop rate: **10 Hz (100 ms budget)**; RW actuator state published at **20 Hz**; the two nodes were **pinned to separate CPU cores** (CPU2 and CPU3) for the CPU-load measurement.
- **HIL architecture — real vs simulated**, with an explicit test-mode matrix (the single most reusable artefact in this batch):

| Test mode | Host: Satellite Simulator | Host: RW model | Onboard: Controller | Onboard: RW model | Hardware: RWs | Hardware: Controller |
|---|---|---|---|---|---|---|
| MIL | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| SIL | ✗ | ✓ (as RW model on host) | ✓ | ✗ | ✗ | ✗ |
| HIL-a | ✓ | ✗ | ✓ | ✗ | ✓ | ✓ |
| HIL-b | ✓ | ✗ | ✗ | ✗ | ✓ | ✓ |
| HIL-c | ✗ | ✗ | ✓ | ✓(as RW model on host) | ✓ | ✓ |

  (Legend: ✓ active, ✗ not used. As printed: MIL — model only; SIL — embedded computer runs the controller against the simulated RW model; HIL-a — real RWs added but the main control loop still closed with simulated RWs; HIL-b — measured RW velocities/accelerations fed into the simulator EoMs, controller still on host; HIL-c — controller on the Jetson Nano closing the loop with physical RWs.)
- Staged integration procedure (the "how"): SIL first (verifies the embedded computer can run the control algorithm accurately/efficiently vs simulation) → then add the RWs with their CAN bus drivers and integrated sensors → then **HIL-a: test RW response** (torque commands sent in parallel to real RWs while the loop stays closed on simulated RWs; compare output torques and angular velocities; RW inertia/mass/torque constant taken from motor datasheets and put into the simulated RWs) → **HIL-b: physical RWs enter the main control loop** (feed real RW angular velocities and accelerations into the EoMs) → **HIL-c: embedded computer in the loop** (run the controller in parallel on the host and the Jetson Nano, compare; then replace the simulator's RW commands with the Jetson's commands). The modular architecture lets new actuators/sensors/computers be swapped in, and is stated to be scalable to air-bearing tests, integration and test campaigns, and end-to-end system tests.
- **Test procedure and the pitfalls (the paper's core contribution):**
  - Torque/current-command mode **failed**: the RWs have a **current deadband of ~300 mA** throughout which any commanded current produces no output; because commanded torques were small and decayed toward zero, most commands fell inside the deadband. Kick-starting and a sign-based deadband offset (`I_cmd = I_cmd + sign(I_cmd)·300`) both failed — the latter produced large jumps in RW angular velocity and poor tracking.
  - Solution: **convert torque commands to angular velocity commands** (`Ω̇_cmd = τ_cmd/J_RW` + forward-Euler + saturation), which the RWs track without the deadband problem; measured velocity then closely followed the simulated RW (small noise).
  - **EoM propagation** needed RW angular acceleration: (a) current→acceleration mapping failed (same deadband issue); (b) numerical differentiation + low-pass filtering introduced a **phase shift (delay) significant enough to make the system unstable**. Final fix: feed **calculated** velocities and accelerations into the EoMs instead of measured accelerations, and **exclude current measurements entirely** (only velocity measurements interface with the simulator). Justified because the control and adaptation laws only need estimated satellite states and RW angular velocities, and EoM propagation is only needed for the numerical simulation.
  - Consequence: physical RW failure injection was **not possible** in this configuration (it needs an acceleration profile consistent with measurement); the framework however remains applicable to physically induced failures on an air-bearing testbed.
  - Hall-effect sensor noise near zero speed: RWs were **spun up to an initial Ω = [100, −100, −100, 100] rad/s** to avoid the worst measurement noise; measurement noise was observed only at low-speed regions due to the digital motor controller's **internal low-pass filtering**, and had minimal impact on tracking and estimation.
  - **Sim-to-real torque gap:** reduced K_ICL by an order of magnitude (10 → 1) was **necessary to avoid demanding torque commands exceeding the RW limits**, which "initially caused the simulator and the ControllerNode on the Jetson Nano to stop once the ICL term was activated" — i.e. a torque limit that is feasible in simulation was not reproducible on hardware.

### Sim-to-real techniques
- Domain randomisation ranges: **not stated** (no DR in this work; it is an adaptive controller).
- Noise injection: **sensor models with noise at realistic sampling rates — gyro 10 Hz, magnetometer 2 Hz, sun sensors 2 Hz**; actuator-side real Hall-effect and current-sensor noise enters naturally.
- Latency modelling: **not explicitly modelled**, but latency/communication is named as one of the realistic conditions "difficult to replicate in simulation"; ROS2 middleware introduces real communication latency; numerical differentiation phase shift is identified as a destabilising delay; the **100 ms control-loop budget** frames the timing requirement.
- Actuator modelling: **RW inertia, mass and torque constant taken from datasheets** and used in the simulated RWs; **torque saturation and velocity saturation** applied; torque-command path passed through a **transfer function designed to mimic the motor driver + RW in closed-loop torque control**.
- Robustness tests: the full HIL-c configuration with **artificially induced 50% degradation on RW#3** over a **4000 s** mission-like scenario, with online health estimation validated against truth; plus explicit reporting of which real-time resource metrics stayed within budget.

### Key quantitative results
- Loop budget **100 ms (10 Hz)** vs measured **3.86 ± 0.20 ms** (max 6.62 ms) → **~26× real-time margin**; **RAM 16.6% → 19.6% (~3% for the control algorithms)**; ControllerNode CPU avg **14.7%**, RWNode avg **10.3%**; RW feedback **20 Hz**; sensor rates **gyro 10 Hz / magnetometer 2 Hz / sun 2 Hz**; scenario **4000 s**, reorientation every **12 min**, nadir-pointing after **2000 s**; degraded wheel factor **0 → 0.5 (50% loss)**; gains **K_ICL 10 → 1**, **K 5e-1 → 1e-2**; simulation plant **65 kg, J = diag{0.44, 0.70, 0.70}, 50 mN·m, 366 rad/s** vs HIL plant **20 kg, J = diag{0.30, 0.42, 0.42}, 20 mN·m, 1040 rad/s**; **current deadband ~300 mA**; initial RW spin-up **[100, −100, −100, 100] rad/s**.

### Directly reusable for the 24U thesis / ESP32-S3 HIL
The **definitive template for the thesis HIL chapter**: an explicit MIL/SIL/HIL-a/HIL-b/HIL-c matrix stating what is real vs simulated at each stage, a staged integration procedure, sensor-noise models at realistic sampling rates (gyro 10 Hz, magnetometer 2 Hz, sun sensor 2 Hz — directly applicable to the thesis sensor suite), a quantified real-time budget (3.86 ms in a 100 ms loop, CPU and RAM deltas), an online actuator-health estimate that the deployed controller uses **instead of** the true fault variable, and two hardware traps to pre-empt: the **~300 mA current deadband** and the fact that **torque commands feasible in simulation exceeded real RW limits and halted the experiment** (forcing a 10× gain reduction). Its limitation — HIL artefacts blocking *physical* fault injection, cured only by an air bearing — is exactly the argument the thesis should make for its own HIL/air-bearing choice.

---

## Cross-cutting patterns — what a defensible HIL chapter must contain

- **An explicit stage table (MIL → SIL → HIL-a/b/c) naming what is real and what is simulated at each step.** Only C4 provides this (Table: host vs onboard vs hardware, with RW model / controller / RWs toggled per mode); C2 and C3 collapse to a single "hardware run" stage, and C1 jumps straight to a policy-in-the-loop RTOS test. A thesis HIL chapter without a per-stage real/simulated declaration is not defensible against the standard set by C4.
- **A quantified real-time margin, not a claim of real-time operation.** C4 is the only paper that reports per-step execution time (3.86 ± 0.20 ms avg, 6.62 ms max) against a stated loop budget (100 ms → ~26× margin), plus CPU load per node (14.7% / 10.3%) and RAM delta (16.6% → 19.6%). C1, C2 and C3 report **no** latency or footprint figures at all. For an ESP32-S3 target the equivalent table (inference ms avg/max/σ, RAM/flash bytes, loop period, margin) is mandatory.
- **The deployed policy must consume an estimate, never the true fault variable.** Two opposite designs appear: C1 gives each fault case its own specialised policy (fault identity effectively known via policy selection), whereas C4 keeps `Φ` unknown and has the controller estimate `θ̂` online, converging to the true health once the excitation threshold (λ̄ = 1e-7) is crossed. C4's pattern is the one that matches the thesis constraint that the policy never sees the true fault; C1's is the pattern to explicitly argue against.
- **Actuator interface reality must be specified and then defended with numbers.** The two largest documented sim-to-real failures in this batch are both actuator-interface issues: a **~300 mA current deadband** that made torque-mode commands unusable (C4), and a **motor dead zone below PWM ≈ 30** (C3) that contributed to a **3× slowdown (2 s → 6 s)**. C4 also had to cut a gain by 10× because simulated torque commands exceeded real RW limits and halted the run. A defensible HIL chapter states the command mode (torque vs wheel-speed), the dead band, the saturation limits, and the PWM/voltage sag model.
- **Sensor realism at published sampling rates, with an estimator whose location is declared.** C4 injects noise at **gyro 10 Hz, magnetometer 2 Hz, sun sensors 2 Hz** and runs an EKF (multiplicative quaternion → ω, quaternion → MRP) **on the host**, listing EKF onboard migration as future work; C2's real IMU noise came from wheel/arm vibrations; C3 used a bare 100 Hz gyro with no estimator; C1 used perfect state plus delay randomisation [0.5, 1] s at 2 Hz. Sample rates, noise magnitudes, estimator type and estimator host (ground vs embedded) should all be tabulated.
- **A classical baseline carried through the same hardware, plus an honest sim-to-real gap analysis.** C2 and C3 both run PID/PD on the identical rig — C2's PD fails attitude control in simulation *and* on hardware, C3's PID overshoots and keeps oscillating while DDQN does not — which is the evidence a thesis needs to argue RL's case while keeping classical control as the fallback. C1 reports **no baseline** and C4 tests a non-RL adaptive controller, so neither can support a fault-tolerance claim on its own.
- **Deployment feasibility measured, not assumed.** C3's network could **not** be placed on the microcontroller and had to run ground-station-in-the-loop; C2 runs the policy on an ESP32 but reports **no** quantisation, latency or memory data; C1 ported to C in an RTOS with no footprint numbers. An ESP32-S3 HIL claim needs the quantisation/compilation toolchain, the measured network size in bytes, and the inference time on the actual MCU to be stated.
