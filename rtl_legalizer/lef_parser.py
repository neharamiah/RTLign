"""
LEF Parser Module for Real Cell Dimensions

This module parses Library Exchange Format (LEF) files to extract cell dimensions
from MACRO SIZE statements, enabling physically accurate collision detection
in the RTLign hardware legalizer.

The parser handles:
- DATABASE MICRONS extraction for unit conversion
- MACRO SIZE statement parsing
- Dimension validation (positive values, 32-bit range)
- Multiple LEF file merging with duplicate handling
"""

from typing import Dict, Tuple, List, Optional
import re
import os
import json
import argparse


# Type alias for dimension dictionary: cell_type -> (width, height) in database units
Dimension_Dict = Dict[str, Tuple[int, int]]


def parse_lef_files(lef_paths: List[str], verbose: bool = False) -> Dimension_Dict:
    """
    Parse one or more LEF files and return a merged dimension dictionary.
    
    Args:
        lef_paths: List of paths to LEF files (tech.lef, cells.lef, etc.)
        verbose: If True, log each MACRO and extracted dimensions
    
    Returns:
        Dictionary mapping cell type names to (width, height) tuples
        in database units (integer)
    
    Raises:
        FileNotFoundError: If any LEF file does not exist
        ValueError: If no MACRO definitions found across all files
    
    Requirements: 2.1, 2.2, 2.3
    """
    merged_dict: Dimension_Dict = {}
    
    for lef_path in lef_paths:
        # Parse single LEF file (raises FileNotFoundError if missing)
        dimension_dict, _ = parse_lef_file(lef_path, verbose)
        
        # Merge with first-wins strategy for duplicates
        for cell_type, dimensions in dimension_dict.items():
            if cell_type in merged_dict:
                # Log warning for duplicate (first-wins)
                print(f"Warning: Duplicate cell type '{cell_type}' in {lef_path}, using first definition")
            else:
                merged_dict[cell_type] = dimensions
    
    # Raise ValueError if no MACROs found
    if not merged_dict:
        raise ValueError("No MACRO definitions found in any LEF file")
    
    return merged_dict


def parse_lef_file(lef_path: str, verbose: bool = False) -> Tuple[Dimension_Dict, Optional[int]]:
    """
    Parse a single LEF file and extract MACRO definitions.
    
    Args:
        lef_path: Path to a single LEF file
        verbose: If True, log each MACRO and extracted dimensions
    
    Returns:
        Tuple of (dimension_dict, database_units_multiplier)
        - dimension_dict: Maps cell type names to (width, height) in database units
        - database_units_multiplier: DATABASE MICRONS value if present, None otherwise
    
    Raises:
        FileNotFoundError: If the LEF file does not exist
    
    Requirements: 1.1, 1.5, 9.2
    """
    # Check if file exists
    if not os.path.exists(lef_path):
        raise FileNotFoundError(f"LEF file not found: {lef_path}")
    
    # Read the entire file content
    # For streaming large files, we could use line-by-line, but LEF files are typically small
    with open(lef_path, 'r') as f:
        content = f.read()
    
    # Extract DATABASE MICRONS value
    db_units = extract_database_units(content)
    
    # Extract MACRO dimensions
    dimension_dict = extract_macro_dimensions(content, db_units, verbose)
    
    return (dimension_dict, db_units)


def extract_database_units(content: str) -> Optional[int]:
    """
    Extract DATABASE MICRONS value from UNITS block.
    
    LEF format:
        UNITS
            DATABASE MICRONS 1000 ;
        END UNITS
    
    Args:
        content: Full LEF file content as string
    
    Returns:
        Database units multiplier (e.g., 1000), or None if not found
    
    Requirements: 1.5
    """
    # Find the UNITS block
    units_match = re.search(
        r'UNITS\s+(.*?)\s*END\s+UNITS',
        content,
        re.IGNORECASE | re.DOTALL
    )
    
    if not units_match:
        return None
    
    units_block = units_match.group(1)
    
    # Search for DATABASE MICRONS pattern within the UNITS block
    db_match = re.search(
        r'DATABASE\s+MICRONS\s+(\d+)\s*;',
        units_block,
        re.IGNORECASE
    )
    
    if db_match:
        return int(db_match.group(1))
    
    return None


def extract_macro_dimensions(content: str, db_units: Optional[int], verbose: bool = False) -> Dimension_Dict:
    """
    Extract MACRO SIZE statements from LEF content.
    
    LEF format:
        MACRO cell_name
            CLASS CORE ;
            ORIGIN 0 0 ;
            SIZE width BY height ;
            ...
        END cell_name
    
    Args:
        content: Full LEF file content as string
        db_units: Database units multiplier (for converting microns to DB units)
        verbose: If True, log each MACRO and extracted dimensions
    
    Returns:
        Dictionary mapping cell type names to (width, height) in database units
    
    Requirements: 1.1, 1.2, 1.3, 1.4, 4.1, 4.2, 4.3, 4.4
    """
    dimensions: Dimension_Dict = {}
    
    # Find all MACRO blocks using regex
    # Pattern matches: MACRO <name> ... END <name>
    # We use a non-greedy match for the MACRO body
    macro_pattern = re.compile(
        r'MACRO\s+(\S+)\s+(.*?)\s*END\s+\1',
        re.IGNORECASE | re.DOTALL
    )
    
    for macro_match in macro_pattern.finditer(content):
        cell_type = macro_match.group(1)
        macro_body = macro_match.group(2)
        
        # Search for SIZE statement within the MACRO body
        # Format: SIZE <width> BY <height> ;
        size_match = re.search(
            r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;',
            macro_body,
            re.IGNORECASE
        )
        
        if not size_match:
            # Skip MACROs without SIZE statement (per Requirement 1.4)
            if verbose:
                print(f"  Warning: MACRO '{cell_type}' has no SIZE statement, skipping")
            continue
        
        # Extract width and height as floats
        width_microns = float(size_match.group(1))
        height_microns = float(size_match.group(2))
        
        # Convert to database units
        width_db = convert_to_db_units(width_microns, db_units)
        height_db = convert_to_db_units(height_microns, db_units)
        
        # Validate dimensions
        if not validate_dimension(width_db, cell_type, "width"):
            continue
        if not validate_dimension(height_db, cell_type, "height"):
            continue
        
        # Add to dictionary
        dimensions[cell_type] = (width_db, height_db)
        
        if verbose:
            print(f"  {cell_type}: {width_db} x {height_db} DB units ({width_microns} x {height_microns} microns)")
    
    return dimensions


def convert_to_db_units(value_microns: float, db_units: Optional[int]) -> int:
    """
    Convert a dimension from microns to database units.
    
    Args:
        value_microns: Dimension in microns (e.g., 204.8)
        db_units: Database units multiplier (e.g., 1000 for 1000 units/micron)
    
    Returns:
        Dimension in database units (integer), rounded if necessary
    
    Requirements: 8.3
    """
    # Default to 1000 database units per micron if not specified
    multiplier = db_units if db_units is not None else 1000
    return round(value_microns * multiplier)


def validate_dimension(value: int, cell_type: str, dimension_name: str) -> bool:
    """
    Validate that a dimension is a positive integer within 32-bit range.
    
    Args:
        value: Dimension value in database units
        cell_type: Cell type name for error messages
        dimension_name: "width" or "height" for error messages
    
    Returns:
        True if valid, False otherwise (logs error)
    
    Requirements: 4.1, 4.2, 4.3, 4.4
    """
    # Maximum value for 32-bit unsigned integer
    MAX_32BIT = 2**32 - 1
    
    # Check for positive value
    if value <= 0:
        print(f"Error: Invalid dimension for '{cell_type}': {dimension_name}={value} (must be positive)")
        return False
    
    # Check for 32-bit overflow
    if value > MAX_32BIT:
        print(f"Error: Dimension exceeds 32-bit limit for '{cell_type}': {dimension_name}={value}")
        return False
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse LEF files and extract cell dimensions"
    )
    parser.add_argument("lef_files", nargs="+", help="LEF file(s) to parse")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--verbose", "-v", action="store_true", 
                        help="Log each MACRO and dimensions")
    args = parser.parse_args()
    
    dim_dict = parse_lef_files(args.lef_files, verbose=args.verbose)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(dim_dict, f, indent=2)
    else:
        print(json.dumps(dim_dict, indent=2))
