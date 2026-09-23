// ============================================================================
// RTLign — Simulated Annealing Cost Function
// ============================================================================
// Computes:
//   C_total = W_WL * HPWL + W_AREA * (Area_bbox >> AREA_SCALE_SHIFT) + W_BOUNDARY * C_boundary
//
// Where:
//   HPWL = (max_cx - min_cx) + (max_cy - min_cy)
//   Area_bbox = (max_right - min_left) * (max_top - min_bottom)
//   C_boundary = sum of macro boundary violation distances
// ============================================================================

`timescale 1ns / 1ps

module sa_cost #(
    parameter NUM_LINES        = 672,
    parameter DIE_WIDTH        = 200260,
    parameter DIE_HEIGHT       = 201600,
    parameter W_WL             = 4,
    parameter W_AREA           = 1,
    parameter W_BOUNDARY       = 8,
    parameter AREA_SCALE_SHIFT = 14
)(
    input  wire        clk,
    input  wire        rst,
    input  wire        start,
    output reg         done,

    // Memory read port
    output reg  [31:0] mem_addr,
    input  wire [31:0] mem_rdata,

    // Cost outputs
    output reg  [63:0] total_cost,
    output reg  [31:0] hpwl_out,
    output reg  [63:0] bbox_area_out,
    output reg  [31:0] boundary_penalty_out
);

    localparam NUM_MACROS = NUM_LINES / 4;

    // FSM states
    localparam S_IDLE    = 3'd0;
    localparam S_READ_X  = 3'd1;
    localparam S_READ_Y  = 3'd2;
    localparam S_READ_W  = 3'd3;
    localparam S_READ_H  = 3'd4;
    localparam S_CALC    = 3'd5;
    localparam S_DONE    = 3'd6;

    reg [2:0] state;
    reg [31:0] macro_idx;

    reg [31:0] cur_x, cur_y, cur_w, cur_h;
    reg [31:0] min_cx, max_cx;
    reg [31:0] min_cy, max_cy;
    reg [31:0] min_left, max_right;
    reg [31:0] min_bottom, max_top;
    reg [31:0] accum_boundary;

    wire [31:0] cur_h_val = (state == S_READ_H) ? mem_rdata : cur_h;
    wire [31:0] right     = cur_x + cur_w;
    wire [31:0] top       = cur_y + cur_h_val;
    wire [31:0] cx        = cur_x + (cur_w >> 1);
    wire [31:0] cy        = cur_y + (cur_h_val >> 1);

    wire signed [31:0] s_x = cur_x;
    wire signed [31:0] s_y = cur_y;
    wire signed [31:0] s_right = cur_x + cur_w;
    wire signed [31:0] s_top   = cur_y + cur_h_val;

    wire [31:0] pen_x = (s_x < 0) ? (32'd0 - s_x) :
                        (s_right > DIE_WIDTH) ? (s_right - DIE_WIDTH) : 32'd0;
    wire [31:0] pen_y = (s_y < 0) ? (32'd0 - s_y) :
                        (s_top > DIE_HEIGHT) ? (s_top - DIE_HEIGHT) : 32'd0;

    wire [31:0] span_cx = (max_cx > min_cx) ? (max_cx - min_cx) : 32'd0;
    wire [31:0] span_cy = (max_cy > min_cy) ? (max_cy - min_cy) : 32'd0;
    wire [31:0] hpwl    = span_cx + span_cy;

    wire [63:0] bbox_w  = (max_right > min_left)  ? (max_right - min_left)  : 64'd0;
    wire [63:0] bbox_h  = (max_top > min_bottom)  ? (max_top - min_bottom)  : 64'd0;
    wire [63:0] bbox_area = bbox_w * bbox_h;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state                <= S_IDLE;
            done                 <= 1'b0;
            mem_addr             <= 32'd0;
            total_cost           <= 64'd0;
            hpwl_out             <= 32'd0;
            bbox_area_out        <= 64'd0;
            boundary_penalty_out <= 32'd0;
            macro_idx            <= 32'd0;
            cur_x                <= 32'd0;
            cur_y                <= 32'd0;
            cur_w                <= 32'd0;
            cur_h                <= 32'd0;
            min_cx               <= 32'hFFFFFFFF;
            max_cx               <= 32'd0;
            min_cy               <= 32'hFFFFFFFF;
            max_cy               <= 32'd0;
            min_left             <= 32'hFFFFFFFF;
            max_right            <= 32'd0;
            min_bottom           <= 32'hFFFFFFFF;
            max_top              <= 32'd0;
            accum_boundary       <= 32'd0;
        end else begin
            case (state)
                S_IDLE: begin
                    done <= 1'b0;
                    if (start) begin
                        min_cx         <= 32'hFFFFFFFF;
                        max_cx         <= 32'd0;
                        min_cy         <= 32'hFFFFFFFF;
                        max_cy         <= 32'd0;
                        min_left       <= 32'hFFFFFFFF;
                        max_right      <= 32'd0;
                        min_bottom     <= 32'hFFFFFFFF;
                        max_top        <= 32'd0;
                        accum_boundary <= 32'd0;
                        macro_idx      <= 32'd0;
                        mem_addr       <= 32'd0; // Request X of macro 0
                        state          <= S_READ_X;
                    end
                end

                S_READ_X: begin
                    cur_x    <= mem_rdata;
                    mem_addr <= macro_idx * 4 + 1; // Request Y
                    state    <= S_READ_Y;
                end

                S_READ_Y: begin
                    cur_y    <= mem_rdata;
                    mem_addr <= macro_idx * 4 + 2; // Request W
                    state    <= S_READ_W;
                end

                S_READ_W: begin
                    cur_w    <= mem_rdata;
                    mem_addr <= macro_idx * 4 + 3; // Request H
                    state    <= S_READ_H;
                end

                S_READ_H: begin
                    cur_h <= mem_rdata;
                    // Update bounding box and boundary statistics
                    if (cx < min_cx) min_cx <= cx;
                    if (cx > max_cx) max_cx <= cx;
                    if (cy < min_cy) min_cy <= cy;
                    if (cy > max_cy) max_cy <= cy;

                    if (cur_x < min_left)  min_left  <= cur_x;
                    if (right > max_right) max_right <= right;
                    if (cur_y < min_bottom) min_bottom <= cur_y;
                    if (top > max_top)     max_top   <= top;

                    accum_boundary <= accum_boundary + pen_x + pen_y;

                    if (macro_idx + 1 >= NUM_MACROS) begin
                        state <= S_CALC;
                    end else begin
                        macro_idx <= macro_idx + 1;
                        mem_addr  <= (macro_idx + 1) * 4; // Request X of next macro
                        state     <= S_READ_X;
                    end
                end

                S_CALC: begin
                    hpwl_out             <= hpwl;
                    bbox_area_out        <= bbox_area;
                    boundary_penalty_out <= accum_boundary;
                    total_cost           <= (W_WL * hpwl) +
                                            (W_AREA * (bbox_area >> AREA_SCALE_SHIFT)) +
                                            (W_BOUNDARY * accum_boundary);
                    state                <= S_DONE;
                end

                S_DONE: begin
                    done  <= 1'b1;
                    state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
