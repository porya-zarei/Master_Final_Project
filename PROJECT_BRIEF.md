# Project Brief — Fault-Tolerant Nanosatellite Attitude Control (M.Sc. Thesis)

> **v2 — rewritten 2026-09-11.** Supersedes v1, archived at
> `docs/archive/PROJECT_BRIEF_v1_SUPERSEDED.md`. v1 was written *before the simulator existed* and
> describes a codebase that no longer exists — see **§9 Stale claims to discard**.
>
> This is the onboarding document for any agent or human joining the project. The **authoritative
> forward roadmap is `docs/PhaseC_to_F_Master_Plan.md`**. If this brief and that plan ever disagree
> about what is authorized or what comes next, **the plan wins.**

---

## 1. Who / what this is

- **Student:** Pouria Zarei (810103137), M.Sc. Control Engineering, University of Tehran, Faculty of
  Electrical & Computer Engineering, College of Engineering.
- **Advisor:** Dr. Mohammad-Javad Yazdanpanah.
- **Proposal approved:** 1405/03/02 (~May 2026); applied/developmental scope (کاربردی + توسعه‌ای),
  day program.
- **Approved title (Persian):** کنترل وضعیت تحمل‌پذیر خطا در نانوماهواره‌ها با استفاده از یادگیری
  تقویتی: از شبیه‌سازی تا پیاده‌سازی سخت‌افزار در حلقه
- **Approved title (English):** *Fault-Tolerant Attitude Control of Nanosatellites Using
  Reinforcement Learning: From Simulation to Hardware-in-the-Loop Implementation.*

## 2. Research question

Design an ADCS for CubeSats / nanosatellites that points a satellite at **nadir** — starting from a
**random initial attitude and random angular velocity** — with the best precision/accuracy and
minimum time, **and stays stable and accurate when a reaction wheel fails or degrades**, *including
failure modes it did not see during training.*

The deliverable controller is an **RL model**. Classical control appears only as baseline,
reference, and fallback.

## 3. Authoritative phase lettering

⚠️ Earlier advisory material used C/D/E/F for **different** content (D = frozen world model,
E = AdaJEPA, F = safety gate). **That lettering is obsolete.** These are the only valid definitions
(`PhaseC_to_F_Master_Plan.md` §0.2):

| Phase | Content | Status |
|---|---|---|
| **A** | Simulator + LQR nadir-acquisition baseline (Phase 1) + fault model & fault-tolerant allocator (Phase 1B) | ✅ complete |
| **B** | First RL baseline: fault-randomized PPO vs LQR (Phase 2) | ✅ complete |
| **C** | Baseline-controller research, validation, **freeze**, MIL regeneration, **SIL** | 🟡 in progress |
| **D** | **MCU implementation + HIL** (ESP32-S3) | ⬜ after C |
| **E** | Thesis / report / defence / reproducibility freeze | ⬜ after D |
| **F** | **Optional** world-model arm: frozen JEPA+MPC → AdaJEPA+MPC | 🔵 never blocking |

Phase C is split by a hard **freeze gate**: C-I (architecture may still change, evidence-driven)
→ ⛔ **freeze** → C-II (SIL; **no architecture changes allowed**).

## 4. Verified current state (2026-09-11)

Verified by reading the code and by measurement — not from memory.

### 4.1 The plant, as implemented

- Config-driven YAML simulator: **every parameter is loaded from config**, nothing hard-coded.
- 24U, ~35 kg, `J = diag(0.38, 0.73, 0.58)` kg·m². Attitude in quaternions; `ω_max = 5°/s`;
  random initial condition on SO(3).
- **Actuators: 3 reaction wheels + 3 magnetorquers** (no 4th wheel — a firm decision).
- **Sensors:** star tracker, sun sensor, gyro, magnetometer; GPS for orbit.
- **Target: nadir / LVLH** — *not* a fixed inertial attitude.
- **Faults: continuous per-wheel health `h ∈ [0,1]`**, `τ_actual = h · τ_cmd` — not a binary
  "locked wheel". ⚠️ The proposal phrased the fault as binary ("completely unusable **or** 50 %
  torque"); the implementation is **strictly more general**, and both proposal cases are special
  points of it. Say it that way in the thesis.
- Scenario: release (random `q`, `ω`) → detumble → nadir acquisition.
- **RL action = desired body torque** — never raw actuator commands. A shared physics-based
  **fault-tolerant allocator** maps torque onto wheel/magnetorquer commands.

### 4.2 Measured results

Phase 2, **n = 24** initial conditions, 900 s @ 5 Hz, with *both controllers scored under the same
settling hold* (`results/rl_eval_matched/`; full account in `reports/report-state-2.md` §6):

| Case | RL (h=10 s) | RL (h=30 s) | LQR (h=10 s) | LQR (h=30 s) |
|---|---|---|---|---|
| Healthy | 100 % · 0.18° | 100 % · 0.18° | 91.7 % · 0.71° | 83.3 % · 0.71° |
| RW1 @ 50 % torque | 100 % · 0.16° | 100 % · 0.16° | 91.7 % · 0.71° | 83.3 % · 0.71° |
| RW1 dead | 20.8 % · 44.0° | **4.2 %** · 44.0° | 0 % · 68.3° | 0 % · 68.3° |

**Reading:** PPO wins all three cases under **both** criteria, and precision is ~4× better
(0.18° vs 0.71°). The dead-wheel margin is **one initial condition** (1 of 24 under the strict
hold) — quote it as a single-IC result, never as a rate, and **always state the hold**: that number
is sensitive to sample size *and* hold.

- **C1** (done) found the earlier reported horizon was wrong: a nominal "900 s" episode was really
  720 s (ratio 0.8000) until the time-base fix.
- **C4.1** (done) attributed the Phase-B gain (≈4° → ≈0.17°) to a **conjunction** — enough step
  budget ∧ the tolerance-bonus reward term ∧ reward normalisation off — with the bonus term
  dominant (removing it costs **−83.3 pp**).

### 4.3 Code map — what actually runs

| Path | Role |
|---|---|
| `codes/satellite_adcs/config/*.yaml` | all parameters; vars are loaded from config |
| `codes/satellite_adcs/environment/adcs_env.py` | **the real training environment** — custom NumPy + Gymnasium |
| `codes/satellite_adcs/dynamics.py` | Euler + MWM dynamics, inertia coupling |
| `codes/satellite_adcs/controllers.py` | LQR baseline |
| `codes/satellite_adcs/estimation.py` | ⚠️ star-tracker passthrough + gyro only — **no MEKF yet** |
| `codes/scripts/train_rl.py`, `eval_rl_vs_lqr.py`, `diag_rl.py` | train / evaluate / diagnose |
| `codes/scripts/c1_regeneration.py`, `c4_1_attribution.py` | the C1 / C4.1 evidence scripts |

### 4.4 The RL backend — settle this once

Training uses a **custom NumPy + Gymnasium environment** (`adcs_env.py` above) driven by
**stable-baselines3 PPO**. It is **not** Basilisk and **not** `bsk_rl`.

`codes/simulation/envs/adcs_env.py` is **stale legacy** from an abandoned Basilisk / `bsk_rl`
prototype. It produced **none** of the thesis results and must not be used or extended.
(Verdict on migrating the trainer to Basilisk / `bsk_rl`: **don't.** Basilisk may later serve as an
independent *validation* plant, never as the training plant.)

### 4.5 Honest known gaps

| Gap | Evidence | When it matters |
|---|---|---|
| **MEKF not implemented.** Estimator = star-tracker passthrough + gyro; the gyro bias (1e-3 rad/s) is unestimated | `estimation.py`: `propagate()` is a no-op, `update_vector()` returns `self`, no bias/covariance state | Phase C step 8 (C2-e); blocks nothing before that |
| **The policy is blind to health.** Observation is `[θ(3), ω_err(3), Ω_rw(3)]`; `h` appears only in `info` | `adcs_env.py:117` | C2-h → C3a / C3b (Phase C steps 3–5) |
| **Never trained on a dead wheel.** | `config/rl.yaml` → `health_range: [0.5, 1.0]` | same |
| **Aerodynamic-drag / SRP / residual-dipole flags are no-ops** | `dynamics.py:71–73`; all three `enabled: false` and referenced nowhere else | before the freeze — implement + sensitivity study, or delete with a documented order-of-magnitude argument |
| **Step budget 2×10⁶ vs the 2–3×10⁷ typical of the subfield** | `docs/Literature_Survey_Environment_and_Training.md` | deliberately deferred to the final artifact, after C9 |

## 5. Environment

- Training/eval venv: `codes/venv` (Python 3.14.6) — torch 2.9.1+cu128, stable-baselines3 2.9.0,
  gymnasium 1.3.0.
- **Device:** auto-selects **CPU**; `--device cuda` on demand. GPU is an RTX 5060 Laptop 8 GB
  (`sm_120` — needs cu128+ wheels).
- Machine: 24 cores / 16 GB. Measured throughput ≈ 2269 fps ⇒ 20 M steps ≈ 2.4 h.
- `results/` is **gitignored** — copy figures into the tracked `reports/figures/` before they can
  appear on GitHub.

## 6. Document map

| Document | Status |
|---|---|
| `docs/PhaseC_to_F_Master_Plan.md` | ✅ **authoritative roadmap** |
| `reports/report-state-1.md` / `-2.md` / `-3.md` | state reports with evidence (state-2 §6 = the erratum) |
| `docs/Literature_Survey_Environment_and_Training.md` | 29-paper survey of environments & training practice |
| `docs/ADCS_Phase1_Plan.md` | 📜 historical (Phase 1) |
| `codes/docs/Phase2_RL_RewardShaping_Plan.md` | 📜 historical (Phase 2) |
| `docs/archive/*_SUPERSEDED.md` | audit history only — **never implement from these** |

## 7. Immediate next action

**C4.2 — the controlled single-term/scale reward study** (authorized 2026-09-11; its precondition —
C4.1 identifying reward shaping as the material contributor — is met).

Then, in plan order: C2-h → C3a → C3b → observation sweep → C6 → C2-e → C5 → C7-lite → C8 →
**C9 freeze gate** → C10 SIL → Phase D.

⚠️ **Authorization is milestone-scoped.** Approval of a plan is *not* approval of the phase it
describes. Check §0.4 of the master plan before starting anything.

## 8. How to help from here (working agreement)

- **Plan first.** Write the plan into `docs/` before implementing, and wait for an explicit,
  milestone-scoped **go**. Approval never implies approval of the whole phase.
- **Commit at each state worth saving**, so the history shows how the result was reached.
- **Never silently pick** a design choice that changes what the thesis claims (action-space level,
  reward shape, safety-gate design, estimator ordering) — flag it and ask.
- **Never fabricate a result.** If a run fails or a number is missing, say so plainly.
- Advisor-facing deliverables: **Persian, first person, plain tone**, figures embedded.
- The controller delivered by the thesis is the **RL model**; LQR / B-dot stays the reference and
  fallback.
- The **safety governor stays physics-based** — never another neural network.
- The deployed policy must **never receive `h_true`** — only the estimated `h_hat`.

## 9. Stale claims to discard (from v1 — do not repeat these)

Every one of the following is false or obsolete:

1. ❌ *"Stack: `bsk-rl` (built on Basilisk) …"* → custom NumPy + Gymnasium env. See §4.4.
2. ❌ *"We are at the very start of **Phase 1**."* → Phases A and B are complete; we are mid-Phase C.
3. ❌ *"Immediate next action: run the manual test loop from `README.md`."* → long since done.
4. ❌ *"Basilisk's orbital propagator needs to download `de430.bsp` …"* → irrelevant; no Basilisk
   anywhere in the training path.
5. ❌ *"Action space is `act.AttitudeSetpoint` …"* → the action is **desired body torque**.
6. ❌ *"Target attitude is currently fixed at zero."* → the target is **nadir / LVLH**.
7. ❌ *"Reaction-wheel fault zeroes one wheel's torque command … doesn't route around it."* →
   a **fault-tolerant allocator** redistributes the torque across the remaining wheels and
   magnetorquers.
8. ❌ v1's C/D/E/F lettering → see §3.

**Still true, and still the plan for the research contribution** (this lives in **Phase F**, and is
**optional / never-blocking**): the three-way comparison —

1. **Baseline C** — fault-randomized PPO/SAC  ← *this is what exists today*;
2. **Baseline B** — frozen JEPA-style world model + MPC;
3. **The contribution** — an AdaJEPA-style **adaptive** latent world model + MPC, evaluated on
   faults **unseen** during training.

The AdaJEPA reference is verified real: *AdaJEPA: An Adaptive Latent World Model*, arXiv:2606.32026v1
(2026-06-30), code at <https://github.com/agentic-learning-ai-lab/adajepa> — it adapts a latent world
model *inside* the MPC loop with one self-supervised gradient step per replan. Our addition beyond
it: a **physics-based validation/safety gate** that rejects an online adaptation step if it would
raise predicted cost or drift the parameters too far.
