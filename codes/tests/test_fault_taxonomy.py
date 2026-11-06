"""D.3 regression tests: fault taxonomy — every family behind a flag, all default OFF.

Acceptance for this step (MASTER_ROADMAP D.3): each family has a regression test, and
with the flags off every historical number reproduces BIT-IDENTICALLY. The last test in
this file is the bit-identity acceptance check.

The locked-vs-dead distinction is the one that matters physically and is the one a naive
`h = 0` implementation gets wrong: a DEAD wheel free-spins under bearing friction and
still reacts on the structure, a LOCKED wheel does neither.
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
from satellite_adcs.sensors import SensorSuite
from satellite_adcs.fault_taxonomy import (WheelFault, WheelFaultSchedule, SensorFaults,
                                           DEAD, LOCKED, RAMP, INTERMITTENT)
from simulate import make_ic_bias, run_episode

COUL = 2.0e-4


def _dyn(coulomb=COUL, seed=0):
    cfg = load_config({"actuators": {"reaction_wheels":
                                     {"friction_coulomb_Nm": float(coulomb)}}})
    return cfg, SpacecraftDynamics(cfg, np.random.default_rng(seed))


def _spin(dyn, n=10, dt=0.1):
    for _ in range(n):
        dyn.step(dt, np.zeros(3), np.zeros(3))
    return dyn


# --------------------------------------------------------------------- schedule shape
def test_ramp_is_linear_and_clipped_at_the_floor():
    s = WheelFaultSchedule([WheelFault(1, RAMP, t0=10.0, rate=0.02, floor=0.4)])
    assert s.health(9.999)[1] == 1.0                 # not yet
    assert s.health(10.0)[1] == pytest.approx(1.0)   # onset
    assert s.health(20.0)[1] == pytest.approx(0.8)   # 10 s * 0.02
    assert s.health(60.0)[1] == pytest.approx(0.4)   # floor reached, not below
    assert s.health(600.0)[1] == pytest.approx(0.4)


def test_intermittent_toggles_with_period_and_duty():
    s = WheelFaultSchedule([WheelFault(0, INTERMITTENT, t0=0.0, period=10.0,
                                       duty=0.3, depth=0.2)])
    assert s.health(0.0)[0] == pytest.approx(0.2)    # inside the degraded window
    assert s.health(2.9)[0] == pytest.approx(0.2)
    assert s.health(3.1)[0] == pytest.approx(1.0)    # recovered
    assert s.health(10.1)[0] == pytest.approx(0.2)   # next period
    assert s.health(13.5)[0] == pytest.approx(1.0)


def test_schedule_only_touches_its_own_wheel():
    s = WheelFaultSchedule([WheelFault(2, DEAD)])
    h = s.health(1.0)
    assert h[0] == 1.0 and h[1] == 1.0 and h[2] == 0.0


def test_invalid_inputs_are_rejected():
    with pytest.raises(ValueError):
        WheelFault(0, "exploded")
    with pytest.raises(ValueError):
        WheelFault(0, INTERMITTENT, depth=2.0)
    with pytest.raises(ValueError):
        WheelFaultSchedule([WheelFault(7, DEAD)], n_rw=3)


# ---------------------------------------------------- dead vs locked (the physical split)
def test_dead_wheel_spins_under_friction_and_reacts_on_the_body():
    cfg, dyn = _dyn()
    dyn.reset(q=[1.0, 0.0, 0.0, 0.0], omega=[0.0, 0.0, 0.0],
              omega_w=[10.0, 10.0, 10.0])
    dyn.set_wheel_faults(WheelFaultSchedule([WheelFault(0, DEAD)]))
    _spin(dyn)
    assert abs(dyn.omega_w[0] - 10.0) > 1e-3, "a dead wheel still accelerates under friction"
    assert np.linalg.norm(dyn.omega) > 0.0, "and its bearing torque still reaches the body"


def test_locked_wheel_neither_rotates_nor_transmits():
    cfg, dyn = _dyn()
    dyn.reset(q=[1.0, 0.0, 0.0, 0.0], omega=[0.0, 0.0, 0.0],
              omega_w=[10.0, 10.0, 10.0])
    dyn.set_wheel_faults(WheelFaultSchedule([WheelFault(0, LOCKED)]))
    _spin(dyn)
    assert dyn.omega_w[0] == 10.0, "a jammed wheel cannot rotate at all"
    # wheels 1 and 2 are healthy, so the body may still move; wheel 0 contributes nothing
    assert dyn.rw_lock[0] and not dyn.rw_lock[1]


def test_all_wheels_locked_gives_no_wheel_reaction_on_the_body():
    cfg, dyn = _dyn()
    dyn.reset(q=[1.0, 0.0, 0.0, 0.0], omega=[0.0, 0.0, 0.0],
              omega_w=[10.0, 10.0, 10.0])
    w0 = dyn.omega_w.copy()
    dyn.set_wheel_faults(WheelFaultSchedule([WheelFault(i, LOCKED) for i in range(3)]))
    _spin(dyn, n=20)
    assert np.array_equal(dyn.omega_w, w0), "no wheel rotates"
    # The body must NOT be exactly still: gravity gradient is a real torque. What must
    # vanish is the WHEEL contribution -- 9 orders below the ~1e-2 rad/s a healthy
    # bearing would have produced over 2 s at omega_w = 10 rad/s.
    assert np.linalg.norm(dyn.omega) < 1e-7, f"body moved {np.linalg.norm(dyn.omega):.2e}"


def test_locked_wheel_ignores_a_command():
    cfg, dyn = _dyn(coulomb=0.0)
    dyn.reset(q=[1.0, 0.0, 0.0, 0.0], omega=[0.0, 0.0, 0.0], omega_w=[0.0, 0.0, 0.0])
    dyn.set_wheel_faults(WheelFaultSchedule([WheelFault(1, LOCKED)]))
    for _ in range(10):
        # +tau on the HEALTHY wheel 0, and a command on the LOCKED wheel 1 that must be
        # absorbed (the jam carries it internally, so the body sees nothing from it)
        dyn.step(0.1, np.array([0.01, 0.01, 0.0]), np.zeros(3))
    assert dyn.omega_w[1] == 0.0, "the jammed wheel must not rotate"
    # sign: J_w*dw/dt = -tau_eff + tau_f, so a POSITIVE command drives the wheel negative
    assert dyn.omega_w[0] < 0.0, "the healthy wheel must still accelerate"


# ------------------------------------------------------------------------- sensor faults
def test_gyro_bias_step_appears_only_after_onset():
    cfg = load_config({"sensors": {"gyro": {"noise_std_rad_s": 0.0}}})
    cfg, _ = cfg, None
    dyn = SpacecraftDynamics(cfg, np.random.default_rng(0))
    dyn.reset(q=[1.0, 0.0, 0.0, 0.0], omega=[0.2, 0.0, 0.0], omega_w=[0.0, 0.0, 0.0])
    sens = SensorSuite(cfg, np.random.default_rng(0))
    sens.set_bias(np.zeros(3))
    sens.set_faults(SensorFaults(bias_step_at=0.5, bias_step_delta=(1e-3, 0.0, 0.0)))

    dyn.t = 0.4
    before = sens.measure(dyn)["gyro"]
    dyn.t = 0.6
    after = sens.measure(dyn)["gyro"]
    assert before[0] == pytest.approx(0.2)
    assert after[0] == pytest.approx(0.2 + 1e-3)
    assert after[1] == pytest.approx(before[1])


def test_star_tracker_dropout_removes_the_channel():
    cfg = load_config()
    dyn = SpacecraftDynamics(cfg, np.random.default_rng(0))
    dyn.reset(q=[1.0, 0.0, 0.0, 0.0], omega=[0.0, 0.0, 0.0], omega_w=[0.0, 0.0, 0.0])
    sens = SensorSuite(cfg, np.random.default_rng(0))
    sens.set_faults(SensorFaults(st_dropouts=((0.2, 0.4),)))

    dyn.t = 0.1
    assert "st" in sens.measure(dyn)
    dyn.t = 0.3
    assert "st" not in sens.measure(dyn), "dropout must be ABSENT, not noisy"
    dyn.t = 0.5
    assert "st" in sens.measure(dyn)


# ------------------------------------------------- flags-off bit-identity (the acceptance)
def test_empty_schedule_is_a_no_op_on_the_plant():
    cfg, a = _dyn()
    _, b = _dyn()
    a.reset(q=[1.0, 0.0, 0.0, 0.0], omega=[0.01, 0.0, 0.0], omega_w=[1.0, 2.0, 3.0])
    b.reset(q=[1.0, 0.0, 0.0, 0.0], omega=[0.01, 0.0, 0.0], omega_w=[1.0, 2.0, 3.0])
    b.set_wheel_faults(WheelFaultSchedule([]))       # flag ON but empty
    for _ in range(20):
        tau = np.array([1e-3, -2e-3, 5e-4])
        a.step(0.1, tau, np.zeros(3))
        b.step(0.1, tau, np.zeros(3))
    for name in ("q", "omega", "omega_w", "r", "v"):
        assert np.array_equal(getattr(a, name), getattr(b, name)), f"{name} moved"


def test_end_to_end_flags_off_reproduces_bit_identically():
    """The acceptance criterion: an episode with the taxonomy attached but empty must be
    identical to an episode with the taxonomy absent, to the last bit."""
    cfg = load_config()
    q0, w0, bias = make_ic_bias(0)
    ref = run_episode(cfg, seed=0, T=60.0, ic=(q0, w0), gyro_bias=bias)
    got = run_episode(cfg, seed=0, T=60.0, ic=(q0, w0), gyro_bias=bias,
                      wheel_faults=WheelFaultSchedule([]),
                      sensor_faults=SensorFaults())
    assert np.array_equal(ref["pe"], got["pe"]), "pointing-error series moved"
    assert np.array_equal(ref["ow"], got["ow"])
    assert np.array_equal(ref["dyn"].q, got["dyn"].q)


def test_static_and_scheduled_faults_cannot_be_combined():
    cfg = load_config()
    q0, w0, bias = make_ic_bias(0)
    with pytest.raises(ValueError):
        run_episode(cfg, seed=0, T=2.0, rw_health=[0.5, 1, 1], ic=(q0, w0),
                    gyro_bias=bias,
                    wheel_faults=WheelFaultSchedule([WheelFault(0, DEAD)]))
