"""Diagnostic: where does the trained residual act, as a function of pointing error?

D5 assumes the nominal cost comes from the policy adding torque at SMALL error, where
the LQR needs none. That is a hypothesis. This measures |delta_tau| binned by the
pointing error, on both the ideal and the Coulomb plant, for the best seed.

If the residual is large at theta < 1 deg, an error-magnitude gate will remove the
nominal cost. If it is already near zero there, the cost has a different cause and a
gate would be the wrong fix.
"""
from __future__ import annotations
import sys, os
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from satellite_adcs.environment.adcs_env import ADCSEnv
from satellite_adcs.environment.residual_env import ResidualADCSEnv
from simulate import make_ic_bias
from stable_baselines3 import SAC

ALPHA = 0.2
BANDS = [(0.0, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 5.0), (5.0, 200.0)]


def run(policy, coulomb, seed=2):
    ov = {"actuators": {"reaction_wheels": {"friction_coulomb_Nm": coulomb}}}
    env = ResidualADCSEnv(ADCSEnv(fault_mode="none", episode_time=900.0,
                                  control_hz=5.0, seed=seed, overrides=ov),
                          alpha=ALPHA)
    q0, w0, bias = make_ic_bias(seed)
    obs, _ = env.reset(seed=seed, options={"q": q0, "omega": w0, "gyro_bias": bias})
    model = SAC.load(policy, device="cpu")
    rec = {b: [] for b in BANDS}
    done = False
    while not done:
        a = model.predict(obs, deterministic=True)[0]
        dtau = float(np.linalg.norm(ALPHA * np.asarray(a) * env.unwrapped.rw_max_torque))
        th = env.unwrapped.pointing_error_deg()
        for lo, hi in BANDS:
            if lo <= th < hi:
                rec[(lo, hi)].append(dtau)
                break
        obs, _, term, trunc, _ = env.step(a)
        done = term or trunc
    return rec


def main():
    pol = "results/residual_d4_s2/policy.zip"
    tau_max = 2.0e-3
    for cond, c in (("ideal", 0.0), ("coulomb 2e-4", 2e-4)):
        rec = run(pol, c)
        print(f"\n=== {cond} ===")
        print(f"{'theta band':>12} {'steps':>7} {'mean|dtau|':>11} "
              f"{'% of alpha*tau_max':>19}")
        for b, v in rec.items():
            if not v:
                continue
            m = float(np.mean(v))
            print(f"{b[0]:>6.1f}-{b[1]:>5.1f}deg {len(v):>7} "
                  f"{m:>11.2e} {100*m/tau_max:>18.1f}%")


if __name__ == "__main__":
    main()
