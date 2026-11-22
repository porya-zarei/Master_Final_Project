"""Shared typed interfaces and protocols for the ADCS research platform."""

from adcs.interfaces.protocols import (
    CapabilityEstimatorProtocol,
    ControllerProtocol,
    EstimatorProtocol,
    SimulatorBackend,
)
from adcs.interfaces.types import (
    ActuatorCapabilityState,
    ActuatorCommand,
    ActuatorStatus,
    ControlStepOutput,
    EstimatorOutput,
    GateDecision,
    MTQCapability,
    PlantStepOutput,
    ReferenceState,
    SensorMeasurement,
    SpacecraftTruthState,
    SupervisorMode,
    WheelCapability,
)

__all__ = [
    "ActuatorCapabilityState",
    "ActuatorCommand",
    "ActuatorStatus",
    "CapabilityEstimatorProtocol",
    "ControlStepOutput",
    "ControllerProtocol",
    "EstimatorOutput",
    "EstimatorProtocol",
    "GateDecision",
    "MTQCapability",
    "PlantStepOutput",
    "ReferenceState",
    "SensorMeasurement",
    "SimulatorBackend",
    "SpacecraftTruthState",
    "SupervisorMode",
    "WheelCapability",
]
