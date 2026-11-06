"""Closed-loop ADCS simulation: B-dot detumble + LQR nadir pointing (M0/M1).

Run from `codes/`:
    python simulate.py --seed 0 --T 600 --plot results/nadir_0.png
"""
from __future__ import annotations
import argparse
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from satellite_adcs.config import load_config
from satellite_adcs.dynamics import SpacecraftDynamics
from satellite_adcs.sensors import SensorSuite
from satellite_adcs.estimation import MEKF
from satellite_adcs.controllers import ADCSController
from satellite_adcs.quaternion import random_quat


def pointing_error_deg(dyn):
    zB_I = dyn.C.T @ np.array([0.0, 0.0, 1.0])     # body +z axis in inertial
    nadir = -dyn.r / np.linalg.norm(dyn.r)
    return np.degrees(np.arccos(np.clip(np.dot(zB_I, nadir), -1, 1)))


def make_ic_bias(seed, cfg=None):
    """Single source of truth for (q0, omega0, gyro_bias) -- G14/step 4.

    Both the RL environment and the classical controller path MUST take their
    conditions from here, otherwise a comparison is not paired. The pre-fix
    harness drew ICs from different positions in the same RNG stream, and gave
    the RL side one frozen bias for all episodes while LQR got a fresh one.
    """
    if cfg is None:
        cfg = load_config()
    rng = np.random.default_rng(10000 + int(seed))
    q0 = random_quat(rng)
    wmax = np.radians(cfg["satellite"]["initial"]["omega_max_deg_per_s"])
    omega0 = rng.uniform(-wmax, wmax, 3)
    bias = cfg["sensors"]["gyro"]["bias_rad_s"] * rng.normal(size=3)
    return q0, omega0, bias


def run_episode(cfg, seed=0, T=None, rw_health=None, momentum_mgmt=True,
                ic=None, gyro_bias=None, controller="lqr", sched_eps=0.05,
                fault_at=None, health_source="true", plant_cfg=None,
                residual_fn=None, residual_alpha=0.0, health_floor=None,
                conservative=False, wheel_sensor=None, record=False):
    sim = cfg["simulation"]
    if T is None:
        T = sim["episode_duration_s"]
    rng = np.random.default_rng(seed)
    # L3/M4: the PLANT may differ from the controller's MODEL. When plant_cfg is
    # given it builds the dynamics only; the controller always uses the NOMINAL
    # inertia from cfg. That separation is the entire point of a mismatch test --
    # building both from the perturbed config would model a perfectly informed
    # controller and measure nothing.
    dyn = SpacecraftDynamics(plant_cfg if plant_cfg is not None else cfg, rng)
    _I = cfg["satellite"]["inertia"]
    J_nom = np.diag([_I["Jxx"], _I["Jyy"], _I["Jzz"]])
    sensors = SensorSuite(cfg, rng)
    est = MEKF(cfg)
    if controller == "scheduled":
        from satellite_adcs.gain_scheduled import ScheduledLQRController
        ctrl = ScheduledLQRController(cfg, J_nom, dyn.mu, dyn.a, rng, eps=sched_eps)
    else:
        ctrl = ADCSController(cfg, J_nom, dyn.mu, dyn.a, rng)
    ctrl.momentum_mgmt = momentum_mgmt
    ctrl.health_floor = health_floor
    # M3.3-B: run the REAL friction/effectiveness estimator inside the loop and let it
    # supply the health state. Ground-truth rw_health is never passed to the controller.
    cons = None
    if conservative:
        from satellite_adcs.friction_estimation import FrictionHealthEstimator
        _rwj = float(cfg["actuators"]["reaction_wheels"]["inertia_kgm2"])
        # ctrl_period is defined further below; derive the same value from `sim`
        cons = FrictionHealthEstimator(rw_J=_rwj,
                                       control_period=1.0 / float(sim["control_hz"]))
        cons.prime(dyn.omega_w)
        ctrl.conservative_alloc = True
        ctrl.health_state = cons.state()
    if ic is not None:
        dyn.reset(q=np.asarray(ic[0], float), omega=np.asarray(ic[1], float))
        if gyro_bias is not None:
            sensors.set_bias(gyro_bias)
    else:
        dyn.reset()
    # M1: with fault_at the fault is applied DURING the episode, which is the
    # regime where adaptation can matter (a fault present from t=0 is already
    # masked by the allocator from the first step).
    fault_pending = rw_health is not None and fault_at is not None
    if rw_health is not None and not fault_pending:
        dyn.set_rw_health(rw_health)
    # C2-e: reset the estimator properly -- see the matching note in
    # adcs_env.reset(). Poking q_hat/P alone left the gyro-bias state stale.
    est.reset()

    dt = sim["dt_s"]
    # integer substeps per control period; the EFFECTIVE period is nctrl*dt, so
    # the labeled time axis equals the simulated time (both RL env and LQR).
    nctrl = max(1, int(round((1.0 / sim["control_hz"]) / dt)))
    ctrl_period = nctrl * dt

    # M1 (D-C2h-1a): the estimated-allocation arm. The estimator is driven ONLY
    # by the previous commanded wheel torque and the measured wheel speed.
    h_est = None
    if health_source == "hat":
        from satellite_adcs.health_estimation import WheelHealthEstimator
        _rw = cfg["actuators"]["reaction_wheels"]
        h_est = WheelHealthEstimator(rw_J=float(_rw["inertia_kgm2"]),
                                     control_period=ctrl_period)
        h_est.reset()
        h_est.prime(dyn.omega_w)
        ctrl.health_source = "hat"
    elif health_source == "unity":
        # M3.3-B control arm: the allocator is told "every wheel is healthy" and is
        # never corrected. This is the NO-FAULT-KNOWLEDGE lower bound -- what an
        # unknown fault costs with no estimator at all. It is the arm the estimated
        # path must beat, and the oracle path (health_source="true") must in turn
        # beat both. Additive: "true" (default) and "hat" are untouched.
        ctrl.health_source = "hat"
        ctrl.health_hat = np.ones(int(ctrl.n_rw), dtype=float)
    prev_tau_rw = np.zeros(3, dtype=float)
    _rw_max = float(cfg["actuators"]["reaction_wheels"]["max_torque_Nm"])
    t = 0.0
    t_arr, pe, om, ow, ph = [], [], [], [], []
    rec = (dict(tau=[], deliv=[], m=[], w=[], h_hat=[], state=[], sigma=[], health=[])
           if record else None)
    while t < T:
        if fault_pending and t >= float(fault_at):
            dyn.set_rw_health(rw_health)
            fault_pending = False
        # M3.3-B: the estimator is allowed to see a MEASURED wheel speed, not the
        # plant state. `wheel_sensor=None` passes dyn.omega_w through unchanged, so
        # the default path is bit-identical; any callable (noise + quantisation)
        # is the stated sensitivity case, because the project has no tachometer.
        _w_meas = dyn.omega_w if wheel_sensor is None else wheel_sensor(dyn.omega_w)
        if h_est is not None:
            h_est.update(prev_tau_rw, _w_meas)
            ctrl.health_hat = h_est.h.copy()
        if cons is not None:
            # estimator sees only commanded torque and measured wheel speed
            cons.update(prev_tau_rw, _w_meas)
            ctrl.health_hat = cons.h.copy()
            ctrl.health_state = cons.state()
        meas = sensors.measure(dyn)
        est.update(meas, dyn)                       # correct to CURRENT measurement
        tau_rw, m = ctrl.control(meas, est, dyn, t, ctrl_period)
        # M1-C remediation / M2 infrastructure: the RL residual acts INSIDE the
        # classical loop, on the torque the phase-managed controller produced. With
        # residual_fn=None the classical path is reproduced exactly, which is the
        # parity M1-C showed the wrapper could not provide.
        if residual_fn is not None:
            _a = residual_fn(dict(meas=meas, est=est, dyn=dyn, t=t,
                                  tau_rw=np.asarray(tau_rw, float),
                                  phase=ctrl.phase))
            if _a is not None:
                tau_rw = np.clip(np.asarray(tau_rw, float)
                                 + residual_alpha * np.clip(np.asarray(_a, float), -1.0, 1.0)
                                 * _rw_max, -_rw_max, _rw_max)
        if h_est is not None or cons is not None:
            prev_tau_rw = np.asarray(tau_rw, dtype=float).copy()
        if record:
            # the EXECUTED wheel command and the torque the wheel actually delivered
            _tau = np.asarray(tau_rw, dtype=float)
            _h = np.asarray(dyn.rw_health, dtype=float)
            rec["tau"].append(_tau.copy())
            rec["deliv"].append(_tau * _h)
            rec["m"].append(np.asarray(m, dtype=float).copy())
            rec["health"].append(_h.copy())
            if cons is not None:
                rec["h_hat"].append(cons.h.astype(float))
                rec["state"].append(cons.state().astype(int))
                rec["sigma"].append(cons.sigma_h.astype(float))
            elif h_est is not None:
                rec["h_hat"].append(h_est.h.astype(float))
                rec["state"].append(np.full(int(ctrl.n_rw), -1, dtype=int))
                rec["sigma"].append(np.zeros(int(ctrl.n_rw), dtype=float))
            else:
                rec["h_hat"].append(np.zeros(int(ctrl.n_rw), dtype=float))
                rec["state"].append(np.full(int(ctrl.n_rw), -1, dtype=int))
                rec["sigma"].append(np.zeros(int(ctrl.n_rw), dtype=float))
        # step dynamics AND propagate estimator in lockstep (same elapsed time)
        for _ in range(nctrl):
            dyn.step(dt, tau_rw, m)
            est.propagate(meas["gyro"], dt)
        if record:
            rec["w"].append(np.asarray(dyn.omega_w, dtype=float).copy())
        t += ctrl_period
        t_arr.append(t)
        pe.append(pointing_error_deg(dyn))
        om.append(np.linalg.norm(dyn.omega))
        ow.append(np.max(np.abs(dyn.omega_w)))
        ph.append(ctrl.phase)

    return dict(t=np.array(t_arr), pe=np.array(pe), om=np.array(om),
                ow=np.array(ow), phase=np.array(ph), dyn=dyn, cfg=cfg,
                h_est=h_est, rw_health=np.asarray(dyn.rw_health, dtype=float),
                cons=cons,
                rec=None if rec is None else {k: np.array(v) for k, v in rec.items()})


def settling_time(t, pe, threshold=1.0, hold=30.0):
    dt = np.median(np.diff(t))
    steps = max(1, int(round(hold / dt)))
    n = len(pe)
    for i in range(n):
        if i + steps <= n and np.all(pe[i:i + steps] < threshold):
            return t[i]
    return np.inf


def plot_episode(res, out_path):
    fig, ax = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    t = res["t"]
    ax[0].plot(t, res["pe"])
    ax[0].set_ylabel("pointing error [deg]")
    ax[0].axhline(1.0, color="r", ls="--", lw=0.8, label="1° threshold")
    ax[0].legend(); ax[0].set_yscale("log")
    ax[1].plot(t, res["om"]); ax[1].set_ylabel("|omega| [rad/s]")
    ax[2].plot(t, res["ow"]); ax[2].set_ylabel("max wheel speed [rad/s]")
    ax[2].set_xlabel("time [s]")
    ax[0].set_title("ADCS nadir acquisition (B-dot detumble + LQR)")
    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=None)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--T", type=float, default=None)
    p.add_argument("--plot", default="results/nadir_acquisition.png")
    a = p.parse_args()

    cfg = load_config()
    res = run_episode(cfg, seed=a.seed, T=a.T)
    ts = settling_time(res["t"], res["pe"])
    print(f"seed={a.seed}  initial_w={np.degrees(np.linalg.norm(res['dyn'].omega)):.2f} deg/s")
    print(f"pointing error final = {res['pe'][-1]:.3f} deg")
    print(f"RMS pointing error   = {np.sqrt(np.mean(res['pe']**2)):.3f} deg")
    print(f"max pointing error   = {res['pe'].max():.3f} deg")
    print(f"settling time (<1°)  = {ts:.1f} s  ({'NOT SETTLED' if np.isinf(ts) else 'settled'})")
    print(f"max wheel speed      = {res['ow'].max():.1f} rad/s")
    plot_episode(res, a.plot)
    print(f"plot saved: {a.plot}")


if __name__ == "__main__":
    main()
