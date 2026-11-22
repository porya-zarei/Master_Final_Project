# simulation/ — shared simulation core (MIL)

The single source of truth for the satellite environment used by **every** phase
(rl, world_models, adaptive, sil, hil). Keep environment changes here so all
baselines are evaluated on identical dynamics, observations, rewards and faults.

## Modules

| Path | Contents |
|---|---|
| `envs/adcs_env.py` | `ADCSSatellite` (bsk_rl/Basilisk), `make_env()`, `FaultToleranceWrapper` |
| `envs/eo_imaging_env.py` | Earth-observing imaging satellite (Nagano & Schaub style tasking): imaging + charge, power/battery, target opportunities |
| `envs/__init__.py` | re-exports for `from simulation.envs import ...` |
| `dynamics/` | satellite dyn/fsw model selection + physical parameters |
| `faults/` | fault model catalog (RW lock, sensor bias, dropout, …) |
| `scenarios/` | mission scenarios (nadir / sun / custom target attitude) |
| `configs/` | yaml configs (env kwargs, scenario, fault profile) |

## Earth-observing env (`envs/eo_imaging_env.py`)

Port of the tasking environment from *Nagano & Schaub, "Autonomous Task
Scheduling for Earth-Observing Satellites Tracking Moving Targets"
(AVS Lab, CU Boulder — bsk_rl paper)*, implemented on the installed
bsk_rl 1.3.0 API:

- **Obs (14-dim):** r_BN_N (norm 1e6), v_BN_N (norm 1e4), battery_charge_fraction,
  n_ahead_observe=3 × (opportunity_mid, target_angle), normalized time.
- **Actions (Discrete(4)):** image target 0/1/2 (`act.Image(n_ahead_image=3)`)
  or charge (`act.Charge`) — semi-Markov steps (up to `max_step_duration`).
- **Reward:** `UniqueImageReward` — new images of high-priority targets.
- **Scenario:** `UniformTargets(50)` with random priority; LEO at 7000 km, 45°.

Notes / deviations from the paper:
- The paper/guide code uses the **legacy bsk_rl API** (`gym.make("GeneralSatelliteTasking-v1")`,
  `sat_args=`, `obs_type=`, `action_type=`). This file uses the 1.3.0 class-based
  API (`SatelliteTasking(...)`, `observation_spec`/`action_spec`, `sat_args={...}`).
- bsk_rl 1.3.0 `act.Image` has no `target_type`; opportunities are of type `target`.
- `UniqueImageReward` requires an access-aware satellite base → use
  `sats.ImagingSatellite` (not `sats.Satellite`).
- Basilisk `ClassicElements.a` is in **meters** (`a_km * 1e3`), angles in rad.
- The paper's **moving targets + uncertainty propagation** is its own extension
  to bsk_rl; `UniformTargets` here are static ground points. (Candidate thesis
  addition: moving-target model under the same scenario layer.)

Try it: `python simulation/envs/eo_imaging_env.py` (random-policy rollout:
watch battery charge/drain, imaging rewards appear with a trained policy).

## Current state / known simplifications (revisit once the loop runs)

1. **Action level** — `act.AttitudeSetpoint` commands a target attitude and
   Basilisk's built-in MRP steering law computes wheel torques. The proposal
   describes raw actuator torques; write to the RW motor-torque message once the
   setpoint-level version works.
2. **Target attitude** — currently fixed at zero (hold current inertial attitude).
   Swap in nadir / sun / randomized target once the mission frame is chosen.
3. **Sensor fault realism** — bias applied to the returned observation vector,
   not through a Basilisk sensor model (`simpleNav`). Graduate later.
4. **RW fault realism** — one wheel's commanded torque is zeroed; it does not yet
   route around the fault via `RWAvailabilityMsg`, so the other wheels don't
   automatically reallocate. Add once the basic loop is stable.
