# Run & Verify — Project State 1

Everything runs from the `codes/` folder. You have two options for the Python
interpreter:

- **PowerShell:** activate once with `.\venv\Scripts\Activate.ps1`, then use `python ...`
- **Any shell (no activation):** prefix commands with `.\venv\Scripts\python.exe`

> All commands below assume you are in `E:\Education\Master\Final_Project\codes`.

---

## 0) Setup (already done; only needed on a fresh machine)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

First run of any Basilisk env downloads support data (ephemeris + gravity model)
once and caches it — needs internet the first time only.

---

## 1) Quick health checks (do these first)

```powershell
# Phase-1 ADCS env: 20-step random rollout. Expect "Smoke test OK."
python scripts/manual_test.py

# Env passes stable-baselines3 compliance checks. Expect "CHECK_ENV: PASS"
python -c "import sys; sys.path.insert(0,'.'); from simulation.envs.adcs_env import make_env, FaultToleranceWrapper; from stable_baselines3.common.env_checker import check_env; check_env(FaultToleranceWrapper(make_env(), seed=0)); print('CHECK_ENV: PASS')"
```

---

## 2) Environment 1 — Phase-1 fault-tolerant ADCS env (Basilisk / bsk_rl)

```powershell
# 2 rollouts, 250 s each; writes results/first_simulation.png
python scripts/demo_rollout.py 2 250
```
Verify: `results/first_simulation.png` shows MRP / body-rate / wheel-speed / reward
with a red band where a fault (RW-lock or sensor-bias) is active.

3D attitude animation (body tumbling, body-fixed axes):
```powershell
python scripts/animate_satellite.py 60          # -> results/satellite_animation.gif
```

Orbit around Earth + attitude:
```powershell
python scripts/animate_orbit.py 140 10          # -> results/orbit_attitude.gif
```

---

## 3) Environment 2 — Earth-observing mission env (imaging + power)

```powershell
python simulation/envs/eo_imaging_env.py
```
Verify: prints `Observation space: Box(14,)`, `Action space: Discrete(4)`, and a
20-step rollout where **battery rises on charge actions (3) and falls on imaging
actions (0–2)**.

3D orbit + ground targets:
```powershell
python scripts/animate_eo_orbit.py 120 30 25     # -> results/eo_orbit.gif
```

---

## 4) Live 3D viewer (Vizard)

```powershell
# writes a Protobuf viz replay into viz_output/
python scripts/gen_vizard.py 40 120 50

# open it in the Vizard app:
& "D:\Vizard\Vizard\Vizard.exe" --loadFile "E:\Education\Master\Final_Project\codes\viz_output\<newest>.bin"
```
Vizard shows Earth, orbit, targets and the satellite in 3D. (Regenerate the
`.bin` any time with `gen_vizard.py`.)

---

## 5) Simulator 3 — custom config-driven ADCS simulator (M0/M1 core)

Single closed-loop episode (random release → LQR nadir acquisition):
```powershell
python simulate.py --seed 0 --T 900 --plot results/nadir_acquisition.png
```
Verify: prints final pointing error, RMS error, settling time (<1°) and max wheel
speed; saves the plot.

**M1 validation** — LQR acquisition over many random initial conditions:
```powershell
python scripts/run_m1_validation.py --n 60 --T 900 --out results/m1_validation
```
Verify: success rate ≈ 73%, settling time ≈ 100–150 s, final error ≈ 0.8°;
writes `results/m1_validation/summary.png` and `metrics.npz`.

**Tune the satellite** by editing the YAML config (no code changes):
`satellite_adcs/config/satellite.yaml`, `orbit.yaml`, `actuators.yaml`,
`sensors.yaml`, `disturbances.yaml`, `simulation.yaml`.

---

## What "verified" means for each feature

| Feature | Command | Expected output |
|---|---|---|
| Phase-1 ADCS env | `scripts/manual_test.py` | `Smoke test OK.` |
| Env RL-compliance | (check_env one-liner) | `CHECK_ENV: PASS` |
| Fault injection | `scripts/demo_rollout.py 2 250` | red fault band in the figure |
| Attitude dynamics | `scripts/animate_satellite.py` | `satellite_animation.gif` |
| Orbit + attitude | `scripts/animate_orbit.py` | `orbit_attitude.gif`, r ≈ 1.08 RE |
| EO mission env | `simulation/envs/eo_imaging_env.py` | `Box(14,)`, `Discrete(4)`, battery charges/drains |
| Vizard 3D | `scripts/gen_vizard.py` + Vizard.exe | `viz_output/*.bin` opens in Vizard |
| Custom simulator | `simulate.py --seed 0 --T 900` | settles <1°, ~0.8° final |
| M1 statistics | `scripts/run_m1_validation.py --n 60` | ~73% success, summary.png |

---

## Notes / known limits

- The ~27% of M1 cases that don't settle <1° in 900 s are dominated by
  **reaction-wheel momentum saturation**; MTQ momentum management is the next step.
- The estimator currently uses the star tracker directly (0.003° accuracy);
  full MEKF with gyro-bias estimation is deferred to Phase 2.
- Run everything from `codes/` (scripts add the repo root to `sys.path`, but
  relative paths like `results/...` assume the `codes/` working directory).
