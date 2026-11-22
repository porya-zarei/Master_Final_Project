"""B2 — Fault-symptom extractor built strictly from measurable onboard signals.

Produces a normalized 12-dim fault-symptom vector `s` without leaking ground-truth fault labels
(CONTROL_ARCHITECTURE.md §6).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from adcs.interfaces.types import (
    ActuatorCapabilityState,
    ActuatorCommand,
    EstimatorOutput,
    FloatArray,
    SensorMeasurement,
)
from adcs.utils.config import SpacecraftConfig


@dataclass(frozen=True)
class SymptomSummary:
    """Normalized fault symptom vector and named scalar diagnostics."""

    vector: FloatArray  # shape (12,)
    torque_residual_xyz_norm: FloatArray  # shape (3,)
    max_torque_residual_norm: float
    momentum_utilization_xyz: FloatArray  # shape (3,)
    degradation_indicator: float
    authority_deficit_norm: float = 0.0


class FaultSymptomExtractor:
    """Computes temporally smoothed onboard fault symptoms (B2)."""

    def __init__(self, sc_config: SpacecraftConfig, ema_alpha: float = 0.25) -> None:
        self.tau_lim = sc_config.reaction_wheels.torque_limit_nominal_nm
        self.h_lim = sc_config.reaction_wheels.effective_momentum_limit_nms
        self.rotor_j = sc_config.reaction_wheels.rotor_inertia_kg_m2
        self.tau_c = float(sc_config.reaction_wheels.time_constant_s)
        self.n_rw = sc_config.reaction_wheels.count
        self.a_rw = sc_config.reaction_wheels.axis_matrix_body.copy()
        self.ema_alpha = float(ema_alpha)
        self.reset()

    def reset(self) -> None:
        self._prev_rw_speed: FloatArray | None = None
        self._resid_ema = np.zeros(3, dtype=np.float64)
        self._expected_tau_rw = np.zeros(self.n_rw, dtype=np.float64)
        self._deficit_ema = 0.0

    def update(
        self,
        *,
        att_err_rad: float,
        rate_err_norm_rad_s: float,
        estimator_out: EstimatorOutput,
        capability: ActuatorCapabilityState,
        measurement: SensorMeasurement,
        last_command: ActuatorCommand | None,
        dt_s: float,
    ) -> SymptomSummary:
        dt = max(float(dt_s), 1e-4)
        # 1. Lagged, bias/effectiveness-compensated RW torque vs. tachometer-inferred body torque
        rw_speeds = np.asarray(measurement.rw_speed_rad_s, dtype=np.float64)
        if (
            last_command is not None
            and self._prev_rw_speed is not None
            and all(measurement.rw_speed_valid)
            and np.all(np.isfinite(rw_speeds))
        ):
            u_cmd = np.clip(last_command.rw_torque_cmd_nm, -self.tau_lim, self.tau_lim)
            if capability.valid and len(capability.wheels) == self.n_rw:
                u_exp_target = np.array(
                    [
                        wcap.effectiveness_nom * float(u_cmd[i]) + wcap.bias_est_nm
                        for i, wcap in enumerate(capability.wheels)
                    ],
                    dtype=np.float64,
                )
            else:
                u_exp_target = u_cmd.astype(np.float64, copy=False)

            if self.tau_c > 1e-6:
                decay = float(np.exp(-dt / self.tau_c))
                u_exp_avg = u_exp_target + (self._expected_tau_rw - u_exp_target) * (
                    self.tau_c / dt
                ) * (1.0 - decay)
                self._expected_tau_rw = (
                    u_exp_target + (self._expected_tau_rw - u_exp_target) * decay
                )
            else:
                u_exp_avg = u_exp_target
                self._expected_tau_rw = u_exp_target.copy()

            tau_expected_body = self.a_rw @ u_exp_avg
            tau_meas_rw = -self.rotor_j * (rw_speeds - self._prev_rw_speed) / dt
            tau_meas_body = self.a_rw @ tau_meas_rw
            resid_norm = np.abs(tau_expected_body - tau_meas_body) / max(self.tau_lim, 1e-6)
            self._resid_ema = (1.0 - self.ema_alpha) * self._resid_ema + self.ema_alpha * np.clip(
                resid_norm, 0.0, 2.0
            )
        if all(measurement.rw_speed_valid) and np.all(np.isfinite(rw_speeds)):
            self._prev_rw_speed = rw_speeds.copy()

        if last_command is not None:
            def_inst = float(
                np.linalg.norm(last_command.tau_request_nm - last_command.tau_allocated_nm)
            ) / max(self.tau_lim, 1e-6)
            if np.isfinite(def_inst):
                self._deficit_ema = (
                    1.0 - self.ema_alpha
                ) * self._deficit_ema + self.ema_alpha * min(def_inst, 3.0)

        # 2. Wheel momentum utilization projected onto 3 body axes (N-wheel general)
        h_est = self.rotor_j * rw_speeds
        h_axis_max = np.maximum(np.sum(np.abs(self.a_rw), axis=1) * self.h_lim, 1e-6)
        h_util = np.clip(np.abs(self.a_rw @ h_est) / h_axis_max, 0.0, 1.0)

        # 3. Attitude, rate, innovation, observability, and capability deficits
        att_s = float(np.clip(att_err_rad / 0.35, 0.0, 2.0))
        rate_s = float(np.clip(rate_err_norm_rad_s / 0.05, 0.0, 2.0))
        innov_s = float(np.clip(estimator_out.diagnostics.get("innov_ema", 0.0) / 10.0, 0.0, 2.0))
        obs_def = float(np.clip(1.0 - estimator_out.gamma_obs, 0.0, 1.0))
        cap_unc = float(np.clip(1.0 - capability.confidence, 0.0, 1.0))
        min_margin = float(np.min(capability.directional_margin_xyz)) if capability.valid else 0.0
        dir_def = float(np.clip(1.0 - min_margin, 0.0, 1.0))

        vec = np.array(
            [
                self._resid_ema[0],
                self._resid_ema[1],
                self._resid_ema[2],
                h_util[0],
                h_util[1],
                h_util[2],
                att_s,
                rate_s,
                innov_s,
                obs_def,
                cap_unc,
                dir_def,
            ],
            dtype=np.float64,
        )
        # Sanitize any non-finite input into conservative worst-case symptom values
        vec = np.where(np.isfinite(vec), vec, 2.0)

        max_res = float(np.max(self._resid_ema))
        deg_ind = max(dir_def, max_res)
        return SymptomSummary(
            vector=vec,
            torque_residual_xyz_norm=self._resid_ema.copy(),
            max_torque_residual_norm=max_res,
            momentum_utilization_xyz=h_util,
            degradation_indicator=deg_ind,
            authority_deficit_norm=self._deficit_ema,
        )
