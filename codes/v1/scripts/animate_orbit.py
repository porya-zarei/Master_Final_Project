"""Animate the satellite orbiting the Earth, with its attitude visible.

Uses real simulated data: inertial position `sat.dynamics.r_BN_N` (orbit) and
MRP attitude sigma (body orientation). Earth is drawn as a sphere at the origin
(radius = 1 unit), orbit + satellite body are normalized to Earth radii.
Body/axes are exaggerated for visibility (not to scale).

Run from `codes/`:
    python scripts/animate_orbit.py [steps] [seconds_per_step]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

from simulation.envs.adcs_env import make_env, FaultToleranceWrapper

RE = 6378137.0  # Earth radius [m] (r_BN_N is in meters)


def mrp_to_dcm(sig):
    s = np.asarray(sig, dtype=float)
    s2 = s @ s
    S = np.array([[0, -s[2], s[1]], [s[2], 0, -s[0]], [-s[1], s[0], 0]])
    d = (1.0 + s2) ** 2
    return np.eye(3) + (8.0 * (S @ S) - 4.0 * (1.0 - s2) * S) / d


def run_rollout(steps: int, dt: float, seed: int = 3):
    env = FaultToleranceWrapper(make_env(max_step_duration=dt), seed=seed)
    obs, info = env.reset(seed=seed)
    dyn = env.unwrapped.satellite.dynamics

    sig = [obs[0:3].copy()]
    pos = [np.array(dyn.r_BN_N) / RE]  # normalized to Earth radii
    for _ in range(int(steps)):
        obs, r, term, trunc, info = env.step(env.action_space.sample())
        sig.append(obs[0:3].copy())
        pos.append(np.array(dyn.r_BN_N) / RE)
        if term or trunc:
            break
    env.close()
    return np.array(sig), np.array(pos)


# ---- cube wireframe (normalized size, exaggerated) ----
HB = 0.06  # body half-size in Earth radii
CUBE = np.array([[x, y, z] for x in (-HB, HB) for y in (-HB, HB) for z in (-HB, HB)])
EDGES = [
    (0, 1), (0, 2), (1, 3), (2, 3),
    (4, 5), (4, 6), (5, 7), (6, 7),
    (0, 4), (1, 5), (2, 6), (3, 7),
]
BODY_AXES = np.eye(3) * 0.18


def earth_surface(ax, res=40):
    u = np.linspace(0, 2 * np.pi, res)
    v = np.linspace(0, np.pi, res)
    x = np.outer(np.cos(u), np.sin(v))
    y = np.outer(np.sin(u), np.sin(v))
    z = np.outer(np.ones(res), np.cos(v))
    ax.plot_surface(x, y, z, color="#2c7fb8", alpha=0.85, rstride=1, cstride=1,
                    linewidth=0, shade=True)
    # a little "axis" hint through the poles
    ax.plot([0, 0], [0, 0], [-1.05, 1.05], color="k", lw=0.5, alpha=0.3)


def main(steps: int = 140, dt: float = 10.0, seed: int = 3):
    sig, pos = run_rollout(steps, dt, seed)
    n = len(sig)

    fig = plt.figure(figsize=(6.2, 6.2))
    ax = fig.add_subplot(111, projection="3d")
    earth_surface(ax)

    # inertial axes (fixed) at Earth center
    for i, col in enumerate(["red", "green", "blue"]):
        d = np.eye(3)[i] * 1.35
        ax.plot([0, d[0]], [0, d[1]], [0, d[2]], color=col, lw=1.2, alpha=0.6)

    # orbit path
    ax.plot(pos[:, 0], pos[:, 1], pos[:, 2], color="gray", alpha=0.6, lw=1.0)

    # moving satellite artists
    box_lines, = ax.plot([], [], [], color="tab:orange", lw=1.8)
    trail, = ax.plot([], [], [], color="tab:orange", alpha=0.5, lw=1.0)
    body_axes = [
        ax.plot([], [], [], color="red", lw=2.2)[0],
        ax.plot([], [], [], color="green", lw=2.2)[0],
        ax.plot([], [], [], color="blue", lw=2.2)[0],
    ]
    tlabel = ax.text2D(0.02, 0.95, "", transform=ax.transAxes, fontsize=11)

    L = 1.6
    ax.set_xlim(-L, L); ax.set_ylim(-L, L); ax.set_zlim(-L, L)
    ax.set_box_aspect((1, 1, 1))
    ax.set_xlabel("X_I"); ax.set_ylabel("Y_I"); ax.set_zlabel("Z_I")
    ax.set_title("Satellite orbit around Earth + attitude (body axes)")

    def update(i):
        R = mrp_to_dcm(sig[i])
        p = pos[i]
        # box edges body->inertial, translated to satellite position
        segs = []
        for a, b in EDGES:
            segs.append(R @ CUBE[a] + p); segs.append(R @ CUBE[b] + p)
        x = [q[0] for q in segs]; y = [q[1] for q in segs]; z = [q[2] for q in segs]
        box_lines.set_data(x, y); box_lines.set_3d_properties(z)
        # trail (last 30 points)
        t0 = max(0, i - 30)
        tr = pos[t0:i + 1]
        trail.set_data(tr[:, 0], tr[:, 1]); trail.set_3d_properties(tr[:, 2])
        # body axes
        for q, axv in zip(body_axes, BODY_AXES):
            d = R @ axv + p
            q.set_data([p[0], d[0]], [p[1], d[1]]); q.set_3d_properties([p[2], d[2]])
        tlabel.set_text(f"t = {i * dt:.0f} s")
        return (box_lines, trail, *body_axes, tlabel)

    frame_idx = range(0, n, 2)  # decimate to keep the GIF small
    anim = FuncAnimation(fig, update, frames=frame_idx, interval=80, blit=False)
    out = Path("results") / "orbit_attitude.gif"
    out.parent.mkdir(exist_ok=True)
    anim.save(out, writer=PillowWriter(fps=12))
    print(f"frames={n}, orbit pts from r={pos[0][0]:.3f}..{pos[-1][0]:.3f} RE")
    print("saved:", out.resolve())


if __name__ == "__main__":
    st = int(sys.argv[1]) if len(sys.argv) > 1 else 140
    dt = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
    main(st, dt)
