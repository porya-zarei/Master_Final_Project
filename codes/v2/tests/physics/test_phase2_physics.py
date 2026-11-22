"""Phase 2 physics and analytical verification suite (Gate C0 & spacecraft_config.yaml)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from adcs.dynamics.disturbances import gravity_gradient_torque_body
from adcs.dynamics.orbit import KeplerianOrbit, compute_lvlh_reference
from adcs.interfaces import SimulatorBackend
from adcs.simulation.fast import FastSimulatorBackend
from adcs.utils import load_spacecraft_config
from adcs.utils.quaternion import (
    dcm_to_quat,
    quat_canonicalize,
    quat_conjugate,
    quat_derivative,
    quat_error,
    quat_error_rotvec,
    quat_from_axis_angle,
    quat_geodesic_angle,
    quat_multiply,
    quat_rotate_vec,
    quat_rotate_vec_inv,
    quat_to_dcm,
    skew,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SPACECRAFT_YAML = REPO_ROOT / "spacecraft_config.yaml"


def test_quaternion_algebra_dcm_and_error_conventions() -> None:
    q1 = quat_from_axis_angle(np.array([1.0, 2.0, -0.5]), 0.7)
    q2 = quat_from_axis_angle(np.array([-0.3, 0.4, 1.0]), -1.1)

    # Composition consistency: R(q1 (*) q2) == R(q1) @ R(q2)
    r_comp = quat_to_dcm(quat_multiply(q1, q2))
    r_prod = quat_to_dcm(q1) @ quat_to_dcm(q2)
    np.testing.assert_allclose(r_comp, r_prod, atol=1e-13)

    # Orthogonality and det = +1
    np.testing.assert_allclose(r_comp.T @ r_comp, np.eye(3), atol=1e-13)
    assert np.linalg.det(r_comp) == pytest.approx(1.0, abs=1e-13)

    # Shepperd round-trip across edge angles including pi
    for axis, ang in [
        ([1, 0, 0], 0.0),
        ([1, 0, 0], np.pi),
        ([0, 1, 0], np.pi),
        ([0, 0, 1], np.pi),
        ([1, -2, 3], 2.3),
    ]:
        q = quat_canonicalize(quat_from_axis_angle(np.array(axis, dtype=float), ang))
        q_rt = dcm_to_quat(quat_to_dcm(q))
        assert quat_geodesic_angle(quat_multiply(quat_conjugate(q), q_rt)) < 1e-12

    # Kinematics check: d/dt R_IB == R_IB @ [omega_B]_x
    omega = np.array([0.12, -0.07, 0.25])
    eps = 1e-7
    q_plus = q1 + eps * quat_derivative(q1, omega)
    q_minus = q1 - eps * quat_derivative(q1, omega)
    dr_num = (quat_to_dcm(q_plus) - quat_to_dcm(q_minus)) / (2.0 * eps)
    dr_ana = quat_to_dcm(q1) @ skew(omega)
    np.testing.assert_allclose(dr_num, dr_ana, atol=1e-8)

    # Attitude error sign: rotating body by +theta about +x_R gives +theta on x component
    q_ir = q1
    theta = 0.2
    q_rb_true = quat_from_axis_angle(np.array([1.0, 0.0, 0.0]), theta)
    q_ib = quat_multiply(q_ir, q_rb_true)
    q_err = quat_error(q_ir, q_ib)
    rv = quat_error_rotvec(q_err)
    np.testing.assert_allclose(rv, np.array([theta, 0.0, 0.0]), atol=1e-12)
    assert quat_geodesic_angle(q_err) == pytest.approx(theta, abs=1e-12)


def test_torque_free_asymmetric_rigid_body_momentum_and_energy_conservation() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    j_asym = np.diag([12.0, 18.0, 24.0])
    sim = FastSimulatorBackend(
        cfg,
        inertia_override_kg_m2=j_asym,
        gravity_gradient_enabled=False,
        residual_dipole_override_am2=np.zeros(3),
    )
    assert isinstance(sim, SimulatorBackend)

    q0 = quat_from_axis_angle(np.array([0.3, -0.5, 0.8]), 0.9)
    w0 = np.array([0.15, -0.22, 0.18])
    st = sim.reset(q_ib_init=q0, omega_body_init=w0)
    h_i_0 = quat_rotate_vec(st.q_ib, j_asym @ st.omega_body_rad_s)
    ke_0 = 0.5 * float(st.omega_body_rad_s @ (j_asym @ st.omega_body_rad_s))

    zero3 = np.zeros(3)
    for _ in range(100):  # 20 seconds of torque-free tumbling
        out = sim.step(zero3, zero3)
        st = out.truth
        assert abs(float(np.linalg.norm(st.q_ib)) - 1.0) < 1e-13
        assert out.info["max_substep_quat_norm_drift"] < 1e-9

    h_i_end = quat_rotate_vec(st.q_ib, j_asym @ st.omega_body_rad_s)
    ke_end = 0.5 * float(st.omega_body_rad_s @ (j_asym @ st.omega_body_rad_s))

    np.testing.assert_allclose(h_i_end, h_i_0, atol=1e-10)
    assert ke_end == pytest.approx(ke_0, abs=1e-10)


def test_internal_rw_torque_conserves_total_angular_momentum_and_matches_sign() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    sim = FastSimulatorBackend(
        cfg,
        gravity_gradient_enabled=False,
        residual_dipole_override_am2=np.zeros(3),
        rw_time_constant_override_s=0.0,  # instantaneous for exact analytical check
    )
    st0 = sim.reset(
        q_ib_init=np.array([1.0, 0.0, 0.0, 0.0]),
        omega_body_init=np.array([0.05, -0.03, 0.02]),
        wheel_momentum_init=np.array([0.2, -0.1, 0.15]),
    )
    j = cfg.inertia_matrix_kg_m2
    a_rw = cfg.reaction_wheels.axis_matrix_body
    h_tot_0 = quat_rotate_vec(st0.q_ib, j @ st0.omega_body_rad_s + a_rw @ st0.wheel_momentum_nms)

    # Apply varying internal 3-axis RW torques for 10 seconds
    for k in range(50):
        tau_cmd = np.array([0.08 * np.sin(0.2 * k), -0.05, 0.04 * np.cos(0.1 * k)])
        st = sim.step(tau_cmd, np.zeros(3)).truth

    h_tot_end = quat_rotate_vec(st.q_ib, j @ st.omega_body_rad_s + a_rw @ st.wheel_momentum_nms)
    np.testing.assert_allclose(h_tot_end, h_tot_0, atol=1e-10)

    # Analytical single-axis torque sign check from rest: +tau_x -> +omega_x, -h_x
    sim.reset()
    tau_x = 0.10
    dt = 0.2
    st1 = sim.step(np.array([tau_x, 0.0, 0.0]), np.zeros(3), dt_s=dt).truth
    expected_wx = tau_x * dt / float(j[0, 0])
    assert st1.omega_body_rad_s[0] == pytest.approx(expected_wx, rel=1e-10)
    assert st1.wheel_momentum_nms[0] == pytest.approx(-tau_x * dt, rel=1e-10)


def test_rw_first_order_lag_and_saturation_limits() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    sim = FastSimulatorBackend(cfg, gravity_gradient_enabled=False)
    sim.reset()

    # Step response with first-order lag tau_c = 0.1 s under saturated command (0.5 > 0.15)
    out = sim.step(np.array([0.5, 0.0, 0.0]), np.zeros(3), dt_s=0.2)
    assert out.truth.actuator_status.rw_torque_saturated[0] is True
    expected_tau = 0.15 * (1.0 - np.exp(-0.2 / 0.1))
    assert out.truth.rw_torque_achieved_nm[0] == pytest.approx(expected_tau, rel=1e-4)

    # Momentum saturation wall test: wheel at +h_limit blocks further spin-up (negative body torque)
    h_lim = cfg.reaction_wheels.effective_momentum_limit_nms
    sim_inst = FastSimulatorBackend(
        cfg, gravity_gradient_enabled=False, rw_time_constant_override_s=0.0
    )
    sim_inst.reset(wheel_momentum_init=np.array([h_lim, 0.0, 0.0]))
    # Negative body torque -> dh/dt > 0 -> blocked at +h_lim
    out_blk = sim_inst.step(np.array([-0.1, 0.0, 0.0]), np.zeros(3), dt_s=0.2)
    assert out_blk.truth.actuator_status.rw_momentum_saturated[0] is True
    assert out_blk.truth.wheel_momentum_nms[0] == pytest.approx(h_lim, abs=1e-12)
    assert out_blk.truth.rw_torque_achieved_nm[0] == pytest.approx(0.0, abs=1e-12)
    # Positive body torque -> dh/dt < 0 -> allowed (desaturates wheel!)
    out_desat = sim_inst.step(np.array([0.1, 0.0, 0.0]), np.zeros(3), dt_s=0.2)
    assert out_desat.truth.wheel_momentum_nms[0] < h_lim - 0.01


def test_mtq_torque_perpendicular_to_b_field_and_dipole_saturation() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    sim = FastSimulatorBackend(cfg, mtq_time_constant_override_s=0.0)
    sim.reset()
    # Command exceeding 2.0 A*m^2 dipole limit
    out = sim.step(np.zeros(3), np.array([5.0, -3.0, 1.0]))
    st = out.truth
    assert st.actuator_status.mtq_dipole_saturated == (True, True, False)
    np.testing.assert_allclose(st.mtq_dipole_achieved_am2, np.array([2.0, -2.0, 1.0]), atol=1e-12)
    # Strictly perpendicular to B_body
    b_norm = float(np.linalg.norm(st.b_field_body_t))
    assert 1.0e-5 < b_norm < 8.0e-5  # Realistic LEO magnitude (10-80 uT)
    dot = abs(float(np.dot(st.mtq_torque_achieved_nm, st.b_field_body_t)))
    assert dot < 1e-18


def test_gravity_gradient_zero_for_cube_and_exact_for_asymmetric_inertia() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    orb = KeplerianOrbit(cfg.orbit).state_at(0.0)
    q = quat_from_axis_angle(np.array([1.0, 1.0, 0.0]), 0.5)

    # Uniform cube -> identically zero
    tau_cube = gravity_gradient_torque_body(
        orb.position_eci_m, q, cfg.inertia_matrix_kg_m2, cfg.orbit.gravitational_parameter_m3_s2
    )
    np.testing.assert_allclose(tau_cube, np.zeros(3), atol=1e-15)

    # Asymmetric inertia at 45 deg pitch in orbital plane -> known analytical magnitude
    j_asym = np.diag([10.0, 20.0, 30.0])
    q_pitch = quat_from_axis_angle(np.array([0.0, 1.0, 0.0]), np.deg2rad(45.0))
    r_eci = np.array([cfg.orbit.semi_major_axis_m, 0.0, 0.0])
    tau_gg = gravity_gradient_torque_body(
        r_eci, q_pitch, j_asym, cfg.orbit.gravitational_parameter_m3_s2
    )
    # r_hat_b = [cos45, 0, sin45], J r_hat_b = [10 cos45, 0, 30 sin45]
    # cross = [0, (30 - 10)*(-sin45*cos45), 0]? Wait: (r x Jr)_y = r_z (Jr)_x - r_x (Jr)_z
    # = sin45*10*cos45 - cos45*30*sin45 = -20 * 0.5 = -10
    coeff = 3.0 * cfg.orbit.gravitational_parameter_m3_s2 / (cfg.orbit.semi_major_axis_m**3)
    expected_y = coeff * (-10.0)
    np.testing.assert_allclose(tau_gg, np.array([0.0, expected_y, 0.0]), rtol=1e-12, atol=1e-15)


def test_lvlh_nadir_reference_kinematic_consistency_over_orbit() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    sim = FastSimulatorBackend(
        cfg,
        gravity_gradient_enabled=False,
        residual_dipole_override_am2=np.zeros(3),
    )
    orbit = KeplerianOrbit(cfg.orbit)
    orb0 = orbit.state_at(0.0)
    ref0, prev_x = compute_lvlh_reference(0.0, orb0.position_eci_m, orb0.velocity_eci_m_s)

    # Check +z_R points nadir (-r_hat_eci)
    z_in_eci = quat_rotate_vec(ref0.q_ir, np.array([0.0, 0.0, 1.0]))
    np.testing.assert_allclose(
        z_in_eci, -orb0.position_eci_m / np.linalg.norm(orb0.position_eci_m), atol=1e-13
    )

    # A torque-free cube initialized at LVLH attitude & LVLH angular rate tracks LVLH exactly!
    sim.reset(
        q_ib_init=ref0.q_ir,
        omega_body_init=ref0.omega_ref_inertial_in_ref_rad_s,
    )
    b_fields = []
    for _ in range(300):  # 60 seconds along orbit
        st = sim.step(np.zeros(3), np.zeros(3)).truth
        ref, prev_x = compute_lvlh_reference(
            st.time_s, st.position_eci_m, st.velocity_eci_m_s, prev_x
        )
        err_rad = quat_geodesic_angle(quat_error(ref.q_ir, st.q_ib))
        assert err_rad < 1e-10
        b_fields.append(st.b_field_body_t)

    # Verify magnetic field is non-constant along the orbit
    b_arr = np.asarray(b_fields)
    assert np.linalg.norm(b_arr[-1] - b_arr[0]) > 1e-7


def test_deterministic_replay_and_rk4_timestep_convergence() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    j_asym = np.diag([14.0, 17.0, 21.0])

    def run_once(step_s: float) -> np.ndarray:
        sim = FastSimulatorBackend(cfg, inertia_override_kg_m2=j_asym)
        # Override integration step via shallow copy of simulation config
        sim.config = type(cfg)(
            **{
                **cfg.__dict__,
                "simulation": type(cfg.simulation)(
                    **{**cfg.simulation.__dict__, "integration_step_s": step_s}
                ),
            }
        )
        sim.reset(
            q_ib_init=quat_from_axis_angle(np.array([1.0, -1.0, 0.5]), 0.6),
            omega_body_init=np.array([0.08, -0.05, 0.11]),
        )
        for k in range(25):  # 5 seconds
            st = sim.step(
                np.array([0.05 * np.sin(k), -0.04, 0.03]),
                np.array([0.5, -0.3, 0.2]),
                dt_s=0.2,
            ).truth
        return np.concatenate([st.q_ib, st.omega_body_rad_s, st.wheel_momentum_nms])

    # Bit-identical determinism
    r_a = run_once(0.01)
    r_b = run_once(0.01)
    np.testing.assert_array_equal(r_a, r_b)

    # RK4 convergence: error(dt=0.1) / error(dt=0.05) ~ 16 (4th order)
    ref_fine = run_once(0.005)
    err_coarse = float(np.linalg.norm(run_once(0.1) - ref_fine))
    err_med = float(np.linalg.norm(run_once(0.05) - ref_fine))
    err_nom = float(np.linalg.norm(run_once(0.01) - ref_fine))
    assert err_coarse > err_med > err_nom
    assert err_nom < 1e-9
    order_est = np.log2(err_coarse / err_med)
    assert order_est > 3.5


def test_fast_backend_rejects_non_finite_commands() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    sim = FastSimulatorBackend(cfg)
    with pytest.raises(ValueError, match="finite"):
        sim.step(np.array([np.nan, 0.0, 0.0]), np.zeros(3))
    with pytest.raises(ValueError, match="finite"):
        sim.step(np.zeros(3), np.array([0.0, np.inf, 0.0]))
    # Sanity check quat_rotate_vec_inv inverse relationship
    q = quat_from_axis_angle(np.array([0.2, 0.5, -0.3]), 1.2)
    v = np.array([1.0, -2.0, 3.0])
    np.testing.assert_allclose(quat_rotate_vec_inv(q, quat_rotate_vec(q, v)), v, atol=1e-13)
