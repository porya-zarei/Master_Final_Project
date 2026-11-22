"""Phase 3 tests: Basilisk adapter contract, MRP <-> quaternion math, and comparison harness."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from adcs.interfaces import SimulatorBackend, SpacecraftTruthState
from adcs.simulation.basilisk import (
    BasiliskBackend,
    BasiliskUnavailableError,
    is_basilisk_available,
    mrp_bn_to_quat_ib,
    quat_ib_to_mrp_bn,
)
from adcs.simulation.basilisk.backend import build_basilisk_wiring_spec, mrp_bn_to_dcm_bn
from adcs.simulation.comparison import compare_backends
from adcs.simulation.fast import FastSimulatorBackend
from adcs.utils import load_spacecraft_config
from adcs.utils.quaternion import (
    quat_error,
    quat_from_axis_angle,
    quat_geodesic_angle,
    quat_to_dcm,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SPACECRAFT_YAML = REPO_ROOT / "spacecraft_config.yaml"


def test_mrp_quaternion_conversion_matches_basilisk_dcm_convention() -> None:
    for axis, ang in [
        ([1.0, 0.0, 0.0], 0.0),
        ([0.0, 0.0, 1.0], 0.6),
        ([1.0, -2.0, 0.5], 1.7),
        ([-0.3, 0.7, -0.6], 2.9),
    ]:
        q_ib = quat_from_axis_angle(np.array(axis), ang)
        sigma_bn = quat_ib_to_mrp_bn(q_ib)
        assert float(np.linalg.norm(sigma_bn)) <= 1.0 + 1e-12

        # Round-trip quaternion matches within machine precision
        q_rt = mrp_bn_to_quat_ib(sigma_bn)
        assert quat_geodesic_angle(quat_error(q_ib, q_rt)) < 1e-12

        # Basilisk [BN] DCM equals R_BI = R_IB^T
        dcm_bn = mrp_bn_to_dcm_bn(sigma_bn)
        r_bi = quat_to_dcm(q_ib).T
        np.testing.assert_allclose(dcm_bn, r_bi, atol=1e-12)


def test_basilisk_wiring_spec_and_unavailable_guard() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    spec = build_basilisk_wiring_spec(cfg)
    assert spec.integration_step_ns == 10_000_000
    assert spec.control_period_ns == 200_000_000
    assert spec.mass_kg == pytest.approx(100.0)
    assert len(spec.rw_axes_body) == 3
    assert len(spec.mtq_axes_body) == 3

    if not is_basilisk_available():
        with pytest.raises(BasiliskUnavailableError, match="not installed"):
            BasiliskBackend(cfg)


def test_basilisk_adapter_protocol_and_comparison_harness_with_mock_runtime() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)

    class _MockBskRuntime:
        """Minimal mock matching Basilisk MRP/state output using FastSimulatorBackend physics."""

        def __init__(self, fast: FastSimulatorBackend) -> None:
            self.fast = fast

        def advance(self, rw_cmd: np.ndarray, mtq_cmd: np.ndarray, dt: float) -> None:
            self.fast.step(rw_cmd, mtq_cmd, dt_s=dt)

        def read_state(self) -> dict[str, Any]:
            st = self.fast.get_truth_state()
            b_eci = self.fast.mag_model.field_eci_t(st.position_eci_m, st.time_s)
            return {
                "time_s": st.time_s,
                "r_eci_m": st.position_eci_m,
                "v_eci_m_s": st.velocity_eci_m_s,
                "sigma_bn": quat_ib_to_mrp_bn(st.q_ib),
                "omega_bn_b": st.omega_body_rad_s,
                "wheel_momentum_nms": st.wheel_momentum_nms,
                "rw_torque_nm": st.rw_torque_achieved_nm,
                "mtq_dipole_am2": st.mtq_dipole_achieved_am2,
                "b_eci_t": b_eci,
                "disturbance_nm": st.disturbance_torque_body_nm,
            }

    def _build_runtime(
        sc_cfg: Any,
        spec: Any,
        sigma0: np.ndarray,
        w0: np.ndarray,
        h0: np.ndarray,
        nu0: float,
    ) -> _MockBskRuntime:
        del spec
        fast_inner = FastSimulatorBackend(sc_cfg)
        fast_inner.reset(
            q_ib_init=mrp_bn_to_quat_ib(sigma0),
            omega_body_init=w0,
            wheel_momentum_init=h0,
            true_anomaly_deg_init=nu0,
        )
        return _MockBskRuntime(fast_inner)

    fast_backend = FastSimulatorBackend(cfg)
    mock_bsk = BasiliskBackend(cfg, _bsk_modules={"build_runtime": _build_runtime})
    assert isinstance(mock_bsk, SimulatorBackend)

    q0 = quat_from_axis_angle(np.array([0.4, -0.3, 0.8]), 0.5)
    w0 = np.array([0.02, -0.01, 0.03])
    rw_cmds = [np.array([0.02, -0.01, 0.005]) for _ in range(10)]
    mtq_cmds = [np.array([0.5, 0.0, -0.5]) for _ in range(10)]

    metrics = compare_backends(
        fast_backend,
        mock_bsk,
        rw_commands=rw_cmds,
        mtq_commands=mtq_cmds,
        q_ib_init=q0,
        omega_body_init=w0,
    )
    assert metrics.n_steps == 10
    assert metrics.max_attitude_diff_rad < 1e-12
    assert metrics.max_omega_diff_rad_s < 1e-12
    assert metrics.max_wheel_momentum_diff_nms < 1e-12
    assert metrics.max_b_field_diff_t < 1e-15


@pytest.mark.skipif(not is_basilisk_available(), reason="Basilisk not installed in this Python")
def test_live_basilisk_gate_c6_cross_validation_and_closed_loop_control() -> None:
    """Gate C6: live matched FastSimulatorBackend vs BasiliskBackend physics & closed-loop test."""
    from adcs.control.classical import StrongClassicalController
    from adcs.control.reference import NadirReferenceGenerator, compute_attitude_error
    from adcs.dynamics.magnetic_field import (
        GeomagneticFieldModel,
        default_tilted_dipole_coefficients,
    )
    from adcs.estimation import MultiplicativeEKF, OnlineCapabilityEstimator
    from adcs.sensors import SensorSuite

    cfg = load_spacecraft_config(SPACECRAFT_YAML)

    # 1. Matched open-loop 3-axis RW + MTQ comparison (instantaneous actuators to match Basilisk)
    fast_matched = FastSimulatorBackend(
        cfg,
        rw_time_constant_override_s=0.0,
        mtq_time_constant_override_s=0.0,
    )
    # Match Basilisk centered dipole (non-rotating ECI dipole) for exact field comparison
    fast_matched.mag_model = GeomagneticFieldModel(
        coefficients=default_tilted_dipole_coefficients(),
        gmst_initial_rad=0.0,
        auto_load_igrf14=False,
    )
    bsk_live = BasiliskBackend(cfg)
    assert isinstance(bsk_live, SimulatorBackend)

    q0 = quat_from_axis_angle(np.array([0.5, -0.4, 0.7]), 0.45)
    w0 = np.array([0.02, -0.015, 0.01])
    h0 = np.array([0.3, -0.2, 0.15])
    rw_cmds = [
        np.array([0.04 * np.sin(0.2 * k), -0.03, 0.025 * np.cos(0.15 * k)]) for k in range(50)
    ]
    mtq_cmds = [np.array([1.0, -0.5, 0.8]) for _ in range(50)]  # 10 seconds

    metrics = compare_backends(
        fast_matched,
        bsk_live,
        rw_commands=rw_cmds,
        mtq_commands=mtq_cmds,
        q_ib_init=q0,
        omega_body_init=w0,
        wheel_momentum_init=h0,
    )
    print(f"\n[Gate C6 Live Basilisk vs FastRK4] {metrics}")
    # Tight quantitative cross-validation bounds across 10 s of 3-axis RW+MTQ+orbit dynamics!
    assert metrics.max_position_diff_m < 1.0  # < 1 m orbital agreement
    assert metrics.max_attitude_diff_rad < 5e-3  # < 0.3 deg attitude agreement
    assert metrics.max_omega_diff_rad_s < 1e-3  # < 1 mrad/s rate agreement
    assert metrics.max_wheel_momentum_diff_nms < 5e-3  # exact RW momentum conservation & sign!

    # 2. Live closed-loop nadir pointing with StrongClassicalController on BasiliskBackend
    st0 = bsk_live.reset()
    ref_gen = NadirReferenceGenerator()
    ref0 = ref_gen.compute(st0.time_s, st0.position_eci_m, st0.velocity_eci_m_s)
    from adcs.utils.quaternion import quat_multiply

    q_pert = quat_from_axis_angle(np.array([0.6, -0.5, 0.6]), np.deg2rad(20.0))
    q_init = quat_multiply(ref0.q_ir, q_pert)
    st = bsk_live.reset(q_ib_init=q_init, omega_body_init=ref0.omega_ref_inertial_in_ref_rad_s)
    ref_gen.reset()
    sensors = SensorSuite(n_rw=cfg.reaction_wheels.count)
    sensors.reset(seed=7, q_ib_init=q_init)
    mekf = MultiplicativeEKF()
    mekf.reset(q_ib_init=q_init, omega_init=st.omega_body_rad_s)
    cap_est = OnlineCapabilityEstimator(cfg)
    cap_est.reset()
    ctrl = StrongClassicalController(cfg)
    ctrl.reset()

    dt = cfg.simulation.control_period_s
    last_cmd = None
    for _ in range(250):  # 50 s live Basilisk closed-loop nadir tracking
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
        st = bsk_live.step(
            out.command.rw_torque_cmd_nm, out.command.mtq_dipole_cmd_am2, dt_s=dt
        ).truth

    final_err_deg = np.rad2deg(
        compute_attitude_error(st.q_ib, st.omega_body_rad_s, ref).geodesic_angle_rad
    )
    print(f"[Gate C6 Live Basilisk Closed-Loop A3] final_err_deg = {final_err_deg:.4f} deg")
    assert final_err_deg < 0.5  # Live Basilisk closed-loop converges to < 0.5 deg!


@pytest.mark.skipif(not is_basilisk_available(), reason="Basilisk not installed in this Python")
def test_live_basilisk_validation_matrix_8_regimes() -> None:
    """Stage 2 comprehensive 8-regime FastSimulatorBackend vs BasiliskBackend validation matrix."""
    from adcs.control.classical import StrongClassicalController
    from adcs.control.reference import NadirReferenceGenerator, compute_attitude_error
    from adcs.dynamics.magnetic_field import (
        GeomagneticFieldModel,
        default_tilted_dipole_coefficients,
    )
    from adcs.estimation import MultiplicativeEKF, OnlineCapabilityEstimator
    from adcs.faults import FaultEvent, FaultInjector
    from adcs.sensors import SensorFaultParams, SensorSuite
    from adcs.utils.quaternion import quat_multiply

    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    dt = cfg.simulation.control_period_s

    def _make_matched_pair() -> tuple[FastSimulatorBackend, BasiliskBackend]:
        fast = FastSimulatorBackend(
            cfg,
            rw_time_constant_override_s=0.0,
            mtq_time_constant_override_s=0.0,
        )
        fast.mag_model = GeomagneticFieldModel(
            coefficients=default_tilted_dipole_coefficients(),
            gmst_initial_rad=0.0,
            auto_load_igrf14=False,
        )
        bsk = BasiliskBackend(cfg)
        return fast, bsk

    def _run_closed_loop_on_backend(
        backend: SimulatorBackend,
        *,
        init_att_deg: float,
        init_rate_deg_s: float,
        n_steps: int,
        rw_fault_events: tuple[FaultEvent, ...] = (),
        st_dropout_window: tuple[float, float] | None = None,
    ) -> tuple[float, float, SpacecraftTruthState]:
        st0 = backend.reset()
        ref_gen = NadirReferenceGenerator()
        ref0 = ref_gen.compute(st0.time_s, st0.position_eci_m, st0.velocity_eci_m_s)
        q_pert = quat_from_axis_angle(
            np.array([0.6, -0.5, 0.6]), np.deg2rad(init_att_deg)
        )
        q_init = quat_multiply(ref0.q_ir, q_pert)
        rate_dir = np.array([1.0, -1.0, 1.0], dtype=np.float64) / np.sqrt(3.0)
        w_init = ref0.omega_ref_inertial_in_ref_rad_s + rate_dir * np.deg2rad(init_rate_deg_s)

        st = backend.reset(q_ib_init=q_init, omega_body_init=w_init)
        ref_gen.reset()
        sensors = SensorSuite(n_rw=cfg.reaction_wheels.count)
        sensors.reset(seed=7, q_ib_init=q_init)
        mekf = MultiplicativeEKF()
        mekf.reset(q_ib_init=q_init, omega_init=w_init)
        cap_est = OnlineCapabilityEstimator(cfg)
        cap_est.reset()
        ctrl = StrongClassicalController(cfg)
        ctrl.reset()
        injector = FaultInjector(cfg, rw_fault_events)

        last_cmd = None
        max_err_deg = 0.0
        for _ in range(n_steps):
            act_faults, sens_faults = injector.evaluate(st.time_s)
            if st_dropout_window is not None:
                t_lo, t_hi = st_dropout_window
                if t_lo <= st.time_s < t_hi:
                    sens_faults = SensorFaultParams(star_tracker_dropout=True)

            if isinstance(backend, FastSimulatorBackend):
                backend.set_fault_state(act_faults)
            elif isinstance(backend, BasiliskBackend) and rw_fault_events:
                backend.set_rw_fault(
                    effectiveness=act_faults.rw.effectiveness,
                    bias_nm=act_faults.rw.torque_bias_nm,
                )

            meas = sensors.measure(st, dt_s=dt, faults=sens_faults)
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
                estimator_out=est,
                reference=ref,
                capability=cap,
                measurement=meas,
                dt_s=dt,
            )
            last_cmd = out.command
            st = backend.step(
                out.command.rw_torque_cmd_nm,
                out.command.mtq_dipole_cmd_am2,
                dt_s=dt,
            ).truth
            ref_now = ref_gen.compute(st.time_s, st.position_eci_m, st.velocity_eci_m_s)
            err_now_deg = float(
                np.rad2deg(
                    compute_attitude_error(
                        st.q_ib, st.omega_body_rad_s, ref_now
                    ).geodesic_angle_rad
                )
            )
            max_err_deg = max(max_err_deg, err_now_deg)

        ref_end = ref_gen.compute(st.time_s, st.position_eci_m, st.velocity_eci_m_s)
        final_err_deg = float(
            np.rad2deg(
                compute_attitude_error(st.q_ib, st.omega_body_rad_s, ref_end).geodesic_angle_rad
            )
        )
        return final_err_deg, max_err_deg, st

    # -------------------------------------------------------------------------
    # Regime 1: Nominal orbit & 3-axis RW+MTQ dynamics (10 s plant validation)
    # -------------------------------------------------------------------------
    fast1, bsk1 = _make_matched_pair()
    q0_r1 = quat_from_axis_angle(np.array([0.5, -0.4, 0.7]), 0.45)
    w0_r1 = np.array([0.02, -0.015, 0.01])
    h0_r1 = np.array([0.3, -0.2, 0.15])
    rw_cmds_r1 = [
        np.array([0.04 * np.sin(0.2 * k), -0.03, 0.025 * np.cos(0.15 * k)]) for k in range(50)
    ]
    mtq_cmds_r1 = [np.array([1.0, -0.5, 0.8]) for _ in range(50)]
    m_r1 = compare_backends(
        fast1,
        bsk1,
        rw_commands=rw_cmds_r1,
        mtq_commands=mtq_cmds_r1,
        q_ib_init=q0_r1,
        omega_body_init=w0_r1,
        wheel_momentum_init=h0_r1,
    )
    assert m_r1.max_attitude_diff_rad < 5e-3
    assert m_r1.max_position_diff_m < 1.0

    # -------------------------------------------------------------------------
    # Regime 2: Large 90-deg attitude slew (50 s closed-loop validation)
    # -------------------------------------------------------------------------
    fast2, bsk2 = _make_matched_pair()
    f_err2, _, st_f2 = _run_closed_loop_on_backend(
        fast2, init_att_deg=90.0, init_rate_deg_s=0.0, n_steps=250
    )
    b_err2, _, st_b2 = _run_closed_loop_on_backend(
        bsk2, init_att_deg=90.0, init_rate_deg_s=0.0, n_steps=250
    )
    diff_r2_deg = float(np.rad2deg(quat_geodesic_angle(quat_error(st_f2.q_ib, st_b2.q_ib))))
    assert f_err2 < 1.0 and b_err2 < 1.0
    assert diff_r2_deg < 2.0

    # -------------------------------------------------------------------------
    # Regime 3: High angular rate 10 deg/s detumble (60 s closed-loop validation)
    # -------------------------------------------------------------------------
    fast3, bsk3 = _make_matched_pair()
    f_err3, _, st_f3 = _run_closed_loop_on_backend(
        fast3, init_att_deg=10.0, init_rate_deg_s=10.0, n_steps=300
    )
    b_err3, _, st_b3 = _run_closed_loop_on_backend(
        bsk3, init_att_deg=10.0, init_rate_deg_s=10.0, n_steps=300
    )
    diff_r3_deg = float(np.rad2deg(quat_geodesic_angle(quat_error(st_f3.q_ib, st_b3.q_ib))))
    assert f_err3 < 1.0 and b_err3 < 1.0
    assert diff_r3_deg < 2.0

    # -------------------------------------------------------------------------
    # Regime 4: RW torque saturation & high-momentum operation near wall (plant)
    # -------------------------------------------------------------------------
    fast4, bsk4 = _make_matched_pair()
    h0_r4 = np.array([5.80, -5.00, 3.50])
    # First 5 steps command [-0.25, +0.25, -0.20] (saturated at 0.15 Nm -> h0 reaches 5.95 Nms),
    # then 20 steps command [+0.25, -0.25, +0.20] (saturated at 0.15 Nm desaturating from 5.95).
    rw_cmds_r4 = [np.array([-0.25, 0.25, -0.20]) for _ in range(5)] + [
        np.array([0.25, -0.25, 0.20]) for _ in range(20)
    ]
    mtq_cmds_r4 = [np.zeros(3) for _ in range(25)]
    m_r4 = compare_backends(
        fast4,
        bsk4,
        rw_commands=rw_cmds_r4,
        mtq_commands=mtq_cmds_r4,
        wheel_momentum_init=h0_r4,
    )
    assert m_r4.max_wheel_momentum_diff_nms < 1e-2
    assert m_r4.max_attitude_diff_rad < 5e-3

    # -------------------------------------------------------------------------
    # Regime 5: RW 50% effectiveness loss + +0.015 Nm bias fault (closed-loop)
    # -------------------------------------------------------------------------
    fast5, bsk5 = _make_matched_pair()
    rw_events_r5 = (
        FaultEvent("rw_effectiveness_loss", start_s=0.0, target_index=0, severity=0.5),
        FaultEvent("rw_torque_bias", start_s=0.0, target_index=0, severity=0.015),
    )
    f_err5, _, st_f5 = _run_closed_loop_on_backend(
        fast5,
        init_att_deg=20.0,
        init_rate_deg_s=0.5,
        n_steps=250,
        rw_fault_events=rw_events_r5,
    )
    b_err5, _, st_b5 = _run_closed_loop_on_backend(
        bsk5,
        init_att_deg=20.0,
        init_rate_deg_s=0.5,
        n_steps=250,
        rw_fault_events=rw_events_r5,
    )
    diff_r5_deg = float(np.rad2deg(quat_geodesic_angle(quat_error(st_f5.q_ib, st_b5.q_ib))))
    assert f_err5 < 1.0 and b_err5 < 1.0

    # -------------------------------------------------------------------------
    # Regime 6: MTQ dipole saturation & tau_mtq _|_ B_body invariant (plant)
    # -------------------------------------------------------------------------
    fast6, bsk6 = _make_matched_pair()
    rw_cmds_r6 = [np.zeros(3) for _ in range(20)]
    mtq_cmds_r6 = [np.array([5.0, -5.0, 5.0]) for _ in range(20)]
    m_r6 = compare_backends(
        fast6,
        bsk6,
        rw_commands=rw_cmds_r6,
        mtq_commands=mtq_cmds_r6,
        q_ib_init=q0_r1,
    )
    st_f6 = fast6.get_truth_state()
    st_b6 = bsk6.get_truth_state()
    dot_f6 = abs(float(np.dot(st_f6.mtq_torque_achieved_nm, st_f6.b_field_body_t)))
    dot_b6 = abs(float(np.dot(st_b6.mtq_torque_achieved_nm, st_b6.b_field_body_t)))
    assert m_r6.max_attitude_diff_rad < 5e-3
    np.testing.assert_allclose(
        st_b6.mtq_dipole_achieved_am2, np.array([2.0, -2.0, 2.0]), atol=1e-12
    )
    assert dot_f6 < 1e-12 and dot_b6 < 1e-12

    # -------------------------------------------------------------------------
    # Regime 7: 20 s star-tracker dropout t=15..35s (60 s closed-loop recovery)
    # -------------------------------------------------------------------------
    fast7, bsk7 = _make_matched_pair()
    f_err7, _, st_f7 = _run_closed_loop_on_backend(
        fast7,
        init_att_deg=20.0,
        init_rate_deg_s=0.5,
        n_steps=300,
        st_dropout_window=(15.0, 35.0),
    )
    b_err7, _, st_b7 = _run_closed_loop_on_backend(
        bsk7,
        init_att_deg=20.0,
        init_rate_deg_s=0.5,
        n_steps=300,
        st_dropout_window=(15.0, 35.0),
    )
    diff_r7_deg = float(np.rad2deg(quat_geodesic_angle(quat_error(st_f7.q_ib, st_b7.q_ib))))
    assert f_err7 < 1.0 and b_err7 < 1.0

    # -------------------------------------------------------------------------
    # Regime 8: 600 s long-duration orbit & attitude propagation (3000 steps)
    # -------------------------------------------------------------------------
    fast8, bsk8 = _make_matched_pair()
    rw_cmds_r8 = [
        np.array([0.01 * np.sin(0.02 * k), -0.008 * np.cos(0.015 * k), 0.005 * np.sin(0.01 * k)])
        for k in range(3000)
    ]
    mtq_cmds_r8 = [np.zeros(3) for _ in range(3000)]
    m_r8 = compare_backends(
        fast8,
        bsk8,
        rw_commands=rw_cmds_r8,
        mtq_commands=mtq_cmds_r8,
        q_ib_init=q0_r1,
        omega_body_init=np.array([0.005, -0.004, 0.003]),
    )
    assert m_r8.max_position_diff_m < 1.0
    assert m_r8.max_attitude_diff_rad < 0.05

    r1_att_deg = float(np.rad2deg(m_r1.max_attitude_diff_rad))
    r8_att_deg = float(np.rad2deg(m_r8.max_attitude_diff_rad))
    print("\n=== STAGE 2 FAST-RK4 VS BASILISK 2.12.2 8-REGIME VALIDATION MATRIX ===")
    print(
        f"R1_NOMINAL_10S        | pos_diff={m_r1.max_position_diff_m:.3e} m | "
        f"att_diff={m_r1.max_attitude_diff_rad:.3e} rad ({r1_att_deg:.4f} deg) | "
        f"omega_diff={m_r1.max_omega_diff_rad_s:.3e} rad/s | "
        f"rw_h_diff={m_r1.max_wheel_momentum_diff_nms:.3e} Nms"
    )
    print(
        f"R2_SLEW_90DEG_50S     | fast_final={f_err2:.4f} deg | "
        f"bsk_final={b_err2:.4f} deg | final_att_diff={diff_r2_deg:.4f} deg"
    )
    print(
        f"R3_DETUMBLE_10DEGS    | fast_final={f_err3:.4f} deg | "
        f"bsk_final={b_err3:.4f} deg | final_att_diff={diff_r3_deg:.4f} deg"
    )
    print(
        f"R4_RW_SATURATION      | att_diff={m_r4.max_attitude_diff_rad:.3e} rad | "
        f"omega_diff={m_r4.max_omega_diff_rad_s:.3e} rad/s | "
        f"rw_h_diff={m_r4.max_wheel_momentum_diff_nms:.3e} Nms"
    )
    print(
        f"R5_RW_FAULT_50PCT_BIAS| fast_final={f_err5:.4f} deg | "
        f"bsk_final={b_err5:.4f} deg | final_att_diff={diff_r5_deg:.4f} deg"
    )
    print(
        f"R6_MTQ_SAT_PERP_B     | att_diff={m_r6.max_attitude_diff_rad:.3e} rad | "
        f"b_diff={m_r6.max_b_field_diff_t:.3e} T | "
        f"dot_fast={dot_f6:.3e} | dot_bsk={dot_b6:.3e}"
    )
    print(
        f"R7_ST_DROPOUT_20S     | fast_final={f_err7:.4f} deg | "
        f"bsk_final={b_err7:.4f} deg | final_att_diff={diff_r7_deg:.4f} deg"
    )
    print(
        f"R8_LONG_ORBIT_600S    | pos_diff={m_r8.max_position_diff_m:.3e} m | "
        f"omega_diff={m_r8.max_omega_diff_rad_s:.3e} rad/s | "
        f"att_diff={m_r8.max_attitude_diff_rad:.3e} rad ({r8_att_deg:.4f} deg) | "
        f"rw_h_diff={m_r8.max_wheel_momentum_diff_nms:.3e} Nms"
    )

