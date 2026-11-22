"""Strong classical fault-tolerant baseline controllers (Arms A0, A1, A2, A3).

- A0: ClassicalLQRController (nominal LQR + nominal allocation)
- A1: OracleAllocationLQRController (LQR + oracle capability allocation, diagnostic only)
- A2: ClassicalDOBController (LQR + Extended State Observer disturbance rejection)
- A3: StrongClassicalController (LQR + ESO/DOB + onboard capability allocation + gain schedule)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from adcs.control.allocation import AllocationConfig
from adcs.control.allocation.allocator import (
    detect_underactuated_axis,
    step_underactuated_latch,
)
from adcs.control.classical.lqr import (
    ClassicalLQRConfig,
    ClassicalLQRController,
    apply_underactuated_magnetic_axis_law,
)
from adcs.control.reference import compute_attitude_error
from adcs.interfaces.types import (
    ActuatorCapabilityState,
    ActuatorCommand,
    ControlStepOutput,
    EstimatorOutput,
    FloatArray,
    GateDecision,
    ReferenceState,
    SensorMeasurement,
    SupervisorMode,
)
from adcs.utils.config import SpacecraftConfig


@dataclass(frozen=True)
class ESOConfig:
    """Extended State Observer (DOB/ESO) parameters for disturbance & mismatch rejection."""

    observer_bandwidth_rad_s: float = 0.75  # Critically damped poles at -omega_o
    disturbance_leak_rad_s: float = 0.02  # Small leak prevents unbounded drift
    disturbance_limit_nm: float | None = None  # Default: 0.8 * nominal RW torque limit
    min_gamma_obs_for_update: float = 0.35  # Freeze ESO during severe sensor outages


class ExtendedStateObserver:
    """3-axis nonlinear Extended State Observer estimating lumped body disturbance torque.

    Models J * d(omega)/dt = tau_known - omega x (J*omega + A_rw*h_w) + d_lumped.
    """

    def __init__(self, sc_config: SpacecraftConfig, cfg: ESOConfig | None = None) -> None:
        self.cfg = ESOConfig() if cfg is None else cfg
        self.inertia = sc_config.inertia_matrix_kg_m2.copy()
        self.inertia_inv = np.linalg.inv(self.inertia)
        self.a_rw = sc_config.reaction_wheels.axis_matrix_body.copy()
        self._dist_lim = (
            0.8 * sc_config.reaction_wheels.torque_limit_nominal_nm
            if self.cfg.disturbance_limit_nm is None
            else self.cfg.disturbance_limit_nm
        )
        self.reset()

    def reset(self) -> None:
        self._omega_hat = np.zeros(3, dtype=np.float64)
        self._d_hat = np.zeros(3, dtype=np.float64)
        self._initialized = False

    @property
    def disturbance_estimate_nm(self) -> FloatArray:
        return self._d_hat.copy()

    def update(
        self,
        *,
        omega_est: FloatArray,
        tau_expected_nm: FloatArray,
        wheel_momentum_nms: FloatArray,
        dt_s: float,
        gamma_obs: float,
        valid: bool,
    ) -> FloatArray:
        if not valid or not np.all(np.isfinite(omega_est)):
            # Decay disturbance estimate gently on invalid state
            self._d_hat *= float(np.exp(-0.5 * dt_s))
            return self._d_hat.copy()

        if not self._initialized:
            self._omega_hat = omega_est.copy()
            self._d_hat = np.zeros(3, dtype=np.float64)
            self._initialized = True
            return self._d_hat.copy()

        if gamma_obs < self.cfg.min_gamma_obs_for_update:
            # Freeze disturbance integration during sensor dropout, leak slowly
            self._omega_hat = omega_est.copy()
            self._d_hat *= float(np.exp(-0.2 * dt_s))
            return self._d_hat.copy()

        wo = self.cfg.observer_bandwidth_rad_s
        beta1 = 2.0 * wo
        beta2 = wo * wo

        err = omega_est - self._omega_hat
        h_tot = self.inertia @ self._omega_hat + self.a_rw @ wheel_momentum_nms
        gyro = np.cross(self._omega_hat, h_tot)

        domega_hat = (
            self.inertia_inv @ (tau_expected_nm - gyro + self._d_hat) + beta1 * err
        )
        dd_hat = beta2 * (self.inertia @ err) - self.cfg.disturbance_leak_rad_s * self._d_hat

        self._omega_hat = self._omega_hat + domega_hat * dt_s
        self._d_hat = np.clip(
            self._d_hat + dd_hat * dt_s,
            -self._dist_lim,
            self._dist_lim,
        )
        return self._d_hat.copy()


def zoh_first_order_lag(
    u_target: FloatArray,
    prev_state: FloatArray,
    tau_c: float,
    dt_s: float,
) -> tuple[FloatArray, FloatArray]:
    """Return (interval_average, end_of_step_state) for ZOH first-order lag over dt_s."""
    dt = max(float(dt_s), 1e-4)
    if tau_c > 1e-6:
        decay = float(np.exp(-dt / tau_c))
        u_avg = u_target + (prev_state - u_target) * (tau_c / dt) * (1.0 - decay)
        next_state = u_target + (prev_state - u_target) * decay
        return u_avg, next_state
    return u_target, u_target.copy()


class ClassicalDOBController(ClassicalLQRController):
    """Arm A2: Classical LQR + Extended State Observer (DOB/ESO) disturbance rejection."""

    def __init__(
        self,
        sc_config: SpacecraftConfig,
        lqr_config: ClassicalLQRConfig | None = None,
        alloc_config: AllocationConfig | None = None,
        eso_config: ESOConfig | None = None,
        *,
        name: str = "A2_classical_dob_eso",
    ) -> None:
        super().__init__(sc_config, lqr_config, alloc_config, name=name)
        self.eso = ExtendedStateObserver(sc_config, eso_config)
        self._rw_tau_c = float(sc_config.reaction_wheels.time_constant_s)
        self._last_allocated_tau = np.zeros(3, dtype=np.float64)
        self._eso_expected_tau_lag = np.zeros(3, dtype=np.float64)

    def reset(self) -> None:
        super().reset()
        self.eso.reset()
        self._last_allocated_tau = np.zeros(3, dtype=np.float64)
        self._eso_expected_tau_lag = np.zeros(3, dtype=np.float64)

    def _update_eso(
        self,
        estimator_out: EstimatorOutput,
        wheel_h_est: FloatArray,
        dt_s: float,
    ) -> FloatArray:
        tau_avg, self._eso_expected_tau_lag = zoh_first_order_lag(
            self._last_allocated_tau,
            self._eso_expected_tau_lag,
            self._rw_tau_c,
            dt_s,
        )
        return self.eso.update(
            omega_est=estimator_out.omega_body_est_rad_s,
            tau_expected_nm=tau_avg,
            wheel_momentum_nms=wheel_h_est,
            dt_s=dt_s,
            gamma_obs=estimator_out.gamma_obs,
            valid=estimator_out.valid,
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
        wheel_h_est = self.rw_rotor_j * measurement.rw_speed_rad_s
        d_hat = self._update_eso(estimator_out, wheel_h_est, dt_s)

        tau_lqr, diag = self.compute_base_torque(
            estimator_out, reference, wheel_h_est, dt_s
        )
        tau_base = tau_lqr - d_hat
        tau_norm = float(np.linalg.norm(tau_base))
        if tau_norm > self._max_tau_req:
            tau_base = tau_base * (self._max_tau_req / tau_norm)

        b_meas = measurement.mag_body_t if measurement.mag_valid else np.zeros(3, dtype=np.float64)
        alloc = self.allocator.allocate(
            tau_base,
            wheel_momentum_nms=wheel_h_est,
            b_field_body_t=b_meas,
            capability=capability,
        )
        self.apply_anti_windup(tau_base, alloc.tau_total_allocated_nm, dt_s)
        self._last_allocated_tau = alloc.tau_total_allocated_nm.copy()

        cmd = ActuatorCommand(
            rw_torque_cmd_nm=alloc.rw_torque_cmd_nm,
            mtq_dipole_cmd_am2=alloc.mtq_dipole_cmd_am2,
            tau_request_nm=alloc.tau_request_nm,
            tau_allocated_nm=alloc.tau_total_allocated_nm,
        )
        gate_disabled = GateDecision(
            rho=0.0,
            alpha=0.0,
            directional_gain_xyz=np.zeros(3, dtype=np.float64),
            tau_rl_raw_nm=np.zeros(3, dtype=np.float64),
            tau_rl_gated_nm=np.zeros(3, dtype=np.float64),
            rl_enabled=False,
            rejected_reason="classical_baseline_no_rl",
            mode=SupervisorMode.M0_NOMINAL,
        )
        return ControlStepOutput(
            command=cmd,
            tau_base_nm=tau_base,
            gate_decision=gate_disabled,
            mode=SupervisorMode.M0_NOMINAL,
            diagnostics={
                **diag,
                "eso_disturbance_norm_nm": float(np.linalg.norm(d_hat)),
                "infeasible_torque_norm_nm": float(np.linalg.norm(alloc.infeasible_residual_nm)),
                "rw_saturated": alloc.rw_saturated,
                "mtq_saturated": alloc.mtq_saturated,
            },
        )


class StrongClassicalController(ClassicalDOBController):
    """Arm A3: Strongest practical classical baseline (LQR + ESO + capability alloc + schedule)."""

    def __init__(
        self,
        sc_config: SpacecraftConfig,
        lqr_config: ClassicalLQRConfig | None = None,
        eso_config: ESOConfig | None = None,
        *,
        name: str = "A3_strong_classical",
    ) -> None:
        alloc_cfg = AllocationConfig(
            capability_aware=True,
            use_conservative_effectiveness=False,
            compensate_bias=True,
            mtq_assist_enabled=True,
            mtq_unload_gain=0.004,
        )
        super().__init__(sc_config, lqr_config, alloc_cfg, eso_config, name=name)
        self._underactuated_count = 0
        self._underactuated_clear_count = 0
        self._underactuated_axis_latched: FloatArray | None = None

    def reset(self) -> None:
        super().reset()
        self._underactuated_count = 0
        self._underactuated_clear_count = 0
        self._underactuated_axis_latched = None

    def compute(
        self,
        *,
        estimator_out: EstimatorOutput,
        reference: ReferenceState,
        capability: ActuatorCapabilityState,
        measurement: SensorMeasurement,
        dt_s: float,
    ) -> ControlStepOutput:
        wheel_h_est = self.rw_rotor_j * measurement.rw_speed_rad_s
        d_hat = self._update_eso(estimator_out, wheel_h_est, dt_s)

        # Deterministic, bounded gain schedule:
        # 1. Under low observability (e.g., ST dropout), soften proportional gain to avoid chasing
        #    integrated gyro drift while retaining rate damping.
        kp_scale = float(np.clip(0.45 + 0.55 * estimator_out.gamma_obs, 0.45, 1.0))
        kd_scale = float(np.clip(0.85 + 0.15 * estimator_out.gamma_obs, 0.85, 1.0))

        tau_lqr, diag = self.compute_base_torque(
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
                self.a_rw,
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
            # Freeze ESO contribution along the dead axis to prevent windup against MTQ saturation
            d_hat_eff = d_hat - float(np.dot(d_hat, dead_axis)) * dead_axis
            tau_base = tau_lqr - d_hat_eff
            att_err = compute_attitude_error(
                estimator_out.q_ib_est, estimator_out.omega_body_est_rad_s, reference
            )
            tau_base = apply_underactuated_magnetic_axis_law(
                self.sc_cfg,
                att_err.rotvec_rad,
                att_err.omega_err_body_rad_s,
                estimator_out.omega_body_est_rad_s,
                wheel_h_est,
                tau_base,
                dead_axis,
            )
        else:
            tau_base = tau_lqr - d_hat
        tau_norm = float(np.linalg.norm(tau_base))
        if tau_norm > self._max_tau_req:
            tau_base = tau_base * (self._max_tau_req / tau_norm)

        b_meas = measurement.mag_body_t if measurement.mag_valid else np.zeros(3, dtype=np.float64)
        alloc = self.allocator.allocate(
            tau_base,
            wheel_momentum_nms=wheel_h_est,
            b_field_body_t=b_meas,
            capability=capability,
            dead_axis_override=dead_axis,
            use_underactuated=(dead_axis is not None),
        )
        self.apply_anti_windup(tau_base, alloc.tau_total_allocated_nm, dt_s)
        self._last_allocated_tau = alloc.tau_total_allocated_nm.copy()

        cmd = ActuatorCommand(
            rw_torque_cmd_nm=alloc.rw_torque_cmd_nm,
            mtq_dipole_cmd_am2=alloc.mtq_dipole_cmd_am2,
            tau_request_nm=alloc.tau_request_nm,
            tau_allocated_nm=alloc.tau_total_allocated_nm,
        )
        gate_disabled = GateDecision(
            rho=0.0,
            alpha=0.0,
            directional_gain_xyz=np.zeros(3, dtype=np.float64),
            tau_rl_raw_nm=np.zeros(3, dtype=np.float64),
            tau_rl_gated_nm=np.zeros(3, dtype=np.float64),
            rl_enabled=False,
            rejected_reason="classical_baseline_no_rl",
            mode=SupervisorMode.M0_NOMINAL,
        )
        return ControlStepOutput(
            command=cmd,
            tau_base_nm=tau_base,
            gate_decision=gate_disabled,
            mode=SupervisorMode.M0_NOMINAL,
            diagnostics={
                **diag,
                "kp_scale": kp_scale,
                "kd_scale": kd_scale,
                "eso_disturbance_norm_nm": float(np.linalg.norm(d_hat)),
                "infeasible_torque_norm_nm": float(np.linalg.norm(alloc.infeasible_residual_nm)),
                "rw_saturated": alloc.rw_saturated,
                "mtq_saturated": alloc.mtq_saturated,
            },
        )


def make_oracle_allocation_lqr(sc_config: SpacecraftConfig) -> ClassicalLQRController:
    """Arm A1: Classical LQR + oracle capability-aware allocation (non-deployable diagnostic)."""
    return ClassicalLQRController(
        sc_config,
        alloc_config=AllocationConfig(
            capability_aware=True,
            use_conservative_effectiveness=False,
            compensate_bias=True,
            mtq_assist_enabled=True,
            mtq_unload_gain=0.004,
        ),
        name="A1_classical_oracle_alloc",
    )
