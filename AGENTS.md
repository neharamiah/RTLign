# RTLign: AI Agent System Architecture & Guidelines

Welcome, AI Agent! This document contains all the necessary steering context and guidelines to work on the RTLign project effectively. Please read this entirely before making modifications.

---

## 1. Product Summary

**Product Overview**
RTLign is an ML-assisted simulated annealing tool for VLSI macro placement that replaces traditional software placers with a heterogeneous hardware-software co-design pipeline. It integrates with the OpenROAD physical design flow to accelerate macro legalization using custom RTL hardware.

**Core Value Proposition**
Traditional macro placement is an NP-hard optimization bottleneck in VLSI physical design. RTLign addresses this by:
- Using a Graph Neural Network (GNN) to predict relative topological relationships (L-flows) between macros
- Resolving these topologies into exact coordinates in parallel hardware (SystemVerilog Simulated Annealing engine via a single-cycle combinational DAG-Solver) instead of sequential CPU calculations
- Maintaining physical design rule compliance through deterministic RTL legalization

**Pipeline Architecture**
```
OpenROAD DEF ──▶ ML Predictor ──▶ RTL Legalizer ──▶ OpenROAD Import
                 (PyTorch GNN)      (Verilog)         (Python / TCL)
```
1. **DEF Parser** - Extracts macro placements from OpenROAD `.def` files
2. **LEF Parser** - Extracts real cell dimensions from library `.lef` files  
3. **ML Predictor** - Topological GNN predicts relative spatial relationships (L-flows) and DFS cycle-breaker guarantees a Directed Acyclic Graph (DAG)
4. **RTL Legalizer** - Custom SystemVerilog Simulated Annealing engine for parallel L-flow resolution via combinational DAG-Solver
5. **HEX→DEF Injector** - Patches legalized coordinates back into DEF files
6. **Evaluation & Signoff** - Verifies legality and measures HPWL in OpenROAD, generating comparison floorplans

**Current Status**
- Phase 1 complete: End-to-end pipeline with temporary greedy sweep legalizer
- Phase 2 complete: Real cell dimension extraction via LEF parser
- Phase 3 complete: Dataset Generation Pipeline and Robust Testing
- Phase 4 complete: ML Feature Extraction (Parquet datasets generated)
- Phase 5 complete: ML Predictor & Evaluation Suite (GNN trained, DAG prediction, hex export, OpenROAD evaluation & plotting implemented)
- Phase 6 planned: Verilog Simulated Annealing engine (RTL legalizer upgrade) and benchmarking

---

## 2. Technology Stack

**Languages**
- **Python 3.x** - Pipeline orchestration, parsing, ML predictor, evaluation
- **Verilog HDL** - RTL legalizer hardware (Simulated Annealing engine / FSM)
- **TCL** - OpenROAD automation scripts (placement, evaluation, metrics)

**Tools & Frameworks**
- **RTL Simulation:** Icarus Verilog (`iverilog`, `vvp`) - Verilog compilation and simulation. Used for legalizer FSM simulation and VCD waveform output for debugging.
- **EDA Tools:** OpenROAD - Physical design suite (GUI, routing, STA). DEF/LEF file import/export, placement visualization, signoff analysis.
- **ML/AI:** PyTorch, PyTorch Geometric (Topological GNN), scikit-learn, pandas, matplotlib.
- **Testing:** pytest (Unit and integration tests), Hypothesis (Property-based testing).

**Build & Run Commands**
*Full Baseline Pipeline:*
```bash
python orchestration/master_run.py
```
*GNN Training:*
```bash
python ml_predictor/train_nn.py --data_dir data/parquet_dataset --epochs 100
```
*GNN Inference & DAG Constraint Export:*
```bash
python run_predict.py
# or directly:
python ml_predictor/predict.py --def_file openroad_scripts/mockup_export.def --lef_file data/cells.lef --model_path topological_gnn_model.pth --output_hex data/macro_rel_constraints.hex
```
*End-to-End Evaluation & Visualization:*
```bash
python ml_predictor/evaluate.py --def_file openroad_scripts/mockup_export.def --tech_lef data/tech.lef --cells_lef data/cells.lef --output_dir evaluation_output
```
*Individual Stages:*
- **LEF Parsing:** `python rtl_legalizer/lef_parser.py data/ispd_benchmarks/ispd2015/hidden/mgc_matrix_mult_2/tech.lef data/ispd_benchmarks/ispd2015/hidden/mgc_matrix_mult_2/cells.lef --verbose`
- **DEF → HEX:** `python ml_predictor/def_parser.py`
- **RTL Legalizer:** `cd rtl_legalizer && iverilog -o sim.out collision_check.v legalizer_fsm.v legalizer_tb.v && vvp sim.out`
- **HEX → DEF:** `python ml_predictor/hex_to_def.py`
- **Testing:** `pytest tests/ rtl_legalizer/`

**Data Formats**
- **DEF:** Component placements, netlist, die area
- **LEF:** Cell dimensions, pin locations, routing layers
- **HEX:** Hardware memory format for Verilog legalizer (4 lines per macro: X, Y, Width, Height) or topological constraint matrix ($N \times N$)
- **Parquet:** Snappy-compressed graph features, connectivity indices, and pairwise relative distances

---

## 3. Project Structure

**Root Directory**
```
RTLign/
├── orchestration/          # Pipeline orchestration scripts
├── ml_predictor/           # ML models, GNN training, prediction, and evaluation
├── rtl_legalizer/          # Verilog RTL legalizer hardware & tests
├── openroad_scripts/       # OpenROAD DEF files and TCL scripts
├── tests/                  # Integration and CLI tests
└── data/                   # Benchmarks and training data (gitignored)
```

**Module Organization**
- **orchestration/**: `master_run.py` (pipeline orchestrator), `data_generator.py` (multi-threaded OpenROAD placement sweeps), `generate_rtl_dataset.py` (Yosys synthesis), `rtl_to_def.py` (floorplan generation).
- **ml_predictor/**: `dataset.py` (PyG dataset loader), `model.py` (Topological GNN), `train_nn.py` (GNN training), `predict.py` (inference & DFS DAG cycle-breaker), `evaluate.py` (OpenROAD HPWL benchmark & layout plotting), `feature_extractor.py` (Parquet extractor), `def_parser.py`, `hex_to_def.py`.
- **rtl_legalizer/**: `collision_check.v`, `legalizer_fsm.v`, `legalizer_tb.v`, `lef_parser.py`, `lef_parser_test.py`, `lef_parser_property_test.py`. Generated: `dummy_layout.hex`, `output_layout.hex`, `sim.out`, `legalizer.vcd`. Key params: `NUM_LINES`=672, `DIE_WIDTH`=200260, `DIE_HEIGHT`=201600.
- **openroad_scripts/**: `run_placement.tcl` (batch placement), `evaluate_layout.tcl` (HPWL & legality verification), `generate_ibex_floorplan.tcl`, `mockup_export.def` (GCD design), `legalized_export.def` (Final output).
- **data/**: Training datasets and benchmarks.

**Data Flow**
```
DEF ──▶ ml_predictor/predict.py ──▶ HEX ──▶ legalizer_fsm.v ──▶ HEX ──▶ hex_to_def.py ──▶ DEF
                ▲                                                                          │
                │                                                                          ▼
      topological_gnn_model.pth                                                     evaluate.py / OpenROAD
```

**File Naming Conventions**
- Python: `snake_case.py`
- Verilog: `snake_case.v`
- Data files: `snake_case.def`, `snake_case.lef`, `snake_case.hex`, `snake_case.parquet`
- Documentation: `UPPERCASE.md`, `README.md`

---

## 4. Agent Operational Guidelines

1. **Test Before Committing:** Always run the full test suite (`pytest tests/ rtl_legalizer/ -v`) to ensure no regressions.
2. **Reproducibility:** Ensure `master_run.py` works seamlessly from the project root after pipeline modifications.
3. **Data Integrity:** Do not check in large `.def`, `.lef`, or output files unless explicitly meant for versioned mocking or openroad integration scripts.
4. **ASD-STE100 Communication Standard:** Use ASD-STE100 (Simplified Technical English) rules for all responses, implementation plans, and documentation (active voice, simple tenses, short sentences ≤ 25 words, no jargon without definition).
5. **Karpathy Coding Guidelines:**

### 1. Think Before Coding
**Don't assume. Don't hide confusion. Surface tradeoffs.**
Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First
**Minimum code that solves the problem. Nothing speculative.**
- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.
Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes
**Touch only what you must. Clean up only your own mess.**
When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.
When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.
The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution
**Define success criteria. Loop until verified.**
Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"
For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```
Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
