# Phase 6 Report — Strong Classical Fault-Tolerant Baselines

**Phase:** 6 — Strong Classical Fault-Tolerant Baselines  
**Status:** `COMPLETE`  
**Date:** 2026-11-21  

---

## 1. Implemented Changes

- `src/adcs/control/classical/baselines.py`:
  - **Arm A0 (`ClassicalLQRController`)**: Nominal offline-CARE LQR + gyroscopic feedforward + nominal allocation.
  - **Arm A1 (`make_oracle_allocation_lqr`)**: LQR + oracle capability-aware allocation (`is_oracle=True`, diagnostic baseline only).
  - **Arm A2 (`ClassicalDOBController`)**: LQR + 3-axis nonlinear Extended State Observer (`ExtendedStateObserver`, bandwidth $\omega_o = 0.75\,\mathrm{rad/s}$, bounded `0.12 Nm`, freezes integration when `gamma_obs < 0.35`).
  - **Arm A3 (`StrongClassicalController`)**: Strongest practical classical baseline combining LQR + ESO/DOB + onboard estimated capability-aware allocation (effectiveness + bias compensation + MTQ assist/unloading) + deterministic observability-aware gain schedule (`kp_scale in [0.45, 1.0]`, `kd_scale in [0.85, 1.0]`).
- `src/adcs/evaluation/metrics.py`: Frozen primary & secondary metric schema (`v1.0.0`) shared identically across all controller arms (`SuccessCriteria`, `EpisodeMetrics`, `compute_episode_metrics`).
- `src/adcs/evaluation/runner.py`: Paired deterministic `EpisodeRunner` separating truth state, noisy/faulted sensors, MEKF, online vs. oracle capability estimators, and controller computation.
- `tests/controller/test_phase6_classical_baselines.py`: Validation-split benchmark test verifying A0–A3 across S0, S1, S4, and S6 plus paired determinism.

---

## 2. Critical Bug Discovered & Resolved During Validation

- **MEKF post-dropout innovation lock-out (`S6_st_dropout_val`):** During 25 s of star-tracker dropout paired with a `0.003 rad/s` gyro bias step, true attitude drifted by ~4.3° while MEKF covariance stayed small. Upon star-tracker recovery at `t = 45 s`, the fixed Mahalanobis threshold (`25.0`) permanently rejected the healthy star tracker, causing `11.09 deg` steady RMS error.
- **Root-cause fix (`src/adcs/estimation/mekf.py`):** Added kinematic frame-to-frame consistency verification (`delta_st < 0.04 rad` over 3 consecutive frames after outage `> 2.0 s` with plausible drift `< 0.45 rad`) triggering conservative covariance inflation and clean re-acquisition, while continuing to reject wild star-tracker glitches (`test_phase5` verified).
- **Exact RK4 orbit/B-field stage caching (`src/adcs/simulation/fast/backend.py`):** Reused `(r_eci, b_eci)` across shared RK4 midpoint/endpoint stages (`k2/k3` and `k4/next k1`) with zero mathematical approximation, verified against all Phase 2 physics tests.

---

## 3. Verification Commands & Outcomes

- `python -m ruff check --no-cache src tests` → `All checks passed!`
- `python -m pytest -v -p no:cacheprovider tests/physics/test_phase2_physics.py tests/fault_injection/test_phase5_estimation_faults_capability.py tests/controller/test_phase6_classical_baselines.py` → **13 passed, 0 failed** (cumulative: **29 passed, 0 failed**).
- Verified key baseline properties on train/val splits (held-out test split untouched):
  - All arms A0–A3 achieve `< 0.35 deg` steady RMS on `S0_nominal_val` with zero loss of control.
  - A2 (ESO) and A3 reduce steady pointing RMS by `> 50%` relative to pure LQR A0 under RW bias + Coulomb/stiction friction (`S4_rw_bias_friction_train`).
  - A1 and A3 hold `< 0.5 deg` steady RMS under 60% gradual wheel degradation (`S1_rw1_gradual40_val`).
  - A3 cleanly recovers after 25 s star-tracker dropout + gyro bias step (`S6_st_dropout_val`).

---

## 4. Next Phase & Prerequisites

Per `CONTROL_ARCHITECTURE.md` §16 (Gate C5) & §20, implement and validate **B2 (Fault Symptoms), B4/B8 (Supervisor M0–M4 & Control Validity), and B7 (Deterministic Residual Authority Gate)** to satisfy Gate C4 **before** beginning Phase 7 RL training with the deployed gate in the loop.
