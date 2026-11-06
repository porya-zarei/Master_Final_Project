# OPEN_QUESTIONS — what is unresolved, and what would resolve it

Severity: **S1** blocks a thesis claim · **S2** degrades one · **S3** housekeeping.
"No new data needed" means resolvable from artifacts already on disk.

| id | question | severity | what would resolve it | phase |
|---|---|---|---|---|
| **Q-01** | Does residual RL beat nominal LQR **+ oracle allocation** under Coulomb friction, at a defensible sample? | **S1** | Phase B grid: 5 training seeds, n=24, both holds, paired McNemar | B |
| **Q-02** | ~~Are the D4 checkpoints validly re-evaluable through the new `residual_fn` path?~~ | — | **RESOLVED 2026-11-06 (B.0, D-13)** — command-level equivalence **0.000e+00 over 40 perturbed states**; hashes match; `K` identical; policies load. Re-evaluable for **h = 1** cells (S0, S2) only; h ≠ 1 cells must be retrained because the residual sits at a different point in the signal path | — |
| **Q-13** | D4's `config.json` does **not** record `reward_shape` or `friction_range` (written before the c7fa879 fix), so the training configuration is recoverable only from the commit record: `--reward_shape log --friction_max 3e-4 --steps 300000 --coulomb 2e-4 --alpha 0.2` | S2 | Any extension must re-declare those flags explicitly and verify them against the new run's own `config.json` | B |
| **Q-03** | Why is `h_hat` biased **high** by +0.106 at h=0.5 (min 0.533, never reaches truth)? Hypothesis: the constant `tau_f` column absorbing part of the multiplicative signal at low excitation | **S1** | Excitation sweep at constant `h` with `tau_f` toggled; the settled-phase measurement (1-param LS returns **−0.11**) already implicates the trade-off | C |
| **Q-04** | Can friction be separated from effectiveness at realistic tachometer noise? At 0.5 rad/s quantisation `sigma_v = 7.07e-4`, **3.5×** the friction to detect | **S1** | Phase C harness under a stated sensing model; may be answered **NO**, in which case the additive parameter is not identifiable and must be dropped or bounded rather than estimated | C |
| **Q-05** | Does a detection-grade estimator remove the G13 oracle asterisk without a performance loss? Ceiling is 0.04–0.06 deg, so the bar is low but the claim matters | **S1** | Phase C: coverage-validated detector, then the same 8 scenarios | C |
| **Q-06** | Which of PPO / SAC is scientifically justified? | **S2** | Phase D.1 single-factor, 5 seeds, task metrics only | D |
| **Q-07** | Does a one-step performance filter help or merely veto useful residual actions? | **S2** | Phase D.2: intervention rate + paired performance with/without | D |
| **Q-08** | Is the residual's nominal cost avoidable (gate on the *detected* fault rather than on error magnitude)? The error-magnitude gate is already falsified (identical residual authority at 0.5–1 deg with and without friction) | **S2** | Phase C/D once a detector exists; a gate whose trigger is the regulated quantity cannot work | C→D |
| **Q-09** | Do the results hold on **unseen fault families** (locked wheel, ramped, intermittent, sensor)? | **S1** for "generalises", S2 otherwise | Phase D.3–D.4; held-out families reported separately | D |
| **Q-10** | Is `SIGMA_H_MAX = 0.1` intended as absolute or relative? Source comment says "±0.1"; implementation is `std(h)/sigma_v` with implicit `sigma_v = 1 N·m` | S2 | **Researcher answer** — no data can settle intent. Recorded in the M3.4 audit §8.2 | A (now) |
| **Q-11** | Does enabling viscous friction silently alias into `h`? The regressor has no `omega` column | S2 | Add `−omega` as a third regressor, or forbid enabling `b_visc`. **Resolvable analytically** — already true by construction | D |
| **Q-12** | ~~Dead configuration key `initial_speed_rad_s` (read by nothing) and `cons.prime()` called before `dyn.reset()`~~ | — | **RESOLVED 2026-11-06** — key honoured by `SpacecraftDynamics.reset()`; priming moved after reset; both covered by `tests/test_config_honoured.py`; default path bit-identical (0.000e+00) | — |

## Answered this session (kept for the record)

| question | answer |
|---|---|
| Does the estimator's confidence gate ever open? | **No** — 0 DEGRADED wheel-steps in 192 episodes; `sigma_h` 1.66–28.2 vs a 0.1 threshold |
| Is `sigma_h` a standard deviation? | **No** — it is `std(h)/sigma_v` with implicit `sigma_v = 1 N·m`; units (N·m)⁻¹ |
| Does better fault knowledge help under pure friction? | **No, structurally** — with `h = 1` there is nothing to invert; oracle ≡ unity bit-identically |
| How much is perfect fault knowledge worth? | **0.04–0.06 deg, ≈4 pp** on multiplicative faults; **0** on additive; **negative** for a dead wheel |
| Was D4's `p < 0.001` legitimate? | **No** — wrong unit of analysis (episodes, not seeds) |
