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
