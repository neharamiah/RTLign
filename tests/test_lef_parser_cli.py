"""
Unit tests for LEF Parser CLI interface.

Tests the CLI implementation for Requirements 10.1, 10.2, 10.3, 10.4:
- 10.1: --help displays usage information
- 10.2: JSON output to stdout
- 10.3: --output writes to file
- 10.4: --verbose logs each MACRO
"""

import subprocess
import json
import tempfile
import os
import sys


def test_help_displays_usage():
    """Test Requirement 10.1: --help shows usage information"""
    result = subprocess.run(
        [sys.executable, "rtl_legalizer/lef_parser.py", "--help"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Expected exit code 0, got {result.returncode}"
    assert "usage:" in result.stdout.lower(), "Help should show usage"
    assert "lef_files" in result.stdout, "Help should mention lef_files argument"
    assert "--output" in result.stdout, "Help should mention --output flag"
    assert "--verbose" in result.stdout, "Help should mention --verbose flag"


def test_json_output_to_stdout():
    """Test Requirement 10.2: JSON output to stdout"""
    result = subprocess.run(
        [sys.executable, "rtl_legalizer/lef_parser.py", 
         "data/ispd_benchmarks/ispd2015/hidden/mgc_matrix_mult_2/cells.lef"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Expected exit code 0, got {result.returncode}"
    
    # Verify valid JSON output
    output_data = json.loads(result.stdout)
    assert isinstance(output_data, dict), "Output should be a JSON object"
    assert len(output_data) > 0, "Output should contain parsed MACROs"
    
    # Verify structure of first entry
    first_key = next(iter(output_data))
    assert isinstance(output_data[first_key], list), "Each entry should be a list"
    assert len(output_data[first_key]) == 2, "Each entry should have [width, height]"


def test_output_writes_to_file():
    """Test Requirement 10.3: --output writes to specified file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        output_file = f.name
    
    try:
        result = subprocess.run(
            [sys.executable, "rtl_legalizer/lef_parser.py",
             "data/ispd_benchmarks/ispd2015/hidden/mgc_matrix_mult_2/cells.lef",
             "--output", output_file],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"Expected exit code 0, got {result.returncode}"
        
        # Verify file was created and contains valid JSON
        assert os.path.exists(output_file), "Output file should be created"
        
        with open(output_file, 'r') as f:
            file_data = json.load(f)
        
        assert isinstance(file_data, dict), "File should contain JSON object"
        assert len(file_data) > 0, "File should contain parsed MACROs"
        
    finally:
        if os.path.exists(output_file):
            os.remove(output_file)


def test_verbose_logs_each_macro():
    """Test Requirement 10.4: --verbose logs each MACRO name and dimensions"""
    result = subprocess.run(
        [sys.executable, "rtl_legalizer/lef_parser.py",
         "data/ispd_benchmarks/ispd2015/hidden/mgc_matrix_mult_2/cells.lef",
         "--verbose"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Expected exit code 0, got {result.returncode}"
    
    # Check that verbose output contains MACRO logging
    # The verbose output goes to stderr (print statements)
    combined_output = result.stdout + result.stderr
    
    # Should contain MACRO names with dimensions
    assert "ms00f80:" in combined_output, "Should log MACRO names"
    assert "DB units" in combined_output, "Should log dimensions in DB units"


def test_multiple_lef_files():
    """Test that multiple LEF files can be parsed"""
    result = subprocess.run(
        [sys.executable, "rtl_legalizer/lef_parser.py",
         "data/ispd_benchmarks/ispd2015/hidden/mgc_matrix_mult_2/tech.lef",
         "data/ispd_benchmarks/ispd2015/hidden/mgc_matrix_mult_2/cells.lef"],
        capture_output=True,
        text=True
    )
    
    # This should succeed (tech.lef has no MACROs but cells.lef does)
    assert result.returncode == 0, f"Expected exit code 0, got {result.returncode}"
    
    output_data = json.loads(result.stdout)
    assert len(output_data) > 0, "Should contain parsed MACROs from cells.lef"


def test_error_on_missing_file():
    """Test that missing LEF file produces error"""
    result = subprocess.run(
        [sys.executable, "rtl_legalizer/lef_parser.py", 
         "nonexistent.lef"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode != 0, "Should fail on missing file"
    assert "not found" in result.stderr.lower() or "error" in result.stderr.lower()