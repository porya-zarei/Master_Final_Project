"""M1-C: classical LQR path versus residual-wrapper (a=0) parity. Diagnostic only."""
import sys, os, json
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from satellite_adcs.config import load_config
from satellite_adcs.environment.adcs_env import ADCSEnv
from satellite_adcs.environment.residual_env import ResidualADCSEnv
from simulate import run_episode, make_ic_bias

# TOLERANCE DECLARED BEFORE THE COMPARISON (not chosen after seeing numbers)
TOL_MEDIAN_DEG = 0.05
TOL_VECTOR_DEG = 0.02

def classical(cfg, s):
    q0, w0, b = make_ic_bias(s)
    r = run_episode(cfg, seed=s, T=900.0, ic=(q0, w0), gyro_bias=b, controller="lqr")
    return float(r["pe"][-1])

def wrapper(cfg, s, coulomb):
    ov = {"actuators": {"reaction_wheels": {"friction_coulomb_Nm": coulomb}}}
    e = ResidualADCSEnv(ADCSEnv(fault_mode="none", episode_time=900.0, control_hz=5.0,
                                seed=s, overrides=ov), alpha=0.2)
    q0, w0, b = make_ic_bias(s)
    o, _ = e.reset(seed=s, options={"q": q0, "omega": w0, "gyro_bias": b})
    d = False; pe = []
    while not d:
        o, r, t, tr, i = e.step(np.zeros(3)); pe.append(e.unwrapped.pointing_error_deg()); d = t or tr
    return float(pe[-1])

out = {}
print("M1-C  classical LQR vs wrapper(a=0) parity")
print(f"declared tolerance: median diff <= {TOL_MEDIAN_DEG} deg, per-episode <= {TOL_VECTOR_DEG} deg\n")
for cond, c in (("ideal", 0.0), ("coulomb_2e4", 2e-4)):
    cfg = load_config()
    if c > 0:
        cfg = load_config({"actuators": {"reaction_wheels": {"friction_coulomb_Nm": c}}})
    cl = [classical(cfg, s) for s in range(6)]
    wr = [wrapper(cfg, s, c) for s in range(6)]
    diffs = np.array(wr) - np.array(cl)
    med_d = float(abs(np.median(wr) - np.median(cl)))
    max_d = float(np.max(np.abs(diffs)))
    ok = (med_d <= TOL_MEDIAN_DEG) and (max_d <= TOL_VECTOR_DEG)
    print(f"[{cond}] classical median {np.median(cl):.4f}  wrapper median {np.median(wr):.4f}")
    print(f"        median diff {med_d:.4f}  max per-episode diff {max_d:.4f}  -> {'PASS' if ok else 'FAIL'}")
    print(f"        per-episode diffs: {np.round(diffs,4).tolist()}\n")
    out[cond] = {"classical": [round(v,4) for v in cl], "wrapper": [round(v,4) for v in wr],
                 "median_diff": med_d, "max_diff": max_d, "pass": bool(ok)}
out["tolerance_pre_declared"] = {"median_deg": TOL_MEDIAN_DEG, "per_episode_deg": TOL_VECTOR_DEG}
json.dump(out, open("results/m1/m1c_lqr_parity.json", "w"), indent=2)
print("saved results/m1/m1c_lqr_parity.json")
