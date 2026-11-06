# M1-C — Classical LQR versus residual-wrapper parity

**Scope:** diagnostic only. Both arms run; no configuration changed.

## 1. Pre-declared tolerance

Declared **before** the comparison: median difference <= 0.05 deg, and per-episode
difference <= 0.02 deg.

## 2. Method

- **Classical path:** `run_episode(..., controller="lqr")`, which uses `ADCSController`
  (a phase manager: B-dot detumble then LQR).
- **Wrapper path:** `ResidualADCSEnv(ADCSEnv(...))` with `action = 0`, i.e. LQR only.
- Identical seeds, identical initial conditions and gyro-bias draws, same plant,
  same allocator.

## 3. Results

| condition | classical median | wrapper median | median diff | max per-episode diff | verdict |
|---|---|---|---|---|---|
| ideal | 0.1341 deg | 0.1021 deg | 0.0319 | 0.1007 | **FAIL** |
| Coulomb 2e-4 | 1.6898 deg | 1.6229 deg | 0.0669 | 0.0971 | **FAIL** |

Per-episode differences (wrapper minus classical):
ideal: `[-0.0043, -0.1007, -0.0154, -0.0032, -0.0492, -0.0215]`
Coulomb: `[-0.0916, -0.0971, -0.0187, 0.0093, -0.051, 0.0194]`

## 4. Diagnosis

**The two are not the same controller.** `ADCSController` is a phase manager that runs a
**B-dot detumble** before handing over to the LQR. `ResidualADCSEnv` applies the LQR
**from step 0** and contains no detumble phase. The two therefore follow different
trajectories during the high-rate initial phase, which is sufficient to explain a
0.03–0.10 deg difference in final error.

This is a genuine discrepancy, not noise: it is systematic in sign at every seed except
two, and the magnitude is far above the declared tolerance.

## 5. Consequences

1. **D4's "LQR baseline" was LQR-only, without the detumble phase** — not the full
   classical controller used elsewhere in the thesis.
2. The wrapper is therefore **not a valid independent baseline**, which is precisely the
   condition Section 9 of the roadmap forbids.
3. The direction of the bias is not obvious: the RL arm also lacked detumble, so the
   comparison may be fair *to both*, but it is not a comparison against the thesis's
   classical controller. This must be resolved before any advantage claim.

## 6. Unresolved questions

- Can the wrapper be made to host the full `ADCSController` (detumble + LQR) so that
  `a = 0` reproduces the classical path exactly?
- If the residual policy is added on top of the *phase-managed* controller, does the D4
  effect survive?
- Is the detumble phase relevant at all under the 1 deg evaluation criterion, or does it
  only shift the transient?
