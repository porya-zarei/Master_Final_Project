# Phase 5 Report — Sensors, Estimation, Fault Injection, and Capability

**Phase:** 5 — Sensors, Estimation, Fault Injection, and Capability  
**Status:** `COMPLETE`  
**Date:** 2026-11-21  

---

## 1. Implemented Changes

- `src/adcs/sensors/suite.py` & `configs/sensors.yaml`: `SensorSuite` modeling 3-axis gyroscope (turn-on bias, bias random walk, scale factor, drift, white noise, dropout), star tracker (attitude noise, delay queue, update divider, bias, dropout, invalid glitch), magnetometer (noise, bias, dropout), and per-wheel tachometers.
- `src/adcs/estimation/mekf.py` (Block **B1**): 6-state error-state `MultiplicativeEKF` (attitude error + gyro bias) with Joseph-form covariance update, chi-squared Mahalanobis outlier rejection (`threshold = 25.0`), and documented monotonic observability confidence `gamma_obs = f_cov * f_age * f_innov * f_sens` in `[0, 1]`.
- `src/adcs/faults/catalog.py`: deterministic `FaultEvent`, `ScenarioSpec`, `FaultInjector`, and `build_default_scenario_catalog()` covering **S0–S8** across disjoint `train`, `val`, and held-out `test` regions, with distinct physical models for RW gain degradation, hard wheel lock, stuck torque, momentum saturation, Coulomb/viscous/stiction friction, MTQ dropout/degradation, sensor dropouts/glitches, inertia/lag mismatch, and combined faults.
- `src/adcs/estimation/capability.py` (Block **B3**):
  - `OracleCapabilityEstimator` (`is_oracle=True`) for diagnostic arms A1/A6.
  - `OnlineCapabilityEstimator` (`is_oracle=False`) using onboard-only excitation-gated 2-parameter RLS/KF (wheel effectiveness `g_i` and torque bias `b_i`) from commanded torque vs. tachometer acceleration, plus `k_sigma = 2.0` conservative lower bounds, momentum-wall headroom, and field-dependent MTQ torque vectors.
  - `ams_support_function` computing $h_{\mathcal{T}}(v)$ and bidirectional conservative directional margins $m_{dir}(e_k)$.
- `tests/fault_injection/test_phase5_estimation_faults_capability.py`: Gates C2 & C3 verification tests.

---

## 2. Verification Evidence (Gates C2 & C3)

- **MEKF & `gamma_obs`:** Converges from 2° initial offset to `< 0.25 deg` attitude error and `< 5e-4 rad/s` gyro-bias error (`gamma_obs > 0.85`), rejects star-tracker invalid glitch via Mahalanobis gate without corrupting attitude, monotonically decreases `gamma_obs` during star-tracker dropout (`< 0.35` after 10 s), and outputs `valid=False, gamma_obs=0.0` under complete sensor blackout.
- **Fault catalog:** Verified ramp vs. abrupt onset, distinct lock vs. stuck-torque behavior, and strict train/val/test split coverage over S0–S8.
- **Online capability & AMS (Gate C2):** Onboard RLS detects abrupt 60% wheel-0 effectiveness loss (`true=0.4`) within `0.12` while keeping healthy wheels `> 0.85` and strictly preserving conservative bounds (`h_online_cons <= h_oracle`) verified against 5,000 Monte Carlo sampled achievable torques across arbitrary directions.

---

## 3. Verification Commands & Outcomes

- `python -m ruff check --no-cache src tests` → `All checks passed!`
- `python -m pytest -v -p no:cacheprovider tests/fault_injection/test_phase5_estimation_faults_capability.py` → **3 passed, 0 failed** (cumulative: **28 passed, 0 failed**).

---

## 4. Next Phase & Prerequisites

Proceed to **Phase 6 — Strong Classical Fault-Tolerant Baselines** (Arms A0, A1 oracle, A2 LQR+ESO/DOB, A3 strongest classical baseline with capability-aware allocation + gain scheduling, plus shared metric evaluator and paired scenario runner).
