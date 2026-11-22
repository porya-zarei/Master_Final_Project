"""LVLH nadir-pointing reference generator and attitude/rate error conventions."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from adcs.dynamics.orbit import compute_lvlh_reference
from adcs.interfaces.types import FloatArray, ReferenceState
from adcs.utils.quaternion import (
    quat_error,
    quat_error_rotvec,
    quat_geodesic_angle,
    quat_rotate_vec_inv,
)


@dataclass(frozen=True)
class AttitudeError:
    """Attitude and angular-rate tracking errors expressed in body frame B."""

    q_rb: FloatArray  # Error quaternion B -> R, canonicalized q0 >= 0
    rotvec_rad: FloatArray  # Exact geodesic rotation vector theta * e_hat (rad)
    geodesic_angle_rad: float  # Scalar geodesic pointing error in [0, pi] rad
    omega_ref_body_rad_s: FloatArray  # Reference frame angular velocity expressed in B
    omega_err_body_rad_s: FloatArray  # omega_body - omega_ref_body (rad/s)


def compute_attitude_error(
    q_ib: FloatArray,
    omega_body_rad_s: FloatArray,
    reference: ReferenceState,
) -> AttitudeError:
    """Compute canonical attitude and angular-rate error for controller feedback.

    With q_rb = conj(q_ir) (*) q_ib (B -> R), the reference frame rate expressed in B is
    omega_ref_B = R_RB^T @ omega_ref_R, so d(R_RB)/dt = R_RB @ [omega_B - omega_ref_B]_x.
    """
    q_rb = quat_error(reference.q_ir, q_ib)
    rotvec = quat_error_rotvec(q_rb)
    angle = quat_geodesic_angle(q_rb)
    omega_ref_b = quat_rotate_vec_inv(q_rb, reference.omega_ref_inertial_in_ref_rad_s)
    omega_err_b = np.asarray(omega_body_rad_s, dtype=np.float64) - omega_ref_b
    return AttitudeError(
        q_rb=q_rb,
        rotvec_rad=rotvec,
        geodesic_angle_rad=angle,
        omega_ref_body_rad_s=omega_ref_b,
        omega_err_body_rad_s=omega_err_b,
    )


class NadirReferenceGenerator:
    """Stateful nadir-pointing LVLH reference generator with degeneracy persistence."""

    def __init__(self) -> None:
        self._prev_x_eci: FloatArray | None = None

    def reset(self) -> None:
        self._prev_x_eci = None

    def compute(
        self,
        time_s: float,
        position_eci_m: FloatArray,
        velocity_eci_m_s: FloatArray,
    ) -> ReferenceState:
        ref, x_hat = compute_lvlh_reference(
            time_s, position_eci_m, velocity_eci_m_s, prev_x_eci=self._prev_x_eci
        )
        self._prev_x_eci = x_hat
        return ref
