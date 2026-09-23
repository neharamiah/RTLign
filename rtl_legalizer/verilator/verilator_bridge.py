"""
Verilator Bridge for RTLign Simulated Annealing Legalizer.

Provides high-speed hardware simulation by executing the compiled Verilator
C++ harness directly, achieving 100x-1000x speedup over Icarus Verilog.
"""

import os
import re
import shutil
import subprocess
from typing import Dict, Any, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RTL_DIR = os.path.join(PROJECT_ROOT, "rtl_legalizer")
VERILATOR_DIR = os.path.join(RTL_DIR, "verilator")
SIM_BINARY = os.path.join(VERILATOR_DIR, "legalizer_sim")


def build_verilator(verbose: bool = False) -> bool:
    """Compile the Verilator simulation binary if needed."""
    try:
        cmd = ["make", "-C", VERILATOR_DIR]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        if verbose:
            print(result.stdout)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        if verbose:
            print(f"[WARN] Verilator build failed: {e}")
        return False


def run_verilator_legalizer(
    input_hex: str,
    output_hex: str,
    cwd: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute the Verilator Simulated Annealing legalizer.

    Args:
        input_hex: Path to input dummy_layout.hex
        output_hex: Path where legalized coordinates will be written
        cwd: Working directory (defaults to rtl_legalizer)

    Returns:
        Dictionary containing simulation performance and SA metrics.
    """
    work_dir = cwd or RTL_DIR

    # Ensure binary is built
    if not os.path.isfile(SIM_BINARY):
        built = build_verilator()
        if not built or not os.path.isfile(SIM_BINARY):
            raise RuntimeError(f"Verilator simulation binary not found at {SIM_BINARY}")

    # Ensure dummy_layout.hex in working directory
    target_dummy = os.path.join(work_dir, "dummy_layout.hex")
    if os.path.abspath(input_hex) != os.path.abspath(target_dummy):
        shutil.copyfile(input_hex, target_dummy)

    target_output = os.path.abspath(output_hex)

    # Run the Verilator binary
    cmd = [SIM_BINARY, target_output]
    result = subprocess.run(
        cmd,
        cwd=work_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True
    )

    stdout = result.stdout
    metrics = {
        "engine": "Verilator SA",
        "cycles": 0,
        "iterations": 0,
        "accepted_moves": 0,
        "final_cost": 0,
        "final_temp": 0
    }

    # Parse stdout metrics
    for line in stdout.splitlines():
        line = line.strip()
        if "Clock Cycles" in line:
            m = re.search(r":\s*(\d+)", line)
            if m:
                metrics["cycles"] = int(m.group(1))
        elif "SA Iterations" in line:
            m = re.search(r":\s*(\d+)", line)
            if m:
                metrics["iterations"] = int(m.group(1))
        elif "Accepted Moves" in line:
            m = re.search(r":\s*(\d+)", line)
            if m:
                metrics["accepted_moves"] = int(m.group(1))
        elif "Final Cost" in line:
            m = re.search(r":\s*(\d+)", line)
            if m:
                metrics["final_cost"] = int(m.group(1))
        elif "Final Temp" in line:
            m = re.search(r":\s*(\d+)", line)
            if m:
                metrics["final_temp"] = int(m.group(1))

    return metrics


if __name__ == "__main__":
    test_in = os.path.join(RTL_DIR, "dummy_layout.hex")
    test_out = os.path.join(RTL_DIR, "output_layout.hex")
    res = run_verilator_legalizer(test_in, test_out)
    print("Verilator Bridge Result:", res)

