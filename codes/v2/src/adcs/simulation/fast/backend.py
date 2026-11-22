"""Fast deterministic RK4 nonlinear spacecraft simulator implementing SimulatorBackend."""

from __future__ import annotations

import numpy as np

from adcs.actuators.models import (
    ActuatorFaultState,
    MagnetorquerBank,
    MTQFaultParams,
    ReactionWheelBank,
    RWFaultParams,
)
from adcs.dynamics.disturbances import (
    gravity_gradient_torque_body,
    residual_magnetic_dipole_torque_body,
)
from adcs.dynamics.magnetic_field import (
    GeomagneticFieldModel,
    load_shc_coefficients,
)
from adcs.dynamics.orbit import KeplerianOrbit
from adcs.interfaces.types import (
    ActuatorStatus,
    FloatArray,
    PlantStepOutput,
    SpacecraftTruthState,
)
from adcs.utils.config import SpacecraftConfig
from adcs.utils.quaternion import quat_derivative, quat_normalize


class FastSimulatorBackend:
    """Deterministic RK4 rigid-body + RW + MTQ + orbit + environment spacecraft simulator.

    State vector integrated by RK4 over each substep:
    - q_ib (4): scalar-first body-to-inertial quaternion
    - omega_b (3): body angular velocity wrt inertial, expressed in body frame (rad/s)
    - h_w (N_rw): wheel rotor spin angular momentum about each wheel axis (N*m*s)
    - tau_rw_state (N_rw): first-order RW actuator torque lag state (N*m)
    - m_mtq_state (N_mtq): first-order MTQ actuator dipole lag state (A*m^2)
    """

    def __init__(
        self,
        config: SpacecraftConfig,
        *,
        inertia_override_kg_m2: FloatArray | None = None,
        residual_dipole_override_am2: FloatArray | None = None,
        rw_time_constant_override_s: float | None = None,
        mtq_time_constant_override_s: float | None = None,
        gravity_gradient_enabled: bool | None = None,
        gmst_initial_rad: float = 0.0,
    ) -> None:
        self.config = config
        self.inertia = (
            config.inertia_matrix_kg_m2.copy()
            if inertia_override_kg_m2 is None
            else np.asarray(inertia_override_kg_m2, dtype=np.float64).copy()
        )
        if self.inertia.shape != (3, 3) or not np.all(np.isfinite(self.inertia)):
            raise ValueError("inertia_override_kg_m2 must be a finite 3x3 matrix")
        self.inertia_inv = np.linalg.inv(self.inertia)

        self.residual_dipole = (
            config.disturbances.residual_dipole_body_am2.copy()
            if residual_dipole_override_am2 is None
            else np.asarray(residual_dipole_override_am2, dtype=np.float64).copy()
        )
        self.gg_enabled = (
            config.disturbances.gravity_gradient_enabled
            if gravity_gradient_enabled is None
            else bool(gravity_gradient_enabled)
        )
        self.rmd_enabled = config.disturbances.residual_magnetic_dipole_enabled

        self.orbit = KeplerianOrbit(config.orbit)
        coeffs = (
            load_shc_coefficients(config.magnetic_field.coefficient_file)
            if config.magnetic_field.coefficient_file
            else None
        )
        self.mag_model = GeomagneticFieldModel(
            coefficients=coeffs,
            gmst_initial_rad=gmst_initial_rad,
        )

        self.rw_bank = ReactionWheelBank(config.reaction_wheels)
        if rw_time_constant_override_s is not None:
            self.rw_bank.time_constant = float(rw_time_constant_override_s)
        self.mtq_bank = MagnetorquerBank(config.magnetorquers)
        if mtq_time_constant_override_s is not None:
            self.mtq_bank.time_constant = float(mtq_time_constant_override_s)

        self.faults = ActuatorFaultState(
            rw=RWFaultParams.nominal(config.reaction_wheels),
            mtq=MTQFaultParams.nominal(config.magnetorquers),
        )

        self._time_s = 0.0
        self._true_anomaly_deg_init = config.orbit.true_anomaly_deg_initial
        self._q_ib = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
        self._omega_b = np.zeros(3, dtype=np.float64)
        self._h_w = np.zeros(self.rw_bank.n, dtype=np.float64)
        self._tau_rw_state = np.zeros(self.rw_bank.n, dtype=np.float64)
        self._m_mtq_state = np.zeros(self.mtq_bank.m, dtype=np.float64)
        self._last_truth: SpacecraftTruthState | None = None
        self.reset()

    @property
    def backend_name(self) -> str:
        return "fast_rk4"

    @property
    def backend_version(self) -> str:
        return "0.1.0"

    def set_fault_state(self, faults: ActuatorFaultState) -> None:
        """Update active actuator fault parameters for subsequent simulation steps."""
        self.faults = faults

    def reset(
        self,
        *,
        q_ib_init: FloatArray | None = None,
        omega_body_init: FloatArray | None = None,
        wheel_momentum_init: FloatArray | None = None,
        true_anomaly_deg_init: float | None = None,
        seed: int | None = None,
    ) -> SpacecraftTruthState:
        del seed  # Deterministic plant: no hidden randomness
        self._time_s = 0.0
        self._true_anomaly_deg_init = (
            self.config.orbit.true_anomaly_deg_initial
            if true_anomaly_deg_init is None
            else float(true_anomaly_deg_init)
        )
        self._q_ib = (
            np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
            if q_ib_init is None
            else quat_normalize(np.asarray(q_ib_init, dtype=np.float64))
        )
        self._omega_b = (
            np.zeros(3, dtype=np.float64)
            if omega_body_init is None
            else np.asarray(omega_body_init, dtype=np.float64).copy()
        )
        if self._omega_b.shape != (3,) or not np.all(np.isfinite(self._omega_b)):
            raise ValueError("omega_body_init must be a finite 3-vector")

        self._h_w = (
            np.zeros(self.rw_bank.n, dtype=np.float64)
            if wheel_momentum_init is None
            else np.asarray(wheel_momentum_init, dtype=np.float64).copy()
        )
        if self._h_w.shape != (self.rw_bank.n,) or not np.all(np.isfinite(self._h_w)):
            raise ValueError(f"wheel_momentum_init must be a finite {self.rw_bank.n}-vector")
        self._h_w = np.clip(self._h_w, -self.rw_bank.h_limit, self.rw_bank.h_limit)

        self._tau_rw_state = np.zeros(self.rw_bank.n, dtype=np.float64)
        self._m_mtq_state = np.zeros(self.mtq_bank.m, dtype=np.float64)
        self.rw_bank.reset()
        self.mtq_bank.reset()
        self.faults = ActuatorFaultState(
            rw=RWFaultParams.nominal(self.config.reaction_wheels),
            mtq=MTQFaultParams.nominal(self.config.magnetorquers),
        )

        self._last_truth = self._build_truth(
            rw_tau_achieved=np.zeros(self.rw_bank.n, dtype=np.float64),
            mtq_dipole_achieved=np.zeros(self.mtq_bank.m, dtype=np.float64),
            rw_tau_sat=(False,) * self.rw_bank.n,
            rw_h_sat=tuple(
                bool(abs(float(h)) >= self.rw_bank.h_limit - 1e-12) for h in self._h_w
            ),
            mtq_sat=(False,) * self.mtq_bank.m,
        )
        return self._last_truth

    def _compute_disturbances(
        self,
        r_eci: FloatArray,
        q_ib: FloatArray,
        b_body_t: FloatArray,
    ) -> FloatArray:
        tau_dist = np.zeros(3, dtype=np.float64)
        if self.gg_enabled:
            tau_dist = tau_dist + gravity_gradient_torque_body(
                r_eci, q_ib, self.inertia, self.orbit.mu
            )
        if self.rmd_enabled and np.any(self.residual_dipole != 0.0):
            tau_dist = tau_dist + residual_magnetic_dipole_torque_body(
                self.residual_dipole, b_body_t
            )
        if np.any(self.faults.extra_disturbance_body_nm != 0.0):
            tau_dist = tau_dist + self.faults.extra_disturbance_body_nm
        return tau_dist

    def _build_truth(
        self,
        *,
        rw_tau_achieved: FloatArray,
        mtq_dipole_achieved: FloatArray,
        rw_tau_sat: tuple[bool, ...],
        rw_h_sat: tuple[bool, ...],
        mtq_sat: tuple[bool, ...],
    ) -> SpacecraftTruthState:
        orb = self.orbit.state_at(self._time_s, self._true_anomaly_deg_init)
        b_body = self.mag_model.field_body_t(orb.position_eci_m, self._q_ib, self._time_s)
        tau_mtq = self.mtq_bank.body_torque(mtq_dipole_achieved, b_body)
        tau_dist = self._compute_disturbances(orb.position_eci_m, self._q_ib, b_body)
        status = ActuatorStatus(
            rw_torque_saturated=rw_tau_sat,
            rw_momentum_saturated=rw_h_sat,
            mtq_dipole_saturated=mtq_sat,
            rw_locked=tuple(self.faults.rw.locked),
            notes={"magnetic_field_fidelity": self.mag_model.model_fidelity},
        )
        truth = SpacecraftTruthState(
            time_s=self._time_s,
            position_eci_m=orb.position_eci_m,
            velocity_eci_m_s=orb.velocity_eci_m_s,
            q_ib=self._q_ib.copy(),
            omega_body_rad_s=self._omega_b.copy(),
            wheel_momentum_nms=self._h_w.copy(),
            wheel_speed_rad_s=self._h_w / self.rw_bank.rotor_inertia,
            rw_torque_achieved_nm=rw_tau_achieved.copy(),
            mtq_dipole_achieved_am2=mtq_dipole_achieved.copy(),
            mtq_torque_achieved_nm=tau_mtq,
            b_field_body_t=b_body,
            disturbance_torque_body_nm=tau_dist,
            actuator_status=status,
        )
        truth.validate()
        return truth

    def _rhs(
        self,
        r_eci: FloatArray,
        b_eci: FloatArray,
        q: FloatArray,
        omega: FloatArray,
        h_w: FloatArray,
        tau_rw_st: FloatArray,
        m_mtq_st: FloatArray,
        rw_cmd_delayed: FloatArray,
        mtq_target: FloatArray,
    ) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray, FloatArray]:
        qn = quat_normalize(q)
        # Fast inline R_BI = R_IB^T @ b_eci
        w, x, y, z = float(qn[0]), float(qn[1]), float(qn[2]), float(qn[3])
        r00 = 1.0 - 2.0 * (y * y + z * z)
        r01 = 2.0 * (x * y - w * z)
        r02 = 2.0 * (x * z + w * y)
        r10 = 2.0 * (x * y + w * z)
        r11 = 1.0 - 2.0 * (x * x + z * z)
        r12 = 2.0 * (y * z - w * x)
        r20 = 2.0 * (x * z - w * y)
        r21 = 2.0 * (y * z + w * x)
        r22 = 1.0 - 2.0 * (x * x + y * y)
        bx_i, by_i, bz_i = float(b_eci[0]), float(b_eci[1]), float(b_eci[2])
        b_body = np.array(
            [
                r00 * bx_i + r10 * by_i + r20 * bz_i,
                r01 * bx_i + r11 * by_i + r21 * bz_i,
                r02 * bx_i + r12 * by_i + r22 * bz_i,
            ],
            dtype=np.float64,
        )

        rw_target, _ = self.rw_bank.compute_motor_target(rw_cmd_delayed, self.faults.rw)
        if self.rw_bank.time_constant > 1e-9:
            dtau_rw = (rw_target - tau_rw_st) / self.rw_bank.time_constant
            tau_for_wall = tau_rw_st
        else:
            dtau_rw = np.zeros_like(tau_rw_st)
            tau_for_wall = rw_target

        tau_rw_ach, _ = self.rw_bank.apply_bearing_friction_and_wall(
            tau_for_wall, h_w, self.faults.rw
        )

        if self.mtq_bank.time_constant > 1e-9:
            dm_mtq = (mtq_target - m_mtq_st) / self.mtq_bank.time_constant
            m_ach = m_mtq_st
        else:
            dm_mtq = np.zeros_like(m_mtq_st)
            m_ach = mtq_target

        tau_rw_body = self.rw_bank.body_torque(tau_rw_ach)
        tau_mtq_body = self.mtq_bank.body_torque(m_ach, b_body)
        tau_dist = self._compute_disturbances(r_eci, qn, b_body)

        # Rigid-body + wheel Euler equation:
        # J * d(omega)/dt = tau_rw_body + tau_mtq_body + tau_dist - omega x (J*omega + A_rw*h_w)
        h_total_body = self.inertia @ omega + self.rw_bank.axis_matrix @ h_w
        gyroscopic = np.cross(omega, h_total_body)
        domega = self.inertia_inv @ (tau_rw_body + tau_mtq_body + tau_dist - gyroscopic)
        dq = quat_derivative(qn, omega)
        dh_w = -tau_rw_ach
        return dq, domega, dh_w, dtau_rw, dm_mtq

    def _orbit_and_b_eci(self, t: float) -> tuple[FloatArray, FloatArray]:
        orb = self.orbit.state_at(t, self._true_anomaly_deg_init)
        b_eci = self.mag_model.field_eci_t(orb.position_eci_m, t)
        return orb.position_eci_m, b_eci

    def step(
        self,
        rw_torque_cmd_nm: FloatArray,
        mtq_dipole_cmd_am2: FloatArray,
        dt_s: float | None = None,
    ) -> PlantStepOutput:
        rw_cmd = np.asarray(rw_torque_cmd_nm, dtype=np.float64)
        mtq_cmd = np.asarray(mtq_dipole_cmd_am2, dtype=np.float64)
        if rw_cmd.shape != (self.rw_bank.n,) or not np.all(np.isfinite(rw_cmd)):
            raise ValueError(
                f"rw_torque_cmd_nm must be a finite ({self.rw_bank.n},) array, got {rw_cmd!r}"
            )
        if mtq_cmd.shape != (self.mtq_bank.m,) or not np.all(np.isfinite(mtq_cmd)):
            raise ValueError(
                f"mtq_dipole_cmd_am2 must be a finite ({self.mtq_bank.m},) array, got {mtq_cmd!r}"
            )

        period = self.config.simulation.control_period_s if dt_s is None else float(dt_s)
        if not np.isfinite(period) or period <= 0.0:
            raise ValueError(f"dt_s must be finite positive, got {period}")

        h_step = self.config.simulation.integration_step_s
        n_sub = max(1, int(round(period / h_step)))
        dt = period / n_sub

        rw_cmd_delayed = self.rw_bank.apply_command_delay(rw_cmd, self.faults.rw)
        mtq_cmd_delayed = self.mtq_bank.apply_command_delay(mtq_cmd, self.faults.mtq)
        mtq_target, mtq_sat = self.mtq_bank.compute_effective_dipole(
            mtq_cmd_delayed, self.faults.mtq
        )

        # If instantaneous actuators (tau_c == 0), sync states directly
        if self.mtq_bank.time_constant <= 1e-9:
            self._m_mtq_state = mtq_target.copy()

        max_quat_norm_err = 0.0
        any_rw_tau_sat = [False] * self.rw_bank.n
        any_rw_h_sat = [False] * self.rw_bank.n

        # Evaluate slow-varying ECI orbit position and geomagnetic vector at step endpoints
        # and linearly interpolate across substeps (error < 1e-8 over 0.2s vs 5676s orbit period).
        t_init = self._time_s
        r_step0, b_step0 = self._orbit_and_b_eci(t_init)
        r_step1, b_step1 = self._orbit_and_b_eci(t_init + period)
        dr_step = r_step1 - r_step0
        db_step = b_step1 - b_step0
        inv_nsub = 1.0 / n_sub

        for sub_idx in range(n_sub):
            t0 = t_init + sub_idx * dt
            q0 = self._q_ib
            w0 = self._omega_b
            h0 = self._h_w
            tr0 = self._tau_rw_state
            mm0 = self._m_mtq_state

            f0 = sub_idx * inv_nsub
            fm = (sub_idx + 0.5) * inv_nsub
            f1 = (sub_idx + 1.0) * inv_nsub
            r_start = r_step0 + f0 * dr_step
            b_start = b_step0 + f0 * db_step
            r_mid = r_step0 + fm * dr_step
            b_mid = b_step0 + fm * db_step
            r_end = r_step0 + f1 * dr_step
            b_end = b_step0 + f1 * db_step

            k1 = self._rhs(r_start, b_start, q0, w0, h0, tr0, mm0, rw_cmd_delayed, mtq_target)
            k2 = self._rhs(
                r_mid,
                b_mid,
                q0 + 0.5 * dt * k1[0],
                w0 + 0.5 * dt * k1[1],
                h0 + 0.5 * dt * k1[2],
                tr0 + 0.5 * dt * k1[3],
                mm0 + 0.5 * dt * k1[4],
                rw_cmd_delayed,
                mtq_target,
            )
            k3 = self._rhs(
                r_mid,
                b_mid,
                q0 + 0.5 * dt * k2[0],
                w0 + 0.5 * dt * k2[1],
                h0 + 0.5 * dt * k2[2],
                tr0 + 0.5 * dt * k2[3],
                mm0 + 0.5 * dt * k2[4],
                rw_cmd_delayed,
                mtq_target,
            )
            k4 = self._rhs(
                r_end,
                b_end,
                q0 + dt * k3[0],
                w0 + dt * k3[1],
                h0 + dt * k3[2],
                tr0 + dt * k3[3],
                mm0 + dt * k3[4],
                rw_cmd_delayed,
                mtq_target,
            )

            q_next = q0 + (dt / 6.0) * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0])
            max_quat_norm_err = max(max_quat_norm_err, abs(float(np.linalg.norm(q_next)) - 1.0))
            self._q_ib = quat_normalize(q_next)
            self._omega_b = w0 + (dt / 6.0) * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1])
            h_next = h0 + (dt / 6.0) * (k1[2] + 2.0 * k2[2] + 2.0 * k3[2] + k4[2])
            self._h_w = np.clip(h_next, -self.rw_bank.h_limit, self.rw_bank.h_limit)

            if self.rw_bank.time_constant > 1e-9:
                self._tau_rw_state = tr0 + (dt / 6.0) * (
                    k1[3] + 2.0 * k2[3] + 2.0 * k3[3] + k4[3]
                )
            else:
                rw_t, _ = self.rw_bank.compute_motor_target(rw_cmd_delayed, self.faults.rw)
                self._tau_rw_state = rw_t

            if self.mtq_bank.time_constant > 1e-9:
                self._m_mtq_state = mm0 + (dt / 6.0) * (
                    k1[4] + 2.0 * k2[4] + 2.0 * k3[4] + k4[4]
                )
            else:
                self._m_mtq_state = mtq_target.copy()

            self._time_s = t0 + dt

            _, ts = self.rw_bank.compute_motor_target(rw_cmd_delayed, self.faults.rw)
            _, hs = self.rw_bank.apply_bearing_friction_and_wall(
                self._tau_rw_state, self._h_w, self.faults.rw
            )
            for i in range(self.rw_bank.n):
                any_rw_tau_sat[i] = any_rw_tau_sat[i] or ts[i]
                any_rw_h_sat[i] = any_rw_h_sat[i] or hs[i]

        rw_tau_achieved, _ = self.rw_bank.apply_bearing_friction_and_wall(
            self._tau_rw_state, self._h_w, self.faults.rw
        )
        self._last_truth = self._build_truth(
            rw_tau_achieved=rw_tau_achieved,
            mtq_dipole_achieved=self._m_mtq_state,
            rw_tau_sat=tuple(any_rw_tau_sat),
            rw_h_sat=tuple(any_rw_h_sat),
            mtq_sat=mtq_sat,
        )
        return PlantStepOutput(
            truth=self._last_truth,
            info={"max_substep_quat_norm_drift": max_quat_norm_err, "n_substeps": n_sub},
        )

    def get_truth_state(self) -> SpacecraftTruthState:
        assert self._last_truth is not None
        return self._last_truth
