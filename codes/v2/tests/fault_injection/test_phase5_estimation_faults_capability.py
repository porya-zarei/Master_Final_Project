"""Phase 5 tests (Gates C2 & C3): sensors, MEKF + gamma_obs, fault catalog, capability/AMS."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from adcs.estimation import (
    MultiplicativeEKF,
    OnlineCapabilityEstimator,
    OracleCapabilityEstimator,
    ams_support_function,
)
from adcs.faults import FaultEvent, FaultInjector, build_default_scenario_catalog
from adcs.interfaces import ActuatorCommand
from adcs.sensors import SensorFaultParams, SensorSuite
from adcs.simulation.fast import FastSimulatorBackend
from adcs.utils import load_spacecraft_config
from adcs.utils.quaternion import quat_error, quat_from_axis_angle, quat_geodesic_angle

REPO_ROOT = Path(__file__).resolve().parents[2]
SPACECRAFT_YAML = REPO_ROOT / "spacecraft_config.yaml"


def test_mekf_tracks_attitude_estimates_gyro_bias_and_drops_gamma_obs_on_fault() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    sim = FastSimulatorBackend(cfg)
    sensors = SensorSuite()
    mekf = MultiplicativeEKF()

    q0 = quat_from_axis_angle(np.array([0.4, -0.5, 0.7]), 0.5)
    w0 = np.array([0.02, -0.015, 0.01])
    st = sim.reset(q_ib_init=q0, omega_body_init=w0)
    sensors.reset(seed=7, q_ib_init=q0)
    # Deliberately start MEKF with 2 deg attitude offset
    q_init_err = quat_from_axis_angle(np.array([1.0, 0.0, 0.0]), np.deg2rad(2.0))
    from adcs.utils.quaternion import quat_multiply

    mekf.reset(quat_multiply(q0, q_init_err), omega_init=w0, time_s=0.0)

    dt = cfg.simulation.control_period_s
    # 1. Healthy phase (25 s): attitude error shrinks, gyro bias converges, gamma_obs stays high
    for _ in range(125):
        st = sim.step(np.array([0.005, -0.004, 0.003]), np.zeros(3), dt_s=dt).truth
        meas = sensors.measure(st, dt_s=dt)
        est = mekf.update(meas, dt_s=dt)

    att_err_deg = np.rad2deg(quat_geodesic_angle(quat_error(st.q_ib, est.q_ib_est)))
    assert att_err_deg < 0.25
    assert est.gamma_obs > 0.85
    assert est.valid is True
    # Gyro bias estimate moved closer to true bias
    bias_err_norm = float(np.linalg.norm(est.gyro_bias_est_rad_s - sensors.true_gyro_bias_rad_s))
    assert bias_err_norm < 5e-4

    # 2. Star-tracker glitch rejected by Mahalanobis gate without corrupting attitude
    meas_glitch = sensors.measure(
        st, dt_s=dt, faults=SensorFaultParams(star_tracker_invalid_glitch=True)
    )
    est_glitch = mekf.update(meas_glitch, dt_s=dt)
    assert est_glitch.diagnostics["st_outlier_rejected"] is True
    att_err_after_glitch = np.rad2deg(quat_geodesic_angle(quat_error(st.q_ib, est_glitch.q_ib_est)))
    assert att_err_after_glitch < 0.5  # Rejected glitch did not corrupt attitude

    # 3. Prolonged star-tracker dropout monotonically decreases gamma_obs
    gammas_drop: list[float] = []
    for _ in range(50):  # 10 s dropout
        st = sim.step(np.zeros(3), np.zeros(3), dt_s=dt).truth
        meas = sensors.measure(st, dt_s=dt, faults=SensorFaultParams(star_tracker_dropout=True))
        est_d = mekf.update(meas, dt_s=dt)
        gammas_drop.append(est_d.gamma_obs)
    assert gammas_drop[-1] < gammas_drop[0]
    assert gammas_drop[-1] < 0.35

    # 4. Complete blackout (gyro + ST dropout) -> gamma_obs == 0 and valid == False
    meas_dead = sensors.measure(
        st, dt_s=dt, faults=SensorFaultParams(gyro_dropout=True, star_tracker_dropout=True)
    )
    est_dead = mekf.update(meas_dead, dt_s=dt)
    assert est_dead.valid is False
    assert est_dead.gamma_obs == pytest.approx(0.0)


def test_fault_injector_distinct_models_and_determinism() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    events = (
        FaultEvent(
            "rw_effectiveness_loss", start_s=10.0, ramp_s=10.0, target_index=0, severity=0.4
        ),
        FaultEvent("rw_lock", start_s=15.0, target_index=1, severity=0.0),
        FaultEvent("rw_stuck_torque", start_s=15.0, target_index=2, severity=0.05),
    )
    inj = FaultInjector(cfg, events)

    f_before, _ = inj.evaluate(5.0)
    assert f_before.rw.effectiveness[0] == pytest.approx(1.0)
    assert f_before.rw.locked[1] is False
    assert f_before.rw.stuck_torque_nm[2] is None

    f_mid, _ = inj.evaluate(15.0)
    assert f_mid.rw.effectiveness[0] == pytest.approx(0.7)  # halfway through 10s ramp to 0.4
    assert f_mid.rw.locked[1] is True
    assert f_mid.rw.stuck_torque_nm[2] == pytest.approx(0.05)

    f_after, _ = inj.evaluate(25.0)
    assert f_after.rw.effectiveness[0] == pytest.approx(0.4)

    # Catalog split discipline check
    catalog = build_default_scenario_catalog()
    splits = {s.split for s in catalog.values()}
    assert splits == {"train", "val", "test"}
    categories = {s.category for s in catalog.values()}
    assert {"S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"}.issubset(categories)


def test_capability_ams_support_vs_sampled_torques_and_online_rls_tracking_gate_c2() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    sim = FastSimulatorBackend(cfg)
    sensors = SensorSuite()
    oracle_cap = OracleCapabilityEstimator(cfg)
    online_cap = OnlineCapabilityEstimator(cfg)

    # Inject 60% effectiveness loss (eff = 0.4) on wheel 0 from t = 5s
    events = (FaultEvent("rw_effectiveness_loss", start_s=5.0, target_index=0, severity=0.4),)
    inj = FaultInjector(cfg, events)

    st = sim.reset()
    sensors.reset(seed=11, q_ib_init=st.q_ib)
    oracle_cap.reset()
    online_cap.reset()

    dt = cfg.simulation.control_period_s
    last_cmd: ActuatorCommand | None = None
    cap_online = None
    cap_oracle = None

    for k in range(150):  # 30 seconds
        act_faults, sens_faults = inj.evaluate(st.time_s)
        sim.set_fault_state(act_faults)
        # Exciting torque commands across all 3 wheels
        rw_cmd = np.array(
            [0.06 * np.sin(0.5 * k + 0.3), 0.05 * np.cos(0.4 * k), -0.04 * np.sin(0.3 * k)]
        )
        last_cmd = ActuatorCommand(
            rw_torque_cmd_nm=rw_cmd,
            mtq_dipole_cmd_am2=np.zeros(3),
            tau_request_nm=rw_cmd,
            tau_allocated_nm=rw_cmd,
        )
        st = sim.step(rw_cmd, np.zeros(3), dt_s=dt).truth
        meas = sensors.measure(st, dt_s=dt, faults=sens_faults)
        cap_oracle = oracle_cap.estimate(
            time_s=st.time_s,
            measurement=meas,
            last_command=last_cmd,
            b_field_body_t=meas.mag_body_t,
            dt_s=dt,
            truth_override={
                "actuator_faults": act_faults,
                "wheel_momentum_nms": st.wheel_momentum_nms,
                "b_field_body_t": st.b_field_body_t,
            },
        )
        cap_online = online_cap.estimate(
            time_s=st.time_s,
            measurement=meas,
            last_command=last_cmd,
            b_field_body_t=meas.mag_body_t,
            dt_s=dt,
        )

    assert cap_oracle is not None and cap_online is not None
    assert cap_oracle.is_oracle is True
    assert cap_online.is_oracle is False

    # Online RLS detects wheel 0 degradation (true=0.4) while healthy wheels remain near 1.0
    assert abs(cap_online.wheels[0].effectiveness_nom - 0.4) < 0.12
    assert cap_online.wheels[1].effectiveness_nom > 0.85
    assert cap_online.wheels[2].effectiveness_nom > 0.85

    # Conservative lower bound must NOT overstate true capability along x!
    assert cap_online.wheels[0].effectiveness_min <= 0.4 + 0.05
    assert cap_online.directional_margin_xyz[0] < cap_online.directional_margin_xyz[1]

    # Gate C2: AMS support function matches Monte Carlo sampled achievable torques for arbitrary v
    rng = np.random.default_rng(42)
    b_true = cfg.reaction_wheels.axis_matrix_body @ np.diag([0.4, 1.0, 1.0])
    u_samples = rng.uniform(
        -cfg.reaction_wheels.torque_limit_nominal_nm,
        cfg.reaction_wheels.torque_limit_nominal_nm,
        size=(3, 5000),
    )
    tau_samples = b_true @ u_samples
    for direction in [
        np.array([1.0, 0.0, 0.0]),
        np.array([1.0, 1.0, 0.0]),
        np.array([0.3, -0.7, 0.6]),
    ]:
        v_hat = direction / np.linalg.norm(direction)
        h_oracle = ams_support_function(cap_oracle, v_hat, conservative=True)
        h_online_cons = ams_support_function(cap_online, v_hat, conservative=True)
        max_sampled = float(np.max(v_hat @ tau_samples))
        # Oracle support upper-bounds all sampled achievable torques tightly
        assert max_sampled <= h_oracle + 1e-9
        assert max_sampled > 0.92 * h_oracle
        # Online conservative support does not overstate true oracle support
        assert h_online_cons <= h_oracle + 0.015
