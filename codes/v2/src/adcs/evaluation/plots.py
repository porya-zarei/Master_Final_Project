"""All 12 required research figures specified in RESEARCH_PROTOCOL.md §12."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from adcs.evaluation.runner import EpisodeLog
from adcs.evaluation.statistics import PairedComparisonRow
from adcs.faults import ScenarioSpec
from adcs.interfaces.types import SupervisorMode

MODE_TO_INT = {
    SupervisorMode.M0_NOMINAL.value: 0,
    SupervisorMode.M1_SUSPECTED_DEGRADATION.value: 1,
    SupervisorMode.M2_CONFIRMED_DEGRADATION.value: 2,
    SupervisorMode.M3_UNKNOWN_INVALID_UNSAFE.value: 3,
    SupervisorMode.M4_RECOVERY.value: 4,
}


def _annotate_faults(ax: plt.Axes, scenario: ScenarioSpec) -> None:
    seen: set[float] = set()
    for ev in scenario.events:
        if ev.start_s not in seen:
            ax.axvline(ev.start_s, color="crimson", linestyle="--", linewidth=1.0, alpha=0.75)
            seen.add(ev.start_s)
        if ev.end_s is not None and ev.end_s not in seen:
            ax.axvline(ev.end_s, color="seagreen", linestyle=":", linewidth=1.0, alpha=0.75)
            seen.add(ev.end_s)


def generate_all_required_plots(
    *,
    df: pd.DataFrame,
    trace_logs: dict[str, EpisodeLog],
    trace_scenario: ScenarioSpec,
    ablation_comparisons: list[PairedComparisonRow],
    out_dir: Path,
    rw_tau_limit_nm: float = 0.15,
    rw_h_limit_nms: float = 6.0,
) -> list[Path]:
    """Generate and save all 12 protocol plots to `out_dir`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []

    ccr_log = trace_logs.get("A7_ccr_v2_full") or next(iter(trace_logs.values()))
    t_ccr = np.array([s.time_s for s in ccr_log.steps])

    # 1. Attitude-error time histories with fault onset
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for arm, log in trace_logs.items():
        t = [s.time_s for s in log.steps]
        err = [s.att_err_deg for s in log.steps]
        ax.plot(t, err, label=arm, linewidth=1.5)
    _annotate_faults(ax, trace_scenario)
    ax.set_title(f"1. Attitude Error Time History — {trace_scenario.scenario_id}")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Geodesic Attitude Error (deg)")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    p = out_dir / "01_attitude_error_time_history.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    # 2. Angular-rate error time histories
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for arm, log in trace_logs.items():
        t = [s.time_s for s in log.steps]
        rerr = [s.rate_err_rad_s for s in log.steps]
        ax.plot(t, rerr, label=arm, linewidth=1.4)
    _annotate_faults(ax, trace_scenario)
    ax.set_title(f"2. Angular-Rate Error Time History — {trace_scenario.scenario_id}")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Angular Rate Error Norm (rad/s)")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    p = out_dir / "02_rate_error_time_history.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    # 3. Requested, allocated, and achieved torque (A7 trace)
    fig, axes = plt.subplots(3, 1, figsize=(9, 6.5), sharex=True)
    tau_req = np.array([s.tau_request_nm for s in ccr_log.steps])
    tau_alloc = np.array([s.tau_allocated_nm for s in ccr_log.steps])
    tau_ach = np.array([s.tau_achieved_total_nm for s in ccr_log.steps])
    for i, lbl in enumerate(["X", "Y", "Z"]):
        axes[i].plot(t_ccr, tau_req[:, i], label="Requested", alpha=0.8)
        axes[i].plot(t_ccr, tau_alloc[:, i], "--", label="Allocated", alpha=0.8)
        axes[i].plot(t_ccr, tau_ach[:, i], ":", label="Achieved", linewidth=1.6)
        _annotate_faults(axes[i], trace_scenario)
        axes[i].set_ylabel(f"Torque {lbl} (N·m)")
        axes[i].grid(True, alpha=0.3)
    axes[0].legend(loc="upper right", fontsize=8, ncol=3)
    axes[0].set_title(
        f"3. Requested vs Allocated vs Achieved Torque ({ccr_log.metrics.controller_arm})"
    )
    axes[-1].set_xlabel("Time (s)")
    p = out_dir / "03_requested_allocated_achieved_torque.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    # 4. Wheel torque, momentum, and saturation
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 5.5), sharex=True)
    rw_tau = np.array([s.rw_torque_achieved_nm for s in ccr_log.steps])
    rw_h = np.array([s.wheel_momentum_nms for s in ccr_log.steps])
    for i in range(rw_tau.shape[1]):
        ax1.plot(t_ccr, rw_tau[:, i], label=f"RW{i}")
        ax2.plot(t_ccr, rw_h[:, i], label=f"RW{i}")
    ax1.axhline(rw_tau_limit_nm, color="k", linestyle=":", alpha=0.5)
    ax1.axhline(-rw_tau_limit_nm, color="k", linestyle=":", alpha=0.5)
    ax2.axhline(rw_h_limit_nms, color="k", linestyle=":", alpha=0.5)
    ax2.axhline(-rw_h_limit_nms, color="k", linestyle=":", alpha=0.5)
    _annotate_faults(ax1, trace_scenario)
    _annotate_faults(ax2, trace_scenario)
    ax1.set_ylabel("RW Torque (N·m)")
    ax2.set_ylabel("RW Momentum (N·m·s)")
    ax2.set_xlabel("Time (s)")
    ax1.legend(fontsize=8, ncol=3)
    ax1.grid(True, alpha=0.3)
    ax2.grid(True, alpha=0.3)
    ax1.set_title(f"4. Reaction Wheel Torque & Momentum ({ccr_log.metrics.controller_arm})")
    p = out_dir / "04_wheel_torque_momentum_saturation.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    # 5. MTQ command and field-dependent torque
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 5.5), sharex=True)
    mtq_m = np.array([s.mtq_dipole_cmd_am2 for s in ccr_log.steps])
    mtq_t = np.array([s.mtq_torque_achieved_nm for s in ccr_log.steps]) * 1e6  # uN*m
    for i, lbl in enumerate(["X", "Y", "Z"]):
        ax1.plot(t_ccr, mtq_m[:, i], label=f"MTQ {lbl}")
        ax2.plot(t_ccr, mtq_t[:, i], label=f"Tau_MTQ {lbl}")
    _annotate_faults(ax1, trace_scenario)
    _annotate_faults(ax2, trace_scenario)
    ax1.set_ylabel("Dipole Cmd (A·m²)")
    ax2.set_ylabel("Achieved Torque (µN·m)")
    ax2.set_xlabel("Time (s)")
    ax1.legend(fontsize=8, ncol=3)
    ax1.grid(True, alpha=0.3)
    ax2.grid(True, alpha=0.3)
    ax1.set_title(
        f"5. MTQ Dipole Command & Field-Dependent Torque ({ccr_log.metrics.controller_arm})"
    )
    p = out_dir / "05_mtq_command_and_field_torque.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    # 6. CCR gate signals: tau_RL_raw, rho, alpha, G, and accepted residual
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(9, 7.0), sharex=True)
    rhos = np.array([s.rho for s in ccr_log.steps])
    alphas = np.array([s.alpha for s in ccr_log.steps])
    g_xyz = np.array([s.directional_gain_xyz for s in ccr_log.steps])
    rl_raw_n = np.array([np.linalg.norm(s.tau_rl_raw_nm) for s in ccr_log.steps])
    rl_gat_n = np.array([np.linalg.norm(s.tau_rl_gated_nm) for s in ccr_log.steps])
    ax1.plot(t_ccr, rhos, label="Need rho")
    ax1.plot(t_ccr, alphas, label="Trust alpha")
    ax1.set_ylabel("Scalars [0,1]")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)
    for i, lbl in enumerate(["G_x", "G_y", "G_z"]):
        ax2.plot(t_ccr, g_xyz[:, i], label=lbl)
    ax2.set_ylabel("Dir. Gate G")
    ax2.legend(fontsize=8, ncol=3)
    ax2.grid(True, alpha=0.3)
    ax3.plot(t_ccr, rl_raw_n, label="||tau_RL_raw||", alpha=0.7)
    ax3.plot(t_ccr, rl_gat_n, label="||tau_RL_gated||", linewidth=1.6)
    ax3.set_ylabel("Residual Norm (N·m)")
    ax3.set_xlabel("Time (s)")
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)
    for ax in (ax1, ax2, ax3):
        _annotate_faults(ax, trace_scenario)
    ax1.set_title(f"6. CCR v2 Deterministic Authority Gate Signals — {trace_scenario.scenario_id}")
    p = out_dir / "06_ccr_gate_signals_rho_alpha_G_residual.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    # 7. Capability estimate & conservative bound vs true oracle capability
    fig, axes = plt.subplots(3, 1, figsize=(9, 6.2), sharex=True)
    m_est = np.array([s.cap_margin_est_xyz for s in ccr_log.steps])
    m_ora = np.array([s.cap_margin_oracle_xyz for s in ccr_log.steps])
    for i, lbl in enumerate(["X", "Y", "Z"]):
        axes[i].plot(t_ccr, m_ora[:, i], "k--", label="Oracle True Margin")
        axes[i].plot(t_ccr, m_est[:, i], label="Online Conservative Margin")
        _annotate_faults(axes[i], trace_scenario)
        axes[i].set_ylabel(f"Margin {lbl}")
        axes[i].set_ylim(-0.05, 1.1)
        axes[i].grid(True, alpha=0.3)
    axes[0].legend(fontsize=8, ncol=2)
    axes[0].set_title(
        f"7. Online Conservative Capability vs Oracle Truth — {trace_scenario.scenario_id}"
    )
    axes[-1].set_xlabel("Time (s)")
    p = out_dir / "07_capability_estimate_vs_oracle.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    # 8. Supervisor modes and transitions
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 4.8), sharex=True)
    mode_ints = [MODE_TO_INT.get(s.mode, 3) for s in ccr_log.steps]
    gammas = [s.gamma_obs for s in ccr_log.steps]
    ax1.step(t_ccr, mode_ints, where="post", linewidth=1.6)
    ax1.set_yticks([0, 1, 2, 3, 4])
    ax1.set_yticklabels(["M0 Nom", "M1 Susp", "M2 Conf", "M3 Unsafe", "M4 Recov"])
    ax1.set_ylabel("Supervisor Mode")
    ax1.grid(True, alpha=0.3)
    ax2.plot(t_ccr, gammas, color="darkorange", label="gamma_obs")
    ax2.set_ylabel("Observability gamma_obs")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylim(-0.05, 1.05)
    ax2.grid(True, alpha=0.3)
    _annotate_faults(ax1, trace_scenario)
    _annotate_faults(ax2, trace_scenario)
    ax1.set_title(f"8. Supervisor Mode Transitions & Observability — {trace_scenario.scenario_id}")
    p = out_dir / "08_supervisor_modes_and_transitions.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    # 9. Recovery-time distribution across controller arms
    fig, ax = plt.subplots(figsize=(10, 4.8))
    arms_sorted = sorted(df["controller_arm"].unique())
    data_rec = [
        df[(df["controller_arm"] == a) & (df["recovered"])]["recovery_time_s"].dropna().to_numpy()
        for a in arms_sorted
    ]
    data_rec = [d if len(d) > 0 else np.array([np.nan]) for d in data_rec]
    ax.boxplot(data_rec, tick_labels=arms_sorted, showfliers=True)
    ax.set_ylabel("Recovery Time (s)")
    ax.set_title("9. Fault Recovery-Time Distribution Across Arms (Recovered Episodes)")
    ax.tick_params(axis="x", rotation=35, labelsize=8)
    ax.grid(True, axis="y", alpha=0.3)
    p = out_dir / "09_recovery_time_distribution.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    # 10. Performance vs actuator effort scatter
    fig, ax = plt.subplots(figsize=(8.5, 5.0))
    arm_agg = df.groupby("controller_arm", as_index=False).agg(
        rms=("rms_attitude_err_deg", "mean"),
        effort=("rw_effort_nms", "mean"),
    )
    for _, row in arm_agg.iterrows():
        ax.scatter(row["effort"], row["rms"], s=70)
        ax.annotate(
            row["controller_arm"],
            (row["effort"], row["rms"]),
            fontsize=7.5,
            xytext=(4, 3),
            textcoords="offset points",
        )
    ax.set_xlabel("Mean RW Actuation Effort (N·m·s)")
    ax.set_ylabel("Mean Steady RMS Attitude Error (deg)")
    ax.set_title("10. Pointing Performance vs. Actuation Effort Across Arms")
    ax.grid(True, alpha=0.3)
    p = out_dir / "10_performance_vs_effort.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    # 11. Failure rate (loss of control %) by scenario category & arm
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    piv = df.pivot_table(
        index="scenario_id",
        columns="controller_arm",
        values="loss_of_control",
        aggfunc=lambda s: 100.0 * float(np.mean(s)),
    )
    im = ax.imshow(piv.to_numpy(dtype=float), aspect="auto", cmap="YlOrRd", vmin=0.0, vmax=100.0)
    ax.set_yticks(range(len(piv.index)))
    ax.set_yticklabels(piv.index, fontsize=8)
    ax.set_xticks(range(len(piv.columns)))
    ax.set_xticklabels(piv.columns, rotation=35, ha="right", fontsize=8)
    for i in range(len(piv.index)):
        for j in range(len(piv.columns)):
            val = piv.iloc[i, j]
            ax.text(j, i, f"{val:.0f}%", ha="center", va="center", fontsize=7, color="black")
    fig.colorbar(im, ax=ax, label="Loss-of-Control Rate (%)")
    ax.set_title("11. Loss-of-Control Failure Rate (%) by Scenario & Controller Arm")
    p = out_dir / "11_failure_rate_by_scenario.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    # 12. Ablation summary: paired differences & 95% bootstrap CIs
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    valid_cmp = [c for c in ablation_comparisons if np.isfinite(c.mean_diff)]
    if valid_cmp:
        y_pos = np.arange(len(valid_cmp))
        means = [c.mean_diff for c in valid_cmp]
        err_lo = [c.mean_diff - c.ci_low for c in valid_cmp]
        err_hi = [c.ci_high - c.mean_diff for c in valid_cmp]
        labels = [f"{c.arm} vs {c.reference_arm}" for c in valid_cmp]
        ax.errorbar(
            means,
            y_pos,
            xerr=[err_lo, err_hi],
            fmt="o",
            capsize=4,
            color="navy",
        )
        ax.axvline(0.0, color="crimson", linestyle="--", linewidth=1.1)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel("Paired RMS Attitude Error Diff (deg) [Negative = Better]")
        ax.set_title("12. Paired Effect Summary with 95% Bootstrap CIs")
        ax.grid(True, axis="x", alpha=0.3)
    p = out_dir / "12_ablation_effect_sizes_ci.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    saved.append(p)

    return saved
