"""
RTLign — Master Orchestration Script
=====================================
Single-click execution of the full RTLign pipeline:
  1. Parse LEF → Dimension_Dict  (lef_parser.py)
  2. Parse DEF → HEX with real dimensions  (def_parser.py)
  3. RTL Legalization  (iverilog + vvp)
  4. Inject HEX → DEF  (hex_to_def.py)

Run from the RTLign project root:
    python orchestration/master_run.py
"""

import subprocess
import sys
import os
import time

# Import LEF and DEF parsers directly for dimension_dict passing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rtl_legalizer.lef_parser import parse_lef_files
from ml_predictor.def_parser import parse_def_to_hex


# ---------------------------------------------------------------------------
# Configuration — all paths relative to the RTLign project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HEX_INJECTOR = os.path.join(PROJECT_ROOT, "ml_predictor", "hex_to_def.py")

VERILOG_SRC  = [
    os.path.join(PROJECT_ROOT, "rtl_legalizer", "collision_check.v"),
    os.path.join(PROJECT_ROOT, "rtl_legalizer", "legalizer_fsm.v"),
    os.path.join(PROJECT_ROOT, "rtl_legalizer", "legalizer_tb.v"),
]
SIM_OUTPUT   = os.path.join(PROJECT_ROOT, "rtl_legalizer", "sim.out")

# LEF file paths - using ISPD 2015 mgc_matrix_mult_2 LEF for dimension dictionary
LEF_FILES = [
    os.path.join(PROJECT_ROOT, "data/ispd_benchmarks/ispd2015/hidden/mgc_matrix_mult_2/tech.lef"),
    os.path.join(PROJECT_ROOT, "data/ispd_benchmarks/ispd2015/hidden/mgc_matrix_mult_2/cells.lef"),
]

# DEF file paths - using mockup_export.def (168 components) for testing
# The ISPD 2015 benchmark has 155K components which is too large for current legalizer
INPUT_DEF    = os.path.join(PROJECT_ROOT, "openroad_scripts", "mockup_export.def")
INPUT_HEX    = os.path.join(PROJECT_ROOT, "rtl_legalizer", "dummy_layout.hex")
OUTPUT_HEX   = os.path.join(PROJECT_ROOT, "rtl_legalizer", "output_layout.hex")
OUTPUT_DEF   = os.path.join(PROJECT_ROOT, "openroad_scripts", "legalized_export.def")


def run_step(step_name, cmd, cwd=PROJECT_ROOT):
    """Run a subprocess command with timing and error handling."""
    print(f"\n{'='*60}")
    print(f"  {step_name}")
    print(f"{'='*60}")
    print(f"  CMD: {' '.join(cmd)}")
    print()

    t0 = time.time()
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    elapsed = time.time() - t0

    # Print stdout
    if result.stdout:
        for line in result.stdout.strip().split('\n'):
            print(f"  {line}")

    # Print stderr (warnings, etc.)
    if result.stderr:
        for line in result.stderr.strip().split('\n'):
            print(f"  [stderr] {line}")

    print(f"\n  Elapsed: {elapsed:.2f}s | Exit code: {result.returncode}")

    if result.returncode != 0:
        print(f"\n  ERROR: Step '{step_name}' failed with exit code {result.returncode}")
        sys.exit(1)

    return result


def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║         RTLign Co-Design Pipeline — Master Run          ║")
    print("╚══════════════════════════════════════════════════════════╝")
    
    t_total = time.time()

    # ------------------------------------------------------------------
    # Stage 1: Parse LEF → Dimension_Dict
    # ------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("  [1/4] LEF Parser (Extract cell dimensions)")
    print(f"{'='*60}")
    
    try:
        dimension_dict = parse_lef_files(LEF_FILES, verbose=False)
        print(f"  Extracted dimensions for {len(dimension_dict)} cell types")
    except FileNotFoundError as e:
        print(f"  ERROR: LEF file not found: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"  WARNING: {e}")
        print("  All components will use default dimensions (100×100)")
        dimension_dict = {}

    # ------------------------------------------------------------------
    # Stage 2: Parse DEF → HEX (with real dimensions)
    # ------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("  [2/4] DEF → HEX Parser (Extract macro coordinates with real dimensions)")
    print(f"{'='*60}")
    
    try:
        parse_def_to_hex(INPUT_DEF, INPUT_HEX, dimension_dict)
    except FileNotFoundError as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Stage 3: RTL Legalization (Compile + Simulate)
    # ------------------------------------------------------------------
    # 3a. Compile with Icarus Verilog
    run_step(
        "[3a/4] Compile Verilog (iverilog)",
        ["iverilog", "-o", SIM_OUTPUT] + VERILOG_SRC,
    )

    # 3b. Run simulation
    run_step(
        "[3b/4] Run RTL Legalizer (vvp)",
        ["vvp", SIM_OUTPUT],
        cwd=os.path.join(PROJECT_ROOT, "rtl_legalizer"),  # so $readmemh finds the .hex
    )

    # ------------------------------------------------------------------
    # Stage 4: Inject legalized HEX → DEF
    # ------------------------------------------------------------------
    run_step(
        "[4/4] HEX → DEF Injector (Patch legalized coordinates)",
        [sys.executable, HEX_INJECTOR, INPUT_DEF, OUTPUT_HEX, OUTPUT_DEF],
    )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    elapsed_total = time.time() - t_total
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║              Pipeline Complete!                         ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  Total time:  {elapsed_total:.2f}s")
    print(f"  Output DEF:  {OUTPUT_DEF}")
    print(f"  Output HEX:  {OUTPUT_HEX}")
    print()
    print("  Next step: Open the legalized DEF in OpenROAD GUI")
    print("    openroad -gui")
    print("    > read_def openroad_scripts/legalized_export.def")
    print()


if __name__ == "__main__":
    main()
