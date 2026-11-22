"""Rigid-body + orbit dynamics for the ADCS simulator.

State:  [q_BN(4), omega(3), omega_w(3), r_I(3), v_I(3)]
- q_BN: body attitude (inertial -> body), scalar-first quaternion
- omega: body rate relative to inertial, in body frame [rad/s]
- omega_w: reaction-wheel speeds [rad/s] (wheels along body axes)
- r_I, v_I: inertial position/velocity [m, m/s]

Model: Euler attitude dynamics with 3 reaction wheels + 3 magnetorquers,
gravity-gradient + optional disturbance torques, tilted-dipole Earth B field,
two-body Keplerian orbit propagation.
"""
from __future__ import annotations
import numpy as np

from .quaternion import (
    quat_mult, quat_normalize, quat_to_dcm, dcm_to_quat, random_quat,
)

MU0_4PI = 1e-7  # mu0/(4*pi) [T*m^3/(A*m^2)] - dipole constant


def skew(v):
    return np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])


class SpacecraftDynamics:
    def __init__(self, cfg: dict, rng: np.random.Generator):
        self.cfg = cfg
        self.rng = rng
        sat = cfg["satellite"]
        orb = cfg["orbit"]

        self.mass = sat["mass"]
        J = sat["inertia"]
        self.J = np.diag([J["Jxx"], J["Jyy"], J["Jzz"]])
        self.J_inv = np.linalg.inv(self.J)

        # reaction wheels (body-aligned axes)
        rw = cfg["actuators"]["reaction_wheels"]
        self.rw_axes = np.array(rw["axes"], dtype=float)
        self.rw_J = rw["inertia_kgm2"]
        self.rw_max_torque = rw["max_torque_Nm"]
        self.rw_max_speed = rw["max_speed_rad_s"]
        self.n_rw = rw["count"]
        # reaction-wheel health fault: tau_actual = health * tau_command (1.0 = healthy)
        self.rw_health = np.ones(self.n_rw)
        # D.3: a time-varying fault schedule, DEFAULT NONE. When it is set the plant
        # overwrites rw_health (and the lock mask) once per integrator step; when it is
        # None the code below is exactly what it was, so history stays bit-identical.
        self.wheel_faults = None
        self.rw_lock = np.zeros(self.n_rw, dtype=bool)
        self.locked_any = False

        # ---- MILESTONE B: actuator nonlinearities -------------------------
        # ALL DEFAULT TO ZERO, so the ideal actuator (and every historical
        # result) is bit-identical unless a config explicitly enables an effect.
        #   deadzone_Nm           breakaway: |tau| below this delivers nothing
        #   friction_viscous_Nms  bearing drag proportional to wheel speed
        #   friction_coulomb_Nm   speed-independent bearing drag at breakaway
        #   rate_limit_Nm_per_s   the drive cannot slew its torque instantly
        #   quant_step_Nm         DAC / current-loop resolution
        self.rw_deadzone = float(rw.get("deadzone_Nm", 0.0))
        self.rw_b_visc = float(rw.get("friction_viscous_Nms", 0.0))
        self.rw_c_coul = float(rw.get("friction_coulomb_Nm", 0.0))
        self.rw_rate_limit = float(rw.get("rate_limit_Nm_per_s", 0.0))
        self.rw_quant = float(rw.get("quant_step_Nm", 0.0))
        # Q-12: `initial_speed_rad_s` was documented in actuators.yaml but read by
        # nobody, so the wheels always started at rest. Honoured now; the default of
        # 0.0 keeps every historical result bit-identical.
        self.rw_init_speed = float(rw.get("initial_speed_rad_s", 0.0))
        self._tau_prev = np.zeros(self.n_rw)

        # magnetorquers
        mtq = cfg["actuators"]["magnetorquers"]
        self.mtq_axes = np.array(mtq["axes"], dtype=float)
        self.mtq_max_dipole = mtq["max_dipole_Am2"]

        # orbit
        self.mu = float(orb["mu_m3_s2"])
        self.Re = float(orb["Re_m"])
        self.a = float(self.Re + orb["altitude_km"] * 1e3)
        self.ecc = float(orb["eccentricity"])
        self.inc = np.radians(float(orb["inclination_deg"]))
        self.raan = np.radians(float(orb["raan_deg"]))
        self.argp = np.radians(float(orb["argp_deg"]))
        self.f0 = np.radians(float(orb["true_anomaly_deg"]))

        # magnetic dipole (tilted ~11.5 deg)
        self.mag_tilt = np.radians(11.5)
        self.m_e = 7.94e22  # Earth dipole moment [A*m^2]

        # disturbances flags
        dist = cfg["disturbances"]
        self.gravity_gradient = dist["gravity_gradient"]
        self.aero_on = dist["aerodynamic"]["enabled"]
        self.srp_on = dist["solar_radiation_pressure"]["enabled"]
        self.magres_on = dist["magnetic_residual"]["enabled"]

        self.reset()

    # ------------------------------------------------------------------ init
    def _init_orbit(self):
        # classical elements -> inertial r,v (a in m, angles in rad)
        a, e, inc, Om, om, f = self.a, self.ecc, self.inc, self.raan, self.argp, self.f0
        p = a * (1 - e * e)
        r_norm = p / (1 + e * np.cos(f))
        r_pf = np.array([r_norm * np.cos(f), r_norm * np.sin(f), 0.0])
        v_pf = np.sqrt(self.mu / p) * np.array([-np.sin(f), e + np.cos(f), 0.0])
        # perifocal -> inertial (R3(-Om) R1(-inc) R3(-om))
        cO, sO = np.cos(Om), np.sin(Om)
        ci, si = np.cos(inc), np.sin(inc)
        co, so = np.cos(om), np.sin(om)
        R3O = np.array([[cO, sO, 0], [-sO, cO, 0], [0, 0, 1]])
        R1i = np.array([[1, 0, 0], [0, ci, si], [0, -si, ci]])
        R3o = np.array([[co, so, 0], [-so, co, 0], [0, 0, 1]])
        C_PF_I = R3O.T @ R1i.T @ R3o.T  # perifocal -> inertial
        self.r = C_PF_I @ r_pf
        self.v = C_PF_I @ v_pf

    def reset(self, q=None, omega=None, omega_w=None):
        sat = self.cfg["satellite"]
        self.t = 0.0
        self._init_orbit()
        if q is None:
            q = random_quat(self.rng)
        if omega is None:
            wmax = np.radians(sat["initial"]["omega_max_deg_per_s"])
            omega = self.rng.uniform(-wmax, wmax, 3)
        if omega_w is None:
            omega_w = np.full(self.n_rw, self.rw_init_speed)
        self.q = quat_normalize(q)
        self.omega = np.asarray(omega, float)
        self.omega_w = np.asarray(omega_w, float)
        return self

    # ------------------------------------------------------------- helpers
    @property
    def C(self):
        """inertial -> body DCM."""
        return quat_to_dcm(self.q)

    @property
    def B_body(self):
        """Earth magnetic field in body frame [T] (tilted dipole)."""
        r_I = self.r
        rn = np.linalg.norm(r_I)
        rhat = r_I / rn
        # tilted dipole moment direction in inertial frame
        c, s = np.cos(self.mag_tilt), np.sin(self.mag_tilt)
        mhat = np.array([s, 0.0, c])
        B_I = MU0_4PI * self.m_e / rn**3 * (3 * (mhat @ rhat) * rhat - mhat)
        return self.C @ B_I

    def sun_inertial(self):
        """Inertial unit vector to the sun (fixed in M0; slowly drifting later)."""
        s = np.array([1.0, 0.0, 0.0])
        return s / np.linalg.norm(s)

    # ------------------------------------------------------ disturbance torques
    def disturbance_torque(self):
        tau = np.zeros(3)
        rn = np.linalg.norm(self.r)
        if self.gravity_gradient:
            rhat_b = self.C @ (self.r / rn)
            tau += 3.0 * self.mu / rn**3 * np.cross(rhat_b, self.J @ rhat_b)
        # (aero / SRP / residual magnetic are config-gated; add later if needed)
        return tau

    # ------------------------------------------------------------ derivatives
    def derivatives(self, tau_rw, m_mtq):
        """Return state derivative given wheel torque on body and MTQ dipole."""
        q = self.q
        w = self.omega
        J = self.J
        H_w = self.rw_J * self.omega_w  # wheel momentum (body axes)
        H = J @ w + H_w

        q_dot = 0.5 * quat_mult(q, np.array([0.0, w[0], w[1], w[2]]))

        tau_mtq = np.cross(m_mtq, self.B_body)
        # actuator fault: each wheel delivers only `health` of its commanded torque
        tau_rw_eff = np.asarray(tau_rw, dtype=float) * self.rw_health

        # Bearing friction is INTERNAL (wheel <-> body), so it must conserve total
        # momentum: the wheel loses tau_f and the body gains exactly -tau_f.
        # tanh gives a smooth Coulomb law; a hard sign() would chatter inside RK4.
        tau_f = -(self.rw_b_visc * self.omega_w
                  + self.rw_c_coul * np.tanh(self.omega_w / 0.05))

        tau = (-np.cross(w, H) + tau_rw_eff - tau_f + tau_mtq
               + self.disturbance_torque())
        if self.locked_any:
            # A jammed wheel transmits NOTHING to the structure: its command is absorbed
            # and its bearing torque is internal. Subtracting the wheel's own
            # contribution is exact and, with no locked wheel, this branch never runs.
            tau = tau - np.where(self.rw_lock, tau_rw_eff - tau_f, 0.0)
        w_dot = self.J_inv @ tau

        # wheel speed: motor applies -tau_rw (effective) plus friction to the wheel
        ow_dot = (-tau_rw_eff + tau_f) / self.rw_J
        if self.locked_any:
            ow_dot = np.where(self.rw_lock, 0.0, ow_dot)

        rn = np.linalg.norm(self.r)
        v_dot = -self.mu * self.r / rn**3

        return np.concatenate([q_dot, w_dot, ow_dot, self.v, v_dot])

    def _state(self):
        return np.concatenate([self.q, self.omega, self.omega_w, self.r, self.v])

    def _set_state(self, x):
        self.q = quat_normalize(x[0:4])
        self.omega = x[4:7]
        self.omega_w = x[7:10]
        self.r = x[10:13]
        self.v = x[13:16]

    def _rw_command_effective(self, tau_cmd, dt):
        """Apply the static and rate actuator effects to a commanded wheel torque.

        Kept out of derivatives(): RK4 calls that 4x per step with the same
        command, so a stateful rate limit there would be applied four times.
        """
        t = np.asarray(tau_cmd, float).copy()
        if self.rw_rate_limit > 0.0:
            dmax = self.rw_rate_limit * dt
            t = np.clip(t, self._tau_prev - dmax, self._tau_prev + dmax)
        if self.rw_deadzone > 0.0:
            t = np.where(np.abs(t) < self.rw_deadzone, 0.0, t)
        if self.rw_quant > 0.0:
            t = np.round(t / self.rw_quant) * self.rw_quant
        self._tau_prev = t.copy()
        return t

    def step(self, dt, tau_rw, m_mtq):
        """RK4 integrate dynamics by dt."""
        # D.3: refresh the scheduled fault state once per step (not per RK4 stage, or a
        # time-varying schedule would be applied four times inside one step).
        if self.wheel_faults is not None:
            self.rw_health = self.wheel_faults.health(self.t)
            self.rw_lock = self.wheel_faults.locked(self.t)
            self.locked_any = bool(self.rw_lock.any())
        tau_rw = np.asarray(tau_rw, float)
        tau_rw = self._rw_command_effective(tau_rw, dt)
        m_mtq = np.asarray(m_mtq, float)

        def f(x):
            self._set_state(x)
            return self.derivatives(tau_rw, m_mtq)

        x0 = self._state()
        k1 = f(x0)
        k2 = f(x0 + 0.5 * dt * k1)
        k3 = f(x0 + 0.5 * dt * k2)
        k4 = f(x0 + dt * k3)
        x1 = x0 + dt / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)
        self._set_state(x1)
        # clamp wheel speeds at saturation
        self.omega_w = np.clip(self.omega_w, -self.rw_max_speed, self.rw_max_speed)
        self.t += dt
        return self

    def saturate_rw(self, tau):
        """Clip wheel torque commands to per-wheel maximum."""
        return np.clip(tau, -self.rw_max_torque, self.rw_max_torque)

    def set_rw_health(self, health):
        """Set per-wheel health in [0,1] (fault: tau_actual = health * tau_command)."""
        self.rw_health = np.asarray(health, dtype=float)
        return self

    def set_wheel_faults(self, schedule):
        """Attach a D.3 time-varying fault schedule (None = static health, unchanged path).

        Ground truth in the plant only: controllers and estimators must never read it
        (D-03). Passing None restores the static `rw_health` behaviour exactly.
        """
        self.wheel_faults = schedule
        if schedule is None:
            self.rw_lock = np.zeros(self.n_rw, dtype=bool)
            self.locked_any = False
        return self
