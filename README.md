# RTLign

**Topological Hardware-Software Co-Design for VLSI Macro Legalization**

RTLign is a hardware-software co-design tool that replaces the traditional OpenROAD macro placer with a 4-stage topological pipeline: an ML Predictor (GNN) that infers relative topological relationships (L-flows), a custom Verilog SystemVerilog Simulated Annealing (SA) engine that resolves these topologies into overlap-free coordinates using a single-cycle combinational DAG-Solver, and a Python orchestrator that wires everything back into the OpenROAD physical design flow.

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
- **Python 3.x**
- **Icarus Verilog** (`iverilog`, `vvp`)
- **OpenROAD** (optional, for GUI visualization and signoff)

#### Run the Full Pipeline

```bash
# From the RTLign project root
python orchestration/master_run.py
```

This will:
1. Parse LEF dimensions (Implicit in master_run)
2. Parse `openroad_scripts/mockup_export.def` with exact LEF geometries → extract macro coordinates to `rtl_legalizer/dummy_layout.hex`
3. Compile and simulate the Verilog legalizer → produce `rtl_legalizer/output_layout.hex`
4. Inject legalized coordinates back → produce `openroad_scripts/legalized_export.def`

### Run Individual Stages

```bash
# Stage 1: Parse LEF dimensions (imported by DEF parser)
# No manual command required; handled during def_parser execution.

# Stage 2: DEF + LEF → HEX
python ml_predictor/def_parser.py

# Stage 3: Compile & simulate the RTL legalizer
cd rtl_legalizer
iverilog -o sim.out collision_check.v legalizer_fsm.v legalizer_tb.v
vvp sim.out

# Stage 4: HEX → DEF injection
python ml_predictor/hex_to_def.py
```

## Project Structure

```
RTLign/
├── orchestration/
│   ├── master_run.py          # Single-click pipeline orchestrator
│   ├── data_generator.py      # Automated OpenROAD placement dataset generator
│   ├── generate_rtl_dataset.py # Generates gate-level netlists for RTL designs
│   └── rtl_to_def.py          # Converts RTL to floorplanned DEFs
├── ml_predictor/
│   ├── def_parser.py          # DEF + LEF → HEX coordinate extractor
│   ├── hex_to_def.py          # HEX → DEF coordinate injector
│   └── feature_extractor.py   # Extracts features and GNN edge indices to Parquet
├── rtl_legalizer/
│   ├── lef_parser.py          # LEF → Dimension Dictionary extractor
│   ├── lef_parser_test.py     # Unit tests for LEF parser
│   ├── collision_check.v      # Combinational AABB overlap detector
│   ├── legalizer_fsm.v        # FSM-based greedy sweep legalizer
│   ├── legalizer_tb.v         # Testbench with overlap audit
│   └── dummy_layout.hex       # Input macro layout (generated)
├── openroad_scripts/          # OpenROAD DEF files and TCL scripts
├── ROADMAP.md                 # 6-Month Comprehensive Roadmap
├── PROGRESS.md                # Project Progress Document
└── data/                      # Training datasets (gitignored)
```

## How It Works

### 1. LEF Parser (`lef_parser.py`)
Extracts actual macro dimensions (Width, Height) from an OpenROAD `.lef` library file, converting from microns to DEF database units to enable accurate collision detection for non-square geometries.

### 2. Dataset Generator (`data_generator.py`)
Automates OpenROAD (`run_placement.tcl`) to sweep through physical design constraints (e.g., Target Density, Core Utilization, Aspect Ratio). Generates hundreds of `Legal`, `Illegal`, and `Failed` layout variations for machine learning training.

### 3. DEF Parser (`def_parser.py`)
Extracts macro placement data from an OpenROAD `.def` file, matches them with actual LEF dimensions, and converts them to a flat `.hex` memory file representing the topological rules and L-flows. Each macro is represented as hex values: `Width, Height, Area, Aspect Ratio, Pin Count`.

### 4. Feature Extractor (`feature_extractor.py`)
Parses generated DEF layouts to extract structural node features and graph edge indices (14-channel edge feature vectors representing routing connectivity) into Parquet files. These files train the Graph Neural Network (GNN) model to predict relative topological relationships (L-flows).

### 5. SystemVerilog RTL Legalizer (`legalizer_fsm.v`)
A Simulated Annealing engine that translates the relative L-flow rules into exact physical coordinates. It relies on a custom combinational DAG-Solver that instantly computes 100% legal, overlap-free coordinates in a single hardware cycle. Die-boundary clamping prevents macros from leaving the chip area.

### 6. HEX → DEF Injector (`hex_to_def.py`)
Reads the legalized `.hex` output and patches the coordinates back into the original `.def` file, preserving all other physical design data (pins, nets, routing, special nets).

## Team P124

| Role | Name |
|:---|:---|
| **Team Leader** | K Sahana |
| **Team Member** | Ratik Agrawal |
| **Team Member** | Neha Ramiah |
| **Mentor** | Dr. Krupa Rasane |

## License

Academic project under IEEE Computer Sciety Bangalore Section under CS IAMPRO initiative.
