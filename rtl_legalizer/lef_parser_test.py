"""
Unit tests for LEF Parser Module

Tests the LEF parser functions for parsing DATABASE MICRONS,
extracting MACRO dimensions, and handling multiple LEF files.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 4.1, 4.2, 4.3, 4.4, 8.3, 9.2
"""

import unittest
import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lef_parser import (
    extract_database_units,
    convert_to_db_units,
    validate_dimension,
    extract_macro_dimensions,
    parse_lef_file,
    parse_lef_files
)


class TestExtractDatabaseUnits(unittest.TestCase):
    """Unit tests for extract_database_units function."""
    
    def test_standard_units_block(self):
        """Test parsing a standard UNITS block with DATABASE MICRONS 1000."""
        content = """
VERSION 5.8 ;
NAMESCASESENSITIVE ON ;
UNITS
    DATABASE MICRONS 1000 ;
END UNITS

MACRO test_cell
    SIZE 100 BY 200 ;
END test_cell
"""
        result = extract_database_units(content)
        self.assertEqual(result, 1000)
    
    def test_different_multiplier(self):
        """Test parsing with a different multiplier value."""
        content = """
UNITS
    DATABASE MICRONS 2000 ;
END UNITS
"""
        result = extract_database_units(content)
        self.assertEqual(result, 2000)
    
    def test_missing_units_block(self):
        """Test that None is returned when UNITS block is missing."""
        content = """
VERSION 5.8 ;
MACRO test_cell
    SIZE 100 BY 200 ;
END test_cell
"""
        result = extract_database_units(content)
        self.assertIsNone(result)
    
    def test_missing_database_microns(self):
        """Test that None is returned when DATABASE MICRONS is missing from UNITS block."""
        content = """
UNITS
    TIME NANOSECONDS 1 ;
END UNITS
"""
        result = extract_database_units(content)
        self.assertIsNone(result)
    
    def test_case_insensitive(self):
        """Test that parsing is case-insensitive."""
        content = """
units
    database microns 1000 ;
end units
"""
        result = extract_database_units(content)
        self.assertEqual(result, 1000)
    
    def test_whitespace_variations(self):
        """Test handling of various whitespace patterns."""
        content = """
UNITS
    DATABASE   MICRONS   500  ;
END UNITS
"""
        result = extract_database_units(content)
        self.assertEqual(result, 500)
    
    def test_real_lef_format(self):
        """Test with a realistic LEF file format from ISPD benchmarks."""
        content = """
VERSION 5.8 ;
BUSBITCHARS "[]" ;
DIVIDERCHAR "/" ;
UNITS
    DATABASE MICRONS 1000 ;
END UNITS
MANUFACTURINGGRID 0.005 ;
USEMINSPACING OBS OFF ;
CLEARANCEMEASURE MIN ;
USEMINSPACING PIN OFF ;
"""
        result = extract_database_units(content)
        self.assertEqual(result, 1000)


class TestConvertToDbUnits(unittest.TestCase):
    """Unit tests for convert_to_db_units function."""
    
    def test_basic_conversion(self):
        """Test basic unit conversion with 1000 multiplier."""
        result = convert_to_db_units(204.8, 1000)
        self.assertEqual(result, 204800)
    
    def test_default_multiplier(self):
        """Test that None db_units defaults to 1000."""
        result = convert_to_db_units(204.8, None)
        self.assertEqual(result, 204800)
    
    def test_fractional_values(self):
        """Test conversion with fractional micron values."""
        result = convert_to_db_units(1.6, 1000)
        self.assertEqual(result, 1600)
    
    def test_rounding(self):
        """Test that rounding is applied correctly."""
        # Python uses banker's rounding (round to even for .5)
        result = convert_to_db_units(1.2345, 1000)
        self.assertEqual(result, 1234)  # round(1234.5) = 1234 (banker's rounding)
    
    def test_different_multipliers(self):
        """Test conversion with different database unit multipliers."""
        result = convert_to_db_units(10.0, 2000)
        self.assertEqual(result, 20000)


class TestValidateDimension(unittest.TestCase):
    """Unit tests for validate_dimension function."""
    
    def test_valid_positive_value(self):
        """Test that positive values are validated as valid."""
        result = validate_dimension(100, "test_cell", "width")
        self.assertTrue(result)
    
    def test_reject_zero(self):
        """Test that zero is rejected."""
        result = validate_dimension(0, "test_cell", "width")
        self.assertFalse(result)
    
    def test_reject_negative(self):
        """Test that negative values are rejected."""
        result = validate_dimension(-10, "test_cell", "height")
        self.assertFalse(result)
    
    def test_reject_32bit_overflow(self):
        """Test that values exceeding 32-bit limit are rejected."""
        result = validate_dimension(2**32, "test_cell", "width")
        self.assertFalse(result)
    
    def test_accept_max_32bit_value(self):
        """Test that max 32-bit value is accepted."""
        result = validate_dimension(2**32 - 1, "test_cell", "width")
        self.assertTrue(result)


class TestExtractMacroDimensions(unittest.TestCase):
    """Unit tests for extract_macro_dimensions function."""
    
    def test_single_macro(self):
        """Test extraction of a single MACRO block."""
        content = """
MACRO test_cell
    CLASS CORE ;
    SIZE 10.5 BY 5.25 ;
END test_cell
"""
        result = extract_macro_dimensions(content, 1000)
        self.assertEqual(len(result), 1)
        self.assertIn("test_cell", result)
        self.assertEqual(result["test_cell"], (10500, 5250))
    
    def test_multiple_macros(self):
        """Test extraction of multiple MACRO blocks."""
        content = """
MACRO cell1
    SIZE 10.0 BY 20.0 ;
END cell1

MACRO cell2
    SIZE 5.5 BY 7.5 ;
END cell2
"""
        result = extract_macro_dimensions(content, 1000)
        self.assertEqual(len(result), 2)
        self.assertEqual(result["cell1"], (10000, 20000))
        self.assertEqual(result["cell2"], (5500, 7500))
    
    def test_macro_without_size(self):
        """Test that MACROs without SIZE statement are skipped."""
        content = """
MACRO no_size_cell
    CLASS CORE ;
END no_size_cell
"""
        result = extract_macro_dimensions(content, 1000)
        self.assertEqual(len(result), 0)
    
    def test_case_insensitive(self):
        """Test that SIZE parsing is case-insensitive."""
        content = """
MACRO test_cell
    size 10.0 by 5.0 ;
END test_cell
"""
        result = extract_macro_dimensions(content, 1000)
        self.assertEqual(result["test_cell"], (10000, 5000))
    
    def test_invalid_dimension_skipped(self):
        """Test that MACROs with invalid dimensions are skipped."""
        content = """
MACRO zero_width
    SIZE 0 BY 5.0 ;
END zero_width

MACRO valid_cell
    SIZE 10.0 BY 5.0 ;
END valid_cell
"""
        result = extract_macro_dimensions(content, 1000)
        self.assertEqual(len(result), 1)
        self.assertIn("valid_cell", result)


class TestParseLefFile(unittest.TestCase):
    """Unit tests for parse_lef_file function."""
    
    def test_valid_lef_file(self):
        """Test parsing a valid LEF file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lef', delete=False) as f:
            f.write("""
VERSION 5.8 ;
UNITS
    DATABASE MICRONS 1000 ;
END UNITS

MACRO test_cell
    SIZE 10.0 BY 5.0 ;
END test_cell
""")
            temp_path = f.name
        
        try:
            dim_dict, db_units = parse_lef_file(temp_path)
            self.assertEqual(db_units, 1000)
            self.assertEqual(len(dim_dict), 1)
            self.assertEqual(dim_dict["test_cell"], (10000, 5000))
        finally:
            os.unlink(temp_path)
    
    def test_file_not_found(self):
        """Test that FileNotFoundError is raised for missing files."""
        with self.assertRaises(FileNotFoundError):
            parse_lef_file("nonexistent_file.lef")
    
    def test_lef_without_units(self):
        """Test parsing LEF file without UNITS block (uses default)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lef', delete=False) as f:
            f.write("""
MACRO test_cell
    SIZE 10.0 BY 5.0 ;
END test_cell
""")
            temp_path = f.name
        
        try:
            dim_dict, db_units = parse_lef_file(temp_path)
            self.assertIsNone(db_units)
            self.assertEqual(len(dim_dict), 1)
        finally:
            os.unlink(temp_path)


class TestParseLefFiles(unittest.TestCase):
    """Unit tests for parse_lef_files function."""
    
    def test_merge_multiple_files(self):
        """Test merging dimension dicts from multiple LEF files."""
        # Create two temporary LEF files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lef', delete=False) as f1:
            f1.write("""
UNITS
    DATABASE MICRONS 1000 ;
END UNITS

MACRO cell1
    SIZE 10.0 BY 5.0 ;
END cell1
""")
            temp_path1 = f1.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lef', delete=False) as f2:
            f2.write("""
MACRO cell2
    SIZE 20.0 BY 10.0 ;
END cell2
""")
            temp_path2 = f2.name
        
        try:
            merged = parse_lef_files([temp_path1, temp_path2])
            self.assertEqual(len(merged), 2)
            self.assertIn("cell1", merged)
            self.assertIn("cell2", merged)
        finally:
            os.unlink(temp_path1)
            os.unlink(temp_path2)
    
    def test_duplicate_first_wins(self):
        """Test that first definition wins for duplicate MACROs."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lef', delete=False) as f1:
            f1.write("""
MACRO shared_cell
    SIZE 10.0 BY 5.0 ;
END shared_cell
""")
            temp_path1 = f1.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lef', delete=False) as f2:
            f2.write("""
MACRO shared_cell
    SIZE 999.0 BY 999.0 ;
END shared_cell
""")
            temp_path2 = f2.name
        
        try:
            merged = parse_lef_files([temp_path1, temp_path2])
            # First definition should win
            self.assertEqual(merged["shared_cell"], (10000, 5000))
        finally:
            os.unlink(temp_path1)
            os.unlink(temp_path2)
    
    def test_no_macros_raises_error(self):
        """Test that ValueError is raised when no MACROs found."""
        with self.assertRaises(ValueError):
            parse_lef_files([])


if __name__ == "__main__":
    unittest.main()
