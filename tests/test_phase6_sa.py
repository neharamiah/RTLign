"""
Phase 6 Automated Test Suite — Verilog Simulated Annealing Engine & Verilator Bridge.

Tests:
1. LFSR randomness and compilation
2. SA cost module calculation
3. Verilator compilation and high-speed simulation
4. SA metrics reporting
5. Overlap elimination and legality verification
"""

import os
import shutil
import subprocess
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RTL_DIR = os.path.join(PROJECT_ROOT, "rtl_legalizer")
VERILATOR_DIR = os.path.join(RTL_DIR, "verilator")


class TestLFSR32:
    def test_lfsr_compilation_and_execution(self, tmp_path):
        """Verify lfsr32 compiles with iverilog and produces non-repeating values."""
        tb_content = """`timescale 1ns/1ps
module tb;
    reg clk = 0;
    reg rst = 1;
    reg [31:0] seed = 32'h12345678;
    reg en = 1;
    wire [31:0] rand_out;

    lfsr32 dut (.clk(clk), .rst(rst), .seed(seed), .enable(en), .rand_out(rand_out));
    always #5 clk = ~clk;

    integer i;
    reg [31:0] v1, v2;
    initial begin
        #20 rst = 0;
        @(posedge clk); #1; v1 = rand_out;
        @(posedge clk); #1; v2 = rand_out;
        if (v1 == v2 || v1 == 32'b0 || v2 == 32'b0) begin
            $display("FAIL");
            $finish;
        end
        $display("PASS");
        $finish;
    end
endmodule
"""
        tb_file = tmp_path / "tb.v"
        tb_file.write_text(tb_content)
        sim_out = tmp_path / "sim.out"

        res = subprocess.run(
            ["iverilog", "-o", str(sim_out), os.path.join(RTL_DIR, "lfsr32.v"), str(tb_file)],
            capture_output=True,
            text=True
        )
        assert res.returncode == 0, f"Compilation failed: {res.stderr}"

        res_sim = subprocess.run(["vvp", str(sim_out)], capture_output=True, text=True)
        assert "PASS" in res_sim.stdout


class TestSACost:
    def test_sa_cost_calculation(self, tmp_path):
        """Verify sa_cost accurately computes HPWL, area, and boundary penalties."""
        tb_content = """`timescale 1ns/1ps
module cost_tb;
    reg clk = 0;
    reg rst = 1;
    reg start = 0;
    wire done;
    wire [31:0] mem_addr;
    reg  [31:0] mem_rdata;
    wire [63:0] total_cost;
    wire [31:0] hpwl;
    wire [63:0] area;
    wire [31:0] boundary;

    reg [31:0] mem [0:7];

    sa_cost #(
        .NUM_LINES(8),
        .DIE_WIDTH(1000),
        .DIE_HEIGHT(1000),
        .W_WL(4),
        .W_AREA(1),
        .W_BOUNDARY(8),
        .AREA_SCALE_SHIFT(0)
    ) dut (
        .clk(clk), .rst(rst), .start(start), .done(done),
        .mem_addr(mem_addr), .mem_rdata(mem_rdata),
        .total_cost(total_cost), .hpwl_out(hpwl),
        .bbox_area_out(area), .boundary_penalty_out(boundary)
    );

    always #5 clk = ~clk;
    always @(posedge clk) mem_rdata <= mem[mem_addr];

    initial begin
        mem[0] = 100; mem[1] = 200; mem[2] = 50; mem[3] = 60;
        mem[4] = 300; mem[5] = 400; mem[6] = 100; mem[7] = 100;
        #20 rst = 0;
        @(posedge clk); #1 start = 1;
        @(posedge clk); #1 start = 0;
        while (!done) @(posedge clk);
        #1;
        if (hpwl == 445 && area == 90000 && boundary == 0 && total_cost == 91780)
            $display("PASS_COST");
        else
            $display("FAIL_COST hpwl=%0d area=%0d bnd=%0d cost=%0d", hpwl, area, boundary, total_cost);
        $finish;
    end
endmodule
"""
        tb_file = tmp_path / "cost_tb.v"
        tb_file.write_text(tb_content)
        sim_out = tmp_path / "cost_sim.out"

        res = subprocess.run(
            ["iverilog", "-o", str(sim_out), os.path.join(RTL_DIR, "sa_cost.v"), str(tb_file)],
            capture_output=True,
            text=True
        )
        assert res.returncode == 0, f"Compilation failed: {res.stderr}"

        res_sim = subprocess.run(["vvp", str(sim_out)], capture_output=True, text=True)
        assert "PASS_COST" in res_sim.stdout


class TestVerilatorBridge:
    def test_verilator_build_and_simulation(self, tmp_path):
        """Verify Verilator builds and legalizes dummy_layout.hex with 0 overlaps."""
        from rtl_legalizer.verilator.verilator_bridge import run_verilator_legalizer

        dummy_hex = os.path.join(RTL_DIR, "dummy_layout.hex")
        out_hex = tmp_path / "test_out.hex"

        metrics = run_verilator_legalizer(dummy_hex, str(out_hex))
        assert metrics["cycles"] > 0
        assert metrics["iterations"] > 0
        assert metrics["accepted_moves"] > 0
        assert metrics["final_cost"] > 0
        assert os.path.isfile(out_hex)

        # Audit overlaps
        with open(out_hex) as f:
            lines = [int(line.strip(), 16) for line in f if line.strip()]
        macros = [lines[i:i+4] for i in range(0, len(lines), 4)]
        assert len(macros) == 168

        overlaps = 0
        for i in range(len(macros)):
            x1, y1, w1, h1 = macros[i]
            r1, t1 = x1 + w1, y1 + h1
            for j in range(i + 1, len(macros)):
                x2, y2, w2, h2 = macros[j]
                r2, t2 = x2 + w2, y2 + h2
                if x1 < r2 and r1 > x2 and y1 < t2 and t1 > y2:
                    overlaps += 1
        assert overlaps == 0, f"Expected 0 overlaps, found {overlaps}"


class TestIcarusSAPipeline:
    def test_icarus_sa_runs_and_cleans_overlaps(self, tmp_path):
        """Verify Icarus Verilog compiles and runs SA + Greedy Cleanup with 0 overlaps."""
        sim_out = tmp_path / "sim.out"
        out_hex = tmp_path / "out.hex"

        srcs = [
            os.path.join(RTL_DIR, "collision_check.v"),
            os.path.join(RTL_DIR, "iter_div.v"),
            os.path.join(RTL_DIR, "lfsr32.v"),
            os.path.join(RTL_DIR, "sa_cost.v"),
            os.path.join(RTL_DIR, "sa_engine.v"),
            os.path.join(RTL_DIR, "legalizer_fsm.v"),
            os.path.join(RTL_DIR, "sa_legalizer_top.v"),
            os.path.join(RTL_DIR, "legalizer_tb.v"),
        ]

        cmd = [
            "iverilog",
            "-Plegalizer_tb.NUM_LINES=672",
            "-Plegalizer_tb.ENABLE_SA=1",
            "-Plegalizer_tb.MAX_ITERS=500",
            "-Plegalizer_tb.INNER_ITERS=50",
            "-o", str(sim_out)
        ] + srcs

        res = subprocess.run(cmd, capture_output=True, text=True, cwd=RTL_DIR)
        assert res.returncode == 0, f"Compilation failed: {res.stderr}"

        res_sim = subprocess.run(["vvp", str(sim_out)], capture_output=True, text=True, cwd=RTL_DIR)
        assert res_sim.returncode == 0
        assert "AUDIT PASS: Zero overlaps detected!" in res_sim.stdout
        assert "Final Cost" in res_sim.stdout

