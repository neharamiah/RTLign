#!/usr/bin/env python3
"""
evaluate.py — RTLign Pipeline Evaluation Orchestrator

Runs the full ML -> RTL -> DEF pipeline on a given design and
compares the final metrics (HPWL, legality) with the baseline OpenROAD placement.
Generates a side-by-side visual comparison plot of the macro layouts.
"""

import os
import sys
import subprocess
import argparse
import time
import math
import re

def check_dependencies():
    try:
        import matplotlib.pyplot as plt
        import pandas as pd
    except ImportError:
        print("Missing dependencies. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "matplotlib", "pandas", "scikit-learn"])
        print("Installed dependencies.")

check_dependencies()
import matplotlib.pyplot as plt

# Ensure ml_predictor and rtl_legalizer are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml_predictor.feature_extractor import FeatureExtractor
from ml_predictor.predict import get_die_bounds
from rtl_legalizer.lef_parser import parse_lef_files

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL_TCL = os.path.join(PROJECT_ROOT, "openroad_scripts", "evaluate_layout.tcl")


def run_cmd(cmd, env=None, cwd=PROJECT_ROOT):
    print(f"\n[EVAL] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed! Stderr: {result.stderr}")
        print(f"Stdout: {result.stdout}")
        sys.exit(result.returncode)
    return result.stdout


def run_openroad_eval(def_file, tech_lef, cells_lef):
    env = os.environ.copy()
    env["TECH_LEF"] = tech_lef
    env["CELLS_LEF"] = cells_lef
    env["INPUT_DEF"] = def_file
    
    cmd = ["openroad", "-no_init", "-exit", EVAL_TCL]
    stdout = run_cmd(cmd, env=env)
    
    hpwl = "N/A"
    legal = False
    for line in stdout.split('\n'):
        if "[METRIC] HPWL:" in line:
            hpwl = line.split(":")[-1].strip()
        if "check_placement finished (legal)." in line:
            legal = True
            
    return hpwl, legal


def plot_layouts(baseline_def, legalized_def, plot_path, dim_dict=None):
    extractor = FeatureExtractor()
    base_comps = extractor.parse_def_components(baseline_def)
    leg_comps = extractor.parse_def_components(legalized_def)
    
    if not base_comps or not leg_comps:
        print("[EVAL] Could not parse components for plotting.")
        return
        
    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    
    for ax, comps, title in zip(axes, [base_comps, leg_comps], ['OpenROAD Baseline', 'RTLign ML Pipeline']):
        ax.set_title(title)
        ax.set_xlabel("X (DBU)")
        ax.set_ylabel("Y (DBU)")
        for c in comps:
            cell_type = c.get('cell_type', '')
            if dim_dict and cell_type in dim_dict:
                w, h = dim_dict[cell_type]
            else:
                w = c.get('width', 1000)
                h = c.get('height', 1000)
                if math.isnan(w): w = 1000
                if math.isnan(h): h = 1000
                
            x, y = c['target_x'], c['target_y']
            rect = plt.Rectangle((x, y), w, h, linewidth=1, edgecolor='blue', facecolor='lightblue', alpha=0.7)
            ax.add_patch(rect)
        ax.autoscale_view()
        ax.invert_yaxis()
    
    plt.tight_layout()
    plt.savefig(plot_path)
    print(f"\n[EVAL] Plot saved to {plot_path}")


def main():
    parser = argparse.ArgumentParser(description="RTLign Pipeline Evaluation Orchestrator")
    parser.add_argument("--def_file", required=True, help="Baseline DEF file")
    parser.add_argument("--tech_lef", required=True, help="Technology LEF")
    parser.add_argument("--cells_lef", required=True, help="Cells LEF")
    parser.add_argument("--model_path", default="topological_gnn_model.pth", help="Path to GNN checkpoint")
    parser.add_argument("--output_dir", default="evaluation_output", help="Directory for evaluation artifacts")
    args = parser.parse_args()
    args.def_file = os.path.abspath(args.def_file)
    args.tech_lef = os.path.abspath(args.tech_lef)
    args.cells_lef = os.path.abspath(args.cells_lef)
    if args.model_path:
        args.model_path = os.path.abspath(args.model_path)
    args.output_dir = os.path.abspath(args.output_dir)
    os.makedirs(args.output_dir, exist_ok=True)
    
    predicted_hex = os.path.join(args.output_dir, "predicted_constraints.hex")
    dummy_hex = os.path.join(PROJECT_ROOT, "rtl_legalizer", "dummy_layout.hex")
    legalized_def = os.path.join(args.output_dir, "legalized.def")
    sim_out = os.path.join(args.output_dir, "sim.out")
    output_hex = os.path.join(PROJECT_ROOT, "rtl_legalizer", "output_layout.hex")
    
    print("\n============================================================")
    print(" RTLign ML Predictor Evaluation Orchestrator")
    print("============================================================")
    
    t0 = time.time()
    
    # 1. Prediction & Topological Coordinate Resolution
    run_cmd([
        sys.executable, "ml_predictor/predict.py",
        "--def_file", args.def_file,
        "--lef_file", args.cells_lef,
        "--model_path", args.model_path,
        "--output_hex", predicted_hex,
        "--output_coords_hex", dummy_hex
    ])
    
    # 2. Extract line count and die bounds for parameterized Verilog simulation
    with open(dummy_hex, 'r') as f:
        hex_lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('//')]
    num_lines = len(hex_lines)
    die_w, die_h = get_die_bounds(args.def_file)
    
    # 3. RTL Legalizer Simulation
    sa_metrics = {}
    verilator_sim = os.path.join(PROJECT_ROOT, "rtl_legalizer", "verilator", "legalizer_sim")
    if num_lines == 672 and os.path.isfile(verilator_sim):
        try:
            from rtl_legalizer.verilator.verilator_bridge import run_verilator_legalizer
            sa_metrics = run_verilator_legalizer(dummy_hex, output_hex, cwd=os.path.join(PROJECT_ROOT, "rtl_legalizer"))
            print(f"[VERILATOR] Accelerated simulation completed in {sa_metrics.get('cycles', 0)} cycles.")
        except Exception as e:
            print(f"[WARN] Verilator execution failed ({e}); using Icarus Verilog.")
            sa_metrics = {}

    if not sa_metrics:
        iverilog_cmd = [
            "iverilog",
            f"-Plegalizer_tb.NUM_LINES={num_lines}",
            f"-Plegalizer_tb.DIE_WIDTH={die_w}",
            f"-Plegalizer_tb.DIE_HEIGHT={die_h}",
            "-o", sim_out,
            "collision_check.v", "lfsr32.v", "sa_cost.v", "sa_engine.v",
            "legalizer_fsm.v", "sa_legalizer_top.v", "legalizer_tb.v"
        ]
        run_cmd(iverilog_cmd, cwd=os.path.join(PROJECT_ROOT, "rtl_legalizer"))
        vvp_out = run_cmd(["vvp", sim_out], cwd=os.path.join(PROJECT_ROOT, "rtl_legalizer"))
        for line in vvp_out.splitlines():
            if "Legalization complete in" in line:
                m = re.search(r"in (\d+) clock cycles", line)
                if m:
                    sa_metrics["cycles"] = int(m.group(1))
            elif "Iterations" in line:
                m = re.search(r":\s*(\d+)", line)
                if m:
                    sa_metrics["iterations"] = int(m.group(1))
            elif "Final Cost" in line:
                m = re.search(r":\s*(\d+)", line)
                if m:
                    sa_metrics["final_cost"] = int(m.group(1))
            elif "Final Temp" in line:
                m = re.search(r":\s*(\d+)", line)
                if m:
                    sa_metrics["final_temp"] = int(m.group(1))
    
    # 4. HEX -> DEF Injection
    run_cmd([
        sys.executable, "ml_predictor/hex_to_def.py",
        args.def_file,
        output_hex,
        legalized_def,
        dummy_hex
    ])
    pipeline_time = time.time() - t0
    
    # 5. OpenROAD Evaluation
    print("\n[EVAL] Evaluating Baseline Placement...")
    base_hpwl, base_leg = run_openroad_eval(args.def_file, args.tech_lef, args.cells_lef)
    
    print("\n[EVAL] Evaluating RTLign Legalized Placement...")
    rtl_hpwl, rtl_leg = run_openroad_eval(legalized_def, args.tech_lef, args.cells_lef)
    
    # 6. Layout Plotting with real LEF dimensions
    plot_path = os.path.join(args.output_dir, "evaluation_plot.png")
    try:
        dim_dict = parse_lef_files([args.cells_lef], verbose=False)
    except Exception:
        dim_dict = {}
    plot_layouts(args.def_file, legalized_def, plot_path, dim_dict=dim_dict)
    
    # 7. Summary
    print("\n============================================================")
    print(" EVALUATION SUMMARY")
    print("============================================================")
    print(f"Pipeline Runtime : {pipeline_time:.2f}s")
    if sa_metrics:
        print(f"Hardware Engine  : {sa_metrics.get('engine', 'SA Optimizer + Greedy Cleanup')}")
        if 'cycles' in sa_metrics:
            print(f"Clock Cycles     : {sa_metrics['cycles']}")
        if 'iterations' in sa_metrics:
            print(f"SA Iterations    : {sa_metrics['iterations']}")
        if 'final_cost' in sa_metrics:
            print(f"SA Final Cost    : {sa_metrics['final_cost']}")
    print(f"Baseline HPWL    : {base_hpwl} (Legal: {base_leg})")
    print(f"RTLign HPWL      : {rtl_hpwl} (Legal: {rtl_leg})")
    
    try:
        bh = float(base_hpwl)
        rh = float(rtl_hpwl)
        imp = ((bh - rh) / bh) * 100
        print(f"HPWL Improvement : {imp:+.2f}%")
    except (ValueError, TypeError):
        pass
    print("============================================================")
    print(f"Visual plot saved to: {plot_path}")


if __name__ == "__main__":
    main()
