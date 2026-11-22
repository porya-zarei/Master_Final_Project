"""B7 — Deterministic Residual Authority Gate (core CCR v2 mechanism).

Computes:
    tau_RL = rho * alpha * G * tau_RL_raw

Separating three orthogonal concepts (CONTROL_ARCHITECTURE.md §11):
- rho in [0, 1]: Need (baseline insufficiency / tracking or residual mismatch)
- alpha in [0, 1]: Trust (observability, covariance, capability confidence, OOD, supervisor mode)
  with asymmetric slew rate limiting (instant drop on M3/invalid, fast decrease, slow recovery)
- G: Directional capability gate from conservative AMS margin (diagonal or geometry-aware)

Each factor (`enable_rho`, `enable_alpha`, `enable_directional_g`, `use_supervisor`) is
independently ablatable for clean experiments (Arms A4, A5, A6, A7 and ablations).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from adcs.control.supervisor.supervisor import SupervisorStatus
from adcs.control.supervisor.symptoms import SymptomSummary
from adcs.estimation.capability import ams_support_function
from adcs.interfaces.types import (
    ActuatorCapabilityState,
    EstimatorOutput,
    FloatArray,
    GateDecision,
    SupervisorMode,
)


@dataclass(frozen=True)
class GateConfig:
    """Configurable, auditable parameters for B7 Deterministic Authority Gate."""

    # Ablation switches (all True for full CCR v2 Arm A7)
    enable_rho: bool = True
    enable_alpha: bool = True
    enable_directional_g: bool = True
    use_supervisor: bool = True
    use_geometry_projection: bool = False  # Optional geometry-aware directional ablation

    # Need scalar `rho` scaling & deadband
    rho_att_scale_rad: float = 0.08  # ~4.6 deg -> contributes 1.0 to need score
    rho_rate_scale_rad_s: float = 0.015  # 0.015 rad/s -> contributes 1.0 to need score
    rho_resid_scale: float = 0.35  # torque residual norm -> contributes 1.0
    rho_resid_noise_floor: float = 0.045  # 5 Hz tach diff noise floor (~0.035-0.045 * tau_lim)
    rho_att_deadzone_rad: float = 0.0035  # ~0.20 deg, inside ST noise floor
    rho_rate_deadzone_rad_s: float = 0.0012
    rho_deadband: float = 0.06  # quiet nominal pointing -> rho == 0
    rho_full_score: float = 1.0

    # Trust scalar `alpha` operational thresholds
    trust_att_std_nom_rad: float = 0.004
    trust_att_std_scale_rad: float = 0.03
    trust_ood_rate_nom_rad_s: float = 0.12
    trust_ood_rate_scale_rad_s: float = 0.15
    alpha_slew_down_per_s: float = 2.5  # Fast authority reduction
    alpha_slew_up_per_s: float = 0.35  # Conservative slow recovery

    # Directional gate `G`
    directional_exponent: float = 1.0  # g_k = margin_k ^ exponent

    # Hard residual authority envelope (None -> scaled automatically from spacecraft RW limit)
    max_residual_torque_nm: float | None = 0.06


class DeterministicAuthorityGate:
    """Non-learned, deterministic, fail-conservative residual authority gate (B7)."""

    def __init__(self, config: GateConfig | None = None) -> None:
        self.cfg = GateConfig() if config is None else config
        self.reset()

    def reset(self) -> None:
        self._alpha_filtered = 0.0

    @property
    def current_alpha(self) -> float:
        return self._alpha_filtered

    def compute_need_rho(
        self,
        att_err_rad: float,
        rate_err_norm_rad_s: float,
        symptoms: SymptomSummary,
    ) -> float:
        """Compute bounded need scalar rho in [0, 1] from tracking & mismatch indicators."""
        if not self.cfg.enable_rho:
            return 1.0
        if not (np.isfinite(att_err_rad) and np.isfinite(rate_err_norm_rad_s)):
            return 0.0
        att_excess = max(0.0, abs(att_err_rad) - self.cfg.rho_att_deadzone_rad)
        rate_excess = max(0.0, abs(rate_err_norm_rad_s) - self.cfg.rho_rate_deadzone_rad_s)
        resid_excess = max(0.0, symptoms.max_torque_residual_norm - self.cfg.rho_resid_noise_floor)
        score = (
            att_excess / max(self.cfg.rho_att_scale_rad, 1e-6)
            + rate_excess / max(self.cfg.rho_rate_scale_rad_s, 1e-6)
            + resid_excess / max(self.cfg.rho_resid_scale, 1e-6)
        )
        span = max(self.cfg.rho_full_score - self.cfg.rho_deadband, 1e-6)
        return float(np.clip((score - self.cfg.rho_deadband) / span, 0.0, 1.0))

    def compute_raw_trust_alpha(
        self,
        estimator_out: EstimatorOutput,
        capability: ActuatorCapabilityState,
        supervisor_status: SupervisorStatus,
    ) -> float:
        """Compute strictly monotonic trust scalar alpha_raw in [0, 1] from operational factors."""
        if not self.cfg.enable_alpha:
            if self.cfg.use_supervisor and not supervisor_status.rl_permitted:
                return 0.0
            return 1.0

        # Invalid or stale state -> immediately zero trust
        if (
            not estimator_out.valid
            or not capability.valid
            or capability.stale
            or not np.isfinite(estimator_out.gamma_obs)
            or not np.isfinite(capability.confidence)
        ):
            return 0.0

        t_obs = float(np.clip(estimator_out.gamma_obs, 0.0, 1.0))
        t_cap = float(np.clip(capability.confidence, 0.0, 1.0))

        att_std_rms = float(np.sqrt(np.mean(np.square(estimator_out.attitude_std_rad))))
        if not np.isfinite(att_std_rms):
            return 0.0
        t_cov = float(
            np.exp(
                -max(0.0, att_std_rms - self.cfg.trust_att_std_nom_rad)
                / max(self.cfg.trust_att_std_scale_rad, 1e-6)
            )
        )

        rate_norm = float(np.linalg.norm(estimator_out.omega_body_est_rad_s))
        if not np.isfinite(rate_norm):
            return 0.0
        t_ood = float(
            np.exp(
                -max(0.0, rate_norm - self.cfg.trust_ood_rate_nom_rad_s)
                / max(self.cfg.trust_ood_rate_scale_rad_s, 1e-6)
            )
        )

        t_mode = supervisor_status.mode_trust_multiplier if self.cfg.use_supervisor else 1.0
        # Conservative combination: min(t_obs, t_cov) * t_cap * t_ood * t_mode
        # Strictly monotonic in every uncertainty/observability/validity input.
        return float(np.clip(t_mode * min(t_obs, t_cov) * t_cap * t_ood, 0.0, 1.0))

    def compute_directional_gain(
        self,
        capability: ActuatorCapabilityState,
        tau_rl_raw_nm: FloatArray,
    ) -> FloatArray:
        """Compute directional capability gain vector g in [0, 1]^3 from conservative AMS."""
        if not self.cfg.enable_directional_g:
            return np.ones(3, dtype=np.float64)
        if not capability.valid or capability.stale:
            return np.zeros(3, dtype=np.float64)
        if not np.all(np.isfinite(capability.directional_margin_xyz)):
            return np.zeros(3, dtype=np.float64)

        if self.cfg.use_geometry_projection and float(np.linalg.norm(tau_rl_raw_nm)) > 1e-9:
            v_hat = tau_rl_raw_nm / float(np.linalg.norm(tau_rl_raw_nm))
            h_nom = ams_support_function(capability, v_hat, conservative=False)
            h_cons = ams_support_function(capability, v_hat, conservative=True)
            m_dir = float(np.clip(h_cons / h_nom, 0.0, 1.0)) if h_nom > 1e-9 else 0.0
            g_scalar = m_dir ** self.cfg.directional_exponent
            return np.full(3, g_scalar, dtype=np.float64)

        margins = np.clip(capability.directional_margin_xyz, 0.0, 1.0)
        return np.power(margins, self.cfg.directional_exponent)

    def evaluate(
        self,
        *,
        tau_rl_raw_nm: FloatArray | None,
        att_err_rad: float,
        rate_err_norm_rad_s: float,
        estimator_out: EstimatorOutput,
        capability: ActuatorCapabilityState,
        symptoms: SymptomSummary,
        supervisor_status: SupervisorStatus,
        dt_s: float,
    ) -> GateDecision:
        """Apply deterministic need, trust (with asymmetric slew), directional gate, and bounds."""
        mode = supervisor_status.mode
        zero3 = np.zeros(3, dtype=np.float64)

        # 1. Policy unavailable or non-finite proposal -> immediate safe fallback (zero residual)
        if tau_rl_raw_nm is None:
            self._alpha_filtered = 0.0
            return GateDecision(
                rho=0.0,
                alpha=0.0,
                directional_gain_xyz=zero3,
                tau_rl_raw_nm=zero3,
                tau_rl_gated_nm=zero3,
                rl_enabled=False,
                rejected_reason="policy_unavailable",
                mode=mode,
            )

        raw = np.asarray(tau_rl_raw_nm, dtype=np.float64)
        if raw.shape != (3,) or not np.all(np.isfinite(raw)):
            self._alpha_filtered = 0.0
            return GateDecision(
                rho=0.0,
                alpha=0.0,
                directional_gain_xyz=zero3,
                tau_rl_raw_nm=zero3,
                tau_rl_gated_nm=zero3,
                rl_enabled=False,
                rejected_reason="non_finite_policy_output",
                mode=mode,
            )

        # 2. Supervisor M3 / hard invalid state -> instantaneous zeroing (no slew delay!)
        if self.cfg.use_supervisor and (
            mode == SupervisorMode.M3_UNKNOWN_INVALID_UNSAFE or not supervisor_status.rl_permitted
        ):
            self._alpha_filtered = 0.0
            return GateDecision(
                rho=0.0,
                alpha=0.0,
                directional_gain_xyz=zero3,
                tau_rl_raw_nm=raw.copy(),
                tau_rl_gated_nm=zero3,
                rl_enabled=False,
                rejected_reason=supervisor_status.unsafe_reason or "supervisor_m3_fallback",
                mode=mode,
            )

        rho = self.compute_need_rho(att_err_rad, rate_err_norm_rad_s, symptoms)
        alpha_target = self.compute_raw_trust_alpha(estimator_out, capability, supervisor_status)

        # 3. Asymmetric slew-rate limiting on trust alpha
        dt = max(float(dt_s), 1e-4)
        if not self.cfg.enable_alpha:
            self._alpha_filtered = alpha_target
        elif alpha_target <= 0.0:
            self._alpha_filtered = 0.0
        elif alpha_target < self._alpha_filtered:
            max_drop = self.cfg.alpha_slew_down_per_s * dt
            self._alpha_filtered = max(alpha_target, self._alpha_filtered - max_drop)
        else:
            # Never allow upward slew when data is stale or invalid
            if estimator_out.valid and capability.valid and not capability.stale:
                max_rise = self.cfg.alpha_slew_up_per_s * dt
                self._alpha_filtered = min(alpha_target, self._alpha_filtered + max_rise)
        alpha = float(np.clip(self._alpha_filtered, 0.0, 1.0))

        # 4. Directional capability gate G and hard torque norm cap
        g_vec = self.compute_directional_gain(capability, raw)
        max_res = (
            0.06
            if self.cfg.max_residual_torque_nm is None
            else self.cfg.max_residual_torque_nm
        )
        # Bound raw proposal before gating
        raw_norm = float(np.linalg.norm(raw))
        raw_bounded = raw * (max_res / raw_norm) if raw_norm > max_res else raw.copy()
        tau_gated = rho * alpha * (g_vec * raw_bounded)

        # Final hard safety clamp on gated residual
        gated_norm = float(np.linalg.norm(tau_gated))
        if gated_norm > max_res:
            tau_gated = tau_gated * (max_res / gated_norm)

        rejected: str | None = None
        if alpha <= 1e-9:
            rejected = "zero_trust_alpha"
        elif rho <= 1e-9:
            rejected = "zero_need_rho"

        return GateDecision(
            rho=rho,
            alpha=alpha,
            directional_gain_xyz=g_vec,
            tau_rl_raw_nm=raw.copy(),
            tau_rl_gated_nm=tau_gated,
            rl_enabled=(alpha > 1e-9 and rho > 1e-9),
            rejected_reason=rejected,
            mode=mode,
            diagnostics={"alpha_target": alpha_target},
        )
