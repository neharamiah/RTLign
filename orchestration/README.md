# RTLign Orchestration & Dataset Generation Tutorial

Welcome to the **Dataset Generation Pipeline**! 

If you are just getting started with RTLign, you might be wondering: *How do we get the data to train our ML models?* This folder contains the answer. Here, we provide a step-by-step tutorial on how to automatically generate hundreds (or thousands) of unique macro placements using OpenROAD.

---

## 🌟 The Big Picture

To train a Machine Learning model to predict macro placements, it needs to see many examples of *good* and *bad* placements across different stages of optimization. 

Instead of doing this by hand, we use OpenROAD's RePlAce engine to generate these placements for us. By varying physical constraints and placement parameters:
- **Aspect Ratio** (`--aspect_ratios`): Flattens or stretches core area geometry (e.g. 1.0, 0.66, 1.5).
- **Core Utilization** (`--utilizations`): Adjusts cell packing density (e.g. 60%, 70%, 80%).
- **Target Density** (`--densities`): Controls maximum allowable cell area per bin (e.g. 0.60, 0.65, 0.70, 0.75).
- **Random Seed** (`--seeds`): Shifts standard cell initial positions using circular Gaussian distributions (e.g. 10, 42, 100).
- **Routability Snapshot Overflow** (`--snapshot_thresholds`): Captures intermediate layout snapshots at specific congestion levels (e.g. 0.4, 0.6, 0.8).

This pipeline loops over all combinations of these parameters, calls OpenROAD in parallel threads, and saves the resulting `.def` layout files along with a summary CSV containing placement status and HPWL wirelength metrics.

---

## 🛠️ Step 1: Understand the Components

The pipeline consists of two primary files that communicate via environment variables:

1. **`openroad_scripts/run_placement.tcl` (The Worker Engine)**
   * **What it is:** An OpenROAD TCL script.
   * **What it does:** Reads input LEF/DEF files, re-initializes floorplans, places I/O pins (`place_pins`), runs global placement (`global_placement -routability_driven -routability_snapshot_overflow $snapshot_threshold`), executes detailed placement legalization (`detailed_placement`), checks legality, logs HPWL metrics, and exports placed `.def` files.
   * **Analogy:** Think of this as a single factory worker who builds one specific layout when given instructions.

2. **`orchestration/data_generator.py` (The Manager)**
   * **What it is:** A multi-threaded Python orchestrator (`ThreadPoolExecutor`).
   * **What it does:** Automatically discovers benchmark designs (`data/ispd_benchmarks` and `data/generated_rtl_dataset`), generates parameter combination matrices, spawns parallel OpenROAD subprocess workers, tracks progress, and generates incremental `dataset_summary.csv` reports.
   * **Analogy:** Think of this as the factory manager who organizes work and assigns tasks to multiple workers to finish fast.

---

## 📂 Step 2: Prepare Your Input Files

Before generating a dataset for a benchmark or RTL design, ensure three files exist in the design directory:

1. **Tech LEF (`tech.lef`)**: Manufacturing rules (layers, vias, routing rules).
2. **Cells LEF (`cells.lef`)**: Physical dimensions of standard cells and macros.
3. **Floorplan DEF (`floorplan.def`)**: Initial design file with defined die area and unplaced components.

---

## 🚀 Step 3: Run the Generator

### Example 1: Run Multi-Dimensional Sweeps on Specific Designs
To run dataset generation for `picorv32`, `opentitan_blocks`, or `ibex`:

```bash
python orchestration/data_generator.py \
  --all_benchmarks \
  --only_designs picorv32 opentitan_blocks ibex \
  --seeds 10 42 100 \
  --snapshot_thresholds 0.4 0.6 0.8 \
  --aspect_ratios 1.0 0.66 1.5 \
  --utilizations 60 70 80 \
  --densities 0.6 0.65 0.7 0.75 \
  --workers 4
```

### Example 2: Single-Design Custom Run
To run placement for a single design:

```bash
python orchestration/data_generator.py \
  --design mgc_matrix_mult_2 \
  --tech_lef data/ispd_benchmarks/ispd2015/hidden/mgc_matrix_mult_2/tech.lef \
  --cells_lef data/ispd_benchmarks/ispd2015/hidden/mgc_matrix_mult_2/cells.lef \
  --input_def data/ispd_benchmarks/ispd2015/hidden/mgc_matrix_mult_2/floorplan.def \
  --aspect_ratios 1.0 0.66 1.5 \
  --utilizations 60 70 80 \
  --densities 0.6 0.65 0.7 0.75 \
  --workers 4
```

### CLI Command Options Summary:
* `--all_benchmarks`: Automatically discovers designs in benchmark directories.
* `--benchmarks_dir`: Path to ISPD benchmarks (default: `data/ispd_benchmarks`).
* `--rtl_benchmarks_dir`: Path to RTL designs (default: `data/generated_rtl_dataset`).
* `--only_designs`: Explicit list of design names to include (e.g. `picorv32 opentitan_blocks ibex`).
* `--exclude_designs`: List of design names to skip (default: `swerv`).
* `--seeds`: List of random seeds for global placement (default: `10 42 100`).
* `--snapshot_thresholds`: Overflow snapshot thresholds (default: `0.4 0.6 0.8`).
* `--workers`: Number of parallel worker threads (default: `4`).

---

## 🔍 Step 4: Check Your Outputs

Output `.def` layout files and logs are saved in `data/generated_defs/<design>/`:
- File naming convention: `{design}_s{seed}_t{threshold}_ar{ar}_u{util}_d{density}.def`
  - Example: `picorv32_s10_t0.4_ar1.0_u60_d0.6.def`
- Dataset summary manifest: `data/generated_defs/dataset_summary.csv` containing design name, seed, snapshot threshold, aspect ratio, utilization, density, status (`Legal`/`Illegal`/`Failed`), HPWL wirelength, and file paths.

---

## 🎯 What's Next?

With **1,299 generated DEF layout files** available across ISPD and RTL benchmarks (`opentitan_blocks`, `picorv32`, `ibex`):
1. Run `python ml_predictor/feature_extractor.py` to parse DEF files into ML feature matrices.
2. Train and evaluate the macro placement prediction models.
