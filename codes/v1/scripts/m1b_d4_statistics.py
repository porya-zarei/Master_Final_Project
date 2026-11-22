"""M1-B: D4 statistical reassessment. Diagnostic only; reads the committed artifact."""
import json, itertools
from math import comb

D = json.load(open("../reports/d4_residual_vs_lqr.json"))
CONDS = ["ideal", "coulomb_2e4"]
SEEDS = ["seed0", "seed1", "seed2"]

def sign_test(n_pos, n):
    """Exact two-sided sign test; with n=3 the minimum p is 0.25."""
    if n == 0: return 1.0
    tot = 2 ** n
    k = max(n_pos, n - n_pos)
    tail = sum(comb(n, i) for i in range(k, n + 1))
    return min(1.0, 2 * tail / tot)

def mcnemar(b, c):
    """Exact McNemar on discordant pairs (b, c)."""
    n = b + c
    if n == 0: return 1.0
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(0, k + 1))
    return min(1.0, 2 * tail / (2 ** n))

out = {"note": "Seed is the independent training-level unit. Episode-level analysis is "
               "secondary, within-policy evidence only.", "conditions": {}}

print("M1-B  D4 statistical reassessment\n")
for cond in CONDS:
    lqr = D[cond]["lqr"]
    lqr_s = lqr["success30"]
    print(f"=== {cond} ===  LQR success30 = {lqr_s:.1f}%")
    rows = []
    n_pos = 0
    for s in SEEDS:
        p = D[cond][s]["success30"]
        better = p > lqr_s
        n_pos += int(better)
        rows.append({"seed": s, "success30": p, "final_median": D[cond][s]["final_median"],
                     "better_than_lqr": better})
        print(f"  {s}: success30={p:5.1f}%  final_med={D[cond][s]['final_median']:.3f} deg"
              f"  {'BETTER' if better else 'not better'}")
    p_sign = sign_test(n_pos, len(SEEDS))
    print(f"  seed-level sign test: {n_pos}/{len(SEEDS)} positive, two-sided p = {p_sign:.4f}"
          f"  (n=3 -> minimum attainable p = 0.25)")

    # secondary: episode-level paired, success := final < 1 deg (DIFFERENT definition)
    lf = lqr["finals"]
    ep = {}
    for s in SEEDS:
        sf = D[cond][s]["finals"]
        b = c = 0
        for a_, b_ in zip(lf, sf):
            la, sa = (a_ < 1.0), (b_ < 1.0)
            if sa and not la: b += 1
            elif la and not sa: c += 1
        ep[s] = {"discordant_rl_only": b, "discordant_lqr_only": c,
                 "mcnemar_p": mcnemar(b, c)}
        print(f"  [secondary] {s}: RL-only {b}, LQR-only {c}, McNemar p = {mcnemar(b,c):.4f}"
              f"   (success := final < 1 deg)")
    out["conditions"][cond] = {"lqr_success30": lqr_s, "seeds": rows,
                               "seed_sign_test_p": p_sign,
                               "episode_level_secondary": ep}
    print()

out["multiple_comparisons"] = {"n_tests": len(CONDS) * len(SEEDS),
                               "note": "6 seed-level comparisons, uncorrected; Holm would "
                                       "require p < 0.0083 for the smallest."}
json.dump(out, open("results/m1/m1b_d4_statistics.json", "w"), indent=2)
print(f"tests performed: {len(CONDS)*len(SEEDS)}, uncorrected")
print("saved results/m1/m1b_d4_statistics.json")
