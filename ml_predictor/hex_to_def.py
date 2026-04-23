"""
RTLign — HEX → DEF Injector
============================
Reads a legalized .hex file (output from the Verilog legalizer) and patches
the coordinates back into the original .def file's COMPONENTS section.

Two modes of operation:
  1. Components with existing PLACED coordinates → update in-place
  2. Components without coordinates (unplaced) → add '+ PLACED ( X Y ) N'

FIXED components (fill cells, IO pads, endcaps) are always left untouched.

Usage:
    python hex_to_def.py                          # uses defaults
    python hex_to_def.py <input.def> <coords.hex> <output.def>
"""

import re
import sys
import os


def read_hex_coordinates(hex_path):
    """Read the .hex file and return a list of (x, y) tuples.
    
    Each macro occupies 4 lines: X, Y, W, H.
    We only need X and Y for DEF injection; W and H are hardware-only.
    """
    coords = []
    values = []
    
    with open(hex_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            # Strip inline comments: "0001A2B3 // X coord" → "0001A2B3"
            token = line.split('//')[0].strip()
            if token:
                values.append(int(token, 16))
    
    # Group into macros of 4 fields: X, Y, W, H
    for i in range(0, len(values), 4):
        if i + 1 < len(values):
            coords.append((values[i], values[i + 1]))
    
    return coords


def inject_coords_into_def(def_path, coords, output_path):
    """Patch legalized coordinates into a DEF file.
    
    Strategy:
    - Walk through the COMPONENTS section line by line.
    - For FIXED components: pass through unchanged.
    - For components with existing PLACED coordinates: replace (X Y).
    - For unplaced components (no coordinates): append '+ PLACED ( X Y ) N'
      before the trailing semicolon.
    - Everything outside COMPONENTS is passed through unchanged.
    """
    in_components = False
    coord_idx = 0
    lines_out = []
    patched_count = 0
    placed_count = 0
    
    with open(def_path, 'r') as f:
        for line in f:
            stripped = line.strip()
            
            # Detect COMPONENTS section boundaries
            if stripped.startswith("COMPONENTS"):
                in_components = True
                lines_out.append(line)
                continue
            if stripped.startswith("END COMPONENTS"):
                in_components = False
                lines_out.append(line)
                continue
            
            if in_components and coord_idx < len(coords):
                # Skip FIXED components — fill cells / endcaps
                if '+ FIXED' in line:
                    lines_out.append(line)
                    continue
                
                # Check if this is a component definition line (starts with '-')
                if stripped.startswith('-'):
                    # Check for existing placement coordinates
                    match = re.search(r'\(\s*\d+\s+\d+\s*\)', line)
                    
                    if match:
                        # Has existing coordinates → replace them
                        x_new, y_new = coords[coord_idx]
                        new_placement = f'( {x_new} {y_new} )'
                        line = line[:match.start()] + new_placement + line[match.end():]
                        coord_idx += 1
                        patched_count += 1
                    elif '+ FIXED' not in line:
                        # Unplaced component → add PLACED coordinates
                        x_new, y_new = coords[coord_idx]
                        # Insert '+ PLACED ( X Y ) N' before the trailing ';'
                        line = line.rstrip()
                        if line.endswith(';'):
                            line = line[:-1].rstrip() + f' + PLACED ( {x_new} {y_new} ) N ;\n'
                        else:
                            line = line + f' + PLACED ( {x_new} {y_new} ) N\n'
                        coord_idx += 1
                        placed_count += 1
            
            lines_out.append(line)
    
    with open(output_path, 'w') as f:
        f.writelines(lines_out)
    
    total = patched_count + placed_count
    print(f"Injection complete → {output_path}")
    print(f"  {patched_count} coordinates updated (existing PLACED)")
    print(f"  {placed_count} coordinates added (were unplaced)")
    print(f"  {total} total components modified")
    print(f"  ({coord_idx}/{len(coords)} hex entries consumed)")
    
    if coord_idx < len(coords):
        print(f"  NOTE: {len(coords) - coord_idx} hex entries unused (more macros in HEX than non-FIXED components)")
    
    return total


def main():
    if len(sys.argv) == 4:
        def_path    = sys.argv[1]
        hex_path    = sys.argv[2]
        output_path = sys.argv[3]
    else:
        # Default paths relative to RTLign project root
        def_path    = "openroad_scripts/mockup_export.def"
        hex_path    = "rtl_legalizer/output_layout.hex"
        output_path = "openroad_scripts/legalized_export.def"
    
    print(f"=== RTLign HEX → DEF Injector ===")
    print(f"  Input DEF:  {def_path}")
    print(f"  Input HEX:  {hex_path}")
    print(f"  Output DEF: {output_path}")
    print()
    
    if not os.path.exists(def_path):
        print(f"ERROR: DEF file not found: {def_path}")
        sys.exit(1)
    if not os.path.exists(hex_path):
        print(f"ERROR: HEX file not found: {hex_path}")
        sys.exit(1)
    
    coords = read_hex_coordinates(hex_path)
    print(f"  Loaded {len(coords)} macro coordinates from HEX file")
    print()
    
    inject_coords_into_def(def_path, coords, output_path)


if __name__ == "__main__":
    main()
