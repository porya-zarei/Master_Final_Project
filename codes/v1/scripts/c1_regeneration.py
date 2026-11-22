"""C1 - truth/regeneration of the classical (LQR) baselines on the corrected time base.

WHY
---
The pre-fix `simulate.py` advanced the LABELLED time axis by ``1/control_hz`` while the
integrator only advanced ``nctrl*dt`` seconds of physics.  With the old
``simulation.yaml`` (control_hz = 4, dt = 0.1)::

    nctrl = max(1, round(0.25/0.1)) = 2      # 2 x 0.1 = 0.2 s of physics ...
    t    += 1/control_hz = 0.25 s            # ... per 0.25 s of labelled time

so a "900 s" episode integrated only ``900 * 0.2/0.25 = 720 s`` of real dynamics and
every reported settling time was stretched by ``0.25/0.2 = 1.25x``.  The fix sets the
axis to ``nctrl*dt`` (= 0.2 s, a true 5 Hz loop), so labelled time == simulated time.

The physics, the controller and the estimator are otherwise IDENTICAL, and both
variants consume the random numbers in the same order -- therefore a legacy run is
exactly the corrected run truncated at 720 s of physics with a 1.25x-relabelled axis.
This is verified, not assumed (see ``--selfcheck`` and the printed ``physics_s``).

WHAT THIS SCRIPT DOES (C1.1 / C1.2 / C1.3)
------------------------------------------
1. Regenerates M1 (LQR nadir acquisition) and Phase 1B (RW faults) on the corrected
   base, with the SAME seeds and the SAME n as the archived pre-fix runs, so the
   before/after comparison is paired.
2. Re-runs those identical seeds with the pre-fix time handling (``--legacy-ab``) and
   reports the paired difference explicitly (per-seed settling ratio, 2x2 success
   table).  No hard-coded expectation is baked into the code.
3. Measures episodes/s (1 core and N cores) and RL-rollout throughput for MC sizing.

EXPECTATION, STATED BEFORE RUNNING (plan SS C1)
-----------------------------------------------
* Settling times should shrink by ~20% (x0.8) on the corrected axis.
* Success rate is threshold-based and is NOT automatically expected to move; the
  corrected base additionally integrates 900 s instead of 720 s, which can only ADD
  settling opportunity.  Any change in success rate is measured here and explained
  separately -- it is never attributed to "the fix" without the measurement.

Usage (from ``codes/``)::

    python scripts/c1_regeneration.py --mode selfcheck
    python scripts/c1_regeneration.py --mode both --legacy-ab --n_m1 60 --n_fault 30
    python scripts/c1_regeneration.py --mode throughput
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from satellite_adcs.config import load_config
from satellite_adcs.dynamics import SpacecraftDynamics
from satellite_adcs.sensors import SensorSuite
from satellite_adcs.estimation import MEKF
from satellite_adcs.controllers import ADCSController
import simulate

# ---------------------------------------------------------------- constants
LEGACY_CONTROL_HZ = 4.0          # simulation.yaml value BEFORE the time-base correction
HOLDS = (10.0, 30.0)             # settling-hold candidates
#   The RL-vs-LQR evaluator used hold=10 s for the RL side but hold=30 s (the
#   simulate.settling_time default) for the LQR side -- an apples-to-oranges
#   criterion.  Both are computed here so the discrepancy is visible and removable.
SETTLE_DEG = 1.0

CASES = {
    "healthy":      [1.0, 1.0, 1.0],   # C1.1 -- M1 protocol,     n = --n_m1
    "healthy_30ic": [1.0, 1.0, 1.0],   # C1.2 -- Phase-1B protocol, n = --n_fault
    "rw1_50pct":    [0.5, 1.0, 1.0],
    "rw1_failed":   [0.0, 1.0, 1.0],
}

_CFG = None


def _cfg():
    global _CFG
    if _CFG is None:
        _CFG = load_config()
    return _CFG


# ---------------------------------------------------------------- simulation
def rollout(cfg, seed, T, rw_health=None, legacy=False, momentum_mgmt=True):
    """One closed-loop LQR episode.

    ``legacy=True`` reproduces the PRE-FIX time handling exactly:
    the integrator still takes ``nctrl = round((1/4)/dt)`` substeps but the labelled
    axis advances by ``1/4`` s, so labelled time outstrips simulated time by 1.25x.
    """
    sim = cfg["simulation"]
    dt = float(sim["dt_s"])
    if legacy:
        label_period = 1.0 / LEGACY_CONTROL_HZ
        nctrl = max(1, int(round(label_period / dt)))
    else:
        nctrl = max(1, int(round((1.0 / float(sim["control_hz"])) / dt)))
        label_period = nctrl * dt

    rng = np.random.default_rng(seed)
    dyn = SpacecraftDynamics(cfg, rng)
    sensors = SensorSuite(cfg, rng)
    est = MEKF(cfg)
    ctrl = ADCSController(cfg, dyn.J, dyn.mu, dyn.a, rng)
    ctrl.momentum_mgmt = momentum_mgmt
    dyn.reset()
    if rw_health is not None:
        dyn.set_rw_health(rw_health)
    w0_deg = float(np.degrees(np.linalg.norm(dyn.omega)))
    est.q_hat = np.array([1.0, 0, 0, 0])
    est.P = np.eye(3) * 1e-2

    t = 0.0
    t_arr, pe, ow = [], [], []
    n_iter = 0
    while t < T:
        meas = sensors.measure(dyn)
        est.update(meas, dyn)
        tau_rw, m = ctrl.control(meas, est, dyn, t, label_period)
        for _ in range(nctrl):
            dyn.step(dt, tau_rw, m)
            est.propagate(meas["gyro"], dt)
        t += label_period
        n_iter += 1
        t_arr.append(t)
        pe.append(simulate.pointing_error_deg(dyn))
        ow.append(float(np.max(np.abs(dyn.omega_w))))

    return dict(t=np.asarray(t_arr), pe=np.asarray(pe), ow=np.asarray(ow),
                n_iter=n_iter, nctrl=nctrl,
                physics_s=float(n_iter * nctrl * dt), label_s=float(t),
                w0_deg=w0_deg)


def episode_metrics(res):
    """All C1 metrics for one episode, reported SEPARATELY (never a single blend)."""
    t, pe = res["t"], res["pe"]
    m = {
        "w0_deg": round(res["w0_deg"], 3),
        "n_iter": int(res["n_iter"]),
        "physics_s": round(res["physics_s"], 2),
        "label_s": round(res["label_s"], 2),
        "final_pe_deg": round(float(pe[-1]), 4),
        "rms_pe_deg": round(float(np.sqrt(np.mean(pe ** 2))), 4),
        "max_pe_deg": round(float(pe.max()), 4),
        "wheel_max_rad_s": round(float(res["ow"].max()), 2),
    }
    for h in HOLDS:
        st = simulate.settling_time(t, pe, threshold=SETTLE_DEG, hold=h)
        m[f"settle_h{int(h)}_s"] = None if np.isinf(st) else round(float(st), 2)
    return m


def aggregate(rows):
    """Aggregate per-episode metric rows into the C1 report block."""
    n = len(rows)
    agg = {"n": n}
    for h in HOLDS:
        key = f"settle_h{int(h)}_s"
        ok = [r[key] is not None for r in rows]
        settled = np.array([r[key] for r in rows if r[key] is not None], float)
        blk = {
            "success_n": int(sum(ok)),
            "success_pct": round(100.0 * sum(ok) / n, 2) if n else None,
            "n_settled": int(settled.size),
        }
        if settled.size:
            blk.update({
                "settle_mean_s": round(float(settled.mean()), 2),
                "settle_median_s": round(float(np.median(settled)), 2),
                "settle_p90_s": round(float(np.percentile(settled, 90)), 2),
                "settle_p95_s": round(float(np.percentile(settled, 95)), 2),
                "settle_min_s": round(float(settled.min()), 2),
                "settle_max_s": round(float(settled.max()), 2),
            })
        else:
            blk.update({k: None for k in ("settle_mean_s", "settle_median_s",
                                          "settle_p90_s", "settle_p95_s",
                                          "settle_min_s", "settle_max_s")})
        agg[f"hold{int(h)}_s"] = blk

    for name, key in (("final_pe_deg", "final_pe_deg"),
                      ("rms_pe_deg", "rms_pe_deg"),
                      ("max_pe_deg", "max_pe_deg")):
        v = np.array([r[key] for r in rows], float)
        agg[name] = {
            "mean": round(float(v.mean()), 4),
            "median": round(float(np.median(v)), 4),
            "p95": round(float(np.percentile(v, 95)), 4),
            "max": round(float(v.max()), 4),
        }
    ps = np.array([r["physics_s"] for r in rows], float)
    agg["physics_s"] = {"mean": round(float(ps.mean()), 2),
                        "note": "true integrated duration per episode"}
    return agg


def paired_ab(fixed_rows, legacy_rows, case):
    """Paired before/after comparison on identical seeds."""
    out = {"case": case, "n_pairs": len(fixed_rows)}
    for h in HOLDS:
        key = f"settle_h{int(h)}_s"
        a = [r[key] for r in fixed_rows]
        b = [r[key] for r in legacy_rows]
        both = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
        only_fixed = sum(1 for x, y in zip(a, b) if x is not None and y is None)
        only_legacy = sum(1 for x, y in zip(a, b) if x is None and y is not None)
        neither = sum(1 for x, y in zip(a, b) if x is None and y is None)
        ratios = np.array([x / y for x, y in both], float) if both else np.array([])
        blk = {
            "success_fixed_n": int(sum(1 for x in a if x is not None)),
            "success_legacy_n": int(sum(1 for x in b if x is not None)),
            "settled_in_fixed_only": only_fixed,
            "settled_in_legacy_only": only_legacy,
            "settled_in_neither": neither,
            "n_both_settled": len(both),
        }
        if ratios.size:
            blk.update({
                "settle_ratio_fixed_over_legacy_mean": round(float(ratios.mean()), 4),
                "settle_ratio_fixed_over_legacy_median": round(float(np.median(ratios)), 4),
                "settle_ratio_expected": 0.8,
                "settle_ratio_min": round(float(ratios.min()), 4),
                "settle_ratio_max": round(float(ratios.max()), 4),
            })
        else:
            blk.update({k: None for k in ("settle_ratio_fixed_over_legacy_mean",
                                          "settle_ratio_fixed_over_legacy_median",
                                          "settle_ratio_expected",
                                          "settle_ratio_min", "settle_ratio_max")})
        out[f"hold{int(h)}_s"] = blk

    fa = np.array([r["final_pe_deg"] for r in fixed_rows], float)
    lb = np.array([r["final_pe_deg"] for r in legacy_rows], float)
    out["final_pe_deg"] = {
        "fixed_mean": round(float(fa.mean()), 4),
        "legacy_mean": round(float(lb.mean()), 4),
        "fixed_median": round(float(np.median(fa)), 4),
        "legacy_median": round(float(np.median(lb)), 4),
    }
    return out


# ---------------------------------------------------------------- workers
def _worker(job):
    case, seed, T, health, legacy = job
    res = rollout(_cfg(), seed, T, rw_health=health, legacy=legacy)
    # Return only the pe series (ndarray = buffer-pickled). `t` is deterministic from
    # the time base and `ow` is already reduced into `metrics`, so shipping them back
    # was 3x the payload for nothing -- the list version broke the pool under memory
    # pressure (this box runs ~2 GB free while training is in flight).
    return dict(case=case, seed=seed, legacy=legacy,
                metrics=episode_metrics(res), pe=res["pe"])


def run_cases(jobs, workers):
    out = []
    if workers <= 1:
        for j in jobs:
            out.append(_worker(j))
        return out
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(_worker, jobs, chunksize=1):
            out.append(r)
    return out


def _rows_by_case(results, case, legacy):
    rs = [r for r in results if r["case"] == case and r["legacy"] == legacy]
    rs.sort(key=lambda r: r["seed"])
    return [r["metrics"] for r in rs]


# ---------------------------------------------------------------- modes
def mode_regenerate(a):
    cfg = _cfg()
    workers = a.workers
    out_dir = a.out
    os.makedirs(out_dir, exist_ok=True)

    jobs = []
    # C1.1 - M1: LQR nadir acquisition, healthy wheels
    for s in range(a.n_m1):
        jobs.append(("healthy", s, a.T, list(CASES["healthy"]), False))
        if a.legacy_ab:
            jobs.append(("healthy", s, a.T, list(CASES["healthy"]), True))
    # C1.2 - Phase 1B: healthy + RW faults, all at the originally reported n (--n_fault)
    for case in ("healthy_30ic", "rw1_50pct", "rw1_failed"):
        for s in range(a.n_fault):
            jobs.append((case, s, a.T, list(CASES[case]), False))
            if a.legacy_ab:
                jobs.append((case, s, a.T, list(CASES[case]), True))

    print(f"[C1] {len(jobs)} episodes (T={a.T}s, legacy_ab={a.legacy_ab}, "
          f"workers={workers}) ...")
    t0 = time.perf_counter()
    results = run_cases(jobs, workers)
    wall = time.perf_counter() - t0
    print(f"[C1] done in {wall:.1f}s  ({len(results)/wall:.2f} episodes/s)")

    report = {"generated_by": "scripts/c1_regeneration.py",
              "T_s": a.T, "settle_threshold_deg": SETTLE_DEG, "holds_s": list(HOLDS),
              "wall_time_s": round(wall, 2), "cases": {}}

    for case in ("healthy", "healthy_30ic", "rw1_50pct", "rw1_failed"):
        fixed = _rows_by_case(results, case, False)
        if not fixed:
            continue
        blk = {"fixed": aggregate(fixed)}
        legacy = _rows_by_case(results, case, True)
        if legacy:
            blk["legacy"] = aggregate(legacy)
            blk["paired_ab"] = paired_ab(fixed, legacy, case)
        report["cases"][case] = blk

    with open(os.path.join(out_dir, "c1_regeneration.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    np.savez_compressed(
        os.path.join(out_dir, "pe_series.npz"),
        **{f"{r['case']}|{'legacy' if r['legacy'] else 'fixed'}|{r['seed']}": np.array(r["pe"])
           for r in results})

    # ---- console summary
    for case, blk in report["cases"].items():
        print(f"\n--- {case} ---")
        for variant in ("legacy", "fixed"):
            if variant not in blk:
                continue
            s = blk[variant]
            print(f"  {variant:6s} n={s['n']:3d}  "
                  f"hold10: success={s['hold10_s']['success_pct']:5.1f}% "
                  f"median={s['hold10_s']['settle_median_s']} p90={s['hold10_s']['settle_p90_s']} "
                  f"p95={s['hold10_s']['settle_p95_s']}  |  "
                  f"hold30: success={s['hold30_s']['success_pct']:5.1f}% "
                  f"median={s['hold30_s']['settle_median_s']}  |  "
                  f"final_pe mean={s['final_pe_deg']['mean']} median={s['final_pe_deg']['median']} "
                  f"p95={s['final_pe_deg']['p95']}  |  physics={s['physics_s']['mean']}s")
        if "paired_ab" in blk:
            p = blk["paired_ab"]
            print(f"  PAIRED: fixed-only-settled={p['hold10_s']['settled_in_fixed_only']} "
                  f"legacy-only-settled={p['hold10_s']['settled_in_legacy_only']}  "
                  f"settle_ratio(fixed/legacy) median="
                  f"{p['hold10_s']['settle_ratio_fixed_over_legacy_median']} "
                  f"(expected {p['hold10_s']['settle_ratio_expected']})")

    _figure(results, report, out_dir)
    print("\nsaved:", os.path.join(out_dir, "c1_regeneration.json"))
    return report


def _figure(results, report, out_dir):
    cases = [c for c in report["cases"]]
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.4))
    w = 0.35
    x = np.arange(len(cases))
    for k, (variant, color) in enumerate((("legacy", "tab:red"), ("fixed", "tab:blue"))):
        vals, err = [], []
        for c in cases:
            b = report["cases"][c].get(variant)
            vals.append(b["hold10_s"]["success_pct"] if b else np.nan)
            err.append(b["hold10_s"]["settle_median_s"] if b and b["hold10_s"]["settle_median_s"] else np.nan)
        ax[0].bar(x + (k - 0.5) * w, vals, w, label=variant, color=color)
        ax[1].bar(x + (k - 0.5) * w, err, w, label=variant, color=color)
        fe = [report["cases"][c].get(variant, {})
              .get("final_pe_deg", {}).get("mean", np.nan) for c in cases]
        ax[2].bar(x + (k - 0.5) * w, fe, w, label=variant, color=color)
    for a_, t in zip(ax, ("success rate [%] (hold 10s)", "median settling time [s]",
                          "final pointing error [deg]")):
        a_.set_xticks(x); a_.set_xticklabels(cases, rotation=12)
        a_.set_title(t); a_.grid(alpha=0.3); a_.legend()
    fig.suptitle(f"C1 - LQR baselines: pre-fix (legacy) vs corrected time base, T={report['T_s']}s")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "c1_summary.png"), dpi=120)
    plt.close(fig)


def mode_selfcheck(a):
    """Verify the rollout replica is faithful AND that the legacy variant really is
    the corrected one truncated at 720 s with a 1.25x-relabelled axis."""
    cfg = _cfg()
    print("[selfcheck] replica vs simulate.run_episode (fixed time base)")
    for seed in (0, 7):
        ref = simulate.run_episode(cfg, seed=seed, T=a.T)
        mine = rollout(cfg, seed=seed, T=a.T)
        d = float(np.max(np.abs(ref["pe"] - mine["pe"])))
        print(f"  seed={seed}: len {len(ref['pe'])} vs {len(mine['pe'])}  "
              f"max|dpe|={d:.3e}  {'OK' if d == 0.0 and len(ref['pe']) == len(mine['pe']) else 'MISMATCH'}")
    print("\n[selfcheck] legacy vs fixed physics/label accounting")
    for seed in (0,):
        fx = rollout(cfg, seed=seed, T=a.T)
        lg = rollout(cfg, seed=seed, T=a.T, legacy=True)
        n_trunc = int(round(lg["physics_s"] / (fx["nctrl"] * float(cfg["simulation"]["dt_s"]))))
        d = float(np.max(np.abs(fx["pe"][:n_trunc] - lg["pe"][:n_trunc])))
        print(f"  fixed : n_iter={fx['n_iter']} physics={fx['physics_s']:.1f}s label={fx['label_s']:.1f}s")
        print(f"  legacy: n_iter={lg['n_iter']} physics={lg['physics_s']:.1f}s label={lg['label_s']:.1f}s")
        print(f"  legacy physics / fixed physics = {lg['physics_s']/fx['physics_s']:.4f} "
              f"(expect 0.8 = labelled-time inflation 1.25x)")
        print(f"  max|dpe| over the first {n_trunc} legacy samples = {d:.3e} "
              f"({'bit-identical trajectory, pure relabel' if d == 0.0 else 'DIFFERS'})")


def mode_throughput(a):
    """C1.3 - measure evaluation throughput so Monte-Carlo size N is sized from data."""
    cfg = _cfg()
    out = {"T_s": a.T, "n_episodes_per_point": a.n_tp}
    os.makedirs(a.out, exist_ok=True)

    # (1) classical single core
    t0 = time.perf_counter()
    for s in range(a.n_tp):
        rollout(cfg, s, a.T)
    dt1 = time.perf_counter() - t0
    out["classical_1core"] = {"episodes": a.n_tp, "wall_s": round(dt1, 3),
                              "episodes_per_s": round(a.n_tp / dt1, 3),
                              "steps_per_s": round(a.n_tp * (a.T / 0.2) / dt1, 1)}
    print(f"[throughput] classical  1 core : {a.n_tp/dt1:.2f} ep/s "
          f"({out['classical_1core']['steps_per_s']:.0f} control-steps/s)")

    # (2) classical multi core
    for nw in [w for w in (4, 8, 16, 20) if w <= (a.workers or 20)]:
        jobs = [(("healthy"), s, a.T, list(CASES["healthy"]), False) for s in range(a.n_tp * nw)]
        t0 = time.perf_counter()
        run_cases(jobs, nw)
        dt = time.perf_counter() - t0
        out[f"classical_{nw}core"] = {"episodes": len(jobs), "wall_s": round(dt, 3),
                                      "episodes_per_s": round(len(jobs) / dt, 3),
                                      "scaling_vs_1core": round((len(jobs) / dt) / (a.n_tp / dt1), 2)}
        print(f"[throughput] classical {nw:2d} core : {len(jobs)/dt:.2f} ep/s "
              f"(x{(len(jobs)/dt)/(a.n_tp/dt1):.1f} vs 1 core)")

    # (3) RL policy rollouts
    if os.path.exists(a.rl_model):
        from satellite_adcs.environment.adcs_env import ADCSEnv
        from stable_baselines3 import PPO
        from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
        model = PPO.load(a.rl_model, device="cpu")
        vn_path = os.path.join(os.path.dirname(a.rl_model), "vecnormalize.pkl")
        vecnorm = VecNormalize.load(vn_path, DummyVecEnv([lambda: ADCSEnv()])) \
            if os.path.exists(vn_path) else None
        env = ADCSEnv(fault_mode="none", episode_time=a.T, seed=0)
        t0 = time.perf_counter()
        n_steps = 0
        for ep in range(a.n_tp):
            env.reset(seed=ep)
            done = False
            while not done:
                o = env._obs()
                if vecnorm is not None:
                    vecnorm.training = False
                    o = np.clip((o - vecnorm.obs_rms.mean) /
                                np.sqrt(vecnorm.obs_rms.var + 1e-8), -10, 10)
                act, _ = model.predict(o, deterministic=True)
                _, _, term, trunc, _ = env.step(act)
                done = term or trunc
                n_steps += 1
        dt = time.perf_counter() - t0
        env.close()
        out["rl_1core"] = {"episodes": a.n_tp, "control_steps": n_steps,
                           "wall_s": round(dt, 3), "episodes_per_s": round(a.n_tp / dt, 3),
                           "steps_per_s": round(n_steps / dt, 1),
                           "model": a.rl_model}
        print(f"[throughput] RL policy 1 core : {a.n_tp/dt:.2f} ep/s ({n_steps/dt:.0f} steps/s)")
    else:
        print(f"[throughput] RL model not found ({a.rl_model}) - skipped")

    with open(os.path.join(a.out, "c1_throughput.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\nsaved:", os.path.join(a.out, "c1_throughput.json"))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", default="both",
                   choices=["m1", "fault", "both", "throughput", "selfcheck"])
    p.add_argument("--T", type=float, default=900.0)
    p.add_argument("--n_m1", type=int, default=60, help="M1 seeds (archived run used 60)")
    p.add_argument("--n_fault", type=int, default=30, help="Phase 1B seeds (archived run used 30)")
    p.add_argument("--workers", type=int, default=20)
    p.add_argument("--legacy-ab", action="store_true",
                   help="also re-run the SAME seeds with the pre-fix time base")
    p.add_argument("--out", default="results/c1_regeneration")
    p.add_argument("--n_tp", type=int, default=3, help="episodes per throughput point")
    p.add_argument("--rl_model", default="results/rl_shaped/ppo_adcs.zip")
    a = p.parse_args()

    if a.mode == "selfcheck":
        mode_selfcheck(a)
    elif a.mode == "throughput":
        mode_throughput(a)
    elif a.mode == "m1":
        a.n_fault = 0
        mode_regenerate(a)
    elif a.mode == "fault":
        a.n_m1 = 0
        mode_regenerate(a)
    else:
        mode_regenerate(a)


if __name__ == "__main__":
    main()
