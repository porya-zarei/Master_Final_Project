"""Live 3D Basilisk 2.12.2 + CCR v2 Spacecraft Orbit, Disturbance & Wheel-Failure Demo.

Runs real Basilisk 2.12.2 rigid-body + orbital + reaction-wheel + magnetorquer +
gravity-gradient dynamics coupled with our real 6-state MEKF, Online Capability
Estimator, Supervisor (M0-M4), and trained CCR v2 residual RL controller.

Mission timeline (default 120 s at 5 Hz):
  1. t = 0..35 s   : Random orbital position/velocity + random 3D tumble -> Nadir lock
  2. t = 35..50 s  : External 3-axis disturbance torque pulse -> Reaction & recovery
  3. t = 65..120 s : Reaction wheel failure (20%, 80%, or 100% loss) + perturbation at 78..90 s

Usage (run with `.venv_bsk\\Scripts\\python.exe` where Basilisk 2.12.2 is installed):
  .\\.venv_bsk\\Scripts\\python.exe scripts\\live_3d_basilisk_demo.py --compare-all --open
  .\\.venv_bsk\\Scripts\\python.exe scripts\\live_3d_basilisk_demo.py --wheel-loss 0.8 --open
  .\\.venv_bsk\\Scripts\\python.exe scripts\\live_3d_basilisk_demo.py --wheel-loss 0.8 --vizard-live
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import webbrowser
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from adcs.control.classical.baselines import (  # noqa: E402
    ESOConfig,
    StrongClassicalController,
)
from adcs.control.classical.lqr import ClassicalLQRConfig  # noqa: E402
from adcs.control.reference.nadir import NadirReferenceGenerator  # noqa: E402
from adcs.control.residual_rl.controller import (  # noqa: E402
    CCRController,
    CCRControllerConfig,
)
from adcs.control.residual_rl.policy import TorchMLPResidualPolicy  # noqa: E402
from adcs.control.safety import GateConfig  # noqa: E402
from adcs.estimation.capability import (  # noqa: E402
    CapabilityEstimatorConfig,
    OnlineCapabilityEstimator,
)
from adcs.estimation.mekf import MEKFConfig, MultiplicativeEKF  # noqa: E402
from adcs.interfaces.types import ActuatorCommand  # noqa: E402
from adcs.sensors.suite import SensorSuite, SensorSuiteConfig  # noqa: E402
from adcs.simulation.basilisk.backend import (  # noqa: E402
    BasiliskBackend,
    is_basilisk_available,
)
from adcs.utils.config import SpacecraftConfig, load_spacecraft_config  # noqa: E402
from adcs.utils.quaternion import (  # noqa: E402
    quat_error,
    quat_from_axis_angle,
    quat_geodesic_angle,
    quat_multiply,
    quat_rotate_vec_inv,
    quat_to_dcm,
)

TEMPLATE_HTML = REPO_ROOT / "scripts" / "templates" / "live_3d_studio_template.html"

DEFAULT_CHECKPOINT_CANDIDATES = [
    REPO_ROOT / "experiments" / "E002_ccr_v2_igrf14_rlsfix" / "checkpoints" / "A7_ccr_v2_eso",
    Path(
        r"C:\Users\ASUS\.gemini\antigravity-cli\brain"
        r"\65affd91-4f5b-41ee-b6bc-1a64c8142955\scratch"
        r"\E002_ccr_v2_igrf14_rlsfix\checkpoints\A7_ccr_v2_eso"
    ),
]


def find_default_checkpoint() -> Path | None:
    for candidate in DEFAULT_CHECKPOINT_CANDIDATES:
        if (candidate / "policy_weights.npz").exists():
            return candidate
    return None


def sample_random_orbit_and_attitude(
    sc_cfg: SpacecraftConfig,
    rng: np.random.Generator,
) -> dict[str, Any]:
    """Sample a random orbital position/velocity and random initial 3D tumble attitude."""
    mu = sc_cfg.orbit.gravitational_parameter_m3_s2
    a_m = sc_cfg.orbit.semi_major_axis_m + float(rng.uniform(-25_000.0, 25_000.0))
    ecc = float(rng.uniform(0.001, 0.012))
    inc = np.deg2rad(sc_cfg.orbit.inclination_deg + float(rng.uniform(-4.0, 4.0)))
    raan = np.deg2rad(float(rng.uniform(0.0, 360.0)))
    argp = np.deg2rad(float(rng.uniform(0.0, 360.0)))
    nu = np.deg2rad(float(rng.uniform(0.0, 360.0)))

    p = a_m * (1.0 - ecc * ecc)
    r_mag = p / (1.0 + ecc * math.cos(nu))
    r_pqw = np.array([r_mag * math.cos(nu), r_mag * math.sin(nu), 0.0], dtype=np.float64)
    v_scale = math.sqrt(mu / p)
    v_pqw = np.array(
        [-v_scale * math.sin(nu), v_scale * (ecc + math.cos(nu)), 0.0],
        dtype=np.float64,
    )

    c_o, s_o = math.cos(raan), math.sin(raan)
    c_i, s_i = math.cos(inc), math.sin(inc)
    c_w, s_w = math.cos(argp), math.sin(argp)
    r_eci_pqw = np.array(
        [
            [c_o * c_w - s_o * s_w * c_i, -c_o * s_w - s_o * c_w * c_i, s_o * s_i],
            [s_o * c_w + c_o * s_w * c_i, -s_o * s_w + c_o * c_w * c_i, -c_o * s_i],
            [s_w * s_i, c_w * s_i, c_i],
        ],
        dtype=np.float64,
    )
    r_eci = r_eci_pqw @ r_pqw
    v_eci = r_eci_pqw @ v_pqw

    ref0 = NadirReferenceGenerator().compute(0.0, r_eci, v_eci)

    axis = rng.normal(size=3)
    axis /= float(np.linalg.norm(axis)) + 1e-12
    angle_deg = float(rng.uniform(45.0, 75.0))
    q_err = quat_from_axis_angle(axis, math.radians(angle_deg))
    q_ib_init = quat_multiply(ref0.q_ir, q_err)

    w_axis = rng.normal(size=3)
    w_axis /= float(np.linalg.norm(w_axis)) + 1e-12
    w_mag_deg_s = float(rng.uniform(0.25, 0.55))
    omega_init = ref0.omega_ref_inertial_in_ref_rad_s + w_axis * math.radians(w_mag_deg_s)

    return {
        "r_eci_m": r_eci,
        "v_eci_m_s": v_eci,
        "q_ib_init": q_ib_init,
        "omega_init": omega_init,
        "init_att_err_deg": angle_deg,
        "init_rate_deg_s": w_mag_deg_s,
        "raan_deg": float(np.rad2deg(raan)),
        "nu_deg": float(np.rad2deg(nu)),
        "inc_deg": float(np.rad2deg(inc)),
        "altitude_km": (float(np.linalg.norm(r_eci)) - 6_371_000.0) / 1000.0,
    }


def compute_orbit_ring_eci_km(
    r_eci_m: np.ndarray,
    v_eci_m_s: np.ndarray,
    mu: float,
    n_pts: int = 128,
) -> list[list[float]]:
    """Generate one closed Keplerian orbit ring [km] for 3D visualization."""
    r0 = float(np.linalg.norm(r_eci_m))
    h_vec = np.cross(r_eci_m, v_eci_m_s)
    h_hat = h_vec / (float(np.linalg.norm(h_vec)) + 1e-12)
    e_hat_r = r_eci_m / (r0 + 1e-12)
    e_hat_t = np.cross(h_hat, e_hat_r)
    v2 = float(np.dot(v_eci_m_s, v_eci_m_s))
    a_m = 1.0 / max(2.0 / r0 - v2 / mu, 1e-12)
    e_vec = ((v2 - mu / r0) * r_eci_m - float(np.dot(r_eci_m, v_eci_m_s)) * v_eci_m_s) / mu
    ecc = min(float(np.linalg.norm(e_vec)), 0.05)
    p = a_m * (1.0 - ecc * ecc)
    pts: list[list[float]] = []
    for k in range(n_pts + 1):
        theta = 2.0 * math.pi * k / n_pts
        rad_km = (p / (1.0 + ecc * math.cos(theta))) / 1000.0
        pos = rad_km * (math.cos(theta) * e_hat_r + math.sin(theta) * e_hat_t)
        pts.append([round(float(pos[0]), 2), round(float(pos[1]), 2), round(float(pos[2]), 2)])
    return pts


def run_basilisk_mission(
    sc_cfg: SpacecraftConfig,
    *,
    seed: int,
    wheel_loss: float,
    fault_wheel: int,
    controller_name: str,
    checkpoint_dir: Path | None,
    duration_s: float,
    vizard_file: Path | None = None,
    vizard_live: bool = False,
) -> dict[str, Any]:
    """Run one complete live Basilisk 2.12.2 closed-loop 3D mission scenario."""
    if not is_basilisk_available():
        raise RuntimeError(
            "Basilisk is not available in this Python interpreter. "
            "Run with `.venv_bsk\\Scripts\\python.exe`."
        )

    rng = np.random.default_rng(seed)
    init = sample_random_orbit_and_attitude(sc_cfg, rng)
    dt = sc_cfg.simulation.control_period_s
    n_steps = int(round(duration_s / dt))
    n_rw = sc_cfg.reaction_wheels.count
    tau_lim = sc_cfg.reaction_wheels.torque_limit_nominal_nm

    # Scale event timestamps cleanly to mission duration so both short (120 s)
    # and orbit-scale (1500+ s) runs show clear acquisition, disturbance, and RW fault phases.
    if duration_s >= 600.0:
        t_dist1_start = 150.0
        t_dist1_end = 195.0
        t_fault_start = 320.0
        t_dist2_start = 360.0
        t_dist2_end = 372.0 if wheel_loss >= 0.95 else 405.0
        record_stride = 2  # 2.5 Hz playback frames -> smooth & compact HTML
    else:
        t_dist1_start = 35.0
        t_dist1_end = 50.0
        t_fault_start = 65.0
        t_dist2_start = 78.0
        t_dist2_end = 90.0
        record_stride = 1  # 5 Hz playback frames

    backend = BasiliskBackend(
        sc_cfg,
        vizard_file=str(vizard_file) if vizard_file is not None else None,
        vizard_live=vizard_live,
    )
    truth = backend.reset(
        q_ib_init=init["q_ib_init"],
        omega_body_init=init["omega_init"],
        wheel_momentum_init=np.zeros(n_rw, dtype=np.float64),
        r_eci_init_m=init["r_eci_m"],
        v_eci_init_m_s=init["v_eci_m_s"],
    )

    ref_gen = NadirReferenceGenerator()
    ref_gen.reset()
    sensors = SensorSuite(SensorSuiteConfig(), n_rw=n_rw)
    sensors.reset(seed=seed + 1000, q_ib_init=truth.q_ib)
    mekf = MultiplicativeEKF(MEKFConfig())
    mekf.reset(q_ib_init=truth.q_ib, omega_init=truth.omega_body_rad_s, time_s=truth.time_s)
    cap_est = OnlineCapabilityEstimator(sc_cfg, CapabilityEstimatorConfig.from_spacecraft(sc_cfg))
    cap_est.reset()

    if controller_name == "A3_strong_classical":
        ctrl: Any = StrongClassicalController(
            sc_cfg,
            lqr_config=ClassicalLQRConfig.from_spacecraft(sc_cfg),
            eso_config=ESOConfig(disturbance_limit_nm=0.8 * tau_lim),
            name="A3_strong_classical",
        )
    else:
        policy = None
        if checkpoint_dir is not None and (checkpoint_dir / "policy_weights.npz").exists():
            policy = TorchMLPResidualPolicy.load(checkpoint_dir)
        ctrl = CCRController(
            sc_cfg,
            policy,
            CCRControllerConfig(
                name=controller_name,
                lqr=ClassicalLQRConfig.from_spacecraft(sc_cfg),
                gate=GateConfig(max_residual_torque_nm=0.4 * tau_lim),
                use_eso_backbone=(controller_name == "A7_ccr_v2_eso"),
                eso=ESOConfig(disturbance_limit_nm=0.8 * tau_lim),
            ),
        )
    ctrl.reset()

    last_cmd: ActuatorCommand | None = None
    true_eff = np.ones(n_rw, dtype=np.float64)

    dist1_vec = np.array([0.22, -0.18, 0.16], dtype=np.float64) * tau_lim
    dist2_vec = np.zeros(3, dtype=np.float64)
    if wheel_loss >= 0.95:
        # Realistic LEO post-failure perturbation (~1.2 mN*m brief impulse) that kicks the
        # dead axis ~15-20 deg off nadir so we can watch the 2.0 A*m^2 MTQs + 2 RWs recover!
        dist2_vec[fault_wheel % 3] = 0.008 * tau_lim
        dist2_vec[(fault_wheel + 1) % 3] = -0.05 * tau_lim
    else:
        dist2_vec[fault_wheel % 3] = 0.20 * tau_lim
        dist2_vec[(fault_wheel + 1) % 3] = -0.10 * tau_lim

    frames: list[dict[str, Any]] = []
    all_errs: list[float] = []
    all_ts: list[float] = []

    for step_idx in range(n_steps):
        t = truth.time_s

        dist_active = np.zeros(3, dtype=np.float64)
        phase = "ACQUISITION"
        if t < t_dist1_start:
            phase = "ACQUISITION"
        elif t_dist1_start <= t < t_dist1_end:
            phase = "DISTURBANCE"
            # Zero-net-impulse push-pull wave: produces a vivid multi-degree attitude reaction
            # without biasing healthy wheel momentum far from zero before the fault phase.
            s_frac = (t - t_dist1_start) / max(t_dist1_end - t_dist1_start, 1e-6)
            dist_active = dist1_vec * math.sin(2.0 * math.pi * s_frac)
        elif t_dist1_end <= t < t_fault_start:
            phase = "NOMINAL_LOCK"
        else:
            true_eff = np.ones(n_rw, dtype=np.float64)
            true_eff[fault_wheel] = max(0.0, 1.0 - wheel_loss)
            backend.set_rw_fault(effectiveness=true_eff)
            if t_dist2_start <= t < t_dist2_end:
                phase = "FAULT_PERTURBED"
                s_frac = (t - t_dist2_start) / max(t_dist2_end - t_dist2_start, 1e-6)
                dist_active = dist2_vec * (0.5 + 0.5 * math.sin(math.pi * s_frac))
            else:
                phase = "WHEEL_FAULT"

        backend.set_external_disturbance_body_nm(dist_active)

        meas = sensors.measure(truth, dt_s=dt)
        ref = ref_gen.compute(t, truth.position_eci_m, truth.velocity_eci_m_s)
        est = mekf.update(meas, dt_s=dt)
        cap = cap_est.estimate(
            time_s=t,
            measurement=meas,
            last_command=last_cmd,
            b_field_body_t=meas.mag_body_t,
            dt_s=dt,
        )

        ctrl_out = ctrl.compute(
            estimator_out=est,
            reference=ref,
            capability=cap,
            measurement=meas,
            dt_s=dt,
        )
        cmd = ctrl_out.command
        gate = ctrl_out.gate_decision
        mode_val = ctrl_out.mode.value

        att_err_deg = math.degrees(quat_geodesic_angle(quat_error(ref.q_ir, truth.q_ib)))
        rate_err_deg_s = math.degrees(
            float(np.linalg.norm(truth.omega_body_rad_s - ref.omega_ref_inertial_in_ref_rad_s))
        )
        r_hat_eci = truth.position_eci_m / (float(np.linalg.norm(truth.position_eci_m)) + 1e-12)
        nadir_body = quat_rotate_vec_inv(truth.q_ib, -r_hat_eci)
        dcm_ib = quat_to_dcm(truth.q_ib)
        r_km = truth.position_eci_m / 1000.0
        v_km_s = truth.velocity_eci_m_s / 1000.0
        rw_rpm = truth.wheel_speed_rad_s * (60.0 / (2.0 * math.pi))

        tau_ach = (
            sc_cfg.reaction_wheels.axis_matrix_body @ truth.rw_torque_achieved_nm
            + truth.mtq_torque_achieved_nm
        )

        all_errs.append(float(att_err_deg))
        all_ts.append(float(t))

        if step_idx % record_stride == 0 or step_idx == n_steps - 1:
            frames.append(
                {
                    "t": round(float(t), 2),
                    "phase": phase,
                    "r_km": [round(float(x), 2) for x in r_km],
                    "v_km_s": [round(float(x), 3) for x in v_km_s],
                    "dcm": [[round(float(v), 4) for v in row] for row in dcm_ib],
                    "nadir_b": [round(float(x), 4) for x in nadir_body],
                    "att_err_deg": round(float(att_err_deg), 3),
                    "rate_deg_s": round(float(rate_err_deg_s), 3),
                    "dist_nm": [round(float(x), 5) for x in dist_active],
                    "tau_ach_nm": [round(float(x), 5) for x in tau_ach],
                    "rw_rpm": [round(float(x), 1) for x in rw_rpm],
                    "rw_eff_true": [round(float(x), 3) for x in true_eff],
                    "rw_eff_est": [round(float(w.effectiveness_nom), 3) for w in cap.wheels],
                    "mtq_cmd": [round(float(x), 2) for x in cmd.mtq_dipole_cmd_am2],
                    "rho": round(float(gate.rho), 3),
                    "alpha": round(float(gate.alpha), 3),
                    "mode": mode_val,
                }
            )

        step_out = backend.step(cmd.rw_torque_cmd_nm, cmd.mtq_dipole_cmd_am2)
        truth = step_out.truth
        last_cmd = cmd

    errs = np.array(all_errs, dtype=np.float64)
    ts = np.array(all_ts, dtype=np.float64)
    lock_start = max(25.0, t_dist1_start - 40.0)
    pre_dist = errs[(ts >= lock_start) & (ts < t_dist1_start)]
    during_dist = errs[(ts >= t_dist1_start) & (ts < t_dist1_end)]
    post_fault = errs[ts >= t_fault_start]

    return {
        "label": f"{int(round(wheel_loss * 100))}% Wheel Failure (RW{fault_wheel + 1})",
        "wheel_loss_pct": int(round(wheel_loss * 100)),
        "fault_wheel": fault_wheel,
        "controller": controller_name,
        "seed": seed,
        "basilisk_version": backend.backend_version,
        "spacecraft_name": sc_cfg.name,
        "tau_lim_nm": float(tau_lim),
        "frame_hz": round(1.0 / (dt * record_stride), 3),
        "events": {
            "dist1_start": t_dist1_start,
            "dist1_end": t_dist1_end,
            "fault_start": t_fault_start,
            "dist2_start": t_dist2_start,
            "dist2_end": t_dist2_end,
            "duration_s": duration_s,
        },
        "init": {
            "att_err_deg": round(float(init["init_att_err_deg"]), 2),
            "rate_deg_s": round(float(init["init_rate_deg_s"]), 2),
            "altitude_km": round(float(init["altitude_km"]), 1),
            "inc_deg": round(float(init["inc_deg"]), 1),
            "raan_deg": round(float(init["raan_deg"]), 1),
            "nu_deg": round(float(init["nu_deg"]), 1),
        },
        "summary": {
            "nadir_locked_deg": round(float(np.mean(pre_dist)) if len(pre_dist) else 0.0, 3),
            "peak_disturbance_deg": round(
                float(np.max(during_dist)) if len(during_dist) else 0.0, 3
            ),
            "peak_post_fault_deg": round(float(np.max(post_fault)) if len(post_fault) else 0.0, 3),
            "final_err_deg": round(float(errs[-1]), 3),
        },
        "orbit_ring_km": compute_orbit_ring_eci_km(
            init["r_eci_m"],
            init["v_eci_m_s"],
            sc_cfg.orbit.gravitational_parameter_m3_s2,
        ),
        "vizard_file": str(vizard_file) if vizard_file is not None else "",
        "frames": frames,
    }


def build_interactive_3d_html(scenarios: list[dict[str, Any]], out_html: Path) -> None:
    """Write a self-contained, zero-CDN, interactive 3D Mission Studio HTML file."""
    template = TEMPLATE_HTML.read_text(encoding="utf-8")
    payload_json = json.dumps(scenarios, separators=(",", ":"))
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(template.replace("__SCENARIOS_JSON__", payload_json), encoding="utf-8")


def launch_matplotlib_live_3d(sc: dict[str, Any]) -> None:
    """Optional native desktop Matplotlib 3D live animation window."""
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation

    frames = sc["frames"]
    fig = plt.figure(figsize=(12, 5.5))
    ax_orb = fig.add_subplot(121, projection="3d")
    ax_sat = fig.add_subplot(122, projection="3d")

    u = np.linspace(0, 2 * np.pi, 24)
    v = np.linspace(0, np.pi, 16)
    ex = 6371.0 * np.outer(np.cos(u), np.sin(v))
    ey = 6371.0 * np.outer(np.sin(u), np.sin(v))
    ez = 6371.0 * np.outer(np.ones_like(u), np.cos(v))
    ring = np.array(sc["orbit_ring_km"])

    def update(idx: int) -> None:
        f = frames[idx]
        ax_orb.cla()
        ax_orb.plot_wireframe(ex, ey, ez, color="#1d4ed8", alpha=0.28, linewidth=0.6)
        ax_orb.plot(ring[:, 0], ring[:, 1], ring[:, 2], color="#38bdf8", linewidth=1.2)
        rk = f["r_km"]
        ax_orb.scatter([rk[0]], [rk[1]], [rk[2]], color="#ef4444", s=60)
        ax_orb.plot([rk[0], 0], [rk[1], 0], [rk[2], 0], "g--", linewidth=1.3)
        ax_orb.set_xlim(-8000, 8000)
        ax_orb.set_ylim(-8000, 8000)
        ax_orb.set_zlim(-8000, 8000)
        ax_orb.set_title(f"Orbit ECI | t={f['t']:.1f}s | {f['phase']}")

        ax_sat.cla()
        dcm = np.array(f["dcm"])
        for col, c, lbl in [(0, "r", "+X RW1"), (1, "g", "+Y"), (2, "b", "+Z Cam")]:
            vec = dcm[:, col]
            ax_sat.quiver(0, 0, 0, vec[0], vec[1], vec[2], color=c, label=lbl, linewidth=2.0)
        r_hat = np.array(rk) / (np.linalg.norm(rk) + 1e-12)
        nadir = -r_hat
        ax_sat.quiver(
            0, 0, 0, nadir[0], nadir[1], nadir[2], color="lime", linestyle="--", label="Nadir"
        )
        ax_sat.set_xlim(-1.4, 1.4)
        ax_sat.set_ylim(-1.4, 1.4)
        ax_sat.set_zlim(-1.4, 1.4)
        ax_sat.legend(loc="upper right", fontsize=8)
        ax_sat.set_title(f"Att Err: {f['att_err_deg']:.2f} deg | Mode: {f['mode']}")

    _anim = FuncAnimation(fig, update, frames=range(0, len(frames), 2), interval=60, repeat=True)
    plt.tight_layout()
    plt.show()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Live 3D Basilisk 2.12.2 + CCR v2 Orbit, Disturbance & Wheel-Failure Demo"
    )
    parser.add_argument(
        "--spacecraft-config",
        type=Path,
        default=REPO_ROOT / "spacecraft_config.yaml",
        help="Path to spacecraft YAML config",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for initial orbit/tumble")
    parser.add_argument(
        "--wheel-loss",
        type=float,
        default=0.8,
        help="Fractional wheel loss in [0, 1] (e.g. 0.2=20%%, 0.8=80%%, 1.0=100%%)",
    )
    parser.add_argument(
        "--compare-all",
        action="store_true",
        help="Run 20%%, 80%%, and 100%% wheel failure in Basilisk and embed all 3 in the 3D studio",
    )
    parser.add_argument("--fault-wheel", type=int, default=0, help="Failed wheel index (0=RW1)")
    parser.add_argument(
        "--controller",
        type=str,
        default="A7_ccr_v2_eso",
        choices=["A7_ccr_v2_eso", "A7_ccr_v2_full", "A3_strong_classical"],
    )
    parser.add_argument("--checkpoint", type=Path, default=None, help="Trained RL checkpoint dir")
    parser.add_argument(
        "--duration",
        type=float,
        default=1500.0,
        help="Mission duration [s] (default 1500 s = 25 min ~ 96 deg real LEO orbit arc)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "results" / "live_3d_basilisk_demo",
        help="Output directory for HTML studio and Basilisk Vizard .bin files",
    )
    parser.add_argument(
        "--vizard-live",
        action="store_true",
        help="Stream live directly to a running Basilisk Vizard application",
    )
    parser.add_argument(
        "--matplotlib-live",
        action="store_true",
        help="Open a native live 3D Matplotlib window after simulation",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Automatically open the interactive 3D HTML studio in default browser",
    )
    args = parser.parse_args()

    sc_cfg = load_spacecraft_config(args.spacecraft_config)
    ckpt = args.checkpoint if args.checkpoint is not None else find_default_checkpoint()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    loss_levels = [0.2, 0.8, 1.0] if args.compare_all else [float(args.wheel_loss)]
    scenarios: list[dict[str, Any]] = []

    print(
        f"[Live 3D Basilisk Demo] Spacecraft={sc_cfg.name}, Controller={args.controller}, "
        f"Seed={args.seed}, Checkpoint={'loaded' if ckpt else 'fallback-zero'}"
    )
    for loss in loss_levels:
        pct = int(round(loss * 100))
        viz_bin = args.out_dir / f"basilisk_vizard_rw{args.fault_wheel + 1}_loss_{pct}pct.bin"
        print(f"  -> Live Basilisk 2.12.2 mission ({pct}% RW{args.fault_wheel + 1} loss)...")
        sc_data = run_basilisk_mission(
            sc_cfg,
            seed=args.seed,
            wheel_loss=loss,
            fault_wheel=args.fault_wheel,
            controller_name=args.controller,
            checkpoint_dir=ckpt,
            duration_s=args.duration,
            vizard_file=None if args.vizard_live else viz_bin,
            vizard_live=args.vizard_live,
        )
        scenarios.append(sc_data)
        s = sc_data["summary"]
        print(
            f"     Init={sc_data['init']['att_err_deg']} deg | "
            f"Nadir Lock={s['nadir_locked_deg']} deg | "
            f"Dist Peak={s['peak_disturbance_deg']} deg | "
            f"Post-Fault Peak={s['peak_post_fault_deg']} deg | "
            f"Final={s['final_err_deg']} deg | Vizard={viz_bin.name}"
        )

    out_html = args.out_dir / "live_3d_basilisk_studio.html"
    build_interactive_3d_html(scenarios, out_html)
    print(f"[DONE] Interactive 3D Mission Studio saved to: {out_html}")

    if args.open:
        webbrowser.open(out_html.resolve().as_uri())
    if args.matplotlib_live:
        launch_matplotlib_live_3d(scenarios[-1])


if __name__ == "__main__":
    main()
