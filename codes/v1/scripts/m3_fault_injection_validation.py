"""Stage 3: independent validation of fault injection + joint parameter identification.

Gate: do NOT integrate the estimator into the allocator unless BOTH tau_f and h are
demonstrated against verified physical fault injection.

Fault application, traced:
  ADCSEnv.reset()  ->  self.dyn.set_rw_health(self._sample_health())    (line 182)
  ADCSEnv.step()   ->  uses dyn.rw_health in derivatives: tau_rw_eff = tau_rw * health
  => health must be set AFTER reset; setting it before is overwritten.
"""
from __future__ import annotations
import sys, os, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from satellite_adcs.environment.adcs_env import ADCSEnv
from satellite_adcs.environment.residual_env import ResidualADCSEnv
from satellite_adcs.friction_estimation import FrictionHealthEstimator
from simulate import make_ic_bias

TOL_H = 0.15
TOL_F = 5e-5

CASES = [
    ("healthy_no_friction", [1.0, 1.0, 1.0], 0.0),
    ("healthy_coulomb_2e4", [1.0, 1.0, 1.0], 2e-4),
    ("rw1_50_no_friction",  [0.5, 1.0, 1.0], 0.0),
    ("rw1_50_coulomb_2e4",  [0.5, 1.0, 1.0], 2e-4),
    ("rw1_dead_no_friction", [0.0, 1.0, 1.0], 0.0),
]


def run(health, coulomb, seed=0):
    ov = {"actuators": {"reaction_wheels": {"friction_coulomb_Nm": coulomb}}}
    env = ResidualADCSEnv(ADCSEnv(fault_mode="none", episode_time=900.0,
                                  control_hz=5.0, seed=seed, overrides=ov), alpha=0.2)
    q, w, b = make_ic_bias(seed)
    env.reset(seed=seed, options={"q": q, "omega": w, "gyro_bias": b})
    # AFTER reset -- this is the fix; step() does not re-sample
    env.unwrapped.dyn.set_rw_health(health)
    d = env.unwrapped.dyn
    est = FrictionHealthEstimator(rw_J=float(d.rw_J),
                                  control_period=env.unwrapped.control_period, n_rw=3)
    est.prime(d.omega_w)

    prev_om = np.asarray(d.omega_w, float).copy()
    rec = {"cmd": [], "deliv": [], "dw": [], "fric": [], "h_true": []}
    done = False
    while not done:
        obs, r, t, tr, info = env.step(np.zeros(3))
        done = t or tr
        tau_cmd = np.asarray(info.get("tau_cmd", np.zeros(3)), float).copy()
        om = np.asarray(d.omega_w, float).copy()
        rec["cmd"].append(tau_cmd)
        rec["deliv"].append(tau_cmd * np.asarray(d.rw_health, float))
        rec["dw"].append((om - prev_om) / env.unwrapped.control_period)
        om_mid = 0.5 * (om + prev_om)
        rec["fric"].append(-(d.rw_b_visc * om_mid
                             + d.rw_c_coul * np.tanh(om_mid / 0.05)))
        rec["h_true"].append(np.asarray(d.rw_health, float).copy())
        est.update(tau_cmd, om)
        prev_om = om

    out = {k: np.array(v) for k, v in rec.items()}
    return out, est


def main():
    results = {}
    print("Stage 3  fault-injection + joint identification validation\n")
    all_ok = True
    for name, health, coulomb in CASES:
        rec, est = run(health, coulomb, seed=0)
        h_true_final = rec["h_true"][-1]
        # physical check: delivered must be health * commanded
        ratio = np.divide(rec["deliv"][-1], rec["cmd"][-1],
                          out=np.full(3, np.nan), where=np.abs(rec["cmd"][-1]) > 1e-9)
        h_hat, tf_hat = est.h, est.tau_f
        # expected friction torque in the tau_f convention (signed)
        tf_true = float(np.median(rec["fric"][-200:, 0])) if coulomb > 0 else 0.0
        e_h = float(np.max(np.abs(h_hat - h_true_final)))
        e_f = abs(float(tf_hat[0]) - tf_true)
        ok_h = e_h < TOL_H
        ok_f = e_f < TOL_F
        all_ok &= (ok_h and ok_f)
        results[name] = {
            "health_commanded": health, "coulomb": coulomb,
            "h_true_final": h_true_final.tolist(),
            "delivered_over_commanded": [None if np.isnan(v) else round(float(v), 4) for v in ratio],
            "h_hat": np.round(h_hat, 4).tolist(),
            "tau_f_hat": np.round(tf_hat, 8).tolist(),
            "tau_f_true_median": tf_true,
            "err_h": round(e_h, 4), "err_tau_f": e_f,
            "pass_h": bool(ok_h), "pass_tau_f": bool(ok_f),
        }
        print(f"[{name}]  h_true={np.round(h_true_final,2)}  coulomb={coulomb}")
        print(f"   delivered/commanded = {results[name]['delivered_over_commanded']}"
              f"   (must equal h_true where |cmd|>0)")
        print(f"   h_hat={np.round(h_hat,3)}  err={e_h:.3f}  {'OK' if ok_h else 'FAIL'}")
        print(f"   tau_f_hat={tf_hat[0]:+.3e}  tau_f_true={tf_true:+.3e}"
              f"  err={e_f:.1e}  {'OK' if ok_f else 'FAIL'}\n")

    print("GATE:", "PASS -> integration authorised" if all_ok else "FAIL -> stop, do not integrate")
    os.makedirs("results/m3", exist_ok=True)
    with open("results/m3/fault_injection_validation.json", "w") as f:
        json.dump({"tolerances": {"h": TOL_H, "tau_f": TOL_F},
                   "gate": "PASS" if all_ok else "FAIL", "cases": results}, f, indent=2)
    print("saved results/m3/fault_injection_validation.json")


if __name__ == "__main__":
    main()
