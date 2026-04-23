"""
RTLign — Master Orchestration Script
=====================================
Single-click execution of the full RTLign pipeline:
  1. Parse DEF → HEX  (def_parser.py)
  2. RTL Legalization  (iverilog + vvp)
  3. Inject HEX → DEF  (hex_to_def.py)

Run from the RTLign project root:
    python orchestration/master_run.py
"""

import subprocess
import sys
import os
import time


# ---------------------------------------------------------------------------
# Configuration — all paths relative to the RTLign project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEF_PARSER   = os.path.join(PROJECT_ROOT, "ml_predictor", "def_parser.py")
HEX_INJECTOR = os.path.join(PROJECT_ROOT, "ml_predictor", "hex_to_def.py")

VERILOG_SRC  = [
    os.path.join(PROJECT_ROOT, "rtl_legalizer", "collision_check.v"),
    os.path.join(PROJECT_ROOT, "rtl_legalizer", "legalizer_fsm.v"),
    os.path.join(PROJECT_ROOT, "rtl_legalizer", "legalizer_tb.v"),
]
SIM_OUTPUT   = os.path.join(PROJECT_ROOT, "rtl_legalizer", "sim.out")

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
    # Stage 1: Parse DEF → HEX
    # ------------------------------------------------------------------
    run_step(
        "[1/3] DEF → HEX Parser (Extract macro coordinates)",
        [sys.executable, DEF_PARSER],
    )

    # ------------------------------------------------------------------
    # Stage 2: RTL Legalization (Compile + Simulate)
    # ------------------------------------------------------------------
    # 2a. Compile with Icarus Verilog
    run_step(
        "[2a/3] Compile Verilog (iverilog)",
        ["iverilog", "-o", SIM_OUTPUT] + VERILOG_SRC,
    )

    # 2b. Run simulation
    run_step(
        "[2b/3] Run RTL Legalizer (vvp)",
        ["vvp", SIM_OUTPUT],
        cwd=os.path.join(PROJECT_ROOT, "rtl_legalizer"),  # so $readmemh finds the .hex
    )

    # ------------------------------------------------------------------
    # Stage 3: Inject legalized HEX → DEF
    # ------------------------------------------------------------------
    run_step(
        "[3/3] HEX → DEF Injector (Patch legalized coordinates)",
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