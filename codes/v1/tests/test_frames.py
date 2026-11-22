"""Frame-convention regression suite for the ADCS simulator.

These tests encode the DOCUMENTED semantics -- `C_BN` (inertial -> body, so
`v_B = C @ v_I`) -- and are checked against an independent implementation
(scipy `Rotation`) or a conservation law. They exist because a transposed
`quat_to_dcm` went unnoticed through Phases A-C and invalidated every number
in report-1/2/3 (see docs/PhaseC_to_F_Master_Plan.md 1.3, G14).

Run either way:
    cd codes && PYTHONPATH=. ./venv/Scripts/python.exe tests/test_frames.py
    cd codes && PYTHONPATH=. ./venv/Scripts/python.exe -m pytest tests/test_frames.py -q
"""
from __future__ import annotations

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from scipy.spatial.transform import Rotation

from satellite_adcs.config import load_config
from satellite_adcs.dynamics import SpacecraftDynamics
from satellite_adcs.guidance import NadirGuidance
from satellite_adcs.quaternion import dcm_to_quat, quat_to_dcm
import simulate

TOL = 1e-10


def _C_BN_scipy(q):
    """Independent inertial->body DCM: scipy's active matrix, transposed."""
    return Rotation.from_quat([q[1], q[2], q[3], q[0]]).as_matrix().T


def _C_NB_scipy(q):
    """Independent body->inertial DCM (scipy's active matrix).

    Needed for "where does the body +z point in inertial coords?" -- column 3 of
    C_NB. Using _C_BN_scipy for that question would compare the metric with
    ITSELF and pass no matter what (a mistake this suite originally made).
    """
    return Rotation.from_quat([q[1], q[2], q[3], q[0]]).as_matrix()


def _rand_q(rng):
    q = rng.normal(size=4)
    return q / np.linalg.norm(q)


def _lvlh_C_IL(r, v):
    rhat = r / np.linalg.norm(r)
    h = np.cross(r, v)
    yhat = -h / np.linalg.norm(h)
    zhat = -rhat
    xhat = np.cross(yhat, zhat)
    return np.column_stack([xhat, yhat, zhat / np.linalg.norm(zhat)]).T


# --------------------------------------------------------------------- T1/T2
def test_dcm_is_inertial_to_body():
    """quat_to_dcm(q) must be C_BN, matching scipy, for random q."""
    rng = np.random.default_rng(1)
    for _ in range(20):
        q = _rand_q(rng)
        C = quat_to_dcm(q)
        assert np.allclose(C, _C_BN_scipy(q), atol=TOL), "quat_to_dcm is not C_BN"
        v = rng.normal(size=3)
        assert np.allclose(C @ v, Rotation.from_quat(
            [q[1], q[2], q[3], q[0]]).inv().apply(v), atol=TOL), \
            "C @ v_I must give v expressed in the body frame"


def test_dcm_to_quat_is_the_inverse():
    rng = np.random.default_rng(2)
    for _ in range(20):
        q = _rand_q(rng)
        r = dcm_to_quat(quat_to_dcm(q))
        assert min(np.linalg.norm(r - q), np.linalg.norm(r + q)) < 1e-9, \
            "dcm_to_quat is not the inverse of quat_to_dcm"


# ---------------------------------------------------------------------- T3
def test_inertial_momentum_conserved_in_torque_free_spin():
    """The catch-all: any frame slip anywhere breaks this conservation law."""
    cfg = load_config()
    cfg["disturbances"]["gravity_gradient"] = False
    rng = np.random.default_rng(3)
    d = SpacecraftDynamics(cfg, rng)
    d.gravity_gradient = False
    d.reset(q=np.array([1.0, 0, 0, 0]), omega=np.array([0.3, -0.2, 0.5]))
    L0 = None
    for _ in range(2000):
        d.step(0.01, np.zeros(3), np.zeros(3))
        L = d.C.T @ (d.J @ d.omega)          # C_BN^T = C_NB
        L0 = L if L0 is None else L0
        drift = np.linalg.norm(L - L0) / np.linalg.norm(L0)
        assert drift < 1e-8, f"inertial momentum drifted {drift:.2e}"


# ---------------------------------------------------------------------- T4
def test_pointing_metric_equals_true_body_z_to_nadir():
    """The test that would have caught G14."""
    cfg = load_config()
    rng = np.random.default_rng(4)
    d = SpacecraftDynamics(cfg, rng)
    for _ in range(10):
        q = _rand_q(rng)
        d.reset(q=q, omega=np.array([0.02, -0.01, 0.03]))
        truth = np.degrees(np.arccos(np.clip(
            (_C_NB_scipy(d.q) @ np.array([0.0, 0.0, 1.0])) @ (-d.r / np.linalg.norm(d.r)),
            -1, 1)))
        assert abs(simulate.pointing_error_deg(d) - truth) < 1e-6, \
            f"metric {simulate.pointing_error_deg(d):.4f} != truth {truth:.4f}"


# ---------------------------------------------------------------------- T5
def test_guidance_reference_points_at_nadir():
    cfg = load_config()
    rng = np.random.default_rng(5)
    d = SpacecraftDynamics(cfg, rng)
    d.reset()
    q_ref, _ = NadirGuidance(d.mu, d.a).reference(d.r, d.v)
    # body +z in inertial = column 3 of C_NB -- use the INDEPENDENT matrix, not
    # quat_to_dcm (which is C_BN and is itself under test here).
    zb = _C_NB_scipy(q_ref) @ np.array([0.0, 0.0, 1.0])
    nadir = -d.r / np.linalg.norm(d.r)
    ang = np.degrees(np.arccos(np.clip(zb @ nadir, -1, 1)))
    assert ang < 1e-6, f"q_ref body+z is {ang:.4f} deg from nadir"


def test_guidance_rate_sign():
    """LVLH rotates about the orbit normal h_hat = -y_hat at +n, so in LVLH
    coordinates omega = [0, -n, 0]."""
    cfg = load_config()
    cfg["orbit"]["eccentricity"] = 0.0     # circular: instantaneous rate == n
    rng = np.random.default_rng(6)
    d = SpacecraftDynamics(cfg, rng)
    d.gravity_gradient = False
    d.reset()
    _, wr = NadirGuidance(d.mu, d.a).reference(d.r, d.v)
    n = np.sqrt(d.mu / d.a ** 3)
    # measure the frame rate numerically: c_dot = -omega x c for inertial-fixed c
    dt = 1e-3
    r0, v0 = d.r.copy(), d.v.copy()
    C0 = _lvlh_C_IL(r0, v0)
    C1 = _lvlh_C_IL(r0 + v0 * dt, v0)
    A, b = [], []
    for j in range(3):
        e = np.zeros(3); e[j] = 1.0
        c0, c1 = C0 @ e, C1 @ e
        A.append([[0, -c0[2], c0[1]], [c0[2], 0, -c0[0]], [-c0[1], c0[0], 0]])
        b.append((c1 - c0) / dt)
    om = np.linalg.lstsq(np.vstack(A), np.concatenate(b), rcond=None)[0]
    assert abs(om[1] - (-n)) < 1e-8, f"measured omega_y = {om[1]:.3e}, expected {-n:.3e}"
    assert abs(wr[1] - (-n)) < 1e-12, \
        f"guidance returns omega_ref = {wr[1]:.3e}, should be {-n:.3e}"


# ---------------------------------------------------------------------- T6
def test_gravity_gradient_uses_body_frame_nadir():
    cfg = load_config()
    rng = np.random.default_rng(7)
    d = SpacecraftDynamics(cfg, rng)
    d.reset(q=_rand_q(rng), omega=np.zeros(3))
    # nadir in body coords, from the INDEPENDENT matrix (not from d.C, which is
    # what is under test -- otherwise the assertion is vacuous).
    rhat_b = _C_BN_scipy(d.q) @ (d.r / np.linalg.norm(d.r))
    expect = 3.0 * d.mu / np.linalg.norm(d.r) ** 3 * np.cross(rhat_b, d.J @ rhat_b)
    got = d.disturbance_torque()
    assert np.allclose(got, expect, atol=1e-18), "gravity-gradient torque frame is wrong"


def test_magnetic_field_is_in_the_body_frame():
    """Recompute the tilted-dipole field independently and rotate with scipy."""
    cfg = load_config()
    rng = np.random.default_rng(8)
    d = SpacecraftDynamics(cfg, rng)
    d.reset(q=_rand_q(rng), omega=np.zeros(3))
    rn = np.linalg.norm(d.r)
    rhat = d.r / rn
    c, s = np.cos(d.mag_tilt), np.sin(d.mag_tilt)
    mhat = np.array([s, 0.0, c])
    B_I = 1e-7 * d.m_e / rn ** 3 * (3 * (mhat @ rhat) * rhat - mhat)
    assert np.allclose(d.B_body, _C_BN_scipy(d.q) @ B_I, atol=1e-14), \
        "B_body is not C_BN @ B_I"


# ------------------------------------------------------------------- T7/T8
def test_sun_sensor_frame():
    """sensors.py: sun_meas = C @ sun_inertial must be the body-frame sun."""
    cfg = load_config()
    cfg["sensors"]["sun_sensor"]["noise_std_rad"] = 0.0
    rng = np.random.default_rng(9)
    d = SpacecraftDynamics(cfg, rng)
    d.reset(q=_rand_q(rng), omega=np.zeros(3))
    from satellite_adcs.sensors import SensorSuite
    got = SensorSuite(cfg, rng).measure(d)["sun"]
    e = _C_BN_scipy(d.q) @ d.sun_inertial()
    assert np.allclose(got, e / np.linalg.norm(e), atol=1e-12), \
        "sun sensor is not measuring the body-frame sun vector"


def test_controller_error_frame_rotation():
    """controllers.py: C_e = quat_to_dcm(q_err) must map a REFERENCE-frame vector
    into the BODY frame (it is applied to omega_ref_lvlh)."""
    from satellite_adcs.quaternion import quat_error
    rng = np.random.default_rng(10)
    q_ref, q = _rand_q(rng), _rand_q(rng)
    q_err = quat_error(q, q_ref)
    v = rng.normal(size=3)
    indep = _C_BN_scipy(q) @ _C_NB_scipy(q_ref)      # C_{B<-I} C_{I<-ref}
    assert np.allclose(quat_to_dcm(q_err) @ v, indep @ v, atol=1e-10), \
        "the error-frame rotation does not map reference coords to body coords"


# ---------------------------------------------------------------- harness T9
def test_paired_harness_conditions():
    """Step 4: the RL path and the classical path must be able to share the SAME
    initial condition and gyro bias, or an RL-vs-LQR comparison is not paired."""
    cfg = load_config()
    from satellite_adcs.environment.adcs_env import ADCSEnv
    from simulate import make_ic_bias, run_episode

    # (a) the shared generator is deterministic and shaped correctly
    a1 = make_ic_bias(3, cfg)
    a2 = make_ic_bias(3, cfg)
    for x, y in zip(a1, a2):
        assert np.allclose(x, y), "make_ic_bias is not deterministic"
    q0, w0, b0 = a1
    assert abs(np.linalg.norm(q0) - 1.0) < 1e-12 and w0.shape == (3,) and b0.shape == (3,)

    # (b) the RL env honours an injected condition EXACTLY
    env = ADCSEnv(fault_mode="none", episode_time=5.0, control_hz=5.0, seed=0)
    env.reset(seed=3, options={"q": q0, "omega": w0, "gyro_bias": b0})
    assert np.allclose(env.dyn.q, q0, atol=1e-12), "env did not take the injected q0"
    assert np.allclose(env.dyn.omega, w0, atol=1e-12), "env did not take the injected omega0"
    assert np.allclose(env.sensors.gyro_bias, b0, atol=1e-15), "env did not take the bias"
    env.close()

    # (c) the classical path starts from the same injected attitude. Compare the
    # first pointing error with the value implied by q0 alone: one 0.2 s step of
    # wheel torque cannot move a 35 kg satellite more than a fraction of a degree,
    # whereas a DIFFERENT initial condition gives a wildly different angle.
    rng = np.random.default_rng(0)
    from satellite_adcs.dynamics import SpacecraftDynamics
    d = SpacecraftDynamics(cfg, rng)
    d.reset(q=q0, omega=w0)
    expect = np.degrees(np.arccos(np.clip(
        (_C_NB_scipy(d.q) @ np.array([0.0, 0.0, 1.0])) @ (-d.r / np.linalg.norm(d.r)),
        -1, 1)))
    res = run_episode(cfg, seed=3, T=0.2, ic=(q0, w0), gyro_bias=b0)
    assert abs(res["pe"][0] - expect) < 2.0, \
        f"run_episode ignored the injected IC (got {res['pe'][0]:.2f}, expected ~{expect:.2f})"


# ------------------------------------------------------------- baseline T10
def test_gain_scheduled_lqr_is_a_strict_generalisation():
    """h = 1 must reproduce the fixed baseline exactly; a lost axis must detune."""
    cfg = load_config()
    from satellite_adcs.controllers import design_lqr
    from satellite_adcs.gain_scheduled import scheduled_K, scheduled_R
    J = np.diag([cfg["satellite"]["inertia"][k]
                 for k in ("Jxx", "Jyy", "Jzz")])
    Q = np.diag([1.0, 1.0, 1.0, 0.3, 0.3, 0.3])
    R0 = np.eye(3) / cfg["actuators"]["reaction_wheels"]["max_torque_Nm"] ** 2

    K_healthy = scheduled_K(J, Q, R0, [1.0, 1.0, 1.0])
    assert np.allclose(K_healthy, design_lqr(J, Q, R0), atol=1e-12), \
        "scheduling must be a no-op when healthy"

    K_dead = scheduled_K(J, Q, R0, [0.0, 1.0, 1.0])
    ax = [np.linalg.norm(K_dead[:, i]) for i in range(3)]
    axh = [np.linalg.norm(K_healthy[:, i]) for i in range(3)]
    assert ax[0] < 0.5 * axh[0], f"lost axis not detuned ({ax[0]:.3g} vs {axh[0]:.3g})"
    # The Riccati solution couples the axes, so the healthy columns DO move a
    # little; what must hold is that the lost axis is attenuated FAR more than
    # the surviving ones (an earlier version of this test asserted they were
    # untouched, which is not true of an LQR gain).
    rel = [ax[i] / axh[i] for i in range(3)]
    assert rel[0] < 0.5 * min(rel[1], rel[2]), \
        f"attenuation is not axis-selective: {['%.3f' % r for r in rel]}"
    for i in (1, 2):
        assert rel[i] > 0.5, f"healthy axis {i} was over-detuned ({rel[i]:.3f})"
    # and it is monotone in authority
    assert np.allclose(scheduled_R(R0, [1.0, 1.0, 1.0]), R0)
    norms = [np.linalg.norm(scheduled_K(J, Q, R0, [h, 1.0, 1.0])[:, 0])
             for h in (1.0, 0.5, 0.05)]
    assert norms[0] > norms[1] > norms[2], f"gain not monotone in authority: {norms}"


# --------------------------------------------------------------------- runner
def main():
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except AssertionError as e:
            failed.append(name)
            print(f"  FAIL  {name}: {e}")
        except Exception as e:                                   # noqa: BLE001
            failed.append(name)
            print(f"  ERROR {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
