"""Physical actuator models for Reaction Wheels and Magnetorquers with fault hooks."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np

from adcs.interfaces.types import FloatArray
from adcs.utils.config import MagnetorquerConfig, ReactionWheelConfig


@dataclass
class RWFaultParams:
    """Per-wheel physical fault parameters applied inside the plant actuator model."""

    effectiveness: FloatArray  # multiplicative gain in [0, 1.5], nominal 1.0
    torque_bias_nm: FloatArray  # additive body-torque bias (N*m)
    viscous_nm_per_rad_s: FloatArray  # viscous friction coefficient
    coulomb_nm: FloatArray  # Coulomb friction magnitude (N*m)
    stiction_band_nm: FloatArray  # stiction deadband at near-zero speed (N*m)
    locked: list[bool]  # wheel lock fault: h_dot = 0, achieved torque = 0
    stuck_torque_nm: list[float | None]  # stuck motor torque command (N*m) or None
    delay_steps: list[int]  # pure command delay in control steps

    @classmethod
    def nominal(cls, cfg: ReactionWheelConfig) -> RWFaultParams:
        n = cfg.count
        return cls(
            effectiveness=np.ones(n, dtype=np.float64),
            torque_bias_nm=np.zeros(n, dtype=np.float64),
            viscous_nm_per_rad_s=np.full(n, cfg.viscous_nm_per_rad_s, dtype=np.float64),
            coulomb_nm=np.full(n, cfg.coulomb_nm, dtype=np.float64),
            stiction_band_nm=np.full(n, cfg.stiction_band_nm, dtype=np.float64),
            locked=[False] * n,
            stuck_torque_nm=[None] * n,
            delay_steps=[0] * n,
        )


@dataclass
class MTQFaultParams:
    """Per-magnetorquer physical fault parameters applied inside the plant actuator model."""

    effectiveness: FloatArray  # multiplicative gain, nominal 1.0
    polarity: FloatArray  # +1.0 nominal, -1.0 polarity reversal
    dipole_bias_am2: FloatArray  # additive dipole bias (A*m^2)
    dropout: list[bool]  # complete dropout (0 output)
    delay_steps: list[int]  # command delay in control steps

    @classmethod
    def nominal(cls, cfg: MagnetorquerConfig) -> MTQFaultParams:
        m = cfg.count
        return cls(
            effectiveness=np.ones(m, dtype=np.float64),
            polarity=np.ones(m, dtype=np.float64),
            dipole_bias_am2=np.zeros(m, dtype=np.float64),
            dropout=[False] * m,
            delay_steps=[0] * m,
        )


@dataclass
class ActuatorFaultState:
    """Combined instantaneous actuator fault configuration injected into plant."""

    rw: RWFaultParams
    mtq: MTQFaultParams
    extra_disturbance_body_nm: FloatArray = field(
        default_factory=lambda: np.zeros(3, dtype=np.float64)
    )


class ReactionWheelBank:
    """Reaction wheel bank with first-order lag, momentum/torque saturation, friction, and faults.

    Sign convention (strict angular momentum conservation):
    - `tau_cmd[i]` and `tau_achieved[i]` are the reaction torque applied BY wheel i ON the
      spacecraft body along `axis_matrix_body[:, i]`.
    - Therefore `dh_i/dt = -tau_achieved[i]` and body receives `+axis_matrix_body @ tau_achieved`.
    """

    def __init__(self, cfg: ReactionWheelConfig) -> None:
        self.cfg = cfg
        self.n = cfg.count
        self.axis_matrix = cfg.axis_matrix_body.copy()
        self.rotor_inertia = cfg.rotor_inertia_kg_m2
        self.tau_limit = cfg.torque_limit_nominal_nm
        self.h_limit = cfg.effective_momentum_limit_nms
        self.time_constant = cfg.time_constant_s
        self._delay_queues: list[deque[float]] = [deque([0.0]) for _ in range(self.n)]
        self.reset()

    def reset(self) -> None:
        self._delay_queues = [deque([0.0]) for _ in range(self.n)]

    def apply_command_delay(self, cmd_nm: FloatArray, faults: RWFaultParams) -> FloatArray:
        """Apply per-wheel discrete control-step command delay and stuck-torque faults."""
        delayed = np.zeros(self.n, dtype=np.float64)
        for i in range(self.n):
            val = float(cmd_nm[i])
            if faults.stuck_torque_nm[i] is not None:
                val = float(faults.stuck_torque_nm[i])  # type: ignore[arg-type]
            d = max(0, int(faults.delay_steps[i]))
            q = self._delay_queues[i]
            q.append(val)
            while len(q) > d + 1:
                q.popleft()
            delayed[i] = q[0]
        return delayed

    def compute_motor_target(
        self,
        cmd_delayed_nm: FloatArray,
        faults: RWFaultParams,
    ) -> tuple[FloatArray, tuple[bool, ...]]:
        """Compute target electromagnetic motor torque before first-order actuator lag.

        Applies nominal command clipping, effectiveness scaling, additive motor torque bias,
        and wheel-lock zeroing, clipped to physical electromagnetic limit [-tau_limit, tau_limit].
        """
        clipped = np.clip(cmd_delayed_nm, -self.tau_limit, self.tau_limit)
        tau_sat = tuple(bool(x) for x in (np.abs(cmd_delayed_nm) > self.tau_limit + 1e-12))
        eff_tau = faults.effectiveness * clipped + faults.torque_bias_nm
        if any(faults.locked):
            lock_arr = np.asarray(faults.locked, dtype=bool)
            eff_tau = np.where(lock_arr, 0.0, eff_tau)
        tau_target = np.clip(eff_tau, -self.tau_limit, self.tau_limit)
        return tau_target, tau_sat

    def apply_bearing_friction_and_wall(
        self,
        tau_elec_state_nm: FloatArray,
        wheel_momentum_nms: FloatArray,
        faults: RWFaultParams,
    ) -> tuple[FloatArray, tuple[bool, ...]]:
        """Apply instantaneous mechanical bearing friction, stiction breakaway, and momentum wall.

        Mechanical bearing friction and stiction act directly between the rotor and housing
        (bypassing the electrical motor lag tau_c and electromagnetic torque clip).
        """
        w = wheel_momentum_nms / self.rotor_inertia
        # Friction on rotor opposes spin w; reaction on body has same sign as w
        fric = faults.viscous_nm_per_rad_s * w + faults.coulomb_nm * np.tanh(w / 0.05)
        net_tau = tau_elec_state_nm + fric
        stiction_mask = (np.abs(w) < 1e-3) & (np.abs(tau_elec_state_nm) <= faults.stiction_band_nm)
        net_tau = np.where(stiction_mask, 0.0, net_tau)
        return self.apply_momentum_wall(net_tau, wheel_momentum_nms, faults)

    def compute_effective_command(
        self,
        cmd_delayed_nm: FloatArray,
        wheel_momentum_nms: FloatArray,
        faults: RWFaultParams,
    ) -> tuple[FloatArray, tuple[bool, ...]]:
        """Backwards-compatible combined effective torque mapping."""
        tau_target, tau_sat = self.compute_motor_target(cmd_delayed_nm, faults)
        tau_net, _ = self.apply_bearing_friction_and_wall(tau_target, wheel_momentum_nms, faults)
        return tau_net, tau_sat

    def apply_momentum_wall(
        self,
        tau_state_nm: FloatArray,
        wheel_momentum_nms: FloatArray,
        faults: RWFaultParams,
    ) -> tuple[FloatArray, tuple[bool, ...]]:
        """Enforce momentum saturation wall: wheel at +/- h_limit cannot spin further out.

        Remember dh_i/dt = -tau_body_i:
        - If h_i >= +h_limit, tau_body_i < 0 blocked (would increase h_i).
        - If h_i <= -h_limit, tau_body_i > 0 blocked (would decrease h_i).
        """
        at_pos = wheel_momentum_nms >= self.h_limit - 1e-12
        at_neg = wheel_momentum_nms <= -self.h_limit + 1e-12
        blocked = (at_pos & (tau_state_nm < 0.0)) | (at_neg & (tau_state_nm > 0.0))
        if any(faults.locked):
            blocked = blocked | np.asarray(faults.locked, dtype=bool)
        achieved = np.where(blocked, 0.0, tau_state_nm)
        h_sat = tuple(bool(x) for x in (at_pos | at_neg))
        return achieved, h_sat

    def body_torque(self, achieved_wheel_torque_nm: FloatArray) -> FloatArray:
        """Net torque on spacecraft body from reaction wheels: A_rw @ tau_achieved."""
        return self.axis_matrix @ achieved_wheel_torque_nm


class MagnetorquerBank:
    """Magnetorquer bank with first-order dipole lag, saturation, and fault hooks."""

    def __init__(self, cfg: MagnetorquerConfig) -> None:
        self.cfg = cfg
        self.m = cfg.count
        self.axis_matrix = cfg.axis_matrix_body.copy()
        self.limits = cfg.dipole_command_limits_am2.copy()  # (m, 2)
        self.time_constant = cfg.time_constant_s
        self._delay_queues: list[deque[float]] = [deque([0.0]) for _ in range(self.m)]
        self.reset()

    def reset(self) -> None:
        self._delay_queues = [deque([0.0]) for _ in range(self.m)]

    def apply_command_delay(self, cmd_am2: FloatArray, faults: MTQFaultParams) -> FloatArray:
        delayed = np.zeros(self.m, dtype=np.float64)
        for i in range(self.m):
            val = float(cmd_am2[i])
            d = max(0, int(faults.delay_steps[i]))
            q = self._delay_queues[i]
            q.append(val)
            while len(q) > d + 1:
                q.popleft()
            delayed[i] = q[0]
        return delayed

    def compute_effective_dipole(
        self,
        cmd_delayed_am2: FloatArray,
        faults: MTQFaultParams,
    ) -> tuple[FloatArray, tuple[bool, ...]]:
        target = np.zeros(self.m, dtype=np.float64)
        sat = [False] * self.m
        for i in range(self.m):
            if faults.dropout[i]:
                target[i] = 0.0
                continue
            lo, hi = float(self.limits[i, 0]), float(self.limits[i, 1])
            raw = float(cmd_delayed_am2[i])
            clipped = float(np.clip(raw, lo, hi))
            if raw < lo - 1e-12 or raw > hi + 1e-12:
                sat[i] = True
            eff = (
                float(faults.effectiveness[i]) * float(faults.polarity[i]) * clipped
                + float(faults.dipole_bias_am2[i])
            )
            target[i] = float(np.clip(eff, lo, hi))
        return target, tuple(sat)

    def body_torque(
        self, achieved_dipole_am2: FloatArray, b_field_body_t: FloatArray
    ) -> FloatArray:
        """Compute MTQ body torque: (A_mtq @ m) x B_body (strictly perpendicular to B_body)."""
        m_body = self.axis_matrix @ achieved_dipole_am2
        return np.cross(m_body, b_field_body_t)
