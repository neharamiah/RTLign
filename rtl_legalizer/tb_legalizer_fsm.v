// ============================================================================
// RTLign — Unit testbench for legalizer_fsm.v (greedy sweep only)
// Generic driver: the Python harness writes dummy_layout.hex for the case,
// runs this TB with matching -P overrides, then parses and audits out.hex.
// Fails via $fatal on hang (watchdog) or missing done pulse.
// ============================================================================

`timescale 1ns / 1ps

module tb_legalizer_fsm;

    parameter NUM_LINES  = 672;
    parameter DIE_WIDTH  = 200260;
    parameter DIE_HEIGHT = 201600;

    reg  clk = 0;
    reg  rst = 1;
    reg  start = 0;
    wire done;
    integer cycles;

    legalizer_fsm #(
        .NUM_LINES(NUM_LINES),
        .DIE_WIDTH(DIE_WIDTH),
        .DIE_HEIGHT(DIE_HEIGHT)
    ) dut (
        .clk(clk),
        .rst(rst),
        .start(start),
        .done(done),
        .ext_we(1'b0),
        .ext_waddr(32'd0),
        .ext_wdata(32'd0),
        .ext_rdata()
    );

    always #5 clk = ~clk;

    initial begin
        #50_000_000;  // 50 ms watchdog — catches RESOLVE/CHECK infinite loops
        $fatal(1, "TIMEOUT: legalizer_fsm never asserted done");
    end

    initial begin
        rst   = 1;
        start = 0;
        #20;
        rst = 0;
        #10;

        @(posedge clk); #1 start = 1;
        @(posedge clk); #1 start = 0;
        cycles = 0;
        while (!done) begin
            @(posedge clk);
            cycles = cycles + 1;
        end

        $display("FSM DONE in %0d cycles", cycles);
        $writememh("out.hex", dut.layout_mem);
        $finish;
    end

endmodule
