"""Paired statistical analysis: bootstrap CIs, effect sizes (Cohen's dz), and Wilcoxon tests."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


@dataclass(frozen=True)
class ArmSummaryRow:
    """Summary statistics for one controller arm (overall or per-scenario)."""

    arm: str
    group: str
    n_episodes: int
    rms_mean_deg: float
    rms_std_deg: float
    rms_median_deg: float
    rms_iqr_deg: float
    peak_mean_deg: float
    recovery_rate: float
    recovery_time_median_s: float
    loc_count: int
    loc_rate_pct: float
    effort_mean_nms: float
    sat_frac_mean: float
    mean_rho: float
    mean_alpha: float
    mean_rl_torque_nm: float
    cycle_ms_mean: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PairedComparisonRow:
    """Paired comparison of `arm` minus `reference_arm` on identical (scenario, seed) pairs."""

    arm: str
    reference_arm: str
    metric: str
    n_pairs: int
    mean_diff: float  # negative is BETTER for attitude error / recovery time / effort
    ci_low: float
    ci_high: float
    median_diff: float
    cohens_dz: float
    wilcoxon_p: float
    win_rate_pct: float  # % of paired episodes where arm < reference_arm
    wilcoxon_p_holm: float = float("nan")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize_arms(df: pd.DataFrame, group_col: str | None = None) -> list[ArmSummaryRow]:
    """Compute summary statistics per controller arm (and optional grouping column)."""
    rows: list[ArmSummaryRow] = []
    if group_col is None:
        groups = [("ALL", df)]
    else:
        groups = [(str(k), g) for k, g in df.groupby(group_col, sort=True)]

    for grp_name, gdf in groups:
        for arm, adf in gdf.groupby("controller_arm", sort=True):
            rms = adf["rms_attitude_err_deg"].dropna().to_numpy(dtype=np.float64)
            rec_t = adf.loc[adf["recovered"], "recovery_time_s"].dropna().to_numpy(dtype=np.float64)
            n = len(adf)
            loc_cnt = int(adf["loss_of_control"].sum())
            rows.append(
                ArmSummaryRow(
                    arm=str(arm),
                    group=grp_name,
                    n_episodes=n,
                    rms_mean_deg=float(np.mean(rms)) if len(rms) else float("nan"),
                    rms_std_deg=float(np.std(rms, ddof=1)) if len(rms) > 1 else 0.0,
                    rms_median_deg=float(np.median(rms)) if len(rms) else float("nan"),
                    rms_iqr_deg=(
                        float(np.percentile(rms, 75) - np.percentile(rms, 25))
                        if len(rms)
                        else float("nan")
                    ),
                    peak_mean_deg=float(adf["peak_attitude_err_deg"].mean()),
                    recovery_rate=float(adf["recovered"].mean()),
                    recovery_time_median_s=(
                        float(np.median(rec_t)) if len(rec_t) else float("nan")
                    ),
                    loc_count=loc_cnt,
                    loc_rate_pct=100.0 * loc_cnt / max(n, 1),
                    effort_mean_nms=float(adf["rw_effort_nms"].mean()),
                    sat_frac_mean=float(adf["rw_saturation_fraction"].mean()),
                    mean_rho=float(adf["mean_rho"].mean()),
                    mean_alpha=float(adf["mean_alpha"].mean()),
                    mean_rl_torque_nm=float(adf["mean_rl_torque_nm"].mean()),
                    cycle_ms_mean=float(adf["mean_cycle_time_ms"].mean()),
                )
            )
    return rows


def paired_bootstrap_comparison(
    df: pd.DataFrame,
    *,
    arm: str,
    reference_arm: str,
    metric: str = "rms_attitude_err_deg",
    n_boot: int = 5000,
    seed: int = 2026,
) -> PairedComparisonRow:
    """Compute paired difference, 95% bootstrap CI, Cohen's dz, and Wilcoxon signed-rank p.

    Aggregates by (scenario_id, seed) before pairing so multi-train_seed evaluations
    yield one independent policy-averaged observation per mission pair (no pseudoreplication).
    """
    sub_a = (
        df[df["controller_arm"] == arm][["scenario_id", "seed", metric]]
        .groupby(["scenario_id", "seed"], as_index=False)[metric]
        .mean()
        .rename(columns={metric: "a"})
    )
    sub_r = (
        df[df["controller_arm"] == reference_arm][["scenario_id", "seed", metric]]
        .groupby(["scenario_id", "seed"], as_index=False)[metric]
        .mean()
        .rename(columns={metric: "r"})
    )
    merged = pd.merge(sub_a, sub_r, on=["scenario_id", "seed"], how="inner").dropna()
    diffs = (merged["a"] - merged["r"]).to_numpy(dtype=np.float64)
    n = len(diffs)
    if n == 0:
        return PairedComparisonRow(
            arm=arm,
            reference_arm=reference_arm,
            metric=metric,
            n_pairs=0,
            mean_diff=float("nan"),
            ci_low=float("nan"),
            ci_high=float("nan"),
            median_diff=float("nan"),
            cohens_dz=float("nan"),
            wilcoxon_p=float("nan"),
            win_rate_pct=float("nan"),
        )

    mean_d = float(np.mean(diffs))
    std_d = float(np.std(diffs, ddof=1)) if n > 1 else 0.0
    dz = mean_d / std_d if std_d > 1e-12 else 0.0

    rng = np.random.default_rng(seed)
    boot_idx = rng.integers(0, n, size=(n_boot, n))
    boot_means = np.mean(diffs[boot_idx], axis=1)
    ci_lo, ci_hi = np.percentile(boot_means, [2.5, 97.5])

    nz = diffs[np.abs(diffs) > 1e-12]
    if len(nz) >= 5:
        try:
            wilc_p = float(stats.wilcoxon(nz).pvalue)
        except Exception:
            wilc_p = float("nan")
    else:
        wilc_p = float("nan")

    win_pct = 100.0 * float(np.mean(diffs < -1e-9))
    return PairedComparisonRow(
        arm=arm,
        reference_arm=reference_arm,
        metric=metric,
        n_pairs=n,
        mean_diff=mean_d,
        ci_low=float(ci_lo),
        ci_high=float(ci_hi),
        median_diff=float(np.median(diffs)),
        cohens_dz=float(dz),
        wilcoxon_p=wilc_p,
        win_rate_pct=win_pct,
    )


def apply_holm_bonferroni(rows: list[PairedComparisonRow]) -> list[PairedComparisonRow]:
    """Apply step-down Holm-Bonferroni correction across finite `wilcoxon_p` values."""
    valid_idx = [i for i, row in enumerate(rows) if np.isfinite(row.wilcoxon_p)]
    if not valid_idx:
        return [replace(row, wilcoxon_p_holm=float("nan")) for row in rows]

    sorted_idx = sorted(valid_idx, key=lambda i: rows[i].wilcoxon_p)
    m = len(sorted_idx)
    adjusted: dict[int, float] = {}
    prev_adj = 0.0
    for k, orig_i in enumerate(sorted_idx):
        raw_adj = min(1.0, (m - k) * rows[orig_i].wilcoxon_p)
        adj = max(prev_adj, raw_adj)
        adjusted[orig_i] = adj
        prev_adj = adj

    return [
        replace(row, wilcoxon_p_holm=adjusted.get(i, float("nan")))
        for i, row in enumerate(rows)
    ]


def summarize_failure_breakdown(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Break down loss-of-control across controllable vs physically infeasible episodes."""
    rows: list[dict[str, Any]] = []
    has_det = "infeasibility_detected" in df.columns
    has_resp = "correct_infeasibility_response" in df.columns

    for arm, adf in df.groupby("controller_arm", sort=True):
        n_total = len(adf)
        overall_loc_pct = 100.0 * float(adf["loss_of_control"].sum()) / max(n_total, 1)

        infeas_mask = adf["physically_infeasible"].astype(bool)
        ctrl_df = adf[~infeas_mask]
        infeas_df = adf[infeas_mask]

        n_ctrl = len(ctrl_df)
        ctrl_loc_cnt = int(ctrl_df["loss_of_control"].sum()) if n_ctrl else 0
        ctrl_loc_pct = 100.0 * ctrl_loc_cnt / n_ctrl if n_ctrl else 0.0

        n_infeas = len(infeas_df)
        infeas_loc_cnt = int(infeas_df["loss_of_control"].sum()) if n_infeas else 0
        infeas_loc_pct = 100.0 * infeas_loc_cnt / n_infeas if n_infeas else 0.0

        det_pct = (
            100.0 * float(infeas_df["infeasibility_detected"].astype(bool).sum()) / n_infeas
            if has_det and n_infeas
            else 0.0
        )
        resp_pct = (
            100.0
            * float(infeas_df["correct_infeasibility_response"].astype(bool).sum())
            / n_infeas
            if has_resp and n_infeas
            else 0.0
        )

        rows.append(
            {
                "arm": str(arm),
                "n_total": n_total,
                "overall_loc_pct": overall_loc_pct,
                "n_controllable": n_ctrl,
                "controllable_loc_count": ctrl_loc_cnt,
                "controllable_loc_pct": ctrl_loc_pct,
                "n_infeasible": n_infeas,
                "infeasible_loc_count": infeas_loc_cnt,
                "infeasible_loc_pct": infeas_loc_pct,
                "infeasibility_detected_pct": det_pct,
                "correct_infeasibility_response_pct": resp_pct,
            }
        )
    return rows
