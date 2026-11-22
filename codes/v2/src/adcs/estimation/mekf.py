"""Multiplicative Extended Kalman Filter (MEKF) with operational observability confidence (B1).

State:
- Reference attitude quaternion q_ib_est (unit, scalar-first)
- Gyro bias estimate b_g_est (rad/s)
- 6x6 error-state covariance P over [delta_theta (3), delta_b_g (3)]

Observability confidence gamma_obs in [0, 1] is computed deterministically from measurable
covariance, measurement freshness/age, innovation consistency, and sensor validity flags.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from adcs.interfaces.types import EstimatorOutput, FloatArray, SensorMeasurement
from adcs.utils.quaternion import (
    quat_error,
    quat_error_rotvec,
    quat_from_rotvec,
    quat_multiply,
    quat_normalize,
    skew,
)


@dataclass(frozen=True)
class MEKFConfig:
    """MEKF process/measurement noise covariances and gamma_obs calibration thresholds."""

    gyro_noise_std_rad_s: float = 3.0e-4
    gyro_bias_rw_std_rad_s_sqrt_s: float = 3.0e-5
    star_tracker_noise_std_rad: float = 6.0e-4
    init_att_std_rad: float = 0.02
    init_bias_std_rad_s: float = 2.0e-3
    mahalanobis_reject_threshold: float = 25.0  # Chi^2(3) > 25 is p < 1.5e-5 outlier
    # gamma_obs operational calibration thresholds (strictly monotonic)
    obs_att_std_nom_rad: float = 0.003  # ~0.17 deg nominal std -> f_cov = 1
    obs_att_std_scale_rad: float = 0.025  # decay scale (~1.4 deg)
    obs_age_nom_s: float = 0.6  # age <= 0.6 s -> f_age = 1
    obs_age_scale_s: float = 6.0  # decay scale during ST dropout
    obs_innov_nom: float = 3.5  # nominal Mahalanobis norm
    obs_innov_scale: float = 8.0  # decay scale on inconsistent measurements
    obs_innov_ema_alpha: float = 0.25  # smoothing for innovation metric
    max_blackout_s: float = 120.0  # hard validity timeout if sensors completely dead


class MultiplicativeEKF:
    """6-state Multiplicative EKF for spacecraft attitude and gyro-bias estimation."""

    def __init__(self, config: MEKFConfig | None = None) -> None:
        self.cfg = MEKFConfig() if config is None else config
        self._q_est = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
        self._b_est = np.zeros(3, dtype=np.float64)
        self._omega_est = np.zeros(3, dtype=np.float64)
        self._p = np.eye(6, dtype=np.float64)
        self._innov_ema = 0.0
        self._last_st_update_t = 0.0
        self._last_gyro_valid_t = 0.0
        self._consecutive_rejects = 0
        self._prev_st_q: FloatArray | None = None
        self._consistent_reacq_count = 0

    def reset(
        self,
        q_ib_init: FloatArray,
        omega_init: FloatArray | None = None,
        time_s: float = 0.0,
    ) -> EstimatorOutput:
        self._q_est = quat_normalize(q_ib_init)
        self._b_est = np.zeros(3, dtype=np.float64)
        self._omega_est = (
            np.zeros(3, dtype=np.float64)
            if omega_init is None
            else np.asarray(omega_init, dtype=np.float64).copy()
        )
        self._p = np.diag(
            [self.cfg.init_att_std_rad**2] * 3 + [self.cfg.init_bias_std_rad_s**2] * 3
        ).astype(np.float64)
        self._innov_ema = 0.0
        self._last_st_update_t = float(time_s)
        self._last_gyro_valid_t = float(time_s)
        self._consecutive_rejects = 0
        self._prev_st_q = self._q_est.copy()
        self._consistent_reacq_count = 0
        return self._make_output(
            time_s=float(time_s),
            sensor_status={"gyro": True, "star_tracker": True, "magnetometer": True},
            data_age_s=0.0,
            valid=True,
            innov_norm=0.0,
            rejected=False,
        )

    def _compute_gamma_obs(
        self,
        att_std_rms: float,
        data_age_s: float,
        innov_ema: float,
        gyro_valid: bool,
        st_valid_accepted: bool,
    ) -> float:
        if not (
            np.isfinite(att_std_rms) and np.isfinite(data_age_s) and np.isfinite(innov_ema)
        ):
            return 0.0
        if not gyro_valid and not st_valid_accepted:
            return 0.0
        f_cov = float(
            np.exp(
                -max(0.0, att_std_rms - self.cfg.obs_att_std_nom_rad)
                / self.cfg.obs_att_std_scale_rad
            )
        )
        f_age = float(
            np.exp(-max(0.0, data_age_s - self.cfg.obs_age_nom_s) / self.cfg.obs_age_scale_s)
        )
        f_innov = float(
            np.exp(-max(0.0, innov_ema - self.cfg.obs_innov_nom) / self.cfg.obs_innov_scale)
        )
        if gyro_valid and st_valid_accepted:
            f_sens = 1.0
        elif gyro_valid:
            # Dead reckoning on gyro alone: cap immediately below full observability
            f_sens = 0.65
        else:
            # Star tracker only (no gyro): degraded rate observability
            f_sens = 0.35
        return float(np.clip(f_cov * f_age * f_innov * f_sens, 0.0, 1.0))

    def _make_output(
        self,
        *,
        time_s: float,
        sensor_status: dict[str, bool],
        data_age_s: float,
        valid: bool,
        innov_norm: float,
        rejected: bool,
    ) -> EstimatorOutput:
        p_att = self._p[:3, :3].copy()
        p_bias = self._p[3:, 3:].copy()
        r_gyro = (self.cfg.gyro_noise_std_rad_s**2) * np.eye(3, dtype=np.float64)
        p_rate = p_bias + r_gyro
        att_std = np.sqrt(np.maximum(np.diag(p_att), 0.0))
        rate_std = np.sqrt(np.maximum(np.diag(p_rate), 0.0))
        att_std_rms = float(np.sqrt(np.mean(att_std**2)))
        gamma = (
            self._compute_gamma_obs(
                att_std_rms,
                data_age_s,
                self._innov_ema,
                gyro_valid=sensor_status["gyro"],
                st_valid_accepted=sensor_status["star_tracker"] and not rejected,
            )
            if valid
            else 0.0
        )
        return EstimatorOutput(
            time_s=time_s,
            q_ib_est=self._q_est.copy(),
            omega_body_est_rad_s=self._omega_est.copy(),
            gyro_bias_est_rad_s=self._b_est.copy(),
            attitude_cov_rad2=p_att,
            rate_cov_rad2_s2=p_rate,
            attitude_std_rad=att_std,
            rate_std_rad_s=rate_std,
            gamma_obs=gamma,
            sensor_status=sensor_status,
            data_age_s=data_age_s,
            valid=valid,
            innovation_norm=innov_norm,
            diagnostics={
                "innov_ema": self._innov_ema,
                "st_outlier_rejected": rejected,
                "consecutive_rejects": self._consecutive_rejects,
                "att_std_rms_rad": att_std_rms,
            },
        )

    def update(
        self,
        measurement: SensorMeasurement,
        dt_s: float,
        applied_rw_torque_nm: FloatArray | None = None,
    ) -> EstimatorOutput:
        del applied_rw_torque_nm
        t = float(measurement.time_s)
        dt = float(dt_s)
        gyro_ok = bool(measurement.gyro_valid and np.all(np.isfinite(measurement.gyro_rad_s)))
        st_ok = bool(
            measurement.star_tracker_valid
            and np.all(np.isfinite(measurement.star_tracker_q_ib))
            and float(np.linalg.norm(measurement.star_tracker_q_ib)) > 1e-6
        )
        mag_ok = bool(measurement.mag_valid and np.all(np.isfinite(measurement.mag_body_t)))

        # 1. Time Propagation
        if gyro_ok:
            omega_hat = measurement.gyro_rad_s - self._b_est
            self._omega_est = omega_hat.copy()
            self._last_gyro_valid_t = t
            # Propagate attitude with exact exponential map
            self._q_est = quat_normalize(
                quat_multiply(self._q_est, quat_from_rotvec(omega_hat * dt))
            )
            # State transition matrix Phi for [dtheta, db_g]
            f_mat = np.zeros((6, 6), dtype=np.float64)
            f_mat[:3, :3] = -skew(omega_hat)
            f_mat[:3, 3:] = -np.eye(3, dtype=np.float64)
            phi = np.eye(6, dtype=np.float64) + f_mat * dt + 0.5 * (f_mat @ f_mat) * (dt * dt)

            sig_v2 = self.cfg.gyro_noise_std_rad_s**2
            sig_u2 = self.cfg.gyro_bias_rw_std_rad_s_sqrt_s**2
            q_d = np.zeros((6, 6), dtype=np.float64)
            q_d[:3, :3] = (sig_v2 * (dt * dt) + (1.0 / 3.0) * sig_u2 * (dt**3)) * np.eye(3)
            q_d[:3, 3:] = -0.5 * sig_u2 * (dt**2) * np.eye(3)
            q_d[3:, :3] = -0.5 * sig_u2 * (dt**2) * np.eye(3)
            q_d[3:, 3:] = (sig_u2 * dt) * np.eye(3)
            self._p = phi @ self._p @ phi.T + q_d
        else:
            # No valid gyro: coast at previous rate, inflate covariance conservatively
            self._q_est = quat_normalize(
                quat_multiply(self._q_est, quat_from_rotvec(self._omega_est * dt))
            )
            self._p[:3, :3] += (0.05 * dt) ** 2 * np.eye(3)
            self._p[3:, 3:] += (0.01 * dt) ** 2 * np.eye(3)

        # 2. Star-Tracker Measurement Update with Chi^2 Innovation Gate
        innov_norm = 0.0
        rejected = False
        if st_ok:
            q_st = quat_normalize(measurement.star_tracker_q_ib)
            q_innov = quat_error(self._q_est, q_st)
            y = quat_error_rotvec(q_innov)

            h_mat = np.zeros((3, 6), dtype=np.float64)
            h_mat[:, :3] = np.eye(3, dtype=np.float64)
            # Inflate measurement variance slightly with measurement age
            age_pen = 1.0 + 2.0 * max(0.0, measurement.star_tracker_age_s)
            r_mat = (self.cfg.star_tracker_noise_std_rad**2 * age_pen) * np.eye(3)
            s_mat = h_mat @ self._p @ h_mat.T + r_mat
            try:
                s_inv_y = np.linalg.solve(s_mat, y)
                maha2 = float(y @ s_inv_y)
                innov_norm = float(np.sqrt(max(0.0, maha2)))
            except np.linalg.LinAlgError:
                maha2 = float("inf")
                innov_norm = float("inf")

            a_ema = self.cfg.obs_innov_ema_alpha
            self._innov_ema = (1.0 - a_ema) * self._innov_ema + a_ema * min(innov_norm, 50.0)

            # Kinematic consistency check on consecutive ST frames to distinguish genuine
            # post-dropout re-acquisition (drifted q_hat vs healthy ST) from wild glitches.
            st_kinematically_consistent = False
            if self._prev_st_q is not None:
                q_pred_st = quat_normalize(
                    quat_multiply(self._prev_st_q, quat_from_rotvec(self._omega_est * dt))
                )
                delta_st = float(np.linalg.norm(quat_error_rotvec(quat_error(q_pred_st, q_st))))
                st_kinematically_consistent = delta_st < 0.04
            self._prev_st_q = q_st.copy()

            innov_angle_rad = float(np.linalg.norm(y))
            stale_outage = (t - self._last_st_update_t) > 2.0
            if maha2 > self.cfg.mahalanobis_reject_threshold and st_kinematically_consistent:
                if stale_outage and innov_angle_rad < 0.45:
                    self._consistent_reacq_count += 1
                else:
                    self._consistent_reacq_count = 0
            else:
                self._consistent_reacq_count = 0

            reacquire = self._consistent_reacq_count >= 3
            if reacquire:
                # Re-acquire after dropout/step-bias: zero stale cross-covariances,
                # inflate P diagonals conservatively, and re-lock
                self._p[:3, 3:] = 0.0
                self._p[3:, :3] = 0.0
                self._p[:3, :3] += (max(innov_angle_rad, 0.05) ** 2) * np.eye(3)
                self._p[3:, 3:] += (0.005**2) * np.eye(3)
                s_mat = h_mat @ self._p @ h_mat.T + r_mat

            # Accept update if within chi-squared gate, re-acquiring, or gyro is dead
            if maha2 <= self.cfg.mahalanobis_reject_threshold or reacquire or not gyro_ok:
                k_gain = self._p @ h_mat.T @ np.linalg.inv(s_mat)
                dx = k_gain @ y
                self._q_est = quat_normalize(
                    quat_multiply(self._q_est, quat_from_rotvec(dx[:3]))
                )
                self._b_est = self._b_est + dx[3:]
                # Joseph-form covariance update for numerical SPD preservation
                ikh = np.eye(6, dtype=np.float64) - k_gain @ h_mat
                self._p = ikh @ self._p @ ikh.T + k_gain @ r_mat @ k_gain.T
                self._p = 0.5 * (self._p + self._p.T)
                self._last_st_update_t = t - max(0.0, measurement.star_tracker_age_s)
                self._consecutive_rejects = 0
                self._consistent_reacq_count = 0
                if not gyro_ok:
                    # Finite-difference rough rate if gyro dead
                    self._omega_est = 0.8 * self._omega_est + 0.2 * (y / max(dt, 1e-3))
            else:
                rejected = True
                self._consecutive_rejects += 1
        else:
            # Decay innovation EMA very slowly during dropout
            self._innov_ema = max(self._innov_ema, 0.0)

        data_age_s = max(0.0, t - self._last_st_update_t)
        blackout = (not gyro_ok and not st_ok) or (
            data_age_s > self.cfg.max_blackout_s and not gyro_ok
        )
        valid = bool(
            not blackout
            and np.all(np.isfinite(self._q_est))
            and np.all(np.isfinite(self._omega_est))
            and np.all(np.isfinite(self._p))
        )

        return self._make_output(
            time_s=t,
            sensor_status={"gyro": gyro_ok, "star_tracker": st_ok, "magnetometer": mag_ok},
            data_age_s=data_age_s,
            valid=valid,
            innov_norm=innov_norm,
            rejected=rejected,
        )
