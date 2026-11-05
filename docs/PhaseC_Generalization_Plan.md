# Phase C — Generalisation Week Plan

**Scope recorded:** development is confined to **MIL and SIL**. **HIL is deferred
indefinitely** -- no hardware (RPi or ESP32-S3) is part of this week, this phase, or
any claim made from it. The thesis claims simulation levels, not hardware.

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

## Phase D (revised) — MIL and SIL only

Two levels of simulation, each answering a different question. Being precise about the
distinction is what makes the results citable.

| level | what runs | question it answers |
|---|---|---|
| **MIL** | controller algorithm **and** plant model in one process (Python) | is the *algorithm* correct and does it perform? |
| **SIL** | the controller as **deployed software** (fixed-step, no RL framework), in a **separate process**, talking to the plant over a real interface | does the *software* implement it correctly, in real time, with realistic numerics? |

All of Phase C is MIL. SIL begins once the algorithm is frozen at G6.

### MIL milestones

| ID | deliverable | pass criterion |
|---|---|---|
| MIL-1 | **reference specification** of the discrete-time controller: observation vector and scaling, action → desired torque, allocator, safety filter, clipping -- writable as C from the document alone | an independent implementation from the spec alone reproduces the reference |
| MIL-2 | regression: the frozen controller reproduces the G6 reported metrics | exact match on a fixed seed set |
| MIL-3 | plant-model integrity: the same controller under two integrator step sizes converges (step-size sensitivity) | metric change bounded and reported |

### SIL milestones

| ID | deliverable | pass criterion |
|---|---|---|
| SIL-1 | policy exported to **ONNX**; equivalence vs PyTorch on a fixed input batch | max abs difference < 1e-5 |
| SIL-2 | loop split: plant server ↔ controller client (TCP, 5 Hz, timestamps both ends) | runs 900 s without a missed deadline |
| SIL-3 | **numerics**: ONNX float32 vs the float64 reference | pointing degradation quantified, not assumed zero |
| SIL-4 | **timing**: latency mean/p95/worst, and pointing performance under injected jitter | report the jitter sensitivity curve |
| SIL-5 | **parity**: SIL vs MIL on the same seeds | difference stated with a tolerance chosen *before* the run |
| SIL-6 | fault injection in the SIL loop (wheel dead at t = 300 s) | allocator + safety filter behave as in MIL |

### Why this ordering

MIL-1 (a spec complete enough to implement from) is what makes SIL meaningful: if the
spec is ambiguous, a SIL discrepancy cannot be attributed to the software rather than
the document. **A SIL result without MIL-1 is untraceable.**

### Explicitly out of scope

HIL, real actuators, real sensors, realtime operating systems, flight qualification.

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
4. **SIL timing source**: (a) simulated clock advanced by the plant server
   (recommended -- deterministic, reproducible) or (b) wall-clock real time (realistic
   jitter, non-reproducible runs).
