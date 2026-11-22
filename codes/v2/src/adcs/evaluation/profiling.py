"""Phase 10 CPU inference, control-cycle latency, and memory profiling (Hypothesis H5)."""

from __future__ import annotations

import time
import tracemalloc
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from adcs.control.classical import StrongClassicalController
from adcs.control.reference import NadirReferenceGenerator
from adcs.control.residual_rl import CCRController, CCRControllerConfig, ResidualPolicyProtocol
from adcs.estimation import MultiplicativeEKF, OnlineCapabilityEstimator
from adcs.sensors import SensorSuite
from adcs.simulation.fast import FastSimulatorBackend
from adcs.utils.config import SpacecraftConfig


@dataclass(frozen=True)
class ComponentLatency:
    """Per-call CPU latency distribution (ms) for a control-stack component."""

    component: str
    n_calls: int
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _summarize(name: str, samples_ms: list[float]) -> ComponentLatency:
    arr = np.asarray(samples_ms, dtype=np.float64)
    return ComponentLatency(
        component=name,
        n_calls=len(arr),
        mean_ms=float(np.mean(arr)),
        p50_ms=float(np.percentile(arr, 50)),
        p95_ms=float(np.percentile(arr, 95)),
        p99_ms=float(np.percentile(arr, 99)),
        max_ms=float(np.max(arr)),
    )


def profile_control_stack_cpu(
    sc_config: SpacecraftConfig,
    policy: ResidualPolicyProtocol,
    *,
    n_steps: int = 500,
) -> dict[str, Any]:
    """Benchmark CPU timing and peak memory allocation for every component in the 5 Hz loop."""
    sim = FastSimulatorBackend(sc_config)
    sensors = SensorSuite(n_rw=sc_config.reaction_wheels.count)
    ref_gen = NadirReferenceGenerator()
    mekf = MultiplicativeEKF()
    cap_est = OnlineCapabilityEstimator(sc_config)
    ccr = CCRController(sc_config, policy=policy, config=CCRControllerConfig(name="A7_profile"))
    a3 = StrongClassicalController(sc_config)

    truth = sim.reset()
    sensors.reset(seed=0, q_ib_init=truth.q_ib)
    mekf.reset(q_ib_init=truth.q_ib, omega_init=truth.omega_body_rad_s)
    cap_est.reset()
    ccr.reset()
    a3.reset()
    dt = sc_config.simulation.control_period_s

    t_sim: list[float] = []
    t_mekf: list[float] = []
    t_cap: list[float] = []
    t_a3: list[float] = []
    t_ccr: list[float] = []
    t_policy: list[float] = []
    t_total_onboard: list[float] = []

    last_cmd = None
    dummy_obs = np.zeros(30, dtype=np.float64)

    tracemalloc.start()
    for _ in range(n_steps):
        meas = sensors.measure(truth, dt_s=dt)
        ref = ref_gen.compute(truth.time_s, truth.position_eci_m, truth.velocity_eci_m_s)

        t0 = time.perf_counter()
        est_out = mekf.update(meas, dt_s=dt)
        t1 = time.perf_counter()
        cap_out = cap_est.estimate(
            time_s=truth.time_s,
            measurement=meas,
            last_command=last_cmd,
            b_field_body_t=meas.mag_body_t,
            dt_s=dt,
        )
        t2 = time.perf_counter()
        ctrl_out = ccr.compute(
            estimator_out=est_out,
            reference=ref,
            capability=cap_out,
            measurement=meas,
            dt_s=dt,
        )
        t3 = time.perf_counter()

        t_a3_0 = time.perf_counter()
        a3.compute(
            estimator_out=est_out,
            reference=ref,
            capability=cap_out,
            measurement=meas,
            dt_s=dt,
        )
        t_a3_1 = time.perf_counter()

        t_pol_0 = time.perf_counter()
        policy.predict(dummy_obs, deterministic=True)
        t_pol_1 = time.perf_counter()

        t_sim_0 = time.perf_counter()
        truth = sim.step(
            ctrl_out.command.rw_torque_cmd_nm,
            ctrl_out.command.mtq_dipole_cmd_am2,
            dt_s=dt,
        ).truth
        t_sim_1 = time.perf_counter()

        last_cmd = ctrl_out.command
        t_mekf.append((t1 - t0) * 1000.0)
        t_cap.append((t2 - t1) * 1000.0)
        t_ccr.append((t3 - t2) * 1000.0)
        t_total_onboard.append((t3 - t0) * 1000.0)
        t_a3.append((t_a3_1 - t_a3_0) * 1000.0)
        t_policy.append((t_pol_1 - t_pol_0) * 1000.0)
        t_sim.append((t_sim_1 - t_sim_0) * 1000.0)

    current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    budget_ms = dt * 1000.0
    total_summary = _summarize("onboard_total_B1_B3_CCR_v2", t_total_onboard)
    return {
        "control_period_budget_ms": budget_ms,
        "budget_utilization_pct_mean": 100.0 * total_summary.mean_ms / budget_ms,
        "budget_utilization_pct_p99": 100.0 * total_summary.p99_ms / budget_ms,
        "peak_python_traced_memory_kb": peak_bytes / 1024.0,
        "current_python_traced_memory_kb": current_bytes / 1024.0,
        "mlp_param_count": 30 * 64 + 64 + 64 * 64 + 64 + 64 * 3 + 3,
        "mlp_weights_float32_kb": (30 * 64 + 64 + 64 * 64 + 64 + 64 * 3 + 3) * 4 / 1024.0,
        "components": [
            _summarize("B1_MEKF", t_mekf).to_dict(),
            _summarize("B3_OnlineCapability", t_cap).to_dict(),
            _summarize("B6_PolicyInference_NumPy", t_policy).to_dict(),
            _summarize("CCR_v2_Controller_Step", t_ccr).to_dict(),
            _summarize("A3_StrongClassical_Step", t_a3).to_dict(),
            total_summary.to_dict(),
            _summarize("FastSimulator_RK4_Step", t_sim).to_dict(),
        ],
    }
