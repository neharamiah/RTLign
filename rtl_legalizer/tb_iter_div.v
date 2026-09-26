// ============================================================================
// RTLign — Unit testbench for iter_div.v
// Self-checking: drives directed corner cases plus pseudo-random vectors and
// compares the iterative quotient against the combinational `/` operator on
// the same operands. $fatal on any mismatch.
// ============================================================================

`timescale 1ns / 1ps

module tb_iter_div;

    reg         clk = 0;
    reg         rst = 1;
    reg         start = 0;
    reg  [63:0] dividend = 64'd0;
    reg  [31:0] divisor  = 32'd1;
    wire        done;
    wire [63:0] quotient;

    iter_div dut (
        .clk(clk), .rst(rst), .start(start),
        .dividend(dividend), .divisor(divisor),
        .done(done), .quotient(quotient)
    );

    always #5 clk = ~clk;

    integer errors;
    integer i;
    reg [31:0] lfsr;
    reg [63:0] exp_q;
    reg [63:0] lo, hi;

    task run_case(input [63:0] n, input [31:0] d);
    begin
        @(negedge clk);
        dividend = n;
        divisor  = d;
        start    = 1;
        @(negedge clk);
        start    = 0;
        while (!done) @(posedge clk);
        #1;
        exp_q = n / d;
        if (quotient !== exp_q) begin
            errors = errors + 1;
            $display("FAIL: %0d / %0d -> %0d (expected %0d)",
                     n, d, quotient, exp_q);
        end
    end
    endtask

    initial begin
        #200_000_000;
        $fatal(1, "TIMEOUT");
    end

    initial begin
        errors = 0;

        rst = 1;
        #20;
        rst = 0;
        #10;

        // Directed corners
        run_case(64'd0,    32'd1);
        run_case(64'd5,    32'd2);
        run_case(64'd10,   32'd2);
        run_case(64'd7,    32'd7);
        run_case(64'd6,    32'd7);
        run_case(64'hFFFFFFFF, 32'd1);
        run_case(64'hFFFFFFFFFFFFFFFF, 32'd1);
        run_case(64'hFFFFFFFFFFFFFFFF, 32'hFFFFFFFF);
        run_case(64'h1_0000_0000, 32'hFFFF_FFFF);   // quotient 1, exercises high bits
        run_case(64'h0_FFFF_FFFF, 32'h2);           // full-width quotient
        run_case(64'd123456789, 32'd1000000);       // delta<<12 / T shape, quotient 0
        run_case(64'd4096_000_000, 32'd1000000);    // ratio just under saturation

        // Pseudo-random sweep (LFSR-driven operands; divisor kept nonzero)
        lfsr = 32'hDEAD_BEEF;
        for (i = 0; i < 200; i = i + 1) begin
            if (lfsr[0]) lfsr = (lfsr >> 1) ^ 32'h80200003;
            else         lfsr = (lfsr >> 1);
            lo = {lfsr, lfsr ^ 32'hA5A5_5A5A};
            if (lfsr[0]) lfsr = (lfsr >> 1) ^ 32'h80200003;
            else         lfsr = (lfsr >> 1);
            hi = {2'b00, lfsr | 32'd1};   // divisor in [1, 2^32)
            run_case(lo, hi[31:0]);
        end

        if (errors == 0) begin
            $display("ALL DIVIDER CHECKS PASSED");
            $finish;
        end else begin
            $fatal(1, "%0d divider checks failed", errors);
        end
    end

endmodule
