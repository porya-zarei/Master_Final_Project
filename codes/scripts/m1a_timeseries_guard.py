"""M1-A addendum: persist the time series and reproduce the guard predicate.

Diagnostic only. Writes results/m1/m1a_timeseries.json.

Signals logged per control period:
  tau_cmd        allocator output (per wheel)
  omega_w        wheel speed
  dw_dt          finite-difference wheel acceleration
  tau_f_resid    corrected model-based residual  = tau_cmd + J_w*dw_dt
  tau_f_true     plant friction torque at the interval midpoint
  coupling_i     the (omega x H_w) component that the WHEEL equation does not contain
  guard          skip_excite predicate evaluated on the PREVIOUS command, matching the
                 environment's update ordering (update() runs before allocation)
"""
from __future__ import annotations
import sys, os, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from satellite_adcs.environment.adcs_env import ADCSEnv
from satellite_adcs.environment.residual_env import ResidualADCSEnv
from simulate import make_ic_bias

DS = 10   # downsample factor for the saved series


def run(coulomb, seed=2):
    ov = {"actuators": {"reaction_wheels": {"friction_coulomb_Nm": coulomb}}}
    env = ResidualADCSEnv(ADCSEnv(fault_mode="none", episode_time=900.0,
                                  control_hz=5.0, seed=seed, overrides=ov), alpha=0.2)
    q0, w0, b = make_ic_bias(seed)
    obs, _ = env.reset(seed=seed, options={"q": q0, "omega": w0, "gyro_bias": b})
    d = env.unwrapped.dyn
    he = env.unwrapped.health_est
    Tc = env.unwrapped.control_period
    Jw = float(d.rw_J)

    series = []
    prev_om = None
    prev_tau = np.zeros(3)
    pred_excite = np.zeros(3, dtype=int)
    k = 0
    done = False
    while not done:
        obs, r, term, trunc, info = env.step(np.zeros(3))
        done = term or trunc
        om = np.asarray(d.omega_w, float).copy()
        tau_now = np.asarray(info.get("tau_cmd", np.zeros(3)), float).copy()
        if prev_om is not None:
            dw_dt = (om - prev_om) / Tc
            om_mid = 0.5 * (om + prev_om)
            tau_f_true = -(d.rw_b_visc * om_mid
                           + d.rw_c_coul * np.tanh(om_mid / 0.05))
            # predicate on the PREVIOUS command, as the env does (update before alloc)
            exc = (np.abs(prev_tau) < he.tau_min_eff).astype(int)
            pred_excite += exc
            if k % DS == 0:
                H_w = Jw * om
                series.append({
                    "t": round(k * Tc, 2),
                    # the command APPLIED during this step pairs with dw_dt over it;
                    # the guard below uses the PREVIOUS command, as update() runs
                    # before allocation
                    "tau_cmd": np.round(tau_now, 10).tolist(),
                    "omega_w": np.round(om, 8).tolist(),
                    "dw_dt": np.round(dw_dt, 6).tolist(),
                    "tau_f_resid": np.round(tau_now + Jw * dw_dt, 12).tolist(),
                    "tau_f_true": np.round(tau_f_true, 12).tolist(),
                    "coupling_body": np.round(-np.cross(d.omega, H_w), 12).tolist(),
                    "skip_excite": exc.tolist(),
                })
        prev_om = om
        prev_tau = tau_now
        k += 1

    res = np.array([s["tau_f_resid"] for s in series])
    tru = np.array([s["tau_f_true"] for s in series])
    return {
        "coulomb": coulomb,
        "n_steps": k,
        "tau_min_eff": float(he.tau_min_eff),
        "guard_actual_skip_excite": he.n_skip_excite.tolist(),
        "guard_predicate_skip_excite": pred_excite.tolist(),
        "predicate_matches_actual": bool(np.array_equal(pred_excite, he.n_skip_excite)),
        "n_upd_actual": he.n_upd.tolist(),
        "residual_vs_truth_max_abs": float(np.max(np.abs(res - tru))) if len(res) else None,
        "series": series,
    }


def main():
    out = {}
    for name, c in (("ideal", 0.0), ("coulomb_2e4", 2e-4)):
        r = run(c)
        out[name] = r
        print(f"[{name}] steps={r['n_steps']}  tau_min_eff={r['tau_min_eff']:.2e}")
        print(f"   skip_excite actual   = {r['guard_actual_skip_excite']}")
        print(f"   skip_excite predicted= {r['guard_predicate_skip_excite']}"
              f"   MATCH={r['predicate_matches_actual']}")
        print(f"   n_upd actual = {r['n_upd_actual']}")
        print(f"   max |residual - truth| over saved series = "
              f"{r['residual_vs_truth_max_abs']:.3e}")
        print(f"   saved {len(r['series'])} samples\n")
    os.makedirs("results/m1", exist_ok=True)
    with open("results/m1/m1a_timeseries.json", "w") as f:
        json.dump(out, f, indent=1)
    print("saved results/m1/m1a_timeseries.json")


if __name__ == "__main__":
    main()
