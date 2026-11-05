# Phase C — Generalisation Week Plan

**Pivot recorded:** the HIL target is **Raspberry Pi first** (was ESP32-S3). RPi runs
Python natively, so the frozen SB3 policy can be deployed unchanged for the first
integration; ESP32-S3 becomes the later embedded target, not the first milestone.

**Week objective:** replace the single-point D4 result ("RL wins at Coulomb = 2e-4")
with a **fault-space map** — one policy, trained over a randomised actuator/fault
distribution, evaluated on a grid, showing *where* RL beats the LQR, where it ties,
and where it loses, with a physical reason for each region.

**Why this matters for the thesis:** a single favourable operating point is a demo.
A map with a measured boundary is a scientific claim, and it is what makes
"RL benefits over a wide range of faults" defensible rather than asserted.

---

## The key algorithmic change: replace the gate with a Lyapunov safety filter

D5 failed because the gate needed to *detect* friction, and friction is unobservable
at rest (`skip_excite = 4500/4500`). That is a dead end by construction.

**The filter needs no detector.** Ask the question directly:

> Does this residual actually improve the state, according to the same cost the LQR
> is optimising?

    V(x) = theta' Q theta + omega' R omega        (the LQR's own Q, R)
    candidate_LQR = tau_LQR
    candidate_RL  = tau_LQR + alpha * delta_tau
    accept the residual iff   V(x_{k+1}^{RL}) <= V(x_{k+1}^{LQR}) + eps

using a one-step (or 3-step) model prediction. Otherwise fall back to the LQR.

**Why this is strictly better than the gate:**

| | friction gate (D5) | Lyapunov filter (G4) |
|---|---|---|
| needs the friction to be observable | **yes — blocked** | no |
| works at rest / at zero wheel speed | no | **yes** |
| nominal non-degradation | hoped for | **by construction** (up to model error) |
| physics-based, not a network | yes | yes |
| general across fault types | tied to one detector | **any fault the model sees** |

It also satisfies the standing rule that the safety layer stays **physical**, and it
converts the D4 trade-off (nominal cost) into a structural guarantee rather than a
tuned behaviour. The residual becomes an *optimisation proposal* that a model-based
monitor may veto — which is exactly the architecture a reviewer expects.

**Risk to measure, not assume:** one-step monotone decrease can veto a residual that
is beneficial over several steps. Mitigation: an N-step (3–5) check and/or a small
`eps`; both are pre-registered and ablated. If the filter is too conservative it will
suppress the friction benefit — that is a measurable outcome, not a hidden one.

---

## Milestones (this week)

### G1 — Fault space specification (before any training)

Define the space, and **separate training from testing** so the map is not measured on
points the policy memorised.

| axis | training distribution | test grid |
|---|---|---|
| Coulomb friction | U(0, 5e-4) continuous | {0, 5e-5, 1e-4, 2e-4, 3e-4, 5e-4} |
| wheel health (per wheel) | h ~ {1, 0.5, 0}, random subset | {healthy, 1@50%, 1 dead, 2@50%, 1@50%+1 dead} |
| fault timing | t = 0 or uniform in [0, 600] s | {t = 0, t = 300 s} |
| inertia error | J*(1+delta), delta ~ U(-0.2, 0.2) | {0.8, 1.0, 1.2} |
| sensor noise | nominal | nominal |

Deliverable: `docs/FaultSpace.md` with the grid, the metric definitions, and the
**pre-registered benefit criterion**: a cell counts as an RL win only if success is
higher by ≥ 20 points *and* the 95 % CI excludes zero, at n ≥ 24 paired.

### G2 — Generalised observation (conditioning)

A single policy cannot serve the whole space unless it can infer the actuator state.

    obs = 15 (current) + h_hat(3) + slip/friction proxy(3) = 21

`h_hat` must come from the estimator, **never** from `h_true` (standing rule).
The friction proxy is the model-based residual from G2b (below), not the raw
difference that failed at 1.7× separation.

**G2b — friction observable that actually works.** Regress, per wheel, the additive
offset *and* the gain with the coupling modelled:

    tau_ach = h * tau_cmd - tau_f        (2 parameters per wheel, RLS)

Unlike the naive differentiator, this separates an additive deadband (friction) from a
multiplicative loss (fault), which is exactly the distinction the project needs. This
is the piece D5 option (b) identified and deferred; here it is a deliverable.

### G3 — Generalised environment

Per-episode randomisation of friction (done), wheel health, fault timing, and inertia,
all behind flags with **defaults preserving every historical result**. Tests must
assert: with randomisation off, D4 numbers reproduce bit-identically.

### G4 — Lyapunov safety filter (the algorithmic centrepiece)

Implement behind a default-OFF flag; unit tests:

- LQR-only residual (delta_tau = 0) passes the filter unchanged → **bit-identical**.
- On the ideal plant, a residual that increases V is **rejected** → nominal precision
  preserved by construction.
- On the friction plant, a residual that decreases V is **accepted**.
- Prediction horizon N = 1 and 3, and `eps` × {0, small}: all ablated.

### G5 — Train the general policy

SAC (and PPO as the Baseline-C challenger), 3–5 seeds, ≥ 1M steps, curriculum
(healthy/no friction → randomised), obs 21. Report per-seed, never only the mean.

### G6 — The fault-space map (the headline result)

Evaluate the general policy and the LQR on the **whole test grid**, paired, n ≥ 24 per
cell, with the Lyapunov filter ON and OFF.

Deliverables:
1. A **benefit map**: per cell, success difference and final-error difference, with
   significance. Rendered as a heat map figure.
2. The **boundary**: the friction magnitude above which RL stops helping, and why.
3. An honest **loss region**, if any exists.

---

## Phase D (revised) — RPi first

| ID | deliverable |
|---|---|
| D.1 | policy → `policy.onnx` (ONNX Runtime on RPi, ARM64) — no framework rewrite needed |
| D.2 | RPi runs the policy at 5 Hz, host simulates the plant; timestamps both ends |
| D.3 | latency/jitter: mean, p95, worst case (a 5 Hz loop on RPi should be ≪ 1 ms) |
| D.4 | HIL fault injection in the loop |
| D.5 | *later* ESP32-S3 port as the embedded target |

RPi is not flight-qualified either; the claim remains a **bench HIL demonstration**.

---

## What I am explicitly NOT doing this week

- No plant redesign (Phase C is frozen after G6).
- No AdaJEPA (never gates anything).
- No new sensor models.

## Decisions requested

1. **Lyapunov filter as the D5 replacement** — recommended.
2. **G5 budget**: 3 seeds × 1M (~4 h) vs **5 seeds × 1M** (~7 h, recommended for a
   map that will be read cell-by-cell).
3. **Test grid size**: the full 6 × 5 × 2 grid is ~60 cells × 24 episodes ≈ heavy;
   recommended is the 6-friction × 4-health subset (~24 cells) for the map, with the
   remaining axes reported as a smaller ablation.
