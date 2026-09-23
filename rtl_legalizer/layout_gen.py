"""
Seeded layout generator for legalizer verification.

Generates input hex files (same format as ml_predictor/def_parser.py output:
one 32-bit word per line, 4 words per macro in X, Y, W, H order) for directed
and randomized legalizer tests. Every mode is deterministic for a given seed.
"""

from __future__ import annotations

import argparse
import random

# Defaults match the RTL parameters.
DIE_WIDTH = 200260
DIE_HEIGHT = 201600

MODES = (
    "single",         # exactly one macro (NUM_MACROS == 1 edge case)
    "legal",          # n macros in a non-overlapping grid
    "pair_overlap",   # two macros overlapping on one axis
    "chain",          # n macros, each overlapping its right neighbor
    "dense",          # n macros stacked with heavy mutual overlap
    "out_of_bounds",  # legal grid plus macros poking outside the die
    "wide_macro",     # one macro wider than the die (unfixable by design)
)


def write_hex(macros: list, path: str) -> None:
    """Write macros as hex words with def_parser-style comments."""
    fields = ("X coord", "Y coord", "Width", "Height")
    with open(path, "w") as f:
        for (x, y, w, h) in macros:
            for val, name in zip((x, y, w, h), fields):
                f.write(f"{val & 0xFFFFFFFF:08X} // {name}\n")


def _rand_size(rng: random.Random, lo=4000, hi=20000) -> tuple:
    return rng.randint(lo, hi), rng.randint(lo, hi)


def gen_layout(mode: str, n: int, seed: int,
               die_w: int = DIE_WIDTH, die_h: int = DIE_HEIGHT) -> list:
    """Return a list of (x, y, w, h) macro tuples for the requested mode."""
    rng = random.Random(seed)

    if mode == "single":
        w, h = _rand_size(rng)
        return [(die_w // 3, die_h // 3, w, h)]

    if mode == "legal":
        cols = max(1, int(n ** 0.5) + (n ** 0.5 % 1 > 0))
        cell_w = die_w // cols
        cell_h = die_h // (max(1, -(-n // cols)))
        macros = []
        for i in range(n):
            w = min(cell_w * 3 // 5, rng.randint(4000, max(5000, cell_w * 3 // 5)))
            h = min(cell_h * 3 // 5, rng.randint(4000, max(5000, cell_h * 3 // 5)))
            x = (i % cols) * cell_w + (cell_w - w) // 2
            y = (i // cols) * cell_h + (cell_h - h) // 2
            macros.append((x, y, w, h))
        return macros

    if mode == "pair_overlap":
        if n < 2:
            return gen_layout("single", n, seed, die_w, die_h)
        w1, h1 = _rand_size(rng)
        w2, h2 = _rand_size(rng)
        x1, y1 = die_w // 4, die_h // 4
        # Second macro overlaps the first by half its width, offset in y so
        # the overlap region is a proper rectangle.
        x2 = x1 + w1 - w2 // 2
        y2 = y1 + h1 // 3
        macros = [(x1, y1, w1, h1), (x2, y2, w2, h2)]
        macros += gen_layout("legal", n - 2, seed, die_w, die_h)
        return macros

    if mode == "chain":
        macros = []
        x = die_w // 8
        y = die_h // 2
        for i in range(n):
            w, h = _rand_size(rng)
            macros.append((x, y, w, h))
            x += w // 2  # next macro starts inside this one
        return macros

    if mode == "dense":
        macros = []
        cx, cy = die_w // 2, die_h // 2
        for i in range(n):
            w, h = _rand_size(rng, 8000, 30000)
            x = cx - w // 2 + rng.randint(-w // 4, w // 4)
            y = cy - h // 2 + rng.randint(-h // 4, h // 4)
            macros.append((x, y, w, h))
        return macros

    if mode == "out_of_bounds":
        if n < 2:
            w, h = _rand_size(rng)
            return [(-100, die_h // 2, w, h)]
        macros = gen_layout("legal", n - 2, seed, die_w, die_h)
        w, h = _rand_size(rng)
        macros.append((die_w - w // 2, die_h // 4, w, h))          # pokes right
        macros.append((-100, die_h // 2, w, h))                    # negative x
        return macros

    if mode == "wide_macro":
        macros = gen_layout("legal", max(0, n - 1), seed, die_w, die_h)
        macros.append((0, die_h - 100, die_w * 2, 50))  # wider than the die
        return macros

    raise ValueError(f"unknown mode: {mode}. Valid modes: {', '.join(MODES)}")
