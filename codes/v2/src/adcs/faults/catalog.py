"""Deterministic fault injection catalog spanning Scenarios S0–S8 (RESEARCH_PROTOCOL.md §4).

Explicitly separates training, validation, and held-out test scenario regions so
hyperparameter tuning and RL training never leak into held-out evaluation scenarios.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from adcs.actuators.models import ActuatorFaultState, MTQFaultParams, RWFaultParams
from adcs.sensors.suite import SensorFaultParams
from adcs.utils.config import SpacecraftConfig


@dataclass(frozen=True)
class FaultEvent:
    """Single deterministic fault event with onset, optional end, target, and severity."""

    fault_type: str
    start_s: float
    end_s: float | None = None  # None => persistent until episode end
    ramp_s: float = 0.0  # 0 => abrupt; >0 => linear ramp from nominal to severity
    target_index: int = 0  # Actuator/axis index (0, 1, 2)
    severity: float = 0.5  # Meaning documented per fault_type
    extra: dict[str, Any] = field(default_factory=dict)

    def active_fraction(self, time_s: float) -> float:
        """Return active fault fraction in [0, 1] at simulation time `time_s`."""
        if time_s < self.start_s:
            return 0.0
        if self.end_s is not None and time_s >= self.end_s:
            return 0.0
        if self.ramp_s <= 1e-9:
            return 1.0
        return float(np.clip((time_s - self.start_s) / self.ramp_s, 0.0, 1.0))


@dataclass(frozen=True)
class ScenarioSpec:
    """Complete, immutable, reproducible scenario definition."""

    scenario_id: str
    category: str  # S0..S8
    split: str  # "train", "val", or "test"
    description: str
    duration_s: float = 120.0
    initial_attitude_err_deg: float = 20.0
    initial_rate_err_rad_s: float = 0.015
    initial_wheel_momentum_nms: tuple[float, float, float] = (0.0, 0.0, 0.0)
    inertia_scale_xyz: tuple[float, float, float] = (1.0, 1.0, 1.0)
    residual_dipole_am2: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rw_time_constant_scale: float = 1.0
    events: tuple[FaultEvent, ...] = ()


class FaultInjector:
    """Evaluates a sequence of FaultEvents into instantaneous actuator & sensor fault structs."""

    def __init__(self, sc_config: SpacecraftConfig, events: tuple[FaultEvent, ...] = ()) -> None:
        self.sc_cfg = sc_config
        self.events = events

    def evaluate(self, time_s: float) -> tuple[ActuatorFaultState, SensorFaultParams]:
        rw = RWFaultParams.nominal(self.sc_cfg.reaction_wheels)
        mtq = MTQFaultParams.nominal(self.sc_cfg.magnetorquers)
        sens = SensorFaultParams()
        extra_dist = np.zeros(3, dtype=np.float64)

        for ev in self.events:
            frac = ev.active_fraction(time_s)
            if frac <= 0.0:
                continue
            idx = ev.target_index
            ft = ev.fault_type

            if ft == "rw_effectiveness_loss":
                # severity = target remaining effectiveness in [0, 1] (e.g. 0.4 means 60% loss)
                eff = 1.0 - frac * (1.0 - float(ev.severity))
                rw.effectiveness[idx] = min(float(rw.effectiveness[idx]), max(0.0, eff))
            elif ft == "rw_lock":
                rw.locked[idx] = True
                rw.effectiveness[idx] = 0.0
            elif ft == "rw_stuck_torque":
                rw.stuck_torque_nm[idx] = float(ev.severity)
            elif ft == "rw_torque_bias":
                rw.torque_bias_nm[idx] += frac * float(ev.severity)
            elif ft == "rw_friction":
                rw.coulomb_nm[idx] += frac * float(ev.severity)
                rw.viscous_nm_per_rad_s[idx] += frac * float(ev.extra.get("viscous", 0.0))
                rw.stiction_band_nm[idx] += frac * float(ev.extra.get("stiction", 0.0))
            elif ft == "rw_delay":
                rw.delay_steps[idx] = max(rw.delay_steps[idx], int(round(ev.severity)))
            elif ft == "mtq_effectiveness_loss":
                eff = 1.0 - frac * (1.0 - float(ev.severity))
                mtq.effectiveness[idx] = min(float(mtq.effectiveness[idx]), max(0.0, eff))
            elif ft == "mtq_polarity_reversal":
                mtq.polarity[idx] = -1.0
            elif ft == "mtq_dropout":
                mtq.dropout[idx] = True
            elif ft == "disturbance_torque":
                vec = np.asarray(ev.extra.get("torque_nm", [ev.severity, 0.0, 0.0]), dtype=float)
                extra_dist = extra_dist + frac * vec
            elif ft == "gyro_bias":
                sens.gyro_extra_bias_rad_s[idx] += frac * float(ev.severity)
            elif ft == "gyro_drift":
                sens.gyro_drift_rate_rad_s2[idx] += frac * float(ev.severity)
            elif ft == "gyro_noise":
                sens.gyro_noise_mult = max(sens.gyro_noise_mult, 1.0 + frac * (ev.severity - 1.0))
            elif ft == "gyro_dropout":
                sens.gyro_dropout = True
            elif ft == "star_tracker_dropout":
                sens.star_tracker_dropout = True
            elif ft == "star_tracker_bias":
                vec = np.asarray(ev.extra.get("rotvec_rad", [ev.severity, 0.0, 0.0]), dtype=float)
                sens.star_tracker_bias_rotvec_rad = sens.star_tracker_bias_rotvec_rad + frac * vec
            elif ft == "star_tracker_delay":
                sens.star_tracker_delay_steps = max(
                    sens.star_tracker_delay_steps, int(round(ev.severity))
                )
            elif ft == "star_tracker_glitch":
                sens.star_tracker_invalid_glitch = True
            elif ft == "mag_bias":
                sens.mag_bias_t[idx] += frac * float(ev.severity)
            elif ft == "mag_dropout":
                sens.mag_dropout = True
            else:
                raise ValueError(f"Unsupported fault_type: {ft!r}")

        return ActuatorFaultState(rw=rw, mtq=mtq, extra_disturbance_body_nm=extra_dist), sens


def build_default_scenario_catalog() -> dict[str, ScenarioSpec]:
    """Build structured S0–S8 catalog partitioned into disjoint train / val / held-out test splits.

    Held-out test scenarios use fault severities, onset timings, affected axes, and multi-fault
    combinations strictly withheld from training and validation.
    """
    specs: list[ScenarioSpec] = [
        # S0 — Nominal
        ScenarioSpec(
            scenario_id="S0_nominal_val",
            category="S0",
            split="val",
            description="Nominal nadir acquisition & tracking, 20 deg initial offset",
            initial_attitude_err_deg=20.0,
            initial_rate_err_rad_s=0.015,
        ),
        ScenarioSpec(
            scenario_id="S0_nominal_test",
            category="S0",
            split="test",
            description="Held-out nominal larger offset (35 deg)",
            initial_attitude_err_deg=35.0,
            initial_rate_err_rad_s=0.025,
        ),
        # S1 — RW effectiveness degradation (train: 0.4-0.7; test: 0.25 abrupt)
        ScenarioSpec(
            scenario_id="S1_rw0_deg50_train",
            category="S1",
            split="train",
            description="Wheel 0 abrupt 50% effectiveness loss at t=20s",
            events=(
                FaultEvent("rw_effectiveness_loss", start_s=20.0, target_index=0, severity=0.5),
            ),
        ),
        ScenarioSpec(
            scenario_id="S1_rw1_gradual40_val",
            category="S1",
            split="val",
            description="Wheel 1 gradual ramp to 40% effectiveness (t=15..35s)",
            events=(
                FaultEvent(
                    "rw_effectiveness_loss", start_s=15.0, ramp_s=20.0, target_index=1, severity=0.4
                ),
            ),
        ),
        ScenarioSpec(
            scenario_id="S1_rw2_severe25_test",
            category="S1",
            split="test",
            description="Held-out wheel 2 abrupt severe 75% loss (eff=0.25) at t=25s",
            initial_attitude_err_deg=25.0,
            events=(
                FaultEvent("rw_effectiveness_loss", start_s=25.0, target_index=2, severity=0.25),
            ),
        ),
        # S2 — Hard RW failure (lock vs stuck torque modeled distinctly)
        ScenarioSpec(
            scenario_id="S2_rw0_lock_val",
            category="S2",
            split="val",
            description="Wheel 0 hard mechanical lock at t=20s (MTQ assist required on x)",
            events=(FaultEvent("rw_lock", start_s=20.0, target_index=0, severity=0.0),),
        ),
        ScenarioSpec(
            scenario_id="S2_rw1_stuck_torque_test",
            category="S2",
            split="test",
            description="Held-out wheel 1 stuck torque (+0.04 Nm) at t=25s",
            events=(FaultEvent("rw_stuck_torque", start_s=25.0, target_index=1, severity=0.04),),
        ),
        # S3 — Wheel saturation / momentum constraint
        ScenarioSpec(
            scenario_id="S3_momentum_sat_val",
            category="S3",
            split="val",
            description="High initial wheel momentum near limit + persistent disturbance",
            initial_wheel_momentum_nms=(5.4, -4.5, 2.0),
            events=(
                FaultEvent(
                    "disturbance_torque",
                    start_s=10.0,
                    severity=0.015,
                    extra={"torque_nm": [0.015, -0.01, 0.005]},
                ),
            ),
        ),
        ScenarioSpec(
            scenario_id="S3_momentum_sat_test",
            category="S3",
            split="test",
            description="Held-out severe momentum offset + larger disturbance",
            initial_attitude_err_deg=25.0,
            initial_wheel_momentum_nms=(5.7, 5.2, -4.0),
            events=(
                FaultEvent(
                    "disturbance_torque",
                    start_s=12.0,
                    severity=0.02,
                    extra={"torque_nm": [0.02, 0.012, -0.008]},
                ),
            ),
        ),
        # S4 — Actuator bias & friction / stiction
        ScenarioSpec(
            scenario_id="S4_rw_bias_friction_train",
            category="S4",
            split="train",
            description="Wheel 0 torque bias (+0.02 Nm) + Coulomb friction (0.015 Nm)",
            events=(
                FaultEvent("rw_torque_bias", start_s=15.0, target_index=0, severity=0.02),
                FaultEvent(
                    "rw_friction",
                    start_s=15.0,
                    target_index=0,
                    severity=0.015,
                    extra={"viscous": 5e-5, "stiction": 0.005},
                ),
            ),
        ),
        ScenarioSpec(
            scenario_id="S4_rw_bias_stiction_test",
            category="S4",
            split="test",
            description="Held-out multi-axis torque bias + stiction on wheels 1 & 2",
            events=(
                FaultEvent("rw_torque_bias", start_s=18.0, target_index=1, severity=-0.03),
                FaultEvent(
                    "rw_friction",
                    start_s=18.0,
                    target_index=2,
                    severity=0.025,
                    extra={"viscous": 8e-5, "stiction": 0.01},
                ),
            ),
        ),
        # S5 — MTQ degradation & field geometry
        ScenarioSpec(
            scenario_id="S5_mtq_degraded_test",
            category="S5",
            split="test",
            description="Held-out MTQ axis 0 dropout + high initial wheel momentum",
            initial_wheel_momentum_nms=(4.5, -3.5, 3.0),
            events=(
                FaultEvent("mtq_dropout", start_s=10.0, target_index=0, severity=0.0),
                FaultEvent("mtq_effectiveness_loss", start_s=10.0, target_index=1, severity=0.4),
            ),
        ),
        # S6 — Sensor faults (ST dropout, gyro bias, ST glitch)
        ScenarioSpec(
            scenario_id="S6_st_dropout_val",
            category="S6",
            split="val",
            description="Star tracker dropout for 25s (t=20..45s) + gyro bias step",
            events=(
                FaultEvent("star_tracker_dropout", start_s=20.0, end_s=45.0, severity=1.0),
                FaultEvent("gyro_bias", start_s=20.0, target_index=1, severity=0.003),
            ),
        ),
        ScenarioSpec(
            scenario_id="S6_sensor_fault_test",
            category="S6",
            split="test",
            description="Held-out ST dropout (35s) + ST glitch + gyro noise spike",
            events=(
                FaultEvent("star_tracker_glitch", start_s=15.0, end_s=20.0, severity=1.0),
                FaultEvent("star_tracker_dropout", start_s=25.0, end_s=60.0, severity=1.0),
                FaultEvent("gyro_noise", start_s=25.0, end_s=60.0, severity=5.0),
            ),
        ),
        # S7 — Model/environment mismatch
        ScenarioSpec(
            scenario_id="S7_inertia_mismatch_val",
            category="S7",
            split="val",
            description="Asymmetric inertia mismatch (+20%, -15%, +25%) + residual dipole + RW lag",
            inertia_scale_xyz=(1.20, 0.85, 1.25),
            residual_dipole_am2=(0.08, -0.06, 0.05),
            rw_time_constant_scale=1.5,
        ),
        ScenarioSpec(
            scenario_id="S7_inertia_mismatch_test",
            category="S7",
            split="test",
            description="Held-out severe inertia mismatch (+25%, -25%, +25%) + lag 2x + dipole",
            initial_attitude_err_deg=30.0,
            inertia_scale_xyz=(1.25, 0.75, 1.25),
            residual_dipole_am2=(0.12, 0.10, -0.08),
            rw_time_constant_scale=2.0,
        ),
        # S8 — Combined & withheld unknown faults
        ScenarioSpec(
            scenario_id="S8_combined_rw_sensor_test",
            category="S8",
            split="test",
            description=(
                "Held-out combined: dual-RW degradation + torque bias + ST dropout + inertia"
            ),
            initial_attitude_err_deg=25.0,
            inertia_scale_xyz=(1.18, 0.88, 1.15),
            events=(
                FaultEvent("rw_effectiveness_loss", start_s=15.0, target_index=0, severity=0.35),
                FaultEvent("rw_effectiveness_loss", start_s=30.0, target_index=1, severity=0.50),
                FaultEvent("rw_torque_bias", start_s=20.0, target_index=2, severity=0.02),
                FaultEvent("star_tracker_dropout", start_s=35.0, end_s=55.0, severity=1.0),
            ),
        ),
    ]
    return {s.scenario_id: s for s in specs}
