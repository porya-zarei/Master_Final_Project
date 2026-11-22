"""Classical attitude controllers (LQR/PD backbone, DOB/ESO, and gain-scheduled baselines)."""

from adcs.control.classical.baselines import (
    ClassicalDOBController,
    ESOConfig,
    ExtendedStateObserver,
    StrongClassicalController,
    make_oracle_allocation_lqr,
)
from adcs.control.classical.lqr import ClassicalLQRConfig, ClassicalLQRController

__all__ = [
    "ClassicalDOBController",
    "ClassicalLQRConfig",
    "ClassicalLQRController",
    "ESOConfig",
    "ExtendedStateObserver",
    "StrongClassicalController",
    "make_oracle_allocation_lqr",
]
