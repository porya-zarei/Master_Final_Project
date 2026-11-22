"""Reference attitude and angular rate generators."""

from adcs.control.reference.nadir import (
    AttitudeError,
    NadirReferenceGenerator,
    compute_attitude_error,
)

__all__ = ["AttitudeError", "NadirReferenceGenerator", "compute_attitude_error"]
