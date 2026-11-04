"""Milestone D: residual RL wrapper around ADCSEnv.

    tau_des = tau_LQR + alpha * delta_tau_RL

The nominal LQR is computed from the SAME observation the policy sees, so the
policy learns a *correction*, not the whole control law. The residual is bounded
by construction (action in [-1,1] -> |delta_tau| <= alpha * rw_max_torque per axis).

Deliberately implemented as a gymnasium Wrapper rather than by editing ADCSEnv:
the existing environment, its tests and every historical result stay untouched,
and `residual=0` provably reproduces the LQR (tested).

Observation = base 9 (theta, omega_err, wheel speed) + tau_LQR (3) + previous
action (3) = 15. The directive's fuller list (health estimate, sensor residuals,
B_body, quaternion, wheel momenta) extends the same way and is added in D2.
"""
from __future__ import annotations
import numpy as np
import gymnasium as gym
from gymnasium import spaces

from ..controllers import design_lqr


class ResidualADCSEnv(gym.Wrapper):
    """LQR + bounded learned residual."""

    def __init__(self, env, alpha=0.2, q_diag=None, r_scale=1.0 / 0.010 ** 2,
                 use_prev_action=True):
        super().__init__(env)
        self.alpha = float(alpha)
        I = env.cfg["satellite"]["inertia"]
        J = np.diag([I["Jxx"], I["Jyy"], I["Jzz"]])
        Q = np.diag(q_diag if q_diag is not None
                    else [1.0, 1.0, 1.0, 0.3, 0.3, 0.3])
        R = np.eye(3) * r_scale
        self.K = design_lqr(J, Q, R)
        self.scale = float(env.tau_scale * env.rw_max_torque)
        self.residual_max = self.alpha * float(env.rw_max_torque)
        self.use_prev_action = use_prev_action
        n_extra = 6 if use_prev_action else 3
        base = int(np.prod(env.observation_space.shape))
        self.observation_space = spaces.Box(-np.inf, np.inf,
                                            shape=(base + n_extra,),
                                            dtype=np.float32)
        self._prev = np.zeros(3)
        self._base_obs = None

    # ------------------------------------------------------------------ helpers
    def lqr_action(self, base_obs):
        """Normalised action that reproduces the nominal LQR exactly."""
        return np.clip((-self.K @ np.asarray(base_obs, float)[:6]) / self.scale,
                       -1.0, 1.0)

    def _obs(self, base_obs):
        tau_lqr = -self.K @ np.asarray(base_obs, float)[:6]
        parts = [np.asarray(base_obs, float), tau_lqr / self.scale]
        if self.use_prev_action:
            parts.append(self._prev)
        return np.concatenate(parts).astype(np.float32)

    # ------------------------------------------------------------------- gym api
    def reset(self, **kwargs):
        base, info = self.env.reset(**kwargs)
        self._base_obs = np.asarray(base, float)
        self._prev = np.zeros(3)
        info = dict(info)
        info["base_obs"] = self._base_obs.copy()
        return self._obs(self._base_obs), info

    def step(self, action):
        a = np.clip(np.asarray(action, float), -1.0, 1.0)
        base = self._base_obs if self._base_obs is not None else self.env._obs()
        combined = np.clip(self.lqr_action(base) + self.alpha * a, -1.0, 1.0)
        obs, r, term, trunc, info = self.env.step(combined)
        self._base_obs = np.asarray(obs, float)
        self._prev = a.copy()
        info = dict(info)
        info["base_obs"] = self._base_obs.copy()
        info["combined_action"] = combined.copy()
        return self._obs(self._base_obs), r, term, trunc, info
