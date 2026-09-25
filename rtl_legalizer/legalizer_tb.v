// ============================================================================
// RTLign — Legalizer Testbench (SA Optimizer + Greedy Cleanup)
// ============================================================================
// Drives sa_legalizer_top, waits for the `done` signal, then dumps the
// legalized layout memory to `output_layout.hex` via $writememh.
// Also performs a post-legalization overlap audit and prints SA metrics.
// ============================================================================

`timescale 1ns / 1ps

module legalizer_tb;

    // -----------------------------------------------------------------------
    // Parameters — must match the DUT
    // -----------------------------------------------------------------------
    parameter NUM_LINES   = 672;
    parameter DIE_WIDTH   = 200260;
    parameter DIE_HEIGHT  = 201600;
    parameter ENABLE_SA   = 1;
    parameter T_INIT      = 1000000;
    parameter T_MIN       = 100;
    parameter COOL_SHIFT  = 3;
    parameter INNER_ITERS = 100;
    parameter MAX_ITERS   = 1000;
    parameter W_WL        = 4;
    parameter W_AREA      = 1;
    parameter W_BOUNDARY  = 8;

    localparam NUM_MACROS = NUM_LINES / 4;

    // -----------------------------------------------------------------------
    // DUT signals
    // -----------------------------------------------------------------------
    reg  clk;
    reg  rst;
    reg  start;
    wire done;

    wire [63:0] final_cost;
    wire [31:0] final_temp;
    wire [31:0] total_iters;
    wire [31:0] accepted_count;

    sa_legalizer_top #(
        .NUM_LINES   (NUM_LINES),
        .DIE_WIDTH   (DIE_WIDTH),
        .DIE_HEIGHT  (DIE_HEIGHT),
        .ENABLE_SA   (ENABLE_SA),
        .T_INIT      (T_INIT),
        .T_MIN       (T_MIN),
        .COOL_SHIFT  (COOL_SHIFT),
        .INNER_ITERS (INNER_ITERS),
        .MAX_ITERS   (MAX_ITERS),
        .W_WL        (W_WL),
        .W_AREA      (W_AREA),
        .W_BOUNDARY  (W_BOUNDARY)
    ) dut (
        .clk            (clk),
        .rst            (rst),
        .start          (start),
        .done           (done),
        .out_addr       (10'd0),
        .out_data       (),
        .final_cost     (final_cost),
        .final_temp     (final_temp),
        .total_iters    (total_iters),
        .accepted_count (accepted_count)
    );

    // -----------------------------------------------------------------------
    // Clock generation — 10 ns period (100 MHz)
    // -----------------------------------------------------------------------
    initial clk = 0;
    always #5 clk = ~clk;

    // -----------------------------------------------------------------------
    // Simulation timeout safety net
    // -----------------------------------------------------------------------
    initial begin
        #100_000_000;  // 100 ms wall time
        $display("ERROR: Simulation timed out after 100 ms!");
        $finish;
    end

    // -----------------------------------------------------------------------
    // Input reference copy — used by the size-preservation audit (P3)
    // -----------------------------------------------------------------------
    reg [31:0] input_mem [0:NUM_LINES-1];
    initial $readmemh("dummy_layout.hex", input_mem);

    // -----------------------------------------------------------------------
    // Main test sequence
    // -----------------------------------------------------------------------
    integer cycle_count;
    
    initial begin
        // Optional: dump waveform for debugging
        // $dumpfile("legalizer.vcd");
        // $dumpvars(0, legalizer_tb);

        // --- Reset ---
        rst   = 1;
        start = 0;
        #20;
        rst = 0;
        #10;

        // --- Start the engine ---
        $display("========================================");
        $display("  RTLign Legalizer — Simulation Start");
        $display("  Macros: %0d | Die: %0d x %0d", NUM_MACROS, DIE_WIDTH, DIE_HEIGHT);
        if (ENABLE_SA)
            $display("  Engine: SA Optimizer + Greedy Cleanup");
        else
            $display("  Engine: Greedy Sweep Only");
        $display("========================================");

        @(posedge clk);
        #1 start = 1;
        cycle_count = 0;
        @(posedge clk);
        #1 start = 0;

        // --- Wait for completion ---
        while (!done) begin
            @(posedge clk);
            cycle_count = cycle_count + 1;
        end

        $display("");
        $display("  Legalization complete in %0d clock cycles.", cycle_count);
        if (ENABLE_SA) begin
            $display("  [SA METRICS]");
            $display("    Iterations      : %0d", total_iters);
            $display("    Accepted Moves  : %0d", accepted_count);
            $display("    Final Cost      : %0d", final_cost);
            $display("    Final Temp      : %0d", final_temp);
        end
        $display("");

        // --- Dump results ---
        $writememh("output_layout.hex", dut.layout_mem);
        $display("  Output written to: output_layout.hex");

        // --- Post-legalization audits: overlaps, die bounds, size integrity ---
        run_overlap_audit;
        run_boundary_audit;
        run_size_audit;

        if ((overlap_count != 0) || (boundary_count != 0) || (size_count != 0))
            $fatal(1, "LEGALIZATION AUDIT FAILED: %0d overlaps, %0d boundary violations, %0d size mismatches",
                   overlap_count, boundary_count, size_count);
        $display("  ALL AUDITS PASSED");

        $display("");
        $display("========================================");
        $display("  Simulation Finished");
        $display("========================================");
        $finish;
    end

    // -----------------------------------------------------------------------
    // Overlap Audit Task — checks all pairs for remaining overlaps
    // -----------------------------------------------------------------------
    integer i, j;
    integer overlap_count;
    reg [31:0] ax, ay, aw, ah, bx, by, bw, bh;
    reg [31:0] ar, at, br, bt;  // right and top edges

    task run_overlap_audit;
    begin
        overlap_count = 0;
        for (i = 0; i < NUM_MACROS; i = i + 1) begin
            ax = dut.layout_mem[i*4];
            ay = dut.layout_mem[i*4 + 1];
            aw = dut.layout_mem[i*4 + 2];
            ah = dut.layout_mem[i*4 + 3];
            ar = ax + aw;
            at = ay + ah;

            for (j = i + 1; j < NUM_MACROS; j = j + 1) begin
                bx = dut.layout_mem[j*4];
                by = dut.layout_mem[j*4 + 1];
                bw = dut.layout_mem[j*4 + 2];
                bh = dut.layout_mem[j*4 + 3];
                br = bx + bw;
                bt = by + bh;

                if ((ax < br) && (ar > bx) && (ay < bt) && (at > by)) begin
                    overlap_count = overlap_count + 1;
                    if (overlap_count <= 10)
                        $display("  OVERLAP: macro[%0d] (%0d,%0d %0dx%0d) vs macro[%0d] (%0d,%0d %0dx%0d)",
                                 i, ax, ay, aw, ah, j, bx, by, bw, bh);
                end
            end
        end

        if (overlap_count == 0)
            $display("  AUDIT PASS: Zero overlaps detected!");
        else
            $display("  AUDIT FAIL: %0d overlaps remain (showing first 10 above).", overlap_count);
    end
    endtask

    // -----------------------------------------------------------------------
    // Boundary Audit — every macro must satisfy 0 <= x, x+w <= DIE_WIDTH
    // and 0 <= y, y+h <= DIE_HEIGHT (P2). Coordinates are unsigned 32-bit,
    // so a wrapped "negative" coordinate appears as a huge value and is
    // caught by the x > DIE_WIDTH test. Sums use 64 bits to avoid wrap.
    // -----------------------------------------------------------------------
    integer boundary_count;
    reg [63:0] sum_x, sum_y;

    task run_boundary_audit;
    begin
        boundary_count = 0;
        for (i = 0; i < NUM_MACROS; i = i + 1) begin
            ax = dut.layout_mem[i*4];
            ay = dut.layout_mem[i*4 + 1];
            aw = dut.layout_mem[i*4 + 2];
            ah = dut.layout_mem[i*4 + 3];
            sum_x = ax + aw;
            sum_y = ay + ah;
            if ((ax > DIE_WIDTH) || (sum_x > DIE_WIDTH)) begin
                boundary_count = boundary_count + 1;
                if (boundary_count <= 10)
                    $display("  BOUNDARY: macro[%0d] x=%0d x+w=%0d exceeds die width %0d",
                             i, ax, sum_x, DIE_WIDTH);
            end
            if ((ay > DIE_HEIGHT) || (sum_y > DIE_HEIGHT)) begin
                boundary_count = boundary_count + 1;
                if (boundary_count <= 10)
                    $display("  BOUNDARY: macro[%0d] y=%0d y+h=%0d exceeds die height %0d",
                             i, ay, sum_y, DIE_HEIGHT);
            end
        end

        if (boundary_count == 0)
            $display("  AUDIT PASS: All macros inside the die.");
        else
            $display("  AUDIT FAIL: %0d boundary violations (showing first 10 above).", boundary_count);
    end
    endtask

    // -----------------------------------------------------------------------
    // Size Audit — output W/H must equal input W/H for every macro (P3).
    // The legalizer moves macros; it must never resize them.
    // -----------------------------------------------------------------------
    integer size_count;

    task run_size_audit;
    begin
        size_count = 0;
        for (i = 0; i < NUM_MACROS; i = i + 1) begin
            if (dut.layout_mem[i*4 + 2] !== input_mem[i*4 + 2]) begin
                size_count = size_count + 1;
                if (size_count <= 10)
                    $display("  SIZE: macro[%0d] width in=%0d out=%0d",
                             i, input_mem[i*4 + 2], dut.layout_mem[i*4 + 2]);
            end
            if (dut.layout_mem[i*4 + 3] !== input_mem[i*4 + 3]) begin
                size_count = size_count + 1;
                if (size_count <= 10)
                    $display("  SIZE: macro[%0d] height in=%0d out=%0d",
                             i, input_mem[i*4 + 3], dut.layout_mem[i*4 + 3]);
            end
        end

        if (size_count == 0)
            $display("  AUDIT PASS: All macro sizes preserved.");
        else
            $display("  AUDIT FAIL: %0d size mismatches (showing first 10 above).", size_count);
    end
    endtask

endmodule
