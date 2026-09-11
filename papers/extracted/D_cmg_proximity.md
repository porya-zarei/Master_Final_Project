# Extraction D — CMG-based RL attitude control, RL vs classical for proximity ops, target capture, state-uncertainty guidance

Scope: ENVIRONMENT / TRAINING / SIMULATION setup extracted from 4 papers. Values copied verbatim where stated; schema fields the papers do not report are marked "not stated". OCR-origin ambiguity is flagged inline.

---

## Paper 1 — Deep reinforcement learning-based attitude control for spacecraft using control moment gyros

**Simulator/environment**
- Simulator: **not stated** (no named framework — equations of motion and quaternion kinematics written out in the paper; no MATLAB/Simulink/Basilisk/Gazebo/Python statement).
- Integrator: not stated. Only "the environment is characterized by the rotational equations of motion and quaternion kinematics"; a fixed **time step of 0.1 s** is used.
- Control frequency: **10 Hz** (0.1 s step, 300 steps per episode).
- Episode: **30 s max maneuver**, **300 steps** per training episode (0.1 s action interval ⇒ 300 steps = 30 s).
- Relative-motion model: none (attitude-only; no translational/orbital dynamics).

**Dynamics fidelity**
- 6-DOF: **no** — attitude-only 3-DOF rigid-body rotational dynamics plus quaternion kinematics (no translation, no orbit).
- Orbital/relative dynamics (CW/Hill): none.
- Disturbances: yes — external sinusoidal disturbance torques; amplitudes **5, 5, 10** (units as printed; ambiguous). Robustness study additionally adds **white Gaussian noise**.
- Gravity gradient, drag/SRP, flexible appendages: not stated / not modelled.
- CMG singularities: yes — addressed via a **generalized singularity-robust inverse (GSRI) steering law** used by the conventional baseline and in the second (recovery) phase; the DRL policy outputs gimbal rates directly, so singularity behaviour is learned implicitly rather than analytically managed during phase 1.
- Inertia: `diag(21400, 20100, 5500) kg·m²` (large agile satellite). Robustness test re-runs with a different inertia `diag(22470, 21105, 5250)` kg·m², CMG momentum **H = 800 N·m·s**, and a **roof-type** CMG cluster (vs the nominal configuration).
- CMG cluster: 4 CMGs, **pyramid** configuration, skew angle **53.13°**, nominal momentum **h = 1000 N·m·s**; initial gimbal angles `[+45°, −45°, +45°, −45°]` (Table 2).
- Control torque saturation: printed as **"3000 N·m"** (sic — unit as printed; suspicious for this class of vehicle, flagged). Max slew rate assumed **30 deg/s**. Max gimbal rate **1.0 rad/s**.

**Sensors & estimation**
- No estimator, no EKF/UKF/MEKF. The policy consumes the **true state** plus CMG gimbal angles.
- Observation (11-dim): quaternion error `q_e` (4) + body angular velocity `ω` (3) + CMG gimbal angles `δ` (4).
- Noise (robustness study only, white Gaussian): angular-momentum noise std **1.0 N·m (or N·m·s as printed)**, rate noise std **ρ_ω = 0.005 rad/s**, gimbal-angle noise std **ρ_δ = 0.01 rad**. Noise is injected as **noise-augmented observations** — not a belief state; no POMDP formalism.

**Actuators**
- CMG only (4 CMGs, pyramid, 53.13° skew). Action = **gimbal-rate commands**, 4-dim continuous, limited to **|δ̇| ≤ 1.0 rad/s**.
- Steering law/allocation: for the actor, none — the RL action *is* gimbal rate. The conventional controller + GSRI steering law is used as the benchmark and as the phase-2 controller.
- Desaturation / RW / MTQ / thrusters: not used, not stated.

**Faults or failure modes**
- No actuator fault modelled (no CMG failure, no gimbal lock injection). "Fault tolerance" is limited to **parametric robustness**: different inertia, different CMG momentum, roof-type CMG cluster, added sensor-type noise — all without retraining.

**RL setup**
- Algorithm: **SAC** (primary); compared against **TD3** and **PPO**.
- Library/implementation: not stated.
- Networks: SAC uses **5 networks** (1 actor, 2 critics, 2 target critics) — sizes/activations not stated. TD3/PPO network sizes not stated.
- Key hyperparameters: only reward weights and the tolerance are given (see rewards). Learning rate, batch size, buffer size, γ, τ, target-update interval, entropy coefficient: **not stated**.
- Parallel envs: not stated.
- Total training steps/episodes: not stated (learning curves use a **moving window of 1000 episodes**, implying ≥ several thousand episodes, but the paper gives no total).
- Wall-clock/hardware: not stated.

**Simulation workflow**
- No vectorization/parallel-env statement, no domain randomization statement, no curriculum statement.
- **Two-phase architecture (key design)**: 
  - Phase 1 — DRL (SAC) drives the plant from the initial attitude to a **tolerance band around the target**, defined by `β_q = 0.04`.
  - Phase 2 — a **conventional quaternion-error feedback controller + GSRI steering law** takes over once inside the tolerance band.
  - Rationale stated: the DRL controller retains a small steady-state bias at ≈23 s and cannot null it cleanly, so the switching architecture is used.
- Reward (shaping): `r = −k_q ‖q_e‖² − k_1 ‖ω‖² − k_2 log(1 + ‖ω‖²) − (β_q chosen term)`, with **k_q = 1.0, k_1 = 100, k_2 = 500**. A log-shaped rate term was added because the quadratic term alone left residual rate error; the log term sharpens the gradient near convergence. No explicit safety/constraint penalty, no action-smoothness penalty stated.
- Termination: episode ends at `β_q = 0.04` tolerance (hand-off to phase 2) or at the 300-step / 30 s horizon. Constraint-violation termination not stated.

**Evaluation protocol**
- Initial conditions: Table 2 gives a set of initial quaternions with **zero initial angular rates**. Number of evaluation episodes/Monte Carlo count: not stated.
- Metrics: quaternion-error norm, angular-velocity norm, control effort; learning-curve return.
- Baselines: **(a)** the conventional quaternion-error feedback control law with **GSRI** steering; **(b)** TD3 and PPO vs SAC learning curves.
- Statistical treatment: the tolerance `β_q = 0.04` is stated to have been chosen using "Monte-Carlo simulations", but no counts, CIs or seeds are reported. Learning curves comparable.
- Convergence: SAC and TD3 both reach a return plateau of **≈700**; PPO plateaus **lower** (value not specified in text beyond "lower"). SAC and TD3 stabilize at similar return; SAC selected for better robustness/behaviour.

**Comparison methodology (RL vs classical)**
- Fairness: the classical controller is a **published quaternion-error feedback law with GSRI** — i.e., a real, non-strawman baseline. However, the comparison is **not head-to-head on the same task** — the paper's own conclusion is that DRL alone does not match the conventional controller's steady-state accuracy, and it therefore *combines* them (phase 1 RL + phase 2 classical). That is an honest admission rather than an unfair advantage claim.
- Risks detected: (i) no reported tuning budget for either controller, so "same tuning effort" cannot be verified; (ii) no compute comparison (RL training cost never stated); (iii) both controllers are given the same perfect state (noise only in a separate robustness study), so information parity holds in the main study; (iv) the classical baseline benefits from an analytic singularity-robust steering law that the RL policy has to discover — an asymmetry in *prior knowledge*, not information.

**Sim-to-hardware**
- None. No MIL/SIL/HIL, no processor-in-the-loop, no target hardware. Deployment vehicle implied to be a large agile satellite, not a nanosat.

**Key quantitative results**
- Simulator timestep 0.1 s; 300 steps; 30 s maneuver; 4 CMGs, pyramid, 53.13° skew, h = 1000 N·m·s, gimbal rate limit 1.0 rad/s.
- Inertia diag(21400, 20100, 5500) kg·m²; robustness variant diag(22470, 21105, 5250) kg·m² + roof-type CMGs + H = 800 N·m·s.
- Noise for robustness: 1.0 (momentum), 0.005 rad/s (rate), 0.01 rad (gimbal angle).
- SAC/TD3 plateau return ≈700; PPO lower. Hand-off tolerance β_q = 0.04; residual DRL bias at ≈23 s.
- Disturbance amplitudes 5, 5, 10 (units as printed).

**Reusable for a 24U nanosat fault-tolerant thesis**
- The **hybrid "RL slews + classical/allocator finishes" architecture with an explicit tolerance band (β_q = 0.04)** maps directly onto our design: RL produces desired torque, a physics-based fault-tolerant allocator finishes and holds; the tolerance-band switching logic and the steady-state-bias honesty are exactly the pattern we need for a defensible RL+allocation split.
- It also gives a realistic **model-mismatch/noise test recipe** (changed inertia, changed actuator set, Gaussian noise on rate/gimbal-state) and an observation that includes **actuator state** (gimbal angles) — structurally identical to including normalized wheel speeds in our 9-dim observation.

---

## Paper 2 — Comparing Modern Control to Reinforcement Learning Control for Spacecraft Proximity Operations

**Simulator/environment**
- Simulator: **custom, Python** (opens with an OpenAI-Gym-style framing in the references/background; no MATLAB/Simulink/Basilisk/STK). Named framework: not stated.
- Integrator: not stated — linear quadratic solutions used analytically; RL rollout step **∆t = 1.0 s**.
- Control frequency: **1 Hz** (∆t = 1.0 s). All controllers, including the continuous modern controllers, are **discretized at ∆t = 1.0 s** for comparability; RL uses **zero-order hold** commands.
- Episode horizon: **maximum two orbits = 6117 s** (chosen orbital period), n = 0.001027 rad/s.
- Relative-motion model: **Clohessy–Wiltshire / Hill equations, 2-D in-plane (out-of-plane neglected)**.

**Dynamics fidelity**
- Full 6-DOF: no. **2-D relative translational motion in the Hill frame** (x = radial, y = along-track); out-of-plane z neglected.
- Relative dynamics: **CW/Hill linearized equations** — the linear model is the plant for every controller including the RL agent.
- Disturbances, drag/SRP, gravity gradient, flexible appendages: not modelled (linear CW plant only).
- Attitude dynamics: none (position/velocity only; the paper notes attitude is not part of the study).

**Sensors & estimation**
- Perfect state (full relative position and velocity available to all controllers); no estimator, no EKF/UKF.
- State uncertainty: **not modelled** — no POMDP, no noise-augmented observations.
- Constraints tied to state: **max relative velocity 0.5 m/s**, control accel/force limit ±1 N.

**Actuators**
- **Thrusters only** (3-axis force command, in-plane components used). Limits: **±1 N** per axis. Mass **m = 12 kg** (6U CubeSat class).
- No RW/CMG/MTQ, no allocation, no desaturation, no steering law.

**Faults or failure modes**
- None modelled. No actuator failure; "safety" appears only as the 0.5 m/s velocity constraint and the "avoid crashing" reward term.

**RL setup**
- Algorithm: **PPO** (proximal policy optimization), on-policy.
- Library: not stated explicitly.
- Network size, activations, learning rate, γ, clip range, entropy coefficient, epochs, batch size: **not stated**.
- Parallel envs: not stated.
- Total training steps/episodes: not stated — training continued "until the ∆V and rendezvous time stagnated" (convergence-based stopping, no step count given).
- Wall-clock/hardware: not stated.

**Simulation workflow**
- No vectorization, no domain randomization, no curriculum stated.
- Reward shaping (four candidate formulations tested, tuned "with slightly differing values for each reward function"): penalize high **relative velocity** and high **acceleration/∆V**; reward progress toward the parking orbit; reward avoiding a crash; reward reaching the target. A reward ablation (4 variants) is reported.
- Termination: episode ends at two-orbit time limit; crash/constraint violation is penalized. Explicit constraint-violation termination semantics: not stated beyond that.

**Evaluation protocol**
- Initial conditions: **4 hand-picked rendezvous cases** (differences in relative position/velocity and in target co-location with the parking orbit). The RL agent trained on **random initial conditions**, then evaluated on the 4 cases → an explicit generalization test.
- Monte Carlo count / episode count: **not stated** (4 cases, apparently single or few realizations each).
- Metrics: **cumulative ∆V** (labelled [m/s] in the table but written as "N" in the text — internal inconsistency), **rendezvous time**, and qualitative chatter/constraint-violation observations.
- Baselines: **LQR, LQI, LQT (LQR with tracking), each with Bryson's rule tuning** tuned by trial-and-error to give the best response; all four classical solutions plus PPO on the same plant/ICs/limits.
- Statistical treatment: **none** — single deterministic runs per control/IC; no seeds, CIs or significance tests.

**Comparison methodology (RL vs classical)**
- Fair practices they DO implement: (i) **same plant** (identical CW model) for all controllers; (ii) **same initial conditions**; (iii) **same control limits (±1 N) and same 0.5 m/s velocity constraint**; (iv) **same discretization ∆t = 1.0 s and zero-order hold** applied to the classical continuous controllers so they are compared at the RL's actual implementation rate; (v) **same metrics (∆V, rendezvous time)**; (vi) classical tuning by an explicit, documented rule (**Bryson's rule + trial-and-error**), and reward-function tuning documented too.
- Unfair-comparison risks: **the paper itself admits the RL agent was limited by training time** — "a better trained model may result in better maneuvering, but limited training time" caused chattering and a **velocity-limit violation reaching 0.6 m/s** (limit 0.5 m/s), which is an RL-safety failure they report honestly. No compute-budget parity is reported; no tuning-effort parity metric; only 4 test cases, so the ranking is fragile.
- Verdict as printed: the modern classical controllers (especially **LQT**) dominate RL on ∆V in the reported cases; RL is competitive but violates the velocity constraint in at least one case.

**Sim-to-hardware**
- None. No MIL/SIL/HIL, no target hardware (study is a software trade study).

**Key quantitative results**
- CW in-plane; n = 0.001027 rad/s; horizon 6117 s (2 orbits); ∆t = 1.0 s; m = 12 kg; ±1 N; 0.5 m/s limit.
- Cumulative ∆V per case (values from text; units printed as "N", table header "m/s"):
  - Case 1: LQR 3.306, LQI 2.747, LQT 0.633, **RL 3.774** (highest; RL also shows chatter).
  - Case 2: LQR 2.072, LQI 5.566 (highest), LQT 1.262, RL 4.763.
  - Case 3: LQR ≈1.626, LQI 1.539 (lowest classical), LQT 0.603, RL 4.053.
  - Case 4: LQR 3.907, LQI 4.971, LQT 1.423, **RL 6.276** (highest).
- Rendezvous times [s] as printed (16 values; OCR column mapping unreliable — do not re-cite a per-cell mapping without checking the original): 11226, 10996, 11308, 10186, 3760, 11195, 5404, 4904, 2993, 10373, 5862, 5331, 913, 10230, 1959, 2847.
- Safety: RL peak relative velocity **0.6 m/s vs 0.5 m/s limit** → constraint violation.

**Reusable for a 24U nanosat fault-tolerant thesis**
- The **fairness protocol is the most reusable artifact**: identical plant, identical ICs, identical control/state limits, discretize *all* continuous controllers at the RL control rate with ZOH, use a documented classical tuning rule (Bryson) and report the RL reward-tuning effort too — this is the template for our LQR baseline (same 6-DOF plant, same 5 Hz, same torque limits, same allocator).
- Also reusable: reporting **constraint violations and chatter** as first-class results (not hiding them), and evaluating an RL agent **trained on random ICs on fixed hand-picked cases** as a generalization test — directly applicable to our random-attitude/random-rate training vs fixed-case evaluation.

---

## Paper 3 — Reinforcement Learning-Based Satellite Attitude Stabilization Method for Non-Cooperative Target Capturing

**Simulator/environment**
- Simulator: **custom Python**, **TensorFlow** under **Anaconda 3** (stated). No MATLAB/Simulink/Basilisk/STK/Gazebo.
- Integrator: not stated explicitly; rigid-body Euler equations + quaternion kinematics integrated in the custom simulator.
- Control frequency / timestep: **not stated** (training is described in iterations, not seconds or Hz).
- Relative-motion model: none (attitude stabilization of the chaser after contact/capture; no translational dynamics).

**Dynamics fidelity**
- 6-DOF: **no** — **3-DOF attitude-only** rigid-body dynamics (`J ω̇ + ω × Jω = M`) with quaternion kinematics.
- Orbital/relative dynamics: none.
- Disturbances: modelled as **random disturbance torques**:
  - Disturbance `T_S = 1.0e-3 · r · [−1, 0, 1]^T` with `r` a uniform random scalar.
  - Burst/impulse disturbance `T_R = 1.0e-2 · [r_1, r_2, r_3]^T` with `r_i` uniform random (models the contact/capture impulse).
- Gravity gradient, drag/SRP, flexible appendages: not modelled / not stated.
- **Parametric uncertainty**: the inertia matrix is randomized each episode — `J = J_basis ⊙ (1 + perturbation)`, perturbation entries uniform. This is the *capture* modelling: an unknown/perturbed inertia stands in for a docked non-cooperative target. J basis is given explicitly in the paper (small satellite, mass **m = 5 kg**).
- CMG singularities: not applicable (no CMGs).

**Sensors & estimation**
- **Perfect state, no sensors modelled** — explicitly: since the sensor and the simulation are both "fixed" in the same computer, sensor data are taken as the true state; no measurement noise.
- Observation: **7-dim = [quaternion (4), angular velocity (3)]**.
- State uncertainty: **not modelled** — no POMDP, no belief state, no noise-augmented observations; only inertia (dynamics) uncertainty.

**Actuators**
- **Not modelled** — the action is the **control torque directly** (3-axis), applied to `J ω̇ + ω × Jω = M`. No RW/CMG/MTQ, no torque limits documented, no allocation, no saturation, no desaturation.
- Action space: **discretized** — DQN with **7 output nodes** (a discrete action set over torque/attitude commands rather than continuous).

**Faults or failure modes**
- No explicit actuator fault (no RW/CMG failure). The "failure-like" element is the **random inertia perturbation** per episode, i.e. parametric uncertainty after capture. No sensor fault, no stuck actuator.

**RL setup**
- Algorithm: **DQN** (deep Q-network), value-based, discrete actions.
- Library: **TensorFlow** (Anaconda 3 environment) — stated.
- Network: **two hidden layers with 1024 and 2048 nodes**; input **7 nodes**; output **7 nodes**.
- Key hyperparameters: **3000 iterations**, **experience pool (replay buffer) capacity 500**, **discount factor 0.99**, **initial network weight 0.01**, **minibatch SGD**.
- Parallel envs: not stated. Total training steps/episodes: iterations = 3000; convergence reported at **≈2000 iterations**. Wall-clock/hardware: not stated (CPU/GPU not given).

**Simulation workflow**
- No vectorization/parallel envs stated.
- Domain randomization: **yes, per-episode randomized inertia perturbation** (the capture-uncertainty model).
- Curriculum: not stated.
- Reward shaping: per-axis **Gaussian** shaping: `r = exp(−0.5 (ω_i − ω_0)²) / √(2π)` around the desired angular velocity — a smooth "closeness to target rate" reward, not a constraint/safety penalty. No explicit safety or constraint term.
- Termination: episode/iteration terminates when the **attitude angular-velocity deviation < 1e-6** (very tight convergence criterion) or at the iteration limit.

**Evaluation protocol**
- Initial conditions: randomized (random attitude/rate via the randomized setup); the number of evaluated episodes/Monte Carlo count is **not stated**.
- Metrics: convergence of angular velocity deviation; qualitative comparison of stabilization behaviour. No success rate, energy, or time statistics given.
- Baselines: **two classical controllers** — a **PD controller** and a **backstepping controller**.
- Statistical treatment: none (single trajectories/cases shown).

**Comparison methodology (RL vs classical)**
- Same plant, same ICs (attitude stabilization after capture), same reward-like objective.
- **Unfair-comparison risk (detected)**: the PD baseline is reported to **diverge** and the backstepping baseline to work **only under a constant control cycle**, while the RL agent is specifically built to handle the randomized inertia. The PD gains appear **not to be re-tuned** for the perturbed inertia — so the classical baseline is effectively a strawman under the uncertainty the RL agent was trained for. The paper does not report equal tuning effort or equal compute. This is the clearest fairness weakness of the four papers.

**Sim-to-hardware**
- None performed. **Future work explicitly plans a "semi-physical simulation platform with a 3D turntable and actuators"** — i.e. a HIL platform is proposed but not built. No MIL/SIL/HIL results.

**Key quantitative results**
- m = 5 kg; 7-dim observation; 7 discrete actions; 1024 + 2048 hidden nodes; 3000 iterations, replay 500, γ = 0.99, init weights 0.01, minibatch SGD; convergence ≈2000 iterations.
- Disturbances: 1.0e-3 magnitude random torque, 1.0e-2 burst impulse.
- Termination tolerance: angular-velocity deviation < 1e-6.
- Qualitative: RL stabilizes under randomized inertia; PD diverges; backstepping only with a fixed control cycle.

**Reusable for a 24U nanosat fault-tolerant thesis**
- The **per-episode randomized-inertia domain randomization** is a directly transferable stand-in for fault-induced/uncertain plant dynamics (though for us the true randomizer should be the **actuator fault**, not just inertia) — and the finding that **an un-retuned PD diverges while RL copes** is a caution: we must **re-tune LQR fairly for the fault case** before claiming RL superiority.
- The **Gaussian closeness reward** and a **tight convergence-based termination (<1e-6)** are cheap, reusable reward/termination patterns; the paper's lack of sensor/actuator modelling is exactly the gap our MIL→SIL→HIL roadmap fills.

---

## Paper 4 — Deep reinforcement learning spacecraft guidance with state uncertainty for autonomous shape reconstruction of uncooperative target

**Simulator/environment**
- Simulator: **custom, Python** (implied; no MATLAB/Simulink/Gazebo/Basilisk/STK named).
- Integrator: not stated (the paper says the relative equations are integrated; scheme/step not given).
- Control frequency: **guidance step ∆t = 1 s** (thruster/acceleration command); **picture steps ∆t_p = 10 s** (imaging).
- Episode horizon: not stated in seconds; episodes terminate on leaving the imaging region or on mission completion. Nominal mission time `t_100% = 1595 s` to full map.
- Relative-motion model: **linearized relative motion in the LVLH frame** using the **eccentric-orbit linearized relative motion (Inalhan) formulation** (an eccentric generalization of CW/Hill).

**Dynamics fidelity**
- Full 6-DOF: **yes for the chaser** — the state is 12-dim: relative position (3) + relative velocity (3) + **Euler angles (3) + angular rates (3)**, i.e. coupled translational and rotational relative dynamics.
- Orbital/relative dynamics: **yes** — linearized relative motion in LVLH (Inalhan eccentric formulation).
- Disturbances, drag/SRP, gravity gradient, flexible appendages: not stated / not modelled.
- No CMG, no RW, no singularities.

**Sensors & estimation**
- Sensors: the guidance uses **relative navigation** inputs; the imaging sensor is a **camera with FOV 10°**, requiring range 50 m ≤ d ≤ 500 m.
- Estimator: **not stated** — no EKF/UKF/MEKF is used; instead the paper **injects navigation errors** between the navigation and guidance blocks at each timestep. This is the paper's central contribution.
- **State uncertainty model (explicit POMDP framing)**:
  - The problem is formalized as a **POMDP**; the agent is an **RL "controller" mapping a belief/observation to an action** (the paper writes the policy as `a = π(b)` over a belief, i.e. a **belief-state policy**) — and the belief is realized as the **noisy state estimate** rather than a full probability distribution.
  - Noise is added **at every guidance timestep**, not only at the start.
  - **Relative position error: uniform in ±10 m**; **relative velocity error: uniform in ±0.1 m/s**; **angular position (attitude) error: Gaussian with σ = 2°**.
  - Noise-augmented observations: the noisy estimate is fed directly to the policy — i.e. **noise-augmented observations**, not an explicit belief/distribution.
  - Remedy studied: **retrain the policy in the noisy simulation** (train-with-noise), which the authors state is what makes the policy robust; they explicitly note the noisy input "becomes part of the training simulation".

**Actuators**
- **Single electric thruster / low-thrust propulsion** providing **3-D thrust acceleration**; thrust command is a **continuous 3-D acceleration** (bounded implicitly by the action-space scaling).
- Limits, RW/CMG/MTQ, allocation, desaturation, steering law: not stated / not applicable.
- Propellant: consumed and reported (see results).

**Faults or failure modes**
- No actuator fault modelled. However, a **"failure event" analysis** is run: one of the three thrust directions is **unavailable**, and the policy's degradation is measured. This is the closest analogue to a fault-tolerance test in the four papers.

**RL setup**
- Algorithm: **PPO**.
- Library: not stated.
- Networks: **actor MLP 12→256→256→3** (tanh), learning rate **1e-5**; **critic MLP 12→256→256→1**, learning rate **5e-5**.
- Key hyperparameters (beyond the two learning rates): not stated (γ, clip, epochs, batch size, entropy coefficient unspecified in the extraction-relevant text).
- Parallel envs / vectorization: not stated.
- Total training: **30,000 episodes (nominal training)**; **40,000 episodes for the noisy retraining**. Wall-clock and hardware: not stated.

**Simulation workflow**
- Domain randomization: **yes** — randomized initial conditions and randomized **relative geometry** (position/orientation w.r.t. the target) across episodes; and, for the robust policy, **randomized navigation noise injected during training** (train-with-noise).
- Curriculum: not stated.
- Reward shaping (three additive components):
  1. **Distance term** `r_d`: `−100` if the chaser is at/below the minimum standoff `d ≤ 50 m` or beyond `d ≥ 500 m`, else `+1` (keeps the agent inside the imaging shell; the ±100 penalty is the safety/constraint term).
  2. **Incidence-angle term** `r_e`: score **1 for 10° ≤ e ≤ 50°** (good illumination/imaging geometry), **linear ramp-down for 5° ≤ e ≤ 10°** and **50° ≤ e ≤ 60°**, and **0 otherwise** (the exact piecewise constants are OCR-degraded in the source; the shape — plateau 1 for 10–50°, ramps outside, zero beyond 60° — is reliable).
  3. **Mapping term** `r_m`: **+1** for any improvement in mapped fraction, **+100** when the map reaches 100%, else **0** — drives full coverage.
- Termination: episode ends when the chaser leaves the imaging region (d outside 50–500 m, or the visibility/incidence bounds fail) or when the mission/spatial coverage is complete; no step-limit truncation is stated.
- Mapping requirement: **N_p = 20 quality pictures per face**, with a **minimum of 3 per face** to count the face.

**Evaluation protocol**
- Monte Carlo: **5000 test episodes** per policy (a large, statistically meaningful test set — the strongest evaluation protocol of the four papers).
- Initial conditions: randomized geometry (same distribution as training, plus generalization tests on different target shapes and on the failure event).
- Metrics: **% of target surface reconstructed**, mission completion time (t_100%), propellant used, and mapping histograms over the 5000 episodes.
- Baselines: **no classical controller baseline** (no LQR/MPC comparison). The comparisons are: **nominal-trained policy vs noise-retrained policy**, and **nominal vs failure-event**.
- Statistical treatment: histogram-based distributions over 5000 episodes (distributional, not just means) — reasonable for an RL-only study.

**Comparison methodology (RL vs classical)**
- **No RL-vs-classical comparison is attempted** — the paper compares RL variants (with/without noise-aware training, with/without a failed thrust direction). So the fairness question is largely N/A; the honest and reusable element is the **controlled ablation**: same task, same network, same training budget, only the training-noise condition or the failure event changed, evaluated on the same 5000-episode protocol.
- Not applicable: no LQR/MPC baseline means no guarantee an RL policy was actually needed.

**Sim-to-hardware**
- None. No MIL/SIL/HIL. The study is purely software; the "uncertainty" is injected in simulation rather than tested on hardware.

**Key quantitative results**
- State 12-dim; action 3-D acceleration; actor 12-256-256-3 (lr 1e-5), critic 12-256-256-1 (lr 5e-5), tanh; **30,000 nominal episodes**, **40,000 noised retraining episodes**; ∆t = 1 s, ∆t_p = 10 s; FOV 10°, 50 m ≤ d ≤ 500 m; N_p = 20 pictures/face, min 3.
- **Nominal (noise-free) policy: 95% surface reconstruction.**
- **Noise-injected evaluation of the nominal policy** (5000 episodes): **all-noise 69.22%**, position-only 84.07%, velocity-only 87.58%, angles-only 81.71%.
- **Retraining with noise: 85%** — an improvement of **≈16 percentage points** over the 69.22% nominal-under-noise case.
- Robustness to a **different target shape** (parallelepiped) with the retrained policy: **≈90%**.
- **Failure-event** (one thrust direction lost): 88.46% (all directions available, reference), **86.01% (X), 89.37% (Y), 88.63% (Z)** — average loss ≈**7%**, worst on the x-axis.
- Reconstruction quality: **n% ≳ 60%** of episodes achieve a complete (100%) reconstruction (value printed as "≥ 60%"; treat as approximate).
- Mission: **t_100% = 1595 s**, propellant **4.56e-5 kg**.

**Reusable for a 24U nanosat fault-tolerant thesis**
- The **explicit POMDP framing with per-step noise injection between navigation and guidance** (uniform ±10 m / ±0.1 m/s, Gaussian σ = 2° attitude) and the **quantified benefit of train-with-noise (69.22% → 85%)** is the single most reusable result: it justifies both (a) modelling state uncertainty as noise-augmented observations in our 9-dim vector, and (b) **domain-randomizing sensor noise during PPO training** rather than only testing under noise.
- Also reusable: the **failure-event ablation protocol** (disable one axis, report the % loss) — this is exactly the shape of our RW-dead / RW-at-50% evaluation, and the **5000-episode Monte Carlo evaluation with histograms** is the statistical standard we should copy.

---

## Cross-cutting patterns

- **Simulators are all custom/self-written and none is a named aerospace framework.** Across the four papers (custom Python/TensorFlow, custom CW Python, attitude-only custom code, custom LVLH Python) there is **no Gazebo, Basilisk or STK** anywhere; consequently no paper has a shared, validated plant, no integrator/timestep is documented explicitly, and control rates vary widely (10 Hz, 1 Hz, unstated). Reproducibility of the *environment* is the weakest dimension across the set.
- **Fidelity is deliberately narrow.** Every paper covers only the DOF it needs: attitude-only (Papers 1, 3), in-plane 2-D relative translation (Paper 2), and coupled 12-state relative translation+rotation (Paper 4). Disturbances are simplified (sinusoids, uniform random torques); **drag/SRP, gravity gradient and flexible appendages are absent everywhere**, and only Paper 1 touches CMG singularities (via GSRI for the classical baseline).
- **Uncertainty is injected as noise, not estimated.** No paper runs an EKF/UKF/MEKF. Three of four use perfect state for training; Paper 4 is the only one to formalize a **POMDP** and inject per-step navigation noise (uniform ±10 m, ±0.1 m/s; Gaussian σ = 2°), and it is the only one to show that **retraining with noise is what buys robustness** (69% → 85%). Paper 1 adds Gaussian noise only in a separate robustness study; Paper 3 explicitly assumes noise-free sensing.
- **Training budgets and hardware are almost never reported, and comparisons are rarely compute-paired.** Papers 1, 2 report no steps/episodes at all; Paper 3 reports 3000 iterations (convergence ≈2000); only Paper 4 gives episode counts (30k/40k). None gives wall-clock or hardware, and **none reports vectorization or parallel envs** — so no paper can substantiate that an RL policy and a classical controller received comparable tuning/compute effort.
- **Evaluation is mostly qualitative; one paper sets the statistical standard.** Papers 1 and 3 show single trajectories/curves; Paper 2 tests 4 fixed cases single-shot (and admits the RL agent was undertrained, violating a 0.5 m/s limit at 0.6 m/s); Paper 4 is the outlier with **5000 Monte Carlo episodes and distributional histograms**, plus an explicit failure-event ablation.
- **Fault tolerance is diluted into "uncertainty" or "robustness."** No paper models an actuator failure in training. Robustness is achieved by parametric variation (Paper 1: changed inertia/CMG type/noise; Paper 3: randomized inertia per episode) or tested post hoc (Paper 4: one thrust direction disabled, ≈7% average map loss). The word "fault tolerant" is not operationalized anywhere in the set.

## How to compare RL vs classical fairly

Fairest practices found across the four papers, ranked by value to our thesis:

- **Same plant, same ICs, same limits, same metrics (Paper 2).** All controllers run on the identical CW model with identical initial conditions, identical ±1 N force limit, identical 0.5 m/s velocity constraint, and the same two metrics (∆V, rendezvous time). Adapt directly: LQR and PPO on the **same NumPy 6-DOF plant, same 5 Hz, same torque limit, same allocator**.
- **Discretize classical controllers at the RL's control rate, with the same zero-order hold (Paper 2).** Continuous LQR/LQI/LQT were sampled at ∆t = 1.0 s to match the RL agent's command interval. This removes the "RL is handicapped by 1 Hz" confound and is trivially applicable at our 5 Hz.
- **Use a documented, reproducible classical tuning rule plus documented RL reward tuning (Paper 2).** Bryson's rule for the classical family, and an explicit statement of how reward variants were tuned — tuning effort on both sides made legible.
- **Test generalization by training on random ICs and evaluating on fixed cases (Paper 2) and by changing the plant without retraining (Paper 1).** Both are cheap to replicate.
- **Report the classical controller's weakness honestly rather than engineering a strawman (Paper 1) and report RL's safety failures (Paper 2).** Paper 1 explicitly concludes its RL alone is inferior in steady state and *combines* RL with a conventional controller + GSRI steering; Paper 2 reports the RL velocity violation and attributes it to limited training. For us the equivalent is re-tuning LQR for the fault case before any RL-superiority claim (Paper 3's un-retuned, diverging PD is the counter-example to avoid).
- **Run a matched ablation with everything else fixed (Paper 4).** Same network, same task, same budget — only the training condition (with/without noise) or the failure event changes — evaluated on 5000 episodes with histograms. This is the pattern for our fault comparison: `PPO(healthy)`, `PPO(fault-aware training)`, `LQR(fault)` all on the same plant, same 5000-episode Monte Carlo protocol, same metrics.
- **Net recommendation for the thesis:** the four papers collectively supply a fairness checklist (same plant/ICs/limits/rate/metrics/tuning-effort/report-safety) but *none* of them executes a fully paired RL-vs-classical study with equal tuning and compute — so the thesis can claim a genuine methodological contribution by doing explicitly what they do only partially: **same 6-DOF plant, same 5 Hz ZOH rate, same torque limits and allocator for RL and LQR, LQR re-tuned per fault case, ≥ thousands of Monte Carlo episodes, and fault-tolerance reported as distributional success rate and pointing error.**
