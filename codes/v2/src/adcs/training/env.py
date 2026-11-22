"""Gymnasium-compatible residual RL training environment with deployed gate in the loop.

Strictly enforces:
- Training scenario randomization confined to disjoint training region (zero held-out leakage).
- Actor observation `obs` contains ONLY onboard-estimated information (no truth/fault labels).
- Deployed deterministic gate and estimator imperfections run inside the training loop by default
  (with explicit ablation flag `clean_state_training=True` for H3 testing).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from adcs.control.reference import NadirReferenceGenerator, compute_attitude_error
from adcs.control.residual_rl.controller import CCRController, CCRControllerConfig
from adcs.control.residual_rl.policy import ACTION_DIM, OBS_DIM
from adcs.estimation import (
    MEKFConfig,
    MultiplicativeEKF,
    OnlineCapabilityEstimator,
    OracleCapabilityEstimator,
)
from adcs.faults import FaultEvent, FaultInjector
from adcs.interfaces.types import EstimatorOutput, FloatArray, SensorMeasurement
from adcs.sensors import SensorSuite, SensorSuiteConfig
from adcs.simulation.fast import FastSimulatorBackend
from adcs.utils.config import SpacecraftConfig
from adcs.utils.quaternion import quat_from_axis_angle, quat_multiply
from adcs.utils.seeding import SeedManager


@dataclass(frozen=True)
class EnvTrainConfig:
    """Training environment horizon, reward weights, and training-region randomization."""

    episode_duration_s: float = 80.0
    use_oracle_capability: bool = False
    clean_state_training: bool = False  # Ablation flag for H3 (no sensor noise / no gate)
    ccr_config: CCRControllerConfig = field(default_factory=CCRControllerConfig)
    # Reward weights (documented, physical units)
    w_att: float = 2.5
    att_log_scale_rad: float = 0.03
    w_rate: float = 4.0
    w_rl_effort: float = 6.0
    w_sat: float = 0.15
    w_gate_align: float = 2.0
    w_action_smooth: float = 0.05


class ADCSResidualEnv(gym.Env[np.ndarray, np.ndarray]):
    """Gymnasium Env wrapping FastSimulatorBackend + MEKF + B3 + CCRController."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        sc_config: SpacecraftConfig,
        train_config: EnvTrainConfig | None = None,
        sensor_config: SensorSuiteConfig | None = None,
        mekf_config: MEKFConfig | None = None,
    ) -> None:
        super().__init__()
        self.sc_cfg = sc_config
        self.cfg = EnvTrainConfig() if train_config is None else train_config
        self.sensor_cfg = sensor_config
        self.mekf_cfg = mekf_config
        self.dt = sc_config.simulation.control_period_s
        self.max_steps = int(round(self.cfg.episode_duration_s / self.dt))

        self.observation_space = spaces.Box(
            low=-5.0, high=5.0, shape=(OBS_DIM,), dtype=np.float32
        )
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(ACTION_DIM,), dtype=np.float32
        )

        self._rng = SeedManager(0).spawn_rng("env_train")
        self._sim: FastSimulatorBackend | None = None
        self._ref_gen = NadirReferenceGenerator()
        self._sensors = SensorSuite(sensor_config, n_rw=sc_config.reaction_wheels.count)
        self._mekf = MultiplicativeEKF(mekf_config)
        self._online_cap = OnlineCapabilityEstimator(sc_config)
        self._oracle_cap = OracleCapabilityEstimator(sc_config)
        self._controller = CCRController(sc_config, policy=None, config=self.cfg.ccr_config)
        self._injector = FaultInjector(sc_config, ())

        self._step_idx = 0
        self._cached_ctx: dict[str, object] = {}
        self._cached_est: EstimatorOutput | None = None
        self._cached_cap: Any = None
        self._cached_meas: SensorMeasurement | None = None
        self._last_cmd: Any = None
        self._prev_action = np.zeros(ACTION_DIM, dtype=np.float64)

    def _sample_train_episode_params(
        self,
    ) -> tuple[FloatArray, FloatArray, float, tuple[FaultEvent, ...], FloatArray]:
        """Sample strictly within disjoint TRAINING scenario region (never held-out test)."""
        r = self._rng
        regime = float(r.uniform(0.0, 1.0))
        inertia_scale = np.ones(3, dtype=np.float64)
        res_dipole = np.zeros(3, dtype=np.float64)
        tau_scale = 1.0
        n_rw = self.sc_cfg.reaction_wheels.count
        tau_lim = self.sc_cfg.reaction_wheels.torque_limit_nominal_nm
        h_lim = self.sc_cfg.reaction_wheels.effective_momentum_limit_nms
        m_lim = self.sc_cfg.magnetorquers.dipole_limit_per_axis_am2
        h_init = np.zeros(n_rw, dtype=np.float64)
        events: list[FaultEvent] = []

        if regime < 0.20:
            # S0-train nominal
            pass
        elif regime < 0.45:
            # S1-train: wheel degradation in [0.45, 0.80] across ALL wheels (disjoint from 0.25)
            wheel = int(r.integers(0, n_rw))
            eff = float(r.uniform(0.45, 0.80))
            onset = float(r.uniform(6.0, 22.0))
            ramp = float(r.choice([0.0, 10.0]))
            events.append(
                FaultEvent(
                    "rw_effectiveness_loss",
                    start_s=onset,
                    ramp_s=ramp,
                    target_index=wheel,
                    severity=eff,
                )
            )
        elif regime < 0.68:
            # S4-train: single-wheel bias, Coulomb friction & stiction across ALL wheels
            target_rw = int(r.integers(0, n_rw))
            bias = float(r.uniform(-0.17 * tau_lim, 0.17 * tau_lim))
            coul = float(r.uniform(0.03 * tau_lim, 0.12 * tau_lim))
            stic = float(r.uniform(0.015, 0.05) * tau_lim)
            onset = float(r.uniform(5.0, 18.0))
            events.append(
                FaultEvent("rw_torque_bias", start_s=onset, target_index=target_rw, severity=bias)
            )
            events.append(
                FaultEvent(
                    "rw_friction",
                    start_s=onset,
                    target_index=target_rw,
                    severity=coul,
                    extra={"viscous": 2.5e-4 * tau_lim, "stiction": stic},
                )
            )
        elif regime < 0.82:
            # S7-train: moderate inertia mismatch (+/- 15%) & dipole scaled to MTQ authority
            inertia_scale = r.uniform(0.85, 1.15, size=3)
            res_dipole = r.uniform(-0.03 * m_lim, 0.03 * m_lim, size=3)
            tau_scale = float(r.uniform(0.9, 1.4))
        elif regime < 0.92:
            # S6-train: star-tracker dropout [8, 18]s
            onset = float(r.uniform(12.0, 28.0))
            dur = float(r.uniform(8.0, 18.0))
            events.append(
                FaultEvent("star_tracker_dropout", start_s=onset, end_s=onset + dur, severity=1.0)
            )
        else:
            # S3-train: elevated initial wheel momentum + mild disturbance scaled to h_lim/tau_lim
            h_init = r.uniform(-0.7 * h_lim, 0.7 * h_lim, size=n_rw)
            dist = r.uniform(-0.07 * tau_lim, 0.07 * tau_lim, size=3)
            events.append(
                FaultEvent(
                    "disturbance_torque",
                    start_s=8.0,
                    severity=0.07 * tau_lim,
                    extra={"torque_nm": dist.tolist()},
                )
            )

        return inertia_scale, res_dipole, tau_scale, tuple(events), h_init

    def _prepare_step_observation(self) -> np.ndarray:
        assert self._sim is not None
        truth = self._sim.get_truth_state()
        act_faults, sens_faults = self._injector.evaluate(truth.time_s)
        self._sim.set_fault_state(act_faults)

        if self.cfg.clean_state_training:
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
                rw_speed_valid=(True,) * self.sc_cfg.reaction_wheels.count,
            )
            est_out = EstimatorOutput(
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
        else:
            meas = self._sensors.measure(truth, dt_s=self.dt, faults=sens_faults)
            est_out = self._mekf.update(meas, dt_s=self.dt)

        ref = self._ref_gen.compute(truth.time_s, truth.position_eci_m, truth.velocity_eci_m_s)
        if self.cfg.use_oracle_capability:
            cap = self._oracle_cap.estimate(
                time_s=truth.time_s,
                measurement=meas,
                last_command=self._last_cmd,
                b_field_body_t=meas.mag_body_t,
                dt_s=self.dt,
                truth_override={
                    "actuator_faults": act_faults,
                    "wheel_momentum_nms": truth.wheel_momentum_nms,
                    "b_field_body_t": truth.b_field_body_t,
                },
            )
        else:
            cap = self._online_cap.estimate(
                time_s=truth.time_s,
                measurement=meas,
                last_command=self._last_cmd,
                b_field_body_t=meas.mag_body_t,
                dt_s=self.dt,
            )

        obs, ctx = self._controller.build_observation_and_context(
            estimator_out=est_out,
            reference=ref,
            capability=cap,
            measurement=meas,
            dt_s=self.dt,
        )
        self._cached_ctx = ctx
        self._cached_est = est_out
        self._cached_cap = cap
        self._cached_meas = meas
        return obs.astype(np.float32)

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        super().reset(seed=seed)
        del options
        if seed is not None:
            self._rng = SeedManager(int(seed)).spawn_rng("env_train")

        inertia_scale, res_dipole, tau_scale, events, h_init = self._sample_train_episode_params()
        inertia_true = self.sc_cfg.inertia_matrix_kg_m2 * np.diag(inertia_scale)
        self._sim = FastSimulatorBackend(
            self.sc_cfg,
            inertia_override_kg_m2=inertia_true,
            residual_dipole_override_am2=res_dipole,
            rw_time_constant_override_s=self.sc_cfg.reaction_wheels.time_constant_s * tau_scale,
        )
        self._injector = FaultInjector(self.sc_cfg, events)

        nu0 = float(self._rng.uniform(0.0, 360.0))
        st0 = self._sim.reset(true_anomaly_deg_init=nu0)
        self._ref_gen.reset()
        ref0 = self._ref_gen.compute(st0.time_s, st0.position_eci_m, st0.velocity_eci_m_s)

        axis = self._rng.normal(size=3)
        axis /= max(float(np.linalg.norm(axis)), 1e-9)
        att_deg = float(self._rng.uniform(5.0, 30.0))
        q_init = quat_multiply(ref0.q_ir, quat_from_axis_angle(axis, np.deg2rad(att_deg)))
        w_dir = self._rng.normal(size=3)
        w_dir /= max(float(np.linalg.norm(w_dir)), 1e-9)
        w_mag = float(self._rng.uniform(0.002, 0.025))
        w_init = ref0.omega_ref_inertial_in_ref_rad_s + w_dir * w_mag

        self._sim.reset(
            q_ib_init=q_init,
            omega_body_init=w_init,
            wheel_momentum_init=h_init,
            true_anomaly_deg_init=nu0,
        )
        self._ref_gen.reset()
        sens_seed = int(self._rng.integers(0, 2**31 - 1))
        self._sensors.reset(seed=sens_seed, q_ib_init=q_init)
        self._mekf.reset(q_ib_init=q_init, omega_init=w_init, time_s=0.0)
        self._online_cap.reset()
        self._oracle_cap.reset()
        self._controller.reset()
        self._step_idx = 0
        self._last_cmd = None
        self._prev_action = np.zeros(ACTION_DIM, dtype=np.float64)

        obs = self._prepare_step_observation()
        return obs, {"n_events": len(events)}

    def step(
        self, action: np.ndarray
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        assert (
            self._sim is not None
            and self._cached_est is not None
            and self._cached_meas is not None
        )
        act = np.clip(np.asarray(action, dtype=np.float64), -1.0, 1.0)
        ctrl_out = self._controller.apply_raw_action(
            raw_action_norm=act,
            ctx=self._cached_ctx,
            estimator_out=self._cached_est,
            capability=self._cached_cap,
            measurement=self._cached_meas,
            dt_s=self.dt,
        )
        self._last_cmd = ctrl_out.command
        truth = self._sim.step(
            ctrl_out.command.rw_torque_cmd_nm,
            ctrl_out.command.mtq_dipole_cmd_am2,
            dt_s=self.dt,
        ).truth
        self._step_idx += 1

        ref_next = self._ref_gen.compute(truth.time_s, truth.position_eci_m, truth.velocity_eci_m_s)
        true_err = compute_attitude_error(truth.q_ib, truth.omega_body_rad_s, ref_next)
        att_rad = true_err.geodesic_angle_rad
        rate_norm = float(np.linalg.norm(true_err.omega_err_body_rad_s))

        sat_flag = 1.0 if (
            any(truth.actuator_status.rw_torque_saturated)
            or any(truth.actuator_status.rw_momentum_saturated)
        ) else 0.0
        rl_raw = ctrl_out.gate_decision.tau_rl_raw_nm
        rl_gated = ctrl_out.gate_decision.tau_rl_gated_nm
        # Scale effort penalties to spacecraft torque scale so reward is scale-invariant!
        rl_scale = max(self._controller._action_scale_nm, 1e-6)
        rl_raw_n = rl_raw / rl_scale
        rl_diff_n = (rl_raw - rl_gated) / rl_scale
        act_delta_sq = float(np.sum(np.square(act - self._prev_action)))

        reward = (
            -self.cfg.w_att * float(np.log1p(att_rad / self.cfg.att_log_scale_rad))
            - self.cfg.w_rate * rate_norm
            - (self.cfg.w_rl_effort * 0.0036) * float(np.dot(rl_raw_n, rl_raw_n))
            - self.cfg.w_sat * sat_flag
            - (self.cfg.w_gate_align * 0.06) * float(np.linalg.norm(rl_diff_n))
            - self.cfg.w_action_smooth * act_delta_sq
        )
        self._prev_action = act.copy()

        # Terminate early only on catastrophic tumble (> 150 deg or > 1.0 rad/s)
        terminated = bool(att_rad > np.deg2rad(150.0) or rate_norm > 1.0)
        if terminated:
            reward -= 25.0
        truncated = self._step_idx >= self.max_steps

        next_obs = self._prepare_step_observation()
        info = {
            "att_err_deg": float(np.rad2deg(att_rad)),
            "rate_err_rad_s": rate_norm,
            "rho": ctrl_out.gate_decision.rho,
            "alpha": ctrl_out.gate_decision.alpha,
            "mode": ctrl_out.mode.value,
        }
        return next_obs, float(reward), terminated, truncated, info
