#!/usr/bin/env python3
"""
run_predict.py — RTLign GNN Prediction Top-Level Runner

Automates running the Topological GNN inference and DAG cycle-breaker.
Exports N×N pairwise topological constraints to hex for hardware handoff.

Usage:
    python run_predict.py --def_file <path.def> --lef_file <cells.lef> [--model_path <model.pth>] [--output_hex <out.hex>]
"""

import os
import sys
import argparse
import subprocess


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="RTLign GNN Inference and Hardware Handoff Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example Usage:
  python run_predict.py \\
      --def_file data/generated_defs/mgc_fft_1/mgc_fft_1_ar0.66_u60_d0.6.def \\
      --lef_file data/ispd_benchmarks/ispd2015/mgc_fft_1/cells.lef \\
      --output_hex data/macro_rel_constraints.hex
"""
    )
    parser.add_argument(
        "--def_file",
        required=True,
        help="Path to the placed design DEF file (e.g. data/generated_defs/.../*.def)"
    )
    parser.add_argument(
        "--lef_file",
        required=True,
        help="Path to the library cells LEF file containing MACRO definitions (e.g. cells.lef)"
    )
    parser.add_argument(
        "--model_path",
        default="topological_gnn_model.pth",
        help="Path to the trained PyTorch Geometric model checkpoint (default: topological_gnn_model.pth)"
    )
    parser.add_argument(
        "--output_hex",
        default="data/macro_rel_constraints.hex",
        help="Path for the output N×N hardware constraint HEX file (default: data/macro_rel_constraints.hex)"
    )
    return parser.parse_args()


def main():
    if len(sys.argv) == 1:
        print("❌ Error: Missing required arguments: --def_file and --lef_file\n")
        print("Usage:")
        print("    python run_predict.py --def_file <path.def> --lef_file <cells.lef> [--model_path <model.pth>] [--output_hex <out.hex>]\n")
        print("Example:")
        print("    python run_predict.py \\")
        print("        --def_file data/generated_defs/mgc_fft_1/mgc_fft_1_ar0.66_u60_d0.6.def \\")
        print("        --lef_file data/ispd_benchmarks/ispd2015/mgc_fft_1/cells.lef\n")
        sys.exit(1)

    args = parse_arguments()

    # Validate file existence
    if not os.path.exists(args.def_file):
        print(f"❌ Error: DEF file not found: {args.def_file}")
        sys.exit(1)

    if not os.path.exists(args.lef_file):
        print(f"❌ Error: LEF file not found: {args.lef_file}")
        sys.exit(1)

    if os.path.basename(args.lef_file).lower() == "tech.lef":
        print(f"⚠️  Warning: '{args.lef_file}' appears to be a technology LEF.")
        print("   RTLign requires cell macro geometry definitions (typically found in 'cells.lef').")

    if not os.path.exists(args.model_path):
        print(f"❌ Error: Model checkpoint not found: {args.model_path}")
        print("   Please train the model first using 'python ml_predictor/train_nn.py'.")
        sys.exit(1)

    print("🚀 RTLign Prediction Pipeline")
    print(f"  ✓ Model : {args.model_path}")
    print(f"  ✓ DEF   : {args.def_file}")
    print(f"  ✓ LEF   : {args.lef_file}")
    print(f"  ✓ Output: {args.output_hex}\n")

    cmd = [
        sys.executable, "ml_predictor/predict.py",
        "--def_file", args.def_file,
        "--lef_file", args.lef_file,
        "--model_path", args.model_path,
        "--output_hex", args.output_hex
    ]

    print(f"[RUN] Executing: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print(f"\n✅ Prediction completed successfully! Generated: {args.output_hex}")
    else:
        print("\n❌ Prediction failed. Check error output above.")
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()