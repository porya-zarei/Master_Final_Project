"""Gymnasium environment for the ADCS simulator (for later RL training)."""
from __future__ import annotations
import numpy as np
import gymnasium as gym
from gymnasium import spaces

from ..config import load_config
from ..dynamics import SpacecraftDynamics
from ..sensors import SensorSuite
from ..estimation import MEKF
from ..guidance import NadirGuidance
from ..quaternion import quat_error, theta_vec, quat_to_dcm


class ADCSEnv(gym.Env):
    """RL wrapper: action = desired body torque; obs = pointing/rate/wheel state.

    Reward (per step) mirrors the thesis cost functional:
        r = -( w_e * theta^2 + w_omega * |omega_err|^2 + w_u * |tau|^2 )
    """

    def __init__(self, cfg=None, overrides=None):
        self.cfg = cfg if cfg is not None else load_config(overrides)
        sim = self.cfg["simulation"]
        self.dt = sim["dt_s"]
        self.control_period = 1.0 / sim["control_hz"]
        self.rw_max_torque = self.cfg["actuators"]["reaction_wheels"]["max_torque_Nm"]
        self.n_rw = self.cfg["actuators"]["reaction_wheels"]["count"]

        self.rng = np.random.default_rng(sim["random_seed"])
        self.dyn = SpacecraftDynamics(self.cfg, self.rng)
        self.sensors = SensorSuite(self.cfg, self.rng)
        self.est = MEKF(self.cfg)
        self.guidance = NadirGuidance(self.cfg["orbit"]["mu_m3_s2"], self.dyn.a)

        self.action_space = spaces.Box(-1.0, 1.0, (3,), dtype=np.float64)
        self.observation_space = spaces.Box(-1e3, 1e3, (9,), dtype=np.float64)

    def _obs(self, use_est=True):
        q_ref, wr = self.guidance.reference(self.dyn.r, self.dyn.v)
        q_cur = self.est.q_hat if use_est else self.dyn.q
        w_cur = self.est.gyro_rate(self.sensors.measure(self.dyn)["gyro"]) if use_est \
            else self.dyn.omega
        q_err = quat_error(q_cur, q_ref)
        theta = theta_vec(q_err)
        w_err = w_cur - quat_to_dcm(q_err) @ wr
        return np.concatenate([theta, w_err, self.dyn.omega_w]).astype(np.float64)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self.rng = np.random.default_rng(seed)
            self.dyn.rng = self.rng
            self.sensors.rng = self.rng
        self.dyn.reset()
        self.est.q_hat = np.array([1.0, 0, 0, 0])
        self.est.P = np.eye(3) * 1e-2
        return self._obs(), {}

    def step(self, action):
        tau_des = np.clip(np.asarray(action, float), -1, 1) * self.rw_max_torque
        m = np.zeros(3)
        n = max(1, int(round(self.control_period / self.dt)))
        meas = self.sensors.measure(self.dyn)
        self.est.update(meas, self.dyn)             # correct to current measurement
        for _ in range(n):
            self.dyn.step(self.dt, tau_des, m)
            self.est.propagate(meas["gyro"], self.dt)

        q_ref, wr = self.guidance.reference(self.dyn.r, self.dyn.v)
        q_err = quat_error(self.est.q_hat, q_ref)
        theta = theta_vec(q_err)
        w_err = self.est.gyro_rate(meas["gyro"]) - quat_to_dcm(q_err) @ wr

        reward = -(np.sum(theta**2) + 0.1 * np.sum(w_err**2) + 1e-3 * np.sum(tau_des**2))
        obs = self._obs()
        return obs, reward, False, False, {}
