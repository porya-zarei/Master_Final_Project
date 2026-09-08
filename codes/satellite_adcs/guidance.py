"""Nadir / LVLH reference guidance (time-varying, orbit-dependent)."""
from __future__ import annotations
import numpy as np

from .quaternion import dcm_to_quat


class NadirGuidance:
    def __init__(self, mu: float, a: float):
        self.mu = float(mu)
        self.a = float(a)
        self.n = np.sqrt(self.mu / self.a**3)  # mean motion [rad/s]

    def reference(self, r_I, v_I, C_to_body=None):
        """Return (q_ref, omega_ref_body).

        q_ref: q_BN with body frame = LVLH (nadir-pointing frame).
        omega_ref_body: angular velocity of LVLH frame in body (LVLH) coords.
        """
        rn = np.linalg.norm(r_I)
        rhat = r_I / rn
        h = np.cross(r_I, v_I)
        hn = np.linalg.norm(h)
        yhat = -h / hn          # orbit normal (plan convention)
        zhat = -rhat            # nadir
        xhat = np.cross(yhat, zhat)
        xhat = xhat / np.linalg.norm(xhat)

        C_I_L = np.column_stack([xhat, yhat, zhat]).T  # inertial -> LVLH (rows = body axes)
        q_ref = dcm_to_quat(C_I_L)

        # LVLH rotates about the orbit normal (yhat) at mean motion n
        omega_ref_body = np.array([0.0, self.n, 0.0])  # in LVLH coords
        return q_ref, omega_ref_body
