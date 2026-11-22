"""Joint friction/effectiveness estimator (M3).

The existing estimator asserts  y = h * phi  with phi = -tau_cmd/tau_ref, i.e. it
attributes EVERY deviation of the wheel response to a multiplicative effectiveness
loss. Under Coulomb friction it therefore reports h -> 0 ("all wheels dead") although
the wheels are healthy, and the allocator's tau_des/h then saturates them.

The plant is (dynamics.py):
    J_w * d(omega_w)/dt = -h * tau_cmd + tau_f
    tau_f = -(b_visc * omega_w + c_coul * tanh(omega_w / 0.05))

which is LINEAR in two parameters per wheel:

    y = J_w * d(omega_w)/dt = [ -tau_cmd , +1 ] . [ h , tau_f ]

So h and tau_f are separable: a multiplicative loss scales with the command, whereas
friction is an additive offset. This module regresses both, per wheel, by RLS.

Diagnostic/estimator module only: nothing else is modified.
"""
from __future__ import annotations
import numpy as np


UNKNOWN, HEALTHY, DEGRADED = 0, 1, 2
STATE_NAME = {UNKNOWN: "UNKNOWN", HEALTHY: "HEALTHY", DEGRADED: "DEGRADED"}


class FrictionHealthEstimator:
    """Per-wheel RLS on theta = [h, tau_f], with an explicit health STATE.

    Thresholds, all derived rather than chosen to pass tests:

    N_MIN = 5          the model has 2 parameters per wheel; 5 accepted updates gives
                       redundancy beyond the parameter count. Below this the estimate
                       is initialisation, not information.
    SIGMA_H_MAX = 0.1  the RLS covariance P[0,0] gives sigma_h = sqrt(P[0,0]).
                       Requiring sigma_h <= 0.1 means effectiveness is known to +/-0.1,
                       i.e. 2x the 0.05 healthy tolerance below.
    H_TOL = 0.05       10x below the smallest fault of interest (h=0.5) and ~25x above
                       the healthy estimation error measured in C2-h (0.002), so both
                       margins are set by measured quantities.
    """

    # lam=1.0 (no forgetting) is required for the covariance to be a usable
    # confidence measure: with lam<1 the P/lam inflation dominates when the regressor
    # direction is nearly constant (a rank-1 estimation problem), so sigma_h grows
    # without bound even after thousands of updates and every wheel is UNKNOWN.
    # Measured: lam=0.995 -> sigma_h ~ 1e4 after 4500 updates. The parameters here are
    # constant, so no forgetting is needed; time-varying faults would require a
    # bounded-forgetting or sliding-window variant, which is NOT implemented.
    N_MIN = 5
    SIGMA_H_MAX = 0.1
    H_TOL = 0.05

    def __init__(self, rw_J=2.0e-4, control_period=0.2, n_rw=3,
                 lam=1.0, p0=1.0e3, tau_min=1.0e-5, h_init=1.0):
        self.rw_J = float(rw_J)
        self.Tc = float(control_period)
        self.n_rw = int(n_rw)
        self.lam = float(lam)
        self.p0 = float(p0)
        self.tau_min = float(tau_min)
        self.h_init = float(h_init)
        self.reset()

    def reset(self):
        self.theta = np.tile(np.array([self.h_init, 0.0]), (self.n_rw, 1))
        self.P = np.tile(np.eye(2) * self.p0, (self.n_rw, 1, 1))
        self.last_w = None
        self.n_upd = np.zeros(self.n_rw, dtype=int)

    def prime(self, omega_w_meas):
        self.last_w = np.asarray(omega_w_meas, float).copy()
        return self

    @property
    def h(self):
        return self.theta[:, 0].copy()

    @property
    def tau_f(self):
        return self.theta[:, 1].copy()

    @property
    def sigma_h(self):
        return np.sqrt(np.maximum(self.P[:, 0, 0], 0.0))

    def state(self):
        """Per-wheel health state from excitation count, confidence and estimate."""
        st = np.full(self.n_rw, UNKNOWN, dtype=int)
        for i in range(self.n_rw):
            # no excitation -> the estimate is initialisation, never evidence
            if self.n_upd[i] < self.N_MIN:
                continue
            if self.sigma_h[i] > self.SIGMA_H_MAX:
                continue
            if self.theta[i, 0] < 1.0 - self.H_TOL:
                st[i] = DEGRADED
            else:
                st[i] = HEALTHY
        return st

    def state_names(self):
        return [STATE_NAME[int(s)] for s in self.state()]

    def update(self, tau_cmd, omega_w_meas):
        tau = np.asarray(tau_cmd, float).reshape(self.n_rw)
        w = np.asarray(omega_w_meas, float).reshape(self.n_rw)
        if self.last_w is None:
            return self.prime(w)

        dw = w - self.last_w
        y = self.rw_J * dw / self.Tc          # [N*m] per wheel
        for i in range(self.n_rw):
            if abs(tau[i]) < self.tau_min:     # nothing to identify from
                continue
            phi = np.array([-tau[i], 1.0])
            Pp = self.P[i] / self.lam
            den = 1.0 + phi @ Pp @ phi
            K = Pp @ phi / den
            self.theta[i] = self.theta[i] + K * (y[i] - phi @ self.theta[i])
            self.P[i] = Pp - np.outer(K, phi @ Pp)
            # physical bounds: effectiveness in [0,1]
            self.theta[i, 0] = float(np.clip(self.theta[i, 0], 0.0, 1.5))
            self.n_upd[i] += 1
        self.last_w = w.copy()
        return self


def main():
    """Validation: does it separate friction from effectiveness loss?"""
    import sys, os
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, here)
    from satellite_adcs.config import load_config
    from satellite_adcs.environment.adcs_env import ADCSEnv
    from satellite_adcs.environment.residual_env import ResidualADCSEnv
    from simulate import make_ic_bias

    cases = [
        ("ideal",        [1.0, 1.0, 1.0], 0.0,  1.0, 0.0),
        ("coulomb_2e4",  [1.0, 1.0, 1.0], 2e-4, 1.0, -2e-4),
        ("rw1_50pct",    [0.5, 1.0, 1.0], 0.0,  0.5, 0.0),
        ("rw1_50+c2e4",  [0.5, 1.0, 1.0], 2e-4, 0.5, -2e-4),
    ]
    print("M3  joint (h, tau_f) estimator validation\n")
    ok_all = True
    for name, health, coulomb, h_true1, tf_true1 in cases:
        ov = {"actuators": {"reaction_wheels": {"friction_coulomb_Nm": coulomb}}}
        env = ResidualADCSEnv(ADCSEnv(fault_mode="none", episode_time=900.0,
                                      control_hz=5.0, seed=0, overrides=ov), alpha=0.2)
        env.unwrapped.dyn.set_rw_health(health)
        q, w, b = make_ic_bias(0)
        obs, _ = env.reset(seed=0, options={"q": q, "omega": w, "gyro_bias": b})
        d = env.unwrapped.dyn
        est = FrictionHealthEstimator(rw_J=float(d.rw_J),
                                      control_period=env.unwrapped.control_period,
                                      n_rw=3)
        est.prime(d.omega_w)
        done = False
        while not done:
            obs, r, t, tr, info = env.step(np.zeros(3))
            est.update(np.asarray(info.get("tau_cmd", np.zeros(3)), float), d.omega_w)
            done = t or tr
        h_hat, tf_hat = est.h, est.tau_f
        print(f"[{name}] truth: h1={h_true1:.2f} tau_f1={tf_true1:.2e}")
        print(f"   h_hat      = {np.round(h_hat,3)}")
        print(f"   tau_f_hat  = {np.round(tf_hat,8)}")
        e_mag = abs(h_hat[0] - h_true1)
        e_fr = abs(tf_hat[0] - tf_true1)
        good = (e_mag < 0.15) and (e_fr < 5e-5)
        ok_all &= good
        print(f"   errors: |dh|={e_mag:.3f}  |dtau_f|={e_fr:.2e}  -> {'OK' if good else 'FAIL'}\n")
    print("ALL OK" if ok_all else "SOME CASES FAIL")


if __name__ == "__main__":
    main()
