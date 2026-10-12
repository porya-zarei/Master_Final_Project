"""C2-h offline validation of the reaction-wheel health estimator.

No RL training, no plant change -- this validates an estimator against truth.

LEVEL A -- synthetic, deterministic (one wheel, exact regressor)
  A1  exact identification of h = 0.5 with no noise
  A2  SATURATION TRAP: a wheel pinned at the speed limit gives dOmega = 0 while
      tau_cmd != 0. Compare the guarded estimator with the unguarded one.
  A3  EXCITATION GATE: tau_cmd = 0 carries no information; age must grow and the
      estimate must not random-walk.
  A4  TRACKING a step 1.0 -> 0.4 for several forgetting factors.

LEVEL B -- closed loop, real plant, the actual Baseline-C PPO policy
  healthy | rw1@50% | rw1 dead | rw1 step 1->0.4 at t=300 s, plus a tachometer
  noise/quantisation sweep.

  The dead-wheel case is fed twice from the SAME recorded trajectory:
    (i)  the command actually issued (the current allocator zeroes it), and
    (ii) the command a NON-oracle allocator would have issued (tau_des).
  Both are exact, because the applied torque on a dead wheel is h*tau = 0 either
  way, so the wheel-speed trajectory is identical -- only the regressor differs.
  This separates "unobservable in principle" from "merely never commanded".

Outputs: results/c2h/c2h_health_estimator.json, c2h_table.md, c2h_*.png
         reports/figures/c2h_validation.png (tracked)
Usage:   cd codes && PYTHONPATH=. ./venv/Scripts/python.exe scripts/c2h_health_estimator.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from satellite_adcs.environment.adcs_env import ADCSEnv
from satellite_adcs.health_estimation import Tachometer, WheelHealthEstimator

TOL = 0.05                    # acceptance tolerance on |h_hat - h|
HOLD_S = 1.0                  # deviation must persist this long to count as detected
RW_J = 2.0e-4
RW_MAX_TORQUE = 0.010
RW_MAX_SPEED = 628.3
DEC = 10                      # decimation for stored series


def _dither(k, amp=0.005, half=10):
    """Zero-mean square-wave wheel command.

    Keeps |omega| bounded so the plant never reaches the speed limit -- otherwise
    the (correct) saturation guard would legitimately refuse to update and the
    synthetic test would measure the guard instead of the estimator.
    """
    return -amp if (k // half) % 2 == 0 else +amp


def _median(xs):
    xs = [x for x in xs if x is not None]
    return None if not xs else round(float(np.median(xs)), 4)


# ============================================================== LEVEL A
def level_a():
    out = {}
    Tc = 0.2

    # ---- A1: exact identification, no noise -------------------------------
    est = WheelHealthEstimator(rw_J=RW_J, control_period=Tc, n_rw=1, lam=1.0,
                               p0=1.0, h_init=1.0)
    h_true = 0.5
    w = 0.0
    est.prime([w])
    hist = []
    for k in range(100):
        tau = _dither(k)                        # zero-mean -> no speed-limit contact
        w += -h_true * tau * Tc / RW_J          # exact plant: J dw = -h tau Tc
        est.update([tau], [w])
        hist.append(float(est.h[0]))
    out["A1_exact"] = {
        "h_true": h_true, "tau_cmd": "zero-mean square wave, +/-0.005",
        "n_updates": int(est.n_upd[0]),
        "h_hat_after_1_step": round(hist[0], 6),
        "h_hat_final": round(hist[-1], 8),
        "abs_err_final": round(abs(hist[-1] - h_true), 10),
        # lambda = 1 means P keeps shrinking, so convergence is ALGEBRAIC (~1/n),
        # not exponential -- report the trajectory rather than one final number.
        "abs_err_after_steps": {str(k): round(abs(hist[k - 1] - h_true), 6)
                                for k in (1, 5, 10, 25, 50, 100)},
    }

    # ---- A2: saturation trap, guarded vs unguarded ------------------------
    def sat_run(guards):
        e = WheelHealthEstimator(rw_J=RW_J, control_period=Tc, n_rw=1, lam=1.0,
                                 p0=1.0, h_init=1.0)
        w = RW_MAX_SPEED                     # pinned at the limit
        e.prime([w])
        tau = -0.010
        for _ in range(100):
            w = float(np.clip(w + (-1.0 * tau * Tc / RW_J),
                              -RW_MAX_SPEED, RW_MAX_SPEED))
            e.update([tau], [w], guards=guards)
        return e
    eg, eu = sat_run(True), sat_run(False)
    out["A2_saturation_trap"] = {
        "h_true": 1.0, "tau_cmd": -0.010, "steps": 100, "wheel_pinned_at_limit": True,
        "guarded_h_hat": round(float(eg.h[0]), 6),
        "guarded_skips": int(eg.n_skip_sat[0]),
        "UNguarded_h_hat": round(float(eu.h[0]), 6),
        "UNguarded_verdict": "FALSE DEAD WHEEL" if eu.h[0] < 0.5 else "ok",
    }

    # ---- A3: excitation gate ---------------------------------------------
    e = WheelHealthEstimator(rw_J=RW_J, control_period=Tc, n_rw=1, lam=0.98,
                             p0=1.0, h_init=1.0)
    e.prime([10.0])
    for _ in range(50):                       # wheel coasting, no command
        e.update([0.0], [10.0])
    out["A3_excitation_gate"] = {
        "tau_cmd": 0.0, "steps": 50,
        "h_hat": round(float(e.h[0]), 6),
        "age_s": round(float(e.age[0]), 2),
        "updates": int(e.n_upd[0]), "skips_excitation": int(e.n_skip_excite[0]),
    }

    # ---- A4: tracking a step 1.0 -> 0.4 ----------------------------------
    n1 = int(60.0 / Tc)
    n2 = int(120.0 / Tc)
    track, curves = {}, {}
    for lam in (1.0, 0.995, 0.98, 0.90):
        e = WheelHealthEstimator(rw_J=RW_J, control_period=Tc, n_rw=1, lam=lam,
                                 p0=1.0, h_init=1.0)
        w = 0.0
        e.prime([w])
        errs, run, delay, hh = [], 0, None, []
        for k in range(n1 + n2):
            h_true = 1.0 if k < n1 else 0.4
            tau = _dither(k)                    # zero-mean -> no speed-limit contact
            w += -h_true * tau * Tc / RW_J
            e.update([tau], [w])
            errs.append(abs(float(e.h[0]) - h_true))
            hh.append(float(e.h[0]))
            if k >= n1:
                run = run + 1 if errs[-1] <= TOL else 0
                if run >= int(HOLD_S / Tc) and delay is None:
                    delay = (k - n1) * Tc
        track[str(lam)] = {"delay_to_within_0.05_s": delay,
                           "h_hat_end": round(float(e.h[0]), 5),
                           "abs_err_end": round(errs[-1], 5)}
        curves[str(lam)] = hh
    out["A4_step_tracking"] = {"step_at_s": 60.0, "h_before": 1.0, "h_after": 0.4,
                               "by_lambda": track}
    out["_curves_A4"] = {"t": [k * Tc for k in range(n1 + n2)], "h": curves}
    return out


# ============================================================== LEVEL B
def _load_policy(model_dir):
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    m = PPO.load(os.path.join(model_dir, "ppo_adcs.zip"), device="cpu")
    vp = os.path.join(model_dir, "vecnormalize.pkl")
    vn = None
    if os.path.exists(vp):
        vn = VecNormalize.load(vp, DummyVecEnv([lambda: ADCSEnv()]))
        vn.training = False
    return m, vn


def _run_case(model, vecnorm, health, seed, sigma, quant, step_case=False,
              fault_at_s=300.0, tau_min_k=0.0):
    """Closed loop with the estimator in the loop. Records everything needed."""
    env = ADCSEnv(fault_mode="none", episode_time=900.0, control_hz=5.0, seed=seed)
    env.reset(seed=seed)
    env.dyn.set_rw_health(np.asarray(health, float))
    tacho = Tachometer(noise_std=sigma, quant_step=quant,
                       rng=np.random.default_rng(seed + 7))
    est = WheelHealthEstimator(rw_J=RW_J, control_period=env.control_period,
                               n_rw=3, lam=0.98, p0=1.0, h_init=1.0,
                               tacho_sigma=sigma, tau_min_k=tau_min_k)
    est.prime(tacho.measure(env.dyn.omega_w))
    keys = ("t", "h_hat", "h_true", "age", "tau_cmd", "tau_des", "w_meas")
    rec = {k: [] for k in keys}
    done = False
    while not done:
        o = env._obs()
        if vecnorm is not None:
            o = np.clip((o - vecnorm.obs_rms.mean) /
                        np.sqrt(vecnorm.obs_rms.var + 1e-8), -10, 10)
        act, _ = model.predict(o, deterministic=True)
        if step_case and env.dyn.t >= fault_at_s:
            env.dyn.rw_health[0] = health[0] if isinstance(health, tuple) else 0.4
        _, _, term, trunc, info = env.step(act)
        w_meas = tacho.measure(env.dyn.omega_w)
        est.update(info["tau_cmd"], w_meas)
        rec["t"].append(env.dyn.t)
        rec["h_hat"].append(est.h.copy())
        rec["h_true"].append(info["rw_health"].copy())
        rec["age"].append(est.age.copy())
        rec["tau_cmd"].append(info["tau_cmd"].copy())
        rec["tau_des"].append(np.asarray(act, float) * env.tau_scale * RW_MAX_TORQUE)
        rec["w_meas"].append(np.asarray(w_meas, float).copy())
        done = term or trunc
    env.close()
    for k in rec:
        rec[k] = np.asarray(rec[k])
    rec["diag"] = est.diagnostics()
    return rec


def _metrics(h_hat, h_true, t, age, i, onset_s=0.0):
    """Detection delay is measured FROM THE FAULT ONSET, never from t=0.

    For a static fault the onset is t=0; for the synthetic step case it is the step
    time. Measuring from t=0 would report a trivially small delay whenever the
    initial estimate happens to already match (h_init = 1.0 = healthy), which is
    what an earlier version of this script did.
    """
    err = np.abs(h_hat[:, i] - h_true[:, i])
    ag = age[:, i]
    dt = float(t[1] - t[0])
    n_hold = max(1, int(round(HOLD_S / dt)))
    k0 = int(round(onset_s / dt))
    already = bool(err[k0] <= TOL)
    run, delay = 0, None
    for k in range(k0, len(t)):
        run = run + 1 if err[k] <= TOL else 0
        if run >= n_hold:
            delay = float(t[k] - (n_hold - 1) * dt - onset_s)
            break
    tail = max(1, int(0.2 * len(t)))
    return {
        "onset_s": onset_s,
        "already_correct_at_onset": already,
        "detection_delay_s": None if delay is None else round(delay, 2),
        "abs_err_end": round(float(np.median(err[-tail:])), 5),
        "staleness_frac": round(float(np.mean(ag > 1.0)), 4),
        "updates": int(np.sum(ag == 0.0)),
        "h_true_final": float(h_true[-1, i]),
    }


def level_b(sigmas=(0.0, 0.05, 0.5), quant=0.0):
    model, vn = _load_policy(os.path.join(_ROOT, "results", "rl_shaped"))
    seeds = (0, 1, 2)
    out = {"cases": {}, "noise_sweep": {}}
    series = {}
    cases = [("healthy", [1.0, 1.0, 1.0], False),
             ("rw1_50", [0.5, 1.0, 1.0], False),
             ("rw1_dead", [0.0, 1.0, 1.0], False),
             ("rw1_step", [1.0, 1.0, 1.0], True)]

    for name, h, step_case in cases:
        per = []
        for s in seeds:
            rec = _run_case(model, vn, h, s, 0.0, quant, step_case=step_case)
            onset = 300.0 if step_case else 0.0
            m = _metrics(rec["h_hat"], rec["h_true"], rec["t"], rec["age"], 0,
                         onset_s=onset)
            m["tau_cmd_absmax"] = float(np.max(np.abs(rec["tau_cmd"][:, 0])))
            m["tau_des_absmax"] = float(np.max(np.abs(rec["tau_des"][:, 0])))
            m["updates_wheel0"] = int(np.sum(rec["age"][:, 0] == 0.0))
            m["unobservable_entirely"] = bool(m["updates_wheel0"] == 0)
            per.append(m)
            if s == 0:
                series[name] = {k: rec[k][::DEC] for k in ("t", "h_true", "age")}
                series[name]["h_hat"] = rec["h_hat"][::DEC]
                series[name]["tau_cmd"] = rec["tau_cmd"][::DEC]
                series[name]["tau_des"] = rec["tau_des"][::DEC]
        out["cases"][name] = {
            "per_seed": per,
            "delay_median_s": _median([p["detection_delay_s"] for p in per]),
            "err_end_median": _median([p["abs_err_end"] for p in per]),
            "staleness_median": _median([p["staleness_frac"] for p in per]),
            "tau_cmd_absmax_median": _median([p["tau_cmd_absmax"] for p in per]),
            "tau_des_absmax_median": _median([p["tau_des_absmax"] for p in per]),
            "updates_wheel0_median": _median([p["updates_wheel0"] for p in per]),
        }

    # counterfactual: same trajectory, regressor = what a NON-oracle allocator issues
    cf = []
    for s in seeds:
        rec = _run_case(model, vn, [0.0, 1.0, 1.0], s, 0.0, quant)
        e = WheelHealthEstimator(rw_J=RW_J, control_period=rec["t"][1] - rec["t"][0],
                                 n_rw=3, lam=0.98, p0=1.0, h_init=1.0)
        e.prime(rec["w_meas"][0])
        hs, ages = [], []
        for k in range(len(rec["t"])):
            e.update(rec["tau_des"][k], rec["w_meas"][k])
            hs.append(e.h[0]); ages.append(e.age[0])
        hs, ages = np.asarray(hs), np.asarray(ages)
        t = rec["t"]
        err = np.abs(hs - rec["h_true"][:, 0])
        dt = float(t[1] - t[0]); n_hold = max(1, int(round(HOLD_S / dt)))
        run, delay = 0, None
        for k in range(len(t)):
            run = run + 1 if err[k] <= TOL else 0
            if run >= n_hold:
                delay = float(t[k] - (n_hold - 1) * dt); break
        cf.append({"detection_delay_s": None if delay is None else round(delay, 2),
                   "h_hat_end": round(float(hs[-1]), 5),
                   "updates": int(np.sum(ages == 0.0))})
        if s == 0:
            series["rw1_dead_counterfactual"] = {
                "t": t[::DEC], "h_hat_cf": hs[::DEC],
                "h_true": rec["h_true"][::DEC, 0],
                "tau_des": rec["tau_des"][::DEC, 0]}
    out["cases"]["rw1_dead_counterfactual"] = {
        "description": ("identical wheel-speed trajectory; regressor = the command a "
                        "NON-oracle allocator would have issued (tau_des)"),
        "per_seed": cf,
        "delay_median_s": _median([c["detection_delay_s"] for c in cf]),
        "h_hat_end_median": _median([c["h_hat_end"] for c in cf]),
    }

    for name, h in (("healthy", [1.0, 1.0, 1.0]), ("rw1_50", [0.5, 1.0, 1.0])):
        rows = []
        for sigma in sigmas:
            for gate, k in (("fixed tau_min", 0.0), ("noise-matched k=3", 3.0)):
                ms = []
                for s in seeds:
                    rec = _run_case(model, vn, h, s, sigma, quant, tau_min_k=k)
                    ms.append(_metrics(rec["h_hat"], rec["h_true"], rec["t"],
                                       rec["age"], 0))
                rows.append({"sigma_rad_s": sigma, "gate": gate,
                             "tau_min_eff": round(max(1e-5, k * RW_J * np.sqrt(2.0)
                                                       * sigma / 0.2), 8),
                             "err_end_median": _median([m["abs_err_end"] for m in ms]),
                             "delay_median_s": _median([m["detection_delay_s"] for m in ms]),
                             "staleness_median": _median([m["staleness_frac"] for m in ms])})
        out["noise_sweep"][name] = rows
    return out, series


# ================================================================= outputs
def write_table(a, b, out_dir):
    L = ["# C2-h -- wheel-health estimator, offline validation\n",
         f"Tolerance |h_hat - h| <= {TOL}; deviation must persist >= {HOLD_S} s to "
         "count as detected. Estimator: per-wheel RLS (lambda=0.98) with excitation, "
         "saturation and plausibility guards.\n",
         "## Level A -- synthetic guard tests\n",
         "| test | result |", "|---|---|",
         f"| A1 exact identification (h=0.5, no noise) | h_hat final "
         f"{a['A1_exact']['h_hat_final']} (err {a['A1_exact']['abs_err_final']:.1e}); "
         "abs err after 1/10/100 steps = "
         + "/".join(str(a['A1_exact']['abs_err_after_steps'][k])
                     for k in ("1", "10", "100")) + " |",
         f"| A2 saturation trap, **guarded** | h_hat = {a['A2_saturation_trap']['guarded_h_hat']} "
         f"({a['A2_saturation_trap']['guarded_skips']} updates skipped) |",
         f"| A2 saturation trap, **unguarded** | h_hat = {a['A2_saturation_trap']['UNguarded_h_hat']} "
         f"-> **{a['A2_saturation_trap']['UNguarded_verdict']}** |",
         f"| A3 excitation gate (tau_cmd = 0) | h_hat = {a['A3_excitation_gate']['h_hat']}, "
         f"age = {a['A3_excitation_gate']['age_s']} s, "
         f"{a['A3_excitation_gate']['updates']} updates, no random walk |",
         "",
         "## Level A4 -- tracking a step 1.0 -> 0.4\n",
         "| lambda | delay to within 0.05 | h_hat at end |", "|---|---|---|"]
    for lam, v in a["A4_step_tracking"]["by_lambda"].items():
        L.append(f"| {lam} | {v['delay_to_within_0.05_s']} s | {v['h_hat_end']} |")
    L += ["", "## Level B -- closed loop, Baseline-C policy (wheel 0; medians over 3 seeds)\n",
          "| case | h_true | detection delay | abs err at end | staleness frac | updates | tau_cmd max |",
          "|---|---|---|---|---|---|---|"]
    for name, v in b["cases"].items():
        if name == "rw1_dead_counterfactual":
            L.append(f"| {name} | 0.0 | {v['delay_median_s']} s | "
                     f"h_hat end {v['h_hat_end_median']} | - | - | (non-oracle regressor) |")
            continue
        L.append(f"| {name} | {v['per_seed'][0]['h_true_final']:.1f} | "
                 f"{v['delay_median_s']} s | {v['err_end_median']} | "
                 f"{v['staleness_median']} | {v['updates_wheel0_median']} | "
                 f"{v['tau_cmd_absmax_median']} N.m |")
    L += ["", "## Level B -- tachometer noise / quantisation sweep\n",
          "The `tau_min_eff` column shows the excitation gate actually used. With a fixed",
          "absolute gate the sub-SNR updates bias the estimate; scaling the gate with the",
          "noise floor (`k=3` x J_w*sqrt(2)*sigma/T_c) removes the bias at the cost of staleness.\n",
          "| case | sigma [rad/s] | gate | tau_min_eff | abs err at end | delay | staleness |",
          "|---|---|---|---|---|---|---|"]
    for name, rows in b["noise_sweep"].items():
        for r in rows:
            L.append(f"| {name} | {r['sigma_rad_s']} | {r.get('gate', '-')} | "
                     f"{r.get('tau_min_eff', '-')} | {r['err_end_median']} | "
                     f"{r['delay_median_s']} s | {r['staleness_median']} |")
    p = os.path.join(out_dir, "c2h_table.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"saved {p}", flush=True)


def write_figures(a, series, out_dir):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:                                     # pragma: no cover
        print(f"figure skipped: {e}")
        return
    # series may come straight from the in-memory pass (ndarrays) or from the saved
    # JSON (lists) -- normalise so both paths index identically.
    series = {k: {kk: (np.asarray(vv) if isinstance(vv, (list, tuple)) else vv)
                  for kk, vv in v.items()} for k, v in series.items()}
    fig, ax = plt.subplots(2, 2, figsize=(13.5, 8))

    # (a) A4 tracking
    for lam, hh in a["_curves_A4"]["h"].items():
        ax[0, 0].plot(a["_curves_A4"]["t"], hh, lw=1.5, label=f"lambda={lam}")
    ax[0, 0].axhline(1.0, color="k", ls=":", lw=1)
    ax[0, 0].axhline(0.4, color="k", ls=":", lw=1)
    ax[0, 0].axvline(60.0, color="r", ls="--", lw=1, label="fault step")
    ax[0, 0].set_xlabel("time [s]"); ax[0, 0].set_ylabel("h_hat")
    ax[0, 0].set_title("A4  tracking a health step 1.0 -> 0.4"); ax[0, 0].grid(alpha=.3)
    ax[0, 0].legend(fontsize=7)

    # (b) saturation trap bars
    names = ["guarded", "unguarded"]
    vals = [a["A2_saturation_trap"]["guarded_h_hat"],
            a["A2_saturation_trap"]["UNguarded_h_hat"]]
    ax[0, 1].bar(names, vals, color=["tab:green", "tab:red"])
    ax[0, 1].axhline(1.0, color="k", ls=":", lw=1)
    ax[0, 1].set_ylim(0, 1.15); ax[0, 1].set_ylabel("h_hat after 100 steps at the speed limit")
    ax[0, 1].set_title("A2  saturation trap: h_true = 1.0 (healthy)")
    for i, v in enumerate(vals):
        ax[0, 1].text(i, v + 0.03, f"{v:.3f}", ha="center", fontsize=9)

    # (c) closed loop, wheel 0
    for name, order in (("healthy", 0), ("rw1_50", 1), ("rw1_dead", 2)):
        s = series[name]
        ax[1, 0].plot(s["t"], s["h_hat"][:, 0], lw=1.6,
                      label=f"{name} (h_true={s['h_true'][-1,0]:.1f})")
        ax[1, 0].axhline(s["h_true"][-1, 0], color="k", ls=":", lw=0.8)
    s = series["rw1_dead_counterfactual"]
    ax[1, 0].plot(s["t"], s["h_hat_cf"], lw=1.6, ls="--", color="tab:purple",
                  label="rw1_dead, NON-oracle regressor")
    ax[1, 0].set_xlabel("time [s]"); ax[1, 0].set_ylabel("h_hat (wheel 0)")
    ax[1, 0].set_ylim(-0.05, 1.15)
    ax[1, 0].set_title("closed loop, wheel 0"); ax[1, 0].grid(alpha=.3)
    ax[1, 0].legend(fontsize=7)

    # (d) tau_cmd on wheel 0 -- why the dead wheel is unobservable
    ax[1, 1].plot(series["rw1_dead"]["t"], np.abs(series["rw1_dead"]["tau_cmd"][:, 0]),
                  lw=1.4, label="|tau_cmd| issued (oracle allocator)")
    ax[1, 1].plot(series["rw1_dead"]["t"], np.abs(series["rw1_dead"]["tau_des"][:, 0]),
                  lw=1.4, ls="--", label="|tau_des| (non-oracle would issue)")
    ax[1, 1].set_xlabel("time [s]"); ax[1, 1].set_ylabel("|tau| on wheel 0 [N.m]")
    ax[1, 1].set_title("why a dead wheel is unobservable today")
    ax[1, 1].grid(alpha=.3); ax[1, 1].legend(fontsize=7)

    fig.suptitle("C2-h  wheel-health estimator -- offline validation", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    p1 = os.path.join(out_dir, "c2h_validation.png")
    fig.savefig(p1, dpi=140)
    print(f"saved {p1}", flush=True)
    tdir = os.path.join(os.path.dirname(_ROOT), "reports", "figures")
    if os.path.isdir(tdir):
        p2 = os.path.join(tdir, "c2h_validation.png")
        fig.savefig(p2, dpi=140)
        print(f"saved {p2}", flush=True)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-only", action="store_true",
                    help="reload the saved JSON and regenerate table + figures only")
    args = ap.parse_args()
    out_dir = os.path.join("results", "c2h")
    os.makedirs(out_dir, exist_ok=True)
    if args.report_only:
        p = os.path.join(out_dir, "c2h_health_estimator.json")
        with open(p, encoding="utf-8") as f:
            r = json.load(f)
        a, b, series = r["level_a"], r["level_b"], r["series"]
        write_table(a, b, out_dir)
        write_figures(a, series, out_dir)
        print("report-only: table + figures regenerated", flush=True)
        return 0
    print("LEVEL A -- synthetic guard tests", flush=True)
    a = level_a()
    for k, v in a.items():
        if k.startswith("_"):
            continue
        print(f"  {k}: {json.dumps(v)}", flush=True)
    print("\nLEVEL B -- closed loop with the trained Baseline-C policy", flush=True)
    b, series = level_b()
    for name, v in b["cases"].items():
        print(f"  {name}: "
              f"{json.dumps({k: x for k, x in v.items() if k != 'per_seed'})}", flush=True)
    for name, rows in b["noise_sweep"].items():
        for r in rows:
            print(f"  sweep {name} sigma={r['sigma_rad_s']}: {json.dumps(r)}", flush=True)

    def _jsonable(o):
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, dict):
            return {k: _jsonable(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_jsonable(v) for v in o]
        return o

    report = {"study": "C2-h wheel-health estimator, offline validation",
              "tolerance": TOL, "hold_s": HOLD_S, "level_a": a, "level_b": b,
              "series": series}
    p = os.path.join(out_dir, "c2h_health_estimator.json")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_jsonable(report), f, indent=2)   # atomic: never leave a half file
    os.replace(tmp, p)
    print(f"\nsaved {p}", flush=True)
    write_table(a, b, out_dir)
    write_figures(a, series, out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
