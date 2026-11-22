"""Phase 9 & 10 tests: statistical analysis, CPU profiling, and plot generation pipeline."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from adcs.control.allocation import AllocationConfig
from adcs.control.classical import ClassicalLQRController, StrongClassicalController
from adcs.control.residual_rl import (
    CCRController,
    CCRControllerConfig,
    ZeroResidualPolicy,
)
from adcs.control.safety import GateConfig
from adcs.evaluation import EpisodeRunner
from adcs.evaluation.metrics import compute_episode_metrics
from adcs.evaluation.profiling import profile_control_stack_cpu
from adcs.evaluation.statistics import (
    PairedComparisonRow,
    apply_holm_bonferroni,
    paired_bootstrap_comparison,
    summarize_arms,
    summarize_failure_breakdown,
)
from adcs.faults import build_default_scenario_catalog
from adcs.utils import load_spacecraft_config

REPO_ROOT = Path(__file__).resolve().parents[2]
SPACECRAFT_YAML = REPO_ROOT / "spacecraft_config.yaml"


def test_paired_bootstrap_statistics_and_arm_summary() -> None:
    rows = []
    for seed in range(20):
        base = 2.0 + 0.1 * seed
        rows.append(
            {
                "scenario_id": "S1_test",
                "category": "S1",
                "controller_arm": "A0",
                "seed": seed,
                "rms_attitude_err_deg": base,
                "peak_attitude_err_deg": base * 2.0,
                "recovered": True,
                "recovery_time_s": 15.0 + seed * 0.2,
                "loss_of_control": False,
                "rw_effort_nms": 3.0,
                "rw_saturation_fraction": 0.05,
                "mean_rho": 0.0,
                "mean_alpha": 0.0,
                "mean_rl_torque_nm": 0.0,
                "mean_cycle_time_ms": 0.5,
            }
        )
        rows.append(
            {
                "scenario_id": "S1_test",
                "category": "S1",
                "controller_arm": "A7",
                "seed": seed,
                "rms_attitude_err_deg": base - 0.5,
                "peak_attitude_err_deg": (base - 0.5) * 2.0,
                "recovered": True,
                "recovery_time_s": 10.0 + seed * 0.2,
                "loss_of_control": False,
                "rw_effort_nms": 2.8,
                "rw_saturation_fraction": 0.02,
                "mean_rho": 0.4,
                "mean_alpha": 0.85,
                "mean_rl_torque_nm": 0.015,
                "mean_cycle_time_ms": 0.7,
            }
        )
    df = pd.DataFrame(rows)
    summaries = summarize_arms(df)
    assert len(summaries) == 2
    cmp_row = paired_bootstrap_comparison(df, arm="A7", reference_arm="A0", n_boot=500)
    assert cmp_row.n_pairs == 20
    assert cmp_row.mean_diff == pytest.approx(-0.5, abs=1e-9)
    assert cmp_row.ci_high < 0.0
    assert cmp_row.win_rate_pct == pytest.approx(100.0)


def test_cpu_profiling_reports_valid_latency_and_memory_budget() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    prof = profile_control_stack_cpu(cfg, ZeroResidualPolicy(), n_steps=40)
    assert prof["control_period_budget_ms"] == pytest.approx(200.0)
    assert prof["budget_utilization_pct_mean"] < 50.0
    assert prof["mlp_param_count"] == 6339
    assert len(prof["components"]) == 7
    for comp in prof["components"]:
        assert np.isfinite(comp["mean_ms"]) and comp["mean_ms"] >= 0.0
        assert comp["p99_ms"] >= comp["p50_ms"]


def test_apply_holm_bonferroni_stepdown_and_monotonicity() -> None:
    def _row(arm: str, p: float) -> PairedComparisonRow:
        return PairedComparisonRow(
            arm=arm,
            reference_arm="A3",
            metric="rms_attitude_err_deg",
            n_pairs=10,
            mean_diff=-0.1,
            ci_low=-0.2,
            ci_high=0.0,
            median_diff=-0.1,
            cohens_dz=-0.5,
            wilcoxon_p=p,
            win_rate_pct=80.0,
        )

    rows = [
        _row("arm_c", 0.03),
        _row("arm_nan", float("nan")),
        _row("arm_a", 0.01),
        _row("arm_b", 0.012),
    ]
    out = apply_holm_bonferroni(rows)
    assert [r.arm for r in out] == ["arm_c", "arm_nan", "arm_a", "arm_b"]
    # m=3 finite p-values: (0.01, 0.012, 0.03) -> (0.03, 0.03, 0.03)
    assert out[2].wilcoxon_p_holm == pytest.approx(0.03)
    assert out[3].wilcoxon_p_holm == pytest.approx(0.03)
    assert out[0].wilcoxon_p_holm == pytest.approx(0.03)
    assert np.isnan(out[1].wilcoxon_p_holm)


def test_multi_train_seed_pairing_avoids_pseudoreplication() -> None:
    rows = []
    for seed in range(10):
        rows.append(
            {
                "scenario_id": "S1_test",
                "controller_arm": "A3",
                "seed": seed,
                "train_seed": 42,
                "rms_attitude_err_deg": 1.0,
            }
        )
        for tseed, delta in [(42, -0.3), (107, -0.2), (211, -0.1)]:
            rows.append(
                {
                    "scenario_id": "S1_test",
                    "controller_arm": "A7",
                    "seed": seed,
                    "train_seed": tseed,
                    "rms_attitude_err_deg": 1.0 + delta,
                }
            )
    df = pd.DataFrame(rows)
    cmp_row = paired_bootstrap_comparison(df, arm="A7", reference_arm="A3", n_boot=200)
    # Must aggregate across the 3 train_seeds per (scenario_id, seed) -> 10 independent pairs
    assert cmp_row.n_pairs == 10
    assert cmp_row.mean_diff == pytest.approx(-0.2, abs=1e-9)


def test_infeasibility_metrics_and_failure_breakdown() -> None:
    n = 20
    times = np.arange(n, dtype=np.float64) * 0.2
    att = np.full(n, 30.0)
    rate = np.full(n, 0.05)
    rw_ach = np.zeros((n, 3))
    mtq_ach = np.zeros((n, 3))
    tau_req = np.zeros((n, 3))
    tau_tot = np.zeros((n, 3))
    rw_sat = np.zeros(n, dtype=bool)
    rho = np.zeros(n)
    alpha = np.zeros(n)
    rl_norm = np.zeros(n)
    rej = np.zeros(n, dtype=bool)
    cyc = np.ones(n) * 0.5

    # Synthetic physically infeasible episode detected via authority_infeasible_flags
    m_det = compute_episode_metrics(
        scenario_id="S2_syn",
        category="S2",
        split="test",
        controller_arm="A7",
        seed=1,
        times_s=times,
        att_err_deg=att,
        rate_err_rad_s=rate,
        rw_torque_achieved_nm=rw_ach,
        mtq_dipole_achieved_am2=mtq_ach,
        tau_request_nm=tau_req,
        tau_achieved_total_nm=tau_tot,
        rw_saturated_any=rw_sat,
        rho_hist=rho,
        alpha_hist=alpha,
        rl_torque_norm_nm=rl_norm,
        gate_rejected=rej,
        modes=["M0_NOMINAL"] * 5 + ["M3_UNKNOWN_INVALID_UNSAFE"] * (n - 5),
        cycle_times_ms=cyc,
        fault_onset_s=1.0,
        min_oracle_rank=2,
        dt_s=0.2,
        authority_infeasible_flags=np.array([False] * 5 + [True] * (n - 5)),
    )
    assert m_det.physically_infeasible is True
    assert m_det.infeasibility_detected is True
    assert m_det.correct_infeasibility_response is True

    # Real S2 and S3 (both physically infeasible) + S0 (controllable) episodes
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    cat = build_default_scenario_catalog()
    cap_alloc = AllocationConfig(
        capability_aware=True,
        compensate_bias=True,
        mtq_assist_enabled=True,
        mtq_unload_gain=0.004,
    )
    runner = EpisodeRunner(cfg)
    ccr_cfg = CCRControllerConfig(
        name="A7_zero",
        use_eso_backbone=True,
        allocation=cap_alloc,
        gate=GateConfig(),
    )
    ccr = CCRController(cfg, ZeroResidualPolicy(), ccr_cfg)
    lqr = ClassicalLQRController(cfg)

    m_s2_a7 = runner.run_episode(ccr, cat["S2_rw1_stuck_torque_test"], seed=100).metrics
    m_s2_a0 = runner.run_episode(lqr, cat["S2_rw1_stuck_torque_test"], seed=100).metrics
    m_s3_a7 = runner.run_episode(ccr, cat["S3_momentum_sat_test"], seed=100).metrics
    m_s0_a7 = runner.run_episode(ccr, cat["S0_nominal_test"], seed=100).metrics

    assert m_s2_a7.physically_infeasible is True
    assert m_s2_a7.infeasibility_detected is True
    assert m_s2_a7.correct_infeasibility_response is True
    assert m_s3_a7.physically_infeasible is True
    assert m_s3_a7.infeasibility_detected is True
    assert m_s3_a7.correct_infeasibility_response is True
    assert m_s0_a7.physically_infeasible is False
    assert m_s0_a7.loss_of_control is False
    assert m_s2_a0.physically_infeasible is True
    assert m_s2_a0.infeasibility_detected is False
    assert m_s2_a0.correct_infeasibility_response is False

    df = pd.DataFrame(
        [
            m_s2_a7.to_dict(),
            m_s3_a7.to_dict(),
            m_s0_a7.to_dict(),
            {**m_s0_a7.to_dict(), "loss_of_control": True, "seed": 101},
            m_s2_a0.to_dict(),
        ]
    )
    breakdown = {row["arm"]: row for row in summarize_failure_breakdown(df)}
    b_a7 = breakdown["A7_zero"]
    assert b_a7["n_total"] == 4
    assert b_a7["n_controllable"] == 2
    assert b_a7["controllable_loc_count"] == 1
    assert b_a7["controllable_loc_pct"] == pytest.approx(50.0)
    assert b_a7["n_infeasible"] == 2
    assert b_a7["infeasible_loc_count"] == 2
    assert b_a7["infeasible_loc_pct"] == pytest.approx(100.0)
    assert b_a7["infeasibility_detected_pct"] == pytest.approx(100.0)
    assert b_a7["correct_infeasibility_response_pct"] == pytest.approx(100.0)

    b_a0 = breakdown["A0_classical_lqr"]
    assert b_a0["n_infeasible"] == 1
    assert b_a0["infeasibility_detected_pct"] == pytest.approx(0.0)
    assert b_a0["correct_infeasibility_response_pct"] == pytest.approx(0.0)

    class _ConstNonzeroPolicy:
        def predict(self, obs: np.ndarray, *, deterministic: bool = True) -> np.ndarray:
            return np.array([0.8, 0.8, 0.8], dtype=np.float64)

    a4_cfg = CCRControllerConfig(
        name="A4_unstructured_rl",
        use_eso_backbone=False,
        allocation=AllocationConfig(capability_aware=False),
        gate=GateConfig(
            enable_rho=False,
            enable_alpha=False,
            enable_directional_g=False,
            use_supervisor=False,
        ),
    )
    a4 = CCRController(cfg, _ConstNonzeroPolicy(), a4_cfg)
    m_s2_a4 = runner.run_episode(a4, cat["S2_rw1_stuck_torque_test"], seed=100).metrics
    assert m_s2_a4.infeasibility_detected is False
    assert m_s2_a4.correct_infeasibility_response is False

    a3 = StrongClassicalController(cfg)
    m_s5_a3 = runner.run_episode(a3, cat["S5_mtq_degraded_test"], seed=105).metrics
    assert m_s5_a3.physically_infeasible is False
    assert m_s5_a3.loss_of_control is False
