# RTLign Orchestration & Dataset Generation Tutorial

Welcome to the **Dataset Generation Pipeline**! 

If you are just getting started with RTLign, you might be wondering: *How do we get the data to train our ML models?* This folder contains the answer. Here, we provide a step-by-step tutorial on how to automatically generate hundreds (or thousands) of unique macro placements using OpenROAD.

---

## 🌟 The Big Picture

To train a Machine Learning model to predict macro placements, it needs to see many examples of *good* and *bad* placements. 

Instead of doing this by hand, we use OpenROAD's RePlAce engine to generate these placements for us. By varying the physical constraints like **aspect ratio**, **core utilization**, and **target density**, we get uniquely optimized layouts for the exact same circuit design.

This pipeline does exactly that: it loops over all combinations of these constraints, tells OpenROAD to place the macros, and saves the results along with a summary CSV containing placement metrics.

---

## 🛠️ Step 1: Understand the Components

The pipeline consists of two files that talk to each other:

1. **`openroad_scripts/run_placement.tcl` (The Worker Engine)**
   * **What it is:** An OpenROAD script written in TCL. 
   * **What it does:** It takes exactly one set of instructions (aspect ratio, utilization, density, design) and tells OpenROAD to compute the placement. 
   * **Analogy:** Think of this as a single factory worker who knows how to build one specific layout when given the instructions.

2. **`orchestration/data_generator.py` (The Manager)**
   * **What it is:** A Python orchestration script.
   * **What it does:** It creates a massive "To-Do" list of all the different constraint combinations you want. Then, it spins up multiple parallel threads (workers) and sends the instructions to the TCL script. 
   * **Analogy:** Think of this as the factory manager who organizes the work and assigns tasks to multiple workers to get the job done fast.

---

## 📂 Step 2: Prepare Your Input Files

Before you can generate a dataset, you need a benchmark design (e.g., from the ISPD 2015 dataset). You must have three specific files ready:

1. **Tech LEF (`tech.lef`)**: Contains the manufacturing rules (layers, vias, routing rules).
2. **Cells LEF (`cells.lef`)**: Contains the physical shapes and dimensions of the standard cells and macros.
3. **Floorplan DEF (`floorplan.def`)**: The initial design file that has the die area defined, but the macros are *not* placed yet.

*In this tutorial, we will use the `mgc_matrix_mult_2` benchmark located in `data/ispd_benchmarks/ispd2015/hidden/mgc_matrix_mult_2/`.*

---

## 🚀 Step 3: Run the Generator

Now it's time to run the generator! Open your terminal, ensure you are in the **root of the RTLign repository**, and run the following command:

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

### Let's break down what you just typed:
* `python orchestration/data_generator.py`: You are starting the "Manager" script.
* `--design mgc_matrix_mult_2`: You are naming the project. This is used to name the output files.
* `--tech_lef`, `--cells_lef`, `--input_def`: You are providing the exact paths to the input files we discussed in Step 2.
* `--aspect_ratios 1.0 0.66 1.5`: You are telling the script to generate floorplans with these specific aspect ratios.
* `--utilizations 60 70 80`: You are varying the core utilization percentages.
* `--densities 0.6 0.65 0.7 0.75`: You are giving it 4 different target densities.
* `--workers 4`: You are telling the script to use 4 parallel CPU threads so it finishes 4x faster!

**Total generated files:** 3 aspect ratios × 3 utilizations × 4 densities = **36 unique placements!**

---

## 🔍 Step 4: Check Your Outputs

While the script is running, it will print out its progress. Once it says "Generation complete!", you can find your data.

1. Navigate to the `data/generated_defs/mgc_matrix_mult_2/` directory.
2. Inside, you will see 36 DEF files along with their placement logs that look like this:
   * `mgc_matrix_mult_2_ar1.0_u60.0_d0.6.def` (AR: 1.0, Util: 60%, Density: 60%)
   * `mgc_matrix_mult_2_ar1.5_u70.0_d0.65.def` (AR: 1.5, Util: 70%, Density: 65%)

You will also find a `dataset_summary.csv` file in the output directory containing the legal status and wirelength (HPWL) metrics for all the generated layouts!

These `.def` files now contain the `PLACED` coordinates for all your macros and standard cells! 

---

## 🎯 What's Next?

Congratulations! You have successfully generated a raw dataset. 

In the next phase of the project (Month 2), we will write a Feature Extractor script. That script will open all these `.def` files, extract the exact X/Y coordinates and wire connectivity of the macros, and package them into ML-ready matrices (like `.npy` or `.h5` files) so we can start training our Random Forest model!
