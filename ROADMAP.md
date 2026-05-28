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

| Task | Owner | Details |
|:-----|:------|:--------|
| Find FreePDK45 / Nangate45 LEF file | Any | Search OpenROAD install, copy to `data/freepdk45.lef` |
| Write `ml_predictor/lef_parser.py` | Ratik | Parse `MACRO ... SIZE W BY H ... END` blocks, return `{cell_type: (w, h)}` dict |
| Update `def_parser.py` | Ratik | Cross-reference DEF component names with LEF dimensions, write real W/H to `.hex` |
| Re-run full pipeline with real dimensions | Neha | Verify legalizer still achieves zero overlaps |
| Fix any legalizer bugs exposed by real geometry | Sahana | Real cells are tall/thin (380×1400) not square (100×100) — expect edge cases |

**Deliverable:** Pipeline runs end-to-end with physically accurate cell dimensions.

---

### Week 3: Study — Machine Learning for EDA

| Day | Study Topic | Resource | Duration |
|:----|:------------|:---------|:---------|
| 1 | ML basics refresher: supervised learning, Random Forest, neural nets | Andrew Ng's ML course (relevant sections) or StatQuest YouTube | 3 hours |
| 2 | Feature engineering for tabular data | Kaggle's feature engineering micro-course | 2 hours |
| 3 | Read: "Machine Learning for EDA" survey paper | Paper: Huang et al., "Machine Learning for Electronic Design Automation: A Survey," ACM TODAES 2021 | 3 hours |
| 4 | Graph Neural Networks — what they are, why they matter for netlists | PyTorch Geometric intro tutorial | 3 hours |
| 5 | Read: Google's chip placement paper (Nature 2021) — focus on Section 2 (Methods) | "A Graph Placement Methodology for Fast Chip Design" | 3 hours |
| 6 | Read: MaskPlace paper (NeurIPS 2022) — simpler RL formulation | "MaskPlace: Fast Chip Placement via RL with Visual Representation" | 2 hours |
| 7 | Read: ChiPFormer (ICML 2023) — offline RL for placement | "ChiPFormer: Transferable Chip Placement via Offline RL" | 2 hours |

**Deliverable:** Team understands supervised ML, GNNs, and has read the 3 key placement papers.

---

### Week 4: Build — Dataset Generation Pipeline

| Task | Owner | Details |
|:-----|:------|:--------|
| Write OpenROAD TCL batch script | Neha | `run_placement.tcl` — takes design + parameters, outputs placed `.def` |
| Write `data_generator.py` | Ratik | Loops over designs × seeds × densities, calls OpenROAD via subprocess |
| Generate GCD placements (1,000 runs) | Sahana | Vary random seeds and placement density, ~1 hour |
| Generate PicoRV32 placements (500 runs) | Ratik | Synthesis first, then 500 placement runs, ~6 hours |
| Parse ISPD 2015 benchmarks for features | Neha | Extract component positions, connectivity, die area from the 18 provided `.def` files |
| Organize into `data/training_ready/` | All | Extract features into structured formats (e.g., `.npy`, `.h5` or `.pkl`) |

**Deliverable:** 1,500+ training examples in a clean, ML-ready format (NPY or HDF5) — *not* `.hex` (which is only for Verilog) or `.csv` (which is too slow/large for graphs).

---

## Month 2: Supervised ML Predictor & Evaluation

> **Goal:** Build a working ML predictor that generates approximate placements. This is your safety net.

### Week 5: Study — Scikit-Learn & Feature Engineering

| Day | Study Topic | Resource | Duration |
|:----|:------------|:---------|:---------|
| 1–2 | scikit-learn: Random Forest, cross-validation, GridSearchCV | scikit-learn official tutorials | 4 hours |
| 3 | HPWL computation — how to measure wirelength from a placement | Implement it from scratch in Python | 2 hours |
| 4 | Feature design: what inputs predict good placement? | Brainstorm session — cell type, degree, die area, cluster membership | 2 hours |

---

### Week 6: Build — Random Forest Baseline

| Task | Owner | Details |
|:-----|:------|:--------|
| Write `ml_predictor/feature_extractor.py` | Neha | Extract features from `.def`: cell type (one-hot), connectivity degree, die dimensions, cell dimensions |
| Write `ml_predictor/train_rf.py` | Sahana | Train Random Forest regressor: features → (X, Y), 5-fold cross-validation |
| Write `ml_predictor/predict.py` | Ratik | Load trained model, predict coordinates for a new design, output `.hex` |
| Evaluate: predicted placement → legalizer → HPWL | All | Compare against OpenROAD's own placement |
| Write `ml_predictor/evaluate.py` | Neha | HPWL calculator + overlap counter + visualization |

**Deliverable:** Random Forest model that predicts placements. Measured HPWL vs OpenROAD baseline.

---

### Week 7: Build — Neural Network (optional improvement)

| Task | Owner | Details |
|:-----|:------|:--------|
| Write `ml_predictor/train_nn.py` | Ratik | Simple feedforward: 200 → 512 → 256 → 2, PyTorch |
| Train on A100 | Ratik | Should take ~30 min for 10K samples |
| Compare RF vs NN accuracy | Sahana | MAE on (X, Y) predictions, HPWL after legalization |
| Decision point: is NN significantly better? | All | If not, stick with RF for simplicity |

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

| Task | Owner | Details |
|:-----|:------|:--------|
| Design SA FSM state diagram on paper | All | States: INIT → PERTURB → EVALUATE → ACCEPT/REJECT → COOL → CHECK_DONE |
| Implement 32-bit LFSR | Sahana | Galois LFSR with maximal-length polynomial, produces pseudo-random numbers |
| Implement temperature register + cooling | Ratik | `temp <= temp - (temp >> COOL_SHIFT)` — exponential decay |
| Implement perturbation logic | Ratik | Pick random macro, apply random displacement scaled by temperature |
| Implement cost function | Neha | `cost = overlap_area + α × estimated_HPWL` (combinational logic) |
| Implement Metropolis acceptance | Sahana | `if new_cost < old_cost: accept. else: accept with probability e^(-ΔC/T)` |
| Integrate with existing collision checker | All | Reuse `collision_check.v`, add HPWL estimator |

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

## Month 4: Reinforcement Learning

> **Goal:** Build an RL agent that learns to place macros, using the SA legalizer as environment feedback.

### Week 13: Study — Reinforcement Learning

| Day | Study Topic | Resource | Duration |
|:----|:------------|:---------|:---------|
| 1–2 | RL fundamentals: MDP, rewards, policies, value functions | OpenAI Spinning Up — Key Concepts section | 4 hours |
| 3 | Policy gradient methods: REINFORCE, PPO | Spinning Up — PPO section | 3 hours |
| 4 | Hands-on: solve CartPole and LunarLander with Stable-Baselines3 | SB3 quickstart tutorial | 3 hours |
| 5 | Multi-environment training: SubprocVecEnv | SB3 documentation | 1.5 hours |
| 6 | Reward shaping — the art of designing reward functions | Blog: "Reward Shaping in RL" + Spinning Up section on reward hacking | 2 hours |
| 7 | Study Google's RL placement code: state, action, reward design | Their open-source Circuit Training repo on GitHub | 3 hours |

---

### Week 14: Build — RL Environment (Gymnasium)

| Task | Owner | Details |
|:-----|:------|:--------|
| Write `rl_agent/placement_env.py` | Ratik | Gymnasium environment class |
| Define state space | All | Canvas grid (die area discretized) + netlist adjacency + already-placed mask |
| Define action space | All | (X, Y) continuous coordinates for the next macro |
| Define reward v1 | All | `r = -HPWL_normalized` (keep it simple initially) |
| Implement `step()` | Ratik | Place one macro, compute HPWL delta, check episode done |
| Implement `reset()` | Neha | Shuffle macro order, clear placement |
| Test with random agent | Sahana | Verify env runs, episodes complete, rewards are finite |

**Environment design:**

```python
class PlacementEnv(gymnasium.Env):
    """
    State:  (N × 4) array — for each macro: [placed?, x, y, cell_type_id]
            + flattened adjacency features
    Action: (x, y) — continuous coordinates for the next macro to place
    Reward: computed after ALL macros placed + legalization
    Done:   when all macros are placed
    """
```

---

### Week 15–16: Build — RL Training Pipeline

| Task | Owner | Details |
|:-----|:------|:--------|
| Write `rl_agent/train.py` | Ratik | PPO training loop using Stable-Baselines3 |
| Implement SML warm-start | Sahana | Initialize policy network weights from supervised pre-training |
| Connect Verilator legalizer to env | Neha | After all macros placed, run SA legalizer, compute displacement |
| Reward v2 | All | `r = -α·HPWL - β·displacement - γ·density_variance` |
| Train on GCD (small, fast) | All | 16 parallel envs on A100, train overnight |
| Monitor with TensorBoard | Sahana | Track: mean reward, HPWL, displacement, acceptance rate |
| Checkpoint management | Neha | Save best model every 10K steps |

**Training config:**

```python
model = PPO(
    "MlpPolicy",           # or custom GNN policy
    vec_env,                # 16–32 parallel environments
    learning_rate=3e-4,
    n_steps=2048,
    batch_size=256,
    n_epochs=10,
    gamma=0.99,
    device="cuda",          # A100
    tensorboard_log="./tb_logs/",
)
model.learn(total_timesteps=2_000_000)  # ~6–12 hours on A100
```

**Deliverable:** RL agent that places GCD macros with lower HPWL than random placement.

---

## Month 5: Integration, Scaling & Benchmarking

> **Goal:** Scale to larger designs, close the RL-legalizer feedback loop, and produce benchmark numbers.

### Week 17–18: Build — RL + Legalizer Feedback Loop

| Task | Owner | Details |
|:-----|:------|:--------|
| Reward v3: add legalizer displacement penalty | All | RL learns to produce near-legal placements that the SA engine barely modifies |
| Train on PicoRV32 (~3K macros) | Ratik | Bigger design, longer episodes, more training needed |
| Experiment: RL with vs without warm-start | Sahana | Measure convergence speed difference |
| Experiment: reward ablation study | Neha | Remove one reward term at a time, measure impact |

---

### Week 19–20: Build — Full Benchmarking Suite

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
| Placement Runtime | Wall-clock time for ML/RL prediction + legalization |
| Legalization Cycles | Clock cycles in Verilog simulation |
| Legalizer Displacement | Total Manhattan distance macros were moved by SA |
| Overlap Count (pre-legalization) | How many overlaps the ML/RL output had before SA |
| Theoretical HW Latency | Legalization cycles ÷ target frequency |

---

### Week 21: Build — Visualization & Analysis

| Task | Owner | Details |
|:-----|:------|:--------|
| Placement heatmap visualization | Neha | Python matplotlib: color-coded macro positions before/after legalization |
| RL training curves | Sahana | Reward, HPWL, displacement over training steps (TensorBoard screenshots) |
| Waveform analysis | Ratik | GTKWave screenshots of SA convergence (temp, cost, acceptance) |
| Generate comparison plots | All | Bar charts: HPWL comparison, runtime comparison, scatter plots |

---

## Month 6: Paper, Defense & Polish

> **Goal:** Document everything, prepare defense, write a paper-quality report.

### Week 22–23: Write

| Deliverable | Owner | Content |
|:------------|:------|:--------|
| Abstract + Introduction | Ratik | Problem statement, motivation, key results |
| Related Work | Neha | Google's paper, MaskPlace, ChiPFormer, traditional SA placers |
| Methodology | All | Pipeline architecture, ML/RL design, SA engine, Verilog implementation |
| Results | Sahana | All benchmark tables, comparison charts, training curves |
| Discussion | All | What worked, what didn't, limitations, future work |
| Update PROGRESS.md | All | Final comprehensive progress document |

---

### Week 24: Defend

| Task | Owner | Details |
|:-----|:------|:--------|
| Prepare slides | All | 20–25 slides covering the full story |
| Prepare live demo | Ratik | Run `master_run.py` live, show OpenROAD GUI with legalized layout |
| Prepare FAQ answers | All | Anticipate 15 likely questions, have clear answers ready |
| Practice presentation | All | 2–3 dry runs, time each section |

**Key defense questions to prepare for:**

| Question | Your Answer |
|:---------|:------------|
| "Why not just use OpenROAD's built-in placer?" | "Our goal is to accelerate legalization in hardware. OpenROAD runs entirely on CPU." |
| "Does your RL agent beat OpenROAD?" | "On HPWL, [your result]. The key contribution is the hardware-accelerated legalization loop." |
| "Have you synthesized to FPGA?" | "We report theoretical latency based on cycle-accurate simulation. FPGA synthesis is future work." |
| "Why SA and not just greedy?" | "SA explores the solution space and can escape local minima. Greedy only pushes apart." |
| "Why RL over supervised ML?" | "RL learns to cooperate with the hardware legalizer. SML only mimics OpenROAD's strategy." |
| "What's your cost function?" | "α·HPWL + β·overlap_area, with Metropolis acceptance at temperature T." |

---

## Team Task Division

| Member | Primary Ownership | Secondary |
|:-------|:------------------|:----------|
| **Ratik** | Verilog RTL (SA engine, FSM), Verilator bridge, RL training pipeline | Pipeline orchestration |
| **Sahana** | ML predictor (RF, NN), RL environment, benchmarking | Testbench & verification |
| **Neha** | Data pipeline (parsers, feature extraction), OpenROAD scripts, visualization | Documentation & paper |

---

## Critical Milestones & Go/No-Go Decisions

| Date | Milestone | Go/No-Go |
|:-----|:----------|:---------|
| End of Month 1 | Pipeline with real dimensions, 1,500+ training examples | Must pass: pipeline works with real LEF dimensions |
| End of Month 2 | SML predictor with measured HPWL | Must pass: model predicts better than random |
| End of Month 3 | SA engine in Verilog with HPWL improvement over greedy | Must pass: SA reduces HPWL compared to greedy sweep |
| End of Month 4 | RL agent beats random placement | Decision point: if RL doesn't converge, double down on SML + SA |
| End of Month 5 | Benchmark numbers on ISPD designs | Must have: at least 3 designs benchmarked with full metrics |
| End of Month 6 | Defense ready | Must have: slides, demo, paper |

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|:-----|:------------|:-------|:-----------|
| RL doesn't converge | Medium | High | SML fallback is always ready. RL failure itself is a valid result to present. |
| SA in Verilog has bugs | Medium | High | Extensive testbench. Compare SA output against Python SA implementation. |
| OpenROAD batch runs are slow/broken | Medium | Medium | Use ISPD 2015 benchmarks directly — they already have placed DEFs. |
| A100 access gets delayed | Low | Medium | SML + SA work entirely on laptop. RL training can start on RTX 2050 (slower). |
| Real dimensions break legalizer | High | Low | Already anticipated. Week 2 is dedicated to fixing this. |
| ISPD benchmarks too large for RL | Medium | Medium | Start with small designs (28K components). Scale up only if time permits. |

---

## Reading List (Complete)

### Textbooks
1. **"VLSI Physical Design: From Graph Partitioning to Timing Closure"** — Kahng, Lienig, Markov, Hu *(the bible)*
2. **"Reinforcement Learning: An Introduction"** — Sutton & Barto *(free online, read Chapters 1–6)*

### Key Papers
3. **Google Nature 2021:** "A Graph Placement Methodology for Fast Chip Design" — Mirhoseini et al.
4. **MaskPlace (NeurIPS 2022):** "Fast Chip Placement via RL with Visual Representation" — Lai et al.
5. **ChiPFormer (ICML 2023):** "Transferable Chip Placement via Offline RL" — Lai et al.
6. **Critique:** "On the Reality of Google's Chip Placement" — Cheng et al., 2023
7. **ML for EDA Survey:** "Machine Learning for EDA: A Survey" — Huang et al., ACM TODAES 2021
8. **TimberWolf:** "The TimberWolf Placement and Routing Package" — Sechen, 1986
9. **DREAMPlace:** "DREAMPlace: Deep Learning Toolkit-Enabled GPU Acceleration for Modern VLSI Placement" — Lin et al., DAC 2019

### Online Courses & Tutorials
10. **OpenAI Spinning Up in Deep RL** — `spinningup.openai.com`
11. **Stable-Baselines3 Documentation** — `stable-baselines3.readthedocs.io`
12. **PyTorch Geometric Tutorials** — `pytorch-geometric.readthedocs.io`
13. **Andrew Kahng's Lectures** — YouTube
14. **David Silver's RL Course** — YouTube (UCL/DeepMind, 10 lectures)

---

*This roadmap is a living document. Update it monthly as priorities shift and results come in.*
