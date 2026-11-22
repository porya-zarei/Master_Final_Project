# Phase 3 Report — Basilisk Truth/Validation Backend

**Phase:** 3 — Basilisk Truth/Validation Backend  
**Status:** `COMPLETE (Live Basilisk 2.12.2 Gate C6 & 8-Regime Matrix Validated)`  
**Date:** 2026-11-22  

---

## 1. Implemented Changes

- Installed AVS Lab **Basilisk (`bsk==2.12.2`)** in a dedicated Python 3.11.15 virtual environment (`.venv_bsk`) alongside `numpy`, `scipy`, `PyYAML`, and `pytest`.
- `src/adcs/simulation/basilisk/backend.py`:
  - `is_basilisk_available()` runtime availability check and explicit `BasiliskUnavailableError` when absent.
  - Verified Schaub & Junkins MRP $\leftrightarrow$ scalar-first Hamilton quaternion bridge (`quat_ib_to_mrp_bn`, `mrp_bn_to_quat_ib`, `mrp_bn_to_dcm_bn`) and motor-torque sign negation (`motorTorque = -rw_torque_cmd_nm`).
  - Full native Basilisk 2.12.2 simulation wiring using config-general `"custom"` reaction wheels (`ReactionWheelStateEffector`), `MtbEffector`, `GravityGradientEffector`, `MagneticFieldCenteredDipole` (IGRF-14 2025.0 dipole), `ExtForceTorque` (`set_external_disturbance_body_nm`), and RW fault injection (`set_rw_fault(effectiveness, bias_nm)`).
- `src/adcs/simulation/comparison.py`: matched-trajectory discrepancy harness (`compare_backends`).
- `tests/integration/test_phase3_basilisk.py`: contract tests + **live Gate C6 cross-validation, live closed-loop control test, and 8-regime validation matrix (`test_live_basilisk_validation_matrix_8_regimes`)** on Basilisk 2.12.2.

---

## 2. Live Gate C6 Cross-Validation Evidence (`FastSimulatorBackend` vs `BasiliskBackend` 2.12.2)

Matched 10-second 3-axis trajectory (`50` control steps, varying 3-axis RW torques + active 3-axis MTQ dipoles + initial wheel momentum + Keplerian orbit + gravity gradient):

| Quantity | Measured Max Discrepancy (`fast_rk4` vs `Basilisk 2.12.2`) |
|---|---|
| ECI Orbital Position | **`9.31e-9 m`** (`9.3 nm`) |
| Geodesic Attitude | **`1.51e-4 rad`** (**`0.0086 deg`**, RMS `0.0056 deg`) |
| Body Angular Rate | **`3.83e-5 rad/s`** (`0.0022 deg/s`) |
| Reaction Wheel Momentum | **`6.59e-4 N·m·s`** |
| Geomagnetic Field (matched dipole) | **`8.39e-9 T`** (`8.4 nT`, `0.028%`) |

- **Live Closed-Loop Nadir Pointing on Basilisk 2.12.2 (`StrongClassicalController` A3 + noisy sensors + MEKF + Online B3 Capability):** Starting `20.0 deg` off nadir, converged cleanly to **`0.1216 deg`** steady pointing error in `50 s` with zero controller changes — proving clean backend decoupling.
- **Documented intentional model differences during training:** `FastSimulatorBackend` includes first-order RW/MTQ actuator lags (`tau_c = 0.1 s`) and full degree-13 IGRF-14 (`configs/igrf14coeffs.txt`); Gate C6 and the 8-regime plant comparisons match instantaneous actuators (`tau_c = 0`) and centered dipole for apples-to-apples physics verification.

---

## 3. Comprehensive 8-Regime Fast-vs-Basilisk Validation Matrix (`test_live_basilisk_validation_matrix_8_regimes`)

The 8-regime validation suite explicitly separates **Plant Validation** (open-loop trajectory discrepancy via `compare_backends`) from **Closed-Loop Controller Validation** (`StrongClassicalController` + `MultiplicativeEKF` + `OnlineCapabilityEstimator` + `SensorSuite` running identically on `FastSimulatorBackend` and `BasiliskBackend`):

| # | Regime | Validation Type | Duration / Steps | Measured `FastSimulatorBackend` vs `Basilisk 2.12.2` Outcome | Pass Criterion |
|---|---|---|---|---|---|
| **R1** | Nominal 3-axis orbit + RW + MTQ dynamics | **Plant Validation** | `10 s` (`50` steps) | `max_pos_diff = 9.313e-09 m`, `max_att_diff = 1.507e-04 rad` (`0.0086 deg`), `max_omega_diff = 3.830e-05 rad/s`, `max_rw_h_diff = 6.587e-04 N·m·s` | `att_diff < 5e-3 rad`, `pos_diff < 1.0 m` (**PASS**) |
| **R2** | Large `90 deg` attitude slew to nadir | **Closed-Loop Controller Validation** | `50 s` (`250` steps) | Fast final error = **`0.6744 deg`**, Basilisk final error = **`0.6744 deg`**, terminal Fast-vs-Basilisk attitude diff = **`0.0000 deg`** | Both `< 1.0 deg`, diff `< 2.0 deg` (**PASS**) |
| **R3** | High angular rate `10 deg/s` detumble + acquisition | **Closed-Loop Controller Validation** | `60 s` (`300` steps) | Fast final error = **`0.4241 deg`**, Basilisk final error = **`0.4211 deg`**, terminal Fast-vs-Basilisk attitude diff = **`0.0225 deg`** | Both `< 1.0 deg`, diff `< 2.0 deg` (**PASS**) |
| **R4** | RW torque saturation (`0.25 > 0.15 N·m`) & high wheel momentum (`5.95 N·m·s`) | **Plant Validation** | `5 s` (`25` steps) | `max_att_diff = 1.190e-03 rad` (`0.0682 deg`), `max_omega_diff = 3.231e-04 rad/s`, `max_rw_h_diff = 5.386e-03 N·m·s` | `rw_h_diff < 1e-2 N·m·s`, `att_diff < 5e-3 rad` (**PASS**) |
| **R5** | RW0 `50%` effectiveness loss + `+0.015 N·m` bias fault (`set_rw_fault`) | **Closed-Loop Controller Validation** | `50 s` (`250` steps) | Fast final error = **`0.1062 deg`**, Basilisk final error = **`0.1047 deg`**, terminal Fast-vs-Basilisk attitude diff = **`0.0260 deg`** | Both converge `< 1.0 deg` (**PASS**) |
| **R6** | MTQ dipole saturation (`±5.0 -> ±2.0 A·m²`) & $\tau_{\text{MTQ}} \perp \mathbf{B}_{\text{body}}$ | **Plant Validation** | `4 s` (`20` steps) | `max_att_diff = 0.000e+00 rad`, `max_b_diff = 2.135e-09 T`, $|\tau_{\text{MTQ}} \cdot \mathbf{B}|_{\text{Fast}} = 2.585\times 10^{-26}$, $|\tau_{\text{MTQ}} \cdot \mathbf{B}|_{\text{Bsk}} = 1.995\times 10^{-14}$ | Clip at `±2.0 A·m²`, $|\tau \cdot B| < 10^{-12}$ (**PASS**) |
| **R7** | `20 s` star-tracker dropout (`t = 15..35 s`) + recovery | **Closed-Loop Controller Validation** | `60 s` (`300` steps) | Fast post-recovery error = **`0.0938 deg`**, Basilisk post-recovery error = **`0.1014 deg`**, terminal Fast-vs-Basilisk attitude diff = **`0.0105 deg`** | Both recover `< 1.0 deg` after ST return (**PASS**) |
| **R8** | Long-duration `600 s` orbit & attitude propagation | **Plant Validation** | `600 s` (`3000` steps) | `max_pos_diff = 1.971e-07 m` (`0.197 µm`), `max_omega_diff = 1.949e-05 rad/s`, `max_att_diff = 5.010e-03 rad` (`0.2870 deg`), `max_rw_h_diff = 3.164e-04 N·m·s` | `pos_diff < 1.0 m`, `att_diff < 0.05 rad` (**PASS**) |

---

## 4. Verification Commands & Outcomes

- `python -m pytest -v -p no:cacheprovider tests/physics/test_stage1_invariants.py tests/integration/test_phase3_basilisk.py` → **8 passed, 2 skipped** (Py3.14).
- `.\.venv_bsk\Scripts\python.exe -m pytest -v -s -p no:cacheprovider tests/integration/test_phase3_basilisk.py` → **5 passed, 0 failed** (`68.54 s`, Py3.11 `.venv_bsk` with live `Basilisk 2.12.2`).
- `python -m ruff check --no-cache tests/physics/test_stage1_invariants.py tests/integration/test_phase3_basilisk.py` → **All checks passed!**
