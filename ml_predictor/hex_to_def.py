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


def read_hex_coordinates(hex_path, names_path=None, return_names=False):
    """Read the .hex file and return coords (and optionally macro names).
    
    Each macro occupies 4 lines: X, Y, W, H.
    We only need X and Y for DEF injection; W and H are hardware-only.
    """
    coords = []
    values = []
    inline_names = []
    
    with open(hex_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            # Strip inline comments: "0001A2B3 // X coord" → "0001A2B3"
            parts = line.split('//')
            token = parts[0].strip()
            if token:
                values.append(int(token, 16))
                if len(parts) > 1:
                    comment = parts[1].strip()
                    m = re.match(r'^X\s+(\S+)$', comment)
                    if m and m.group(1).lower() != 'coord':
                        inline_names.append(m.group(1))
    
    # Group into macros of 4 fields: X, Y, W, H
    for i in range(0, len(values), 4):
        if i + 1 < len(values):
            coords.append((values[i], values[i + 1]))
    
    names = None
    if len(inline_names) == len(coords):
        names = inline_names
    else:
        # Check explicit names_path or fallback to dummy_layout.hex in same dir
        candidate_paths = []
        if names_path and os.path.exists(names_path):
            candidate_paths.append(names_path)
        dir_name = os.path.dirname(os.path.abspath(hex_path))
        dummy_in_dir = os.path.join(dir_name, "dummy_layout.hex")
        if os.path.exists(dummy_in_dir) and dummy_in_dir not in candidate_paths:
            candidate_paths.append(dummy_in_dir)
            
        for cpath in candidate_paths:
            extracted = []
            with open(cpath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split('//')
                    if len(parts) > 1:
                        m = re.match(r'^X\s+(\S+)$', parts[1].strip())
                        if m and m.group(1).lower() != 'coord':
                            extracted.append(m.group(1))
            if len(extracted) == len(coords):
                names = extracted
                break

    if return_names:
        return coords, names
    return coords


def inject_coords_into_def(def_path, coords, output_path, names=None):
    """Patch legalized coordinates into a DEF file.
    
    Two matching modes:
    1. By Name: If `names` is provided (matching coords length), matches components
       by instance name (e.g. '- <inst_name>').
       This allows modifying only macros and leaving standard cells untouched.
    2. Sequential Fallback: If `names` is None, sequentially assigns coordinates
       to non-FIXED components.
    """
    in_components = False
    coord_idx = 0
    lines_out = []
    patched_count = 0
    placed_count = 0
    
    name_to_coord = None
    if names and len(names) == len(coords):
        name_to_coord = {name: coord for name, coord in zip(names, coords)}
    
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
            
            if in_components:
                if name_to_coord is not None:
                    # Name-based matching mode
                    if stripped.startswith('-'):
                        m_inst = re.match(r'-\s+(\S+)', stripped)
                        if m_inst and m_inst.group(1) in name_to_coord:
                            inst_name = m_inst.group(1)
                            x_new, y_new = name_to_coord[inst_name]
                            
                            match = re.search(r'\(\s*\d+\s+\d+\s*\)', line)
                            if match:
                                new_placement = f'( {x_new} {y_new} )'
                                line = line[:match.start()] + new_placement + line[match.end():]
                                if '+ FIXED' in line:
                                    line = line.replace('+ FIXED', '+ PLACED')
                                patched_count += 1
                            elif '+ UNPLACED' in line:
                                line = line.replace('+ UNPLACED', f'+ PLACED ( {x_new} {y_new} ) N')
                                placed_count += 1
                            else:
                                line = line.rstrip()
                                if line.endswith(';'):
                                    line = line[:-1].rstrip() + f' + PLACED ( {x_new} {y_new} ) N ;\n'
                                else:
                                    line = line + f' + PLACED ( {x_new} {y_new} ) N\n'
                                placed_count += 1
                else:
                    # Sequential matching mode (backward compatible)
                    if coord_idx < len(coords):
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
    if name_to_coord is not None:
        print(f"  Mode: Name-based matching ({len(name_to_coord)} macros)")
        print(f"  {patched_count} coordinates updated (existing PLACED/FIXED)")
        print(f"  {placed_count} coordinates added (were unplaced)")
        print(f"  {total} total components modified")
    else:
        print(f"  Mode: Sequential matching")
        print(f"  {patched_count} coordinates updated (existing PLACED)")
        print(f"  {placed_count} coordinates added (were unplaced)")
        print(f"  {total} total components modified")
        print(f"  ({coord_idx}/{len(coords)} hex entries consumed)")
        if coord_idx < len(coords):
            print(f"  NOTE: {len(coords) - coord_idx} hex entries unused (more macros in HEX than non-FIXED components)")
    
    return total


def main():
    names_path = None
    if len(sys.argv) in (4, 5):
        def_path    = sys.argv[1]
        hex_path    = sys.argv[2]
        output_path = sys.argv[3]
        if len(sys.argv) == 5:
            names_path = sys.argv[4]
    else:
        # Default paths relative to RTLign project root
        def_path    = "openroad_scripts/mockup_export.def"
        hex_path    = "rtl_legalizer/output_layout.hex"
        output_path = "openroad_scripts/legalized_export.def"
    
    print(f"=== RTLign HEX → DEF Injector ===")
    print(f"  Input DEF:  {def_path}")
    print(f"  Input HEX:  {hex_path}")
    print(f"  Output DEF: {output_path}")
    if names_path:
        print(f"  Names HEX:  {names_path}")
    print()
    
    if not os.path.exists(def_path):
        print(f"ERROR: DEF file not found: {def_path}")
        sys.exit(1)
    if not os.path.exists(hex_path):
        print(f"ERROR: HEX file not found: {hex_path}")
        sys.exit(1)
    
    coords, names = read_hex_coordinates(hex_path, names_path=names_path, return_names=True)
    print(f"  Loaded {len(coords)} macro coordinates from HEX file")
    if names:
        print(f"  Loaded {len(names)} macro names for targeted injection")
    print()
    
    inject_coords_into_def(def_path, coords, output_path, names=names)


if __name__ == "__main__":
    main()
