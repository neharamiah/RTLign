# Requirements Document

## Introduction

This feature adds real cell dimension extraction from LEF library files to the RTLign pipeline. Currently, the pipeline uses hardcoded 100×100 placeholder dimensions for collision detection. This causes incorrect overlap calculations when legalizing placements with actual cell geometries, which can be tall and thin (e.g., 380×1400) rather than square. The LEF parser will extract actual cell widths and heights from MACRO blocks, enabling physically accurate legalization.

## Glossary

- **LEF_File**: A Library Exchange Format file containing physical library data including MACRO definitions with cell dimensions, pin locations, and routing information
- **DEF_File**: A Design Exchange Format file containing the placed design with component instances and their coordinates
- **MACRO_Block**: A LEF construct defining a standard cell or macro cell with properties including SIZE (width and height)
- **Cell_Type**: The master cell name (e.g., `ms00f80`, `oa22f80`) that defines the dimension template for a component instance
- **Component_Instance**: A specific instantiation of a Cell_Type in a DEF file with a unique name and placement coordinates
- **Dimension_Dict**: A Python dictionary mapping Cell_Type names to their (width, height) tuples extracted from LEF files
- **Database_Units**: The coordinate system units defined in LEF (e.g., 1000 database units per micron)
- **LEF_Parser**: Python module that reads LEF files and extracts MACRO SIZE information into a Dimension_Dict
- **DEF_Parser**: Python module that reads DEF files and extracts component placements, now enhanced to cross-reference with LEF dimensions
- **Legalizer_FSM**: Verilog hardware module that resolves placement overlaps using AABB collision detection

## Requirements

### Requirement 1: Parse LEF MACRO SIZE Statements

**User Story:** As a developer, I want to parse LEF files to extract cell dimensions from MACRO blocks, so that the pipeline uses physically accurate geometry.

#### Acceptance Criteria

1. WHEN a valid LEF file is provided, THE LEF_Parser SHALL extract all MACRO blocks and their SIZE statements
2. THE LEF_Parser SHALL return a Dimension_Dict mapping each Cell_Type name to its (width, height) tuple in database units
3. WHEN parsing a MACRO block with `SIZE W BY H`, THE LEF_Parser SHALL extract W as width and H as height
4. WHEN a MACRO block lacks a SIZE statement, THE LEF_Parser SHALL skip that MACRO without error
5. WHEN the LEF file contains UNITS with DATABASE MICRONS, THE LEF_Parser SHALL record the database units multiplier for coordinate conversion

### Requirement 2: Handle Multiple LEF Files

**User Story:** As a developer, I want to parse multiple LEF files (tech.lef and cells.lef), so that all cell definitions are available for dimension lookup.

#### Acceptance Criteria

1. WHEN provided multiple LEF file paths, THE LEF_Parser SHALL parse all files and merge their MACRO definitions into a single Dimension_Dict
2. WHEN the same Cell_Type appears in multiple LEF files, THE LEF_Parser SHALL use the first occurrence and log a warning about the duplicate
3. THE LEF_Parser SHALL support both absolute and relative file paths

### Requirement 3: Cross-Reference DEF Components with LEF Dimensions

**User Story:** As a developer, I want the DEF parser to look up real cell dimensions from the LEF Dimension_Dict, so that the hardware memory file contains accurate geometry.

#### Acceptance Criteria

1. WHEN parsing a DEF COMPONENT with a Cell_Type, THE DEF_Parser SHALL look up the Cell_Type in the Dimension_Dict
2. WHEN the Cell_Type is found in the Dimension_Dict, THE DEF_Parser SHALL use the real width and height in the output HEX file
3. WHEN the Cell_Type is not found in the Dimension_Dict, THE DEF_Parser SHALL use a fallback DEFAULT_WIDTH and DEFAULT_HEIGHT of 100 and log a warning
4. THE DEF_Parser SHALL output the HEX file with dimensions converted to 32-bit hexadecimal format matching the hardware memory contract

### Requirement 4: Validate Dimension Extraction

**User Story:** As a developer, I want to verify that extracted dimensions are valid, so that downstream hardware processing receives well-formed data.

#### Acceptance Criteria

1. WHEN extracting dimensions, THE LEF_Parser SHALL validate that width and height are positive numbers greater than zero
2. WHEN a dimension value is zero or negative, THE LEF_Parser SHALL skip that MACRO and log an error
3. WHEN extracting dimensions, THE LEF_Parser SHALL validate that dimensions do not exceed the maximum representable 32-bit unsigned integer value (4,294,967,295 database units)
4. WHEN a dimension value exceeds the 32-bit limit, THE LEF_Parser SHALL log an error and skip that MACRO

### Requirement 5: Integrate LEF Parsing into Pipeline

**User Story:** As a developer, I want the master orchestrator to run LEF parsing before DEF parsing, so that dimensions are available for coordinate extraction.

#### Acceptance Criteria

1. WHEN master_run.py executes, THE Pipeline SHALL run the LEF_Parser before the DEF_Parser
2. THE Pipeline SHALL pass the Dimension_Dict from the LEF_Parser to the DEF_Parser
3. WHEN the LEF_Parser fails, THE Pipeline SHALL abort and report the error without proceeding to DEF parsing
4. WHEN the LEF_Parser succeeds but finds zero MACRO definitions, THE Pipeline SHALL proceed with a warning that all components will use default dimensions

### Requirement 6: Test with Real Benchmark Data

**User Story:** As a developer, I want to run the full pipeline with ISPD 2015 benchmark data, so that I can verify correct handling of real cell geometries.

#### Acceptance Criteria

1. WHEN running the pipeline with ISPD 2015 mgc_matrix_mult_2 design data, THE Pipeline SHALL successfully parse tech.lef and cells.lef
2. WHEN parsing ISPD 2015 cells.lef, THE LEF_Parser SHALL extract at least 100 distinct Cell_Type definitions with their dimensions
3. WHEN running the legalizer with real dimensions, THE Legalizer_FSM SHALL complete without deadlock or infinite loop
4. WHEN legalization completes with real dimensions, THE output HEX file SHALL contain component placements with non-uniform dimensions matching the LEF definitions

### Requirement 7: Handle Real Geometry Edge Cases

**User Story:** As a developer, I want the legalizer to handle tall/thin cells correctly, so that the pipeline works with physically realistic geometries.

#### Acceptance Criteria

1. WHEN cells have aspect ratios greater than 3:1 (tall) or less than 1:3 (wide), THE Legalizer_FSM SHALL resolve overlaps correctly
2. WHEN a cell is placed near the die boundary, THE Legalizer_FSM SHALL clamp coordinates to prevent out-of-bounds placement
3. WHEN real dimensions are significantly larger than the previous 100×100 default, THE Legalizer_FSM SHALL still achieve zero overlaps in the final placement
4. WHEN the number of collision iterations exceeds 10 times the number of macro pairs, THE Legalizer_FSM SHALL terminate with a warning to prevent infinite loops

### Requirement 8: Round-Trip Property for Dimension Data

**User Story:** As a developer, I want to verify that dimension extraction preserves data integrity, so that extracted values match source LEF file values.

#### Acceptance Criteria

1. FOR ALL Cell_Type entries in the Dimension_Dict, THE width and height values SHALL match the SIZE statement in the source LEF file exactly
2. WHEN parsing then printing LEF SIZE values, THE output SHALL be parseable back to equivalent dimension values (round-trip property)
3. WHEN converting floating-point dimensions from LEF to integer database units, THE LEF_Parser SHALL apply the DATABASE MICRONS multiplier correctly

### Requirement 9: Error Handling for Malformed LEF

**User Story:** As a developer, I want graceful error handling for malformed LEF files, so that the pipeline reports meaningful errors instead of crashing.

#### Acceptance Criteria

1. WHEN a LEF file has syntax errors, THE LEF_Parser SHALL report the line number and nature of the error
2. WHEN a LEF file is missing or unreadable, THE LEF_Parser SHALL raise FileNotFoundError with a descriptive message
3. WHEN a MACRO block is truncated or incomplete, THE LEF_Parser SHALL skip the malformed MACRO and continue parsing subsequent MACROs
4. WHEN parsing completes with errors, THE LEF_Parser SHALL return successfully parsed MACROs and include an error summary

### Requirement 10: CLI Interface for Standalone Use

**User Story:** As a developer, I want to run the LEF parser standalone from the command line, so that I can test dimension extraction independently.

#### Acceptance Criteria

1. WHEN running `python lef_parser.py --help`, THE LEF_Parser SHALL display usage information including required and optional arguments
2. WHEN running `python lef_parser.py <lef_file>`, THE LEF_Parser SHALL output the Dimension_Dict in JSON format to stdout
3. WHEN running with `--output <file>` flag, THE LEF_Parser SHALL write the Dimension_Dict to the specified file
4. WHEN running with `--verbose` flag, THE LEF_Parser SHALL log each MACRO name and extracted dimensions
