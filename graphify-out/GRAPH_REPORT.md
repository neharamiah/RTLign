# Graph Report - RTLign  (2026-09-23)

## Corpus Check
- 57 files · ~45,334 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 16 file(s) not represented in the graph (top: .parquet 5, (none) 4, .tcl 4)

## Summary
- 618 nodes · 759 edges · 50 communities (39 shown, 8 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7c2dedf3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- convert_to_db_units
- FeatureExtractor
- test_ispd2015_integration.py
- golden_model.py
- extract_database_units
- parse_def_to_hex
- RTLign — 6-Month Comprehensive Roadmap
- test_lef_parser_cli.py
- 4. Component Deep-Dives
- validate_dimension
- TestExtractMacroDimensions
- How It Works
- test_phase5_integration.py
- data_generator.py
- rtl_to_def.py
- legalizer_tb
- run_predict.py
- legalizer_fsm
- collision_check.v
- RTLign — Dataset Directory
- RTLign Orchestration & Dataset Generation Tutorial
- RTLign: AI Agent System Architecture & Guidelines
- audit.py
- RTLign: ML-Assisted Simulated Annealing for RTL-Accelerated VLSI Macro Placement
- ML Predictor
- Direct CLI Usage
- RTL Legalizer & Simulated Annealing Engine
- TestCheckLayout
- run_verilator_legalizer
- TestLegalizerFSM
- parse_lef_file
- 3. Findings
- test_golden_model.py
- TopologicalMacroDataset
- test_dimension_dict_matches_source
- TestParseLefFile
- TestParseLefFiles
- tb_collision_check
- tb_sa_cost
- sa_engine
- sa_legalizer_top
- tb_cost_vectors
- tb_legalizer_fsm
- tb_sa_trace
- conftest.py
- lfsr32.v
- sa_cost.v

## God Nodes (most connected - your core abstractions)
1. `4. Component Deep-Dives` - 16 edges
2. `FeatureExtractor` - 15 edges
3. `parse_lef_file()` - 14 edges
4. `parse_lef_files()` - 13 edges
5. `extract_macro_dimensions()` - 13 edges
6. `convert_to_db_units()` - 12 edges
7. `extract_database_units()` - 11 edges
8. `TestCheckLayout` - 11 edges
9. `TestLayoutGen` - 10 edges
10. `TestLegalizerFSM` - 10 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `parse_lef_files()`  [EXTRACTED]
  ml_predictor/evaluate.py → rtl_legalizer/lef_parser.py
- `main()` --calls--> `run_verilator_legalizer()`  [EXTRACTED]
  ml_predictor/evaluate.py → rtl_legalizer/verilator/verilator_bridge.py
- `main()` --calls--> `parse_lef_files()`  [EXTRACTED]
  orchestration/master_run.py → rtl_legalizer/lef_parser.py
- `main()` --calls--> `parse_def_to_hex()`  [EXTRACTED]
  orchestration/master_run.py → ml_predictor/def_parser.py
- `run_icarus_legalizer()` --calls--> `read_hex_words()`  [EXTRACTED]
  tests/test_phase6_verification.py → rtl_legalizer/audit.py

## Import Cycles
- None detected.

## Communities (50 total, 8 thin omitted)

### Community 0 - "convert_to_db_units"
Cohesion: 0.19
Nodes (9): convert_to_db_units(), Convert a dimension from microns to database units. Args: value_microns:…, Unit tests for convert_to_db_units function., Test basic unit conversion with 1000 multiplier., Test that None db_units defaults to 1000., Test conversion with fractional micron values., Test that rounding is applied correctly., Test conversion with different database unit multipliers. (+1 more)

### Community 1 - "FeatureExtractor"
Cohesion: 0.08
Nodes (28): DiGraph, main(), plot_layouts(), evaluate.py — RTLign Pipeline Evaluation Orchestrator Runs the full ML -> RTL…, run_cmd(), run_openroad_eval(), FeatureExtractor, get_die_diagonal() (+20 more)

### Community 2 - "test_ispd2015_integration.py"
Cohesion: 0.07
Nodes (17): Integration tests with ISPD 2015 benchmarks. Tests Requirements 6.1, 6.2, 6.3,…, Requirement 7.1: Verify extreme aspect ratio cells handled correctly. WHEN…, Test 16.2: Full pipeline integration with real dimensions, Requirement 6.3: Legalizer FSM completes without deadlock. WHEN running the…, Requirement 6.4: Output HEX contains non-uniform dimensions. WHEN legalization…, Test 16.3: Error handling scenarios, Requirement 5.3: Invalid LEF file path aborts pipeline. WHEN the LEF_Parser…, Test 16.1: LEF parsing with mgc_matrix_mult_2 design data (+9 more)

### Community 3 - "golden_model.py"
Cohesion: 0.08
Nodes (30): Random, boxes_overlap(), cost_model(), greedy_model(), legalize_model(), LFSR32, metropolis_threshold(), Cycle-accurate Python golden model of the rtl_legalizer Verilog pipeline.… (+22 more)

### Community 4 - "extract_database_units"
Cohesion: 0.15
Nodes (11): extract_database_units(), Extract DATABASE MICRONS value from UNITS block. LEF format: UNITS DATABASE…, Unit tests for extract_database_units function., Test parsing a standard UNITS block with DATABASE MICRONS 1000., Test parsing with a different multiplier value., Test that None is returned when UNITS block is missing., Test that None is returned when DATABASE MICRONS is missing from UNITS block., Test that parsing is case-insensitive. (+3 more)

### Community 5 - "parse_def_to_hex"
Cohesion: 0.17
Nodes (11): parse_def_to_hex(), Dimension_Dict, Parse a DEF file and generate a .hex memory file for the hardware legalizer.…, main(), RTLign — Master Orchestration Script =====================================…, Run a subprocess command with timing and error handling., run_step(), Additional integration tests for LEF + DEF pipeline (+3 more)

### Community 6 - "RTLign — 6-Month Comprehensive Roadmap"
Cohesion: 0.11
Nodes (18): Month 1: Foundations & Physical Design Literacy, Month 2: Supervised ML Predictor & Evaluation, Month 3: Simulated Annealing in RTL, Month 4: Integration, Scaling & Benchmarking, Philosophy, RTLign — 6-Month Comprehensive Roadmap, Week 11: Build — Testbench & Validation, Week 12: Build — Verilator Bridge (+10 more)

### Community 7 - "test_lef_parser_cli.py"
Cohesion: 0.14
Nodes (13): Unit tests for LEF Parser CLI interface. Tests the CLI implementation for…, Test that multiple LEF files can be parsed, Test that missing LEF file produces error, Test Requirement 10.1: --help shows usage information, Test Requirement 10.2: JSON output to stdout, Test Requirement 10.3: --output writes to specified file, Test Requirement 10.4: --verbose logs each MACRO name and dimensions, test_error_on_missing_file() (+5 more)

### Community 8 - "4. Component Deep-Dives"
Cohesion: 0.05
Nodes (39): 1. Project Overview, 2. Repository Structure, 3. Development Timeline, 4.10 Feature Extractor (`ml_predictor/feature_extractor.py`), 4.11 GNN Dataset Loader (`ml_predictor/dataset.py`), 4.12 Topological GNN Model (`ml_predictor/model.py`), 4.13 GNN Training Pipeline (`ml_predictor/train_nn.py`), 4.14 Inference Engine & DAG Cycle-Breaker (`ml_predictor/predict.py` & `run_predict.py`) (+31 more)

### Community 9 - "validate_dimension"
Cohesion: 0.19
Nodes (9): Validate that a dimension is a positive integer within 32-bit range. Args:…, Unit tests for validate_dimension function., Test that positive values are validated as valid., Test that zero is rejected., Test that negative values are rejected., Test that values exceeding 32-bit limit are rejected., Test that max 32-bit value is accepted., TestValidateDimension (+1 more)

### Community 10 - "TestExtractMacroDimensions"
Cohesion: 0.17
Nodes (7): Unit tests for extract_macro_dimensions function., Test extraction of a single MACRO block., Test extraction of multiple MACRO blocks., Test that MACROs without SIZE statement are skipped., Test that SIZE parsing is case-insensitive., Test that MACROs with invalid dimensions are skipped., TestExtractMacroDimensions

### Community 11 - "How It Works"
Cohesion: 0.09
Nodes (22): 1. LEF Parser (`lef_parser.py`), 2. Dataset Generator (`data_generator.py`), 3. Feature Extractor (`feature_extractor.py`), 4. Topological GNN Training & Inference (`train_nn.py`, `predict.py`), 5. Two-Pass Hardware Legalizer & Verilator Accelerator, 6. HEX → DEF Injector (`hex_to_def.py`), 7. Closed-Loop Evaluation (`evaluate.py` & `evaluate_layout.tcl`), How It Works (+14 more)

### Community 12 - "test_phase5_integration.py"
Cohesion: 0.13
Nodes (14): inject_coords_into_def(), main(), RTLign — HEX → DEF Injector ============================ Reads a legalized .hex…, Read the .hex file and return coords (and optionally macro names). Each macro…, Patch legalized coordinates into a DEF file. Two matching modes: 1. By Name: If…, read_hex_coordinates(), Integration tests for Phase 5 ML Predictor and Evaluation Pipeline., run_predict.py requires --def_file and --lef_file. (+6 more)

### Community 13 - "data_generator.py"
Cohesion: 0.48
Nodes (6): extract_metrics_from_log(), find_benchmarks(), main(), Runs a single OpenROAD placement job via subprocess., run_openroad_placement(), write_summary_report()

### Community 14 - "rtl_to_def.py"
Cohesion: 0.60
Nodes (4): find_rtl_files(), main(), Finds all .v and .sv files in the given directory recursively, excluding…, run_pipeline()

### Community 15 - "legalizer_tb"
Cohesion: 0.29
Nodes (6): legalizer_tb, run_boundary_audit, run_overlap_audit, run_size_audit, run_overlap_audit, sa_legalizer_top

### Community 16 - "run_predict.py"
Cohesion: 0.67
Nodes (3): main(), parse_arguments(), run_predict.py — RTLign GNN Prediction Top-Level Runner Automates running the…

### Community 21 - "RTLign — Dataset Directory"
Cohesion: 0.18
Nodes (10): 1. Generating RTL-derived DEF Files, 2. Running Parameter Sweeps Across Designs, 3. Extracting ML Features, Benchmark Summary, Directory Layout, Generated Dataset Summary, How to Use & Generate Data, ISPD 2015 — Detailed Routing-Driven Placement (DEF + LEF) (+2 more)

### Community 22 - "RTLign Orchestration & Dataset Generation Tutorial"
Cohesion: 0.18
Nodes (10): CLI Command Options Summary:, Example 1: Run Multi-Dimensional Sweeps on Specific Designs, Example 2: Single-Design Custom Run, 🗂️ Overview of All Orchestration Scripts, RTLign Orchestration & Dataset Generation Tutorial, 🛠️ Step 1: Understand the Components, 📁 Step 2: Prepare Your Input Files, 🚀 Step 3: Run the Generator (+2 more)

### Community 23 - "RTLign: AI Agent System Architecture & Guidelines"
Cohesion: 0.18
Nodes (10): 1. Product Summary, 1. Think Before Coding, 2. Simplicity First, 2. Technology Stack, 3. Project Structure, 3. Surgical Changes, 4. Agent Operational Guidelines, 4. Goal-Driven Execution (+2 more)

### Community 24 - "audit.py"
Cohesion: 0.08
Nodes (24): audit_layout(), AuditResult, check_layout(), main(), Layout auditor for the RTL legalizer. This module is the single source of truth…, Audit an output hex file against its input hex file., Outcome of one layout audit. Empty lists mean the property passed., True when no property failed and no structural error exists. (+16 more)

### Community 25 - "RTLign: ML-Assisted Simulated Annealing for RTL-Accelerated VLSI Macro Placement"
Cohesion: 0.25
Nodes (7): Datasets, Pipeline Architecture, Project Background & Problem Statement, Project Timeline, RTLign: ML-Assisted Simulated Annealing for RTL-Accelerated VLSI Macro Placement, Team P124, Tools & Technologies

### Community 26 - "ML Predictor"
Cohesion: 0.25
Nodes (7): 1. Train the Topological GNN, 2. Run Inference on a DEF/LEF Pair, 3. Evaluate End-to-End Metrics and Generate Layout Plots, Components, ML Predictor, Pipeline Architecture, Usage Examples

### Community 27 - "Direct CLI Usage"
Cohesion: 0.33
Nodes (5): Direct CLI Usage, Evaluating a Placed Layout:, Files, OpenROAD Scripts, Running Placement:

### Community 28 - "RTL Legalizer & Simulated Annealing Engine"
Cohesion: 0.15
Nodes (12): 1. Accelerated Verilator Execution (Recommended), 2. Interpreted Icarus Verilog Simulation, Architecture Overview, Build the executable:, Execution Modes, File Manifest, Hardware Memory Contract, Hardware Parameters (+4 more)

### Community 29 - "TestCheckLayout"
Cohesion: 0.07
Nodes (5): parametrize, Unit tests for rtl_legalizer/audit.py and rtl_legalizer/layout_gen.py., TestCheckLayout, TestHexIO, TestLayoutGen

### Community 30 - "run_verilator_legalizer"
Cohesion: 0.10
Nodes (15): build_verilator(), Any, Verilator Bridge for RTLign Simulated Annealing Legalizer. Provides high-speed…, Compile the Verilator simulation binary if needed., Execute the Verilator Simulated Annealing legalizer. Args: input_hex: Path to…, run_verilator_legalizer(), Phase 6 Automated Test Suite — Verilog Simulated Annealing Engine & Verilator…, Verify Verilator builds and legalizes dummy_layout.hex with 0 overlaps. (+7 more)

### Community 31 - "TestLegalizerFSM"
Cohesion: 0.18
Nodes (6): Unit testbenches for the rtl_legalizer Verilog modules (Icarus). -…, Compile a TB with iverilog, run with vvp, return (rc, stdout, stderr). sim_cwd…, run_icarus(), TestCollisionCheck, TestLegalizerFSM, TestSaCost

### Community 32 - "parse_lef_file"
Cohesion: 0.23
Nodes (12): extract_macro_dimensions(), parse_lef_file(), parse_lef_files(), extreme_aspect_ratio_strategy(), Property-based tests for LEF Parser Module These tests verify universal…, Generates extreme aspect ratio dimensions: - Tall cells: width:height > 3:1…, Dimension_Dict, LEF Parser Module for Real Cell Dimensions This module parses Library Exchange… (+4 more)

### Community 33 - "3. Findings"
Cohesion: 0.13
Nodes (14): 1. Verification spec, 2. Infrastructure added, 3. Findings, 4. Property results, 5. How to re-run, 6. Recommended next steps (out of scope here), BUG-1 (fixed): outer-loop hang for `NUM_MACROS == 1`, BUG-2 (fixed): infinite RESOLVE/CHECK loop on unresolvable pairs (+6 more)

### Community 34 - "test_golden_model.py"
Cohesion: 0.22
Nodes (6): compile_and_run(), parametrize, Staged validation of the Python golden model against the RTL. Stage 1:…, TestStage1Cost, TestStage2Greedy, TestStage3SA

### Community 35 - "TopologicalMacroDataset"
Cohesion: 0.17
Nodes (5): InMemoryDataset, TopologicalMacroDataset, x: [N, node_in_channels] edge_index: [2, E] edge_attr: [E, edge_in_channels], TopologicalMacroGNN, train()

### Community 36 - "test_dimension_dict_matches_source"
Cohesion: 0.32
Nodes (8): given, Property 14: Dimension Dict Matches Source Validates: Requirements 8.1 FOR ALL…, Property 15: Round-Trip Parsing Validates: Requirements 8.2 WHEN parsing then…, Property 13: Extreme Aspect Ratio Preservation Validates: Requirements 7.1 WHEN…, test_dimension_dict_matches_source(), test_extreme_aspect_ratio_preservation(), test_round_trip_parsing(), settings

### Community 37 - "TestParseLefFile"
Cohesion: 0.25
Nodes (5): Unit tests for parse_lef_file function., Test parsing a valid LEF file., Test that FileNotFoundError is raised for missing files., Test parsing LEF file without UNITS block (uses default)., TestParseLefFile

### Community 38 - "TestParseLefFiles"
Cohesion: 0.25
Nodes (5): Unit tests for parse_lef_files function., Test merging dimension dicts from multiple LEF files., Test that first definition wins for duplicate MACROs., Test that ValueError is raised when no MACROs found., TestParseLefFiles

### Community 39 - "tb_collision_check"
Cohesion: 0.40
Nodes (4): check, tb_collision_check, check, collision_check

### Community 40 - "tb_sa_cost"
Cohesion: 0.40
Nodes (4): tb_sa_cost, run_case, sa_cost, run_case

### Community 41 - "sa_engine"
Cohesion: 0.50
Nodes (3): lfsr32, sa_engine, sa_cost

### Community 42 - "sa_legalizer_top"
Cohesion: 0.50
Nodes (3): sa_legalizer_top, legalizer_fsm, sa_engine

## Knowledge Gaps
- **142 isolated node(s):** `collision_check`, `collision_check`, `sa_legalizer_top`, `run_overlap_audit`, `run_overlap_audit` (+137 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 353 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `parse_lef_files()` connect `parse_lef_file` to `FeatureExtractor`, `parse_def_to_hex`, `TestParseLefFiles`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `TestLEFDEFIntegration` connect `parse_def_to_hex` to `test_ispd2015_integration.py`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **What connects `collision_check`, `collision_check`, `sa_legalizer_top` to the rest of the system?**
  _142 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `FeatureExtractor` be split into smaller, more focused modules?**
  _Cohesion score 0.08139534883720931 - nodes in this community are weakly interconnected._
- **Should `test_ispd2015_integration.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07407407407407407 - nodes in this community are weakly interconnected._
- **Should `golden_model.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07657657657657657 - nodes in this community are weakly interconnected._
- **Should `RTLign — 6-Month Comprehensive Roadmap` be split into smaller, more focused modules?**
  _Cohesion score 0.10526315789473684 - nodes in this community are weakly interconnected._