# rtl_legalizer Verification Report

Date: 2026-09-23. Scope: the two-pass Verilog legalizer (SA engine + greedy
sweep) in `rtl_legalizer/`. Tools: Icarus Verilog 12.0, Verilator 5.025
(oss-cad-suite), OpenROAD 26Q2 (not exercised here), Python 3.13.

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

### LIM-1 (documented, not fixed): dense layouts keep residual overlaps

The greedy cleanup runs at most 9 sweeps. Pushes can cascade (pushing B
shoves it into C, D, ...), and 9 sweeps do not settle moderately dense
layouts. A 350-run sweep of the RTL-validated golden model found:

- `dense`: overlaps on every seed at N >= 24 (up to ~3800 residual pairs at N=168).
- `chain`: overlaps on every seed at N >= 24.
- `pair_overlap`, `out_of_bounds`: occasional overlaps at N >= 64.
- `single`, `legal`: always clean.
- P3 (size preservation): zero violations in all 350 runs.
- P2 violations only for `wide_macro` (unfixable by design, see LIM-2).

RTL confirmation: the full SA + greedy pipeline on `dense/24/seed0` leaves
exactly 2 overlaps; the hardened testbench exits non-zero via `$fatal`
(`tests/test_phase6_verification.py::TestSweepFindings`).

The README previously claimed "Zero overlaps guaranteed". That claim is now
removed; the guarantee holds only for layouts the sweep can settle (sparse
inputs, small N). Fixing this needs an algorithm change (more sweeps, a
progressive-resolution scheme, or row-based legalization) and is a design
decision, not a bug fix.

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
| P1 zero overlaps | Pass on sparse/realistic layouts. Fails on dense layouts >= 24 macros (LIM-1). | sweep + RTL confirmation |
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
