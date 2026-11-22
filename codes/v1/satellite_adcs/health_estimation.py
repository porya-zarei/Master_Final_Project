"""Per-wheel reaction-wheel health estimation (C2-h).

Fault model (`dynamics.py:158,163`):

    J_w * Omega_dot_w = -h * tau_cmd          h in [0,1],  1 = healthy

There is **no friction and no viscous drag** in the plant, and the wheels are
independent, so over one control period T_c (zero-order hold on the command):

    J_w * dOmega_w / T_c  =  -h * tau_cmd        <- exactly linear in h

The estimator is therefore a **scalar recursive least squares per wheel** with a
forgetting factor (so it can track a changing health), plus guards that prevent
the two ways this naive estimator lies:

 1. **Excitation gate** — a wheel that is not commanded carries no information
    about h. Updating anyway lets noise random-walk the estimate.
 2. **Saturation guard** — wheel speed is hard-clamped at +-Omega_max *after*
    integration (`dynamics.py:197`). While clamped, dOmega = 0 even though
    tau_cmd != 0, so an ungated RLS drives h_hat -> 0 and reports a **false dead
    wheel** on a perfectly healthy one.
 3. **Plausibility gate** — |y| = h|tau_cmd| <= tau_max by construction; anything
    larger means a sensor glitch or an unmodelled clamp.

The estimator publishes its own ignorance: `age[i]` is the time since the last
accepted update for wheel i. A consumer must treat a large age as "unknown" and
**never** fall back to a truth value.

Provenance note (why this matters for the thesis): with the *current* allocator
(`controllers.py:35-39`) a degraded wheel is commanded as tau_des / h_true, so
tau_cmd is kept away from zero and h stays identifiable — but a wheel with
h_true = 0 is commanded **exactly zero**, so it is *unobservable by construction*.
That is demonstrated in `scripts/c2h_health_estimator.py`, not assumed here.
"""
from __future__ import annotations

import numpy as np


class WheelHealthEstimator:
    """Scalar RLS per reaction wheel, with excitation/saturation/plausibility guards.

    Parameters
    ----------
    rw_J : float
        Wheel spin inertia [kg m^2].
    control_period : float
        Control period T_c [s]; the command is held constant over this interval.
    n_rw : int
        Number of wheels.
    rw_max_torque : float
        Per-wheel torque limit [N m]; used by the plausibility gate.
    rw_max_speed : float
        Per-wheel speed limit [rad/s]; used by the saturation guard.
    lam : float
        Forgetting factor in (0, 1]. lam = 1 -> infinite memory (batch-like).
    p0 : float
        Initial covariance. Large = fast, noisy; small = slow, smooth.
    h_init : float
        Initial estimate. 1.0 = "assume healthy until evidence".
    tau_min : float
        Excitation gate: |tau_cmd| below this is treated as "no command".
    speed_frac : float
        Saturation guard threshold as a fraction of rw_max_speed.
    plaus_margin : float
        Plausibility gate: reject |y| > plaus_margin * rw_max_torque.
    """

    def __init__(self, rw_J: float = 2.0e-4, control_period: float = 0.2,
                 n_rw: int = 3, rw_max_torque: float = 0.010,
                 rw_max_speed: float = 628.3, lam: float = 0.98, p0: float = 1.0,
                 h_init: float = 1.0, tau_min: float = 1.0e-5,
                 speed_frac: float = 0.98, plaus_margin: float = 1.5,
                 tau_ref: float | None = None,
                 tacho_sigma: float = 0.0, tau_min_k: float = 0.0):
        self.rw_J = float(rw_J)
        self.Tc = float(control_period)
        self.n_rw = int(n_rw)
        self.rw_max_torque = float(rw_max_torque)
        self.rw_max_speed = float(rw_max_speed)
        self.lam = float(lam)
        self.p0 = float(p0)
        self.h_init = float(h_init)
        self.tau_min = float(tau_min)
        self.speed_frac = float(speed_frac)
        self.plaus_margin = float(plaus_margin)
        # Regressor normalisation. tau_cmd lives at ~1e-2 N.m, so an unnormalised
        # regressor makes P0 = 1 a hopelessly small covariance: convergence would
        # need ~1/phi^2 = 4e4 steps. Scaling y and phi by tau_ref makes both O(1)
        # (and h invariant, since h = y/phi is unchanged).
        self.tau_ref = float(tau_ref if tau_ref is not None else rw_max_torque)
        # Noise-matched excitation gate. An absolute tau_min cannot know whether an
        # update is informative: the torque-equivalent measurement noise is
        # J_w*sqrt(2)*sigma_omega/T_c (differencing two tachometer samples), so the
        # gate must scale with it. With tau_min_k > 0 the effective threshold is
        # max(tau_min, tau_min_k * that noise level).
        self.tacho_sigma = float(tacho_sigma)
        self.tau_min_k = float(tau_min_k)
        self.tau_min_eff = max(self.tau_min,
                              self.tau_min_k * self.rw_J * np.sqrt(2.0)
                              * self.tacho_sigma / self.Tc)
        self.reset()

    # ------------------------------------------------------------------ state
    def reset(self):
        self.h = np.full(self.n_rw, self.h_init, dtype=float)
        self.P = np.full(self.n_rw, self.p0, dtype=float)
        self.age = np.zeros(self.n_rw, dtype=float)
        self.last_w = None
        self.k = 0
        self.n_upd = np.zeros(self.n_rw, dtype=int)
        self.n_skip_excite = np.zeros(self.n_rw, dtype=int)
        self.n_skip_sat = np.zeros(self.n_rw, dtype=int)
        self.n_skip_plaus = np.zeros(self.n_rw, dtype=int)
        return self

    def prime(self, omega_w_meas):
        """Seed the speed history without performing an update."""
        self.last_w = np.asarray(omega_w_meas, dtype=float).copy()
        return self

    # ----------------------------------------------------------------- update
    def update(self, tau_cmd, omega_w_meas, guards: bool = True):
        """One control-period update.

        Parameters
        ----------
        tau_cmd : array (n_rw,)
            The commanded wheel torque actually issued (post-allocation clip).
        omega_w_meas : array (n_rw,)
            Measured wheel speeds.
        guards : bool
            Set False to reproduce the *unguarded* estimator used to demonstrate
            the saturation / excitation failure modes.

        Returns
        -------
        (h, P, age) : tuple of arrays
        """
        tau = np.asarray(tau_cmd, dtype=float).reshape(self.n_rw)
        w = np.asarray(omega_w_meas, dtype=float).reshape(self.n_rw)
        if self.last_w is None:
            self.prime(w)
            return self.h.copy(), self.P.copy(), self.age.copy()

        dw = w - self.last_w
        # normalised by tau_ref -> both y and phi are O(1); the identified h is
        # unchanged because h = y / phi.
        y = (self.rw_J * dw / self.Tc) / self.tau_ref
        phi = -tau / self.tau_ref                 # regressor; y = h * phi

        for i in range(self.n_rw):
            skip = False
            if guards and abs(tau[i]) < self.tau_min_eff:
                self.n_skip_excite[i] += 1
                skip = True
            if guards and abs(w[i]) >= self.speed_frac * self.rw_max_speed:
                self.n_skip_sat[i] += 1
                skip = True
            if guards and abs(y[i]) > self.plaus_margin:
                self.n_skip_plaus[i] += 1
                skip = True

            if skip:
                self.age[i] += self.Tc
                continue

            Pp = self.P[i] / self.lam
            denom = 1.0 + Pp * phi[i] * phi[i]
            K = Pp * phi[i] / denom
            self.h[i] = float(np.clip(self.h[i] + K * (y[i] - self.h[i] * phi[i]),
                                      0.0, 1.0))
            self.P[i] = Pp / denom
            self.age[i] = 0.0
            self.n_upd[i] += 1

        self.last_w = w.copy()
        self.k += 1
        return self.h.copy(), self.P.copy(), self.age.copy()

    # ---------------------------------------------------------------- helpers
    def diagnostics(self):
        return {
            "n_updates": self.n_upd.tolist(),
            "skip_excitation": self.n_skip_excite.tolist(),
            "skip_saturation": self.n_skip_sat.tolist(),
            "skip_plausibility": self.n_skip_plaus.tolist(),
            "h_final": self.h.tolist(),
            "P_final": self.P.tolist(),
        }


class Tachometer:
    """Idealised / noisy / quantised wheel-speed sensor.

    The plant has **no wheel-speed sensor at all** (`sensors.py` measures gyro,
    magnetometer, sun sensor, star tracker, GPS). `ADCSEnv._obs()` reads
    `dyn.omega_w` straight from the state, so both the policy and this estimator
    currently see a perfect tachometer. Noise and quantisation are therefore a
    declared *sensitivity case*, not a plant feature.
    """

    def __init__(self, noise_std: float = 0.0, quant_step: float = 0.0, rng=None):
        self.noise_std = float(noise_std)
        self.quant_step = float(quant_step)
        self.rng = rng if rng is not None else np.random.default_rng(0)

    def measure(self, omega_true):
        w = np.asarray(omega_true, dtype=float)
        if self.noise_std > 0.0:
            w = w + self.rng.normal(0.0, self.noise_std, w.shape)
        if self.quant_step > 0.0:
            w = np.round(w / self.quant_step) * self.quant_step
        return w
