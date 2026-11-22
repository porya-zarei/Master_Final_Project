"""M1-A: physical signal, wheel dynamics and D5 excitation-guard audit.

DIAGNOSTIC ONLY. Reads the plant, modifies nothing. Compares the two candidate
residual conventions against the plant's own friction torque, and reports the
estimator guard's behaviour.

The implemented wheel equation (dynamics.py) is

    J_w * d(omega_w)/dt = -tau_rw_eff + tau_f
    tau_f = -(b_visc * omega_w + c_coul * tanh(omega_w / 0.05))

so the model-based residual is  tau_f = tau_cmd + J_w*d(omega_w)/dt.
D5 used             tau_cmd - J_w*d(omega_w)/dt  (sign inverted on the derivative).
"""
from __future__ import annotations
import sys, os, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from satellite_adcs.environment.adcs_env import ADCSEnv
from satellite_adcs.environment.residual_env import ResidualADCSEnv
from simulate import make_ic_bias

T_EP = 900.0
CASES = [("ideal", 0.0), ("coulomb_2e-4", 2e-4), ("coulomb_3e-4", 3e-4)]


def run(coulomb, seed=2):
    ov = {"actuators": {"reaction_wheels": {"friction_coulomb_Nm": coulomb}}}
    # ADCSEnv is PLANT-ONLY: the action IS the torque. Driving it with a=0 applies
    # ZERO control input, which is what made D5's "no excitation" result an artifact.
    # The LQR lives in the residual wrapper, so a=0 here means "LQR only".
    env = ResidualADCSEnv(ADCSEnv(fault_mode="none", episode_time=T_EP,
                                  control_hz=5.0, seed=seed, overrides=ov),
                          alpha=0.2)
    q0, w0, bias = make_ic_bias(seed)
    obs, _ = env.reset(seed=seed, options={"q": q0, "omega": w0, "gyro_bias": bias})
    d = env.unwrapped.dyn
    period = env.unwrapped.control_period
    Jw = float(d.rw_J)

    rows = []
    prev_om = None
    done = False
    while not done:
        obs, r, term, trunc, info = env.step(np.zeros(3))   # a = 0 -> pure LQR
        done = term or trunc
        om = np.asarray(d.omega_w, float).copy()
        if prev_om is None:
            prev_om = om
            continue
        dw = (om - prev_om) / period
        tau_cmd = np.asarray(info.get("tau_cmd", np.zeros(3)), float)
        om_mid = 0.5 * (om + prev_om)
        tau_f_true = -(d.rw_b_visc * om_mid
                       + d.rw_c_coul * np.tanh(om_mid / 0.05))
        rows.append({
            "tau_cmd": tau_cmd.tolist(),
            "dw": dw.tolist(),
            "naive": (tau_cmd - Jw * dw).tolist(),        # D5 convention
            "corrected": (tau_cmd + Jw * dw).tolist(),    # from the source
            "true": tau_f_true.tolist(),
        })
        prev_om = om
    return {"rows": rows, "Jw": Jw,
            "guards": {"n_upd": env.unwrapped.health_est.n_upd.tolist(),
                       "skip_excite": env.unwrapped.health_est.n_skip_excite.tolist(),
                       "skip_sat": env.unwrapped.health_est.n_skip_sat.tolist(),
                       "skip_plaus": env.unwrapped.health_est.n_skip_plaus.tolist()}}


def summarise(rows, key, skip=200):
    arr = np.array([r[key] for r in rows[skip:]])
    true = np.array([r["true"] for r in rows[skip:]])
    err = np.abs(arr - true)
    return {"median_abs": float(np.median(np.abs(arr))),
            "median_abs_err_vs_true": float(np.median(err)),
            "p90_abs_err_vs_true": float(np.percentile(err, 90))}


def main():
    out = {}
    print("M1-A  wheel-dynamics and residual-convention audit\n")
    for name, c in CASES:
        res = run(c)
        rows = res["rows"]
        s_naive = summarise(rows, "naive")
        s_corr = summarise(rows, "corrected")
        out[name] = {"coulomb": c, "n_steps": len(rows), "Jw": res["Jw"],
                     "naive_D5": s_naive, "corrected": s_corr, "guards": res["guards"]}
        print(f"[{name}]  coulomb={c}  Jw={res['Jw']}")
        print(f"   D5 convention  |tau_cmd - Jw*dw| : median {s_naive['median_abs']:.3e}"
              f"   error vs truth {s_naive['median_abs_err_vs_true']:.3e}")
        print(f"   corrected      |tau_cmd + Jw*dw| : median {s_corr['median_abs']:.3e}"
              f"   error vs truth {s_corr['median_abs_err_vs_true']:.3e}")
        g = res["guards"]
        print(f"   guard: n_upd={g['n_upd']} skip_excite={g['skip_excite']} "
              f"skip_sat={g['skip_sat']} skip_plaus={g['skip_plaus']}\n")

    # separation: healthy vs 2e-4, using each convention
    h = out["ideal"]["corrected"]["median_abs"]
    f = out["coulomb_2e-4"]["corrected"]["median_abs"]
    hn = out["ideal"]["naive_D5"]["median_abs"]
    fn = out["coulomb_2e-4"]["naive_D5"]["median_abs"]
    out["separation"] = {
        "corrected": float(f / h) if h > 0 else None,
        "naive_D5": float(fn / hn) if hn > 0 else None,
    }
    print(f"separation (coulomb/ideal median |residual|):")
    print(f"   D5 convention : {out['separation']['naive_D5']:.2f}x")
    print(f"   corrected     : {out['separation']['corrected']:.2f}x")

    os.makedirs("results/m1", exist_ok=True)
    with open("results/m1/m1a_signal_audit.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nsaved results/m1/m1a_signal_audit.json")


if __name__ == "__main__":
    main()
