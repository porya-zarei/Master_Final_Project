"""Milestone M3.3-B — closed-loop evaluation of state-aware conservative allocation.

WHY THIS FILE EXISTS
The M3.3-B numbers in commit d57b78b came from inline commands: 3 of 8 scenarios, no
saved experiment script, no per-episode artifacts.  This file is the deliverable that
was missing — one script, one artifact tree, one printed gate table — and it cannot be
run by accident on the wrong controller, because every arm is declared here.

ARMS (every arm shares ICs, plant, seed, horizon, allocator and MTQ path)
  oracle     allocation from GROUND-TRUTH wheel health.  Privileged; this is the
             historical default and therefore the upper bound.
  unity      the allocator is told "all wheels healthy" and never corrected.  This is
             the NO-FAULT-KNOWLEDGE lower bound: what an unknown fault costs with no
             estimator at all.
  estimated  per-wheel joint RLS on  y = [-tau_cmd, +1] . [h, tau_f]  (M3), feeding the
             state-aware policy (M3.3-A): UNKNOWN/HEALTHY -> no compensation,
             DEGRADED -> h_used = max(h_hat, 0.5).  This is the ONLY deployable arm.

  Ordering is unity <= estimated <= oracle in information.  `estimated` must land
  between them; anything else is a measurement bug, not a discovery.

PRE-REGISTERED CRITERIA — fixed BEFORE the run, from already-measured quantities
  P0  fault injection is physically real, not a flag: a dead wheel is commanded
      (>25 % of tau_max on average) and nevertheless does not rotate (net |dw| < 5 rad/s);
      a healthy wheel does rotate.  Measured from the wheel state, NOT from rw_health
      (computing delivered = cmd * rw_health would only prove the field is set).
  P1  NO FALSE ALARMS.  On scenarios whose wheels are all healthy (S0-S2) the estimated
      arm must report exactly zero DEGRADED wheel-steps and reproduce the unity arm
      BIT-IDENTICALLY (no compensation is the only choice that cannot manufacture
      performance — the M2 lesson).
  P2  MASKED-FAULT RECOVERY.  On every h=0.5 scenario the median final error must come
      within 0.05 deg of the oracle, and success@30 s within 1/n.  (0.05 deg is 25 % of
      the measured healthy error floor 0.19 deg; the oracle reference is the same-IC run.)
  P3  DEAD-WHEEL HONESTY.  On S6 the dead wheel is never reported HEALTHY; if it is
      certified DEGRADED the command stays bounded by the floor (amplification <= 2.0,
      never the 1/h -> saturation machine of M2).
  P4  MID-FLIGHT DETECTION.  On S7 (fault at t=300 s) the fault is certified DEGRADED
      after the fault onset, and the time-to-certify is reported.
  P5  NO MANUFACTURED WIN.  `estimated` may never beat `oracle` by more than 0.05 deg
      median final error.  The oracle has strictly more information, so such a result is
      an ARTEFACT FLAG requiring investigation, not a result.
  Claims require n >= 24 episode-level independent IC draws.  There is no learned policy
  in this experiment, so episodes are genuine independent draws (unlike the D4 RL arms,
  where the unit of analysis is the training seed).

USAGE
    python scripts/m33b_state_aware_allocation.py --n 3  --procs 6      # smoke / preflight
    python scripts/m33b_state_aware_allocation.py --n 24 --procs 6      # reported grid
    python scripts/m33b_state_aware_allocation.py --report-only         # rebuild tables

ARTIFACTS
    results/m33b/run.json                     aggregate + criteria + config fingerprint
    results/m33b/episodes/<scenario>__<arm>.json    per-episode rows (the missing artifact)
    results/m33b/timeseries/<scenario>__<arm>__s<k>.json   series for the decisive cases
    reports/m33b_state_aware_allocation.json  compact TRACKED copy (results/ is gitignored)
    docs/research/M33B_allocation_report.md   generated report (banner when n < 24)
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time

# Per-worker BLAS threading MUST be pinned to 1 BEFORE numpy is imported, and the
# assignment has to happen in the parent so spawned children inherit it. Every matrix
# in this problem is 3x3-6x6, so threading buys nothing and each worker's thread pool
# costs real memory -- unpinned, 6 workers exhaust RAM at spawn and the pool dies with
# "OpenBLAS error: Memory allocation still failed" plus BrokenProcessPool, which looks
# like a code fault and is not one.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_v] = "1"

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from satellite_adcs.config import load_config
from simulate import make_ic_bias, run_episode, settling_time

# --------------------------------------------------------------------------- setup
HORIZON = 900.0          # s — the project's comparison horizon (4500 control steps)
TOL_DEG = 1.0            # the requirement under test
HOLDS = (10.0, 30.0)     # s — ALWAYS report both; the hold decides the comparison
N_CLAIM = 24             # below this the run is a preflight, not evidence
AGREE_DEG = 0.05         # P2/P5 tolerance, 25 % of the measured healthy floor
DEAD_CMD_FRAC = 0.25     # P0: a "commanded" wheel averages > 25 % of tau_max
DEAD_ROT_RAD = 5.0       # P0: ... and nets < 5 rad/s of rotation over the episode
H_FLOOR = 0.5            # the policy's DEGRADED floor (allocation_policy.H_FLOOR)

# 8 scenarios = the staged matrix of the roadmap (§3.6), restricted to wheel faults,
# with BOTH the multiplicative (h) and the additive (tau_f) family represented, plus a
# mid-flight onset and a second wheel so per-wheel attribution is actually tested.
SCENARIOS = [
    dict(id="S0_nominal",           health=[1.0, 1.0, 1.0], coul=0.0,  fault_at=None,
         purpose="regression: nothing to fix"),
    dict(id="S1_coulomb_1e4",       health=[1.0, 1.0, 1.0], coul=1e-4, fault_at=None,
         purpose="friction below the LQR failure threshold (85.9 % classical)"),
    dict(id="S2_coulomb_2e4",       health=[1.0, 1.0, 1.0], coul=2e-4, fault_at=None,
         purpose="the decisive family: classical LQR 0/16"),
    dict(id="S3_rw1_50",            health=[0.5, 1.0, 1.0], coul=0.0,  fault_at=None,
         purpose="maskable multiplicative fault"),
    dict(id="S4_rw1_50_coulomb2e4", health=[0.5, 1.0, 1.0], coul=2e-4, fault_at=None,
         purpose="multiplicative + additive together (must be separable)"),
    dict(id="S5_rw2_50",            health=[1.0, 0.5, 1.0], coul=0.0,  fault_at=None,
         purpose="per-wheel attribution on a wheel other than wheel 1"),
    dict(id="S6_rw1_dead",          health=[0.0, 1.0, 1.0], coul=0.0,  fault_at=None,
         purpose="zero effectiveness; unidentifiable only if never commanded"),
    dict(id="S7_rw1_50_midflight",  health=[0.5, 1.0, 1.0], coul=0.0,  fault_at=300.0,
         purpose="fault in flight: the regime real failures live in"),
]

ARMS = {
    "oracle":    dict(health_source="true",  conservative=False),
    "unity":     dict(health_source="unity", conservative=False),
    "estimated": dict(health_source="true",  conservative=True),
}

# scenarios whose wheels are all healthy -> P1 applies
P1_SCEN = {"S0_nominal", "S1_coulomb_1e4", "S2_coulomb_2e4"}
# scenarios carrying an h=0.5 wheel -> P2 applies
P2_SCEN = {"S3_rw1_50", "S4_rw1_50_coulomb2e4", "S5_rw2_50", "S7_rw1_50_midflight"}
TIMESERIES_DEFAULT = "S2_coulomb_2e4,S7_rw1_50_midflight"


# --------------------------------------------------------------------------- episode
def _cfg(coulomb: float) -> dict:
    return load_config({"actuators": {"reaction_wheels":
                                      {"friction_coulomb_Nm": float(coulomb)}}})


def _first_time(t, mask):
    idx = np.flatnonzero(mask)
    return None if idx.size == 0 else float(t[idx[0]])


def metrics(res, scen, tau_max, mtq_max, n_rw=3):
    """Episode-level metrics. Every quantity is computed here, from the run itself."""
    t = np.asarray(res["t"], float)
    pe = np.asarray(res["pe"], float)
    rec = res["rec"]
    out = {"scenario": scen["id"],
           "final": float(pe[-1]),
           "max": float(pe.max()),
           "tail_max": float(pe[-100:].max()),      # sustained behaviour, no transient
           "tail_sigma": float(pe[-100:].std()),
           "rms": float(np.sqrt(np.mean(pe ** 2)))}
    for hold in HOLDS:
        st = settling_time(t, pe, threshold=TOL_DEG, hold=hold)
        out[f"settle_{int(hold)}"] = None if np.isinf(st) else float(st)
        out[f"success_{int(hold)}"] = bool(np.isfinite(st))
    out["t_first"] = _first_time(t, pe < TOL_DEG)

    tau = rec["tau"]
    om = rec["m"]
    # actuator usage: how often is the command / the magnetorquer at its own limit
    out["sat_frac"] = float(np.mean(np.abs(tau).max(axis=1) >= 0.999 * tau_max))
    out["mtq_frac"] = float(np.mean(np.abs(om).max(axis=1) >= 0.999 * mtq_max))
    out["cmd_rms"] = float(np.sqrt(np.mean(tau ** 2)))

    w = rec["w"]
    out["w_max"] = float(np.max(np.abs(w)))
    out["w_final"] = np.round(w[-1], 3).tolist()
    out["w_net_rot"] = np.round(np.abs(w[-1] - w[0]), 2).tolist()   # P0 observable
    out["cmd_mean_abs"] = np.round(np.mean(np.abs(tau), axis=0), 6).tolist()

    # estimator behaviour (meaningful only when an estimator runs)
    st = rec["state"]
    hh = rec["h_hat"]
    sg = rec["sigma"]
    est = {}
    if st.size and int(np.max(st)) >= 0:
        SIG = 0.1     # FrictionHealthEstimator.SIGMA_H_MAX
        for i in range(n_rw):
            est[f"rw{i+1}_cert_t"] = _first_time(t, st[:, i] == 2)      # DEGRADED
            est[f"rw{i+1}_healthy_t"] = _first_time(t, st[:, i] == 1)   # HEALTHY
            est[f"rw{i+1}_deg_steps"] = int(np.sum(st[:, i] == 2))
            est[f"rw{i+1}_h_final"] = float(hh[-1, i])
            est[f"rw{i+1}_state_final"] = int(st[-1, i])
            # the gate's own predicate: is the covariance tight enough to ACT on?
            est[f"rw{i+1}_sigma_final"] = float(sg[-1, i])
            est[f"rw{i+1}_gate_open_t"] = _first_time(t, sg[:, i] <= SIG)
        est["deg_steps_total"] = int(np.sum(st == 2))
        est["healthy_steps_total"] = int(np.sum(st == 1))
        est["gate_open_frac"] = float(np.mean(np.any(sg <= SIG, axis=1)))
    out["est"] = est
    out["h_final"] = np.round(res["rw_health"], 4).tolist()
    if res.get("cons") is not None:
        out["n_upd"] = np.asarray(res["cons"].n_upd, int).tolist()
        out["tau_f_final"] = np.round(res["cons"].tau_f, 9).tolist()
    return out


def run_one(task):
    """Worker: one (scenario, arm, seed). Pure function of the task dict."""
    scen, arm, seed, want_series = (task["scen"], task["arm"], task["seed"],
                                    task["want_series"])
    cfg = _cfg(scen["coul"])
    q0, w0, bias = make_ic_bias(seed)
    # M3.3-B sensitivity: there is no wheel tachometer in sensors.py, so the estimate
    # normally reads the plant exactly. "noisy" is the stated case: 0.5 rad/s
    # quantisation (a 12-bit encoder on a 628 rad/s wheel is coarser than this) plus
    # 0.2 rad/s of white noise, drawn per episode.
    ws = None
    if task.get("tachometer") == "noisy":
        _rng = np.random.default_rng(97_000 + seed)

        def ws(w, _r=_rng):                      # noqa: F811 - shadow is intentional
            return np.round(np.asarray(w, float) / 0.5) * 0.5 + _r.normal(0.0, 0.2, size=3)

    res = run_episode(cfg, seed=seed, T=HORIZON,
                      rw_health=scen["health"], ic=(q0, w0), gyro_bias=bias,
                      fault_at=scen["fault_at"], record=True,
                      wheel_sensor=ws, **ARMS[arm])
    tau_max = float(cfg["actuators"]["reaction_wheels"]["max_torque_Nm"])
    mtq_max = float(cfg["actuators"]["magnetorquers"]["max_dipole_Am2"])
    m = metrics(res, scen, tau_max, mtq_max)
    m.update(arm=arm, seed=seed)
    if want_series:
        m["series"] = {k: np.asarray(v, float).round(6).tolist()
                       for k, v in res["rec"].items()}
        m["series"]["t"] = np.asarray(res["t"], float).round(4).tolist()
        m["series"]["pe"] = np.asarray(res["pe"], float).round(6).tolist()
    return m


# ----------------------------------------------------------------------- aggregation
def _binom_p(k, n):
    """Exact two-sided McNemar (binomial on the discordant pairs)."""
    from scipy.stats import binomtest
    if n == 0:
        return 1.0
    return float(binomtest(k, n, 0.5).pvalue)


def mcnemar(rows_a, rows_b, key="success_30"):
    """Paired exact test on a binary metric. Returns (b01, b10, p)."""
    a = {r["seed"]: r[key] for r in rows_a}
    b = {r["seed"]: r[key] for r in rows_b}
    seeds = sorted(set(a) & set(b))
    b01 = sum(1 for s in seeds if (not a[s]) and b[s])   # a fail -> b success
    b10 = sum(1 for s in seeds if a[s] and (not b[s]))
    return b01, b10, _binom_p(min(b01, b10), b01 + b10)


def wilcoxon(rows_a, rows_b):
    from scipy.stats import wilcoxon as _w
    a = {r["seed"]: r["final"] for r in rows_a}
    b = {r["seed"]: r["final"] for r in rows_b}
    seeds = sorted(set(a) & set(b))
    x = np.array([a[s] for s in seeds])
    y = np.array([b[s] for s in seeds])
    if np.allclose(x, y):
        return 1.0
    try:
        return float(_w(x, y).pvalue)
    except Exception:
        return float("nan")


def aggregate(rows, n):
    out = {}
    for scen in SCENARIOS:
        sid = scen["id"]
        out[sid] = {"purpose": scen["purpose"],
                    "health": scen["health"], "coulomb": scen["coul"],
                    "fault_at": scen["fault_at"], "arms": {}}
        for arm in ARMS:
            rs = [r for r in rows if r["scenario"] == sid and r["arm"] == arm]
            if not rs:
                continue
            fin = np.array([r["final"] for r in rs], float)
            tf = [r["t_first"] for r in rs]
            tf_ok = [v for v in tf if v is not None]
            out[sid]["arms"][arm] = {
                "n": len(rs),
                "success_10": 100.0 * float(np.mean([r["success_10"] for r in rs])),
                "success_30": 100.0 * float(np.mean([r["success_30"] for r in rs])),
                "final_median": float(np.median(fin)),
                "final_p25": float(np.percentile(fin, 25)),
                "final_p75": float(np.percentile(fin, 75)),
                "final_list": [round(float(v), 4) for v in fin],
                "t_first_median": None if not tf_ok else float(np.median(tf_ok)),
                "t_first_n": len(tf_ok),
                "tail_sigma_median": float(np.median([r["tail_sigma"] for r in rs])),
                "sat_frac": float(np.mean([r["sat_frac"] for r in rs])),
                "mtq_frac": float(np.mean([r["mtq_frac"] for r in rs])),
                "deg_steps_total": int(sum(r["est"].get("deg_steps_total", 0) for r in rs)),
                "healthy_steps_total": int(sum(r["est"].get("healthy_steps_total", 0) for r in rs)),
                "cert_t_median": _cert_median(rs, scen),
                "seeds": [r["seed"] for r in rs],
            }
        # paired contrasts, always estimated vs the two bounds
        for other in ("unity", "oracle"):
            sa = [r for r in rows if r["scenario"] == sid and r["arm"] == "estimated"]
            sb = [r for r in rows if r["scenario"] == sid and r["arm"] == other]
            if sa and sb:
                b01, b10, p = mcnemar(sa, sb)
                out[sid][f"mcnemar_vs_{other}"] = {
                    "est_only_success": b01, "other_only_success": b10,
                    "p": round(p, 5), "p_final": round(wilcoxon(sa, sb), 5),
                }
    return out


def _cert_median(rows, scen):
    """Median time-to-certify over episodes that certified at all (fault wheel only)."""
    vals = []
    for r in rows:
        e = r["est"]
        for i, h in enumerate(scen["health"]):
            if h < 0.95:
                v = e.get(f"rw{i+1}_cert_t")
                if v is not None:
                    vals.append(v)
    return None if not vals else float(np.median(vals))


def evaluate_criteria(agg, rows, n):
    """Apply the pre-registered criteria. Returns {id: {pass, detail}}."""
    res = {}
    est = lambda sid: agg[sid]["arms"].get("estimated", {})
    orc = lambda sid: agg[sid]["arms"].get("oracle", {})
    uni = lambda sid: agg[sid]["arms"].get("unity", {})

    # ---- P0 physical reality of the injection, measured from the WHEEL STATE.
    # The `unity` arm is the probe: it commands every wheel the full demand. The
    # `oracle` arm commands a dead wheel exactly zero (G13), so it cannot show whether
    # the wheel is physically dead -- that is reported separately as a finding.
    tau_max_cfg = float(_cfg(0.0)["actuators"]["reaction_wheels"]["max_torque_Nm"])
    p0, det0 = True, []
    for scen in SCENARIOS:
        rs = [r for r in rows if r["scenario"] == scen["id"] and r["arm"] == "unity"]
        ro = [r for r in rows if r["scenario"] == scen["id"] and r["arm"] == "oracle"]
        if not rs:
            continue
        for i, h in enumerate(scen["health"]):
            rot = float(np.median([r["w_net_rot"][i] for r in rs]))
            cmd = float(np.median([r["cmd_mean_abs"][i] for r in rs]))
            if h == 0.0:
                ok = (rot < DEAD_ROT_RAD) and (cmd > DEAD_CMD_FRAC * tau_max_cfg)
                p0 &= ok
                det0.append(f"{scen['id']} rw{i+1} DEAD: net_rot={rot:.2f} rad/s "
                            f"(<{DEAD_ROT_RAD}), mean cmd={cmd:.2e} N*m "
                            f"(>{DEAD_CMD_FRAC*tau_max_cfg:.2e}) -> {'ok' if ok else 'FAIL'}")
                if ro:
                    cmd_o = float(np.median([r["cmd_mean_abs"][i] for r in ro]))
                    det0.append(f"{scen['id']} rw{i+1} oracle-arm mean cmd={cmd_o:.2e} "
                                f"N*m -- the oracle zeroes a dead wheel, so it is "
                                f"unidentifiable under the oracle (G13)")
            elif h >= 0.99:
                ok = rot > DEAD_ROT_RAD
                p0 &= ok
                det0.append(f"{scen['id']} rw{i+1} HEALTHY: net_rot={rot:.1f} rad/s "
                            f"(>{DEAD_ROT_RAD}) -> {'ok' if ok else 'FAIL'}")
    res["P0_injection_is_physical"] = {"pass": bool(p0), "detail": det0}

    # ---- P1 no false alarms on healthy wheels (compared on RAW floats)
    p1, det1 = True, []
    for sid in P1_SCEN:
        re_ = {r["seed"]: r["final"] for r in rows
               if r["scenario"] == sid and r["arm"] == "estimated"}
        ru = {r["seed"]: r["final"] for r in rows
              if r["scenario"] == sid and r["arm"] == "unity"}
        if not re_ or not ru:
            continue
        seeds = sorted(set(re_) & set(ru))
        diffs = [abs(re_[s] - ru[s]) for s in seeds]
        same = all(d == 0.0 for d in diffs)
        deg = int(sum(r["est"].get("deg_steps_total", 0) for r in rows
                      if r["scenario"] == sid and r["arm"] == "estimated"))
        ok = (deg == 0) and same
        p1 &= ok
        det1.append(f"{sid}: DEGRADED wheel-steps={deg}, max|final_est - final_unity|="
                    f"{max(diffs) if diffs else 0.0:.3e}, bit_identical={same} "
                    f"-> {'ok' if ok else 'FAIL'}")
    res["P1_no_false_alarms"] = {"pass": bool(p1), "detail": det1}

    # ---- P2 masked-fault recovery
    p2, det2 = True, []
    for sid in P2_SCEN:
        e, o = est(sid), orc(sid)
        if not e or not o:
            continue
        d = e["final_median"] - o["final_median"]
        dsucc = o["success_30"] - e["success_30"]
        ok = (d <= AGREE_DEG) and (dsucc <= 100.0 / max(n, 1))
        p2 &= ok
        det2.append(f"{sid}: d_final=+{d:.3f} deg (<= {AGREE_DEG}), "
                    f"d_success=-{dsucc:.1f} pp (<= {100.0/max(n,1):.1f}) "
                    f"cert_med={e['cert_t_median']} -> {'ok' if ok else 'FAIL'}")
    res["P2_masked_fault_recovery"] = {"pass": bool(p2), "detail": det2}

    # ---- P3 dead-wheel honesty
    sid = "S6_rw1_dead"
    e = est(sid)
    det3, p3 = [], bool(e)
    if e:
        # the dead wheel is index 0; inspect every episode's final state
        rows_e = [r for r in rows if r["scenario"] == sid and r["arm"] == "estimated"]
        never_healthy = all(r["est"].get("rw1_state_final") != 1 for r in rows_e)
        certified = sum(1 for r in rows_e if r["est"].get("rw1_cert_t") is not None)
        p3 = never_healthy and certified > 0
        det3 = [f"never_reported_HEALTHY={never_healthy}",
                f"certified_DEGRADED={certified}/{len(rows_e)}",
                f"amplification_bound={1.0/H_FLOOR:.1f}x (floor {H_FLOOR}) -- structural, "
                f"not measured: it is what makes 1/h finite at h=0",
                f"cmd saturation fraction (median)="
                f"{np.median([r['sat_frac'] for r in rows_e]):.3f}",
                f"final_median={e['final_median']:.3f} deg vs oracle "
                f"{orc(sid)['final_median']:.3f} (expected WORSE: a floored command cannot "
                f"route a total failure's residual to the magnetorquers)"]
    res["P3_dead_wheel_honesty"] = {"pass": bool(p3), "detail": det3}

    # ---- P4 mid-flight detection
    sid = "S7_rw1_50_midflight"
    e = est(sid)
    det4, p4 = [], bool(e)
    if e:
        rows_e = [r for r in rows if r["scenario"] == sid and r["arm"] == "estimated"]
        cert = [r["est"].get("rw1_cert_t") for r in rows_e]
        ok_cert = [c for c in cert if c is not None and c > 300.0]
        p4 = len(ok_cert) == len(rows_e) and len(rows_e) > 0
        det4 = [f"fault onset = 300.0 s",
                f"certified after onset = {len(ok_cert)}/{len(rows_e)}",
                f"median time-to-certify = {None if not ok_cert else round(float(np.median(ok_cert)),1)} s"]
    res["P4_midflight_detection"] = {"pass": bool(p4), "detail": det4}

    # ---- P5 no manufactured win
    p5, det5 = True, []
    for scen in SCENARIOS:
        sid = scen["id"]
        e, o = est(sid), orc(sid)
        if not e or not o:
            continue
        d = o["final_median"] - e["final_median"]
        flag = d > AGREE_DEG
        p5 &= (not flag)
        det5.append(f"{sid}: oracle-estimated={d:+.3f} deg "
                    f"-> {'ARTEFACT FLAG' if flag else 'ok'}")
    res["P5_no_manufactured_win"] = {"pass": bool(p5), "detail": det5}
    return res


# ------------------------------------------------------------------------- reporting
def table(agg, n):
    lines = []
    lines.append("| scenario | arm | success@10s | success@30s | final med [deg] | IQR | "
                 "t_first med [s] | sat frac | MTQ frac |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for scen in SCENARIOS:
        a = agg[scen["id"]]["arms"]
        for arm in ("oracle", "estimated", "unity"):
            if arm not in a:
                continue
            d = a[arm]
            tf = "-" if d["t_first_median"] is None else f"{d['t_first_median']:.1f}"
            lines.append(f"| {scen['id']} | {arm} | {d['success_10']:.1f} % | "
                         f"{d['success_30']:.1f} % | {d['final_median']:.3f} | "
                         f"{d['final_p25']:.3f}-{d['final_p75']:.3f} | {tf} | "
                         f"{d['sat_frac']:.2f} | {d['mtq_frac']:.2f} |")
    return "\n".join(lines)


def contrast_table(agg, n):
    lines = ["| scenario | contrast | d final med [deg] | success@30 est vs other | "
             "McNemar p | Wilcoxon p (final) |",
             "|---|---|---|---|---|---|"]
    for scen in SCENARIOS:
        sid = scen["id"]
        a = agg[sid]["arms"]
        if "estimated" not in a:
            continue
        for other in ("unity", "oracle"):
            if other not in a:
                continue
            d = a["estimated"]["final_median"] - a[other]["final_median"]
            mc = agg[sid].get(f"mcnemar_vs_{other}", {})
            lines.append(f"| {sid} | est vs {other} | {d:+.3f} | "
                         f"{a['estimated']['success_30']:.0f} vs {a[other]['success_30']:.0f} % | "
                         f"{mc.get('p', float('nan'))} | {mc.get('p_final', float('nan'))} |")
    return "\n".join(lines)


def write_report(agg, crit, n, path, elapsed):
    prov = n < N_CLAIM
    L = []
    L.append("# M3.3-B — state-aware conservative allocation, closed loop\n")
    L.append(f"**Generated by** `codes/scripts/m33b_state_aware_allocation.py` "
             f"(n = {n} per cell, {HORIZON:.0f} s horizon, {elapsed/60:.1f} min).\n")
    if prov:
        L.append("> **PROVISIONAL — n < 24. This is a preflight, not evidence.** "
                 "Re-run with `--n 24` before quoting any number.\n")
    L.append("## Arms\n")
    L.append("- `oracle` — allocation from ground-truth wheel health (privileged upper bound).\n"
             "- `unity` — allocator believes all wheels healthy, never corrected "
             "(no-fault-knowledge lower bound).\n"
             "- `estimated` — per-wheel joint RLS `(h, tau_f)` -> state-aware policy "
             "(the only deployable arm).\n")
    L.append("## Results\n")
    L.append(table(agg, n) + "\n")
    L.append("## Paired contrasts\n")
    L.append("`estimated` vs each bound; McNemar is paired on identical ICs.\n")
    L.append(contrast_table(agg, n) + "\n")
    L.append("## Pre-registered criteria\n")
    for k, v in crit.items():
        L.append(f"### {k} — {'PASS' if v['pass'] else 'FAIL'}\n")
        for d in v["detail"]:
            L.append(f"- {d}")
        L.append("")
    L.append("## Caveats that travel with these numbers\n")
    for c in [
        "The estimator reads the plant's wheel speed. There is **no tachometer** in "
        "`sensors.py`; this is an idealised readout. `--tachometer noisy` is the stated "
        "sensitivity case.",
        "Faults are static inside an episode except S7, so this does not exercise tracking "
        "of a time-varying health.",
        "Disturbance flags (aero / SRP / residual dipole) are **no-ops** (G9) and no plant "
        "uncertainty is present (G10). Nothing here claims robustness to either.",
        "The `DEGRADED` floor caps amplification at "
        f"{1.0/H_FLOOR:.1f}x, which by construction cannot route a *total* wheel failure's "
        "residual to the magnetorquers. S6 is the scenario that measures that cost.",
        "Episodes are independent IC draws because no policy is learned here; this is a "
        "classical-controller comparison, not a method-level RL claim.",
    ]:
        L.append(f"- {c}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


def _free_gb():
    """Free physical memory in GB, without psutil (ctype on the Win32 struct)."""
    try:
        import ctypes

        class MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        m = MS()
        m.dwLength = ctypes.sizeof(MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return m.ullAvailPhys / 1024 ** 3
    except Exception:
        return float("nan")


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
    p.add_argument("--procs", type=int, default=6,
                   help="process pool size; keep 6 on a 16 GB host sharing the machine")
    p.add_argument("--out", default=os.path.join(HERE, "results", "m33b"))
    p.add_argument("--report",
                   default=os.path.join(REPO, "docs", "research",
                                        "M33B_allocation_report.md"))
    p.add_argument("--tracked",
                   default=os.path.join(REPO, "reports",
                                        "m33b_state_aware_allocation.json"))
    p.add_argument("--timeseries", default=TIMESERIES_DEFAULT,
                   help="comma-separated scenario ids to dump series for (seed 0 only), "
                        "or 'none'")
    p.add_argument("--scenarios", default="all")
    p.add_argument("--arms", default="all")
    p.add_argument("--report-only", action="store_true",
                   help="rebuild tables/report from the saved run.json")
    p.add_argument("--tachometer", choices=["ideal", "noisy"], default="ideal")
    a = p.parse_args()

    run_json = os.path.join(a.out, "run.json")
    if a.report_only:
        with open(run_json) as f:
            saved = json.load(f)
        write_report(saved["aggregate"], saved["criteria"], saved["n"], a.report, 0.0)
        print(f"rebuilt {a.report} from {run_json} (n={saved['n']})")
        return

    scens = SCENARIOS if a.scenarios == "all" else [
        s for s in SCENARIOS if s["id"] in a.scenarios.split(",")]
    arms = list(ARMS) if a.arms == "all" else [x for x in a.arms.split(",") if x in ARMS]
    ts_ids = set() if a.timeseries == "none" else set(a.timeseries.split(","))
    assert scens and arms, "nothing to run"

    tasks = []
    for scen in scens:
        for arm in arms:
            for seed in range(a.n):
                tasks.append(dict(scen=scen, arm=arm, seed=seed,
                                  tachometer=a.tachometer,
                                  want_series=(scen["id"] in ts_ids and seed == 0)))
    print(f"M3.3-B  scenarios={len(scens)} arms={len(arms)} n={a.n} "
          f"episodes={len(tasks)} procs={a.procs} tachometer={a.tachometer}")
    print(f"horizon={HORIZON:.0f}s  holds={HOLDS}  tol={TOL_DEG} deg  "
          f"friction_values={sorted({s['coul'] for s in scens})}")
    free = _free_gb()
    print(f"free RAM: {free:.2f} GB  ->  ~0.2 GB/worker, keep procs*0.25 < free")
    if a.procs * 0.25 > free:
        print(f"  ** WARNING: procs={a.procs} is above the safe budget for {free:.2f} GB. "
              f"Lower --procs or free memory; an over-subscribed pool dies at spawn with "
              f"'OpenBLAS error: Memory allocation still failed'. **")

    t0 = time.time()
    rows, series = [], {}
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=a.procs) as ex:
        for i, r in enumerate(ex.map(run_one, tasks, chunksize=1)):
            if "series" in r:
                # keyed by identity, NOT by completion index: a reordered pool must not
                # be able to attach one episode's series to another episode's record.
                series[(r["scenario"], r["arm"], r["seed"])] = r.pop("series")
            rows.append(r)
            if (i + 1) % max(1, len(tasks) // 20) == 0 or i == len(tasks) - 1:
                el = time.time() - t0
                eta = el / (i + 1) * (len(tasks) - i - 1)
                print(f"  {i+1}/{len(tasks)} episodes  {el:5.0f}s elapsed  "
                      f"eta {eta:5.0f}s", flush=True)
    elapsed = time.time() - t0

    # per-episode artifacts — the thing the previous session could not produce
    ep_dir = os.path.join(a.out, "episodes")
    for scen in scens:
        for arm in arms:
            rs = [r for r in rows if r["scenario"] == scen["id"] and r["arm"] == arm]
            if rs:
                _atomic_json({"scenario": scen, "arm": arm, "n": len(rs),
                              "episodes": rs}, os.path.join(ep_dir, f"{scen['id']}__{arm}.json"))
    if series:
        ts_dir = os.path.join(a.out, "timeseries")
        for (sid, arm, seed), ser in sorted(series.items()):
            _atomic_json({"scenario": sid, "arm": arm, "seed": seed, "series": ser},
                         os.path.join(ts_dir, f"{sid}__{arm}__s{seed}.json"))

    agg = aggregate(rows, a.n)
    crit = evaluate_criteria(agg, rows, a.n)
    payload = {"n": a.n, "horizon_s": HORIZON, "tolerance_deg": TOL_DEG,
               "holds": list(HOLDS), "procs": a.procs,
               "tachometer": a.tachometer,
               "h_floor": H_FLOOR, "agree_deg": AGREE_DEG,
               "criteria_pass": {k: v["pass"] for k, v in crit.items()},
               "criteria": crit, "aggregate": agg,
               "elapsed_s": round(elapsed, 1),
               "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "scenarios": [s["id"] for s in scens], "arms": arms}
    _atomic_json(payload, run_json)

    # compact tracked copy: no per-episode lists, no series — evidence without bulk
    tracked = json.loads(json.dumps(payload))
    for sid in tracked["aggregate"]:
        for arm in tracked["aggregate"][sid]["arms"]:
            tracked["aggregate"][sid]["arms"][arm].pop("final_list", None)
    _atomic_json(tracked, a.tracked)

    write_report(agg, crit, a.n, a.report, elapsed)

    print("\n" + table(agg, a.n))
    print("\n" + contrast_table(agg, a.n))
    print("\nPRE-REGISTERED CRITERIA")
    for k, v in crit.items():
        print(f"  {k:32s} {'PASS' if v['pass'] else 'FAIL'}")
    print(f"\nelapsed {elapsed/60:.1f} min")
    print(f"saved {run_json}\n      {ep_dir}/<scenario>__<arm>.json\n"
          f"      {a.tracked}\n      {a.report}")
    if a.n < N_CLAIM:
        print(f"\n** PROVISIONAL: n={a.n} < {N_CLAIM}. Preflight only. **")


if __name__ == "__main__":
    main()
