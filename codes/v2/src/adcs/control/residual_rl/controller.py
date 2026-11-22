"""Integrated CCR v2 Controller implementing Arms A4, A5, A6, A7 and all ablations.

Control path (CONTROL_ARCHITECTURE.md §3 & §13):
1. B5 classical backbone computes nominal tau_base (LQR or optional LQR+ESO).
2. B2 extracts onboard fault symptoms s.
3. B4/B8 supervisor evaluates control validity and mode M0–M4.
4. B6 residual policy proposes normalized action -> tau_rl_raw (or None if disabled/unavailable).
5. B7 deterministic authority gate computes tau_rl = rho * alpha * G * tau_rl_raw.
6. Combine tau_request = tau_base + tau_rl (bounded).
7. B9 actuator allocator enforces RW/MTQ physical constraints & logs requested vs allocated.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from adcs.control.allocation import ActuatorAllocator, AllocationConfig
from adcs.control.allocation.allocator import (
    detect_underactuated_axis,
    step_underactuated_latch,
)
from adcs.control.classical.baselines import (
    ESOConfig,
    ExtendedStateObserver,
    zoh_first_order_lag,
)
from adcs.control.classical.lqr import (
    ClassicalLQRConfig,
    ClassicalLQRController,
    apply_underactuated_magnetic_axis_law,
)
from adcs.control.reference import compute_attitude_error
from adcs.control.residual_rl.policy import ObservationBuilder, ResidualPolicyProtocol
from adcs.control.safety import DeterministicAuthorityGate, GateConfig
from adcs.control.supervisor import (
    ControlValiditySupervisor,
    FaultSymptomExtractor,
    SupervisorConfig,
)
from adcs.interfaces.types import (
    ActuatorCapabilityState,
    ActuatorCommand,
    ControlStepOutput,
    EstimatorOutput,
    FloatArray,
    ReferenceState,
    SensorMeasurement,
)
from adcs.utils.config import SpacecraftConfig


@dataclass(frozen=True)
class CCRControllerConfig:
    """Configuration defining any CCR v2 arm (A4, A5, A6, A7) or single-factor ablation."""

    name: str = "A7_ccr_v2_full"
    action_scale_nm: float | None = None  # Default: 0.4 * nominal RW torque limit
    use_eso_backbone: bool = False
    lqr: ClassicalLQRConfig | None = None  # Default: auto-scaled from SpacecraftConfig
    eso: ESOConfig = field(default_factory=ESOConfig)
    allocation: AllocationConfig = field(
        default_factory=lambda: AllocationConfig(
            capability_aware=True,
            use_conservative_effectiveness=False,
            compensate_bias=True,
            mtq_assist_enabled=True,
            mtq_unload_gain=0.004,
        )
    )
    gate: GateConfig = field(default_factory=GateConfig)
    supervisor: SupervisorConfig = field(default_factory=SupervisorConfig)


class CCRController:
    """Full CCR v2 residual-assisted controller with deterministic fallback (Invariant 10)."""

    def __init__(
        self,
        sc_config: SpacecraftConfig,
        policy: ResidualPolicyProtocol | None,
        config: CCRControllerConfig | None = None,
    ) -> None:
        self.sc_cfg = sc_config
        self.cfg = CCRControllerConfig() if config is None else config
        self.policy = policy
        self.rw_rotor_j = sc_config.reaction_wheels.rotor_inertia_kg_m2
        self._tau_lim = sc_config.reaction_wheels.torque_limit_nominal_nm
        self._action_scale_nm = (
            0.4 * self._tau_lim
            if self.cfg.action_scale_nm is None
            else float(self.cfg.action_scale_nm)
        )
        lqr_cfg = (
            ClassicalLQRConfig.from_spacecraft(sc_config)
            if self.cfg.lqr is None
            else self.cfg.lqr
        )
        self._max_tau_req = (
            3.0 * self._tau_lim
            if lqr_cfg.max_torque_request_nm is None
            else lqr_cfg.max_torque_request_nm
        )
        gate_cfg = self.cfg.gate
        if gate_cfg.max_residual_torque_nm is None:
            gate_cfg = GateConfig(
                **{**gate_cfg.__dict__, "max_residual_torque_nm": self._action_scale_nm}
            )

        self.backbone = ClassicalLQRController(sc_config, lqr_cfg, self.cfg.allocation)
        self.eso = ExtendedStateObserver(sc_config, self.cfg.eso)
        self.allocator = ActuatorAllocator(sc_config, self.cfg.allocation)
        self.symptoms = FaultSymptomExtractor(sc_config)
        self.supervisor = ControlValiditySupervisor(self.cfg.supervisor)
        self.gate = DeterministicAuthorityGate(gate_cfg)
        self.obs_builder = ObservationBuilder(sc_config, action_scale_nm=self._action_scale_nm)

        self._rw_tau_c = float(sc_config.reaction_wheels.time_constant_s)
        self._last_command: ActuatorCommand | None = None
        self._last_allocated_tau = np.zeros(3, dtype=np.float64)
        self._eso_expected_tau_lag = np.zeros(3, dtype=np.float64)
        self._prev_tau_rl_gated = np.zeros(3, dtype=np.float64)
        self._underactuated_count = 0
        self._underactuated_clear_count = 0
        self._underactuated_axis_latched: FloatArray | None = None
        self.reset()

    @property
    def name(self) -> str:
        return self.cfg.name

    def reset(self) -> None:
        self.backbone.reset()
        self.eso.reset()
        self.symptoms.reset()
        self.supervisor.reset()
        self.gate.reset()
        self._last_command = None
        self._last_allocated_tau = np.zeros(3, dtype=np.float64)
        self._eso_expected_tau_lag = np.zeros(3, dtype=np.float64)
        self._prev_tau_rl_gated = np.zeros(3, dtype=np.float64)
        self._underactuated_count = 0
        self._underactuated_clear_count = 0
        self._underactuated_axis_latched = None

    def build_observation_and_context(
        self,
        *,
        estimator_out: EstimatorOutput,
        reference: ReferenceState,
        capability: ActuatorCapabilityState,
        measurement: SensorMeasurement,
        dt_s: float,
    ) -> tuple[FloatArray, dict[str, object]]:
        """Compute classical backbone, symptoms, supervisor context, and 30-dim policy obs."""
        wheel_h_est = self.rw_rotor_j * np.asarray(measurement.rw_speed_rad_s, dtype=np.float64)
        att_err = compute_attitude_error(
            estimator_out.q_ib_est,
            estimator_out.omega_body_est_rad_s,
            reference,
        )

        d_hat = np.zeros(3, dtype=np.float64)
        if self.cfg.use_eso_backbone:
            tau_avg, self._eso_expected_tau_lag = zoh_first_order_lag(
                self._last_allocated_tau,
                self._eso_expected_tau_lag,
                self._rw_tau_c,
                dt_s,
            )
            d_hat = self.eso.update(
                omega_est=estimator_out.omega_body_est_rad_s,
                tau_expected_nm=tau_avg,
                wheel_momentum_nms=wheel_h_est,
                dt_s=dt_s,
                gamma_obs=estimator_out.gamma_obs,
                valid=estimator_out.valid,
            )

        kp_scale = float(np.clip(0.45 + 0.55 * estimator_out.gamma_obs, 0.45, 1.0))
        kd_scale = float(np.clip(0.85 + 0.15 * estimator_out.gamma_obs, 0.85, 1.0))
        tau_lqr, base_diag = self.backbone.compute_base_torque(
            estimator_out,
            reference,
            wheel_h_est,
            dt_s,
            kp_scale=kp_scale,
            kd_scale=kd_scale,
        )
        allow_fallback = (
            self.allocator.cfg.capability_aware and self.allocator.cfg.underactuated_mtq_fallback
        )
        detected_axis = (
            detect_underactuated_axis(
                self.sc_cfg.reaction_wheels.axis_matrix_body,
                capability,
                dead_eff_threshold=self.allocator.cfg.dead_wheel_eff_threshold,
            )
            if allow_fallback
            else None
        )
        (
            self._underactuated_count,
            self._underactuated_clear_count,
            self._underactuated_axis_latched,
        ) = step_underactuated_latch(
            detected_axis,
            self._underactuated_count,
            self._underactuated_clear_count,
            self._underactuated_axis_latched,
        )
        dead_axis = self._underactuated_axis_latched
        if dead_axis is not None:
            d_hat_eff = d_hat - float(np.dot(d_hat, dead_axis)) * dead_axis
            tau_base = apply_underactuated_magnetic_axis_law(
                self.sc_cfg,
                att_err.rotvec_rad,
                att_err.omega_err_body_rad_s,
                estimator_out.omega_body_est_rad_s,
                wheel_h_est,
                tau_lqr - d_hat_eff,
                dead_axis,
            )
        else:
            tau_base = tau_lqr - d_hat
        tau_norm = float(np.linalg.norm(tau_base))
        if tau_norm > self._max_tau_req:
            tau_base = tau_base * (self._max_tau_req / tau_norm)

        sym = self.symptoms.update(
            att_err_rad=att_err.geodesic_angle_rad,
            rate_err_norm_rad_s=float(np.linalg.norm(att_err.omega_err_body_rad_s)),
            estimator_out=estimator_out,
            capability=capability,
            measurement=measurement,
            last_command=self._last_command,
            dt_s=dt_s,
        )
        obs = self.obs_builder.build(
            att_err=att_err,
            tau_base_nm=tau_base,
            prev_tau_rl_gated_nm=self._prev_tau_rl_gated,
            estimator_out=estimator_out,
            capability=capability,
            symptoms=sym,
            measurement=measurement,
        )
        ctx: dict[str, object] = {
            "wheel_h_est": wheel_h_est,
            "att_err": att_err,
            "tau_base": tau_base,
            "base_diag": base_diag,
            "symptoms": sym,
            "dead_axis": dead_axis,
        }
        return obs, ctx

    def apply_raw_action(
        self,
        *,
        raw_action_norm: FloatArray | None,
        ctx: dict[str, object],
        estimator_out: EstimatorOutput,
        capability: ActuatorCapabilityState,
        measurement: SensorMeasurement,
        dt_s: float,
    ) -> ControlStepOutput:
        """Apply supervisor, deterministic gate, torque combination, and actuator allocation."""
        wheel_h_est: FloatArray = ctx["wheel_h_est"]  # type: ignore[assignment]
        att_err = ctx["att_err"]
        tau_base: FloatArray = ctx["tau_base"]  # type: ignore[assignment]
        base_diag: dict[str, float] = ctx["base_diag"]  # type: ignore[assignment]
        sym = ctx["symptoms"]

        policy_valid = raw_action_norm is not None and bool(
            np.asarray(raw_action_norm).shape == (3,) and np.all(np.isfinite(raw_action_norm))
        )
        sup_status = self.supervisor.update(
            estimator_out=estimator_out,
            capability=capability,
            symptoms=sym,  # type: ignore[arg-type]
            policy_valid=policy_valid,
        )

        tau_rl_raw = (
            None
            if raw_action_norm is None
            else np.asarray(raw_action_norm, dtype=np.float64) * self._action_scale_nm
        )
        gate_dec = self.gate.evaluate(
            tau_rl_raw_nm=tau_rl_raw,
            att_err_rad=att_err.geodesic_angle_rad,  # type: ignore[attr-defined]
            rate_err_norm_rad_s=float(
                np.linalg.norm(att_err.omega_err_body_rad_s)  # type: ignore[attr-defined]
            ),
            estimator_out=estimator_out,
            capability=capability,
            symptoms=sym,  # type: ignore[arg-type]
            supervisor_status=sup_status,
            dt_s=dt_s,
        )

        tau_request = tau_base + gate_dec.tau_rl_gated_nm
        req_norm = float(np.linalg.norm(tau_request))
        if req_norm > self._max_tau_req:
            tau_request = tau_request * (self._max_tau_req / req_norm)

        b_meas = measurement.mag_body_t if measurement.mag_valid else np.zeros(3, dtype=np.float64)
        dead_axis = ctx.get("dead_axis", self._underactuated_axis_latched)
        alloc = self.allocator.allocate(
            tau_request,
            wheel_momentum_nms=wheel_h_est,
            b_field_body_t=b_meas,
            capability=capability,
            dead_axis_override=dead_axis,  # type: ignore[arg-type]
            use_underactuated=(dead_axis is not None),
        )
        self.backbone.apply_anti_windup(tau_request, alloc.tau_total_allocated_nm, dt_s)

        cmd = ActuatorCommand(
            rw_torque_cmd_nm=alloc.rw_torque_cmd_nm,
            mtq_dipole_cmd_am2=alloc.mtq_dipole_cmd_am2,
            tau_request_nm=alloc.tau_request_nm,
            tau_allocated_nm=alloc.tau_total_allocated_nm,
        )
        self._last_command = cmd
        self._last_allocated_tau = alloc.tau_total_allocated_nm.copy()
        self._prev_tau_rl_gated = gate_dec.tau_rl_gated_nm.copy()

        return ControlStepOutput(
            command=cmd,
            tau_base_nm=tau_base,
            gate_decision=gate_dec,
            mode=sup_status.mode,
            diagnostics={
                **base_diag,
                "supervisor_unsafe_reason": sup_status.unsafe_reason,
                "authority_infeasible": bool(
                    self.gate.cfg.use_supervisor and sup_status.authority_infeasible
                ),
                "degradation_indicator": sym.degradation_indicator,  # type: ignore[attr-defined]
                "infeasible_torque_norm_nm": float(np.linalg.norm(alloc.infeasible_residual_nm)),
                "rw_saturated": alloc.rw_saturated,
                "mtq_saturated": alloc.mtq_saturated,
            },
        )

    def compute(
        self,
        *,
        estimator_out: EstimatorOutput,
        reference: ReferenceState,
        capability: ActuatorCapabilityState,
        measurement: SensorMeasurement,
        dt_s: float,
    ) -> ControlStepOutput:
        obs, ctx = self.build_observation_and_context(
            estimator_out=estimator_out,
            reference=reference,
            capability=capability,
            measurement=measurement,
            dt_s=dt_s,
        )
        raw_action: FloatArray | None = None
        if self.policy is not None:
            try:
                raw_action = self.policy.predict(obs, deterministic=True)
            except Exception:
                # Invariant 10: policy exception safely triggers deterministic fallback
                raw_action = None
        return self.apply_raw_action(
            raw_action_norm=raw_action,
            ctx=ctx,
            estimator_out=estimator_out,
            capability=capability,
            measurement=measurement,
            dt_s=dt_s,
        )
