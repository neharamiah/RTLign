# Graph Report - .  (2026-08-03)

## Corpus Check
- Corpus is ~26,485 words - fits in a single context window. You may not need a graph.

## Summary
- 204 nodes · 271 edges · 17 communities (15 shown, 2 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 3 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Pipeline Master Orchestration
- LEF Parser & Property Tests
- ISPD 2015 Integration Tests
- ML Feature Extraction
- LEF Units & Dimension Extraction
- LEF Parser CLI Tests
- LEF Parser Extended Property Tests
- DEF to HEX Parser
- LEF Parser Unit Tests
- HEX to DEF Injector
- Data Generator & Metrics Extraction
- RTL to DEF Pipeline
- Verilog Legalizer Testbench
- Verilog Legalizer FSM Module
- Verilog Collision Check Module

## God Nodes (most connected - your core abstractions)
1. `parse_lef_file()` - 14 edges
2. `extract_macro_dimensions()` - 13 edges
3. `FeatureExtractor` - 12 edges
4. `convert_to_db_units()` - 12 edges
5. `parse_lef_files()` - 11 edges
6. `extract_database_units()` - 11 edges
7. `validate_dimension()` - 9 edges
8. `TestExtractDatabaseUnits` - 9 edges
9. `parse_def_to_hex()` - 7 edges
10. `TestConvertToDbUnits` - 7 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `parse_def_to_hex()`  [EXTRACTED]
  orchestration/master_run.py → ml_predictor/def_parser.py
- `main()` --calls--> `parse_lef_files()`  [EXTRACTED]
  orchestration/master_run.py → rtl_legalizer/lef_parser.py
- `test_dimension_dict_matches_source()` --calls--> `parse_lef_file()`  [EXTRACTED]
  rtl_legalizer/lef_parser_property_test.py → rtl_legalizer/lef_parser.py
- `test_extreme_aspect_ratio_preservation()` --calls--> `parse_lef_file()`  [EXTRACTED]
  rtl_legalizer/lef_parser_property_test.py → rtl_legalizer/lef_parser.py
- `test_round_trip_parsing()` --calls--> `parse_lef_file()`  [EXTRACTED]
  rtl_legalizer/lef_parser_property_test.py → rtl_legalizer/lef_parser.py

## Import Cycles
- None detected.

## Communities (17 total, 2 thin omitted)

### Community 0 - "Pipeline Master Orchestration"
Cohesion: 0.09
Nodes (22): main(), RTLign — Master Orchestration Script =====================================…, Run a subprocess command with timing and error handling., run_step(), parse_lef_files(), LEF Parser Module for Real Cell Dimensions This module parses Library Exchange…, Validate that a dimension is a positive integer within 32-bit range. Args:…, Parse one or more LEF files and return a merged dimension dictionary. Args:… (+14 more)

### Community 1 - "LEF Parser & Property Tests"
Cohesion: 0.10
Nodes (25): given, convert_to_db_units(), extract_macro_dimensions(), parse_lef_file(), extreme_aspect_ratio_strategy(), Property-based tests for LEF Parser Module These tests verify universal…, Property 14: Dimension Dict Matches Source Validates: Requirements 8.1 FOR ALL…, Property 15: Round-Trip Parsing Validates: Requirements 8.2 WHEN parsing then… (+17 more)

### Community 2 - "ISPD 2015 Integration Tests"
Cohesion: 0.08
Nodes (15): Integration tests with ISPD 2015 benchmarks. Tests Requirements 6.1, 6.2, 6.3,…, Requirement 7.1: Verify extreme aspect ratio cells handled correctly. WHEN…, Test 16.2: Full pipeline integration with real dimensions, Requirement 6.3: Legalizer FSM completes without deadlock. WHEN running the…, Requirement 6.4: Output HEX contains non-uniform dimensions. WHEN legalization…, Test 16.3: Error handling scenarios, Requirement 5.3: Invalid LEF file path aborts pipeline. WHEN the LEF_Parser…, Test 16.1: LEF parsing with mgc_matrix_mult_2 design data (+7 more)

### Community 3 - "ML Feature Extraction"
Cohesion: 0.13
Nodes (12): Any, FeatureExtractor, Scans workspace directories to discover all generated DEF files., Rebuilds or extends dataset_summary.csv to ensure all discovered DEFs are…, Locates the corresponding LEF file for a given design name., Parses cell libraries (LEF files) for the specified designs to identify…, Parses the COMPONENTS section of a DEF file and returns placed cell instances.…, Parses the NETS section of a DEF file and extracts macro-to-macro connectivity.… (+4 more)

### Community 4 - "LEF Units & Dimension Extraction"
Cohesion: 0.15
Nodes (11): extract_database_units(), Extract DATABASE MICRONS value from UNITS block. LEF format: UNITS DATABASE…, Unit tests for extract_database_units function., Test parsing a standard UNITS block with DATABASE MICRONS 1000., Test parsing with a different multiplier value., Test that None is returned when UNITS block is missing., Test that None is returned when DATABASE MICRONS is missing from UNITS block., Test that parsing is case-insensitive. (+3 more)

### Community 5 - "LEF Parser CLI Tests"
Cohesion: 0.14
Nodes (13): Unit tests for LEF Parser CLI interface. Tests the CLI implementation for…, Test that multiple LEF files can be parsed, Test that missing LEF file produces error, Test Requirement 10.1: --help shows usage information, Test Requirement 10.2: JSON output to stdout, Test Requirement 10.3: --output writes to specified file, Test Requirement 10.4: --verbose logs each MACRO name and dimensions, test_error_on_missing_file() (+5 more)

### Community 6 - "LEF Parser Extended Property Tests"
Cohesion: 0.17
Nodes (7): Unit tests for extract_macro_dimensions function., Test extraction of a single MACRO block., Test extraction of multiple MACRO blocks., Test that MACROs without SIZE statement are skipped., Test that SIZE parsing is case-insensitive., Test that MACROs with invalid dimensions are skipped., TestExtractMacroDimensions

### Community 7 - "DEF to HEX Parser"
Cohesion: 0.22
Nodes (7): parse_def_to_hex(), Dimension_Dict, Parse a DEF file and generate a .hex memory file for the hardware legalizer.…, Additional integration tests for LEF + DEF pipeline, Test that DEF parser correctly uses real dimensions from LEF. WHEN parsing a…, Test that DEF parser falls back to default dimensions for unknown cells. WHEN…, TestLEFDEFIntegration

### Community 8 - "LEF Parser Unit Tests"
Cohesion: 0.25
Nodes (5): Unit tests for parse_lef_file function., Test parsing a valid LEF file., Test that FileNotFoundError is raised for missing files., Test parsing LEF file without UNITS block (uses default)., TestParseLefFile

### Community 9 - "HEX to DEF Injector"
Cohesion: 0.38
Nodes (6): inject_coords_into_def(), main(), RTLign — HEX → DEF Injector ============================ Reads a legalized .hex…, Read the .hex file and return a list of (x, y) tuples. Each macro occupies 4…, Patch legalized coordinates into a DEF file. Strategy: - Walk through the…, read_hex_coordinates()

### Community 10 - "Data Generator & Metrics Extraction"
Cohesion: 0.48
Nodes (6): extract_metrics_from_log(), find_benchmarks(), main(), Runs a single OpenROAD placement job via subprocess., run_openroad_placement(), write_summary_report()

### Community 11 - "RTL to DEF Pipeline"
Cohesion: 0.60
Nodes (4): find_rtl_files(), main(), Finds all .v and .sv files in the given directory recursively, excluding…, run_pipeline()

### Community 12 - "Verilog Legalizer Testbench"
Cohesion: 0.50
Nodes (3): legalizer_fsm, legalizer_tb, run_overlap_audit

## Knowledge Gaps
- **4 isolated node(s):** `collision_check`, `collision_check`, `legalizer_fsm`, `run_overlap_audit`
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `parse_def_to_hex()` connect `DEF to HEX Parser` to `Pipeline Master Orchestration`?**
  _High betweenness centrality (0.164) - this node is a cross-community bridge._
- **Why does `TestLEFDEFIntegration` connect `DEF to HEX Parser` to `ISPD 2015 Integration Tests`?**
  _High betweenness centrality (0.135) - this node is a cross-community bridge._
- **Why does `parse_lef_files()` connect `Pipeline Master Orchestration` to `LEF Parser & Property Tests`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **What connects `collision_check`, `collision_check`, `legalizer_fsm` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Pipeline Master Orchestration` be split into smaller, more focused modules?**
  _Cohesion score 0.08522727272727272 - nodes in this community are weakly interconnected._
- **Should `LEF Parser & Property Tests` be split into smaller, more focused modules?**
  _Cohesion score 0.0989247311827957 - nodes in this community are weakly interconnected._
- **Should `ISPD 2015 Integration Tests` be split into smaller, more focused modules?**
  _Cohesion score 0.08333333333333333 - nodes in this community are weakly interconnected._