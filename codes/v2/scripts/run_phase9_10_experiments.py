"""Phase 9 & 10 master experiment runner: training, Monte Carlo, ablations, plots, CPU profile.

Outputs immutable experiment records under `experiments/E001_ccr_v2_benchmark/` (or a specified
output directory). Strictly respects train / val / held-out test isolation: policies are trained
ONLY on the disjoint training distribution and evaluated paired across validation & held-out test
scenarios (S0–S8) against all classical baselines (A0–A3) and single-factor ablations.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from adcs.control.allocation import AllocationConfig
from adcs.control.classical import (
    ClassicalDOBController,
    ClassicalLQRController,
    StrongClassicalController,
    make_oracle_allocation_lqr,
)
from adcs.control.residual_rl import CCRController, CCRControllerConfig, TorchMLPResidualPolicy
from adcs.control.safety import GateConfig
from adcs.evaluation import EpisodeRunner
from adcs.evaluation.metrics import METRIC_SCHEMA_VERSION
from adcs.evaluation.plots import generate_all_required_plots
from adcs.evaluation.profiling import profile_control_stack_cpu
from adcs.evaluation.statistics import (
    PairedComparisonRow,
    apply_holm_bonferroni,
    paired_bootstrap_comparison,
    summarize_arms,
    summarize_failure_breakdown,
)
from adcs.faults import ScenarioSpec, build_default_scenario_catalog
from adcs.utils import capture_run_metadata, load_spacecraft_config, sha256_canonical

REPO_ROOT = Path(__file__).resolve().parents[1]
SPACECRAFT_YAML = REPO_ROOT / "spacecraft_config.yaml"


def _make_arm_configs() -> dict[str, dict[str, Any]]:
    """Define exact training configurations for the 6 learned policy variants."""
    cap_alloc = AllocationConfig(
        capability_aware=True,
        compensate_bias=True,
        mtq_assist_enabled=True,
        mtq_unload_gain=0.004,
    )
    # All RL arms (A4-A7) share the B9 capability allocator so comparisons isolate
    # the B7 gate and B4 supervisor effects without an allocator confounder.
    return {
        "A4_unstructured_rl": {
            "ccr_config": CCRControllerConfig(
                name="A4_unstructured_rl",
                allocation=cap_alloc,
                gate=GateConfig(
                    enable_rho=False,
                    enable_alpha=False,
                    enable_directional_g=False,
                    use_supervisor=False,
                ),
            ),
            "use_oracle": False,
            "clean_train": False,
        },
        "A5_rl_need_rho": {
            "ccr_config": CCRControllerConfig(
                name="A5_rl_need_rho",
                allocation=cap_alloc,
                gate=GateConfig(
                    enable_rho=True,
                    enable_alpha=False,
                    enable_directional_g=False,
                    use_supervisor=False,
                ),
            ),
            "use_oracle": False,
            "clean_train": False,
        },
        "A6_rl_oracle_gate": {
            "ccr_config": CCRControllerConfig(
                name="A6_rl_oracle_gate",
                allocation=cap_alloc,
                gate=GateConfig(
                    enable_rho=True,
                    enable_alpha=True,
                    enable_directional_g=True,
                    use_supervisor=True,
                ),
            ),
            "use_oracle": True,
            "clean_train": False,
        },
        "A7_ccr_v2_full": {
            "ccr_config": CCRControllerConfig(
                name="A7_ccr_v2_full",
                use_eso_backbone=False,
                allocation=cap_alloc,
                gate=GateConfig(
                    enable_rho=True,
                    enable_alpha=True,
                    enable_directional_g=True,
                    use_supervisor=True,
                ),
            ),
            "use_oracle": False,
            "clean_train": False,
        },
        "A7_ccr_v2_eso": {
            "ccr_config": CCRControllerConfig(
                name="A7_ccr_v2_eso",
                use_eso_backbone=True,
                allocation=cap_alloc,
                gate=GateConfig(
                    enable_rho=True,
                    enable_alpha=True,
                    enable_directional_g=True,
                    use_supervisor=True,
                ),
            ),
            "use_oracle": False,
            "clean_train": False,
        },
        "A7_clean_trained": {
            "ccr_config": CCRControllerConfig(
                name="A7_clean_trained",
                allocation=cap_alloc,
                gate=GateConfig(
                    enable_rho=False,
                    enable_alpha=False,
                    enable_directional_g=False,
                    use_supervisor=False,
                ),
            ),
            "use_oracle": False,
            "clean_train": True,
        },
    }


def _train_one_policy(
    args: tuple[str, int, int, int, str, str],
) -> tuple[str, int, str, float, list[float]]:
    from adcs.training import ADCSResidualEnv, EnvTrainConfig, SACConfig, train_sac

    arm_name, total_steps, train_seed, sac_seed, ckpt_dir_str, sc_yaml_str = args
    sc_cfg = load_spacecraft_config(sc_yaml_str)
    spec = _make_arm_configs()[arm_name]
    env_cfg = EnvTrainConfig(
        episode_duration_s=80.0,
        use_oracle_capability=spec["use_oracle"],
        clean_state_training=spec["clean_train"],
        ccr_config=spec["ccr_config"],
    )
    env = ADCSResidualEnv(sc_cfg, env_cfg)
    sac_cfg = SACConfig(
        total_steps=total_steps,
        warmup_steps=min(1000, max(200, total_steps // 10)),
        batch_size=128,
        buffer_size=max(20_000, total_steps + 2000),
        seed=sac_seed,
    )
    res = train_sac(env, sac_cfg, checkpoint_dir=Path(ckpt_dir_str), arm_label=arm_name)
    return arm_name, train_seed, res.weights_sha256, res.wall_time_s, res.episode_returns


def _build_eval_controller(
    arm_name: str,
    sc_cfg: Any,
    policies: dict[str, TorchMLPResidualPolicy],
) -> tuple[Any, bool]:
    """Instantiate any comparison arm (A0–A7) or single-factor ablation."""
    cap_alloc = AllocationConfig(
        capability_aware=True,
        compensate_bias=True,
        mtq_assist_enabled=True,
        mtq_unload_gain=0.004,
    )

    if arm_name == "A0_classical_lqr":
        return ClassicalLQRController(sc_cfg), False
    if arm_name == "A1_classical_oracle_alloc":
        return make_oracle_allocation_lqr(sc_cfg), True
    if arm_name == "A2_classical_dob_eso":
        return ClassicalDOBController(sc_cfg), False
    if arm_name == "A3_strong_classical":
        return StrongClassicalController(sc_cfg), False

    # All RL arms (A4-A7) use cap_alloc to eliminate allocator confounding.
    if arm_name == "A4_unstructured_rl":
        cfg = CCRControllerConfig(
            name=arm_name,
            allocation=cap_alloc,
            gate=GateConfig(
                enable_rho=False,
                enable_alpha=False,
                enable_directional_g=False,
                use_supervisor=False,
            ),
        )
        return CCRController(sc_cfg, policies["A4_unstructured_rl"], cfg), False

    if arm_name == "A5_rl_need_rho":
        cfg = CCRControllerConfig(
            name=arm_name,
            allocation=cap_alloc,
            gate=GateConfig(
                enable_rho=True,
                enable_alpha=False,
                enable_directional_g=False,
                use_supervisor=False,
            ),
        )
        return CCRController(sc_cfg, policies["A5_rl_need_rho"], cfg), False

    if arm_name == "A6_rl_oracle_gate":
        cfg = CCRControllerConfig(
            name=arm_name,
            allocation=cap_alloc,
            gate=GateConfig(
                enable_rho=True,
                enable_alpha=True,
                enable_directional_g=True,
                use_supervisor=True,
            ),
        )
        return CCRController(sc_cfg, policies["A6_rl_oracle_gate"], cfg), True

    if arm_name == "A7_ccr_v2_full":
        cfg = CCRControllerConfig(
            name=arm_name,
            use_eso_backbone=False,
            allocation=cap_alloc,
            gate=GateConfig(
                enable_rho=True,
                enable_alpha=True,
                enable_directional_g=True,
                use_supervisor=True,
            ),
        )
        return CCRController(sc_cfg, policies["A7_ccr_v2_full"], cfg), False

    if arm_name == "A7_ccr_v2_eso":
        cfg = CCRControllerConfig(
            name=arm_name,
            use_eso_backbone=True,
            allocation=cap_alloc,
            gate=GateConfig(
                enable_rho=True,
                enable_alpha=True,
                enable_directional_g=True,
                use_supervisor=True,
            ),
        )
        return CCRController(sc_cfg, policies["A7_ccr_v2_eso"], cfg), False

    # Single-factor ablations from A7_ccr_v2_full
    p_a7 = policies["A7_ccr_v2_full"]
    if arm_name == "Abl_A7_no_rho":
        cfg = CCRControllerConfig(
            name=arm_name, allocation=cap_alloc, gate=GateConfig(enable_rho=False)
        )
        return CCRController(sc_cfg, p_a7, cfg), False
    if arm_name == "Abl_A7_no_alpha":
        cfg = CCRControllerConfig(
            name=arm_name, allocation=cap_alloc, gate=GateConfig(enable_alpha=False)
        )
        return CCRController(sc_cfg, p_a7, cfg), False
    if arm_name == "Abl_A7_no_G":
        cfg = CCRControllerConfig(
            name=arm_name, allocation=cap_alloc, gate=GateConfig(enable_directional_g=False)
        )
        return CCRController(sc_cfg, p_a7, cfg), False
    if arm_name == "Abl_A7_no_supervisor":
        cfg = CCRControllerConfig(
            name=arm_name, allocation=cap_alloc, gate=GateConfig(use_supervisor=False)
        )
        return CCRController(sc_cfg, p_a7, cfg), False
    if arm_name == "Abl_A7_geom_G":
        cfg = CCRControllerConfig(
            name=arm_name, allocation=cap_alloc, gate=GateConfig(use_geometry_projection=True)
        )
        return CCRController(sc_cfg, p_a7, cfg), False
    if arm_name == "Abl_A7_clean_trained":
        cfg = CCRControllerConfig(name=arm_name, allocation=cap_alloc, gate=GateConfig())
        return CCRController(sc_cfg, policies["A7_clean_trained"], cfg), False

    raise ValueError(f"Unknown arm: {arm_name}")


CLASSICAL_ARMS = frozenset(
    {
        "A0_classical_lqr",
        "A1_classical_oracle_alloc",
        "A2_classical_dob_eso",
        "A3_strong_classical",
    }
)


def _eval_worker(
    job: tuple[str, str, int, int, dict[str, str], str],
) -> dict[str, Any]:
    arm_name, scenario_id, seed, train_seed, ckpt_paths, sc_yaml_str = job
    sc_cfg = load_spacecraft_config(sc_yaml_str)
    catalog = build_default_scenario_catalog()
    scenario = catalog[scenario_id]
    policies = {k: TorchMLPResidualPolicy.load(v) for k, v in ckpt_paths.items()}
    ctrl, use_oracle = _build_eval_controller(arm_name, sc_cfg, policies)
    runner = EpisodeRunner(sc_cfg)
    log = runner.run_episode(
        ctrl, scenario, seed=seed, use_oracle_capability=use_oracle, record_trace=False
    )
    rec = log.metrics.to_dict()
    rec["train_seed"] = train_seed
    return rec


def _save_paired_comparisons(
    sub_df: pd.DataFrame,
    eval_arms: list[str],
    analysis_dir: Path,
    *,
    prefix: str,
) -> list[PairedComparisonRow]:
    vs_a3 = apply_holm_bonferroni(
        [
            paired_bootstrap_comparison(sub_df, arm=a, reference_arm="A3_strong_classical")
            for a in eval_arms
            if a != "A3_strong_classical"
        ]
    )
    vs_a0 = apply_holm_bonferroni(
        [
            paired_bootstrap_comparison(sub_df, arm=a, reference_arm="A0_classical_lqr")
            for a in eval_arms
            if a != "A0_classical_lqr"
        ]
    )
    abl_arms = [
        "A0_classical_lqr",
        "A3_strong_classical",
        "A4_unstructured_rl",
        "A5_rl_need_rho",
        "A6_rl_oracle_gate",
        "A7_ccr_v2_eso",
        "Abl_A7_no_rho",
        "Abl_A7_no_alpha",
        "Abl_A7_no_G",
        "Abl_A7_no_supervisor",
        "Abl_A7_geom_G",
        "Abl_A7_clean_trained",
    ]
    abl_vs_a7 = apply_holm_bonferroni(
        [
            paired_bootstrap_comparison(sub_df, arm=a, reference_arm="A7_ccr_v2_full")
            for a in abl_arms
        ]
    )
    pd.DataFrame([r.to_dict() for r in vs_a3]).to_csv(
        analysis_dir / f"{prefix}_vs_A3.csv", index=False
    )
    pd.DataFrame([r.to_dict() for r in vs_a0]).to_csv(
        analysis_dir / f"{prefix}_vs_A0.csv", index=False
    )
    pd.DataFrame([r.to_dict() for r in abl_vs_a7]).to_csv(
        analysis_dir / f"{prefix}_ablations_vs_A7.csv", index=False
    )
    return abl_vs_a7


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CCR v2 Phase 9 & 10 benchmark suite.")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--spacecraft-config", type=Path, default=SPACECRAFT_YAML)
    parser.add_argument("--train-steps", type=int, default=12_000)
    parser.add_argument("--n-seeds", type=int, default=8)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 4))
    parser.add_argument(
        "--train-workers",
        type=int,
        default=None,
        help="Parallel workers for SAC training (defaults to --workers).",
    )
    parser.add_argument("--train-seed", type=int, default=42)
    parser.add_argument(
        "--train-seeds",
        type=str,
        default=None,
        help="Comma-separated training seeds (e.g. '42,107,211'); defaults to [--train-seed].",
    )
    parser.add_argument(
        "--eval-splits",
        type=str,
        default="val,test",
        help="Comma-separated scenario splits to evaluate (default: 'val,test').",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Reuse existing policy checkpoints (policy_weights.npz + policy_meta.json) "
            "in --out-dir instead of retraining."
        ),
    )
    args = parser.parse_args()

    if args.train_seeds:
        train_seeds = [int(s.strip()) for s in args.train_seeds.split(",") if s.strip()]
    else:
        train_seeds = [args.train_seed]
    eval_splits = {s.strip() for s in args.eval_splits.split(",") if s.strip()}
    if not eval_splits:
        raise ValueError("--eval-splits must contain at least one split name.")

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_root = out_dir / "checkpoints"
    ckpt_root.mkdir(parents=True, exist_ok=True)
    sc_cfg = load_spacecraft_config(args.spacecraft_config)
    sc_yaml_str = str(args.spacecraft_config)
    catalog = build_default_scenario_catalog()

    t_all = time.perf_counter()
    train_arms = list(_make_arm_configs().keys())
    multi_seed = len(train_seeds) > 1
    pending_train_jobs: list[tuple[str, int, int, int, str, str]] = []
    ckpt_paths_by_tseed: dict[int, dict[str, str]] = {ts: {} for ts in train_seeds}
    policy_hashes: dict[str, str] = {}
    train_times: dict[str, float] = {}
    for tseed in train_seeds:
        for i, arm in enumerate(train_arms):
            cdir = ckpt_root / arm / f"seed_{tseed}" if multi_seed else ckpt_root / arm
            ckpt_paths_by_tseed[tseed][arm] = str(cdir)
            weights_path = Path(cdir) / "policy_weights.npz"
            meta_path = Path(cdir) / "policy_meta.json"
            if args.resume and weights_path.exists() and meta_path.exists():
                meta_json = json.loads(meta_path.read_text(encoding="utf-8"))
                w_hash = str(meta_json["weights_sha256"])
                key = f"{arm}_seed_{tseed}" if multi_seed else arm
                policy_hashes[key] = w_hash
                train_times[key] = 0.0
                print(
                    f"  Reused {arm} (train_seed={tseed}): hash={w_hash[:12]}",
                    flush=True,
                )
            else:
                pending_train_jobs.append(
                    (arm, args.train_steps, tseed, tseed + i * 1000, str(cdir), sc_yaml_str)
                )

    if pending_train_jobs:
        train_workers = min(len(pending_train_jobs), args.train_workers or args.workers)
        print(
            f"[Phase 9] Training {len(pending_train_jobs)} SAC policies "
            f"({len(train_arms)} arms x {len(train_seeds)} train seeds, "
            f"{args.train_steps} steps each) on {sc_cfg.name} with {train_workers} workers...",
            flush=True,
        )
        with concurrent.futures.ProcessPoolExecutor(max_workers=train_workers) as ex:
            for arm_name, tseed, w_hash, wt, ep_rets in ex.map(
                _train_one_policy, pending_train_jobs
            ):
                key = f"{arm_name}_seed_{tseed}" if multi_seed else arm_name
                policy_hashes[key] = w_hash
                train_times[key] = wt
                last_ret = float(np.mean(ep_rets[-5:])) if ep_rets else float("nan")
                print(
                    f"  Trained {arm_name} (train_seed={tseed}): {wt:.1f}s "
                    f"| episodes={len(ep_rets)} | last5_ret={last_ret:.1f} | hash={w_hash[:12]}",
                    flush=True,
                )
    else:
        print(
            "[Phase 9] Reused all existing SAC checkpoints; skipping training.",
            flush=True,
        )

    # All evaluation arms: A0-A7 + A7_eso + 6 single-factor ablations = 15 arms
    eval_arms = [
        "A0_classical_lqr",
        "A1_classical_oracle_alloc",
        "A2_classical_dob_eso",
        "A3_strong_classical",
        "A4_unstructured_rl",
        "A5_rl_need_rho",
        "A6_rl_oracle_gate",
        "A7_ccr_v2_full",
        "A7_ccr_v2_eso",
        "Abl_A7_no_rho",
        "Abl_A7_no_alpha",
        "Abl_A7_no_G",
        "Abl_A7_no_supervisor",
        "Abl_A7_geom_G",
        "Abl_A7_clean_trained",
    ]

    # Evaluate across selected scenario splits (default: all val and held-out test scenarios)
    eval_scenarios: list[ScenarioSpec] = [
        s for s in catalog.values() if s.split in eval_splits
    ]
    seeds = [100 + i for i in range(args.n_seeds)]
    eval_jobs: list[tuple[str, str, int, int, dict[str, str], str]] = []
    for sc in eval_scenarios:
        for arm in eval_arms:
            # Deterministic classical baselines run once per (scenario, eval_seed)
            arm_tseeds = [train_seeds[0]] if arm in CLASSICAL_ARMS else train_seeds
            for tseed in arm_tseeds:
                ckpts = {} if arm in CLASSICAL_ARMS else ckpt_paths_by_tseed[tseed]
                for seed in seeds:
                    eval_jobs.append((arm, sc.scenario_id, seed, tseed, ckpts, sc_yaml_str))

    print(
        f"[Phase 9] Running {len(eval_jobs)} paired Monte Carlo episodes "
        f"({len(eval_scenarios)} scenarios x {len(seeds)} eval seeds, "
        f"train_seeds={train_seeds})...",
        flush=True,
    )
    t_eval = time.perf_counter()
    records: list[dict[str, Any]] = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as ex:
        for rec in ex.map(_eval_worker, eval_jobs):
            records.append(rec)
    eval_wall = time.perf_counter() - t_eval
    print(f"  Completed {len(records)} episodes in {eval_wall:.1f}s.", flush=True)

    df = pd.DataFrame(records)
    metrics_dir = out_dir / "metrics"
    analysis_dir = out_dir / "analysis"
    plots_dir = out_dir / "plots"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(metrics_dir / "raw_episodes.csv", index=False)

    # Separate overall, held-out test-only, controllable held-out, and per-scenario summaries
    df_test = df[df["split"] == "test"].copy()
    ref_mask = df_test["controller_arm"].isin(
        ["A1_classical_oracle_alloc", "A3_strong_classical"]
    )
    if ref_mask.any():
        ref_infeas = (
            df_test.loc[ref_mask]
            .groupby(["scenario_id", "seed"])["physically_infeasible"]
            .any()
        )
        pair_keys = pd.MultiIndex.from_frame(df_test[["scenario_id", "seed"]])
        df_test["physically_infeasible"] = (
            pair_keys.map(ref_infeas).fillna(df_test["physically_infeasible"]).astype(bool)
        )
        df_test["correct_infeasibility_response"] = (
            df_test["correct_infeasibility_response"].astype(bool)
            & df_test["physically_infeasible"]
        )
    df_test_ctrl = df_test[~df_test["physically_infeasible"]]
    summary_all = pd.DataFrame([r.to_dict() for r in summarize_arms(df)])
    summary_test = pd.DataFrame([r.to_dict() for r in summarize_arms(df_test)])
    summary_test_ctrl = pd.DataFrame([r.to_dict() for r in summarize_arms(df_test_ctrl)])
    summary_by_cat = pd.DataFrame(
        [r.to_dict() for r in summarize_arms(df_test, group_col="category")]
    )
    failure_breakdown = pd.DataFrame(summarize_failure_breakdown(df_test))

    summary_all.to_csv(analysis_dir / "summary_all_splits.csv", index=False)
    summary_test.to_csv(analysis_dir / "summary_heldout_test.csv", index=False)
    summary_test_ctrl.to_csv(analysis_dir / "summary_heldout_controllable.csv", index=False)
    summary_by_cat.to_csv(analysis_dir / "summary_test_by_category.csv", index=False)
    failure_breakdown.to_csv(analysis_dir / "failure_breakdown_heldout.csv", index=False)

    if multi_seed:
        summary_by_tseed = pd.DataFrame(
            [r.to_dict() for r in summarize_arms(df_test, group_col="train_seed")]
        )
        summary_by_tseed.to_csv(analysis_dir / "summary_by_train_seed.csv", index=False)
        if not df_test_ctrl.empty:
            summary_ctrl_by_tseed = pd.DataFrame(
                [r.to_dict() for r in summarize_arms(df_test_ctrl, group_col="train_seed")]
            )
            summary_ctrl_by_tseed.to_csv(
                analysis_dir / "summary_controllable_by_train_seed.csv", index=False
            )

    # Paired bootstrap statistical comparisons (Holm-Bonferroni corrected, no pseudoreplication)
    paired_abl_vs_a7 = _save_paired_comparisons(
        df_test, eval_arms, analysis_dir, prefix="paired_test"
    )
    _save_paired_comparisons(
        df_test_ctrl, eval_arms, analysis_dir, prefix="paired_test_controllable"
    )

    # Record detailed traces on held-out S8 combined fault for Plots 1-8
    trace_scenario = catalog["S8_combined_rw_sensor_test"]
    policies_loaded = {
        k: TorchMLPResidualPolicy.load(v) for k, v in ckpt_paths_by_tseed[train_seeds[0]].items()
    }
    runner = EpisodeRunner(sc_cfg)
    trace_arms = [
        "A0_classical_lqr",
        "A2_classical_dob_eso",
        "A3_strong_classical",
        "A4_unstructured_rl",
        "A7_ccr_v2_full",
        "A7_ccr_v2_eso",
    ]
    trace_logs = {}
    for arm in trace_arms:
        ctrl, use_ora = _build_eval_controller(arm, sc_cfg, policies_loaded)
        trace_logs[arm] = runner.run_episode(
            ctrl, trace_scenario, seed=seeds[0], use_oracle_capability=use_ora, record_trace=True
        )

    plots = generate_all_required_plots(
        df=df_test,
        trace_logs=trace_logs,
        trace_scenario=trace_scenario,
        ablation_comparisons=paired_abl_vs_a7,
        out_dir=plots_dir,
        rw_tau_limit_nm=sc_cfg.reaction_wheels.torque_limit_nominal_nm,
        rw_h_limit_nms=sc_cfg.reaction_wheels.effective_momentum_limit_nms,
    )
    print(f"[Phase 9] Generated {len(plots)} protocol plots in {plots_dir}", flush=True)

    # Phase 10 CPU latency & memory profile
    print(
        "[Phase 10] Profiling CPU inference, control cycle latency, and memory...",
        flush=True,
    )
    cpu_profile = profile_control_stack_cpu(
        sc_cfg, policies_loaded["A7_ccr_v2_full"], n_steps=500
    )
    (analysis_dir / "cpu_profile.json").write_text(
        json.dumps(cpu_profile, indent=2), encoding="utf-8"
    )

    # Write immutable experiment manifest.json
    exp_cfg_snapshot = {
        "train_steps": args.train_steps,
        "train_seed": train_seeds[0],
        "train_seeds": train_seeds,
        "n_seeds": args.n_seeds,
        "eval_seeds": seeds,
        "eval_splits": sorted(eval_splits),
        "eval_arms": eval_arms,
        "eval_scenarios": [s.scenario_id for s in eval_scenarios],
        "spacecraft_config_hash": sc_cfg.raw_hash,
    }
    meta = capture_run_metadata(sha256_canonical(exp_cfg_snapshot), cwd=REPO_ROOT)
    manifest = {
        "experiment_id": out_dir.name,
        "description": "CCR v2 paired benchmark, ablations, and CPU profiling across S0-S8",
        "metric_schema_version": METRIC_SCHEMA_VERSION,
        "backend": "fast_rk4",
        "basilisk_cross_validation": (
            "VALIDATED_GATE_C6_8_REGIME "
            "(bsk 2.12.2, plant_att=0.0086 deg, 600s_att=0.2870 deg, 8/8 regimes)"
        ),
        "policy_hashes": policy_hashes,
        "train_times_s": train_times,
        "eval_wall_time_s": eval_wall,
        "total_wall_time_s": time.perf_counter() - t_all,
        "config": exp_cfg_snapshot,
        "run_metadata": meta.to_dict(),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Print concise summary table to stdout
    print("\n=== HELD-OUT TEST SPLIT SUMMARY (S0-S8) ===")
    cols = [
        "arm",
        "rms_mean_deg",
        "rms_median_deg",
        "loc_rate_pct",
        "recovery_time_median_s",
        "effort_mean_nms",
        "mean_rl_torque_nm",
    ]
    print(summary_test[cols].to_string(index=False))
    print("\n=== CPU PROFILE (5 Hz = 200 ms budget) ===")
    for comp in cpu_profile["components"]:
        print(
            f"  {comp['component']:28s} mean={comp['mean_ms']:.3f} ms "
            f"p99={comp['p99_ms']:.3f} ms max={comp['max_ms']:.3f} ms"
        )
    print(
        f"  Total onboard mean util: {cpu_profile['budget_utilization_pct_mean']:.3f}% "
        f"| p99 util: {cpu_profile['budget_utilization_pct_p99']:.3f}% "
        f"| MLP weights (fp32): {cpu_profile['mlp_weights_float32_kb']:.2f} KB"
    )
    print(f"Done in {time.perf_counter() - t_all:.1f}s.")


if __name__ == "__main__":
    main()
