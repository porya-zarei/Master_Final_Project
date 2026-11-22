"""Verification of official IGRF-14 degree-13 field, RLS steady-state fix, and config generality."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import yaml

from adcs.control.classical import StrongClassicalController
from adcs.control.reference import NadirReferenceGenerator, compute_attitude_error
from adcs.control.residual_rl import CCRController, CCRControllerConfig, ZeroResidualPolicy
from adcs.dynamics.magnetic_field import (
    GeomagneticFieldModel,
    find_default_igrf14_file,
    load_igrf14_coefficients,
)
from adcs.estimation import MultiplicativeEKF, OnlineCapabilityEstimator
from adcs.sensors import SensorSuite
from adcs.simulation.fast import FastSimulatorBackend
from adcs.training import ADCSResidualEnv, EnvTrainConfig
from adcs.utils import load_spacecraft_config
from adcs.utils.quaternion import (
    quat_error,
    quat_from_axis_angle,
    quat_geodesic_angle,
    quat_multiply,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SPACECRAFT_YAML = REPO_ROOT / "spacecraft_config.yaml"


def test_official_igrf14_degree13_maxwell_equations_and_physical_regions() -> None:
    igrf_path = find_default_igrf14_file()
    assert igrf_path is not None and igrf_path.exists()

    coeffs_2025 = load_igrf14_coefficients(igrf_path, decimal_year=2025.0)
    coeffs_2027 = load_igrf14_coefficients(igrf_path, decimal_year=2027.5)
    assert coeffs_2025.max_degree == 13
    assert "IGRF-14_deg_13" in coeffs_2025.model_fidelity
    # Verify official IGRF-14 2025.0 main dipole g_1^0 = -29350.0 nT and SV +12.6 nT/yr
    assert coeffs_2025.g[1, 0] == pytest.approx(-29350.0, abs=1e-6)
    assert coeffs_2027.g[1, 0] == pytest.approx(-29350.0 + 2.5 * 12.6, abs=1e-6)

    model = GeomagneticFieldModel(coefficients=coeffs_2025)
    # 1. Maxwell's equations in source-free space (LEO): div(B) == 0 and curl(B) == 0!
    r0 = np.array([4.5e6, -3.2e6, 4.1e6], dtype=np.float64)  # ~6880 km LEO point
    eps = 10.0  # 10 m finite-difference step
    jac = np.zeros((3, 3), dtype=np.float64)
    for j in range(3):
        dr = np.zeros(3, dtype=np.float64)
        dr[j] = eps
        jac[:, j] = (model.field_ecef_t(r0 + dr) - model.field_ecef_t(r0 - dr)) / (2.0 * eps)

    div_b = float(np.trace(jac))
    curl_b = np.array(
        [jac[2, 1] - jac[1, 2], jac[0, 2] - jac[2, 0], jac[1, 0] - jac[0, 1]], dtype=np.float64
    )
    b_scale = float(np.linalg.norm(model.field_ecef_t(r0))) / float(np.linalg.norm(r0))
    assert abs(div_b) / b_scale < 1e-8
    assert float(np.linalg.norm(curl_b)) / b_scale < 1e-8

    # 2. Realistic geomagnetic features at Earth surface (r = 6371.2 km):
    # South Atlantic Anomaly (lat -25 deg, lon -50 deg) is significantly weaker than high latitudes
    r_earth = 6371200.0
    lat_saa, lon_saa = np.deg2rad(-25.0), np.deg2rad(-50.0)
    pos_saa = r_earth * np.array(
        [np.cos(lat_saa) * np.cos(lon_saa), np.cos(lat_saa) * np.sin(lon_saa), np.sin(lat_saa)]
    )
    lat_pole, lon_pole = np.deg2rad(75.0), np.deg2rad(-100.0)
    pos_pole = r_earth * np.array(
        [np.cos(lat_pole) * np.cos(lon_pole), np.cos(lat_pole) * np.sin(lon_pole), np.sin(lat_pole)]
    )
    b_saa = float(np.linalg.norm(model.field_ecef_t(pos_saa))) * 1e6  # uT
    b_pole = float(np.linalg.norm(model.field_ecef_t(pos_pole))) * 1e6  # uT
    assert 20.0 < b_saa < 28.0
    assert 50.0 < b_pole < 65.0
    assert b_pole > 2.0 * b_saa


def test_rls_directional_forgetting_preserves_steady_state_conservative_margin() -> None:
    """Regression test for Plot 07: quiet steady-state pointing must NOT collapse g_min."""
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    sim = FastSimulatorBackend(cfg)
    sensors = SensorSuite(n_rw=cfg.reaction_wheels.count)
    mekf = MultiplicativeEKF()
    cap_est = OnlineCapabilityEstimator(cfg)
    ref_gen = NadirReferenceGenerator()
    ctrl = StrongClassicalController(cfg)

    st = sim.reset()
    ref0 = ref_gen.compute(st.time_s, st.position_eci_m, st.velocity_eci_m_s)
    st = sim.reset(q_ib_init=ref0.q_ir, omega_body_init=ref0.omega_ref_inertial_in_ref_rad_s)
    sensors.reset(seed=1, q_ib_init=st.q_ib)
    mekf.reset(q_ib_init=st.q_ib, omega_init=st.omega_body_rad_s)
    cap_est.reset()
    ctrl.reset()

    dt = cfg.simulation.control_period_s
    last_cmd = None
    cap = None
    for _ in range(250):  # 50 s of quiet steady nadir holding
        meas = sensors.measure(st, dt_s=dt)
        ref = ref_gen.compute(st.time_s, st.position_eci_m, st.velocity_eci_m_s)
        est = mekf.update(meas, dt_s=dt)
        cap = cap_est.estimate(
            time_s=st.time_s,
            measurement=meas,
            last_command=last_cmd,
            b_field_body_t=meas.mag_body_t,
            dt_s=dt,
        )
        out = ctrl.compute(
            estimator_out=est, reference=ref, capability=cap, measurement=meas, dt_s=dt
        )
        last_cmd = out.command
        st = sim.step(out.command.rw_torque_cmd_nm, out.command.mtq_dipole_cmd_am2, dt_s=dt).truth

    assert cap is not None
    # Healthy wheels in quiet pointing must keep conservative margin > 0.75 (not collapse to 0.05!)
    assert float(np.min(cap.directional_margin_xyz)) > 0.75
    assert cap.confidence > 0.70


def test_config_generality_3u_cubesat_and_4wheel_pyramid(tmp_path: Path) -> None:
    """Verify changing spacecraft_config.yaml scales LQR/ESO/B3/CCR/Env seamlessly."""
    base = yaml.safe_load(SPACECRAFT_YAML.read_text(encoding="utf-8"))

    # 1. Tiny 4 kg 3U CubeSat (3 orders of magnitude smaller inertia & torque!)
    cube = yaml.safe_load(yaml.safe_dump(base))
    cube["metadata"]["name"] = "cubesat_3u_test"
    cube["spacecraft"]["mass_kg"] = 4.0
    cube["spacecraft"]["dimensions_m"] = [0.1, 0.1, 0.3]
    cube["spacecraft"]["inertia"]["matrix_kg_m2"] = [
        [0.033, 0.0, 0.0],
        [0.0, 0.033, 0.0],
        [0.0, 0.0, 0.007],
    ]
    cube["reaction_wheels"]["per_wheel"]["rotor_inertia_kg_m2"] = 3.0e-5
    cube["reaction_wheels"]["per_wheel"]["torque_limit_nominal_Nm"] = 0.002
    cube["reaction_wheels"]["per_wheel"]["torque_limit_peak_Nm"] = 0.004
    cube["reaction_wheels"]["per_wheel"]["momentum_limit_nominal_Nms"] = 0.015
    cube["reaction_wheels"]["per_wheel"]["momentum_limit_peak_Nms"] = 0.015
    cube["reaction_wheels"]["per_wheel"]["speed_limit_rpm"] = 6000.0
    cube["magnetorquers"]["dipole_limit_per_axis_Am2"] = 0.2
    cube["magnetorquers"]["dipole_command_limits_Am2"] = [[-0.2, 0.2], [-0.2, 0.2], [-0.2, 0.2]]
    cube_path = tmp_path / "cubesat_3u.yaml"
    cube_path.write_text(yaml.safe_dump(cube), encoding="utf-8")

    cfg_3u = load_spacecraft_config(cube_path)
    sim_3u = FastSimulatorBackend(cfg_3u)
    assert "IGRF-14_deg_13" in sim_3u.mag_model.model_fidelity
    ctrl_3u = StrongClassicalController(cfg_3u)
    ref_gen = NadirReferenceGenerator()
    sensors = SensorSuite(n_rw=3)
    mekf = MultiplicativeEKF()
    cap_est = OnlineCapabilityEstimator(cfg_3u)

    st0 = sim_3u.reset()
    ref0 = ref_gen.compute(st0.time_s, st0.position_eci_m, st0.velocity_eci_m_s)
    q_pert = quat_from_axis_angle(np.array([1.0, -0.5, 0.3]), np.deg2rad(25.0))
    q_init = quat_multiply(ref0.q_ir, q_pert)
    st = sim_3u.reset(q_ib_init=q_init, omega_body_init=ref0.omega_ref_inertial_in_ref_rad_s)
    sensors.reset(seed=2, q_ib_init=q_init)
    mekf.reset(q_ib_init=q_init, omega_init=st.omega_body_rad_s)
    cap_est.reset()
    ctrl_3u.reset()

    dt = cfg_3u.simulation.control_period_s
    last_cmd = None
    for _ in range(250):  # 50 s
        meas = sensors.measure(st, dt_s=dt)
        ref = ref_gen.compute(st.time_s, st.position_eci_m, st.velocity_eci_m_s)
        est = mekf.update(meas, dt_s=dt)
        cap = cap_est.estimate(
            time_s=st.time_s,
            measurement=meas,
            last_command=last_cmd,
            b_field_body_t=meas.mag_body_t,
            dt_s=dt,
        )
        out = ctrl_3u.compute(
            estimator_out=est, reference=ref, capability=cap, measurement=meas, dt_s=dt
        )
        last_cmd = out.command
        st = sim_3u.step(
            out.command.rw_torque_cmd_nm, out.command.mtq_dipole_cmd_am2, dt_s=dt
        ).truth
    err_3u_deg = np.rad2deg(
        compute_attitude_error(st.q_ib, st.omega_body_rad_s, ref).geodesic_angle_rad
    )
    assert err_3u_deg < 0.5  # 3U CubeSat converges cleanly with ZERO manual retuning!

    # 2. 4-wheel NASA pyramid spacecraft through CCRController + ADCSResidualEnv
    pyr = yaml.safe_load(yaml.safe_dump(base))
    s = float(1.0 / np.sqrt(3.0))
    pyr["metadata"]["name"] = "pyramid_4rw_test"
    pyr["reaction_wheels"]["count"] = 4
    pyr["reaction_wheels"]["configuration"] = "pyramid"
    pyr["reaction_wheels"]["axis_matrix_body"] = [
        [s, -s, -s, s],
        [s, s, -s, -s],
        [s, s, s, s],
    ]
    pyr_path = tmp_path / "pyramid_4rw.yaml"
    pyr_path.write_text(yaml.safe_dump(pyr), encoding="utf-8")

    cfg_4rw = load_spacecraft_config(pyr_path)
    env_4rw = ADCSResidualEnv(cfg_4rw, EnvTrainConfig(episode_duration_s=10.0))
    obs, _ = env_4rw.reset(seed=9)
    assert obs.shape == (30,) and np.all(np.isfinite(obs))
    for _ in range(10):
        obs, rew, _, _, _ = env_4rw.step(np.array([0.1, -0.1, 0.05], dtype=np.float32))
        assert obs.shape == (30,) and np.all(np.isfinite(obs)) and np.isfinite(rew)

    ccr_4rw = CCRController(cfg_4rw, ZeroResidualPolicy(), CCRControllerConfig(name="A7_4rw"))
    assert ccr_4rw.allocator.n_rw == 4


def test_underactuated_hybrid_2rw_3mtq_recovery_on_100pct_rw_failure() -> None:
    """Verify 3-RW + 3-MTQ (2.0 A*m^2) recovers < 10 deg from 20 deg error after 100% RW1 loss."""
    from adcs.actuators.models import ActuatorFaultState, MTQFaultParams, RWFaultParams

    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    sim = FastSimulatorBackend(cfg)
    ref_gen = NadirReferenceGenerator()
    sensors = SensorSuite(n_rw=3)
    mekf = MultiplicativeEKF()
    cap_est = OnlineCapabilityEstimator(cfg)
    ctrl = StrongClassicalController(cfg)

    st0 = sim.reset(true_anomaly_deg_init=30.0)
    ref0 = ref_gen.compute(st0.time_s, st0.position_eci_m, st0.velocity_eci_m_s)
    q_pert = quat_from_axis_angle(np.array([1.0, 0.0, 0.0]), np.deg2rad(20.0))
    q_init = quat_multiply(ref0.q_ir, q_pert)
    w_init = ref0.omega_ref_inertial_in_ref_rad_s + np.array([np.deg2rad(0.03), 0.0, 0.0])
    st = sim.reset(q_ib_init=q_init, omega_body_init=w_init, true_anomaly_deg_init=30.0)
    rw_f = RWFaultParams.nominal(cfg.reaction_wheels)
    rw_f.effectiveness[0] = 0.0
    sim.set_fault_state(
        ActuatorFaultState(rw=rw_f, mtq=MTQFaultParams.nominal(cfg.magnetorquers))
    )
    sensors.reset(seed=7, q_ib_init=q_init)
    mekf.reset(q_ib_init=q_init, omega_init=w_init)
    cap_est.reset()
    ctrl.reset()

    dt = cfg.simulation.control_period_s
    last_cmd = None
    errs_last_300s: list[float] = []
    n_steps = int(1200.0 / dt)
    for k in range(n_steps):
        meas = sensors.measure(st, dt_s=dt)
        ref = ref_gen.compute(st.time_s, st.position_eci_m, st.velocity_eci_m_s)
        est = mekf.update(meas, dt_s=dt)
        cap = cap_est.estimate(
            time_s=st.time_s,
            measurement=meas,
            last_command=last_cmd,
            b_field_body_t=meas.mag_body_t,
            dt_s=dt,
        )
        out = ctrl.compute(
            estimator_out=est, reference=ref, capability=cap, measurement=meas, dt_s=dt
        )
        last_cmd = out.command
        st = sim.step(out.command.rw_torque_cmd_nm, out.command.mtq_dipole_cmd_am2, dt_s=dt).truth
        if k >= n_steps - int(300.0 / dt):
            err_deg = float(np.rad2deg(quat_geodesic_angle(quat_error(ref.q_ir, st.q_ib))))
            errs_last_300s.append(err_deg)

    assert float(np.max(errs_last_300s)) < 10.0
    assert float(np.mean(errs_last_300s)) < 5.0
