"""M1 (D-C2h-1a) tests: oracle vs estimated allocation.

The oracle path (health=None) must remain BIT-IDENTICAL to every earlier result,
because all prior evidence depends on it. The estimated path must invert the
BELIEF, not the truth, or the ablation is meaningless.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from satellite_adcs.config import load_config
from satellite_adcs.controllers import allocate_torque, ADCSController
from satellite_adcs.dynamics import SpacecraftDynamics
from satellite_adcs.environment.adcs_env import ADCSEnv


def _setup(health):
    cfg = load_config()
    rng = np.random.default_rng(0)
    dyn = SpacecraftDynamics(cfg, rng)
    dyn.set_rw_health(np.asarray(health, dtype=float))
    rw = cfg["actuators"]["reaction_wheels"]
    return cfg, dyn, rw["max_torque_Nm"], rw["inertia_kgm2"]


def test_oracle_path_unchanged():
    """health=None must reproduce the ground-truth inversion exactly."""
    cfg, dyn, tau_max, rw_J = _setup([1.0, 0.5, 0.8])
    tau = np.array([1e-3, 2e-3, -3e-3])
    mtq = cfg["actuators"]["magnetorquers"]["max_dipole_Am2"]
    a = allocate_torque(tau, dyn, tau_max, mtq, rw_J, health=None)
    b = allocate_torque(tau, dyn, tau_max, mtq, rw_J)          # legacy call
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1]), \
        "health=None is not bit-identical to the legacy call"
    # and it must equal a hand-computed truth inversion
    expect = np.clip(tau / np.array([1.0, 0.5, 0.8]), -tau_max, tau_max)
    assert np.allclose(a[0], expect), f"oracle inversion wrong: {a[0]} vs {expect}"
    print("  oracle path bit-identical to the legacy call  OK")


def test_estimate_is_used_not_truth():
    """A deliberately WRONG estimate must change the command."""
    cfg, dyn, tau_max, rw_J = _setup([1.0, 1.0, 1.0])         # truly healthy
    tau = np.array([1e-3, 1e-3, 1e-3])
    mtq = cfg["actuators"]["magnetorquers"]["max_dipole_Am2"]
    cmd_true, _ = allocate_torque(tau, dyn, tau_max, mtq, rw_J, health=None)
    cmd_hat, _ = allocate_torque(tau, dyn, tau_max, mtq, rw_J,
                                 health=np.array([1.0, 0.5, 1.0]))
    assert np.allclose(cmd_true, tau)
    assert np.allclose(cmd_hat[1], 2 * tau[1]), \
        f"estimate ignored: {cmd_hat} vs {tau}"
    assert np.allclose(cmd_hat[0], tau[0]), "unaffected wheel should be unchanged"
    print("  a wrong estimate changes the command (belief, not truth)  OK")


def test_env_default_is_oracle():
    env = ADCSEnv(fault_mode="none", episode_time=20.0, control_hz=5.0, seed=0)
    assert env.health_source == "true", f"default changed: {env.health_source}"
    env.reset(seed=0)
    assert env._last_tau_cmd.shape == (env.n_rw,)
    print("  env defaults to the oracle allocator  OK")


def test_env_hat_mode_runs_and_ignores_nothing():
    env = ADCSEnv(fault_mode="rw1_failed", episode_time=60.0, control_hz=5.0,
                  seed=0, health_source="hat")
    assert env.health_source == "hat"
    env.reset(seed=0)
    done = False
    n = 0
    while not done and n < 400:
        _, r, term, trunc, info = env.step(np.zeros(3))
        assert np.isfinite(r), "non-finite reward in hat mode"
        done = term or trunc
        n += 1
    h = np.asarray(env.health_est.h).ravel()
    assert h.shape == (3,) and np.all(np.isfinite(h)), f"bad h_hat: {h}"
    assert np.all((h >= 0.0) & (h <= 1.5)), f"h_hat implausible: {h}"
    print(f"  hat mode runs 60 s; h_hat={np.round(h,3)}  OK")


def test_controller_switch():
    cfg = load_config()
    rng = np.random.default_rng(0)
    dyn = SpacecraftDynamics(cfg, rng)          # supplies J, mu and a
    ctrl = ADCSController(cfg, dyn.J, dyn.mu, dyn.a, rng)
    assert ctrl.health_source == "true", "controller default changed"
    ctrl.health_source = "hat"
    ctrl.health_hat = np.array([1.0, 0.5, 1.0])
    print("  LQR controller exposes the oracle/estimate switch  OK")


if __name__ == "__main__":
    print("M1 oracle-vs-estimate allocation tests")
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); n += 1
    print(f"\n{n}/{n} passing")
