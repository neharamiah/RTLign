# RTL Legalizer Engine

This directory contains the custom hardware logic for the RTLign pipeline. The engine detects Axis-Aligned Bounding Box (AABB) collisions and resolves overlaps in parallel.

## Components

- `collision_check.v`: This module detects overlaps between two macros. It uses combinational logic.
- `legalizer_fsm.v`: This is the core Finite State Machine (FSM). It reads coordinates from memory, checks for overlaps, and pushes macros apart to resolve collisions.
- `legalizer_tb.v`: This is the testbench. It drives the FSM, audits the final layout for overlaps, and writes the output `.hex` file.
- `lef_parser.py`: This script extracts accurate macro dimensions from `.lef` files. It converts micron measurements to database units.
- `dummy_layout.hex`: This is the input memory map. The Python orchestrator writes extracted coordinates here.