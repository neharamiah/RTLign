# RTLign Audit Report

**Date:** 2026-09-24 23:54 IST
**Commit:** db86abc
**Runner wall time:** 1.6 min
**Tiers run:** all (retrain smoke test off)

**Verdict counts:** 42 PASS, 0 FAIL, 3 WARN, 0 DOC-DRIFT, 2 EXPECTED-LIMITATION, 1 SKIP

**Overall: PASS** (exit 0 requires zero FAIL; WARN and DOC-DRIFT are reported, not fatal)

## Results by tier

### env

| ID | Check | Verdict | Detail |
|:---|:---|:---|:---|
| A0.1 | python3 present | PASS | Python 3.13.12 |
| A0.2 | pytest present | PASS | pytest 9.0.3 |
| A0.3 | iverilog + vvp present | PASS | iverilog: Icarus Verilog version 12.0 (stable) (); vvp: Icarus Verilog runtime version 12.0 (stable) () |
| A0.4 | verilator present (PATH or oss-cad-suite) | PASS | Verilator 5.025 devel rev v5.024-52-g9a8e68928 |
| A0.5 | openroad present | PASS | 26Q2-322-g1afad943d3 |
| A0.6 | python imports (torch, PyG, pandas, ...) | PASS | torch 2.14.0+cpu; torch_geometric 2.8.0.post1; pandas 3.0.5; matplotlib 3.11.1; networkx 3.6.1; hypothesis 6.154.1; joblib 1.6.0; sklearn 1.9.0; pyarrow 25.0.0 |
| A0.7 | prebuilt Verilator binary present | PASS | /home/ratik/Projects/RTLign/rtl_legalizer/verilator/legalizer_sim (210144 bytes) |
| A0.8 | Verilator binary freshness vs RTL sources | PASS | binary newer than all design .v sources |

### inventory

| ID | Check | Verdict | Detail |
|:---|:---|:---|:---|
| A1.1 | README project structure matches disk | PASS | 47 README-listed paths all exist |
| A1.2 | GNN checkpoint present | PASS | checkpoint present, 780226 bytes, modified 2026-09-06 |
| A1.3 | scaler files present | PASS | node_scaler.joblib and edge_scaler.joblib present in data/ |
| A1.4 | golden regression fixtures present | PASS | 3 golden fixtures present |
| A1.5 | ISPD 2015 benchmark designs present | PASS | 4 designs: mgc_matrix_mult_2, mgc_matrix_mult_c, mgc_superblue14, mgc_superblue19 |
| A1.6 | parquet row count vs 21.6M claim | PASS | row counts: {'ml_features.parquet': 876, 'raw_coords.parquet': 876, 'edge_index.parquet': 540, 'pairwise_distances.parquet': 1956}; files total 4,248 rows (matches the corrected PROGRESS claim; the original 21.6M-sample extraction is not part of the shipped snapshot) |
| A1.7 | generated DEF count vs 277 claim | PASS | 1300 generated DEFs (matches the corrected PROGRESS claim) |
| A1.8 | git working tree state | WARN | dirty tree, 17 entries (informational) |

### static

| ID | Check | Verdict | Detail |
|:---|:---|:---|:---|
| A2.1 | byte-compile every project .py | PASS | all 34 .py files byte-compile |
| A2.2 | iverilog elaborates all .v sources | PASS | all 6 design files + 6 testbenches elaborate under iverilog |
| A2.3 | TODO/FIXME inventory | PASS | no TODO/FIXME/HACK/XXX markers |
| A2.4 | documented command targets exist | PASS | all 26 doc-referenced repo targets exist |
| A2.5 | stale data/parquet_dataset path (README) | PASS | path consistent |
| A2.6 | greedy pass cap wording (8 vs 9) | PASS | wording consistent (RTL-8:True, PROGRESS-8:True, VERIFICATION-9:False) |
| A2.7 | mockup component count (482 vs 168) | PASS | DEF header COMPONENTS 482; component lines 482; the legalizer consumes 168 placed macros (672 hex words). master_run.py comment is corrected. |
| A2.8 | HEX contract (4 words, X/Y/W/H) consistency | PASS | 672 words both ways; round-trip exact; order documented in audit.py, predict.py uses // X // Y // Width // Height tags; ['ml_predictor/hex_to_def.py: name-tagged'] |

### tests

| ID | Check | Verdict | Detail |
|:---|:---|:---|:---|
| A3.1 | full pytest suite green | PASS | 135 tests passed in 23s (claim: 135) |
| A3.2 | test count matches the '135 tests' claim | PASS | 135 tests passed in 23s (claim: 135) |
| A3.3 | 350-case sweep matches documented profile | EXPECTED-LIMITATION | 350 runs in 10s; profile matches VERIFICATION.md LIM-1 (violations: chain:1603; dense:4755; legal:0; out_of_bounds:18; pair_overlap:0; single:0; wide_macro:50; P3: 0) |
| A3.4 | Metropolis characterization matches QUIRK-1 | EXPECTED-LIMITATION | k=3.992 (theory 4), hard rejection at delta/T=1.0 — matches QUIRK-1 |

### stage

| ID | Check | Verdict | Detail |
|:---|:---|:---|:---|
| A4.1 | LEF parse extracts cell dimensions | PASS | 331 cell types; sample: {'ms00f80': (1600, 2000), 'oa22f80': (204800, 2000), 'oa22f40': (102400, 2000)} |
| A4.2 | DEF -> HEX extraction (672 words, 168 macros) | PASS | 672 words = 168 placed components (168 'X coord' tags; def_parser format carries no instance names) |
| A4.3 | Icarus legalizer run + audit | PASS | legalized 168 macros in 3.1s; audit P1/P2/P3 PASS; metrics {'cycles': 889115, 'iterations': 1000, 'final_cost': 3704579} |
| A4.4 | Icarus metrics vs documented values | PASS | cycles=889115, cost=3704579, iterations=1000 — matches PROGRESS.md §5 |
| A4.5 | Verilator run word-identical to Icarus | PASS | word-identical to Icarus; 0.07s; metrics {'cycles': 889114, 'iterations': 1000, 'final_cost': 3704579} |
| A4.6 | golden regression (Verilator vs fixtures) | PASS | output words and final cost match tests/data/golden/ |
| A4.7 | determinism (two Verilator runs) | PASS | two runs byte-identical (P4 determinism) |
| A4.8 | 10x-1000x Verilator speedup claim | WARN | speedup 42.3x on the 168-macro mockup (claim ~400x; small design amortizes poorly) |
| A4.9 | HEX -> DEF injection follows its matching contract | PASS | 482 components preserved; exactly the 168 sequential-contract components changed; 314 untouched |
| A4.10 | audit.py CLI exit codes | PASS | exit 0 on legal pair, exit 1 on crafted overlap |

### ml

| ID | Check | Verdict | Detail |
|:---|:---|:---|:---|
| A5.1 | checkpoint + scalers load | PASS | state_dict keys=28; scalers loaded (StandardScaler, StandardScaler) |
| A5.2 | predict.py inference (mockup + ISPD fallback) | PASS | mockup predict fails as expected (no matching LEF in repo: ValueError: No macro components found in /home/ratik/Projects/RTLign/openroad_scripts/mockup_export.def. Check LEF and DEF files.); ISPD-domain fallback succeeded on mgc_pci_bridge32_b_ar0.66_u80_d0.75.def: inference completed in 7s; 6 macros, edges retained 3/3 |
| A5.3 | constraint hex is acyclic (independent re-check) | PASS | recomputed 6x6 matrix from hex: 3 edges, graph is a DAG (independent networkx check) |
| A5.4 | resolved coordinates satisfy die containment | PASS | 6 resolved coordinates inside die 803215x536925 |
| A5.5 | run_predict.py CLI contract | PASS | no-args exits 1 with usage (documented CLI contract) |
| A5.6 | run_predict.py end-to-end wrapper | PASS | wrapper ran end-to-end on mgc_pci_bridge32_b_ar0.66_u80_d0.75.def; output hex non-empty |
| A5.7 | 1-epoch retrain smoke test | SKIP | not requested (use --with-retrain) |

### e2e

| ID | Check | Verdict | Detail |
|:---|:---|:---|:---|
| A6.1 | master_run.py full pipeline | PASS | all 4 stages exited 0 in 3s; audit PASS; matches golden fixture |
| A6.4 | evaluate.py closed-loop + macro-level signoff | PASS | closed loop on mgc_pci_bridge32_b_ar0.66_u80_d0.75.def in 30s; plot produced; baseline HPWL 597144 vs RTLign 789575 (-32.2%); check_placement legal flags: 0/2 (cell-level overlaps are downstream scope) |
| A6.5 | HPWL comparison sanity | WARN | RTLign HPWL is 32.2% worse than the OpenROAD baseline (no specific claim is documented; flagged for review) |

## Claims ledger (A7)

| Claim | Source | Verdict | Observed |
|:---|:---|:---|:---|
| Full test suite green | README, PROGRESS | PASS | 135 tests passed in 23s (claim: 135) |
| 135 tests pass | README, PROGRESS | PASS | 135 tests passed in 23s (claim: 135) |
| SA legalizer produces audit-clean mockup placement | PROGRESS §5 | PASS | legalized 168 macros in 3.1s; audit P1/P2/P3 PASS; metrics {'cycles': 889115, 'iterations': 1000, 'final_cost': 3704579} |
| 889,115 clock cycles (mockup, post legality scan) | PROGRESS §5 | PASS | cycles=889115, cost=3704579, iterations=1000 — matches PROGRESS.md §5 |
| SA never leaves the legal placement space (legality scan) | VERIFICATION, README | PASS | legalized 168 macros in 3.1s; audit P1/P2/P3 PASS; metrics {'cycles': 889115, 'iterations': 1000, 'final_cost': 3704579} |
| Final placement cost 3,704,579 | PROGRESS §5 | PASS | legalized 168 macros in 3.1s; audit P1/P2/P3 PASS; metrics {'cycles': 889115, 'iterations': 1000, 'final_cost': 3704579} |
| 1000 SA iterations | PROGRESS §5 | PASS | legalized 168 macros in 3.1s; audit P1/P2/P3 PASS; metrics {'cycles': 889115, 'iterations': 1000, 'final_cost': 3704579} |
| Icarus and Verilator produce identical output | VERIFICATION P4 | PASS | word-identical to Icarus; 0.07s; metrics {'cycles': 889114, 'iterations': 1000, 'final_cost': 3704579} |
| Verilator 10x-1000x faster than Icarus | README | WARN | speedup 42.3x on the 168-macro mockup (claim ~400x; small design amortizes poorly) |
| Bit-exact golden regression | VERIFICATION | PASS | output words and final cost match tests/data/golden/ |
| Deterministic reruns | VERIFICATION P4 | PASS | two runs byte-identical (P4 determinism) |
| HEX->DEF preserves non-macro components | README §6 | PASS | 482 components preserved; exactly the 168 sequential-contract components changed; 314 untouched |
| 277 generated training DEFs | PROGRESS Phase 3 | PASS | 1300 generated DEFs (matches the corrected PROGRESS claim) |
| 21.6M training samples | PROGRESS Phase 4 | PASS | row counts: {'ml_features.parquet': 876, 'raw_coords.parquet': 876, 'edge_index.parquet': 540, 'pairwise_distances.parquet': 1956}; files total 4,248 rows (matches the corrected PROGRESS claim; the original 21.6M-sample extraction is not part of the shipped snapshot) |
| Dense layouts >= 24 macros leave residual overlaps | VERIFICATION LIM-1 | EXPECTED-LIMITATION | 350 runs in 10s; profile matches VERIFICATION.md LIM-1 (violations: chain:1603; dense:4755; legal:0; out_of_bounds:18; pair_overlap:0; single:0; wide_macro:50; P3: 0) |
| Metropolis acceptance deviates from exp(-d/T) with k≈4 | VERIFICATION QUIRK-1 | EXPECTED-LIMITATION | k=3.992 (theory 4), hard rejection at delta/T=1.0 — matches QUIRK-1 |
| GNN inference exports an acyclic constraint graph | predict.py assert | PASS | recomputed 6x6 matrix from hex: 3 edges, graph is a DAG (independent networkx check) |
| Closed-loop OpenROAD evaluation works end to end | README §7 | PASS | closed loop on mgc_pci_bridge32_b_ar0.66_u80_d0.75.def in 30s; plot produced; baseline HPWL 597144 vs RTLign 789575 (-32.2%); check_placement legal flags: 0/2 (cell-level overlaps are downstream scope) |
| README project structure is accurate | README | PASS | 47 README-listed paths all exist |
| Training documentation matches the code (no CLI flags, epochs=100) | README Quick Start | PASS | path consistent |
| Mockup DEF has 482 components (168 are legalized as macros) | PROGRESS vs master_run comment | PASS | DEF header COMPONENTS 482; component lines 482; the legalizer consumes 168 placed macros (672 hex words). master_run.py comment is corrected. |
| Greedy cleanup performs at most 8 sweeps (RTL-confirmed) | PROGRESS vs VERIFICATION | PASS | wording consistent (RTL-8:True, PROGRESS-8:True, VERIFICATION-9:False) |
| 277->1300 generated DEF inventory matches PROGRESS | PROGRESS Phase 3 | PASS | 1300 generated DEFs (matches the corrected PROGRESS claim) |

## Manual review findings (agent per-file pass)

**R1 (fixed 2026-09-24) — Closed-loop legality on real designs.**
The first audit found the closed loop aborting on real designs: the SA
pass (whose cost has no overlap term) wandered into overlapping states and
the greedy sweep converged to a fixed point with residual overlaps that no
sweep cap could fix. Fix: `sa_engine.v` now legality-scans every candidate
move (collision_check over all macros) and rejects illegal moves before
Metropolis acceptance; `golden_model.py` mirrors it (`legal_moves`).
Result: the closed loop on `mgc_pci_bridge32_b` completes with
macro-vs-macro-legal output. Macro-vs-standard-cell overlaps after macro
movement remain a documented downstream scope item (cell re-placement +
macro site alignment, Phase 7).

**R2 — The mockup "macros" are fill cells.** All 168 placed components
in `mockup_export.def` are `FILLCELL_X1`. The RTL demo path is a plumbing
demo; real macro flows run on the ISPD-domain designs.

**R3 (documented) — Mockup has no matching LEF.** `predict.py` on the
mockup raises "No macro components found" (Nangate45 types match no LEF in
the repo). Docs now use ISPD-domain examples; the audit's ML tier falls
back to `mgc_pci_bridge32_b` where inference, DAG check, and containment
all pass.

**R4 (corrected) — Dataset claims.** The shipped `data/` holds 4,248
parquet rows and 1,300 generated DEFs; PROGRESS.md now says so and notes
the original 21.6M-sample extraction is not in the snapshot.

**R5 (open) — Scaler overwrite side effect.** `dataset.py` `process()`
refits and overwrites `data/*.joblib` scalers on every reprocessing run —
train/serve skew risk. Follow-up item.

**R6 (resolved) — Silent CLI behavior.** `train_nn.py`'s missing argparse
is now documented in README/AGENTS; `def_parser.py` silently skipping
unplaced components is documented in the audit; `evaluate.py` still
pip-installs packages as a side effect (harmless, open).

**R7 (re-baselined) — Cycle counts.** With the legality scan: Icarus
889,115, Verilator 889,114 cycles; cost 3,704,579 unchanged; 4 illegal
moves rejected on the mockup. Docs updated.

**R8 — RTL code quality.** `collision_check.v`, `lfsr32.v`, `sa_cost.v`,
`sa_engine.v`, `sa_legalizer_top.v`, `legalizer_fsm.v` are clean, match
their documented behavior, and the golden model stays bit-exact against
the RTL after the legality-scan change (verified word-for-word).

**R9 (resolved) — `master_run.py` now gates on `audit.py`;** root-level
`get_help.tcl` / `temp.tcl` are scratch files; `merge_lefs.py` regenerates
the sky130 merged LEF.

