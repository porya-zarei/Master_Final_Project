# Phase C-R — Where RL can honestly beat LQR

**Status:** proposed, awaiting milestone-scoped approval. Nothing in this document is
implemented yet.

---

## 0. Why this document exists

The n = 24 paired comparison (`reports/report-state-3.md` §10) established:

| case | RL | LQR |
|---|---|---|
| healthy | 100 %, 0.27° | 100 %, 0.27° |
| RW1 @ 50 % | 100 %, 0.29° | 100 %, 0.27° |
| RW1 dead | 4.2 %, 80.02° | 0 %, 81.96° |

**RL matches LQR and does not beat it.** The temptation is to answer that with more
training. That would be a mistake, and this document exists to explain why and to
propose what to do instead.

The reason is not that the policy is undertrained. It is that **the current benchmark
is structurally favourable to the classical controller**, in five specific ways:

1. **The allocator uses the true wheel health (G13).** The controller is handed `h_true`
   and inverts it exactly. The fault is never *unknown*, so there is nothing to adapt
   to. At h = 0.5 the fault is perfectly masked and the two controllers are doing the
   identical thing.
2. **The objective is the LQR design cost.** We score both controllers on a quadratic
   in angle and rate error — the exact functional LQR is optimal for.
3. **There are no actuator nonlinearities.** No wheel friction, stiction, deadzone,
   torque-rate limit or quantization, so the linear model is exact.
4. **There is no plant uncertainty.** Inertia, alignment and CoM are exact; the model
   the controller uses *is* the plant.
5. **The disturbance flags are no-ops** (`dynamics.py:71-73`, G9), so there is no
   unmodelled disturbance to reject.

A superiority claim on that benchmark would be either false or unfalsifiable. Both are
unacceptable for the thesis.

---

## 1. The principle — the line that will not be crossed

> **RL superiority must be earned on a benchmark that reflects the real problem. It
> will never be produced by tuning until RL wins.**

Rules that follow, and that apply to every milestone below:

- **R1 — Realism justification.** Every change must be defensible as *more realistic*,
  not as *more favourable to RL*. If a change cannot be justified that way, it is not
  made.
- **R2 — Pre-registration.** The protocol, metric and pass/fail condition are written
  and committed **before** training. No metric may be added afterwards.
- **R3 — Symmetric information.** Both controllers get the same sensors, the same
  estimates, the same actuator model and the same disturbances. If the RL policy gets
  `h_hat`, the LQR gets `h_hat`. No hidden advantages in either direction.
- **R4 — Honest reporting.** If RL does not win after these changes, **that is the
  result** and it is reported as such. A negative result obtained under a *fair* and
  *realistic* benchmark is a legitimate thesis contribution. A positive result obtained
  by weakening the baseline is not.
- **R5 — Same tuning effort.** The classical baseline gets at least the same care as
  the policy: fixed-gain, gain-scheduled, and (where appropriate) an adaptive
  classical variant. A straw-man LQR proves nothing.

---

## 2. The four levers — where LQR is *structurally* limited

These are the only places where a learned policy can have a real, explainable
advantage. Each is a genuine property of the real problem, not a handicap invented for
RL.

### L1 — The fault is unknown (remove the oracle)

**What changes.** Allocation uses `h_hat` from the C2-h estimator instead of `h_true`.
The `h_hat` allocation path already exists by design (decision D-C2h-1 = (a)) and is
currently a documented, *unrun* ablation. This milestone runs it.

**Why LQR suffers.** The LQR's allocator inverts a health it does not know. Under-
estimating `h` produces too little torque (sluggish, large residual); over-estimating
produces saturation and, on a wheel approaching failure, the wrong torque vector
entirely. The error is **systematic**, not zero-mean, so it does not average out.

**Why RL can win.** The policy observes the *response* — commanded versus achieved
rate, wheel speeds, `h_hat` and its staleness — and can infer effective authority
online. That is adaptation in the true sense, and it is unavailable to a fixed-gain
controller with a nominal model.

**Known obstacle (must be stated).** For a *dead* wheel, G13 showed `h_hat` is
**unobservable** from an oracle-allocator's telemetry (τ_cmd = 0 → no regressor
excitation; identified in 3.2 s only once commanded). This milestone must therefore
also test the realistic ordering: **detect first, then compensate.** If the fault is
undetectable, no controller can compensate and that is a legitimate finding about the
*system*, not about RL.

**Metric.** Paired, n ≥ 24: success rate, final error, settling time, and the
`h_hat` estimation error at the moment of first compensation.

### L2 — Nonlinear actuators

**What changes.** Add the effects the linear model assumes away:
wheel friction and stiction, a deadzone around zero torque, a torque-rate limit, and
DAC/sensor quantization. All configurable, all switched off in the current plant.

**Why LQR suffers.** A linear controller designed on an ideal actuator will produce
limit cycles around the deadzone, stick-slip at low wheel speeds, and torque commands
the wheel cannot honour. These are exactly the phenomena that motivate nonlinear
control in practice.

**Why RL can win.** A policy trained *with* these effects learns to avoid the
deadzone, to approach the target without exciting stiction, and to respect the rate
limit by construction. This is the classic "learned control handles the real actuator"
argument, and here it is earned rather than asserted.

**Metric.** Same as L1, plus a limit-cycle / chatter index (mean absolute rate of
change of commanded torque near the target).

### L3 — Plant uncertainty and distribution shift

**What changes.** Randomize during training: inertia ±20 %, principal-axis
misalignment, CoM offset, and the aero/SRP disturbance flags (G9) implemented rather
than left as no-ops. Evaluate on **held-out** parameter draws the policy never saw.

**Why LQR suffers.** LQR is designed on the nominal `J`. A 20 % inertia error changes
the closed-loop bandwidth and damping; a misalignment couples the axes. Performance
degrades predictably with the mismatch, and the controller cannot tell that it has
happened.

**Why RL can win.** Domain randomization is the one setting where learned policies
have a demonstrated, mechanism-level advantage: the policy learns a *policy for the
distribution*, not for a point. This is the strongest available evidence for
"robust and adaptive" in the thesis.

**Metric.** Held-out generalization: success and final error on unseen parameter
draws, plus degradation slope versus mismatch magnitude for both controllers.

### L4 — Time-optimal slew under saturation

**What changes.** Add a second objective: **minimize time to acquire the target within
tolerance**, under hard torque and wheel-speed limits. Keep the precision criterion.

**Why LQR suffers.** This is a *provable* limitation, not a matter of tuning. The
time-optimal control for a double integrator with bounded input is bang-bang with a
switching curve (minimum-time, not minimum-quadratic-cost). An LQR is smooth by
construction and therefore cannot be time-optimal. This is the cleanest theoretical
argument available in this thesis.

**Why RL can win.** Bang-bang switching is exactly what a policy can represent and a
quadratic controller cannot. The expected gain is largest for large initial errors,
which is precisely the operating regime (random initial attitude).

**Metric.** Time-to-acquire distribution, with the LQR compared at its *best* tuning
and against a computed bang-bang reference where tractable.

---

## 3. Milestones

Each milestone is independently gated. **Approval of one is not approval of the next.**

### M1 — Remove the oracle (L1) — *the fairness fix*
Deliverables: `h_hat` allocation path wired and tested; paired comparison
LQR(`h_true`) / LQR(`h_hat`) / RL(`h_hat`).
Pass condition: the comparison runs and is reported, **whatever it shows**.
Decision it forces: whether an unknown fault is compensable at all, and if not, the
honest statement of that limit.

### M2 — Adaptation (L1 + observation redesign)
Deliverables: observation includes `h_hat`, its staleness, wheel speeds and the
commanded-versus-achieved residual history; retrain; paired eval, n ≥ 24, ≥ 3 seeds.
Pass condition: RL beats LQR(`h_hat`) on at least one fault case **with a confidence
interval that excludes zero**.

### M3 — Nonlinear actuators (L2)
Deliverables: friction/stiction/deadzone/rate-limit/quantization in the plant;
retrain; paired eval; chatter index.
Pass condition: measurable RL advantage, or an explanation of why not.

### M4 — Uncertainty and generalization (L3)
Deliverables: randomization + implemented aero/SRP; held-out evaluation.
Pass condition: RL degrades more slowly than LQR on unseen draws.

### M5 — Time-optimal (L4)
Deliverables: time-optimal objective; bang-bang reference where tractable.
Pass condition: RL acquires faster at equal precision.

### M6 — Statistics and freeze
n ≥ 24 paired, ≥ 5 seeds, McNemar/Fisher with CIs, pre-registered primary metric.
Freeze the canonical result. Only then decide what the thesis claims.

---

## 4. What I expect, stated in advance so it can be checked

- **M1** is likely to *hurt* both controllers and may show that a dead wheel is
  genuinely unrecoverable. That is a system-level finding, not an RL failure.
- **M2** is the highest-probability source of a real RL win, because it is the only
  lever where the classical controller has no mechanism to adapt at all.
- **M3** and **M4** are the strongest *defensible* claims ("robust and adaptive" in the
  sense an examiner will accept), even if the margin is modest.
- **M4** has the best chance of a large, unambiguous gap: LQR on a 20 % inertia error
  versus a policy trained on the distribution.

If, after M1–M5, RL still does not beat LQR, the thesis reports that — with the
benchmark documented as fair, realistic and pre-registered. That outcome is defensible.
An inflated win is not.

---

## 5. M5 PRE-REGISTRATION — time-optimal policy (frozen before training)

Committed **before** any time-optimal training, per rule R2. No term, metric or
threshold below may be changed after results are seen.

### 5.1 Why this is the primary lever

Measured (`reports/report-state-3.md` §12, `reports/l4_headroom.json`): the LQR's
median settle is **241.3 s** against a **19.8 s** bang-bang lower bound — a **9.08×**
gap (range 3.17–25.41×), using the bound most favourable to the LQR. This is a
structural consequence of a quadratic cost being smooth, not a tuning artefact.

### 5.2 Objective (fixed)

Replace the precision-only reward with a **time-to-target** reward:

    r_t = -1                      (per control step: minimise time)
        - k_theta * theta^2       (k_theta = 0.01, keep a gradient far from target)
        + BONUS                   when theta < 1 deg, for the first time
    BONUS = +500, awarded ONCE per episode on first entry into tolerance, so the
    optimal policy is to arrive early and stay, not to dawdle.

Rationale for each term: `-1/step` makes time the currency; `k_theta` keeps a
usable gradient while far away (the failure mode of §8 was a flat signal);
the one-off bonus prevents the "arrive late, then farm the tolerance band"
degeneracy that a per-step bonus would create.

### 5.3 Metrics (fixed, primary first)

1. **PRIMARY: time-to-first-entry into 1°** (`t_first`), median over paired episodes.
2. Secondary: settle time with a 10 s hold; success at 10 s and 30 s holds; final error;
   control effort; wheel-speed margin.
3. Chatter index: mean |Δτ_cmd| near the target (seconds-order check that a fast
   policy did not simply bang-bang forever).

### 5.4 Pass / fail (fixed)

- **PASS** if the policy's median `t_first` is **≥ 25 % lower** than the LQR's, with
  a 95 % bootstrap CI on the difference excluding zero, at **n ≥ 24 paired episodes**
  and **≥ 3 training seeds**.
- **PARTIAL** if 10–25 % faster with a CI excluding zero.
- **FAIL** otherwise, and the failure is reported with the same prominence.

A faster policy that violates the precision criterion (final error > 1°) is a **FAIL**,
not a win: speed at the cost of pointing is not the objective.

### 5.5 Controls (fixed)

- The LQR is compared at its **existing tuning**, plus the gain-scheduled variant.
- A hand-built **bang-bang baseline** (full torque toward the target, switching on the
  rate condition) is reported alongside, because it is the honest reference for what
  "time-optimal" means here. If the policy cannot beat a trivial bang-bang rule, that
  is the finding.
- Same paired initial conditions and gyro bias for every controller.

### 5.6 What would falsify the thesis's L4 claim

If a bang-bang baseline and the policy both fail to beat the LQR on `t_first`, then the
9× bound is not reachable in practice (rate nulling, wheel saturation, or three-axis
coupling dominates) and **L4 is closed too** — leaving the thesis with the honest
negative result plus the methodological contributions. That outcome will be reported.
