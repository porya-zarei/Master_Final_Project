"""Gymnasium environment for the ADCS simulator — RL baselines (Phase 2).

Action  : desired body torque (3) in [-1,1] -> tau_des = a * tau_scale * rw_max_torque
Obs (9) : pointing error (rotvec, 3) + body-rate error (3) + wheel speeds (3)
Reward  : -(|theta|^2 + 0.1*|omega_err|^2 + 1e-2*|u|^2)
Faults  : randomized reaction-wheel health per episode (fault_mode).

The low-level fault-tolerant allocator (health inversion + MTQ residual +
momentum desaturation) is shared with the LQR controller, so the LQR and the RL
agent operate at the same abstraction level (both output a desired torque).
"""
from __future__ import annotations
import numpy as np
import gymnasium as gym
from gymnasium import spaces

from ..config import load_config
from ..dynamics import SpacecraftDynamics
from ..sensors import SensorSuite
from ..estimation import MEKF
from ..guidance import NadirGuidance
from ..controllers import allocate_torque
from ..quaternion import quat_error, theta_vec, quat_to_dcm


class ADCSEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, cfg=None, fault_mode="random_health", health_range=(0.5, 1.0),
                 control_hz=2.0, episode_time=300.0, tau_scale=1.0, seed=None,
                 overrides=None):
        self.cfg = cfg if cfg is not None else load_config(overrides)
        sim = self.cfg["simulation"]
        self.dt = sim["dt_s"]
        self.control_period = 1.0 / control_hz
        self.n_sub = max(1, int(round(self.control_period / self.dt)))
        self.max_steps = int(round(episode_time / self.control_period))
        self.tau_scale = tau_scale

        rw = self.cfg["actuators"]["reaction_wheels"]
        self.rw_max_torque = rw["max_torque_Nm"]
        self.rw_max_speed = rw["max_speed_rad_s"]
        self.rw_J = rw["inertia_kgm2"]
        self.n_rw = rw["count"]
        self.mtq_max_dipole = self.cfg["actuators"]["magnetorquers"]["max_dipole_Am2"]

        self.fault_mode = fault_mode
        self.health_range = health_range

        self.rng = np.random.default_rng(seed if seed is not None else sim["random_seed"])
        self.dyn = SpacecraftDynamics(self.cfg, self.rng)
        self.sensors = SensorSuite(self.cfg, self.rng)
        self.est = MEKF(self.cfg)
        self.guidance = NadirGuidance(self.cfg["orbit"]["mu_m3_s2"], self.dyn.a)

        self.action_space = spaces.Box(-1.0, 1.0, (3,), dtype=np.float64)
        self.observation_space = spaces.Box(-10.0, 10.0, (9,), dtype=np.float64)
        self._step_count = 0
        self._last_gyro = np.zeros(3)

    # --------------------------------------------------------------- helpers
    def _sample_health(self):
        fm = self.fault_mode
        if fm == "none":
            return np.ones(self.n_rw)
        if fm == "random_health":
            return self.rng.uniform(self.health_range[0], self.health_range[1], self.n_rw)
        if fm == "random_discrete":
            return self.rng.choice([0.5, 0.75, 1.0], size=self.n_rw)
        if fm == "dead_wheel":
            h = np.ones(self.n_rw)
            h[self.rng.integers(0, self.n_rw)] = 0.0
            return h
        return np.ones(self.n_rw)

    def _obs(self):
        q_ref, wr = self.guidance.reference(self.dyn.r, self.dyn.v)
        q_err = quat_error(self.est.q_hat, q_ref)
        theta = theta_vec(q_err)
        omega_err = self.est.gyro_rate(self._last_gyro) - quat_to_dcm(q_err) @ wr
        return np.concatenate([theta, omega_err,
                               self.dyn.omega_w / self.rw_max_speed]).astype(np.float64)

    def pointing_error_deg(self):
        from ..quaternion import quat_to_dcm
        zB = self.dyn.C.T @ np.array([0.0, 0.0, 1.0])
        nadir = -self.dyn.r / np.linalg.norm(self.dyn.r)
        return float(np.degrees(np.arccos(np.clip(zB @ nadir, -1, 1))))

    # ---------------------------------------------------------------- gym API
    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self.rng = np.random.default_rng(seed)
            self.dyn.rng = self.rng
            self.sensors.rng = self.rng
        self.dyn.reset()
        self.dyn.set_rw_health(self._sample_health())
        self.est.q_hat = np.array([1.0, 0, 0, 0])
        self.est.P = np.eye(3) * 1e-2
        meas = self.sensors.measure(self.dyn)
        self.est.update(meas, self.dyn)
        self._last_gyro = meas["gyro"]
        self._step_count = 0
        return self._obs(), {"rw_health": self.dyn.rw_health.copy()}

    def step(self, action):
        a = np.clip(np.asarray(action, dtype=float), -1.0, 1.0)
        tau_des = a * self.tau_scale * self.rw_max_torque
        tau_cmd, m = allocate_torque(tau_des, self.dyn, self.rw_max_torque,
                                     self.mtq_max_dipole, self.rw_J,
                                     k_desat=0.02, momentum_mgmt=True)

        meas = self.sensors.measure(self.dyn)
        self.est.update(meas, self.dyn)
        for _ in range(self.n_sub):
            self.dyn.step(self.dt, tau_cmd, m)
            self.est.propagate(meas["gyro"], self.dt)
        # refresh estimate for the returned observation
        meas2 = self.sensors.measure(self.dyn)
        self.est.update(meas2, self.dyn)
        self._last_gyro = meas2["gyro"]

        q_ref, wr = self.guidance.reference(self.dyn.r, self.dyn.v)
        q_err = quat_error(self.est.q_hat, q_ref)
        theta = theta_vec(q_err)
        omega_err = self.est.gyro_rate(self._last_gyro) - quat_to_dcm(q_err) @ wr

        reward = -(float(theta @ theta) + 0.1 * float(omega_err @ omega_err)
                   + 1e-2 * float(a @ a))
        self._step_count += 1
        truncated = self._step_count >= self.max_steps
        info = {
            "rw_health": self.dyn.rw_health.copy(),
            "pointing_error_deg": self.pointing_error_deg(),
            "theta_rad": float(np.linalg.norm(theta)),
        }
        return self._obs(), reward, False, truncated, info
