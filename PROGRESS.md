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
| RTL Simulation | Icarus Verilog (`iverilog` + `vvp`) |
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
│   ├── collision_check.v           # Combinational AABB overlap detector
│   ├── legalizer_fsm.v             # FSM-based greedy sweep legalizer
│   ├── legalizer_tb.v              # Testbench with overlap audit
│   ├── lef_parser.py               # LEF → Dimension Dictionary extractor
│   ├── lef_parser_test.py          # Unit tests for LEF parser
│   ├── lef_parser_property_test.py # Property-based tests for LEF parser
│   ├── dummy_layout.hex            # Input macro layout (generated)
│   └── output_layout.hex           # Legalized layout coordinates (generated)
│
├── openroad_scripts/
│   ├── run_placement.tcl           # OpenROAD placement flow script for dataset generation
│   ├── evaluate_layout.tcl         # OpenROAD placement legality & HPWL metric script
│   ├── generate_ibex_floorplan.tcl # Floorplan generator for Ibex core
│   ├── mockup_export.def           # Baseline GCD design (FreePDK45, 482 components)
│   └── legalized_export.def        # Legalized placement output DEF
│
├── tests/
│   ├── __init__.py
│   ├── test_ispd2015_integration.py # Integration testing on real ISPD benchmarks
│   └── test_lef_parser_cli.py      # Command Line Interface tests
│
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

### Legalizer Hardware Simulation Metrics
| Metric | Value |
|:---|:---|
| Number of macros | 168 |
| Clock cycles to legalize | 42,086 |
| Simulated clock frequency | 100 MHz |
| Theoretical hardware latency | 0.42 ms |
| Overlaps after legalization | **0** (AUDIT PASS) |
| Coordinates injected into DEF | 168 / 168 |

### ML Predictor & Evaluation Artifacts
- **Model Checkpoint:** `topological_gnn_model.pth` (PyTorch Geometric weights trained on Parquet datasets).
- **Inference Visualization:** `gnn_prediction_visualization.png` and `evaluation_output/evaluation_plot.png` comparing baseline vs. RTLign macro layouts.
- **Legality Verification:** Passed via OpenROAD `check_placement -verbose` within `evaluate_layout.tcl`.

---

## 6. Known Limitations

### Current Limitations & Next Steps

| # | Limitation | Impact | Status / Planned Fix |
|:---|:---|:---|:---|
| 1 | **Greedy sweep, not Simulated Annealing** | Push-apart logic lacks temperature schedule and stochastic hill-climbing | Phase 6: SA engine in Verilog |
| 2 | **No wirelength optimization in RTL** | The baseline legalizer only eliminates overlaps without minimizing HPWL | Phase 6: Cost function in SA |
| 3 | **Sequential pair iteration** | The FSM checks one pair at a time ($N^2/2$ iterations) | Phase 6: Parallel collision units |
| 4 | **OpenROAD re-import verification** | Automated closed-loop re-import verified via `evaluate_layout.tcl` | ✅ Verified in Phase 5 |

---

## 7. Roadmap — What's Next

### Month 1: Foundations & Dataset Generation
- **[DONE]** Build: LEF Parser & Real Dimensions (Extract real cell widths/heights, convert dimensions, fix legalizer bugs)
- **[DONE]** Build: Dataset Generation Pipeline (`run_placement.tcl` batch script and `data_generator.py` wrapper completed)

### Month 2: Supervised ML Predictor & Evaluation
- **[DONE]** Build: GNN Topological Predictor Baseline (Feature extraction, train GNN, infer L-flows, evaluate HPWL)
- **[DONE]** Build: Advanced GNN Predictor & Inference (`dataset.py`, `model.py`, `train_nn.py`, `predict.py`, `run_predict.py`)
- **[DONE]** Build: Evaluation Suite & OpenROAD Signoff (`evaluate.py`, `evaluate_layout.tcl`, layout visualization)

### Month 3: Simulated Annealing in RTL (Active Phase)
- Build: SA Engine in Verilog (LFSR, temperature cooling, perturbation, cost function, Metropolis acceptance)
- Build: SA Testbench & Validation (Monitor cost/temperature, verify on benchmarks, waveform analysis)
- Build: Verilator Bridge (Verilator wrapper, Python ctypes binding, speed benchmarking)

### Month 4: Integration, Scaling & Benchmarking
- Build: Full Benchmarking Suite (Run on ISPD 2015, OpenROAD re-import, routing & STA, compile metrics)
