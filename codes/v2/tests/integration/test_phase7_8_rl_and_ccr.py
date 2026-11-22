"""Phase 7 & 8 integration tests: Gymnasium env, deterministic SAC, CCR v2 fallback & ablations."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from adcs.control.residual_rl import (
    OBS_DIM,
    CCRController,
    CCRControllerConfig,
    TorchMLPResidualPolicy,
    ZeroResidualPolicy,
)
from adcs.evaluation import EpisodeRunner
from adcs.faults import build_default_scenario_catalog
from adcs.training import ADCSResidualEnv, EnvTrainConfig, SACConfig, train_sac
from adcs.utils import load_spacecraft_config

REPO_ROOT = Path(__file__).resolve().parents[2]
SPACECRAFT_YAML = REPO_ROOT / "spacecraft_config.yaml"


def test_gymnasium_env_api_determinism_and_bounded_actions() -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    env = ADCSResidualEnv(cfg, EnvTrainConfig(episode_duration_s=10.0))

    obs1, info1 = env.reset(seed=7)
    assert obs1.shape == (OBS_DIM,)
    assert np.all(np.isfinite(obs1))
    assert env.observation_space.contains(obs1)

    traj1 = []
    for _ in range(15):
        o, r, term, trunc, _ = env.step(np.array([0.2, -0.3, 0.1], dtype=np.float32))
        assert o.shape == (OBS_DIM,) and np.all(np.isfinite(o))
        assert np.isfinite(r)
        traj1.append((o, r, term, trunc))

    # Replay with identical seed produces exact same trajectory
    obs2, _ = env.reset(seed=7)
    np.testing.assert_array_equal(obs1, obs2)
    for k in range(15):
        o, r, term, trunc, _ = env.step(np.array([0.2, -0.3, 0.1], dtype=np.float32))
        np.testing.assert_array_equal(o, traj1[k][0])
        assert r == traj1[k][1]


def test_sac_smoke_training_checkpoint_reload_and_ccr_fallback(tmp_path: Path) -> None:
    cfg = load_spacecraft_config(SPACECRAFT_YAML)
    env = ADCSResidualEnv(cfg, EnvTrainConfig(episode_duration_s=12.0))
    ckpt_dir = tmp_path / "ckpt_a7"

    res = train_sac(
        env,
        SACConfig(total_steps=300, warmup_steps=80, batch_size=32, buffer_size=2000, seed=5),
        checkpoint_dir=ckpt_dir,
        arm_label="A7_smoke",
    )
    assert len(res.weights_sha256) == 64
    assert (ckpt_dir / "policy_weights.npz").exists()
    assert (ckpt_dir / "policy_meta.json").exists()
    assert (ckpt_dir / "training_curve.jsonl").exists()

    # Reload policy cleanly without training side effects & verify deterministic identical output
    reloaded = TorchMLPResidualPolicy.load(ckpt_dir)
    sample_obs = np.zeros(OBS_DIM, dtype=np.float64)
    a1 = res.policy.predict(sample_obs, deterministic=True)
    a2 = reloaded.predict(sample_obs, deterministic=True)
    np.testing.assert_array_equal(a1, a2)
    assert np.all(np.abs(a1) <= 1.0)

    # Verify CCR v2 controller with reloaded policy AND safe fallback when policy=None or crashes
    catalog = build_default_scenario_catalog()
    runner = EpisodeRunner(cfg)
    s0 = catalog["S0_nominal_val"]

    ccr_live = CCRController(cfg, policy=reloaded, config=CCRControllerConfig(name="A7_live"))
    ccr_none = CCRController(cfg, policy=None, config=CCRControllerConfig(name="A7_fallback"))

    class _CrashingPolicy:
        def predict(self, obs: np.ndarray, *, deterministic: bool = True) -> np.ndarray:
            del obs, deterministic
            raise RuntimeError("simulated inference timeout")

    ccr_crash = CCRController(
        cfg, policy=_CrashingPolicy(), config=CCRControllerConfig(name="A7_crash")
    )
    ccr_zero = CCRController(
        cfg, policy=ZeroResidualPolicy(), config=CCRControllerConfig(name="A7_zero")
    )

    m_live = runner.run_episode(ccr_live, s0, seed=3).metrics
    m_none = runner.run_episode(ccr_none, s0, seed=3).metrics
    m_crash = runner.run_episode(ccr_crash, s0, seed=3).metrics
    m_zero = runner.run_episode(ccr_zero, s0, seed=3).metrics

    assert m_live.loss_of_control is False
    assert m_none.loss_of_control is False
    assert m_crash.loss_of_control is False
    assert m_zero.loss_of_control is False
    # Crash fallback produces bit-identical trajectory to policy=None fallback!
    assert m_crash.rms_attitude_err_deg == m_none.rms_attitude_err_deg
    assert m_none.mean_rl_torque_nm == 0.0
    assert m_crash.mean_rl_torque_nm == 0.0
