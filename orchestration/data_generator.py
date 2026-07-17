import os
import subprocess
import argparse
import itertools
from concurrent.futures import ThreadPoolExecutor

def run_openroad_placement(tcl_script, design, tech_lef, cells_lef, input_def, output_def, seed, density):
    """Runs a single OpenROAD placement job via subprocess."""
    cmd = [
        "openroad", "-no_init", "-exit", tcl_script,
        "-design_name", design,
        "-tech_lef", tech_lef,
        "-cells_lef", cells_lef,
        "-input_def", input_def,
        "-output_def", output_def,
        "-seed", str(seed),
        "-target_density", str(density)
    ]
    
    print(f"Running: {design} | Seed: {seed} | Density: {density}")
    try:
        # Run subprocess, suppress standard output for clean logs, capture stderr for errors
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"[ERROR] Failed to place {design} (Seed: {seed}, Density: {density})")
            print(result.stderr)
            return False
        return True
    except FileNotFoundError:
        print("[ERROR] 'openroad' executable not found. Ensure it is installed and in your PATH.")
        return False
    except Exception as e:
        print(f"[ERROR] Exception during execution: {e}")
        return False

def main():
    parser = argparse.add_argument_group("Dataset Generator")
    parser = argparse.ArgumentParser(description="Generate layout placements by varying seed and density.")
    parser.add_argument("--design", required=True, help="Name of the design (e.g., gcd, picorv32)")
    parser.add_argument("--tech_lef", required=True, help="Path to tech LEF file")
    parser.add_argument("--cells_lef", required=True, help="Path to cells LEF file")
    parser.add_argument("--input_def", required=True, help="Path to input floorplan DEF file")
    parser.add_argument("--out_dir", default="data/generated_defs", help="Directory to save generated DEFs")
    parser.add_argument("--seeds", type=int, default=10, help="Number of random seeds to use")
    parser.add_argument("--densities", type=float, nargs="+", default=[0.6, 0.65, 0.7, 0.75, 0.8], help="List of target densities")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel OpenROAD workers")
    parser.add_argument("--tcl_script", default="openroad_scripts/run_placement.tcl", help="Path to OpenROAD TCL script")

    args = parser.parse_args()

    design_out_dir = os.path.join(args.out_dir, args.design)
    os.makedirs(design_out_dir, exist_ok=True)

    # Create combinations of seeds and densities
    seeds = list(range(1, args.seeds + 1))
    combinations = list(itertools.product(seeds, args.densities))
    
    print(f"Starting generation for '{args.design}'")
    print(f"Total combinations: {len(combinations)} ({len(seeds)} seeds * {len(args.densities)} densities)")
    print(f"Output directory: {design_out_dir}")

    success_count = 0
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = []
        for seed, density in combinations:
            output_def = os.path.join(design_out_dir, f"{args.design}_s{seed}_d{density}.def")
            futures.append(
                executor.submit(
                    run_openroad_placement,
                    args.tcl_script, args.design, args.tech_lef, args.cells_lef, args.input_def, output_def, seed, density
                )
            )

        for future in futures:
            if future.result():
                success_count += 1

    print(f"\nGeneration complete! Successfully generated {success_count}/{len(combinations)} DEF files.")

if __name__ == "__main__":
    main()
