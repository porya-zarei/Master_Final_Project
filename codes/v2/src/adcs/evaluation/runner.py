"""Paired deterministic episode runner separating truth, sensors, estimator, capability, control."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from adcs.control.reference import NadirReferenceGenerator, compute_attitude_error
from adcs.estimation import (
    MEKFConfig,
    MultiplicativeEKF,
    OnlineCapabilityEstimator,
    OracleCapabilityEstimator,
)
from adcs.evaluation.metrics import EpisodeMetrics, SuccessCriteria, compute_episode_metrics
from adcs.faults import FaultInjector, ScenarioSpec
from adcs.interfaces import ActuatorCommand, ControllerProtocol
from adcs.sensors import SensorSuite, SensorSuiteConfig
from adcs.simulation.fast import FastSimulatorBackend
from adcs.utils.config import SpacecraftConfig
from adcs.utils.quaternion import quat_from_axis_angle, quat_multiply
from adcs.utils.seeding import EpisodeSeedBundle, SeedManager


@dataclass(frozen=True)
class EpisodeStepRecord:
    """Compact per-step diagnostic log sufficient to reconstruct every control & gate decision."""

    time_s: float
    att_err_deg: float
    rate_err_rad_s: float
    est_att_err_deg: float
    gamma_obs: float
    tau_base_nm: np.ndarray
    tau_rl_raw_nm: np.ndarray
    tau_rl_gated_nm: np.ndarray
    tau_request_nm: np.ndarray
    tau_allocated_nm: np.ndarray
    tau_achieved_total_nm: np.ndarray
    rw_torque_cmd_nm: np.ndarray
    rw_torque_achieved_nm: np.ndarray
    wheel_momentum_nms: np.ndarray
    mtq_dipole_cmd_am2: np.ndarray
    mtq_torque_achieved_nm: np.ndarray
    rho: float
    alpha: float
    directional_gain_xyz: np.ndarray
    cap_margin_est_xyz: np.ndarray
    cap_margin_oracle_xyz: np.ndarray
    mode: str
    rejected_reason: str | None


@dataclass(frozen=True)
class EpisodeLog:
    """Full episode metrics + optional time-series trace."""

    metrics: EpisodeMetrics
    steps: list[EpisodeStepRecord]


class EpisodeRunner:
    """Runs paired deterministic closed-loop ADCS episodes across any controller arm."""

    def __init__(
        self,
        sc_config: SpacecraftConfig,
        sensor_config: SensorSuiteConfig | None = None,
        mekf_config: MEKFConfig | None = None,
        criteria: SuccessCriteria | None = None,
    ) -> None:
        self.sc_cfg = sc_config
        self.sensor_cfg = sensor_config
        self.mekf_config = mekf_config
        self.criteria = criteria

    def run_episode(
        self,
        controller: ControllerProtocol,
        scenario: ScenarioSpec,
        *,
        seed: int,
        use_oracle_capability: bool = False,
        record_trace: bool = False,
    ) -> EpisodeLog:
        """Execute one deterministic episode on paired `seed` and compute full metrics."""
        seeds = EpisodeSeedBundle.from_episode_seed(seed)
        init_rng = SeedManager(seeds.initial_state_seed).spawn_rng("init")

        # Build plant with scenario-specific physical parameters (S7 inertia/dipole/lag mismatch)
        inertia_true = self.sc_cfg.inertia_matrix_kg_m2 * np.diag(scenario.inertia_scale_xyz)
        sim = FastSimulatorBackend(
            self.sc_cfg,
            inertia_override_kg_m2=inertia_true,
            residual_dipole_override_am2=np.asarray(scenario.residual_dipole_am2, dtype=float),
            rw_time_constant_override_s=(
                self.sc_cfg.reaction_wheels.time_constant_s * scenario.rw_time_constant_scale
            ),
        )
        ref_gen = NadirReferenceGenerator()
        sensors = SensorSuite(self.sensor_cfg, n_rw=self.sc_cfg.reaction_wheels.count)
        mekf = MultiplicativeEKF(self.mekf_config)
        oracle_cap = OracleCapabilityEstimator(self.sc_cfg)
        online_cap = OnlineCapabilityEstimator(self.sc_cfg)
        injector = FaultInjector(self.sc_cfg, scenario.events)

        # Deterministic paired initial orbit anomaly & attitude/rate perturbation
        nu0 = float(init_rng.uniform(0.0, 360.0))
        st0 = sim.reset(true_anomaly_deg_init=nu0)
        ref0 = ref_gen.compute(st0.time_s, st0.position_eci_m, st0.velocity_eci_m_s)

        axis = init_rng.normal(size=3)
        axis = axis / max(float(np.linalg.norm(axis)), 1e-9)
        q_pert = quat_from_axis_angle(axis, np.deg2rad(scenario.initial_attitude_err_deg))
        q_init = quat_multiply(ref0.q_ir, q_pert)

        w_dir = init_rng.normal(size=3)
        w_dir = w_dir / max(float(np.linalg.norm(w_dir)), 1e-9)
        w_init = ref0.omega_ref_inertial_in_ref_rad_s + w_dir * scenario.initial_rate_err_rad_s
        h_init = np.asarray(scenario.initial_wheel_momentum_nms, dtype=np.float64)

        truth = sim.reset(
            q_ib_init=q_init,
            omega_body_init=w_init,
            wheel_momentum_init=h_init,
            true_anomaly_deg_init=nu0,
        )
        ref_gen.reset()
        sensors.reset(seed=seeds.sensor_noise_seed, q_ib_init=q_init)
        mekf.reset(q_ib_init=q_init, omega_init=w_init, time_s=0.0)
        oracle_cap.reset()
        online_cap.reset()
        controller.reset()

        dt = self.sc_cfg.simulation.control_period_s
        n_steps = int(round(scenario.duration_s / dt))

        times = np.zeros(n_steps, dtype=np.float64)
        att_errs = np.zeros(n_steps, dtype=np.float64)
        rate_errs = np.zeros(n_steps, dtype=np.float64)
        rw_ach = np.zeros((n_steps, self.sc_cfg.reaction_wheels.count), dtype=np.float64)
        mtq_ach = np.zeros((n_steps, self.sc_cfg.magnetorquers.count), dtype=np.float64)
        tau_reqs = np.zeros((n_steps, 3), dtype=np.float64)
        tau_achs = np.zeros((n_steps, 3), dtype=np.float64)
        rw_sats = np.zeros(n_steps, dtype=bool)
        rhos = np.zeros(n_steps, dtype=np.float64)
        alphas = np.zeros(n_steps, dtype=np.float64)
        rl_norms = np.zeros(n_steps, dtype=np.float64)
        rejects = np.zeros(n_steps, dtype=bool)
        auth_infeasible_flags = np.zeros(n_steps, dtype=bool)
        modes: list[str] = []
        cycle_ms = np.zeros(n_steps, dtype=np.float64)
        trace: list[EpisodeStepRecord] = []

        last_cmd: ActuatorCommand | None = None
        min_oracle_rank = 3
        oracle_zero_margin_steps = 0

        for k in range(n_steps):
            act_faults, sens_faults = injector.evaluate(truth.time_s)
            sim.set_fault_state(act_faults)

            meas = sensors.measure(truth, dt_s=dt, faults=sens_faults)
            ref = ref_gen.compute(truth.time_s, truth.position_eci_m, truth.velocity_eci_m_s)

            t_start = time.perf_counter()
            est_out = mekf.update(meas, dt_s=dt)
            cap_est = online_cap.estimate(
                time_s=truth.time_s,
                measurement=meas,
                last_command=last_cmd,
                b_field_body_t=meas.mag_body_t,
                dt_s=dt,
            )
            cap_ora = oracle_cap.estimate(
                time_s=truth.time_s,
                measurement=meas,
                last_command=last_cmd,
                b_field_body_t=meas.mag_body_t,
                dt_s=dt,
                truth_override={
                    "actuator_faults": act_faults,
                    "wheel_momentum_nms": truth.wheel_momentum_nms,
                    "b_field_body_t": truth.b_field_body_t,
                },
            )
            min_oracle_rank = min(min_oracle_rank, cap_ora.effective_rank)
            if float(np.min(cap_ora.directional_margin_xyz)) < 0.05:
                oracle_zero_margin_steps += 1
            cap_for_ctrl = cap_ora if use_oracle_capability else cap_est

            ctrl_out = controller.compute(
                estimator_out=est_out,
                reference=ref,
                capability=cap_for_ctrl,
                measurement=meas,
                dt_s=dt,
            )
            cycle_ms[k] = (time.perf_counter() - t_start) * 1000.0
            last_cmd = ctrl_out.command

            truth = sim.step(
                ctrl_out.command.rw_torque_cmd_nm,
                ctrl_out.command.mtq_dipole_cmd_am2,
                dt_s=dt,
            ).truth

            ref_next = ref_gen.compute(truth.time_s, truth.position_eci_m, truth.velocity_eci_m_s)
            true_err = compute_attitude_error(truth.q_ib, truth.omega_body_rad_s, ref_next)
            est_err = compute_attitude_error(est_out.q_ib_est, est_out.omega_body_est_rad_s, ref)

            tau_rw_body = self.sc_cfg.reaction_wheels.axis_matrix_body @ truth.rw_torque_achieved_nm
            tau_tot_ach = tau_rw_body + truth.mtq_torque_achieved_nm

            times[k] = truth.time_s
            att_errs[k] = float(np.rad2deg(true_err.geodesic_angle_rad))
            rate_errs[k] = float(np.linalg.norm(true_err.omega_err_body_rad_s))
            rw_ach[k] = truth.rw_torque_achieved_nm
            mtq_ach[k] = truth.mtq_dipole_achieved_am2
            tau_reqs[k] = ctrl_out.command.tau_request_nm
            tau_achs[k] = tau_tot_ach
            rw_sats[k] = any(truth.actuator_status.rw_torque_saturated) or any(
                truth.actuator_status.rw_momentum_saturated
            )
            rhos[k] = ctrl_out.gate_decision.rho
            alphas[k] = ctrl_out.gate_decision.alpha
            rl_norms[k] = float(np.linalg.norm(ctrl_out.gate_decision.tau_rl_gated_nm))
            rejects[k] = ctrl_out.gate_decision.rejected_reason is not None and (
                ctrl_out.gate_decision.rejected_reason != "classical_baseline_no_rl"
            )
            auth_infeasible_flags[k] = bool(
                ctrl_out.diagnostics.get("authority_infeasible", False)
            )
            modes.append(ctrl_out.mode.value)

            if record_trace:
                trace.append(
                    EpisodeStepRecord(
                        time_s=truth.time_s,
                        att_err_deg=att_errs[k],
                        rate_err_rad_s=rate_errs[k],
                        est_att_err_deg=float(np.rad2deg(est_err.geodesic_angle_rad)),
                        gamma_obs=est_out.gamma_obs,
                        tau_base_nm=ctrl_out.tau_base_nm.copy(),
                        tau_rl_raw_nm=ctrl_out.gate_decision.tau_rl_raw_nm.copy(),
                        tau_rl_gated_nm=ctrl_out.gate_decision.tau_rl_gated_nm.copy(),
                        tau_request_nm=ctrl_out.command.tau_request_nm.copy(),
                        tau_allocated_nm=ctrl_out.command.tau_allocated_nm.copy(),
                        tau_achieved_total_nm=tau_tot_ach.copy(),
                        rw_torque_cmd_nm=ctrl_out.command.rw_torque_cmd_nm.copy(),
                        rw_torque_achieved_nm=truth.rw_torque_achieved_nm.copy(),
                        wheel_momentum_nms=truth.wheel_momentum_nms.copy(),
                        mtq_dipole_cmd_am2=ctrl_out.command.mtq_dipole_cmd_am2.copy(),
                        mtq_torque_achieved_nm=truth.mtq_torque_achieved_nm.copy(),
                        rho=ctrl_out.gate_decision.rho,
                        alpha=ctrl_out.gate_decision.alpha,
                        directional_gain_xyz=ctrl_out.gate_decision.directional_gain_xyz.copy(),
                        cap_margin_est_xyz=cap_est.directional_margin_xyz.copy(),
                        cap_margin_oracle_xyz=cap_ora.directional_margin_xyz.copy(),
                        mode=ctrl_out.mode.value,
                        rejected_reason=ctrl_out.gate_decision.rejected_reason,
                    )
                )

        fault_onset = min((ev.start_s for ev in scenario.events), default=0.0)
        metrics = compute_episode_metrics(
            scenario_id=scenario.scenario_id,
            category=scenario.category,
            split=scenario.split,
            controller_arm=controller.name,
            seed=seed,
            times_s=times,
            att_err_deg=att_errs,
            rate_err_rad_s=rate_errs,
            rw_torque_achieved_nm=rw_ach,
            mtq_dipole_achieved_am2=mtq_ach,
            tau_request_nm=tau_reqs,
            tau_achieved_total_nm=tau_achs,
            rw_saturated_any=rw_sats,
            rho_hist=rhos,
            alpha_hist=alphas,
            rl_torque_norm_nm=rl_norms,
            gate_rejected=rejects,
            modes=modes,
            cycle_times_ms=cycle_ms,
            fault_onset_s=fault_onset,
            min_oracle_rank=min_oracle_rank,
            dt_s=dt,
            criteria=self.criteria,
            authority_infeasible_flags=auth_infeasible_flags,
            oracle_zero_margin_steps=oracle_zero_margin_steps,
        )
        return EpisodeLog(metrics=metrics, steps=trace)
