"""B6 residual RL policy interface, observation builder, and integrated CCR v2 controller."""

from adcs.control.residual_rl.controller import CCRController, CCRControllerConfig
from adcs.control.residual_rl.policy import (
    OBS_DIM,
    ObservationBuilder,
    ResidualPolicyProtocol,
    TorchMLPResidualPolicy,
    ZeroResidualPolicy,
)

__all__ = [
    "CCRController",
    "CCRControllerConfig",
    "OBS_DIM",
    "ObservationBuilder",
    "ResidualPolicyProtocol",
    "TorchMLPResidualPolicy",
    "ZeroResidualPolicy",
]
