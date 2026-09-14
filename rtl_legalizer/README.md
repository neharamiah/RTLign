# RTL Legalizer Engine

This directory contains the custom hardware logic and verification suite for the RTLign pipeline. The engine detects Axis-Aligned Bounding Box (AABB) collisions and resolves overlaps in parallel.

## Components

- **`collision_check.v`**: Pure combinational Verilog module that tests whether two macros overlap using 2D AABB bounding-box conditions (`x1 < right2 && right1 > x2 && y1 < top2 && top1 > y2`).
- **`legalizer_fsm.v`**: Core Finite State Machine (FSM). Reads macro positions from internal memory, orchestrates pairwise overlap evaluations, pushes conflicting macros apart along the axis of minimal overlap, clamps to die boundaries, and writes back resolved coordinates.
- **`legalizer_tb.v`**: Hardware verification testbench. Initializes `layout_mem` with input coordinates, triggers the FSM, audits all $N(N-1)/2$ macro pairs post-legalization for zero residual overlap, dumps waveforms to `legalizer.vcd`, and exports final coordinates to `output_layout.hex`.
- **`lef_parser.py`**: Extracts accurate macro dimensions (Width, Height) from `.lef` files and converts micron floating-point values to integer DEF database units (DBU).
- **`lef_parser_test.py`**: Unit test suite for `lef_parser.py` validating dictionary output and scaling accuracy.
- **`lef_parser_property_test.py`**: Property-based verification suite powered by Hypothesis, ensuring bounding box dimensions remain positive, finite, and invariant across scaling factors.
- **`dummy_layout.hex`**: Input layout memory map initialized with coordinates extracted from the initial placement.
- **`output_layout.hex`**: Legalized layout memory map exported by `legalizer_tb.v` upon simulation completion.

## Simulation Commands

```bash
# Compile the legalizer modules
iverilog -o sim.out collision_check.v legalizer_fsm.v legalizer_tb.v

# Execute simulation
vvp sim.out

# View waveforms (optional)
gtkwave legalizer.vcd
```
