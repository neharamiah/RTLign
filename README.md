# RTLign

**Topological Hardware-Software Co-Design for VLSI Macro Legalization**

RTLign is a hardware-software co-design tool that replaces the traditional OpenROAD macro placer with a 4-stage topological pipeline: an ML Predictor (GNN) that infers relative topological relationships (L-flows), a custom Verilog / SystemVerilog Simulated Annealing (SA) engine that resolves these topologies into overlap-free coordinates using a single-cycle combinational DAG-Solver, and a Python orchestrator that wires everything back into the OpenROAD physical design flow.

## Pipeline Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│  OpenROAD    │     │  ML Predictor│     │  SystemVerilog SA│     │  OpenROAD    │
│  DEF & LEF   │────▶│  (GNN L-flows│────▶│  (DAG-Solver)    │────▶│  .def import │
│              │     │  Extraction) │     │  (iverilog/vvp)  │     │  Route + STA │
└──────────────┘     └──────────────┘     └──────────────────┘     └──────────────┘
```

## Scientific Claims & Baselines

- **Hardware Speedup:** We achieve up to 1,800× speedup compared to brute-force baselines. Note that this 1,800× figure from the 2026 Nature baseline represents search step reduction (the algorithmic efficiency of Simulated Annealing over brute-force), not raw clock-to-clock execution speed against software. Our hardware speedup specifically comes from resolving coordinates in a single combinational clock cycle via our custom DAG-Solver, bypassing sequential software pointer-chasing.
- **Power Profile:** RTLign is fully synthesizable on standard silicon. Its power profile will be reported post-synthesis using OpenROAD's power analysis tools. We do not claim the 76.44 nJ energy footprint cited in recent experimental 2D-material CMOS literature.

---

## Quick Start

### Option A: Running with Docker (Recommended for Windows / Teammates)

Using Docker ensures all EDA tools (OpenROAD, Icarus Verilog via OSS CAD Suite) and Python dependencies are isolated and identical across all systems (Windows & Linux).

#### Prerequisites:
- **Windows:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (ensure WSL 2 backend is enabled).
- **Linux:** Install `docker.io` and `docker-compose-v2` (`sudo apt-get install docker.io docker-compose-v2`).

#### Usage:
1. Open the repository in **Antigravity**.
2. **Build the Docker container** (first time only):
   ```bash
   docker compose build
   ```
3. **Run the full pipeline inside Docker:**
   ```bash
   docker compose run --rm rtlign python orchestration/master_run.py
   ```
4. **Run an interactive bash session inside Docker:**
   ```bash
   docker compose run --rm rtlign bash
   ```
5. **Run tests inside Docker:**
   ```bash
   docker compose run --rm rtlign pytest tests/ rtl_legalizer/
   ```
*Note: Any edits you make in Antigravity on your host system are instantly reflected inside the container.*

---

### Option B: Local Environment Setup

#### Prerequisites
- **Python 3.x** (with PyTorch, PyTorch Geometric, pandas, matplotlib)
- **Icarus Verilog** (`iverilog`, `vvp`)
- **OpenROAD** (optional, for GUI visualization, placement generation, and signoff)

#### Run the Baseline Co-Design Pipeline

```bash
# From the RTLign project root
python orchestration/master_run.py
```

This will:
1. Parse LEF dimensions (Implicit in master_run)
2. Parse `openroad_scripts/mockup_export.def` with exact LEF geometries → extract macro coordinates to `rtl_legalizer/dummy_layout.hex`
3. Compile and simulate the Verilog legalizer → produce `rtl_legalizer/output_layout.hex`
4. Inject legalized coordinates back → produce `openroad_scripts/legalized_export.def`

#### Run ML Predictor & Evaluation Flow

```bash
# 1. Train the Topological GNN (requires the Parquet tables in data/)
#    Note: train_nn.py takes no CLI flags; epochs default to 100.
python ml_predictor/train_nn.py

# 2. Run inference & export DAG constraints to hex
python run_predict.py --def_file <placed.def> --lef_file <cells.lef>

# 3. Benchmark pipeline against OpenROAD baseline & visualize layout
#    (any placed DEF whose cell types match the given LEF)
python ml_predictor/evaluate.py \
  --def_file data/generated_defs/mgc_pci_bridge32_b/mgc_pci_bridge32_b_ar1.0_u60_d0.7.def \
  --tech_lef data/ispd_benchmarks/ispd2015/mgc_pci_bridge32_b/tech.lef \
  --cells_lef data/ispd_benchmarks/ispd2015/mgc_pci_bridge32_b/cells.lef \
  --model_path topological_gnn_model.pth \
  --output_dir evaluation_output
```

#### Verification & Test Suite

```bash
# Run the complete test suite (136 tests):
pytest tests/ rtl_legalizer/ -v

# Run the layout auditor (P1: overlaps, P2: die bounds, P3: size preservation):
python rtl_legalizer/audit.py <input.hex> <output.hex>

# Run the 350-case randomized sweep:
python scripts/sweep_legalizer.py

# Run the Metropolis characterization script:
python scripts/characterize_metropolis.py
```

---

## Project Structure

```
RTLign/
├── orchestration/
│   ├── master_run.py          # Single-click pipeline orchestrator
│   ├── data_generator.py      # Automated OpenROAD placement dataset generator
│   ├── generate_rtl_dataset.py # Generates gate-level netlists for RTL designs
│   └── rtl_to_def.py          # Converts RTL to floorplanned DEFs
├── ml_predictor/
│   ├── dataset.py             # PyTorch Geometric dataset loader (Parquet → Graphs)
│   ├── model.py               # Topological GNN with spatial convolutions
│   ├── train_nn.py            # Supervised GNN training script
│   ├── predict.py             # Inference engine with DFS DAG cycle-breaker
│   ├── evaluate.py            # Closed-loop evaluation and plotting script
│   ├── feature_extractor.py   # Extracts features and GNN edge indices to Parquet
│   ├── def_parser.py          # DEF + LEF → HEX coordinate extractor
│   └── hex_to_def.py          # HEX → DEF coordinate injector
├── rtl_legalizer/
│   ├── sa_legalizer_top.v     # Top-level SA + greedy legalizer
│   ├── sa_engine.v            # Simulated Annealing optimizer FSM
│   ├── sa_cost.v              # 3-term hardware cost module (HPWL, area, boundary)
│   ├── lfsr32.v               # 32-bit Galois LFSR pseudo-random generator
│   ├── collision_check.v      # Combinational AABB overlap detector
│   ├── legalizer_fsm.v        # Greedy cleanup FSM with alternating-axis push
│   ├── legalizer_tb.v         # Testbench with full audit checks
│   ├── audit.py               # Layout auditor for zero overlaps, bounds, and sizes
│   ├── golden_model.py        # Bit-exact cycle-accurate Python golden model
│   ├── layout_gen.py          # Synthetic layout generator for stress testing
│   ├── lef_parser.py          # LEF → Dimension Dictionary extractor
│   ├── lef_parser_test.py     # Unit tests for LEF parser
│   ├── lef_parser_property_test.py # Property-based tests for LEF parser
│   ├── tb_*.v                 # Directed Verilog unit testbenches
│   ├── VERIFICATION.md        # Comprehensive verification and audit report
│   └── verilator/             # Fast C++ simulation harness and bridge
├── openroad_scripts/
│   ├── run_placement.tcl      # OpenROAD placement flow script for dataset generation
│   ├── evaluate_layout.tcl    # OpenROAD layout legality & HPWL verification script
│   ├── generate_ibex_floorplan.tcl # Floorplan generator for Ibex RISC-V core
│   ├── mockup_export.def      # Baseline GCD design file
│   └── legalized_export.def   # Output file with legalized coordinates
├── scripts/
│   ├── sweep_legalizer.py     # Bug-hunt sweep over 350 layout configurations
│   └── characterize_metropolis.py # RTL Metropolis acceptance characterization
├── tests/
│   ├── test_audit.py          # Tests for layout auditor and generator
│   ├── test_golden_model.py   # Staged golden model vs RTL equivalence tests
│   ├── test_phase6_verification.py # Cross-simulator determinism and regression tests
│   ├── test_unit_tbs.py       # Directed Verilog testbench runner tests
│   ├── test_phase6_sa.py      # SA engine and Verilator bridge integration tests
│   ├── test_phase5_integration.py # GNN prediction and DEF injection tests
│   ├── test_ispd2015_integration.py # Real benchmark LEF/DEF integration tests
│   ├── test_lef_parser_cli.py # CLI tests for LEF parser
│   └── data/golden/           # Versioned golden regression fixtures
├── conftest.py                # Pytest path configuration
├── run_predict.py             # One-click prediction orchestrator with auto-detection
├── topological_gnn_model.pth  # Trained Topological GNN weights
├── ROADMAP.md                 # 6-Month Comprehensive Roadmap
├── PROGRESS.md                # Project Progress Document
└── data/                      # Training datasets (gitignored)
```

---

## How It Works

### 1. LEF Parser (`lef_parser.py`)
Extracts actual macro dimensions (Width, Height) from an OpenROAD `.lef` library file, converting from microns to DEF database units (DBU) to enable accurate collision detection for non-square geometries.

### 2. Dataset Generator (`data_generator.py`)
Automates OpenROAD (`run_placement.tcl`) to sweep through physical design constraints (e.g., Target Density, Core Utilization, Aspect Ratio). Generates hundreds of `Legal`, `Illegal`, and `Failed` layout variations for machine learning training.

### 3. Feature Extractor (`feature_extractor.py`)
Parses generated DEF layouts to extract structural node features and graph edge indices (14-channel edge feature vectors representing routing connectivity) into Parquet files.

### 4. Topological GNN Training & Inference (`train_nn.py`, `predict.py`)
Trains a Graph Neural Network (`model.py`) to infer pairwise relative topological relationships (L-flows $\Delta x, \Delta y$). The inference engine includes a Depth-First Search (DFS) cycle-breaking algorithm to guarantee a strict Directed Acyclic Graph (DAG) for hardware consumption.

### 5. Two-Pass Hardware Legalizer, Verilator Bridge & Verification
A heterogeneous two-pass placement engine implemented in synthesizable Verilog:
- **Pass 1: Simulated Annealing Optimizer (`sa_engine.v`):** Explores the placement solution space using stochastic hill-climbing, 32-bit Galois LFSR pseudo-random perturbations (`lfsr32.v`), and Metropolis acceptance ($P = e^{-\Delta C / T}$). A built-in legality scan rejects any candidate move that would overlap another macro, so SA never leaves the legal placement space. Minimizes a 3-term cost function (`sa_cost.v`): wirelength (HPWL), bounding box area, and boundary penalties.
- **Pass 2: Deterministic Greedy Cleanup (`legalizer_fsm.v`):** Resolves residual overlaps via axis-of-minimum-overlap push with multi-pass cascade resolution, guaranteeing overlap-free macro layouts for realistic (sparse to moderate) placements. Dense synthetic clusters may retain residual overlaps (see `rtl_legalizer/VERIFICATION.md`, LIM-1).
- **Verilator Simulation Bridge (`verilator/`):** A high-speed C++ simulation harness (`sa_harness.cpp`, `verilator_bridge.py`) delivering 10×–1000× speedup over interpreted simulation depending on design size (the 168-macro mockup measures ~40×; larger designs amortize better).
- **Formal Verification & Auditing (`audit.py`, `golden_model.py`, `VERIFICATION.md`):** Bit-exact Python golden model reproducing RTL arithmetic, automated 3-property layout auditor (P1: overlaps, P2: die containment, P3: size preservation), and a 136-test verification suite with cross-simulator equivalence (Icarus vs. Verilator).

### 6. HEX → DEF Injector (`hex_to_def.py`)
Reads the legalized `.hex` output and patches coordinates back into the original `.def` file via targeted macro name matching, preserving standard cells and physical design data (pins, nets, routing, special nets).

### 7. Closed-Loop Evaluation (`evaluate.py` & `evaluate_layout.tcl`)
Automates verification by feeding candidate placements into OpenROAD to confirm zero residual overlaps (`check_placement`), measures half-perimeter wirelength via database net traversal, and generates visual comparison plots (`evaluation_plot.png`).

---

## Team P124

| Role | Name |
|:---|:---|
| **Team Leader** | K Sahana |
| **Team Member** | Ratik Agrawal |
| **Team Member** | Neha Ramiah |
| **Mentor** | Dr. Krupa Rasane |

## License

Academic project under IEEE Computer Society Bangalore Section under CS IAMPRO initiative.
