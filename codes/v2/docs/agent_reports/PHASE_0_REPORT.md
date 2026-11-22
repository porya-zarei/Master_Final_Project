# Phase 0 Report — Repository and Environment Audit

**Phase:** 0 — Repository and Environment Audit  
**Status:** `COMPLETE`  
**Date:** 2026-11-21  

---

## 1. Repository State Audit

- **Workspace root:** `E:\Education\Master\Final_Project\codes\v2`
- **Git repository root:** `E:\Education\Master\Final_Project` (branch: `residual-rl`, tracking `origin/residual-rl`).
- **Existing Git working tree:** Parent directory `codes/` has a prior refactor (`../v1/` untracked, prior root files deleted). All work for this mission is strictly scoped inside `codes/v2/` to preserve existing user files and Git history.
- **Files present in `codes/v2/` at audit time:**
  - `AGENT_MISSION.md` (master execution contract and phase gates)
  - `CONTROL_ARCHITECTURE.md` (CCR v2 control and fault-tolerance specification)
  - `RESEARCH_PROTOCOL.md` (experimental hypotheses, scenarios, arms A0–A8, ablations, statistics)
  - `pyproject.toml` (package `adcs-rl` v0.1.0, `src/adcs` layout, pytest/ruff/mypy config)
  - `spacecraft_config.yaml` (`spacecraft_reference_001` preliminary plant config)
- **Missing repository files/directories:**
  - `README.md` (required by `pyproject.toml` `readme = "README.md"`)
  - `src/adcs/` (no source code exists yet)
  - `tests/` (no test suite exists yet)
  - `configs/`, `experiments/`, `results/`, `scripts/`, `docs/`

---

## 2. Environment & Compute Audit

Commands run:
- `python --version` / `where.exe python`
- `uv python list`
- `nvidia-smi`
- Package availability check via `importlib.util.find_spec` and `python -m pip list`

Observed environment:
- **OS:** Windows x86_64
- **CPU:** 24 logical cores
- **GPU:** NVIDIA GeForce RTX 5060 (8151 MiB VRAM; PyTorch installed is CPU build `2.12.1+cpu`, suitable for CPU inference profiling and fast MLP SAC training)
- **Active Python:** `C:\Python314\python.exe` (Python 3.14.6). `uv` is installed with local CPython 3.11.15, 3.12.11, 3.13.13, 3.14.6.
- **Installed packages:**
  - Core: `numpy 2.5.0`, `scipy 1.18.1`, `PyYAML 6.0.3`, `setuptools 81.0.0`, `pydantic 2.13.4`
  - Testing/Lint: `pytest 9.2.0`, `ruff 0.16.9`
  - RL/Data/Plotting: `gymnasium 1.4.0`, `torch 2.12.1+cpu`, `matplotlib 3.11.2`, `pandas 3.0.3`, `scikit-learn 1.9.1`
- **Missing optional packages:**
  - `Basilisk`: **Not installed** (Phase 3 live Basilisk validation will be explicitly marked `BLOCKED/NOT VALIDATED`, while implementing the clean adapter boundary and interface tests).
  - `stable_baselines3`: **Not installed** (will implement a clean, deterministic, self-contained PyTorch SAC trainer in `src/adcs/training/` with optional SB3 compatibility, enabling exact seed control, asymmetric privileged-critic separation, and lightweight CPU inference).
  - `mypy`, `pytest-cov`: **Not installed** (source code will maintain strict type annotations compatible with `pyproject.toml` `[tool.mypy]`).
  - External IGRF library (`pyIGRF`, `ppigrf`, `pygeomag`): **Not installed**.

---

## 3. Specification & Configuration Conflicts / Technical Notes

1. **Terminology mismatch (prose vs. config):** `CONTROL_ARCHITECTURE.md` refers to a "nanosatellite ADCS", whereas `spacecraft_config.yaml` specifies a 100 kg, 1 m × 1 m × 1 m spacecraft ($J = 16.6667\,\mathrm{kg\cdot m^2}$, RW $\tau_{\max}=0.15\,\mathrm{N\cdot m}$, $h_{\max}=6.0\,\mathrm{N\cdot m\cdot s}$, MTQ $m_{\max}=2.0\,\mathrm{A\cdot m^2}$). Per `AGENT_MISSION.md` §1, `spacecraft_config.yaml` governs physical parameters.
2. **RW momentum vs. speed limit consistency:** `spacecraft_config.yaml` lists `rotor_inertia_kg_m2: 0.0149`, `speed_limit_rpm: 5000.0`, `momentum_limit_nominal_Nms: 6.0`, and `momentum_limit_peak_Nms: 7.83`. At 5000 rpm ($\omega = 523.599\,\mathrm{rad/s}$), $I_w \omega_{\max} = 7.8016\,\mathrm{N\cdot m\cdot s}$. Nominal limit (6.0 N·m·s) is well within 5000 rpm (~3845 rpm), while peak (7.83 N·m·s) slightly exceeds 5000 rpm by 0.36%. Implementation will enforce $\min(h_{\mathrm{limit}}, I_w \omega_{\mathrm{limit}})$ explicitly and validate it in config checks.
3. **Uniform cube inertia and gravity-gradient torque:** With isotropic inertia $J = \frac{1}{6}mL^2 I_3$, $\hat{r}_b \times (J \hat{r}_b) \equiv 0$, so gravity-gradient torque is analytically zero for the nominal cube and non-zero under inertia asymmetry/mismatch (Scenario S7). Both behaviors will be tested in Phase 2.
4. **Geomagnetic field model (IGRF-14 vs. offline availability):** `spacecraft_config.yaml` specifies IGRF-14 in ECEF transformed to body frame. Because no IGRF library or IAGA `.shc`/`.cof` table is installed offline, we will implement a general Schmidt semi-normalized spherical-harmonic evaluator supporting standard IAGA coefficient files, paired with a documented, orbit-varying **tilted geomagnetic dipole** ($n=1$, ECEF-rotated) built-in default so no higher-order coefficients are fabricated. This approximation will be tagged in simulation metadata.
5. **Quaternion & frame convention:** `spacecraft_config.yaml` sets `scalar_first [q0, q1, q2, q3]` and `body_to_reference`. We freeze the mathematical convention in Phase 1/2: $q_{IB}$ maps body vectors to inertial ($v_I = R_{IB}(q_{IB}) v_B$), kinematics $\dot{q}_{IB} = \frac{1}{2} q_{IB} \otimes [0, \omega_B]$, LVLH reference $q_{IR}$ has $+z_R$ nadir ($-\hat{r}_I$) and $+x_R$ along velocity projection ($\hat{v}_I$ orthogonalized to $z_R$), and attitude error $q_{RB} = q_{IR}^* \otimes q_{IB}$ canonicalized to $q_0 \ge 0$.
6. **Missing `README.md`:** Must be created in Phase 1 so `pyproject.toml` builds and installs cleanly.

---

## 4. Phased Implementation Plan & Risk Register

| Phase | Deliverables | Primary Gate / Risk |
|---|---|---|
| 1 | `README.md`, `src/adcs/` package, editable install, typed interfaces (`state`, `config`, `simulator`, `controller`), YAML loader + validator, seeding & logging | Editable install without internet (`--no-build-isolation --no-deps`) |
| 2 | Quaternion/LVLH math, RK4 rigid-body + RW + MTQ + orbit + geomagnetic + gravity-gradient dynamics, `FastSimulatorBackend` | Analytical physics tests (momentum conservation, torque signs, RK4 convergence, saturation) |
| 3 | `BasiliskBackend` adapter isolated in `src/adcs/simulation/basilisk/`, availability detection, interface/mock tests, comparison harness | Basilisk unavailable in environment → mark live cross-validation `BLOCKED/NOT VALIDATED` honestly |
| 4 | Nadir/LVLH reference generator, tuned LQR/PD classical controller (A0), RW+MTQ allocator, anti-windup, nominal pointing tests | Gate C1: nominal nadir acquisition/tracking & reproducible baseline |
| 5 | Configurable sensors (gyro, star tracker, magnetometer, RW tach), MEKF attitude estimator + `gamma_obs`, deterministic fault catalog (S0–S8), capability/AMS estimator (oracle & estimated) | Gate C2 & C3: independent fault verification, AMS bounds, separation of truth vs. onboard state |
| 6 | Strong classical baselines: A0 (LQR/PD), A1 (oracle allocation), A2 (LQR + ESO/DOB), A3 (strongest classical with estimated capability allocation + gain scheduling) | Credible, tuned classical baselines on train/val splits; held-out test untouched |
| 7 | Gymnasium `ADCSResidualEnv`, observation/reward spec, deterministic PyTorch SAC trainer, A4 (unstructured residual RL) | Gate C5: verified prior gates, bounded actions, reproducible checkpoints |
| 8 | Full CCR v2 stack: B2 symptoms, B4/B8 supervisor modes M0–M4, B7 deterministic gate (`rho`, `alpha`, `G`, asymmetric slew, NaN/stale fail-conservative), arms A5, A6, A7 + ablations | Gate C4: gate invariants, monotonicity, fallback, oracle vs. estimated separation |
| 9 | Paired Monte Carlo benchmark across S0–S8 (train/val/held-out test), pilot variance check, bootstrap CIs, paired effect sizes, all 12 required plots, experiment records | Statistical rigor, zero test leakage, honest reporting of wins/losses |
| 10 | CPU latency/memory profiling (H5), C/C99 deployment boundary doc, SIL/HIL interface & test plan, final research report | Complete verifiable evidence package |

---

## 5. Next Phase & Prerequisites

Proceed to **Phase 1 — Package Foundation and Interfaces**:
1. Create `README.md` and `src/adcs/` package layout.
2. Implement shared typed dataclasses/protocols (`interfaces/`), deterministic seeding and structured logging (`utils/`), and strict YAML config loading/validation (`config/`).
3. Install package in editable mode and run unit/smoke tests + `ruff check`.
