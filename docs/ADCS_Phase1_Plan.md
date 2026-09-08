# ADCS Phase 1 Plan — Post-Release Nadir Acquisition & Fault-Tolerant Control

**Project:** Fault-Tolerant Attitude Control of Nanosatellites Using RL
**Phase 1 objective (revised):** *Autonomous post-release attitude recovery, detumbling,
nadir acquisition, and Earth-pointing stabilization from randomized initial conditions —
on a configuration-driven, high-fidelity simulator.*
**Phase 1 is NOT "train PPO first." It is: build a trustworthy simulator, validate a
classical controller on it, then put RL on top of the *same* simulator.**

---

## 1. Mission sequence (the real scenario)

Release from launch vehicle with arbitrary attitude + angular velocity → then:

```
RELEASE (random q0, random ω0)
   │
   ▼
DETUMBLING          MTQ (B-dot) → ‖ω‖ < threshold
   │
   ▼
EARTH ACQUISITION   point body Z toward nadir
   │
   ▼
NADIR / LVLH TRACK  hold nadir frame (q_des(t) from orbit)
   │
   ▼
FAULT → RECOVERY → RESUME TRACKING   (Phase 1B+)
```

Randomized release: `q0 ~ Uniform(SO(3))`, `ω0_i ~ U(-5, +5) deg/s` (configurable envelope).

---

## 2. Definitions (make "best precision / min time" rigorous)

### Nadir / LVLH reference frame (NOT a fixed attitude)
```
r = inertial position, v = inertial velocity
ẑ_d = -r/‖r‖                (nadir)
ĥ   = r × v
ŷ_d = -ĥ/‖ĥ‖                (orbit normal)
x̂_d = ŷ_d × ẑ_d             (along-track)
C_I^d = [ x̂_d  ŷ_d  ẑ_d ]  → desired quaternion q_des(t)
```
Target is time-varying (orbit-dependent), computed from the orbit state / GPS.

### Objective functional
```
J = w_e ∫θ_e² dt + w_ω ∫‖ω‖² dt + w_u ∫‖τ‖² dt + w_t·T
```
with hard constraints: `|τ_i| ≤ τ_max`, `|ω_RW,i| ≤ ω_RW,max`, `|m| ≤ m_max`,
and acceptable pointing error `θ_e < θ_max` (e.g. 0.1°).

### Settling time (explicit)
> Time after which pointing error stays < 0.1° AND ‖ω‖ stays < 0.01 deg/s for ≥ 30 s.

### Metrics (per controller, per scenario)
Detumble time · acquisition time · total settling time · RMS/max pointing error ·
‖ω‖ residual · max control torque · RW speed · MTQ effort · energy.

---

## 3. Software architecture (layered, config-driven)

```
satellite_adcs/
├── config/                # YAML: satellite, orbit, sensors, actuators, disturbances, sim
│   ├── satellite.yaml  orbit.yaml  sensors.yaml  actuators.yaml
│   ├── disturbances.yaml  simulation.yaml
│   └── profiles/        # nominal.yaml, fault_rw50.yaml, fault_rw0.yaml, randomized.yaml
├── dynamics/             # rigid_body, orbit, gravity, environment, disturbances
├── actuators/            # reaction_wheel, magnetorquer, actuator_faults
├── sensors/              # gyro, magnetometer, sun_sensor, star_tracker, sensor_faults
├── estimation/           # MEKF/EKF → estimated q̂, ω̂  (NOT perfect attitude)
├── guidance/             # nadir/LVLH reference
├── controllers/          # pid, lqr, smc, rl (PPO/SAC), (later mpc, adaptive)
├── faults/               # reaction_wheel, sensor, manager
├── environment/          # adcs_env.py (Gymnasium wrapper on the simulator)
├── evaluation/           # metrics.py, scenarios.py
└── training/             # train_ppo.py, train_sac.py
```

Design rule: **simulator is the single source of truth**; classical control AND RL run on
exactly the same simulator, so comparisons are apples-to-apples. Everything is
YAML-configurable → reproducible experiments (`simulate.py --config profiles/fault_rw50.yaml`).

### Actuators — 3 reaction wheels + 3 magnetorquers (physical)
- RW: axis, max_torque, max_speed, inertia. Command = torque.
- MTQ: torque = `m × B` → **no torque along B** (magnetic authority is constrained).
  RL does NOT command MTQ dipoles directly at first; it outputs a desired control torque,
  then a split **RW allocator + MTQ allocator** maps it to `τ_RW` and `m`.

### Sensors — star tracker, sun sensor, gyro, magnetometer
- Realistic measurement models (noise, bias): ω_meas = ω + b_g + n_g; B_meas = B + n_B; etc.
- **GPS / orbit propagator → orbit state → nadir reference** (GPS is navigation, not attitude).

### Estimation — MEKF/EKF between sensors and controller
```
Sensors → MEKF/EKF → estimated q̂, ω̂ → Controller
```
(Not: Sensors → RL directly.) This is far more defensible for a Control-Eng thesis.

---

## 4. Fault model (continuous, not boolean)

Reaction-wheel health `h ∈ [0,1]`:
```
τ_actual = h × τ_command
h=1.0 normal · 0.5 → 50% degradation (your fault) · 0.0 → complete failure
```
Fault types (RW): torque degradation, speed-limit scale, bias, saturation, stuck,
intermittent, complete failure.
Sensor faults: gyro bias / noise incr. / scale / dropout; magnetometer bias/noise/axis/dropout;
star-tracker bias / dropout / large noise.
Faults sit **between the ideal component and its physical model** (a Fault Manager), NOT
random edits of the observation vector.

---

## 5. Curriculum (makes RL tractable)

| Level | Content |
|---|---|
| 1 | random attitude + random ω, no faults, no disturbances |
| 2 | + environmental disturbances |
| 3 | RW degradation (e.g. 50%) |
| 4 | RW complete failure |
| 5 | sensor bias |
| 6 | sensor dropout |
| 7 | **unseen fault severity** (generalization) |
| 8 | multiple simultaneous faults |

---

## 6. Milestones

- **M0 — Simulator skeleton + config-driven init.** Config YAMLs load; satellite, orbit,
  inertia, initial state randomized; env runs a random rollout. *(≈ current codebase refactor)*
- **M1 — Nominal nadir acquisition (classical baseline).** LQR (then PID/SMC) + MEKF on
  the simulator; **1000 random initial conditions**; record success rate, settling time,
  RMS/max error, control effort. Disturbances OFF, faults OFF.
- **M2 — First fault experiment.** RW1 health = 0.5, then 0.0, then randomized h~U(0,1);
  same 1000 ICs; show MTQ compensating the underactuated axis (magnetic authority).
- **M3 — RL baselines.** PPO and SAC trained on the *same* env (level 1 → 3 → 4 → 5 → 6);
  compare vs LQR in the central table; unseen-severity generalization test.
- **M4 — (later) JEPA-MPC and AdaJEPA adaptive** — Baselines B and contribution.
- **M5 — SIL / HIL.**

### Central comparison table (target)
| Controller | Settling | RMS err | Max err | Energy | Fault recovery |
|---|---|---|---|---|---|

---

## 7. Open decisions (to confirm before coding)

1. **Simulator backend:** extend the current **bsk_rl/Basilisk** env (high fidelity, sensors
   not all present by default) **vs.** build a **custom lightweight Python ADCS simulator**
   (full control of RW/MTQ/sensor/fault models, faster, ideal for RL iterations, but
   re-verifies dynamics). *Recommend: custom simulator for the control/RL core (config-driven,
   per the external advice), keep Basilisk as the high-fidelity cross-check / HIL path.*
2. **Controller baseline first:** LQR (recommended) vs. PID vs. B-dot detumble only.
3. **Action space for RL:** desired torque (then RW+MTQ allocator) — recommended; later
   compare raw `[τ_RW1..3, m_x..z]`.
4. **Sensor set:** confirm star-tracker + sun-sensor + gyro + magnetometer (proposal listed
   GPS for orbit — GPS stays as navigation).
5. **Inertia/mass/actuator numbers:** use realistic CubeSat values (config defaults below).
6. **Estimator:** MEKF included in M1 (recommended) or perfect-state first (simpler, swap later).

### Default config values (initial)
- mass 6 kg; inertia diag ~ [0.10, 0.12, 0.08] kg·m²
- RW: 3 wheels, max_torque ~2 mN·m, max_speed ~6000 rpm, wheel inertia ~1e-4 kg·m²
- MTQ: 3 dipoles, max ~0.2 A·m²
- orbit: 500 km LEO, i=51.6°, e~0.001
- release ω ~ U(-5,+5) deg/s; q0 random on SO(3)

---

## 8. Risks / notes
- **Underactuated axis under RW failure:** remaining 2 RW give 2-axis authority; MTQ fills the
  third only along ⊥B — controller must exploit orbital variation of B. Genuinely nonlinear,
  time-varying → strong thesis material, but harder.
- Don't over-optimize "fast": a controller reaching nadir in 2 s via absurd torque is not
  better — the cost functional and hard constraints define "better."
- Proposal says "raw actuator torques" as the RL action; the architecture above uses desired
  torque + allocator (see Open Decision 3).
