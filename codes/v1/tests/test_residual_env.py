"""Milestone D tests: the residual layer must reproduce the LQR at zero residual.

This is Experiment 1's foundation (the directive's "nominal non-degradation"
requirement): if a = 0 does not reproduce the nominal controller bit-for-bit,
the hybrid comparison is meaningless.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from satellite_adcs.environment.adcs_env import ADCSEnv
from satellite_adcs.environment.residual_env import ResidualADCSEnv
from simulate import make_ic_bias


def _mk(seed=0, ep_time=60.0):
    return ADCSEnv(fault_mode="none", episode_time=ep_time, control_hz=5.0, seed=seed)


def test_zero_residual_reproduces_lqr():
    """a=0 through the wrapper == the LQR acting directly, step for step."""
    q0, w0, bias = make_ic_bias(0)
    opts = {"q": q0, "omega": w0, "gyro_bias": bias}

    env_a = ResidualADCSEnv(_mk(0), alpha=0.2)
    env_b = _mk(0)
    obs_a, _ = env_a.reset(seed=0, options=opts)
    obs_b, _ = env_b.reset(seed=0, options=opts)

    for k in range(200):
        obs_a, ra, ta, tr_a, ia = env_a.step(np.zeros(3))
        a_lqr = np.clip((-env_a.K @ obs_b[:6]) / env_a.scale, -1.0, 1.0)
        obs_b, rb, tb, tr_b, _ = env_b.step(a_lqr)
        if k % 50 == 0 or ta or tr_a:
            d_att = np.linalg.norm(env_a.unwrapped.dyn.q - env_b.dyn.q)
            d_rate = np.linalg.norm(env_a.unwrapped.dyn.omega - env_b.dyn.omega)
            assert d_att < 1e-9 and d_rate < 1e-9, \
                f"diverged at step {k}: dq={d_att:.2e} dw={d_rate:.2e}"
        if ta or tr_a:
            break
    print("  residual=0 reproduces the LQR exactly (state match < 1e-9)  OK")


def test_observation_and_bounds():
    env = ResidualADCSEnv(_mk(0, ep_time=20.0), alpha=0.2)
    obs, _ = env.reset(seed=0)
    assert obs.shape == (15,), f"obs shape {obs.shape}, expected (15,)"
    _, r, term, trunc, info = env.step(np.ones(3))
    cap = env.alpha * env.unwrapped.rw_max_torque
    assert np.all(np.abs(info["combined_action"] - 0) <= 1.0 + 1e-9)
    print(f"  obs dim 15; residual authority alpha*rw_max = {cap:.2e} Nm  OK")


def test_residual_actually_does_something():
    """A non-zero residual must change the applied command."""
    q0, w0, bias = make_ic_bias(0)
    opts = {"q": q0, "omega": w0, "gyro_bias": bias}
    env = ResidualADCSEnv(_mk(0, ep_time=20.0), alpha=0.5)
    env.reset(seed=0, options=opts)
    _, _, _, _, i0 = env.step(np.zeros(3))
    env.reset(seed=0, options=opts)
    _, _, _, _, i1 = env.step(np.ones(3))
    d = np.linalg.norm(i1["combined_action"] - i0["combined_action"])
    assert d > 1e-6, "the residual had no effect on the combined command"
    print(f"  non-zero residual changes the command by {d:.3f} (normalised)  OK")


def test_gain_matches_the_classical_controller():
    """The wrapper's nominal LQR must BE the thesis LQR, not a re-tuned one.

    This is the invariant whose absence produced a 1e8x-wrong R and an evaluation
    that "proved" the LQR was unaffected by friction. Self-consistency is not
    enough: the gain must equal the one the classical baseline actually uses.
    """
    from satellite_adcs.controllers import ADCSController
    env = _mk(0)
    w = ResidualADCSEnv(env, alpha=0.2)
    d = env.unwrapped.dyn
    ctrl = ADCSController(env.cfg, d.J, d.mu, d.a, np.random.default_rng(0))
    assert np.allclose(w.K, ctrl.K), \
        "residual wrapper's LQR gain differs from the classical controller's"
    print("  wrapper gain == classical controller gain (same Q, R)  OK")


if __name__ == "__main__":
    print("Milestone D: residual RL wrapper tests")
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); n += 1
    print(f"\n{n}/{n} passing")
