# Implementation Plan: LEF Parser for Real Cell Dimensions

## Overview

This implementation adds a LEF parser module to extract real cell dimensions from Library Exchange Format files, enabling physically accurate collision detection in the RTLign hardware legalizer. The work involves creating a new `lef_parser.py` module, modifying the existing `def_parser.py` to accept dimension lookup, and updating the pipeline orchestration.

## Tasks

- [x] 1. Create LEF parser module with core interfaces
  - Create `rtl_legalizer/lef_parser.py` with type aliases and function signatures
  - Define `Dimension_Dict = Dict[str, Tuple[int, int]]` type alias
  - Implement `parse_lef_files()` function stub with docstring
  - Implement `parse_lef_file()` function stub with docstring
  - Implement `extract_database_units()` function stub with docstring
  - Implement `extract_macro_dimensions()` function stub with docstring
  - Implement `convert_to_db_units()` function stub with docstring
  - Implement `validate_dimension()` function stub with docstring
  - _Requirements: 1.1, 1.2, 1.3, 1.5_

- [x] 2. Implement DATABASE MICRONS extraction
  - [x] 2.1 Implement `extract_database_units()` function
    - Parse UNITS block with regex: `DATABASE MICRONS N ;`
    - Return integer multiplier or None if not found
    - Handle missing UNITS block gracefully
    - _Requirements: 1.5_

  - [ ]* 2.2 Write property test for DATABASE MICRONS extraction
    - **Property 5: DATABASE MICRONS Extraction**
    - **Validates: Requirements 1.5**

- [x] 3. Implement unit conversion logic
  - [x] 3.1 Implement `convert_to_db_units()` function
    - Convert floating-point microns to integer database units
    - Apply `round(value_microns * db_units)` formula
    - Handle None db_units with default 1000
    - _Requirements: 8.3_

  - [ ]* 3.2 Write property test for unit conversion correctness
    - **Property 16: Unit Conversion Correctness**
    - **Validates: Requirements 8.3**

- [x] 4. Implement dimension validation
  - [x] 4.1 Implement `validate_dimension()` function
    - Validate width/height are positive (> 0)
    - Validate dimensions fit in 32-bit unsigned integer (< 2^32)
    - Log errors for invalid dimensions
    - Return True if valid, False otherwise
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 4.2 Write property test for positive dimension validation
    - **Property 11: Dimension Validation (Positive Values)**
    - **Validates: Requirements 4.1, 4.2**

  - [ ]* 4.3 Write property test for 32-bit overflow validation
    - **Property 12: Dimension Validation (32-Bit Overflow)**
    - **Validates: Requirements 4.3, 4.4**

- [x] 5. Implement MACRO SIZE extraction
  - [x] 5.1 Implement `extract_macro_dimensions()` function
    - Parse MACRO blocks with regex for SIZE statement
    - Extract width and height from `SIZE W BY H ;`
    - Convert to database units using `convert_to_db_units()`
    - Validate dimensions using `validate_dimension()`
    - Skip MACROs without SIZE statement or with invalid dimensions
    - Return Dimension_Dict mapping cell type to (width, height)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 4.1, 4.2, 4.3, 4.4_

  - [ ]* 5.2 Write property test for MACRO extraction completeness
    - **Property 1: MACRO Extraction Completeness**
    - **Validates: Requirements 1.1**

  - [ ]* 5.3 Write property test for dimension dict structure
    - **Property 2: Dimension Dict Structure**
    - **Validates: Requirements 1.2**

  - [ ]* 5.4 Write property test for SIZE statement parsing
    - **Property 3: SIZE Statement Parsing**
    - **Validates: Requirements 1.3**

  - [ ]* 5.5 Write property test for MACRO without SIZE handling
    - **Property 4: MACRO Without SIZE Handling**
    - **Validates: Requirements 1.4**

- [x] 6. Implement single LEF file parsing
  - [x] 6.1 Implement `parse_lef_file()` function
    - Read LEF file content (streaming line-by-line for large files)
    - Call `extract_database_units()` to get multiplier
    - Call `extract_macro_dimensions()` to get dimension dict
    - Return tuple of (dimension_dict, database_units_multiplier)
    - Raise FileNotFoundError for missing files
    - _Requirements: 1.1, 1.5, 9.2_

  - [ ]* 6.2 Write unit tests for single LEF file parsing
    - Test valid LEF file with multiple MACROs
    - Test LEF file without UNITS block
    - Test FileNotFoundError for missing file
    - _Requirements: 1.1, 1.5, 9.2_

- [x] 7. Implement multiple LEF file parsing with merge
  - [x] 7.1 Implement `parse_lef_files()` function
    - Iterate over LEF file paths
    - Call `parse_lef_file()` for each
    - Merge dimension dicts with first-wins strategy for duplicates
    - Log warning for duplicate MACRO names
    - Support both absolute and relative file paths
    - Return merged Dimension_Dict
    - Raise FileNotFoundError if any file missing
    - Raise ValueError if no MACROs found across all files
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ]* 7.2 Write property test for multiple LEF file merge
    - **Property 6: Multiple LEF File Merge**
    - **Validates: Requirements 2.1**

  - [ ]* 7.3 Write property test for duplicate MACRO first-wins
    - **Property 7: Duplicate MACRO First-Wins**
    - **Validates: Requirements 2.2**

  - [ ]* 7.4 Write unit tests for file path handling
    - Test absolute paths
    - Test relative paths
    - _Requirements: 2.3_

- [x] 8. Implement malformed LEF resilience
  - [x] 8.1 Add error recovery to `extract_macro_dimensions()`
    - Skip malformed MACRO blocks and continue parsing
    - Track skipped MACROs with reasons
    - Return successfully parsed MACROs with error summary
    - _Requirements: 9.1, 9.3, 9.4_

  - [ ]* 8.2 Write property test for malformed MACRO resilience
    - **Property 17: Malformed MACRO Resilience**
    - **Validates: Requirements 9.3, 9.4**

  - [ ]* 8.3 Write unit tests for error handling
    - Test syntax error reporting with line numbers
    - Test truncated MACRO block handling
    - Test partial success with error summary
    - _Requirements: 9.1, 9.3, 9.4_

- [x] 9. Checkpoint - Verify LEF parser module
  - Run all unit tests and property tests
  - Ensure tests pass, ask the user if questions arise.

- [x] 10. Modify DEF parser to accept dimension dictionary
  - [x] 10.1 Update `parse_def_to_hex()` function signature
    - Add `dimension_dict: Optional[Dimension_Dict] = None` parameter
    - Extract cell type from COMPONENT line using regex
    - Look up cell type in dimension_dict for width/height
    - Fall back to DEFAULT_WIDTH=100, DEFAULT_HEIGHT=100 if not found
    - Log warning for unknown cell types when dimension_dict provided
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ]* 10.2 Write property test for DEF component dimension lookup
    - **Property 8: DEF Component Dimension Lookup**
    - **Validates: Requirements 3.1, 3.2**

  - [ ]* 10.3 Write property test for unknown cell type fallback
    - **Property 9: Unknown Cell Type Fallback**
    - **Validates: Requirements 3.3**

  - [ ]* 10.4 Write property test for hex output format
    - **Property 10: Hex Output Format**
    - **Validates: Requirements 3.4**

  - [ ]* 10.5 Write unit tests for DEF parser modifications
    - Test dimension lookup for known cell type
    - Test fallback to defaults for unknown cell type
    - Test backward compatibility with None dimension_dict
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 11. Add round-trip verification properties
  - [ ]* 11.1 Write property test for dimension dict matches source
    - **Property 14: Dimension Dict Matches Source**
    - **Validates: Requirements 8.1**

  - [ ]* 11.2 Write property test for round-trip parsing
    - **Property 15: Round-Trip Parsing**
    - **Validates: Requirements 8.2**

- [x] 12. Add extreme aspect ratio handling
  - [ ]* 12.1 Write property test for extreme aspect ratio preservation
    - **Property 13: Extreme Aspect Ratio Preservation**
    - **Validates: Requirements 7.1**

- [x] 13. Update pipeline orchestration
  - [x] 13.1 Add LEF parsing stage to `master_run.py`
    - Import `parse_lef_files` from `rtl_legalizer.lef_parser`
    - Define LEF file paths (tech.lef, cells.lef)
    - Add Stage 1: LEF Parser before DEF parsing
    - Pass dimension_dict to DEF parser
    - Handle FileNotFoundError and ValueError from LEF parser
    - Update stage numbering from 3 to 4 total stages
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x]* 13.2 Write integration tests for pipeline orchestration
    - Test LEF parser runs before DEF parser (`test_ispd2015_integration.py`)
    - Test dimension_dict is passed correctly (`TestLEFDEFIntegration`)
    - Test pipeline aborts on LEF parse failure (`TestErrorScenarios`)
    - Test pipeline continues with warning on empty result (`TestErrorScenarios`)
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 14. Implement CLI interface for standalone use
  - [x] 14.1 Add argparse CLI to `lef_parser.py`
    - Add `__main__` block with argparse setup
    - Support positional LEF file arguments (one or more)
    - Support `--output` flag for JSON file output
    - Support `--verbose` flag for per-MACRO logging
    - Support `--help` for usage information
    - Output JSON to stdout by default
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [x]* 14.2 Write unit tests for CLI interface
    - Test `--help` displays usage information (`test_lef_parser_cli.py`)
    - Test JSON output to stdout (`test_json_output_to_stdout`)
    - Test `--output` writes to file (`test_output_writes_to_file`)
    - Test `--verbose` logs each MACRO (`test_verbose_logs_each_macro`)
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [x] 15. Checkpoint - Verify module integration
  - Run all unit tests and property tests
  - Ensure tests pass, ask the user if questions arise.

- [x] 16. Integration tests with ISPD 2015 benchmarks
  - [x] 16.1 Test with mgc_matrix_mult_2 design data
    - Parse tech.lef and cells.lef (`test_parse_tech_and_cells_lef_successfully`)
    - Verify at least 100 cell types extracted (`test_extract_at_least_100_cell_types`)
    - Verify specific known dimensions ms00f80=1600×2000, oa22f80=204800×2000 (`test_verify_specific_known_dimensions`)
    - Verify extreme aspect ratio cells handled correctly (`test_verify_extreme_aspect_ratio_cells`)
    - _Requirements: 6.1, 6.2, 6.4_

  - [x] 16.2 Test full pipeline with real dimensions
    - Run master_run.py with ISPD 2015 benchmark (`test_full_pipeline_completes_without_deadlock`)
    - Verify legalizer completes without deadlock (60s timeout)
    - Verify output HEX contains non-uniform dimensions (`test_output_hex_contains_non_uniform_dimensions`)
    - _Requirements: 6.3, 6.4_

  - [x] 16.3 Test error scenarios
    - Test invalid LEF file path aborts pipeline (`test_invalid_lef_file_path_aborts_pipeline`)
    - Test LEF with no MACROs proceeds with warning (`test_lef_with_no_macros_proceeds_with_warning`)
    - _Requirements: 5.3, 5.4_

- [x] 17. Final checkpoint - Complete validation
  - All 47 tests pass: 10 integration, 6 CLI, 25 unit, 3 property-based (Hypothesis)
  - Full pipeline runs end-to-end in <60s with ISPD 2015 mgc_matrix_mult_2 benchmark
  - Zero regressions. Feature complete.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design
- Unit tests validate specific examples and edge cases
- Integration tests verify end-to-end behavior with real benchmark data
