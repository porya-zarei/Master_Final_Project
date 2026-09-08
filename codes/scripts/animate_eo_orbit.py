"""Animate the Earth-observing satellite env: Earth + targets + orbit + attitude.

Runs a rollout of the EO imaging env and renders:
  - Earth (blue sphere), 50 ground targets (green dots on the surface)
  - the satellite orbit path, and the satellite body with its attitude axes
Uses real simulated state (r_BN_N, sigma_BN) from the env.

Run from `codes/`:
    python scripts/animate_eo_orbit.py [steps] [seconds_per_step] [n_targets]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

from simulation.envs.eo_imaging_env import make_eo_env

RE = 6378137.0  # Earth radius [m] (r_BN_N is in meters)


def mrp_to_dcm(sig):
    s = np.asarray(sig, dtype=float)
    s2 = s @ s
    S = np.array([[0, -s[2], s[1]], [s[2], 0, -s[0]], [-s[1], s[0], 0]])
    d = (1.0 + s2) ** 2
    return np.eye(3) + (8.0 * (S @ S) - 4.0 * (1.0 - s2) * S) / d


def run_rollout(steps: int, dt: float, n_targets: int):
    env = make_eo_env(max_step_duration=dt, n_targets=n_targets)
    obs, info = env.reset(seed=7)
    dyn = env.unwrapped.satellite.dynamics

    sig = [np.array(dyn.sigma_BN)]
    pos = [np.array(dyn.r_BN_N) / RE]
    batt = [float(dyn.battery_charge_fraction)]
    for _ in range(int(steps)):
        env.step(env.action_space.sample())
        sig.append(np.array(dyn.sigma_BN))
        pos.append(np.array(dyn.r_BN_N) / RE)
        batt.append(float(dyn.battery_charge_fraction))

    # ground targets: planet-fixed positions -> unit sphere (read before close)
    tg = []
    try:
        for t in env.unwrapped.scenario.targets:
            r = np.asarray(t.r_LP_P, dtype=float)
            n = np.linalg.norm(r)
            tg.append(r / n if n else np.zeros(3))
    except Exception:
        tg = []
    env.close()
    return np.array(sig), np.array(pos), np.array(batt), np.array(tg)


HB = 0.06
CUBE = np.array([[x, y, z] for x in (-HB, HB) for y in (-HB, HB) for z in (-HB, HB)])
EDGES = [
    (0, 1), (0, 2), (1, 3), (2, 3),
    (4, 5), (4, 6), (5, 7), (6, 7),
    (0, 4), (1, 5), (2, 6), (3, 7),
]
BODY_AXES = np.eye(3) * 0.18


def earth_surface(ax, res=36):
    u = np.linspace(0, 2 * np.pi, res)
    v = np.linspace(0, np.pi, res)
    x = np.outer(np.cos(u), np.sin(v))
    y = np.outer(np.sin(u), np.sin(v))
    z = np.outer(np.ones(res), np.cos(v))
    ax.plot_surface(x, y, z, color="#2c7fb8", alpha=0.85, rstride=1, cstride=1,
                    linewidth=0, shade=True)


def main(steps: int = 120, dt: float = 30.0, n_targets: int = 25):
    sig, pos, batt, tg = run_rollout(steps, dt, n_targets)
    n = len(sig)

    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_subplot(111, projection="3d")
    earth_surface(ax)

    # inertial axes
    for i, col in enumerate(["red", "green", "blue"]):
        d = np.eye(3)[i] * 1.4
        ax.plot([0, d[0]], [0, d[1]], [0, d[2]], color=col, lw=1.1, alpha=0.5)

    # ground targets on the globe
    if tg.size:
        ax.scatter(tg[:, 0], tg[:, 1], tg[:, 2], s=12, color="lime",
                   depthshade=False, label="targets")

    # orbit path
    ax.plot(pos[:, 0], pos[:, 1], pos[:, 2], color="gray", alpha=0.55, lw=1.0)

    box_lines, = ax.plot([], [], [], color="tab:orange", lw=1.8)
    trail, = ax.plot([], [], [], color="tab:orange", alpha=0.5, lw=1.0)
    body_axes = [
        ax.plot([], [], [], color="red", lw=2.2)[0],
        ax.plot([], [], [], color="green", lw=2.2)[0],
        ax.plot([], [], [], color="blue", lw=2.2)[0],
    ]
    tlabel = ax.text2D(0.02, 0.96, "", transform=ax.transAxes, fontsize=11)

    L = 1.7
    ax.set_xlim(-L, L); ax.set_ylim(-L, L); ax.set_zlim(-L, L)
    ax.set_box_aspect((1, 1, 1))
    ax.set_xlabel("X_I"); ax.set_ylabel("Y_I"); ax.set_zlabel("Z_I")
    if tg.size:
        ax.legend(loc="upper right", fontsize=8)
    ax.set_title("Earth-observing satellite: orbit + attitude (green dots = targets)")

    def update(i):
        R = mrp_to_dcm(sig[i])
        p = pos[i]
        segs = []
        for a, b in EDGES:
            segs.append(R @ CUBE[a] + p); segs.append(R @ CUBE[b] + p)
        x = [q[0] for q in segs]; y = [q[1] for q in segs]; z = [q[2] for q in segs]
        box_lines.set_data(x, y); box_lines.set_3d_properties(z)
        t0 = max(0, i - 25)
        tr = pos[t0:i + 1]
        trail.set_data(tr[:, 0], tr[:, 1]); trail.set_3d_properties(tr[:, 2])
        for q, axv in zip(body_axes, BODY_AXES):
            d = R @ axv + p
            q.set_data([p[0], d[0]], [p[1], d[1]]); q.set_3d_properties([p[2], d[2]])
        tlabel.set_text(f"t = {i * dt:.0f} s   battery = {batt[i]:.2f}")
        return (box_lines, trail, *body_axes, tlabel)

    frame_idx = range(0, n, 2)
    anim = FuncAnimation(fig, update, frames=frame_idx, interval=80, blit=False)
    out = Path("results") / "eo_orbit.gif"
    out.parent.mkdir(exist_ok=True)
    anim.save(out, writer=PillowWriter(fps=12))
    print(f"frames={n}, targets={len(tg)}, orbit r~{np.linalg.norm(pos[0]):.3f} RE")
    print("saved:", out.resolve())


if __name__ == "__main__":
    st = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    dt = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
    nt = int(sys.argv[3]) if len(sys.argv) > 3 else 25
    main(st, dt, nt)
