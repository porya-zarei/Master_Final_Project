"""Shared episode metric definitions used identically across all controller arms (A0–A8).

Freezes primary outcomes, secondary outcomes, and success/loss-of-control criteria
per RESEARCH_PROTOCOL.md §3 and §9.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

METRIC_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class SuccessCriteria:
    """Frozen episode success & loss-of-control thresholds (RESEARCH_PROTOCOL.md §9)."""

    theta_success_deg: float = 2.0  # Pointing envelope threshold (deg)
    omega_success_rad_s: float = 0.015  # Rate error envelope threshold (rad/s)
    sustained_duration_s: float = 5.0  # Must stay inside envelope for T_success
    recovery_deadline_s: float = 80.0  # Max allowed recovery time after fault onset
    eval_window_start_s: float = 40.0  # Post-transient steady/recovery window start
    loc_steady_rms_deg: float = 8.0  # Loss-of-control steady RMS threshold
    loc_peak_post_recovery_deg: float = 25.0  # Severe divergence threshold


@dataclass(frozen=True)
class EpisodeMetrics:
    """Standardized primary and secondary metrics for one episode."""

    schema_version: str
    scenario_id: str
    category: str
    split: str
    controller_arm: str
    seed: int
    # Primary outcomes
    rms_attitude_err_deg: float  # Over steady/eval window (t >= eval_window_start_s)
    recovery_time_s: float  # Time from reference onset to sustained envelope; NaN if unrecovered
    recovered: bool
    loss_of_control: bool
    failure_reason: str | None
    physically_infeasible: bool
    # Secondary outcomes
    full_rms_attitude_err_deg: float
    peak_attitude_err_deg: float
    p95_attitude_err_deg: float
    p99_attitude_err_deg: float
    rms_rate_err_rad_s: float
    peak_rate_err_rad_s: float
    rw_effort_nms: float
    rw_energy_proxy: float
    mtq_effort_am2_s: float
    rw_saturation_fraction: float
    req_vs_achieved_torque_rms_nm: float
    mean_rho: float
    mean_alpha: float
    mean_rl_torque_nm: float
    gate_reject_count: int
    mode_transition_count: int
    mean_cycle_time_ms: float
    infeasibility_detected: bool = False
    correct_infeasibility_response: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_episode_metrics(
    *,
    scenario_id: str,
    category: str,
    split: str,
    controller_arm: str,
    seed: int,
    times_s: np.ndarray,
    att_err_deg: np.ndarray,
    rate_err_rad_s: np.ndarray,
    rw_torque_achieved_nm: np.ndarray,
    mtq_dipole_achieved_am2: np.ndarray,
    tau_request_nm: np.ndarray,
    tau_achieved_total_nm: np.ndarray,
    rw_saturated_any: np.ndarray,
    rho_hist: np.ndarray,
    alpha_hist: np.ndarray,
    rl_torque_norm_nm: np.ndarray,
    gate_rejected: np.ndarray,
    modes: list[str],
    cycle_times_ms: np.ndarray,
    fault_onset_s: float,
    min_oracle_rank: int,
    dt_s: float,
    criteria: SuccessCriteria | None = None,
    authority_infeasible_flags: np.ndarray | None = None,
    oracle_zero_margin_steps: int = 0,
) -> EpisodeMetrics:
    """Compute all primary & secondary metrics consistently from episode arrays."""
    crit = SuccessCriteria() if criteria is None else criteria
    n = len(times_s)
    if n == 0:
        raise ValueError("Cannot compute metrics on empty episode")

    phys_infeasible = (min_oracle_rank < 3) or (
        oracle_zero_margin_steps >= max(50, int(0.40 * n))
    )
    infeas_mask = (
        np.asarray(authority_infeasible_flags, dtype=bool)
        if authority_infeasible_flags is not None
        else np.zeros(n, dtype=bool)
    )
    infeas_det = bool(np.any(infeas_mask))
    rl_suppressed_during_infeas = bool(
        infeas_det and float(np.max(rl_torque_norm_nm[infeas_mask])) < 1e-6
    )
    correct_infeas_resp = bool(phys_infeasible and infeas_det and rl_suppressed_during_infeas)

    non_finite = bool(
        not np.all(np.isfinite(att_err_deg)) or not np.all(np.isfinite(rate_err_rad_s))
    )
    if non_finite:
        return EpisodeMetrics(
            schema_version=METRIC_SCHEMA_VERSION,
            scenario_id=scenario_id,
            category=category,
            split=split,
            controller_arm=controller_arm,
            seed=seed,
            rms_attitude_err_deg=float("nan"),
            recovery_time_s=float("nan"),
            recovered=False,
            loss_of_control=True,
            failure_reason="non_finite_state",
            physically_infeasible=phys_infeasible,
            full_rms_attitude_err_deg=float("nan"),
            peak_attitude_err_deg=float("nan"),
            p95_attitude_err_deg=float("nan"),
            p99_attitude_err_deg=float("nan"),
            rms_rate_err_rad_s=float("nan"),
            peak_rate_err_rad_s=float("nan"),
            rw_effort_nms=float("nan"),
            rw_energy_proxy=float("nan"),
            mtq_effort_am2_s=float("nan"),
            rw_saturation_fraction=1.0,
            req_vs_achieved_torque_rms_nm=float("nan"),
            mean_rho=0.0,
            mean_alpha=0.0,
            mean_rl_torque_nm=0.0,
            gate_reject_count=int(np.sum(gate_rejected)),
            mode_transition_count=0,
            mean_cycle_time_ms=float(np.mean(cycle_times_ms)),
            infeasibility_detected=infeas_det,
            correct_infeasibility_response=correct_infeas_resp,
        )

    eval_mask = times_s >= crit.eval_window_start_s
    if not np.any(eval_mask):
        eval_mask = np.ones(n, dtype=bool)
    att_eval = att_err_deg[eval_mask]

    rms_eval = float(np.sqrt(np.mean(att_eval**2)))
    full_rms = float(np.sqrt(np.mean(att_err_deg**2)))
    peak_att = float(np.max(att_err_deg))
    p95_att = float(np.percentile(att_eval, 95))
    p99_att = float(np.percentile(att_eval, 99))
    rms_rate = float(np.sqrt(np.mean(rate_err_rad_s[eval_mask] ** 2)))
    peak_rate = float(np.max(rate_err_rad_s))

    # Sustained recovery time after fault_onset_s (or t=0 for fault-free S0/S7)
    sustain_steps = max(1, int(round(crit.sustained_duration_s / dt_s)))
    in_env = (att_err_deg <= crit.theta_success_deg) & (
        rate_err_rad_s <= crit.omega_success_rad_s
    )
    start_idx = int(np.searchsorted(times_s, fault_onset_s))
    recovery_time = float("nan")
    recovered = False
    for idx in range(start_idx, max(start_idx, n - sustain_steps + 1)):
        if bool(np.all(in_env[idx : idx + sustain_steps])):
            recovery_time = float(times_s[idx] - fault_onset_s)
            recovered = True
            break

    # Failure / loss-of-control classification
    failure_reason: str | None = None
    loc = False
    if not recovered or recovery_time > crit.recovery_deadline_s:
        loc = True
        failure_reason = "failed_to_recover_within_deadline"
    elif rms_eval > crit.loc_steady_rms_deg:
        loc = True
        failure_reason = "steady_rms_exceeded"
    elif (
        float(np.max(att_eval)) > crit.loc_peak_post_recovery_deg
        and fault_onset_s < crit.eval_window_start_s
    ):
        loc = True
        failure_reason = "post_recovery_peak_exceeded"

    rw_norms = np.linalg.norm(rw_torque_achieved_nm, axis=1)
    mtq_norms = np.linalg.norm(mtq_dipole_achieved_am2, axis=1)
    torque_err_norms = np.linalg.norm(tau_request_nm - tau_achieved_total_nm, axis=1)

    transitions = sum(1 for k in range(1, len(modes)) if modes[k] != modes[k - 1])

    return EpisodeMetrics(
        schema_version=METRIC_SCHEMA_VERSION,
        scenario_id=scenario_id,
        category=category,
        split=split,
        controller_arm=controller_arm,
        seed=seed,
        rms_attitude_err_deg=rms_eval,
        recovery_time_s=recovery_time,
        recovered=recovered,
        loss_of_control=loc,
        failure_reason=failure_reason,
        physically_infeasible=phys_infeasible,
        full_rms_attitude_err_deg=full_rms,
        peak_attitude_err_deg=peak_att,
        p95_attitude_err_deg=p95_att,
        p99_attitude_err_deg=p99_att,
        rms_rate_err_rad_s=rms_rate,
        peak_rate_err_rad_s=peak_rate,
        rw_effort_nms=float(np.sum(rw_norms) * dt_s),
        rw_energy_proxy=float(np.sum(rw_norms**2) * dt_s),
        mtq_effort_am2_s=float(np.sum(mtq_norms) * dt_s),
        rw_saturation_fraction=float(np.mean(rw_saturated_any)),
        req_vs_achieved_torque_rms_nm=float(np.sqrt(np.mean(torque_err_norms**2))),
        mean_rho=float(np.mean(rho_hist)),
        mean_alpha=float(np.mean(alpha_hist)),
        mean_rl_torque_nm=float(np.mean(rl_torque_norm_nm)),
        gate_reject_count=int(np.sum(gate_rejected)),
        mode_transition_count=transitions,
        mean_cycle_time_ms=float(np.mean(cycle_times_ms)),
        infeasibility_detected=infeas_det,
        correct_infeasibility_response=correct_infeas_resp,
    )
