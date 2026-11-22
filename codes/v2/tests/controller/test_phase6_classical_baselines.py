"""Phase 6 tests: strong classical fault-tolerant baselines (A0, A1, A2, A3) on train/val splits."""

from __future__ import annotations

from pathlib import Path

from adcs.control.classical import (
    ClassicalDOBController,
    ClassicalLQRController,
    StrongClassicalController,
    make_oracle_allocation_lqr,
)
from adcs.evaluation import EpisodeRunner
from adcs.faults import build_default_scenario_catalog
from adcs.utils import load_spacecraft_config

REPO_ROOT = Path(__file__).resolve().parents[2]
SPACECRAFT_YAML = REPO_ROOT / "spacecraft_config.yaml"


def test_classical_baselines_nominal_and_fault_accommodation_on_val_splits() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    catalog = build_default_scenario_catalog()
    runner = EpisodeRunner(cfg)

    a0 = ClassicalLQRController(cfg)
    a1 = make_oracle_allocation_lqr(cfg)
    a2 = ClassicalDOBController(cfg)
    a3 = StrongClassicalController(cfg)

    # 1. S0 Nominal validation: all classical arms recover cleanly with < 0.3 deg steady RMS
    s0 = catalog["S0_nominal_val"]
    for ctrl, oracle in [(a0, False), (a1, True), (a2, False), (a3, False)]:
        m = runner.run_episode(ctrl, s0, seed=10, use_oracle_capability=oracle).metrics
        assert m.loss_of_control is False, f"{ctrl.name} failed S0: {m.failure_reason}"
        assert m.rms_attitude_err_deg < 0.35

    # 2. S4 Torque bias + friction (train split): A2 (ESO) & A3 strongly outperform pure LQR A0!
    s4 = catalog["S4_rw_bias_friction_train"]
    m_a0_s4 = runner.run_episode(a0, s4, seed=10, use_oracle_capability=False).metrics
    m_a2_s4 = runner.run_episode(a2, s4, seed=10, use_oracle_capability=False).metrics
    m_a3_s4 = runner.run_episode(a3, s4, seed=10, use_oracle_capability=False).metrics
    assert m_a2_s4.rms_attitude_err_deg < 0.5 * m_a0_s4.rms_attitude_err_deg
    assert m_a3_s4.rms_attitude_err_deg < 0.5 * m_a0_s4.rms_attitude_err_deg
    assert m_a3_s4.loss_of_control is False

    # 3. S1 RW gradual effectiveness degradation (val split): A1 oracle & A3 recover cleanly
    s1 = catalog["S1_rw1_gradual40_val"]
    m_a1_s1 = runner.run_episode(a1, s1, seed=10, use_oracle_capability=True).metrics
    m_a3_s1 = runner.run_episode(a3, s1, seed=10, use_oracle_capability=False).metrics
    assert m_a1_s1.loss_of_control is False
    assert m_a3_s1.loss_of_control is False
    assert m_a3_s1.rms_attitude_err_deg < 0.5

    # 4. S6 Star-tracker dropout + gyro bias (val split): A3 stays stable without ESO windup
    s6 = catalog["S6_st_dropout_val"]
    m_a3_s6 = runner.run_episode(a3, s6, seed=10, use_oracle_capability=False).metrics
    assert m_a3_s6.rms_attitude_err_deg < 5.0
    assert m_a3_s6.recovered is True

    # 5. Paired seed determinism check
    m_a3_repeat = runner.run_episode(a3, s4, seed=10, use_oracle_capability=False).metrics
    assert m_a3_repeat.rms_attitude_err_deg == m_a3_s4.rms_attitude_err_deg
    assert m_a3_repeat.rw_effort_nms == m_a3_s4.rw_effort_nms
