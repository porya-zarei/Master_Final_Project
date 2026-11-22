"""C4.1 - attribution of the Phase-B (reward-shaping) improvement.

QUESTION
--------
Between the 1M "classic" run (stuck at ~4 deg) and the 2M winning run
(`results/rl_shaped`, 0.17 deg) FIVE things changed at once.  Which one actually
produced the gain?  C4.1 answers that BEFORE any Reward-v2 work is attempted.

METHOD - one-factor-at-a-time (OFAT), reverted FROM THE WINNER
-------------------------------------------------------------
Each arm starts from the winning configuration and reverts exactly ONE factor.
Everything else (seed=0, n_envs=8, PPO hyper-parameters, fault randomisation
health in [0.5, 1.0], network) is held fixed.

  arm          factor reverted                      value in arm
  -----------  -----------------------------------  -----------------------
  BASE         (none - the winner as trained)       bonus | norm=0 | 5 Hz | 900 s | 2M
  A1_shape     reward shaping                       quad  | norm=0 | 5 Hz | 900 s | 2M
  A2_norm      reward normalisation                 bonus | norm=1 | 5 Hz | 900 s | 2M
  A3_rate      control rate                        bonus | norm=0 | 2 Hz | 900 s | 2M
  A4_horizon   training horizon                    bonus | norm=0 | 5 Hz | 300 s | 2M
  A5_budget    training budget                     bonus | norm=0 | 5 Hz | 900 s | 1M

WHY TASK METRICS, NOT REWARD
----------------------------
The arms do not share a reward function (A1 drops the tolerance bonus, A2 divides
the reward by a running std), so episode RETURN is not comparable across arms and
is never used as the yardstick.  All arms are scored on the same task metrics:
success rate (settling < 1 deg), final pointing error, RMS pointing error,
measured on identical initial conditions (seeds 0..n-1).

PROTOCOL
--------
* Primary: every arm is evaluated on the COMMON TARGET TASK - 5 Hz control,
  900 s horizon, the three fault cases - so the comparison is apples-to-apples.
* A3 is additionally evaluated IN-DISTRIBUTION (2 Hz) because a policy trained at
  the wrong control rate is off-distribution when deployed at the right one; both
  numbers are reported.
* n=24 seeds by default (wider than the n=8 headline, so the ranking is not noise).

Usage (from ``codes/``)::

    python scripts/c4_1_attribution.py train --arm A1_shape
    python scripts/c4_1_attribution.py train --all
    python scripts/c4_1_attribution.py eval --n 24
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from satellite_adcs.environment.adcs_env import ADCSEnv
import simulate

TARGET_HZ = 5.0
TARGET_T = 900.0
SETTLE_DEG = 1.0
HOLDS = (10.0, 30.0)
CASES = {
    "healthy":    [1.0, 1.0, 1.0],
    "rw1_50pct":  [0.5, 1.0, 1.0],
    "rw1_failed": [0.0, 1.0, 1.0],
}

ARMS = {
    "BASE":       dict(factor="none (winner as trained, results/rl_shaped)",
                       model="results/rl_shaped", retrain=False),
    "A1_shape":   dict(factor="reward shaping (bonus -> quad)",
                       reward_shape="quad", steps=2_000_000),
    "A2_norm":    dict(factor="reward normalisation (off -> on)",
                       norm_reward=1, steps=2_000_000),
    "A3_rate":    dict(factor="control rate (5 Hz -> 2 Hz)",
                       control_hz=2.0, steps=2_000_000),
    "A4_horizon": dict(factor="training horizon (900 s -> 300 s)",
                       episode_time=300.0, steps=2_000_000),
    "A5_budget":  dict(factor="step budget (2M -> 1M)",
                       steps=1_000_000),
}


# ---------------------------------------------------------------- metrics
def metrics_from_pe(t, pe):
    m = {"final_pe_deg": round(float(pe[-1]), 4),
         "rms_pe_deg": round(float(np.sqrt(np.mean(pe ** 2))), 4),
         "max_pe_deg": round(float(pe.max()), 4)}
    for h in HOLDS:
        st = simulate.settling_time(t, pe, threshold=SETTLE_DEG, hold=h)
        m[f"settle_h{int(h)}_s"] = None if np.isinf(st) else round(float(st), 2)
    return m


def aggregate(rows):
    n = len(rows)
    agg = {"n": n}
    for h in HOLDS:
        key = f"settle_h{int(h)}_s"
        ok = [r[key] is not None for r in rows]
        settled = np.array([r[key] for r in rows if r[key] is not None], float)
        agg[f"hold{int(h)}_s"] = {
            "success_n": int(sum(ok)),
            "success_pct": round(100.0 * sum(ok) / n, 2) if n else None,
            "settle_median_s": round(float(np.median(settled)), 2) if settled.size else None,
            "settle_p90_s": round(float(np.percentile(settled, 90)), 2) if settled.size else None,
        }
    fin = np.array([r["final_pe_deg"] for r in rows], float)
    rms = np.array([r["rms_pe_deg"] for r in rows], float)
    agg["final_pe_deg"] = {"mean": round(float(fin.mean()), 4),
                           "median": round(float(np.median(fin)), 4),
                           "p95": round(float(np.percentile(fin, 95)), 4),
                           "max": round(float(fin.max()), 4)}
    agg["rms_pe_deg"] = {"mean": round(float(rms.mean()), 4),
                         "max": round(float(rms.max()), 4)}
    return agg


# ---------------------------------------------------------------- RL rollout
def rollout_rl(model, vecnorm, health, n, episode_time, control_hz, seed0=0):
    env = ADCSEnv(fault_mode="none", episode_time=episode_time,
                  control_hz=control_hz, seed=0)
    rows = []
    for ep in range(n):
        env.reset(seed=seed0 + ep)
        env.dyn.set_rw_health(np.asarray(health, dtype=float))
        if vecnorm is not None:
            vecnorm.training = False
        pe, done = [], False
        while not done:
            o = env._obs()
            if vecnorm is not None:
                o = np.clip((o - vecnorm.obs_rms.mean) /
                            np.sqrt(vecnorm.obs_rms.var + 1e-8), -10, 10)
            act, _ = model.predict(o, deterministic=True)
            _, _, term, trunc, info = env.step(act)
            pe.append(info["pointing_error_deg"])
            done = term or trunc
        pe = np.array(pe)
        t = np.arange(1, len(pe) + 1) * env.control_period
        rows.append(metrics_from_pe(t, pe))
    env.close()
    return rows


def load_arm(arm, out_root):
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    spec = ARMS[arm]
    if spec.get("retrain", True) is False:
        d = spec["model"]
    else:
        d = os.path.join(out_root, arm)
    mp = os.path.join(d, "ppo_adcs.zip")
    if not os.path.exists(mp):
        return None, None, d
    model = PPO.load(mp, device="cpu")
    vp = os.path.join(d, "vecnormalize.pkl")
    vecnorm = VecNormalize.load(vp, DummyVecEnv([lambda: ADCSEnv()])) \
        if os.path.exists(vp) else None
    return model, vecnorm, d


# ---------------------------------------------------------------- train
def train_cmd(arm, a):
    spec = ARMS[arm]
    cmd = [sys.executable, os.path.join("scripts", "train_rl.py"),
           "--algo", "ppo", "--steps", str(spec.get("steps", 2_000_000)),
           "--n_envs", str(a.n_envs), "--seed", str(a.seed),
           "--device", a.device,
           "--control_hz", str(spec.get("control_hz", TARGET_HZ)),
           "--episode_time", str(spec.get("episode_time", TARGET_T)),
           "--norm_reward", str(spec.get("norm_reward", 0)),
           "--out", os.path.join(a.out, arm)]
    if spec.get("reward_shape"):
        cmd += ["--reward_shape", spec["reward_shape"]]
    return cmd


def mode_train(a):
    arms = list(ARMS) if a.all else [a.arm]
    for arm in arms:
        spec = ARMS[arm]
        if spec.get("retrain", True) is False:
            print(f"[train] {arm}: skip (fixed artifact {spec['model']})")
            continue
        out = os.path.join(a.out, arm)
        os.makedirs(out, exist_ok=True)
        cmd = train_cmd(arm, a)
        log = os.path.join(out, "train.log")
        print(f"[train] {arm}: {spec['factor']}")
        print("        " + " ".join(cmd))
        t0 = time.perf_counter()
        with open(log, "w", encoding="utf-8") as f:
            p = subprocess.run(cmd, cwd=_ROOT, stdout=f, stderr=subprocess.STDOUT)
        dt = time.perf_counter() - t0
        print(f"[train] {arm}: exit={p.returncode}  wall={dt/60:.1f} min  log={log}")
        if p.returncode != 0:
            print(f"[train] {arm}: FAILED - see {log}")
            return 1
    return 0


# ---------------------------------------------------------------- eval
def mode_eval(a):
    out_root = a.out
    report = {"target": {"control_hz": TARGET_HZ, "episode_time_s": TARGET_T,
                         "settle_threshold_deg": SETTLE_DEG, "holds_s": list(HOLDS),
                         "n_seeds": a.n},
              "arms": {}, "config": {k: {kk: vv for kk, vv in v.items()}
                                     for k, v in ARMS.items()}}
    raw = {}
    for arm in ARMS:
        model, vecnorm, d = load_arm(arm, out_root)
        if model is None:
            print(f"[eval] {arm}: model missing ({d}) - skipped")
            continue
        print(f"[eval] {arm}: {ARMS[arm]['factor']}")
        blk = {"factor": ARMS[arm]["factor"], "dir": d, "cases": {}}
        for name, health in CASES.items():
            rows = rollout_rl(model, vecnorm, health, a.n, TARGET_T, TARGET_HZ)
            blk["cases"][name] = aggregate(rows)
            raw[f"{arm}|{name}|target"] = rows
            c = blk["cases"][name]
            print(f"        {name:11s} success(h10)={c['hold10_s']['success_pct']:5.1f}%  "
                  f"success(h30)={c['hold30_s']['success_pct']:5.1f}%  "
                  f"final_pe={c['final_pe_deg']['mean']:7.3f}deg  rms={c['rms_pe_deg']['mean']:7.3f}")
        # in-distribution check for the control-rate arm
        if ARMS[arm].get("control_hz"):
            hz = float(ARMS[arm]["control_hz"])
            idist = {}
            for name, health in CASES.items():
                rows = rollout_rl(model, vecnorm, health, a.n, TARGET_T, hz)
                idist[name] = aggregate(rows)
                raw[f"{arm}|{name}|indist"] = rows
            blk["in_distribution"] = {"control_hz": hz, "cases": idist}
            print(f"        [in-distribution {hz} Hz] healthy="
                  f"{idist['healthy']['hold10_s']['success_pct']:.1f}%/"
                  f"{idist['healthy']['final_pe_deg']['mean']:.3f}deg  "
                  f"rw1_50pct={idist['rw1_50pct']['hold10_s']['success_pct']:.1f}%/"
                  f"{idist['rw1_50pct']['final_pe_deg']['mean']:.3f}deg")
        report["arms"][arm] = blk

    # ---------------- attribution summary
    base = report["arms"].get("BASE")
    attr = {}
    if base:
        for arm, blk in report["arms"].items():
            if arm == "BASE":
                continue
            row = {"factor_reverted": blk["factor"]}
            for name in CASES:
                b = base["cases"][name]
                c = blk["cases"][name]
                row[name] = {
                    "success_h10_delta_pp": round(
                        (c["hold10_s"]["success_pct"] or 0) -
                        (b["hold10_s"]["success_pct"] or 0), 2),
                    "final_pe_delta_deg": round(
                        c["final_pe_deg"]["mean"] - b["final_pe_deg"]["mean"], 4),
                    "rms_pe_delta_deg": round(
                        c["rms_pe_deg"]["mean"] - b["rms_pe_deg"]["mean"], 4),
                }
            # cost of removing this factor on the two discriminating cases
            row["removal_cost"] = {
                "success_h10_delta_pp_sum(healthy,rw1_50pct)": round(
                    row["healthy"]["success_h10_delta_pp"] +
                    row["rw1_50pct"]["success_h10_delta_pp"], 2),
                "final_pe_delta_deg_sum(healthy,rw1_50pct)": round(
                    row["healthy"]["final_pe_delta_deg"] +
                    row["rw1_50pct"]["final_pe_delta_deg"], 4),
            }
            attr[arm] = row
        report["attribution"] = {
            "note": "deltas are (arm - BASE); negative success delta = removing the "
                    "factor hurt; positive final_pe delta = removing it degraded precision",
            "per_arm": attr,
        }

    os.makedirs(out_root, exist_ok=True)
    with open(os.path.join(out_root, "c4_1_attribution.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    np.savez_compressed(os.path.join(out_root, "c4_1_raw.npz"),
                        **{k.replace("|", "__"): np.array([r.get("final_pe_deg", np.nan)
                                                           for r in v]) for k, v in raw.items()})
    _table(report, out_root)
    _figure(report, out_root)
    print("\nsaved:", os.path.join(out_root, "c4_1_attribution.json"))
    return 0


def _table(report, out_root):
    arms = list(report["arms"])
    lines = ["# C4.1 - attribution of the Phase-B improvement", "",
             f"Target: {TARGET_HZ} Hz, {TARGET_T}s, n={report['target']['n_seeds']} seeds "
             f"(identical ICs across arms); settle < {SETTLE_DEG} deg",
             "Reward returns are NOT comparable across arms (different reward functions);",
             "all arms are scored on task metrics only.", "",
             "| arm | factor reverted | healthy succ(h10) | healthy succ(h30) | healthy final_pe | "
             "rw1_50pct succ(h10) | rw1_50pct final_pe | rw1_failed succ(h10) | rw1_failed final_pe |",
             "|---|---|---|---|---|---|---|---|---|"]
    for arm in arms:
        c = report["arms"][arm]["cases"]
        lines.append(
            f"| `{arm}` | {report['arms'][arm]['factor']} | "
            f"{c['healthy']['hold10_s']['success_pct']:.1f}% | "
            f"{c['healthy']['hold30_s']['success_pct']:.1f}% | "
            f"{c['healthy']['final_pe_deg']['mean']:.3f} | "
            f"{c['rw1_50pct']['hold10_s']['success_pct']:.1f}% | "
            f"{c['rw1_50pct']['final_pe_deg']['mean']:.3f} | "
            f"{c['rw1_failed']['hold10_s']['success_pct']:.1f}% | "
            f"{c['rw1_failed']['final_pe_deg']['mean']:.3f} |")
    lines.append("")
    if "attribution" in report:
        lines.append("## Removal cost (arm - BASE)")
        lines.append("")
        lines.append("| arm | factor reverted | d success(healthy) pp | d success(rw1_50pct) pp | "
                     "d final_pe(healthy) deg | d final_pe(rw1_50pct) deg |")
        lines.append("|---|---|---|---|---|---|")
        for arm, r in report["attribution"]["per_arm"].items():
            lines.append(f"| `{arm}` | {r['factor_reverted']} | "
                         f"{r['healthy']['success_h10_delta_pp']:+.1f} | "
                         f"{r['rw1_50pct']['success_h10_delta_pp']:+.1f} | "
                         f"{r['healthy']['final_pe_delta_deg']:+.3f} | "
                         f"{r['rw1_50pct']['final_pe_delta_deg']:+.3f} |")
    txt = "\n".join(lines) + "\n"
    with open(os.path.join(out_root, "c4_1_table.md"), "w", encoding="utf-8") as f:
        f.write(txt)
    print("\n" + txt)


def _figure(report, out_root):
    arms = list(report["arms"])
    cases = list(CASES)
    fig, ax = plt.subplots(1, 3, figsize=(17, 4.6))
    x = np.arange(len(arms))
    w = 0.26
    for k, (case, color) in enumerate(zip(cases, ("tab:green", "tab:orange", "tab:red"))):
        ax[0].bar(x + (k - 1) * w,
                  [report["arms"][a]["cases"][case]["hold10_s"]["success_pct"] for a in arms],
                  w, label=case, color=color)
        ax[1].bar(x + (k - 1) * w,
                  [report["arms"][a]["cases"][case]["final_pe_deg"]["mean"] for a in arms],
                  w, label=case, color=color)
        ax[2].bar(x + (k - 1) * w,
                  [report["arms"][a]["cases"][case]["rms_pe_deg"]["mean"] for a in arms],
                  w, label=case, color=color)
    for a_, t in zip(ax, ("success rate [%] (hold 10 s)", "final pointing error [deg]",
                          "RMS pointing error [deg]")):
        a_.set_xticks(x)
        a_.set_xticklabels(arms, rotation=18)
        a_.set_title(t)
        a_.grid(alpha=0.3)
        a_.legend()
    fig.suptitle("C4.1 - one-factor-at-a-time attribution: each arm reverts ONE factor "
                 "from the winning config")
    fig.tight_layout()
    fig.savefig(os.path.join(out_root, "c4_1_attribution.png"), dpi=120)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("train")
    t.add_argument("--arm", default=None, choices=list(ARMS))
    t.add_argument("--all", action="store_true")
    t.add_argument("--seed", type=int, default=0)
    t.add_argument("--n_envs", type=int, default=8)
    t.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    t.add_argument("--out", default="results/c4_1")
    t.set_defaults(func=mode_train)

    e = sub.add_parser("eval")
    e.add_argument("--n", type=int, default=24)
    e.add_argument("--out", default="results/c4_1")
    e.set_defaults(func=mode_eval)

    a = p.parse_args()
    if a.cmd == "train" and not a.all and not a.arm:
        p.error("train requires --arm or --all")
    sys.exit(a.func(a) or 0)


if __name__ == "__main__":
    main()
