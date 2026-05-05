import os
import re
from typing import Dict, Tuple, Optional

# Type alias for dimension dictionary: cell_type -> (width, height) in database units
Dimension_Dict = Dict[str, Tuple[int, int]]

# Default dimensions for cells not found in LEF
DEFAULT_WIDTH = 100
DEFAULT_HEIGHT = 100

def parse_def_to_hex(
    def_path: str, 
    hex_path: str, 
    dimension_dict: Optional[Dimension_Dict] = None
) -> None:
    """
    Parse a DEF file and generate a .hex memory file for the hardware legalizer.
    
    Args:
        def_path: Path to the input DEF file
        hex_path: Path to the output .hex file
        dimension_dict: Optional dictionary mapping cell types to (width, height).
                       If None or cell not found, uses DEFAULT_WIDTH/DEFAULT_HEIGHT.
    
    Raises:
        FileNotFoundError: If def_path does not exist
    """
    in_components = False
    
    print(f"Starting extraction from {def_path}...")
    
    try:
        with open(def_path, 'r') as f_in, open(hex_path, 'w') as f_out:
            for line in f_in:
                # Detect the start and end of the macro/cell section
                if line.strip().startswith("COMPONENTS"):
                    in_components = True
                    continue
                if line.strip().startswith("END COMPONENTS"):
                    break
                    
                if in_components:
                    # Extract cell type and coordinates from DEF COMPONENT line
                    # Format: - instance_name cell_type + PLACED ( X Y ) orientation ;
                    # Example: - _0_ ms00f80 + PLACED ( 1000 2000 ) N ;
                    cell_type_match = re.match(r'\s*-\s+\S+\s+(\S+)', line)
                    coord_match = re.search(r'\(\s*(\d+)\s+(\d+)\s*\)', line)
                    
                    if cell_type_match and coord_match:
                        cell_type = cell_type_match.group(1)
                        x_coord = int(coord_match.group(1))
                        y_coord = int(coord_match.group(2))
                        
                        # Look up dimensions from dimension_dict
                        if dimension_dict and cell_type in dimension_dict:
                            width, height = dimension_dict[cell_type]
                        else:
                            width, height = DEFAULT_WIDTH, DEFAULT_HEIGHT
                            if dimension_dict is not None:
                                print(f"  Warning: Cell type '{cell_type}' not found in LEF, using default dimensions")
                        
                        # Convert to 32-bit hex (8 characters, uppercase, zero-padded)
                        x_hex = format(x_coord, '08X')
                        y_hex = format(y_coord, '08X')
                        w_hex = format(width, '08X')
                        h_hex = format(height, '08X')
                        
                        # Write strictly to the hardware memory contract format
                        f_out.write(f"{x_hex} // X coord\n")
                        f_out.write(f"{y_hex} // Y coord\n")
                        f_out.write(f"{w_hex} // Width\n")
                        f_out.write(f"{h_hex} // Height\n")
                        
        print(f"Success! Hardware memory contract generated at {hex_path}")
        
    except FileNotFoundError:
        print(f"Error: Could not find {def_path}. Ensure you pulled the latest commit from OpenROAD.")
        raise

if __name__ == "__main__":
    # Updated paths: looking forward from the RTLign root folder
    def_file = "openroad_scripts/mockup_export.def"
    hex_file = "rtl_legalizer/dummy_layout.hex"
    
    # Execute the parser
    parse_def_to_hex(def_file, hex_file)
   