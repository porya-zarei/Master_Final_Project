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
