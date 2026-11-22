"""Matched-scenario backend comparison harness (Gate C6: Fast vs. Basilisk)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from adcs.interfaces.protocols import SimulatorBackend
from adcs.interfaces.types import FloatArray
from adcs.utils.quaternion import quat_error, quat_geodesic_angle


@dataclass(frozen=True)
class BackendComparisonMetrics:
    """Discrepancy metrics between two simulator backends on a matched trajectory."""

    backend_a: str
    backend_b: str
    n_steps: int
    max_attitude_diff_rad: float
    rms_attitude_diff_rad: float
    max_omega_diff_rad_s: float
    max_wheel_momentum_diff_nms: float
    max_position_diff_m: float
    max_b_field_diff_t: float


def compare_backends(
    backend_a: SimulatorBackend,
    backend_b: SimulatorBackend,
    *,
    rw_commands: list[FloatArray],
    mtq_commands: list[FloatArray],
    q_ib_init: FloatArray | None = None,
    omega_body_init: FloatArray | None = None,
    wheel_momentum_init: FloatArray | None = None,
    dt_s: float | None = None,
) -> BackendComparisonMetrics:
    """Run two backends from identical initial states & commands and measure discrepancies."""
    if len(rw_commands) != len(mtq_commands) or len(rw_commands) == 0:
        raise ValueError("rw_commands and mtq_commands must be non-empty lists of equal length")

    backend_a.reset(
        q_ib_init=q_ib_init,
        omega_body_init=omega_body_init,
        wheel_momentum_init=wheel_momentum_init,
    )
    backend_b.reset(
        q_ib_init=q_ib_init,
        omega_body_init=omega_body_init,
        wheel_momentum_init=wheel_momentum_init,
    )

    att_diffs: list[float] = []
    w_diffs: list[float] = []
    h_diffs: list[float] = []
    r_diffs: list[float] = []
    b_diffs: list[float] = []

    for rw_u, mtq_u in zip(rw_commands, mtq_commands, strict=True):
        st_a = backend_a.step(rw_u, mtq_u, dt_s=dt_s).truth
        st_b = backend_b.step(rw_u, mtq_u, dt_s=dt_s).truth
        att_diffs.append(quat_geodesic_angle(quat_error(st_a.q_ib, st_b.q_ib)))
        w_diffs.append(float(np.linalg.norm(st_a.omega_body_rad_s - st_b.omega_body_rad_s)))
        h_diffs.append(float(np.linalg.norm(st_a.wheel_momentum_nms - st_b.wheel_momentum_nms)))
        r_diffs.append(float(np.linalg.norm(st_a.position_eci_m - st_b.position_eci_m)))
        b_diffs.append(float(np.linalg.norm(st_a.b_field_body_t - st_b.b_field_body_t)))

    att_arr = np.asarray(att_diffs, dtype=np.float64)
    return BackendComparisonMetrics(
        backend_a=backend_a.backend_name,
        backend_b=backend_b.backend_name,
        n_steps=len(rw_commands),
        max_attitude_diff_rad=float(np.max(att_arr)),
        rms_attitude_diff_rad=float(np.sqrt(np.mean(att_arr**2))),
        max_omega_diff_rad_s=float(np.max(w_diffs)),
        max_wheel_momentum_diff_nms=float(np.max(h_diffs)),
        max_position_diff_m=float(np.max(r_diffs)),
        max_b_field_diff_t=float(np.max(b_diffs)),
    )
