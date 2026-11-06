# M1-B — D4 statistical reassessment

**Scope:** diagnostic only. Reads `reports/d4_residual_vs_lqr.json`; no results altered.

## 1. Unit of analysis

**Seed is the independent training-level unit.** Episodes from one policy share weights,
seed, and training history and are not independent. Episode-level analysis is reported
**only as secondary, within-policy evidence** and is labelled as such.

## 2. Seed-level results

| condition | LQR | seed 0 | seed 1 | seed 2 | positive | two-sided sign test |
|---|---|---|---|---|---|---|
| ideal | 100.0 % | 25.0 % | 58.3 % | 75.0 % | 0/3 | **p = 0.2500** |
| Coulomb 2e-4 | 0.0 % | 35.3 % | 58.3 % | 66.7 % | 3/3 | **p = 0.2500** |

With n = 3 the minimum attainable two-sided p is **0.25**. The design **cannot** reach
significance regardless of effect size.

## 3. Episode-level secondary (different success definition)

Success defined as final error < 1 deg (this is *not* the same as `success30`):

| condition | seed | RL-only | LQR-only | McNemar exact p |
|---|---|---|---|---|
| ideal | 0 | 0 | 9 | 0.0039 |
| ideal | 1 | 0 | 5 | 0.0625 |
| ideal | 2 | 0 | 3 | 0.2500 |
| Coulomb | 0 | 4 | 0 | 0.1250 |
| Coulomb | 1 | 7 | 0 | 0.0156 |
| Coulomb | 2 | 8 | 0 | 0.0078 |

These are **within-policy** results: they describe the twelve evaluation episodes of one
policy, not the method. They cannot be used to claim a method-level effect.

## 4. Multiple comparisons

Six seed-level comparisons were performed, uncorrected. Holm–Bonferroni at family-wise
0.05 would require the smallest p < 0.0083. At seed level no comparison approaches it.

## 5. Conclusions

1. **The previously reported `p < 0.001` is not supportable.** It treated twelve
   correlated episodes as independent Bernoulli trials.
2. At the correct unit the effect is **large and consistently signed** (3/3 positive
   under Coulomb; 0/3 under ideal) but **statistically underpowered**.
3. The honest statement: *"a large, consistently signed effect was observed in three
   seeds; the design cannot establish it at the method level."*
4. **Five seeds is a starting point, not a guarantee**; the final sample size must be
   justified by a precision or power analysis, and a bootstrap over three clusters is
   not sufficient evidence.
