"""Quaternion and SO(3) rotation utilities.

Frozen mathematical convention:
- Scalar-first Hamilton quaternion: q = [q0, q1, q2, q3] = [w, x, y, z].
- q_ib maps vectors from Body (B) to Inertial (I): v_I = R_IB(q_ib) @ v_B.
- Composition: R(p (*) q) = R(p) @ R(q).
- Kinematics: dq_ib/dt = 0.5 * q_ib (*) [0, omega_B], where omega_B is Body wrt Inertial in B.
- Attitude error: q_rb = canonicalize(conj(q_ir) (*) q_ib) maps Body (B) to Reference (R).
"""

from __future__ import annotations

import numpy as np

from adcs.interfaces.types import FloatArray


def skew(v: FloatArray) -> FloatArray:
    """Return 3x3 skew-symmetric matrix [v]_x such that [v]_x @ u == cross(v, u)."""
    x, y, z = float(v[0]), float(v[1]), float(v[2])
    return np.array(
        [
            [0.0, -z, y],
            [z, 0.0, -x],
            [-y, x, 0.0],
        ],
        dtype=np.float64,
    )


def quat_normalize(q: FloatArray) -> FloatArray:
    """Return unit-norm copy of quaternion q; raises ValueError on zero or non-finite norm."""
    arr = np.asarray(q, dtype=np.float64)
    if arr.shape != (4,) or not np.all(np.isfinite(arr)):
        raise ValueError(f"Quaternion must be a finite 4-vector, got {arr!r}")
    norm = float(np.linalg.norm(arr))
    if norm <= 1e-15:
        raise ValueError("Cannot normalize near-zero quaternion")
    return arr / norm


def quat_canonicalize(q: FloatArray) -> FloatArray:
    """Normalize quaternion and enforce scalar part q0 >= 0 (shortest-path hemisphere)."""
    qn = quat_normalize(q)
    if qn[0] < 0.0:
        return -qn
    return qn


def quat_conjugate(q: FloatArray) -> FloatArray:
    """Hamilton conjugate q* = [q0, -q1, -q2, -q3] (inverse for unit quaternions)."""
    arr = np.asarray(q, dtype=np.float64)
    return np.array([arr[0], -arr[1], -arr[2], -arr[3]], dtype=np.float64)


def quat_multiply(p: FloatArray, q: FloatArray) -> FloatArray:
    """Hamilton quaternion product p (*) q such that R(p (*) q) = R(p) @ R(q)."""
    pw, px, py, pz = float(p[0]), float(p[1]), float(p[2]), float(p[3])
    qw, qx, qy, qz = float(q[0]), float(q[1]), float(q[2]), float(q[3])
    return np.array(
        [
            pw * qw - px * qx - py * qy - pz * qz,
            pw * qx + px * qw + py * qz - pz * qy,
            pw * qy - px * qz + py * qw + pz * qx,
            pw * qz + px * qy - py * qx + pz * qw,
        ],
        dtype=np.float64,
    )


def quat_to_dcm(q: FloatArray) -> FloatArray:
    """Convert unit quaternion q_AB to 3x3 direction cosine matrix R_AB (v_A = R_AB @ v_B)."""
    qn = quat_normalize(q)
    w, x, y, z = float(qn[0]), float(qn[1]), float(qn[2]), float(qn[3])
    return np.array(
        [
            [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - w * z), 2.0 * (x * z + w * y)],
            [2.0 * (x * y + w * z), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - w * x)],
            [2.0 * (x * z - w * y), 2.0 * (y * z + w * x), 1.0 - 2.0 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def dcm_to_quat(dcm: FloatArray) -> FloatArray:
    """Convert proper orthogonal 3x3 DCM R_AB to canonical scalar-first unit quaternion q_AB."""
    r = np.asarray(dcm, dtype=np.float64)
    if r.shape != (3, 3) or not np.all(np.isfinite(r)):
        raise ValueError(f"DCM must be a finite 3x3 matrix, got shape {r.shape}")
    tr = float(r[0, 0] + r[1, 1] + r[2, 2])
    if tr > 0.0:
        s = 2.0 * np.sqrt(tr + 1.0)
        w = 0.25 * s
        x = (r[2, 1] - r[1, 2]) / s
        y = (r[0, 2] - r[2, 0]) / s
        z = (r[1, 0] - r[0, 1]) / s
    elif r[0, 0] > r[1, 1] and r[0, 0] > r[2, 2]:
        s = 2.0 * np.sqrt(1.0 + r[0, 0] - r[1, 1] - r[2, 2])
        w = (r[2, 1] - r[1, 2]) / s
        x = 0.25 * s
        y = (r[0, 1] + r[1, 0]) / s
        z = (r[0, 2] + r[2, 0]) / s
    elif r[1, 1] > r[2, 2]:
        s = 2.0 * np.sqrt(1.0 + r[1, 1] - r[0, 0] - r[2, 2])
        w = (r[0, 2] - r[2, 0]) / s
        x = (r[0, 1] + r[1, 0]) / s
        y = 0.25 * s
        z = (r[1, 2] + r[2, 1]) / s
    else:
        s = 2.0 * np.sqrt(1.0 + r[2, 2] - r[0, 0] - r[1, 1])
        w = (r[1, 0] - r[0, 1]) / s
        x = (r[0, 2] + r[2, 0]) / s
        y = (r[1, 2] + r[2, 1]) / s
        z = 0.25 * s
    return quat_canonicalize(np.array([w, x, y, z], dtype=np.float64))


def quat_from_axis_angle(axis: FloatArray, angle_rad: float) -> FloatArray:
    """Create unit quaternion for rotation by `angle_rad` about unit `axis`."""
    ax = np.asarray(axis, dtype=np.float64)
    norm = float(np.linalg.norm(ax))
    if norm <= 1e-15:
        if abs(angle_rad) <= 1e-15:
            return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
        raise ValueError("Rotation axis cannot be zero for non-zero angle")
    u = ax / norm
    half = 0.5 * float(angle_rad)
    return quat_normalize(np.array([np.cos(half), *(np.sin(half) * u)], dtype=np.float64))


def quat_from_rotvec(rotvec: FloatArray) -> FloatArray:
    """Exponential map so(3) -> Unit Quaternion: exp(0.5 * rotvec)."""
    rv = np.asarray(rotvec, dtype=np.float64)
    angle = float(np.linalg.norm(rv))
    if angle < 1e-8:
        half = 0.5 * rv
        return quat_normalize(np.array([1.0, half[0], half[1], half[2]], dtype=np.float64))
    return quat_from_axis_angle(rv / angle, angle)


def quat_rotate_vec(q_ab: FloatArray, v_b: FloatArray) -> FloatArray:
    """Map vector v_b from frame B to frame A using q_AB: v_A = R_AB @ v_B."""
    return quat_to_dcm(q_ab) @ np.asarray(v_b, dtype=np.float64)


def quat_rotate_vec_inv(q_ab: FloatArray, v_a: FloatArray) -> FloatArray:
    """Map vector v_a from frame A to frame B using q_AB: v_B = R_AB^T @ v_A."""
    return quat_to_dcm(q_ab).T @ np.asarray(v_a, dtype=np.float64)


def quat_derivative(q_ib: FloatArray, omega_body_rad_s: FloatArray) -> FloatArray:
    """Quaternion kinematics dq_ib/dt = 0.5 * q_ib (*) [0, omega_B]."""
    omega_q = np.array(
        [0.0, float(omega_body_rad_s[0]), float(omega_body_rad_s[1]), float(omega_body_rad_s[2])],
        dtype=np.float64,
    )
    return 0.5 * quat_multiply(q_ib, omega_q)


def quat_error(q_ir: FloatArray, q_ib: FloatArray) -> FloatArray:
    """Attitude error quaternion q_RB = canonicalize(conj(q_IR) (*) q_IB).

    Maps body frame B to reference frame R. Equals [1, 0, 0, 0] when aligned.
    """
    return quat_canonicalize(quat_multiply(quat_conjugate(q_ir), q_ib))


def quat_geodesic_angle(q_err: FloatArray) -> float:
    """Geodesic rotation angle in [0, pi] rad represented by error quaternion q_err."""
    qn = quat_normalize(q_err)
    return float(2.0 * np.arccos(np.clip(abs(float(qn[0])), 0.0, 1.0)))


def quat_error_rotvec(q_err: FloatArray) -> FloatArray:
    """Exact rotation vector theta * e_hat (rad) of error quaternion q_err (q0 >= 0)."""
    qc = quat_canonicalize(q_err)
    qv = qc[1:]
    v_norm = float(np.linalg.norm(qv))
    if v_norm < 1e-10:
        return 2.0 * qv
    angle = 2.0 * float(np.arctan2(v_norm, float(qc[0])))
    return (angle / v_norm) * qv
