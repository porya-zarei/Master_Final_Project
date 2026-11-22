"""Gate C3 & C4 tests: B2 symptoms, B4/B8 supervisor M0-M4, and B7 deterministic authority gate."""

from __future__ import annotations

import numpy as np
import pytest

from adcs.control.safety import DeterministicAuthorityGate, GateConfig
from adcs.control.supervisor import (
    ControlValiditySupervisor,
    SupervisorConfig,
    SymptomSummary,
)
from adcs.interfaces import (
    ActuatorCapabilityState,
    EstimatorOutput,
    SupervisorMode,
    WheelCapability,
)


def _make_est(
    *,
    gamma_obs: float = 0.95,
    att_std: float = 0.002,
    omega_norm: float = 0.01,
    data_age_s: float = 0.2,
    valid: bool = True,
) -> EstimatorOutput:
    return EstimatorOutput(
        time_s=10.0,
        q_ib_est=np.array([1.0, 0.0, 0.0, 0.0]),
        omega_body_est_rad_s=np.array([omega_norm, 0.0, 0.0]),
        gyro_bias_est_rad_s=np.zeros(3),
        attitude_cov_rad2=np.eye(3) * (att_std**2),
        rate_cov_rad2_s2=np.eye(3) * 1e-6,
        attitude_std_rad=np.full(3, att_std),
        rate_std_rad_s=np.full(3, 1e-3),
        gamma_obs=gamma_obs,
        sensor_status={"gyro": True, "star_tracker": True, "magnetometer": True},
        data_age_s=data_age_s,
        valid=valid,
    )


def _make_cap(
    *,
    margins: tuple[float, float, float] = (1.0, 1.0, 1.0),
    confidence: float = 0.95,
    rank: int = 3,
    stale: bool = False,
    valid: bool = True,
) -> ActuatorCapabilityState:
    wheels = tuple(
        WheelCapability(
            axis_body=np.eye(3)[:, i],
            effectiveness_nom=margins[i],
            effectiveness_min=margins[i],
            effectiveness_max=margins[i],
            bias_est_nm=0.0,
            bias_bound_nm=0.0,
            torque_limit_nm=0.15,
            momentum_limit_nms=6.0,
            current_momentum_nms=0.0,
            available_pos_torque_nm=0.15 * margins[i],
            available_neg_torque_nm=0.15 * margins[i],
            saturated_torque=False,
            saturated_momentum=False,
            confidence=confidence,
            valid=valid,
        )
        for i in range(3)
    )
    return ActuatorCapabilityState(
        time_s=10.0,
        wheels=wheels,
        mtqs=(),
        nominal_support_xyz=np.full(3, 0.15),
        conservative_support_xyz=np.asarray(margins) * 0.15,
        directional_margin_xyz=np.asarray(margins, dtype=np.float64),
        effective_rank=rank,
        confidence=confidence,
        is_oracle=False,
        stale=stale,
        valid=valid,
    )


def _make_sym(deg: float = 0.0, max_res: float = 0.0) -> SymptomSummary:
    return SymptomSummary(
        vector=np.zeros(12),
        torque_residual_xyz_norm=np.full(3, max_res),
        max_torque_residual_norm=max_res,
        momentum_utilization_xyz=np.zeros(3),
        degradation_indicator=deg,
    )


def test_supervisor_mode_ladder_hysteresis_contradictory_and_recovery_gate_c3() -> None:
    sup = ControlValiditySupervisor(SupervisorConfig())
    est = _make_est()
    cap = _make_cap()
    assert sup.mode == SupervisorMode.M0_NOMINAL

    # 1. Suspected degradation requires persistence (3 steps)
    sym_deg = _make_sym(deg=0.4, max_res=0.35)
    for _ in range(2):
        st = sup.update(estimator_out=est, capability=cap, symptoms=sym_deg)
        assert st.mode == SupervisorMode.M0_NOMINAL
    st = sup.update(estimator_out=est, capability=cap, symptoms=sym_deg)
    assert st.mode == SupervisorMode.M1_SUSPECTED_DEGRADATION

    # 2. Confirmed degradation requires persistence (8 steps) + adequate confidence
    for _ in range(7):
        st = sup.update(estimator_out=est, capability=cap, symptoms=sym_deg)
        assert st.mode == SupervisorMode.M1_SUSPECTED_DEGRADATION
    st = sup.update(estimator_out=est, capability=cap, symptoms=sym_deg)
    assert st.mode == SupervisorMode.M2_CONFIRMED_DEGRADATION

    # 3. Invalid estimator triggers IMMEDIATE M3 (0-step delay)
    st_m3 = sup.update(estimator_out=_make_est(valid=False), capability=cap, symptoms=sym_deg)
    assert st_m3.mode == SupervisorMode.M3_UNKNOWN_INVALID_UNSAFE
    assert st_m3.rl_permitted is False
    assert st_m3.mode_trust_multiplier == 0.0

    # 4. Recovery from M3 -> M4 -> M0 requires sustained healthy persistence
    sym_ok = _make_sym(deg=0.0, max_res=0.0)
    for _ in range(10):
        st = sup.update(estimator_out=est, capability=cap, symptoms=sym_ok)
    assert st.mode == SupervisorMode.M4_RECOVERY
    for _ in range(15):
        st = sup.update(estimator_out=est, capability=cap, symptoms=sym_ok)
    assert st.mode == SupervisorMode.M0_NOMINAL

    # 5. Contradictory evidence (high residual + low capability confidence) escalates to M3
    cap_unc = _make_cap(confidence=0.1)
    sym_contra = _make_sym(deg=0.6, max_res=0.6)
    for _ in range(10):
        st = sup.update(estimator_out=est, capability=cap_unc, symptoms=sym_contra)
    assert st.mode == SupervisorMode.M3_UNKNOWN_INVALID_UNSAFE


def test_deterministic_gate_monotonicity_asymmetric_slew_nan_and_directionality_gate_c4() -> None:
    gate = DeterministicAuthorityGate(GateConfig())
    sup = ControlValiditySupervisor(SupervisorConfig())
    est = _make_est(gamma_obs=0.95)
    cap = _make_cap(margins=(0.0, 1.0, 0.5), confidence=0.9)
    sym = _make_sym(deg=0.0, max_res=0.0)
    st_m0 = sup.update(estimator_out=est, capability=cap, symptoms=_make_sym())

    # 1. Need rho == 0 at tiny steady-state error -> RL silent
    d_quiet = gate.evaluate(
        tau_rl_raw_nm=np.array([0.05, 0.05, 0.05]),
        att_err_rad=0.001,
        rate_err_norm_rad_s=0.0001,
        estimator_out=est,
        capability=cap,
        symptoms=sym,
        supervisor_status=st_m0,
        dt_s=0.2,
    )
    assert d_quiet.rho == pytest.approx(0.0)
    np.testing.assert_array_equal(d_quiet.tau_rl_gated_nm, np.zeros(3))

    # 2. Large attitude error increases rho (need) but NEVER increases raw trust alpha
    alpha_high = gate.compute_raw_trust_alpha(_make_est(gamma_obs=0.9), cap, st_m0)
    alpha_med = gate.compute_raw_trust_alpha(_make_est(gamma_obs=0.6), cap, st_m0)
    alpha_low = gate.compute_raw_trust_alpha(_make_est(gamma_obs=0.3), cap, st_m0)
    assert alpha_high > alpha_med > alpha_low > 0.0

    # Worsening covariance monotonically lowers alpha
    assert gate.compute_raw_trust_alpha(
        _make_est(att_std=0.05), cap, st_m0
    ) < gate.compute_raw_trust_alpha(_make_est(att_std=0.002), cap, st_m0)

    # 3. Asymmetric slew: slow ramp UP, fast ramp DOWN, instant drop on NaN / M3
    gate.reset()
    alphas_up = []
    for _ in range(10):
        d = gate.evaluate(
            tau_rl_raw_nm=np.array([0.04, 0.04, 0.04]),
            att_err_rad=0.2,
            rate_err_norm_rad_s=0.02,
            estimator_out=est,
            capability=cap,
            symptoms=sym,
            supervisor_status=st_m0,
            dt_s=0.2,
        )
        alphas_up.append(d.alpha)
    up_step = alphas_up[1] - alphas_up[0]
    assert up_step == pytest.approx(0.35 * 0.2, abs=1e-6)  # slow conservative recovery

    # Directional gate G blocks dead x-axis (margin=0), allows full y-axis (margin=1)
    assert d.tau_rl_gated_nm[0] == pytest.approx(0.0, abs=1e-12)
    assert abs(d.tau_rl_gated_nm[1]) > abs(d.tau_rl_gated_nm[2]) > 0.0

    # Fast downward slew when observability drops
    d_down = gate.evaluate(
        tau_rl_raw_nm=np.array([0.04, 0.04, 0.04]),
        att_err_rad=0.2,
        rate_err_norm_rad_s=0.02,
        estimator_out=_make_est(gamma_obs=0.2),
        capability=cap,
        symptoms=sym,
        supervisor_status=st_m0,
        dt_s=0.2,
    )
    down_step = alphas_up[-1] - d_down.alpha
    assert down_step > up_step * 3.0  # drops much faster than it recovers

    # 4. NaN policy output or None policy -> immediate zeroing & safe fallback
    d_nan = gate.evaluate(
        tau_rl_raw_nm=np.array([np.nan, 0.02, 0.01]),
        att_err_rad=0.2,
        rate_err_norm_rad_s=0.02,
        estimator_out=est,
        capability=cap,
        symptoms=sym,
        supervisor_status=st_m0,
        dt_s=0.2,
    )
    assert d_nan.alpha == 0.0
    assert d_nan.rl_enabled is False
    assert d_nan.rejected_reason == "non_finite_policy_output"
    np.testing.assert_array_equal(d_nan.tau_rl_gated_nm, np.zeros(3))

    d_none = gate.evaluate(
        tau_rl_raw_nm=None,
        att_err_rad=0.2,
        rate_err_norm_rad_s=0.02,
        estimator_out=est,
        capability=cap,
        symptoms=sym,
        supervisor_status=st_m0,
        dt_s=0.2,
    )
    assert d_none.rl_enabled is False
    assert d_none.rejected_reason == "policy_unavailable"
