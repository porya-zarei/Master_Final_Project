"""
Minimal fault-tolerant attitude-control RL environment built on bsk_rl / Basilisk.

Verified against bsk-rl==1.3.0 / bsk==2.10.2 (installed via `pip install bsk-rl`).

CONFIRMED BY ACTUALLY RUNNING IN A SANDBOX:
  - The package installs cleanly with a single `pip install bsk-rl`.
  - The satellite/dyn/fsw class wiring below constructs without error.
  - `sigma_BN`, `omega_BN_B` are real dynamics-model properties (read from source).
  - `act.AttitudeSetpoint` is a real continuous Box(3) action.
  - The default reaction wheel configuration is a 3-wheel "triad".
  - `simulator.createNewEvent(..., conditionFunction=..., actionFunction=...)`
    is the real, working pattern for scheduling fault events (confirmed by
    reading bsk_rl's own internal usage, not just the docs).
  - `messaging.ArrayMotorTorqueMsgPayload` has a field called `motorTorque`.

NOT YET VERIFIED END TO END: a full simulated rollout. Basilisk's orbital
propagator needs to download a NASA ephemeris file (de430.bsp) on first use,
and the sandbox this was built in blocks that specific external domain. On a
normal machine with internet access this is a one-time download that gets
cached afterward. If something in the fault-injection logic below throws an
AttributeError once you can actually run it, it's most likely the exact
object path (e.g. `satellite.fsw.rwMotorTorque`) shifting between versions --
tell me the error and I'll help you fix it.
"""

import numpy as np
from Basilisk.architecture import bskLogging
from Basilisk.utilities import macros
import gymnasium as gym

from bsk_rl import SatelliteTasking, act, data, obs, sats, scene
from bsk_rl.sim import dyn, fsw

bskLogging.setDefaultLogLevel(bskLogging.BSK_WARNING)


class ADCSSatellite(sats.Satellite):
    """A satellite whose only job is attitude pointing (no imaging/scheduling)."""

    # sigma_BN: body attitude (MRP) relative to the inertial frame
    # omega_BN_B: body rate relative to inertial frame, in body-frame coords [rad/s]
    # wheel_speeds: current reaction wheel speeds [rad/s]
    observation_spec = [
        obs.SatProperties(
            dict(prop="sigma_BN"),
            dict(prop="omega_BN_B"),
            dict(prop="wheel_speeds"),
        ),
    ]

    # AttitudeSetpoint commands sigma_RN (reference attitude relative to
    # inertial), then Basilisk's built-in MRP steering + servo control law
    # computes the RW torques to track it. control_period is set close to
    # sim_rate so the RL agent effectively re-issues its command every step,
    # which is closer to continuous feedback control than a long maneuver.
    action_spec = [act.AttitudeSetpoint(control_period=1.0)]

    dyn_type = dyn.FullFeaturedDynModel
    fsw_type = fsw.SteeringFSWModel


def make_env(sim_rate=1.0, max_step_duration=1.0, time_limit=300.0):
    """Build the base (fault-free) Gymnasium environment."""
    sat = ADCSSatellite(name="ADCS-1")
    return SatelliteTasking(
        satellite=sat,
        scenario=scene.Scenario(),
        rewarder=data.NoReward(),  # reward is computed in the wrapper below
        sim_rate=sim_rate,
        max_step_duration=max_step_duration,
        time_limit=time_limit,
        log_level="WARNING",
    )


class FaultToleranceWrapper(gym.Wrapper):
    """
    Adds three things on top of the base environment:

    1. A real reward: negative pointing error to a fixed inertial target
       attitude, plus a rate penalty. `target_sigma` defaults to zero
       (hold current inertial attitude) -- swap in nadir/sun/custom-target
       pointing once you've picked a mission frame.
    2. Randomized reaction-wheel-lock faults: at a random time in the
       episode, one wheel's commanded torque is zeroed for the rest of the
       episode (a stuck/failed wheel).
    3. Randomized sensor-bias faults: after a random onset time, a fixed
       bias is added to the returned observation (a miscalibrated sensor).
       This is a simple observation-level bias for a first pass -- Basilisk
       has proper sensor noise models (e.g. simpleNav) you can graduate to
       once the basic loop is working.

    Each episode independently samples: no fault / RW lock / sensor bias.
    """

    def __init__(
        self,
        env,
        target_sigma=None,
        rate_weight=0.1,
        fault_time_range=(60.0, 200.0),
        sensor_bias_scale=0.05,
        seed=None,
    ):
        super().__init__(env)
        self.target_sigma = (
            np.zeros(3) if target_sigma is None else np.asarray(target_sigma, dtype=np.float64)
        )
        self.rate_weight = rate_weight
        self.fault_time_range = fault_time_range
        self.sensor_bias_scale = sensor_bias_scale
        self.rng = np.random.default_rng(seed)

        self._sensor_bias = np.zeros(6)
        self._fault_active = False
        self._fault_kind = "none"

    def reset(self, **kwargs):
        obs_, info = self.env.reset(**kwargs)
        sat = self.env.unwrapped.satellite

        self._fault_active = False
        self._sensor_bias[:] = 0.0
        self._fault_kind = self.rng.choice(["none", "rw_lock", "sensor_bias"])
        fault_time_ns = macros.sec2nano(self.rng.uniform(*self.fault_time_range))

        if self._fault_kind == "rw_lock":
            locked_wheel = int(self.rng.integers(0, 3))

            def condition(sim):
                return sim.TotalSim.CurrentNanos >= fault_time_ns

            def zero_wheel_torque(sim):
                self._fault_active = True
                msg = sat.fsw.rwMotorTorque.rwMotorTorqueOutMsg
                payload = msg.read()
                torques = list(payload.motorTorque)
                torques[locked_wheel] = 0.0
                payload.motorTorque = torques
                msg.write(payload, sim.TotalSim.CurrentNanos)

            sat.simulator.createNewEvent(
                f"rw_lock_{locked_wheel}",
                macros.sec2nano(sat.simulator.sim_rate),
                True,
                conditionFunction=condition,
                actionFunction=zero_wheel_torque,
                terminal=False,  # keep re-applying every step once triggered
            )

        elif self._fault_kind == "sensor_bias":
            bias = self.rng.normal(scale=self.sensor_bias_scale, size=6)

            def condition(sim):
                return sim.TotalSim.CurrentNanos >= fault_time_ns

            def apply_bias(sim):
                self._fault_active = True
                self._sensor_bias[:] = bias

            sat.simulator.createNewEvent(
                "sensor_bias_onset",
                macros.sec2nano(sat.simulator.sim_rate),
                True,
                conditionFunction=condition,
                actionFunction=apply_bias,
                terminal=True,  # fires once; bias then persists in Python state
            )

        return self._augment(obs_), info

    def step(self, action):
        obs_, _, terminated, truncated, info = self.env.step(action)
        obs_ = self._augment(obs_)
        sigma_err = obs_[0:3] - self.target_sigma
        omega = obs_[3:6]
        reward = -(np.sum(sigma_err**2) + self.rate_weight * np.sum(omega**2))
        info["fault_active"] = self._fault_active
        info["fault_kind"] = self._fault_kind
        return obs_, reward, terminated, truncated, info

    def _augment(self, obs_):
        obs_ = np.array(obs_, dtype=np.float64, copy=True)
        obs_[0:6] += self._sensor_bias
        return obs_
