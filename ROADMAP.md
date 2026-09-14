# RTLign — 6-Month Comprehensive Roadmap

**Project:** ML-Assisted Simulated Annealing for RTL-Accelerated VLSI Macro Placement  
**Team:** P124 — K Sahana, Ratik Agrawal, Neha Ramiah  
**Start Date:** April 2026  
**End Date:** October 2026  
**Hardware:** NVIDIA A100 (20GB), 16-core CPU, 64GB RAM + personal laptops  

---

## Philosophy

This roadmap follows a **build-learn-build** cycle. Every implementation phase is preceded by a study phase. The strategy is:

```
Month 1–2:  ML Predictor + Foundations       ← SAFETY NET (guaranteed to work)
Month 3:    SA Legalizer in RTL              ← CORE INNOVATION (hardware)
Month 4–5:  RL Agent + Integration           ← AMBITIOUS GOAL (high impact)
Month 6:    Benchmarking + Defense            ← POLISH & PRESENT
```

If RL fails to converge → fall back to the ML predictor. The project is still complete and defensible. RL is the cherry on top.

---

## Month 1: Foundations & Physical Design Literacy

> **Goal:** Understand the physical design flow deeply, fix the dimension problem, and set up the complete development environment.

### Week 1: Study — VLSI Physical Design

| Day | Study Topic | Resource | Duration |
|:----|:------------|:---------|:---------|
| 1 | What is physical design? Synthesis → Placement → Routing → Signoff | Textbook: "VLSI Physical Design" by Kahng et al., Chapter 1–2 | 3 hours |
| 2 | Placement algorithms: min-cut, analytical, SA | Same textbook, Chapter 4 | 3 hours |
| 3 | Legalization and detailed placement | Same textbook, Chapter 4.5–4.7 | 2 hours |
| 4 | DEF/LEF file formats — what every field means | OpenROAD docs + manually read your `mockup_export.def` | 2 hours |
| 5 | Watch Andrew Kahng's lecture on OpenROAD placement | YouTube: "Andrew Kahng OpenROAD" | 1.5 hours |
| 6 | Read the OpenROAD flow-scripts README, understand the Makefile flow | `OpenROAD-flow-scripts/flow/README.md` | 2 hours |
| 7 | Review — discuss as a team, identify gaps | Team meeting | 1 hour |

**Deliverable:** Each team member can explain the full RTL-to-GDSII flow verbally.

---

### Week 2: Build — LEF Parser & Real Dimensions

| Task | Owner | Details | Status |
|:-----|:------|:--------|:-------|
| Find FreePDK45 / Nangate45 LEF file | Any | Search OpenROAD install, copy to `data/freepdk45.lef` | ✅ Done |
| Write `ml_predictor/lef_parser.py` | Ratik | Parse `MACRO ... SIZE W BY H ... END` blocks, return `{cell_type: (w, h)}` dict | ✅ Done |
| Update `def_parser.py` | Ratik | Cross-reference DEF component names with LEF dimensions, write real W/H to `.hex` | ✅ Done |
| Re-run full pipeline with real dimensions | Neha | Verify legalizer still achieves zero overlaps | ✅ Done |
| Fix any legalizer bugs exposed by real geometry | Sahana | Real cells are tall/thin (380×1400) not square (100×100) — expect edge cases | ✅ Done |

**Deliverable:** Pipeline runs end-to-end with physically accurate cell dimensions.

---

### Week 3: Study — Machine Learning for EDA

| Day | Study Topic | Resource | Duration |
|:----|:------------|:---------|:---------|
| 1 | ML basics refresher: PyTorch, Graph Neural Networks | PyTorch official tutorials | 3 hours |
| 2 | Feature engineering for PyTorch Geometric | PyTorch Geometric documentation | 2 hours |
| 3 | Read: "Machine Learning for EDA" survey paper | Paper: Huang et al., "Machine Learning for Electronic Design Automation: A Survey," ACM TODAES 2021 | 3 hours |
| 4 | Graph Neural Networks — what they are, why they matter for netlists | PyTorch Geometric intro tutorial | 3 hours |
| 5 | Read: Google's chip placement paper (Nature 2021) — focus on Section 2 (Methods) | "A Graph Placement Methodology for Fast Chip Design" | 3 hours |
| 6 | Read: DREAMPlace paper | "DREAMPlace: Deep Learning Toolkit-Enabled GPU Acceleration for Modern VLSI Placement" | 2 hours |
| 7 | Read: Pytorch Geometric for graph classification | "PyTorch Geometric documentation" | 2 hours |

**Deliverable:** Team understands supervised ML, GNNs, and has read the 3 key placement papers.

---

### Week 4: Build — Dataset Generation Pipeline

| Task | Owner | Details | Status |
|:-----|:------|:--------|:-------|
| Write OpenROAD TCL batch script | Neha | `run_placement.tcl` — takes design + parameters, outputs placed `.def` | ✅ Done |
| Write `data_generator.py` | Ratik | Loops over designs × constraints, calls OpenROAD via subprocess | ✅ Done |
| Generate ISPD 2015 placements | Sahana | Sweep 22 designs with varying AR/Util/Density (792 combinations) | ✅ Done |
| Extract ML Features | Ratik | `feature_extractor.py` to parse 277 output DEFs into ML features | ✅ Done |

**Deliverable:** 21.6 million training examples extracted across 277 layout configurations in a clean, ML-ready CSV format (`data/ml_features.csv`).

---

## Month 2: Supervised ML Predictor & Evaluation

> **Goal:** Build a working ML predictor that generates approximate placements. This is your safety net.

### Week 5: Study — PyTorch Geometric & Parquet

| Day | Study Topic | Resource | Duration |
|:----|:------------|:---------|:---------|
| 1–2 | PyTorch Geometric: Dataset creation, Message Passing, GraphSAGE | PyTorch Geometric official tutorials | 4 hours |
| 3 | HPWL computation — how to measure wirelength from a placement | Implement it from scratch in Python | 2 hours |
| 4 | Topological L-flow design: what edge structures predict relative placement? | Brainstorm session — bounding boxes, spanning trees | 2 hours |

---

### Week 6: Build — GNN Baseline & Inference

| Task | Owner | Details | Status |
|:-----|:------|:--------|:-------|
| Write `ml_predictor/feature_extractor.py` | Neha | Extract features from `.def` into Parquet: node features, raw coordinates, 14-channel edge connectivity | ✅ Done |
| Write `ml_predictor/dataset.py` | Sahana | Build PyTorch Geometric `InMemoryDataset` from Parquet tables | ✅ Done |
| Write `ml_predictor/train_nn.py` | Sahana | Train PyTorch Geometric GNN: features → L-flows (`topological_gnn_model.pth`) | ✅ Done |
| Write `ml_predictor/predict.py` | Ratik | Load trained model, predict L-flows, cycle-breaking DFS for DAG, output `.hex` | ✅ Done |
| Write `run_predict.py` | Ratik | Auto-detect inputs and run end-to-end inference | ✅ Done |

**Deliverable:** Trained GNN model (`topological_gnn_model.pth`) that infers topological DAG constraints in `.hex` format.

---

### Week 7: Build — Evaluation Suite & Benchmarking

| Task | Owner | Details | Status |
|:-----|:------|:--------|:-------|
| Write `ml_predictor/evaluate.py` | Neha | End-to-end pipeline evaluation: ML → Legalizer → Inject → OpenROAD check | ✅ Done |
| Write `openroad_scripts/evaluate_layout.tcl` | Neha | OpenROAD script for checking placement legality and reporting HPWL wirelength | ✅ Done |
| Floorplan visualizer | Neha | Side-by-side layout comparison plots (`evaluation_plot.png`) | ✅ Done |
| Pipeline integration test | All | Verify GCD baseline against ML-inferred placement | ✅ Done |

**Deliverable:** Automated evaluation framework reporting HPWL, overlap legality, and visualization plots comparing OpenROAD native placement against the RTLign pipeline.

---

### Week 8: Study — Simulated Annealing Deep Dive

| Day | Study Topic | Resource | Duration |
|:----|:------------|:---------|:---------|
| 1 | SA theory: Metropolis criterion, cooling schedules, ergodicity | Textbook: Kahng et al. Chapter 4.3, or Wikipedia (surprisingly good) | 3 hours |
| 2 | TimberWolf placer — the original SA-based placer | Paper: Sechen & Sangiovanni-Vincentelli, "TimberWolf3.2" | 2 hours |
| 3 | LFSR (Linear Feedback Shift Register) — hardware random number generation | YouTube tutorials + Wikipedia | 1.5 hours |
| 4 | Verilog refresher: parameterized modules, FSMs, memory interfaces | Your own `legalizer_fsm.v` + Verilog tutorial | 2 hours |
| 5 | Verilator — compiling Verilog to C++ for fast simulation | Verilator documentation + "getting started" tutorial | 2 hours |
| 6 | Read: hardware-accelerated SA papers | Search "FPGA simulated annealing placement" on Google Scholar | 2 hours |

**Deliverable:** Team understands SA theory, LFSR design, and Verilator toolchain.

---

## Month 3: Simulated Annealing in RTL

> **Goal:** Upgrade the greedy legalizer into a proper SA engine. This is the core hardware innovation.

### Week 9–10: Build — SA Engine in Verilog

| Task | Owner | Details | Status |
|:-----|:------|:--------|:-------|
| Design SA FSM state diagram on paper | All | States: INIT → PERTURB → EVALUATE → ACCEPT/REJECT → COOL → CHECK_DONE | ⏳ In Progress |
| Implement 32-bit LFSR | Sahana | Galois LFSR with maximal-length polynomial, produces pseudo-random numbers | ⏳ In Progress |
| Implement temperature register + cooling | Ratik | `temp <= temp - (temp >> COOL_SHIFT)` — exponential decay | ⏳ In Progress |
| Implement perturbation logic | Ratik | Pick random macro, apply random displacement scaled by temperature | ⏳ In Progress |
| Implement cost function | Neha | `cost = overlap_area + α × estimated_HPWL` (combinational logic) | ⏳ In Progress |
| Implement Metropolis acceptance | Sahana | `if new_cost < old_cost: accept. else: accept with probability e^(-ΔC/T)` | ⏳ In Progress |
| Integrate with existing collision checker | All | Reuse `collision_check.v`, add HPWL estimator | ⏳ In Progress |

**New FSM (replaces greedy sweep):**

```
INIT ──► PERTURB ──► FETCH ──► EVALUATE_COST ──► ACCEPT/REJECT ──► COOL ──►─┐
  ▲                                                                           │
  │                              frozen (temp ≈ 0)                            │
  └──────────────────────── LEGALIZE ◄── CHECK_FROZEN ◄───────────────────────┘
                               │
                            FINISH
```

---

### Week 11: Build — Testbench & Validation

| Task | Owner | Details |
|:-----|:------|:--------|
| Update `legalizer_tb.v` for SA | Sahana | Monitor temperature, cost, acceptance rate over time |
| Verify on GCD benchmark | Ratik | SA should reduce HPWL compared to greedy sweep |
| VCD waveform analysis | Neha | Open in GTKWave, verify cooling schedule, cost convergence |
| Compare: greedy sweep vs SA | All | Table: cycles, final HPWL, final overlap count |

---

### Week 12: Build — Verilator Bridge

| Task | Owner | Details |
|:-----|:------|:--------|
| Install Verilator | Ratik | `sudo apt install verilator` or build from source |
| Write Verilator wrapper for legalizer | Ratik | C++ class that loads `.hex`, runs SA, returns result |
| Write Python ctypes binding | Neha | `legalizer.so` → callable from Python in microseconds |
| Benchmark: vvp vs Verilator speed | Sahana | Expect 100–1000× speedup |

**Deliverable:** SA legalizer callable from Python at microsecond latency. HPWL improvement measured over greedy sweep.

---

## Month 4: Integration, Scaling & Benchmarking

> **Goal:** Scale to larger designs, close the feedback loop, and produce benchmark numbers.

### Week 13–14: Build — Full Benchmarking Suite

| Task | Owner | Details |
|:-----|:------|:--------|
| Run on ISPD 2015 benchmarks (28K–1.3M components) | All | Start with small ones (mgc_fft), scale up |
| OpenROAD re-import | Neha | Load `legalized_export.def` into OpenROAD, run routing + STA |
| Comparison table | Sahana | RTLign-RL vs RTLign-SML vs OpenROAD native placer |
| Metrics to report | All | See table below |

**Benchmark metrics:**

| Metric | How to Measure |
|:-------|:---------------|
| HPWL (Half-Perimeter Wire Length) | Sum of bounding box half-perimeters for all nets |
| Routed Wirelength | OpenROAD global router output |
| Worst Negative Slack (WNS) | OpenROAD STA after routing |
| Total Negative Slack (TNS) | OpenROAD STA |
| Placement Runtime | Wall-clock time for ML prediction + legalization |
| Legalization Cycles | Clock cycles in Verilog simulation |
| Legalizer Displacement | Total Manhattan distance macros were moved by SA |
| Overlap Count (pre-legalization) | How many overlaps the ML output had before SA |
