"""Q-12 regression tests: configuration keys that were documented but unread,
and an estimator-ordering defect, both fixed in the housekeeping step.

These exist because a flag that "reads like physics and moves no number" is a
correctness smell (G9 class), and because priming an estimator before the state it
measures has been reset is a latent defect that only shows up at non-zero initial
wheel speed.
"""
from __future__ import annotations
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from satellite_adcs.config import load_config
from satellite_adcs.dynamics import SpacecraftDynamics
from satellite_adcs import friction_estimation as fe
from simulate import make_ic_bias, run_episode


def _cfg(initial_speed=None):
    ov = {"actuators": {"reaction_wheels": {}}}
    if initial_speed is not None:
        ov["actuators"]["reaction_wheels"]["initial_speed_rad_s"] = initial_speed
    return load_config(ov)


def test_initial_wheel_speed_defaults_to_rest():
    """The shipped config says 0.0, so the default path is unchanged."""
    cfg = _cfg()
    dyn = SpacecraftDynamics(cfg, np.random.default_rng(0))
    dyn.reset()
    assert np.allclose(dyn.omega_w, 0.0)


def test_initial_wheel_speed_is_honoured():
    """Q-12: this key was read by nothing, so the wheels always started at rest."""
    cfg = _cfg(initial_speed=7.5)
    assert float(cfg["actuators"]["reaction_wheels"]["initial_speed_rad_s"]) == 7.5
    dyn = SpacecraftDynamics(cfg, np.random.default_rng(0))
    dyn.reset()
    assert np.allclose(dyn.omega_w, 7.5), (
        "initial_speed_rad_s is documented in actuators.yaml and must reach the plant; "
        f"got omega_w={dyn.omega_w}"
    )
    # an explicit reset argument still wins
    dyn.reset(omega_w=np.array([1.0, 2.0, 3.0]))
    assert np.allclose(dyn.omega_w, [1.0, 2.0, 3.0])


def test_friction_estimator_is_primed_after_the_plant_is_reset(monkeypatch):
    """Q-12: `cons.prime()` used to run BEFORE `dyn.reset()`, so the first
    innovation was measured against a pre-reset wheel speed."""
    cfg = _cfg(initial_speed=7.5)
    seen = {}
    orig = fe.FrictionHealthEstimator.prime

    def spy(self, omega_w_meas):
        if "w" not in seen:
            seen["w"] = np.asarray(omega_w_meas, dtype=float).copy()
        return orig(self, omega_w_meas)

    monkeypatch.setattr(fe.FrictionHealthEstimator, "prime", spy)
    q0, w0, bias = make_ic_bias(0)
    run_episode(cfg, seed=0, T=6.0, ic=(q0, w0), gyro_bias=bias, conservative=True)

    assert "w" in seen, "the conservative arm must prime its estimator"
    assert np.allclose(seen["w"], 7.5), (
        "prime() must receive the POST-reset wheel speed; got "
        f"{seen['w']} instead of 7.5"
    )
