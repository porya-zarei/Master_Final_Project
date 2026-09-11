> # ⛔ SUPERSEDED — DO NOT USE
>
> This is **v1 (draft)** of the Phase C → F plan, kept only for audit history.
> It has **known errors**, in particular an incorrect claim that the M1 LQR success-rate
> change (83.3% → 75%) was caused by the time-base fix — that claim is wrong and has been
> removed (see §2.2 of the current plan).
>
> **The authoritative, current plan is: `docs/PhaseC_to_F_Master_Plan.md`**
> (v2, `STATUS: PLAN FINALIZED`, `EXECUTION AUTHORIZATION: C1 + C4.1 ONLY`).
>
> Nothing in this file is authoritative. Do not implement from it.

---

# Phase C → F Master Plan (v1 — DRAFT, SUPERSEDED)

**Fault-Tolerant Attitude Control of Nanosatellites Using Reinforcement Learning: From Simulation to Hardware-in-the-Loop**

- **Author:** Pouria Zarei (810103137) — M.Sc. Control Engineering, University of Tehran
- **Advisor:** Dr. Mohammad-Javad Yazdanpanah
- **Date:** 2026-09-11
- **Status:** 🟨 **PLAN ONLY** — no implementation until an explicit *"go"*
- **Scope:** everything from the end of Phase B (RL baseline proven) to the end of the project.

---

## 0. How to read this document

### 0.1 Numbering rule — this document is authoritative

Two independent advisory documents used **conflicting** phase letters. To avoid a fatal
misunderstanding, the letters in **this** file are the only ones that mean anything:

| Letter | This plan | Content |
|---|---|---|
| **Phase C** | Finalize + **freeze** the baseline controller → regenerate MIL → **SIL on the frozen artifact** | C-I (freeze) ⟶ gate ⟶ C-II (SIL) |
| **Phase D** | **MCU implementation + HIL** | port, quantize, time, inject faults, validate |
| **Phase E** | **Thesis / report / defence freeze** | evidence matrix, plots, limitations, defence package |
| **Phase F** | **World-model research arm** (frozen JEPA+MPC → AdaJEPA+MPC) | time-permitting; **must not gate D or E** |

> ⚠️ **Ignore the other advisor document's lettering.** That document used *D = frozen world
> model, E = AdaJEPA, F = safety gate*. Every one of those items lives in **Phase C** or
> **Phase F** here. If both documents are handed to an implementer without this warning, the
> implementer will execute the wrong roadmap.

### 0.2 Relationship to the names already used in the reports

| This plan | Name used in `report-state-2.md` | Status |
|---|---|---|
| Phase A (implicit) | M0 simulator, M1 LQR, Phase 1B fault model | ✅ done (numbers need regeneration) |
| **Phase B (implicit)** | "Phase 2: RL baseline (Baseline C)" | ✅ done (PPO beats LQR on all 3 cases) |
| Phase C | *(did not exist)* | 🟨 this plan |
| Phase D | "Phase 6: HIL" | 🟨 this plan |
| Phase E | *(did not exist)* | 🟨 this plan |
| Phase F | "Phase 3: world models (Baseline B)" + "Phase 4: AdaJEPA" | 🟨 optional |

### 0.3 The one structural fix that makes Phase C closeable

> "Phase C = the last architecture change **and** end of MIL **and** end of SIL"

That is **three exits in one phase, and it will not close.** So Phase C is divided by a hard gate:

```
        C-I  FREEZE  ──────────────►  ⛔ GATE  ──────────────►  C-II  SIL
   architecture may still change      artifact + definitions      NO architecture
   (evidence-driven)                  frozen; MIL regenerated     changes allowed
```

**"Last architecture change" means C-I only.** After the gate, the controller is a frozen
artifact and only its *execution environment* changes (host → embedded-representative → MCU).

### 0.4 A warning that shapes the whole plan

The current PPO is **not** freezable as-is. It was:

- trained **without** ever seeing a health estimate `ĥ` (blind to the fault it is meant to tolerate),
- trained on `h ∈ [0.5, 1.0]` only — so the **dead-wheel case (h = 0) was never trained**,
- scored on **n = 8** random initial conditions,
- produced alongside **five simultaneous changes**, so its gain is demonstrated but **not attributed**.

Freezing that as "the reference architecture" would bake all four weaknesses into the thesis.
**Phase C exists to remove them.** This is the single most important statement in this document.

---

## 1. Verified current state — code audit

Verified by reading the code on 2026-09-11, not from memory.

### 1.1 What exists and is verified working

| Component | File | State | Evidence |
|---|---|---|---|
| Plant: 24U, 35 kg, `J = diag(0.38, 0.73, 0.58)` | `config/satellite.yaml` | ✅ | config-driven, random IC on SO(3), `ω_max = 5°/s` |
| Euler + MWM dynamics, inertia coupling `−ω×H` | `dynamics.py` | ✅ | `tau = −ω×H + τ_rw_eff + τ_mtq + τ_dist` |
| Gravity-gradient torque | `dynamics.py:139` | ✅ on | `3μ/r³ · r̂ × (J r̂)` |
| Tilted-dipole B-field (11.5°) | `dynamics.py:119` | ✅ | `B_body()` |
| Sensors: gyro, mag, sun, star tracker, GPS | `config/sensors.yaml` | ✅ | ST 5e-5 rad, gyro 1e-4 rad/s + **bias 1e-3 rad/s** |
| Actuators: 3 RW (10 mN·m, 628 rad/s) + 3 MTQ (1 A·m²) | `config/actuators.yaml` | ✅ | |
| Fault model `τ_actual = h·τ_cmd`, `h ∈ [0,1]` | `dynamics.py:158` | ✅ | continuous |
| Fault-tolerant allocator: health inversion + MTQ residual + momentum desaturation | `controllers.py:24` | ✅ | **shared by LQR and RL** |
| B-dot detumble → LQR phase manager | `controllers.py:51` | ✅ | detumble threshold 0.3°/s, `k_bdot = 1e4` |
| Nadir guidance (LVLH from orbit, recomputed each step) | `guidance.py` | ✅ | not a fixed attitude |
| RL env: 9-dim obs, 3-dim action (desired torque) | `adcs_env.py` | ✅ | `Box(-10,10,(9,))`, `Box(-1,1,(3,))` |
| Shaped reward: `−‖θ‖² − 0.1‖ω_err‖² − 0.01‖a‖² + 1·1[‖θ‖<1°]` | `adcs_env.py:126` | ✅ | YAML knobs in `config/rl.yaml` |
| Time-axis fix | `simulate.py:50` | ✅ **in code** | `nctrl = max(1, round((1/hz)/dt))`, `t += ctrl_period` |
| Result: PPO beats LQR on all 3 fault cases | `results/rl_eval_shaped/` | ✅ | 100%/0.17° vs 75%/0.73°; dead-wheel 12.5% vs 0% |

### 1.2 What is NOT done — the honest list

These are the gaps Phase C must close. **None of them may be silently marked "done" by an
implementer.**

| # | Gap | Verified evidence | Why it matters for the thesis |
|---|---|---|---|
| **G1** | **`MEKF` is a stub.** The class is *named* `MEKF` but is star-tracker passthrough + raw gyro. `propagate()` is a **no-op**; `update_vector()` returns `self`; there is no bias state, no covariance. | `estimation.py` (40 lines): `update_star_tracker` just assigns `q_meas`; docstring admits *"bias small and neglected here"* while `sensors.yaml` **defines a gyro bias of 1e-3 rad/s** | A thesis claiming MEKF must actually have one, or must not claim it. Also: rate estimate is biased. |
| **G2** | **The policy is fault-blind.** `h` appears only in `info["rw_health"]`, never in the observation. | `adcs_env.py:117` — obs = `[θ(3), ω_err(3), Ω_rw/Ω_max(3)]` | Two states with identical `(θ, ω, Ω)` but `h=[1,1,1]` vs `h=[1,0.2,1]` demand different actions. The policy cannot distinguish them. This is *the* fundamental limit on fault adaptation. |
| **G3** | **The dead wheel was never trained.** `health_range: [0.5, 1.0]`. | `config/rl.yaml` | The 12.5% dead-wheel result is **zero-shot generalization**, not training performance. This must be stated explicitly — and then either fixed (curriculum) or framed (recoverability). |
| **G4** | **Health is constant for the whole episode.** Sampled once in `reset()`, never during the run. | `adcs_env.py:152` | No fault onset, no detection time, no adaptation transient, no recovery metric — i.e. none of the genuinely valuable fault-tolerance experiments. |
| **G5** | **Reward has no safety, saturation or rate terms.** `w_ctrl` penalizes the **normalized action `a`**, not the physical torque; there is no wheel-speed penalty and no `Δτ` penalty. | `adcs_env.py:126–142` | An embedded controller should not saturate wheels or produce jerky torque. Currently nothing discourages either. |
| **G6** | **No safety governor and no fallback.** The action is clipped to `[-1,1]`; nothing else supervises it. | `adcs_env.py:162` | Required before any MCU deployment. The validated `ADCSController` (B-dot+LQR) is a ready-made fallback and is currently **not wired to the RL path at all**. |
| **G7** | **Evaluation is n = 8.** | `eval_rl_vs_lqr.py --n 8` | Not a statistically defensible headline number. M1 used 60 ICs, Phase 1B used 30. |
| **G8** | **M1 and Phase 1B numbers are stale.** Generated **before** the `simulate.py` time fix. | `results/m1_validation_60/` = Sep 8 17:41; `results/fault_experiment/` = Sep 10 19:37; fix landed in `4502482` | Settling times are inflated ~25%; the "900 s" episodes really ran 720 s. Any table quoting 143 s / 146.6 s is wrong. |
| **G9** | **Aero / SRP / residual-dipole torques are flags with no implementation.** They are read into `self.aero_on` … and never used. | `dynamics.py:71–73` read the flags; `disturbance_torque()` (line 136) returns **gravity-gradient only**, with the comment *"add later if needed"* | Enabling them in YAML currently does **nothing**. Do not claim disturbance robustness that isn't modelled. |
| **G10** | **No plant uncertainty.** Only fault health is randomized; mass, inertia and actuator gains are fixed constants. | `satellite.yaml`, `actuators.yaml` | A controller robust to faults but not to a ±10% inertia error is not deployable. |
| **G11** | **No definition of physical recoverability.** "Success" for the dead wheel is demanded over *all* ICs. | `eval_rl_vs_lqr.py:61` — `success = not isinf(settling_time)` over the whole sample | With one dead wheel the system is underactuated; some ICs are **physically unreachable** within 900 s. Counting those as controller failures is scientifically wrong and understates the contribution. |
| **G12** | **Wheel speed is clipped as a state, not modelled.** | `dynamics.py:197` — `self.omega_w = clip(omega_w, ±max_speed)` | Silently destroys wheel momentum at saturation (violates conservation of `H`). Acceptable as a placeholder, must be documented, and ideally replaced by a motor torque-rolloff. |

---

## 2. Phase C — Finalize the baseline, freeze it, then SIL on the freeze

**Goal:** one frozen, physically defensible, safety-wrapped, statistically validated
controller, plus the evidence for *why* it is the way it is.

### 2.1 Hard exit criteria (the gate)

Phase C is complete **only when all of these exist simultaneously**. C-II may not start until
every row is satisfied.

| # | Exit criterion | Artifact |
|---|---|---|
| E1 | **One frozen controller diagram** | `docs/figures/baseline_c_final_architecture.{png,md}` |
| E2 | **Frozen definitions**: observation set, reward, fault distribution, success criterion, recoverability criterion | a `FROZEN_SPEC.md` with a version hash |
| E3 | **Real attitude/rate estimator** (MEKF with gyro-bias, or a documented decision not to claim MEKF) | `estimation.py` + validation plot |
| E4 | **Health estimator `ĥ`** producing the policy's fault input, validated on 3 fault cases | `health_estimator.py` + `ĥ` vs `h` plot |
| E5 | **Safety governor + classical fallback**, wired in, with gated-vs-ungated numbers reported separately | governor spec + comparison table |
| E6 | **Reward ablation complete**: the 5 simultaneous changes are attributed | results table, one row per factor |
| E7 | **Observation ablation complete**: O0/O1/O2/O3 compared | results table |
| E8 | **Fault-onset experiments** with detection / adaptation / recovery metrics | results table + plots |
| E9 | **Recoverability map** separating *physically unrecoverable* from *controller failure* | map figure + `X_rec` definition |
| E10 | **MIL regenerated** on the corrected time base | regenerated M1 / 1B / MC tables |
| E11 | **Large-N Monte Carlo** ≥ 500 ICs (≥ 1000 for the dead-wheel headline) | `results/mc_final/` bundle |
| E12 | **SIL**: the frozen policy executing through the *embedded-representative* path (quantized, fixed-point inference, frozen normalization constants), performance within ±2 pp of MIL | SIL report + timing/memory table |

### 2.2 C-I / Milestone C1 — Truth and infrastructure

**Nothing else in this plan is trustworthy until C1 is done.**

| Task | Detail |
|---|---|
| C1.1 | Regenerate **M1 (LQR, 60 ICs)** with the fixed time base. Publish the corrected settling-time median/p90 — expect ~25% *smaller* than the 103 s / 153 s currently quoted. |
| C1.2 | Regenerate **Phase 1B (30 ICs × 3 fault cases)** with the corrected time base. |
| C1.3 | **Measure evaluation throughput** (episodes/min, and how it scales with the 24 cores) so Monte Carlo size N can be *sized honestly* rather than guessed. |
| C1.4 | Fix the stale docstring in `estimation.py` ("at the control rate (4 Hz)") to match the real 5 Hz. |

> **Expected outcome to write down now, so it isn't hidden later:** the LQR success rate moves
> 83.3% → **75%** purely because of the time-base fix. That is a correction, not a regression,
> and it must be stated in the report — not quietly absorbed.

### 2.3 C-I / Milestone C2 — Estimator: make MEKF real, add the health estimator

**C2.1 Attitude/rate estimator (G1).** Two defensible options:

| Option | What it is | Pros | Cons | Recommendation |
|---|---|---|---|---|
| **A** | Full MEKF: 3-axis attitude error state + 3 gyro-bias states, star-tracker + mag/sun vector updates, `δθ/δb` cross-covariance | Textbook-defensible; estimates the 1e-3 rad/s gyro bias already in the config | The stars-tracker-only large-angle acquisition case is exactly where naive bias observability can go unstable | ✅ **do this**, with rate-limiting/protection during large-angle acquisition |
| **B** | Keep ST passthrough + a **separate gyro-bias observer** (e.g. low-pass on `ω_gyro − ω_st_differentiated`, gated on ST validity) | Far simpler, almost as accurate, no stability risk | Not a "real MEKF" if the thesis claims MEKF | acceptable fallback if A misbehaves |

Either way: **the deployed rate estimate must be bias-corrected**, and the thesis must state which
option was used. Claiming "MEKF" while shipping a `q_meas` assignment is not acceptable (G1).

**C2.2 Actuator health estimator `ĥ` (G2, G3).** Physics-based, no training required:

- Per wheel `i`, the wheel's own momentum balance gives
  `J_w · dΩ_i/dt = −h_i · τ_c,i`  ⟹  `ĥ_i = −J_w · (dΩ_i/dt) / τ_c,i`
- Gate on **excitation**: only update when `|τ_c,i| > τ_min` (a dead wheel cannot be detected if
  it is never commanded). Use recursive least squares with forgetting, plus a light low-pass
  (`τ_f ≈ 0.5 s`) on the wheel-speed derivative to fight tacho noise.
- Cross-check against the body-rate equation: `J ω̇ + ω × (Jω + J_wΩ) = diag(ĥ)τ_c + m×B + τ_GG`
  solved by least squares over a short window.
- **Confidence** `c_i ∈ [0,1]` from excitation level + residual + time-since-detection.
  Low confidence ⟹ hold last estimate and flag to the governor; **never** feed `h_true`.
- Validation targets: dead wheel detected `ĥ → 0` in < 10 s of commanded motion; 50% wheel gives
  `ĥ = 0.5 ± 0.05`.

**C2.3 Train/deploy consistency:** the policy input must be the **actual online `ĥ`**, so train and
test see the same quantity. Optionally augment with estimator-error noise to harden it.

### 2.4 C-I / Milestone C3 — Observation ablation

Answers the thesis-quality question: *how much fault information does a learned controller
actually need?*

| Set | Contents | Dim | Status |
|---|---|---|---|
| **O0** | `θ, ω_err, Ω_rw` | 9 | ✅ already trained (`rl_shaped`) |
| **O1** | O0 + `ĥ` | 12 | 🟨 run |
| **O2** | O1 + `B_body` | 15 | 🟨 run |
| **O3** | O2 + `τ_prev` | 18 | 🟨 run |
| (O4) | O3 + authority indicator `τ_achievable` | 21 | optional, only if O3 still lags |

Protocol: identical reward, identical fault distribution, identical seeds, **one variable changed
per run.** Each run is ~2 M steps ≈ 13 min (measured ≈ 2270 fps), so this milestone is cheap —
the cost is analysis, not compute.

### 2.5 C-I / Milestone C4 — Reward ablation (attribute the 5 changes) + reward v2

**C4.1 The confound.** The 4° → 0.17° jump came from **five simultaneous changes**. Factorial
design, everything else fixed to the corrected settings:

| Factor | Levels | Runs |
|---|---|---|
| Reward shape | `quad` vs `bonus` | 2 |
| Observe-reward normalization | `norm_reward` off vs on | 2 |
| Control rate | 5 Hz (corrected) vs 2 Hz (original) | 2 |

Run the `quad`/`bonus` × `norm_reward` 2×2 first (4 runs, ~52 min), then the 2 control-rate runs.
**Whichever factor actually moved the result becomes the headline claim.** If it turns out *not*
to be reward shaping, that is a finding, not a failure — report it and adjust the narrative.

**C4.2 Reward v2 (target design, all knobs in `config/rl.yaml`):**

```
r = − wθ·log(1 + ‖θ‖²/θ_tol²)          fine-pointing-aware error term (steep near 0)
    − wω·‖ω_err‖²                        rate damping
    − wu·‖τ_cmd‖²                        control effort  ← physical torque, NOT normalized action (G5)
    − wΩ·Σ max(0, (|Ω_i|/Ω_max − 0.8)/0.2)²   wheel-saturation hinge (G5)
    − wΔ·‖τ_k − τ_{k−1}‖²                torque-rate smoothing (embedded-friendliness)
    − wsafe·f_safety                     saturation / overspeed / emergency-ω indicator penalties
    + R_prec·1[‖θ‖ < θ_tol]              retention bonus (this is what worked)
    + R_settled·1[settled]               hold-steady bonus (hysteresis, ≥60 s inside tol)
```

Keep `θ_tol = 1°` (= the evaluation threshold). Every term stays config-driven.

### 2.6 C-I / Milestone C5 — Fault model v2 + plant uncertainty

**C5.1 Fault taxonomy (G3, G4):**

| Mode | Definition | Purpose |
|---|---|---|
| healthy | `h = 1` | nominal |
| static degradation | `h_i ~ U(0.1, 1.0)` | interpolates the whole range, incl. untrained values |
| total failure | `h_i = 0` | underactuated case |
| **onset (step)** | `h = 1` until `t_on ~ U(0, 0.4 T)`, then step to `U(0.1, 0.7)` or `0` | detection / adaptation / recovery |
| **incipient (ramp)** | `h` declines linearly to a final value over 50–200 s | slow-fault detection |

Training mixture (config-driven weights): e.g. 25% healthy / 35% static degradation / 20% dead /
20% onset. **The dead wheel must now actually appear in training** — otherwise "fault-tolerant"
is a misnomer.

**C5.2 Held-out test protocol (no cherry-picking):**

- **unseen severities**: `h = 0.82, 0.43, 0.17` (never exactly trained)
- **unseen onset times**: late faults, e.g. `t_on = 600 s`
- **unseen wheel index**: stratified across RW1/RW2/RW3 (note J and RW axes are not symmetric,
  so this is a real test)
- **unseen combinations**: two degraded wheels

**C5.3 Disturbance + plant uncertainty (G9, G10):**

| Item | Action |
|---|---|
| Aero / SRP / residual dipole | They are **not implemented** (`dynamics.py:136` returns GG only). Either implement them with config coefficients, or leave them off and **document that they are not modelled**. Do not claim them. |
| Domain randomization | mass ±10%, `J_xx/J_yy/J_zz` ±10%, RW `max_torque` ±10%, `max_speed` ±5% — cheap runtime perturbations, high academic value ("robust to model error, not only to faults"). |
| Wheel saturation (G12) | Replace the hard state clip with a motor torque roll-off near `Ω_max`, or at minimum document the inconsistency. |

Recommended: one `realism` variant of the best policy, compared against the nominal one, so the
effect is measurable rather than confounded.

### 2.7 C-I / Milestone C6 — Safety governor + classical fallback

The governor sits **between the policy and the allocator** and must be **physics-based, not
another neural network**.

```
   RL torque τ_des
        │
        ▼
  ┌──────────────────────────────────────────┐
  │  SAFETY GOVERNOR                         │
  │   • clip |τ| per axis & total             │
  │   • rate-limit ‖Δτ‖                       │
  │   • wheel-speed limit → taper wheel cmd   │
  │   • magnetic authority check (m×B)        │
  │   • ‖ω‖ > ω_emerg  → FALLBACK             │
  │   • ĥ confidence collapse → FALLBACK      │
  │   • attitude outside safe cone → FALLBACK │
  └───────────────┬──────────────┬───────────┘
                  │              │
            safe  │              │ unsafe / uncertain
                  ▼              ▼
            RL τ_des        LQR + B-dot  ← already implemented & validated (controllers.py)
                  \              /
                   ▼            ▼
              fault-tolerant allocator  (health inversion + MTQ residual + desaturation)
                   │
                   ▼
            RW1 RW2 RW3 + MTQ
```

**The fallback is free:** `ADCSController` (B-dot detumble → LQR) already exists and is validated
at ~75% success. It just needs to be wired into the RL path as the supervisor's escape route.
This directly answers "the satellite never has to blindly trust the neural network."

Note on hierarchy: the policy already solves detumble → acquisition → fine pointing *end-to-end*
from a random tumble, which is a **stronger** result than a mode manager. Recommendation:
**keep the single end-to-end policy** and let the classical controller serve as the *safety
fallback* rather than re-introducing a hierarchical mode manager in C-I. (A mode manager would be
a new architecture change, and C must close.) Report gated and ungated numbers separately so the
governor can't silently mask policy failures.

### 2.8 C-I / Milestone C7 — Recoverability map *(the highest-value scientific addition)*

**Problem (G11).** With one dead wheel the spacecraft is underactuated; magnetic torque is
instantaneously constrained to the plane ⊥ `B(t)` and only becomes useful over an orbit as `B`
rotates. Therefore **some initial conditions are physically unrecoverable within 900 s**, and
scoring them as controller failures is wrong.

**Definition:**

- `X_rec = { (θ₀, ω₀, orbit phase) : ∃ an admissible trajectory reaching and holding ‖θ‖ < 1° within T }`
- **Controller failure** = IC ∈ `X_rec` but the controller did not succeed.
- **Physically unrecoverable** = IC ∉ `X_rec` — **not penalized.**

**Estimating `X_rec` (a feasibility oracle, not the controller):**

1. **Primary:** a full-knowledge long-horizon trajectory optimiser / MPPI on the *true* model, with
   3× horizon and multiple restarts. If it cannot reach < 1°, label unrecoverable.
2. **Cross-check:** a **privileged** RL agent trained specifically with `h = 0` in the observation
   and a long horizon. Two independent oracles agreeing is a defensible feasibility argument.

**Deliverable:** a boundary map over `(‖θ₀‖, ‖ω₀‖)` (and orbit phase), plus a table:

| Quantity | Meaning |
|---|---|
| raw success % | over ALL ICs (honest, unflattering) |
| **conditional success %** | over `X_rec` only ← **the fair controller metric** |
| controller gap % | failures inside `X_rec` ← where research effort belongs |
| recoverable fraction | size of `X_rec` ← a *physics* statement about a 3-wheel satellite |

**This converts "RL got 12.5%" into:** *"RL learns to exploit the remaining controllability of an
underactuated spacecraft — and here is the boundary of what is physically possible at all."*
That is a far stronger thesis claim, and it is robust even if the recovery rate stays low.

### 2.9 C-I / Milestone C8 — Large-N Monte Carlo + metric suite

**Do not use n = 8 as the final number.** Target **N ≥ 500** ICs for final comparisons,
**N ≥ 1000** for the dead-wheel headline. Size N from the throughput measured in C1.3.

Use a **fixed IC set (common random numbers) across all controllers** so comparisons are
*paired*, then report bootstrap confidence intervals / a McNemar test rather than raw point
estimates.

**Metric suite (report all of it, per fault case):**

| Group | Metrics |
|---|---|
| Success | success %, **conditional success on `X_rec`**, controller gap % |
| Time | settling time: mean / median / p90 / p95 |
| Precision | final error mean / median / max; RMS error over the last 60 s |
| Rates | max ‖ω‖; max ‖ω_err‖ |
| Wheels | peak speed, % time at limit, saturation events, momentum redistribution |
| MTQ | total effort ∫‖m‖dt, peak dipole, duty cycle |
| Effort | ∫‖τ‖²dt; max ‖Δτ‖ (torque rate) |
| Onset cases | **detection time**, **adaptation time**, transient peak error, **recovery time** |
| Estimator | `ĥ` error, gyro-bias estimate error, attitude estimate error |

### 2.10 C-I / Milestone C9 — FREEZE: **Baseline C-Final**

Select **one** policy. The winner is the best *trade-off* — not the highest mean reward:

```
maximise:  conditional success on X_rec
         + healthy precision
         + unseen-fault robustness
         − MCU complexity (params, MACs, memory)
```

**Freeze all of the following, with a content hash:**

| Frozen item | Why |
|---|---|
| Policy weights + **architecture** (`2×64` or `2×128`) | the artifact itself |
| **Observation normalization constants** (`obs_rms.mean/var` from VecNormalize) | ⚠️ **part of the controller** — forgetting these on the MCU silently breaks it |
| Deterministic action path (mean, not sampled) | inference is deterministic |
| Action → torque mapping (`a · tau_scale · τ_max`) and clipping | interface spec |
| Reward + success definitions | so results stay comparable |
| Fault distribution + test protocol | so the test set can't drift |
| `ĥ` estimator + governor parameters | deployment behaviour |
| IC seed list for Monte Carlo | reproducibility |

**Architecture size rule:** do **not** grow the network dramatically. Sweep `64×64 → 128×64 →
128×128` and **stop at saturation**. The current 2×64 MLP is a *feature* for MCU deployment
(~5 k parameters). There is no reason to put a transformer on a CubeSat.

### 2.11 C-II / Milestone C10 — SIL on the frozen artifact

**No architecture changes are permitted in C-II.** Only the execution path changes.

| Task | Detail |
|---|---|
| C10.1 | Export the frozen policy to a portable form (ONNX → C, or TFLite-Micro-compatible) |
| C10.2 | **INT8 post-training quantization**; quantify action error: `max‖Δτ‖`, % of steps within ε, and closed-loop impact |
| C10.3 | **Bake the normalization constants** into the embedded path; verify obs preprocessing matches MIL bit-for-bit at a set of test points |
| C10.4 | Run the **closed loop on the host through the exact embedded inference library** (SIL): same simulator, same fault suite, same ICs |
| C10.5 | Measure per-step inference latency (mean / max / p99), jitter, flash/RAM footprint |
| C10.6 | Compare **SIL vs MIL**: success within ±2 pp, trajectory deviation bounded, action error distribution documented |

**Exit:** the frozen policy runs through its embedded code path and reproduces MIL performance.
This proves deployment won't change the result *before* touching hardware.

### 2.12 Explicitly OUT of scope for Phase C (the cut list)

✅ **Keep:** desired-torque interface · 3 RW + 3 MTQ · 24U plant · PPO as Baseline C · small MLPs ·
shared allocator · `ĥ` (never `h_true`) into the deployed policy.

❌ **Cut from C:** mandatory SAC · AdaJEPA · a 4th reaction wheel · a plant rewrite · large networks ·
a hierarchical mode manager · sensor faults beyond the gyro-bias fix.

> **SAC is a *challenger*, not a gate.** Run it only if time remains after E1–E12; the frozen
> baseline is whichever policy wins the controlled comparison — PPO is allowed to win.
> **Sensor faults** (mag dropout, sun-sensor loss): establish *actuator* fault tolerance first,
> then *sensor*, then *combined* — never all at once, or you won't know why the controller failed.
> For C, sensor faults are documented future work.

---

## 3. Phase D — MCU implementation + HIL

**Starts only after the Phase C gate is fully satisfied.** Phase D uses the **frozen** artifact
and the **same** fault suite and IC list.

### 3.1 Target selection (decision required)

| Option | Rationale | Notes |
|---|---|---|
| **ESP32-S3** | ✅ recommended — in-house toolchain experience (ESP-IDF, RadioLib), FPU + vector extensions, ample for a ~5 k-parameter MLP, cheap and available | INT8 via ESP-DL / TFLite-Micro-ESP, or plain float32 (comfortably fast at 5 Hz) |
| STM32F4/H7 | Classic aerospace-adjacent choice, CMSIS-NN support | more peripheral bring-up effort |
| Anything else | — | not recommended; no benefit for a 5 Hz loop |

### 3.2 Build order

| Step | Deliverable |
|---|---|
| **D1** | **Interface freeze**: sensor packet → MCU, torque packet → plant. Framing, CRC, timestamps, sample rate. Documented in `docs/DEPLOYMENT_INTERFACE.md`. |
| **D2** | **Port to C**: estimator (`ĥ`; MEKF or the documented equivalent), policy inference, safety governor, allocator. All parameters from a generated header (hash-matched to the frozen bundle). |
| **D3** | **Bench characterization**: WCET per control step, jitter, stack/flash/RAM usage, worst-case inference time. Must be ≪ the 200 ms control period. |
| **D4** | **HIL loop**: PC simulator ⇄ UART/UDP ⇄ MCU, closed at 5 Hz; log MCU timestamps + both states. Verify real-time behaviour and that comms latency is measurable and small. |
| **D5** | **Embedded fault injection at two levels**: (a) software — override `h`; (b) **hardware** — relay/MOSFET on a wheel driver line, or force a wheel to a fixed torque, and observe the loop's detection and recovery. |
| **D6** | **HIL vs SIL vs MIL**: trajectory deviation, success/conditional-success parity, latency-induced tracking error. |

### 3.3 Exit criteria

- The frozen policy runs in **real time** on the MCU with measured, documented timing and memory.
- HIL reproduces SIL/MIL performance within a stated tolerance on the same fault suite.
- At least one fault injected at the **hardware** level is detected and handled.
- Every number is reproducible from a documented command + frozen config hash.

---

## 4. Phase E — Thesis freeze, reports, defence

Phase E **freezes the evidence**, it does not produce new results.

| Task | Detail |
|---|---|
| E1 | Final experiment matrix — every table/figure traceable to a command and a config hash |
| E2 | Regenerate **all** plots and tables from one frozen results bundle (no hand-edited numbers) |
| E3 | Architecture diagrams: MIL, SIL, HIL; controller diagram; fault taxonomy |
| E4 | Results chapters: baselines (LQR, PPO), ablations, recoverability, safety, SIL, HIL |
| E5 | **Limitations chapter written honestly**: `n` and CIs, unrecoverable set, unimplemented disturbances (G9), wheel-speed clip (G12), estimator assumptions, seen-vs-unseen fault gap |
| E6 | Persian reports (`.docx`, RTL) via the existing `reports/post_process_rtl.py` pipeline, from Pouria's own first-person voice |
| E7 | Defence package: slides, likely examiner questions with prepared answers, live demo scripts |
| E8 | **Reproducibility package**: seeds, IC list, configs, environment, one-command rerun; publish frozen weights as a GitHub Release (they are `results/`-gitignored on purpose) |

**Exit:** a defence-ready package in which every claim maps to a reproducible artifact.

---

## 5. Phase F — World-model research arm (optional; must not gate D or E)

**Rule:** F replaces **only the intelligence block**. `MEKF → ĥ → governor → allocator → plant →
evaluation → HIL` all stay frozen. That is what makes the comparison clean, and it is why F can be
done *after* D and E without destabilizing them.

```
Baseline C-Final:     state ──► PPO ──► τ_des ──┐
                                                ├──► governor ──► allocator
Phase F:              history ──► encoder ──► z ─┤
                                 │              │
                                 ▼              │
                        adaptive world model ───┘
                                 │
                              MPC ──► τ_des
```

| Sub-phase | Content | Role in thesis |
|---|---|---|
| **F0** | **Frozen** JEPA-style latent world model + MPC (learned, then frozen) | **Baseline B** — the frozen-model comparison arm |
| **F1** | **AdaJEPA-style adaptive model + MPC**: `f = f_nominal + Δf_adaptive`, with `‖Δf‖ ≤ Δ_max` and a confidence measure; high confidence → adaptive model, low → nominal | **the contribution** |
| **F2** | Evaluation **specifically on faults unseen in training** (severities, onset times, wheel indices, combinations) | the novelty claim |

**Narrative this produces:**

| Method | Story |
|---|---|
| LQR | works on the nominal model, fails under severe actuator fault |
| PPO | learns a policy over randomized faults — but the knowledge is baked into weights |
| Frozen JEPA+MPC | learns a model, and *assumes it stays valid* |
| **AdaJEPA+MPC** | **observes model mismatch → adapts latent dynamics → MPC replans → handles unseen fault severity** |

**Safety constraint (must be stated):** AdaJEPA may never freely rewrite the model online.
Nominal + bounded adaptive residual, confidence-gated, with the same governor and LQR fallback
underneath. Anything else is not defensible for a flight system.

**If time runs out:** Phase F is documented as future work and **E proceeds regardless.** F must
never be the reason the thesis is unfinished.

---

## 6. Decision discipline — what must NOT change

**Three firm decisions:**

1. **Keep 3 reaction wheels.** One dead wheel ⇒ underactuated ⇒ MTQ provides time-varying auxiliary
   authority. That is the *interesting* fault, and it is already producing a real research
   question. A 4th wheel would delete the most interesting physics. (A 4-wheel study can appear
   later as *"effect of actuator redundancy on fault-tolerant RL"* — not as a redesign.)
2. **Do not abandon PPO.** It works. PPO is Baseline C; SAC is a challenger.
3. **Do not jump to AdaJEPA before the baseline experiments are finished.** AdaJEPA is Phase F.

**And the architectural rule that protects the whole thesis:**

> The RL block outputs a **desired body torque**, never raw actuator commands. Everything below it
> — safety, allocation, saturation handling, magnetic geometry — stays physics-based and shared
> with the classical controller. That single decision is what makes every comparison in this
> project clean, and it is already in place.

---

## 7. Rough schedule & compute budget

Training cost is *not* the bottleneck (≈ 2270 fps ⇒ 2 M steps ≈ 13 min). Implementation and
analysis dominate.

| Milestone | Sessions (≈ one evening each) | Compute |
|---|---|---|
| C1 truth + regeneration | 0.5 | minutes |
| C2 estimator + `ĥ` | 1 – 1.5 | minutes |
| C3 observation ablation | 0.5 | ~4 × 13 min |
| C4 reward ablation | 0.5 | ~6 × 13 min |
| C5 fault v2 + onset + uncertainty | 1 | ~4 × 13 min |
| C6 governor + fallback | 1 | minutes |
| C7 recoverability map | 1 – 2 | oracle is the heavy item |
| C8 Monte Carlo (N ≥ 500) | 0.5 | size after C1.3 |
| C9 freeze | 0.5 | — |
| C10 SIL | 1 – 2 | minutes |
| **Phase C total** | **≈ 8 – 11** | |
| Phase D (MCU + HIL) | 3 – 5 | hardware time dominates |
| Phase E (thesis freeze) | 3 – 4 | — |
| Phase F (if time) | 4 – 8 | training-heavy |

---

## 8. Risk register

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | Dead-wheel recovery stays low even after training on `h = 0` | headlining "12.5%" looks weak | **the recoverability map (C7)** reframes it as a physics boundary + conditional success rate |
| R2 | The ablation shows the jump was **not** reward shaping (e.g. it was the corrected control rate) | the Phase 2 narrative changes | report it; the claim simply changes to whatever the data says. This is why C4 exists. |
| R3 | `ĥ` is unobservable when a wheel is never commanded | policy gets bad fault input | excitation gating + confidence flag + governor fallback; report `ĥ` quality |
| R4 | The safety governor masks policy failures | inflated numbers | **always report gated AND ungated** |
| R5 | Scope creep — C never closes | the real project risk | the C12 exit table + §2.12 cut list + the C-I/C-II gate |
| R6 | `C:` drive nearly full; results grow | build failures | keep results/venv/caches on `E:` (`E:/pip-cache`, `E:/pip-tmp`) |
| R7 | Hardware (MCU) delays HIL | schedule slip | D2–D3 (port + bench timing) have no hardware dependency beyond the dev board; SIL (C10) already de-risks the numerical path |

---

## 9. Open decisions — need Pouria's answer before C-I starts

| # | Question | My recommendation |
|---|---|---|
| **Q1** | Target MCU: **ESP32-S3**, STM32, or decide at Phase D? | **ESP32-S3** |
| **Q2** | Accept the **recoverability-map** framing, knowing it may *lower* the headline success numbers while strengthening the science? | **Yes** |
| **Q3** | Include **plant-parameter randomization** (mass/J/torque ±10%) in C, or keep fault-only? | **Include** as a separate measured variant |
| **Q4** | Is **Baseline B (frozen JEPA+MPC)** required in the thesis, or strictly optional inside Phase F? | required **if** F is executed; otherwise documented as future work |
| **Q5** | Any **hard deadline** for the defence that should size Phase D/E against Phase F? | needed to answer |
| **Q6** | Is a real reaction-wheel/MTQ hardware bench available, or is HIL simulation-only (MCU in the loop, no real actuators)? | determines D5's depth |

---

## 10. If you say "go" — the first five actions

1. **C1** — regenerate M1 and Phase 1B on the corrected time base, and measure eval throughput.
2. **C2** — implement and validate the health estimator `ĥ` on the three fault cases.
3. **C3** — run the cheapest high-value experiment: **O1 (`ĥ` added to the observation)**; does the
   policy even benefit from knowing the fault?
4. **C4** — run the reward/normalization 2×2 ablation to attribute the Phase 2 gain.
5. **C5** — implement fault **onset** and the unseen-severity test protocol.

Then the gate: freeze, regenerate MIL, and only then enter C-II (SIL).

---

*End of plan. No code has been written for Phases C–F. Implementation begins on explicit approval.*
