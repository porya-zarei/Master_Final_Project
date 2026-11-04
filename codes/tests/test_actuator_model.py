"""Milestone B tests: actuator nonlinearities are off by default and behave.

The critical guarantee is that ALL effects default to zero, so every historical
result remains bit-identical. Each effect is then verified individually.
"""
from __future__ import annotations
import sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from satellite_adcs.config import load_config
from satellite_adcs.dynamics import SpacecraftDynamics


def _dyn(**params):
    cfg = copy.deepcopy(load_config())
    cfg["actuators"]["reaction_wheels"].update(params)
    return SpacecraftDynamics(cfg, np.random.default_rng(0)), cfg


def test_defaults_are_ideal():
    """All-zero parameters must reproduce the ideal (historical) actuator."""
    d, _ = _dyn()
    assert d.rw_deadzone == 0 and d.rw_b_visc == 0 and d.rw_c_coul == 0
    assert d.rw_rate_limit == 0 and d.rw_quant == 0
    cmd = np.array([1e-5, 3e-4, -2e-3])
    out = d._rw_command_effective(cmd, 0.02)
    assert np.array_equal(out, cmd), f"ideal path altered: {out} vs {cmd}"
    print("  all effects default OFF; command passes through bit-identical  OK")


def test_deadzone():
    d, _ = _dyn(deadzone_Nm=1e-4)
    cmd = np.array([5e-5, 3e-4, -5e-5])
    out = d._rw_command_effective(cmd, 0.02)
    assert out[0] == 0.0 and out[2] == 0.0, f"deadzone not applied: {out}"
    assert out[1] == 3e-4, f"above-deadzone command altered: {out}"
    print("  deadzone: sub-breakaway commands deliver nothing  OK")


def test_rate_limit():
    d, _ = _dyn(rate_limit_Nm_per_s=0.05)          # 0.05 Nm/s
    dt = 0.02                                       # => 1e-3 Nm per step
    out = d._rw_command_effective(np.array([1e-2, 0, 0]), dt)
    assert np.isclose(out[0], 1e-3), f"rate limit wrong: {out[0]}"
    out2 = d._rw_command_effective(np.array([1e-2, 0, 0]), dt)
    assert np.isclose(out2[0], 2e-3), f"rate limit not accumulating: {out2[0]}"
    print("  rate limit: command slews at the specified Nm/s  OK")


def test_quantisation():
    d, _ = _dyn(quant_step_Nm=1e-4)
    out = d._rw_command_effective(np.array([1.7e-4, 0, 0]), 0.02)
    assert np.isclose(out[0], 2e-4), f"quantisation wrong: {out[0]}"
    print("  quantisation: command snapped to the DAC step  OK")


def test_friction_decays_wheel_and_conserves_momentum():
    """Bearing friction is internal: the wheel slows and total H is conserved."""
    d, _ = _dyn(friction_viscous_Nms=2e-6, friction_coulomb_Nm=2e-4)
    # 5 rad/s, not 300: at 300 rad/s the wheel stores ~0.6 Nms while the bearing
    # delivers 2e-4 Nm, so 10 s of simulation would barely change it. The regime
    # must be one where the effect is observable, or the test proves nothing.
    d.omega_w = np.array([5.0, -4.0, 2.0])
    d.omega = np.zeros(3)
    H0 = d.J @ d.omega + d.rw_J * d.omega_w
    for _ in range(2000):            # 40 s
        d.step(0.02, np.zeros(3), np.zeros(3))
    H1 = d.J @ d.omega + d.rw_J * d.omega_w
    assert np.linalg.norm(d.omega_w) < np.sqrt(25 + 16 + 4), \
        f"friction did not slow the wheels: {d.omega_w}"
    # NOTE: H measured in the BODY frame is not conserved -- it rotates with the
    # body (the -omega x H term), and gravity gradient acts here too. A vector
    # conservation check is therefore wrong; the magnitude is the invariant, and
    # we additionally check the physical signature: the body must react.
    drift = abs(np.linalg.norm(H1) - np.linalg.norm(H0)) / max(np.linalg.norm(H0), 1e-12)
    assert np.linalg.norm(d.omega) > 1e-6, "friction produced no reaction on the body"
    assert drift < 0.1, f"friction |H| drift too large: {drift:.2e}"
    print(f"  friction slows the wheel and spins the body; |H| drift {drift:.1e}  OK")


if __name__ == "__main__":
    print("Milestone B: actuator nonlinearity tests")
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); n += 1
    print(f"\n{n}/{n} passing")
