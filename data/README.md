# RTLign — Dataset Directory

This directory contains all RTL sources, placement benchmarks, and generated training data
for the RTLign ML predictor. **This entire directory is gitignored** — share via Google Drive: https://drive.google.com/drive/folders/11rk3iiRVHchWg8NOZXbroGBBM0-_1Dg5

**Total size: ~14.0 GB | Total Generated Layout DEFs: 1,299**

---

## Directory Layout

```
data/
├── rtl_sources/                  RTL designs to feed into OpenROAD for .def generation
│   ├── picorv32/                 Single-file RISC-V core (93 KB)
│   │   └── picorv32.v
│   ├── ibex/                     lowRISC RISC-V core (30 .sv files)
│   │   └── rtl/
│   ├── swerv/                    Western Digital RISC-V core (47 .sv files)
│   │   └── design/
│   └── opentitan_blocks/         Individual OpenTitan IP blocks (242 .sv files)
│       └── hw/ip/
│           ├── aes/rtl/          AES encryption engine
│           ├── hmac/rtl/         HMAC authentication
│           ├── uart/rtl/         UART controller
│           ├── spi_device/rtl/   SPI device controller
│           ├── i2c/rtl/          I2C controller
│           ├── gpio/rtl/         GPIO controller
│           └── timer/rtl/        Timer/watchdog
│
├── ispd_benchmarks/
│   │
│   ├── ispd2015/                 22 designs (18 public + 4 hidden, DEF + LEF format)
│   │   ├── mgc_fft_1/            32,281 components
│   │   ├── mgc_fft_2/            32,281 components
│   │   ├── mgc_fft_a/            30,631 components
│   │   ├── mgc_fft_b/            30,631 components
│   │   ├── mgc_pci_bridge32_a/   29,521 components
│   │   ├── mgc_pci_bridge32_b/   28,920 components
│   │   ├── mgc_des_perf_1/       112,644 components
│   │   ├── mgc_des_perf_a/       108,292 components
│   │   ├── mgc_des_perf_b/       112,644 components
│   │   ├── mgc_edit_dist_a/      127,419 components
│   │   ├── mgc_edit_dist_1_a/    130,662 components
│   │   ├── mgc_edit_dist_1_b/    130,662 components
│   │   ├── mgc_matrix_mult_1/    155,325 components
│   │   ├── mgc_matrix_mult_a/    149,655 components
│   │   ├── mgc_matrix_mult_b/    146,442 components
│   │   ├── mgc_superblue11_a/    927,074 components
│   │   ├── mgc_superblue12/      1,287,037 components
│   │   └── mgc_superblue16_a/    680,869 components

│
├── openroad_configs/             Per-design OpenROAD flow configs & scripts
│
├── generated_defs/               Output: 1,299 generated .def layout files from ISPD & RTL sweeps
│   ├── opentitan_blocks/         (324 DEFs, 7.6 GB)
│   ├── picorv32/                 (324 DEFs, 417 MB)
│   ├── ibex/                     (324 DEFs, 1.8 GB)
│   ├── mgc_fft_1/                (ISPD benchmark DEFs)
│   └── dataset_summary.csv       Summary CSV containing placement status, HPWL, seed, snapshot threshold, etc.
│
├── generated_rtl_dataset/        Synthesized gate-level netlists, floorplans, and LEFs for RTL designs
│   ├── picorv32/                 (tech.lef, cells.lef, floorplan.def)
│   ├── opentitan_blocks/         (tech.lef, cells.lef, floorplan.def)
│   ├── ibex/                     (tech.lef, cells.lef, floorplan.def - 14,463 instances)
│   └── swerv/                    (tech.lef, cells.lef, floorplan.def)
│
├── sky130_pdk/                   SkyWater 130nm PDK standard cell libraries & tech LEFs
│
├── ml_features.csv               Extracted feature dataset (~1.5 GB) from generated DEF files for ML training
│
└── dataset_generation.log        Build & execution logs for automated dataset generation pipeline
```

---

## Generated Dataset Summary

We have generated **1,299 DEF files** across ISPD 2015 benchmarks and synthesized RTL designs:

| Source | Category | Generated DEF Files | Details / Constraints Swept | Storage |
|:---|:---|---:|:---|---:|
| **ISPD 2015 Benchmarks** | Benchmark Sweeps | **327 DEFs** | 11 benchmark designs (`mgc_des_perf_1`, `mgc_matrix_mult_1`, `mgc_fft_1`, etc.) swept over Aspect Ratio (0.66, 1.0, 1.5), Core Utilization (60%, 70%, 80%), and Target Density (0.60, 0.65, 0.70, 0.75). | **4.2 GB** |
| **RTL — OpenTitan** | Synthesized & Placed | **324 DEFs** | Swept over 3 seeds (10, 42, 100), 3 snapshot thresholds (0.4, 0.6, 0.8), 3 aspect ratios, 3 utilizations, and 4 densities (324/324 100% success). | **7.6 GB** |
| **RTL — PicoRV32** | Synthesized & Placed | **324 DEFs** | Swept over 3 seeds, 3 snapshot thresholds, 3 aspect ratios, 3 utilizations, and 4 densities (324/324 100% success). | **417 MB** |
| **RTL — Ibex** | Synthesized & Placed | **324 DEFs** | Floorplanned with 14,463 instances; swept over 3 seeds, 3 snapshot thresholds, 3 aspect ratios, 3 utilizations, and 4 densities (324/324 100% success). | **1.8 GB** |
| **RTL — SweRV EH1** | Synthesized & Floorplanned | **0 DEFs** | Synthesized & floorplanned (2.1M instances; excluded from large parameter sweeps). | **-** |
| **Total** | | **1,299 DEFs** | Tracked in `data/generated_defs/dataset_summary.csv` | **~14.0 GB** |

---

## Benchmark Summary

### ISPD 2015 — Detailed Routing-Driven Placement (DEF + LEF)

| Design | Components | Format | DEF Size |
|:---|---:|:---|---:|
| mgc_pci_bridge32_b | 28,920 | DEF + LEF + Verilog | 4.8 MB |
| mgc_pci_bridge32_a | 29,521 | DEF + LEF + Verilog | 4.3 MB |
| mgc_fft_a | 30,631 | DEF + LEF + Verilog | 4.6 MB |
| mgc_fft_b | 30,631 | DEF + LEF + Verilog | 4.6 MB |
| mgc_fft_1 | 32,281 | DEF + LEF + Verilog | 4.0 MB |
| mgc_fft_2 | 32,281 | DEF + LEF + Verilog | 4.0 MB |
| mgc_des_perf_a | 108,292 | DEF + LEF + Verilog | 14 MB |
| mgc_des_perf_1 | 112,644 | DEF + LEF + Verilog | 13 MB |
| mgc_des_perf_b | 112,644 | DEF + LEF + Verilog | 14 MB |
| mgc_edit_dist_a | 127,419 | DEF + LEF + Verilog | 18 MB |
| mgc_edit_dist_1_a | 130,662 | DEF + LEF + Verilog | 19 MB |
| mgc_edit_dist_1_b | 130,662 | DEF + LEF + Verilog | 19 MB |
| mgc_matrix_mult_b | 146,442 | DEF + LEF + Verilog | 19 MB |
| mgc_matrix_mult_a | 149,655 | DEF + LEF + Verilog | 19 MB |
| mgc_matrix_mult_1 | 155,325 | DEF + LEF + Verilog | 18 MB |
| mgc_superblue16_a | 680,869 | DEF + LEF + Verilog | 72 MB |
| mgc_superblue11_a | 927,074 | DEF + LEF + Verilog | 102 MB |
| mgc_superblue12 | 1,287,037 | DEF + LEF + Verilog | 148 MB |

Each design directory contains: `tech.lef`, `cells.lef`, `floorplan.def`, `design.v`, `placement.constraints`.

---

## RTL Sources Summary

| Source | Files | Size | Status |
|:---|---:|---:|:---|
| PicoRV32 | 1 `.v` file | 93 KB | ✅ Synthesized & Placed (324 DEFs) |
| OpenTitan blocks | 242 `.sv` files | 6.8 MB | ✅ Synthesized & Placed (324 DEFs) |
| Ibex | 30 `.sv` files | 50 MB | ✅ Floorplanned (14,463 insts) & Placed (324 DEFs) |
| SweRV EH1 | 47 `.sv` files | 3.8 MB | ✅ Synthesized & Floorplanned (2.1M insts, excluded from large sweep) |
| **Total** | **320 RTL files** | **~61 MB** | |

---

## How to Use & Generate Data

### 1. Generating RTL-derived DEF Files
To synthesize RTL designs into gate-level netlists with Yosys (Sky130 PDK) and perform OpenROAD placement sweeps:
```bash
python orchestration/generate_rtl_dataset.py
```

### 2. Running Parameter Sweeps Across Designs
To run multi-dimensional constraint sweeps (Seeds, Snapshot Overflow Thresholds, Aspect Ratio, Utilization, Target Density):
```bash
python orchestration/data_generator.py --all_benchmarks --only_designs picorv32 opentitan_blocks ibex
```

### 3. Extracting ML Features
To extract graph connectivity, pin density, and cell bounding box features from all generated DEF files into `data/ml_features.csv`:
```bash
python ml_predictor/feature_extractor.py
```
