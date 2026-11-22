"""Phase 1 foundation tests: packaging, interfaces, config validation, seeding, logging."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import yaml

import adcs
from adcs.interfaces import (
    ActuatorStatus,
    SpacecraftTruthState,
    SupervisorMode,
)
from adcs.utils import (
    ConfigValidationError,
    SeedManager,
    capture_run_metadata,
    load_spacecraft_config,
    sha256_canonical,
    write_jsonl,
)
from adcs.utils.seeding import EpisodeSeedBundle

REPO_ROOT = Path(__file__).resolve().parents[2]
SPACECRAFT_YAML = REPO_ROOT / "spacecraft_config.yaml"


def test_package_version_and_import() -> None:
    assert adcs.__version__ == "0.1.0"
    assert SupervisorMode.M0_NOMINAL.value == "M0_NOMINAL"
    assert SupervisorMode.M3_UNKNOWN_INVALID_UNSAFE.value == "M3_UNKNOWN_INVALID_UNSAFE"


def test_load_reference_spacecraft_config() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    assert cfg.name == "spacecraft_reference_001"
    assert cfg.mass_kg == pytest.approx(100.0)
    assert cfg.inertia_matrix_kg_m2.shape == (3, 3)
    assert cfg.simulation.control_period_s == pytest.approx(0.2)
    assert cfg.simulation.integration_step_s == pytest.approx(0.01)
    assert cfg.reaction_wheels.count == 3
    assert cfg.magnetorquers.count == 3
    assert len(cfg.raw_hash) == 64
    # Known consistency warning between peak 7.83 Nms and 5000 rpm * 0.0149 = 7.8016 Nms
    assert any("slightly exceeds" in w for w in cfg.warnings)
    assert cfg.reaction_wheels.effective_momentum_limit_nms == pytest.approx(6.0)
    # Regression: YAML 1.1 parses '3.986004418e14' as str; verify coercion to float
    assert cfg.orbit.gravitational_parameter_m3_s2 == pytest.approx(3.986004418e14)


def test_config_rejects_boolean_for_float(tmp_path: Path) -> None:
    raw = yaml.safe_load(SPACECRAFT_YAML.read_text(encoding="utf-8"))
    raw["spacecraft"]["mass_kg"] = True
    bad = tmp_path / "bad_bool.yaml"
    bad.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ConfigValidationError, match="bool"):
        load_spacecraft_config(bad)


def test_config_rejects_non_spd_inertia(tmp_path: Path) -> None:
    raw = yaml.safe_load(SPACECRAFT_YAML.read_text(encoding="utf-8"))
    raw["spacecraft"]["inertia"]["matrix_kg_m2"] = [
        [-1.0, 0.0, 0.0],
        [0.0, 10.0, 0.0],
        [0.0, 0.0, 10.0],
    ]
    bad = tmp_path / "bad_inertia.yaml"
    bad.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ConfigValidationError, match="positive definite"):
        load_spacecraft_config(bad)


def test_config_rejects_bad_timestep_multiple(tmp_path: Path) -> None:
    raw = yaml.safe_load(SPACECRAFT_YAML.read_text(encoding="utf-8"))
    raw["simulation"]["integration"]["step_s"] = 0.07
    bad = tmp_path / "bad_step.yaml"
    bad.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ConfigValidationError, match="integer multiple"):
        load_spacecraft_config(bad)


def test_config_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigValidationError, match="does not exist"):
        load_spacecraft_config(tmp_path / "missing.yaml")


def test_deterministic_seeding_and_hashing() -> None:
    s1 = SeedManager(42)
    s2 = SeedManager(42)
    a = s1.spawn_rng("sensor_noise").normal(size=10)
    b = s2.spawn_rng("sensor_noise").normal(size=10)
    c = s1.spawn_rng("fault").normal(size=10)
    np.testing.assert_array_equal(a, b)
    assert not np.allclose(a, c)

    b1 = EpisodeSeedBundle.from_episode_seed(123)
    b2 = EpisodeSeedBundle.from_episode_seed(123)
    assert b1 == b2
    assert b1.sensor_noise_seed != b1.fault_seed

    h1 = sha256_canonical({"b": 2, "a": np.array([1.0, 2.0])})
    h2 = sha256_canonical({"a": [1.0, 2.0], "b": 2})
    assert h1 == h2


def test_truth_state_validation_rejects_nan() -> None:
    st = SpacecraftTruthState(
        time_s=0.0,
        position_eci_m=np.array([6878137.0, 0.0, 0.0]),
        velocity_eci_m_s=np.array([0.0, 7612.6, 0.0]),
        q_ib=np.array([1.0, 0.0, 0.0, 0.0]),
        omega_body_rad_s=np.array([np.nan, 0.0, 0.0]),
        wheel_momentum_nms=np.zeros(3),
        wheel_speed_rad_s=np.zeros(3),
        rw_torque_achieved_nm=np.zeros(3),
        mtq_dipole_achieved_am2=np.zeros(3),
        mtq_torque_achieved_nm=np.zeros(3),
        b_field_body_t=np.array([0.0, 0.0, 3e-5]),
        disturbance_torque_body_nm=np.zeros(3),
        actuator_status=ActuatorStatus(
            rw_torque_saturated=(False, False, False),
            rw_momentum_saturated=(False, False, False),
            mtq_dipole_saturated=(False, False, False),
        ),
    )
    with pytest.raises(ValueError, match="non-finite"):
        st.validate()


def test_metadata_and_jsonl_logging(tmp_path: Path) -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    meta = capture_run_metadata(cfg.raw_hash, cwd=REPO_ROOT)
    assert meta.adcs_version == "0.1.0"
    assert meta.config_hash == cfg.raw_hash
    out = tmp_path / "log.jsonl"
    write_jsonl(out, [meta.to_dict(), {"step": 0, "vec": np.array([1.0, 2.0])}])
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
