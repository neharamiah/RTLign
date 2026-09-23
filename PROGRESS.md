# RTLign — Project Progress Document

**Project:** ML-Assisted Simulated Annealing for RTL-Accelerated VLSI Macro Placement  
**Team:** P124 — K Sahana, Ratik Agrawal, Neha Ramiah  
**Mentor:** Dr. Krupa Rasane  
**Last Updated:** September 2026  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Repository Structure](#2-repository-structure)
3. [Development Timeline](#3-development-timeline)
4. [Component Deep-Dives](#4-component-deep-dives)
   - 4.1 [Collision Check Module](#41-collision-check-module-collision_checkv)
   - 4.2 [LEF Parser](#42-lef-parser-lef_parserpy)
   - 4.3 [DEF Parser](#43-def-parser-def_parserpy)
   - 4.4 [Legalizer FSM](#44-legalizer-fsm-legalizer_fsmv)
   - 4.5 [Legalizer Testbench](#45-legalizer-testbench-legalizer_tbv)
   - 4.6 [HEX → DEF Injector](#46-hex--def-injector-hex_to_defpy)
   - 4.7 [Master Orchestrator](#47-master-orchestrator-master_runpy)
   - 4.8 [Testing Suite](#48-testing-suite-tests-and-property-tests)
   - 4.9 [OpenROAD Placement Script](#49-openroad-placement-script-openroad_scriptsrun_placementtcl)
   - 4.10 [Feature Extractor](#410-feature-extractor-ml_predictorfeature_extractorpy)
   - 4.11 [GNN Dataset Loader](#411-gnn-dataset-loader-ml_predictordatasetpy)
   - 4.12 [Topological GNN Model](#412-topological-gnn-model-ml_predictormodelpy)
   - 4.13 [GNN Training Pipeline](#413-gnn-training-pipeline-ml_predictortrain_nnpy)
   - 4.14 [Inference Engine & DAG Cycle-Breaker](#414-inference-engine--dag-cycle-breaker-ml_predictorpredictpy--run_predictpy)
   - 4.15 [Evaluation Suite & OpenROAD Signoff](#415-evaluation-suite--openroad-signoff-ml_predictorevaluatepy--openroad_scriptsevaluate_layouttcl)
   - 4.16 [SA Hardware Engine & Cost Function](#416-sa-hardware-engine--cost-function-sa_enginev-sa_costv-lfsr32v)
   - 4.17 [Verilator C++ Simulation Bridge](#417-verilator-c-simulation-bridge-verilatorsa_harnesscpp)
   - 4.18 [Layout Auditor](#418-layout-auditor-rtl_legalizerauditpy)
   - 4.19 [Cycle-Accurate Python Golden Model](#419-cycle-accurate-python-golden-model-rtl_legalizergolden_modelpy)
   - 4.20 [Synthetic Layout Generator & Sweeps](#420-synthetic-layout-generator--sweeps-layout_genpy-scripts)
5. [Simulation & Evaluation Results](#5-simulation--evaluation-results)
6. [Known Limitations](#6-known-limitations)
7. [Roadmap — What's Next](#7-roadmap--whats-next)

---

## 1. Project Overview

During the physical design phase of VLSI development, **macro placement** is an NP-hard optimization problem heavily bottlenecked by sequential CPU calculations. Suboptimal placement degrades a chip's Power, Performance, and Area (PPA) metrics.

**RTLign** addresses this by acting as a drop-in heterogeneous accelerator. We hijack the standard EDA flow, replacing the traditional software macro placer with:

1. **A high-speed ML Predictor (GNN)** — infers relative topological relationships (L-flows) from a `.def` file
2. **A deterministic RTL Hardware Legalizer** — resolves overlaps in custom Verilog hardware using parallel AABB collision detection
3. **A Python orchestrator** — wires everything together and reinjects results into OpenROAD

### Pipeline Diagram

```
┌──────────────────┐      ┌───────────────────┐      ┌─────────────────────┐      ┌──────────────────┐
│    OpenROAD      │      │   ML Predictor    │      │   RTL Legalizer     │      │    OpenROAD      │
│                  │      │                   │      │                     │      │                  │
│  Synthesize &    │─────▶│  def_parser.py    │─────▶│  collision_check.v  │─────▶│  hex_to_def.py   │
│  Export .def     │      │  predict.py (GNN) │      │  legalizer_fsm.v    │      │  .hex → .def     │
│                  │      │  DEF → .hex       │      │  legalizer_tb.v     │      │  Route + STA     │
└──────────────────┘      └───────────────────┘      └─────────────────────┘      └──────────────────┘
```

### Technology Stack

| Category | Tool / Language |
|:---|:---|
| RTL Design | Verilog HDL / SystemVerilog |
| RTL Simulation | Icarus Verilog (`iverilog` + `vvp`) & Verilator (C++ simulation) |
| Scripting & ML | Python 3.x, PyTorch, PyTorch Geometric |
| EDA Suite | OpenROAD (with GUI, RePlAce, DPL, STA) |
| Target PDK | FreePDK45, Nangate45 |
| Benchmark Designs | GCD, ISPD 2015, Ibex, PicoRV32, OpenTitan |
| Version Control | Git / GitHub |

---

## 2. Repository Structure

```
RTLign/
├── orchestration/
│   ├── master_run.py               # Single-click baseline pipeline orchestrator
│   ├── data_generator.py           # Automated OpenROAD placement dataset generator
│   ├── generate_rtl_dataset.py     # Yosys synthesis for RTL designs
│   └── rtl_to_def.py               # Floorplan DEF generator from gate netlists
│
├── ml_predictor/
│   ├── dataset.py                  # PyTorch Geometric InMemoryDataset loader
│   ├── model.py                    # Topological GNN with spatial convolutions
│   ├── train_nn.py                 # Supervised GNN training pipeline
│   ├── predict.py                  # Inference engine + DFS DAG cycle-breaker
│   ├── evaluate.py                 # End-to-end evaluation runner and plotter
│   ├── feature_extractor.py        # High-throughput DEF → Parquet extractor
│   ├── def_parser.py               # DEF + LEF → HEX coordinate extractor
│   └── hex_to_def.py               # HEX → DEF coordinate injector
│
├── rtl_legalizer/
│   ├── sa_legalizer_top.v          # Top-level SA + greedy legalizer
│   ├── sa_engine.v                 # Simulated Annealing optimizer FSM
│   ├── sa_cost.v                   # 3-term hardware cost (HPWL, area, boundary)
│   ├── lfsr32.v                    # 32-bit Galois LFSR pseudo-random generator
│   ├── collision_check.v           # Combinational AABB overlap detector
│   ├── legalizer_fsm.v             # FSM-based greedy sweep legalizer
│   ├── legalizer_tb.v              # Testbench with full audit checks
│   ├── audit.py                    # Layout auditor (zero overlaps, bounds, sizes)
│   ├── golden_model.py             # Bit-exact cycle-accurate Python golden model
│   ├── layout_gen.py               # Synthetic layout generator for stress testing
│   ├── lef_parser.py               # LEF → Dimension Dictionary extractor
│   ├── lef_parser_test.py          # Unit tests for LEF parser
│   ├── lef_parser_property_test.py # Property-based tests for LEF parser
│   ├── tb_*.v                      # Directed Verilog unit testbenches
│   ├── VERIFICATION.md             # Formal verification report and audit results
│   └── verilator/                  # C++ simulation harness and Python bridge
│
├── openroad_scripts/
│   ├── run_placement.tcl           # OpenROAD placement flow script for dataset generation
│   ├── evaluate_layout.tcl         # OpenROAD placement legality & HPWL metric script
│   ├── generate_ibex_floorplan.tcl # Floorplan generator for Ibex core
│   ├── mockup_export.def           # Baseline GCD design (FreePDK45, 482 components)
│   └── legalized_export.def        # Legalized placement output DEF
│
├── scripts/
│   ├── sweep_legalizer.py          # Bug-hunt sweep over 350 layout configurations
│   └── characterize_metropolis.py  # Metropolis LUT characterization script
│
├── tests/
│   ├── test_audit.py               # Tests for layout auditor and generator
│   ├── test_golden_model.py        # Golden model vs RTL equivalence tests
│   ├── test_phase6_verification.py # Cross-simulator determinism and golden regressions
│   ├── test_unit_tbs.py            # Directed Verilog unit testbench runners
│   ├── test_phase6_sa.py           # SA engine and Verilator bridge tests
│   ├── test_phase5_integration.py  # GNN prediction and DEF injection tests
│   ├── test_ispd2015_integration.py # Integration testing on real ISPD benchmarks
│   ├── test_lef_parser_cli.py      # Command Line Interface tests
│   └── data/golden/                # Golden regression test fixtures
│
├── conftest.py                     # Root pytest import configuration
├── run_predict.py                  # Top-level prediction orchestrator with auto-detection
├── topological_gnn_model.pth       # Trained Topological GNN weights
├── data/                           # Training datasets and raw benchmarks
├── README.md                       # Project README
├── ROADMAP.md                      # Comprehensive 6-month roadmap
└── PROGRESS.md                     # This document
```

---

## 3. Development Timeline

### Phase 1: Proof of Concept — End-to-End Pipeline (Commits `3b1c5da` → `7dc9944`)
- Implemented baseline greedy push-apart legalizer in Verilog.
- Verified collision detection and basic DEF injection into OpenROAD.
- Validated on GCD benchmark layout.

### Phase 2: Dimension Accuracy & Scalability (Commits `897a44f` → `9557fc9`)
- Replaced hardcoded dimensions with dynamic `.lef` extraction via `lef_parser.py`.
- Corrected unit scaling from microns to Database Units (DBU).
- Resolved aspect-ratio clamping bugs in the Verilog FSM.

### Phase 3: Robust Testing & Dataset Preparation (Commits `ba8af81` → `ee64e51`)
- **Robust Testing Infrastructure:** Added property-based tests via Hypothesis (`rtl_legalizer/lef_parser_property_test.py`) to verify dimension parsing properties. Created CLI tests (`tests/test_lef_parser_cli.py`) and full integration tests (`tests/test_ispd2015_integration.py`) on real ISPD 2015 benchmarks.
- **OpenROAD Batch Placement Script:** Developed `openroad_scripts/run_placement.tcl` to drive OpenROAD's RePlAce global placement and detailed legalization engines with custom seeds and densities.
- **Dataset Generation Orchestrator:** Wrote `orchestration/data_generator.py` utilizing Python's `ThreadPoolExecutor` for multi-threaded dataset generation across 22 ISPD benchmarks under varying aspect ratios, utilizations, and target densities.
- **Generated Data:** Evaluated 792 configurations; yielded 277 completed layout DEFs (113 Legal, 164 with minor overlap).

### Phase 4: ML Feature Extraction (Completed)
- **Feature Extractor Development:** Wrote `ml_predictor/feature_extractor.py` to systematically parse the hundreds of generated `.def` files and their entries in `dataset_summary.csv`.
- **Large-scale Parsing:** Extracted node features, raw coordinates, 14-channel edge connectivity, and pairwise distances into 4 snappy-compressed Parquet datasets (`ml_features.parquet`, `raw_coords.parquet`, `edge_index.parquet`, `pairwise_distances.parquet`) representing over 21.6 million samples.

### Phase 5: ML Predictor & Evaluation Suite (Completed)
- **GNN Dataset Loader:** Implemented `ml_predictor/dataset.py` to convert Parquet feature tables into PyTorch Geometric `Data` graphs with training/validation splits.
- **Topological GNN Model:** Implemented `ml_predictor/model.py` and `ml_predictor/train_nn.py` to train a supervised model that predicts normalized pairwise macro displacements (L-flows $\Delta x, \Delta y$) from netlist graph connectivity. Checkpoint saved as `topological_gnn_model.pth`.
- **Hardware Handoff Bridge:** Created `ml_predictor/predict.py` with a cycle-breaking DFS algorithm to enforce a strict Directed Acyclic Graph (DAG) and export an $N \times N$ 32-bit hex matrix for hardware initialization. Added top-level `run_predict.py` for automated one-click inference.
- **Evaluation Orchestrator & OpenROAD Signoff:** Implemented `ml_predictor/evaluate.py` and `openroad_scripts/evaluate_layout.tcl` to benchmark the ML+RTL pipeline against native OpenROAD placement, verify physical legality, measure HPWL wirelength, and produce side-by-side layout comparison plots (`evaluation_plot.png`).

### Phase 6: Simulated Annealing in RTL & Formal Verification (Completed)
- **SA Engine in Verilog:** Built `sa_engine.v` implementing stochastic simulated annealing with exponential cooling, coordinate perturbation, and 16-bit LUT Metropolis acceptance.
- **LFSR Pseudo-Random Generator:** Built `lfsr32.v` using a 32-bit Galois LFSR with maximal-length polynomial ($x^{32} + x^{22} + x^2 + x + 1$) and non-zero lockup avoidance.
- **3-Term Hardware Cost Function:** Built `sa_cost.v` to compute wirelength (HPWL), bounding box area, and boundary violation penalties with configurable integer weights.
- **Greedy Cleanup Hardening:** Hardened `legalizer_fsm.v` by bounding resolve loops with `MAX_RESOLVE_TRIES` to eliminate hang risks and fixed unsigned pointer underflow on single-macro designs.
- **Integrated Legalizer Top:** Built `sa_legalizer_top.v` coordinating Pass 1 (SA optimization) and Pass 2 (deterministic greedy cleanup).
- **Verilator Simulation Bridge:** Developed `verilator/sa_harness.cpp` with parametric compile flags (`NUM_LINES`, `DIE_WIDTH`, `DIE_HEIGHT`) and Python wrapper, delivering ~400× speedup over interpreted simulation.
- **Cycle-Accurate Golden Model:** Implemented `rtl_legalizer/golden_model.py` replicating RTL arithmetic, LFSR sequence, Metropolis LUT, and boundary handling for exact word-by-word equivalence.
- **Layout Auditor & Verification Suite:** Built `rtl_legalizer/audit.py` to audit P1 (overlaps), P2 (die containment), and P3 (size preservation). Created 135 passing tests across unit testbenches, determinism, cross-simulator equivalence, and golden regressions.

---

## 4. Component Deep-Dives

### 4.1 Collision Check Module (`collision_check.v`)
**Purpose:** Pure combinational logic that tests whether two axis-aligned bounding boxes overlap.  
**Logic:** Computes right and top edges for both macros, asserting `overlap` if and only if `x1 < right2 && right1 > x2 && y1 < top2 && top1 > y2`.

---

### 4.2 LEF Parser (`lef_parser.py`)
**Purpose:** Extracts actual macro dimensions (Width, Height) from an OpenROAD `.lef` library file, converting from microns to DEF database units (DBU).

---

### 4.3 DEF Parser (`def_parser.py`)
**Purpose:** Extracts macro placement coordinates and matches them with LEF dimensions, writing them as a flat `.hex` memory file for the Verilog legalizer.

---

### 4.4 Legalizer FSM (`legalizer_fsm.v`)
**Purpose:** Sequentially audits all macro pairs. When an overlap is detected, it calculates horizontal and vertical overlaps and pushes Macro B along the axis of minimum overlap, with boundary clamping.

---

### 4.5 Legalizer Testbench (`legalizer_tb.v`)
**Purpose:** Drives the legalizer FSM, measures cycle count, dumps `output_layout.hex` via `$writememh`, audits all $N(N-1)/2$ pairs for zero residual overlaps, and generates waveform dumps (`legalizer.vcd`).

---

### 4.6 HEX → DEF Injector (`hex_to_def.py`)
**Purpose:** Reads the legalized `.hex` coordinates and patches them back into the original `.def` file. Supports targeted name-based macro injection from comments (`// X <inst_name>`) as well as sequential matching fallback, preserving pins, standard cells, and routing.

---

### 4.7 Master Orchestrator (`master_run.py`)
**Purpose:** Single-command Python orchestrator linking DEF parsing, Verilog compilation (`iverilog`), simulation (`vvp`), and DEF injection.

---

### 4.8 Testing Suite (`tests/` and property tests)
**Purpose:** Unit tests, Hypothesis property-based tests for LEF scaling invariants, and full integration tests executing on ISPD 2015 benchmarks.

---

### 4.9 OpenROAD Placement Script (`openroad_scripts/run_placement.tcl`)
**Purpose:** Programmatic OpenROAD TCL script running global placement (RePlAce) and detailed placement (`dpl`) to generate diverse layouts across parameter sweeps.

---

### 4.10 Feature Extractor (`ml_predictor/feature_extractor.py`)
**Purpose:** Ingests placed `.def` layouts and extracts cell attributes, node coordinates, pin counts, 14-channel edge connectivity vectors, and pairwise distance tables into high-performance Parquet format.

---

### 4.11 GNN Dataset Loader (`ml_predictor/dataset.py`)
**Purpose:** Ingests the Parquet datasets into PyTorch Geometric `Data` graphs. Handles node normalization, 14-channel edge conditioning, and train/val splitting for topological learning.

---

### 4.12 Topological GNN Model (`ml_predictor/model.py`)
**Purpose:** Implements `TopologicalGNN` and `SpatialEdgeConv`. Uses graph message passing conditioned on routing connectivity to infer relative spatial topological constraints ($\Delta x, \Delta y$).

---

### 4.13 GNN Training Pipeline (`ml_predictor/train_nn.py`)
**Purpose:** Trains `TopologicalGNN` with MSE and Smooth L1 objectives against ground-truth OpenROAD placements, optimizing network weights and saving `topological_gnn_model.pth`.

---

### 4.14 Inference Engine & DAG Cycle-Breaker (`ml_predictor/predict.py` & `run_predict.py`)
**Purpose:** Executes inference on unseen DEF layouts. Employs a Depth-First Search (DFS) cycle-breaking algorithm to eliminate topological loops, ensuring the relative macro dependencies form a strict Directed Acyclic Graph (DAG). Includes a topological coordinate resolver (`resolve_topological_coordinates`) to convert DAG constraints and LEF dimensions into hardware coordinates (`dummy_layout.hex`) with area-based macro filtering.

---

### 4.15 Evaluation Suite & OpenROAD Signoff (`ml_predictor/evaluate.py` & `openroad_scripts/evaluate_layout.tcl`)
**Purpose:** Runs the complete closed-loop pipeline: GNN inference → topological resolution → parameterized RTL legalization (`iverilog`) → targeted DEF injection → OpenROAD re-import. Measures placement legality (`check_placement`), calculates pre-route HPWL via direct OpenROAD database net traversal (`[ord::get_db_block] getNets`), and exports dual layout visualization figures (`evaluation_plot.png`).

---

### 4.16 SA Hardware Engine & Cost Function (`sa_engine.v`, `sa_cost.v`, `lfsr32.v`)
**Purpose:** Implements Pass 1 of the hardware legalizer. `sa_engine.v` controls stochastic hill-climbing using exponential cooling and a 16-bit lookup-table Metropolis acceptance rule. `lfsr32.v` provides high-entropy 32-bit pseudo-random numbers via a Galois LFSR ($x^{32} + x^{22} + x^2 + x + 1$). `sa_cost.v` evaluates a 3-term objective combining HPWL wirelength, bounding box area, and boundary penalties.

---

### 4.17 Verilator C++ Simulation Bridge (`verilator/sa_harness.cpp`)
**Purpose:** Accelerates hardware simulation by compiling synthesizable Verilog into native C++ binaries. Provides ~400× speedup over interpreted simulation, enabling hundreds of thousands of annealing cycles in milliseconds. Supports parameterized builds via make variables (`NUM_LINES`, `DIE_WIDTH`, `DIE_HEIGHT`).

---

### 4.18 Layout Auditor (`rtl_legalizer/audit.py`)
**Purpose:** Serves as the single source of truth for post-legalization validation. Audits layout hex files against three core physical properties:
- **P1 Zero Overlaps:** Strict AABB intersection test over all macro pairs.
- **P2 Die Containment:** $0 \le x$, $x + w \le \text{DIE\_WIDTH}$, and the same for $y$.
- **P3 Size Preservation:** Output width and height match input dimensions exactly.

---

### 4.19 Cycle-Accurate Python Golden Model (`rtl_legalizer/golden_model.py`)
**Purpose:** Bit-exact software replica of the Verilog hardware pipeline. Models 32-bit wraparound arithmetic, Galois LFSR sequences, Metropolis LUT evaluation, boundary reflection, and greedy push resolution to cross-check RTL output word-for-word.

---

### 4.20 Synthetic Layout Generator & Sweeps (`layout_gen.py`, `scripts/`)
**Purpose:** Generates synthetic stress layouts across 7 modes (single, legal, pair overlap, chain, dense, out of bounds, wide macro). Evaluates convergence across 350 randomized layout sweeps (`scripts/sweep_legalizer.py`) and characterizes Metropolis probability distributions (`scripts/characterize_metropolis.py`).

---

## 5. Simulation & Evaluation Results

### Baseline Pipeline Execution
```
╔══════════════════════════════════════════════════════════╗
║         RTLign Co-Design Pipeline — Master Run           ║
╚══════════════════════════════════════════════════════════╝

  [1/3] DEF → HEX Parser              ✅  0.02s
  [2a/3] Compile Verilog (iverilog)    ✅  0.01s
  [2b/3] Run RTL Legalizer (vvp)      ✅  0.18s
  [3/3] HEX → DEF Injector            ✅  0.02s

╔══════════════════════════════════════════════════════════╗
║              Pipeline Complete!                          ║
╚══════════════════════════════════════════════════════════╝
  Total time:  0.22s
```

### Legalizer Hardware & Verification Metrics
| Metric | Icarus Verilog | Verilator Bridge | Golden Model |
|:---|:---|:---|:---|
| Macros Evaluated | 168 | 168 | 168 |
| Clock Cycles | 724,110 | 724,111 | N/A (cycle-accurate) |
| SA Iterations | 1,000 | 1,000 | 1,000 |
| Accepted Moves | 1,000 | 1,000 | 1,000 |
| Final Placement Cost | 3,704,579 | 3,704,579 | 3,704,579 |
| Bit-Exact Equivalence | Match | Match | Match |
| Test Suite Coverage | **135 / 135 passing** | **135 / 135 passing** | **135 / 135 passing** |
| Post-Run Audit Status | **PASS (P1, P2, P3)** | **PASS (P1, P2, P3)** | **PASS (P1, P2, P3)** |

### ML Predictor & Evaluation Artifacts
- **Model Checkpoint:** `topological_gnn_model.pth` (PyTorch Geometric weights trained on Parquet datasets).
- **Inference Visualization:** `gnn_prediction_visualization.png` and `evaluation_output/evaluation_plot.png` comparing baseline vs. RTLign macro layouts.
- **Legality Verification:** Passed via OpenROAD `check_placement -verbose` within `evaluate_layout.tcl`.

---

## 6. Known Limitations

### Current Limitations & Verified Boundaries (from `VERIFICATION.md`)

| # | Limitation | Impact | Status / Documentation |
|:---|:---|:---|:---|
| 1 | **Greedy sweep pass cap (8 passes)** | Dense clusters of 24+ overlapping macros may leave residual overlaps | Documented in `VERIFICATION.md`. Hardened with `$fatal` audit in testbench. |
| 2 | **Macro width exceeding die width** | Macros with width > `DIE_WIDTH` cannot satisfy containment P2 | Documented boundary limitation. Clamped to $x = 0$. |
| 3 | **Slow sequential simulation in Icarus** | Interpreted simulation runs in seconds | Resolved via Verilator C++ simulation bridge (~400× speedup). |
| 4 | **Single-macro FSM underflow** | $N=1$ macro designs previously hung greedy FSM | Resolved: corrected pointer underflow logic `(ptr_a + 4) < last_base`. |

---

## 7. Roadmap — What's Next

### Month 1: Foundations & Dataset Generation
- **[DONE]** Build: LEF Parser & Real Dimensions (Extract real cell widths/heights, convert dimensions, fix legalizer bugs)
- **[DONE]** Build: Dataset Generation Pipeline (`run_placement.tcl` batch script and `data_generator.py` wrapper completed)

### Month 2: Supervised ML Predictor & Evaluation
- **[DONE]** Build: GNN Topological Predictor Baseline (Feature extraction, train GNN, infer L-flows, evaluate HPWL)
- **[DONE]** Build: Advanced GNN Predictor & Inference (`dataset.py`, `model.py`, `train_nn.py`, `predict.py`, `run_predict.py`)
- **[DONE]** Build: Evaluation Suite & OpenROAD Signoff (`evaluate.py`, `evaluate_layout.tcl`, layout visualization)

### Month 3: Simulated Annealing in RTL & Verification
- **[DONE]** Build: SA Engine in Verilog (`lfsr32.v`, `sa_cost.v`, `sa_engine.v`, `sa_legalizer_top.v`, Metropolis acceptance, step cooling)
- **[DONE]** Build: SA Testbench & Validation (`legalizer_tb.v`, multi-pass cascade resolution, audit assertions)
- **[DONE]** Build: Verilator Bridge (`verilator/sa_harness.cpp`, `Makefile`, parameterized builds, ~400× speedup)
- **[DONE]** Build: Formal Verification Suite (`audit.py`, `golden_model.py`, `layout_gen.py`, `VERIFICATION.md`, 135 passing tests)

### Month 4: Integration, Scaling & Benchmarking
- Build: Full Benchmarking Suite (Run on ISPD 2015, OpenROAD re-import, routing & STA, compile metrics)
