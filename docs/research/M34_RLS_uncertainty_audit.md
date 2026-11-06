# M3.4 — RLS Uncertainty Model: Mathematical Audit

**Type:** read-only mathematical audit. No source, parameter, threshold or result was modified.
**Repository:** `E:\Education\Master\Final_Project`
**Branch:** `residual-rl` **HEAD:** `c9a4aa5` **Tree:** clean, `0 ahead / 0 behind` `origin/residual-rl`
**Inputs inspected:** `codes/satellite_adcs/friction_estimation.py`, `dynamics.py`, `controllers.py`,
`allocation_policy.py`, `simulate.py`, `sensors.py`, `config/*.yaml`, `codes/results/m33b/**`,
`docs/research/M33B_allocation_report.md`, `reports/m33b_state_aware_allocation.json`.

**Evidence labels used throughout:**
`[V]` verified from source code · `[O]` numerical observation from an existing artifact ·
`[D]` mathematical derivation · `[A]` assumption · `[Q]` open question requiring new data ·
`[R]` recommendation.

---

## 1. Executive summary

The estimator's stored matrix is a **correct inverse information matrix** but it is **not a parameter
covariance**, and the number compared against `SIGMA_H_MAX = 0.1` is **not a standard deviation**.

Three findings, in order of importance:

**1.1 The reported `sigma_h` has units of (N·m)⁻¹. Thresholding it is dimensionally invalid.**
`[D]` For the implemented regressor, `sigma_h = 1/sqrt(sum (tau - tau_bar)^2)`, which carries units of
reciprocal torque. `[O]` Verified to four decimal places against the recorded traces (§6.2). `[O]` The
same physics, with torque merely *written in mN·m*, yields `sigma_h = 0.0124` instead of `11.55` — the
gate would open (§4.3). The gate's verdict therefore depends on the unit in which torque is expressed,
the episode length, and the command magnitudes. It is an **excitation test with an unstated noise
scale**, not a confidence test.

**1.2 The same mis-scaling is simultaneously an adaptation defect.**
`[D]` In RLS, `P` is not merely reported — it *is* the gain (`K = P·phi / (1 + phi'P phi)`). Over-scaled
`P` therefore means over-scaled uncertainty **and** a mis-scaled estimator. `[O]` Both effects are
present in the existing artifacts: from a fault present at t=0 the estimate **stalls** at
`h_hat = 0.602` (median over 24 seeds) against a truth of 0.50, and a **mid-flight** fault to 0.5 is
**not tracked at all** (`0.9997`), while a batch least-squares fit to the *same recorded data* recovers
`0.4807` (§7.4). The information is in the data; the recursion does not use it.

**1.3 Point accuracy at h = 0.5 is not established, and one earlier impression must be corrected.**
`[O]` Over 24 seeds: bias `+0.106`, MAE `0.106`, max error `0.308`, and `min(h_hat) = 0.533` — the
estimator is *systematically high* and never reaches 0.50. A single-seed reading of `0.535` (used in the
M3.3-B report as "estimates are good") was optimistic and is superseded by these 24-seed statistics.

**1.4 The measurement-noise variance that any defensible interval requires has no physical source in the
current model.** `[V]` `sensors.py` contains no wheel-speed channel at all; the estimator and the RL
observation both read `dyn.omega_w` — the plant state (`adcs_env.py:134`, `simulate.py:135`). `[V]` The
wheel equation is otherwise exact (`dynamics.py:186`) and deadzone / rate-limit / viscous friction all
default to `0.0` (`dynamics.py:57–60`). `[O]` The only residual in the regression is unmodelled friction,
measured at `2.5e-4 N·m`. `[D]` Any covariance calibrated on this plant with zero noise collapses toward
zero, i.e. becomes infinitely confident; the correct noise floor is a **model-error budget**, which does
not yet exist.

**1.5 Verdict: CONDITIONAL GO** (§13) — the mathematics of the current model are now fully understood,
but a confidence-model change cannot be justified or validated until a wheel-speed sensing model and a
model-error budget exist, both of which are outside this audit's permission.

**Summary table**

| # | Claim | Status |
|---|---|---|
| 1 | Stored matrix = inverse information matrix under implicit `sigma_v = 1 N·m` | `[V]`+`[D]`+`[O]` confirmed to 4 dp |
| 2 | `sigma_h` is a standard deviation in `h` | **false** — it is `std(h)/sigma_v[N·m]` |
| 3 | `SIGMA_H_MAX = 0.1` is statistically meaningful | **false** — dimensionally inconsistent, unit-dependent |
| 4 | Implicit assumption `sigma_v = 1` | **confirmed** = 100 × `tau_max` = 3896 × observed residual |
| 5 | Good point estimates imply identifiability | **false** — the two are independent (§7.5) |
| 6 | Wheel equation exact / no tachometer | `[V]` exact except friction; no sensor exists |
| 7 | Gate can be repaired by a scaling constant | **no** — that is relabelling, not estimation (§9) |

---

## 2. Repository and implementation trace

### 2.1 State at audit time `[V]`

| item | value |
|---|---|
| root | `E:/Education/Master/Final_Project` |
| branch / HEAD | `residual-rl` / `c9a4aa5` |
| tree | clean; `0 ahead / 0 behind` `origin/residual-rl` |
| other branches / stashes / tags | `master` @ `714bf50`; 0 stashes; 0 tags |
| M3.3-B commit present | yes — `c9a4aa5` |
| M3.3-B artifacts present | `results/m33b/run.json` (n=24, 576 episodes), 24 episode files, 6 timeseries files, `reports/m33b_state_aware_allocation.json`, `docs/research/M33B_allocation_report.md`, `reports/m33b_parity_pre_post.json` |

No discrepancy between the expected and actual repository state. The preflight archive
`results/m33b_preflight_n1/` is also present and untouched.

### 2.2 Files, classes, functions, lines `[V]`

| concern | file:line | symbol |
|---|---|---|
| estimator class | `satellite_adcs/friction_estimation.py:29` | `class FrictionHealthEstimator` |
| constants | `…:52–54` | `N_MIN=5`, `SIGMA_H_MAX=0.1`, `H_TOL=0.05` |
| construction / defaults | `…:56–65` | `rw_J=2e-4`, `control_period=0.2`, `lam=1.0`, `p0=1e3`, `tau_min=1e-5`, `h_init=1.0` |
| state reset | `…:67–71` | `theta = [1,0]`; **`P = I₂ · p0`** (`:69`) |
| priming | `…:73–75` | `prime(omega_w)` → `last_w` |
| estimate | `…:77–79` | `h = theta[:,0]` |
| reported uncertainty | `…:85–87` | `sigma_h = sqrt(max(P[:,0,0],0))` |
| classification | `…:89–102` | `state()` |
| RLS update | `…:107–128` | `update(tau_cmd, omega_w_meas)` |
| measurement | `…:114` | `y = rw_J * dw / Tc` |
| excitation guard | `…:116–117` | skip if `abs(tau) < tau_min` |
| regressor | `…:118` | `phi = [-tau, 1]` |
| gain / covariance | `…:119–123` | `Pp=P/lam`; `den=1+phi@Pp@phi`; `K=Pp@phi/den`; `P=Pp-outer(K,phi@Pp)` |
| physical clip | `…:125` | `h → clip(h, 0, 1.5)` |
| plant wheel equation | `satellite_adcs/dynamics.py:186` | `ow_dot = (-tau_rw_eff + tau_f)/rw_J` |
| delivered torque | `…:173` | `tau_rw_eff = tau_rw * rw_health` |
| friction law | `…:178–179` | `tau_f = -(b_visc·w + c_coul·tanh(w/0.05))` |
| actuator defaults | `…:57–60` | `deadzone=0`, `b_visc=0`, `c_coul=cfg`, `rate_limit=0` |
| closed-loop wiring | `simulate.py:78–87` | estimator constructed with `control_period = 1/control_hz` (`:84`) |
| update call | `simulate.py:132–136` | `cons.update(prev_tau_rw, w_meas)` |
| allocated command fed back | `simulate.py:144–153` | post-allocator, post-residual, clipped command |
| conservative allocation | `satellite_adcs/controllers.py:148–160` | `resolve_effectiveness(...) → allocate_torque(health=h_used)` |
| policy | `satellite_adcs/allocation_policy.py:53–70` | UNKNOWN/HEALTHY → 1.0; DEGRADED → `max(h, 0.5)` |
| floor | `allocation_policy.py:32` | `H_FLOOR = 0.5` |
| sensors | `satellite_adcs/sensors.py` | **no wheel-speed channel** |

### 2.3 Call path (verified) `[V]`

```
dyn.omega_w  (plant state, NOT measured)  ─┐
                                           ├─> FrictionHealthEstimator.update
prev_tau_rw  (executed wheel command)    ─┘        │
                                                   ├─> .h        ─> controllers._allocate
                                                   └─> .state()  ─> resolve_effectiveness -> h_used
allocate_torque(tau_des, health=h_used) ──> tau_cmd  ──> dyn.step  (tau_eff = tau_cmd * rw_health)
```

### 2.4 Discrepancies found during the trace (all latent, none affecting the M3.3-B numbers)

1. `[V]` **`initial_speed_rad_s: 0.0` is a dead configuration key.** It appears only in
   `config/actuators.yaml:7` and is read by no Python file; `dynamics.reset()` hard-codes
   `omega_w = zeros(n_rw)` when `omega_w is None` (`dynamics.py:120–121`). This is the same defect class
   as G9 (a flag that reads like physics and moves no number). It is benign today only because the value
   is zero.
2. `[V]` **`cons.prime(dyn.omega_w)` is called before `dyn.reset()`** (`simulate.py:85` vs `:89`/`:93`),
   so `last_w` is primed from the *pre-reset* wheel speed. Harmless here (both are zero) but it is a
   latent ordering defect: with a non-zero initial wheel speed the first `y` would be a spurious spike.
3. `[V]` **There is no wheel-speed measurement anywhere in the model.** `sensors.py` models gyro,
   magnetometer, sun sensor, star tracker and GPS only; the speed enters the estimator as the exact plant
   state. Everything in §5 follows from this single fact.

---

## 3. Exact implemented regression and RLS equations

### 3.1 The plant equation, read from source `[V]`

`dynamics.py:186`:  `J_w · d(omega_w)/dt = -tau_rw_eff + tau_f`, with
`tau_rw_eff = tau_rw · h` (`:173`) and `tau_f = -(b_visc·omega_w + c_coul·tanh(omega_w/0.05))` (`:178–179`).

So, for wheel *i*:

```
J_w · dω_i/dt = -h_i · τ_cmd,i + τ_f,i          τ_f,i = -(b_v·ω_i + c·tanh(ω_i/0.05))
```

Both unknown quantities enter **linearly**, which is why the two-parameter regression is well posed in
principle.

### 3.2 The measurement, as implemented `[V]`+`[D]`

`friction_estimation.py:113–114`:

```
Δω_k = ω_k − ω_{k−1}                 (samples at the CONTROL rate, Tc = 0.2 s)
y_k  = J_w · Δω_k / Tc = J_w · (ω_k − ω_{k−1}) / Tc
```

This is a first-order (backward) difference of the wheel speed, scaled by `J_w` to a torque. Because the
dynamics integrate `n_sub = 2` RK4 substeps of `dt = 0.1 s` per control period, `y_k` is the **mean**
wheel acceleration over `[k−1, k]` multiplied by `J_w` — consistent with the model only if `τ_cmd` and
`τ_f` are constant over that interval.

`[V]` Timing alignment is **correct**: `update()` is called at the top of the control loop with
`prev_tau_rw` (the command executed during `[k−1, k)`) and the *current* `omega_w`; `last_w` is updated
at the end of `update()` (`:127`). So `y_k` is regressed against the command that produced it.

`[V]` The command is the **executed** wheel torque — post-allocation, post-residual, clipped to
`±tau_max` (`simulate.py:144–153`) — not the raw desired torque `tau_des`. This is correct and important:
regressing against `tau_des` would have folded allocator clipping into `h`.

### 3.3 The implemented recursion `[V]`

For each wheel independently (`n_rw = 3` scalar `2×2` problems, no cross-wheel coupling):

```
y_k = φ_k' θ_k + v_k ,     φ_k = [ −τ_k ,  1 ] ,   θ = [ h , τ_f ]'

θ_0 = [1 , 0]' ,   P_0 = p0 · I₂ = 1e3 · I₂

P⁻_k = P_{k−1} / λ                     (λ = 1.0 → no forgetting)
den  = 1 + φ_k' P⁻_k φ_k
K_k  = P⁻_k φ_k / den
θ_k  = θ_{k−1} + K_k ( y_k − φ_k' θ_{k−1} )
P_k  = P⁻_k − K_k ( φ_k' P⁻_k )        (Joseph-free standard form)
h    ← clip(h, 0, 1.5)                (:125, applied after the update)
n_upd++ if |τ_k| ≥ tau_min = 1e-5     (:116)
```

### 3.4 Sign and convention verification `[D]`

- Regressor column 1 is `−τ_cmd`, matching `−h·τ_cmd` in the plant. **Correct sign.**
- Regressor column 2 is `+1`, matching `+τ_f`. **Correct sign.**
- `τ_f` is *defined negative* for positive rotation (`−(c·tanh(ω/0.05))`), so a healthy spinning wheel
  must return `τ_f < 0`. `[O]` Seed 0, S2: `τ_f_hat = [−1.854e−4, −1.957e−4, −1.776e−4]` against a
  per-wheel truth of `−2.0e−4` (errors 7 %, 2 %, 11 %). Signs and magnitudes are consistent.
- Units of measurement and parameter are as claimed: `y` in N·m, `τ_cmd` in N·m, `h` dimensionless,
  `τ_f` in N·m. `J_w = 2.0e-4 kg·m²` is applied (`:114`), `Tc = 0.2 s` matches the true effective
  control period (`simulate.py:84` → `1/5 Hz`; `nctrl·dt = 2 × 0.1 = 0.2`). **Verified, no 25 %-style
  scale error.**
- Correlation structure: `Δω_k` and `Δω_{k+1}` share sample `ω_k`, so `{y_k}` is **not** white — see §5.3.

### 3.5 What the model does *not* contain `[V]`

| effect | present in plant? | in regressor? | consequence |
|---|---|---|---|
| deadzone | no (`deadzone_Nm` absent → 0.0) | no | none today |
| torque-rate limit | no (`rate_limit` absent → 0.0) | no | none today |
| viscous friction | no (`b_visc` absent → 0.0) | modelled by the `+1` column? **no — see below** | — |
| Coulomb `tanh` nonlinearity | yes | as a *constant* `τ_f` | model error near `|ω| < 0.05` |
| `τ_f` variation within a control period | yes | no | small, second order |
| wheel-speed sensor noise | **not modelled** | — | the central gap (§5) |
| speed clip at 628 rad/s | yes | no | guard needed; not exercised (max ≈ 461 rad/s) |

`[D]` Note a structural limitation: `+1·τ_f` can represent only a **constant** additive torque. The
viscous term `−b_v·ω` is proportional to the wheel speed, which is *not* a regressor column. With
`b_v = 0` this is harmless today; enabling viscous friction in `actuators.yaml` would silently be
absorbed into `h` and `τ_f` and destroy the separation the estimator exists to provide.

---

## 4. Dimensional analysis

### 4.1 Units of every quantity `[D]`

| quantity | symbol | unit |
|---|---|---|
| wheel inertia | `J_w` | kg·m² |
| control period | `Tc` | s |
| measured wheel acceleration | `Δω/Tc` | rad·s⁻² |
| **measurement** | `y_k` | **N·m** |
| commanded torque | `τ_k` | N·m |
| effectiveness | `h` | **dimensionless** |
| friction torque | `τ_f` | N·m |
| regressor | `φ = [−τ, 1]` | **[N·m, 1]** — mixed |
| information matrix | `Φ'Φ = [[Στ², −Στ],[−Στ, N]]` | **[[N²m², Nm],[Nm, 1]]** |
| covariance / inverse information | `P` | **[[1/(N²m²), 1/(Nm)],[1/(Nm), 1]]** |
| RLS gain | `K = Pφ/(1+φ'Pφ)` | inherits `Pφ` (mixed) |
| innovation | `y − φ'θ` | N·m |
| innovation variance | `σ_v²` | N²m² |
| parameter error | `θ̂ − θ` | `[1, N·m]` |
| **reported `sigma_h`** | `sqrt(P[0,0])` | **(N·m)⁻¹** |

**The two regression parameters have different units**, and the covariance is *not* a covariance of
`θ` until it is multiplied by the measurement-noise variance. This is the crux.

### 4.2 What `sigma_h` actually is `[D]`

`P = (P_0⁻¹ + Φ'Φ)⁻¹` with `P_0⁻¹ = 1e-3 · I₂`, negligible for `Στ² ≫ 1e-3`. In the near-orthogonal
case (`Στ ≪ sqrt(N·Στ²)`, true here) the `(0,0)` entry reduces to

```
P[0,0] = 1 / ( Στ² − (Στ)²/N ) = 1 / Σ (τ_k − τ̄)²
```

so

```
sigma_h_reported = sqrt(P[0,0]) = 1 / sqrt( Σ (τ_k − τ̄)² )        [(N·m)⁻¹]
```

`[O]` Verified numerically on the recorded S2 trace: closed form `12.4071`, implementation with
`p0 = 1e3` gives `11.5499`, and the **recorded** value is `11.5505` — agreement to four decimals. The
`p0` inflation of `Στ²` supplies the 7 % difference between `12.41` and `11.55`.

**The general relation** `[D]`. For the textbook recursion `P_k = (P_{k−1}⁻¹ + φφ'/σ_v²)⁻¹`,

```
Cov(θ̂) = σ_v² · P_k        ⟹   std(h) = σ_v · sqrt(P[0,0]) = sigma_h_reported · σ_v
```

The implementation never divides by `σ_v²`, i.e. it takes **`σ_v = 1` in whatever units `τ` is written**.
Therefore the reported number is

```
sigma_h_reported = std(h) / σ_v[in the unit of τ]
```

**It is a signal-to-noise ratio, not a standard deviation.** Comparing it to `0.1` asks: *"is the
parameter standard deviation at most 0.1 measurement-noise standard deviations?"* — a scale-free
statement that is only interpretable if `σ_v` is a physical quantity. Here `σ_v` silently becomes
`1 N·m`.

### 4.3 The decisive check: the same physics, three units `[O]`

Recomputing `P[0,0]` from the **same recorded command trace**, changing only the unit in which torque is
expressed (a pure change of variables, physically identical):

| torque written in | `sigma_h_reported` | gate `≤ 0.1`? |
|---|---|---|
| N·m (implemented) | 11.5499 | **closed** |
| mN·m | 0.0124071 | **open** |
| µN·m | 1.24071e−05 | **open** |

The gate's verdict is a unit choice. No physical statement about the estimator can depend on the unit a
quantity is recorded in, so `SIGMA_H_MAX = 0.1` cannot be a physical confidence threshold as used.

### 4.4 The implicit noise assumption, quantified `[O]`

| comparison | value |
|---|---|
| implied `σ_v` | `1 N·m` |
| as a multiple of `tau_max = 0.01 N·m` | **100 ×** the wheel's entire torque authority |
| as a multiple of the residual actually observed in the data (`2.567e-4 N·m`) | **3896 ×** |

The estimator therefore behaves as if every wheel-torque observation were uncertain by 100 times the
maximum torque the wheel can produce.

### 4.5 Direct answers `[D]`

1. **Does `sigma_h` have a physically meaningful unit?** Yes — `(N·m)⁻¹` — but not a unit in which it can
   be compared to a dimensionless threshold.
2. **Is it a parameter standard deviation?** No. It is `std(h)/σ_v`; a standard deviation only after
   multiplication by a physical `σ_v`.
3. **Does the implementation implicitly assume unit-variance noise?** Yes, exactly: `σ_v = 1` in torque
   units. Confirmed both algebraically (§4.2) and numerically (§4.2/§6.2).
4. **Is `SIGMA_H_MAX = 0.1` dimensionally and statistically meaningful?** Dimensionally inconsistent with
   `(N·m)⁻¹`; statistically it fixes `std(h) ≤ 0.1 σ_v` with `σ_v = 1 N·m`, i.e. `std(h) ≤ 0.1` under an
   assumption 3896× larger than the observed residual. Its numeric value is not defensible as written.
5. **Can the existing values be read as physical parameter uncertainty?** No. They can be read as a
   *relative excitation measure* (`1/sqrt(Σ(τ−τ̄)²)`), which is meaningful — but it is a property of the
   operating point, not of the estimate's trustworthiness.

---

## 5. Measurement-noise propagation

### 5.1 Where the measurement comes from `[V]`

`y_k = J_w (ω_k − ω_{k−1})/Tc`, with `ω` the **plant state**. In the current simulator the wheel speed is
exact: `[V]` `sensors.py` has no wheel-speed channel; `[V]` `dynamics.py:57–60` leaves deadzone, viscous
and rate-limit at `0.0`; `[V]` the speed clip (`:238`) was not reached (max ≈ 461 rad/s vs 628).

Hence, in the current plant, `y_k` is **noise-free** and the only departure from the model is
unmodelled friction.

### 5.2 What the data's own residual says `[O]`

Regressing the recorded S2 trace on `−ĥ·τ` only (friction excluded deliberately):

| wheel | residual RMS vs `−ĥτ` | friction magnitude |
|---|---|---|
| 1 | 2.534e−4 | 2e−4 |
| 2 | 2.589e−4 | 2e−4 |
| 3 | 2.579e−4 | 2e−4 |

The residual is the friction term itself — i.e. **the data is consistent with zero measurement noise and
a deterministic model error**. That is the correct interpretation, and it is why the "noise" a defensible
interval needs must come from a *stated model-error budget* here.

### 5.3 What a real tachometer would do `[D]`

With wheel-speed noise std `σ_ω` and a first-order difference,

```
Var(Δω) = 2 σ_ω²           (difference of a white sequence)
σ_v = J_w · sqrt(2) σ_ω / Tc = 2.0e-4 · 1.414 · σ_ω / 0.2 = 1.414e-3 · σ_ω   [N·m]
```

| `σ_ω` | `σ_v` | `σ_v` / (friction to detect, 2e−4) |
|---|---|---|
| 0.50 rad/s (quantisation of a 12-bit encoder on a 628 rad/s wheel) | 7.071e−4 | **3.54 ×** |
| 0.20 rad/s | 2.828e−4 | 1.41 × |
| 0.05 rad/s | 7.071e−5 | 0.35 × |

`[D]` Two consequences. (i) With a realistic quantisation step the additive friction term is **below the
noise floor** — `τ_f` would not be identifiable at 2e−4, independently of any covariance question.
(ii) Adjacent `y` share the sample `ω_k`, giving an MA(1) structure with correlation `−0.5`; RLS assumes
white noise, so the effective noise variance for a run of `N` samples is inflated by roughly
`(1 + 2ρ) = 0`, i.e. the *paired* structure changes the information content, and a naive white-noise
covariance is wrong in either direction.

### 5.4 What is *not* modelled (stated, not invented) `[V]`

No tachometer noise, no quantisation, no sampling jitter, no filtering, no latency. `simulate.py` gained
a `wheel_sensor` hook in `c9a4aa5` (0.5 rad/s quantisation + 0.2 rad/s white, opt-in via `--tachometer
noisy`) but **it has never been executed**; no noisy-tachometer result exists in the repository. This
audit does not attribute any noise model to the implementation.

### 5.5 Distinguishing noise from model error `[D]`

| source | present now | estimated magnitude | affects |
|---|---|---|---|
| sensor noise | **no** | 0 | would widen `Cov(θ̂)` |
| quantisation | **no** | 0 | same |
| `tanh` friction model error (|ω| < 0.05) | yes | inside the 2.5e−4 residual | biases `τ_f`, contaminates `h` |
| `τ_f` variation within `Tc` | yes | second order | small bias |
| unmodelled viscous term (if enabled) | no | 0 today | would alias into `h` (§3.5) |
| allocator clipping | yes (clipped command is used) | none on the estimate | — |

---

## 6. Covariance interpretation

### 6.1 What the stored matrix is `[D]`

For the recursion in §3.3, `P_k = (P_0⁻¹ + Σ_{j≤k} φ_j φ_j')⁻¹`. It is:

- **an inverse information matrix** (information accumulated in the regressor directions), and
- **a covariance only up to the factor `σ_v²`**, which the implementation omits, and
- **not** a "scaled covariance" in any normalised sense: there is no reference torque anywhere in
  `friction_estimation.py`.

### 6.2 Numerical confirmation `[O]`

Recorded `sigma_h` (final, per wheel) vs `sqrt([(P₀⁻¹+Φ'Φ)⁻¹]₀₀)` rebuilt from the recorded commands:

| trace | wheel | `Φ'Φ` entries `(Στ², Στ, N)` | predicted | recorded |
|---|---|---|---|---|
| S2 coulomb 2e−4, w1 | 1 | (6.652e−3, −0.838, 4500) | 11.5499 | **11.5505** |
| S2, w2 | 2 | (6.071e−3, −0.957, 4500) | 12.0673 | **12.0674** |
| S2, w3 | 3 | (2.804e−3, −0.822, 4500) | 16.5432 | **16.5432** |

The stored quantity is exactly the inverse information matrix, with no noise scaling.

### 6.3 The five regimes, and which assumptions each needs `[D]`

| regime | formulation | needs | what it would give here |
|---|---|---|---|
| **known `σ_v`** | `Cov = σ_v² P` | a physical measurement-noise variance | `std(h) = σ_v·11.55`; with `σ_v = 2.57e−4` → `2.97e−3` |
| **estimated `σ_v`** | `σ̂_v² = EMA(residual²)`; `Cov ≈ σ̂_v² P` | whiteness + enough residual samples | collapses to ~0 in this plant (residual is model error, not noise) → over-confident |
| **weighted / normalised** | regress `y/τ_ref` on `[−τ/τ_ref, 1]` | a defensible `τ_ref` | makes `sigma_h` dimensionless; `0.124–0.194` here (§4.3 with `τ_ref=τ_max`) — **still closed** |
| **forgetting `λ<1`** | `P⁻=P/λ` | bounded parameter drift; λ not too small | restores tracking; but the project measured `λ=0.995 → σ_h ~1e4 after 4500 updates` (comment at `:45–51`), because the regressor direction is nearly constant |
| **correlated / heteroscedastic** | GLS with `R` from the MA(1) structure; or batch covariance | the sensor model | the only statistically correct route, and it needs §5.3 data that does not exist yet |

### 6.4 The duality that matters `[D]`

`P` is not a reporting by-product: it is the gain. With `φ = [−τ, 1]` and small `τ`, both the per-step
innovation (`≈ (ĥ−h)·τ`) and the per-step information (`∝ τ²`) vanish together, so the movement of `ĥ`
scales with `Στ²`. The same failure that makes `sigma_h` huge makes adaptation slow. Measured §7.4.

---

## 7. Regressor conditioning and identifiability

### 7.1 The condition number is a **scale** artifact, not collinearity `[D]`+`[O]`

With `Στ ≈ 0`: eigenvalues of `Φ'Φ` are `≈ N` and `≈ Στ²`, so

```
cond(Φ'Φ) ≈ N / Στ²
```

`[O]` Measured: `6.0e5`, `6.6e5`, `1.2e6` (S2 wheels 1–3) — matching `4500/6.65e-3 = 6.8e5`.

But the **parameter correlation is small**: `[O]` `corr(h, τ_f) = +0.143, +0.170, +0.199` (S2) and
`−0.010` (S7). The columns are nearly orthogonal; the large condition number reflects that one column is
`O(1e-3)` and the other is `O(1)`. **Diagnosis "the regressor is collinear" is refuted**; the defect is
one of units, exactly as §4 established. This matters because a naive fix — e.g. adding regularisation to
"cure conditioning" — would treat the wrong problem.

### 7.2 Identifiability is governed by centred excitation, and it collapses after acquisition `[O]`

| window (S2, wheel 1) | `τ_rms` | `Σ(τ−τ̄)²` | 1-param LS `h₁` | 2-param LS `h₂`, `τ_f` | residual |
|---|---|---|---|---|---|
| whole episode | 1.22e−3 | 6.50e−3 | 0.9646 | 0.9878, −1.84e−4 | 1.72e−4 |
| slew, t ≤ 300 s | 2.09e−3 | — | 0.9806 | 0.9877, −1.56e−4 | 2.96e−4 |
| settled, t > 300 s | **1.80e−4** | ~1e−5 | **−0.1117** | 0.5548, −1.20e−4 | 1.12e−5 |

In the settled phase the command is ~11× smaller and comparable to the friction itself; the one-parameter
fit returns a **negative** effectiveness and the two-parameter fit is meaningless. The estimator's useful
information comes almost entirely from the **slew transient**.

### 7.3 A dead wheel `[O]`+`[V]`

`[O]` A dead wheel is identified accurately when it is *commanded*: `S6` gives `h_hat = 0.0030` (median
over 24 seeds, truth 0.0), and `[V]` the `unity` arm commands `0.86·tau_max` mean. Under the **oracle**
allocator the dead wheel is commanded exactly zero, so no information exists — consistent with the
previously documented G13 limitation, and it is a property of the allocator, not the estimator.

### 7.4 The two failures that point accuracy hides `[O]`

Both are visible because the fault trace is recorded:

| case | batch LS on the same data | online RLS | comment |
|---|---|---|---|
| **from t=0**, h=0.5 (S3, 24 seeds) | — | `min 0.533, med 0.602, max 0.808` | estimator **stalls** above truth; never reaches 0.5 |
| **mid-flight** to 0.5 at t=300 (S7) | `h₁ = 0.4807`, `h₂ = 0.4059` | `h = 0.9997` | information is present; the recursion does not track it |

`[D]` Mechanism: after the fault the command RMS drops `2.11e−3 → 4.50e−5` (26×), so `Στ²` falls ~1000×;
the per-step innovation `≈ (ĥ−h)τ` and the gain-vector projection both shrink proportionally, and with
`λ = 1.0` the covariance has already contracted, so `ĥ` cannot move in the remaining 3000 steps. `[O]`
Note this is **not** the `tau_min` guard: 93.8 % of post-fault samples exceed `1e−5`. Lowering `tau_min`
would change nothing. `[O]` The `λ=1` choice is documented in the source (`:45–51`) as deliberate, to keep
`P` usable as a confidence measure — so the confidence design and the tracking design are in direct
conflict, and both are currently unsatisfied.

### 7.5 Point accuracy ≠ identifiability `[O]` (24 seeds, fault wheel)

| scenario | truth | min | median | max | bias | MAE | RMSE |
|---|---|---|---|---|---|---|---|
| S3 rw1@50 % | 0.50 | 0.533 | 0.602 | 0.808 | **+0.1057** | 0.1057 | 0.1245 |
| S5 rw2@50 % | 0.50 | 0.539 | 0.584 | 0.866 | **+0.0908** | 0.0908 | 0.1121 |
| S6 rw1 dead | 0.00 | 0.003 | 0.003 | 0.038 | +0.0046 | 0.0046 | 0.0084 |
| S2 healthy + friction | 1.00 | 0.945 | 0.996 | 1.000 | −0.0150 | 0.0150 | 0.0243 |
| S1 healthy + half friction | 1.00 | 0.985 | 0.999 | 1.000 | −0.0040 | 0.0040 | 0.0065 |
| S0 nominal | 1.00 | 1.000 | 1.000 | 1.000 | 0.0000 | 0.0000 | 0.0000 |

The estimator is accurate where it is easy (h = 1, h = 0) and biased by ~20 % relative where the thesis
needs it (h = 0.5). The near-perfect `h = 1` and `h = 0` results are **not** evidence of good
identifiability: they are endpoint cases in which the regressor is dominated by one column.

### 7.6 Can effectiveness be distinguished from unmodelled friction? `[Q]`

`[D]` Not in general: any additive term that is constant over the estimation window is, by construction,
absorbed by the `τ_f` column. The two are separable only to the extent that the residual signature differs
(proportional-to-command vs constant). `[O]` In the settled phase both are `O(1e−4)` and the design matrix
is nearly rank-deficient in that direction, so they are **not** separable there. `[Q]` A quantitative
answer (bias of `ĥ` induced by a mis-specified `τ_f`) needs a surgical experiment that varies `τ_f` at
constant `h` — proposed in §10, not executed.

---

## 8. Health-state classification audit

### 8.1 The implemented rules `[V]`

```
state_i = UNKNOWN   if n_upd_i < N_MIN (=5)                      :94–95
        = UNKNOWN   if sigma_h_i > SIGMA_H_MAX (=0.1)            :96–97
        = DEGRADED  if h_hat_i < 1 − H_TOL (=0.95)               :98–99
        = HEALTHY   otherwise                                    :101
consumer (allocation_policy.py:53–70):
        UNKNOWN  -> h_used = 1.0          (no compensation)
        HEALTHY  -> h_used = 1.0
        DEGRADED -> h_used = max(h_hat, H_FLOOR=0.5)
```

### 8.2 Are the rules statistically justified? `[D]`

| constant | intended meaning | actual meaning | verdict |
|---|---|---|---|
| `SIGMA_H_MAX = 0.1` | "effectiveness known to ±0.1" (source comment `:37–39`) | "`std(h) ≤ 0.1 σ_v` with `σ_v = 1 N·m`", and dimensionally `(N·m)⁻¹` | **not** the intended test; unit-dependent (§4.3) |
| `H_TOL = 0.05` | 10× below the smallest fault of interest | comparison of a dimensionless estimate against a dimensionless tolerance | dimensionally **correct**, but applied only after an excitation test that never passes |
| `N_MIN = 5` | "redundancy beyond 2 parameters" | a sample-count guard; no information content | harmless, but not a confidence statement |
| `tau_min = 1e-5` | guard against zero-command updates | fires rarely (93.8 % of post-fault samples pass) | not the limiting factor (§7.4) |

`[D]` So the classification conflates **four distinct quantities**: (i) parameter estimate, (ii) parameter
uncertainty, (iii) excitation/identifiability, (iv) detection decision. The single scalar `sigma_h`
currently stands in for (ii) and (iii) at once, in the wrong units, which is why the gate can neither open
nor be trusted when it does.

### 8.3 A good point estimate does not imply a trustworthy interval `[D]`+`[O]`

`[O]` The correlation between the point error and the reported `sigma_h` is essentially nil:
`|err|/sigma_h` median is `7.1e−3` (S3), `6.5e−3` (S5), `1.7e−3` (S6), `2.5e−4` (S2). The reported
uncertainty is ~3 orders of magnitude larger than the actual error in every case, and it moves with the
*operating point*, not with the error. A quantity uncorrelated with the error cannot certify the estimate.

### 8.4 Risks, with the measured evidence `[O]`

| failure mode | mechanism | measured consequence |
|---|---|---|
| **excessive UNKNOWN** (current) | gate never opens | 0 DEGRADED wheel-steps in 192 episodes; estimator-driven arm **bit-identical** to the no-information arm in 192/192 cells |
| **false DEGRADED** | `ĥ` biased low by unmodelled additive torque; `tau_des/h` then saturates the wheel | historically the M2 artefact: `h_hat=[0,0,0]` on healthy wheels turned the allocator into a saturation machine and produced a **spurious "win"** (0.366 deg → 0.920 with floor 0.5) |
| **false HEALTHY** | `ĥ` biased high (measured +0.106 at h=0.5; +0.9997 vs 0.5 in flight) | allocation keeps `h_used=1`, the wheel under-delivers, residual never routed to MTQ; no diagnostic fires |

`[O]` The S7 case is a live false-HEALTHY: truth 0.5, `h_hat = 0.9997`, `state = UNKNOWN` (so it does no
harm today only because the gate is closed). If the gate were opened by any rescaling without fixing
tracking, this episode would be classified HEALTHY and the fault would go uncompensated.

---

## 9. Candidate mathematical formulations

For each: what it **does** and does **not** estimate, requirements, and behaviour on the recorded data.
None is implemented; no threshold is proposed.

| | formulation | estimates | does **not** estimate | required assumption | measured behaviour (§4.3/§6.3) | principal failure mode |
|---|---|---|---|---|---|---|
| **A** | `Cov = σ̂_v² P` (noise-variance-scaled) | parameter covariance **given** a noise variance | the noise variance, or model error | `σ_v` known from the sensing model | with `σ_v = 7.07e−4` → `8.2e−3 … 1.2e−2` → gate opens | over-confident when model error dominates (here `σ_v→0` ⇒ `Cov→0`) |
| **B** | online innovation variance `σ̂_v² = EMA(e²)` (optionally with a window) | a data-driven noise+model-error scale | any guarantee that residual is white; any bound on **bias** | innovations capture the dominant error | in this plant `σ̂_v ≈ 2.5e−4` (model error) → gate would open; in a noise-free model it would collapse | self-confirming: a stalling estimator has small innovations and therefore looks confident |
| **C** | weighted / normalised regression (`y/τ_ref`, `φ/τ_ref`) | a **dimensionless** `sigma_h` | the noise scale; `τ_ref` is a free choice unless tied to hardware | a defensible `τ_ref` (e.g. `tau_max`) | `0.124 … 0.194` → **still closed** | hides the noise problem; shifting `τ_ref` moves the answer |
| **D** | parameter scaling before RLS (e.g. `θ' = [h, τ_f/τ_ref]`) | identical estimate, better conditioned numerics | **nothing statistically** — a similarity transform | none (it is exact) | same `sigma_h` in original units | cosmetic if presented as an uncertainty fix |
| **E** | batch / sliding-window LS covariance `σ̂_v²(Φ'Φ)⁻¹` with `t`-quantiles | covariance with honest **finite-sample** coverage | tracking (a window is a design choice, not a model) | independent, identically distributed residuals | recovers `h₁ = 0.48` where RLS reports 1.00 (§7.4) | window length trades variance against responsiveness |
| **F** | different estimator: e.g. joint `(h, τ_f, b_v)` with GLS + explicit model-error term, or a Kalman filter with augmented state and a measured `σ_ω` | parameters **and** a defensible posterior | anything about unmodelled physics outside the state | a stated sensing model and a model-error budget | not evaluable without a sensing model | complexity vs. benefit at a 5 Hz, 3-wheel problem |

`[D]` **Explicit warning, as required:** innovation variance is **not** parameter uncertainty. A
stalled estimator produces small innovations precisely *because* it has stopped moving; `EMA(e²)` then
reports a small number while `ĥ` is 20 % wrong (measured: §7.4, `ĥ = 0.9997` vs truth 0.5 with
`resid = 6.2e−6`). Any formulation whose confidence derives only from residuals can therefore certify a
failed estimate.

`[R]` On this evidence the defensible ordering is **E as an independent reference → A with a *stated*
`σ_v` (sensing model) → B only as a diagnostic of model error, never as the confidence itself**. C and D
are implementation hygiene (they make units explicit), not confidence models. F should be considered only
if §10 shows that the additive-vs-multiplicative separation cannot be achieved with the current
regression.

---

## 10. Independent validation protocol (proposed, **not executed**)

### 10.1 Design

- **Unit of analysis:** estimator-only harness, no closed loop, no controller. Replay *recorded* command
  and speed traces, or generate synthetic wheel traces from the plant equation with a specified input
  profile. This is the cheapest level and it must be passed first.
- **Three disjoint datasets** (never reused):
  1. **Calibration** — used only to fix any estimator constants;
  2. **Validation** — used to choose between candidate formulations;
  3. **Held-out** — evaluated once, at the end, on conditions never seen in 1 or 2.
- **Conditions (minimum):** healthy; healthy + Coulomb friction; h = 0.5; h = 0.5 + friction; dead;
  dead + friction; **two excitation magnitudes** (slew-like `τ_rms ≈ 2e−3` and settled `τ_rms ≈ 2e−4`);
  **three operating speeds** (near zero, mid, near `max_speed`); three tachometer treatments
  (ideal / 0.5 rad/s quantisation / 0.5 rad/s + white); an **insufficient-excitation** case designed to
  remain UNKNOWN; and one **model-mismatch** case (e.g. `c_coul` differing from the estimator's model).
- **Seeds:** independent traces per condition, sized by the metric that decides the outcome (not by
  convention); fix the count in advance.

### 10.2 Metrics

| metric | definition | decision use |
|---|---|---|
| `h` bias / MAE / RMSE | vs the known truth, per condition and per excitation magnitude | primary accuracy |
| `τ_f` bias / MAE / RMSE | sign-aware truth: `−c·tanh(ω_i/0.05)`, per wheel | separation check |
| **interval coverage** | fraction of runs whose nominal 95 % interval contains the truth | **the confidence test** |
| coverage CI | Wilson interval on the coverage estimate itself | prevents "coverage = 1.0 at n = 5" |
| false HEALTHY rate | truth degraded, reported HEALTHY | safety |
| false DEGRADED rate | truth healthy, reported DEGRADED | the M2 artefact |
| UNKNOWN rate | per condition | usability |
| detection delay | time from fault onset to first DEGRADED | the in-flight case |
| noise/excitation sensitivity | coverage and RMSE vs `σ_ω`, vs `Στ²` | robustness |

### 10.3 How 95 % coverage must be judged `[D]`

A nominal 95 % interval is **validated by coverage**, not by construction: over `M` independent runs the
interval must contain the truth in `0.95 M` of them within sampling error. With `M = 100` a Wilson 95 %
interval on `0.95` is roughly `[0.887, 0.979]`; an observed coverage of 0.60 or 1.00 is therefore an
unambiguous failure in either direction (anti-conservative or uselessly wide), and a "coverage" computed
on the same data that calibrated the interval is not evidence at all. Coverage must be reported **per
condition**, since it will not be uniform across excitation magnitudes — and a formulation that achieves
95 % only by making intervals enormous must be reported with its width, otherwise it "passes" by being
uninformative.

### 10.4 What this protocol cannot settle `[Q]`

It cannot establish that the additive/multiplicative separation holds under fault **combinations** not
enumerated above, and it cannot substitute for a stated sensing model: if the sensor specification is
assumed rather than measured, coverage is conditional on that assumption.

---

## 11. Risks and unresolved questions

| # | risk / question | severity | resolution path |
|---|---|---|---|
| R1 | any rescaling of `sigma_h` opens the gate without fixing tracking → false HEALTHY (already visible: `ĥ = 0.9997` on a 0.5 wheel) | **high** — safety-relevant | must be closed by §10's detection-delay metric, not by a threshold change |
| R2 | model-error variance is unestimated; a noiseless plant makes any honest covariance ~0 | **high** | add a sensing model, then budget model error explicitly |
| R3 | `λ = 1` means no tracking; `λ < 1` destroys `P` as a confidence measure (measured `σ_h ~ 1e4`) | **high** — the two requirements conflict | separate estimator (with forgetting) from uncertainty (batch/window) — candidate E |
| R4 | viscous friction, if enabled, aliases into `h` (§3.5) | medium | add `−ω` as a third regressor or forbid enabling `b_v` |
| R5 | `h` bias at 0.5 (+0.106) is unexplained by noise; cause not isolated | **high** for the thesis claim | §10 with an excitation sweep at constant `h` |
| R6 | friction accuracy across seeds is **not computable** from current artifacts (truth is sign-dependent and only two traces were saved) | medium | record per-step `τ_f_true` in future artifacts |
| R7 | dead config key `initial_speed_rad_s`; `prime()` before `reset()` | low | fold into the next code-touching step |
| R8 | `τ_f` separability under combined faults is assumed, not measured (§7.6) | medium | §10 combination conditions |
| Q1 | Would a correctly scaled covariance open the gate on *healthy* wheels too? | — | yes for A with `σ_v = 7.07e−4` (measured); whether that is a false alarm depends on `H_TOL`, which is a policy question |
| Q2 | Is `SIGMA_H_MAX` intended as a relative or absolute quantity? | — | the source comment says "effectiveness known to ±0.1", i.e. **absolute**, which is inconsistent with the implementation's units |

---

## 12. Recommended next steps (none implemented)

1. **Freeze the present finding.** No threshold or scaling change. The M3.3-B result (estimator-driven
   arm inert, 192/192 bit-identical) stands as the honest baseline.
2. **Write the sensing model down** — a wheel-speed channel with noise, quantisation and sample timing,
   and a stated model-error budget. Without it, no covariance can be validated (R2).
3. **Build the estimator-only harness of §10**, at the synthetic level first, then on recorded traces.
4. **Evaluate candidates E → A → B** in that order, on the §10.2 metrics, with coverage as the deciding
   metric.
5. **Only then** propose a bounded implementation: one formulation, one threshold derivation, one test
   suite, re-scored against the same 8 scenarios and the same pre-registered criteria.
6. Housekeeping (R7) folded into whichever step next touches code.

---

## 13. GO / NO-GO recommendation

### **CONDITIONAL GO**

The current mathematical model is **fully understood** — that part of the question is closed, and closed
by derivation confirmed numerically:

- the stored matrix is the inverse information matrix, verified to four decimals against recorded traces;
- the implicit noise assumption is `σ_v = 1 N·m`, i.e. 100 × `tau_max` and 3896 × the observed residual;
- `sigma_h` is `std(h)/σ_v`, with units (N·m)⁻¹, and the gate's verdict can be flipped by changing only
  the unit torque is written in (`11.55` in N·m vs `0.0124` in mN·m — same physics);
- the same mis-scaling is an adaptation defect, measured twice: `h` stalls at 0.602 (truth 0.50) from a
  t=0 fault, and does not track a mid-flight step (`0.9997` vs 0.5) although batch LS on the identical
  recorded data returns `0.4807`.

But a confidence-model change is **not yet justified or validatable**, because:

1. the measurement-noise variance that any covariance requires has **no physical source** — there is no
   wheel-speed sensor in the model, and the wheel equation is otherwise exact;
2. a noiseless plant drives any honest covariance toward zero, i.e. toward infinite confidence, which is
   the opposite error of the present one;
3. the point estimates themselves are not dependable where the thesis needs them (`h = 0.5`: bias
   `+0.106`, worst error `0.308`, and it never reaches the truth), so a better interval around a biased
   estimate would certify the wrong number;
4. the four quantities the classifier conflates (estimate, uncertainty, excitation, decision) cannot be
   separated by rescaling a single scalar.

**Exact evidence supporting the decision:** §4.2–§4.4 (derivation + numerical confirmation + the
unit-invariance test), §6.2 (recorded vs predicted `sigma_h`), §7.2 and §7.4 (excitation collapse; batch
LS vs RLS on identical data), §7.5 (24-seed bias/MAE), §8.4 (the three classification risks, one of them
already realised historically as the M2 artefact), and §2.4/§5.1 (no tachometer; exact wheel equation).

**What would move this to GO:** a defined wheel-speed sensing model and a model-error budget (step 2),
plus the §10 estimator-only harness at the synthetic level (step 3). **What would move it to NO-GO:** if
the §10 excitation sweep shows the additive/multiplicative separation fails even with a good sensor, in
which case the regression structure itself, not its covariance, is the defect (candidate F).

---

## Statement of permissions compliance

- No source file, configuration value, threshold, parameter, allocator rule or controller behaviour was
  modified.
- No training run and no new closed-loop experiment was executed. All numerical values above are either
  derived analytically or computed from **existing** recorded artifacts (`results/m33b/**`); the offline
  least-squares comparisons of §7.2/§7.4 are recomputations on those recorded traces, not new episodes.
- No existing result, report or retraction was regenerated, overwritten or deleted.
- No commit, push, checkout, reset, rebase or branch change was performed.
- The only new file in the repository is this report,
  `docs/research/M34_RLS_uncertainty_audit.md`.

---

## Addendum A1 — the estimator ceiling (added 2026-11-06, Phase A)

The audit above analyses the estimator *in isolation*. Its **worth to the thesis** is bounded by an
experiment already in the repository: the `oracle` arm of the M3.3-B grid allocates from **ground-truth**
wheel health, i.e. it is the best any estimator could ever be, and it is paired on identical ICs with the
`unity` arm (allocator told every wheel is healthy, no fault knowledge). Source:
`codes/results/m33b/run.json`, n = 24 per cell, 900 s, both holds scored.

| scenario | oracle success@30 | oracle final med [deg] | unity success@30 | unity final med [deg] |
|---|---|---|---|---|
| S0 nominal | 100.0 % | 0.243 | 100.0 % | 0.243 |
| S1 + friction 1e-4 | 95.8 % | 0.760 | 95.8 % | 0.760 |
| S2 + friction 2e-4 | 8.3 % | 1.570 | 8.3 % | 1.570 |
| S3 rw1 @ 50 % | 100.0 % | 0.242 | 95.8 % | 0.285 |
| S4 rw1 @ 50 % + friction | 8.3 % | 1.570 | 0.0 % | 2.425 |
| S5 rw2 @ 50 % | 100.0 % | 0.243 | 100.0 % | 0.304 |
| S6 rw1 dead | 0.0 % | 91.342 | 0.0 % | 90.518 |
| S7 rw1 @ 50 %, mid-flight | 100.0 % | 0.243 | 95.8 % | 0.284 |

**Deltas (perfect knowledge minus none):**

| scenario | Δ final median | Δ success@30 | reading |
|---|---|---|---|
| S0, S1, S2 | **0.000 deg** | 0.0 pp | **identical by construction** — see below |
| S3 rw1 @ 50 % | +0.043 deg | +4.2 pp | the whole value of a perfect estimator |
| S5 rw2 @ 50 % | +0.061 deg | 0.0 pp | same |
| S7 mid-flight @ 50 % | +0.042 deg | +4.2 pp | same |
| S4 50 % + friction | +0.855 deg | +8.3 pp | both arms fail (8.3 % vs 0 %) |
| S6 rw1 dead | **−0.825 deg** | 0.0 pp | perfect knowledge is **worse** |

**Three consequences, which change how much the estimator is worth.**

1. **The ceiling on the entire estimation programme is 0.04–0.06 deg and ≈4 pp**, in the multiplicative
   cases only. No covariance model can exceed the oracle, so no confidence model can be worth more than
   that. The audit's defect is therefore a *correctness and limitations* item, not a results item.

2. **Under pure friction the ceiling is structurally zero, not merely small.** With `h = 1` there is
   nothing for the allocator to invert (`allocation_policy.py:53–70` returns `h_used = 1.0` for both
   HEALTHY and UNKNOWN), so the oracle and unity commands are bit-identical and the final medians match
   to every printed digit. This is a **structural property**, not a measurement. Its significance: the
   classical controller's friction failure (S2: 8.3 % success@30, 1.570 deg) is **information-invariant**
   — it cannot be attributed to unknown fault state, and no estimator, however well calibrated, moves it.

3. **A dead wheel can be made worse by better information.** The oracle routes the full residual to the
   magnetorquers, which have no authority along **B**; commanding the dead wheel to zero and asking the
   MTQs to cover everything loses 0.8 deg against doing nothing. Fault-awareness must therefore be
   *selective*, which is the motivation for the state-aware policy rather than blanket inversion.

**Consequence for prioritisation (Phase A → Phase B).** Because the ceiling is 0.04 deg on multiplicative
faults and exactly zero on additive ones, the confidence-model repair cannot be on the critical path for
the thesis's central claim. The strongest fair classical baseline is therefore **nominal LQR with the
oracle allocator** — strictly harder to beat than any estimator-driven baseline, and available today
without waiting for Phase C. That is the baseline Phase B must be run against.

**Caveat that travels with this addendum.** The oracle/unity contrast isolates *allocation information*
only. It does not bound the value of a **detector** (a binary, calibrated health decision feeding a
supervisor or an RL observation), which is a different question and is the subject of Phase C.
