"""Modular fault injection catalog and scenario splits (S0–S8)."""

from adcs.faults.catalog import (
    FaultEvent,
    FaultInjector,
    ScenarioSpec,
    build_default_scenario_catalog,
)

__all__ = [
    "FaultEvent",
    "FaultInjector",
    "ScenarioSpec",
    "build_default_scenario_catalog",
]
