"""B6 — Onboard-only observation builder and lightweight residual MLP policy.

Strict separation: observations contain ONLY onboard-estimated state, normalized symptoms,
capability summaries, and previous commands—never ground-truth attitude, rates, or fault labels.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import numpy as np

from adcs.control.reference import AttitudeError
from adcs.control.supervisor.symptoms import SymptomSummary
from adcs.interfaces.types import (
    ActuatorCapabilityState,
    EstimatorOutput,
    FloatArray,
    SensorMeasurement,
)
from adcs.utils.config import SpacecraftConfig

OBS_DIM = 30
ACTION_DIM = 3


@runtime_checkable
class ResidualPolicyProtocol(Protocol):
    """Inference interface for residual policies outputting normalized actions in [-1, 1]^3."""

    def predict(self, obs: FloatArray, *, deterministic: bool = True) -> FloatArray: ...


class ObservationBuilder:
    """Constructs the documented 30-dim onboard observation vector z for B6."""

    def __init__(
        self,
        sc_config: SpacecraftConfig,
        action_scale_nm: float | None = None,
    ) -> None:
        self.tau_lim = sc_config.reaction_wheels.torque_limit_nominal_nm
        self.h_lim = sc_config.reaction_wheels.effective_momentum_limit_nms
        self.rotor_j = sc_config.reaction_wheels.rotor_inertia_kg_m2
        self.a_rw = sc_config.reaction_wheels.axis_matrix_body.copy()
        self.action_scale_nm = (
            0.4 * self.tau_lim if action_scale_nm is None else float(action_scale_nm)
        )
        # Per-axis max wheel momentum projection for arbitrary N-wheel geometries
        self._h_axis_scale = np.maximum(
            np.sum(np.abs(self.a_rw), axis=1) * self.h_lim, 1e-6
        )

    def build(
        self,
        *,
        att_err: AttitudeError,
        tau_base_nm: FloatArray,
        prev_tau_rl_gated_nm: FloatArray,
        estimator_out: EstimatorOutput,
        capability: ActuatorCapabilityState,
        symptoms: SymptomSummary,
        measurement: SensorMeasurement,
    ) -> FloatArray:
        rotvec_n = np.clip(att_err.rotvec_rad / 0.5, -3.0, 3.0)
        rate_n = np.clip(att_err.omega_err_body_rad_s / 0.05, -3.0, 3.0)
        tau_b_n = np.clip(tau_base_nm / max(self.tau_lim, 1e-6), -3.0, 3.0)
        prev_rl_n = np.clip(prev_tau_rl_gated_nm / max(self.action_scale_nm, 1e-6), -2.0, 2.0)

        # Project arbitrary N-wheel momentum into 3 body axes for geometry generality
        h_est = self.rotor_j * np.asarray(measurement.rw_speed_rad_s, dtype=np.float64)
        h_body = self.a_rw @ h_est
        h_n = np.clip(h_body / self._h_axis_scale, -1.2, 1.2)

        b_vec = measurement.mag_body_t if measurement.mag_valid else np.zeros(3, dtype=np.float64)
        b_n = np.clip(b_vec / 5.0e-5, -2.0, 2.0)

        margins = (
            np.clip(capability.directional_margin_xyz, 0.0, 1.0)
            if capability.valid
            else np.zeros(3, dtype=np.float64)
        )
        # Project per-wheel effectiveness into 3 body axes (works for 3, 4, or N wheels)
        if capability.valid and len(capability.wheels) > 0:
            w_axes = np.column_stack([w.axis_body for w in capability.wheels])
            w_effs = np.array([w.effectiveness_nom for w in capability.wheels], dtype=np.float64)
            denom = np.maximum(np.sum(np.abs(w_axes), axis=1), 1e-6)
            g_hat = np.clip((np.abs(w_axes) @ w_effs) / denom, 0.0, 1.25)
        else:
            g_hat = np.zeros(3, dtype=np.float64)

        gamma_obs = float(np.clip(estimator_out.gamma_obs, 0.0, 1.0))
        cap_conf = float(np.clip(capability.confidence, 0.0, 1.0)) if capability.valid else 0.0
        resid_n = np.clip(symptoms.torque_residual_xyz_norm, 0.0, 2.0)
        att_std_rms = float(np.sqrt(np.mean(np.square(estimator_out.attitude_std_rad))))
        att_std_n = float(np.clip(att_std_rms / 0.02, 0.0, 3.0))

        obs = np.concatenate(
            [
                rotvec_n,
                rate_n,
                tau_b_n,
                prev_rl_n,
                h_n,
                b_n,
                margins,
                g_hat,
                np.array([gamma_obs, cap_conf], dtype=np.float64),
                resid_n,
                np.array([att_std_n], dtype=np.float64),
            ]
        ).astype(np.float64)
        obs = np.where(np.isfinite(obs), obs, 0.0)
        assert obs.shape == (OBS_DIM,)
        return obs


class ZeroResidualPolicy:
    """Deterministic zero-action policy for testing pipeline equivalence with classical control."""

    def predict(self, obs: FloatArray, *, deterministic: bool = True) -> FloatArray:
        del obs, deterministic
        return np.zeros(ACTION_DIM, dtype=np.float64)


@dataclass
class NumpyMLPWeights:
    """Pure-NumPy weights for ultra-fast deterministic CPU inference & C99 exportability."""

    w1: FloatArray
    b1: FloatArray
    w2: FloatArray
    b2: FloatArray
    w_mean: FloatArray
    b_mean: FloatArray

    def forward_mean(self, obs: FloatArray) -> FloatArray:
        h1 = np.maximum(0.0, obs @ self.w1.T + self.b1)
        h2 = np.maximum(0.0, h1 @ self.w2.T + self.b2)
        return np.tanh(h2 @ self.w_mean.T + self.b_mean)


class TorchMLPResidualPolicy:
    """Lightweight MLP residual policy with pure-NumPy deterministic deployment path."""

    def __init__(
        self,
        weights: NumpyMLPWeights,
        *,
        action_scale_nm: float = 0.06,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.weights = weights
        self.action_scale_nm = float(action_scale_nm)
        self.metadata = {} if metadata is None else dict(metadata)

    def predict(self, obs: FloatArray, *, deterministic: bool = True) -> FloatArray:
        del deterministic
        x = np.asarray(obs, dtype=np.float64)
        if x.shape != (OBS_DIM,) or not np.all(np.isfinite(x)):
            return np.full(ACTION_DIM, np.nan, dtype=np.float64)
        return np.clip(self.weights.forward_mean(x), -1.0, 1.0)

    def save(self, checkpoint_dir: str | Path) -> str:
        """Save weights and JSON metadata; returns SHA-256 hash of weights."""
        out_dir = Path(checkpoint_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        npz_path = out_dir / "policy_weights.npz"
        np.savez(
            npz_path,
            w1=self.weights.w1,
            b1=self.weights.b1,
            w2=self.weights.w2,
            b2=self.weights.b2,
            w_mean=self.weights.w_mean,
            b_mean=self.weights.b_mean,
        )
        hasher = hashlib.sha256()
        for key in ("w1", "b1", "w2", "b2", "w_mean", "b_mean"):
            arr = np.ascontiguousarray(getattr(self.weights, key), dtype=np.float64)
            hasher.update(arr.tobytes())
        weight_hash = hasher.hexdigest()
        meta = {
            **self.metadata,
            "obs_dim": OBS_DIM,
            "action_dim": ACTION_DIM,
            "action_scale_nm": self.action_scale_nm,
            "weights_sha256": weight_hash,
        }
        (out_dir / "policy_meta.json").write_text(
            json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8"
        )
        return weight_hash

    @classmethod
    def load(cls, checkpoint_dir: str | Path) -> TorchMLPResidualPolicy:
        in_dir = Path(checkpoint_dir)
        data = np.load(in_dir / "policy_weights.npz")
        meta = json.loads((in_dir / "policy_meta.json").read_text(encoding="utf-8"))
        weights = NumpyMLPWeights(
            w1=data["w1"].astype(np.float64),
            b1=data["b1"].astype(np.float64),
            w2=data["w2"].astype(np.float64),
            b2=data["b2"].astype(np.float64),
            w_mean=data["w_mean"].astype(np.float64),
            b_mean=data["b_mean"].astype(np.float64),
        )
        return cls(
            weights,
            action_scale_nm=float(meta.get("action_scale_nm", 0.06)),
            metadata=meta,
        )
