# rtl_legalizer Verification Report

Date: 2026-09-23; updated 2026-09-24 (SA legality scan added, fixtures and
profiles re-baselined, LIM-1 re-measured). Scope: the two-pass Verilog
legalizer (SA engine + greedy sweep) in `rtl_legalizer/`. Tools: Icarus
Verilog 12.0, Verilator 5.025 (oss-cad-suite), OpenROAD 26Q2 (not exercised
here), Python 3.13.

## 1. Verification spec

A legalizer run counts as correct when it satisfies all of these:

| ID | Property | Definition |
|----|----------|------------|
| P1 | Zero overlaps | Strict AABB test over all macro pairs. Touching edges are legal. |
| P2 | Die containment | `0 <= x`, `x+w <= DIE_WIDTH`, and the same for `y`. |
| P3 | Size preservation | Output W and H match input W and H for every macro. |
| P4 | Determinism | Same input and seed give bit-identical output on every run and on both simulators. |
| P5 | Liveness | `done` asserts within a bounded cycle budget. No hangs. |
| P6 | Cost correctness | `sa_cost` matches a bit-exact Python golden model. |

Both simulator paths are in scope: Icarus (`legalizer_tb.v`) and Verilator
(`verilator/sa_harness.cpp`), plus a cross-simulator equivalence check.

## 2. Infrastructure added

| File | Purpose |
|------|---------|
| `rtl_legalizer/audit.py` | Single source of truth for P1, P2, P3 checks. CLI + importable. |
| `rtl_legalizer/layout_gen.py` | Seeded input generator: 7 modes (single, legal, pair_overlap, chain, dense, out_of_bounds, wide_macro). |
| `rtl_legalizer/golden_model.py` | Bit-exact Python model of lfsr32, sa_cost, sa_engine (LFSR schedule, fixed-point Metropolis, boundary reflection), and legalizer_fsm. |
| `rtl_legalizer/tb_collision_check.v` | Directed AABB corner matrix, self-checking, `$fatal` on mismatch. |
| `rtl_legalizer/tb_sa_cost.v` | Directed cost scenarios, including negative-coordinate wrap semantics. |
| `rtl_legalizer/tb_legalizer_fsm.v` | Generic greedy-sweep driver (Python supplies input, audits output). |
| `rtl_legalizer/tb_sa_trace.v` | Debug probe: prints per-iteration SA internals for golden-model validation. |
| `rtl_legalizer/tb_cost_vectors.v` | Real-scale cost vector generation for golden-model validation. |
| `rtl_legalizer/verilator/sa_harness.cpp` + `Makefile` | Parameterized via `NUM_LINES`/`DIE_WIDTH`/`DIE_HEIGHT` make variables (was hardcoded to 672). |
| `tests/test_audit.py`, `tests/test_unit_tbs.py`, `tests/test_golden_model.py`, `tests/test_phase6_verification.py` | 135 tests total, all green from the repo root: `pytest tests/ rtl_legalizer/ -v`. |
| `tests/data/golden/` | Golden input, output, and metrics for the 168-macro mockup regression. |
| `scripts/sweep_legalizer.py`, `scripts/characterize_metropolis.py` | Bug-hunt sweep (350 runs) and Metropolis characterization. |
| `conftest.py` | Puts the repo root on `sys.path` for every test. |

Golden-model validation is staged and exact (no tolerances): cost vectors,
greedy word-for-word on 6 layouts, a 1000-iteration SA trajectory (selection
stream, all 999 tracked cost transitions, final metrics), and the full
two-pass pipeline on the mockup (word-for-word).

## 3. Findings

### BUG-1 (fixed): outer-loop hang for `NUM_MACROS == 1`

`legalizer_fsm.v` computed the outer-loop bound as `ptr_a < last_base - 4`.
The subtraction runs in a 32-bit context, so with one macro (`last_base = 0`)
it wrapped to `0xFFFFFFFC` and the loop never ended. Fix: compare
`(ptr_a + 4) < last_base`. Semantics are identical for `NUM_MACROS >= 2`.
Reproducer: `tests/test_unit_tbs.py::TestLegalizerFSM::test_single_macro_terminates`.

### BUG-2 (fixed): infinite RESOLVE/CHECK loop on unresolvable pairs

When a pair cannot be separated on any axis (for example two die-wide macros
whose heights overflow the die), the push recomputed the same position every
cycle and the FSM hung forever. Fix: a per-pair attempt counter
(`MAX_RESOLVE_TRIES = 16`); `CHECK` falls through to `ADVANCE` at the cap.
Normal pairs resolve in 1-2 tries, so their behavior is unchanged. The pair
stays overlapping and the audit layer reports it.
Reproducer: `tests/test_unit_tbs.py::TestLegalizerFSM::test_unresolvable_pair_terminates`.

### LIM-1 (re-measured 2026-09-24): dense synthetic layouts keep residual overlaps

The SA engine now rejects any candidate move that would overlap another macro
(a legality scan over `collision_check.v` before Metropolis acceptance), so
Pass 1 never leaves the legal placement space and no longer *creates* the
overlaps that Pass 2 must undo. The greedy cleanup still runs at most 8
sweeps, and its push-only strategy cannot untangle dense synthetic clusters:

- `dense`: P1 violations on 23 of 50 runs (was 29); up to ~4500 residual
  pairs at N=168.
- `chain`: P1 violations on 4 of 50 runs (was 22); P2 boundary violations
  can also remain (the sweep cannot pull wrapped macros back inside).
- `pair_overlap`: clean (was occasional violations).
- `out_of_bounds`: P1 on 1 of 50 runs (was 6).
- `single`, `legal`: always clean.
- `wide_macro`: P1 clean; P2 violations remain by design (LIM-2).
- P3 (size preservation): zero violations in all 350 runs.

Real-design result: with the legality scan, the closed loop (GNN prediction →
RTL legalization → DEF injection) produces macro-vs-macro-legal output on
`mgc_pci_bridge32_b` where the pre-scan RTL left 3 residual overlaps and
aborted. Remaining macro-vs-standard-cell overlaps after macro movement are a
downstream-flow responsibility (cell re-placement + macro site alignment;
Phase 7).

RTL confirmation: the full SA + greedy pipeline on `dense/24/seed0` leaves
exactly 3 overlaps; the hardened testbench exits non-zero via `$fatal`
(`tests/test_phase6_verification.py::TestSweepFindings`).

Fixing the dense case needs an algorithm change (progressive-resolution or
row-based legalization) and is a design decision, not a bug fix.

### LIM-2 (documented): a macro wider than the die can never be legal

The engine clamps it to x=0 and keeps its size; containment stays violated.
The audit flags it. This is inherent to the input, not an engine bug.

### QUIRK-1 (characterized): Metropolis acceptance deviates from exp(-delta/T)
Measured with the golden model (`scripts/characterize_metropolis.py`):

| delta/T | true Metropolis | RTL acceptance |
|--------:|----------------:|---------------:|
| 0.0625  | 0.939 | 0.779 |
| 0.25    | 0.779 | 0.369 |
| 0.5     | 0.607 | 0.136 |
| 1.0     | 0.368 | 0.000 |
| >= 1.0  | > 0   | 0.000 (hard rejection) |
| [32,33) | ~0    | ~1.000 (alias window) |

- The LUT indexing yields an effective exponent of **k = 3.99 (theory: 4)**:
  the engine anneals at T/4.
- Any uphill move with `delta >= T` is always rejected (ratio bit-field
  saturation). True Metropolis would accept it with p = 0.37 at delta = T.
- The saturation test checks only `ratio[16:12]`, so `delta/T` in [32,33) and
  [64,65) aliases back into the low LUT and is **always accepted**. Reachable
  at low temperature; benign in observed runs but worth knowing.
- The RNG is structurally correlated: each iteration consumes three LFSR
  words (selection, move bytes, dice), and the next iteration's selection
  word is the previous iteration's dice word.

**Quality impact and decision**: with the same RNG stream and the fixed
1000-iteration budget, exact Metropolis gives *worse* mean final cost than
the RTL math (mockup: +1.3%, dense/24: +4.0%). The RTL math is effectively a
greedier search, which suits the short schedule. **Recommendation: do not
change the acceptance math now.** If quality matters more than runtime, raise
`MAX_ITERS` first and re-measure; regenerate the golden files after any such
change.

### QUIRK-2 (documented): negative coordinates collapse the cost bbox

`sa_cost.v` scans bounding-box extrema with unsigned comparisons. A macro at
a "negative" coordinate (two's-complement word) becomes a huge unsigned
value, which corrupts min/max tracking and can zero the bbox term. The
golden model replicates this exactly (`tb_sa_cost.v` pins it). Real pipeline
inputs never produce negative coordinates; the reflection chain in
`sa_engine.v` clamps candidates into the die.

### Observation (fixed as part of verification): silent testbench

The Icarus testbench previously printed `AUDIT FAIL` and still exited 0. It
now audits overlaps (P1), die containment (P2), and size preservation (P3),
and calls `$fatal(1)` on any violation, so `vvp` exits 1. CI-ready.

## 4. Property results

| Property | Result | Evidence |
|----------|--------|----------|
| P1 zero overlaps | Pass on sparse/realistic layouts and on real-design closed-loop runs. Fails on dense synthetic clusters >= 24 macros (LIM-1). | sweep + RTL confirmation + closed-loop check |
| P2 die containment | Pass everywhere except unfittable `wide_macro` inputs (LIM-2). | sweep |
| P3 size preservation | Pass in all 350 sweep runs and all RTL runs. | sweep + audits |
| P4 determinism | Byte-identical outputs across repeated runs on both simulators. | `TestDeterminism` |
| P5 liveness | Guaranteed after BUG-1/BUG-2 fixes (watchdog-backed). | unit TBs |
| P6 cost correctness | Bit-exact match between `sa_cost.v` and the golden model. | `TestStage1Cost` |
| Icarus = Verilator | Word-identical outputs and metrics on the mockup; cycle counts differ by 1 due to harness counting boundaries only. | `TestSimulatorEquivalence` |

## 5. How to re-run

```bash
pytest tests/ rtl_legalizer/ -v          # full regression (135 tests)
python scripts/sweep_legalizer.py        # model-level bug hunt
python scripts/characterize_metropolis.py # Metropolis deviation + quality
python rtl_legalizer/audit.py in.hex out.hex   # audit any layout pair
```

The golden regression needs the default Verilator binary:
`make -C rtl_legalizer/verilator`. Rebuild with
`make -B NUM_LINES=32` for other sizes; the harness dump depth follows.

## 6. Recommended next steps (out of scope here)

1. Decide whether to strengthen Pass 2 (LIM-1) if dense input support matters.
2. Consider raising `MAX_ITERS` and re-measuring quality before touching the
   Metropolis math.
3. Gate `master_run.py` on `audit.py` so pipeline regressions fail loudly.
4. Optional: CI workflow that runs the pytest suite; Verilator + Icarus are
   already wired for it.
