"""Geometry-aware and capability-aware RW + MTQ actuator allocator.

Enforces hardware torque limits, momentum-wall headroom, and field-dependent MTQ constraints
(tau_MTQ = m x B) in a single coherent constraint path (CONTROL_ARCHITECTURE.md §13).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from adcs.interfaces.types import ActuatorCapabilityState, FloatArray
from adcs.utils.config import SpacecraftConfig


@dataclass(frozen=True)
class AllocationConfig:
    """Configurable actuator allocation weights and safety parameters."""

    capability_aware: bool = False
    use_conservative_effectiveness: bool = False
    compensate_bias: bool = False
    regularization: float = 1e-6
    qp_max_iters: int = 30
    mtq_assist_enabled: bool = True
    mtq_unload_gain: float = 0.002  # 1/s proportional momentum unloading gain
    mtq_min_b_norm_t: float = 1e-6  # floor to avoid singular division by ||B||^2
    momentum_guard_fraction: float = 0.96  # start tapering spin-up torque near momentum limit
    underactuated_mtq_fallback: bool = True  # decouple 2-RW + 3-MTQ when a wheel fails ~100%
    dead_wheel_eff_threshold: float = 0.08  # singular value threshold for rank-deficient RW set


def detect_underactuated_axis(
    a_rw: FloatArray,
    capability: ActuatorCapabilityState | None,
    *,
    dead_eff_threshold: float = 0.08,
) -> FloatArray | None:
    """Return unit body axis lacking RW torque authority when effective RW matrix is rank < 3.

    Cleanly separates 100%-dead wheels (g_nom < 0.08 -> decoupled hybrid 2-RW + 3-MTQ mode)
    from partially degraded wheels (e.g., 75-80% loss, g_nom ~ 0.20-0.25 -> normal 3-RW mode).
    """
    if capability is None or not capability.valid:
        return None
    n_rw = a_rw.shape[1]
    eff = np.ones(n_rw, dtype=np.float64)
    for i, wcap in enumerate(capability.wheels[:n_rw]):
        eff[i] = float(np.clip(wcap.effectiveness_nom, 0.0, 1.0)) if wcap.valid else 0.0
    b_eff = a_rw * eff[np.newaxis, :]
    u_mat, s_vals, _ = np.linalg.svd(b_eff, full_matrices=True)
    if s_vals.size < 3 or float(s_vals[2]) < dead_eff_threshold:
        d_hat = u_mat[:, 2].astype(np.float64)
        idx = int(np.argmax(np.abs(d_hat)))
        if d_hat[idx] < 0.0:
            d_hat = -d_hat
        return d_hat / max(float(np.linalg.norm(d_hat)), 1e-12)
    return None


def step_underactuated_latch(
    detected_axis: FloatArray | None,
    count: int,
    clear_count: int,
    latched_axis: FloatArray | None,
    *,
    confirm_steps: int = 5,
    clear_steps: int = 2,
) -> tuple[int, int, FloatArray | None]:
    """Update persistent underactuated-axis latch with confirmation and clear hysteresis."""
    if detected_axis is not None:
        count += 1
        clear_count = 0
        if latched_axis is not None or count >= confirm_steps:
            latched_axis = detected_axis
        return count, clear_count, latched_axis

    count = 0
    if latched_axis is not None:
        clear_count += 1
        if clear_count >= clear_steps:
            latched_axis = None
            clear_count = 0
    return count, clear_count, latched_axis


@dataclass(frozen=True)
class AllocationResult:
    """Detailed allocator output separating requested, allocated, and commanded quantities."""

    rw_torque_cmd_nm: FloatArray
    mtq_dipole_cmd_am2: FloatArray
    tau_request_nm: FloatArray
    tau_rw_allocated_nm: FloatArray
    tau_mtq_allocated_nm: FloatArray
    tau_total_allocated_nm: FloatArray
    infeasible_residual_nm: FloatArray
    rw_saturated: tuple[bool, ...]
    mtq_saturated: tuple[bool, ...]


def solve_box_lsq(
    b_mat: FloatArray,
    target: FloatArray,
    u_min: FloatArray,
    u_max: FloatArray,
    *,
    reg: float = 1e-6,
    max_iters: int = 30,
) -> FloatArray:
    """Solve min_u 0.5 * ||B u - target||^2 + 0.5 * reg * ||u||^2 s.t. u_min <= u <= u_max.

    Uses deterministic projected Gauss-Seidel coordinate descent (fast, C99-portable, exact
    for orthogonal and low-dimensional over-actuated wheel geometries, zero external solver).
    """
    n = b_mat.shape[1]
    h = b_mat.T @ b_mat + reg * np.eye(n, dtype=np.float64)
    g = b_mat.T @ target
    # Warm start from unconstrained regularized least squares clipped to box
    try:
        u = np.linalg.solve(h, g)
    except np.linalg.LinAlgError:
        u = np.zeros(n, dtype=np.float64)
    u = np.clip(u, u_min, u_max)

    diag = np.diag(h)
    for _ in range(max_iters):
        max_delta = 0.0
        for i in range(n):
            if diag[i] <= 1e-15 or u_max[i] <= u_min[i] + 1e-15:
                u[i] = float(np.clip(u[i], u_min[i], u_max[i]))
                continue
            r_i = float(g[i] - np.dot(h[i], u) + diag[i] * u[i])
            u_new = float(np.clip(r_i / diag[i], u_min[i], u_max[i]))
            max_delta = max(max_delta, abs(u_new - float(u[i])))
            u[i] = u_new
        if max_delta < 1e-11:
            break
    return u


class ActuatorAllocator:
    """Unified RW + MTQ allocator supporting arbitrary actuator geometry and capability bounds."""

    def __init__(
        self,
        sc_config: SpacecraftConfig,
        alloc_config: AllocationConfig | None = None,
    ) -> None:
        self.sc_cfg = sc_config
        self.cfg = AllocationConfig() if alloc_config is None else alloc_config
        self.a_rw = sc_config.reaction_wheels.axis_matrix_body.copy()
        self.a_mtq = sc_config.magnetorquers.axis_matrix_body.copy()
        self.n_rw = sc_config.reaction_wheels.count
        self.n_mtq = sc_config.magnetorquers.count
        self.rw_tau_lim = sc_config.reaction_wheels.torque_limit_nominal_nm
        self.rw_h_lim = sc_config.reaction_wheels.effective_momentum_limit_nms
        self.mtq_limits = sc_config.magnetorquers.dipole_command_limits_am2.copy()

    def _rw_box_and_matrix(
        self,
        wheel_momentum_nms: FloatArray,
        capability: ActuatorCapabilityState | None,
    ) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
        eff = np.ones(self.n_rw, dtype=np.float64)
        bias_body = np.zeros(3, dtype=np.float64)
        u_min = np.full(self.n_rw, -self.rw_tau_lim, dtype=np.float64)
        u_max = np.full(self.n_rw, self.rw_tau_lim, dtype=np.float64)

        if self.cfg.capability_aware and capability is not None and capability.valid:
            for i, wcap in enumerate(capability.wheels):
                if not wcap.valid:
                    eff[i] = 0.0
                    u_min[i] = 0.0
                    u_max[i] = 0.0
                    continue
                g_i = (
                    wcap.effectiveness_min
                    if self.cfg.use_conservative_effectiveness
                    else wcap.effectiveness_nom
                )
                eff[i] = float(np.clip(g_i, 0.0, 1.5))
                if eff[i] < 1e-3:
                    u_min[i] = 0.0
                    u_max[i] = 0.0
                else:
                    # Available wheel torque commands respect physical torque & momentum headroom
                    u_max[i] = min(self.rw_tau_lim, max(0.0, wcap.available_pos_torque_nm / eff[i]))
                    u_min[i] = max(
                        -self.rw_tau_lim, -max(0.0, wcap.available_neg_torque_nm / eff[i])
                    )
                if self.cfg.compensate_bias:
                    bias_body = bias_body + wcap.axis_body * wcap.bias_est_nm
        else:
            # Nominal momentum-wall tapering to prevent useless saturation push
            guard_h = self.cfg.momentum_guard_fraction * self.rw_h_lim
            for i in range(self.n_rw):
                h_i = float(wheel_momentum_nms[i])
                if h_i > guard_h:
                    frac = max(0.0, (self.rw_h_lim - h_i) / max(1e-9, self.rw_h_lim - guard_h))
                    # Negative body torque increases h_i further (dh/dt = -tau_body)
                    u_min[i] = -self.rw_tau_lim * frac
                elif h_i < -guard_h:
                    frac = max(0.0, (self.rw_h_lim + h_i) / max(1e-9, self.rw_h_lim - guard_h))
                    u_max[i] = self.rw_tau_lim * frac

        b_eff = self.a_rw * eff[np.newaxis, :]
        return b_eff, u_min, u_max, bias_body

    def allocate(
        self,
        tau_request_nm: FloatArray,
        *,
        wheel_momentum_nms: FloatArray,
        b_field_body_t: FloatArray,
        capability: ActuatorCapabilityState | None = None,
        dead_axis_override: FloatArray | None = None,
        use_underactuated: bool | None = None,
    ) -> AllocationResult:
        """Allocate requested body torque across RWs and field-constrained MTQs."""
        tau_req = np.asarray(tau_request_nm, dtype=np.float64)
        if tau_req.shape != (3,) or not np.all(np.isfinite(tau_req)):
            raise ValueError(f"tau_request_nm must be a finite 3-vector, got {tau_req!r}")
        h_w = np.asarray(wheel_momentum_nms, dtype=np.float64)
        b_body = np.asarray(b_field_body_t, dtype=np.float64)

        b_eff, u_min, u_max, bias_body = self._rw_box_and_matrix(h_w, capability)
        b_norm2 = float(np.dot(b_body, b_body))
        allow_fallback = self.cfg.capability_aware and self.cfg.underactuated_mtq_fallback
        if use_underactuated is False or not allow_fallback:
            dead_axis: FloatArray | None = None
        elif dead_axis_override is not None:
            dead_axis = np.asarray(dead_axis_override, dtype=np.float64)
        else:
            dead_axis = detect_underactuated_axis(
                self.a_rw,
                capability,
                dead_eff_threshold=self.cfg.dead_wheel_eff_threshold,
            )

        # Decoupled Hybrid 2-RW + 3-MTQ Mode when a wheel axis has lost ~100% authority:
        # 1) Dedicate 3-MTQ dipole to maximize torque along `dead_axis`: (m x B) . d = m . (B x d)
        # 2) Feedforward-cancel the resulting MTQ cross-coupling torque using the healthy RWs!
        if (
            dead_axis is not None
            and self.cfg.mtq_assist_enabled
            and b_norm2 > self.cfg.mtq_min_b_norm_t**2
            and np.all(np.isfinite(b_body))
        ):
            g_d = np.cross(b_body, dead_axis)
            g_norm2 = float(np.dot(g_d, g_d))
            # Do NOT subtract estimated RW bias along the dead axis (collinear RLS bias
            # on an unexcited dead wheel would invert the tiny magnetic torque command!).
            tau_d_req = float(np.dot(tau_req, dead_axis))
            m_body_des = np.zeros(3, dtype=np.float64)
            if g_norm2 > 1e-14:
                m_body_des = (tau_d_req / g_norm2) * g_d

            # Gentle unloading of healthy wheels orthogonal to g_d (nullspace of dead axis)
            # so stored momentum in healthy wheels (e.g. RW3) does not create persistent gyroscopic
            # cross-torque along the dead axis during orbit rotation.
            if self.cfg.mtq_unload_gain > 0.0:
                h_body = self.a_rw @ h_w
                h_healthy = h_body - float(np.dot(h_body, dead_axis)) * dead_axis
                m_unload = (2.0 * self.cfg.mtq_unload_gain) * np.cross(h_healthy, b_body) / b_norm2
                if g_norm2 > 1e-14:
                    g_hat = g_d / math.sqrt(g_norm2)
                    m_unload = m_unload - float(np.dot(m_unload, g_hat)) * g_hat
                m_body_des = m_body_des + m_unload

            mtq_eff = np.ones(self.n_mtq, dtype=np.float64)
            if capability is not None and capability.valid:
                for i, mcap in enumerate(capability.mtqs):
                    mtq_eff[i] = mcap.effectiveness_nom if mcap.valid else 0.0
            a_mtq_eff = self.a_mtq * mtq_eff[np.newaxis, :]
            # Direct projection onto MTQ axes with hard box saturation for max dead-axis authority
            m_pinv = np.linalg.pinv(a_mtq_eff) @ m_body_des
            m_cmd = np.clip(m_pinv, self.mtq_limits[:, 0], self.mtq_limits[:, 1])
            tau_mtq_alloc = np.cross(self.a_mtq @ m_cmd, b_body)

            # Healthy RWs cancel MTQ cross-coupling torque on all healthy axes!
            rw_target = tau_req - bias_body - tau_mtq_alloc
            u_rw = solve_box_lsq(
                b_eff,
                rw_target,
                u_min,
                u_max,
                reg=self.cfg.regularization,
                max_iters=self.cfg.qp_max_iters,
            )
            tau_rw_alloc = b_eff @ u_rw + bias_body
            rw_sat = tuple(
                bool(
                    abs(float(u_rw[i])) >= self.rw_tau_lim - 1e-9
                    or float(u_rw[i]) <= float(u_min[i]) + 1e-9
                    or float(u_rw[i]) >= float(u_max[i]) - 1e-9
                )
                and abs(float(tau_req[0]) + float(tau_req[1]) + float(tau_req[2])) > 1e-12
                for i in range(self.n_rw)
            )
            mtq_sat = tuple(
                bool(
                    float(m_cmd[i]) <= float(self.mtq_limits[i, 0]) + 1e-9
                    or float(m_cmd[i]) >= float(self.mtq_limits[i, 1]) - 1e-9
                )
                for i in range(self.n_mtq)
            )
            tau_total = tau_rw_alloc + tau_mtq_alloc
            return AllocationResult(
                rw_torque_cmd_nm=u_rw,
                mtq_dipole_cmd_am2=m_cmd,
                tau_request_nm=tau_req.copy(),
                tau_rw_allocated_nm=tau_rw_alloc,
                tau_mtq_allocated_nm=tau_mtq_alloc,
                tau_total_allocated_nm=tau_total,
                infeasible_residual_nm=tau_req - tau_total,
                rw_saturated=rw_sat,
                mtq_saturated=mtq_sat,
            )

        rw_target = tau_req - bias_body
        u_rw = solve_box_lsq(
            b_eff,
            rw_target,
            u_min,
            u_max,
            reg=self.cfg.regularization,
            max_iters=self.cfg.qp_max_iters,
        )
        tau_rw_alloc = b_eff @ u_rw + bias_body
        rw_sat = tuple(
            bool(
                abs(float(u_rw[i])) >= self.rw_tau_lim - 1e-9
                or float(u_rw[i]) <= float(u_min[i]) + 1e-9
                or float(u_rw[i]) >= float(u_max[i]) - 1e-9
            )
            and abs(float(tau_req[0]) + float(tau_req[1]) + float(tau_req[2])) > 1e-12
            for i in range(self.n_rw)
        )

        # MTQ allocation: instantaneous deficit assist (priority) + momentum unloading
        m_cmd = np.zeros(self.n_mtq, dtype=np.float64)
        if b_norm2 > self.cfg.mtq_min_b_norm_t**2 and np.all(np.isfinite(b_body)):
            m_body_des = np.zeros(3, dtype=np.float64)
            tau_deficit = tau_req - tau_rw_alloc
            if self.cfg.mtq_assist_enabled and float(np.linalg.norm(tau_deficit)) > 1e-7:
                # (B x tau_def) x B / ||B||^2 == tau_def_perp_B
                m_body_des = m_body_des + np.cross(b_body, tau_deficit) / b_norm2

            if self.cfg.mtq_unload_gain > 0.0:
                h_body = self.a_rw @ h_w
                # (H_w x B) x B / ||B||^2 == -H_w_perp_B -> unloads wheel momentum
                m_unload = self.cfg.mtq_unload_gain * np.cross(h_body, b_body) / b_norm2
                m_body_des = m_body_des + m_unload

            # Map desired body dipole onto MTQ axes via box-constrained LSQ
            mtq_eff = np.ones(self.n_mtq, dtype=np.float64)
            if self.cfg.capability_aware and capability is not None and capability.valid:
                for i, mcap in enumerate(capability.mtqs):
                    mtq_eff[i] = mcap.effectiveness_nom if mcap.valid else 0.0
            a_mtq_eff = self.a_mtq * mtq_eff[np.newaxis, :]
            m_cmd = solve_box_lsq(
                a_mtq_eff,
                m_body_des,
                self.mtq_limits[:, 0],
                self.mtq_limits[:, 1],
                reg=1e-8,
                max_iters=15,
            )

        tau_mtq_alloc = np.cross(self.a_mtq @ m_cmd, b_body)
        mtq_sat = tuple(
            bool(
                float(m_cmd[i]) <= float(self.mtq_limits[i, 0]) + 1e-9
                or float(m_cmd[i]) >= float(self.mtq_limits[i, 1]) - 1e-9
            )
            for i in range(self.n_mtq)
        )
        tau_total = tau_rw_alloc + tau_mtq_alloc
        infeasible = tau_req - tau_total

        return AllocationResult(
            rw_torque_cmd_nm=u_rw,
            mtq_dipole_cmd_am2=m_cmd,
            tau_request_nm=tau_req.copy(),
            tau_rw_allocated_nm=tau_rw_alloc,
            tau_mtq_allocated_nm=tau_mtq_alloc,
            tau_total_allocated_nm=tau_total,
            infeasible_residual_nm=infeasible,
            rw_saturated=rw_sat,
            mtq_saturated=mtq_sat,
        )
