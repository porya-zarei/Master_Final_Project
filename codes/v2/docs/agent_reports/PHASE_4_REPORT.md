# Phase 4 Report — Reference, Classical Controller, and Actuator Allocation

**Phase:** 4 — Reference, Classical Controller, and Actuator Allocation  
**Status:** `COMPLETE`  
**Date:** 2026-11-21  

---

## 1. Implemented Changes

- `src/adcs/control/reference/nadir.py`: `NadirReferenceGenerator` (LVLH nadir pointing with velocity-projection degeneracy persistence) and `compute_attitude_error` (canonical geodesic rotation vector `rotvec_rad` and body-frame rate error $\omega_B - R_{RB}^T \omega_{ref,R}$).
- `src/adcs/control/allocation/allocator.py`: `ActuatorAllocator` and `solve_box_lsq` (deterministic box-constrained projected Gauss-Seidel least-squares allocator supporting arbitrary orthogonal or over-actuated RW geometry, momentum-wall tapering, capability effectiveness/bias hooks, and dual-role MTQ allocation: instantaneous deficit assist `(B x tau_def)/||B||^2` + momentum unloading `k*(H_w x B)/||B||^2`).
- `src/adcs/control/classical/lqr.py`: `ClassicalLQRController` (Arm A0 / B5 backbone) solving the continuous-time Algebraic Riccati Equation offline at init (`q_attitude=1.0`, `q_rate=80.0`, `r_torque=4.0` → $K_p \approx 0.50\,\mathrm{N\cdot m/rad}$, $K_d \approx 6.06\,\mathrm{N\cdot m\cdot s/rad}$, critically damped $\zeta \approx 1.05$), with gyroscopic feedforward, smooth eigenaxis slew-rate limiting (`0.08 rad/s`), and back-calculation anti-windup.
- `configs/controller_classical.yaml`: externalized configuration for classical LQR and allocator parameters.
- `tests/controller/test_phase4_classical.py`: Gate C1 closed-loop verification tests.

---

## 2. Gate C1 Verification Evidence

- **Nominal 30° acquisition + 0.03 rad/s tumble:** converges below `0.5 deg` before `60 s` and holds `< 0.05 deg` steady-state nadir pointing error with RL disabled.
- **Large-angle 90° slew under RW torque saturation:** engages RW torque saturation, tracks smoothly without instability, converges to `< 0.1 deg` within `100 s`, and replays bit-identically.
- **MTQ momentum unloading:** drains initial `[1.5, -1.2, 0.8] N*m*s` wheel momentum while maintaining `< 0.1 deg` nadir pointing.
- **General geometry allocation:** verified exact torque allocation on both 3-wheel orthogonal and 4-wheel NASA pyramid geometry (including single-wheel failure redistribution).

---

## 3. Verification Commands & Outcomes

- `python -m ruff check --no-cache src tests` → `All checks passed!`
- `python -m pytest -v -p no:cacheprovider` → **25 passed, 0 failed** (4 new Phase 4 tests + 21 prior tests).

---

## 4. Next Phase & Prerequisites

Proceed to **Phase 5 — Sensors, Estimation, Fault Injection, and Capability**: configurable sensor suite, MEKF estimator with operational `gamma_obs`, deterministic fault catalog (S0–S8), and B3 Actuator Capability / AMS estimator (separating oracle vs. onboard estimated capability).
