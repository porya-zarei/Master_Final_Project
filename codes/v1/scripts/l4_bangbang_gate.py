"""L4 gate: can a bang-bang rule beat the LQR on time-to-first-entry?

The 9x headroom (report-3 section 12) is a LOWER bound. Before spending any
training time, this asks the falsification question the pre-registration demands:
is that headroom reachable by ANY controller, or do rate nulling / wheel limits /
3-axis coupling eat it?

Both controllers are driven through the SAME env, on the SAME paired initial
conditions and gyro bias, with the same allocator -- so the only difference is the
control law.

Bang-bang law (per axis, double-integrator time-optimal switching curve):
    s = theta + omega*|omega| / (2*alpha)
    u = -sign(s)
where alpha = tau_max / J is the available angular acceleration.
"""
from __future__ import annotations
import sys, os, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from satellite_adcs.config import load_config
from satellite_adcs.controllers import design_lqr
from satellite_adcs.environment.adcs_env import ADCSEnv

T_EP = 900.0
TOL = 1.0


def make_controllers(env):
    cfg = env.cfg
    I = cfg["satellite"]["inertia"]
    J = np.diag([I["Jxx"], I["Jyy"], I["Jzz"]])
    Q = np.diag([1.0, 1.0, 1.0, 0.3, 0.3, 0.3])
    R = np.eye(3) * (1.0 / (0.01 ** 2))
    K = design_lqr(J, Q, R)
    tau_max = env.rw_max_torque
    alpha = tau_max / np.diag(J)          # per-axis angular acceleration
    scale = env.tau_scale * tau_max

    def lqr(obs):
        return np.clip((-K @ obs[:6]) / scale, -1.0, 1.0)

    def bangbang(obs):
        th, we = obs[:3], obs[3:6]
        s = th + we * np.abs(we) / (2.0 * alpha)
        return -np.sign(s)

    return {"lqr": lqr, "bangbang": bangbang}


def run(policy, seed):
    env = ADCSEnv(fault_mode="none", episode_time=T_EP, control_hz=5.0, seed=seed)
    from simulate import make_ic_bias
    q0, w0, bias = make_ic_bias(seed)
    obs, _ = env.reset(seed=seed, options={"q": q0, "omega": w0, "gyro_bias": bias})
    ctrl = make_controllers(env)
    act = ctrl[policy]

    t_first, peaks, done, k = None, [], False, 0
    while not done:
        obs, r, term, trunc, info = env.step(act(obs))
        pe = env.pointing_error_deg()
        peaks.append(pe)
        if t_first is None and pe < TOL:
            t_first = (k + 1) * env.control_period
        done = term or trunc
        k += 1
    return {"t_first": t_first, "final": pe,
            "peak": float(np.max(peaks)), "t_episode": k * env.control_period}


def main(n=6):
    rows = []
    for s in range(n):
        a = run("lqr", s)
        b = run("bangbang", s)
        rows.append({"seed": s, "lqr": a, "bb": b})
        f = lambda v: "never" if v is None else f"{v:6.1f}s"
        print(f"seed {s:2d}  t_first  LQR {f(a['t_first']):>8}  BB {f(b['t_first']):>8}"
              f"   |  final LQR {a['final']:6.2f}deg  BB {b['final']:6.2f}deg")

    lqr_t = [r["lqr"]["t_first"] for r in rows if r["lqr"]["t_first"] is not None]
    bb_t = [r["bb"]["t_first"] for r in rows if r["bb"]["t_first"] is not None]
    print(f"\nsolved: LQR {len(lqr_t)}/{n}   BB {len(bb_t)}/{n}")
    if lqr_t and bb_t:
        ml, mb = float(np.median(lqr_t)), float(np.median(bb_t))
        print(f"median t_first:  LQR {ml:.1f}s   bang-bang {mb:.1f}s   "
              f"speedup {ml/mb:.2f}x")
        print(f"final error:     LQR {np.mean([r['lqr']['final'] for r in rows]):.2f}deg"
              f"   BB {np.mean([r['bb']['final'] for r in rows]):.2f}deg")
    os.makedirs("results/l4", exist_ok=True)
    with open("results/l4/l4_bangbang_gate.json", "w") as f:
        json.dump(rows, f, indent=2)
    print("saved results/l4/l4_bangbang_gate.json")


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 6
    main(n)
