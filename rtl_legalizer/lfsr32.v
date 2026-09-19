// ============================================================================
// RTLign — 32-bit Galois Linear Feedback Shift Register (LFSR)
// ============================================================================
// Maximal-length polynomial: x^32 + x^22 + x^2 + x^1 + 1
// Mask: 32'h80200003
// Period: 2^32 - 1 cycles
// ============================================================================

`timescale 1ns / 1ps

module lfsr32 (
    input  wire        clk,
    input  wire        rst,
    input  wire [31:0] seed,
    input  wire        enable,
    output wire [31:0] rand_out
);

    reg [31:0] lfsr;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            lfsr <= (seed != 32'b0) ? seed : 32'hDEAD_BEEF;
        end else if (enable) begin
            if (lfsr[0]) begin
                lfsr <= (lfsr >> 1) ^ 32'h80200003;
            end else begin
                lfsr <= (lfsr >> 1);
            end
        end
    end

    assign rand_out = lfsr;

endmodule

