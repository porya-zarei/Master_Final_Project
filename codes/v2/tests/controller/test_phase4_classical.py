"""Phase 4 controller tests (Gate C1): nadir pointing, saturation, allocation, unloading."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from adcs.control.allocation import ActuatorAllocator, AllocationConfig, solve_box_lsq
from adcs.control.classical import ClassicalLQRConfig, ClassicalLQRController
from adcs.control.reference import NadirReferenceGenerator, compute_attitude_error
from adcs.interfaces import (
    ActuatorCapabilityState,
    ControllerProtocol,
    EstimatorOutput,
    SensorMeasurement,
)
from adcs.simulation.fast import FastSimulatorBackend
from adcs.utils import load_spacecraft_config
from adcs.utils.quaternion import quat_from_axis_angle, quat_multiply

REPO_ROOT = Path(__file__).resolve().parents[2]
SPACECRAFT_YAML = REPO_ROOT / "spacecraft_config.yaml"


def _ideal_estimator_and_meas(truth) -> tuple[EstimatorOutput, SensorMeasurement]:
    est = EstimatorOutput(
        time_s=truth.time_s,
        q_ib_est=truth.q_ib.copy(),
        omega_body_est_rad_s=truth.omega_body_rad_s.copy(),
        gyro_bias_est_rad_s=np.zeros(3),
        attitude_cov_rad2=np.eye(3) * 1e-10,
        rate_cov_rad2_s2=np.eye(3) * 1e-10,
        attitude_std_rad=np.full(3, 1e-5),
        rate_std_rad_s=np.full(3, 1e-5),
        gamma_obs=1.0,
        sensor_status={"gyro": True, "star_tracker": True, "magnetometer": True},
        data_age_s=0.0,
        valid=True,
    )
    meas = SensorMeasurement(
        time_s=truth.time_s,
        gyro_rad_s=truth.omega_body_rad_s.copy(),
        gyro_valid=True,
        star_tracker_q_ib=truth.q_ib.copy(),
        star_tracker_valid=True,
        star_tracker_age_s=0.0,
        mag_body_t=truth.b_field_body_t.copy(),
        mag_valid=True,
        rw_speed_rad_s=truth.wheel_speed_rad_s.copy(),
        rw_speed_valid=(True, True, True),
    )
    return est, meas


def _nominal_dummy_capability(time_s: float) -> ActuatorCapabilityState:
    return ActuatorCapabilityState(
        time_s=time_s,
        wheels=(),
        mtqs=(),
        nominal_support_xyz=np.full(3, 0.15),
        conservative_support_xyz=np.full(3, 0.15),
        directional_margin_xyz=np.ones(3),
        effective_rank=3,
        confidence=1.0,
        is_oracle=True,
        stale=False,
        valid=True,
    )


def test_nominal_nadir_acquisition_and_steady_tracking_gate_c1() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    sim = FastSimulatorBackend(cfg)
    ref_gen = NadirReferenceGenerator()
    ctrl = ClassicalLQRController(cfg)
    assert isinstance(ctrl, ControllerProtocol)

    # Start 30 deg off nadir + 0.03 rad/s initial rate tumble
    st0 = sim.reset()
    ref0 = ref_gen.compute(st0.time_s, st0.position_eci_m, st0.velocity_eci_m_s)
    q_pert = quat_from_axis_angle(np.array([0.6, -0.5, 0.62]), np.deg2rad(30.0))
    q_init = quat_multiply(ref0.q_ir, q_pert)
    w_init = ref0.omega_ref_inertial_in_ref_rad_s + np.array([0.02, -0.015, 0.018])

    st = sim.reset(q_ib_init=q_init, omega_body_init=w_init)
    ref_gen.reset()
    ctrl.reset()

    errors_deg: list[float] = []
    dt = cfg.simulation.control_period_s
    for _ in range(400):  # 80 seconds
        ref = ref_gen.compute(st.time_s, st.position_eci_m, st.velocity_eci_m_s)
        est, meas = _ideal_estimator_and_meas(st)
        out = ctrl.compute(
            estimator_out=est,
            reference=ref,
            capability=_nominal_dummy_capability(st.time_s),
            measurement=meas,
            dt_s=dt,
        )
        assert out.gate_decision.rl_enabled is False
        st = sim.step(out.command.rw_torque_cmd_nm, out.command.mtq_dipole_cmd_am2, dt_s=dt).truth
        err = compute_attitude_error(st.q_ib, st.omega_body_rad_s, ref)
        errors_deg.append(float(np.rad2deg(err.geodesic_angle_rad)))

    # Settles below 0.5 deg well before 60 s (step 300) and holds < 0.05 deg at steady state
    assert errors_deg[299] < 0.5
    assert max(errors_deg[350:]) < 0.05


def test_large_angle_90deg_slew_with_rw_saturation_and_determinism() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)

    def run_slew() -> tuple[list[float], bool]:
        sim = FastSimulatorBackend(cfg)
        ref_gen = NadirReferenceGenerator()
        ctrl = ClassicalLQRController(cfg)
        st0 = sim.reset()
        ref0 = ref_gen.compute(st0.time_s, st0.position_eci_m, st0.velocity_eci_m_s)
        q_init = quat_multiply(
            ref0.q_ir, quat_from_axis_angle(np.array([1.0, 0.4, -0.3]), np.deg2rad(90.0))
        )
        st = sim.reset(q_ib_init=q_init, omega_body_init=np.array([-0.02, 0.03, -0.01]))
        ref_gen.reset()
        ctrl.reset()

        errs: list[float] = []
        saw_sat = False
        dt = cfg.simulation.control_period_s
        for _ in range(500):  # 100 s
            ref = ref_gen.compute(st.time_s, st.position_eci_m, st.velocity_eci_m_s)
            est, meas = _ideal_estimator_and_meas(st)
            out = ctrl.compute(
                estimator_out=est,
                reference=ref,
                capability=_nominal_dummy_capability(st.time_s),
                measurement=meas,
                dt_s=dt,
            )
            st = sim.step(
                out.command.rw_torque_cmd_nm, out.command.mtq_dipole_cmd_am2, dt_s=dt
            ).truth
            if any(st.actuator_status.rw_torque_saturated) or any(out.diagnostics["rw_saturated"]):
                saw_sat = True
            err = compute_attitude_error(st.q_ib, st.omega_body_rad_s, ref)
            errs.append(float(np.rad2deg(err.geodesic_angle_rad)))
        return errs, saw_sat

    errs1, sat1 = run_slew()
    errs2, _ = run_slew()
    assert sat1 is True  # Large 90 deg slew exercises RW torque saturation
    assert errs1[-1] < 0.1  # Smoothly converges to < 0.1 deg
    np.testing.assert_array_equal(np.asarray(errs1), np.asarray(errs2))


def test_mtq_momentum_unloading_reduces_wheel_momentum_while_holding_nadir() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    sim = FastSimulatorBackend(cfg)
    ref_gen = NadirReferenceGenerator()
    ctrl = ClassicalLQRController(
        cfg,
        lqr_config=ClassicalLQRConfig(),
        alloc_config=AllocationConfig(mtq_unload_gain=0.05),
    )

    st0 = sim.reset()
    ref0 = ref_gen.compute(st0.time_s, st0.position_eci_m, st0.velocity_eci_m_s)
    h_init = np.array([1.5, -1.2, 0.8], dtype=np.float64)
    st = sim.reset(
        q_ib_init=ref0.q_ir,
        omega_body_init=ref0.omega_ref_inertial_in_ref_rad_s,
        wheel_momentum_init=h_init,
    )
    h_norm_0 = float(np.linalg.norm(st.wheel_momentum_nms))
    dt = cfg.simulation.control_period_s
    for _ in range(300):  # 60 s of unloading
        ref = ref_gen.compute(st.time_s, st.position_eci_m, st.velocity_eci_m_s)
        est, meas = _ideal_estimator_and_meas(st)
        out = ctrl.compute(
            estimator_out=est,
            reference=ref,
            capability=_nominal_dummy_capability(st.time_s),
            measurement=meas,
            dt_s=dt,
        )
        st = sim.step(out.command.rw_torque_cmd_nm, out.command.mtq_dipole_cmd_am2, dt_s=dt).truth

    h_norm_end = float(np.linalg.norm(st.wheel_momentum_nms))
    assert h_norm_end < h_norm_0 - 1e-3  # Measurable wheel momentum reduction
    err_deg = np.rad2deg(
        compute_attitude_error(st.q_ib, st.omega_body_rad_s, ref).geodesic_angle_rad
    )
    assert err_deg < 0.1  # Nadir pointing preserved during unloading


def test_box_lsq_allocator_handles_overactuated_pyramid_geometry() -> None:
    # 4-wheel NASA pyramid geometry (non-orthogonal)
    s = 1.0 / np.sqrt(3.0)
    a_pyramid = np.array(
        [
            [s, -s, -s, s],
            [s, s, -s, -s],
            [s, s, s, s],
        ],
        dtype=np.float64,
    )
    u_min = np.full(4, -0.15)
    u_max = np.full(4, 0.15)
    tau_des = np.array([0.08, -0.05, 0.12])
    u = solve_box_lsq(a_pyramid, tau_des, u_min, u_max, reg=1e-8)
    assert np.all(u >= u_min - 1e-12) and np.all(u <= u_max + 1e-12)
    np.testing.assert_allclose(a_pyramid @ u, tau_des, atol=1e-6)

    # Now disable wheel 0 (u_min[0] = u_max[0] = 0): remaining 3 wheels span R^3!
    u_min_f = u_min.copy()
    u_max_f = u_max.copy()
    u_min_f[0] = 0.0
    u_max_f[0] = 0.0
    # Feasible torque for remaining 3 wheels
    tau_des_feas = np.array([0.05, -0.04, 0.08])
    u_f = solve_box_lsq(a_pyramid, tau_des_feas, u_min_f, u_max_f, reg=1e-8)
    assert u_f[0] == pytest.approx(0.0, abs=1e-12)
    np.testing.assert_allclose(a_pyramid @ u_f, tau_des_feas, atol=1e-5)

    # Infeasible torque for remaining 3 wheels (requires u3 = 0.10*sqrt(3) = 0.1732 > 0.15):
    # box-LSQ clips wheel 3 cleanly at 0.15 while preserving y-axis exactness
    u_inf = solve_box_lsq(a_pyramid, tau_des, u_min_f, u_max_f, reg=1e-8)
    assert u_inf[0] == pytest.approx(0.0, abs=1e-12)
    assert u_inf[3] == pytest.approx(0.15, abs=1e-6)
    assert (a_pyramid @ u_inf)[1] == pytest.approx(tau_des[1], abs=1e-5)

    # Also verify ActuatorAllocator API directly on nominal 3-wheel config
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    alloc = ActuatorAllocator(cfg)
    res = alloc.allocate(
        np.array([0.1, -0.25, 0.05]),
        wheel_momentum_nms=np.zeros(3),
        b_field_body_t=np.array([0.0, 0.0, 3e-5]),
    )
    assert res.rw_torque_cmd_nm[0] == pytest.approx(0.1, abs=1e-5)
    assert res.rw_torque_cmd_nm[1] == pytest.approx(-0.15, abs=1e-5)  # clipped at nominal limit
    assert res.rw_saturated[1] is True
