"""Basilisk truth/validation simulator adapter implementing SimulatorBackend.

All Basilisk-specific imports and message/MRP/task wiring are isolated strictly inside
this module. Controllers, estimators, and RL code never import Basilisk.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from typing import Any

import numpy as np

from adcs.interfaces.types import (
    ActuatorStatus,
    FloatArray,
    PlantStepOutput,
    SpacecraftTruthState,
)
from adcs.utils.config import SpacecraftConfig
from adcs.utils.quaternion import (
    quat_canonicalize,
    quat_normalize,
    quat_rotate_vec_inv,
)


class BasiliskUnavailableError(RuntimeError):
    """Raised when Basilisk execution is requested in an environment without Basilisk."""


def is_basilisk_available() -> bool:
    """Return True iff the `Basilisk` Python package is importable."""
    return importlib.util.find_spec("Basilisk") is not None


def quat_ib_to_mrp_bn(q_ib: FloatArray) -> FloatArray:
    """Convert scalar-first Hamilton q_IB (B -> I) to Basilisk MRP sigma_BN (Schaub & Junkins).

    In Schaub & Junkins / Basilisk, [BN] = I + (8 [s]^2 - 4(1 - s^2)[s]) / (1 + s^2)^2 maps
    N -> B (equals R_BI = R_IB^T) with sigma_BN = +e_hat * tan(theta / 4) = q_IB[1:] / (1 + q_IB[0])
    when q_IB is canonicalized to q_IB[0] >= 0.
    """
    q_c = quat_canonicalize(quat_normalize(q_ib))
    return q_c[1:] / (1.0 + float(q_c[0]))


def mrp_bn_to_quat_ib(sigma_bn: FloatArray) -> FloatArray:
    """Convert Basilisk MRP sigma_BN (Schaub & Junkins) to canonical scalar-first q_IB (B -> I)."""
    s = np.asarray(sigma_bn, dtype=np.float64)
    if s.shape != (3,) or not np.all(np.isfinite(s)):
        raise ValueError(f"MRP sigma_bn must be a finite 3-vector, got {s!r}")
    s2 = float(np.dot(s, s))
    denom = 1.0 + s2
    q_ib = np.array([(1.0 - s2) / denom, *(2.0 * s / denom)], dtype=np.float64)
    return quat_canonicalize(q_ib)


def mrp_bn_to_dcm_bn(sigma_bn: FloatArray) -> FloatArray:
    """Exact Basilisk MRP -> [BN] DCM formula for independent mathematical cross-checks."""
    s = np.asarray(sigma_bn, dtype=np.float64)
    s2 = float(np.dot(s, s))
    s_tilde = np.array(
        [[0.0, -s[2], s[1]], [s[2], 0.0, -s[0]], [-s[1], s[0], 0.0]],
        dtype=np.float64,
    )
    denom = (1.0 + s2) ** 2
    return (
        np.eye(3, dtype=np.float64)
        + (8.0 * (s_tilde @ s_tilde) - 4.0 * (1.0 - s2) * s_tilde) / denom
    )


@dataclass(frozen=True)
class BasiliskPlantWiringSpec:
    """Serializable specification of how SpacecraftConfig maps to Basilisk modules."""

    integration_step_ns: int
    control_period_ns: int
    mass_kg: float
    inertia_flat_kg_m2: tuple[float, ...]
    rw_axes_body: tuple[tuple[float, float, float], ...]
    rw_max_torque_nm: float
    rw_max_momentum_nms: float
    rw_rotor_inertia_kg_m2: float
    mtq_axes_body: tuple[tuple[float, float, float], ...]
    mtq_max_dipole_am2: float
    gravity_gradient_enabled: bool


def build_basilisk_wiring_spec(cfg: SpacecraftConfig) -> BasiliskPlantWiringSpec:
    """Translate SpacecraftConfig into explicit Basilisk module parameters."""
    sec_to_ns = 1_000_000_000
    rw_axes = tuple(
        (
            float(cfg.reaction_wheels.axis_matrix_body[0, i]),
            float(cfg.reaction_wheels.axis_matrix_body[1, i]),
            float(cfg.reaction_wheels.axis_matrix_body[2, i]),
        )
        for i in range(cfg.reaction_wheels.count)
    )
    mtq_axes = tuple(
        (
            float(cfg.magnetorquers.axis_matrix_body[0, i]),
            float(cfg.magnetorquers.axis_matrix_body[1, i]),
            float(cfg.magnetorquers.axis_matrix_body[2, i]),
        )
        for i in range(cfg.magnetorquers.count)
    )
    return BasiliskPlantWiringSpec(
        integration_step_ns=int(round(cfg.simulation.integration_step_s * sec_to_ns)),
        control_period_ns=int(round(cfg.simulation.control_period_s * sec_to_ns)),
        mass_kg=cfg.mass_kg,
        inertia_flat_kg_m2=tuple(float(x) for x in cfg.inertia_matrix_kg_m2.reshape(9)),
        rw_axes_body=rw_axes,
        rw_max_torque_nm=cfg.reaction_wheels.torque_limit_nominal_nm,
        rw_max_momentum_nms=cfg.reaction_wheels.effective_momentum_limit_nms,
        rw_rotor_inertia_kg_m2=cfg.reaction_wheels.rotor_inertia_kg_m2,
        mtq_axes_body=mtq_axes,
        mtq_max_dipole_am2=cfg.magnetorquers.dipole_limit_per_axis_am2,
        gravity_gradient_enabled=cfg.disturbances.gravity_gradient_enabled,
    )


class BasiliskBackend:
    """SimulatorBackend adapter wrapping AVS Lab's Basilisk astrodynamics framework.

    If Basilisk is not installed, instantiation fails visibly with `BasiliskUnavailableError`
    unless a test runtime injection (`_bsk_modules`) is provided for contract verification.
    """

    def __init__(
        self,
        config: SpacecraftConfig,
        *,
        _bsk_modules: dict[str, Any] | None = None,
        vizard_file: str | None = None,
        vizard_live: bool = False,
    ) -> None:
        self.config = config
        self.wiring_spec = build_basilisk_wiring_spec(config)
        self._vizard_file = vizard_file
        self._vizard_live = bool(vizard_live)
        if _bsk_modules is not None:
            self._bsk = _bsk_modules
            self._version = str(_bsk_modules.get("__version__", "mock"))
        else:
            if not is_basilisk_available():
                raise BasiliskUnavailableError(
                    "Basilisk is not installed in the active Python environment. "
                    "Install Basilisk per platform build instructions to enable live "
                    "Basilisk truth/cross-validation runs."
                )
            self._bsk = self._import_basilisk()
            self._version = str(getattr(self._bsk["Basilisk"], "__version__", "installed"))

        self._sim: Any = None
        self._sc_object: Any = None
        self._rw_eff: Any = None
        self._mtb_eff: Any = None
        self._ext_ft: Any = None
        self._rw_cmd_msg: Any = None
        self._mtq_cmd_msg: Any = None
        self._mag_module: Any = None
        self._viz: Any = None
        self._ext_disturbance_body_nm = np.zeros(3, dtype=np.float64)
        self._rw_effectiveness = np.ones(config.reaction_wheels.count, dtype=np.float64)
        self._rw_bias_nm = np.zeros(config.reaction_wheels.count, dtype=np.float64)
        self._time_s = 0.0
        self._last_truth: SpacecraftTruthState | None = None

    @staticmethod
    def _import_basilisk() -> dict[str, Any]:
        import Basilisk  # type: ignore[import-not-found]
        from Basilisk.architecture import messaging  # type: ignore[import-not-found]
        from Basilisk.simulation import (  # type: ignore[import-not-found]
            GravityGradientEffector,
            MtbEffector,
            extForceTorque,
            magneticFieldCenteredDipole,
            reactionWheelStateEffector,
            spacecraft,
        )
        from Basilisk.utilities import (  # type: ignore[import-not-found]
            SimulationBaseClass,
            macros,
            orbitalMotion,
            simIncludeGravBody,
            simIncludeRW,
            vizSupport,
        )

        return {
            "Basilisk": Basilisk,
            "messaging": messaging,
            "spacecraft": spacecraft,
            "reactionWheelStateEffector": reactionWheelStateEffector,
            "MtbEffector": MtbEffector,
            "GravityGradientEffector": GravityGradientEffector,
            "extForceTorque": extForceTorque,
            "magneticFieldCenteredDipole": magneticFieldCenteredDipole,
            "SimulationBaseClass": SimulationBaseClass,
            "macros": macros,
            "orbitalMotion": orbitalMotion,
            "simIncludeGravBody": simIncludeGravBody,
            "simIncludeRW": simIncludeRW,
            "vizSupport": vizSupport,
        }

    def set_external_disturbance_body_nm(self, tau_body_nm: FloatArray) -> None:
        """Apply an external disturbance torque in body frame [N*m] inside Basilisk."""
        tau = np.asarray(tau_body_nm, dtype=np.float64)
        if tau.shape != (3,) or not np.all(np.isfinite(tau)):
            raise ValueError(f"External disturbance must be finite 3-vector, got {tau!r}")
        self._ext_disturbance_body_nm = tau.copy()
        if self._ext_ft is not None:
            self._ext_ft.extTorquePntB_B = [[float(tau[0])], [float(tau[1])], [float(tau[2])]]

    def set_rw_fault(
        self,
        effectiveness: FloatArray | None = None,
        bias_nm: FloatArray | None = None,
    ) -> None:
        """Inject reaction-wheel effectiveness loss [0, 1] and/or torque bias [N*m]."""
        n_rw = self.config.reaction_wheels.count
        if effectiveness is not None:
            eff = np.asarray(effectiveness, dtype=np.float64)
            if eff.shape != (n_rw,) or not np.all(np.isfinite(eff)):
                raise ValueError(f"RW effectiveness must have shape ({n_rw},), got {eff!r}")
            self._rw_effectiveness = np.clip(eff, 0.0, 1.0)
        if bias_nm is not None:
            bias = np.asarray(bias_nm, dtype=np.float64)
            if bias.shape != (n_rw,) or not np.all(np.isfinite(bias)):
                raise ValueError(f"RW bias must have shape ({n_rw},), got {bias!r}")
            self._rw_bias_nm = bias.copy()

    @property
    def backend_name(self) -> str:
        return "basilisk"

    @property
    def backend_version(self) -> str:
        return self._version

    def reset(
        self,
        *,
        q_ib_init: FloatArray | None = None,
        omega_body_init: FloatArray | None = None,
        wheel_momentum_init: FloatArray | None = None,
        true_anomaly_deg_init: float | None = None,
        r_eci_init_m: FloatArray | None = None,
        v_eci_init_m_s: FloatArray | None = None,
        seed: int | None = None,
    ) -> SpacecraftTruthState:
        del seed
        q0 = (
            np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
            if q_ib_init is None
            else quat_normalize(q_ib_init)
        )
        w0 = (
            np.zeros(3, dtype=np.float64)
            if omega_body_init is None
            else np.asarray(omega_body_init, dtype=np.float64).copy()
        )
        h0 = (
            np.zeros(self.config.reaction_wheels.count, dtype=np.float64)
            if wheel_momentum_init is None
            else np.asarray(wheel_momentum_init, dtype=np.float64).copy()
        )
        sigma0 = quat_ib_to_mrp_bn(q0)
        nu0 = (
            self.config.orbit.true_anomaly_deg_initial
            if true_anomaly_deg_init is None
            else float(true_anomaly_deg_init)
        )
        self._ext_disturbance_body_nm = np.zeros(3, dtype=np.float64)
        self._rw_effectiveness = np.ones(self.config.reaction_wheels.count, dtype=np.float64)
        self._rw_bias_nm = np.zeros(self.config.reaction_wheels.count, dtype=np.float64)

        # Delegate construction to native Basilisk SimulationBaseClass or injected test harness
        builder = self._bsk.get("build_runtime")
        if callable(builder):
            self._sim = builder(self.config, self.wiring_spec, sigma0, w0, h0, nu0)
            self._time_s = 0.0
            self._last_truth = self._extract_truth_from_runtime(
                np.zeros(self.config.reaction_wheels.count),
                np.zeros(self.config.magnetorquers.count),
            )
            return self._last_truth

        self._build_native_basilisk_sim(
            sigma0,
            w0,
            h0,
            nu0,
            r_eci_init_m=r_eci_init_m,
            v_eci_init_m_s=v_eci_init_m_s,
        )
        self._time_s = 0.0
        self._last_truth = self._extract_truth_from_native(
            np.zeros(self.config.reaction_wheels.count),
            np.zeros(self.config.magnetorquers.count),
        )
        return self._last_truth

    def _build_native_basilisk_sim(
        self,
        sigma0: FloatArray,
        omega0: FloatArray,
        h0: FloatArray,
        nu0_deg: float,
        *,
        r_eci_init_m: FloatArray | None = None,
        v_eci_init_m_s: FloatArray | None = None,
    ) -> None:
        bsk = self._bsk
        sc_sim = bsk["SimulationBaseClass"].SimBaseClass()
        dyn_proc = sc_sim.CreateNewProcess("dynamicsProcess")
        dt_ns = self.wiring_spec.integration_step_ns
        dyn_proc.addTask(sc_sim.CreateNewTask("dynamicsTask", dt_ns))

        sc_obj = bsk["spacecraft"].Spacecraft()
        sc_obj.ModelTag = self.config.name
        sc_obj.hub.mHub = self.config.mass_kg
        sc_obj.hub.IHubPntBc_B = [
            list(self.wiring_spec.inertia_flat_kg_m2[0:3]),
            list(self.wiring_spec.inertia_flat_kg_m2[3:6]),
            list(self.wiring_spec.inertia_flat_kg_m2[6:9]),
        ]

        grav_factory = bsk["simIncludeGravBody"].gravBodyFactory()
        earth = grav_factory.createEarth()
        earth.mu = self.config.orbit.gravitational_parameter_m3_s2
        earth.isCentralBody = True
        grav_factory.addBodiesTo(sc_obj)

        if r_eci_init_m is not None and v_eci_init_m_s is not None:
            r_n = np.asarray(r_eci_init_m, dtype=np.float64).reshape(3)
            v_n = np.asarray(v_eci_init_m_s, dtype=np.float64).reshape(3)
        else:
            oe = bsk["orbitalMotion"].ClassicElements()
            oe.a = self.config.orbit.semi_major_axis_m
            oe.e = self.config.orbit.eccentricity
            oe.i = np.deg2rad(self.config.orbit.inclination_deg)
            oe.Omega = np.deg2rad(self.config.orbit.raan_deg)
            oe.omega = np.deg2rad(self.config.orbit.argument_of_perigee_deg)
            oe.f = np.deg2rad(nu0_deg)
            r_n, v_n = bsk["orbitalMotion"].elem2rv(earth.mu, oe)

        sc_obj.hub.r_CN_NInit = r_n
        sc_obj.hub.v_CN_NInit = v_n
        sc_obj.hub.sigma_BNInit = [[float(x)] for x in sigma0]
        sc_obj.hub.omega_BN_BInit = [[float(x)] for x in omega0]
        sc_sim.AddModelToTask("dynamicsTask", sc_obj)

        # External disturbance force/torque effector (defaults to 0)
        ext_ft = bsk["extForceTorque"].ExtForceTorque()
        ext_ft.ModelTag = "externalDisturbance"
        ext_ft.extTorquePntB_B = [[0.0], [0.0], [0.0]]
        sc_obj.addDynamicEffector(ext_ft)
        sc_sim.AddModelToTask("dynamicsTask", ext_ft)

        # Optional gravity-gradient dynamic effector
        if self.wiring_spec.gravity_gradient_enabled:
            gg_eff = bsk["GravityGradientEffector"].GravityGradientEffector()
            gg_eff.ModelTag = "gravityGradient"
            gg_eff.addPlanetName(earth.planetName)
            sc_obj.addDynamicEffector(gg_eff)
            sc_sim.AddModelToTask("dynamicsTask", gg_eff)

        # Reaction wheel state effector (zero friction/jitter to match nominal plant)
        rw_factory = bsk["simIncludeRW"].rwFactory()
        for i, axis in enumerate(self.wiring_spec.rw_axes_body):
            omega_init_rpm = (
                float(h0[i]) / self.wiring_spec.rw_rotor_inertia_kg_m2
            ) * (60.0 / (2.0 * np.pi))
            omega_max_rpm = (
                self.wiring_spec.rw_max_momentum_nms / self.wiring_spec.rw_rotor_inertia_kg_m2
            ) * (60.0 / (2.0 * np.pi))
            rw_factory.create(
                "custom",
                list(axis),
                maxMomentum=self.wiring_spec.rw_max_momentum_nms,
                Omega_max=omega_max_rpm,
                u_max=self.wiring_spec.rw_max_torque_nm,
                Omega=omega_init_rpm,
                useRWfriction=False,
                useMinTorque=False,
                useMaxTorque=True,
            )
        rw_eff = bsk["reactionWheelStateEffector"].ReactionWheelStateEffector()
        rw_eff.ModelTag = "rwEffector"
        rw_factory.addToSpacecraft(sc_obj.ModelTag, rw_eff, sc_obj)
        sc_sim.AddModelToTask("dynamicsTask", rw_eff)

        rw_cmd_payload = bsk["messaging"].ArrayMotorTorqueMsgPayload()
        rw_cmd_payload.motorTorque = [0.0] * self.config.reaction_wheels.count
        rw_cmd_msg = bsk["messaging"].ArrayMotorTorqueMsg().write(rw_cmd_payload)
        rw_eff.rwMotorCmdInMsg.subscribeTo(rw_cmd_msg)

        # Geomagnetic field (IGRF-14 2025.0 main tilted dipole in Basilisk native module)
        mag_module = bsk["magneticFieldCenteredDipole"].MagneticFieldCenteredDipole()
        mag_module.ModelTag = "magField"
        mag_module.g10 = -29350.0e-9
        mag_module.g11 = -1410.3e-9
        mag_module.h11 = 4545.5e-9
        mag_module.planetRadius = 6371200.0
        mag_module.addSpacecraftToModel(sc_obj.scStateOutMsg)
        sc_sim.AddModelToTask("dynamicsTask", mag_module)

        # Magnetorquer dynamic effector
        mtb_cfg_payload = bsk["messaging"].MTBArrayConfigMsgPayload()
        mtb_cfg_payload.numMTB = self.config.magnetorquers.count
        mtb_cfg_payload.GtMatrix_B = (
            self.config.magnetorquers.axis_matrix_body.reshape(-1).tolist()
        )
        mtb_cfg_payload.maxMtbDipoles = [
            float(self.config.magnetorquers.dipole_limit_per_axis_am2)
        ] * self.config.magnetorquers.count
        mtb_cfg_msg = bsk["messaging"].MTBArrayConfigMsg().write(mtb_cfg_payload)

        mtb_cmd_payload = bsk["messaging"].MTBCmdMsgPayload()
        mtb_cmd_payload.mtbDipoleCmds = [0.0] * self.config.magnetorquers.count
        mtb_cmd_msg = bsk["messaging"].MTBCmdMsg().write(mtb_cmd_payload)

        mtb_eff = bsk["MtbEffector"].MtbEffector()
        mtb_eff.ModelTag = "mtbEffector"
        mtb_eff.mtbParamsInMsg.subscribeTo(mtb_cfg_msg)
        mtb_eff.mtbCmdInMsg.subscribeTo(mtb_cmd_msg)
        mtb_eff.magInMsg.subscribeTo(mag_module.envOutMsgs[0])
        sc_obj.addDynamicEffector(mtb_eff)
        sc_sim.AddModelToTask("dynamicsTask", mtb_eff)

        # Optional Basilisk Vizard 3D binary recording or live streaming
        viz = None
        if self._vizard_file is not None or self._vizard_live:
            viz_task = sc_sim.CreateNewTask("vizTask", self.wiring_spec.control_period_ns)
            dyn_proc.addTask(viz_task)
            viz = bsk["vizSupport"].enableUnityVisualization(
                sc_sim,
                "vizTask",
                sc_obj,
                saveFile=self._vizard_file,
                rwEffectorList=rw_eff,
                liveStream=self._vizard_live,
            )

        sc_sim.InitializeSimulation()
        self._sim = sc_sim
        self._sc_object = sc_obj
        self._rw_eff = rw_eff
        self._mtb_eff = mtb_eff
        self._ext_ft = ext_ft
        self._rw_cmd_msg = rw_cmd_msg
        self._mtq_cmd_msg = mtb_cmd_msg
        self._mtb_cfg_msg = mtb_cfg_msg
        self._mag_module = mag_module
        self._viz = viz

    def _extract_truth_from_runtime(
        self, rw_cmd: FloatArray, mtq_cmd: FloatArray
    ) -> SpacecraftTruthState:
        raw = self._sim.read_state()
        q_ib = mrp_bn_to_quat_ib(np.asarray(raw["sigma_bn"], dtype=np.float64))
        b_eci = np.asarray(raw["b_eci_t"], dtype=np.float64)
        b_body = quat_rotate_vec_inv(q_ib, b_eci)
        h_w = np.asarray(raw["wheel_momentum_nms"], dtype=np.float64)
        m_ach = np.asarray(raw.get("mtq_dipole_am2", mtq_cmd), dtype=np.float64)
        tau_rw = np.asarray(raw.get("rw_torque_nm", rw_cmd), dtype=np.float64)
        tau_mtq = np.cross(self.config.magnetorquers.axis_matrix_body @ m_ach, b_body)
        truth = SpacecraftTruthState(
            time_s=float(raw["time_s"]),
            position_eci_m=np.asarray(raw["r_eci_m"], dtype=np.float64),
            velocity_eci_m_s=np.asarray(raw["v_eci_m_s"], dtype=np.float64),
            q_ib=q_ib,
            omega_body_rad_s=np.asarray(raw["omega_bn_b"], dtype=np.float64),
            wheel_momentum_nms=h_w,
            wheel_speed_rad_s=h_w / self.config.reaction_wheels.rotor_inertia_kg_m2,
            rw_torque_achieved_nm=tau_rw,
            mtq_dipole_achieved_am2=m_ach,
            mtq_torque_achieved_nm=tau_mtq,
            b_field_body_t=b_body,
            disturbance_torque_body_nm=np.asarray(
                raw.get("disturbance_nm", np.zeros(3)), dtype=np.float64
            ),
            actuator_status=ActuatorStatus(
                rw_torque_saturated=(False,) * self.config.reaction_wheels.count,
                rw_momentum_saturated=(False,) * self.config.reaction_wheels.count,
                mtq_dipole_saturated=(False,) * self.config.magnetorquers.count,
            ),
        )
        truth.validate()
        return truth

    def _extract_truth_from_native(
        self, rw_cmd: FloatArray, mtq_cmd: FloatArray
    ) -> SpacecraftTruthState:
        st_msg = self._sc_object.scStateOutMsg.read()
        q_ib = mrp_bn_to_quat_ib(np.asarray(st_msg.sigma_BN, dtype=np.float64))
        b_eci = np.asarray(self._mag_module.envOutMsgs[0].read().magField_N, dtype=np.float64)
        b_body = quat_rotate_vec_inv(q_ib, b_eci)
        n_rw = self.config.reaction_wheels.count
        rw_speed_msg = self._rw_eff.rwSpeedOutMsg.read()
        rw_speeds = np.asarray(rw_speed_msg.wheelSpeeds[:n_rw], dtype=np.float64)
        h_w = rw_speeds * self.config.reaction_wheels.rotor_inertia_kg_m2
        rw_tau_ach = np.clip(
            self._rw_effectiveness * rw_cmd + self._rw_bias_nm,
            -self.config.reaction_wheels.torque_limit_nominal_nm,
            self.config.reaction_wheels.torque_limit_nominal_nm,
        )
        m_lim = self.config.magnetorquers.dipole_limit_per_axis_am2
        m_ach = np.clip(mtq_cmd, -m_lim, m_lim)
        mtb_out = self._mtb_eff.mtbOutMsg.read()
        tau_mtq = np.asarray(mtb_out.mtbNetTorque_B, dtype=np.float64)
        if not np.any(tau_mtq) and np.any(m_ach):
            tau_mtq = np.cross(self.config.magnetorquers.axis_matrix_body @ m_ach, b_body)
        truth = SpacecraftTruthState(
            time_s=self._time_s,
            position_eci_m=np.asarray(st_msg.r_BN_N, dtype=np.float64),
            velocity_eci_m_s=np.asarray(st_msg.v_BN_N, dtype=np.float64),
            q_ib=q_ib,
            omega_body_rad_s=np.asarray(st_msg.omega_BN_B, dtype=np.float64),
            wheel_momentum_nms=h_w,
            wheel_speed_rad_s=rw_speeds,
            rw_torque_achieved_nm=rw_tau_ach,
            mtq_dipole_achieved_am2=m_ach,
            mtq_torque_achieved_nm=tau_mtq,
            b_field_body_t=b_body,
            disturbance_torque_body_nm=self._ext_disturbance_body_nm.copy(),
            actuator_status=ActuatorStatus(
                rw_torque_saturated=tuple(
                    bool(abs(float(u)) > self.config.reaction_wheels.torque_limit_nominal_nm)
                    for u in rw_cmd
                ),
                rw_momentum_saturated=tuple(
                    bool(abs(float(h)) >= self.config.reaction_wheels.effective_momentum_limit_nms)
                    for h in h_w
                ),
                mtq_dipole_saturated=tuple(bool(abs(float(m)) > m_lim) for m in mtq_cmd),
            ),
        )
        truth.validate()
        return truth

    def step(
        self,
        rw_torque_cmd_nm: FloatArray,
        mtq_dipole_cmd_am2: FloatArray,
        dt_s: float | None = None,
    ) -> PlantStepOutput:
        rw_cmd = np.asarray(rw_torque_cmd_nm, dtype=np.float64)
        mtq_cmd = np.asarray(mtq_dipole_cmd_am2, dtype=np.float64)
        if not np.all(np.isfinite(rw_cmd)) or not np.all(np.isfinite(mtq_cmd)):
            raise ValueError("Actuator commands must be finite")
        period = self.config.simulation.control_period_s if dt_s is None else float(dt_s)
        if self._sim is None:
            raise RuntimeError("Call reset() before step()")

        if callable(self._bsk.get("build_runtime")):
            self._sim.advance(rw_cmd, mtq_cmd, period)
            self._time_s += period
            self._last_truth = self._extract_truth_from_runtime(rw_cmd, mtq_cmd)
            return PlantStepOutput(truth=self._last_truth, info={"backend": "basilisk_mock"})

        # Note sign convention: Basilisk motorTorque u_s accelerates rotor (+dh/dt),
        # whereas our rw_torque_cmd_nm is body reaction torque (-dh/dt).
        rw_effective_cmd = self._rw_effectiveness * rw_cmd + self._rw_bias_nm
        payload = self._bsk["messaging"].ArrayMotorTorqueMsgPayload()
        payload.motorTorque = (-rw_effective_cmd).tolist()
        self._rw_cmd_msg.write(payload)

        mtb_payload = self._bsk["messaging"].MTBCmdMsgPayload()
        mtb_payload.mtbDipoleCmds = mtq_cmd.tolist()
        self._mtq_cmd_msg.write(mtb_payload)

        self._time_s += period
        stop_ns = int(round(self._time_s * 1_000_000_000))
        self._sim.ConfigureStopTime(stop_ns)
        self._sim.ExecuteSimulation()
        self._last_truth = self._extract_truth_from_native(rw_cmd, mtq_cmd)
        return PlantStepOutput(truth=self._last_truth, info={"backend": "basilisk_native"})

    def get_truth_state(self) -> SpacecraftTruthState:
        if self._last_truth is None:
            raise RuntimeError("Call reset() before get_truth_state()")
        return self._last_truth
