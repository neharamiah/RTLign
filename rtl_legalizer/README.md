# RTL Legalizer & Simulated Annealing Engine

This directory contains the custom Verilog RTL hardware and verification suite for the RTLign pipeline. The system uses a two-pass hardware engine that combines stochastic simulated annealing placement with deterministic overlap elimination.

---

## Architecture Overview

```
                          Two-Pass Hardware Engine
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│  dummy_layout.hex ───► [ Pass 1: SA Optimizer (sa_engine.v) ]          │
│                        - 32-bit Galois LFSR (lfsr32.v)                 │
│                        - 3-term cost function (sa_cost.v)              │
│                        - Metropolis acceptance LUT                     │
│                        - Soft boundary reflection                      │
│                                   │                                    │
│                                   ▼                                    │
│                        [ Pass 2: Greedy Cleanup (legalizer_fsm.v) ]    │
│                        - Minimum-axis push resolution                  │
│                        - Alternating-axis sweep on repeat passes       │
│                        - AABB collision detection (collision_check.v) │
│                                   │                                    │
│                                   ▼                                    │
│                        output_layout.hex (See VERIFICATION.md for      │
│                        legality guarantees and limits)                 │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Pass 1: Simulated Annealing Optimizer ([`sa_engine.v`](file:///home/ratik/Projects/RTLign/rtl_legalizer/sa_engine.v))**:
   Performs stochastic placement optimization. It perturbs macro coordinates and accepts downhill moves or uphill moves via Metropolis probability ($P = e^{-\Delta C / T}$).
2. **Pass 2: Deterministic Greedy Cleanup ([`legalizer_fsm.v`](file:///home/ratik/Projects/RTLign/rtl_legalizer/legalizer_fsm.v))**:
   Iterates through all macro pairs. It pushes overlapping macros along the minimum overlap axis. Repeat passes alternate the push axis to prevent ping-pong loops.

---

## File Manifest

| File | Description |
| :--- | :--- |
| [`sa_legalizer_top.v`](file:///home/ratik/Projects/RTLign/rtl_legalizer/sa_legalizer_top.v) | Top-level module coordinating Pass 1 (SA) and Pass 2 (Greedy Cleanup). |
| [`sa_engine.v`](file:///home/ratik/Projects/RTLign/rtl_legalizer/sa_engine.v) | Simulated Annealing optimizer FSM with adaptive cooling. |
| [`sa_cost.v`](file:///home/ratik/Projects/RTLign/rtl_legalizer/sa_cost.v) | 3-term hardware cost module: $C_{\text{total}} = w_{\text{wl}} \cdot \text{HPWL} + w_{\text{area}} \cdot \text{Area}_{\text{bbox}} + C_{\text{boundary}}$. |
| [`lfsr32.v`](file:///home/ratik/Projects/RTLign/rtl_legalizer/lfsr32.v) | 32-bit Galois Linear Feedback Shift Register pseudo-random generator. |
| [`legalizer_fsm.v`](file:///home/ratik/Projects/RTLign/rtl_legalizer/legalizer_fsm.v) | Greedy cleanup FSM with alternating-axis cascade resolution. |
| [`collision_check.v`](file:///home/ratik/Projects/RTLign/rtl_legalizer/collision_check.v) | Combinational 2D Axis-Aligned Bounding Box (AABB) overlap checker. |
| [`legalizer_tb.v`](file:///home/ratik/Projects/RTLign/rtl_legalizer/legalizer_tb.v) | Testbench with hardware metrics reporting and post-run audits (P1, P2, P3). |
| [`audit.py`](file:///home/ratik/Projects/RTLign/rtl_legalizer/audit.py) | Layout auditor: verifies zero overlaps (P1), die containment (P2), and size preservation (P3). |
| [`golden_model.py`](file:///home/ratik/Projects/RTLign/rtl_legalizer/golden_model.py) | Bit-exact, cycle-accurate Python golden model of the complete RTL pipeline. |
| [`layout_gen.py`](file:///home/ratik/Projects/RTLign/rtl_legalizer/layout_gen.py) | Seeded layout generator supporting 7 synthetic stress modes. |
| [`VERIFICATION.md`](file:///home/ratik/Projects/RTLign/rtl_legalizer/VERIFICATION.md) | Formal verification report, audit proofs, and documented boundary limits. |
| [`tb_*.v`](file:///home/ratik/Projects/RTLign/rtl_legalizer/) | Directed Verilog testbenches: `tb_collision_check.v`, `tb_sa_cost.v`, `tb_legalizer_fsm.v`, `tb_sa_trace.v`. |
| [`lef_parser.py`](file:///home/ratik/Projects/RTLign/rtl_legalizer/lef_parser.py) | LEF parser extracting macro dimensions into integer Database Units (DBU). |
| [`verilator/`](file:///home/ratik/Projects/RTLign/rtl_legalizer/verilator/) | Verilator acceleration directory containing C++ harness, Makefile, and Python bridge. |

---

## Hardware Memory Contract

The engine communicates through 32-bit hexadecimal text files. Each macro occupies four consecutive memory addresses:

```hex
000187E0 // Macro 0: X coordinate (DBU)
00005780 // Macro 0: Y coordinate (DBU)
000507A0 // Macro 0: Width (DBU)
00026930 // Macro 0: Height (DBU)
00030D40 // Macro 1: X coordinate (DBU)
...
```

- Input file: `dummy_layout.hex`
- Output file: `output_layout.hex`
- Memory depth: `NUM_LINES = 4 * NUM_MACROS`

---

## Hardware Parameters

Top-level modules accept the following Verilog parameters:

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `NUM_LINES` | `672` | Memory lines (`4 * NUM_MACROS`). |
| `DIE_WIDTH` | `200260` | Chip boundary width in database units. |
| `DIE_HEIGHT` | `201600` | Chip boundary height in database units. |
| `ENABLE_SA` | `1` | Enable simulated annealing pass (`1` = SA + Greedy, `0` = Greedy only). |
| `T_INIT` | `1000000` | Initial annealing temperature. |
| `T_MIN` | `100` | Annealing stop temperature. |
| `COOL_SHIFT` | `3` | Temperature cooling shift ($T \leftarrow T - T / 2^3$). |
| `INNER_ITERS` | `100` | Perturbation steps per temperature step. |
| `MAX_ITERS` | `1000` | Maximum cooling steps. |
| `W_WL` | `4` | Weight multiplier for Half-Perimeter Wirelength (HPWL). |
| `W_AREA` | `1` | Weight multiplier for Bounding Box Area. |
| `W_BOUNDARY` | `8` | Penalty multiplier for boundary violations. |

---

## Execution Modes

### 1. Accelerated Verilator Execution (Recommended)

Verilator compiles the Verilog RTL into native C++ binaries, delivering a ~400x simulation speedup.

#### Build the executable:
```bash
make -C verilator
```

#### Run via CLI:
```bash
./verilator/legalizer_sim output_layout.hex
```

#### Run via Python:
```python
from rtl_legalizer.verilator.verilator_bridge import run_verilator_legalizer

metrics = run_verilator_legalizer(
    input_hex="dummy_layout.hex",
    output_hex="output_layout.hex"
)
print(f"Cycles: {metrics['cycles']}, Accepted Moves: {metrics['accepted_moves']}")
```

---

### 2. Interpreted Icarus Verilog Simulation

Use Icarus Verilog (`iverilog` and `vvp`) for parameterized simulations and waveform generation.

```bash
# Compile testbench with parameters
iverilog \
  -Plegalizer_tb.NUM_LINES=24 \
  -Plegalizer_tb.DIE_WIDTH=1113715 \
  -Plegalizer_tb.DIE_HEIGHT=741850 \
  -Plegalizer_tb.ENABLE_SA=1 \
  -o sim.out \
  collision_check.v iter_div.v lfsr32.v sa_cost.v sa_engine.v legalizer_fsm.v sa_legalizer_top.v legalizer_tb.v

# Run simulation
vvp sim.out

# View waveform trace (if enabled in testbench)
gtkwave legalizer.vcd
```

---

### 3. FPGA Synthesis (PYNQ / Vivado)

All six design files (`collision_check.v`, `iter_div.v`, `lfsr32.v`,
`sa_cost.v`, `sa_engine.v`, `legalizer_fsm.v`, plus `sa_legalizer_top.v` as
the top module) are Vivado-synthesizable:

- `layout_mem` in `sa_engine.v`, `legalizer_fsm.v`, and `sa_legalizer_top.v`
  infers as true-dual-port / simple-dual-port BRAM (synchronous reads).
- The Metropolis ratio uses the multi-cycle `iter_div.v` divider (no
  combinational divide).
- Reset is synchronized (async assert, sync release) inside
  `sa_legalizer_top.v`; drive the `rst` pin from a button or PS GPIO.
- The legalized layout can be read back on hardware through the registered
  `out_addr`/`out_data` port on `sa_legalizer_top`.
- `$readmemh` initialization uses the `INIT_FILE` parameter (default
  `dummy_layout.hex`, resolved against the simulator/synthesis working
  directory). For Vivado, either add the hex file to the project as a design
  source or override `INIT_FILE` with an absolute path.

---

## Unit, Property, and Verification Testing

Run pytest across the unit tests, property tests, golden model equivalence, and formal verification suite:

```bash
# Run all legalizer and verification tests (136 tests):
pytest tests/ rtl_legalizer/ -v

# Run directed Verilog unit testbenches:
pytest tests/test_unit_tbs.py -v

# Run golden model equivalence tests:
pytest tests/test_golden_model.py -v

# Run cross-simulator determinism and golden regression:
pytest tests/test_phase6_verification.py -v
```

### Layout Auditing & Characterization

Audit any layout HEX output against physical design rules:
```bash
# Verify P1 (overlaps), P2 (die bounds), and P3 (size preservation):
python audit.py <input.hex> <output.hex>

# Run randomized layout sweep (350 cases across 7 modes):
python ../scripts/sweep_legalizer.py

# Characterize Metropolis acceptance probabilities:
python ../scripts/characterize_metropolis.py
```

For full verification metrics, formal specifications, and documented edge-case behavior, see [`VERIFICATION.md`](file:///home/ratik/Projects/RTLign/rtl_legalizer/VERIFICATION.md).
