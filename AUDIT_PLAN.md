# RTLign — Full-Project Audit Plan

**Date:** 2026-09-24
**Scope:** Every file and every documented claim in the repo. The `data/` bulk is checked by metadata only. `oss-cad-suite/`, `.git/`, and `graphify-out/` are out of scope.
**Runner:** `python scripts/run_audit.py` → writes `audit_report.md`. Exit 0 = clean, exit 1 = at least one FAIL.

---

## 1. What "correct" means (evidence base)

The audit checks reality against four sources of truth:

| Source | Key claims it makes |
|:---|:---|
| `README.md` | 135 tests pass. Verilator gives 10×–1000× speedup depending on design size (mockup ~40×). Closed-loop OpenROAD evaluation works. Project structure listing is accurate. |
| `rtl_legalizer/VERIFICATION.md` | Properties P1–P6 hold on sparse/realistic layouts; SA rejects illegal moves (legality scan). Dense synthetic clusters ≥ 24 macros leave overlaps (LIM-1). Metropolis deviates from exp(−Δ/T) (QUIRK-1). Mockup regression: 168 macros, cost 3,704,579, 889,114 Verilator cycles. |
| `PROGRESS.md` §5 | Mockup: 889,115 cycles (Icarus), cost 3,704,579, 1000 iterations, 4 legality-scan rejects, audit PASS. Dataset: 1,300 generated DEFs; 4,248 parquet rows (mockup-scale snapshot). |
| `AUDIT_PLAN.md` (this file) | Defines the exact pass rule for every check below. |

## 2. Audit catalog

Each check has an ID, a command, an expected result, and a pass rule. Tags select tiers: `env`, `inventory`, `static`, `tests`, `stage`, `ml`, `e2e`.

### A0 — Environment & tools (tag: `env`)

| ID | Check | Expected | Pass rule |
|:---|:---|:---|:---|
| A0.1 | `python3 --version` | Python 3.x | Exit 0 |
| A0.2 | `pytest --version` | Installed | Exit 0 |
| A0.3 | `iverilog -V` / `vvp -V` | Icarus 11/12 | Exit 0 |
| A0.4 | `verilator --version` | 5.x via `oss-cad-suite/bin` fallback | Exit 0 on PATH or fallback |
| A0.5 | `openroad -version` | OpenROAD present | Exit 0 (WARN if missing; `--skip openroad` skips A6) |
| A0.6 | Import probe: torch, torch_geometric, pandas, matplotlib, networkx, hypothesis, joblib, sklearn | All importable | Each import exit 0 |
| A0.7 | `rtl_legalizer/verilator/legalizer_sim` exists | Prebuilt binary present | File exists and is executable |
| A0.8 | Binary freshness | `legalizer_sim` newer than every `.v` source | mtime(binary) ≥ max mtime(.v) → else WARN (stale build) |

### A1 — Inventory & data assets (tag: `inventory`)

| ID | Check | Expected | Pass rule |
|:---|:---|:---|:---|
| A1.1 | README project-structure files exist | Every path listed in README §Project Structure | All exist |
| A1.2 | Model checkpoint | `topological_gnn_model.pth` at repo root | Exists, size > 0 |
| A1.3 | Scalers | `data/node_scaler.joblib`, `data/edge_scaler.joblib` | Both exist |
| A1.4 | Golden fixtures | `tests/data/golden/golden_input_168.hex`, `golden_output_168.hex`, `golden_metrics.txt` | All exist |
| A1.5 | ISPD 2015 designs | 4 designs under `data/ispd_benchmarks/ispd2015/hidden/` | ≥ 4 dirs with `tech.lef` + `cells.lef` |
| A1.6 | Parquet row counts (footer only) | `ml_features.parquet` row count vs the 21.6M claim | Read metadata, no full load. Record; FAIL only if unreadable |
| A1.7 | Generated DEF count | `data/generated_defs/` count vs the 277 claim | Record observed vs claim → DOC-DRIFT if mismatch |
| A1.8 | Git tree state | Clean working tree | WARN only (informational) |

### A2 — Static & docs consistency (tag: `static`)

| ID | Check | Expected | Pass rule |
|:---|:---|:---|:---|
| A2.1 | Byte-compile all project `.py` | No syntax errors | `python -m py_compile` exit 0 for each |
| A2.2 | `iverilog` syntax-check all project `.v` | No compile errors | Per-file elaboration exit 0 |
| A2.3 | TODO/FIXME/HACK inventory | Known list | Record; new items flagged as WARN |
| A2.4 | Documented commands parse | Every command in README/AGENTS.md references files that exist | All targets exist |
| A2.5 | Stale path: `data/parquet_dataset` | README training command uses a path that does not exist | Confirm and mark DOC-DRIFT |
| A2.6 | Greedy pass cap wording | PROGRESS says "8 passes"; VERIFICATION says 9 sweeps | Confirm wording, mark DOC-DRIFT |
| A2.7 | Mockup component count | PROGRESS says 482; `master_run.py` comment says 168 | Count COMPONENTS in `mockup_export.def`; mark drift where wrong |
| A2.8 | HEX contract | 4 words per macro, order X, Y, W, H in all producers/consumers (`def_parser.py`, `hex_to_def.py`, `audit.py`, `legalizer_tb.v`, `sa_harness.cpp`) | Consistent order everywhere |

### A3 — Verification suite (tag: `tests`)

| ID | Check | Expected | Pass rule |
|:---|:---|:---|:---|
| A3.1 | `pytest tests/ rtl_legalizer/ -v` | All tests pass | Exit 0 |
| A3.2 | Test count vs "135" claim | Count collected tests | Observed == 135 → PASS; else FAIL the claim (DOC-DRIFT) |
| A3.3 | `python scripts/sweep_legalizer.py` | Result profile matches VERIFICATION.md §LIM-1 (dense ≥ 24 fails P1, sparse clean, P3 always clean) | Profile matches documented findings |
| A3.4 | `python scripts/characterize_metropolis.py` | Acceptance table matches QUIRK-1 (hard rejection at Δ ≥ T, k ≈ 4 exponent) | Qualitative match |

### A4 — Stage-by-stage pipeline, mockup (tag: `stage`)

| ID | Check | Expected | Pass rule |
|:---|:---|:---|:---|
| A4.1 | LEF parse (`parse_lef_files`) | ≥ 100 cell types, known dimensions spot-checked | Count ≥ 100 and spot values match |
| A4.2 | DEF→HEX (`parse_def_to_hex`) | 672 lines (4 × 168), names in comments, dims match LEF dict | Line count exact; spot-check dims |
| A4.3 | Icarus legalizer run | Exit 0, `output_layout.hex` written, audit P1/P2/P3 PASS | `$fatal`-free, `audit.py` PASS |
| A4.4 | Icarus metrics vs PROGRESS.md | cycles 889,115 ± 1, final cost 3,704,579, iterations 1000 | Exact match within tolerance |
| A4.5 | Verilator run | Word-identical output to Icarus | `audit.read_hex_words` equality |
| A4.6 | Golden regression | Verilator output == `tests/data/golden/golden_output_168.hex`; cost matches `golden_metrics.txt` | Word-exact |
| A4.7 | Determinism | Two Verilator runs byte-identical | Byte equality |
| A4.8 | 10×–1000× speedup claim | Time both simulators on the mockup | Record ratio; PASS if ≥ 100×, WARN below (mockup measures ~40×; larger designs amortize better) |
| A4.9 | HEX→DEF injection | Component count preserved; only target macro lines changed; standard cells untouched | Parse input/output DEFs; diff restricted to macro coordinate lines |
| A4.10 | `audit.py` CLI exit codes | 0 on legal pair, non-zero on violation | Synthetic bad layout exits non-zero |

### A5 — ML predictor (tag: `ml`)

| ID | Check | Expected | Pass rule |
|:---|:---|:---|:---|
| A5.1 | Checkpoint + scalers load | `torch.load`, `joblib.load` succeed | Exit 0 |
| A5.2 | `predict.py` on mockup | Completes, writes constraint hex + coordinate hex | Exit 0, files non-empty |
| A5.3 | Independent DAG check | Rebuild graph from constraint hex with networkx; assert acyclic | `nx.is_directed_acyclic_graph` true |
| A5.4 | Coordinate legality | Coordinate hex passes `audit.check_layout` P2 containment (P1 not required pre-legalization) | No boundary violations |
| A5.5 | `run_predict.py` auto-detect | Runs with defaults on repo root | Exit 0 |
| A5.6 | Prediction sanity | L-flow (Δx, Δy) distribution has finite values, plausible range | No NaN/inf |
| A5.7 | (opt) 1-epoch retrain smoke test | `train_nn.py` runs 1 epoch on real data | Only with `--with-retrain`; exit 0 |

### A6 — End-to-end + OpenROAD (tag: `e2e`; skipped by `--skip openroad`)

| ID | Check | Expected | Pass rule |
|:---|:---|:---|:---|
| A6.1 | `master_run.py` full run | All 4 stages exit 0 | Exit 0 |
| A6.2 | Output audit | `dummy_layout.hex` → `output_layout.hex` passes `audit.py` | P1/P2/P3 PASS |
| A6.3 | Output determinism | Output hex matches golden fixture | Word-exact |
| A6.4 | `evaluate.py` on mockup | Completes; `evaluation_plot.png` produced | Exit 0, plot file exists |
| A6.5 | Macro-level OpenROAD legality | No macro-vs-macro pair in the `check_placement` overlap list (macro-vs-cell overlaps after macro movement are a documented downstream scope item: cell re-placement + macro site alignment, Phase 7) | Zero macro-macro pairs; HPWL captured both sides |
| A6.6 | HPWL comparison | Baseline vs RTLign HPWL captured; improvement % reported | Negative improvement → WARN, not auto-FAIL |

### A7 — Claims ledger (auto-assembled)

The runner collects every documented claim and prints one table:

| Claim | Source | Observed | Verdict |
|:---|:---|:---|:---|

Verdicts: **PASS**, **FAIL**, **DOC-DRIFT** (docs wrong, code right or unknown), **EXPECTED-LIMITATION** (documented behavior such as LIM-1, LIM-2, QUIRK-1, QUIRK-2).

## 3. Manual review matrix

The runner prints the file inventory. For each source file below, a human pass looks for: silent failure paths, stale references, dead code, hardcoded assumptions, and producer/consumer contract mismatches.

- `orchestration/`: `master_run.py`, `data_generator.py`, `generate_rtl_dataset.py`, `rtl_to_def.py`
- `ml_predictor/`: `dataset.py`, `model.py`, `train_nn.py`, `predict.py`, `evaluate.py`, `feature_extractor.py`, `def_parser.py`, `hex_to_def.py`
- `rtl_legalizer/`: `sa_legalizer_top.v`, `sa_engine.v`, `sa_cost.v`, `lfsr32.v`, `collision_check.v`, `legalizer_fsm.v`, `legalizer_tb.v`, `tb_*.v`, `audit.py`, `golden_model.py`, `layout_gen.py`, `lef_parser.py`, `verilator/*`
- `scripts/`: `sweep_legalizer.py`, `characterize_metropolis.py`
- `tests/`: all `test_*.py`
- `openroad_scripts/`: `run_placement.tcl`, `evaluate_layout.tcl`, `generate_ibex_floorplan.tcl`
- Root: `run_predict.py`, `merge_lefs.py`, `conftest.py`

## 4. How to run

```bash
# Full audit (may take ~10 min; pytest dominates)
python scripts/run_audit.py

# Skip OpenROAD stages
python scripts/run_audit.py --skip openroad

# Quick sanity (env, inventory, static only)
python scripts/run_audit.py --quick

# One tier
python scripts/run_audit.py --tags tests

# Include the 1-epoch GNN retrain smoke test
python scripts/run_audit.py --with-retrain

# Custom report path
python scripts/run_audit.py --output audit_report.md
```

## 5. Doc-drift ledger (resolved 2026-09-24)

All items below were found by the first audit run and fixed in the docs/code the same day. The checks in `scripts/run_audit.py` now guard against regressions.

1. **RESOLVED** — README training command no longer references the nonexistent `data/parquet_dataset`; it documents that `train_nn.py` takes no CLI flags (epochs default 100).
2. **RESOLVED** — VERIFICATION.md corrected to "8 sweeps" (RTL truth: `pass_count < 8`); PROGRESS.md was right.
3. **RESOLVED** — `master_run.py` comment now distinguishes 482 components from the 168 placed fill-cell macros; PROGRESS's 482 stands for the DEF.
4. **OPEN (by design)** — `evaluate.py` uses Verilator only when `num_lines == 672`; other sizes fall back to Icarus. Harmless fallback; revisit when the harness is parameterized at runtime.
5. **RESOLVED** — `master_run.py` now gates on `audit.py` (VERIFICATION.md next-step #3).
6. **OPEN** — `evaluate.py` `check_dependencies()` pip-installs packages as a side effect; harmless but worth removing.
7. **RESOLVED** — the "135 tests" claim verified exactly (135 collected and passing).
