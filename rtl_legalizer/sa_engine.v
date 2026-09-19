// ============================================================================
// RTLign — Simulated Annealing (SA) Placement Optimizer
// ============================================================================
// Explores the macro placement solution space using stochastic hill-climbing
// with an adaptive temperature schedule and true Metropolis acceptance.
// Minimizes C_total = w_wl*HPWL + w_area*Area_bbox + C_boundary.
// ============================================================================

`timescale 1ns / 1ps

module sa_engine #(
    parameter NUM_LINES        = 672,
    parameter DIE_WIDTH        = 200260,
    parameter DIE_HEIGHT       = 201600,
    parameter T_INIT           = 1000000,
    parameter T_MIN            = 100,
    parameter COOL_SHIFT       = 3,
    parameter INNER_ITERS      = 100,
    parameter MAX_ITERS        = 1000,
    parameter W_WL             = 4,
    parameter W_AREA           = 1,
    parameter W_BOUNDARY       = 8,
    parameter AREA_SCALE_SHIFT = 14,
    parameter LFSR_SEED        = 32'hDEAD_BEEF
)(
    input  wire        clk,
    input  wire        rst,
    input  wire        start,
    output reg         done,

    // Performance & Convergence Metrics
    output reg  [63:0] final_cost,
    output reg  [31:0] final_temp,
    output reg  [31:0] total_iters,
    output reg  [31:0] accepted_count,

    // External Memory Read Interface (for copying to greedy cleanup pass)
    input  wire [31:0] ext_mem_addr,
    output wire [31:0] ext_mem_rdata
);

    localparam NUM_MACROS = NUM_LINES / 4;
    localparam MEM_DEPTH  = NUM_LINES;

    // -----------------------------------------------------------------------
    // Internal Layout Memory
    // -----------------------------------------------------------------------
    reg [31:0] layout_mem [0:MEM_DEPTH-1];
    initial $readmemh("dummy_layout.hex", layout_mem);

    assign ext_mem_rdata = (ext_mem_addr < MEM_DEPTH) ? layout_mem[ext_mem_addr] : 32'd0;

    // -----------------------------------------------------------------------
    // LFSR Random Number Generator
    // -----------------------------------------------------------------------
    reg  lfsr_en;
    wire [31:0] rand_val;

    lfsr32 lfsr_inst (
        .clk(clk),
        .rst(rst),
        .seed(LFSR_SEED),
        .enable(lfsr_en),
        .rand_out(rand_val)
    );

    // -----------------------------------------------------------------------
    // Cost Evaluation Submodule
    // -----------------------------------------------------------------------
    reg         cost_start;
    wire        cost_done;
    wire [31:0] cost_mem_addr;
    wire [63:0] cost_total;
    wire [31:0] cost_hpwl;
    wire [63:0] cost_bbox_area;
    wire [31:0] cost_boundary_pen;

    sa_cost #(
        .NUM_LINES(NUM_LINES),
        .DIE_WIDTH(DIE_WIDTH),
        .DIE_HEIGHT(DIE_HEIGHT),
        .W_WL(W_WL),
        .W_AREA(W_AREA),
        .W_BOUNDARY(W_BOUNDARY),
        .AREA_SCALE_SHIFT(AREA_SCALE_SHIFT)
    ) cost_inst (
        .clk(clk),
        .rst(rst),
        .start(cost_start),
        .done(cost_done),
        .mem_addr(cost_mem_addr),
        .mem_rdata(layout_mem[cost_mem_addr]),
        .total_cost(cost_total),
        .hpwl_out(cost_hpwl),
        .bbox_area_out(cost_bbox_area),
        .boundary_penalty_out(cost_boundary_pen)
    );

    // -----------------------------------------------------------------------
    // 32-entry Exponential LUT for Metropolis acceptance P = exp(-delta / T)
    // ratio = (delta << 12) / T. Index is ratio[11:7] (0 to 31).
    // Values scaled to 16-bit range [0, 65535].
    // -----------------------------------------------------------------------
    reg [15:0] exp_lut [0:31];
    initial begin
        exp_lut[0]  = 16'd65535; // exp(-0.000)
        exp_lut[1]  = 16'd57849; // exp(-0.125)
        exp_lut[2]  = 16'd51065; // exp(-0.250)
        exp_lut[3]  = 16'd45077; // exp(-0.375)
        exp_lut[4]  = 16'd39791; // exp(-0.500)
        exp_lut[5]  = 16'd35125; // exp(-0.625)
        exp_lut[6]  = 16'd31006; // exp(-0.750)
        exp_lut[7]  = 16'd27370; // exp(-0.875)
        exp_lut[8]  = 16'd24161; // exp(-1.000)
        exp_lut[9]  = 16'd21327; // exp(-1.125)
        exp_lut[10] = 16'd18826; // exp(-1.250)
        exp_lut[11] = 16'd16618; // exp(-1.375)
        exp_lut[12] = 16'd14669; // exp(-1.500)
        exp_lut[13] = 16'd12949; // exp(-1.625)
        exp_lut[14] = 16'd11430; // exp(-1.750)
        exp_lut[15] = 16'd10090; // exp(-1.875)
        exp_lut[16] = 16'd8906;  // exp(-2.000)
        exp_lut[17] = 16'd7862;  // exp(-2.125)
        exp_lut[18] = 16'd6940;  // exp(-2.250)
        exp_lut[19] = 16'd6126;  // exp(-2.375)
        exp_lut[20] = 16'd5408;  // exp(-2.500)
        exp_lut[21] = 16'd4774;  // exp(-2.625)
        exp_lut[22] = 16'd4214;  // exp(-2.750)
        exp_lut[23] = 16'd3720;  // exp(-2.875)
        exp_lut[24] = 16'd3283;  // exp(-3.000)
        exp_lut[25] = 16'd2898;  // exp(-3.125)
        exp_lut[26] = 16'd2558;  // exp(-3.250)
        exp_lut[27] = 16'd2258;  // exp(-3.375)
        exp_lut[28] = 16'd1993;  // exp(-3.500)
        exp_lut[29] = 16'd1759;  // exp(-3.625)
        exp_lut[30] = 16'd1553;  // exp(-3.750)
        exp_lut[31] = 16'd1371;  // exp(-3.875)
    end

    // -----------------------------------------------------------------------
    // FSM States
    // -----------------------------------------------------------------------
    localparam ST_IDLE          = 4'd0;
    localparam ST_INIT_COST     = 4'd1;
    localparam ST_WAIT_INIT     = 4'd2;
    localparam ST_PERTURB       = 4'd3;
    localparam ST_APPLY_MOVE    = 4'd4;
    localparam ST_WAIT_EVAL     = 4'd5;
    localparam ST_METROPOLIS    = 4'd6;
    localparam ST_CHECK_INNER   = 4'd7;
    localparam ST_DONE          = 4'd8;

    reg [3:0]  state;
    reg [31:0] temperature;
    reg [31:0] inner_count;
    reg [63:0] current_cost;
    reg [63:0] candidate_cost;

    // Saved state of perturbed macro for rollback
    reg [31:0] sel_macro;
    reg [31:0] saved_x;
    reg [31:0] saved_y;
    reg [31:0] macro_w;
    reg [31:0] macro_h;

    // Displacement calculation registers
    reg signed [31:0] disp_scale;
    reg signed [31:0] raw_dx, raw_dy;
    reg signed [31:0] cand_x, cand_y;

    // Metropolis threshold calculation
    wire [63:0] delta_cost = (candidate_cost > current_cost) ? (candidate_cost - current_cost) : 64'd0;
    wire [31:0] delta_32   = (delta_cost > 64'hFFFFFFFF) ? 32'hFFFFFFFF : delta_cost[31:0];
    wire [63:0] scaled_delta = (delta_cost << 12);
    wire [31:0] ratio = (temperature > 0) ? (scaled_delta / temperature) : 32'hFFFFFFFF;
    wire [4:0]  lut_idx = (ratio[16:12] != 0) ? 5'd31 : ratio[11:7];
    wire [15:0] threshold = (ratio[16:12] != 0) ? 16'd0 : exp_lut[lut_idx];

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state          <= ST_IDLE;
            done           <= 1'b0;
            lfsr_en        <= 1'b0;
            cost_start     <= 1'b0;
            temperature    <= T_INIT;
            inner_count    <= 32'd0;
            total_iters    <= 32'd0;
            accepted_count <= 32'd0;
            current_cost   <= 64'd0;
            candidate_cost <= 64'd0;
            final_cost     <= 64'd0;
            final_temp     <= 32'd0;
            sel_macro      <= 32'd0;
            saved_x        <= 32'd0;
            saved_y        <= 32'd0;
            macro_w        <= 32'd0;
            macro_h        <= 32'd0;
        end else begin
            case (state)
                ST_IDLE: begin
                    done       <= 1'b0;
                    lfsr_en    <= 1'b0;
                    cost_start <= 1'b0;
                    if (start) begin
                        temperature    <= T_INIT;
                        inner_count    <= 32'd0;
                        total_iters    <= 32'd0;
                        accepted_count <= 32'd0;
                        cost_start     <= 1'b1;
                        state          <= ST_INIT_COST;
                    end
                end

                ST_INIT_COST: begin
                    cost_start <= 1'b0;
                    state      <= ST_WAIT_INIT;
                end

                ST_WAIT_INIT: begin
                    if (cost_done) begin
                        current_cost <= cost_total;
                        lfsr_en      <= 1'b1;
                        state        <= ST_PERTURB;
                    end
                end

                ST_PERTURB: begin
                    lfsr_en <= 1'b1;
                    // Select a random macro
                    sel_macro <= rand_val[15:0] % NUM_MACROS;
                    saved_x   <= layout_mem[(rand_val[15:0] % NUM_MACROS) * 4];
                    saved_y   <= layout_mem[(rand_val[15:0] % NUM_MACROS) * 4 + 1];
                    macro_w   <= layout_mem[(rand_val[15:0] % NUM_MACROS) * 4 + 2];
                    macro_h   <= layout_mem[(rand_val[15:0] % NUM_MACROS) * 4 + 3];
                    state     <= ST_APPLY_MOVE;
                end

                ST_APPLY_MOVE: begin
                    lfsr_en <= 1'b0;

                    disp_scale = (temperature >> 14);
                    if (disp_scale <= 0) disp_scale = 1;

                    raw_dx = ($signed({1'b0, rand_val[23:16]}) - 32'sd128) * disp_scale;
                    raw_dy = ($signed({1'b0, rand_val[31:24]}) - 32'sd128) * disp_scale;

                    cand_x = $signed(saved_x) + raw_dx;
                    cand_y = $signed(saved_y) + raw_dy;

                    // Soft boundary reflection
                    if (cand_x < 0) cand_x = -cand_x;
                    if (cand_x + macro_w > DIE_WIDTH) cand_x = (DIE_WIDTH >= macro_w) ? (DIE_WIDTH - macro_w - (cand_x + macro_w - DIE_WIDTH)) : 0;
                    if (cand_x < 0) cand_x = 0;
                    if (cand_x + macro_w > DIE_WIDTH) cand_x = (DIE_WIDTH >= macro_w) ? (DIE_WIDTH - macro_w) : 0;

                    if (cand_y < 0) cand_y = -cand_y;
                    if (cand_y + macro_h > DIE_HEIGHT) cand_y = (DIE_HEIGHT >= macro_h) ? (DIE_HEIGHT - macro_h - (cand_y + macro_h - DIE_HEIGHT)) : 0;
                    if (cand_y < 0) cand_y = 0;
                    if (cand_y + macro_h > DIE_HEIGHT) cand_y = (DIE_HEIGHT >= macro_h) ? (DIE_HEIGHT - macro_h) : 0;

                        // Apply trial move to layout memory
                        layout_mem[sel_macro * 4]     <= cand_x[31:0];
                        layout_mem[sel_macro * 4 + 1] <= cand_y[31:0];

                        // Trigger cost evaluation
                        cost_start <= 1'b1;
                        state      <= ST_WAIT_EVAL;
                end

                ST_WAIT_EVAL: begin
                    cost_start <= 1'b0;
                    if (cost_done) begin
                        candidate_cost <= cost_total;
                        state          <= ST_METROPOLIS;
                    end
                end

                ST_METROPOLIS: begin
                    total_iters <= total_iters + 1;
                    if (candidate_cost <= current_cost) begin
                        // Downhill move: Accept
                        current_cost   <= candidate_cost;
                        accepted_count <= accepted_count + 1;
                    end else begin
                        // Uphill move: Metropolis acceptance condition
                        if (rand_val[15:0] < threshold) begin
                            current_cost   <= candidate_cost;
                            accepted_count <= accepted_count + 1;
                        end else begin
                            // Reject: restore previous position
                            layout_mem[sel_macro * 4]     <= saved_x;
                            layout_mem[sel_macro * 4 + 1] <= saved_y;
                        end
                    end
                    state <= ST_CHECK_INNER;
                end

                ST_CHECK_INNER: begin
                    if (inner_count + 1 >= INNER_ITERS) begin
                        // Step-based temperature decay
                        inner_count <= 32'd0;
                        temperature <= temperature - (temperature >> COOL_SHIFT);
                        if ((temperature <= T_MIN) || (total_iters >= MAX_ITERS)) begin
                            state <= ST_DONE;
                        end else begin
                            lfsr_en <= 1'b1;
                            state   <= ST_PERTURB;
                        end
                    end else begin
                        inner_count <= inner_count + 1;
                        if (total_iters >= MAX_ITERS) begin
                            state <= ST_DONE;
                        end else begin
                            lfsr_en <= 1'b1;
                            state   <= ST_PERTURB;
                        end
                    end
                end

                ST_DONE: begin
                    done       <= 1'b1;
                    final_cost <= current_cost;
                    final_temp <= temperature;
                    state      <= ST_IDLE;
                end

                default: state <= ST_IDLE;
            endcase
        end
    end

endmodule
