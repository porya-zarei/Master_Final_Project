"""B4/B8 — Control-Validity Ladder & Deterministic Fault-Hypothesis Supervisor.

Implements operating modes M0–M4 (CONTROL_ARCHITECTURE.md §8 & §12) with explicit guards,
persistence/hysteresis, contradictory-evidence conservatism, and zero RL dependency.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from adcs.control.supervisor.symptoms import SymptomSummary
from adcs.interfaces.types import (
    ActuatorCapabilityState,
    EstimatorOutput,
    SupervisorMode,
)


@dataclass(frozen=True)
class SupervisorConfig:
    """Explicit transition guards and hysteresis parameters for modes M0–M4."""

    gamma_unsafe_min: float = 0.25  # Below this -> immediate M3
    gamma_suspect_thresh: float = 0.75  # Below this -> M1 suspected degradation
    gamma_recover_min: float = 0.65  # Required to exit M3 into M4
    max_data_age_s: float = 15.0  # Stale estimator data -> immediate M3
    deg_suspect_thresh: float = 0.15  # Degradation indicator to enter M1
    deg_confirm_thresh: float = 0.25  # Degradation indicator to enter M2
    deg_clear_thresh: float = 0.08  # Strict hysteresis threshold to clear degradation
    min_cap_conf_for_confirm: float = 0.35  # Uncertain diagnosis != confirmed fault
    contradictory_resid_thresh: float = 0.45  # High residual with low cap confidence -> M3
    contradictory_cap_conf_max: float = 0.25
    persist_suspect_steps: int = 3
    persist_confirm_steps: int = 8
    persist_contradictory_steps: int = 10
    persist_recover_m3_steps: int = 10
    persist_clear_deg_steps: int = 15
    persist_m4_to_m0_steps: int = 15
    infeasible_deficit_thresh: float = 0.35
    persist_infeasible_steps: int = 12


@dataclass(frozen=True)
class SupervisorStatus:
    """Typed output of the supervisory state machine."""

    mode: SupervisorMode
    rl_permitted: bool
    mode_trust_multiplier: float
    unsafe_reason: str | None
    transitioned: bool
    previous_mode: SupervisorMode
    authority_infeasible: bool = False


class ControlValiditySupervisor:
    """Deterministic finite-state supervisor implementing M0–M4 validity ladder."""

    MODE_TRUST_MAP: dict[SupervisorMode, float] = {
        SupervisorMode.M0_NOMINAL: 1.0,
        SupervisorMode.M1_SUSPECTED_DEGRADATION: 0.6,
        SupervisorMode.M2_CONFIRMED_DEGRADATION: 0.85,
        SupervisorMode.M3_UNKNOWN_INVALID_UNSAFE: 0.0,
        SupervisorMode.M4_RECOVERY: 0.5,
    }

    def __init__(self, config: SupervisorConfig | None = None) -> None:
        self.cfg = SupervisorConfig() if config is None else config
        self.reset()

    def reset(self) -> None:
        self._mode = SupervisorMode.M0_NOMINAL
        self._suspect_count = 0
        self._confirm_count = 0
        self._contradict_count = 0
        self._healthy_count = 0
        self._recovery_hold_count = 0
        self._infeasible_count = 0
        self._infeasible_latched = False

    @property
    def mode(self) -> SupervisorMode:
        return self._mode

    def _check_hard_unsafe(
        self,
        estimator_out: EstimatorOutput,
        capability: ActuatorCapabilityState,
        policy_valid: bool,
    ) -> str | None:
        if not estimator_out.valid:
            return "estimator_invalid"
        if (
            not np.all(np.isfinite(estimator_out.q_ib_est))
            or not np.all(np.isfinite(estimator_out.omega_body_est_rad_s))
            or not np.isfinite(estimator_out.gamma_obs)
        ):
            return "estimator_non_finite"
        if estimator_out.gamma_obs < self.cfg.gamma_unsafe_min:
            return "low_observability_gamma_obs"
        if estimator_out.data_age_s > self.cfg.max_data_age_s:
            return "stale_estimator_data"
        if not capability.valid or capability.stale:
            return "capability_invalid_or_stale"
        if not np.all(np.isfinite(capability.directional_margin_xyz)):
            return "capability_non_finite"
        if capability.effective_rank == 0:
            return "zero_effective_actuator_rank"
        if not policy_valid:
            return "policy_invalid_or_unavailable"
        return None

    def update(
        self,
        *,
        estimator_out: EstimatorOutput,
        capability: ActuatorCapabilityState,
        symptoms: SymptomSummary,
        policy_valid: bool = True,
    ) -> SupervisorStatus:
        prev = self._mode
        unsafe_reason = self._check_hard_unsafe(estimator_out, capability, policy_valid)

        # 1. Immediate fail-conservative entry into M3 on ANY invalid/unsafe condition
        if unsafe_reason is not None:
            self._mode = SupervisorMode.M3_UNKNOWN_INVALID_UNSAFE
            self._healthy_count = 0
            self._recovery_hold_count = 0
            return SupervisorStatus(
                mode=self._mode,
                rl_permitted=False,
                mode_trust_multiplier=0.0,
                unsafe_reason=unsafe_reason,
                transitioned=(self._mode != prev),
                previous_mode=prev,
                authority_infeasible=self._infeasible_latched,
            )

        # Explicit physical authority infeasibility detection with persistence & hysteresis
        infeasible_cond = (
            symptoms.authority_deficit_norm > self.cfg.infeasible_deficit_thresh
        ) or (
            capability.effective_rank < 3
            and symptoms.authority_deficit_norm > 0.5 * self.cfg.infeasible_deficit_thresh
        )
        if infeasible_cond:
            self._infeasible_count += 1
            if self._infeasible_count >= self.cfg.persist_infeasible_steps:
                self._infeasible_latched = True
        else:
            self._infeasible_count = max(0, self._infeasible_count - 1)
            if self._infeasible_count == 0:
                self._infeasible_latched = False

        if self._infeasible_latched:
            self._mode = SupervisorMode.M3_UNKNOWN_INVALID_UNSAFE
            self._healthy_count = 0
            self._recovery_hold_count = 0
            return SupervisorStatus(
                mode=self._mode,
                rl_permitted=False,
                mode_trust_multiplier=0.0,
                unsafe_reason="physical_authority_infeasible",
                transitioned=(self._mode != prev),
                previous_mode=prev,
                authority_infeasible=True,
            )

        # Check contradictory / unknown fault evidence (high torque residual + low cap confidence)
        contradictory = (
            symptoms.max_torque_residual_norm > self.cfg.contradictory_resid_thresh
            and capability.confidence < self.cfg.contradictory_cap_conf_max
        )
        if contradictory:
            self._contradict_count += 1
        else:
            self._contradict_count = max(0, self._contradict_count - 1)

        if self._contradict_count >= self.cfg.persist_contradictory_steps:
            self._mode = SupervisorMode.M3_UNKNOWN_INVALID_UNSAFE
            self._healthy_count = 0
            self._recovery_hold_count = 0
            return SupervisorStatus(
                mode=self._mode,
                rl_permitted=False,
                mode_trust_multiplier=0.0,
                unsafe_reason="contradictory_or_unknown_fault_evidence",
                transitioned=(self._mode != prev),
                previous_mode=prev,
                authority_infeasible=self._infeasible_latched,
            )

        deg = symptoms.degradation_indicator
        obs_degraded = estimator_out.gamma_obs < self.cfg.gamma_suspect_thresh
        suspect_cond = (deg > self.cfg.deg_suspect_thresh) or obs_degraded
        confirm_cond = (
            deg > self.cfg.deg_confirm_thresh
            and capability.confidence >= self.cfg.min_cap_conf_for_confirm
        )
        clear_cond = (
            deg < self.cfg.deg_clear_thresh
            and estimator_out.gamma_obs >= self.cfg.gamma_recover_min
        )

        # 2. Mode-specific guarded transitions with persistence & hysteresis
        if self._mode == SupervisorMode.M3_UNKNOWN_INVALID_UNSAFE:
            if estimator_out.gamma_obs >= self.cfg.gamma_recover_min:
                self._healthy_count += 1
                if self._healthy_count >= self.cfg.persist_recover_m3_steps:
                    self._mode = SupervisorMode.M4_RECOVERY
                    self._recovery_hold_count = 0
                    self._healthy_count = 0
            else:
                self._healthy_count = 0

        elif self._mode == SupervisorMode.M0_NOMINAL:
            if suspect_cond:
                self._suspect_count += 1
                if self._suspect_count >= self.cfg.persist_suspect_steps:
                    self._mode = SupervisorMode.M1_SUSPECTED_DEGRADATION
                    self._suspect_count = 0
                    self._confirm_count = 0
            else:
                self._suspect_count = 0

        elif self._mode == SupervisorMode.M1_SUSPECTED_DEGRADATION:
            if confirm_cond:
                self._confirm_count += 1
                self._healthy_count = 0
                if self._confirm_count >= self.cfg.persist_confirm_steps:
                    self._mode = SupervisorMode.M2_CONFIRMED_DEGRADATION
                    self._confirm_count = 0
            elif clear_cond:
                self._healthy_count += 1
                self._confirm_count = 0
                if self._healthy_count >= self.cfg.persist_clear_deg_steps:
                    self._mode = SupervisorMode.M4_RECOVERY
                    self._recovery_hold_count = 0
                    self._healthy_count = 0
            else:
                self._confirm_count = max(0, self._confirm_count - 1)
                self._healthy_count = 0

        elif self._mode == SupervisorMode.M2_CONFIRMED_DEGRADATION:
            if clear_cond:
                self._healthy_count += 1
                if self._healthy_count >= self.cfg.persist_clear_deg_steps:
                    self._mode = SupervisorMode.M4_RECOVERY
                    self._recovery_hold_count = 0
                    self._healthy_count = 0
            else:
                self._healthy_count = 0

        elif self._mode == SupervisorMode.M4_RECOVERY:
            if suspect_cond:
                self._suspect_count += 1
                self._recovery_hold_count = 0
                if self._suspect_count >= self.cfg.persist_suspect_steps:
                    self._mode = SupervisorMode.M1_SUSPECTED_DEGRADATION
                    self._suspect_count = 0
            else:
                self._suspect_count = 0
                self._recovery_hold_count += 1
                if self._recovery_hold_count >= self.cfg.persist_m4_to_m0_steps:
                    self._mode = SupervisorMode.M0_NOMINAL
                    self._recovery_hold_count = 0

        mult = self.MODE_TRUST_MAP[self._mode]
        return SupervisorStatus(
            mode=self._mode,
            rl_permitted=(self._mode != SupervisorMode.M3_UNKNOWN_INVALID_UNSAFE),
            mode_trust_multiplier=mult,
            unsafe_reason=None,
            transitioned=(self._mode != prev),
            previous_mode=prev,
            authority_infeasible=self._infeasible_latched,
        )
