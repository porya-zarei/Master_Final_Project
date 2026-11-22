"""C.1 regression tests: reaction-wheel speed sensing (tachometer), DEFAULT OFF.

The acceptance for C.1 is twofold:
  1. with `sensors.tachometer.enabled: false` (shipped) nothing changes at all, and
  2. when enabled, the sensor is a *sensor*: it clamps, quantises, adds noise and holds —
     in that physical order — so the estimator's sensitivity to wheel-speed error becomes
     measurable instead of assumed away.
"""
from __future__ import annotations
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from satellite_adcs.config import load_config
from satellite_adcs.wheel_sensor import TachometerModel, make_wheel_sensor
from satellite_adcs.friction_estimation import FrictionHealthEstimator
from simulate import make_ic_bias, run_episode


def test_disabled_by_default_so_the_plant_gets_exact_speed():
    cfg = load_config()
    assert cfg["sensors"]["tachometer"]["enabled"] is False
    assert make_wheel_sensor(cfg) is None


def test_enabling_builds_a_model_with_the_config_numbers():
    cfg = load_config({"sensors": {"tachometer": {"enabled": True}}})
    m = make_wheel_sensor(cfg)
    assert m is not None
    assert m.noise_std == pytest.approx(0.05)
    assert m.quant == pytest.approx(5e-3)
    assert m.max_speed == pytest.approx(628.3)     # null -> actuator full scale


def test_full_scale_clamp_comes_before_quantisation_and_noise():
    m = TachometerModel(noise_std=0.0, quant=0.0, max_speed=600.0)
    out = m.sample(np.array([1e6, -1e6, 0.0]))
    assert out[0] == 600.0 and out[1] == -600.0


def test_quantisation_puts_the_reading_on_the_encoder_grid():
    m = TachometerModel(noise_std=0.0, quant=0.01, max_speed=1e3)
    out = m.sample(np.array([1.234, -0.017, 0.0]))
    assert np.allclose(out / 0.01, np.round(out / 0.01))
    assert out[0] == pytest.approx(1.23)


def test_noise_has_the_configured_scale_and_is_reproducible():
    a = TachometerModel(noise_std=0.05, quant=0.0, max_speed=1e3,
                        rng=np.random.default_rng(7))
    b = TachometerModel(noise_std=0.05, quant=0.0, max_speed=1e3,
                        rng=np.random.default_rng(7))
    x = np.zeros(3)
    sa = np.array([a.sample(x)[0] for _ in range(4000)])
    sb = np.array([b.sample(x)[0] for _ in range(4000)])
    assert np.array_equal(sa, sb), "same seed must give the same stream"
    assert sa.std() == pytest.approx(0.05, rel=0.1)


def test_zero_order_hold_updates_only_at_the_sample_instant():
    # sample every 5 control steps
    m = TachometerModel(noise_std=0.0, quant=0.0, sample_period_s=1.0, dt_s=0.2,
                        max_speed=1e3)
    assert m.hold == 5
    vals = [m(np.array([float(k), 0.0, 0.0]))[0] for k in range(12)]
    # updates at k = 0, 5, 10 and holds in between
    assert vals[0] == 0.0 and vals[1] == 0.0 and vals[4] == 0.0
    assert vals[5] == 5.0
    assert vals[6] == 5.0 and vals[9] == 5.0
    assert vals[10] == 10.0


def test_reset_clears_the_hold():
    m = TachometerModel(noise_std=0.0, quant=0.0, sample_period_s=1.0, dt_s=0.2)
    m(np.array([3.0, 0.0, 0.0]))
    m(np.array([9.0, 0.0, 0.0]))          # held, not sampled
    m.reset()
    assert m(np.array([7.0, 0.0, 0.0]))[0] == pytest.approx(7.0)


def test_enabling_the_tachometer_moves_the_estimator():
    """The path must be live: identical episode, sensor on vs off, different h_hat."""
    cfg = load_config({"actuators": {"reaction_wheels":
                                     {"friction_coulomb_Nm": 2e-4}}})
    q0, w0, bias = make_ic_bias(0)
    kw = dict(seed=0, T=40.0, ic=(q0, w0), gyro_bias=bias, record=True,
              health_source="hat")   # the wheel-health estimator only exists in this mode;
    #                                  the default "true" path records h_hat = 0 by design
    off = run_episode(cfg, wheel_sensor=None, **kw)
    m = TachometerModel(noise_std=0.05, quant=5e-3, sample_period_s=0.2, dt_s=0.2,
                        rng=np.random.default_rng(0))
    on = run_episode(cfg, wheel_sensor=m, **kw)
    # h_hat is a recorded series (record=True), not a top-level scalar
    h_off = np.asarray(off["rec"]["h_hat"])[-1]
    h_on = np.asarray(on["rec"]["h_hat"])[-1]
    assert not np.allclose(h_off, h_on), "sensor had no effect -- the path is dead"


def test_the_measurement_noise_is_the_same_order_as_the_friction_signal():
    """C.1's quantitative point, asserted so it cannot be forgotten or overstated.

    The RLS regressand is J_w*d(omega_w)/dt, so a sample error becomes J_w*err/dt of apparent
    torque before it ever reaches the estimator. MEASURED at this plant's numbers with the
    CONTROL period (the estimator's actual time base -- an earlier estimate of mine used the
    integrator step and was wrong by 2x):

        err = 0.05*sqrt(2) = 70.7 mrad/s
        J_w*err/dt_ctrl = 2e-4 * 0.0707 / 0.2 = 7.1e-5 N*m

    i.e. ~35 % of the 2e-4 N*m Coulomb friction the estimator must resolve -- the same order
    of magnitude, so it cannot be dismissed, but not the dominant term either. Handing the
    estimator the plant's exact omega_w remains the single most favourable assumption in the
    fault-awareness chain; this test pins how favourable.
    """
    # friction_coulomb_Nm is an OPTIONAL key: the plant reads it with .get(..., 0.0) and
    # scenarios inject it. Read it back from a config that actually carries it.
    cfg = load_config({"actuators": {"reaction_wheels":
                                     {"friction_coulomb_Nm": 2e-4}}})
    J_w = float(cfg["actuators"]["reaction_wheels"]["inertia_kgm2"])
    dt_ctrl = 1.0 / float(cfg["simulation"]["control_hz"])
    spec = cfg["sensors"]["tachometer"]
    err = float(spec["noise_std_rad_s"]) * np.sqrt(2.0)     # difference of two samples
    apparent = J_w * err / dt_ctrl
    friction = float(cfg["actuators"]["reaction_wheels"]["friction_coulomb_Nm"])
    ratio = apparent / friction
    assert 0.2 < ratio < 2.0, (f"apparent {apparent:.2e} N*m is {ratio:.2f}x the friction "
                               f"{friction:.2e} N*m -- same order, so it must not be ignored")
