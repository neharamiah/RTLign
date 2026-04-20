import os
import re

def parse_def_to_hex(def_path, hex_path):
    in_components = False
    
    # Note: DEF files store placement (X, Y), but dimensions (Width, Height) 
    # are usually stored in the LEF file. For this Phase 1 mockup, we inject 
    # a standard dummy width and height to satisfy the Verilog memory contract.
    DEFAULT_WIDTH = 100
    DEFAULT_HEIGHT = 100
    
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
                    # Look for the coordinate block in the DEF line: e.g., ( 500 600 )
                    match = re.search(r'\(\s*(\d+)\s+(\d+)\s*\)', line)
                    if match:
                        x_coord = int(match.group(1))
                        y_coord = int(match.group(2))
                        
                        # Convert to 32-bit hex (8 characters, uppercase, zero-padded)
                        x_hex = format(x_coord, '08X')
                        y_hex = format(y_coord, '08X')
                        w_hex = format(DEFAULT_WIDTH, '08X')
                        h_hex = format(DEFAULT_HEIGHT, '08X')
                        
                        # Write strictly to the hardware memory contract format
                        f_out.write(f"{x_hex} // X coord\n")
                        f_out.write(f"{y_hex} // Y coord\n")
                        f_out.write(f"{w_hex} // Width\n")
                        f_out.write(f"{h_hex} // Height\n")
                        
        print(f"Success! Hardware memory contract generated at {hex_path}")
        
    except FileNotFoundError:
        print(f"Error: Could not find {def_path}. Ensure you pulled the latest commit from OpenROAD.")

if __name__ == "__main__":
    # Updated paths: looking forward from the RTLign root folder
    def_file = "openroad_scripts/mockup_export.def"
    hex_file = "rtl_legalizer/dummy_layout.hex"
    
    # Execute the parser
    parse_def_to_hex(def_file, hex_file)
   