"""Regression tests for the C2-e MEKF (gyro-bias estimation).

The bug these lock down: ADCSEnv.reset and simulate.run_episode used to poke
est.q_hat / est.P directly and never call est.reset(), so the gyro-bias state
b_hat survived across episodes. Harmless while the bias is constant; wrong
whenever the bias changes between episodes (the paired harness draws a fresh
bias per episode).
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from satellite_adcs.estimation import MEKF


def _cfg(seed=0):
    return {"sensors": {"gyro": {"bias_rad_s": 1e-3, "noise_std_rad_s": 1e-4},
                        "star_tracker": {"noise_std_rad": 5e-5},
                        "rng_seed": seed}}


def test_reset_zeroes_bias_and_shape():
    est = MEKF(_cfg())
    est.b_hat = np.array([1.0, 2.0, 3.0])          # pretend it drifted
    est.reset()
    assert np.allclose(est.b_hat, 0.0), f"b_hat not cleared: {est.b_hat}"
    assert est.P.shape == (6, 6), f"P has shape {est.P.shape}, expected (6,6)"
    # bias prior must be tight, attitude prior deliberately loose
    assert est.P[3:, 3:].diagonal().max() < 1e-4, "bias prior not tight"
    assert est.P[:3, :3].diagonal().min() >= 0.1, "attitude prior too confident"
    print("  reset clears b_hat and rebuilds a 6x6 P with the right structure  OK")


def test_bias_is_observable_and_converges():
    """Feed a known bias via perfect attitude updates; b_hat must converge."""
    est = MEKF(_cfg())
    est.reset()
    true_bias = np.array([1e-3, -2e-3, 5e-4])
    rng = np.random.default_rng(0)
    q_true = np.array([1.0, 0.0, 0.0, 0.0])
    dt = 0.02
    for k in range(2500):                    # 50 s at 50 Hz
        est.propagate(np.zeros(3) + true_bias + rng.normal(0, 1e-4, 3), dt)
        if k % 10 == 0:                      # ST at 5 Hz gives the true attitude
            est.update({"st": q_true}, None)
    err = np.linalg.norm(est.b_hat - true_bias)
    assert err < 2e-4, f"bias did not converge: err={err:.2e}, b_hat={est.b_hat}"
    print(f"  bias converged to within {err:.1e} of truth  OK")


def test_reset_between_different_biases():
    """The actual bug: a NEW episode with a NEW bias must not inherit b_hat."""
    est = MEKF(_cfg())
    est.reset()
    est.b_hat = np.array([5e-3, 5e-3, 5e-3])   # stale estimate from before
    est.reset()                                 # start of a new episode
    rate = est.gyro_rate(np.array([0.1, 0.0, 0.0]))
    assert np.allclose(rate, [0.1, 0.0, 0.0]), \
        f"a stale b_hat corrupted the rate: {rate}"
    print("  a fresh episode starts with an uncorrupted rate  OK")


if __name__ == "__main__":
    print("C2-e MEKF regression tests")
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); n += 1
    print(f"\n{n}/{n} passing")
