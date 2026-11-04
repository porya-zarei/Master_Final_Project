# Milestone A — Architecture and code audit

**Status:** complete. Written before any implementation change, per the directive.
**Branch:** `residual-rl`. Nothing from the previous work has been modified or deleted.

---

## 1. Current architecture — what actually exists

| layer | file | state |
|---|---|---|
| Config (YAML, deep-merged) | `satellite_adcs/config/*.yaml`, `config/__init__.py` | working; `_merge` is a recursive deep merge |
| Attitude math | `quaternion.py` | `quat_to_dcm`/`dcm_to_quat` **transposed to `C_BN`** (G14 fix, `3293fb9`); 12 regression tests |
| Guidance | `guidance.py` | nadir/LVLH reference; rate sign fixed to `[0,−n,0]` (`0d73fcb`) |
| Dynamics | `dynamics.py` | 3 RW + 3 MTQ, gravity gradient, B-field; wheel `J_wΩ̇=−h·τ_cmd`; **aero/SRP/magnetic-residual flags are no-ops (`:71–73`, G9)** |
| Sensors | `sensors.py` | star tracker, sun, gyro (bias 1e-3 rad/s), magnetometer; explicit bias setter. **No dropouts, no delay, no sun/mag degradation** |
| Attitude estimator | `estimation.py` | **6-state MEKF with gyro-bias estimation** (C2-e, `1ce6f7f`); bias converges to 3.8e-06 |
| Wheel-health estimator | `health_estimation.py` | per-wheel RLS + 4 guards; identifies h=0.5 in 1.8 s, step in 11.2 s; **dead wheel unobservable if dead from t=0** (G13, refined in §11 of report-3) |
| Allocation | `controllers.py::allocate_torque` | RW inversion + MTQ residual (m×B) + momentum dump; `health=None` (oracle) or an estimate (M1, `3224010`) |
| Classical controllers | `controllers.py`, `gain_scheduled.py` | B-dot → LQR phase manager; fixed-gain LQR; gain-scheduled LQR |
| RL environment | `environment/adcs_env.py` | custom NumPy Gymnasium env; obs = `[θ(3), ω_err(3), Ω_rw(3)]`; action = **desired body torque**, normalised; fault modes healthy/rw1_50/rw1_failed/random_health; `health_source` switch (M1) |
| Training | `scripts/train_rl.py` | PPO (official baseline) / SAC; `SubprocVecEnv` when n_envs>1 |
| Evaluation | `scripts/eval_rl_vs_lqr.py` | **paired** ICs + gyro bias for both controllers |
| Regression tests | `tests/test_frames.py` (12), `test_estimation.py` (3), `test_allocation_health.py` (5) | all passing |

### What does **not** exist yet (required by the directive)

- ❌ Reaction-wheel **friction, stiction, deadzone, torque-rate limit, quantization** — the actuator is ideal except for saturation and a speed clamp.
- ❌ **Sensor faults**: no star-tracker dropout, no sun-sensor degradation, no magnetometer bias, no delay.
- ❌ **Fault detection and isolation (FDI)** as a module — health *estimation* exists, but there is no detector making discrete decisions.
- ❌ **Safety filter** between command and allocator.
- ❌ **Residual RL** — the policy currently commands the full torque, not a correction.
- ❌ **MPC / nonlinear model-based baseline.**
- ❌ **MIL/SIL/HIL** code, export path, latency measurement.
- ❌ Disturbance flags (G9) are declared but do nothing.

---

## 2. The LQR acquisition-time discrepancy: 241.3 s vs 67.2 s — RESOLVED

The directive asks for the exact experimental differences before either is used as a
baseline. Two numbers were reported for the same controller in report-3 (§12 and §13).
`scripts/audit_lqr_metric_discrepancy.py` recomputes **every** metric on the **same**
episodes in the **same** harness (`simulate.run_episode`), n = 8:

| metric, identical data | median |
|---|---|
| time-to-first-entry (< 1°) | **69.7 s** |
| settle, 1° held 10 s | **117.8 s** |
| settle, 1° held 30 s | 117.8 s |
| entries into tolerance | 1.0 (no chatter) |

Per-seed `t_first`: `58.4, 62.8, 64.4, 68.0, 71.4 | 206.0, 401.2, 417.0`

### The three differences, quantified

1. **Metric (primary cause of the reported gap's direction):** §12 used
   `settling_time(hold=10 s)` — *sustained* below tolerance — while §13 used
   *first entry*. On identical data this alone is **1.69×** (117.8 vs 69.7).
2. **Sample size and bimodality (primary cause of the magnitude):** §12 used n = 12
   and §13 used n = 6. The distribution is **strongly bimodal** — a fast cluster at
   58–71 s and a slow cluster at 206–417 s. A median over 6 or 12 samples of a
   bimodal variable is unstable and can move by 3× between draws. §12's n = 12
   happened to contain 7 slow cases (206, 277, 291, 401, 417, 419, 430), giving
   241.3 s; §13's n = 6 contained mostly fast ones, giving 67.2 s.
3. **Harness (secondary):** §12 drove the LQR through the classical loop; §13 drove
   the same LQR *law* through `ADCSEnv` as a normalised action, which passes through
   the allocator in exactly the same way but with a different call path.

### Consequence for the thesis — neither number may be used

**The correct baseline is a distribution, not a median.** Report the fast/slow
clusters, the full percentiles, and the median with a confidence interval; and
**never compare controllers using a median from n < 24 paired episodes.** The
bimodality itself is an unexplained phenomenon worth investigating: the fast cluster
acquires in ~65 s, the slow cluster in 200–430 s, at the same initial-error range,
which suggests a geometric effect (slew axis relative to available torque, wheel
saturation, or magnetic-field geometry) rather than a tuning issue.

This also explains why §12's "9× headroom" and §13's "2.71×" are not in conflict:
they measure different quantities on different samples. **The §13 comparison is the
trustworthy one** because both controllers were driven through the identical harness
on identical seeds — and even there the sample is n = 6, so it must be repeated at
n ≥ 24 before it is cited.

---

## 3. Inconsistencies and risks found

1. **G13 (oracle allocator)** — still the default. Must be treated as a documented
   ablation, not the baseline, in any "fault-tolerant" claim.
2. **G9 (no-op disturbance flags)** — `dynamics.py:71–73` declares aero/SRP/residual
   magnetic disturbances but does nothing. Either implement (required for §11
   Experiment 6) or delete; leaving them is a silent lie in the config.
3. **The dead-wheel scenario was unrealistic** — starting an episode already faulted
   produced the 82° figure; in-flight faults give 1.64° (report-3 §11). All fault
   experiments must state the fault *timing*.
4. **Bimodal acquisition time** is unmodelled and unexplained (§2 above).
5. **Training seed variance** — 1 of 2 seeds learned (report-3 §8/§9). Any RL result
   must use ≥ 3 seeds.
6. **No actuator nonlinearity at all**, which is exactly what the directive calls the
   high-priority task: the plant currently flatters every linear controller.

---

## 4. Plan mapped to the directive's milestones

| milestone | work | gate |
|---|---|---|
| **A** | this document | ✅ done |
| **B** | actuator nonlinearities: deadzone, viscous + Coulomb friction, stiction, torque-rate limit, quantization; physically justified parameters; each individually and combined | LQR and bang-bang re-benchmarked **before** any RL |
| **C** | classical benchmarks under the new plant: LQR, fault-aware LQR (h_hat), gain-scheduled, bang-bang; distributions at n ≥ 24 paired | establishes the honest baseline |
| **D** | residual SAC (primary) + residual PPO; `τ_cmd = τ_LQR + α·Δτ_RL`; bounded residual; α fixed/scheduled/state-dependent as a configurable factor | nominal non-degradation first (Experiment 1) |
| **E** | identical-scenario comparison | RL advantage / comparable / disadvantage / inconclusive per experiment |
| **F** | held-out fault distribution, combined faults | generalization is the only defensible RL claim |
| **G** | safety filter + LQR fallback | constraint-violation counting, fallback exercised |
| **H** | SIL/HIL, latency, memory, quantisation | no deployment claim from workstation timing |

**Order is non-negotiable:** B before C, C before D. Training a residual policy on the
current idealised plant would repeat the original mistake — measuring an advantage
that the plant invented.

---

## 5. Rules carried forward from this project's own history

These are not generic; each one was learned the hard way in this repository.

1. **A metric that matches the JSON is not validated.** The frame bug produced numbers
   that reproduced perfectly and were 91° wrong.
2. **Paired conditions, always** — same ICs and same gyro-bias draw for every
   controller. Non-paired comparisons already produced a spurious significance claim.
3. **State the fault timing** (t = 0 vs in flight); it changes the result by 80°.
4. **n ≥ 24, ≥ 3 seeds, CI before any claim.** n = 8 produced a dead-wheel "advantage"
   that vanished at n = 24.
5. **Pre-register the metric and the pass condition** before training (plan §5).
6. **Never weaken the baseline.** Every controller gets the same information, the same
   actuator model and the same tuning effort.
7. **Estimator state must be reset per episode** (C2-e follow-up): a stale `b_hat`
   corrupted the first seconds of every evaluation episode.
8. **A no-op config flag is a defect.** G9.
