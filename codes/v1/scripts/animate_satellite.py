"""Animate the Phase-1 satellite simulation in 3D (attitude + orbit).

Renders the actual simulated motion: the satellite body (with body-fixed x/y/z
axes) rotates in inertial space while traveling along its orbit arc, using the
MRP attitude + position recorded from a live rollout. Saves a GIF.

Run from `codes/`:
    python scripts/animate_satellite.py [seconds]
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


def mrp_to_dcm(sig):
    """MRP sigma (3,) -> body-to-inertial rotation matrix R_BN (3x3)."""
    s = np.asarray(sig, dtype=float)
    s2 = s @ s
    S = np.array([[0, -s[2], s[1]], [s[2], 0, -s[0]], [-s[1], s[0], 0]])
    d = (1.0 + s2) ** 2
    return np.eye(3) + (8.0 * (S @ S) - 4.0 * (1.0 - s2) * S) / d


def run_rollout(seconds: int, seed: int = 3):
    env = FaultToleranceWrapper(make_env(), seed=seed)
    obs, info = env.reset(seed=seed)

    sig = [obs[0:3].copy()]
    pos = []

    # Try to grab the inertial position (for the orbit arc); ignore if unavailable.
    hub = None
    try:
        sat = env.unwrapped.satellite
        dyn = sat.dyn[0] if hasattr(sat, "dyn") else None
        hub = dyn.satellite.hub if dyn is not None else None
    except Exception:
        hub = None

    for _ in range(int(seconds)):
        obs, r, term, trunc, info = env.step(env.action_space.sample())
        sig.append(obs[0:3].copy())
        if hub is not None:
            try:
                pos.append(np.array(hub.r_BN_N).copy())
            except Exception:
                pos.append(pos[-1] if pos else np.zeros(3))
        if term or trunc:
            break
    env.close()

    sig = np.array(sig)
    pos = np.array(pos) if pos else None
    print(f"recorded {len(sig)} frames; orbit available: {pos is not None}")
    return sig, pos


# ---- cube wireframe (unit body) ----
CUBE = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)])
EDGES = [
    (0, 1), (0, 2), (1, 3), (2, 3),
    (4, 5), (4, 6), (5, 7), (6, 7),
    (0, 4), (1, 5), (2, 6), (3, 7),
]
BODY_AXES = np.eye(3) * 1.8
INERTIAL_AXES = np.eye(3) * 3.2


def main(seconds: int = 60, seed: int = 3):
    sig, pos = run_rollout(seconds, seed)
    n = len(sig)

    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(111, projection="3d")

    # Inertial frame (fixed) as Line3D
    for i, col in enumerate(["red", "green", "blue"]):
        ax.plot([0, INERTIAL_AXES[i, 0]], [0, INERTIAL_AXES[i, 1]],
                [0, INERTIAL_AXES[i, 2]], color=col, lw=1.2, alpha=0.45)

    # Orbit arc (in inertial coords)
    if pos is not None:
        c = pos - pos[0]
        ax.plot(c[:, 0], c[:, 1], c[:, 2], color="gray", alpha=0.5, lw=1.0)

    # Body artists (updated each frame): 12 box edges + 3 body axes
    box_lines, = ax.plot([], [], [], color="tab:blue", lw=1.6)
    body_axes = [
        ax.plot([], [], [], color="red", lw=2.2)[0],
        ax.plot([], [], [], color="green", lw=2.2)[0],
        ax.plot([], [], [], color="blue", lw=2.2)[0],
    ]

    lim = 3.2
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim, lim)
    ax.set_box_aspect((1, 1, 1))
    ax.set_xlabel("X_I"); ax.set_ylabel("Y_I"); ax.set_zlabel("Z_I")
    ax.set_title("Satellite attitude simulation (body axes in inertial frame)")

    def update(i):
        R = mrp_to_dcm(sig[i])
        # box edges body->inertial
        segs = []
        for a, b in EDGES:
            segs.append(R @ CUBE[a]); segs.append(R @ CUBE[b])
        x = [p[0] for p in segs]; y = [p[1] for p in segs]; z = [p[2] for p in segs]
        box_lines.set_data(x, y); box_lines.set_3d_properties(z)
        # body axes
        for q, axv in zip(body_axes, BODY_AXES):
            d = R @ axv
            q.set_data([0, d[0]], [0, d[1]]); q.set_3d_properties([0, d[2]])
        return (box_lines, *body_axes)

    anim = FuncAnimation(fig, update, frames=n, interval=100, blit=False)
    out = Path("results") / "satellite_animation.gif"
    out.parent.mkdir(exist_ok=True)
    anim.save(out, writer=PillowWriter(fps=10))
    print("saved:", out.resolve())


if __name__ == "__main__":
    sec = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    main(sec)
