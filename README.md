# RTLign

**ML-Assisted Simulated Annealing for RTL-Accelerated VLSI Macro Placement**

RTLign is a hardware-software co-design tool that replaces the traditional OpenROAD macro placer with a 4-stage pipeline: an ML Predictor that generates approximate coordinates, a custom Verilog RTL Legalizer that resolves overlaps in parallel hardware, and a Python orchestrator that wires everything back into the OpenROAD physical design flow.

## Pipeline Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│  OpenROAD    │     │  ML Predictor│     │  RTL Legalizer   │     │  OpenROAD    │
│  DEF & LEF   │────▶│  Parsers     │────▶│  Verilog SA      │────▶│  .def import │
│              │     │  (Python)    │     │  (iverilog/vvp)  │     │  Route + STA │
└──────────────┘     └──────────────┘     └──────────────────┘     └──────────────┘
```

## Quick Start

### Prerequisites

- **Python 3.x**
- **Icarus Verilog** (`iverilog`, `vvp`)
- **OpenROAD** (optional, for GUI visualization and signoff)

### Run the Full Pipeline

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
│   └── data_generator.py      # Automated OpenROAD placement dataset generator
├── ml_predictor/
│   ├── def_parser.py          # DEF + LEF → HEX coordinate extractor
│   ├── hex_to_def.py          # HEX → DEF coordinate injector
│   └── feature_extractor.py   # Extracts 21.6M features for Random Forest training
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
Extracts macro placement coordinates from an OpenROAD `.def` file, matches them with actual LEF dimensions, and converts them to a flat `.hex` memory file. Each macro is represented as 4 × 32-bit hex values: `X, Y, Width, Height`.

### 4. Feature Extractor (`feature_extractor.py`)
Parses hundreds of generated DEF layouts to extract millions of individual macro and cell coordinate constraints into a massive tabular dataset (`ml_features.csv`), used to train the ML predictor.

### 5. RTL Legalizer (`legalizer_fsm.v`)
A Mealy FSM that iterates over all macro pairs, detects AABB overlaps via the `collision_check` module, and resolves them by pushing the later macro along the axis of minimum overlap. Die-boundary clamping prevents macros from leaving the chip area.

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
