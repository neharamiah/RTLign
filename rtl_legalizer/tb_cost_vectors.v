// ============================================================================
// RTLign — sa_cost vector TB (golden-model validation)
// Loads dummy_layout.hex from the CWD, runs one cost evaluation with the
// default RTL parameters, and prints the four outputs on one line:
//   COST <total> <hpwl> <area> <boundary>
// The Python golden model computes the same values for comparison.
// ============================================================================

`timescale 1ns / 1ps

module tb_cost_vectors;

    parameter NUM_LINES = 672;

    reg         clk = 0;
    reg         rst = 1;
    reg         start = 0;
    wire        done;
    wire [31:0] mem_addr;
    reg  [31:0] mem_rdata;
    wire [63:0] total_cost;
    wire [31:0] hpwl;
    wire [63:0] area;
    wire [31:0] boundary;

    reg [31:0] mem [0:NUM_LINES-1];

    sa_cost #(
        .NUM_LINES(NUM_LINES)
    ) dut (
        .clk(clk), .rst(rst), .start(start), .done(done),
        .mem_addr(mem_addr), .mem_rdata(mem_rdata),
        .total_cost(total_cost), .hpwl_out(hpwl),
        .bbox_area_out(area), .boundary_penalty_out(boundary)
    );

    always #5 clk = ~clk;
    always @(*) mem_rdata = mem[mem_addr];

    initial begin
        $readmemh("dummy_layout.hex", mem);
        #20;
        rst = 0;
        #10;
        @(posedge clk); #1 start = 1;
        @(posedge clk); #1 start = 0;
        while (!done) @(posedge clk);
        #1;
        $display("COST %0d %0d %0d %0d", total_cost, hpwl, area, boundary);
        $finish;
    end

endmodule
