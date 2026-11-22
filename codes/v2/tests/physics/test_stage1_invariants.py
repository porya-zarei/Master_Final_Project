"""Stage 1 & Stage 2 physics and architectural invariant verification suite.

Covers the four critical invariants required by the technical review:
1. Nominal Residual Suppression Invariant (CCR v2 with nonzero policy vs StrongClassicalController)
2. Online RLS Capability Stress Matrix (unexcited confidence cap, low vs high excitation delay,
   S4 torque bias vs gain separation, and fault removal recovery)
3. RW Mechanical Bearing Friction, Stiction Deadband & Internal Angular Momentum Conservation
4. Physical Authority Infeasibility Detection & Instantaneous RL Shutdown (S2/S3)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from adcs.actuators.models import ActuatorFaultState, MTQFaultParams, RWFaultParams
from adcs.control.allocation.allocator import detect_underactuated_axis
from adcs.control.classical import StrongClassicalController
from adcs.control.residual_rl import CCRController, CCRControllerConfig
from adcs.estimation.capability import OnlineCapabilityEstimator
from adcs.evaluation.runner import EpisodeRunner
from adcs.faults import build_default_scenario_catalog
from adcs.interfaces.types import (
    ActuatorCommand,
    ControlStepOutput,
    FloatArray,
    SensorMeasurement,
    SupervisorMode,
)
from adcs.simulation.fast import FastSimulatorBackend
from adcs.utils import load_spacecraft_config
from adcs.utils.quaternion import quat_rotate_vec

REPO_ROOT = Path(__file__).resolve().parents[2]
SPACECRAFT_YAML = REPO_ROOT / "spacecraft_config.yaml"


class _ConstantNonzeroPolicy:
    """Deliberately aggressive constant residual policy to test deterministic gating invariants."""

    def __init__(self, action: FloatArray | None = None) -> None:
        self._action = (
            np.array([0.8, -0.8, 0.8], dtype=np.float64)
            if action is None
            else np.asarray(action, dtype=np.float64)
        )

    def predict(self, observation: FloatArray, *, deterministic: bool = True) -> FloatArray:
        del observation, deterministic
        return self._action.copy()


class _DiagnosticSpyCCRController(CCRController):
    """CCRController wrapper recording per-step ControlStepOutput diagnostics."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.outputs: list[ControlStepOutput] = []

    def reset(self) -> None:
        super().reset()
        self.outputs = []

    def compute(self, **kwargs: object) -> ControlStepOutput:
        out = super().compute(**kwargs)  # type: ignore[arg-type]
        self.outputs.append(out)
        return out


def test_nominal_residual_suppression_invariant() -> None:
    """Test 1: Nonzero policy under CCR v2 is suppressed to ~0 on quiet nominal pointing."""
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    catalog = build_default_scenario_catalog()
    scenario = catalog["S0_nominal_val"]
    runner = EpisodeRunner(cfg)

    ccr_ctrl = CCRController(
        cfg,
        policy=_ConstantNonzeroPolicy(np.array([0.8, -0.8, 0.8])),
        config=CCRControllerConfig(name="A7_ccr_eso_test", use_eso_backbone=True),
    )
    a3_ctrl = StrongClassicalController(cfg)

    ccr_log = runner.run_episode(ccr_ctrl, scenario, seed=10, record_trace=True)
    a3_log = runner.run_episode(a3_ctrl, scenario, seed=10, record_trace=True)

    post_steps = [s for s in ccr_log.steps if s.time_s >= 40.0]
    assert len(post_steps) > 0
    mean_post_rl_gated_nm = float(
        np.mean([float(np.linalg.norm(s.tau_rl_gated_nm)) for s in post_steps])
    )
    assert mean_post_rl_gated_nm < 1e-4, (
        f"Expected post-transient ||tau_rl_gated_nm|| < 1e-4 N*m on S0, got {mean_post_rl_gated_nm}"
    )

    # Steady-state window (t >= 70 s) after the initial 20-deg acquisition transient settles
    ccr_steady_rms = float(
        np.sqrt(np.mean([s.att_err_deg**2 for s in ccr_log.steps if s.time_s >= 70.0]))
    )
    a3_steady_rms = float(
        np.sqrt(np.mean([s.att_err_deg**2 for s in a3_log.steps if s.time_s >= 70.0]))
    )
    rms_diff_deg = abs(ccr_steady_rms - a3_steady_rms)
    assert rms_diff_deg < 0.02, (
        f"Expected CCR v2 steady RMS attitude error within 0.02 deg of StrongClassicalController, "
        f"got CCR={ccr_steady_rms:.4f} vs A3={a3_steady_rms:.4f}"
    )


def _synthetic_meas(
    time_s: float,
    rw_speed_rad_s: FloatArray,
    mag_body_t: FloatArray | None = None,
) -> SensorMeasurement:
    return SensorMeasurement(
        time_s=time_s,
        gyro_rad_s=np.zeros(3, dtype=np.float64),
        gyro_valid=True,
        star_tracker_q_ib=np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64),
        star_tracker_valid=True,
        star_tracker_age_s=0.0,
        mag_body_t=(
            np.array([2.0e-5, -1.0e-5, 1.5e-5], dtype=np.float64)
            if mag_body_t is None
            else mag_body_t.copy()
        ),
        mag_valid=True,
        rw_speed_rad_s=rw_speed_rad_s.copy(),
        rw_speed_valid=(True, True, True),
    )


def test_online_rls_capability_stress_matrix() -> None:
    """Test 2: Online RLS capability estimator across unexcited, low/high exc, S4 bias, recovery."""
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    dt = cfg.simulation.control_period_s

    # (a) Long-duration healthy unexcited steady pointing (60 s, zero torque commands)
    est_a = OnlineCapabilityEstimator(cfg)
    est_a.reset()
    zero_cmd = ActuatorCommand(
        rw_torque_cmd_nm=np.zeros(3, dtype=np.float64),
        mtq_dipole_cmd_am2=np.zeros(3, dtype=np.float64),
        tau_request_nm=np.zeros(3, dtype=np.float64),
        tau_allocated_nm=np.zeros(3, dtype=np.float64),
    )
    false_underactuated_count = 0
    cap_a = None
    for k in range(int(round(60.0 / dt)) + 1):
        t = k * dt
        meas = _synthetic_meas(t, np.zeros(3, dtype=np.float64))
        cap_a = est_a.estimate(
            time_s=t,
            measurement=meas,
            last_command=zero_cmd if k > 0 else None,
            b_field_body_t=meas.mag_body_t,
            dt_s=dt,
        )
        if detect_underactuated_axis(cfg.reaction_wheels.axis_matrix_body, cap_a) is not None:
            false_underactuated_count += 1

    assert cap_a is not None
    assert any(cap_a.diagnostics["unverified_unexcited"])
    assert all(cap_a.diagnostics["unverified_unexcited"])
    assert 0.70 < cap_a.confidence <= 0.85
    assert np.all(cap_a.directional_margin_xyz > 0.75)
    assert false_underactuated_count == 0

    # (b) Fault detection delay under low excitation vs high excitation (60% loss on wheel 0)
    def _run_degradation_trial(u0_amp_nm: float, u1_amp_nm: float) -> tuple[float, object]:
        sim = FastSimulatorBackend(cfg, gravity_gradient_enabled=False)
        truth = sim.reset()
        faults = ActuatorFaultState(
            rw=RWFaultParams.nominal(cfg.reaction_wheels),
            mtq=MTQFaultParams.nominal(cfg.magnetorquers),
        )
        faults.rw.effectiveness[0] = 0.40  # 60% loss on wheel 0
        sim.set_fault_state(faults)

        est = OnlineCapabilityEstimator(cfg)
        est.reset()
        last_cmd: ActuatorCommand | None = None
        detect_time_s = float("inf")
        cap = None
        for k in range(int(round(15.0 / dt))):
            meas = _synthetic_meas(truth.time_s, truth.wheel_speed_rad_s, truth.b_field_body_t)
            cap = est.estimate(
                time_s=truth.time_s,
                measurement=meas,
                last_command=last_cmd,
                b_field_body_t=meas.mag_body_t,
                dt_s=dt,
            )
            if cap.wheels[0].effectiveness_nom < 0.55 and not np.isfinite(detect_time_s):
                detect_time_s = truth.time_s
            s0 = 1.0 if (k // 2) % 2 == 0 else -1.0
            s1 = 1.0 if (k // 3) % 2 == 0 else -1.0
            u_cmd = np.array([u0_amp_nm * s0, u1_amp_nm * s1, 0.0], dtype=np.float64)
            last_cmd = ActuatorCommand(
                rw_torque_cmd_nm=u_cmd,
                mtq_dipole_cmd_am2=np.zeros(3, dtype=np.float64),
                tau_request_nm=u_cmd,
                tau_allocated_nm=u_cmd,
            )
            truth = sim.step(u_cmd, np.zeros(3, dtype=np.float64), dt_s=dt).truth
        return detect_time_s, cap

    t_high, cap_high = _run_degradation_trial(u0_amp_nm=0.08, u1_amp_nm=0.08)
    t_low, _ = _run_degradation_trial(u0_amp_nm=0.011, u1_amp_nm=0.0)
    assert t_high < 6.0, f"High excitation 60% loss should converge in < 6 s, got {t_high:.2f} s"
    assert t_high < t_low, (
        f"High excitation ({t_high:.2f} s) must detect faster than low excitation ({t_low:.2f} s)"
    )
    # Active high-excitation healthy wheel 1 keeps higher confidence than >10s unexcited wheel 2
    assert cap_high.wheels[1].confidence > cap_high.wheels[2].confidence  # type: ignore[union-attr]

    # (c) S4 torque bias (-0.03 Nm on healthy wheel 1) vs effectiveness separation
    sim_c = FastSimulatorBackend(cfg, gravity_gradient_enabled=False)
    truth_c = sim_c.reset()
    faults_c = ActuatorFaultState(
        rw=RWFaultParams.nominal(cfg.reaction_wheels),
        mtq=MTQFaultParams.nominal(cfg.magnetorquers),
    )
    faults_c.rw.torque_bias_nm[1] = -0.03
    sim_c.set_fault_state(faults_c)

    est_c = OnlineCapabilityEstimator(cfg)
    est_c.reset()
    last_cmd_c: ActuatorCommand | None = None
    cap_c = None
    for k in range(int(round(20.0 / dt))):
        meas_c = _synthetic_meas(
            truth_c.time_s, truth_c.wheel_speed_rad_s, truth_c.b_field_body_t
        )
        cap_c = est_c.estimate(
            time_s=truth_c.time_s,
            measurement=meas_c,
            last_command=last_cmd_c,
            b_field_body_t=meas_c.mag_body_t,
            dt_s=dt,
        )
        # Alternating command around +0.03 +/- 0.04 Nm so u + bias crosses zero
        u1 = 0.03 + 0.04 * float(np.sin(0.5 * k))
        u_cmd_c = np.array([0.0, u1, 0.0], dtype=np.float64)
        last_cmd_c = ActuatorCommand(
            rw_torque_cmd_nm=u_cmd_c,
            mtq_dipole_cmd_am2=np.zeros(3, dtype=np.float64),
            tau_request_nm=u_cmd_c,
            tau_allocated_nm=u_cmd_c,
        )
        truth_c = sim_c.step(u_cmd_c, np.zeros(3, dtype=np.float64), dt_s=dt).truth

    assert cap_c is not None
    assert abs(cap_c.wheels[1].bias_est_nm - (-0.03)) < 0.01, (
        f"Expected bias_est_nm ~ -0.03 within 0.01 N*m, got {cap_c.wheels[1].bias_est_nm:.4f}"
    )
    assert cap_c.wheels[1].effectiveness_nom > 0.75, (
        f"Expected healthy wheel 1 effectiveness_nom > 0.75 under bias, "
        f"got {cap_c.wheels[1].effectiveness_nom:.4f}"
    )

    # (d) Fault removal recovery: restore wheel 0 effectiveness from 0.40 back to 1.0
    sim_d = FastSimulatorBackend(cfg, gravity_gradient_enabled=False)
    truth_d = sim_d.reset()
    faults_d = ActuatorFaultState(
        rw=RWFaultParams.nominal(cfg.reaction_wheels),
        mtq=MTQFaultParams.nominal(cfg.magnetorquers),
    )
    faults_d.rw.effectiveness[0] = 0.40
    sim_d.set_fault_state(faults_d)
    est_d = OnlineCapabilityEstimator(cfg)
    est_d.reset()
    last_cmd_d: ActuatorCommand | None = None
    cap_d = None
    for k in range(int(round(20.0 / dt))):
        if truth_d.time_s >= 8.0:
            faults_d.rw.effectiveness[0] = 1.0
            sim_d.set_fault_state(faults_d)
        meas_d = _synthetic_meas(
            truth_d.time_s, truth_d.wheel_speed_rad_s, truth_d.b_field_body_t
        )
        cap_d = est_d.estimate(
            time_s=truth_d.time_s,
            measurement=meas_d,
            last_command=last_cmd_d,
            b_field_body_t=meas_d.mag_body_t,
            dt_s=dt,
        )
        if 7.0 <= truth_d.time_s < 8.0:
            assert cap_d.wheels[0].effectiveness_nom < 0.50
        u0 = 0.08 * (1.0 if (k // 2) % 2 == 0 else -1.0)
        u_cmd_d = np.array([u0, 0.0, 0.0], dtype=np.float64)
        last_cmd_d = ActuatorCommand(
            rw_torque_cmd_nm=u_cmd_d,
            mtq_dipole_cmd_am2=np.zeros(3, dtype=np.float64),
            tau_request_nm=u_cmd_d,
            tau_allocated_nm=u_cmd_d,
        )
        truth_d = sim_d.step(u_cmd_d, np.zeros(3, dtype=np.float64), dt_s=dt).truth

    assert cap_d is not None
    assert cap_d.wheels[0].effectiveness_nom > 0.85, (
        f"Expected wheel 0 effectiveness_nom to recover > 0.85 after fault removal, "
        f"got {cap_d.wheels[0].effectiveness_nom:.4f}"
    )


def test_rw_bearing_friction_stiction_and_momentum_conservation() -> None:
    """Test 3: Stiction deadband, post-clip bearing friction braking, and H_total conservation."""
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    sim = FastSimulatorBackend(
        cfg,
        gravity_gradient_enabled=False,
        residual_dipole_override_am2=np.zeros(3, dtype=np.float64),
    )

    def _make_friction_faults() -> ActuatorFaultState:
        rw_f = RWFaultParams.nominal(cfg.reaction_wheels)
        rw_f.coulomb_nm = np.array([0.012, 0.010, 0.008], dtype=np.float64)
        rw_f.viscous_nm_per_rad_s = np.array([1.0e-4, 1.0e-4, 1.0e-4], dtype=np.float64)
        rw_f.stiction_band_nm = np.array([0.01, 0.01, 0.01], dtype=np.float64)
        return ActuatorFaultState(
            rw=rw_f,
            mtq=MTQFaultParams.nominal(cfg.magnetorquers),
        )

    # 1. Stiction deadband check: |omega_wheel| < 1e-3 and |tau_elec| <= stiction_band -> dh_w = 0
    st0 = sim.reset(
        q_ib_init=np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64),
        omega_body_init=np.zeros(3, dtype=np.float64),
        wheel_momentum_init=np.zeros(3, dtype=np.float64),
    )
    sim.set_fault_state(_make_friction_faults())
    sub_stiction_cmd = np.array([0.006, -0.008, 0.005], dtype=np.float64)
    for _ in range(5):
        st0 = sim.step(sub_stiction_cmd, np.zeros(3, dtype=np.float64)).truth
        # Electrical motor lag state is non-zero, yet stiction holds rotor stationary (dh_w == 0)
        assert np.all(np.abs(sim._tau_rw_state) > 1e-4)
        np.testing.assert_allclose(st0.wheel_momentum_nms, np.zeros(3), atol=1e-15)
        np.testing.assert_allclose(st0.rw_torque_achieved_nm, np.zeros(3), atol=1e-15)

    # 2. Post-clip mechanical friction check & total angular momentum conservation
    st = sim.reset(
        q_ib_init=np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64),
        omega_body_init=np.array([0.04, -0.03, 0.02], dtype=np.float64),
        wheel_momentum_init=np.array([1.5, -1.0, 0.8], dtype=np.float64),
    )
    sim.set_fault_state(_make_friction_faults())
    j_mat = cfg.inertia_matrix_kg_m2
    a_rw = cfg.reaction_wheels.axis_matrix_body
    tau_lim = cfg.reaction_wheels.torque_limit_nominal_nm
    h_tot_0 = quat_rotate_vec(st.q_ib, j_mat @ st.omega_body_rad_s + a_rw @ st.wheel_momentum_nms)

    max_achieved_braking_tau0 = 0.0
    for k in range(30):
        # Wheel 0 has omega_wheel > 0; commanding +tau_lim (braking) + bearing friction > tau_lim
        cmd = np.array(
            [tau_lim, -0.08 * np.cos(0.2 * k), 0.06 * np.sin(0.15 * k)],
            dtype=np.float64,
        )
        st = sim.step(cmd, np.zeros(3, dtype=np.float64)).truth
        max_achieved_braking_tau0 = max(
            max_achieved_braking_tau0, float(st.rw_torque_achieved_nm[0])
        )

        h_tot_now = quat_rotate_vec(
            st.q_ib, j_mat @ st.omega_body_rad_s + a_rw @ st.wheel_momentum_nms
        )
        np.testing.assert_allclose(h_tot_now, h_tot_0, atol=1e-10)

    assert max_achieved_braking_tau0 > tau_lim + 0.01, (
        f"Mechanical bearing friction must add to motor braking torque without being clipped "
        f"by motor limit {tau_lim}, got max_achieved={max_achieved_braking_tau0:.5f}"
    )


@pytest.mark.parametrize("scenario_id", ["S2_rw1_stuck_torque_test", "S3_momentum_sat_test"])
def test_supervisor_infeasibility_detection_and_rl_shutdown(scenario_id: str) -> None:
    """Test 4: Physical authority infeasibility triggers M3 and zeroes tau_rl_gated_nm."""
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    catalog = build_default_scenario_catalog()
    scenario = catalog[scenario_id]
    runner = EpisodeRunner(cfg)

    ctrl = _DiagnosticSpyCCRController(
        cfg,
        policy=_ConstantNonzeroPolicy(np.array([0.9, -0.9, 0.9])),
        config=CCRControllerConfig(name="A7_ccr_infeasibility_spy", use_eso_backbone=True),
    )
    runner.run_episode(ctrl, scenario, seed=10, record_trace=False)

    infeasible_outputs = [
        out for out in ctrl.outputs if bool(out.diagnostics.get("authority_infeasible", False))
    ]
    assert len(infeasible_outputs) > 0, (
        f"Expected authority_infeasible=True after fault onset + saturation in {scenario_id}"
    )
    for out in infeasible_outputs:
        assert out.mode == SupervisorMode.M3_UNKNOWN_INVALID_UNSAFE
        assert out.gate_decision.rl_enabled is False
        np.testing.assert_array_equal(out.gate_decision.tau_rl_gated_nm, np.zeros(3))
