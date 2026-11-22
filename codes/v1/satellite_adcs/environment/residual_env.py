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
                 use_prev_action=True, gate="none", slip_threshold=1.0e-5):
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
        # ---- D5: friction gate -------------------------------------------------
        # "none" reproduces the D4 behaviour exactly (enable always 1). "slip"
        # gates the residual on OBSERVED friction: a wheel in a stick-slip deadband
        # receives tau_cmd but produces less rotation than the command implies, so
        #   tau_achieved = J_w * d(omega_w)/dt,   slip = |tau_cmd - tau_achieved|
        # distinguishes "wheel is stuck" from "wheel is healthy". This is a
        # physics-based switch -- the same residual health_estimation.py regresses.
        self.gate = str(gate).lower()
        self.slip_threshold = float(slip_threshold)
        self._prev_om = None
        self._prev_tau_cmd = None
        self._gate_open = 1.0

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

    def slip(self):
        """Per-wheel |tau_cmd - tau_achieved| from the PREVIOUS step.

        Uses the plant's own wheel inertia, so no constant is guessed here.
        Returns None on the first step, when no wheel motion has been observed.
        """
        if self._prev_om is None or self._prev_tau_cmd is None:
            return None
        d = self.env.unwrapped.dyn
        om = np.asarray(d.omega_w, float)
        domega = (om - self._prev_om) / float(self.env.unwrapped.control_period)
        return np.abs(np.asarray(self._prev_tau_cmd, float) - d.rw_J * domega)

    def gate_open(self, slip):
        if self.gate != "slip" or slip is None:
            return 1.0
        return float(np.any(slip > self.slip_threshold))

    # ------------------------------------------------------------------- gym api
    def reset(self, **kwargs):
        base, info = self.env.reset(**kwargs)
        self._prev_om = None
        self._prev_tau_cmd = None
        self._gate_open = 1.0
        self._base_obs = np.asarray(base, float)
        self._prev = np.zeros(3)
        info = dict(info)
        info["base_obs"] = self._base_obs.copy()
        return self._obs(self._base_obs), info

    def step(self, action):
        a = np.clip(np.asarray(action, float), -1.0, 1.0)
        base = self._base_obs if self._base_obs is not None else self.env._obs()
        # the gate decision uses ONLY information available before this command
        enable = self.gate_open(self.slip())
        self._gate_open = enable
        combined = np.clip(self.lqr_action(base) + enable * self.alpha * a, -1.0, 1.0)
        obs, r, term, trunc, info = self.env.step(combined)
        self._base_obs = np.asarray(obs, float)
        self._prev = a.copy()
        info = dict(info)
        info["base_obs"] = self._base_obs.copy()
        info["combined_action"] = combined.copy()
        info["gate_open"] = self._gate_open
        info["slip"] = self.slip()
        # record what this command was, so the NEXT step can judge whether the wheel
        # actually responded to it
        self._prev_om = np.asarray(self.env.unwrapped.dyn.omega_w, float).copy()
        self._prev_tau_cmd = np.asarray(info.get("tau_cmd", np.zeros(3)), float).copy()
        return self._obs(self._base_obs), r, term, trunc, info
