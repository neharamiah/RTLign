# Graph Report - RTLign  (2026-09-06)

## Corpus Check
- 32 files · ~29,087 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 369 nodes · 427 edges · 29 communities (24 shown, 5 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 39 edges (avg confidence: 0.79)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7b937ce4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- parse_lef_file
- FeatureExtractor
- test_ispd2015_integration.py
- TopologicalMacroDataset
- TestExtractDatabaseUnits
- parse_def_to_hex
- TestParseLefFile
- test_lef_parser_cli.py
- TestConvertToDbUnits
- TestValidateDimension
- TestExtractMacroDimensions
- TestISPD2015LEFParsing
- hex_to_def.py
- data_generator.py
- rtl_to_def.py
- legalizer_tb
- find_first_file
- legalizer_fsm
- collision_check.v
- RTLign — Dataset Directory
- RTLign Orchestration & Dataset Generation Tutorial
- 4. Agent Operational Guidelines
- 3. Development Timeline
- RTLign: ML-Assisted Simulated Annealing for RTL-Accelerated VLSI Macro Placement
- ML Predictor
- OpenROAD Scripts
- RTL Legalizer Engine

## God Nodes (most connected - your core abstractions)
1. `FeatureExtractor` - 13 edges
2. `parse_lef_file()` - 12 edges
3. `extract_macro_dimensions()` - 11 edges
4. `RTLign — 6-Month Comprehensive Roadmap` - 11 edges
5. `extract_database_units()` - 10 edges
6. `convert_to_db_units()` - 10 edges
7. `4. Component Deep-Dives` - 10 edges
8. `parse_lef_files()` - 9 edges
9. `TestExtractDatabaseUnits` - 9 edges
10. `RTLign — Project Progress Document` - 9 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `parse_def_to_hex()`  [EXTRACTED]
  orchestration/master_run.py → ml_predictor/def_parser.py
- `main()` --calls--> `parse_lef_files()`  [EXTRACTED]
  orchestration/master_run.py → rtl_legalizer/lef_parser.py
- `test_dimension_dict_matches_source()` --calls--> `parse_lef_file()`  [INFERRED]
  rtl_legalizer/lef_parser_property_test.py → rtl_legalizer/lef_parser.py
- `test_extreme_aspect_ratio_preservation()` --calls--> `parse_lef_file()`  [INFERRED]
  rtl_legalizer/lef_parser_property_test.py → rtl_legalizer/lef_parser.py
- `test_round_trip_parsing()` --calls--> `parse_lef_file()`  [INFERRED]
  rtl_legalizer/lef_parser_property_test.py → rtl_legalizer/lef_parser.py

## Import Cycles
- None detected.

## Communities (29 total, 5 thin omitted)

### Community 0 - "parse_lef_file"
Cohesion: 0.10
Nodes (18): convert_to_db_units(), extreme_aspect_ratio_strategy(), Property-based tests for LEF Parser Module  These tests verify universal correct, Property 14: Dimension Dict Matches Source     Validates: Requirements 8.1, Property 15: Round-Trip Parsing     Validates: Requirements 8.2          WHEN pa, Generates extreme aspect ratio dimensions:     - Tall cells: width:height > 3:1, Property 13: Extreme Aspect Ratio Preservation     Validates: Requirements 7.1, test_dimension_dict_matches_source() (+10 more)

### Community 1 - "FeatureExtractor"
Cohesion: 0.13
Nodes (15): Any, DiGraph, FeatureExtractor, get_die_diagonal(), Parses LEFs to return macro dimensions and pin directions.         Returns: {des, Uses sparse matrix exponentiation to extract k-path and undirected graph edges., Safely extracts DIEAREA to compute the bounding box diagonal., break_cycles_dfs() (+7 more)

### Community 2 - "test_ispd2015_integration.py"
Cohesion: 0.07
Nodes (17): Integration tests with ISPD 2015 benchmarks.  Tests Requirements 6.1, 6.2, 6.3,, Requirement 7.1: Verify extreme aspect ratio cells handled correctly., Test 16.2: Full pipeline integration with real dimensions, Requirement 6.3: Legalizer FSM completes without deadlock.                  WHEN, Requirement 6.4: Output HEX contains non-uniform dimensions.                  WH, Test 16.3: Error handling scenarios, Requirement 5.3: Invalid LEF file path aborts pipeline.                  WHEN th, Test 16.1: LEF parsing with mgc_matrix_mult_2 design data (+9 more)

### Community 3 - "TopologicalMacroDataset"
Cohesion: 0.14
Nodes (5): InMemoryDataset, TopologicalMacroDataset, x: [N, node_in_channels]         edge_index: [2, E]         edge_attr: [E, edge_, TopologicalMacroGNN, train()

### Community 4 - "TestExtractDatabaseUnits"
Cohesion: 0.15
Nodes (11): extract_database_units(), Extract DATABASE MICRONS value from UNITS block.          LEF format:         UN, Unit tests for extract_database_units function., Test parsing a standard UNITS block with DATABASE MICRONS 1000., Test parsing with a different multiplier value., Test that None is returned when UNITS block is missing., Test that None is returned when DATABASE MICRONS is missing from UNITS block., Test that parsing is case-insensitive. (+3 more)

### Community 5 - "parse_def_to_hex"
Cohesion: 0.10
Nodes (19): parse_def_to_hex(), Dimension_Dict, Parse a DEF file and generate a .hex memory file for the hardware legalizer., main(), RTLign — Master Orchestration Script ===================================== Singl, Run a subprocess command with timing and error handling., run_step(), parse_lef_files() (+11 more)

### Community 6 - "TestParseLefFile"
Cohesion: 0.07
Nodes (29): Critical Milestones & Go/No-Go Decisions, Key Papers, Month 1: Foundations & Physical Design Literacy, Month 2: Supervised ML Predictor & Evaluation, Month 3: Simulated Annealing in RTL, Month 4: Integration, Scaling & Benchmarking, Month 5: Paper, Defense & Polish, Online Courses & Tutorials (+21 more)

### Community 7 - "test_lef_parser_cli.py"
Cohesion: 0.14
Nodes (13): Unit tests for LEF Parser CLI interface.  Tests the CLI implementation for Requi, Test that multiple LEF files can be parsed, Test that missing LEF file produces error, Test Requirement 10.1: --help shows usage information, Test Requirement 10.2: JSON output to stdout, Test Requirement 10.3: --output writes to specified file, Test Requirement 10.4: --verbose logs each MACRO name and dimensions, test_error_on_missing_file() (+5 more)

### Community 8 - "TestConvertToDbUnits"
Cohesion: 0.07
Nodes (28): 1. Project Overview, 2. Repository Structure, 4.1 Collision Check Module (`collision_check.v`), 4.2 LEF Parser (`lef_parser.py`), 4.3 DEF Parser (`def_parser.py`), 4.4 Legalizer FSM (`legalizer_fsm.v`), 4.5 Legalizer Testbench (`legalizer_tb.v`), 4.6 HEX → DEF Injector (`hex_to_def.py`) (+20 more)

### Community 9 - "TestValidateDimension"
Cohesion: 0.19
Nodes (9): Validate that a dimension is a positive integer within 32-bit range.          Ar, Unit tests for validate_dimension function., Test that positive values are validated as valid., Test that zero is rejected., Test that negative values are rejected., Test that values exceeding 32-bit limit are rejected., Test that max 32-bit value is accepted., TestValidateDimension (+1 more)

### Community 10 - "TestExtractMacroDimensions"
Cohesion: 0.10
Nodes (18): extract_macro_dimensions(), parse_lef_file(), Dimension_Dict, Extract MACRO SIZE statements from LEF content.          LEF format:         MAC, Parse a single LEF file and extract MACRO definitions.          Args:         le, Unit tests for LEF Parser Module  Tests the LEF parser functions for parsing DAT, Unit tests for extract_macro_dimensions function., Test extraction of a single MACRO block. (+10 more)

### Community 11 - "TestISPD2015LEFParsing"
Cohesion: 0.09
Nodes (21): 1. LEF Parser (`lef_parser.py`), 2. Dataset Generator (`data_generator.py`), 3. DEF Parser (`def_parser.py`), 4. Feature Extractor (`feature_extractor.py`), 5. SystemVerilog RTL Legalizer (`legalizer_fsm.v`), 6. HEX → DEF Injector (`hex_to_def.py`), How It Works, License (+13 more)

### Community 12 - "hex_to_def.py"
Cohesion: 0.38
Nodes (6): inject_coords_into_def(), main(), RTLign — HEX → DEF Injector ============================ Reads a legalized .hex, Read the .hex file and return a list of (x, y) tuples.          Each macro occup, Patch legalized coordinates into a DEF file.          Strategy:     - Walk throu, read_hex_coordinates()

### Community 13 - "data_generator.py"
Cohesion: 0.48
Nodes (6): extract_metrics_from_log(), find_benchmarks(), main(), Runs a single OpenROAD placement job via subprocess., run_openroad_placement(), write_summary_report()

### Community 14 - "rtl_to_def.py"
Cohesion: 0.60
Nodes (4): find_rtl_files(), main(), Finds all .v and .sv files in the given directory recursively, excluding testben, run_pipeline()

### Community 15 - "legalizer_tb"
Cohesion: 0.50
Nodes (3): legalizer_fsm, legalizer_tb, run_overlap_audit

### Community 16 - "find_first_file"
Cohesion: 0.67
Nodes (3): find_first_file(), main(), Utility to find the first matching file from a list of glob patterns.

### Community 21 - "RTLign — Dataset Directory"
Cohesion: 0.18
Nodes (10): 1. Generating RTL-derived DEF Files, 2. Running Parameter Sweeps Across Designs, 3. Extracting ML Features, Benchmark Summary, Directory Layout, Generated Dataset Summary, How to Use & Generate Data, ISPD 2015 — Detailed Routing-Driven Placement (DEF + LEF) (+2 more)

### Community 22 - "RTLign Orchestration & Dataset Generation Tutorial"
Cohesion: 0.18
Nodes (10): CLI Command Options Summary:, Example 1: Run Multi-Dimensional Sweeps on Specific Designs, Example 2: Single-Design Custom Run, RTLign Orchestration & Dataset Generation Tutorial, 🛠️ Step 1: Understand the Components, 📂 Step 2: Prepare Your Input Files, 🚀 Step 3: Run the Generator, 🔍 Step 4: Check Your Outputs (+2 more)

### Community 23 - "4. Agent Operational Guidelines"
Cohesion: 0.20
Nodes (9): 1. Product Summary, 1. Think Before Coding, 2. Simplicity First, 2. Technology Stack, 3. Project Structure, 3. Surgical Changes, 4. Agent Operational Guidelines, 4. Goal-Driven Execution (+1 more)

### Community 24 - "3. Development Timeline"
Cohesion: 0.20
Nodes (10): 3. Development Timeline, Phase 0.5: Data Pipeline & DEF Export (Commits `4f28874` → `cee702f`), Phase 0.75: Legalizer FSM v1 (Commits `88a61b0` → `f0a8634`), Phase 0.9: Gitignore & Cleanup (Commits `31fd55e` → `eb3d7eb`), Phase 0: Architecture & Initial Scaffolding (Commits `4c49e44` → `380851e`), Phase 1: Fix Foundations & End-to-End Pipeline (Completed), Phase 2: Real Dimensions & Improved Resolution (Commits `af11957` → `b97ae8d`), Phase 3: Robust Testing & Dataset Preparation (Commits `ba8af81` → `ee64e51`) (+2 more)

### Community 25 - "RTLign: ML-Assisted Simulated Annealing for RTL-Accelerated VLSI Macro Placement"
Cohesion: 0.25
Nodes (7): Datasets, Pipeline Architecture, Project Background & Problem Statement, Project Timeline, RTLign: ML-Assisted Simulated Annealing for RTL-Accelerated VLSI Macro Placement, Team P124, Tools & Technologies

## Knowledge Gaps
- **103 isolated node(s):** `collision_check`, `collision_check`, `legalizer_fsm`, `run_overlap_audit`, `1. Product Summary` (+98 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TestLEFDEFIntegration` connect `parse_def_to_hex` to `test_ispd2015_integration.py`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `extract_database_units()` connect `TestExtractDatabaseUnits` to `TestExtractMacroDimensions`, `parse_def_to_hex`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `parse_lef_file()` (e.g. with `test_dimension_dict_matches_source()` and `test_extreme_aspect_ratio_preservation()`) actually correct?**
  _`parse_lef_file()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `extract_macro_dimensions()` (e.g. with `.test_case_insensitive()` and `.test_invalid_dimension_skipped()`) actually correct?**
  _`extract_macro_dimensions()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `extract_database_units()` (e.g. with `.test_case_insensitive()` and `.test_different_multiplier()`) actually correct?**
  _`extract_database_units()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `collision_check`, `collision_check`, `legalizer_fsm` to the rest of the system?**
  _103 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `parse_lef_file` be split into smaller, more focused modules?**
  _Cohesion score 0.10144927536231885 - nodes in this community are weakly interconnected._