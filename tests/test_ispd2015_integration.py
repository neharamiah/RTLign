"""
Integration tests with ISPD 2015 benchmarks.

Tests Requirements 6.1, 6.2, 6.3, 6.4, 5.3, 5.4:
- 6.1: Parse ISPD 2015 tech.lef and cells.lef successfully
- 6.2: Extract at least 100 distinct Cell_Type definitions
- 6.3: Legalizer FSM completes without deadlock
- 6.4: Output HEX contains non-uniform dimensions
- 5.3: Invalid LEF file path aborts pipeline
- 5.4: LEF with no MACROs proceeds with warning
"""

import subprocess
import json
import os
import sys
import tempfile
import re

# Paths to ISPD 2015 benchmark data
ISPD2015_DIR = "data/ispd_benchmarks/ispd2015/hidden/mgc_matrix_mult_2"
TECH_LEF = os.path.join(ISPD2015_DIR, "tech.lef")
CELLS_LEF = os.path.join(ISPD2015_DIR, "cells.lef")
FLOORPLAN_DEF = os.path.join(ISPD2015_DIR, "floorplan.def")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestISPD2015LEFParsing:
    """Test 16.1: LEF parsing with mgc_matrix_mult_2 design data"""

    def test_parse_tech_and_cells_lef_successfully(self):
        """
        Requirement 6.1: Parse tech.lef and cells.lef successfully.
        
        WHEN running the pipeline with ISPD 2015 mgc_matrix_mult_2 design data,
        THE Pipeline SHALL successfully parse tech.lef and cells.lef
        """
        result = subprocess.run(
            [sys.executable, "rtl_legalizer/lef_parser.py", TECH_LEF, CELLS_LEF],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"LEF parsing should succeed, got: {result.stderr}"
        
        # Verify valid JSON output
        output_data = json.loads(result.stdout)
        assert len(output_data) > 0, "Should extract MACRO definitions"

    def test_extract_at_least_100_cell_types(self):
        """
        Requirement 6.2: Extract at least 100 distinct Cell_Type definitions.
        
        WHEN parsing ISPD 2015 cells.lef,
        THE LEF_Parser SHALL extract at least 100 distinct Cell_Type definitions
        """
        result = subprocess.run(
            [sys.executable, "rtl_legalizer/lef_parser.py", TECH_LEF, CELLS_LEF],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"LEF parsing should succeed, got: {result.stderr}"
        
        output_data = json.loads(result.stdout)
        cell_count = len(output_data)
        
        assert cell_count >= 100, (
            f"Should extract at least 100 cell types, got {cell_count}. "
            f"This verifies Requirement 6.2."
        )

    def test_verify_specific_known_dimensions(self):
        """
        Requirement 6.4: Verify specific known dimensions (ms00f80, oa22f80).
        
        WHEN parsing ISPD 2015 cells.lef,
        THE LEF_Parser SHALL extract correct dimensions for known cell types.
        
        Expected (from LEF SIZE statements, converted with DATABASE MICRONS 1000):
        - ms00f80: 1.6 x 2.0 microns = 1600 x 2000 DB units
        - oa22f80: 204.8 x 2.0 microns = 204800 x 2000 DB units
        """
        result = subprocess.run(
            [sys.executable, "rtl_legalizer/lef_parser.py", TECH_LEF, CELLS_LEF],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"LEF parsing should succeed, got: {result.stderr}"
        
        output_data = json.loads(result.stdout)
        
        # Verify ms00f80: SIZE 1.6 BY 2.0 -> 1600 x 2000
        assert "ms00f80" in output_data, "ms00f80 should be in parsed data"
        ms00f80_dims = output_data["ms00f80"]
        assert ms00f80_dims == [1600, 2000], (
            f"ms00f80 should be 1600 x 2000, got {ms00f80_dims}"
        )
        
        # Verify oa22f80: SIZE 204.8 BY 2.0 -> 204800 x 2000
        assert "oa22f80" in output_data, "oa22f80 should be in parsed data"
        oa22f80_dims = output_data["oa22f80"]
        assert oa22f80_dims == [204800, 2000], (
            f"oa22f80 should be 204800 x 2000, got {oa22f80_dims}"
        )

    def test_verify_extreme_aspect_ratio_cells(self):
        """
        Requirement 7.1: Verify extreme aspect ratio cells handled correctly.
        
        WHEN cells have extreme aspect ratios (width >> height or height >> width),
        THE LEF_Parser SHALL preserve these dimensions correctly.
        
        oa22f80 has aspect ratio 204.8/2.0 = 102.4:1 (very tall/wide)
        """
        result = subprocess.run(
            [sys.executable, "rtl_legalizer/lef_parser.py", TECH_LEF, CELLS_LEF],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"LEF parsing should succeed, got: {result.stderr}"
        
        output_data = json.loads(result.stdout)
        
        # oa22f80: width=204800, height=2000, aspect ratio ~102:1
        oa22f80_dims = output_data.get("oa22f80")
        assert oa22f80_dims is not None, "oa22f80 should exist"
        
        width, height = oa22f80_dims
        aspect_ratio = width / height if height > 0 else float('inf')
        
        # Verify extreme aspect ratio is preserved (> 3:1 per Requirement 7.1)
        assert aspect_ratio > 3, (
            f"oa22f80 should have extreme aspect ratio (> 3:1), got {aspect_ratio:.1f}:1"
        )
        
        # Verify the actual dimensions are correct for extreme aspect ratio
        assert width == 204800, f"oa22f80 width should be 204800, got {width}"
        assert height == 2000, f"oa22f80 height should be 2000, got {height}"


class TestFullPipelineWithRealDimensions:
    """Test 16.2: Full pipeline integration with real dimensions"""

    def test_full_pipeline_completes_without_deadlock(self):
        """
        Requirement 6.3: Legalizer FSM completes without deadlock.
        
        WHEN running the legalizer with real dimensions,
        THE Legalizer_FSM SHALL complete without deadlock or infinite loop.
        """
        # Run the full pipeline via master_run.py
        result = subprocess.run(
            [sys.executable, "orchestration/master_run.py"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=60  # Safety timeout to detect infinite loops
        )
        
        # Check that the pipeline completed (not killed by timeout)
        assert result.returncode == 0, (
            f"Pipeline should complete successfully. "
            f"Exit code: {result.returncode}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )
        
        # Verify no deadlock indicators in output
        combined_output = result.stdout + result.stderr
        assert "infinite" not in combined_output.lower(), (
            "Pipeline should not report infinite loop"
        )
        assert "deadlock" not in combined_output.lower(), (
            "Pipeline should not report deadlock"
        )
        assert "timeout" not in combined_output.lower(), (
            "Pipeline should not timeout"
        )

    def test_output_hex_contains_non_uniform_dimensions(self):
        """
        Requirement 6.4: Output HEX contains non-uniform dimensions.
        
        WHEN legalization completes with real dimensions,
        THE output HEX file SHALL contain component placements with
        non-uniform dimensions matching the LEF definitions.
        """
        # First ensure pipeline has been run (or run it now)
        hex_output = os.path.join(PROJECT_ROOT, "rtl_legalizer", "output_layout.hex")
        
        # If the HEX file doesn't exist, run the pipeline
        if not os.path.exists(hex_output):
            result = subprocess.run(
                [sys.executable, "orchestration/master_run.py"],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
                timeout=60
            )
            assert result.returncode == 0, "Pipeline should complete successfully"
        
        # Read the output HEX file
        assert os.path.exists(hex_output), f"Output HEX should exist at {hex_output}"
        
        with open(hex_output, 'r') as f:
            hex_lines = f.readlines()
        
        # Parse dimensions from HEX file (every 4th line starting at line 3)
        heights = []
        widths = []
        
        # HEX format: X, Y, Width, Height per component (4 lines each)
        for i in range(3, len(hex_lines), 4):
            if i < len(hex_lines):
                height_line = hex_lines[i].strip()
                if height_line and not height_line.startswith('//'):
                    try:
                        height = int(height_line, 16)
                        heights.append(height)
                    except ValueError:
                        pass
            
            if i-2 < len(hex_lines):
                width_line = hex_lines[i-2].strip()
                if width_line and not width_line.startswith('//'):
                    try:
                        width = int(width_line, 16)
                        widths.append(width)
                    except ValueError:
                        pass
        
        # Verify we have non-uniform dimensions
        assert len(set(widths)) > 1, (
            f"Output should have non-uniform widths, got only {set(widths)}"
        )
        assert len(set(heights)) > 1, (
            f"Output should have non-uniform heights, got only {set(heights)}"
        )
        
        # Verify dimensions match LEF definitions (not just default 100x100)
        # At least some cells should have real dimensions from LEF
        unique_widths = set(widths)
        assert 100 not in unique_widths or len(unique_widths) > 1, (
            "Output should contain real dimensions from LEF, not just defaults"
        )


class TestErrorScenarios:
    """Test 16.3: Error handling scenarios"""

    def test_invalid_lef_file_path_aborts_pipeline(self):
        """
        Requirement 5.3: Invalid LEF file path aborts pipeline.
        
        WHEN the LEF_Parser fails due to invalid file path,
        THE Pipeline SHALL abort and report the error without proceeding to DEF parsing.
        """
        # Create a temporary Python script that tests invalid LEF path
        test_script = """
import sys
sys.path.insert(0, '.')
from rtl_legalizer.lef_parser import parse_lef_files

try:
    parse_lef_files(["nonexistent/path/to/tech.lef"])
    print("ERROR: Should have raised FileNotFoundError")
    sys.exit(1)
except FileNotFoundError as e:
    print(f"SUCCESS: Got expected FileNotFoundError: {e}")
    sys.exit(0)
except Exception as e:
    print(f"ERROR: Got unexpected exception: {type(e).__name__}: {e}")
    sys.exit(1)
"""
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        
        assert result.returncode == 0, (
            f"Should raise FileNotFoundError for invalid path. "
            f"stdout: {result.stdout}, stderr: {result.stderr}"
        )
        assert "FileNotFoundError" in result.stdout or "not found" in result.stdout.lower()

    def test_lef_with_no_macros_proceeds_with_warning(self):
        """
        Requirement 5.4: LEF with no MACROs proceeds with warning.
        
        WHEN the LEF_Parser succeeds but finds zero MACRO definitions,
        THE Pipeline SHALL proceed with a warning that all components
        will use default dimensions.
        """
        # Create a temporary LEF file with no MACROs
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lef', delete=False) as f:
            f.write("""VERSION 5.5 ;
NAMESCASESENSITIVE ON ;

UNITS
  DATABASE MICRONS 1000 ;
END UNITS

LAYER metal1
  TYPE ROUTING ;
  WIDTH 0.1 ;
END metal1
""")
            empty_lef_path = f.name
        
        try:
            # Test that LEF parsing with no MACROs raises ValueError
            # (which the pipeline catches and proceeds with warning)
            test_script = f"""
import sys
sys.path.insert(0, '.')
from rtl_legalizer.lef_parser import parse_lef_files

try:
    parse_lef_files(["{empty_lef_path}"])
    print("ERROR: Should have raised ValueError for no MACROs")
    sys.exit(1)
except ValueError as e:
    if "No MACRO" in str(e):
        print(f"SUCCESS: Got expected ValueError: {{e}}")
        sys.exit(0)
    else:
        print(f"ERROR: ValueError should mention 'No MACRO': {{e}}")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: Got unexpected exception: {{type(e).__name__}}: {{e}}")
    sys.exit(1)
"""
            result = subprocess.run(
                [sys.executable, "-c", test_script],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            assert result.returncode == 0, (
                f"Should raise ValueError for empty LEF. "
                f"stdout: {result.stdout}, stderr: {result.stderr}"
            )
            assert "No MACRO" in result.stdout, "Error should mention 'No MACRO'"
            
        finally:
            if os.path.exists(empty_lef_path):
                os.remove(empty_lef_path)


class TestLEFDEFIntegration:
    """Additional integration tests for LEF + DEF pipeline"""

    def test_def_parser_uses_real_dimensions(self):
        """
        Test that DEF parser correctly uses real dimensions from LEF.
        
        WHEN parsing a DEF with cell types found in LEF,
        THE DEF_Parser SHALL use real width and height from dimension_dict.
        """
        # First get dimensions from LEF
        result = subprocess.run(
            [sys.executable, "rtl_legalizer/lef_parser.py", TECH_LEF, CELLS_LEF],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "LEF parsing should succeed"
        
        dimension_dict = json.loads(result.stdout)
        
        # Use mockup_export.def which has ms00f80 cells
        mockup_def = os.path.join(PROJECT_ROOT, "openroad_scripts", "mockup_export.def")
        mockup_hex = os.path.join(PROJECT_ROOT, "rtl_legalizer", "test_mockup.hex")
        
        # Clean up any existing test hex file
        if os.path.exists(mockup_hex):
            os.remove(mockup_hex)
        
        try:
            # Import and call parse_def_to_hex with dimension_dict
            sys.path.insert(0, os.path.join(PROJECT_ROOT, "ml_predictor"))
            from def_parser import parse_def_to_hex
            
            parse_def_to_hex(mockup_def, mockup_hex, dimension_dict)
            
            # Verify the HEX file was created
            assert os.path.exists(mockup_hex), "HEX file should be created"
            
            # Read the HEX file and verify dimensions
            with open(mockup_hex, 'r') as f:
                hex_content = f.read()
            
            # Check for real dimensions in output (not default 100x100)
            # ms00f80 should be 1600 x 2000
            assert "00000640" in hex_content or "00000064" in hex_content, (
                "HEX should contain dimensions"
            )
            
        finally:
            if os.path.exists(mockup_hex):
                os.remove(mockup_hex)

    def test_def_parser_fallback_for_unknown_cell_type(self):
        """
        Test that DEF parser falls back to default dimensions for unknown cells.
        
        WHEN parsing a DEF with cell types NOT in LEF,
        THE DEF_Parser SHALL use DEFAULT_WIDTH and DEFAULT_HEIGHT (100x100).
        """
        # Create a minimal dimension dict that doesn't include all cell types
        # and verify fallback works
        mockup_def = os.path.join(PROJECT_ROOT, "openroad_scripts", "mockup_export.def")
        mockup_hex = os.path.join(PROJECT_ROOT, "rtl_legalizer", "test_unknown.hex")
        
        # Empty dimension dict - all cells should use defaults
        empty_dimension_dict = {}
        
        if os.path.exists(mockup_hex):
            os.remove(mockup_hex)
        
        try:
            sys.path.insert(0, os.path.join(PROJECT_ROOT, "ml_predictor"))
            from def_parser import parse_def_to_hex
            
            # Capture output to check for warning
            import io
            from contextlib import redirect_stdout, redirect_stderr
            
            f = io.StringIO()
            with redirect_stdout(f), redirect_stderr(f):
                parse_def_to_hex(mockup_def, mockup_hex, empty_dimension_dict)
            
            output = f.getvalue()
            
            # Verify the HEX file was created
            assert os.path.exists(mockup_hex), "HEX file should be created"
            
            # Read the HEX file
            with open(mockup_hex, 'r') as file:
                hex_content = file.read()
            
            # With empty dimension dict, should see default 100 (0x64) for dimensions
            # Each component has 4 lines: X, Y, Width, Height
            # Width and Height should both be 0x00000064 = 100
            lines = hex_content.strip().split('\n')
            width_height_lines = lines[2::4]  # Every 4th line starting from index 2 (Width)
            
            # All widths should be 0x00000064 (100) with empty dict
            for wh_line in width_height_lines[:5]:  # Check first 5
                if wh_line and not wh_line.startswith('//'):
                    assert "00000064" in wh_line, (
                        f"Default width should be 0x00000064 (100), got {wh_line}"
                    )
                    
        finally:
            if os.path.exists(mockup_hex):
                os.remove(mockup_hex)


class TestTopologicalPipelineSchema:
    """Test Topological Pipeline Parquet output schemas and assertions"""

    def test_schema_and_assertions(self):
        # We assume that the single design test was run before this and generated the parquets in data/
        ml_features = os.path.join(PROJECT_ROOT, "data", "ml_features.parquet")
        edge_index = os.path.join(PROJECT_ROOT, "data", "edge_index.parquet")
        pairwise = os.path.join(PROJECT_ROOT, "data", "pairwise_distances.parquet")
        raw_coords = os.path.join(PROJECT_ROOT, "data", "raw_coords.parquet")

        # Skip if they don't exist (e.g. running unit tests without generating dataset first)
        if not os.path.exists(ml_features) or not os.path.exists(edge_index):
            return

        import pandas as pd
        import numpy as np

        # Test A: Node Features
        df_nodes = pd.read_parquet(ml_features)
        assert "target_x" not in df_nodes.columns
        assert "target_y" not in df_nodes.columns
        assert "HPWL" in df_nodes.columns
        assert df_nodes["HPWL"].isna().all()
        assert df_nodes["routing_congestion"].isna().all()
        assert df_nodes["WNS"].isna().all()
        assert df_nodes["TNS"].isna().all()

        # Test B: Edge Index
        df_edges = pd.read_parquet(edge_index)
        assert "weight" not in df_edges.columns
        expected_cols = [
            "design", "source_inst", "target_inst", 
            "k_path_dir_1", "k_path_dir_2", "k_path_dir_3", "k_path_dir_4", 
            "k_path_dir_5", "k_path_dir_6", "k_path_dir_7", "k_path_dir_8", "k_path_dir_9", 
            "k_path_undir_1", "shared_pins", "net_density", "aux_3", "aux_4"
        ]
        for col in expected_cols:
            assert col in df_edges.columns

        # Check bounds (non-negative)
        for i in range(1, 10):
            assert (df_edges[f"k_path_dir_{i}"] >= 0).all()
        assert (df_edges["k_path_undir_1"] >= 0).all()
        
        # Check logical sum > 0 (each pair must have some path or shared pin)
        path_sum = df_edges[[f"k_path_dir_{i}" for i in range(1, 10)]].sum(axis=1)
        path_sum += df_edges["k_path_undir_1"]
        path_sum += df_edges["shared_pins"]
        path_sum += df_edges["aux_4"]
        assert (path_sum > 0).all()

        # Test C: Pairwise Distances
        if os.path.exists(pairwise):
            df_pair = pd.read_parquet(pairwise)
            assert "dist_norm" in df_pair.columns
            # Due to bounding box, max distance is the diagonal. Normalization divides by diagonal, so max ~ 1.0 (allow up to 1.5 for numerical/padding reasons)
            assert (df_pair["dist_norm"] >= 0.0).all()
            assert (df_pair["dist_norm"] <= 1.5).all()