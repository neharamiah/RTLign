# Graph Report - /home/ratik/Projects/RTLign  (2026-08-14)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 230 nodes · 313 edges · 21 communities (19 shown, 2 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 3 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `fc564bfd`
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

## God Nodes (most connected - your core abstractions)
1. `parse_lef_file()` - 14 edges
2. `extract_macro_dimensions()` - 13 edges
3. `FeatureExtractor` - 12 edges
4. `convert_to_db_units()` - 12 edges
5. `extract_database_units()` - 11 edges
6. `parse_lef_files()` - 11 edges
7. `TopologicalMacroDataset` - 9 edges
8. `TestExtractDatabaseUnits` - 9 edges
9. `validate_dimension()` - 9 edges
10. `TopologicalMacroGNN` - 7 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `parse_lef_files()`  [EXTRACTED]
  orchestration/master_run.py → rtl_legalizer/lef_parser.py
- `main()` --calls--> `parse_def_to_hex()`  [EXTRACTED]
  orchestration/master_run.py → ml_predictor/def_parser.py
- `run_prediction()` --calls--> `TopologicalMacroGNN`  [EXTRACTED]
  ml_predictor/predict.py → ml_predictor/model.py
- `train()` --calls--> `TopologicalMacroDataset`  [EXTRACTED]
  ml_predictor/train_nn.py → ml_predictor/dataset.py
- `train()` --calls--> `TopologicalMacroGNN`  [EXTRACTED]
  ml_predictor/train_nn.py → ml_predictor/model.py

## Import Cycles
- None detected.

## Communities (21 total, 2 thin omitted)

### Community 0 - "parse_lef_file"
Cohesion: 0.13
Nodes (26): given, convert_to_db_units(), extract_database_units(), extract_macro_dimensions(), parse_lef_file(), parse_lef_files(), extreme_aspect_ratio_strategy(), Property-based tests for LEF Parser Module These tests verify universal… (+18 more)

### Community 1 - "FeatureExtractor"
Cohesion: 0.13
Nodes (15): Any, DiGraph, FeatureExtractor, get_die_diagonal(), Parses LEFs to return macro dimensions and pin directions. Returns: {design:…, Uses sparse matrix exponentiation to extract k-path and undirected graph edges., Safely extracts DIEAREA to compute the bounding box diagonal., break_cycles_dfs() (+7 more)

### Community 2 - "test_ispd2015_integration.py"
Cohesion: 0.12
Nodes (11): Integration tests with ISPD 2015 benchmarks. Tests Requirements 6.1, 6.2, 6.3,…, Test 16.2: Full pipeline integration with real dimensions, Requirement 6.3: Legalizer FSM completes without deadlock. WHEN running the…, Requirement 6.4: Output HEX contains non-uniform dimensions. WHEN legalization…, Test 16.3: Error handling scenarios, Requirement 5.3: Invalid LEF file path aborts pipeline. WHEN the LEF_Parser…, Requirement 5.4: LEF with no MACROs proceeds with warning. WHEN the LEF_Parser…, Test Topological Pipeline Parquet output schemas and assertions (+3 more)

### Community 3 - "TopologicalMacroDataset"
Cohesion: 0.16
Nodes (5): InMemoryDataset, TopologicalMacroDataset, x: [N, node_in_channels] edge_index: [2, E] edge_attr: [E, edge_in_channels], TopologicalMacroGNN, train()

### Community 4 - "TestExtractDatabaseUnits"
Cohesion: 0.12
Nodes (9): Unit tests for extract_database_units function., Test parsing a standard UNITS block with DATABASE MICRONS 1000., Test parsing with a different multiplier value., Test that None is returned when UNITS block is missing., Test that None is returned when DATABASE MICRONS is missing from UNITS block., Test that parsing is case-insensitive., Test handling of various whitespace patterns., Test with a realistic LEF file format from ISPD benchmarks. (+1 more)

### Community 5 - "parse_def_to_hex"
Cohesion: 0.17
Nodes (11): parse_def_to_hex(), Dimension_Dict, Parse a DEF file and generate a .hex memory file for the hardware legalizer.…, main(), RTLign — Master Orchestration Script =====================================…, Run a subprocess command with timing and error handling., run_step(), Additional integration tests for LEF + DEF pipeline (+3 more)

### Community 6 - "TestParseLefFile"
Cohesion: 0.13
Nodes (9): Unit tests for parse_lef_file function., Test parsing a valid LEF file., Test that FileNotFoundError is raised for missing files., Test parsing LEF file without UNITS block (uses default)., Test merging dimension dicts from multiple LEF files., Test that first definition wins for duplicate MACROs., Test that ValueError is raised when no MACROs found., TestParseLefFile (+1 more)

### Community 7 - "test_lef_parser_cli.py"
Cohesion: 0.14
Nodes (13): Unit tests for LEF Parser CLI interface. Tests the CLI implementation for…, Test that multiple LEF files can be parsed, Test that missing LEF file produces error, Test Requirement 10.1: --help shows usage information, Test Requirement 10.2: JSON output to stdout, Test Requirement 10.3: --output writes to specified file, Test Requirement 10.4: --verbose logs each MACRO name and dimensions, test_error_on_missing_file() (+5 more)

### Community 8 - "TestConvertToDbUnits"
Cohesion: 0.17
Nodes (7): Unit tests for convert_to_db_units function., Test basic unit conversion with 1000 multiplier., Test that None db_units defaults to 1000., Test conversion with fractional micron values., Test that rounding is applied correctly., Test conversion with different database unit multipliers., TestConvertToDbUnits

### Community 9 - "TestValidateDimension"
Cohesion: 0.17
Nodes (7): Unit tests for validate_dimension function., Test that positive values are validated as valid., Test that zero is rejected., Test that negative values are rejected., Test that values exceeding 32-bit limit are rejected., Test that max 32-bit value is accepted., TestValidateDimension

### Community 10 - "TestExtractMacroDimensions"
Cohesion: 0.17
Nodes (7): Unit tests for extract_macro_dimensions function., Test extraction of a single MACRO block., Test extraction of multiple MACRO blocks., Test that MACROs without SIZE statement are skipped., Test that SIZE parsing is case-insensitive., Test that MACROs with invalid dimensions are skipped., TestExtractMacroDimensions

### Community 11 - "TestISPD2015LEFParsing"
Cohesion: 0.20
Nodes (6): Requirement 7.1: Verify extreme aspect ratio cells handled correctly. WHEN…, Test 16.1: LEF parsing with mgc_matrix_mult_2 design data, Requirement 6.1: Parse tech.lef and cells.lef successfully. WHEN running the…, Requirement 6.2: Extract at least 100 distinct Cell_Type definitions. WHEN…, Requirement 6.4: Verify specific known dimensions (ms00f80, oa22f80). WHEN…, TestISPD2015LEFParsing

### Community 12 - "hex_to_def.py"
Cohesion: 0.38
Nodes (6): inject_coords_into_def(), main(), RTLign — HEX → DEF Injector ============================ Reads a legalized .hex…, Read the .hex file and return a list of (x, y) tuples. Each macro occupies 4…, Patch legalized coordinates into a DEF file. Strategy: - Walk through the…, read_hex_coordinates()

### Community 13 - "data_generator.py"
Cohesion: 0.48
Nodes (6): extract_metrics_from_log(), find_benchmarks(), main(), Runs a single OpenROAD placement job via subprocess., run_openroad_placement(), write_summary_report()

### Community 14 - "rtl_to_def.py"
Cohesion: 0.60
Nodes (4): find_rtl_files(), main(), Finds all .v and .sv files in the given directory recursively, excluding…, run_pipeline()

### Community 15 - "legalizer_tb"
Cohesion: 0.50
Nodes (3): legalizer_fsm, legalizer_tb, run_overlap_audit

### Community 16 - "find_first_file"
Cohesion: 0.67
Nodes (3): find_first_file(), main(), Utility to find the first matching file from a list of glob patterns.

## Knowledge Gaps
- **4 isolated node(s):** `legalizer_fsm`, `run_overlap_audit`, `collision_check`, `collision_check`
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TestLEFDEFIntegration` connect `parse_def_to_hex` to `test_ispd2015_integration.py`?**
  _High betweenness centrality (0.118) - this node is a cross-community bridge._
- **Why does `parse_lef_files()` connect `parse_lef_file` to `parse_def_to_hex`, `TestParseLefFile`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **What connects `legalizer_fsm`, `run_overlap_audit`, `collision_check` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `parse_lef_file` be split into smaller, more focused modules?**
  _Cohesion score 0.1330049261083744 - nodes in this community are weakly interconnected._
- **Should `FeatureExtractor` be split into smaller, more focused modules?**
  _Cohesion score 0.1282051282051282 - nodes in this community are weakly interconnected._
- **Should `test_ispd2015_integration.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11764705882352941 - nodes in this community are weakly interconnected._
- **Should `TestExtractDatabaseUnits` be split into smaller, more focused modules?**
  _Cohesion score 0.125 - nodes in this community are weakly interconnected._