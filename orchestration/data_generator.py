import os
import subprocess
import argparse
import itertools
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed

def extract_metrics_from_log(log_path):
    metrics = {
        "status": "Failed",
        "hpwl": "N/A"
    }
    if not os.path.exists(log_path):
        return metrics
    try:
        with open(log_path, 'r') as f:
            for line in f:
                if "Placement is legal" in line:
                    metrics["status"] = "Legal"
                elif "Placement legality check failed" in line:
                    metrics["status"] = "Illegal"
                elif "METRIC hpwl" in line:
                    parts = line.strip().split()
                    if len(parts) >= 1:
                        metrics["hpwl"] = parts[-1]
    except Exception as e:
        pass
    return metrics

def run_openroad_placement(tcl_script, design, tech_lef, cells_lef, input_def, output_def, aspect_ratio, utilization, density, seed, snapshot_threshold):
    """Runs a single OpenROAD placement job via subprocess."""
    cmd = [
        "openroad", "-no_init", "-exit", tcl_script
    ]
    
    env = os.environ.copy()
    env["DESIGN_NAME"] = design
    env["TECH_LEF"] = tech_lef
    env["CELLS_LEF"] = cells_lef
    env["INPUT_DEF"] = input_def
    env["OUTPUT_DEF"] = output_def
    env["ASPECT_RATIO"] = str(aspect_ratio)
    env["CORE_UTILIZATION"] = str(utilization)
    env["TARGET_DENSITY"] = str(density)
    env["SEED"] = str(seed)
    env["SNAPSHOT_THRESHOLD"] = str(snapshot_threshold)
    
    print(f"Running: {design} | Seed: {seed} | Snap: {snapshot_threshold} | AR: {aspect_ratio} | Util: {utilization} | Density: {density}")
    try:
        # Run subprocess, suppress standard output for clean logs, capture stderr for errors
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env=env)
        if result.returncode != 0:
            print(f"[ERROR] Failed to place {design} (Seed: {seed}, Snap: {snapshot_threshold}, AR: {aspect_ratio}, Util: {utilization}, Density: {density})")
            print(result.stderr)
            return False, design, seed, snapshot_threshold, aspect_ratio, utilization, density
        return True, design, seed, snapshot_threshold, aspect_ratio, utilization, density
    except FileNotFoundError:
        print("[ERROR] 'openroad' executable not found. Ensure it is installed and in your PATH.")
        return False, design, seed, snapshot_threshold, aspect_ratio, utilization, density
    except Exception as e:
        print(f"[ERROR] Exception during execution: {e}")
        return False, design, seed, snapshot_threshold, aspect_ratio, utilization, density

def find_benchmarks(base_dir, exclude_designs=None):
    if exclude_designs is None:
        exclude_designs = []
    benchmarks = []
    for root, dirs, files in os.walk(base_dir):
        # Exclude specific directories from recursion
        dirs[:] = [d for d in dirs if d not in exclude_designs and d != 'dataset']
        design_name = os.path.basename(root)
        if design_name in exclude_designs or design_name == 'dataset':
            continue
        if 'tech.lef' in files and 'cells.lef' in files:
            def_files = [f for f in files if f.endswith('.def')]
            if def_files:
                # Prefer floorplan.def if it exists, otherwise use the first one
                input_def = 'floorplan.def' if 'floorplan.def' in def_files else def_files[0]
                benchmarks.append({
                    'design': design_name,
                    'tech_lef': os.path.join(root, 'tech.lef'),
                    'cells_lef': os.path.join(root, 'cells.lef'),
                    'input_def': os.path.join(root, input_def)
                })
    return benchmarks

def write_summary_report(out_dir, benchmarks, combinations):
    summary_path = os.path.join(out_dir, "dataset_summary.csv")
    with open(summary_path, 'w', newline='') as csvfile:
        fieldnames = ['design', 'seed', 'snapshot_threshold', 'aspect_ratio', 'utilization', 'density', 'status', 'hpwl', 'def_path']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for benchmark in benchmarks:
            design_out_dir = os.path.join(out_dir, benchmark['design'])
            for seed, threshold, ar, util, density in combinations:
                log_name = f"place_{benchmark['design']}_s{seed}_t{threshold}_ar{ar}_u{util}_d{density}.log"
                def_name = f"{benchmark['design']}_s{seed}_t{threshold}_ar{ar}_u{util}_d{density}.def"
                log_path = os.path.join(design_out_dir, log_name)
                def_path = os.path.join(design_out_dir, def_name)
                
                metrics = extract_metrics_from_log(log_path)
                
                writer.writerow({
                    'design': benchmark['design'],
                    'seed': seed,
                    'snapshot_threshold': threshold,
                    'aspect_ratio': ar,
                    'utilization': util,
                    'density': density,
                    'status': metrics['status'],
                    'hpwl': metrics['hpwl'],
                    'def_path': def_path
                })

def main():
    parser = argparse.ArgumentParser(description="Generate layout placements by varying physical constraints.")
    parser.add_argument("--all_benchmarks", action="store_true", help="Automatically discover and run all benchmarks in the benchmarks directory")
    parser.add_argument("--benchmarks_dir", default="data/ispd_benchmarks", help="Directory containing benchmark designs")
    parser.add_argument("--rtl_benchmarks_dir", default="data/generated_rtl_dataset", help="Directory containing RTL benchmark designs")
    parser.add_argument("--exclude_designs", nargs="+", default=["swerv"], help="List of design names to exclude from processing")
    
    parser.add_argument("--design", help="Name of the design (e.g., mgc_matrix_mult_1)")
    parser.add_argument("--tech_lef", help="Path to tech LEF file")
    parser.add_argument("--cells_lef", help="Path to cells LEF file")
    parser.add_argument("--input_def", help="Path to input floorplan DEF file")
    
    parser.add_argument("--out_dir", default="data/generated_defs", help="Directory to save generated DEFs")
    parser.add_argument("--seeds", type=int, nargs="+", default=[10, 42, 100], help="List of random seeds")
    parser.add_argument("--snapshot_thresholds", type=float, nargs="+", default=[0.4, 0.6, 0.8], help="List of snapshot overflow thresholds")
    parser.add_argument("--aspect_ratios", type=float, nargs="+", default=[1.0, 0.66, 1.5], help="List of floorplan aspect ratios")
    parser.add_argument("--utilizations", type=float, nargs="+", default=[60, 70, 80], help="List of core utilizations (percent)")
    parser.add_argument("--densities", type=float, nargs="+", default=[0.6, 0.65, 0.7, 0.75], help="List of target densities")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel OpenROAD workers")
    parser.add_argument("--tcl_script", default="openroad_scripts/run_placement.tcl", help="Path to OpenROAD TCL script")

    args = parser.parse_args()

    if args.all_benchmarks:
        benchmarks = find_benchmarks(args.benchmarks_dir, exclude_designs=args.exclude_designs)
        if os.path.exists(args.rtl_benchmarks_dir):
            rtl_benchmarks = find_benchmarks(args.rtl_benchmarks_dir, exclude_designs=args.exclude_designs)
            benchmarks.extend(rtl_benchmarks)
        print(f"Found {len(benchmarks)} benchmarks.")
    else:
        if not all([args.design, args.tech_lef, args.cells_lef, args.input_def]):
            print("[ERROR] Must provide --design, --tech_lef, --cells_lef, and --input_def if not using --all_benchmarks")
            return
        benchmarks = [{
            'design': args.design,
            'tech_lef': args.tech_lef,
            'cells_lef': args.cells_lef,
            'input_def': args.input_def
        }]

    # Create combinations of parameters
    combinations = list(itertools.product(args.seeds, args.snapshot_thresholds, args.aspect_ratios, args.utilizations, args.densities))
    
    print(f"Starting generation...")
    print(f"Total constraint combinations per design: {len(combinations)}")
    print(f"Total jobs: {len(benchmarks) * len(combinations)}")

    success_count = 0
    total_jobs = 0
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = []
        for benchmark in benchmarks:
            design_out_dir = os.path.join(args.out_dir, benchmark['design'])
            os.makedirs(design_out_dir, exist_ok=True)
            
            for seed, threshold, ar, util, density in combinations:
                # Name output file with parameters
                output_def = os.path.join(design_out_dir, f"{benchmark['design']}_s{seed}_t{threshold}_ar{ar}_u{util}_d{density}.def")
                total_jobs += 1
                
                if os.path.exists(output_def):
                    success_count += 1
                    continue
                    
                futures.append(
                    executor.submit(
                        run_openroad_placement,
                        args.tcl_script, benchmark['design'], benchmark['tech_lef'], benchmark['cells_lef'], benchmark['input_def'], output_def, ar, util, density, seed, threshold
                    )
                )

        # Initial write to populate pre-existing completed runs
        write_summary_report(args.out_dir, benchmarks, combinations)

        if futures:
            print(f"Waiting for {len(futures)} active placement jobs...")
            completed_counter = success_count
            total_target = len(futures) + success_count
            
            for future in as_completed(futures):
                res, design, seed, threshold, ar, util, density = future.result()
                completed_counter += 1
                if res:
                    success_count += 1
                
                pct = (completed_counter / total_target) * 100
                bar_len = 30
                filled_len = int(bar_len * completed_counter // total_target)
                bar = '=' * filled_len + '>' + '.' * (bar_len - filled_len - 1) if filled_len < bar_len else '=' * bar_len
                
                status_str = "SUCCESS" if res else "FAILED"
                print(f"[{bar}] {completed_counter}/{total_target} ({pct:.1f}%) | {design} (S:{seed}, T:{threshold}, AR:{ar}, U:{util}, D:{density}) -> {status_str}", flush=True)
                
                # Update CSV incrementally on every completed job
                write_summary_report(args.out_dir, benchmarks, combinations)

    print(f"\nGeneration complete! Successfully generated {success_count}/{total_jobs} DEF files.")
    # Final write to ensure all metrics are flushed and correct
    write_summary_report(args.out_dir, benchmarks, combinations)

if __name__ == "__main__":
    main()
