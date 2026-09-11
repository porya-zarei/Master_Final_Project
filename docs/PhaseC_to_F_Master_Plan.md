# Phase C → F Master Plan — Authoritative Execution Roadmap

```text
STATUS:                 PLAN FINALIZED
EXECUTION AUTHORIZATION: C1 + C4.1 ONLY
VERSION:                2  (supersedes v1 draft)
```

**Fault-Tolerant Attitude Control of Nanosatellites Using Reinforcement Learning: From Simulation to Hardware-in-the-Loop**

- **Author:** Pouria Zarei (810103137) — M.Sc. Control Engineering, University of Tehran
- **Advisor:** Dr. Mohammad-Javad Yazdanpanah
- **Date:** 2026-09-11
- **Supersedes:** `docs/archive/PhaseC_to_F_Master_Plan_v1_SUPERSEDED.md` (v1 draft — contains a known-incorrect success-rate claim; do not implement from it)

> ### ⚠️ Authorization boundary — read before doing anything
>
> Finalizing this roadmap is **not** authorization to implement it.
>
> **Approval of Phase C does NOT mean approval of all of Phase C.**
> The **only** currently authorized actions are **C1** and **C4.1** (§2).
> Every other milestone in this document is *described* but **NOT authorized** (§0.4).
> A task is not "done" because it appears in this plan.

---

## 0. How to read this document

### 0.1 Document authority

This file is the **single authoritative execution roadmap** for the remainder of the project.

| Document | Status |
|---|---|
| **`docs/PhaseC_to_F_Master_Plan.md`** (this file) | ✅ **AUTHORITATIVE** |
| `docs/archive/PhaseC_to_F_Master_Plan_v1_SUPERSEDED.md` | ⛔ superseded draft — audit history only |
| `docs/ADCS_Phase1_Plan.md` | 📜 historical — Phase 1, **completed**; not a C→F roadmap |
| `codes/docs/Phase2_RL_RewardShaping_Plan.md` | 📜 historical — Phase 2, **completed**; not a C→F roadmap |

No other document may be treated as a C→F roadmap. If a future plan is written, it must update
this file rather than sit beside it.

### 0.2 Authoritative phase definitions

| Phase | Definition | Blocking? |
|---|---|---|
| **Phase C** | Final baseline-controller research, validation, **freeze**, MIL regeneration, and **SIL** | required for D |
| **Phase D** | **MCU implementation + HIL** | required for E |
| **Phase E** | Thesis / report / defence / reproducibility **freeze** | required for defence |
| **Phase F** | **Optional** world-model research arm: frozen JEPA+MPC → AdaJEPA+MPC | 🚫 **never blocking** |

**Phase C is split by a hard gate** (§3):

```
   C-I  FREEZE  ──────────►  ⛔ FREEZE GATE  ──────────►  C-II  SIL
 architecture may still      artifact + definitions        NO architecture
 change (evidence-driven)    frozen; MIL regenerated       changes allowed
```

> After the freeze gate, **no architecture changes are allowed** in C-II/SIL or D/HIL, except
> implementation/deployment changes required to execute the frozen artifact.

### 0.3 Numbering caution

Earlier advisory material used the letters **C/D/E/F for different content** (notably *D = frozen
world model, E = AdaJEPA, F = safety gate*). Those are **not** the definitions here. Every item of
that material lives in **Phase C** (freeze/SIL), **Phase F** (world models), or the safety governor
(§2 step 6). **Ignore the other lettering.**

### 0.4 Authorization status at a glance

Legend: `[DONE]` completed with evidence · `[AUTHORIZED]` may be executed **now** ·
`[PLANNED]` described but **NOT authorized** · `[OPTIONAL]` time-permitting ·
`[GATE]` hard blocking gate · `[NEVER-BLOCK]` must never block thesis/HIL.

| Item | Status |
|---|---|
| M0 simulator · M1 LQR · Phase 1B fault model · Phase 2 shaped PPO vs LQR | `[DONE]` |
| **C1 — truth/regeneration on the corrected time base** | 🟩 **`[AUTHORIZED]`** |
| **C4.1 — attribution of the Phase-B improvement** | 🟩 **`[AUTHORIZED]`** |
| C2-h — health-estimator investigation + integration | `[PLANNED]` |
| C3a — O1-H privileged-health diagnostic | `[PLANNED]` |
| C3b — O1-E estimated-health deployment experiment | `[PLANNED]` |
| Complete observation sweep (O2/O3) | `[PLANNED]` |
| C4.2 — optional reward refinement (incremental) | `[PLANNED]` / `[OPTIONAL]` |
| C6 — safety governor + LQR/B-dot fallback | `[PLANNED]` |
| C2-e — full MEKF **or** documented estimator alternative | `[PLANNED]` |
| C5 — fault-onset / plant uncertainty / final validation | `[PLANNED]` |
| C7-lite — recoverability on failed dead-wheel ICs | `[PLANNED]` |
| C7-full — recoverability map over the whole state space | `[OPTIONAL]` |
| C8 — Monte Carlo, N sized from measured throughput | `[PLANNED]` |
| C9 — **FREEZE Baseline C-Final** | ⛔ `[GATE]` |
| C10 — SIL on the frozen artifact | `[PLANNED]` (after gate) |
| Phase D — MCU + HIL | `[PLANNED]` (after C) |
| Phase E — thesis/defence freeze | `[PLANNED]` (after D) |
| Phase F — JEPA / AdaJEPA | 🔵 `[OPTIONAL]` · `[NEVER-BLOCK]` |
| **Not initially authorized:** full MEKF implementation · complete health-estimator integration · complete observation sweep · reward-v2 redesign · full recoverability oracle · large final Monte Carlo · SIL · MCU work · AdaJEPA | 🚫 **hold** |

### 0.5 Firm architectural decisions (not open for revision)

1. Keep **3 reaction wheels + 3 magnetorquers** (no 4th wheel).
2. RL outputs **desired body torque**, never raw actuator commands.
3. Keep the **shared physics-based fault-tolerant allocator**.
4. Keep **PPO as the official Baseline C candidate**.
5. **SAC is a challenger only** — never mandatory.
6. **AdaJEPA must never gate Phase D or Phase E.**
7. The **safety governor is physics-based**, never another neural network.
8. **Classical LQR / B-dot remains the fallback and reference controller.**
9. The deployed policy **never receives `h_true`** — it uses estimated actuator health `h_hat`.
10. **ESP32-S3 is the preferred MCU/HIL target** — an experimental embedded-control and HIL
    platform, **not a flight-qualified spacecraft OBC** (see §5.1).

### 0.6 Why the current PPO is not freezable as-is

Freezing the existing policy as "the reference architecture" would bake four defects into the thesis:

| Defect | Evidence |
|---|---|
| Never saw `h_hat` — **blind to the fault it is meant to tolerate** | `adcs_env.py:117` obs = `[θ(3), ω_err(3), Ω_rw(3)]`; health appears only in `info` |
| **Never trained on a dead wheel** | `config/rl.yaml` → `health_range: [0.5, 1.0]` |
| Scored on **n = 8** initial conditions | `eval_rl_vs_lqr.py --n 8` |
| The gain came from **5 simultaneous changes** → demonstrated but **unattributed** | Phase-B history |

**Removing these four defects is what Phase C is for.**

### 0.7 What changed in v2 (vs the superseded v1 draft)

| # | Change |
|---|---|
| 1 | **Removed** the incorrect claim that the time-base fix caused 83.3% → 75% (§2.2). Success is threshold-based; the two numbers also came from different sample sizes (n=6 vs n=8). |
| 2 | C-I converted from a **12-item checklist** into an **evidence-driven decision tree** (§2.1). |
| 3 | **Execution narrowed to C1 + C4.1 only**, with an explicit not-authorized list (§0.4). |
| 4 | **C4.1 = attribution only.** Reward v2 is now a separate, later, optional **C4.2**, applied one term at a time. |
| 5 | **O1 split** into `O1-H` (privileged `h_true`, upper bound) and `O1-E` (deployable `h_hat`) — never merged. |
| 6 | **Estimator ordering reversed**: MEKF now comes *after* attribution and the health-estimator work, not before (§2). |
| 7 | Health estimator: body-rate equation demoted from "second estimator" to **sanity cross-check only**. |
| 8 | Recoverability: full oracle map → staged **C7-lite** first; full map optional. |
| 9 | Monte Carlo: fixed `N ≥ 1000` removed; **N sized from measured throughput**. |
| 10 | SIL parity: **±2 pp only for common cases**; low-success cases use CI overlap / paired tests / trajectory deviation. |
| 11 | ESP32-S3 explicitly **not a flight-qualified OBC**. |
| 12 | D5 defaults to **software fault injection**; physical actuator bench is optional. |

---

## 1. Verified current state — code audit

Verified by reading the code on 2026-09-11, not from memory.

### 1.1 What is `[DONE]`

| Component | File | Evidence |
|---|---|---|
| Plant: 24U, 35 kg, `J = diag(0.38, 0.73, 0.58)` | `config/satellite.yaml` | config-driven; random IC on SO(3); `ω_max = 5°/s` |
| Euler + MWM dynamics, inertia coupling `−ω×H` | `dynamics.py` | `τ = −ω×H + τ_rw,eff + τ_mtq + τ_dist` |
| Gravity-gradient torque | `dynamics.py:139` | `3μ/r³ · r̂ × (J r̂)` |
| Tilted-dipole B-field (11.5°) | `dynamics.py:119` | `B_body()` |
| Sensors: gyro, mag, sun, star tracker, GPS | `config/sensors.yaml` | ST 5e-5 rad; gyro 1e-4 rad/s **+ declared bias 1e-3 rad/s** |
| Actuators: 3 RW (10 mN·m, 628 rad/s) + 3 MTQ (1 A·m²) | `config/actuators.yaml` | |
| Fault model `τ_actual = h·τ_cmd`, `h ∈ [0,1]` | `dynamics.py:158` | continuous |
| Fault-tolerant allocator (health inversion + MTQ residual + desaturation) | `controllers.py:24` | **shared by LQR and RL** |
| B-dot detumble → LQR phase manager | `controllers.py:51` | detumble threshold 0.3°/s, `k_bdot = 1e4` |
| Nadir guidance (LVLH from orbit, recomputed every step) | `guidance.py` | not a fixed attitude |
| RL env: 9-dim obs, 3-dim action (desired torque) | `adcs_env.py` | `Box(-10,10,(9,))`, `Box(-1,1,(3,))` |
| Shaped reward `−‖θ‖² − 0.1‖ω_err‖² − 0.01‖a‖² + 1·1[‖θ‖<1°]` | `adcs_env.py:126` | YAML knobs in `config/rl.yaml` |
| Time-axis fix | `simulate.py:50` | **in code** (`nctrl = max(1, round((1/hz)/dt))`, `t += ctrl_period`) |
| Phase-B result: PPO beats LQR on all 3 fault cases | `results/rl_eval_shaped/` | 100%/0.17° vs 75%/0.73°; dead wheel 12.5% vs 0% |

> Milestones above are marked `[DONE]` **because they were run and produced evidence.**
> Nothing else in this document may be marked done on the strength of being described here.

### 1.2 Corrected audit — what is NOT done (G1–G12)

| # | Gap | Verified evidence | Consequence |
|---|---|---|---|
| **G1** | **`MEKF` is a stub.** The class is *named* `MEKF` but is star-tracker passthrough + raw gyro. `propagate()` is a **no-op**, `update_vector()` returns `self`; no bias state, no covariance. | `estimation.py` (40 lines); docstring admits *"bias small and neglected here"* while `sensors.yaml` **declares a 1e-3 rad/s gyro bias** | A thesis claiming MEKF must have one — or must not claim it |
| **G2** | **The policy is fault-blind.** `h` appears only in `info["rw_health"]`, never in the observation. | `adcs_env.py:117` | States identical in `(θ, ω, Ω)` but differing in `h` demand different actions; the policy cannot tell them apart. This is *the* fundamental limit on fault adaptation. |
| **G3** | **The dead wheel was never trained.** `health_range: [0.5, 1.0]`. | `config/rl.yaml` | The 12.5% dead-wheel figure is **zero-shot generalization**, not training performance. Must be stated as such. |
| **G4** | **Health is constant for the whole episode.** Sampled once in `reset()`. | `adcs_env.py:152` | No fault onset ⇒ no detection time, adaptation transient, or recovery metric |
| **G5** | **Reward has no safety / saturation / rate terms.** `w_ctrl` penalizes the **normalized action `a`**, not physical torque; no wheel-speed penalty; no `Δτ` penalty. | `adcs_env.py:126–142` | Nothing discourages wheel saturation or jerky torque — both undesirable on an MCU |
| **G6** | **No safety governor, no fallback.** Action is clipped to `[-1,1]`; nothing else supervises it. | `adcs_env.py:162` | Required before deployment. The validated `ADCSController` (B-dot+LQR) exists but is **not wired to the RL path** |
| **G7** | **Evaluation is n = 8.** | `eval_rl_vs_lqr.py --n 8` | Not a defensible headline number |
| **G8** | **M1 and Phase-1B numbers predate the time-axis fix.** | `results/m1_validation_60/` (Sep 8), `results/fault_experiment/` (Sep 10); fix landed in `4502482` | **Corrected interpretation (v1 was wrong):** the time-axis bug primarily **inflated settling-time measurements**. Success is **threshold-based** (reached tolerance within horizon) and therefore **should not automatically change** because of the time-axis correction. The previously quoted **83.3% and 75% also came from different sample sizes (n = 6 vs n = 8)**. Any change in success after regeneration must be **measured and attributed to the actual experiment/configuration** — never silently credited to the time-base fix. |
| **G9** | **Aero / SRP / residual-dipole torques are flags with no implementation.** | `dynamics.py:71–73` read the flags; `disturbance_torque()` (line 136) returns **gravity-gradient only** (`# add later if needed`) | Enabling them in YAML currently does **nothing**; their effects cannot be claimed |
| **G10** | **No plant uncertainty.** Only fault health is randomized. | `satellite.yaml`, `actuators.yaml` | A controller robust to faults but not to a ±10% inertia error is not deployable |
| **G11** | **No definition of physical recoverability.** "Success" for a dead wheel is demanded over *all* ICs. | `eval_rl_vs_lqr.py:61` — `success = not isinf(settling_time)` over the whole sample | With one dead wheel the system is underactuated; some ICs are **physically unreachable in 900 s**. Counting those as controller failures understates the contribution and is scientifically wrong. |
| **G12** | **Wheel speed is clipped as a state, not modelled.** | `dynamics.py:197` — `omega_w = clip(±max_speed)` | Silently destroys wheel momentum at saturation (violates `H` conservation). Acceptable placeholder; must be documented, ideally replaced by motor torque roll-off. |

---

## 2. Phase C — the evidence-driven workflow

> **C-I does not require C1–C12 regardless of results.** C1 and C4.1 run first; **their evidence
> determines which subsequent experiments are necessary** to finalize the architecture.
> Milestones after the first decision gate are planned, not committed.

### 2.1 The workflow

```text
  ┌──────────────────────────────────────────────────────────────┐
  │  STEP 1   C1    truth / regeneration        🟩 AUTHORIZED NOW │
  └───────────────────────────┬──────────────────────────────────┘
                              ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  STEP 2   C4.1  attribution of Phase-B      🟩 AUTHORIZED NOW │
  └───────────────────────────┬──────────────────────────────────┘
                              ▼
        ╔══════════════════════════════════════════════╗
        ║  DECISION GATE A — review the evidence       ║
        ║  decide which of steps 3–12 are necessary    ║
        ╚══════════════════════════════════════════════╝
                              ▼
     3.  C2-h  health-estimator investigation        [PLANNED]
                              ▼
     4.  C3a   O1-H  (privileged h_true upper bound) [PLANNED]
                              ▼
     5.  C3b   O1-E  (deployable h_hat)              [PLANNED]
                              ▼
     6.  C6    safety governor + LQR/B-dot fallback  [PLANNED]
                              ▼
     7.  C2-e  MEKF or documented alternative        [PLANNED]
                              ▼
     8.  C5    fault-onset / uncertainty / validation[PLANNED]
                              ▼
     9.  C7-lite  recoverability on failed dead-wheel ICs   [PLANNED]
                              ▼
    10.  C8    Monte Carlo — N sized from throughput  [PLANNED]
                              ▼
    11.  C9    ⛔ FREEZE Baseline C-Final              [GATE]
                              ▼
    12.  C10   SIL on the frozen artifact             [PLANNED]
```

**Step ordering is load-bearing, not cosmetic.** See §2.6 for why the estimator work sits *after*
attribution.

### 2.2 STEP 1 — C1: truth and infrastructure 🟩 `[AUTHORIZED]`

**Nothing else in this plan is trustworthy until C1 is done.**

| Task | Detail |
|---|---|
| C1.1 | Regenerate **M1 (LQR)** on the corrected time base |
| C1.2 | Regenerate **Phase 1B** (3 fault cases) on the corrected time base |
| C1.3 | **Measure evaluation throughput** (episodes/min, scaling across the 24 cores) so Monte-Carlo size can be *sized honestly* rather than guessed |
| C1.4 | Fix the stale docstring in `estimation.py` ("at the control rate (4 Hz)") to match the real 5 Hz |

**C1 must report these separately — never as a single blended number:**

| Reported quantity |
|---|
| success rate |
| settling time |
| median settling time |
| p90 / p95 settling time |
| final pointing error |

> ### 🚩 Correction carried into v2
>
> **The time-base correction is expected to primarily reduce reported settling times.
> Any change in success rate must be measured and separately explained.**
>
> Success is a **threshold** criterion, so it should not automatically move because the time axis
> was fixed. The earlier 83.3% and 75% figures additionally came from **different sample sizes
> (n = 6 vs n = 8)**, so they are not directly comparable in the first place. Regenerated numbers
> must be attributed to the actual experimental configuration — **not silently credited to the
> time-base fix.**
>
> **Do not hard-code an expected new success percentage anywhere in this project.**

### 2.3 STEP 2 — C4.1: attribution of the existing Phase-B result 🟩 `[AUTHORIZED]`

**Purpose:** answer exactly one question — *why did Phase-B PPO improve from ≈ 4° to ≈ 0.17°?*

**C4.1 is attribution only. It must not introduce a new controller, a new observation set, or a new reward.**

Test the contributing factors **independently**, holding everything else fixed:

| Factor | Levels |
|---|---|
| Reward shaping | classic quadratic **vs** tolerance-bonus |
| Reward normalization | `norm_reward` off **vs** on |
| Corrected control rate / timing | 5 Hz (corrected) **vs** 2 Hz (original) |
| Other simultaneous changes that produced the original Phase-B result | as identified in the Phase-B record |

```text
        C4.1
  Attribution of the existing
     Phase-B result
           │
           ▼
      DECISION  ← the evidence says which factor actually caused the gain
           │
           ▼
        C4.2                       ← only after attribution is understood
  Optional reward refinement
           │
           ▼
  Controlled single-factor
      experiments
```

**Rule:** the result of C4.1 is whatever the data says. If the gain turns out **not** to be reward
shaping (e.g. it was the corrected control rate), that is the finding — report it and adjust the
narrative. There is no obligation for reward shaping to be the answer.

### 2.4 DECISION GATE A

After C1 + C4.1, review the evidence and decide **which of steps 3–12 are actually necessary**.
Concretely, the evidence should answer:

1. Are the regenerated MIL numbers internally consistent across success / settling / p90 / final error?
2. Which single factor (or combination) caused the Phase-B gain?
3. Given (2), is a reward redesign (C4.2) justified — or was the original reward adequate once the
   timing was corrected?
4. Given (1)–(3), what is the minimum remaining C-I scope?
5. How much compute is needed for the Monte Carlo (from the C1.3 throughput measurement)?

Until this gate is passed, **steps 3–12 are not authorized.**

### 2.5 STEP 3 — C2-h: health-estimator investigation `[PLANNED]`

**Primary estimator — per-wheel recursive least squares on wheel acceleration vs commanded motor torque:**

```text
Jw * Omega_dot  ≈  -h_hat * tau_command
```

| Element | Requirement |
|---|---|
| Excitation gating | update **only** when `|τ_cmd,i| > τ_min` — a wheel that is never commanded cannot be identified |
| Filtered wheel-speed derivative | light low-pass (≈0.5 s) on the tacho derivative to fight noise |
| RLS forgetting factor | so the estimate tracks a **changing** health (fault onset) |
| Confidence estimate | `c_i ∈ [0,1]` from excitation + residual + time since detection |
| Low-confidence behaviour | **hold the last estimate** and flag to the governor — never fall back to a truth value |

**The body-rate equation is *not* an equally authoritative second health estimator.** It may be used
**only** as a physics-based residual / sanity cross-check, because it contains coupled terms that
make it poorly conditioned for direct health estimation:

- gravity-gradient torque
- magnetic torque
- inertia uncertainty
- wheel-momentum coupling
- measurement noise

> **Never feed `h_true` to the deployed controller — not in training-evaluation, not in SIL, not in
> HIL.** Privileged truth is permitted **only** inside the explicitly labelled `O1-H` diagnostic.

### 2.6 STEP 4 & 5 — C3a / C3b: the observation split `[PLANNED]`

The former single "O1" experiment wrongly mixed privileged and deployable information. **Split it.**

| Experiment | Observation | Purpose |
|---|---|---|
| **C3a — O1-H** | `O0 + h_true` | **Privileged upper bound / diagnostic.** What is the theoretical benefit of perfect actuator-health information? |
| **C3b — O1-E** | `O0 + h_hat` | **Deployment experiment.** Does the *deployable* health-estimation architecture provide useful fault information? |

where `O0 = [θ, ω_err, Ω_rw]` (the current 9-dim set).

> **`O1-H` and `O1-E` answer different questions and must never be merged into one experiment.**
> The gap between them quantifies *the cost of not knowing the fault* — which is itself a headline result.

Also test, where appropriate:

- estimator **confidence** as an input / gate
- estimator **error** sensitivity (how much `h_hat` error the policy tolerates)

Later observation sets (`O2 = O1 + B_body`, `O3 = O2 + τ_prev`) remain planned; whether they are run
depends on the C3b result.

**Why the estimator work is ordered after attribution (steps 3 → 7):** the current 0.17° PPO result
was produced **through the existing estimator path**. Replacing the estimator *first* would inject
another uncontrolled variable and could destroy or alter the demonstrated Phase-B result. Hence the
order `C1 → C4.1 → health estimator → O1-H → O1-E → governor → MEKF/alternative → fault-onset/validation`.

### 2.7 STEP 6 — C6: safety governor + classical fallback `[PLANNED]`

Physics-based, **not** another neural network, placed between the policy and the allocator:

```text
   RL torque τ_des
        │
        ▼
  ┌──────────────────────────────────────────┐
  │  SAFETY GOVERNOR                         │
  │   • clip |τ| per axis & total             │
  │   • rate-limit ‖Δτ‖                       │
  │   • wheel-speed limit → taper wheel cmd   │
  │   • magnetic authority check (m×B)        │
  │   • ‖ω‖ > ω_emerg        → FALLBACK       │
  │   • ĥ confidence collapse → FALLBACK      │
  │   • attitude outside safe cone → FALLBACK │
  └───────────────┬──────────────┬───────────┘
            safe  │              │ unsafe / uncertain
                  ▼              ▼
            RL τ_des      LQR + B-dot  ← already implemented & validated (controllers.py)
                  \              /
                   ▼            ▼
              fault-tolerant allocator
                   │
                   ▼
            RW1 RW2 RW3 + MTQ1 MTQ2 MTQ3
```

The fallback is **free**: `ADCSController` (B-dot detumble → LQR) already exists and is validated.
It only needs wiring into the RL path as the governor's escape route.

**Report gated and ungated results separately, always** — otherwise the governor can silently mask
policy failures (risk R4).

### 2.8 STEP 7 — C2-e: MEKF, or a documented estimator alternative `[PLANNED]`

| Option | What it is | Notes |
|---|---|---|
| **A — full MEKF** | attitude-error + gyro-bias states, star-tracker + vector updates, cross-covariance | Textbook-defensible; estimates the declared 1e-3 rad/s bias. Risk: large-angle acquisition observability |
| **B — documented alternative** | star-tracker attitude + a separate gyro-bias observer, gated on star-tracker validity | Simpler, no stability risk |

**Either is acceptable — silently shipping a `q_meas` assignment while calling it "MEKF" is not (G1).**
The thesis must state which was used. If the full MEKF becomes unstable or harmful during large-angle
acquisition, option B is the **documented** alternative — decided by measurement, not convenience.

**Before freezing, compare the old estimator path against the final estimator path** (risk R6).

### 2.9 STEP 8 — C5: fault-onset, uncertainty, final validation `[PLANNED]`

**Fault taxonomy:**

| Mode | Definition | Purpose |
|---|---|---|
| healthy | `h = 1` | nominal |
| static degradation | `h_i ~ U(0.1, 1.0)` | covers untrained severities |
| total failure | `h_i = 0` | underactuated case |
| **onset (step)** | healthy until `t_on ~ U(0, 0.4T)`, then step | detection / adaptation / recovery |
| **incipient (ramp)** | linear decline to a final value over 50–200 s | slow-fault detection |

**Held-out test protocol (no cherry-picking):** unseen severities (e.g. 0.82 / 0.43 / 0.17) ·
unseen onset times (e.g. `t_on = 600 s`) · unseen wheel index (RW1/RW2/RW3 are not symmetric) ·
unseen combinations (two degraded wheels).

**Plant uncertainty (decision Q3):** domain randomization on mass ±10%, `J_xx/J_yy/J_zz` ±10%,
RW `max_torque` ±10%, RW `max_speed` ±5% — as a **separate measured variant**, never silently mixed
into the frozen baseline.

**Disturbance realism (G9):** aero / SRP / residual dipole are **not implemented**. Either implement
them with config coefficients, or leave them off and **state that they are not modelled**. Do not claim them.
Optionally replace the wheel-speed state clip (G12) with a motor torque roll-off.

### 2.10 STEP 9 — C7-lite: recoverability, staged `[PLANNED]`

The recoverability concept is kept — it is scientifically valuable. **But a full MPPI +
privileged-RL map over the entire state space is NOT a mandatory Phase-C blocker.**

**C7-lite (mandatory if step 9 is authorized):**

1. Run the feasibility oracle **primarily on the failed dead-wheel initial conditions**.
2. Determine whether some of those failures are **actually physically recoverable**.
3. Report:

| Reported quantity |
|---|
| raw success (over all ICs — honest, unflattering) |
| the recoverable subset |
| **conditional success** (over the recoverable subset — the fair controller metric) |
| **controller failures within the recoverable subset** (where research effort belongs) |

`X_rec = { (θ₀, ω₀, orbit phase) : ∃ an admissible trajectory reaching and holding ‖θ‖ < 1° within T }`

**C7-full (optional enhancement only):** expand to a complete map over
`θ₀`, `ω₀`, and orbit phase / B-field geometry — **only if C7-lite produces a meaningful result.**
The full map is a research enhancement, **not** a prerequisite for MCU/HIL.

If C7-lite shows the dead-wheel failures are genuinely unrecoverable, the honest framing is still a
result: *the recoverable set of a 3-wheel satellite with one dead wheel is small, and here is its boundary.*

### 2.11 STEP 10 — C8: Monte Carlo, sized by measurement `[PLANNED]`

**First measure simulation throughput (C1.3). Then choose N** from:

- available compute
- confidence-interval width actually achieved
- expected effect size
- project schedule

> There is **no unconditional `N ≥ 1000` requirement**, and an arbitrary large N does **not**
> automatically make a result rigorous.

Required methodology regardless of N:

- **common random numbers / fixed IC sets** across all controllers
- **confidence intervals**
- **paired comparisons** where applicable

### 2.12 STEP 11 — C9: the freeze `[GATE]`

Select **one** policy by trade-off — not by highest mean reward:

```
maximise:  conditional success on X_rec
         + healthy precision
         + unseen-fault robustness
         − MCU complexity (params, MACs, memory)
```

**Freeze, each with a content hash:**

| Frozen item | Why |
|---|---|
| Policy weights + architecture | the artifact |
| **Observation-normalization constants** (`obs_rms.mean/var`) | ⚠️ **part of the controller** — omitting them on the MCU silently breaks it |
| Deterministic action path (mean, not sampled) | inference must be deterministic |
| Action → torque mapping (`a · tau_scale · τ_max`) + clipping | interface spec |
| Reward + success definitions | keeps results comparable |
| Fault distribution + held-out test protocol | prevents test-set drift |
| `h_hat` estimator + governor parameters | deployment behaviour |
| IC seed list | reproducibility |

**Network size:** do **not** grow it dramatically. Sweep `64×64 → 128×64 → 128×128` and **stop at
saturation**. The current 2×64 MLP (~5 k parameters) is a *feature* for MCU deployment.

**Freeze gate definition:** C-I is complete only when the frozen artifact, the frozen definitions and
the regenerated MIL numbers all exist. C-II may not begin before that.

### 2.13 STEP 12 — C10: SIL on the frozen artifact `[PLANNED]`

**No architecture changes in C-II.** Only the execution path changes.

| Task | Detail |
|---|---|
| C10.1 | Export the frozen policy to a portable form (ONNX → C, or TFLite-Micro-compatible) |
| C10.2 | **INT8 post-training quantization**; quantify action error `max‖Δτ‖`, % steps within ε, and closed-loop impact |
| C10.3 | **Bake the normalization constants** into the embedded path; verify obs preprocessing matches MIL at a set of test points |
| C10.4 | Run the closed loop through the **exact embedded inference library** (SIL): same simulator, fault suite, ICs |
| C10.5 | Measure per-step inference latency (mean / max / p99), jitter, flash/RAM footprint |
| C10.6 | Compare **SIL vs MIL** using the criteria in §4 |

### 2.14 Scope-cut rules for Phase C

✅ **Keep:** desired-torque interface · 3 RW + 3 MTQ · 24U plant · PPO as Baseline C · small MLPs ·
shared allocator · `h_hat` (never `h_true`) in the deployed policy.

❌ **Cut from C:** full MEKF as a prerequisite · mandatory SAC · AdaJEPA · a 4th reaction wheel ·
plant rewrite · large networks · hierarchical mode manager · full recoverability oracle ·
sensor faults beyond the gyro-bias fix · any unconditional large-N mandate.

> **SAC is a challenger, not a gate.** Run it only if time remains after the C-I work; the frozen
> baseline is whichever policy wins the controlled comparison — **PPO is allowed to win.**
> **Sensor faults** (mag dropout, sun-sensor loss): establish *actuator* fault tolerance first, then
> *sensor*, then *combined* — never all at once, or you will not know why the controller failed.

---

## 3. The freeze gate and the hard architectural rule

```text
                  ┌───────────────┐
state estimate ──►│ RL / future   │
health estimate ─►│ intelligence  │
                  └───────┬───────┘
                          │ desired body torque
                          ▼
                  ┌───────────────┐
                  │ Safety        │
                  │ Governor      │
                  └───────┬───────┘
                          ▼
                  ┌───────────────┐
                  │ Fault-tolerant│
                  │ Allocator     │
                  └───────┬───────┘
                     ┌────┴────┐
                     ▼         ▼
                  RW1/RW2/RW3  MTQ1/2/3
```

> **After the freeze gate, no architecture changes are allowed in C-II/SIL or D/HIL, except
> implementation/deployment changes required to execute the frozen artifact.**

This diagram is the contract. Everything below the intelligence block — safety governor, allocator,
saturation handling, magnetic geometry — stays physics-based and shared with the classical
controller. That single decision is what keeps every comparison in this project clean.

---

## 4. SIL success criteria

| Case | Criterion |
|---|---|
| **Sufficiently common cases** (healthy, 50% degradation) | **±2 percentage points** vs MIL is acceptable |
| **Low-success / rare cases** (e.g. dead-wheel recovery ≈12%) | ⚠️ **±2 pp is NOT a valid criterion** — at that rate, one or two episodes swing the number by >10 pp |

For low-success cases use instead:

- **confidence-interval overlap**
- **paired outcome tests** where appropriate
- **trajectory / action deviation** (bounded max `‖Δτ‖`, bounded state divergence)
- **qualitative parity of recovery behaviour** (does SIL fail *the same way* as MIL?)

**SIL exit:** the frozen policy runs through its embedded code path and reproduces MIL behaviour under
the criteria above, *before* any hardware is touched.

---

## 5. Phase D — MCU implementation + HIL

**Starts only after the Phase-C freeze gate.** Uses the **frozen** artifact, the **same** fault suite
and the **same** IC list.

### 5.1 Target

**ESP32-S3 = preferred MCU/HIL target.**

> It is an **experimental embedded-control and HIL platform — not a flight-qualified spacecraft OBC.**
> No aerospace flight-qualification claim is made anywhere in this project.

**Purpose of Phase D** — demonstrate:

| Demonstration |
|---|
| deterministic embedded inference |
| timing (WCET, jitter) |
| memory (flash / RAM / stack) |
| interface behaviour |
| closed-loop HIL |
| fault injection |
| SIL / MIL / HIL equivalence |

### 5.2 Build order

| Step | Deliverable |
|---|---|
| **D1** | **Interface freeze**: sensor packet → MCU, torque packet → plant. Framing, CRC, timestamps, rate. Documented in `docs/DEPLOYMENT_INTERFACE.md`. |
| **D2** | **Port to C**: `h_hat` estimator, policy inference, safety governor, allocator. All parameters from a generated header hash-matched to the frozen bundle. |
| **D3** | **Bench characterization**: WCET per control step, jitter, stack/flash/RAM, worst-case inference time — must be ≪ the 200 ms control period. |
| **D4** | **HIL loop**: PC simulator ⇄ UART/UDP ⇄ MCU at 5 Hz; log MCU timestamps + both states. |
| **D5** | **Fault injection** (see §5.3). |
| **D6** | **HIL vs SIL vs MIL**: trajectory deviation, success/conditional-success parity, latency-induced tracking error. |

### 5.3 D5 — fault injection: software first

**Assume initially: MCU-in-the-loop / simulation-in-the-loop only.**

```text
   simulation fault model
            ↓
   override  h / actuator response
            ↓
   MCU detects fault
            ↓
   health estimator
            ↓
   controller adapts
```

> **Real physical wheel/MTQ fault injection is `[OPTIONAL]` and depends on the availability of a real
> actuator bench. It is NOT a prerequisite for Phase D completion.**

### 5.4 Phase D exit criteria

- The frozen policy runs in **real time** on the MCU with documented timing and memory.
- HIL reproduces SIL/MIL behaviour under the §4 criteria on the same fault suite.
- At least one fault injected through the **software** path is detected and handled.
- Every number reproducible from a documented command + frozen config hash.
- No flight-qualification claims made.

---

## 6. Phase E — thesis / report / defence / reproducibility freeze

Phase E **freezes the evidence**; it does not produce new results.

| Task | Detail |
|---|---|
| E1 | Final experiment matrix — every table/figure traceable to a command + config hash |
| E2 | Regenerate **all** plots/tables from one frozen results bundle (no hand-edited numbers) |
| E3 | Architecture diagrams: MIL, SIL, HIL; controller diagram; fault taxonomy |
| E4 | Results chapters: baselines (LQR, PPO), C4.1 attribution, observation split (O1-H vs O1-E), safety, recoverability, SIL, HIL |
| E5 | **Limitations chapter, written honestly**: sample sizes and CIs; the recoverable-set boundary; **unimplemented disturbances (G9)**; the wheel-speed clip (G12); estimator assumptions; **seen-vs-unseen fault gap**; ESP32-S3 is not flight-qualified |
| E6 | Persian reports (`.docx`, RTL) via the existing `reports/post_process_rtl.py` pipeline, in Pouria's first-person voice |
| E7 | Defence package: slides, anticipated examiner questions with prepared answers, demo scripts |
| E8 | **Reproducibility package**: seeds, IC list, configs, environment, one-command rerun; publish frozen weights as a GitHub Release (they are intentionally `results/`-gitignored) |

**Exit:** a defence-ready package where every claim maps to a reproducible artifact.

---

## 7. Phase F — optional world-model research arm

**Rule:** F replaces **only the intelligence block.** Everything else — estimator → `h_hat` →
governor → allocator → plant → evaluation → HIL — stays frozen.

```text
   Frozen Baseline C
        │
        ├──► MCU/HIL ──► Thesis / Defence
        │
        └──► optional Phase F
                 │
                 ├── frozen JEPA + MPC
                 └── AdaJEPA + MPC
```

| Sub-phase | Content | Role |
|---|---|---|
| **F0** | **Frozen** JEPA-style latent world model + MPC | **Baseline B** — the frozen-model comparison arm |
| **F1** | **AdaJEPA-style adaptive model + MPC**: `f = f_nominal + Δf_adaptive` with `‖Δf‖ ≤ Δ_max` and a confidence measure | **the contribution** |
| **F2** | Evaluation on faults **unseen in training** (severity, onset, wheel index, combinations) | the novelty claim |

**Narrative:** LQR works on the nominal model and fails under severe actuator fault → PPO learns a
policy over randomized faults, knowledge baked into weights → frozen JEPA+MPC learns a model and
*assumes it stays valid* → **AdaJEPA observes model mismatch, adapts latent dynamics, MPC replans,
handles unseen fault severity.**

**Safety constraint:** AdaJEPA may never freely rewrite the model online. Nominal + bounded adaptive
residual, confidence-gated, with the same governor and LQR fallback underneath.

> **Phase F must never block: SIL · MCU implementation · HIL · thesis completion · defence.**
> If time runs out, Phase F is documented as future work and Phase E proceeds regardless.

---

## 8. Risk register

| # | Risk | Mitigation |
|---|---|---|
| **R1** | Dead-wheel recovery remains low | Recoverability framing (C7-lite) + **conditional success** rather than raw success |
| **R2** | Attribution shows the Phase-B improvement came from a factor other than reward shaping | **Report the actual causal result.** The claim changes to whatever the data says |
| **R3** | Health estimator cannot identify an **unexcited** wheel | Excitation gating + confidence estimate + governor fallback; report `h_hat` quality |
| **R4** | Governor masks policy failures | **Always report gated AND ungated results** |
| **R5** | Scope creep prevents C from closing | The C1 + C4.1-only authorization, Decision Gate A, and the §2.14 cut list |
| **R6** | **Estimator-in-the-loop degrades PPO fine-pointing** (or changes learned behaviour) | **Compare the old estimator path vs the final estimator path before freezing**; documented alternative estimator (C2-e option B) if the MEKF is harmful |
| **R7** | The recoverability oracle becomes a research project of its own | **C7-lite first**; the full map is optional |
| **R8** | MCU/HIL hardware delays the schedule | **Software fault injection + MCU-in-the-loop first**; the physical bench is optional |

Supporting risks: `C:` drive near-full (keep `results/`, venv and caches on `E:`).

---

## 9. Open decisions

| Decision | Status |
|---|---|
| **Q1 — MCU** | **ESP32-S3 preferred** (experimental HIL platform, not flight-qualified) |
| **Q2 — recoverability framing** | **Accepted** |
| **Q3 — plant uncertainty** | **Separate measured variant; not silently mixed into the frozen baseline** |
| **Q4 — frozen JEPA+MPC** | **Only required if Phase F is executed** |
| **Q5 — defence date** | ⚠️ **STILL REQUIRED — schedule-critical input** |
| **Q6 — hardware bench** | **Assume MCU/simulation HIL initially; physical actuator bench optional** |

> ### ⚠️ Q5 is the only decision that genuinely blocks planning
>
> **The defence date is a schedule-critical input and is still outstanding.** Without it, the
> C / D / E scope cannot be sized against the optional Phase F, and no milestone can be placed on a
> calendar. Everything else in this plan can proceed to Decision Gate A without it — **but the
> decision of whether Phase F is attempted at all cannot be made without it.**

---

## 10. Decision gates (summary)

| Gate | After | Decision |
|---|---|---|
| **Gate A** | C1 + C4.1 | Which of steps 3–12 are necessary; is C4.2 justified; what N and compute are needed |
| **Gate B** | C3b (O1-E) | Are later observation sets (O2/O3) worth running, or is `h_hat` sufficient? |
| **Gate C** | C7-lite | Is C7-full worth pursuing, or is C7-lite the final recoverability result? |
| **Gate D** | end of C-I | **Freeze** — Baseline C-Final selected; C-II/SIL may begin |
| **Gate E** | C-II (SIL) | Enter Phase D (MCU/HIL) |
| **Gate F** | Phase E start | Is there time for Phase F? If yes, F runs **without** touching C/D/E |
| **Gate G** | any time | Q5 (defence date) arrives → re-scope D/E/F immediately |

---

## 11. Scope-cut rules (explicit)

1. **C1 + C4.1 are the only authorized actions.** Everything else awaits Gate A.
2. **No reward redesign during attribution.** C4.2 comes after C4.1, and then **one term at a time** —
   never five new reward terms simultaneously.
3. **`O1-H` and `O1-E` are separate experiments. Never merged.**
4. **The deployed path never sees `h_true`.** Privileged truth only inside the labelled `O1-H` diagnostic.
5. **No architecture change after the freeze gate** other than deployment implementation.
6. **Phase F never gates D, E, HIL, or defence.**
7. **SAC is a challenger, never a gate.** PPO is allowed to win.
8. **No 4th reaction wheel; no plant rewrite; no large networks.**
9. **No unconditional large-N mandate** — N is sized from measured throughput.
10. **No flight-qualification claims** for the ESP32-S3 platform.
11. **Do not mark a task done because it is described here.** Only executed-and-evidenced tasks are done.
12. **Do not credit any regenerated success-rate change to the time-base fix.** Measure it, then attribute it.

---

## 12. Schedule

**No precise number of evenings will be stated until C1 throughput and C4.1 results are known.**
The earlier v1 estimate (8–11 evenings for all of Phase C) was not reliable and is withdrawn.

```text
      C1 + C4.1
          ↓
   review evidence  (Gate A)
          ↓
   estimate remaining C-I scope
          ↓
       freeze baseline
          ↓
          SIL
          ↓
          D
          ↓
          E
          ↓
   F only if time remains
```

Training compute is not the bottleneck (measured ≈2270 fps ⇒ 2 M steps ≈ 13 min). Implementation,
verification and analysis dominate. **Q5 (defence date) is required before any calendar is fixed.**

---

## 13. Deliverables and file map

| Artifact | Path | Status |
|---|---|---|
| **This roadmap** | `docs/PhaseC_to_F_Master_Plan.md` | ✅ authoritative |
| Superseded v1 draft | `docs/archive/PhaseC_to_F_Master_Plan_v1_SUPERSEDED.md` | ⛔ archived |
| C1 regeneration results | `codes/results/c1_regeneration/` | `[AUTHORIZED]` |
| C4.1 attribution results | `codes/results/c4_1_attribution/` | `[AUTHORIZED]` |
| Health-estimator investigation | `codes/satellite_adcs/health_estimator.py` + validation | `[PLANNED]` |
| Observation split results | `codes/results/obs_split/` | `[PLANNED]` |
| Freeze bundle (weights + normalization + hashes) | `codes/results/baseline_c_final/` | `[PLANNED]` |
| SIL report | `docs/SIL_REPORT.md` | `[PLANNED]` |
| Deployment interface spec | `docs/DEPLOYMENT_INTERFACE.md` | `[PLANNED]` |

---

## 14. What "go" means right now

**Authorized — C1 + C4.1 only:**

1. **C1** — regenerate M1 and Phase 1B on the corrected time base; measure evaluation throughput;
   report success rate, settling time, median, p90/p95 and final pointing error **separately**.
2. **C4.1** — attribute the Phase-B improvement with controlled single-factor experiments.

**Not authorized:** full MEKF implementation · complete health-estimator integration · complete
observation sweep · reward-v2 redesign · full recoverability oracle · large final Monte Carlo ·
SIL · MCU work · AdaJEPA.

Then: **Decision Gate A**.

---

*Plan finalized for the repository. No implementation code, configuration or training has been
produced by this document. Execution authorization: **C1 + C4.1 only**.*
