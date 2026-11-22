"""B.1 — the central question: does residual RL beat a strong, fair classical baseline?

ARMS (one loop, one allocator, one fault path — `simulate.run_episode`)
  C1  nominal LQR + ORACLE allocation      strongest fair classical baseline (D-09)
  C2  authority-scheduled LQR              second classical variant; must not be a straw man
  R1  residual SAC, training seeds 0..4    the claim
  R2  residual PPO, training seeds 0..4    algorithm challenger (also feeds D.1)

CONDITIONS (B.2, ids shared with M3.3-B): S0 nominal, S2 Coulomb 2e-4, S4 RW1@50%+2e-4,
S6 RW1 dead, S7 RW1@50% mid-flight.  n = 24 ICs per (arm, seed, condition), 900 s at 5 Hz.

WHY THE RL ARMS ARE NOT SCORED ON EVERY CONDITION
  D-13: a D4 policy was trained with the residual added to `tau_des` BEFORE the allocator
  (health-inverted). `run_episode` adds it to the ALREADY-ALLOCATED wheel torque. The two
  coincide only at h = 1 — i.e. S0 and S2. Scoring an RL arm on S4/S6/S7 would measure a
  different controller than the one that was trained, so those cells are SKIPPED and named,
  never silently filled in. Retraining for them is a separate step.

PRE-REGISTERED DECISION RULES (frozen in MASTER_ROADMAP B.4; changing one requires a dated
DECISIONS entry made BEFORE the affected run)
  nominal non-degradation  FAIL if pooled median(R1) - median(C1) > 0.05 deg on S0
                                AND the smallest Holm-adjusted Wilcoxon p < 0.05
  fault-time advantage     PASS if pooled median(R1) - median(C1) <= -0.30 deg on S2
                                AND >= 4 of 5 seeds agree in sign
                                AND the smallest Holm-adjusted McNemar p < 0.05
  Unit of analysis is the TRAINING SEED (D-10). With 5 seeds the smallest attainable
  two-sided sign-test p is 0.0625, so a 5/5 agreement is "consistent but underpowered".
  Both columns are always reported; a trade-off is a valid outcome.

USAGE
    python scripts/b1_residual_vs_classical.py --n 24 --procs 4          # full grid
    python scripts/b1_residual_vs_classical.py --n 4 --arms C1_oracle_lqr # smoke
    python scripts/b1_residual_vs_classical.py --report-only             # rebuild report

ARTIFACTS
    results/b1/run.json                              aggregate + verdicts
    results/b1/episodes/<condition>__<arm>.json      per-episode rows
    reports/b1_residual_vs_classical.json            tracked compact copy
    docs/research/B1_residual_vs_classical_report.md generated report
"""
from __future__ import annotations
import argparse
import json
import os
import sys

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_v] = "1"

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(HERE)
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, SCRIPTS)

from satellite_adcs.config import load_config
from satellite_adcs.controllers import design_lqr
from satellite_adcs.guidance import NadirGuidance
from satellite_adcs.quaternion import quat_error, theta_vec, quat_to_dcm
from simulate import make_ic_bias, run_episode, settling_time
# the observation adapter VERIFIED in B.0 (command-equivalent to 0.000e+00 over 40 states)
from b0_checkpoint_reuse import obs15

HORIZON = 900.0
TOL_DEG = 1.0
HOLDS = (10.0, 30.0)
N_CLAIM = 24
MIN_SEEDS = 5
DELTA_NOMINAL = 0.05      # deg, nominal non-degradation tolerance
DELTA_ADVANTAGE = 0.30    # deg, fault-time advantage required on S2
ALPHA = 0.2               # D4 training value

CONDITIONS = [
    dict(id="S0_nominal",           health=[1.0, 1.0, 1.0], coul=0.0,  fault_at=None),
    dict(id="S2_coulomb_2e4",       health=[1.0, 1.0, 1.0], coul=2e-4, fault_at=None),
    dict(id="S4_rw1_50_coulomb2e4", health=[0.5, 1.0, 1.0], coul=2e-4, fault_at=None),
    dict(id="S6_rw1_dead",          health=[0.0, 1.0, 1.0], coul=0.0,  fault_at=None),
    dict(id="S7_rw1_50_midflight",  health=[0.5, 1.0, 1.0], coul=0.0,  fault_at=300.0),
]

CLASSICAL = {
    "C1_oracle_lqr": dict(controller="lqr", seed=None),
    "C2_gain_sched": dict(controller="scheduled", seed=None),
}
RL_DIRS = {"R1_sac": ("residual_d4_s{}", range(5)),
           "R2_ppo": ("residual_ppo_s{}", range(5))}

_POLICY = {}


def discover_rl_arms():
    """Only arms whose checkpoint exists on disk. Missing seeds are named, never faked."""
    found = {}
    for fam, (pat, seeds) in RL_DIRS.items():
        for s in seeds:
            p = os.path.join(HERE, "results", pat.format(s), "policy.zip")
            if os.path.exists(p):
                found[f"{fam}_s{s}"] = {"family": fam, "seed": s, "path": p}
    return found


def _load_policy(path):
    if path not in _POLICY:
        from stable_baselines3 import PPO, SAC
        cls = PPO if "ppo" in os.path.basename(os.path.dirname(path)).lower() else SAC
        _POLICY[path] = cls.load(path, device="cpu")
    return _POLICY[path]


def _lqr_gain(cfg):
    I = cfg["satellite"]["inertia"]
    J = np.diag([I["Jxx"], I["Jyy"], I["Jzz"]])
    Q = np.diag([1.0, 1.0, 1.0, 0.3, 0.3, 0.3])
    R = np.eye(3) * (1.0 / 0.010 ** 2)
    return design_lqr(J, Q, R), J


def _make_residual(cfg, path):
    """`residual_fn` that drives the trained policy from the payload only."""
    K, _ = _lqr_gain(cfg)
    model = _load_policy(path)
    scale = float(cfg["simulation"].get("tau_scale", 1.0)) * \
        float(cfg["actuators"]["reaction_wheels"]["max_torque_Nm"])
    rw_max_speed = float(cfg["actuators"]["reaction_wheels"]["max_speed_rad_s"])
    st = {"prev": np.zeros(3), "guid": None}

    def fn(payload):
        dyn, est, meas = payload["dyn"], payload["est"], payload["meas"]
        if st["guid"] is None:
            st["guid"] = NadirGuidance(dyn.mu, dyn.a)
        o = obs15(est, meas["gyro"], dyn, st["guid"], K, scale, st["prev"],
                  rw_max_speed)
        a, _ = model.predict(o.astype(np.float32), deterministic=True)
        a = np.clip(np.asarray(a, float), -1.0, 1.0)
        st["prev"] = a.copy()          # the wrapper stores the CLIPPED action
        return a

    return fn


def _cfg_for(cond):
    return load_config({"actuators": {"reaction_wheels":
                                      {"friction_coulomb_Nm": float(cond["coul"])}}})


def run_one(task):
    cond, arm, seed, ic_idx = (task["cond"], task["arm"], task["seed"], task["ic"])
    cfg = _cfg_for(cond)
    q0, w0, bias = make_ic_bias(ic_idx)
    kw = {}
    if arm in CLASSICAL:
        kw["controller"] = CLASSICAL[arm]["controller"]
    else:
        kw["residual_fn"] = _make_residual(cfg, task["path"])
        kw["residual_alpha"] = ALPHA
    res = run_episode(cfg, seed=ic_idx, T=HORIZON, rw_health=cond["health"],
                      ic=(q0, w0), gyro_bias=bias, fault_at=cond["fault_at"],
                      record=True, **kw)
    t = np.asarray(res["t"], float)
    pe = np.asarray(res["pe"], float)
    rec = res["rec"]
    tau_max = float(cfg["actuators"]["reaction_wheels"]["max_torque_Nm"])
    mtq_max = float(cfg["actuators"]["magnetorquers"]["max_dipole_Am2"])
    out = {"condition": cond["id"], "arm": arm, "seed": seed, "ic": int(ic_idx),
           "final": float(pe[-1]), "max": float(pe.max()),
           "tail_max": float(pe[-100:].max()), "tail_sigma": float(pe[-100:].std())}
    for hold in HOLDS:
        st_ = settling_time(t, pe, threshold=TOL_DEG, hold=hold)
        out[f"settle_{int(hold)}"] = None if np.isinf(st_) else float(st_)
        out[f"success_{int(hold)}"] = bool(np.isfinite(st_))
    below = np.flatnonzero(pe < TOL_DEG)
    out["t_first"] = None if below.size == 0 else float(t[below[0]])
    out["sat_frac"] = float(np.mean(np.abs(rec["tau"]).max(axis=1) >= 0.999 * tau_max))
    out["mtq_frac"] = float(np.mean(np.abs(rec["m"]).max(axis=1) >= 0.999 * mtq_max))
    return out


# ------------------------------------------------------------------------- statistics
def _mcnemar(rows_a, rows_b, key="success_30"):
    from scipy.stats import binomtest
    a = {r["ic"]: r[key] for r in rows_a}
    b = {r["ic"]: r[key] for r in rows_b}
    ics = sorted(set(a) & set(b))
    b01 = sum(1 for i in ics if (not a[i]) and b[i])
    b10 = sum(1 for i in ics if a[i] and (not b[i]))
    if b01 + b10 == 0:
        return b01, b10, 1.0
    return b01, b10, float(binomtest(min(b01, b10), b01 + b10, 0.5).pvalue)


def _wilcoxon(rows_a, rows_b):
    from scipy.stats import wilcoxon
    a = {r["ic"]: r["final"] for r in rows_a}
    b = {r["ic"]: r["final"] for r in rows_b}
    ics = sorted(set(a) & set(b))
    x = np.array([a[i] for i in ics])
    y = np.array([b[i] for i in ics])
    if np.allclose(x, y):
        return 1.0
    try:
        return float(wilcoxon(x, y).pvalue)
    except Exception:
        return float("nan")


def holm(pvals):
    p = np.asarray(pvals, float)
    m = p.size
    order = np.argsort(p)
    adj = np.empty(m)
    run = 0.0
    for k, i in enumerate(order):
        run = max(run, (m - k) * p[i])
        adj[i] = min(1.0, run)
    return adj


def aggregate(rows):
    agg = {}
    for cond in CONDITIONS:
        cid = cond["id"]
        arms = sorted({r["arm"] for r in rows if r["condition"] == cid})
        agg[cid] = {"health": cond["health"], "coulomb": cond["coul"],
                    "fault_at": cond["fault_at"], "arms": {}}
        for arm in arms:
            rs = [r for r in rows if r["condition"] == cid and r["arm"] == arm]
            fin = np.array([r["final"] for r in rs], float)
            tf = [r["t_first"] for r in rs if r["t_first"] is not None]
            agg[cid]["arms"][arm] = {
                "n": len(rs),
                "success_10": 100.0 * float(np.mean([r["success_10"] for r in rs])),
                "success_30": 100.0 * float(np.mean([r["success_30"] for r in rs])),
                "final_median": float(np.median(fin)),
                "final_p25": float(np.percentile(fin, 25)),
                "final_p75": float(np.percentile(fin, 75)),
                "tail_sigma_median": float(np.median([r["tail_sigma"] for r in rs])),
                "t_first_median": None if not tf else float(np.median(tf)),
                "sat_frac": float(np.mean([r["sat_frac"] for r in rs])),
                "mtq_frac": float(np.mean([r["mtq_frac"] for r in rs])),
                "final_list": [round(float(v), 4) for v in fin],
            }
    return agg


def verdicts(rows, agg, arms_rl):
    """Apply the B.4 rules mechanically. Returns a dict of verdict objects."""
    c1 = "C1_oracle_lqr"
    out = {"nominal": {"rule": "FAIL if median(R1)-median(C1) > 0.05 deg on S0 and "
                               "Holm-adjusted Wilcoxon p < 0.05",
                       "per_arm": {}},
           "advantage": {"rule": "PASS if median(R1)-median(C1) <= -0.30 deg on S2 and "
                                 ">=4/5 seeds agree in sign and Holm-adjusted McNemar "
                                 "p < 0.05",
                         "per_arm": {}}}

    for arm in arms_rl:
        # ---- nominal non-degradation on S0
        s0_c1 = [r for r in rows if r["condition"] == "S0_nominal" and r["arm"] == c1]
        s0_r1 = [r for r in rows if r["condition"] == "S0_nominal" and r["arm"] == arm]
        fam = arm.rsplit("_s", 1)[0]
        seeds = sorted({r["seed"] for r in rows if r["arm"] == arm})
        # seed-level: pool all seeds of this family against C1
        all_r1 = [r for r in rows if r["arm"] == arm]
        all_c1 = [r for r in rows if r["arm"] == c1 and r["condition"] == "S0_nominal"]
        d_nom = (float(np.median([r["final"] for r in s0_r1]))
                 - float(np.median([r["final"] for r in s0_c1]))) if s0_r1 else float("nan")
        p_w = _wilcoxon(s0_r1, s0_c1) if s0_r1 else float("nan")
        out["nominal"]["per_arm"][arm] = {
            "delta_median_deg": d_nom, "wilcoxon_p": p_w,
            "n_seeds": len(seeds), "incomplete_seeds": len(seeds) < MIN_SEEDS,
        }

        # ---- fault-time advantage on S2, per seed
        s2_c1 = [r for r in rows if r["condition"] == "S2_coulomb_2e4" and r["arm"] == c1]
        per_seed, ps = [], []
        for s in seeds:
            s2 = [r for r in rows if r["condition"] == "S2_coulomb_2e4"
                  and r["arm"] == arm and r["seed"] == s]
            if not s2:
                continue
            d = float(np.median([r["final"] for r in s2])) - \
                float(np.median([r["final"] for r in s2_c1]))
            b01, b10, p = _mcnemar(s2, s2_c1)
            per_seed.append({"seed": s, "delta_median_deg": d,
                             "mcnemar_b01": b01, "mcnemar_b10": b10, "p": p})
            ps.append(p)
        adj = holm(ps) if ps else []
        for i, row in enumerate(per_seed):
            row["p_holm"] = float(adj[i]) if len(adj) else float("nan")
        d_pool = float(np.median([x["delta_median_deg"] for x in per_seed])) if per_seed \
            else float("nan")
        sign_ok = sum(1 for x in per_seed if x["delta_median_deg"] < 0)
        p_min = float(min(adj)) if len(adj) else float("nan")
        complete = len(per_seed) >= MIN_SEEDS
        passed = bool(complete and d_pool <= -DELTA_ADVANTAGE
                      and sign_ok >= 4 and p_min < 0.05)
        out["advantage"]["per_arm"][arm] = {
            "per_seed": per_seed, "delta_pooled_median_deg": d_pool,
            "seeds_agreeing_in_sign": sign_ok, "n_seeds": len(per_seed),
            "min_holm_p": p_min, "complete": complete, "PASS": passed,
            "family": fam,
        }

    # family-level verdict: any seed set of a family that passes
    for key in ("nominal", "advantage"):
        fams = {}
        for arm, v in out[key]["per_arm"].items():
            fam = v.get("family", arm.rsplit("_s", 1)[0])
            cur = fams.setdefault(fam, {"PASS": False, "complete": False})
            if key == "advantage":
                cur["PASS"] |= bool(v["PASS"])
            cur["complete"] |= bool(v.get("complete", True))
        out[key]["families"] = fams
    return out


# ---------------------------------------------------------------------------- report
def table(agg):
    L = ["| condition | arm | success@10 | success@30 | final med [deg] | IQR | "
         "t_first med [s] | sat frac | MTQ frac |",
         "|---|---|---|---|---|---|---|---|---|"]
    for cond in CONDITIONS:
        cid = cond["id"]
        for arm, d in sorted(agg[cid]["arms"].items()):
            tf = "-" if d["t_first_median"] is None else f"{d['t_first_median']:.1f}"
            L.append(f"| {cid} | {arm} | {d['success_10']:.1f} % | "
                     f"{d['success_30']:.1f} % | {d['final_median']:.3f} | "
                     f"{d['final_p25']:.3f}-{d['final_p75']:.3f} | {tf} | "
                     f"{d['sat_frac']:.2f} | {d['mtq_frac']:.2f} |")
    return "\n".join(L)


def write_report(agg, verd, n, path, meta):
    no_rl = not meta.get("scored_rl_arms")
    prov = (n < N_CLAIM or no_rl
            or any(v.get("incomplete_seeds") for v in verd["nominal"]["per_arm"].values()))
    L = ["# B.1 — residual RL vs a strong classical baseline\n"]
    L.append(f"**Generated by** `codes/scripts/b1_residual_vs_classical.py` "
             f"(n = {n} ICs per cell, {HORIZON:.0f} s, 5 Hz). "
             f"Arms present: {', '.join(meta['arms']) or 'none'}.")
    if no_rl:
        L.append("\n> **CLASSICAL PASS ONLY — no RL arm has been scored.** The table below "
                 "describes the baseline, not the claim. The pre-registered verdicts cannot "
                 "be evaluated without residual arms.\n")
    if prov and not no_rl:
        L.append("\n> **PROVISIONAL.** Either n < 24 or fewer than 5 training seeds for some "
                 "arm. Not evidence; re-run with `--n 24` and five seeds.\n")
    L.append("\n## Arms\n")
    L.append("- `C1_oracle_lqr` — nominal LQR + oracle allocation (strongest fair classical "
             "baseline, D-09).\n- `C2_gain_sched` — authority-scheduled LQR.\n"
             "- `R1_sac_s<k>` / `R2_ppo_s<k>` — residual RL, one row per TRAINING seed "
             "(unit of analysis, D-10).\n")
    L.append("\n## Results\n\n" + table(agg) + "\n")
    L.append("\n## Pre-registered verdicts\n")
    for key, label in (("nominal", "Nominal non-degradation (S0)"),
                       ("advantage", "Fault-time advantage (S2)")):
        L.append(f"\n### {label}\n\n*Rule:* {verd[key]['rule']}\n")
        for arm, d in sorted(verd[key]["per_arm"].items()):
            if key == "nominal":
                L.append(f"- `{arm}`: delta = {d['delta_median_deg']:+.3f} deg, "
                         f"Wilcoxon p = {d['wilcoxon_p']:.4g}"
                         f"{' — INCOMPLETE SEEDS' if d['incomplete_seeds'] else ''}")
            else:
                L.append(f"- `{arm}`: delta(pooled median) = "
                         f"{d['delta_pooled_median_deg']:+.3f} deg over "
                         f"{d['n_seeds']} seeds, {d['seeds_agreeing_in_sign']} agree in "
                         f"sign, min Holm p = {d['min_holm_p']:.4g} -> "
                         f"**{'PASS' if d['PASS'] else 'not met'}**")
    L.append("\n## Limitations that travel with this table\n")
    for c in [
        "`C2_gain_sched` is **identical to `C1_oracle_lqr` on every h = 1 cell** by "
        "construction (`gain_scheduled.py`: re-solving R from the authority returns R0 "
        "when healthy, so K is unchanged). It becomes a distinct arm only where health "
        "differs from 1, i.e. S4/S6/S7 — it therefore adds nothing to the friction claim "
        "and must not be presented as a second independent baseline there.",
        "RL arms are scored on **S0 and S2 only**: a D4 policy was trained with the "
        "residual added before the allocator, `run_episode` adds it after allocation, and "
        "the two coincide only at h = 1 (D-13). S4/S6/S7 are skipped, not filled in.",
        "The classical arms are privileged: they allocate from ground-truth health "
        "(oracle, D-03). That makes the comparison HARDER for RL, which is the point.",
        "Coulomb friction is a static plant parameter here, not randomised per episode.",
        "No disturbances are modelled (aero/SRP/residual dipole are no-ops, G9) and no "
        "plant uncertainty is present (G10).",
        "Success is threshold-based at 1 deg; both holds (10 s and 30 s) are always shown "
        "because the hold decides the comparison.",
    ]:
        L.append(f"- {c}")
    L.append("\n## What this does NOT establish\n")
    L.append("- Nothing about fault families the policy never saw (locked / ramp / "
             "intermittent / sensor): Phase D.4.\n"
             "- Nothing about hardware, real time or embedded timing.\n"
             "- No claim of " + "generalisation" + " beyond the two conditions scored.\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


def _atomic_json(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)
    os.replace(tmp, path)


# ------------------------------------------------------------------------------ main
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=24)
    p.add_argument("--procs", type=int, default=4)
    p.add_argument("--out", default=os.path.join(HERE, "results", "b1"))
    p.add_argument("--report", default=os.path.join(
        REPO, "docs", "research", "B1_residual_vs_classical_report.md"))
    p.add_argument("--tracked", default=os.path.join(
        REPO, "reports", "b1_residual_vs_classical.json"))
    p.add_argument("--arms", default="all", help="comma list or 'all'")
    p.add_argument("--conditions", default="all")
    p.add_argument("--report-only", action="store_true")
    p.add_argument("--append", action="store_true",
                   help="merge into an existing run.json instead of replacing it. Needed on "
                        "this host: the RL arms load torch and cannot share the machine with "
                        "a 4-worker pool, so classical and RL passes run separately")
    a = p.parse_args()

    run_json = os.path.join(a.out, "run.json")
    if a.report_only:
        saved = json.load(open(run_json))
        write_report(saved["aggregate"], saved["verdicts"], saved["n"], a.report,
                     saved["meta"])
        print(f"rebuilt {a.report} from {run_json}")
        return 0

    rl = discover_rl_arms()
    eligible = {}
    for cond in CONDITIONS:
        h1 = all(abs(h - 1.0) < 1e-12 for h in cond["health"])
        eligible[cond["id"]] = h1
    conds = CONDITIONS if a.conditions == "all" else [
        c for c in CONDITIONS if c["id"] in a.conditions.split(",")]

    arms = {}
    if a.arms == "all":
        for name, spec in CLASSICAL.items():
            arms[name] = dict(spec)
        arms.update(rl)
    else:
        for x in [s.strip() for s in a.arms.split(",") if s.strip()]:
            if x in CLASSICAL:
                arms[x] = dict(CLASSICAL[x])
            elif x in rl:
                arms[x] = dict(rl[x])
            else:
                print(f"WARNING: unknown/unevaluable arm {x!r} ignored "
                      f"(classical: {sorted(CLASSICAL)}, RL: {sorted(rl)})")

    tasks, skipped = [], []
    for cond in conds:
        for arm, spec in arms.items():
            is_rl = arm in rl
            if is_rl and not eligible[cond["id"]]:
                skipped.append({"condition": cond["id"], "arm": arm,
                                "reason": "h != 1: residual path differs from training "
                                          "(D-13), retrain before scoring"})
                continue
            for ic in range(a.n):
                tasks.append({"cond": cond, "arm": arm,
                              "seed": spec.get("seed"), "ic": ic,
                              "path": spec.get("path")})

    print(f"B.1  conditions={len(conds)} arms={len(arms)} n={a.n} episodes={len(tasks)} "
          f"procs={a.procs}")
    print(f"RL arms discovered: {sorted(rl)}")
    if skipped:
        print(f"skipped cells (D-13): {len(skipped)}")

    rows = []
    if a.append and os.path.exists(run_json):
        prev = json.load(open(run_json))
        rows = list(prev.get("rows", []))
        have = {(r["condition"], r["arm"], r["seed"], r["ic"]) for r in rows}
        before = len(tasks)
        tasks = [t for t in tasks
                 if (t["cond"]["id"], t["arm"], t["seed"], t["ic"]) not in have]
        print(f"--append: kept {len(rows)} existing rows, {before-len(tasks)} cells already "
              f"present, {len(tasks)} to run")

    if not tasks:
        print("nothing to run")
        return 2

    import time
    from concurrent.futures import ProcessPoolExecutor
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.procs) as ex:
        for i, r in enumerate(ex.map(run_one, tasks, chunksize=1)):
            rows.append(r)
            if (i + 1) % max(1, len(tasks) // 10) == 0 or i == len(tasks) - 1:
                el = time.time() - t0
                print(f"  {i+1}/{len(tasks)}  {el:5.0f}s  eta "
                      f"{el/(i+1)*(len(tasks)-i-1):5.0f}s", flush=True)
    elapsed = time.time() - t0

    ep_dir = os.path.join(a.out, "episodes")
    for cond in conds:
        for arm in arms:
            rs = [r for r in rows if r["condition"] == cond["id"] and r["arm"] == arm]
            if rs:
                _atomic_json({"condition": cond, "arm": arm, "n": len(rs),
                              "episodes": rs},
                             os.path.join(ep_dir, f"{cond['id']}__{arm}.json"))

    agg = aggregate(rows)
    verd = verdicts(rows, agg, [x for x in arms if x in rl])
    meta = {"arms": sorted(arms), "rl_arms": sorted(rl),
            "scored_rl_arms": sorted(x for x in arms if x in rl),
            "skipped_cells": skipped, "procs": a.procs,
            "alpha": ALPHA, "deliberately_not_scored": "S4/S6/S7 for RL arms (D-13)"}
    payload = {"n": a.n, "horizon_s": HORIZON, "tolerance_deg": TOL_DEG,
               "holds": list(HOLDS), "meta": meta, "aggregate": agg, "verdicts": verd,
               "rows": rows,
               "elapsed_s": round(elapsed, 1),
               "generated": time.strftime("%Y-%m-%dT%H:%M:%S")}
    _atomic_json(payload, run_json)
    tracked = json.loads(json.dumps(payload))
    for cid in tracked["aggregate"]:
        for arm in tracked["aggregate"][cid]["arms"]:
            tracked["aggregate"][cid]["arms"][arm].pop("final_list", None)
    _atomic_json(tracked, a.tracked)
    write_report(agg, verd, a.n, a.report, meta)

    print("\n" + table(agg))
    for key in ("nominal", "advantage"):
        print(f"\n{key.upper()}: {verd[key]['rule']}")
        for arm, d in sorted(verd[key]["per_arm"].items()):
            if key == "nominal":
                print(f"  {arm:18s} delta={d['delta_median_deg']:+.3f} deg  "
                      f"p={d['wilcoxon_p']:.3g}")
            else:
                print(f"  {arm:18s} delta={d['delta_pooled_median_deg']:+.3f} deg  "
                      f"sign {d['seeds_agreeing_in_sign']}/{d['n_seeds']}  "
                      f"p_holm={d['min_holm_p']:.3g}  "
                      f"{'PASS' if d['PASS'] else 'not met'}")
    print(f"\nelapsed {elapsed/60:.1f} min\nsaved {run_json}\n      {a.tracked}\n"
          f"      {a.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
