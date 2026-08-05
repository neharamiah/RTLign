# OpenROAD Scripts

This directory contains the Tcl scripts and DEF files for OpenROAD integration.

## Files

- `run_placement.tcl`: This script runs the OpenROAD placement flow. It reads design parameters, executes global placement, and runs detailed placement. It saves the placed `.def` file.
- `generate_ibex_floorplan.tcl`: This script creates the initial floorplan for the Ibex RISC-V core.
- `mockup_export.def`: This is the baseline GCD design file for testing.
- `legalized_export.def`: This is the output file. It contains the final legalized coordinates.