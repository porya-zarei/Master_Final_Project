"""Core typed data structures shared across simulators, estimators, controllers, and logs.

Conventions (frozen across all modules):
- Units: SI everywhere (m, s, kg, rad, rad/s, N*m, N*m*s, A*m^2, T).
- Quaternions: scalar-first [q0, q1, q2, q3], Hamilton convention.
  `q_ib` maps vectors from Body (B) to Inertial (I): v_I = R_IB(q_ib) @ v_B.
  `q_ir` maps vectors from Reference/LVLH (R) to Inertial (I): v_I = R_IR(q_ir) @ v_R.
  Attitude error `q_rb = conj(q_ir) (*) q_ib` (canonicalized with q0 >= 0) maps B to R.
- Angular velocity `omega_body_rad_s`: Body relative to Inertial, expressed in Body frame B.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def _check_vector(arr: FloatArray, expected_len: int, name: str) -> None:
    if arr.shape != (expected_len,):
        raise ValueError(f"{name} must have shape ({expected_len},), got {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains non-finite values: {arr}")


class SupervisorMode(StrEnum):
    """Supervisory operating modes defined in CONTROL_ARCHITECTURE.md §12."""

    M0_NOMINAL = "M0_NOMINAL"
    M1_SUSPECTED_DEGRADATION = "M1_SUSPECTED_DEGRADATION"
    M2_CONFIRMED_DEGRADATION = "M2_CONFIRMED_DEGRADATION"
    M3_UNKNOWN_INVALID_UNSAFE = "M3_UNKNOWN_INVALID_UNSAFE"
    M4_RECOVERY = "M4_RECOVERY"


@dataclass(frozen=True)
class ActuatorStatus:
    """Instantaneous actuator saturation and fault-free physical status flags."""

    rw_torque_saturated: tuple[bool, ...]
    rw_momentum_saturated: tuple[bool, ...]
    mtq_dipole_saturated: tuple[bool, ...]
    rw_locked: tuple[bool, ...] = ()
    notes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SpacecraftTruthState:
    """Ground-truth plant state. Never fed directly to deployed controller policies."""

    time_s: float
    position_eci_m: FloatArray
    velocity_eci_m_s: FloatArray
    q_ib: FloatArray
    omega_body_rad_s: FloatArray
    wheel_momentum_nms: FloatArray
    wheel_speed_rad_s: FloatArray
    rw_torque_achieved_nm: FloatArray
    mtq_dipole_achieved_am2: FloatArray
    mtq_torque_achieved_nm: FloatArray
    b_field_body_t: FloatArray
    disturbance_torque_body_nm: FloatArray
    actuator_status: ActuatorStatus

    def validate(self) -> None:
        if not np.isfinite(self.time_s):
            raise ValueError(f"time_s must be finite, got {self.time_s}")
        _check_vector(self.position_eci_m, 3, "position_eci_m")
        _check_vector(self.velocity_eci_m_s, 3, "velocity_eci_m_s")
        _check_vector(self.q_ib, 4, "q_ib")
        _check_vector(self.omega_body_rad_s, 3, "omega_body_rad_s")
        _check_vector(self.mtq_torque_achieved_nm, 3, "mtq_torque_achieved_nm")
        _check_vector(self.b_field_body_t, 3, "b_field_body_t")
        _check_vector(self.disturbance_torque_body_nm, 3, "disturbance_torque_body_nm")
        if not np.all(np.isfinite(self.wheel_momentum_nms)):
            raise ValueError("wheel_momentum_nms contains non-finite values")
        if not np.all(np.isfinite(self.wheel_speed_rad_s)):
            raise ValueError("wheel_speed_rad_s contains non-finite values")


@dataclass(frozen=True)
class ReferenceState:
    """Mission reference attitude and angular rate in inertial / body-referenced conventions."""

    time_s: float
    q_ir: FloatArray  # LVLH/Reference -> Inertial, scalar-first
    omega_ref_inertial_in_ref_rad_s: FloatArray  # Reference frame angular velocity expressed in R
    valid: bool = True


@dataclass(frozen=True)
class SensorMeasurement:
    """Raw onboard sensor measurements at a control step."""

    time_s: float
    gyro_rad_s: FloatArray
    gyro_valid: bool
    star_tracker_q_ib: FloatArray
    star_tracker_valid: bool
    star_tracker_age_s: float
    mag_body_t: FloatArray
    mag_valid: bool
    rw_speed_rad_s: FloatArray
    rw_speed_valid: tuple[bool, ...]


@dataclass(frozen=True)
class EstimatorOutput:
    """Typed output of B1 state estimator (CONTROL_ARCHITECTURE.md §5)."""

    time_s: float
    q_ib_est: FloatArray
    omega_body_est_rad_s: FloatArray
    gyro_bias_est_rad_s: FloatArray
    attitude_cov_rad2: FloatArray  # 3x3 attitude error covariance
    rate_cov_rad2_s2: FloatArray  # 3x3 rate error covariance
    attitude_std_rad: FloatArray  # 3-vector sqrt(diag(P_att))
    rate_std_rad_s: FloatArray  # 3-vector sqrt(diag(P_rate))
    gamma_obs: float  # Observability confidence in [0, 1]
    sensor_status: dict[str, bool]
    data_age_s: float
    valid: bool
    innovation_norm: float = 0.0
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WheelCapability:
    """Per-reaction-wheel capability representation (CONTROL_ARCHITECTURE.md §7.1)."""

    axis_body: FloatArray
    effectiveness_nom: float
    effectiveness_min: float
    effectiveness_max: float
    bias_est_nm: float
    bias_bound_nm: float
    torque_limit_nm: float
    momentum_limit_nms: float
    current_momentum_nms: float
    available_pos_torque_nm: float
    available_neg_torque_nm: float
    saturated_torque: bool
    saturated_momentum: bool
    confidence: float
    valid: bool


@dataclass(frozen=True)
class MTQCapability:
    """Per-magnetorquer capability representation (CONTROL_ARCHITECTURE.md §7.2)."""

    axis_body: FloatArray
    effectiveness_nom: float
    effectiveness_min: float
    effectiveness_max: float
    dipole_limit_am2: float
    instantaneous_torque_vector_nm: FloatArray  # (axis x B) * m_max * g_min
    confidence: float
    valid: bool


@dataclass(frozen=True)
class ActuatorCapabilityState:
    """Aggregated B3 actuator capability and AMS directional margins."""

    time_s: float
    wheels: tuple[WheelCapability, ...]
    mtqs: tuple[MTQCapability, ...]
    nominal_support_xyz: FloatArray  # h_nom(e_x), h_nom(e_y), h_nom(e_z)
    conservative_support_xyz: FloatArray  # h_cons(e_x), h_cons(e_y), h_cons(e_z)
    directional_margin_xyz: FloatArray  # h_cons / h_nom in [0, 1]
    effective_rank: int
    confidence: float  # in [0, 1]
    is_oracle: bool
    stale: bool
    valid: bool
    horizon_note: str = "instantaneous_rw_box_plus_momentum_guard"
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActuatorCommand:
    """Commands dispatched to plant actuators plus upstream torque audit trail."""

    rw_torque_cmd_nm: FloatArray
    mtq_dipole_cmd_am2: FloatArray
    tau_request_nm: FloatArray
    tau_allocated_nm: FloatArray


@dataclass(frozen=True)
class GateDecision:
    """Full audit record of B7 deterministic authority gate."""

    rho: float
    alpha: float
    directional_gain_xyz: FloatArray
    tau_rl_raw_nm: FloatArray
    tau_rl_gated_nm: FloatArray
    rl_enabled: bool
    rejected_reason: str | None
    mode: SupervisorMode
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ControlStepOutput:
    """Complete typed output of one controller cycle."""

    command: ActuatorCommand
    tau_base_nm: FloatArray
    gate_decision: GateDecision
    mode: SupervisorMode
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlantStepOutput:
    """Output returned by a simulator backend step."""

    truth: SpacecraftTruthState
    info: dict[str, Any] = field(default_factory=dict)
