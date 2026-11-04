"""Gymnasium environment for the ADCS simulator — RL baselines (Phase 2).

Action  : desired body torque (3) in [-1,1] -> tau_des = a * tau_scale * rw_max_torque
Obs (9) : pointing error (rotvec, 3) + body-rate error (3) + wheel speeds (3)
Reward  : shape(||theta||) - w_rate*||omega_err||^2 - w_ctrl*||u||^2
          with an optional per-step tolerance bonus  (config: satellite_adcs/config/rl.yaml)
Faults  : randomized reaction-wheel health per episode (fault_mode).

Reward shapes (config key `rl.reward_shape`):
  - "quad"  : r = -w_theta*||theta||^2 - ...      (classic quadratic, flat near zero)
  - "log"   : r = -log(1 + ||theta||^2/theta_tol^2) - ...  (steep near zero)
  - "bonus" : "quad" + reward_tol_bonus while ||theta|| < reward_tol_deg

Why shaping: the quadratic cost is dominated by the acquisition transient, so the
fine-pointing regime provides almost no gradient. The log/bonus shapes restore the
learning signal exactly where precision matters (see docs/Phase2_RL_RewardShaping_Plan.md).

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
from ..health_estimation import WheelHealthEstimator
from ..quaternion import quat_error, theta_vec, quat_to_dcm


class ADCSEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, cfg=None, fault_mode=None, health_range=None,
                 control_hz=None, episode_time=None, tau_scale=None, seed=None,
                 health_source=None, overrides=None):
        self.cfg = cfg if cfg is not None else load_config(overrides)
        sim = self.cfg["simulation"]
        rl = self.cfg.get("rl", {}) or {}

        # -- config-driven defaults (explicit args / CLI flags still win) --------
        if fault_mode is None:
            fault_mode = rl.get("fault_mode", "random_health")
        if health_range is None:
            health_range = tuple(rl.get("health_range", [0.5, 1.0]))
        if control_hz is None:
            control_hz = float(rl.get("control_hz", sim["control_hz"]))
        if episode_time is None:
            episode_time = float(rl.get("episode_time_s", 900.0))
        if tau_scale is None:
            tau_scale = float(rl.get("tau_scale", 1.0))

        self.dt = sim["dt_s"]
        # integer number of integrator substeps per control period; the effective
        # period is n_sub*dt so the simulated horizon is exactly `episode_time`
        self.n_sub = max(1, int(round((1.0 / float(control_hz)) / self.dt)))
        self.control_period = self.n_sub * self.dt
        self.control_hz = 1.0 / self.control_period
        self.max_steps = int(round(float(episode_time) / self.control_period))
        self.episode_time = float(episode_time)
        self.tau_scale = float(tau_scale)

        rw = self.cfg["actuators"]["reaction_wheels"]
        self.rw_max_torque = rw["max_torque_Nm"]
        self.rw_max_speed = rw["max_speed_rad_s"]
        self.rw_J = rw["inertia_kgm2"]
        self.n_rw = rw["count"]
        self.mtq_max_dipole = self.cfg["actuators"]["magnetorquers"]["max_dipole_Am2"]

        # M1 (D-C2h-1a): wheel-health estimator. Only used when
        # health_source == "hat"; with "true" the oracle allocator is untouched.
        self.health_est = WheelHealthEstimator(rw_J=self.rw_J,
                                              control_period=self.control_period)
        self._last_tau_cmd = np.zeros(self.n_rw, dtype=float)

        self.fault_mode = fault_mode
        self.health_range = health_range
        self.health_source = str(
            health_source if health_source is not None
            else rl.get("health_source", "true")).lower()
        # D4: per-episode Coulomb-friction randomisation. None keeps a fixed plant
        # (every historical result is therefore unchanged). When set, each episode
        # draws rw_c_coul ~ U(lo, hi), which is what lets a policy learn "apply no
        # correction when there is no friction" -- the only way Experiment 1 can pass.
        _fr = rl.get("friction_range", None)
        self.friction_range = tuple(float(v) for v in _fr) if _fr else None

        # -- reward shaping (config-driven) -------------------------------------
        self.reward_shape = str(rl.get("reward_shape", "bonus")).lower()
        self.w_theta = float(rl.get("reward_theta_weight", 1.0))
        self.w_rate = float(rl.get("reward_rate_weight", 0.1))
        self.w_ctrl = float(rl.get("reward_control_weight", 1e-2))
        self.reward_tol_rad = float(np.radians(rl.get("reward_tol_deg", 1.0)))
        self.reward_tol_bonus = float(rl.get("reward_tol_bonus", 1.0))

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

    def _reward(self, theta, omega_err, a):
        """Config-driven shaped reward; returns (reward, components-dict)."""
        theta2 = float(theta @ theta)
        rate2 = float(omega_err @ omega_err)
        ctrl2 = float(a @ a)
        if self.reward_shape == "tol_norm":
            # D3: normalise by the TOLERANCE, not by raw radians.
            # (theta/theta_tol)^2 is 2.56 at 1.6 deg and 0.81 at 0.9 deg, so the
            # gradient in the band where the LQR parks is ~1.75/step (~7900 per
            # episode) instead of ~5e-4/step (~2.4) -- about 3000x stronger, and
            # exactly where the task is decided. Raw theta^2 is noise there.
            eps = max(self.reward_tol_rad ** 2, 1e-12)
            r_err = -self.w_theta * float(theta2 / eps)
        elif self.reward_shape == "log":
            eps = max(self.reward_tol_rad ** 2, 1e-12)
            r_err = -float(np.log1p(theta2 / eps))
        else:                                              # "quad" | "bonus"
            r_err = -self.w_theta * theta2
        reward = r_err - self.w_rate * rate2 - self.w_ctrl * ctrl2
        in_tol = float(np.linalg.norm(theta)) < self.reward_tol_rad
        if self.reward_shape == "bonus" and in_tol:
            reward += self.reward_tol_bonus
        comp = {"r_err": r_err, "r_rate": -self.w_rate * rate2,
                "r_ctrl": -self.w_ctrl * ctrl2, "in_tol": float(in_tol)}
        return float(reward), comp

    # ---------------------------------------------------------------- gym API
    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self.rng = np.random.default_rng(seed)
            self.dyn.rng = self.rng
            self.sensors.rng = self.rng
        # `options` lets a caller inject the initial condition and gyro bias so
        # that two different controllers can be compared on IDENTICAL conditions
        # (paired evaluation). Default path: draw from `self.rng`, unchanged.
        opt = options or {}
        self.dyn.reset(q=opt.get("q", None), omega=opt.get("omega", None))
        if opt.get("gyro_bias") is not None:
            self.sensors.set_bias(opt["gyro_bias"])
        self.dyn.set_rw_health(self._sample_health())
        # C2-e: a reset attitude is UNKNOWN, so call the estimator's own reset
        # rather than poking its fields. Setting only q_hat/P here left b_hat
        # (the gyro-bias state) and the bias covariance STALE from the previous
        # episode: harmless while the bias is constant, but wrong whenever the
        # bias changes between episodes -- exactly what the paired harness does,
        # which draws a fresh bias per episode. It also silently carried a bias
        # estimate across resets that never re-derived it.
        self.est.reset()
        # M1: fresh episode = fresh health estimate (see the C2-e note above --
        # estimator state must never leak across episodes).
        if self.friction_range is not None:
            lo, hi = self.friction_range
            self.dyn.rw_c_coul = float(self.rng.uniform(lo, hi))
        self.health_est.reset()
        self.health_est.prime(self.dyn.omega_w)
        self._last_tau_cmd = np.zeros(self.n_rw, dtype=float)
        meas = self.sensors.measure(self.dyn)
        self.est.update(meas, self.dyn)
        self._last_gyro = meas["gyro"]
        self._step_count = 0
        return self._obs(), {"rw_health": self.dyn.rw_health.copy()}

    def step(self, action):
        a = np.clip(np.asarray(action, dtype=float), -1.0, 1.0)
        tau_des = a * self.tau_scale * self.rw_max_torque
        # M1 (D-C2h-1a): allocate from an ESTIMATE when configured. The estimate
        # is updated from the PREVIOUS commanded torque and the measured wheel
        # speed, i.e. only quantities a real spacecraft has.
        h_alloc = None
        if self.health_source == "hat":
            self.health_est.update(self._last_tau_cmd, self.dyn.omega_w)
            h_alloc = self.health_est.h.copy()
        tau_cmd, m = allocate_torque(tau_des, self.dyn, self.rw_max_torque,
                                     self.mtq_max_dipole, self.rw_J,
                                     k_desat=0.02, momentum_mgmt=True,
                                     health=h_alloc)
        self._last_tau_cmd = np.asarray(tau_cmd, dtype=float).copy()

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

        reward, comp = self._reward(theta, omega_err, a)
        self._step_count += 1
        truncated = self._step_count >= self.max_steps
        info = {
            "rw_health": self.dyn.rw_health.copy(),
            # The commanded WHEEL torque actually issued by the allocator this step,
            # post-clip and pre-health. A real spacecraft knows this (it issued it),
            # and the C2-h health estimator needs it as its regressor. Purely
            # additive: it does not touch obs, reward or the dynamics.
            "tau_cmd": np.asarray(tau_cmd, dtype=float).copy(),
            "pointing_error_deg": self.pointing_error_deg(),
            "theta_rad": float(np.linalg.norm(theta)),
            "reward_components": comp,
        }
        return self._obs(), reward, False, truncated, info
