import os
import subprocess
import sys

def main():
    rtl_sources_dir = os.path.join("data", "rtl_sources")
    out_dir = os.path.join("data", "generated_rtl_dataset")
    pdk_tech_lef = os.path.join("data", "sky130_pdk", "sky130_fd_sc_hd", "tech", "sky130_fd_sc_hd__nom.tlef")
    pdk_macro_lef = os.path.join("data", "sky130_pdk", "sky130_fd_sc_hd", "sky130_fd_sc_hd_merged.lef")

    if not os.path.exists(rtl_sources_dir):
        print(f"[ERROR] RTL sources directory '{rtl_sources_dir}' not found.")
        sys.exit(1)

    designs = [d for d in os.listdir(rtl_sources_dir) if os.path.isdir(os.path.join(rtl_sources_dir, d))]

    if not designs:
        print(f"[ERROR] No designs found in '{rtl_sources_dir}'.")
        sys.exit(1)

    print(f"Found {len(designs)} designs: {', '.join(designs)}")
    print(f"Output directory: {out_dir}")

    # Ensure output directory exists
    os.makedirs(out_dir, exist_ok=True)

    # 1. Synthesis & Floorplanning (RTL to DEF)
    for design in designs:
        print(f"\n--- [Step 1] Synthesizing and Floorplanning {design} ---")
        cmd = [
            sys.executable,
            os.path.join("orchestration", "rtl_to_def.py"),
            "--design", design,
            "--out_dir", out_dir
        ]
        print(f"Running: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to run rtl_to_def.py for {design}")
            sys.exit(1)

        # 2. Create Symlinks for LEFs
        print(f"--- [Step 2] Setting up LEF symlinks for {design} ---")
        design_out = os.path.join(out_dir, design)
        
        if not os.path.exists(design_out):
            print(f"[ERROR] Expected output directory '{design_out}' not found after synthesis.")
            sys.exit(1)
            
        tech_link = os.path.join(design_out, "tech.lef")
        cells_link = os.path.join(design_out, "cells.lef")
        
        abs_pdk_tech_lef = os.path.abspath(pdk_tech_lef)
        abs_pdk_macro_lef = os.path.abspath(pdk_macro_lef)

        if not os.path.exists(tech_link):
            os.symlink(abs_pdk_tech_lef, tech_link)
            print(f"Symlinked tech.lef -> {abs_pdk_tech_lef}")
        else:
            print(f"tech.lef already exists.")
            
        if not os.path.exists(cells_link):
            os.symlink(abs_pdk_macro_lef, cells_link)
            print(f"Symlinked cells.lef -> {abs_pdk_macro_lef}")
        else:
            print(f"cells.lef already exists.")

    # 3. Data Generation (Varying Constraints)
    print(f"\n--- [Step 3] Generating Dataset (Varying Constraints) ---")
    dataset_out = os.path.join(out_dir, "dataset")
    cmd = [
        sys.executable,
        os.path.join("orchestration", "data_generator.py"),
        "--all_benchmarks",
        "--benchmarks_dir", out_dir,
        "--out_dir", dataset_out,
        "--workers", "1"
    ]
    
    print(f"Running Data Generator with 1 worker.")
    print(f"Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to run data_generator.py")
        sys.exit(1)

    print("\n--- Pipeline Complete! ---")
    print(f"Dataset generated at: {dataset_out}")

if __name__ == "__main__":
    main()
