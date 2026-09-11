"""C4.2 arm verification: print the actual reward landscape per arm before training.

Calls ADCSEnv._reward() directly with synthetic attitude error, zero rate, zero control,
so the printed numbers are the pure error-term values (+ tolerance bonus where active).
Nothing here is estimated -- it is the code path training will use.
"""
import numpy as np
from satellite_adcs.environment.adcs_env import ADCSEnv

TOL = np.radians(1.0)
TOL2 = TOL ** 2

ARMS = [
    ("BASE   bonus +1.0   ", "bonus", {}),
    ("A1     quad         ", "quad",  {}),
    ("S1     log          ", "log",   {}),
    ("S2     bonus 0.1    ", "bonus", {"reward_tol_bonus": 0.1}),
    ("S3     bonus tol^2  ", "bonus", {"reward_tol_bonus": TOL2}),
]

print(f"tol = {np.degrees(TOL):.4f} deg | tol^2 = {TOL2:.6e}")
print(f"(a near-target quad penalty at 1 deg is -{TOL2:.3e}; that is the scale S3 matches)\n")

hdr = f"{'arm':20s} {'shape':6s} " + " ".join(f"{d:>12s}" for d in
                                               ("5 deg", "1 deg", "0.5 deg", "0.1 deg"))
print(hdr)
print("-" * len(hdr))

for name, shape, over in ARMS:
    ov = {"rl": {"reward_shape": shape}}
    ov["rl"].update(over)
    env = ADCSEnv(overrides=ov)
    assert env.reward_shape == shape, (env.reward_shape, shape)
    for k, v in over.items():
        assert getattr(env, k if k != "reward_tol_bonus" else "reward_tol_bonus") == v, k
    row = f"{name:20s} {shape:6s} "
    for deg in (5.0, 1.0, 0.5, 0.1):
        th = np.array([np.radians(deg), 0.0, 0.0])
        r, comp = env._reward(th, np.zeros(3), np.zeros(3))
        row += f"{r:>12.6f} "
    print(row)

print("\nPer-step bonus over a full 900 s / 5 Hz episode (4500 steps) if always in tolerance:")
for name, shape, over in ARMS:
    ov = {"rl": {"reward_shape": shape}}
    ov["rl"].update(over)
    env = ADCSEnv(overrides=ov)
    in_tol_th = np.array([np.radians(0.5), 0.0, 0.0])
    r_in, _ = env._reward(in_tol_th, np.zeros(3), np.zeros(3))
    print(f"  {name}: r_in_tol = {r_in:+.6e}  ->  max episode contribution = {r_in * 4500:+.4f}")

print("\nGradient of the error term w.r.t. theta at 0.5 deg (finite difference, per rad):")
for name, shape, over in ARMS:
    ov = {"rl": {"reward_shape": shape}}
    ov["rl"].update(over)
    env = ADCSEnv(overrides=ov)
    h = 1e-7
    a = np.array([np.radians(0.5) - h, 0.0, 0.0])
    b = np.array([np.radians(0.5) + h, 0.0, 0.0])
    ra, _ = env._reward(a, np.zeros(3), np.zeros(3))
    rb, _ = env._reward(b, np.zeros(3), np.zeros(3))
    g = (rb - ra) / (2 * h)
    print(f"  {name}: dr/dtheta_x = {g:+.6f} per rad   ({g * np.radians(1.0):+.3e} per deg)")
