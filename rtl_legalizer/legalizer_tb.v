// ============================================================================
// RTLign — Legalizer Testbench
// ============================================================================
// Drives the legalizer_fsm, waits for the `done` signal, then dumps the
// legalized layout memory to `output_layout.hex` via $writememh.
// Also performs a post-legalization overlap audit and prints a summary.
// ============================================================================

`timescale 1ns / 1ps

module legalizer_tb;

    // -----------------------------------------------------------------------
    // Parameters — must match the DUT
    // -----------------------------------------------------------------------
    parameter NUM_LINES  = 672;
    parameter DIE_WIDTH  = 200260;
    parameter DIE_HEIGHT = 201600;

    localparam NUM_MACROS = NUM_LINES / 4;

    // -----------------------------------------------------------------------
    // DUT signals
    // -----------------------------------------------------------------------
    reg  clk;
    reg  rst;
    reg  start;
    wire done;

    legalizer_fsm #(
        .NUM_LINES  (NUM_LINES),
        .DIE_WIDTH  (DIE_WIDTH),
        .DIE_HEIGHT (DIE_HEIGHT)
    ) dut (
        .clk   (clk),
        .rst   (rst),
        .start (start),
        .done  (done)
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
    // Main test sequence
    // -----------------------------------------------------------------------
    integer cycle_count;
    
    initial begin
        // Optional: dump waveform for debugging
        $dumpfile("legalizer.vcd");
        $dumpvars(0, legalizer_tb);

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
        $display("========================================");

        start = 1;
        cycle_count = 0;
        @(posedge clk);
        start = 0;

        // --- Wait for completion ---
        while (!done) begin
            @(posedge clk);
            cycle_count = cycle_count + 1;
        end

        $display("");
        $display("  Legalization complete in %0d clock cycles.", cycle_count);
        $display("");

        // --- Dump results ---
        $writememh("output_layout.hex", dut.layout_mem);
        $display("  Output written to: output_layout.hex");

        // --- Post-legalization overlap audit ---
        run_overlap_audit;

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

endmodule
