"""Actuator torque allocation for reaction wheels and magnetorquers."""

from adcs.control.allocation.allocator import (
    ActuatorAllocator,
    AllocationConfig,
    AllocationResult,
    solve_box_lsq,
)

__all__ = ["ActuatorAllocator", "AllocationConfig", "AllocationResult", "solve_box_lsq"]
