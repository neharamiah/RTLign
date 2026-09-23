"""
Layout auditor for the RTL legalizer.

This module is the single source of truth for legalization checks. It checks
three properties on a legalized layout hex file:

- P1 Zero overlaps: no two macros overlap. Edges may touch.
- P2 Die containment: 0 <= x, x + w <= DIE_WIDTH, and the same for y.
- P3 Size preservation: output width and height match the input for each macro.

The HEX format is one 32-bit word per line, 4 words per macro in the order
X, Y, W, H (DEF database units). Inline `//` comments are allowed. The Icarus
$writememh output also carries address comments; the parser ignores them.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field

# Defaults match the RTL parameters (ISPD2015 mgc_matrix_mult_2 die).
DIE_WIDTH = 200260
DIE_HEIGHT = 201600

MASK32 = 0xFFFFFFFF


@dataclass
class AuditResult:
    """Outcome of one layout audit. Empty lists mean the property passed."""

    num_macros_in: int = 0
    num_macros_out: int = 0
    overlaps: list = field(default_factory=list)          # (i, j) macro index pairs
    boundary_violations: list = field(default_factory=list)  # (i, axis, detail)
    size_mismatches: list = field(default_factory=list)   # (i, field, in_val, out_val)
    errors: list = field(default_factory=list)            # structural errors (strings)

    @property
    def passed(self) -> bool:
        """True when no property failed and no structural error exists."""
        return not (self.overlaps or self.boundary_violations
                    or self.size_mismatches or self.errors)

    def summary_lines(self) -> list:
        """Human-readable report lines."""
        lines = [
            f"Macros: in={self.num_macros_in} out={self.num_macros_out}",
            f"P1 overlaps           : {len(self.overlaps)}",
            f"P2 boundary violations: {len(self.boundary_violations)}",
            f"P3 size mismatches    : {len(self.size_mismatches)}",
        ]
        lines += [f"ERROR: {e}" for e in self.errors]
        for i, j in self.overlaps[:10]:
            lines.append(f"  OVERLAP: macro {i} vs macro {j}")
        for i, axis, detail in self.boundary_violations[:10]:
            lines.append(f"  BOUNDARY: macro {i} {axis}: {detail}")
        for i, name, in_val, out_val in self.size_mismatches[:10]:
            lines.append(f"  SIZE: macro {i} {name} in={in_val} out={out_val}")
        lines.append("AUDIT PASS" if self.passed else "AUDIT FAIL")
        return lines


def read_hex_words(path: str) -> list:
    """Read 32-bit hex words from a file. Strips // comments and blank lines."""
    words = []
    with open(path) as f:
        for line in f:
            token = line.split("//")[0].strip()
            if token:
                words.append(int(token, 16))
    return words


def to_macros(words: list) -> list:
    """Group flat words into (x, y, w, h) tuples, 4 words per macro."""
    if len(words) % 4 != 0:
        raise ValueError(f"word count {len(words)} is not a multiple of 4")
    return [tuple(words[i:i + 4]) for i in range(0, len(words), 4)]


def check_layout(in_macros: list, out_macros: list,
                 die_w: int = DIE_WIDTH, die_h: int = DIE_HEIGHT) -> AuditResult:
    """Check P1, P2, P3 on macro tuples. Pure function, no file IO."""
    res = AuditResult(num_macros_in=len(in_macros), num_macros_out=len(out_macros))

    if len(in_macros) != len(out_macros):
        res.errors.append(
            f"macro count mismatch: input has {len(in_macros)}, output has {len(out_macros)}")
        return res

    # The RTL sees 32-bit words, so normalize every field to its unsigned
    # 32-bit interpretation first. A negative coordinate in Python (-1)
    # arrives in hex as 0xFFFFFFFF and must violate containment.
    n = len(out_macros)
    boxes = []
    for (x, y, w, h) in out_macros:
        x, y, w, h = x & MASK32, y & MASK32, w & MASK32, h & MASK32
        boxes.append((x, y, x + w, y + h))
    for i in range(n):
        ax, ay, ar, at = boxes[i]
        for j in range(i + 1, n):
            bx, by, br, bt = boxes[j]
            if ax < br and ar > bx and ay < bt and at > by:
                res.overlaps.append((i, j))

    # P2: die containment. Use 64-bit sums so a wrapped 32-bit add cannot
    # hide a violation (x + w must not wrap in real layouts).
    for i, (x, y, w, h) in enumerate(out_macros):
        x, y, w, h = x & MASK32, y & MASK32, w & MASK32, h & MASK32
        sx = x + w
        sy = y + h
        if x > die_w or sx > die_w:
            res.boundary_violations.append((i, "x", f"x={x} x+w={sx} die_w={die_w}"))
        if y > die_h or sy > die_h:
            res.boundary_violations.append((i, "y", f"y={y} y+h={sy} die_h={die_h}"))

    # P3: width and height preservation.
    for i, ((ix, iy, iw, ih), (ox, oy, ow, oh)) in enumerate(zip(in_macros, out_macros)):
        if (iw & MASK32) != (ow & MASK32):
            res.size_mismatches.append((i, "width", iw & MASK32, ow & MASK32))
        if (ih & MASK32) != (oh & MASK32):
            res.size_mismatches.append((i, "height", ih & MASK32, oh & MASK32))

    return res


def audit_layout(in_hex: str, out_hex: str,
                 die_w: int = DIE_WIDTH, die_h: int = DIE_HEIGHT) -> AuditResult:
    """Audit an output hex file against its input hex file."""
    in_macros = to_macros(read_hex_words(in_hex))
    out_macros = to_macros(read_hex_words(out_hex))
    return check_layout(in_macros, out_macros, die_w, die_h)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Audit a legalized layout hex file.")
    ap.add_argument("input_hex", help="input layout hex (pre-legalization)")
    ap.add_argument("output_hex", help="output layout hex (post-legalization)")
    ap.add_argument("--die-width", type=int, default=DIE_WIDTH)
    ap.add_argument("--die-height", type=int, default=DIE_HEIGHT)
    args = ap.parse_args(argv)

    res = audit_layout(args.input_hex, args.output_hex, args.die_width, args.die_height)
    for line in res.summary_lines():
        print(line)
    return 0 if res.passed else 1


if __name__ == "__main__":
    sys.exit(main())
