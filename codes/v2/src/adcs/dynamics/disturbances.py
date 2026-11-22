"""Spacecraft environmental disturbance torque models (body frame, SI units)."""

from __future__ import annotations

import numpy as np

from adcs.interfaces.types import FloatArray
from adcs.utils.quaternion import quat_rotate_vec_inv


def gravity_gradient_torque_body(
    position_eci_m: FloatArray,
    q_ib: FloatArray,
    inertia_body_kg_m2: FloatArray,
    mu_m3_s2: float,
) -> FloatArray:
    """Compute gravity-gradient disturbance torque in body frame (N*m).

    Formula (spacecraft_config.yaml §disturbances.gravity_gradient):
        tau_gg_body = (3 * mu / r^3) * (r_hat_body x (J @ r_hat_body))
    """
    r_eci = np.asarray(position_eci_m, dtype=np.float64)
    r_mag = float(np.linalg.norm(r_eci))
    if r_mag <= 1e-6:
        raise ValueError(f"Invalid spacecraft orbital radius: {r_mag}")
    r_hat_eci = r_eci / r_mag
    r_hat_body = quat_rotate_vec_inv(q_ib, r_hat_eci)
    j_r = inertia_body_kg_m2 @ r_hat_body
    coeff = 3.0 * float(mu_m3_s2) / (r_mag**3)
    return coeff * np.cross(r_hat_body, j_r)


def residual_magnetic_dipole_torque_body(
    residual_dipole_body_am2: FloatArray,
    b_field_body_t: FloatArray,
) -> FloatArray:
    """Compute residual magnetic dipole disturbance torque: m_res x B_body (N*m)."""
    return np.cross(
        np.asarray(residual_dipole_body_am2, dtype=np.float64),
        np.asarray(b_field_body_t, dtype=np.float64),
    )
