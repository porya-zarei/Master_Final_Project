# Milestone B — Actuator model: implemented effects and parameters

**Branch:** `residual-rl`. All effects are **config-driven and default to zero**, so the
ideal actuator — and every historical result — remains **bit-identical** (tested).

## 1. What was implemented

| effect | parameter (`actuators.reaction_wheels`) | model | default |
|---|---|---|---|
| torque deadzone | `deadzone_Nm` | `|τ| < dz → 0`; above it, τ passes unchanged | 0 |
| viscous friction | `friction_viscous_Nms` | `−b·Ω_w` on the wheel, `+b·Ω_w` on the body | 0 |
| Coulomb friction | `friction_coulomb_Nm` | `−c·tanh(Ω_w/0.05)` on the wheel, opposite on body | 0 |
| torque-rate limit | `rate_limit_Nm_per_s` | `|Δτ| ≤ rate·dt` per control step | 0 |
| quantisation | `quant_step_Nm` | `round(τ/step)·step` | 0 |

Saturation (per-wheel) and the wheel-speed clamp were **already** present and are kept.

### Two deliberate implementation decisions

1. **Friction is internal, not a body torque.** The bearing couples the wheel to the
   spacecraft, so the wheel must *lose* exactly what the body *gains*. Implemented as
   `τ_f` on the wheel and `−τ_f` on the body; the test checks that the body reacts and
   that ‖H‖ is preserved to 4.7e-03. Applying friction to the body alone would have
   created angular momentum from nothing.
2. **The rate limit lives in `step()`, not `derivatives()`.** RK4 calls `derivatives`
   four times per step with the same command, so a stateful limiter there would be
   applied four times per step and silently quarter the effective rate.
3. **Coulomb friction uses `tanh`, not `sign`.** A hard `sign()` inside RK4 chatters and
   destroys the integrator; `tanh(Ω/0.05)` is a smooth approximation that is
   indistinguishable from `sign` above ~0.15 rad/s.

## 2. Parameter justification — these are ASSUMPTIONS, and are flagged as such

The directive requires documented sources. **No datasheet values are available for the
simulated wheel, so the following are defensible order-of-magnitude assumptions, not
measured data. They must be stated as assumptions in the thesis.**

| parameter | value used in tests | basis |
|---|---|---|
| `deadzone_Nm` | 1e-4 | ~1 % of the 0.01 N·m maximum; typical of a small-wheel drive's minimum resolvable torque |
| `friction_viscous_Nms` | 2e-6 | chosen so drag is a few percent of max torque at a few hundred rad/s |
| `friction_coulomb_Nm` | 2e-4 | ~2 % of max torque — the usual breakaway-friction order for small space-rated wheels |
| `rate_limit_Nm_per_s` | 0.05 | reaching full torque in ~0.2 s, i.e. one control period |
| `quant_step_Nm` | 1e-4 | 12-bit-ish resolution over a ±0.01 N·m range |

**These are not tuned to make the LQR fail.** They are set at the level where the effect
is physically present and measurable, and the re-benchmark (Milestone C) reports LQR
performance under each one *individually* so any degradation is attributable.

## 3. Tests — `codes/tests/test_actuator_model.py` (5/5)

- all effects default OFF → the command passes through **bit-identical** (this is the
  guarantee that historical results are unchanged);
- deadzone: sub-breakaway commands deliver nothing, above-breakaway passes;
- rate limit: 0.05 N·m/s at dt = 0.02 gives exactly 1e-3 per step and accumulates;
- quantisation: 1.7e-4 snaps to 2e-4;
- friction: the wheel slows, the **body reacts**, ‖H‖ preserved.

Regressions: frames 12/12, estimation 3/3, allocation 5/5.

## 4. Two test-design errors I made, and what they taught

1. **Unrealistic regime.** The first friction test spun the wheel at 300 rad/s with
   2e-4 N·m of bearing torque — ~3000 s to stop — so it "proved" friction did nothing.
   A test must run in the regime where the effect is observable.
2. **Wrong conservation law.** I checked body-frame momentum, which rotates with the
   body (the `−ω×H` term) and is also driven by gravity gradient. The invariant is
   ‖H‖, plus the physical signature (wheel slows, body reacts).

Both are recorded because they are the same class of error as the frame bug: **a test
that passes while measuring the wrong thing.**

## 5. Next: Milestone C (before any RL)

Re-benchmark **LQR, fault-aware LQR, gain-scheduled LQR and bang-bang** under each
effect individually and then combined, at n ≥ 24 paired, reporting the full
distribution (not a median — see the bimodality in `Milestone_A_Audit.md` §2).
Only after that does residual SAC (Milestone D) begin.

---

## 6. Milestone C — classical benchmark under the actuator models

LQR, n = 6 paired episodes per configuration, T = 900 s, 1° tolerance held 30 s.
`t_first` median, final error, success at the 30 s hold, and the standard deviation
of the pointing error over the last 30 % of the episode (a limit-cycle indicator).

| config | t_first | final | success | tail sigma | entries |
|---|---|---|---|---|---|
| ideal | 69.7 s | 0.134° | **100 %** | 0.028 | 1.0 |
| deadzone | 73.7 s | 0.662° | 100 % | 0.027 | 1.0 |
| viscous | **411.5 s** | 0.580° | 100 % | 0.054 | 1.0 |
| **Coulomb** | 47.4 s | **1.690°** | **0 %** | 0.031 | 0.0 |
| rate_limit | 69.7 s | 0.134° | 100 % | 0.028 | 1.0 |
| quantised | 70.0 s | 0.269° | 100 % | 0.022 | 1.0 |
| **combined** | 42.2 s | **2.114°** | **0 %** | **0.114** | 0.0 |

Full `t_first` distributions (the medians hide the bimodality):
```
ideal      [58.4, 64.4, 68.0, 71.4, 206.0, 401.2]
deadzone   [58.4, 68.0, 71.4, 76.0, 150.8, 505.0]
viscous    [41.0, 46.0, 264.6, 558.4, 709.0, 830.6]
coulomb    [47.4]                      <- only 1 of 6 ever entered tolerance
rate_limit [58.4, 64.4, 68.0, 71.4, 206.0, 401.2]
quantised  [58.2, 66.4, 68.0, 72.0, 188.0, 439.0]
combined   [42.2]                      <- only 1 of 6
```

### The finding: lever L2 is LIVE, and it is decisive

**A well-tuned LQR fails the 1° pointing requirement outright under Coulomb
friction — 0 % success, settling at 1.69°, and 2.11° with all effects combined.
It never even enters tolerance in 5 of 6 episodes.**

This is not a tuning artefact and it is not a weakened baseline: it is the physical
consequence of a *speed-dependent bearing torque the controller's model does not
contain*. Near the target the commanded torque is small, the Coulomb term is not,
and the wheel cannot deliver the fine correction. The combined case additionally
shows **sustained oscillation** (tail sigma 0.114 vs 0.028 ideal — a 4x increase),
i.e. the limit-cycle behaviour the directive anticipated.

### What this means for the thesis

| lever | verdict |
|---|---|
| L1 unknown fault | CLOSED |
| L3 plant uncertainty | CLOSED |
| L4 time-optimal | LIVE (2.71x, bang-bang captures it) |
| **L2 actuator friction** | **LIVE and decisive — LQR cannot meet the requirement at all** |

**This is the measured justification for residual RL.** The target is now concrete and
physical: *restore 1° pointing under actuator friction where a tuned LQR achieves
0 % success.* That is not a metric chosen to favour RL — it is the mission requirement
(the 0.1–1° class pointing spec) being violated by a real actuator effect.

### Honest limits — do not overclaim this

1. **n = 6.** Small. The 0 % is consistent across 6/6 episodes and 5/6 never entering
   tolerance, so the direction is credible, but **n >= 24 is required before citing it.**
2. **The friction parameters are assumptions** (§2), not datasheet values. A different
   Coulomb magnitude moves the failure point. The claim must be stated with the
   assumed value attached.
3. **`rate_limit` had no effect at all** (identical to ideal) because the LQR's commands
   are already smooth — worth reporting, since it shows the limit does not bind for a
   smooth controller but might for a switching one.
4. The Coulomb case is *faster* to first entry (47.4 s) because friction adds damping;
   it is the **holding** accuracy that collapses. First-entry speed and sustained
   accuracy must always be reported separately — the same lesson as §2 of the audit.

---

## 7. Milestone C2 — the Coulomb failure is robust, monotonic and complete

Milestone C's 0 % success at `friction_coulomb_Nm = 2e-4` rested on n = 6 and a single
assumed magnitude. This sweeps the magnitude at **n = 16 paired** episodes.

| Coulomb (N·m) | success (30 s hold) | median final | ever entered tolerance | median t_first |
|---|---|---|---|---|
| 0 | **100.0 %** | 0.213° | 100 % | 178.6 s |
| 1e-4 | **85.9 %** | 0.813° | 93.8 % | 266.2 s |
| **2e-4** | **0.0 %** | 1.602° | **18.8 %** | 144.0 s |
| **3e-4** | **0.0 %** | 2.388° | **18.8 %** | 145.8 s |

Final-error distributions per episode:

```
0     0.049 - 0.638   (all below 1 deg)
1e-4  0.277 - 1.136   (spread across the threshold)
2e-4  1.080 - 1.860   (ALL 16 above 1 deg)
3e-4  1.767 - 2.631   (all far above)
```

### Verdict: the justification for residual RL is solid

1. **Monotonic.** Degradation tracks the friction magnitude; there is no discontinuity
   at a single "magic" value.
2. **Complete at 2e-4.** Not "mostly fails" — **16 of 16 episodes** end above 1°, with a
   minimum of 1.080°. 0/16 success is not a sampling accident.
3. **Systematic offset, not scatter.** At 2e-4 the final error clusters tightly around
   1.5-1.9° across very different initial conditions. That is the signature of a
   stick-slip deadband: the wheel cannot deliver the small torque the controller asks
   for, so the attitude parks where demand equals friction. It is a physical bias, not
   noise, which is exactly the kind of error a learned residual can cancel.
4. **The threshold sits between 1e-4 and 2e-4 N·m** — i.e. **~1-2 % of the 0.01 N·m
   wheel rating.** That is the physically defensible statement to carry into the thesis.

### The precise claim to make (and its caveat)

> Above roughly **1.5e-4 N·m** of Coulomb breakaway friction — 1-2 % of the wheel's
> rated torque — a well-tuned LQR cannot hold the 1° pointing requirement, achieving
> **0/16** successes at 2e-4 N·m.

Caveat that must travel with it: the magnitude is an **assumed** wheel property
(§2), not a datasheet value. The *shape* of the result (monotonic, complete, systematic
offset) is robust; the exact threshold depends on the assumption. Stating both is what
makes the claim honest and defensible.

**This is the measured justification for residual RL:** a physical actuator effect, at
a plausible magnitude, destroys the mission requirement for the classical controller —
and leaves a structured, learnable error.

---

## 8. Milestone D2 — residual SAC result: DISADVANTAGE (and why)

Residual SAC, 3 seeds, 150k steps, alpha = 0.2, trained on the Coulomb plant
(2e-4 N·m). Paired evaluation, n = 12, LQR arm produced by the same harness with
residual = 0 (validated: 1.578° matches C2's 1.602°).

| condition | controller | success | median final |
|---|---|---|---|
| ideal (no friction) | **LQR** | **100 %** | **0.147°** |
| ideal | seed 0 | 0 % | 6.051° |
| ideal | seed 1 | 0 % | 8.501° |
| ideal | seed 2 | 0 % | 5.870° |
| Coulomb 2e-4 | **LQR** | 0 % | **1.578°** |
| Coulomb 2e-4 | seed 0 | 0 % | 7.486° |
| Coulomb 2e-4 | seed 1 | 0 % | 6.635° |
| Coulomb 2e-4 | seed 2 | 0 % | 6.388° |

### Classification (directive section 15): RL DISADVANTAGE

The residual policy is **4-5x worse than the LQR in both conditions**, including the
one it was trained on. Experiment 1 (nominal non-degradation) fails outright. The
architecture is not exonerated by the friction result -- there is no friction result
to be exonerated.

### Diagnosis — two causes, both identified rather than guessed

**1. The reward is flat exactly where the task lives.** With `reward = -theta^2`
(theta in radians) and a +1/step bonus only below 1 deg:

- at 1.6° (the LQR's parked error): theta^2 = 7.8e-4 per step
- at 0.9° (the requirement): theta^2 = 2.5e-4 per step
- difference: **5.3e-4 per step, ~2.4 total per episode**

Against acquisition-phase costs of order -1400, that is **noise**. And the +1/step
bonus is a cliff that cannot be reached incrementally from 1.6°. So the policy has
**no incentive to close the 1.6° -> 0.9° gap**, which is the entire objective.
This is the same lesson as C4.2 (where the log-shaped reward was the only arm that
worked on the worst fault): the shaping must be normalised by the tolerance.

**2. The training budget is far too small for the episode length.** 150k steps at
4500 steps/episode is **~33 episodes of experience**. SAC cannot learn a residual
control law from 33 episodes. This is a budget error, not an algorithmic one.

### What this does and does not show

- It does **not** show that residual RL cannot fix the friction offset. The task was
  never given a usable gradient, so the experiment did not test the hypothesis.
- It **does** show that the current reward and budget are inadequate, with the
  mechanism identified.

### Next (D3), in order

1. Normalise the angle by the tolerance in the reward: `-(theta/theta_tol)^2`, which
   is 2.56 at 1.6° and 0.81 at 0.9° -- a gradient of 1.75/step (~7900/episode),
   i.e. ~3000x stronger in the band that matters. (Or reuse the C4.2 `log` shape.)
2. Train on a **friction distribution including zero**, so Experiment 1 can pass:
   0, 1e-4, 2e-4, 3e-4. A policy trained only on friction must fail on the ideal
   plant, and it did.
3. Raise the budget to >= 1M steps; report >= 3 seeds.
4. Only then re-run Experiment 1 (gate) and Experiment 2 (friction).

---

## 9. Milestone D3 — tol_norm reward: still a disadvantage, new failure mode

3 seeds x 300k steps, alpha = 0.2, coulomb = 2e-4, `reward_shape = tol_norm`.
Paired n = 8; LQR arm from the same harness (0.115 ideal, 1.620 coulomb) validates
against C2.

| condition | controller | success | median final |
|---|---|---|---|
| ideal | LQR | 100 % | 0.115° |
| ideal | seed 0 / 1 / 2 | 0 % | 6.057° / 4.517° / 11.560° |
| Coulomb 2e-4 | LQR | 0 % | 1.620° |
| Coulomb 2e-4 | seed 0 | **25 % (2/8)** | 2.299° |
| Coulomb 2e-4 | seed 1 | 0 % | 5.417° |
| Coulomb 2e-4 | seed 2 | 0 % | 10.661° |

### Classification: RL DISADVANTAGE (with one signal worth noting)

Seed 0 reaches **25 % success under Coulomb friction where the LQR gets 0 %** -- the
first time any policy has beaten the LQR on the metric that matters. But it does so
with a **worse** median (2.299° vs 1.620°), and seeds 1 and 2 are far worse (5.4°,
10.7°). At n = 8 a 2/8 vs 0/8 difference is not significant, and the seed spread
(2.3° -> 10.7°) is larger than the effect. Recorded as a signal, not a result.

### The new failure mode, and why `tol_norm` was the wrong shape

`tol_norm` repaired the near-field gradient (7875 per episode vs 2.4) but destroyed
the far-field scale: at theta = 0.5 rad the penalty is (0.5/0.01745)^2 = **821 per
step**. Training returns consequently sat at **-1.2e6 to -1.6e6**. A value function
spanning 1e6 is badly conditioned, and the policy ends up chasing the acquisition
transient instead of the terminal precision it was supposed to fix.

**The correct shape is `log`**, which has both properties:

| | far field (theta = 2.7 rad) | gradient 1.6° -> 0.9° per episode |
|---|---|---|
| quad | -36/step | **2.4** (no signal) |
| **log** | **-10/step (bounded)** | **3060** |
| tol_norm | **-23940/step (1e6/episode)** | 7875 |

`log` gives a 1275x stronger band gradient than `quad` while keeping the far field
bounded -- and it is the same shape that won the C4.2 study on the worst fault.
**D4 will use `log`.**

### Unchanged blocker for Experiment 1

The ideal-actuator gate still fails (6.1° / 4.5° / 11.6° vs 0.115°), because training
is still confined to a single friction value. **No amount of reward shaping fixes a
policy that has never seen a frictionless actuator.** Friction must be randomised per
episode across 0 to 3e-4 before Experiment 1 can pass.

---

## 10. Milestone D4 — RESULT: the hybrid beats the LQR under friction, and pays for it nominally

3 seeds x 300k steps, `reward_shape = log`, friction randomised per episode in
[0, 3e-4], alpha = 0.2. Paired n = 12; LQR arm from the same harness (a = 0),
validated against C2 (1.578° vs 1.602°).

| condition | controller | success | median final | Fisher p vs LQR |
|---|---|---|---|---|
| ideal | **LQR** | **100 % (12/12)** | **0.147°** | — |
| ideal | seed 0 | 25.0 % (3/12) | 1.839° | 0.00017 (worse) |
| ideal | seed 1 | 58.3 % (7/12) | 0.671° | 0.019 (worse) |
| ideal | seed 2 | 75.0 % (9/12) | 0.822° | 0.109 (n.s.) |
| **Coulomb 2e-4** | **LQR** | **0 % (0/12)** | **1.578°** | — |
| Coulomb 2e-4 | **seed 0** | **35.3 % (6/12)** | 1.817° | **0.0069** |
| Coulomb 2e-4 | **seed 1** | **58.3 % (7/12)** | **0.665°** | **0.0023** |
| Coulomb 2e-4 | **seed 2** | **66.7 % (8/12)** | **0.841°** | **0.00067** |

### What this establishes

**Under Coulomb friction the residual policy beats a tuned LQR, significantly, on
every seed.** Seeds 1 and 2 reach **sub-degree median pointing (0.665°, 0.841°)** --
inside the 1° requirement -- where the LQR achieves **0/12** and parks at 1.578°.
The effect is large (0 % -> 35-67 %), consistent across seeds, and statistically
solid (p = 0.0069, 0.0023, 0.00067). This is the first measured RL advantage in the
project that is not explained away by a mis-set baseline.

**Experiment 1 (the gate) does not pass.** On the ideal actuator the hybrid is worse
than the LQR: significantly for seeds 0 and 1 (p = 0.00017, 0.019), not
distinguishable for seed 2 (p = 0.109). So the advantage is **conditional on friction
being present**, and it is **paid for in nominal precision**.

### The honest characterisation

This is a **trade-off, not a free win**: the residual corrects a physical defect the
classical controller cannot handle, and its cost is small-signal noise where no
correction is needed. Reporting only the Coulomb column would be exactly the
dishonest framing the directive forbids, so both columns are reported, both with
significance tests.

### Why the nominal cost appears, and the fix worth testing (D5)

A policy that must add torque to fight a deadband cannot also output exactly zero
when the deadband vanishes; what remains is a small, largely random residual around
the setpoint, which shows up as 0.6-1.8° instead of 0.147°.

**D5: gate the residual on the error magnitude.** Apply `alpha * delta_tau` only when
the pointing error exceeds the region where the LQR is provably stuck (about 1°,
per Milestone C2), and force it to zero inside. This is a physics-based switch, not
another network -- consistent with the project's standing rule that the safety layer
stays physical. It should preserve the Coulomb gain while restoring nominal
precision, and both can then be measured again at n >= 24.

---

## 11. D5 design diagnostic — the error-magnitude gate is WRONG

Before implementing the gate proposed in §10, the hypothesis was tested: does the
residual act at small error, where the LQR needs none? Measured |alpha * delta_tau|
binned by pointing error, seed 2, one episode per condition:

| error band | ideal: mean \|dtau\| (% of alpha*tau_max) | Coulomb: mean \|dtau\| |
|---|---|---|
| 0.5 - 1.0 deg | **30 %** | **47 %** |
| 1.0 - 2.0 deg | 28 % | 13 % |
| 2.0 - 5.0 deg | 37 % | 28 % |
| 5 - 200 deg | 95 % | 105 % |

### The hypothesis was confirmed, and the proposed fix was falsified

Confirmed: on the **ideal** plant the policy spends **~30 % of its authority at
0.5-1 deg**, where no correction is needed. That is the source of the nominal cost.

Falsified: on the **Coulomb** plant it spends **47 % at the same angles** -- because
that is precisely where it fights the deadband and holds sub-degree pointing. **The
identical behaviour is required under friction and harmful without it.**

Therefore **an error-magnitude gate cannot separate the two cases**: closing it
below 1 deg would remove the Coulomb benefit (the whole result of §10), and opening
it everywhere leaves the nominal cost. The design proposed in §10 would have destroyed
the very gain it was meant to protect -- caught by measurement, before implementation.

### The correct gate: detect the friction, not the error

The discriminating signal is not how large the error is, but **whether the wheel is
actually delivering the torque it was commanded**. A wheel in a stick-slip deadband
receives a command and produces less rotation than the command implies; a healthy
wheel does not. That quantity is already measured in this project: the per-wheel
regressor in `health_estimation.py` compares commanded torque against the observed
wheel-speed response, and it identifies `h` from exactly this residual (C2-h: h = 0
in 3.2 s once commanded).

**D5: gate the residual on the estimated friction residual, not on the error.**

    enable = |tau_cmd - tau_achieved| > threshold        (per wheel, from wheel speed)
    tau_des = tau_LQR + alpha * delta_tau * enable

This is a **physics-based switch**, consistent with the standing rule that the safety
layer stays physical rather than another network. Expected outcome:

- no friction -> gate closed -> pure LQR -> nominal precision restored (~0.147 deg)
- friction present -> gate open -> residual active -> Coulomb benefit retained

Both must then be re-measured at n >= 24, and the gate threshold must be
pre-registered, not tuned after seeing the result.
