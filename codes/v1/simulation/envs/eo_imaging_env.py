"""Earth-observing imaging satellite environment (BSK-RL 1.3.0 API).

Faithful port of the Nagano & Schaub (AVS Lab, CU Boulder) style tasking
environment described in "Autonomous Task Scheduling for Earth-Observing
Satellites Tracking Moving Targets":
  - LEO satellite imaging ground targets (tasking: image-target / charge)
  - Power tracking (battery_charge_fraction) and instrument power draw
  - Target opportunity observation (time until next imaging opportunity)
  - Semi-Markov steps: each action runs a maneuver of up to max_step_duration
  - Reward: unique new images weighted by target priority (UniqueImageReward)

NOTE on API: the original paper/guide code used the legacy bsk_rl API
(`gym.make("GeneralSatelliteTasking-v1", sat_args=..., obs_type=..., ...)`).
This file uses the installed bsk_rl==1.3.0 class-based API
(`SatelliteTasking(...)`, `observation_spec`/`action_spec`).

Run from `codes/`:
    python scripts/manual_eo_test.py
"""

import numpy as np

from Basilisk.utilities import orbitalMotion

from bsk_rl import SatelliteTasking, act, obs, sats, scene
from bsk_rl.data import UniqueImageReward
from bsk_rl.sim import dyn, fsw


def make_oe(a_km=7000.0, e=0.001, i_deg=45.0, raan_deg=0.0, argp_deg=0.0, f_deg=0.0):
    """Build Basilisk `ClassicElements` from km/deg parameters."""
    oe = orbitalMotion.ClassicElements()
    oe.a = a_km * 1e3     # [m] semi-major axis (Basilisk ClassicElements uses meters)
    oe.e = e
    oe.i = np.radians(i_deg)      # [rad]
    oe.Omega = np.radians(raan_deg)
    oe.omega = np.radians(argp_deg)
    oe.f = np.radians(f_deg)
    return oe


class ImagingSat(sats.ImagingSatellite):
    """LEO Earth-observing satellite: image targets or charge batteries."""

    dyn_type = dyn.ImagingDynModel
    fsw_type = fsw.ImagingFSWModel

    observation_spec = [
        obs.SatProperties(  # orbital state (normalized), plus battery level
            dict(prop="r_BN_N", norm=1e6),
            dict(prop="v_BN_N", norm=1e4),
            dict(prop="battery_charge_fraction"),
        ),
        obs.OpportunityProperties(  # upcoming imaging opportunities
            dict(prop="opportunity_mid", norm=300.0),  # time until opportunity midpoint
            dict(prop="target_angle", norm=0.05),      # pointing error to target [rad]
            n_ahead_observe=3,
            type="target",
        ),
        obs.Time(norm=5700.0),  # normalized elapsed mission time
    ]

    action_spec = [
        act.Image(n_ahead_image=3, max_duration=300.0),  # slew & image one of 3 tracked targets
        act.Charge(duration=300.0),                      # sun-point and recharge batteries
    ]


def make_eo_env(
    sim_rate: float = 0.5,
    max_step_duration: float = 300.0,
    time_limit: float = 95 * 60.0,
    n_targets: int = 50,
    oe=None,
    vizard_dir: str | None = None,
):
    """Build the Gymnasium (bsk_rl) Earth-observing environment.

    Args:
        sim_rate: physics step rate [s].
        max_step_duration: max sim time advanced per RL step [s] (semi-Markov).
        time_limit: episode length [s] (~one orbit).
        n_targets: number of ground targets on Earth.
        oe: Keplerian elements (a[km], e, inc[rad], RAAN[rad], argp[rad], f[rad]).
        vizard_dir: If given, writes Basilisk Vizard `.viz` files here so the
            scene (Earth, targets, satellite, wheels) can be viewed in the
            Vizard app. Pass ``vizard_settings={"vizard_rate": ...}`` to tune.
    """
    if oe is None:
        oe = make_oe()  # LEO: a=7000 km, e=0.001, i=45 deg

    sat = ImagingSat(
        name="EO-Sat",
        sat_args={
            "oe": oe,
            "imageAttErrorRequirement": 0.01,   # rad — attitude precision for imaging
            "imageRateErrorRequirement": 0.001,  # rad/s — rate stability for imaging
        },
    )

    scenario = scene.UniformTargets(
        n_targets=n_targets,
        priority_distribution=lambda: np.random.uniform(1.0, 10.0),
    )

    env = SatelliteTasking(
        satellite=sat,
        scenario=scenario,
        rewarder=UniqueImageReward(),
        sim_rate=sim_rate,
        max_step_duration=max_step_duration,
        time_limit=time_limit,
        log_level="WARNING",
        vizard_dir=vizard_dir,
    )
    return env


if __name__ == "__main__":
    env = make_eo_env()
    obs_, info = env.reset(seed=0)
    print("Observation space:", env.observation_space)
    print("Action space:     ", env.action_space)
    print("obs[:8] =", np.round(obs_[:8], 4), " ... battery in obs[6]")
    print()
    dyn = env.unwrapped.satellite.dynamics
    total = 0.0
    for i in range(20):
        a = env.action_space.sample()
        o, r, term, trunc, info = env.step(a)
        total += r
        try:
            batt = float(dyn.battery_charge_fraction)
        except Exception:
            batt = float("nan")
        print(f"step {i:2d}: action={a} (0-2=image,3=charge) "
              f"reward={r:8.3f} battery={batt:6.3f} "
              f"terminated={term} truncated={trunc}")
        if term or trunc:
            print("  episode finished")
            break
    print(f"\ntotal reward (random policy, {i+1} steps): {total:.2f}")
    env.close()