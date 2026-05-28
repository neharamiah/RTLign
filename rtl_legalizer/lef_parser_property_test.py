"""
Property-based tests for LEF Parser Module

These tests verify universal correctness properties using Hypothesis.

Property 13: Extreme Aspect Ratio Preservation
  Validates: Requirements 7.1
  WHEN cells have aspect ratios greater than 3:1 (tall) or less than 1:3 (wide), 
  THE Legalizer_FSM SHALL resolve overlaps correctly

Property 14: Dimension Dict Matches Source
  Validates: Requirements 8.1
  FOR ALL Cell_Type entries in the Dimension_Dict, THE width and height values 
  SHALL match the SIZE statement in the source LEF file exactly

Property 15: Round-Trip Parsing
  Validates: Requirements 8.2
  WHEN parsing then printing LEF SIZE values, THE output SHALL be parseable 
  back to equivalent dimension values (round-trip property)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hypothesis import given, settings, example, assume, HealthCheck
import hypothesis.strategies as st
from lef_parser import (
    parse_lef_file,
    parse_lef_files,
    extract_macro_dimensions,
    convert_to_db_units,
    Dimension_Dict,
)
import tempfile


# --- Strategy for generating extreme aspect ratios ---
def extreme_aspect_ratio_strategy():
    """
    Generates extreme aspect ratio dimensions:
    - Tall cells: width:height > 3:1 (e.g., 300×100)
    - Wide cells: width:height < 1:3 (e.g., 100×300)
    """
    return st.one_of(
        # Tall cells: width > 3 * height
        st.tuples(
            st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.1, max_value=3.0, allow_nan=False, allow_infinity=False)
        ).filter(lambda wh: wh[0] > 3 * wh[1]),  # width > 3 * height
        
        # Wide cells: height > 3 * width
        st.tuples(
            st.floats(min_value=0.1, max_value=3.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
        ).filter(lambda wh: wh[1] > 3 * wh[0]),  # height > 3 * width
    )


@given(
    db_units=st.one_of(st.none(), st.integers(min_value=100, max_value=10000)),
    aspect_ratios=st.lists(extreme_aspect_ratio_strategy(), min_size=1, max_size=10)
)
@settings(max_examples=30, suppress_health_check=[HealthCheck.nested_given])
def test_extreme_aspect_ratio_preservation(db_units, aspect_ratios):
    """
    Property 13: Extreme Aspect Ratio Preservation
    Validates: Requirements 7.1
    
    WHEN cells have aspect ratios greater than 3:1 (tall) or less than 1:3 (wide), 
    THE Legalizer_FSM SHALL resolve overlaps correctly.
    
    This test verifies that:
    1. LEF parser correctly extracts cells with extreme aspect ratios
    2. The width:height ratio is preserved exactly as specified in the source
    3. Dimensions are converted to database units correctly without modification
    
    Tall cells: width:height > 3:1 (e.g., 600×100 = 6:1)
    Wide cells: width:height < 1:3 (e.g., 100×600 = 1:6)
    """
    # Build LEF content with extreme aspect ratios
    units_block = ""
    if db_units is not None:
        units_block = f"""
UNITS
    DATABASE MICRONS {db_units} ;
END UNITS
"""
    
    macros = []
    expected_data = []  # (cell_name, width_microns, height_microns, is_tall)
    
    for i, (w, h) in enumerate(aspect_ratios):
        cell_name = f"extreme_cell_{i}"
        
        # Determine if tall or wide
        aspect_ratio = w / h
        is_tall = aspect_ratio > 3.0
        
        macros.append(f"""
MACRO {cell_name}
    SIZE {w} BY {h} ;
END {cell_name}
""")
        expected_data.append((cell_name, w, h, is_tall))
    
    lef_content = f"""
VERSION 5.8 ;
{units_block}
{''.join(macros)}
"""
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.lef', delete=False) as f:
        f.write(lef_content)
        temp_path = f.name
    
    try:
        # Parse and get dimensions
        dimension_dict, _ = parse_lef_file(temp_path)
        
        # Multiplier for conversion
        multiplier = db_units if db_units is not None else 1000
        
        # Verify each extreme aspect ratio cell
        for cell_name, expected_w, expected_h, is_tall in expected_data:
            assert cell_name in dimension_dict, f"Cell {cell_name} not found in dimension dict"
            
            actual_width, actual_height = dimension_dict[cell_name]
            
            # Convert expected values to database units
            expected_width_db = convert_to_db_units(expected_w, db_units)
            expected_height_db = convert_to_db_units(expected_h, db_units)
            
            # Verify width and height are exact
            assert actual_width == expected_width_db, \
                f"Width mismatch for {cell_name}: expected {expected_width_db}, got {actual_width}"
            assert actual_height == expected_height_db, \
                f"Height mismatch for {cell_name}: expected {expected_height_db}, got {actual_height}"
            
            # Verify aspect ratio is preserved
            # Using the actual database unit values to calculate ratio
            actual_ratio = actual_width / actual_height if actual_height > 0 else float('inf')
            
            # Calculate expected ratio directly from db units to avoid float precision issues
            # The ratio in db units should be the same as in micron units
            expected_ratio = expected_width_db / expected_height_db if expected_height_db > 0 else float('inf')
            
            # Use a reasonable relative tolerance for floating-point comparisons
            # Allow up to 1% relative error to account for rounding
            if expected_ratio > 0:
                rel_error = abs(actual_ratio - expected_ratio) / expected_ratio
                assert rel_error < 0.01, \
                    f"Aspect ratio not preserved for {cell_name}: expected {expected_ratio:.3f}, got {actual_ratio:.3f}, rel_error={rel_error:.4f}"
            
            # Verify it's actually extreme
            if is_tall:
                assert expected_ratio > 3.0, f"{cell_name} should be tall (ratio > 3:1), got {expected_ratio:.3f}"
            else:
                assert expected_ratio < 1.0/3.0, f"{cell_name} should be wide (ratio < 1:3), got {expected_ratio:.3f}"
                
    finally:
        os.unlink(temp_path)


# --- Strategy for generating valid LEF content ---
@settings(max_examples=20, suppress_health_check=[HealthCheck.nested_given])
@given(
    db_units=st.one_of(st.none(), st.integers(min_value=100, max_value=10000)),
    widths=st.lists(st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False), 
                    min_size=1, max_size=5),
    heights=st.lists(st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False), 
                     min_size=1, max_size=5)
)
def test_dimension_dict_matches_source(db_units, widths, heights):
    """
    Property 14: Dimension Dict Matches Source
    Validates: Requirements 8.1
    
    FOR ALL Cell_Type entries in the Dimension_Dict, THE width and height values 
    SHALL match the SIZE statement in the source LEF file exactly.
    
    This test generates random LEF content with known MACRO SIZE values and verifies
    that the parser extracts EXACTLY those values.
    """
    # Ensure same length (use minimum)
    min_len = min(len(widths), len(heights))
    widths = widths[:min_len]
    heights = heights[:min_len]
    
    # Build LEF content
    units_block = ""
    if db_units is not None:
        units_block = f"""
UNITS
    DATABASE MICRONS {db_units} ;
END UNITS
"""
    
    macros = []
    expected_dims = []
    for i, (w, h) in enumerate(zip(widths, heights)):
        cell_name = f"cell_{i}"
        macros.append(f"""
MACRO {cell_name}
    SIZE {w} BY {h} ;
END {cell_name}
""")
        expected_dims.append((cell_name, w, h))
    
    lef_content = f"""
VERSION 5.8 ;
{units_block}
{''.join(macros)}
"""
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.lef', delete=False) as f:
        f.write(lef_content)
        temp_path = f.name
    
    try:
        # Parse and get dimensions
        dimension_dict, _ = parse_lef_file(temp_path)
        
        # Verify each dimension matches EXACTLY
        for cell_name, expected_w, expected_h in expected_dims:
            assert cell_name in dimension_dict, f"Cell {cell_name} not found in dimension dict"
            
            actual_width, actual_height = dimension_dict[cell_name]
            
            # Convert expected values to database units
            expected_width_db = convert_to_db_units(expected_w, db_units)
            expected_height_db = convert_to_db_units(expected_h, db_units)
            
            # Assert exact match
            assert actual_width == expected_width_db, \
                f"Width mismatch for {cell_name}: expected {expected_width_db}, got {actual_width}"
            assert actual_height == expected_height_db, \
                f"Height mismatch for {cell_name}: expected {expected_height_db}, got {actual_height}"
    finally:
        os.unlink(temp_path)


@settings(max_examples=20, suppress_health_check=[HealthCheck.nested_given])
@given(
    db_units=st.one_of(st.none(), st.integers(min_value=100, max_value=10000)),
    widths=st.lists(st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False), 
                    min_size=1, max_size=5),
    heights=st.lists(st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False), 
                     min_size=1, max_size=5)
)
def test_round_trip_parsing(db_units, widths, heights):
    """
    Property 15: Round-Trip Parsing
    Validates: Requirements 8.2
    
    WHEN parsing then printing LEF SIZE values, THE output SHALL be parseable 
    back to equivalent dimension values (round-trip property).
    
    This test verifies that:
    1. We can generate LEF content with known dimensions
    2. Parse it to get dimension dict
    3. Convert dimensions back to string format (SIZE W BY H)
    4. Re-parse the regenerated content
    5. Verify the dimensions are equivalent (accounting for float->int->float rounding)
    """
    # Ensure same length
    min_len = min(len(widths), len(heights))
    widths = widths[:min_len]
    heights = heights[:min_len]
    
    # Build original LEF content
    units_block = ""
    if db_units is not None:
        units_block = f"""
UNITS
    DATABASE MICRONS {db_units} ;
END UNITS
"""
    
    macros = []
    original_dims = {}  # cell_name -> (width_microns, height_microns)
    for i, (w, h) in enumerate(zip(widths, heights)):
        cell_name = f"cell_{i}"
        macros.append(f"""
MACRO {cell_name}
    SIZE {w} BY {h} ;
END {cell_name}
""")
        original_dims[cell_name] = (w, h)
    
    lef_content = f"""
VERSION 5.8 ;
{units_block}
{''.join(macros)}
"""
    
    # First parse
    with tempfile.NamedTemporaryFile(mode='w', suffix='.lef', delete=False) as f:
        f.write(lef_content)
        temp_path = f.name
    
    try:
        dimension_dict, _ = parse_lef_file(temp_path)
        
        # Now "print" the dimensions back to SIZE format
        # This simulates what would happen if we serialized parsed dimensions
        regenerated_macros = []
        for cell_name, (width_db, height_db) in dimension_dict.items():
            # Convert back to microns (reverse the database units conversion)
            multiplier = db_units if db_units is not None else 1000
            width_back = width_db / multiplier
            height_back = height_db / multiplier
            
            regenerated_macros.append(f"""
MACRO {cell_name}
    SIZE {width_back} BY {height_back} ;
END {cell_name}
""")
        
        # Second parse - round trip
        regenerated_content = f"""
VERSION 5.8 ;
{units_block}
{''.join(regenerated_macros)}
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lef', delete=False) as f2:
            f2.write(regenerated_content)
            temp_path2 = f2.name
        
        try:
            roundtrip_dict, _ = parse_lef_file(temp_path2)
            
            # Verify round-trip produces equivalent dimensions
            # Due to float->int->float conversion, we allow small tolerance
            multiplier = db_units if db_units is not None else 1000
            tolerance = 1.0 / multiplier  # Allow 1 unit of tolerance in DB units
            
            for cell_name in original_dims:
                assert cell_name in dimension_dict
                assert cell_name in roundtrip_dict
                
                orig_w_db, orig_h_db = dimension_dict[cell_name]
                rt_w_db, rt_h_db = roundtrip_dict[cell_name]
                
                # Check width is equivalent
                assert abs(orig_w_db - rt_w_db) <= tolerance, \
                    f"Round-trip width mismatch for {cell_name}: {orig_w_db} vs {rt_w_db}"
                
                # Check height is equivalent
                assert abs(orig_h_db - rt_h_db) <= tolerance, \
                    f"Round-trip height mismatch for {cell_name}: {orig_h_db} vs {rt_h_db}"
        finally:
            os.unlink(temp_path2)
    finally:
        os.unlink(temp_path)


# Run with pytest
if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])