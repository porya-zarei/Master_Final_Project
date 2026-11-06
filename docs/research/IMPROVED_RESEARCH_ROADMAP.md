# Improved Research Roadmap — Critical Review and Revised Plan

**Document type:** analysis and planning only. No code, no training, no history changes.
**Inspected at:** branch `residual-rl`, HEAD `1967326`, working tree clean.
**Author:** study assistant, in the role of independent reviewer.

---

## 0. Executive summary

The project has one central empirical claim in progress — that a residual RL layer
restores 1° pointing under Coulomb friction where a tuned LQR fails — and that claim
is **weaker than previously reported**. The measured effect is large and consistent in
direction, but the statistical inference behind `p < 0.001` used the wrong unit of
analysis: twelve episodes from one policy are not twelve independent samples. At the
correct unit (seed), the evidence is suggestive, not established.

Three further conclusions of this review:

1. **The classical baseline is too weak to support any advantage claim.** All reported
   comparisons use a nominal LQR. A fault-aware / gain-scheduled LQR and an MPC
   baseline exist or are feasible and have not been run against the RL policy. Until
   they are, no "RL beats classical" claim is defensible.
2. **The proposed Lyapunov filter is not a safety guarantee** and must be renamed and
   scoped accordingly. It is a model-based performance filter whose one-step
   inequality is invalidated by model error, saturation, and allocation.
3. **The friction-estimation problem is an observability problem, not an estimator
   problem.** D5 demonstrated, by measurement, that the estimator receives no usable
   excitation in the operating condition it is meant to detect. Any new estimator that
   does not first solve the excitation question will fail the same way.

The recommended next milestone is **not** more RL training. It is a **measurable-signal
audit and baseline-strengthening step** (§11, M1) whose deliverable is a defensible
comparison harness. Everything else depends on it.

---

## 1. Verified project state

### 1.1 Repository facts (inspected)

| item | value |
|---|---|
| branch | `residual-rl` (ahead of `master` at `714bf50`) |
| HEAD | `1967326` |
| working tree | clean |
| tracked evidence | 13 JSON artifacts in `reports/` |
| `results/` | gitignored — policies and logs are **not** tracked |
| test suites | 5 files, **29 test functions** |
| plant | custom NumPy Gymnasium env (not Basilisk) |
| control rate | 5 Hz, `dt = 0.1`, 2 substeps, 0.2 s control period |
| horizon | 900 s = 4500 steps |
| wheels | `max_torque = 0.01 N·m`, `J_w = 2e-4 kg m²`, `max_speed = 628.3 rad/s` |
| reward config | `bonus` default, `tol = 1°`, θ-weight 1.0, rate 0.1, control 0.01 |

### 1.2 Classification

**Implemented and verified** (test or reproduced measurement):

- Frame conventions (`C_BN` semantics), 12/12 tests.
- 6-state MEKF with gyro-bias estimation, 3/3 tests, bias convergence 3.8e-6.
- Torque allocator with optional health input, 5/5 tests; oracle path bit-identical.
- Actuator nonlinearity models (friction, deadzone, rate limit, quantisation), 5/5.
- Residual wrapper: `a = 0` reproduces the LQR to <1e-9 over 200 steps, 4/4.
- Coulomb sweep at n=16: monotonic, complete failure at ≥2e-4 (0/16).
- Inertia mismatch ±20 %: ≤11 % slower, no loss of the criterion.

**Implemented but insufficiently validated:**

- The D4 advantage claim (statistics, §2.3).
- The health estimator as a *gate* (it is validated as a fault estimator under
  injected excitation, not under closed-loop quiet operation).
- The gain-scheduled controller (`gain_scheduled.py`) — implemented, tested in
  isolation, but **not used in any paired comparison** against the RL policy.

**Proposed but not implemented:**

- Friction estimator with additive offset and multiplicative gain.
- Lyapunov / performance filter.
- Any MPC baseline.
- Any SIL stage.
- Observation conditioning on estimated fault state.

**Attempted and abandoned (with recorded reasons):**

- Reward `quad` as the primary shaping (no usable gradient in the 1–2° band).
- Reward `tol_norm` (far-field scale ~1e6, ill-conditioned critic).
- Slip-differentiator friction detector (1.7× separation, unusable).
- Health-estimator gate (100 % of updates rejected for lack of excitation).
- Error-magnitude gate (falsified before implementation: identical behaviour is
  required under friction and harmful without).

**Unknown / requires investigation:**

- Whether `results/` checkpoints for D4 seeds still exist and load.
- The exact predicate of the excitation guard in `health_estimation.py`.
- Whether the LQR baseline in D4 would change under a fault-aware formulation.

### 1.3 Reproducibility

Reproducible from artifacts: the actuator benchmark, the Coulomb sweep, the inertia
sweep, the LQR-vs-RL paired harness (script + JSON), the frame audit.

**Not fully reproducible:** every trained policy, because `results/` is gitignored and
no checkpoint hashes are recorded in `reports/`. The JSON files contain the *numbers*
but not the *weights*. This must be fixed before any result is published.

---

## 2. Critical review of D2–D5

### 2.1 D2 — residual SAC, quadratic reward

**Findings that survive:** the reward `−θ²` in radians gave a 1.6°→0.9° improvement a
value of ≈2.4 reward units per 4500-step episode, against acquisition costs of order
1400. The policy had no usable gradient for the objective it was supposed to optimise.
Measured directly on the reward function, not inferred.

**Findings that do not survive:** the causal attribution "reward is *the* cause." The
budget was also ≈33 episodes of experience. Both were sufficient to fail; the
experiment cannot separate them, and the claim should be "reward scale and budget were
both inadequate", not "the reward was the cause."

### 2.2 D3 — tolerance-normalised reward

`tol_norm` produced far-field penalties of (0.5/0.01745)² ≈ 821 per step at θ = 0.5 rad,
and training returns of −1.2e6 to −1.6e6. **The claim that this "destroyed the critic"
is plausible but not demonstrated** — no diagnostic of the value function's conditioning
was recorded. This must be downgraded to "consistent with ill-conditioning" unless a
critic-loss or value-range diagnostic is produced.

### 2.3 D4 — the advantage claim, re-examined

Reported: at Coulomb 2e-4, LQR 0/12 vs seeds 6/12, 7/12, 8/12, Fisher one-sided
p = 0.0069, 0.0023, 0.00067; at ideal, LQR 12/12 vs 3/12, 7/12, 9/12.

**Six defects, in order of severity:**

1. **Wrong statistical unit.** Episodes generated by one policy are not independent:
   they share the weights, the seed, and the training history. The correct unit for a
   claim about the *method* is the **seed**, giving n = 3, not n = 12. All quoted
   p-values treat correlated episodes as independent Bernoulli trials and are therefore
   **invalid as stated**.
2. **Wrong test for the design.** The comparison is paired by initial condition. The
   appropriate test is **McNemar's** (or an exact sign test on discordant pairs), not
   Fisher's exact test, which assumes independent groups.
3. **No multiple-comparison control.** Three seeds × two conditions = six tests, with
   no correction. At seed level the minimum attainable two-sided p for n = 3 is 0.25
   (sign test), i.e. **the design cannot reach significance regardless of effect size**.
4. **Effect-size and CI absent.** Only point estimates and p-values were reported. A
   claim needs the difference with a bootstrap CI, clustered by seed.
5. **Baseline independence.** The LQR arm was produced by `ResidualADCSEnv` with
   `a = 0`, not by an independent controller implementation. It was validated against
   the classical loop (1.578° vs 1.602°), which is good practice but does not satisfy
   the independence requirement: a shared defect in the wrapper would affect both arms.
6. **Baseline strength.** The comparator is a **nominal** LQR. It is not fault-aware,
   not gain-scheduled, and includes no MPC. `gain_scheduled.py` exists and was never
   used here.

**What survives scrutiny:**

- The **effect is large** (0 % → 35–67 % success) and **consistent in direction**
  across all three seeds.
- The nominal cost is real in sign (all three seeds worse on the ideal plant).
- The physical mechanism — a systematic 1.5–1.9° park in the stick-slip deadband,
  reproduced independently at n = 16 — is solid and is the strongest part of the work.

**What does not survive:** the phrase "statistically significant, p < 0.001". The
honest statement is:

> In three training seeds, the residual policy succeeded where the nominal LQR did not,
> with a large and consistently signed effect. The design (n = 3 seeds, episode-level
> pairing only) is underpowered to establish this at the method level; a minimum of
> five seeds with seed-clustered inference is required before the claim is made.

**Action required:** recompute D4 with seed-clustered bootstrap CIs and McNemar at the
episode level as a secondary analysis, then report both, explicitly labelled.

### 2.4 D5 — estimation and gating

**Findings that survive (all measured):** the raw slip differentiator separates healthy
from friction by only 1.7× because `J_w ω̇_w ≠ τ_cmd` even on a healthy wheel — the
`−ω×H_w` coupling is aliased by finite differencing. The health estimator was dormant
under the default configuration (`n_upd = [0,0,0]`, all skip counters zero), a genuine
defect now fixed. Under closed-loop quiet operation the excitation guard rejected
**100 %** of updates.

**Finding that requires correction of language:** "the gate can never open" is too
strong. It is demonstrated for *this estimator with these guards at this operating
point*. Whether a properly conditioned model-based residual can observe the deadband
is an open question (§5), because the wheel's failure to accelerate under a non-zero
command is itself informative.

### 2.5 Summary judgement

| claim | status |
|---|---|
| Coulomb friction breaks a tuned LQR at ≥2e-4 N·m | **supported** (n=16, monotonic, complete) |
| The mechanism is a stick-slip park | **supported** |
| Residual RL restores pointing under friction | **provisional** — large effect, underpowered design |
| Residual RL costs nominal precision | **provisional**, same design |
| RL is better than classical control | **not supported** — baseline too weak |
| The gate is impossible in principle | **not established** — only this implementation failed |

---

## 3. Fault taxonomy

Each entry: model · physical meaning · parameters · timing · observability ·
role (train / val / held-out) · expected control impact.

### A. Reaction wheels

| ID | fault | model | observability | role |
|---|---|---|---|---|
| RW-1 | total failure / lock | `τ = 0` (or constant offset) | high once commanded | train + test |
| RW-2 | partial effectiveness | `τ = h·τ_cmd`, `h ∈ (0,1)` | high with excitation | train |
| RW-3 | Coulomb friction | `τ = τ_cmd − τ_c sign(ω)` | moderate | **held-out** |
| RW-4 | stiction / deadzone | `τ = 0` if `|τ_cmd| < τ_s` | only when commanded below `τ_s` | **held-out** |
| RW-5 | viscous friction | `τ = τ_cmd − b ω` | high (speed-dependent) | train |
| RW-6 | saturation | `|τ| ≤ τ_max` | trivially observable | constraint |
| RW-7 | speed limit | `|ω_w| ≤ ω_max`, torque rejected at limit | observable | constraint |
| RW-8 | rate limit | `|dτ/dt| ≤ r_max` | observable | test |
| RW-9 | gradual degradation | `h(t)` ramp | needs tracking | **held-out** |
| RW-10 | intermittent | `h(t)` telegraph, random dwell | hard | **held-out** |

### B. Magnetorquers

Mandatory physics: `τ_MT = m × B(t)`, with `B` time-varying along the orbit. MTQs must
**never** be modelled as independent three-axis torque sources.

| ID | fault | model | note |
|---|---|---|---|
| MTQ-1 | dipole effectiveness loss | `m_eff = h_m · m`, `h_m ∈ (0,1)` | torque scales linearly |
| MTQ-2 | total failure | `m_eff = 0` | rank-deficient authority |
| MTQ-3 | command bias | `m_eff = m + b_m`, `|b_m| ≤ m_max` | acts as a disturbance |
| MTQ-4 | saturation | `|m| ≤ m_max` | constraint |
| MTQ-5 | delayed / unavailable | `m_eff(t) = m(t − τ_d)` or zero | held-out |

**Structural consequence:** because `τ ⊥ B`, the instantaneous controllable subspace is
2-dimensional. Fault tolerance against MTQ loss is therefore bounded by the geometry,
not by the controller. This must be stated, not discovered later.

### C. Sensors

| ID | fault | model | observability |
|---|---|---|---|
| SEN-1 | gyro bias | `ω_m = ω + b`, `ḃ = w_b` | observable given attitude reference |
| SEN-2 | gyro noise increase | `σ` scaled 5–20× | affects MEKF covariance |
| SEN-3 | gyro dropout | measurement = NaN / stale | detectable by staleness |
| SEN-4 | magnetometer bias | additive, body-fixed | couples with orbit model |
| SEN-5 | magnetometer dropout | stale | detectable |
| SEN-6 | sun-sensor error | angular bias, or unavailable | only affects sun-referenced modes |
| SEN-7 | star-tracker dropout / delay | stale or delayed | **primary attitude reference** |
| SEN-8 | star-tracker error | angular noise increase | MEKF covariance |
| SEN-9 | intermittent combinations | random subsets | held-out |

### D. Model and environment

| ID | fault | model |
|---|---|---|
| MOD-1 | inertia uncertainty | `J(1+δ)`, δ ∈ [−0.2, 0.2] |
| MOD-2 | CoM offset | adds `r_cm × F` coupling |
| MOD-3 | external disturbance | constant + harmonic torque |
| MOD-4 | residual dipole | `m_res × B`, the dominant LEO disturbance |
| MOD-5 | environmental model error | density / field magnitude scaling |
| MOD-6 | timing delay | one or more control periods |

### E. Timeline classes (orthogonal to the above)

1. Present at initialization.
2. Occurring during operation (step change).
3. Gradual (ramp).
4. Intermittent (telegraph).
5. Combined.

### 3.6 Staged test matrix — deliberately not a Cartesian product

| stage | content | purpose |
|---|---|---|
| **S0** | healthy, no friction, ±20 % inertia | regression / nominal |
| **S1** | one fault family at a time, mid-range severity | attribution |
| **S2** | severity sweep within the decisive family (Coulomb) | the boundary |
| **S3** | two-fault combinations (one actuator + one sensor) | interaction |
| **S4** | **held-out**: stiction, gradual degradation, intermittent, timing delay | generalization |
| **S5** | combined stress, only for the final policy | headline, reported separately |

Regla: never test on a cell whose severity appeared in training. Held-out families
(S4) are never trained on.

---

## 4. Architecture reassessment

### 4.1 Proposed architecture (as implemented)

```
sensors → MEKF (q̂, ω̂, b̂) → classical LQR → + α·Δτ_RL → [filter] → allocator → plant
                                                     ↑
                                              fault estimator
```

### 4.2 Alternatives

| architecture | advantages | disadvantages | verdict |
|---|---|---|---|
| pure classical LQR | simple, interpretable, provable locally | fails the friction case entirely | **baseline, insufficient alone** |
| fault-aware / gain-scheduled LQR | adapts to `h`, cheap, no training | needs a fault estimate; no friction model | **must be a baseline** |
| robust control (H∞ / μ) | handles bounded uncertainty formally | conservative; needs a disturbance model; friction is nonlinear | **worth one baseline** |
| MPC | handles constraints and faults naturally; strong competitor | needs a model; QP at 5 Hz is easy (small problem) | **strongly recommended baseline** |
| pure RL (torque) | no structure needed | must relearn allocation, limits, geometry; sample-hungry; no guarantees | reject as primary |
| residual RL (current) | keeps classical structure, learns only the correction | needs the baseline to be good; residual authority must be sized | **keep as primary** |
| RL + fault estimate | informs the policy | depends on observability, which failed in D5 | conditional on §5 |
| RL + performance filter | bounds the damage | can veto useful actions; not a guarantee | **keep, renamed** |

### 4.3 Recommendation

Keep the residual architecture, with three changes:

1. **Comparators become fault-aware.** A nominal LQR cannot be the reference when the
   thesis is about fault tolerance.
2. **The policy outputs a body-torque residual** (as now). Rationale: the allocator
   owns actuator limits, fault redistribution, and MTQ physics. Moving the residual to
   per-wheel torques would entangle the policy with allocation and with a 3→3 map that
   the allocator already solves. **Consequence:** the policy cannot express an
   allocation preference, which is a deliberate loss of authority.
3. **Add estimator confidence to the observation** only if §5 shows the estimate is
   informative. Do not add inputs that are noise.

**Do not add modules without a measured reason.** Each of the filter, the estimator, and
the confidence input must justify itself by an ablation.

---

## 5. Fault estimation and observability

### 5.1 The wheel equation, written correctly

For wheel *i* aligned with a body axis:

```
J_w ω̇_w,i = τ_cmd,i − τ_f,i − (ω × H_w)_i
```

Therefore the friction torque is, in principle, the model-based residual:

```
τ_f,i = τ_cmd,i − J_w ω̇_w,i − (ω × H_w)_i
```

**The coupling term is not optional.** Omitting it was the direct cause of the D5
failure: the naive detector reported 1.34e-4 of "slip" on a *healthy* wheel, against a
2e-4 friction it was meant to detect.

### 5.2 What is observable, and when

| quantity | condition for observability |
|---|---|
| `h` (effectiveness) | wheel commanded with varying torque; `ω̇_w` measurable |
| `τ_f` (Coulomb) | commanded torque must **exceed** the deadband; then `ω̇_w = 0` while `τ_cmd ≠ 0` |
| `b` (viscous) | wheel spinning at several speeds |
| gyro bias | attitude reference available and changing |
| MTQ effectiveness | `B` direction varies (it does, along the orbit) |
| inertia error | angular acceleration excitation |

**The critical insight D5 produced:** at the parked operating point the LQR command is
*balanced* by friction, so `ω̇_w ≈ 0` and the residual reduces to `τ_f ≈ τ_cmd`. That
is observable **provided the guard admits the sample**. The guard rejected 100 % of
updates, so the failure was in the guard/conditioning, not necessarily in the physics.

**This is the single most important open question in the project** and must be
resolved before any estimator is built:

> Under closed-loop LQR holding at ~1.6°, does `τ_cmd` exceed the excitation thresholds
> used by the guard, and if not, why does the controller equilibrium command less than
> the friction it is balancing?

### 5.3 Approaches

| approach | strength | weakness | when to use |
|---|---|---|---|
| model-based residual (above) | transparent, no training | needs accurate `J_w`, coupling, `ω̇` | **first** |
| RLS with offset + gain | separates friction from fault | still needs excitation | second |
| EKF on augmented state | principled uncertainty | linearisation, tuning | if noise dominates |
| multiple-model (IMM) | handles discrete fault modes | combinatorial | for intermittent faults |
| data-driven | no model | no guarantees, needs labels | last resort |

### 5.4 If a fault is not observable

The architecture must remain functional. Two defensible options:

- **Robust fallback:** a controller designed for the worst case in an uncertainty set,
  so an unestimated fault degrades performance but not stability.
- **Conservative allocation:** assume a wheel may be degraded and allocate with margin,
  sacrificing some performance for guaranteed authority.

**Neither requires the RL policy to be fault-aware**, which is the point: the policy
must not be the only thing standing between an unobservable fault and loss of pointing.

### 5.5 Standing rule

The policy may receive only measurable signals and estimates. **`h_true` must never
enter the observation.** This rule has been respected and must be tested by an
assertion in the environment, not by discipline.

---

## 6. RL formulation reassessment

| question | assessment |
|---|---|
| **SAC vs PPO** | SAC is the better *primary* here: off-policy, sample-efficient, continuous control, and it learned where PPO did not (ep_rew 2.7e3 vs −11k on the same task). Keep PPO as the pre-registered challenger, since it is the historical Baseline C. |
| **residual vs direct** | residual is correct: it preserves the classical structure, makes `a = 0` a provable identity, and confines learning to the correction. Direct torque control would have to rediscover allocation and limits. |
| **fixed vs adaptive α** | fixed α is honest but arbitrary. Adaptive α is a *research question*, not an obvious improvement: it adds a tuning surface that can manufacture apparent gains. **Keep α fixed and ablate it** (0.1 / 0.2 / 0.4) rather than adapt it. |
| **what the policy outputs** | body-torque residual. See §4.3. |
| **observation** | currently 15 = θ(3), ω_err(3), wheel speed(3), τ_LQR(3), prev action(3). **Do not grow it to 21 without evidence.** Proposed: 15 + `ĥ`(3) only if the estimate passes an informativeness test; add a 2–3 step history only if a recurrent/history ablation shows a gain. Larger observations with uninformative inputs are a known failure mode. |
| **reward** | `log` shape: bounded far field (~10/step) and a 3060/episode gradient in the 1–2° band. This is the only shape with both properties and it has empirical support (C4.2). Keep it. |
| **domain randomisation** | required. Already implemented for friction; extend to `h`, timing, inertia. Randomise over the **training** distribution only; keep S4 held out. |
| **curriculum** | avoid a curriculum that visits only easy cases first and never returns; use a fixed mixture and let the distribution be stationary. |
| **budget** | ≥1M steps, ≥5 seeds. At 4500 steps/episode that is still only ~220 episodes per seed — this is a **sample-efficiency constraint of the formulation**, and should be stated as a limitation, not hidden. |
| **generalisation** | measured only on held-out families (S4). Training-cell performance is not evidence of generalisation. |

---

## 7. Safety / performance filter assessment

### 7.1 What must be corrected in the previous design

The proposed condition

```
V(x_{k+1}^RL) ≤ V(x_{k+1}^LQR) + ε ,   V = θᵀQθ + ωᵀRω
```

was described as giving non-degradation "by construction". **That is not correct** and
must not be claimed.

### 7.2 Conditions under which the inequality is even meaningful

1. **Model validity.** `x_{k+1}` is a *prediction*. With inertia error, unmodelled
   friction, and disturbance torques, the predicted decrease need not occur. The
   filter is only as good as the model.
2. **Allocation and saturation.** The commanded body torque is not the delivered
   torque: the allocator redistributes, MTQs act only `⊥ B`, and wheels saturate.
   Predicting `x_{k+1}` from `τ_cmd` rather than `τ_delivered` invalidates the test.
3. **One step is not enough.** A residual that increases `V` for one step and reduces
   it over ten is vetoed. This is myopia, not safety.
4. **Feasibility.** There may be no candidate action that satisfies the inequality; a
   fallback must be defined (return to `τ_LQR` is the only defensible one).
5. **`V` is a candidate, not a certificate.** No Lyapunov decrease is proven; `Q` and
   `R` are LQR weights, chosen for performance, not for a stability proof.

### 7.3 Required terminology

| phrase | permissible? |
|---|---|
| "formal safety/stability guarantee" | **no** |
| "model-based performance filter" | **yes** |
| "candidate Lyapunov function" | yes, with the caveat that no decrease is proven |
| "empirically non-degrading in tested conditions" | yes, if measured |

### 7.4 Hard constraints, enforced independently

The filter must not be the mechanism enforcing physical limits. These are separate,
hard, and unconditional:

- `|τ_wheel| ≤ τ_max`
- `|ω_wheel| ≤ ω_max`
- wheel momentum budget
- `|m_MTQ| ≤ m_max`
- actuator availability (a failed wheel delivers zero, regardless of command)
- attitude / rate limits where stated (with the caveat that the 1° criterion is an
  **evaluation threshold**, not a derived mission requirement)

### 7.5 How to evaluate the filter honestly

Run four arms on identical seeds: LQR-only, RL unfiltered, RL + one-step filter,
RL + N-step filter. Report the **filter intervention rate** as a first-class result: a
filter that rejects 95 % of actions has produced a classical controller with extra
latency, and that must be said.

---

## 8. Classical baseline strategy

**Mandatory before any RL claim.** All arms share: dynamics, initial conditions
(drawn once and reused), allocator, physical limits, disturbances, fault scenarios, and
**comparable fault information**.

| arm | what it is | why it must exist |
|---|---|---|
| B1 nominal LQR | existing | the historical reference |
| B2 fault-aware LQR | allocate with `ĥ`; retune `R` for reduced authority | tests whether the RL advantage is just adaptation |
| B3 gain-scheduled LQR | `scheduled_K(J,Q,R,health)` — already implemented | the cheapest strong competitor |
| B4 MPC | short-horizon QP at 5 Hz with the fault model | **the strongest competitor; must be run** |
| B5 bang-bang / time-optimal | already used for the L4 gate | controls for the speed lever |
| R1 residual SAC | primary RL | — |
| R2 residual PPO | challenger | pre-registered |

**Independence requirement:** B1 must be evaluated through the **classical controller
path**, not through `ResidualADCSEnv`. The wrapper is a convenience for R1/R2, not a
baseline implementation. If the two disagree, the wrapper is wrong.

**Forbidden:** weakening a baseline (looser weights, no fault handling, worse
allocation) to manufacture a win.

---

## 9. Experimental methodology and statistics

### 9.1 Data separation

| split | content | rule |
|---|---|---|
| train | randomised fault distribution, S0–S2 severities | may be seen |
| validation | same families, **unseen severities** | for model selection only |
| test | **S4 held-out families** and unseen combinations | touched once, at the end |

No test cell may influence training, reward shaping, α, or the filter threshold.

### 9.2 Metrics

Primary: sustained pointing success under a stated threshold, **and** final attitude
error. Both are always reported together (Milestone C taught that first-entry speed and
sustained accuracy can point in opposite directions).

Secondary: RMS error, max error, time to acquisition, settling time, recovery time,
rate violations, wheel-speed violations, control effort, constraint violations, filter
intervention frequency, computational cost per step.

**The 1° threshold must be labelled as an evaluation criterion of this study, not as a
derived mission requirement.** Any other pointing target used elsewhere must be stated
separately.

### 9.3 Statistics — corrected

1. **Unit of analysis: the seed.** Episodes within a seed are correlated. Any claim
   about the method is made at seed level or with seed-clustered inference.
2. **Clustered bootstrap** over seeds for the difference in success rate and in final
   error. Report the CI, not just a p-value.
3. **Paired tests within seed:** McNemar for success (paired by initial condition),
   Wilcoxon signed-rank for continuous metrics.
4. **Multiple comparisons:** Holm–Bonferroni across cells of the map.
5. **Minimum design:** **5 seeds**, and n ≥ 24 episodes per seed per cell. With 3
   seeds the minimum attainable two-sided p is 0.25 — the design cannot support a claim.
6. **Pre-registration:** criteria written before the run. D4's criteria were written
   before measurement and that practice must continue.
7. **Effect sizes with CIs** are the headline; p-values are supporting.

### 9.4 What the current D4 design can and cannot say

Can: "a large, consistently signed effect was observed in three seeds."
Cannot: "significantly better (p < 0.001)", because that p-value treats correlated
episodes as independent.

---

## 10. MIL / SIL architecture

### 10.1 MIL

- Reference specification complete enough to implement in another language.
- Regression: the frozen controller reproduces reported metrics on fixed seeds.
- Integrator step-size sensitivity: the same controller under two `dt` values.

### 10.2 SIL — independent software validation

```
[ plant server ]  <-- TCP, fixed-step clock -->  [ controller process ]
   dynamics            obs message                  estimator
   sensors             action message               LQR
   faults                                           residual policy
                                                    filter
                                                    allocator
```

Requirements:

- **Fixed-step, plant-driven clock** (deterministic replay) as the primary mode; a
  wall-clock mode for jitter sensitivity only.
- Explicit message schema, versioned; observation and action scaling defined in the
  spec, not inferred from code.
- **Numerical precision:** float32 policy vs float64 reference — the pointing
  difference must be *measured*.
- **Deterministic replay:** a logged episode must reproduce bit-identically.
- Failure handling: controller restart, stale message, NaN, deadline miss.
- Fault injection driven by the plant server, identical to MIL.

Tests: MIL/SIL numerical equivalence within a pre-declared tolerance; float32 vs
float64; observation/action consistency; restart; invalid input; timing determinism.

**Format:** ONNX is convenient but **not mandatory**. Justify it: for a 2×128×128 MLP,
a plain C forward pass is ~40 lines and removes a runtime dependency. The choice should
follow from the controller's complexity, not from convenience.

**Out of scope:** HIL, embedded targets, realtime OS, flight qualification.

---

## 11. Revised roadmap

### M1 — Measurement and baseline audit **(do this first)**

**Objective:** establish what the project can actually measure, and build a defensible
comparison harness before any new claim.

**Why first:** every later phase depends on (a) a baseline that is fair, (b) a
statistical design that can support a conclusion, and (c) knowing which signals are
physically available. Skipping this is what produced D4's overstated p-value.

**Work:** instrument the environment to log `τ_cmd`, `ω_w`, `ω̇_w`, `τ_delivered`,
`(ω×H_w)`, and the estimator's internal state; recompute D4 with seed-clustered CIs and
McNemar; run B1 through the classical path and compare with the wrapper; quantify the
excitation guard's predicate.

**Acceptance:** a written measurement report; D4 restated with correct statistics;
B1/wrapper agreement within a stated tolerance or a diagnosed cause; the guard's
behaviour explained at the parked operating point.

**Out of scope:** training, new estimators, filters.

### M2 — Baseline strengthening

B2 fault-aware LQR, B3 gain-scheduled, **B4 MPC**. All paired on the S0–S2 grid.
**Acceptance:** every baseline beats the nominal LQR somewhere; the strongest baseline
is identified and documented. If MPC beats everything, that is the finding and the RL
work must be re-justified.

### M3 — Observability study

Resolve whether friction, `h`, and MTQ effectiveness are observable in closed loop, and
under what excitation. Deliverable: an observability table backed by measurement, and a
decision on whether any estimator is worth building.

### M4 — Fault taxonomy implementation

Implement §3 families behind flags, default OFF, with per-family tests. Verify S0
reproduces current results bit-identically.

### M5 — RL formulation

Observation and action justified by ablation; SAC primary, PPO challenger; 5 seeds,
≥1M steps; reward fixed at `log` (already justified).

### M6 — The fault-space map

The headline: paired comparison across the staged matrix, seed-clustered inference,
Holm correction, held-out families reported separately.

### M7 — Filter (only if M2–M6 show it is needed)

Renamed "performance filter"; N-step; intervention rate reported; formal-guarantee
language prohibited.

### M8 — MIL/SIL

Spec → MIL regression → SIL split loop → numerics → timing → parity → fault injection.

### M9 — Thesis assembly

Canonical tables, figures, negative-results section, limitations.

**Dependency diagram**

```
M1 ──► M2 ──► M6 ◄── M5 ◄── M4 ◄── M3
 │      │      ▲
 │      └─► M7 ┘
 └─► M8 (spec can start after M1; SIL after M6 freeze)
```

---

## 12. Risk register

| risk | impact | likelihood | mitigation |
|---|---|---|---|
| MPC outperforms residual RL | thesis claim collapses | **moderate** | run it early (M2); if it wins, the contribution shifts to the fault-space analysis |
| friction is unobservable in closed loop | no gate, no fault-aware policy | moderate | M3; fall back to robust/conservative allocation |
| seed variance swamps the effect | no claim | moderate | 5 seeds; report clusters |
| 4500-step episodes make RL sample-inefficient | budget blows up | high | state as a limitation; consider shorter horizon for training only, with a documented shift |
| checkpoints lost (`results/` untracked) | irreproducible | **high** | checksum and archive policies outside `results/` |
| reward/hyperparameter tuning mistaken for capability | credibility | moderate | pre-registration; ablations |
| 1° threshold conflated with a mission requirement | overclaim | moderate | label explicitly in every table |

---

## 13. Open research questions

1. Does the LQR equilibrium command exceed the friction it balances? (M1)
2. Is friction observable without deliberate excitation? (M3)
3. Which classical method is strongest under friction — gain-scheduled, MPC, or robust?
4. Does the RL advantage survive on **held-out fault families**?
5. Is the nominal cost removable without losing the benefit?
6. Is the effect present at 5 seeds with clustered inference?
7. Can a body-torque residual express what is needed under MTQ-only authority?

---

## 14. Decisions requiring researcher approval

1. **M1 first** (measurement and baseline audit) before any training — recommended.
2. **5 seeds minimum** and seed-clustered inference as the reporting standard.
3. **MPC as a mandatory baseline** (adds work, but without it the claim is not
   defensible).
4. **Restate D4** with corrected statistics, including the retraction of "p < 0.001".
5. **Rename the filter** to "model-based performance filter" and prohibit guarantee
   language.
6. **Archive and checksum policies** so results are reproducible.

---

## 15. Required extra deliverables

### 15.1 Principal weaknesses of the previous plan

1. Statistical unit wrong; significance overstated.
2. Baseline too weak (nominal LQR only) for a fault-tolerance thesis.
3. No held-out fault families — generalisation was asserted, not tested.
4. Filter described as a guarantee without justification.
5. Training on a single fault magnitude, then claiming generalisation.
6. No MPC comparator.
7. Checkpoints untracked → results not reproducible.
8. Success criteria mixed with mission requirements (the 1° threshold).
9. Two of three failed experiments attributed to a single cause without a separating
   experiment.

### 15.2 Old vs improved roadmap

| old (G1–G6) | problem | improved |
|---|---|---|
| G1 fault grid | a grid without observability analysis | M4 taxonomy **after** M3 observability |
| G2 obs 21 | added inputs assumed informative | M5 adds inputs only if an ablation justifies them |
| G2b friction estimator | assumes the estimator is the problem | M3 establishes whether it is observable at all |
| G3 randomised env | fine | M4 |
| G4 Lyapunov filter | mislabelled as a guarantee | M7, renamed, only if needed |
| G5 train 1M | no baseline first | M5 **after** M2 baselines |
| G6 map | pairs against a weak baseline | M6 pairs against the strongest baseline |
| — | no measurement audit | **M1 added first** |

### 15.3 First milestone, precise acceptance

**M1 — Measurement and baseline audit.** Accepted when:

1. `docs/research/M1_measurement_report.md` exists and contains, for the parked
   Coulomb case, the time series of `τ_cmd`, `τ_delivered`, `ω_w`, `ω̇_w`, and
   `(ω×H_w)`, with the residual computed and the guard's decision annotated.
2. The guard's rejection predicate is stated and reproduced on at least one sample.
3. D4 is recomputed with seed-clustered bootstrap CIs and McNemar; both the corrected
   and the original numbers are reported side by side.
4. B1 evaluated through the classical controller path agrees with the wrapper within a
   tolerance declared **before** the comparison, or the discrepancy is diagnosed.
5. No training is run.

### 15.4 Claims that cannot yet be made

- "RL significantly outperforms classical control" — wrong test, wrong unit, weak
  baseline.
- "The improvement generalises across faults" — only one fault family, one magnitude,
  in the tests.
- "The filter guarantees safety/stability" — no such guarantee is established.
- "The gate cannot work" — only this implementation failed.
- "The 1° performance is the mission requirement" — it is an evaluation criterion.
- Any hardware, real-time, or flight-readiness claim.

---

## Appendix — literature anchors

Established results drawn on (to be cited properly in the thesis):

- Lyapunov stability and control Lyapunov functions — standard nonlinear control texts
  (Khalil; Slotine & Li).
- Reaction-wheel friction and stick-slip in attitude control — spacecraft ADCS
  literature on wheel friction compensation.
- Magnetic actuation geometry (`τ = m × B`, rank deficiency) — standard.
- Residual / shielded RL: action-projection and safety-shield literature; model-based
  shields with learned policies.
- Domain randomisation and generalisation in RL for control.
- Simulation-to-reality and SIL validation practice in GNC.

**Status:** recommendations are engineering judgements of this review unless marked as
established results. No numerical result in this document is new; every number is
quoted from a tracked artifact or a measurement recorded in the repository.
