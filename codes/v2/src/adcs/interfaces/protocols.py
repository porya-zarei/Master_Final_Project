"""Structural protocols decoupling simulator backends, estimators, and controllers."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from adcs.interfaces.types import (
    ActuatorCapabilityState,
    ActuatorCommand,
    ControlStepOutput,
    EstimatorOutput,
    FloatArray,
    PlantStepOutput,
    ReferenceState,
    SensorMeasurement,
    SpacecraftTruthState,
)


@runtime_checkable
class SimulatorBackend(Protocol):
    """Unified simulator backend interface (fast Python backend and Basilisk backend)."""

    @property
    def backend_name(self) -> str: ...

    @property
    def backend_version(self) -> str: ...

    def reset(
        self,
        *,
        q_ib_init: FloatArray | None = None,
        omega_body_init: FloatArray | None = None,
        wheel_momentum_init: FloatArray | None = None,
        true_anomaly_deg_init: float | None = None,
        seed: int | None = None,
    ) -> SpacecraftTruthState: ...

    def step(
        self,
        rw_torque_cmd_nm: FloatArray,
        mtq_dipole_cmd_am2: FloatArray,
        dt_s: float | None = None,
    ) -> PlantStepOutput: ...

    def get_truth_state(self) -> SpacecraftTruthState: ...


@runtime_checkable
class EstimatorProtocol(Protocol):
    """Interface for B1 state and observability estimator."""

    def reset(
        self,
        q_ib_init: FloatArray,
        omega_init: FloatArray | None = None,
        time_s: float = 0.0,
    ) -> EstimatorOutput: ...

    def update(
        self,
        measurement: SensorMeasurement,
        dt_s: float,
        applied_rw_torque_nm: FloatArray | None = None,
    ) -> EstimatorOutput: ...


@runtime_checkable
class CapabilityEstimatorProtocol(Protocol):
    """Interface for B3 actuator capability and AMS estimation."""

    def reset(self) -> None: ...

    def estimate(
        self,
        *,
        time_s: float,
        measurement: SensorMeasurement,
        last_command: ActuatorCommand | None,
        b_field_body_t: FloatArray,
        dt_s: float,
        truth_override: dict[str, Any] | None = None,
    ) -> ActuatorCapabilityState: ...


@runtime_checkable
class ControllerProtocol(Protocol):
    """Interface for all controller arms (A0–A8)."""

    @property
    def name(self) -> str: ...

    def reset(self) -> None: ...

    def compute(
        self,
        *,
        estimator_out: EstimatorOutput,
        reference: ReferenceState,
        capability: ActuatorCapabilityState,
        measurement: SensorMeasurement,
        dt_s: float,
    ) -> ControlStepOutput: ...
