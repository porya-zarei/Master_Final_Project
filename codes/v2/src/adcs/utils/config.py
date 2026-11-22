"""Configuration loading and strict schema/physics validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from adcs.interfaces.types import FloatArray
from adcs.utils.seeding import sha256_canonical


class ConfigValidationError(ValueError):
    """Raised when a YAML configuration violates schema or physical validity rules."""


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML mapping from disk with explicit error reporting."""
    file_path = Path(path)
    if not file_path.exists():
        raise ConfigValidationError(f"Configuration file does not exist: {file_path}")
    with file_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ConfigValidationError(
            f"Configuration root in {file_path} must be a YAML mapping, got {type(data).__name__}"
        )
    return data


def _require_mapping(parent: dict[str, Any], key: str, ctx: str) -> dict[str, Any]:
    if key not in parent or not isinstance(parent[key], dict):
        raise ConfigValidationError(f"Missing or non-mapping section '{ctx}.{key}'")
    return parent[key]


def _parse_finite_float(val: Any, ctx: str, key: str) -> float:
    """Parse finite floats, including YAML 1.1 scientific notation strings (e.g. '3.98e14')."""
    if isinstance(val, bool):
        raise ConfigValidationError(f"'{ctx}.{key}' must be a number, got bool {val!r}")
    if isinstance(val, (int, float)):
        out = float(val)
    elif isinstance(val, str):
        try:
            out = float(val)
        except ValueError as exc:
            raise ConfigValidationError(
                f"'{ctx}.{key}' must be a finite number, got {val!r}"
            ) from exc
    else:
        raise ConfigValidationError(f"'{ctx}.{key}' must be a finite number, got {val!r}")
    if not np.isfinite(out):
        raise ConfigValidationError(f"'{ctx}.{key}' must be a finite number, got {val!r}")
    return out


def _require_positive_float(parent: dict[str, Any], key: str, ctx: str) -> float:
    if key not in parent:
        raise ConfigValidationError(f"Missing required key '{ctx}.{key}'")
    out = _parse_finite_float(parent[key], ctx, key)
    if out <= 0.0:
        raise ConfigValidationError(f"'{ctx}.{key}' must be a finite positive number, got {out!r}")
    return out


def _require_nonneg_float(parent: dict[str, Any], key: str, ctx: str) -> float:
    if key not in parent:
        raise ConfigValidationError(f"Missing required key '{ctx}.{key}'")
    out = _parse_finite_float(parent[key], ctx, key)
    if out < 0.0:
        raise ConfigValidationError(
            f"'{ctx}.{key}' must be a finite non-negative number, got {out!r}"
        )
    return out


def _require_float(parent: dict[str, Any], key: str, ctx: str) -> float:
    if key not in parent:
        raise ConfigValidationError(f"Missing required key '{ctx}.{key}'")
    return _parse_finite_float(parent[key], ctx, key)


@dataclass(frozen=True)
class OrbitConfig:
    altitude_m: float
    earth_radius_m: float
    semi_major_axis_m: float
    eccentricity: float
    inclination_deg: float
    raan_deg: float
    argument_of_perigee_deg: float
    true_anomaly_deg_initial: float
    gravitational_parameter_m3_s2: float
    epoch_utc: str | None


@dataclass(frozen=True)
class SimulationConfig:
    control_period_s: float
    control_rate_hz: float
    integration_method: str
    integration_step_s: float
    deterministic: bool
    random_seed: int


@dataclass(frozen=True)
class ReactionWheelConfig:
    count: int
    axis_matrix_body: FloatArray  # shape (3, count), columns are unit wheel axes
    rotor_inertia_kg_m2: float
    torque_limit_nominal_nm: float
    torque_limit_peak_nm: float
    momentum_limit_nominal_nms: float
    momentum_limit_peak_nms: float
    speed_limit_rpm: float
    time_constant_s: float
    viscous_nm_per_rad_s: float
    coulomb_nm: float
    stiction_band_nm: float

    @property
    def speed_limit_rad_s(self) -> float:
        return self.speed_limit_rpm * (2.0 * np.pi / 60.0)

    @property
    def effective_momentum_limit_nms(self) -> float:
        """Enforce min(nominal momentum limit, rotor_inertia * speed_limit)."""
        return float(
            min(
                self.momentum_limit_nominal_nms,
                self.rotor_inertia_kg_m2 * self.speed_limit_rad_s,
            )
        )


@dataclass(frozen=True)
class MagnetorquerConfig:
    count: int
    axis_matrix_body: FloatArray  # shape (3, count), columns are unit dipole axes
    dipole_limit_per_axis_am2: float
    dipole_command_limits_am2: FloatArray  # shape (count, 2) [min, max]
    time_constant_s: float


@dataclass(frozen=True)
class DisturbanceConfig:
    gravity_gradient_enabled: bool
    residual_magnetic_dipole_enabled: bool
    residual_dipole_body_am2: FloatArray
    aerodynamic_enabled: bool
    solar_radiation_pressure_enabled: bool


@dataclass(frozen=True)
class MagneticFieldConfig:
    model: str
    generation: str
    epoch_model: str
    coefficient_file: str | None = None


@dataclass(frozen=True)
class SpacecraftConfig:
    """Validated spacecraft plant configuration."""

    name: str
    version: str
    mass_kg: float
    dimensions_m: FloatArray
    inertia_matrix_kg_m2: FloatArray  # shape (3, 3), SPD
    inertia_uncertainty_fraction: float
    orbit: OrbitConfig
    simulation: SimulationConfig
    reaction_wheels: ReactionWheelConfig
    magnetorquers: MagnetorquerConfig
    magnetic_field: MagneticFieldConfig
    disturbances: DisturbanceConfig
    raw_hash: str
    warnings: tuple[str, ...]


def load_spacecraft_config(path: str | Path) -> SpacecraftConfig:
    """Load and strictly validate a spacecraft YAML configuration file."""
    raw = load_yaml(path)
    raw_hash = sha256_canonical(raw)
    warnings: list[str] = []

    meta = _require_mapping(raw, "metadata", "root")
    sc = _require_mapping(raw, "spacecraft", "root")
    inertia_sec = _require_mapping(sc, "inertia", "spacecraft")
    orb = _require_mapping(raw, "orbit", "root")
    sim = _require_mapping(raw, "simulation", "root")
    integ = _require_mapping(sim, "integration", "simulation")
    rw = _require_mapping(raw, "reaction_wheels", "root")
    rw_pw = _require_mapping(rw, "per_wheel", "reaction_wheels")
    rw_resp = _require_mapping(rw_pw, "response", "reaction_wheels.per_wheel")
    rw_fric = _require_mapping(rw_pw, "friction", "reaction_wheels.per_wheel")
    mtq = _require_mapping(raw, "magnetorquers", "root")
    mtq_resp = _require_mapping(mtq, "response", "magnetorquers")
    mag = _require_mapping(raw, "earth_magnetic_field", "root")
    dist = _require_mapping(raw, "disturbances", "root")

    mass_kg = _require_positive_float(sc, "mass_kg", "spacecraft")
    dims = np.asarray(sc.get("dimensions_m", []), dtype=np.float64)
    if dims.shape != (3,) or not np.all(np.isfinite(dims)) or np.any(dims <= 0.0):
        raise ConfigValidationError("spacecraft.dimensions_m must be 3 positive numbers")

    inertia = np.asarray(inertia_sec.get("matrix_kg_m2", []), dtype=np.float64)
    if inertia.shape != (3, 3) or not np.all(np.isfinite(inertia)):
        raise ConfigValidationError("spacecraft.inertia.matrix_kg_m2 must be a finite 3x3 matrix")
    if not np.allclose(inertia, inertia.T, atol=1e-10):
        raise ConfigValidationError("spacecraft.inertia.matrix_kg_m2 must be symmetric")
    eigvals = np.linalg.eigvalsh(inertia)
    if np.any(eigvals <= 0.0):
        raise ConfigValidationError(
            f"spacecraft.inertia.matrix_kg_m2 must be positive definite, eigenvalues={eigvals}"
        )
    # Triangle inequality for principal moments of inertia
    s_eig = np.sort(eigvals)
    if s_eig[0] + s_eig[1] < s_eig[2] - 1e-9:
        raise ConfigValidationError(
            f"Inertia eigenvalues violate physical triangle inequality: {s_eig}"
        )
    inertia_unc = _require_nonneg_float(inertia_sec, "uncertainty_fraction", "spacecraft.inertia")

    # Orbit validation
    alt = _require_positive_float(orb, "altitude_m", "orbit")
    re = _require_positive_float(orb, "earth_radius_m", "orbit")
    sma = _require_positive_float(orb, "semi_major_axis_m", "orbit")
    if abs(sma - (re + alt)) > 1.0:
        raise ConfigValidationError(
            f"orbit.semi_major_axis_m ({sma}) inconsistent with earth_radius_m + altitude_m "
            f"({re + alt})"
        )
    ecc = _require_nonneg_float(orb, "eccentricity", "orbit")
    if ecc >= 1.0:
        raise ConfigValidationError(f"orbit.eccentricity must be < 1.0 for bound orbit, got {ecc}")
    orbit_cfg = OrbitConfig(
        altitude_m=alt,
        earth_radius_m=re,
        semi_major_axis_m=sma,
        eccentricity=ecc,
        inclination_deg=_require_float(orb, "inclination_deg", "orbit"),
        raan_deg=_require_float(orb, "raan_deg", "orbit"),
        argument_of_perigee_deg=_require_float(orb, "argument_of_perigee_deg", "orbit"),
        true_anomaly_deg_initial=_require_float(orb, "true_anomaly_deg_initial", "orbit"),
        gravitational_parameter_m3_s2=_require_positive_float(
            orb, "gravitational_parameter_m3_s2", "orbit"
        ),
        epoch_utc=orb.get("epoch_utc"),
    )

    # Simulation timing validation
    dt_ctrl = _require_positive_float(sim, "control_period_s", "simulation")
    rate_hz = _require_positive_float(sim, "control_rate_hz", "simulation")
    if abs(dt_ctrl * rate_hz - 1.0) > 1e-6:
        raise ConfigValidationError(
            f"simulation.control_period_s ({dt_ctrl}) inconsistent with control_rate_hz ({rate_hz})"
        )
    dt_int = _require_positive_float(integ, "step_s", "simulation.integration")
    if dt_int > dt_ctrl + 1e-12:
        raise ConfigValidationError(
            f"integration.step_s ({dt_int}) cannot exceed control_period_s ({dt_ctrl})"
        )
    ratio = dt_ctrl / dt_int
    if abs(ratio - round(ratio)) > 1e-6:
        raise ConfigValidationError(
            f"control_period_s ({dt_ctrl}) must be an integer multiple of "
            f"integration.step_s ({dt_int})"
        )
    sim_cfg = SimulationConfig(
        control_period_s=dt_ctrl,
        control_rate_hz=rate_hz,
        integration_method=str(integ.get("method", "RK4")),
        integration_step_s=dt_int,
        deterministic=bool(integ.get("deterministic", True)),
        random_seed=int(sim.get("random_seed", 0)),
    )

    # Reaction wheels validation
    rw_count = int(rw.get("count", 0))
    if rw_count < 1:
        raise ConfigValidationError(f"reaction_wheels.count must be >= 1, got {rw_count}")
    rw_axes = np.asarray(rw.get("axis_matrix_body", []), dtype=np.float64)
    if rw_axes.shape != (3, rw_count) or not np.all(np.isfinite(rw_axes)):
        raise ConfigValidationError(
            f"reaction_wheels.axis_matrix_body must have shape (3, {rw_count})"
        )
    col_norms = np.linalg.norm(rw_axes, axis=0)
    if not np.allclose(col_norms, 1.0, atol=1e-6):
        raise ConfigValidationError(
            f"reaction_wheels.axis_matrix_body columns must be unit vectors, norms={col_norms}"
        )
    rw_rotor_j = _require_positive_float(rw_pw, "rotor_inertia_kg_m2", "reaction_wheels.per_wheel")
    rw_tau_nom = _require_positive_float(
        rw_pw, "torque_limit_nominal_Nm", "reaction_wheels.per_wheel"
    )
    rw_tau_peak = _require_positive_float(
        rw_pw, "torque_limit_peak_Nm", "reaction_wheels.per_wheel"
    )
    rw_h_nom = _require_positive_float(
        rw_pw, "momentum_limit_nominal_Nms", "reaction_wheels.per_wheel"
    )
    rw_h_peak = _require_positive_float(
        rw_pw, "momentum_limit_peak_Nms", "reaction_wheels.per_wheel"
    )
    rw_rpm = _require_positive_float(rw_pw, "speed_limit_rpm", "reaction_wheels.per_wheel")
    h_from_speed = rw_rotor_j * (rw_rpm * 2.0 * np.pi / 60.0)
    if rw_h_peak > h_from_speed * 1.001:
        warnings.append(
            f"RW momentum_limit_peak_Nms ({rw_h_peak:.3f}) slightly exceeds "
            f"rotor_inertia * speed_limit ({h_from_speed:.4f} Nms); "
            f"effective limit enforces min(h_limit, I_w * omega_max)."
        )
    rw_cfg = ReactionWheelConfig(
        count=rw_count,
        axis_matrix_body=rw_axes,
        rotor_inertia_kg_m2=rw_rotor_j,
        torque_limit_nominal_nm=rw_tau_nom,
        torque_limit_peak_nm=rw_tau_peak,
        momentum_limit_nominal_nms=rw_h_nom,
        momentum_limit_peak_nms=rw_h_peak,
        speed_limit_rpm=rw_rpm,
        time_constant_s=_require_nonneg_float(
            rw_resp, "time_constant_s", "reaction_wheels.per_wheel.response"
        ),
        viscous_nm_per_rad_s=_require_nonneg_float(
            rw_fric, "viscous_Nm_per_rad_s", "reaction_wheels.per_wheel.friction"
        ),
        coulomb_nm=_require_nonneg_float(
            rw_fric, "coulomb_Nm", "reaction_wheels.per_wheel.friction"
        ),
        stiction_band_nm=_require_nonneg_float(
            rw_fric, "stiction_band_Nm", "reaction_wheels.per_wheel.friction"
        ),
    )

    # Magnetorquer validation
    mtq_count = int(mtq.get("count", 0))
    if mtq_count < 1:
        raise ConfigValidationError(f"magnetorquers.count must be >= 1, got {mtq_count}")
    mtq_axes = np.asarray(mtq.get("axis_matrix_body", []), dtype=np.float64)
    if mtq_axes.shape != (3, mtq_count) or not np.all(np.isfinite(mtq_axes)):
        raise ConfigValidationError(
            f"magnetorquers.axis_matrix_body must have shape (3, {mtq_count})"
        )
    if not np.allclose(np.linalg.norm(mtq_axes, axis=0), 1.0, atol=1e-6):
        raise ConfigValidationError("magnetorquers.axis_matrix_body columns must be unit vectors")
    mtq_limits = np.asarray(mtq.get("dipole_command_limits_Am2", []), dtype=np.float64)
    if mtq_limits.shape != (mtq_count, 2) or not np.all(np.isfinite(mtq_limits)):
        raise ConfigValidationError(
            f"magnetorquers.dipole_command_limits_Am2 must have shape ({mtq_count}, 2)"
        )
    if np.any(mtq_limits[:, 0] >= mtq_limits[:, 1]):
        raise ConfigValidationError("MTQ lower dipole limit must be strictly less than upper limit")
    mtq_cfg = MagnetorquerConfig(
        count=mtq_count,
        axis_matrix_body=mtq_axes,
        dipole_limit_per_axis_am2=_require_positive_float(
            mtq, "dipole_limit_per_axis_Am2", "magnetorquers"
        ),
        dipole_command_limits_am2=mtq_limits,
        time_constant_s=_require_nonneg_float(
            mtq_resp, "time_constant_s", "magnetorquers.response"
        ),
    )

    # Magnetic field & disturbances
    mag_cfg = MagneticFieldConfig(
        model=str(mag.get("model", "IGRF")),
        generation=str(mag.get("generation", "IGRF-14")),
        epoch_model=str(mag.get("epoch_model", "2025.0")),
        coefficient_file=mag.get("coefficient_file"),
    )
    gg_sec = _require_mapping(dist, "gravity_gradient", "disturbances")
    rmd_sec = _require_mapping(dist, "residual_magnetic_dipole", "disturbances")
    aero_sec = _require_mapping(dist, "aerodynamic", "disturbances")
    srp_sec = _require_mapping(dist, "solar_radiation_pressure", "disturbances")
    res_dip = np.asarray(rmd_sec.get("dipole_body_Am2", [0.0, 0.0, 0.0]), dtype=np.float64)
    if res_dip.shape != (3,) or not np.all(np.isfinite(res_dip)):
        raise ConfigValidationError(
            "disturbances.residual_magnetic_dipole.dipole_body_Am2 must be a finite 3-vector"
        )
    dist_cfg = DisturbanceConfig(
        gravity_gradient_enabled=bool(gg_sec.get("enabled", True)),
        residual_magnetic_dipole_enabled=bool(rmd_sec.get("enabled", True)),
        residual_dipole_body_am2=res_dip,
        aerodynamic_enabled=bool(aero_sec.get("enabled", False)),
        solar_radiation_pressure_enabled=bool(srp_sec.get("enabled", False)),
    )

    return SpacecraftConfig(
        name=str(meta.get("name", "unnamed")),
        version=str(meta.get("version", "0.0.0")),
        mass_kg=mass_kg,
        dimensions_m=dims,
        inertia_matrix_kg_m2=inertia,
        inertia_uncertainty_fraction=inertia_unc,
        orbit=orbit_cfg,
        simulation=sim_cfg,
        reaction_wheels=rw_cfg,
        magnetorquers=mtq_cfg,
        magnetic_field=mag_cfg,
        disturbances=dist_cfg,
        raw_hash=raw_hash,
        warnings=tuple(warnings),
    )
