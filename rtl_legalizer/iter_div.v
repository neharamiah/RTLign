// ============================================================================
// RTLign — Iterative Restoring Divider (FPGA-friendly, multi-cycle)
// ============================================================================
// Replaces the combinational 64/32 divider in the Metropolis ratio path with
// a clocked long-division FSM: NUM_WIDTH cycles, small LUT footprint, no
// giant combinational cone. Unsigned, truncating — bit-identical to the
// Verilog `/` operator on the same operands.
//
// Protocol: pulse start with dividend/divisor held for one cycle; done
// pulses one cycle after the final iteration; quotient is registered.
// divisor == 0 is not handled here — callers must guard (the engine does).
// ============================================================================

`timescale 1ns / 1ps

module iter_div #(
    parameter NUM_WIDTH = 64,
    parameter DEN_WIDTH = 32
)(
    input  wire                   clk,
    input  wire                   rst,
    input  wire                   start,
    input  wire [NUM_WIDTH-1:0]   dividend,
    input  wire [DEN_WIDTH-1:0]   divisor,
    output reg                    done,
    output reg  [NUM_WIDTH-1:0]   quotient
);

    localparam CNT_WIDTH = $clog2(NUM_WIDTH);

    reg [NUM_WIDTH-1:0] quo_shift;   // quotient bits collected so far
    reg [NUM_WIDTH-1:0] num_shift;   // dividend, consumed MSB-first
    reg [DEN_WIDTH-1:0] den;         // divisor copy
    reg [DEN_WIDTH:0]   rem;         // partial remainder
    reg [CNT_WIDTH-1:0] iter;
    reg                 busy;

    // One restoring-division step: pull the next dividend bit into the
    // remainder, subtract the divisor when it fits.
    wire [DEN_WIDTH:0] rem_next = {rem[DEN_WIDTH-1:0], num_shift[NUM_WIDTH-1]};
    wire               geq      = (rem_next >= {1'b0, den});

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            done      <= 1'b0;
            busy      <= 1'b0;
            quo_shift <= {NUM_WIDTH{1'b0}};
            num_shift <= {NUM_WIDTH{1'b0}};
            den       <= {DEN_WIDTH{1'b0}};
            rem       <= {(DEN_WIDTH+1){1'b0}};
            iter      <= {CNT_WIDTH{1'b0}};
            quotient  <= {NUM_WIDTH{1'b0}};
        end else begin
            done <= 1'b0;
            if (start) begin
                busy      <= 1'b1;
                num_shift <= dividend;
                den       <= divisor;
                quo_shift <= {NUM_WIDTH{1'b0}};
                rem       <= {(DEN_WIDTH+1){1'b0}};
                iter      <= {CNT_WIDTH{1'b0}};
            end else if (busy) begin
                if (geq) begin
                    rem       <= rem_next - {1'b0, den};
                    quo_shift <= {quo_shift[NUM_WIDTH-2:0], 1'b1};
                end else begin
                    rem       <= rem_next;
                    quo_shift <= {quo_shift[NUM_WIDTH-2:0], 1'b0};
                end
                num_shift <= num_shift << 1;
                if (iter == NUM_WIDTH - 1) begin
                    busy     <= 1'b0;
                    done     <= 1'b1;
                    quotient <= {quo_shift[NUM_WIDTH-2:0], geq};
                end else begin
                    iter <= iter + {{(CNT_WIDTH-1){1'b0}}, 1'b1};
                end
            end
        end
    end

endmodule
