# Project Brief: Fault-Tolerant Nanosatellite Attitude Control (M.Sc. Thesis)

> If you're using Claude Code, you can rename this file to `CLAUDE.md` at the
> project root and it will be loaded automatically at the start of every
> session. Otherwise, paste this whole file as your first message to whatever
> agent you're working with.

## Who / what this is

- Student: Pouria Zarei, M.Sc. Control Engineering, University of Tehran,
  Faculty of Electrical & Computer Engineering, College of Engineering.
- Advisor: Prof. Mohammad Javad Yazdanpanah (Full Professor).
- Proposal approved 1405/03/02 (~May 2026), applied/developmental scope
  (کاربردی + توسعه‌ای — not purely theoretical), day program.
- Approved thesis title (Persian): کنترل وضعیت تحمل‌پذیر خطا در نانوماهواره‌ها
  با استفاده از یادگیری تقویتی: از شبیه‌سازی تا پیاده‌سازی سخت‌افزار در حلقه
- Approved thesis title (English): Fault-Tolerant Attitude Control of
  Nanosatellites Using Reinforcement Learning: From Simulation to
  Hardware-in-the-Loop Implementation

## Core research question

Design an attitude determination and control system (ADCS) for CubeSats /
nanosatellites that stays stable and accurate when actuators (reaction
wheels) or sensors (magnetometer, sun sensor, gyro, GPS) fail or degrade —
without needing to have seen that exact failure mode during training.

## Approved baseline plan (what's already signed off, low risk)

1. **MIL** (Model-in-the-Loop): nonlinear satellite dynamics simulation.
   State space: quaternion/MRP attitude, angular velocity, tracking error.
   Action space: actuator torques (reaction wheels + magnetorquers). Reward
   balances pointing accuracy and energy. Faults (wheel saturation/lock,
   sensor bias/dropout) are randomly injected during training so a PPO/SAC
   agent (via `stable-baselines3`) learns a fault-tolerant policy.
2. **SIL** (Software-in-the-Loop): compress the trained policy (quantization
   / pruning) and validate inference-time feasibility on the target embedded
   profile (ARM / FPGA).
3. **HIL** (Hardware-in-the-Loop): deploy to real embedded hardware,
   interfaced with a physical or semi-physical testbed, with faults injected
   at the signal level.

This three-stage plan is a complete, defensible thesis on its own. Everything
below is an *addition*, not a replacement — flag it to the advisor before
sinking real weeks into it, framed as "a model-based RL variant added to the
fault-tolerance comparison."

## The extension: adaptive world models (AdaJEPA)

We found a very recent paper (AdaJEPA: An Adaptive Latent World Model; Wang,
Bounou, LeCun, Ren; NYU; arXiv:2606.32026, posted 2026-06-30) whose core idea
maps almost one-to-one onto this problem:

- Standard latent world models (JEPA-style: encoder + predictor operating in
  a compact latent space) are trained offline, then frozen, and paired with
  MPC for planning. They degrade badly under test-time distribution shift —
  including exactly the kind of shift the paper tests (changed mass,
  changed damping), which is structurally the same thing as an actuator
  fault changing a satellite's effective dynamics.
- AdaJEPA's fix: a **plan-execute-adapt-replan loop**. After executing an
  action and observing the real next state, take a single self-supervised
  gradient step (matching predicted vs. actual next latent state) on a
  *small subset* of parameters (e.g. last predictor block + last encoder
  layer) before replanning. No reward labels, no expert demonstrations, and
  in their experiments, added latency is negligible (0.01-0.03s per
  replanning step on an H200 GPU).
- Why this is a good fit here specifically: our attitude state is
  low-dimensional (quaternion + angular velocity + a few sensor channels),
  unlike the paper's pixel-observation tasks — so the encoder can be a small
  MLP instead of a ResNet/ViT, making the whole pipeline lighter than what
  the paper already shows is cheap. That's a real point in favor of running
  this on CubeSat-realistic ARM/FPGA hardware.
- Code reference: https://github.com/agentic-learning-ai-lab/adajepa

### The planned three-way comparison (core thesis result)

1. **Baseline C** — fault-randomized PPO/SAC policy (the originally-approved
   approach).
2. **Baseline B** — a frozen JEPA-style world model + MPC (no adaptation).
3. **The contribution** — an AdaJEPA-style *adaptive* world model + MPC,
   evaluated specifically on faults *not seen* during offline training
   (novel severities, novel combinations) — this is the key "unseen fault
   generalization" experiment.

Our own addition beyond the base paper: a validation/safety gate that
rejects an online adaptation step if it would increase predicted cost or
drift parameters too far — this matters much more on a spacecraft than in a
block-pushing simulation, and gives a defensible, novel piece of the thesis
that isn't just a reapplication of someone else's method. It also connects
naturally to classical adaptive control (self-tuning regulators, MRAC),
which is a good bridge for a controls-focused committee.

## Roadmap (rough durations, adjust to actual program timeline)

1. **Baseline RL** (~8 weeks) — fault-tolerant PPO/SAC in the MIL environment.
2. **World model** (~8 weeks) — offline JEPA-style model + frozen MPC baseline.
3. **Adaptation** (~10 weeks) — AdaJEPA-style test-time adaptation loop +
   unseen-fault generalization tests + safety gate + ablations.
4. **SIL / HIL** (~12 weeks) — compress, deploy to embedded hardware, test
   with signal-level fault injection.
5. Writing overlaps the tail of phase 4; a conference submission (IEEE
   Aerospace, IAC) alongside the thesis is realistic given how fresh this
   angle is.

We are at the very start of **Phase 1**.

## Codebase state right now

Stack: `bsk-rl` (built on Basilisk, installed via `pip install bsk-rl` — no
manual C++/SWIG build needed), `stable-baselines3`, `gymnasium`, PyTorch
(for later JEPA phases).

Files that exist so far (in this project folder):

- `adcs_env.py` — `ADCSSatellite` (a bsk_rl satellite doing pure attitude
  pointing, no imaging/scheduling), plus `FaultToleranceWrapper` (a
  Gymnasium wrapper adding a real reward function and randomized
  reaction-wheel-lock / sensor-bias fault injection).
- `train_ppo.py` — trains PPO via stable-baselines3 on the wrapped env.
- `README.md` — setup instructions and known simplifications.

**Verification status, be honest about this**: the satellite/dyn/fsw class
construction and Gymnasium interface wiring were confirmed to work by
actually running them. A full simulated rollout was *not* confirmed
end-to-end — Basilisk's orbital propagator needs to download a NASA
ephemeris file (`de430.bsp`) on first use, which failed only because of a
sandboxed network restriction in the environment this was built in. On a
normal machine with internet access this should be a one-time download. If
`FaultToleranceWrapper`'s fault-injection code throws an `AttributeError`,
the most likely culprit is the exact object path (e.g.
`satellite.fsw.rwMotorTorque`) shifting between bsk_rl versions — that part
was verified by reading source, not by executing it.

**Known simplifications to revisit once the basic loop runs** (see
`README.md` for full detail):

1. Action space is `act.AttitudeSetpoint` (commands a target attitude,
   Basilisk's built-in control law computes torques) rather than raw
   actuator torques as literally described in the approved proposal —
   revisit once the higher-level version works.
2. Target attitude is currently fixed at zero (hold current inertial
   attitude) — needs a real mission frame (nadir/sun/custom target).
3. Sensor-bias fault is applied directly to the observation vector, not
   through a real Basilisk sensor model (e.g. `simpleNav`).
4. Reaction-wheel fault zeroes one wheel's torque command but doesn't yet
   route around it via `RWAvailabilityMsg`, so the other wheels don't
   automatically reallocate control authority.

## Immediate next action

Run the manual test loop from `README.md` (reset + a few random steps,
printing reward and fault info) and fix whatever breaks. Do not move on to
PPO training until a manual rollout runs clean.

## How to help from here

- Debug and iterate on `adcs_env.py` until a full episode runs without error.
- Once stable, help refine the reward and pick a real target attitude.
- Only after Phase 1 (baseline RL) is solid, move to Phase 2 (offline JEPA
  world model) — don't jump ahead.
- Flag any point where a design choice meaningfully changes what the thesis
  claims (e.g. action-space level, safety-gate design) rather than silently
  picking one — these are exactly the kind of decisions worth a quick check
  before committing weeks of work to them.
