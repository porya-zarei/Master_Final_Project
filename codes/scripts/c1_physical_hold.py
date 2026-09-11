"""C1 addendum - the time-base bug ALSO weakened the settling HOLD by 20%.

``simulate.settling_time`` infers the sample period from the time axis it is handed:

    dt = t[1] - t[0];  steps = max(1, round(hold / dt))

On the pre-fix (stretched) axis ``dt = 0.25 s``, so a nominal ``hold = 30 s`` becomes
``round(30/0.25) = 120`` samples.  But 120 samples at the TRUE 0.2 s control period is
only **24 s of physics**.  The archived success rates therefore applied a hold
requirement 20% weaker than the one advertised in the report.

Consequence: at a nominal 30 s hold the old runs were not comparable with corrected
runs, because "30 s" meant 24 s before the fix and 30 s after it.  This script
recomputes every settlement on the TRUE physical axis (``period = nctrl*dt = 0.2 s``)
for both variants, and prints the like-for-like comparison.

Reads : ``results/c1_regeneration/pe_series.npz``
Writes: ``results/c1_regeneration/physical_hold.json``

Usage (from ``codes/``):  python scripts/c1_physical_hold.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

import simulate  # noqa: E402

RES = os.path.join(os.path.dirname(_HERE), "results", "c1_regeneration")
HOLDS = (10.0, 30.0)
CASES = ["healthy", "healthy_30ic", "rw1_50pct", "rw1_failed"]
LABEL_PERIOD = {"legacy": 0.25, "fixed": 0.2}   # legacy axis was stretched by 1.25x
PHYS_PERIOD = 0.2                               # nctrl*dt in BOTH variants


def _settle(pe, period, hold):
    """Settling time on an axis with the given sample period; None if never settled."""
    t = np.arange(1, len(pe) + 1) * period
    st = simulate.settling_time(t, pe, threshold=1.0, hold=hold)
    return None if not np.isfinite(st) else round(float(st), 2)


def _block(series, period, hold):
    st = [_settle(pe, period, hold) for pe in series]
    ok = [s for s in st if s is not None]
    n = len(st)
    d = {"n": n, "success_n": len(ok),
         "success_pct": round(100.0 * len(ok) / n, 2) if n else None,
         "hold_window_physics_s": round(max(1, int(round(hold / period))) * PHYS_PERIOD, 2)}
    if ok:
        a = np.array(ok, float)
        d.update({"settle_mean_s": round(float(a.mean()), 2),
                  "settle_median_s": round(float(np.median(a)), 2),
                  "settle_p90_s": round(float(np.percentile(a, 90)), 2),
                  "settle_p95_s": round(float(np.percentile(a, 95)), 2)})
    else:
        d.update({k: None for k in ("settle_mean_s", "settle_median_s",
                                    "settle_p90_s", "settle_p95_s")})
    return d


def main():
    z = np.load(os.path.join(RES, "pe_series.npz"))
    keys = list(z.keys())
    report = {
        "note": ("settling_time infers dt from the time axis, so the pre-fix (1.25x "
                 "stretched) axis silently shrank the physical hold window by 20%."),
        "control_period_true_s": PHYS_PERIOD,
        "hold_window_physics_s": {
            "legacy_axis_nominal_s": {str(int(h)): round(max(1, int(round(h / LABEL_PERIOD["legacy"]))) * PHYS_PERIOD, 2) for h in HOLDS},
            "fixed_axis_nominal_s": {str(int(h)): round(max(1, int(round(h / PHYS_PERIOD))) * PHYS_PERIOD, 2) for h in HOLDS},
        },
        "cases": {},
    }

    for case in CASES:
        blk = {}
        for variant in ("legacy", "fixed"):
            series = [z[k] for k in keys if k.startswith(f"{case}|{variant}|")]
            if not series:
                continue
            blk[variant] = {
                "archived_semantics_label_axis": {f"hold{int(h)}": _block(series, LABEL_PERIOD[variant], h) for h in HOLDS},
                "true_physics_axis": {f"hold{int(h)}": _block(series, PHYS_PERIOD, h) for h in HOLDS},
            }
        if "legacy" in blk and "fixed" in blk:
            leg = [z[k] for k in keys if k.startswith(f"{case}|legacy|")]
            fix = [z[k] for k in keys if k.startswith(f"{case}|fixed|")]
            l2f = {}
            for h in HOLDS:
                a = [_settle(pe, PHYS_PERIOD, h) for pe in fix]     # identical to its label axis
                b = [_settle(pe, PHYS_PERIOD, h) for pe in leg]
                ratios = [x / y for x, y in zip(a, b) if x is not None and y is not None]
                l2f[f"hold{int(h)}"] = {
                    "success_fixed_n": sum(1 for x in a if x is not None),
                    "success_legacy_n": sum(1 for x in b if x is not None),
                    "settled_in_fixed_only": sum(1 for x, y in zip(a, b) if x is not None and y is None),
                    "settled_in_legacy_only": sum(1 for x, y in zip(a, b) if x is None and y is not None),
                    "n_both": len(ratios),
                    "ratio_median": round(float(np.median(ratios)), 4) if ratios else None,
                }
            blk["like_for_like_physical_axis"] = l2f
        report["cases"][case] = blk

    out = os.path.join(RES, "physical_hold.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("hold window actually enforced (physics seconds):")
    for axis, d in report["hold_window_physics_s"].items():
        print(f"  {axis}: {d}")
    print()
    for case, blk in report["cases"].items():
        print(f"--- {case} ---")
        for variant in ("legacy", "fixed"):
            if variant not in blk:
                continue
            for h in HOLDS:
                a = blk[variant]["archived_semantics_label_axis"][f"hold{int(h)}"]
                b = blk[variant]["true_physics_axis"][f"hold{int(h)}"]
                print(f"  {variant:6s} hold{int(h):>2}s  label-axis succ={a['success_pct']}% "
                      f"(window {a['hold_window_physics_s']}s)  |  physical-axis succ={b['success_pct']}% "
                      f"(window {b['hold_window_physics_s']}s)")
        if "like_for_like_physical_axis" in blk:
            for h in HOLDS:
                x = blk["like_for_like_physical_axis"][f"hold{int(h)}"]
                print(f"  LIKE-FOR-LIKE hold{int(h):>2}s : fixed {x['success_fixed_n']} vs "
                      f"legacy {x['success_legacy_n']} | fixed-only {x['settled_in_fixed_only']} "
                      f"legacy-only {x['settled_in_legacy_only']} | ratio median {x['ratio_median']}")
    print("\nsaved:", out)


if __name__ == "__main__":
    main()
