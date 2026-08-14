#!/usr/bin/env python3
import os
import sys
import glob
import subprocess

def find_first_file(search_patterns):
    """Utility to find the first matching file from a list of glob patterns."""
    for pattern in search_patterns:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            return matches[0]
    return None

def main():
    print("🔍 Auto-detecting input files for RTLign Prediction Pipeline...")

    # 1. Search for a valid DEF file
    def_patterns = [
        "openroad_scripts/*.def",
        "data/**/*.def",
        "**/*.def"
    ]
    def_file = find_first_file(def_patterns)

    # 2. Search for a valid LEF file
    lef_patterns = [
        "data/**/*.lef",
        "openroad_scripts/*.lef",
        "**/*.lef"
    ]
    lef_file = find_first_file(lef_patterns)

    # 3. Model Checkpoint
    model_path = "topological_gnn_model.pth"
    output_hex = "data/macro_rel_constraints.hex"

    # Validation Checks
    if not os.path.exists(model_path):
        print(f"❌ Error: Model checkpoint '{model_path}' not found! Run 'python ml_predictor/train_nn.py' first.")
        sys.exit(1)

    if not def_file:
        print("❌ Error: No .def file found in repository!")
        sys.exit(1)

    if not lef_file:
        print("❌ Error: No .lef file found in repository!")
        sys.exit(1)

    print(f"  ✓ Model: {model_path}")
    print(f"  ✓ DEF  : {def_file}")
    print(f"  ✓ LEF  : {lef_file}")
    print(f"  ✓ Output: {output_hex}\n")

    # Construct execution command
    cmd = [
        sys.executable, "ml_predictor/predict.py",
        "--def_file", def_file,
        "--lef_file", lef_file,
        "--model_path", model_path,
        "--output_hex", output_hex
    ]

    print(f"🚀 Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print(f"\n✅ Prediction completed successfully! Generated: {output_hex}")
    else:
        print("\n❌ Prediction failed. Check error output above.")

if __name__ == "__main__":
    main()