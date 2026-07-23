import os
import subprocess
import argparse
import glob

TOP_MODULE_MAP = {
    'swerv': 'veer_wrapper',
    'ibex': 'ibex_top',
    'opentitan_blocks': 'aes_cipher_core',
    'picorv32': 'picorv32'
}

EXCLUDE_DIRS = {'dv', 'tb', 'sim', 'examples', 'verilator', 'lint', 'formal', 'snapshots', 'tools', 'configs', 'testbench', 'google_riscv-dv', 'test', 'tests', 'fpv', 'pre_dv', 'prim_xilinx', 'shared', 'syn', 'spi_device', 'hmac', 'i2c', 'uart'}

def find_rtl_files(base_dir):
    """Finds all .v and .sv files in the given directory recursively, excluding testbenches and generated files."""
    rtl_files = []
    exclude_keywords = ('tracer', 'tracing', 'rvfi', 'prim_xilinx', 'flash', 'prim_lc', 'sdc_example', 'edn.sv', 'esc', 'prince', 'keccak', 'ascon', 'hmac', 'i2c', 'spi_device', 'uart', 'reg_top', 'racl', 'aes.sv', 'aes_wrap', '_adv', '_scr', 'adapter', 'diff', 'prim_edn_req', 'pad')
    for root, dirs, files in os.walk(base_dir):
        # Skip if current root directory contains any excluded directory name
        parts = set(os.path.normpath(root).split(os.sep))
        if parts.intersection(EXCLUDE_DIRS):
            continue
        for f in files:
            if (f.endswith('.v') or f.endswith('.sv')) and not any(k in f for k in exclude_keywords):
                rtl_files.append(os.path.join(root, f))
    return rtl_files

def run_pipeline(design, out_dir):
    src_dir = os.path.join("data", "rtl_sources", design)
    if not os.path.exists(src_dir):
        print(f"[ERROR] Source directory {src_dir} does not exist.")
        return False

    # Special handling for opentitan_blocks dummy packages
    if design == 'opentitan_blocks':
        dummy_pkg_file = os.path.join(src_dir, 'dummy_pkgs.sv')
        if not os.path.exists(dummy_pkg_file):
            with open(dummy_pkg_file, 'w') as f:
                f.write('''
package keymgr_pkg;
  parameter int Width = 384;
  typedef struct packed {
    logic [Width-1:0] key;
    logic valid;
  } hw_key_req_t;
endpackage

package lc_ctrl_pkg;
  parameter int TxWidth = 4;
  typedef logic [TxWidth-1:0] lc_tx_t;
  parameter lc_tx_t Off = 4'b1010;
  parameter lc_tx_t On = 4'b0101;
  function automatic logic lc_tx_test_true_loose(lc_tx_t val); return (val == On); endfunction;
endpackage

package edn_pkg;
  parameter int ENDPOINT_BUS_WIDTH = 32;
  typedef logic [31:0] edn_req_t;
  typedef logic [31:0] edn_rsp_t;
endpackage
''')

    rtl_files = find_rtl_files(src_dir)
    if design == 'opentitan_blocks':
        ibex_prim = os.path.join("data", "rtl_sources", "ibex", "vendor", "lowrisc_ip", "ip", "prim_generic", "rtl")
        if os.path.exists(ibex_prim):
            rtl_files.extend(find_rtl_files(ibex_prim))
    if not rtl_files:
        print(f"[ERROR] No RTL files found in {src_dir}")
        return False

    # Sky130 PDK Paths
    pdk_base = os.path.join("data", "sky130_pdk", "sky130_fd_sc_hd")
    lib_file = os.path.join(pdk_base, "timing", "sky130_fd_sc_hd__tt_025C_1v80.lib")
    tech_lef = os.path.join(pdk_base, "tech", "sky130_fd_sc_hd__nom.tlef")
    macro_lef = os.path.join(pdk_base, "sky130_fd_sc_hd_merged.lef")
    
    if not os.path.exists(lib_file):
        print(f"[ERROR] Missing PDK library file: {lib_file}")
        return False

    design_out = os.path.join(out_dir, design)
    os.makedirs(design_out, exist_ok=True)
    
    synth_netlist = os.path.join(design_out, f"{design}_synth.v")
    out_def = os.path.join(design_out, "floorplan.def")

    if os.path.exists(out_def):
        print(f"[{design}] Floorplan DEF already exists: {out_def}. Skipping synthesis.")
        return True

    # If design is swerv, run veer.config to generate common_defines.vh if needed
    if design == 'swerv':
        config_script = os.path.join(src_dir, "configs", "veer.config")
        defines_vh = os.path.join(src_dir, "snapshots", "default", "common_defines.vh")
        if os.path.exists(config_script) and not os.path.exists(defines_vh):
            print(f"[{design}] Generating VeeR config defines...")
            subprocess.run(["./configs/veer.config"], cwd=src_dir, env=dict(os.environ, RV_ROOT="."), check=True)

    # Discover all include directories under src_dir
    include_dirs = set()
    for root, dirs, files in os.walk(src_dir):
        parts = set(os.path.normpath(root).split(os.sep))
        if parts.intersection(EXCLUDE_DIRS):
            continue
        if any(f.endswith(('.sv', '.svh', '.v', '.vh', '.h')) for f in files):
            include_dirs.add(root)
            
    snapshots_dir = os.path.join(src_dir, "snapshots", "default")
    if os.path.exists(snapshots_dir):
        include_dirs.add(snapshots_dir)

    # Step 1: Pre-process SV files using sv2v (from OSS-CAD-Suite)
    sv_files = [f for f in rtl_files if f.endswith('.sv')]
    v_files = [f for f in rtl_files if f.endswith('.v')]
    
    # Check for defines files to put at front
    header_files = []
    defines_vh = os.path.join(src_dir, "snapshots", "default", "common_defines.vh")
    if os.path.exists(defines_vh):
        header_files.append(defines_vh)

    flattened_rtl = os.path.join(design_out, f"{design}_flattened.v")
    
    print(f"[{design}] Flattening SystemVerilog with sv2v...")
    if sv_files:
        inc_flags = []
        for inc_dir in include_dirs:
            inc_flags.extend(["-I", inc_dir])
            
        sv2v_cmd = ["./oss-cad-suite/bin/sv2v", "-D", "SYNTHESIS", "-D", "PHYSICAL", "-D", "RV_FPGA_OPTIMIZE"] + inc_flags + header_files + sv_files + v_files
        try:
            with open(flattened_rtl, "w") as f:
                subprocess.run(sv2v_cmd, stdout=f, check=True)
        except Exception as e:
            print(f"[ERROR] sv2v failed: {e}")
            return False
    else:
        # Just concatenate regular verilog files
        with open(flattened_rtl, "w") as out_f:
            for v_file in v_files:
                with open(v_file, "r") as in_f:
                    out_f.write(in_f.read())
                    out_f.write("\n")

    # Step 2: Yosys Synthesis
    top_module = TOP_MODULE_MAP.get(design, design)
    print(f"[{design}] Running Yosys synthesis (top module: {top_module})...")
    env = os.environ.copy()
    env["DESIGN_NAME"] = top_module
    env["RTL_FILES"] = flattened_rtl
    env["LIB_FILE"] = lib_file
    
    yosys_cmd = ["./oss-cad-suite/bin/yosys", "-c", "data/openroad_configs/synth.tcl"]
    try:
        # We also need to capture output so it doesn't spam
        subprocess.run(yosys_cmd, env=env, check=True, stdout=subprocess.DEVNULL)
        # Move the synth netlist to correct location (the tcl writes it to pwd)
        if os.path.exists("synth_netlist.v"):
            os.rename("synth_netlist.v", synth_netlist)
    except Exception as e:
        print(f"[ERROR] Yosys failed: {e}")
        return False

    # Step 3: OpenROAD Floorplanning
    print(f"[{design}] Running OpenROAD floorplanning...")
    env["TECH_LEF"] = tech_lef
    env["MACRO_LEF"] = macro_lef
    env["SYNTH_NETLIST"] = synth_netlist
    env["OUT_DEF"] = out_def
    
    or_cmd = ["openroad", "-no_init", "-exit", "data/openroad_configs/floorplan.tcl"]
    try:
        subprocess.run(or_cmd, env=env, check=True, stdout=subprocess.DEVNULL)
    except Exception as e:
        print(f"[ERROR] OpenROAD failed: {e}")
        return False

    print(f"[{design}] Successfully generated {out_def}")
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", required=True, help="Design name in data/rtl_sources")
    parser.add_argument("--out_dir", default="data/ispd_benchmarks/rtl_generated", help="Output directory mimicking ISPD format")
    args = parser.parse_args()

    run_pipeline(args.design, args.out_dir)

if __name__ == "__main__":
    main()
