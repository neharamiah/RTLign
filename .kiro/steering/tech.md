# RTLign Technology Stack

## Languages

- **Python 3.x** - Pipeline orchestration, parsing, ML predictor (planned)
- **Verilog HDL** - RTL legalizer hardware (collision detection, FSM)
- **TCL** - OpenROAD automation scripts (planned)

## Tools & Frameworks

### RTL Simulation
- **Icarus Verilog** (`iverilog`, `vvp`) - Verilog compilation and simulation
  - Used for legalizer FSM simulation
  - VCD waveform output for debugging

### EDA Tools
- **OpenROAD** - Physical design suite (GUI, routing, STA)
  - DEF/LEF file import/export
  - Placement visualization
  - Signoff analysis

### ML/AI (Planned)
- **scikit-learn** - Random Forest baseline predictor
- **PyTorch** - Neural network models, RL agent
- **Stable-Baselines3** - PPO training for RL
- **PyTorch Geometric** - Graph neural networks for netlist

### Testing
- **pytest** - Unit and integration tests
- **Hypothesis** - Property-based testing for correctness properties

## Build & Run Commands

### Full Pipeline
```bash
python orchestration/master_run.py
```

### Individual Stages

**LEF Parsing:**
```bash
python rtl_legalizer/lef_parser.py data/ispd_benchmarks/ispd2015/hidden/mgc_matrix_mult_2/tech.lef data/ispd_benchmarks/ispd2015/hidden/mgc_matrix_mult_2/cells.lef --verbose
```

**DEF → HEX:**
```bash
python ml_predictor/def_parser.py
```

**RTL Legalizer:**
```bash
cd rtl_legalizer
iverilog -o sim.out collision_check.v legalizer_fsm.v legalizer_tb.v
vvp sim.out
```

**HEX → DEF:**
```bash
python ml_predictor/hex_to_def.py
```

### Testing
```bash
pytest tests/                    # Run all tests
pytest tests/ -k "lef_parser"    # Run specific test module
pytest tests/ --hypothesis-seed=42  # Property-based tests with specific seed
```

## Data Formats

### DEF (Design Exchange Format)
- Component placements, netlist, die area
- Parsed by `def_parser.py` for macro coordinates

### LEF (Library Exchange Format)
- Cell dimensions, pin locations, routing layers
- Parsed by `lef_parser.py` for real geometry

### HEX Memory File
- Hardware memory format for Verilog legalizer
- 4 lines per macro: X, Y, Width, Height (32-bit hex)
- Example: `0001A2B3 // X coord`

## Project Configuration

### Verilog Parameters
- `NUM_LINES` - Total 32-bit lines in .hex file
- `DIE_WIDTH` / `DIE_HEIGHT` - Chip boundary in database units
- Derived: `NUM_MACROS = NUM_LINES / 4`

### Default Values
- Database units: 1000 units/micron (standard)
- Default cell dimensions: 100×100 database units (fallback)

## Dependencies

Core:
- Python 3.8+ (type hints, dataclasses)
- Icarus Verilog 10.3+

Planned:
- OpenROAD (latest)
- PyTorch 2.0+
- scikit-learn 1.3+
- Stable-Baselines3
