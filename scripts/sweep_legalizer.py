"""Randomized bug-hunt sweep for the rtl_legalizer golden model.

Runs the (RTL-validated) golden model over many generated layouts and audits
every result for P1 (overlaps), P2 (die containment), P3 (size preservation).
Findings here are RTL behavior by transitivity; confirm RTL divergences
separately via the equivalence tests.
"""

import sys
from collections import Counter

sys.path.insert(0, "/home/ratik/Projects/RTLign")

from rtl_legalizer import audit, golden_model as gm, layout_gen

MODES = layout_gen.MODES
SIZES = [2, 8, 24, 64, 168]
SEEDS = range(10)

failures = Counter()
details = {}

total = 0
for mode in MODES:
    for n in SIZES:
        for seed in SEEDS:
            macros = layout_gen.gen_layout(mode, n, seed=seed)
            words = [v & 0xFFFFFFFF for m in macros for v in m]
            out, _ = gm.legalize_model(words)
            res = audit.check_layout(audit.to_macros(words), audit.to_macros(out))
            total += 1
            for i, j in res.overlaps:
                failures[f"{mode}/n={n} P1 overlap"] += 1
                details.setdefault(f"{mode}/n={n} P1", (seed, i, j))
            for i, axis, _ in res.boundary_violations:
                failures[f"{mode}/n={n} P2 boundary"] += 1
                details.setdefault(f"{mode}/n={n} P2", (seed, i, axis))
            for i, name, _, _ in res.size_mismatches:
                failures[f"{mode}/n={n} P3 size"] += 1
                details.setdefault(f"{mode}/n={n} P3", (seed, i, name))

print(f"runs: {total}")
print("\nfailures by kind:")
for kind, count in sorted(failures.items()):
    seed_info = details.get(kind.rsplit(" ", 1)[0], "")
    print(f"  {kind}: {count}  (first: seed {seed_info})")

print("\nper-mode summary (runs with >=1 violation / total):")
bad = set()
for kind in failures:
    mode = kind.split("/")[0]
    bad.add(mode)
for mode in MODES:
    n_runs = len(SIZES) * len(SEEDS)
    n_bad = sum(c for k, c in failures.items() if k.startswith(mode + "/"))
    print(f"  {mode}: {n_bad} violations across {n_runs} runs")
