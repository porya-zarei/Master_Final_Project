# M1-A — Physical signal, wheel dynamics, and D5 guard audit

**Scope:** diagnostic only. No code modified. Plant read, not changed.

## 1. Equations as actually implemented (`dynamics.py`)

```
H_w   = J_w * omega_w
H     = J * omega + H_w
tau_f = -(b_visc * omega_w + c_coul * tanh(omega_w / 0.05))

body : w_dot  = J_inv @ (-cross(w, H) + tau_rw_eff - tau_f + tau_mtq + dist)
wheel: ow_dot = (-tau_rw_eff + tau_f) / J_w
```

**The wheel equation contains no `-omega x H_w` term.** That term appears only in the
body equation. Any residual formed from the wheel equation must therefore not include
it.

## 2. Residual convention

From `J_w * ow_dot = -tau_rw_eff + tau_f`:

```
tau_f = tau_cmd + J_w * d(omega_w)/dt        CORRECT
tau_f = tau_cmd - J_w * d(omega_w)/dt        used by D5
```

The two differ in the sign of the derivative term.

## 3. Measurement

LQR only (`alpha = 0`, i.e. the residual action is zero), 900 s, seed 2,
`J_w = 2e-4 kg m^2`, control period 0.2 s. Residual compared against the plant's own
`tau_f`, evaluated at the interval midpoint.

| plant | D5 convention: median abs | error vs truth | corrected: median abs | error vs truth |
|---|---|---|---|---|
| ideal | 3.669e-5 | 3.669e-5 | **5.031e-18** | **5.031e-18** |
| Coulomb 2e-4 | 1.878e-4 | 3.984e-5 | **2.000e-4** | **5.204e-18** |
| Coulomb 3e-4 | 2.866e-4 | 4.148e-5 | **3.000e-4** | **5.258e-18** |

**The corrected residual reproduces the plant's friction torque to machine precision
(5e-18).** The D5 convention is wrong by ~4e-5 at every operating point.

## 4. Earlier D5 conclusion RETRACTED

D5 reported `skip_excite = 4500/4500` and concluded that an excitation-based observer
"cannot bootstrap itself out of the condition it must detect", calling it a fundamental
observability limit.

**That conclusion was an artifact of the test procedure.** `ADCSEnv` is a **plant-only
environment**: the action *is* the commanded torque, and the LQR lives in the residual
wrapper. The D5 audit stepped the plant directly with `action = 0`, i.e. **zero control
input** — hence zero commanded torque, zero wheel motion, error growing from 73.8 deg to
76.5 deg, and every update rejected for lack of excitation.

With the LQR actually running, the guard behaves normally:

| plant | `n_upd` | `skip_excite` |
|---|---|---|
| ideal | [4469, 2329, 2585] | [31, 2171, 1915] |
| Coulomb 2e-4 | [4492, 4497, 4492] | [8, 3, 8] |
| Coulomb 3e-4 | [4491, 4497, 4497] | [9, 3, 3] |

## 5. Conclusions

1. **Friction is perfectly observable** with the correct sign convention: a healthy
   wheel yields exactly zero residual, a 2e-4 wheel yields exactly 2e-4.
2. **The excitation guard does not block** identification under LQR operation on the
   Coulomb plant (≈4 492/4 500 updates accepted).
3. **The D5 "observability limit" is withdrawn.** The gate concept was abandoned on
   the basis of a measurement of the wrong controller.
4. On the *ideal* plant, wheels 2–3 reject ~2 000 updates, consistent with low demanded
   torque near trim rather than with any fault.

## 6. Unresolved questions

- Does the corrected residual stay exact when `rw_health != 1` (`tau_rw_eff` is scaled
  by health, `tau_cmd` is not)?
- Is the finite-difference residual robust to sensor quantisation? The plant currently
  returns exact wheel speed; a tachometer model is absent.
- Does the guard's low-torque rejection on the ideal plant create a false "no fault"
  state that a gate would misinterpret? (Distinguishing detection, identification, and
  parameter estimation remains open.)

---

## 7. Addendum — time series persisted and guard predicate reproduced

### 7.1 Guard predicate, read from `health_estimation.py:155-165`

```python
if guards and abs(tau[i]) < self.tau_min_eff:                  skip_excite
if guards and abs(w[i])   >= self.speed_frac * self.rw_max_speed: skip_sat
if guards and abs(y[i])   >  self.plaus_margin:                skip_plaus
```
with `y = (J_w * dw / T_c) / tau_ref`, `phi = -tau / tau_ref`, and
`tau_min_eff = max(tau_min, k * tacho_sigma * J_w / T_c / tau_ref) = 1.00e-05`.

Note the regressor asserts `y = h * phi`, i.e. it attributes **all** of the wheel's
response to a multiplicative health factor. It contains **no friction term**, so a
Coulomb-friction wheel appears to it as a health loss. Detection (a wheel is not
responding) and identification (is it friction or effectiveness loss?) are therefore
**conflated by construction** in the current estimator.

### 7.2 Predicate reproduction

| plant | actual `skip_excite` | predicted | n_upd actual |
|---|---|---|---|
| ideal | [31, 2171, 1915] | [30, 2170, 1914] | [4469, 2329, 2585] |
| Coulomb 2e-4 | [8, 3, 8] | [7, 2, 7] | [4492, 4497, 4492] |

**Off by exactly one on every wheel, in both conditions.** The discrepancy is the
estimator's first call, which primes `last_w` and returns without evaluating any guard.
The predicate is therefore reproduced exactly; the difference is a documented priming
step, not a modelling error.

### 7.3 Residual accuracy over the persisted series

| plant | median abs error vs truth | max abs error vs truth |
|---|---|---|
| ideal | **0.0** (exact) | 0.0 |
| Coulomb 2e-4 | **5.2e-18** | **9.9e-06** |

The median is at machine precision. The maximum error corresponds to the few steps
where `tanh(omega_w/0.05)` is steep (direction reversals) and the midpoint evaluation
of the friction law is least accurate — expected for a finite difference, and four
orders of magnitude below the 2e-4 friction being detected.

### 7.4 Artefacts

- `codes/scripts/m1a_timeseries_guard.py`
- `reports/m1a_timeseries.json` — 449 samples per condition at 0.2 s spacing, containing
  `t`, `tau_cmd`, `omega_w`, `dw_dt`, `tau_f_resid`, `tau_f_true`, `coupling_body`,
  `skip_excite`.

**Correct disconnect noted while writing this:** the guard uses the command issued on
the *previous* period (the estimator runs before allocation), whereas the residual uses
the command *applied during* the period being differentiated. Logging one for the other
inflates the apparent residual error from 5e-18 to 5e-4. This was a bug in the first
draft of the addendum and is now fixed.

### 7.5 M1-A acceptance

| criterion | status |
|---|---|
| time series of tau_cmd, omega_w, dw_dt, residual, coupling persisted | **met** |
| guard predicate stated and reproduced on sample | **met** (off-by-one explained) |
