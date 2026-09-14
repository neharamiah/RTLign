#!/usr/import/env python3
"""
evaluate.py — RTLign Pipeline Evaluation Orchestrator

This script runs the full ML -> RTL -> DEF pipeline on a given design and
compares the final metrics (HPWL) with the baseline OpenROAD placement.
It generates a visual comparison plot of the macro layouts.
"""

import os
import sys
import subprocess
import argparse
import time
import math

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

# Ensure ml_predictor is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml_predictor.feature_extractor import FeatureExtractor

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL_TCL = os.path.join(PROJECT_ROOT, "openroad_scripts", "evaluate_layout.tcl")

def run_cmd(cmd, env=None, cwd=PROJECT_ROOT):
    print(f"\n[EVAL] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed! Stderr: {result.stderr}")
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

def plot_layouts(baseline_def, legalized_def, plot_path, macro_data=None):
    extractor = FeatureExtractor()
    base_comps = extractor.parse_def_components(baseline_def, macro_data)
    leg_comps = extractor.parse_def_components(legalized_def, macro_data)
    
    if not base_comps or not leg_comps:
        print("[EVAL] Could not parse components for plotting.")
        return
        
    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    
    for ax, comps, title in zip(axes, [base_comps, leg_comps], ['OpenROAD Baseline', 'RTLign ML Pipeline']):
        ax.set_title(title)
        ax.set_xlabel("X (DBU)")
        ax.set_ylabel("Y (DBU)")
        for c in comps:
            # Note: width/height might be NaN if macro_data wasn't fully matched, we plot a generic point if so.
            w = c.get('width', 1000)
            h = c.get('height', 1000)
            if math.isnan(w): w = 1000
            if math.isnan(h): h = 1000
                
            x, y = c['target_x'], c['target_y']
            rect = plt.Rectangle((x, y), w, h, linewidth=1, edgecolor='blue', facecolor='lightblue', alpha=0.7)
            ax.add_patch(rect)
        ax.autoscale_view()
        ax.invert_yaxis() # DEF origin is usually bottom-left, but often displayed differently. Let's rely on standard autoscale.
    
    plt.tight_layout()
    plt.savefig(plot_path)
    print(f"\n[EVAL] Plot saved to {plot_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--def_file", required=True, help="Baseline DEF file")
    parser.add_argument("--tech_lef", required=True, help="Technology LEF")
    parser.add_argument("--cells_lef", required=True, help="Cells LEF")
    parser.add_argument("--model_path", default="topological_gnn_model.pth")
    parser.add_argument("--output_dir", default="evaluation_output")
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Paths
    predicted_hex = os.path.join(args.output_dir, "predicted.hex")
    legalized_def = os.path.join(args.output_dir, "legalized.def")
    sim_out = os.path.join(args.output_dir, "sim.out")
    output_hex = os.path.join(PROJECT_ROOT, "rtl_legalizer", "output_layout.hex") # Hardcoded in testbench usually, but we'll adapt if needed.
    # Actually legalizer_tb.v writes to output_layout.hex. Let's just run it in its folder.
    
    print("\n============================================================")
    print(" RTLign ML Predictor Evaluation Orchestrator")
    print("============================================================")
    
    # 1. Prediction
    t0 = time.time()
    run_cmd([
        sys.executable, "ml_predictor/predict.py",
        "--def_file", args.def_file,
        "--lef_file", args.cells_lef,
        "--model_path", args.model_path,
        "--output_hex", predicted_hex
    ])
    
    # 2. RTL Legalizer
    # Copy predicted hex to dummy_layout.hex because legalizer reads that by default
    run_cmd(["cp", predicted_hex, os.path.join(PROJECT_ROOT, "rtl_legalizer", "dummy_layout.hex")])
    
    run_cmd([
        "iverilog", "-o", sim_out,
        "collision_check.v", "legalizer_fsm.v", "legalizer_tb.v"
    ], cwd=os.path.join(PROJECT_ROOT, "rtl_legalizer"))
    
    run_cmd(["vvp", sim_out], cwd=os.path.join(PROJECT_ROOT, "rtl_legalizer"))
    
    # 3. HEX -> DEF Injection
    run_cmd([
        sys.executable, "ml_predictor/hex_to_def.py",
        args.def_file,
        os.path.join(PROJECT_ROOT, "rtl_legalizer", "output_layout.hex"),
        legalized_def
    ])
    pipeline_time = time.time() - t0
    
    # 4. OpenROAD Evaluation
    print("\n[EVAL] Evaluating Baseline...")
    base_hpwl, base_leg = run_openroad_eval(args.def_file, args.tech_lef, args.cells_lef)
    
    print("\n[EVAL] Evaluating RTLign Legalized...")
    rtl_hpwl, rtl_leg = run_openroad_eval(legalized_def, args.tech_lef, args.cells_lef)
    
    # 5. Plotting
    import math
    plot_path = os.path.join(args.output_dir, "evaluation_plot.png")
    
    # Load macro data for accurate bounding boxes
    extractor = FeatureExtractor()
    macro_data_map = extractor.load_macro_data({args.def_file: args.cells_lef}, area_threshold=0) # Quick hack for full parse, but actually load_macro_data takes set of design names.
    # Better to just not pass macro_data, it will plot generic squares which is fine for visual comparison.
    plot_layouts(args.def_file, legalized_def, plot_path)
    
    # 6. Summary
    print("\n============================================================")
    print(" EVALUATION SUMMARY")
    print("============================================================")
    print(f"Pipeline Runtime : {pipeline_time:.2f}s")
    print(f"Baseline HPWL    : {base_hpwl} (Legal: {base_leg})")
    print(f"RTLign HPWL      : {rtl_hpwl} (Legal: {rtl_leg})")
    
    try:
        bh = float(base_hpwl)
        rh = float(rtl_hpwl)
        imp = ((bh - rh) / bh) * 100
        print(f"HPWL Improvement : {imp:+.2f}%")
    except:
        pass
    print("============================================================")
    print(f"Visual plot saved to: {plot_path}")

if __name__ == "__main__":
    main()
