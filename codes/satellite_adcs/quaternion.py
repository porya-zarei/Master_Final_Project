"""Quaternion utilities (Hamiltonian, scalar-first [w,x,y,z])."""
from __future__ import annotations
import numpy as np


def quat_mult(p, q):
    """Hamilton product p * q."""
    w1, x1, y1, z1 = p
    w2, x2, y2, z2 = q
    return np.array([
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ])


def quat_conj(q):
    return np.array([q[0], -q[1], -q[2], -q[3]])


def quat_inv(q):
    """Inverse of a unit quaternion."""
    return quat_conj(q)


def quat_normalize(q):
    return q / np.linalg.norm(q)


def quat_to_dcm(q):
    """Quaternion q_BN -> DCM C_BN (inertial -> body): v_B = C @ v_I."""
    q = q / np.linalg.norm(q)
    w, x, y, z = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def dcm_to_quat(C):
    """DCM -> quaternion (robust, Shepperd-style)."""
    tr = np.trace(C)
    q = np.zeros(4)
    if tr > 0:
        s = np.sqrt(tr + 1.0) * 2
        q[0] = 0.25 * s
        q[1] = (C[2, 1] - C[1, 2]) / s
        q[2] = (C[0, 2] - C[2, 0]) / s
        q[3] = (C[1, 0] - C[0, 1]) / s
    else:
        i = np.argmax([C[0, 0], C[1, 1], C[2, 2]])
        if i == 0:
            s = np.sqrt(1.0 + C[0, 0] - C[1, 1] - C[2, 2]) * 2
            q[0] = (C[2, 1] - C[1, 2]) / s
            q[1] = 0.25 * s
            q[2] = (C[0, 1] + C[1, 0]) / s
            q[3] = (C[0, 2] + C[2, 0]) / s
        elif i == 1:
            s = np.sqrt(1.0 + C[1, 1] - C[0, 0] - C[2, 2]) * 2
            q[0] = (C[0, 2] - C[2, 0]) / s
            q[1] = (C[0, 1] + C[1, 0]) / s
            q[2] = 0.25 * s
            q[3] = (C[1, 2] + C[2, 1]) / s
        else:
            s = np.sqrt(1.0 + C[2, 2] - C[0, 0] - C[1, 1]) * 2
            q[0] = (C[1, 0] - C[0, 1]) / s
            q[1] = (C[0, 2] + C[2, 0]) / s
            q[2] = (C[1, 2] + C[2, 1]) / s
            q[3] = 0.25 * s
    return quat_normalize(q)


def quat_rotate(q, v):
    """Rotate inertial vector v into body frame."""
    return quat_to_dcm(q) @ v


def quat_error(q, q_ref):
    """Error quaternion from reference frame to body: q_err = q_ref^-1 * q."""
    return quat_mult(quat_inv(q_ref), q)


def theta_vec(q_err):
    """3x1 rotation vector from error quaternion (small-angle)."""
    e0 = q_err[0]
    e = q_err[1:]
    return np.sign(e0) * 2.0 * e / np.sqrt(e0 * e0 + e @ e + 1e-12)


def random_quat(rng: np.random.Generator):
    """Uniformly random unit quaternion on SO(3) (Shoemake)."""
    u1, u2, u3 = rng.random(3)
    q = np.array([
        np.sqrt(1 - u1) * np.sin(2 * np.pi * u2),
        np.sqrt(1 - u1) * np.cos(2 * np.pi * u2),
        np.sqrt(u1) * np.sin(2 * np.pi * u3),
        np.sqrt(u1) * np.cos(2 * np.pi * u3),
    ])
    return quat_normalize(q)
