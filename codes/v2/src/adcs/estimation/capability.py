"""B3 — Actuator Capability Estimation and Attainable Moment Set (AMS).

Strictly separates:
- `OracleCapabilityEstimator` (`is_oracle=True`): ground-truth capability for A1/A6 diagnostics.
- `OnlineCapabilityEstimator` (`is_oracle=False`): onboard-only RLS effectiveness & bias
  estimator using commanded RW torque vs. tachometer-derived rotor acceleration.

Implements AMS directional support function h_T(v) = sum_i |(B^T v)_i| u_max,i and conservative
directional margins m_dir(v) = h_cons(v) / h_nom(v) (CONTROL_ARCHITECTURE.md §7.3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from adcs.actuators.models import ActuatorFaultState
from adcs.interfaces.types import (
    ActuatorCapabilityState,
    ActuatorCommand,
    FloatArray,
    MTQCapability,
    SensorMeasurement,
    WheelCapability,
)
from adcs.utils.config import SpacecraftConfig


@dataclass(frozen=True)
class CapabilityEstimatorConfig:
    """Parameters for onboard B3 capability estimation and conservative uncertainty bounds."""

    forgetting_factor: float = 0.96  # RLS exponential forgetting on excited axes
    excitation_threshold_nm: float | None = None  # Default: 5% of nominal RW torque limit
    init_effectiveness: float = 1.0
    init_gain_std: float = 0.05  # Small initial prior uncertainty on nominal healthy wheels
    process_noise_gain: float = 1.5e-4  # Applied only when wheel is excited
    process_noise_bias: float | None = None  # Default scales with tau_lim^2
    meas_noise_torque_nm: float | None = None  # Default: 4% of nominal RW torque limit
    conservative_k_sigma: float = 2.0  # Lower bound g_min = clip(g_hat - k*sigma, 0, 1)
    momentum_guard_margin_nms: float | None = None  # Default: 4% of effective momentum limit
    stale_timeout_s: float = 2.0

    @classmethod
    def from_spacecraft(cls, sc_config: SpacecraftConfig) -> CapabilityEstimatorConfig:
        tau_lim = sc_config.reaction_wheels.torque_limit_nominal_nm
        h_lim = sc_config.reaction_wheels.effective_momentum_limit_nms
        return cls(
            excitation_threshold_nm=max(1e-6, 0.05 * tau_lim),
            process_noise_bias=max(1e-12, (0.01 * tau_lim) ** 2),
            meas_noise_torque_nm=max(1e-6, 0.04 * tau_lim),
            momentum_guard_margin_nms=max(1e-5, 0.04 * h_lim),
        )


def ams_support_function(
    capability: ActuatorCapabilityState,
    direction_body: FloatArray,
    *,
    conservative: bool = True,
    include_mtq: bool = False,
) -> float:
    """Evaluate directional AMS support function h_T(v) for unit direction v in body frame.

    Uses signed wheel headroom (available_pos_torque_nm, available_neg_torque_nm) so
    momentum-wall asymmetries are accurately represented.
    """
    v = np.asarray(direction_body, dtype=np.float64)
    v_norm = float(np.linalg.norm(v))
    if v_norm <= 1e-12 or not np.all(np.isfinite(v)):
        raise ValueError(f"direction_body must be a finite non-zero 3-vector, got {v!r}")
    v_hat = v / v_norm

    support = 0.0
    for w in capability.wheels:
        if not w.valid:
            continue
        proj = float(np.dot(w.axis_body, v_hat))
        if conservative:
            # Conservative achievable body torque along +v_hat:
            # If proj > 0, push positive wheel torque; if proj < 0, push negative wheel torque.
            # Scale nominal torque capacity by effectiveness_min / max(effectiveness_nom, eps).
            ratio = (
                w.effectiveness_min / max(w.effectiveness_nom, 1e-6)
                if w.effectiveness_nom > 1e-6
                else 0.0
            )
            pos_cap = max(0.0, w.available_pos_torque_nm * min(1.0, ratio) - w.bias_bound_nm)
            neg_cap = max(0.0, w.available_neg_torque_nm * min(1.0, ratio) - w.bias_bound_nm)
            support += proj * pos_cap if proj >= 0.0 else (-proj) * neg_cap
        else:
            support += abs(proj) * w.torque_limit_nm

    if include_mtq:
        for m in capability.mtqs:
            if not m.valid:
                continue
            # instantaneous_torque_vector_nm already equals (a_j x B) * m_max * g_min
            proj_m = abs(float(np.dot(m.instantaneous_torque_vector_nm, v_hat)))
            support += proj_m
    return float(max(0.0, support))


def _assemble_capability_state(
    *,
    time_s: float,
    wheels: tuple[WheelCapability, ...],
    mtqs: tuple[MTQCapability, ...],
    is_oracle: bool,
    stale: bool,
    valid: bool,
    diagnostics: dict[str, Any],
) -> ActuatorCapabilityState:
    dummy = ActuatorCapabilityState(
        time_s=time_s,
        wheels=wheels,
        mtqs=mtqs,
        nominal_support_xyz=np.zeros(3),
        conservative_support_xyz=np.zeros(3),
        directional_margin_xyz=np.zeros(3),
        effective_rank=0,
        confidence=0.0,
        is_oracle=is_oracle,
        stale=stale,
        valid=valid,
    )
    h_nom = np.zeros(3, dtype=np.float64)
    h_cons = np.zeros(3, dtype=np.float64)
    m_dir = np.zeros(3, dtype=np.float64)
    for ax in range(3):
        e = np.zeros(3, dtype=np.float64)
        e[ax] = 1.0
        h_n = ams_support_function(dummy, e, conservative=False, include_mtq=False)
        # Bidirectional conservative minimum of +e_ax and -e_ax
        h_c = min(
            ams_support_function(dummy, e, conservative=True, include_mtq=False),
            ams_support_function(dummy, -e, conservative=True, include_mtq=False),
        )
        h_nom[ax] = h_n
        h_cons[ax] = h_c
        m_dir[ax] = float(np.clip(h_c / h_n, 0.0, 1.0)) if h_n > 1e-9 else 0.0

    # Effective RW rank from conservative effectiveness matrix
    if wheels:
        b_cons = np.column_stack(
            [w.axis_body * (w.effectiveness_min if w.valid else 0.0) for w in wheels]
        )
        svals = np.linalg.svd(b_cons, compute_uv=False)
        eff_rank = int(np.sum(svals > 0.05))
        conf = float(np.mean([w.confidence for w in wheels])) if valid and not stale else 0.0
    else:
        eff_rank = 0
        conf = 0.0

    return ActuatorCapabilityState(
        time_s=time_s,
        wheels=wheels,
        mtqs=mtqs,
        nominal_support_xyz=h_nom,
        conservative_support_xyz=h_cons,
        directional_margin_xyz=m_dir,
        effective_rank=eff_rank,
        confidence=float(np.clip(conf, 0.0, 1.0)),
        is_oracle=is_oracle,
        stale=stale,
        valid=valid,
        diagnostics=diagnostics,
    )


def _momentum_headroom(
    h_i: float, h_lim: float, tau_eff_max: float, guard_margin: float
) -> tuple[float, float, bool]:
    """Compute available positive/negative body torque respecting wheel momentum saturation wall.

    Remember dh/dt = -tau_body:
    - Near +h_lim: negative body torque (which increases h) is restricted.
    - Near -h_lim: positive body torque (which decreases h) is restricted.
    """
    h_sat = abs(h_i) >= h_lim - 1e-6
    pos_frac = 1.0
    neg_frac = 1.0
    if h_i > h_lim - guard_margin:
        neg_frac = float(np.clip((h_lim - h_i) / max(guard_margin, 1e-6), 0.0, 1.0))
    if h_i < -h_lim + guard_margin:
        pos_frac = float(np.clip((h_lim + h_i) / max(guard_margin, 1e-6), 0.0, 1.0))
    return tau_eff_max * pos_frac, tau_eff_max * neg_frac, h_sat


class OracleCapabilityEstimator:
    """Privileged ground-truth capability estimator (`is_oracle=True`, diagnostic arms A1/A6)."""

    def __init__(
        self,
        sc_config: SpacecraftConfig,
        cfg: CapabilityEstimatorConfig | None = None,
    ) -> None:
        self.sc_cfg = sc_config
        self.cfg = (
            CapabilityEstimatorConfig.from_spacecraft(sc_config) if cfg is None else cfg
        )
        self.n_rw = sc_config.reaction_wheels.count
        self.n_mtq = sc_config.magnetorquers.count
        self.a_rw = sc_config.reaction_wheels.axis_matrix_body.copy()
        self.a_mtq = sc_config.magnetorquers.axis_matrix_body.copy()
        self.tau_lim = sc_config.reaction_wheels.torque_limit_nominal_nm
        self.h_lim = sc_config.reaction_wheels.effective_momentum_limit_nms
        self.rotor_j = sc_config.reaction_wheels.rotor_inertia_kg_m2
        self.m_lim = sc_config.magnetorquers.dipole_limit_per_axis_am2
        self._guard_margin = (
            0.04 * self.h_lim
            if self.cfg.momentum_guard_margin_nms is None
            else self.cfg.momentum_guard_margin_nms
        )

    def reset(self) -> None:
        return None

    def estimate(
        self,
        *,
        time_s: float,
        measurement: SensorMeasurement,
        last_command: ActuatorCommand | None,
        b_field_body_t: FloatArray,
        dt_s: float,
        truth_override: dict[str, Any] | None = None,
    ) -> ActuatorCapabilityState:
        del last_command, dt_s
        faults: ActuatorFaultState | None = (
            truth_override.get("actuator_faults") if truth_override else None
        )
        h_true = (
            np.asarray(truth_override["wheel_momentum_nms"], dtype=np.float64)
            if truth_override and "wheel_momentum_nms" in truth_override
            else self.rotor_j * measurement.rw_speed_rad_s
        )
        b_use = (
            np.asarray(truth_override["b_field_body_t"], dtype=np.float64)
            if truth_override and "b_field_body_t" in truth_override
            else b_field_body_t
        )

        wheels: list[WheelCapability] = []
        for i in range(self.n_rw):
            if faults is not None:
                locked = faults.rw.locked[i] or (faults.rw.stuck_torque_nm[i] is not None)
                g_true = 0.0 if locked else float(faults.rw.effectiveness[i])
                bias_true = (
                    float(faults.rw.stuck_torque_nm[i])  # type: ignore[arg-type]
                    if faults.rw.stuck_torque_nm[i] is not None
                    else float(faults.rw.torque_bias_nm[i])
                )
            else:
                g_true = 1.0
                bias_true = 0.0
            pos_cap, neg_cap, h_sat = _momentum_headroom(
                float(h_true[i]),
                self.h_lim,
                self.tau_lim * g_true,
                self._guard_margin,
            )
            wheels.append(
                WheelCapability(
                    axis_body=self.a_rw[:, i].copy(),
                    effectiveness_nom=g_true,
                    effectiveness_min=g_true,
                    effectiveness_max=g_true,
                    bias_est_nm=bias_true,
                    bias_bound_nm=0.0,
                    torque_limit_nm=self.tau_lim,
                    momentum_limit_nms=self.h_lim,
                    current_momentum_nms=float(h_true[i]),
                    available_pos_torque_nm=pos_cap,
                    available_neg_torque_nm=neg_cap,
                    saturated_torque=False,
                    saturated_momentum=h_sat,
                    confidence=1.0,
                    valid=True,
                )
            )

        mtqs: list[MTQCapability] = []
        for j in range(self.n_mtq):
            if faults is not None:
                g_m = 0.0 if faults.mtq.dropout[j] else float(faults.mtq.effectiveness[j])
            else:
                g_m = 1.0
            axis_j = self.a_mtq[:, j].copy()
            tau_vec = np.cross(axis_j, b_use) * (self.m_lim * g_m)
            mtqs.append(
                MTQCapability(
                    axis_body=axis_j,
                    effectiveness_nom=g_m,
                    effectiveness_min=g_m,
                    effectiveness_max=g_m,
                    dipole_limit_am2=self.m_lim,
                    instantaneous_torque_vector_nm=tau_vec,
                    confidence=1.0,
                    valid=True,
                )
            )

        return _assemble_capability_state(
            time_s=time_s,
            wheels=tuple(wheels),
            mtqs=tuple(mtqs),
            is_oracle=True,
            stale=False,
            valid=True,
            diagnostics={"source": "oracle_truth"},
        )


class OnlineCapabilityEstimator:
    """Onboard-only RW/MTQ capability estimator (`is_oracle=False`).

    Tracks per-wheel effectiveness g_i and torque bias b_i using a 2-parameter Kalman/RLS filter
    comparing predicted first-order RW torque response against tachometer-inferred body torque
    `tau_meas_i = -I_w * (omega_w(k) - omega_w(k-1)) / dt`.
    Never reads truth fault states.
    """

    def __init__(
        self,
        sc_config: SpacecraftConfig,
        cfg: CapabilityEstimatorConfig | None = None,
    ) -> None:
        self.sc_cfg = sc_config
        self.cfg = (
            CapabilityEstimatorConfig.from_spacecraft(sc_config) if cfg is None else cfg
        )
        self.n_rw = sc_config.reaction_wheels.count
        self.n_mtq = sc_config.magnetorquers.count
        self.a_rw = sc_config.reaction_wheels.axis_matrix_body.copy()
        self.a_mtq = sc_config.magnetorquers.axis_matrix_body.copy()
        self.tau_lim = sc_config.reaction_wheels.torque_limit_nominal_nm
        self.h_lim = sc_config.reaction_wheels.effective_momentum_limit_nms
        self.rotor_j = sc_config.reaction_wheels.rotor_inertia_kg_m2
        self.tau_c = sc_config.reaction_wheels.time_constant_s
        self.m_lim = sc_config.magnetorquers.dipole_limit_per_axis_am2
        self._exc_thresh = (
            max(1e-6, 0.05 * self.tau_lim)
            if self.cfg.excitation_threshold_nm is None
            else self.cfg.excitation_threshold_nm
        )
        self._meas_noise = (
            max(1e-6, 0.04 * self.tau_lim)
            if self.cfg.meas_noise_torque_nm is None
            else self.cfg.meas_noise_torque_nm
        )
        self._q_bias = (
            max(1e-12, (0.01 * self.tau_lim) ** 2)
            if self.cfg.process_noise_bias is None
            else self.cfg.process_noise_bias
        )
        self._guard_margin = (
            max(1e-5, 0.04 * self.h_lim)
            if self.cfg.momentum_guard_margin_nms is None
            else self.cfg.momentum_guard_margin_nms
        )
        self.reset()

    def reset(self) -> None:
        # Per-wheel state theta_i = [g_i, bias_i] and 2x2 covariance P_i
        self._theta = np.zeros((self.n_rw, 2), dtype=np.float64)
        self._theta[:, 0] = self.cfg.init_effectiveness
        self._p = np.zeros((self.n_rw, 2, 2), dtype=np.float64)
        init_b_std = max(1e-5, 0.015 * self.tau_lim)
        for i in range(self.n_rw):
            self._p[i] = np.diag([self.cfg.init_gain_std**2, init_b_std**2])
        self._prev_rw_speed: FloatArray | None = None
        self._prev_time_s: float | None = None
        self._pred_tau_lag = np.zeros(self.n_rw, dtype=np.float64)
        self._last_valid_t = 0.0
        self._residual_ema = np.zeros(self.n_rw, dtype=np.float64)
        self._dead_count = np.zeros(self.n_rw, dtype=int)
        self._unexcited_time_s = np.zeros(self.n_rw, dtype=np.float64)

    def estimate(
        self,
        *,
        time_s: float,
        measurement: SensorMeasurement,
        last_command: ActuatorCommand | None,
        b_field_body_t: FloatArray,
        dt_s: float,
        truth_override: dict[str, Any] | None = None,
    ) -> ActuatorCapabilityState:
        del truth_override  # Strictly forbidden for onboard estimator!

        t = float(time_s)
        dt = max(float(dt_s), 1e-4)
        rw_speeds = np.asarray(measurement.rw_speed_rad_s, dtype=np.float64)
        rw_valid = measurement.rw_speed_valid
        any_rw_valid = any(rw_valid) and bool(np.all(np.isfinite(rw_speeds)))

        if any_rw_valid:
            self._last_valid_t = t

        # Update per-wheel RLS/KF from last command and tachometer speed delta
        if last_command is not None and self._prev_rw_speed is not None and any_rw_valid:
            u_cmd = np.clip(last_command.rw_torque_cmd_nm, -self.tau_lim, self.tau_lim)
            # Propagate nominal first-order actuator torque state over dt
            if self.tau_c > 1e-6:
                decay = float(np.exp(-dt / self.tau_c))
                # Average torque over [t-dt, t] for step input u_cmd:
                # avg = u_cmd + (tau_0 - u_cmd) * (tau_c / dt) * (1 - exp(-dt / tau_c))
                u_avg = u_cmd + (self._pred_tau_lag - u_cmd) * (self.tau_c / dt) * (1.0 - decay)
                self._pred_tau_lag = u_cmd + (self._pred_tau_lag - u_cmd) * decay
            else:
                u_avg = u_cmd
                self._pred_tau_lag = u_cmd.copy()

            for i in range(self.n_rw):
                if not rw_valid[i]:
                    # Inflate uncertainty when tachometer unavailable
                    self._p[i, 0, 0] = min(0.25, self._p[i, 0, 0] + 0.01)
                    continue
                h_now = self.rotor_j * float(rw_speeds[i])
                h_prev = self.rotor_j * float(self._prev_rw_speed[i])
                # Skip update when pinned on momentum wall (wall torque != gain loss)
                wall_tol = 0.003 * self.h_lim
                if abs(h_now) >= self.h_lim - wall_tol and abs(h_prev) >= self.h_lim - wall_tol:
                    continue

                tau_meas = -(h_now - h_prev) / dt
                u_eff_i = float(u_avg[i])
                excited = abs(u_eff_i) >= self._exc_thresh
                self._unexcited_time_s[i] = 0.0 if excited else self._unexcited_time_s[i] + dt

                # Directional forgetting (Plot 07 fix): ONLY apply exponential forgetting & gain
                # process noise on excited axes so quiet steady-state pointing never inflates
                # gain variance P[0,0] spuriously.
                p_pred = self._p[i].copy()
                if excited:
                    p_pred = p_pred / self.cfg.forgetting_factor + np.diag(
                        [self.cfg.process_noise_gain, self._q_bias]
                    )
                else:
                    # Freeze gain uncertainty; allow gentle bias tracking only
                    p_pred[1, 1] = p_pred[1, 1] / self.cfg.forgetting_factor + self._q_bias

                p_pred[0, 0] = min(p_pred[0, 0], 0.25)
                p_pred[1, 1] = min(p_pred[1, 1], (0.5 * self.tau_lim) ** 2)

                # Observation model: tau_meas = u_eff_i * g_i + 1.0 * bias_i
                pred_val = u_eff_i * float(self._theta[i, 0]) + float(self._theta[i, 1])
                resid = tau_meas - pred_val
                self._residual_ema[i] = 0.8 * self._residual_ema[i] + 0.2 * abs(resid)

                # Adaptive process noise boost when large sudden residual indicates abrupt fault
                abrupt_thresh = 0.16 * self.tau_lim
                if abs(resid) > abrupt_thresh and excited:
                    p_pred[0, 0] = min(0.25, p_pred[0, 0] + 0.08)
                    p_pred[1, 1] = min(
                        (0.5 * self.tau_lim) ** 2, p_pred[1, 1] + (0.15 * self.tau_lim) ** 2
                    )

                # Dead-wheel disambiguation: when a wheel receives significant torque command
                # yet produces near-zero measured acceleration (< 1.5% tau_lim) for >= 3 steps
                # and is not cancelled by estimated bias, update gain directly without letting
                # collinear phantom bias stall g_hat above 0.
                dead_wheel_signature = (
                    excited
                    and abs(tau_meas) < 0.015 * self.tau_lim
                    and abs(u_eff_i + float(self._theta[i, 1])) > 0.12 * self.tau_lim
                )
                if dead_wheel_signature:
                    self._dead_count[i] += 1
                else:
                    self._dead_count[i] = 0

                if self._dead_count[i] >= 3:
                    phi = np.array([u_eff_i, 0.0], dtype=np.float64)
                    self._theta[i, 1] *= 0.85
                elif excited:
                    phi = np.array([u_eff_i, 1.0], dtype=np.float64)
                else:
                    phi = np.array([0.0, 1.0], dtype=np.float64)

                r_var = self._meas_noise**2
                s_val = float(phi @ p_pred @ phi + r_var)
                k_vec = (p_pred @ phi) / s_val
                self._theta[i] = self._theta[i] + k_vec * resid
                self._theta[i, 0] = float(np.clip(self._theta[i, 0], 0.0, 1.25))
                self._theta[i, 1] = float(np.clip(self._theta[i, 1], -self.tau_lim, self.tau_lim))
                ikh = np.eye(2, dtype=np.float64) - np.outer(k_vec, phi)
                self._p[i] = ikh @ p_pred @ ikh.T + np.outer(k_vec, k_vec) * r_var
                self._p[i] = 0.5 * (self._p[i] + self._p[i].T)

        if any_rw_valid:
            self._prev_rw_speed = rw_speeds.copy()
            self._prev_time_s = t

        stale = (t - self._last_valid_t) > self.cfg.stale_timeout_s
        wheels: list[WheelCapability] = []
        for i in range(self.n_rw):
            g_hat = float(self._theta[i, 0])
            b_hat = float(self._theta[i, 1])
            g_std = float(np.sqrt(max(0.0, self._p[i, 0, 0])))
            b_std = float(np.sqrt(max(0.0, self._p[i, 1, 1])))
            g_min = float(np.clip(g_hat - self.cfg.conservative_k_sigma * g_std, 0.0, 1.0))
            g_max = float(np.clip(g_hat + self.cfg.conservative_k_sigma * g_std, g_min, 1.25))
            h_i = self.rotor_j * float(rw_speeds[i]) if rw_valid[i] else 0.0
            pos_cap, neg_cap, h_sat = _momentum_headroom(
                h_i,
                self.h_lim,
                self.tau_lim * g_hat,
                self._guard_margin,
            )
            # Confidence decreases monotonically with gain std and normalized residual
            resid_norm = self._residual_ema[i] / max(self.tau_lim, 1e-6)
            conf_i = float(
                np.exp(-g_std / 0.20) * np.exp(-max(0.0, resid_norm - 0.07) / 0.25)
            )
            if self._unexcited_time_s[i] > 10.0 and g_hat > 0.5:
                conf_i = min(conf_i, 0.85)
            if not rw_valid[i] or stale:
                conf_i = 0.0
            wheels.append(
                WheelCapability(
                    axis_body=self.a_rw[:, i].copy(),
                    effectiveness_nom=g_hat,
                    effectiveness_min=g_min,
                    effectiveness_max=g_max,
                    bias_est_nm=b_hat,
                    bias_bound_nm=min(self.tau_lim, self.cfg.conservative_k_sigma * b_std),
                    torque_limit_nm=self.tau_lim,
                    momentum_limit_nms=self.h_lim,
                    current_momentum_nms=h_i,
                    available_pos_torque_nm=pos_cap,
                    available_neg_torque_nm=neg_cap,
                    saturated_torque=False,
                    saturated_momentum=h_sat,
                    confidence=float(np.clip(conf_i, 0.0, 1.0)),
                    valid=bool(rw_valid[i] and not stale),
                )
            )

        b_valid = measurement.mag_valid and bool(np.all(np.isfinite(b_field_body_t)))
        b_use = b_field_body_t if b_valid else np.zeros(3, dtype=np.float64)
        mtqs: list[MTQCapability] = []
        for j in range(self.n_mtq):
            axis_j = self.a_mtq[:, j].copy()
            tau_vec = np.cross(axis_j, b_use) * self.m_lim
            mtqs.append(
                MTQCapability(
                    axis_body=axis_j,
                    effectiveness_nom=1.0,
                    effectiveness_min=0.85 if b_valid else 0.0,
                    effectiveness_max=1.0,
                    dipole_limit_am2=self.m_lim,
                    instantaneous_torque_vector_nm=tau_vec,
                    confidence=0.9 if b_valid else 0.0,
                    valid=b_valid,
                )
            )

        return _assemble_capability_state(
            time_s=t,
            wheels=tuple(wheels),
            mtqs=tuple(mtqs),
            is_oracle=False,
            stale=stale,
            valid=bool(any_rw_valid and not stale),
            diagnostics={
                "source": "online_rls_tachometer",
                "g_hat": self._theta[:, 0].copy(),
                "g_std": np.sqrt(np.maximum(self._p[:, 0, 0], 0.0)),
                "bias_hat_nm": self._theta[:, 1].copy(),
                "residual_ema_nm": self._residual_ema.copy(),
                "unverified_unexcited": tuple(
                    bool(self._unexcited_time_s[i] > 10.0) for i in range(self.n_rw)
                ),
            },
        )
