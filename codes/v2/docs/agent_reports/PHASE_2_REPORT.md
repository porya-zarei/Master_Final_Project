# Phase 2 Report — Physics and Fast Simulator

**Phase:** 2 — Physics and Fast Simulator  
**Status:** `COMPLETE`  
**Date:** 2026-11-21  

---

## 1. Implemented Changes

- `src/adcs/utils/quaternion.py`: scalar-first Hamilton quaternion algebra (`quat_normalize`, `quat_canonicalize`, `quat_conjugate`, `quat_multiply`, `quat_to_dcm`, Shepperd `dcm_to_quat`, `quat_from_axis_angle`, `quat_from_rotvec`, `quat_rotate_vec`, `quat_rotate_vec_inv`, `quat_derivative`, `quat_error`, `quat_geodesic_angle`, `quat_error_rotvec`, `skew`).
- `src/adcs/dynamics/orbit.py`: deterministic two-body `KeplerianOrbit` propagator (circular + elliptical Newton-Raphson Kepler solver) and `compute_lvlh_reference` (`+z_R` nadir, `+x_R` velocity projection with degeneracy fallback, right-handed `+y_R = z_R x x_R`, exact orbital angular rate $\boldsymbol{\omega}_{ref,R}$).
- `src/adcs/dynamics/magnetic_field.py`: `GeomagneticFieldModel` implementing Schmidt semi-normalized spherical harmonics in ECEF with Earth rotation (`ECI <-> ECEF -> Body`). Supports external IAGA Gauss coefficient tables via `load_shc_coefficients` and defaults to a documented tilted geomagnetic dipole ($n=1$, `tilted_dipole_fallback_pending_igrf14_file`) when offline.
- `src/adcs/dynamics/disturbances.py`: `gravity_gradient_torque_body` and `residual_magnetic_dipole_torque_body`.
- `src/adcs/actuators/models.py`: `ReactionWheelBank` (first-order torque lag, torque & momentum saturation walls, viscous/Coulomb/stiction friction, and full fault hooks: effectiveness, bias, friction, lock, stuck torque, delay) and `MagnetorquerBank` (first-order dipole lag, dipole saturation, `m x B`, fault hooks: effectiveness, polarity, bias, dropout, delay).
- `src/adcs/simulation/fast/backend.py`: `FastSimulatorBackend` implementing `SimulatorBackend` with 4th-order Runge-Kutta (`dt = 0.01 s`, 20 substeps per `0.2 s` control period), strict finite input validation, and exact angular momentum conservation ($\dot{h}_w = -\tau_{rw}$, $J\dot{\omega} = A_{rw}\tau_{rw} + \tau_{mtq} + \tau_{dist} - \omega \times (J\omega + A_{rw}h_w)$).
- `tests/physics/test_phase2_physics.py`: comprehensive analytical physics verification suite covering Gate C0 and all 10 validation tests listed in `spacecraft_config.yaml`.

---

## 2. Numerical & Physics Verification Evidence

Verified via `tests/physics/test_phase2_physics.py`:
- **Quaternion/frame conventions:** DCM composition, orthogonality, $\det(R)=+1$, Shepperd round-trip including $\pi$ rotations, finite-difference kinematics $\dot{R}_{IB} = R_{IB}[\omega_B]_\times$, and attitude error sign all verified to $< 10^{-8}$–$10^{-13}$.
- **Torque-free asymmetric rigid body (20 s):** inertial angular momentum $\|\Delta H_I\| < 10^{-10}\,\mathrm{N\cdot m\cdot s}$, rotational kinetic energy $|\Delta T| < 10^{-10}\,\mathrm{J}$, substep quaternion norm drift $< 10^{-9}$.
- **Internal RW momentum conservation (10 s varying 3-axis torque):** total spacecraft+wheel inertial momentum conserved to $< 10^{-10}\,\mathrm{N\cdot m\cdot s}$; analytical torque sign $+\tau_x \Rightarrow +\omega_x, -h_x$ matches to $10^{-10}$ relative error.
- **Actuator lag & saturation:** first-order step response matches $0.15(1 - e^{-0.2/0.1})$ to $10^{-4}$; momentum saturation wall blocks further spin-up while permitting desaturation.
- **MTQ physics:** $|\tau_{mtq} \cdot B_b| < 10^{-18}$; dipole limits enforced; LEO field magnitude within $10\text{–}80\,\mu\mathrm{T}$ and non-constant along orbit.
- **Gravity gradient:** identically zero ($< 10^{-15}$) for nominal isotropic cube inertia; matches analytical formula to $10^{-12}$ for asymmetric inertia.
- **LVLH nadir tracking kinematics:** torque-free spacecraft initialized aligned with LVLH at $\omega_B = \omega_{ref,R}$ maintains $< 10^{-10}\,\mathrm{rad}$ pointing error over 60 s.
- **Determinism & RK4 convergence:** identical inputs produce bit-identical trajectories (`max |diff| = 0.0`); RK4 error at `dt = 0.01 s` vs `dt = 0.005 s` is $3.83 \times 10^{-10}$ with empirical convergence order $> 3.5$ ($\approx 4.0$).

---

## 3. Verification Commands & Outcomes

- `python -m ruff check --no-cache src tests` → `All checks passed!`
- `python -m pytest -v -p no:cacheprovider` → **18 passed, 0 failed** (9 Phase 1 + 9 Phase 2 tests).

---

## 4. Known Limitations & Next Phase

- Offline magnetic field uses the $n=1$ tilted dipole fallback (`tilted_dipole_fallback_pending_igrf14_file`) until an IGRF-14 coefficient file is supplied.
- Aerodynamic and solar radiation pressure disturbances remain disabled per `spacecraft_config.yaml`.
- Proceed to **Phase 3 — Basilisk Truth/Validation Backend**: build the isolated Basilisk backend adapter, availability guard, interface/mock tests, and matched backend comparison harness (marking live Basilisk execution `BLOCKED/NOT VALIDATED` where Basilisk is absent).
