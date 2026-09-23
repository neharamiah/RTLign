# OpenROAD Scripts

This directory contains the TCL scripts and DEF design fixtures for OpenROAD integration, automated dataset generation, and layout evaluation.

## Files

- **`run_placement.tcl`**: Parametric placement script for OpenROAD. Accepts technology/cell LEFs, an initial floorplan DEF, and placement constraints (seed, target density, routability snapshot overflow). Runs global placement (RePlAce), detailed placement (`dpl`), checks legality, and exports placed `.def` files for ML training dataset generation.
- **`evaluate_layout.tcl`**: Layout verification and metric extraction script invoked during pipeline benchmarking (`ml_predictor/evaluate.py`). Loads candidate DEF and LEF libraries, executes `check_placement -verbose` to verify legality, and dumps HPWL wirelength metrics via `report_wire_length`.
- **`generate_ibex_floorplan.tcl`**: Generates the initial floorplan and pin constraints for the Ibex RISC-V core benchmark.
- **`mockup_export.def`**: Baseline GCD benchmark design file used for testing and pipeline regression runs.
- **`legalized_export.def`**: Output DEF file produced after injecting RTL-legalized coordinates back into the design layout.

## Direct CLI Usage

### Running Placement:
```bash
openroad -no_init -exit run_placement.tcl \
  -design_name gcd \
  -tech_lef path/to/tech.lef \
  -cells_lef path/to/cells.lef \
  -input_def path/to/floorplan.def \
  -output_def path/to/placed.def \
  -seed 42 \
  -target_density 0.70
```

### Evaluating a Placed Layout:
```bash
TECH_LEF=path/to/tech.lef CELLS_LEF=path/to/cells.lef INPUT_DEF=path/to/placed.def \
  openroad -no_init -exit evaluate_layout.tcl
```
