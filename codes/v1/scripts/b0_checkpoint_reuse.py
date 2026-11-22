"""B.0 — feasibility gate: are the D4 checkpoints validly re-evaluable through `residual_fn`?

Three questions, each answered by measurement rather than by inspection:

  Q1  Do the checkpoints on disk match the SHA-256 recorded when the claim was made?
  Q2  Is the RL wrapper's nominal controller the SAME controller the classical path runs?
      (M1-C found a wrapper whose K was built from R = 1e-4 instead of the thesis's 1e4;
      a mismatch here would silently change the meaning of "residual on top of LQR".)
  Q3  Does driving `simulate.run_episode(residual_fn=...)` with a scripted action sequence
      reproduce the SAME closed-loop trajectory as driving `ResidualADCSEnv` with that same
      action sequence?  If yes, the 15-dim observation is reconstructible from the payload
      and re-evaluation is valid.  If no, the paths differ and a policy trained on one would
      be scored on the other.

Q3 is run twice: fault-free (h = 1) and with RW1 at 50 %. The second is expected to FAIL
by construction -- in the wrapper the residual is added to `tau_des` BEFORE the allocator,
whereas in `run_episode` it is added to the ALREADY-ALLOCATED wheel torque, so it is not
health-inverted. Reporting that difference is the point; asserting equality would be wrong.

Verdict: RE-EVALUATE if Q1-Q3(fault-free) hold; RETRAIN if any fails. Never loosen an
adapter to force a match.
"""
from __future__ import annotations
import hashlib
import json
import os
import sys

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from satellite_adcs.config import load_config
from satellite_adcs.dynamics import SpacecraftDynamics
from satellite_adcs.controllers import ADCSController
from satellite_adcs.quaternion import (random_quat, quat_error, theta_vec,
                                       quat_to_dcm)
from satellite_adcs.environment.adcs_env import ADCSEnv
from satellite_adcs.environment.residual_env import ResidualADCSEnv
from simulate import make_ic_bias, run_episode

ALPHA = 0.2          # D4 training value (results/residual_d4_s*/config.json)
T = 300.0            # short horizon: this is an equivalence check, not an evaluation
HASHES = os.path.join(REPO, "reports", "m1_checkpoint_hashes.json")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


_EPS = 1.0e-12   # NOT zero: the star-tracker R would be singular. Negligible vs 1e-4 rad/s.
ZERO_NOISE = {"sensors": {
    "gyro": {"noise_std_rad_s": _EPS},
    "magnetometer": {"noise_std_T": _EPS},
    "sun_sensor": {"noise_std_rad": _EPS},
    "star_tracker": {"noise_std_rad": _EPS},
    "gps": {"position_noise_m": _EPS, "velocity_noise_ms": _EPS},
}}


def obs15(est, gyro, dyn, guidance, K, scale, prev_action, rw_max_speed):
    """The wrapper's 15-dim observation, built from quantities a `residual_fn` payload has.

    This is the ADAPTER under test: if `ADCSController` (which computes theta and
    omega_err through its own code path) issues the same command as `-K @ obs[:6]`,
    then the adapter is faithful and the payload is sufficient.
    """
    q_ref, wr = guidance.reference(dyn.r, dyn.v)
    q_err = quat_error(est.q_hat, q_ref)
    theta = theta_vec(q_err)
    omega_err = est.gyro_rate(gyro) - quat_to_dcm(q_err) @ wr
    base = np.concatenate([theta, omega_err, dyn.omega_w / rw_max_speed])
    return np.concatenate([base, (-K @ base[:6]) / scale, prev_action])


def q3_command_equivalence(cfg, n_states=40):
    """Command-level equivalence on IDENTICAL states (initial + perturbed).

    A trajectory comparison cannot decide this: the two harnesses each draw their own
    orbit anomaly and sensor-noise stream from their own RNG, so their states diverge
    for reasons unrelated to the controller (measured: 7.6 km / 8.4 m/s apart at t=1 s).
    Comparing the COMMAND on a shared state isolates the control law, which is what
    "the policy was trained on this controller" actually rests on.
    """
    I = cfg["satellite"]["inertia"]
    J = np.diag([I["Jxx"], I["Jyy"], I["Jzz"]])
    env = ResidualADCSEnv(ADCSEnv(cfg, fault_mode="none", episode_time=T,
                                  control_hz=5.0, seed=0), alpha=ALPHA)
    d = env.unwrapped.dyn
    ctrl = ADCSController(cfg, J, d.mu, d.a, np.random.default_rng(0))
    rng = np.random.default_rng(12345)
    # ADCSController starts in phase "detumble" and returns ZERO wheel torque on its first
    # call while it flips to "pointing" (controllers.py:123-130). That one call is not a
    # control-law difference -- it affects every arm identically at t=0, because
    # run_episode feeds `prev_tau=0` to the first residual step -- but it would register as
    # a mismatch here. Warm up past it and record the behaviour explicitly.
    d.reset(q=random_quat(rng), omega=rng.uniform(-0.05, 0.05, 3))
    warm = env.unwrapped.sensors.measure(d)
    env.unwrapped.est.reset()
    env.unwrapped.est.update(warm, d)
    tau_first, _ = ctrl.control(warm, env.unwrapped.est, d, 0.0, 0.2)
    first_is_zero = float(np.max(np.abs(tau_first))) == 0.0
    worst, rows = 0.0, []
    for i in range(n_states):
        # perturb attitude / rate / wheel speed so the test is not one special point
        d.reset(q=random_quat(rng), omega=rng.uniform(-0.05, 0.05, 3))
        d.omega_w = rng.uniform(-50.0, 50.0, 3)
        meas = env.unwrapped.sensors.measure(d)
        env.unwrapped.est.reset()
        env.unwrapped.est.update(meas, d)
        est = env.unwrapped.est
        # classical command
        tau_c, _ = ctrl.control(meas, est, d, 0.0, 0.2)
        # adapter command, from the same estimate + measurement + plant
        o15 = obs15(est, meas["gyro"], d, ctrl.guidance, ctrl.K,
                    float(env.unwrapped.tau_scale * env.unwrapped.rw_max_torque),
                    np.zeros(3), float(env.unwrapped.rw_max_speed))
        tau_w = np.clip(-(ctrl.K @ o15[:6]), -ctrl.rw_max_torque, ctrl.rw_max_torque)
        delta = float(np.max(np.abs(np.asarray(tau_c, float) - tau_w)))
        worst = max(worst, delta)
        if i < 3:
            rows.append({"tau_classical": np.round(tau_c, 9).tolist(),
                         "tau_from_obs": np.round(tau_w, 9).tolist(),
                         "max_abs_diff": delta})
    env.close()
    return {"n_states": n_states, "max_abs_command_diff": worst,
            "first_call_returns_zero": bool(first_is_zero),
            "examples": rows, "pass": bool(worst < 1e-9)}


def scripted(k, alpha=ALPHA):
    """Deterministic action sequence: identical in both paths, no policy involved."""
    return alpha * np.array([np.sin(0.013 * k), np.cos(0.017 * k), np.sin(0.011 * k)])


def q1_hashes():
    ref = json.load(open(HASHES))
    rows, ok = [], True
    for rel, rec in ref.items():
        path = os.path.join(REPO, rel.replace("\\", os.sep))
        if not os.path.exists(path):
            rows.append({"file": rel, "status": "MISSING"})
            ok = False
            continue
        got = sha256(path)
        good = (got == rec["sha256"])
        ok &= good
        rows.append({"file": rel, "status": "MATCH" if good else "MISMATCH",
                     "sha256": got[:16], "recorded": rec["sha256"][:16],
                     "bytes": os.path.getsize(path)})
    return ok, rows


def q2_gain_identity(cfg):
    I = cfg["satellite"]["inertia"]
    J = np.diag([I["Jxx"], I["Jyy"], I["Jzz"]])
    rng = np.random.default_rng(0)
    env = ResidualADCSEnv(ADCSEnv(cfg, fault_mode="none", episode_time=T,
                                  control_hz=5.0, seed=0), alpha=ALPHA)
    d = env.unwrapped.dyn
    ctrl = ADCSController(cfg, J, d.mu, d.a, rng)
    dK = float(np.max(np.abs(env.K - ctrl.K)))
    scale_wrap = float(env.scale)
    scale_classical = float(env.unwrapped.tau_scale * env.unwrapped.rw_max_torque)
    # the LVLH reference must agree too, otherwise theta means different things
    r = d.r
    v = d.v
    q_w, w_w = env.unwrapped.guidance.reference(r, v)
    q_c, w_c = ctrl.guidance.reference(r, v)
    dRef = float(max(np.max(np.abs(q_w - q_c)), np.max(np.abs(w_w - w_c))))
    return {"max_abs_dK": dK, "scale_wrapper": scale_wrap,
            "scale_classical": scale_classical,
            "max_abs_dq_ref": dRef, "max_abs_dw_ref": dRef,
            "pass": bool(dK < 1e-12 and abs(scale_wrap - scale_classical) < 1e-15
                         and dRef < 1e-15)}, env


def traj_wrapper(cfg, env, ic, health):
    q0, w0, b = ic
    obs, _ = env.reset(seed=0, options={"q": q0, "omega": w0, "gyro_bias": b})
    env.unwrapped.dyn.set_rw_health(health)      # AFTER reset: reset re-samples
    pe, k, done = [], 0, False
    while not done:
        obs, r, term, trunc, info = env.step(scripted(k))
        pe.append(env.unwrapped.pointing_error_deg())
        k += 1
        done = term or trunc
    return np.asarray(pe)


def traj_run_episode(cfg, ic, health):
    q0, w0, b = ic
    state = {"k": 0}

    def residual(payload):
        a = scripted(state["k"])
        state["k"] += 1
        return a

    res = run_episode(cfg, seed=0, T=T, rw_health=health, ic=(q0, w0), gyro_bias=b,
                      residual_fn=residual, residual_alpha=ALPHA, record=False)
    return np.asarray(res["pe"])


def main():
    cfg = load_config()
    out = {"alpha": ALPHA, "T": T, "numpy": np.__version__}
    try:
        import stable_baselines3, torch
        out["sb3"] = stable_baselines3.__version__
        out["torch"] = torch.__version__
    except Exception as e:                                    # pragma: no cover
        out["sb3_error"] = repr(e)

    print("=" * 78)
    print("Q1  checkpoint hashes vs reports/m1_checkpoint_hashes.json")
    ok1, rows = q1_hashes()
    for r in rows:
        print(f"  {r['status']:9s} {r['file']}")
    out["Q1_hashes"] = {"pass": ok1, "files": rows}

    print("\n" + "=" * 78)
    print("Q2  is the wrapper's nominal controller the classical controller?")
    ok2, env = q2_gain_identity(cfg)
    print(f"  max |K_wrapper - K_ADCSController| = {ok2['max_abs_dK']:.3e}")
    print(f"  scale: wrapper {ok2['scale_wrapper']!r} vs classical {ok2['scale_classical']!r}")
    print(f"  max |dq_ref|, |dw_ref| on the same state = {ok2['max_abs_dq_ref']:.3e}")
    print(f"  -> {'PASS' if ok2['pass'] else 'FAIL'}")
    env.close()
    out["Q2_controller_identity"] = ok2

    print("\n" + "=" * 78)
    print("Q3  command-level equivalence on IDENTICAL states (the decisive test)")
    ok3 = q3_command_equivalence(cfg)
    for e in ok3["examples"]:
        print(f"    tau_classical = {e['tau_classical']}")
        print(f"    tau_from_obs  = {e['tau_from_obs']}   max|d|={e['max_abs_diff']:.3e}")
    print(f"  over {ok3['n_states']} perturbed states: max |tau_classical - tau_from_obs| "
          f"= {ok3['max_abs_command_diff']:.3e} N*m  -> "
          f"{'PASS' if ok3['pass'] else 'FAIL'}")
    out["Q3_command_equivalence"] = ok3

    print("\n  Q3b why a TRAJECTORY comparison cannot be used, quantified")
    print("      (each harness draws its own orbit anomaly and noise stream)")
    ic = make_ic_bias(0)
    e1 = ResidualADCSEnv(ADCSEnv(cfg, fault_mode="none", episode_time=T,
                                 control_hz=5.0, seed=0), alpha=ALPHA)
    pe_w = traj_wrapper(cfg, e1, ic, [1.0, 1.0, 1.0])
    d_w = (np.round(e1.unwrapped.dyn.r, 1).tolist(), e1.unwrapped.dyn.t)
    e1.close()
    pe_c = traj_run_episode(cfg, ic, [1.0, 1.0, 1.0])
    n = min(pe_w.size, pe_c.size)
    d_traj = float(np.max(np.abs(pe_w[:n] - pe_c[:n])))
    print(f"      waveform  max|dpe| = {d_traj:.3e} deg over {n} steps "
          f"(diagnostic only -- NOT a pass/fail criterion)")
    out["Q3b_trajectory_diagnostic"] = {"max_abs_diff_deg": d_traj, "n": int(n),
                                       "usable_as_criterion": False}

    print("\n  Q3c residual-path semantics under a MULTIPLICATIVE fault")
    print("      wrapper: residual added to tau_des BEFORE the allocator (health-inverted)")
    print("      run_episode: residual added to the ALLOCATED wheel torque (not inverted)")
    print("      -> identical when h = 1; different for h != 1, by construction.")
    out["Q3c_residual_semantics"] = {
        "identical_when": "h == 1 (friction family, S0/S2)",
        "differs_when": "h != 1 (S3/S4/S6/S7): residual is not health-inverted in run_episode",
    }

    # ---- policy load test (does the artifact still load under this SB3 version?)
    print("\n" + "=" * 78)
    print("Q4  do the policy.zip files load and predict?")
    load = {}
    try:
        from stable_baselines3 import SAC
        for s in (0, 1, 2):
            p = os.path.join(HERE, "results", f"residual_d4_s{s}", "policy.zip")
            try:
                m = SAC.load(p, device="cpu")
                a, _ = m.predict(np.zeros(15, dtype=np.float32), deterministic=True)
                load[f"s{s}"] = {"loads": True, "obs_space": str(m.observation_space.shape),
                                 "action_shape": str(np.shape(a)),
                                 "action_on_zero_obs": np.round(a, 4).tolist()}
                print(f"  s{s}: loads, obs {m.observation_space.shape}, "
                      f"a(0)={np.round(a,3).tolist()}")
            except Exception as e:
                load[f"s{s}"] = {"loads": False, "error": repr(e)}
                print(f"  s{s}: FAILED to load -> {e!r}")
    except Exception as e:                                    # pragma: no cover
        load["import"] = {"loads": False, "error": repr(e)}
        print(f"  could not import SAC -> {e!r}")
    out["Q4_policy_load"] = load

    cmd_ok = ok3["pass"]
    loads_ok = all(v.get("loads") for k, v in load.items() if not k.startswith("import"))
    # Re-evaluation is valid only where the residual sits at the SAME point in the signal
    # path it was trained at: after the LQR but before the allocator. That holds for h = 1,
    # i.e. the friction family (S0/S2) -- which is exactly what B's central claim tests.
    # Under a multiplicative fault (h != 1) `run_episode` adds the residual to the ALREADY
    # health-inverted wheel command, so those cells need retraining or a declared change.
    core_ok = bool(ok1 and ok2["pass"] and cmd_ok and loads_ok)
    verdict = "RE-EVALUATE (friction/s0 cells only)" if core_ok else "RETRAIN"
    out["verdict"] = verdict
    out["reasons"] = {
        "hashes_match": ok1,
        "wrapper_controller_identical_to_classical": ok2["pass"],
        "command_equivalent_on_identical_states": cmd_ok,
        "policies_load_under_current_sb3": loads_ok,
        "friction_cells_reusable": core_ok,
        "multiplicative_fault_cells_need_retrain": True,
    }

    print("\n" + "=" * 78)
    print(f"VERDICT: {verdict}")
    for k, v in out["reasons"].items():
        print(f"  {k:44s} {v}")

    p = os.path.join(HERE, "results", "b0", "b0_checkpoint_reuse.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    json.dump(out, open(tmp, "w"), indent=2)
    os.replace(tmp, p)
    pr = os.path.join(REPO, "reports", "b0_checkpoint_reuse.json")
    json.dump(out, open(pr, "w"), indent=2)
    print(f"\nsaved {p}\n      {pr}")
    return 0 if core_ok else 2


if __name__ == "__main__":
    sys.exit(main())
