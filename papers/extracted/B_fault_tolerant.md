# B — Fault-tolerant spacecraft attitude control with RL: environment / fault-model / training / simulation extraction

Extraction batch B (4 papers). Source files (markdown conversions of the papers, kept under `papers/markdowns/`):

1. `Fault-tolerant control of spacecraft attitude with prescribed performance based on reinforcement learning.md` — **B1** (Jin Lei et al., *Journal of Beijing University of Aeronautics and Astronautics*, Chinese-language paper; markdown has (cid:) OCR artefacts)
2. `Reinforcement learning based attitude fault-tolerant control of spacecraft with unknown system model.md` — **B2** (Yang Shaolong, Jin Lei, Rao Jiaxuan, *Journal of the Franklin Institute* 362 (2025) 107741)
3. `Safe reinforcement learning based agile satellite attitude control for non-cooperative target tracking with operation constraints and actuator faults.md` — **B3** (W. Lu, H. Zhuang, Z. Geng et al., *Aerospace Science and Technology* 168 (2026) 111238). The ` (copy).md` variant was deliberately **not** used.
4. `Adaptive satellite attitude control for varying masses using deep reinforcement learning.md` — **B4** (Frontiers in Robotics and AI, 2024, doi 10.3389/frobt.2024.1402846; DLR / TU Darmstadt)

Evidence note: these are markdown conversions. Several numbers in tables that were rendered as rotated text in the PDF (B3 Tables 5–7, B1/B2 parameter tables) are scrambled or absent in the `.md`; such fields are marked "not legible in source .md" rather than guessed. Everything else below is taken verbatim from the source text.

---

## B1 — Prescribed-performance FTC with RL (Jin Lei; Chinese journal)

**Simulator / environment**
- Numerical simulation ("数值仿真") of the spacecraft attitude system. No simulator named: not MATLAB/Simulink, Gazebo, Basilisk, STK, no hardware. Custom equations.
- Integrator: not stated. Simulation step = actuator control period ("其控制周期与仿真步长保持一致"); numeric value not stated.
- Run length 40 s (figures span 0–40 s), fault injected at t = 20 s. Attitude converges by ~10 s.

**Dynamics fidelity**
- Rigid-body 3-axis attitude only: J·ω̇ + ω×(Jω) = u_c + T_d + quaternion kinematics. No orbital motion / no 6-DOF translation, no gravity gradient, no drag, no SRP, no magnetic field.
- Inertia uncertainty explicit: true I_b = [[45.4, 1.5, 1.1], [1.5, 23.3, 1.2], [1.1, 1.2, 32.8]] kg·m²; nominal I_b0 = diag(40, 20, 28) kg·m² (≈13 % off-diagonal/diagonal mismatch) — the controller uses I_b0 and must adapt.
- Disturbance torque T_d = [3cos(0.001t); cos(0.001t)+1; −4sin(0.001t)] × 10⁻⁴ N·m.

**Sensors & estimation**
- No sensors modelled at all: "未引入敏感器，量测误差为0" (no sensor introduced, measurement error zero) → perfect full-state feedback of quaternion and angular velocity.
- Estimation is of *model*, not of measurements: adaptive laws estimate the lumped disturbance d = T_d + T_f and the inertia mismatch (rate α_d = 10, gain k_d = 0.001). No fault-specific observer.

**Actuators**
- 3 actuators described as continuous-torque reaction wheels or gyros ("可输出连续力矩的飞轮或陀螺"), installation matrix C = [[1, 0, 1/√3], [0, 1, 1/√3], [0, 0, 1/√3]] (third axis skewed).
- Allocation by pseudo-inverse: u_c = C⁺ T_w. No torque limits, no saturation handling, no desaturation (actuator output constraints explicitly deferred as future work).

**FAULT MODEL (key field)**
- Type: simultaneous **loss-of-effectiveness e₁ = 0.5 (50 % torque loss)** *and* **additive bias fault u₁ = −0.2 N·m** on the x-axis actuator.
- Injection: abrupt ("突发性"), single event at t = 20 s; exactly one actuator; fixed scenario, repeated identically in every run — **not randomised**.
- Controller is **not told** the fault (no FDI input, no fault label); the fault effect enters the lumped uncertainty d and is estimated adaptively online; no dedicated fault estimator/observer (an adaptive estimator of d plus the RL actor handle it).
- FT mechanism: prescribed-performance funnel on the sliding variable (transient + steady-state envelope) + online RL (actor–critic) compensation + adaptive compensation of the lumped disturbance/inertia uncertainty.

**Guarantees**
- Lyapunov proof of uniform ultimate boundedness of all signals (transformation error, estimation errors) with V̇ ≤ −λV + μ, V(t) ≤ μ/λ + (V0 − μ/λ)e^(−λt) (Eqs. 41–42).
- The prescribed-performance constraint is guaranteed by design: the sliding variable s(t) stays inside the performance function ρ(t) for the whole run, hence quaternion and angular-velocity transients/steady states never exceed the prescribed bounds.
- Assumptions: smooth strictly increasing error-transformation function; bounded inertia uncertainty and external disturbance; design parameters chosen to satisfy the stated inequalities (k, κ_c, κ_a, κ_d, δ, ρ).

**RL setup**
- Continuous-time **actor–critic online RL**, hand-coded (no library, no PPO/SAC/DDPG named). Critic = single-hidden-layer feed-forward NN with tanh activations; actor = polynomial basis functions of x_a = [ω_b; ω̇_b] (9 terms).
- Gains: α_c = 2, α_a = 5, k_c = 0.001, k_a = 0.0001, discount γ_c = 0, Q_r = 100·I₆, R_r = I₃, K_f = [1;1;1]ᵀ, α_d = 10, k_d = 0.001. Initial generic weights random in [−1,1]; actor initial parameter [0₃ₓ₆ −I₃]ᵀ.
- No episodes, no parallel envs, no replay buffer, no training-step count (weights adapt online during the 40 s run); hardware not stated.

**Training workflow**
- No domain randomisation, no curriculum, no episode termination. Reward/cost = instantaneous r = xᵀQ_r x + u_cᵀR_r u_c with x = [q_b; ω_b] minimised online (continuous-time cost integral, not episodic return). No sim-to-real tricks.

**Evaluation protocol**
- One deterministic scenario, **1 initial condition** (q_b(0) = [0.9531; 0.1; 0.15; −0.12]ᵀ, ω_b(0) = [0.4; −0.2; 0.3] (°)/s), 40 s; the single 20 s fault is a fixed test scenario.
- Baseline: adaptive sliding-mode fault-tolerant controller (ASM FTC, k₁ = 0.4). No Monte-Carlo runs, no statistics, no unseen-fault test (the only fault is the one in the scenario).

**Sim-to-hardware**: none (simulation only).

**Key quantitative results**
- Convergence by ~10 s; controller parameters k₀ = 2, k = 0.1, κ_i = 0.2, δ = ρ = 1, ρ_i0 = 0.4, ρ_i1 = 10⁻³.
- After the 20 s fault: quaternion variation ≤ 4×10⁻⁵ and angular-velocity variation ≤ 2×10⁻² (°)/s, re-converging to ~0 within 5 s; sliding variable stayed inside the prescribed performance envelope throughout.
- Baseline ASM FTC: quaternion control precision only ~10×10⁻³, ω fluctuation up to 0.2 (°)/s, and the sliding variable left the performance envelope after 10 s and did not converge to zero after the fault.

**Directly reusable for the 24U thesis**: the exact fault case (one x-axis wheel at 50 % effectiveness + torque bias, controller not told) plus the prescribed-performance envelope idea is a ready-made "guaranteed transient bound" component that can be wrapped around an RL policy; the 3-wheel skewed installation matrix and pseudo-inverse allocation match a 3-RW nanosat. Weaknesses to cite as gaps: one fixed fault, one IC, no randomisation, no Monte-Carlo, no hardware.

---

## B2 — RL-based FT attitude control with unknown system model (J. Franklin Institute 2025)

**Simulator / environment**
- Numerical simulation, custom equations (no named simulator, no MATLAB/Basilisk/STK, no hardware). Integrator, time step and control frequency: **not stated**. Simulation duration: not stated (fault at t = 20 s). Only one nominal trajectory is simulated (plus 500 random states used offline for training data).

**Dynamics fidelity**
- 6-state attitude model x ∈ ℝ⁶ (quaternion + angular rate); rigid body; attitude only — no orbit, no gravity gradient, no drag, no SRP, no magnetic field.
- Inertia uncertainty: true I_b = [[45.4, 1.5, 1], [1.5, 23.3, 1.2], [1, 1.2, 32.8]] kg·m² vs nominal I_b0 = diag(40, 20, 28) kg·m² (identical numbers to B1).
- Unmodelled dynamics f(x) assumed Lipschitz, ‖f(x)‖ ≤ D_f‖x‖; external disturbance T_d = [3cos(0.001t); cos(0.001t)+1; −4sin(0.001t)]×10⁻⁴ N·m (same as B1).

**Sensors & estimation**
- Sensor model: not stated — full state assumed available (no noise/bias values given).
- A **neural-network observer** estimates the unknown input matrix B (which is corrupted by multiplicative faults) and the lumped disturbance δ; update gains K_o = 20·I₆, α_w = 10, α_b = 10, α_δ = 100, k_w = k_b = k_δ = 0; x̂(0) = initial state, δ̂(0) = 0, Ŵ(0) random in [−0.5, 0.5]; observer activation σ(x) = [x; σ_c2(x)]ᵀ.

**Actuators**
- 4 actuators with installation matrix C = [0 1 0 1; 1 0 0 1; 0 0 1 1] (rows/columns include 1/√3 entries for the skewed wheel, i.e. 3 orthogonal + 1 redundant/skewed), weight R₁ = 0.1·I₄.
- No torque limits, no saturation, no desaturation; allocation commanded directly through the estimated B̂.

**FAULT MODEL (key field)**
- Type: on the x-axis actuator, simultaneous **multiplicative loss-of-effectiveness e₁ = 0.5 (50 %)** and **additive fault u_c1 = −0.1 N·m** (note: B1 uses −0.2 N·m for the same scenario).
- Injection: abrupt, single event at the **20th second**; one actuator; fixed, identical across runs — **not randomised**; no second fault.
- Controller is **not told** the fault: multiplicative effect is absorbed by the observer's estimate of B̂, additive effect by δ̂ plus a feedforward compensation term; the paper states the observer estimates B and δ "exactly" (to simulation accuracy).
- Dedicated fault estimator/observer: yes — NN observer (state + B + δ estimation). FT mechanism: observer + online RL + feedforward compensation (no redundancy, no safety layer, no prescribed performance).

**Guarantees**
- Theorem 1: NN-observer estimation error (x̃, W̃, B̃, δ̃) is bounded/UUB (set 𝒢₁); sufficient condition λ_min(K_o) > 0.5.
- Theorem 2: with critic weights updated by RLS, closed-loop states are bounded/UUB (set 𝒢₂ = {x : ‖x‖ ≤ √(μ₂/λ_x)}) under λ_min(Q₂) > D_f + 1 and λ_min(R₂) > 0.5·λ_max(BᵀB); f(x) Lipschitz with constant D_f; V̇₂ < 0 outside 𝒢₂. No explicit constraint enforcement beyond these conditions.

**RL setup**
- Continuous-time **approximate dynamic programming / policy iteration** (Vrabie–Lewis style), not a deep-RL library, no PPO/SAC; critic = NN with **21 quadratic-basis activation functions** σ_c1(x) (linear + pairwise quadratic terms of the 6 states); actor derived analytically from ∂σ_c/∂x.
- Offline: initial admissible policy obtained by fitting a PID-based critic (weights e.g. 75.4, 18.9, 37.0, 0, 0, 85.3, …); iteration data from **500 random initial states**; convergence in **4–5 iterations**; a co-state-approximation variant needs ~10 iterations. Online: critic weights updated by **recursive least squares** each sampling instant, P(0) large (value cut in the conversion, text says "sufficiently large unit matrix" or from the offline solution); Q₂ = 50·I₆, R₂ = 0.1·I₄.
- No episodes, no parallel envs, no GPU/library stated; total training steps not stated.

**Training workflow**
- No domain randomisation, no curriculum, no termination rules. Offline data from 500 random initial states; online adapts during the single flight. Reward/cost: quadratic r = xᵀQ₂x + uᵀR₂u. No sim-to-real tricks.

**Evaluation protocol**
- 1 initial condition (same as B1: q(0) = [0.9531, 0.1, 0.15, −0.12]ᵀ, ω(0) = [0.4, −0.2, 0.3] °/s); ablation = same controller with feedforward compensation disabled, plus initial vs final policy comparison; no Monte-Carlo, no statistical treatment; the fault is the single fixed 20 s event → **no unseen-fault test**.

**Sim-to-hardware**: none.

**Key quantitative results**
- Offline policy iteration reduces the cost function from ~8 (initial PID-fitted policy) to ~7 → **≈12.5 % reduction**; converges in 4–5 iterations (co-state variant ~10).
- Without feedforward compensation: after the 20 s fault the quaternions converge to **non-zero** steady values (residual attitude error).
- With feedforward compensation: quaternion and angular-velocity estimation errors converge to zero; NN observer estimates B and δ accurately; command torque shows a persistent deviation after 20 s that rapidly re-converges the attitude/rate deviation; critic-parameter norm converges before attitude stabilisation.

**Directly reusable for the 24U thesis**: same wheel-degradation-plus-bias fault scenario as B1 (50 % LOE), and a clear precedent for the "unknown system model → NN observer estimates the fault-corrupted input matrix, RL provides the optimal policy, feedforward cancels the bias" architecture (a non-deep-RL analogue of an RL controller with fault estimation). Gap: no randomisation, no Monte-Carlo, no episodes/steps, single IC.

---

## B3 — Safe RL for agile-satellite target tracking under constraints and actuator faults (Aerospace Sci. Tech. 2026)

**Simulator / environment**
- Custom Python simulation of the satellite (+ target) built on **OmniSafe's Constrained MDP interface** (OmniSafe RL package, PyTorch 2.2.2, CUDA 12.3, Python 3.11.8, Ubuntu 22.04; CPU AMD EPYC 7453 + GPU NVIDIA RTX 4090 — training "within a few hours").
- Integrator: **4th-order Runge–Kutta (RK4)** for the attitude dynamics. Time step: **1 s for attitude control**, **0.1 s for fault identification**. Episode timeline: 3 s fault-identification phase + **540 s** attitude-manoeuvre/target-tracking phase (9 min scenario, 1 Oct 2024 18:50:00–18:59:00).
- Orbits/ephemeris from **STK ("Systems Tool Kit")** orbital elements (ImagingSat: a = 6900 km, e = 0.0169, i = 96°, RAAN 30°; TargetSat a = 6785 km; 3 dynamic ForbiddenSat). Four forbidden zones checked each `step()`: 1 static (Sun) + 3 dynamic (ForbiddenSat) — i.e. Sun-avoidance + collision-avoidance-style attitude-forbidden zones, plus the tracking mandatory zone.

**Dynamics fidelity**
- Rigid-body attitude dynamics J·ω̇ = −ω×(Jω) + u + d with quaternion kinematics, plus orbital kinematics (satellite and target move on STK-defined orbits; the target is non-cooperative and the desired quaternion is recomputed online). No gravity gradient, no drag, no SRP, no magnetic field mentioned.
- Inertia J = [[10, 0.02, 0.01], [0.02, 15, −0.01], [0.01, −0.01, 20]] kg·m². Inertia uncertainty / time-varying mass: not modelled.
- Disturbance d = 10⁻⁵·[−10 + 4sin(3ωt) + 3cos(10ωt); 15 + 1.5sin(2ωt) + cos(5ωt); 10 + 3sin(10ωt) + 8sin(4ωt)] N·m (ω = orbital rate).

**Sensors & estimation**
- Measured angular velocity with **hybrid Gaussian noise**: ω_m = ω + η_noise, η_noise = η₁ + η₂, η₁ ~ N(0, (0.001|ω|)²), η₂ ~ N(0, (0.0001|ω_old|)²) i.e. 0.1 % of current |ω| plus 0.01 % of previous |ω| (reference [32,49] model). Measurement noise of attitude itself: not stated.
- **Fault-identification network** (learning-based FDI, described below) supplies ê_l and û_a to the policy; the dynamics residual Φ = J·ω̇ + ω×(Jω) is reconstructed from measured ω (finite differences over consecutive steps).

**Actuators**
- Reaction wheels ("reaction wheels are particularly vulnerable to performance degradation"); command torque range **±0.5 N·m per axis** (torque-saturation constraint implemented as part of the action range); angular-velocity constraint |ω_i| ≤ π/10 rad/s; no wheel-momentum model, no redundancy/re-allocation, no desaturation logic.

**FAULT MODEL (key field)**
- Type: general actuator fault model u = (I − E)u_c + u_a with E = diag(e_l1,…,e_ln), **effectiveness loss e_li ∈ [0,1]** (multiplicative; e = 1 ⇒ complete loss) and **additive bias u_a** (per-axis); total fault effect f = −E·u_c + u_a added to the dynamics.
- Sampling: **e_l ~ rand([0,1])** and **u_a ~ rand([−0.15, 0.15]) N·m per axis** — randomised, and constant within an episode (abrupt onset at the start of the tracking phase after the 3 s ID stage; not gradual/incipient, not time-varying).
- Number simultaneously: up to all three axes, independent of each other (no explicit "how many" limit; the 5 test cases use different per-axis combinations).
- Training: initial pose **and** fault scenarios are randomly generated each episode/timestep; the agent **is given the true fault** during training (`ê_l ← e_l`, Algorithm 1) "to encourage fault-tolerant behaviour".
- Testing: the true fault is **not** given — the agent acts on faults estimated by the pretrained fault-ID network (`(ê_l, û_a) ← Network(Φ, u_c)`); 5 test cases are systematically selected to span arbitrary attitude, arbitrary angular velocity and arbitrary actuator faults (within the same randomised fault space).
- Fault estimator/observer: **yes** — bidirectional LSTM (input_size 6 = 3-axis residual Φ + 3-axis command torque u_c, hidden_size 128, bidirectional → 256) with a lightweight **CBAM** channel+spatial attention module, concatenated to a 512-dim feature vector, FC layer → 6 outputs (ê_l, û_a); look-back window L (tensor L×6). Implemented in Torch.
- FT mechanism: learned FDI + safe RL (worst-case soft actor-critic) with safety constraints implemented as **soft constraints through adjustable penalty terms in the cost function**.

**Guarantees**
- No Lyapunov/stability proof for the policy. The guarantee is a **Constrained MDP (CMDP)** formulation M = (S, A, p, r, c, d_cost, γ) with worst-case/risk-aware constraint satisfaction: WCSAC replaces the single-output safety critic with a **distributional safety critic** (mean + variance of the cost return) and enforces a risk level α = 0.8 (CVaR-like worst-case bound); actor and cost weights updated by TD learning and gradient descent.
- Constraints enforced: attitude-forbidden zones (angular separation to Sun/ForbiddenSat > θ_forbidden), attitude-mandatory zone (target inside payload FOV, angle < θ_tracking), angular-velocity limit (|ω_i| ≤ π/10 rad/s), torque saturation (|u_ci| ≤ 0.5 N·m).
- Assumptions: fault estimates from the FDI network are accurate enough (validated by the [a]–[e] estimation-quality ablation); constraints are soft penalties, so occasional constraint violations remain possible (the paper reports sparse post-convergence cost spikes).

**RL setup**
- Algorithm: **WCSAC (worst-case soft actor-critic)**, an off-policy SAC variant (specialised SACLag); framework **OmniSafe**; networks implemented in PyTorch (actor/critic and the FDI LSTM); no explicit hidden-layer sizes for the actor/critic stated in the readable text (weights α and k initialised to 0.6931).
- Hyperparameters (Table 3/4): discount γ = 0.99; risk level α = 0.8; reward coefficients k₁,k₂,k₃,k₄ = 1, 1, 10, 1; learning rate 0.001; optimizer Adam; replay buffer **1×10⁶**; **total timesteps 3×10⁶**; ω_tracking = π/12 rad/s; ω_max = π/10 rad/s; θ_tracking = 10°; θ_forbidden = 25°; command torque ±0.5 N·m; d_cost = safety-threshold value (present in Table 3 but the numeric cell is not legible in the .md).
- Parallel envs: not stated (OmniSafe vectorised interface implied). Hardware: EPYC 7453 + RTX 4090; both the control network and the FDI network train "within a few hours".

**Training workflow**
- Domain randomisation: **yes** — initial attitude pose and angular velocity as well as fault scenarios randomised per trajectory/episode; faults passed to the agent as part of the state (teacher forcing).
- Reward: multi-term (Eqs. 35–36) built from tracking-error and forbidden-zone terms with weights k₁–k₄ and a separate cost signal c (Eq. 31: forbidden-zone violations, angular-velocity limit breaches, actuator-limit breaches); no separate curriculum reported; termination = end of the 540 s episode (+ failure states implied).
- Sim-to-real: none; the paper only argues "lightweight requirements for spaceborne missions" and few-hours training.

**Evaluation protocol**
- **5 test cases** (Table 4) with specified initial attitudes (e.g. quaternions [0.3320, −0.4676, −0.1528, 0.8047]ᵀ and [0.1584, 0.3066, 0.3303, 0.8784]ᵀ appear in the readable text) and specified actuator faults covering the fault space (e_l ∈ [0,1], u_a ∈ [−0.15,0.15] N·m).
- Metrics: reward, cost (constraint violations), percentage reduction of violations vs SAC, tracking time (duration with the target inside the payload FOV), plus nominal/actual torque and quaternion responses.
- Baselines: **vanilla SAC, SACLag, SACPID, TD3PID, Reward-Penalty (λ_RP = 5)** — 5 baselines with identical training/evaluation hyperparameters.
- Statistics: training curves plotted over multiple random seeds (shaded min–max band + mean); the FDI ablation is repeated **5000 runs** with averaged MSE/MAE/inference time. No paired tests reported.
- Table 5 (per-case metrics) and Tables 6–7 (FDI comparison, fault-estimation-quality ablation) are rendered as rotated text in the markdown and their numbers are not legible.

**Sim-to-hardware**: none — no MIL/SIL/HIL, no onboard deployment; only simulation.

**Key quantitative results**
- Training: episode reward rises quickly and converges to **≥ 5000**; episode cost decreases and approaches zero in many episodes (sparse residual violations); actor and critic losses stabilise.
- Fault identification (5000-run average, Table 6): the proposed LSTM+CBAM network achieves the **lowest estimation error** with "relatively short" inference time among Least-Squares filter / gradient-descent / NN[32] comparators (absolute MSE/MAE values not legible in the .md).
- Estimation-quality ablation (Table 7, configurations [a]–[e]): network-estimated faults [a] perform comparably to the ideal true-fault case [e] in reward, cost and execution time, whereas random/incomplete fault assumptions [b]–[d] "significantly" degrade reward and increase manoeuvring cost.
- Comparison: SAC reaches high reward but large cost (poor safety compliance); SACLag lowers cost at the price of tracking reward; SACPID/TD3PID also degrade; WCSAC gives the best reward/cost trade-off and stable tracking duration across the 5 cases; vanilla SAC frequently violates attitude constraints (Case 2 example) while WCSAC keeps all forbidden zones outside the keep-out angle and the target within the 10° half-angle, allowing cumulative tracking time to grow through the episode (small residual tracking error remains by design).

**Directly reusable for the 24U thesis**: the most complete template in this batch — randomised multiplicative (e_l ∈ [0,1], covering dead wheels) + additive wheel faults at every episode, faults re-estimated at deployment by a learned FDI network, safety constraints enforced through a constrained MDP with a risk parameter, and a fault-estimation-quality ablation showing that good FDI is what makes the RL controller safe. Directly transferable: the fault model u = (I−E)u_c + u_a, the e_l ∈ [0,1] randomisation (specialise to {0, 0.5, 1} for the thesis), the 10°/25° keep-out/tracking angle formulation (adapt to nadir pointing + Sun exclusion), and the "told in training, estimated at test" protocol. Gaps: no HIL, no MTQ, no wheel-momentum/desaturation, target-tracking task rather than nadir pointing.

---

## B4 — Adaptive satellite attitude control for varying masses with deep RL (Frontiers in Robotics and AI, 2024)

**Simulator / environment**
- **Basilisk** astrodynamics framework (University of Colorado AVS/LASP, C/C++ modules with Python) as the simulation; agent connected through an **OpenAI Gym interface**; RL algorithms from **RLlib** (SAC and PPO); visualisation with **Vizard**. Modules used: `spacecraft` (rigid body), `gravityEffector` (LEO orbital dynamics), `simpleNav` (attitude, rate, position), `inertial3D` + `attTrackingError` (attitude error), `rwMotorTorque` (maps torque to the 3 reaction wheels), `initialConditions`.
- Time step **10 s**, episode length **600 s = 10 min** (i.e. 60 steps per episode) for the RL agents; RL control frequency therefore 0.1 Hz. The PID baseline runs at **1 Hz**.
- Training hardware: SAC on RTX 3090 + Intel Core i9-12900KF; PPO on RTX 3090 + Intel Xeon Gold 6140.

**Dynamics fidelity**
- Rigid-body spacecraft model with 3 balanced reaction wheels, one per body axis; coupled wheel/full dynamics from Alcorn et al. (2018) EoM; attitude represented by **modified Rodrigues parameters (MRP)**, shortest-path attitude error.
- The simulation has **no aerodynamic, gravitational (on attitude) or solar radiation pressure effects**; no magnetic field, no gravity gradient. `gravityEffector` supplies orbital dynamics for the LEO orbit (translation) only.
- Inertia/mass: **hidden, widely varying mass sampled uniformly 10–1,000 kg per episode** (ADR scenario: unknown debris mass before and after capture); mass is not in the state and must be inferred from stacked observations. No actuator faults.

**Sensors & estimation**
- `simpleNav` provides attitude, attitude rate and position; measurement noise/bias values: **not stated** (perfect-state baseline; no estimator). The agent must infer the hidden mass from a history of observations/actions (stacked observations), which is the paper's substitute for estimation.

**Actuators**
- 3 reaction wheels modelled after the **Honeywell HR16**; action space = torque vector with **u_min = −0.2 N·m, u_max = 0.2 N·m**; wheel-speed limit Ω_max = **6000 rpm** (6000 rpm is the saturation trigger in the reward: r = −1 if |Ω_i| ≥ 6000 rpm).
- No allocation logic (body-aligned wheels), no desaturation (magnetorquers) modelled; wheel speed Ω is part of the state.

**FAULT MODEL (key field)**
- **No actuator faults are modelled in this paper** — no loss of effectiveness, no failure, no bias, no lock, no saturation fault injection; the only actuator-related limiting effect is wheel-speed saturation in the reward. 24U-thesis relevance for the fault model itself: none.

**Guarantees**
- No stability, safety or constraint-enforcement guarantee; purely empirical Monte-Carlo evaluation. States/torques are bounded only implicitly by the action range and the wheel-speed reward penalty.

**RL setup**
- Algorithms: **SAC and PPO (RLlib)**; variants with and without **stacked observations** (5 stacked observations+actions). Networks: 256 hidden units, ReLU, Adam.
  - SAC: learning rate 3×10⁻⁴ (actor, Q-networks and α), γ = 0.99, replay buffer 1,000,000, entropy target −dim(A) = −3, target update interval 1, target smoothing τ = 5×10⁻³.
  - PPO: horizon 60, learning rate 5×10⁻⁵, 500 epochs, clipping ε = 0.2, 256 hidden units, batch size 128.
- Parallel envs: not stated. Total training steps/episodes: not stated (only training parameters and hardware). Timestep 10 s, episode 600 s.

**Training workflow**
- Fixed training initial condition: σ_B/N,Init = [1, 0, 0] (180° rotation about x), ω_B/N,Init = [0, 0, 0] rad/s, goal σ_desired = [0, 0, 0]; **mass is the only randomised quantity** (uniform 10–1,000 kg per episode).
- Reward (Eq. 31, same across all scenarios, −1 ≤ r ≤ 0.1, so −60 ≤ R ≤ 6 over 60 steps): −1 if any |Ω_i| ≥ 6000 rpm; −|σ|² + 0.1 if all three attitude-error coordinates are below 0.05; −|σ|² + 0.05 if at least two coordinates are below the threshold; −1 to prevent spinning out of control (especially at low mass). No curriculum; termination at 60 steps or loss of control.
- Sim-to-real tricks: none beyond the "stacked observations" technique (5 past observation/action pairs) to make the hidden mass observable — described as enabling the agent to extract mass information without measuring it.

**Evaluation protocol**
- **1,000 test episodes**; initial and desired attitudes identical to training; mass uniformly sampled 10–1,000 kg each episode.
- Metrics (Table 4): mean return ± SD; final attitude-error norm |σ_final| ± SD; per-component σ_i final with **95 % confidence interval**; **settling time** ± SD.
- Baselines: SAC, PPO, SAC-stacked, PPO-stacked, and a **PID controller** (interfaced with Basilisk, 1 Hz, gains k_p = 0.36, k_i = 0.00015, k_d = 14.02, manually tuned then Nelder–Mead-optimised at m = 300 kg).
- No unseen faults are tested (no faults exist in this work); the unseen element is *mass* (unknown to the agent), not faults.

**Sim-to-hardware**: not stated — no MIL/SIL/HIL, no real-time constraints, no deployment target (future work mentions varying initial attitudes and mass changing within an episode).

**Key quantitative results (Table 4, 1,000 episodes, mass 10–1,000 kg)**
- SAC: return 0.95 ± 0.98, |σ_final| = 5.36 ± 5.19°, settling 232.77 ± 74.97 s.
- PPO: return 1.16 ± 0.90, |σ_final| = 9.83 ± 1.78°, settling 217.52 ± 81.91 s.
- SAC-stacked: return 1.95 ± 0.69, |σ_final| = 3.92 ± 2.58°, settling 195.77 ± 61.80 s.
- **PPO-stacked (best): return 2.23 ± 0.76, |σ_final| = 4.53 ± 1.21°, settling 166.48 ± 12.46 s.**
- PID: return −0.64 ± 4.30, |σ_final| = 6.77 ± 16.75° (CI [−4.62, 2.11]), settling 229.42 ± 48.54 s; very consistent for m ≥ 100 kg but fails to stabilise at low mass.
- Single-episode comparisons: at m = 15 kg, SAC without stacking reaches R = −8.91 with final attitude error 81.41° ([60.31, −27.02, −47.54]°) while SAC-stacked reaches R = 2.95, |σ_final| = 3.41° ([−0.77, 3.12, 1.14]°), settling 260 s (78° better). At m = 300 kg, SAC-stacked R = 2.16, |σ_final| = 3.24°, settling 180 s vs PID R = 0.65, |σ_final| = 4.19°, settling 206 s.
- Agents without stacked observations cannot handle 10–100 kg; RL agents cannot output exactly [0,0,0] so a small residual action (and small attitude error) remains.

**Directly reusable for the 24U thesis**: Basilisk + RLlib + Gym interface as a credible, citable simulation stack; per-episode randomisation of a hidden plant parameter (mass here → wheel health in the thesis) with a fixed initial condition; reward shaping that adds per-axis tolerance bonuses (all coordinates < 0.05 → bonus; ≥ 2 coordinates → smaller bonus), a wheel-speed saturation penalty (Ω_max = 6000 rpm), and a spin-out penalty — directly portable to the nadir-pointing reward; 1,000-episode Monte-Carlo protocol with return, final error, 95 % CI and settling time as metrics; and the PID baseline tuned by Nelder–Mead for comparison. Gaps: no faults, coarse 10 s control step, fixed initial condition, no HIL.

---

## Cross-cutting patterns

- **Fault-model vocabulary converges on the same two-part actuator model**: multiplicative loss of effectiveness (B1: e₁ = 0.5; B2: e₁ = 0.5; B3: e_l ∈ [0,1] drawn uniformly) plus an additive bias (B1: −0.2 N·m; B2: −0.1 N·m; B3: ±0.15 N·m), with abrupt onset and constant value inside the episode — nobody models incipient/gradual degradation, wheel lock, or multiple time-separated faults.
- **Fault randomisation during training is the exception, not the rule**: only B3 randomises faults (per episode, all three axes independent) and only B3 re-estimates the fault at test time; B1/B2 evaluate a single hand-picked fault (x-axis wheel, 50 % LOE + bias at t = 20 s), B4 has no faults at all. No paper trains and tests on faults drawn from disjoint distributions.
- **Two distinct RL paradigms**: continuous-time actor–critic/ADP with Lyapunov proofs and hand-coded networks (B1, B2; online adaptation, no episodes, no GPU) versus episodic deep RL with modern frameworks — WCSAC/OmniSafe (B3) and SAC/PPO via RLlib (B4). Only the episodic ones use a Gym interface, replay buffers (10⁶ in B3) and millions of steps (3×10⁶ in B3; steps not stated in B4).
- **Fault awareness at run time is provided either by adaptive/observer estimation (B1, B2) or by a learned FDI network (B3)**; in every case the controller is *not* told the fault at deployment, and in B3 the same policy is run with true faults (training) and estimated faults (testing) — the closest thing in this batch to a sim-to-deployment fault-domain shift.
- **Guarantees trade off against RL scale**: B1 (prescribed performance + UUB) and B2 (two Lyapunov theorems, UUB sets 𝒢₁/𝒢₂) prove boundedness but train/evaluate one trajectory from one initial condition; B3 abandons Lyapunov guarantees for a CMDP with a risk level (α = 0.8) and soft constraint penalties, giving broad randomisation + 5 test cases but only probabilistic (not proven) constraint satisfaction; B4 offers no guarantee at all.
- **Environment fidelity is uniformly low and attitude-only**: nobody models gravity gradient, drag/SRP, magnetic field or MTQ actuation; orbit appears only in B3 (STK ephemeris + moving target) and B4 (Basilisk `gravityEffector`). Inertia uncertainty is a static mismatch (B1/B2: true 45.4/23.3/32.8 kg·m² off-diagonal matrix vs nominal diag(40, 20, 28)), never time-varying; mass variation appears only in B4 (10–1,000 kg, hidden). Sensor noise is modelled only in B3 (0.1 % + 0.01 % relative gyro noise); B1 explicitly assumes zero measurement error.
- **No paper in this batch performs MIL/SIL/HIL or any hardware test**; evaluation is pure software simulation, with Monte-Carlo statistics only in B3 (5 cases, multi-seed training curves, 5000-run FDI ablation, though per-case table values are lost in the .md) and B4 (1,000 episodes with SD and 95 % CI). B1/B2 report single scenarios without statistics.

## UNSEEN-FAULT FLAGGING

- **B1 — no**: one fixed fault (x-axis wheel, 50 % LOE + bias at t = 20 s), one initial condition, no randomisation; the "unseen" aspect is only the unknown fault magnitude handled by an adaptive law.
- **B2 — no**: same fault type/magnitude/wheel and same single initial condition; no fault randomisation, no Monte-Carlo.
- **B3 — partial / the only candidate**: faults are randomised during training (e_l ~ rand([0,1]), u_a ~ rand([−0.15,0.15] N·m)) and at test time the agent must act on *estimated* faults from a pretrained FDI network rather than the true fault it saw in training; the 5 test cases are new samples with hand-selected attitude/rate/fault combinations from the same fault family. This is a fault-information shift (true → estimated) rather than a fault-distribution shift, and the paper reports that estimated faults perform comparably to the ideal true-fault configuration. No test uses a fault outside the training distribution or a fault type not seen in training.
- **B4 — no faults exist** in the work; the analogous unseen variable is the hidden mass (10–1,000 kg sampled per episode, never observed by the agent).
- Conclusion: **no paper in this batch demonstrates generalisation to unseen fault types or magnitudes**; this is the clearest gap for a thesis that wants to claim fault-tolerant RL generalising to the 0 % / 50 %-torque wheel-failure cases.

## Gap summary vs the 24U thesis design (for the justification chapter)

- Precedent exists for: 3RW + skewed-wheel fault modelling (B1/B2), wheel health randomisation with e_l ∈ [0,1] (B3 — specialised to h ∈ [0.5,1] plus dead wheel in the thesis), nadir/attitude-pointing rest-to-rest tasks with random initial attitude and rate (B3 randomises initial pose; B4 does not), PPO on a Gym-style env with millions of steps (B4 uses RLlib/PPO/SAC; B3 3×10⁶ steps), 5 Hz-class fixed control steps (B3 uses 1 s, B4 10 s — the thesis's 5 Hz is finer than both), fault-awareness at test via estimation rather than a fault label (B1/B2/B3 all agree on this), and Monte-Carlo evaluation with SD/percentiles (B4 1,000 episodes).
- Gaps the thesis can claim: no batch-B paper combines (i) randomised wheel faults across the full 0–100 % range *including complete failure*, (ii) random initial attitude *and* angular velocity, (iii) a nadir/LVLH pointing target with MTQ-based actuation/desaturation, (iv) a 6-DOF orbit-coupled nanosat-class plant (≈35 kg, J = diag(0.38, 0.73, 0.58) kg·m²), (v) RL with formal or CMDP-style safety constraints, and (vi) a MIL→SIL→HIL path to an embedded MCU. Every batch-B paper misses at least three of these six.
