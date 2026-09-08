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


def pointing_error_deg(dyn):
    zB_I = dyn.C.T @ np.array([0.0, 0.0, 1.0])     # body +z axis in inertial
    nadir = -dyn.r / np.linalg.norm(dyn.r)
    return np.degrees(np.arccos(np.clip(np.dot(zB_I, nadir), -1, 1)))


def run_episode(cfg, seed=0, T=None):
    sim = cfg["simulation"]
    if T is None:
        T = sim["episode_duration_s"]
    rng = np.random.default_rng(seed)
    dyn = SpacecraftDynamics(cfg, rng)
    sensors = SensorSuite(cfg, rng)
    est = MEKF(cfg)
    ctrl = ADCSController(cfg, dyn.J, dyn.mu, dyn.a, rng)
    dyn.reset()
    est.q_hat = np.array([1.0, 0, 0, 0])
    est.P = np.eye(3) * 1e-2

    dt = sim["dt_s"]
    ctrl_period = 1.0 / sim["control_hz"]
    nctrl = max(1, int(round(ctrl_period / dt)))
    t = 0.0
    t_arr, pe, om, ow, ph = [], [], [], [], []
    while t < T:
        meas = sensors.measure(dyn)
        est.update(meas, dyn)                       # correct to CURRENT measurement
        tau_rw, m = ctrl.control(meas, est, dyn, t, ctrl_period)
        # step dynamics AND propagate estimator in lockstep (same elapsed time)
        for _ in range(nctrl):
            dyn.step(dt, tau_rw, m)
            est.propagate(meas["gyro"], dt)
        t += ctrl_period
        t_arr.append(t)
        pe.append(pointing_error_deg(dyn))
        om.append(np.linalg.norm(dyn.omega))
        ow.append(np.max(np.abs(dyn.omega_w)))
        ph.append(ctrl.phase)

    return dict(t=np.array(t_arr), pe=np.array(pe), om=np.array(om),
                ow=np.array(ow), phase=np.array(ph), dyn=dyn, cfg=cfg)


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
