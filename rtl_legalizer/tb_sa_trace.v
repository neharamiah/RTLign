// ============================================================================
// RTLign — sa_engine trace probe (debug tool)
// Prints per-iteration internals (selected macro, LFSR word, move bytes,
// Metropolis dice/threshold) so the Python golden model can be validated
// cycle by cycle. Input: dummy_layout.hex in the CWD.
// ============================================================================

`timescale 1ns / 1ps

module tb_sa_trace;

    parameter NUM_LINES = 32;

    reg  clk = 0;
    reg  rst = 1;
    reg  start = 0;
    wire done;
    wire [63:0] final_cost;
    wire [31:0] final_temp;
    wire [31:0] total_iters;
    wire [31:0] accepted_count;

    sa_engine #(
        .NUM_LINES(NUM_LINES)
    ) dut (
        .clk(clk), .rst(rst), .start(start), .done(done),
        .final_cost(final_cost), .final_temp(final_temp),
        .total_iters(total_iters), .accepted_count(accepted_count),
        .ext_mem_addr(32'd0),
        .ext_mem_rdata()
    );

    always #5 clk = ~clk;

    initial begin
        #200_000_000;
        $fatal(1, "TIMEOUT");
    end

    // FSM state encodings mirror sa_engine.v
    localparam ST_PERTURB     = 4'd3;
    localparam ST_APPLY_MOVE  = 4'd4;
    localparam ST_METROPOLIS  = 4'd6;
    localparam ST_LEGAL_SCAN  = 4'd9;

    always @(posedge clk) begin
        if (rst == 1'b0) begin
            if (dut.state == ST_PERTURB)
                $display("SEL %0d %h", dut.sel_macro, dut.rand_val);
            if (dut.state == ST_APPLY_MOVE)
                $display("MOVE %0d %0d", dut.raw_dx, dut.raw_dy);
            if (dut.state == ST_LEGAL_SCAN && !dut.scan_skip && dut.scan_hit)
                $display("ILLEGAL %0d %0d", dut.current_cost, dut.temperature);
            if (dut.state == ST_METROPOLIS)
                $display("MET %0d %0d %0d %0d %0d", dut.rand_val[15:0], dut.threshold,
                         dut.candidate_cost, dut.current_cost, dut.temperature);
        end
    end

    initial begin
        #20;
        rst = 0;
        #10;
        @(posedge clk); #1 start = 1;
        @(posedge clk); #1 start = 0;
        while (!done) @(posedge clk);
        #1;
        $display("FINAL %0d %0d %0d %0d", final_cost, final_temp, total_iters, accepted_count);
        $finish;
    end

endmodule
