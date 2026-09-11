"""C4.2 -- controlled single-term / single-scale reward study.

Authorized 2026-09-11 (USER DECISION 2) *because* C4.1 identified reward shaping as the
material contributor (A1 = -83.3 pp).  Scope is explicitly NOT a reward redesign: each arm
changes exactly ONE reward knob relative to a known reference, everything else (5 Hz / 900 s
/ 2M steps / norm_reward=0 / health_range [0.5,1]) stays at the frozen canonical config.

------------------------------------------------------------------------------
WHY THIS EXPERIMENT IS WELL POSED  (numbers verified by c4_2_reward_check.py)
------------------------------------------------------------------------------
`bonus` is `quad` PLUS a constant +1.0/step while ||theta|| < 1 deg.  A constant adds NO
gradient, so BASE and A1 have *identical* gradients at every theta:

    arm              r(1 deg)     r(0.5 deg)    dr/dtheta @0.5deg    max episode
    BASE bonus +1.0  -3.046e-04   +9.999e-01    -0.0175 / rad        +4499.66
    A1   quad        -3.046e-04   -7.615e-05    -0.0175 / rad           -0.34

So the BASE-vs-A1 gap is caused ENTIRELY by a discontinuous step, not by any gradient.
That leaves two competing mechanisms, and the arms below separate them:

    (F) FORM  -- the indicator/step itself (it "monetises" the very criterion that
                 defines success: the evaluation threshold IS reward_tol_deg = 1 deg)
    (M) MAGNITUDE -- the sheer size of the near-target reward (+4499 vs -0.34)
    (G) GRADIENT  -- a steeper smooth near-target slope (a third route, tested by S1)

------------------------------------------------------------------------------
ARMS
------------------------------------------------------------------------------
  BASE            bonus +1.0          reference -- the winner as trained (100 % success)
  A1              quad                reference -- bonus removed (C4.1: -83.3 pp)
  S1_log          log                 same scale-ish, DIFFERENT smooth form; the ONLY arm
                                      with a steep near-target gradient (2626x quad's)
  S2_bonus_0p1    bonus, tol_bonus 0.1    exact step form retained, magnitude /10
  S3_bonus_tol2   bonus, tol_bonus tol^2  exact step form retained, magnitude = the quad's
                                          own penalty at 1 deg (episode contribution +1.03,
                                          i.e. 1/4370 of BASE)  -> isolates FORM alone

S2/S3 give a 4370x dose-response span at fixed form; S1 tests the gradient route.
BASE and A1 are re-evaluated here (not copied from C4.1) so the whole table comes from one
harness on the same 24 initial conditions.

------------------------------------------------------------------------------
INTERPRETATION (decided before the runs, so the result cannot be rationalised after)
------------------------------------------------------------------------------
  S3 succeeds            -> FORM alone is sufficient; magnitude is irrelevant
  S3 fails, S2 succeeds  -> magnitude matters but a small indicator step still suffices
  S1 succeeds            -> a smooth steep-gradient reward is enough; no indicator needed
  S1 and S2/S3 all fail  -> the large step is genuinely doing the work (scale is the story)
  S1 succeeds best      -> prefer it downstream: smooth, bounded, no threshold discontinuity
                            (already implemented; better conditioned for the MCU in Phase D)

------------------------------------------------------------------------------
USAGE
------------------------------------------------------------------------------
  python scripts/c4_2_reward_study.py train --all --n_envs 8 --device cpu
  python scripts/c4_2_reward_study.py eval  --all --n 24
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Reuse the C4.1 metric/scoring harness verbatim so results are directly comparable:
# identical settling definition, identical HOLDS = (10 s, 30 s), identical case definitions,
# identical 24 initial conditions (reset(seed=0+ep)).
from c4_1_attribution import (CASES, HOLDS, SETTLE_DEG, TARGET_HZ, TARGET_T,
                             aggregate, metrics_from_pe, rollout_rl)

TOL_DEG = 1.0                                   # == rl.yaml reward_tol_deg
TOL2 = float(np.radians(TOL_DEG)) ** 2          # 3.046174e-04

ARMS = {
    "BASE": dict(
        factor="reference: bonus +1.0 (winner as trained)",
        reward_shape="bonus", reward_tol_bonus=1.0,
        model="results/rl_shaped", retrain=False),
    "A1_quad": dict(
        factor="reference: quad (bonus removed; C4.1 -83.3 pp)",
        reward_shape="quad",
        model="results/c4_1/A1_shape", retrain=False),
    "S1_log": dict(
        factor="FORM/GRADIENT: log (smooth, bounded, 2626x steeper near target)",
        reward_shape="log", steps=2_000_000),
    "S2_bonus_0p1": dict(
        factor="MAGNITUDE: bonus /10 (step form kept, magnitude 0.1)",
        reward_shape="bonus", reward_tol_bonus=0.1, steps=2_000_000),
    "S3_bonus_tol2": dict(
        factor="FORM: bonus at tol^2 (step form kept, magnitude = quad's)",
        reward_shape="bonus", reward_tol_bonus=TOL2, steps=2_000_000),
}


# --------------------------------------------------------------------- train
def train_cmd(arm, a):
    spec = ARMS[arm]
    cmd = [sys.executable, os.path.join("scripts", "train_rl.py"),
           "--algo", "ppo", "--steps", str(spec.get("steps", 2_000_000)),
           "--n_envs", str(a.n_envs), "--seed", str(a.seed),
           "--device", a.device,
           "--control_hz", str(spec.get("control_hz", TARGET_HZ)),
           "--episode_time", str(spec.get("episode_time", TARGET_T)),
           "--norm_reward", str(spec.get("norm_reward", 0)),
           "--reward_shape", spec["reward_shape"],
           "--out", os.path.join(a.out, arm)]
    if spec.get("reward_tol_bonus") is not None:
        cmd += ["--reward_tol_bonus", repr(float(spec["reward_tol_bonus"]))]
    if spec.get("reward_theta_weight") is not None:
        cmd += ["--reward_theta_weight", repr(float(spec["reward_theta_weight"]))]
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
        print(f"[train] {arm}: {spec['factor']}", flush=True)
        print("        " + " ".join(cmd), flush=True)
        t0 = time.perf_counter()
        with open(log, "w", encoding="utf-8") as f:
            p = subprocess.run(cmd, cwd=_ROOT, stdout=f, stderr=subprocess.STDOUT)
        dt = time.perf_counter() - t0
        print(f"[train] {arm}: exit={p.returncode}  wall={dt/60:.1f} min  log={log}",
              flush=True)
        if p.returncode != 0:
            raise SystemExit(f"[train] {arm}: FAILED - see {log}")
    return 0


# ---------------------------------------------------------------------- eval
def load_arm(arm, out_root):
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    spec = ARMS[arm]
    d = spec["model"] if spec.get("retrain", True) is False else os.path.join(out_root, arm)
    mp = os.path.join(d, "ppo_adcs.zip")
    if not os.path.exists(mp):
        print(f"[eval] {arm}: MISSING {mp}")
        return None, None, d
    model = PPO.load(mp, device="cpu")
    vp = os.path.join(d, "vecnormalize.pkl")
    vecnorm = None
    if os.path.exists(vp):
        from satellite_adcs.environment.adcs_env import ADCSEnv
        vecnorm = VecNormalize.load(vp, DummyVecEnv([lambda: ADCSEnv()]))
    return model, vecnorm, d


def mode_eval(a):
    from satellite_adcs.environment.adcs_env import ADCSEnv  # noqa: F401 (import check)
    report = {
        "study": "C4.2 controlled single-term/single-scale reward study",
        "authorized": "2026-09-11 (USER DECISION 2; condition met by C4.1 A1 = -83.3 pp)",
        "frozen_config": {"control_hz": TARGET_HZ, "episode_time_s": TARGET_T,
                          "norm_reward": 0, "health_range": [0.5, 1.0],
                          "steps": 2_000_000, "seed": a.seed},
        "scoring": {"settle_threshold_deg": SETTLE_DEG, "holds_s": list(HOLDS), "n_ic": a.n},
        "reward_geometry": {
            "note": "verified by c4_2_reward_check.py; bonus adds a constant, hence no gradient",
            "tol_deg": TOL_DEG, "tol2": TOL2,
            "r_at_0p5deg": {}, "max_episode_contrib": {}},
        "arms": {},
    }

    # record the observed reward geometry per arm (from the env itself, not from memory)
    for arm in ARMS:
        ov = {"rl": {"reward_shape": ARMS[arm]["reward_shape"]}}
        if ARMS[arm].get("reward_tol_bonus") is not None:
            ov["rl"]["reward_tol_bonus"] = ARMS[arm]["reward_tol_bonus"]
        if ARMS[arm].get("reward_theta_weight") is not None:
            ov["rl"]["reward_theta_weight"] = ARMS[arm]["reward_theta_weight"]
        e = ADCSEnv(overrides=ov)
        th = np.array([np.radians(0.5), 0.0, 0.0])
        r, comp = e._reward(th, np.zeros(3), np.zeros(3))
        report["reward_geometry"]["r_at_0p5deg"][arm] = round(float(r), 6)
        report["reward_geometry"]["max_episode_contrib"][arm] = round(
            float(r) * TARGET_T * TARGET_HZ, 4)

    arms = list(ARMS) if a.all else [a.arm]
    for arm in arms:
        spec = ARMS[arm]
        model, vecnorm, d = load_arm(arm, a.out)
        if model is None:
            continue
        blk = {"factor": spec["factor"], "dir": d,
               "reward": {k: v for k, v in spec.items()
                          if k.startswith("reward") or k in ("steps",)},
               "cases": {}}
        print(f"[eval] {arm}: {spec['factor']}", flush=True)
        for case, health in CASES.items():
            rows = rollout_rl(model, vecnorm, health, a.n, TARGET_T, TARGET_HZ, seed0=0)
            blk["cases"][case] = {"health": list(health), **aggregate(rows), "rows": rows}
            h10 = blk["cases"][case]["hold10_s"]
            h30 = blk["cases"][case]["hold30_s"]
            print(f"        {case:11s} h10={h10['success_pct']:5.1f}% "
                  f"h30={h30['success_pct']:5.1f}% "
                  f"final={blk['cases'][case]['final_pe_deg']['mean']:7.3f}deg", flush=True)
        report["arms"][arm] = blk

    out = os.path.join(a.out, "c4_2_reward_study.json")
    os.makedirs(a.out, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"[eval] saved {out}", flush=True)

    write_table(report, a.out)
    write_figure(report, a.out)
    return 0


# -------------------------------------------------------------------- report
def write_table(report, out_root):
    arms = [a for a in ARMS if a in report["arms"]]
    lines = []
    lines.append("# C4.2 -- controlled single-term / single-scale reward study\n")
    lines.append(f"Frozen config: 5 Hz / 900 s / 2M steps / norm_reward=0 / "
                 f"health [0.5,1] / seed {report['frozen_config']['seed']}. "
                 f"n = {report['scoring']['n_ic']} ICs, scored by the C4.1 harness "
                 f"(holds {list(HOLDS)} s).\n")
    lines.append("Reward geometry (r at 0.5 deg, and its max contribution over a 4500-step "
                 "episode):\n")
    g = report["reward_geometry"]
    lines.append("| arm | r(0.5 deg) | max episode contribution |")
    lines.append("|---|---|---|")
    for a in arms:
        lines.append(f"| {a} | {g['r_at_0p5deg'][a]:+.6e} | "
                     f"{g['max_episode_contrib'][a]:+.4f} |")
    lines.append("")
    for hold in HOLDS:
        k = f"hold{int(hold)}_s"
        lines.append(f"## Success rate, settle hold = {int(hold)} s\n")
        lines.append("| arm | " + " | ".join(CASES) + " |")
        lines.append("|---" * (len(CASES) + 1) + "|")
        for a in arms:
            cells = []
            for c in CASES:
                v = report["arms"][a]["cases"][c][k]["success_pct"]
                cells.append("n/a" if v is None else f"{v:.1f} %")
            lines.append(f"| {a} | " + " | ".join(cells) + " |")
        lines.append("")
    lines.append("## Final pointing error [deg], mean over ICs\n")
    lines.append("| arm | " + " | ".join(CASES) + " |")
    lines.append("|---" * (len(CASES) + 1) + "|")
    for a in arms:
        cells = [f"{report['arms'][a]['cases'][c]['final_pe_deg']['mean']:.3f}"
                 for c in CASES]
        lines.append(f"| {a} | " + " | ".join(cells) + " |")
    lines.append("")
    p = os.path.join(out_root, "c4_2_table.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[eval] saved {p}", flush=True)


def write_figure(report, out_root):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:                                     # pragma: no cover
        print(f"[eval] figure skipped: {e}")
        return
    arms = [a for a in ARMS if a in report["arms"]]
    cases = list(CASES)
    x = np.arange(len(arms))
    w = 0.38
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    for ax, hold, ttl in zip(axes[:2], HOLDS, ("settling hold = 10 s", "settling hold = 30 s")):
        k = f"hold{int(hold)}_s"
        for j, c in enumerate(cases):
            vals = [report["arms"][a]["cases"][c][k]["success_pct"] or 0.0 for a in arms]
            ax.bar(x + (j - 1) * w, vals, w, label=c)
        ax.set_xticks(x)
        ax.set_xticklabels(arms, rotation=20, ha="right", fontsize=8)
        ax.set_ylabel("success [%]")
        ax.set_ylim(0, 105)
        ax.set_title(ttl)
        ax.grid(alpha=.3, axis="y")
        ax.legend(fontsize=7)
    ax = axes[2]
    for j, c in enumerate(cases):
        vals = [report["arms"][a]["cases"][c]["final_pe_deg"]["mean"] for a in arms]
        ax.bar(x + (j - 1) * w, vals, w, label=c)
    ax.set_xticks(x)
    ax.set_xticklabels(arms, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("final pointing error [deg]")
    ax.set_title("mean final error")
    ax.grid(alpha=.3, axis="y")
    ax.legend(fontsize=7)
    fig.suptitle("C4.2 -- form vs magnitude in the tolerance-bonus reward", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    p = os.path.join(out_root, "c4_2_reward_study.png")
    fig.savefig(p, dpi=140)
    print(f"[eval] saved {p}", flush=True)


# ---------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    for name in ("train", "eval"):
        s = sub.add_parser(name)
        s.add_argument("--all", action="store_true")
        s.add_argument("--arm", default=None, choices=list(ARMS))
        s.add_argument("--out", default="results/c4_2")
        s.add_argument("--seed", type=int, default=0)
        s.add_argument("--n_envs", type=int, default=8)
        s.add_argument("--n", type=int, default=24,
                       help="number of initial conditions for eval")
        s.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    a = ap.parse_args()
    if a.mode == "train":
        return mode_train(a)
    return mode_eval(a)


if __name__ == "__main__":
    sys.exit(main())
