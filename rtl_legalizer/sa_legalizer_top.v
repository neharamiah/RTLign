// ============================================================================
// RTLign — Top-Level Co-Design Legalizer (SA Optimizer + Greedy Cleanup)
// ============================================================================
// Two-pass heterogeneous placement optimization:
//   Pass 1: Simulated Annealing Optimizer (sa_engine.v)
//           Stochastically explores placement space minimizing HPWL, bounding
//           box area, and boundary violations.
//   Pass 2: Deterministic Greedy Cleanup (legalizer_fsm.v)
//           Guarantees 100% legal, zero-overlap layout via minimum-axis push.
// ============================================================================

`timescale 1ns / 1ps

module sa_legalizer_top #(
    parameter NUM_LINES        = 672,
    parameter DIE_WIDTH        = 200260,
    parameter DIE_HEIGHT       = 201600,
    parameter ENABLE_SA        = 1,
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

    // SA Metrics
    output wire [63:0] final_cost,
    output wire [31:0] final_temp,
    output wire [31:0] total_iters,
    output wire [31:0] accepted_count
);

    localparam NUM_MACROS = NUM_LINES / 4;
    localparam MEM_DEPTH  = NUM_LINES;

    // Top-level memory exposed for testbench dumping & verification
    reg [31:0] layout_mem [0:MEM_DEPTH-1] /* verilator public */;
    initial $readmemh("dummy_layout.hex", layout_mem);

    // -----------------------------------------------------------------------
    // Internal Signals
    // -----------------------------------------------------------------------
    reg         sa_start;
    wire        sa_done;
    reg  [31:0] sa_ext_addr;
    wire [31:0] sa_ext_rdata;

    reg         clean_start;
    wire        clean_done;
    reg         clean_ext_we;
    reg  [31:0] clean_ext_waddr;
    reg  [31:0] clean_ext_wdata;
    wire [31:0] clean_ext_rdata;

    // -----------------------------------------------------------------------
    // Submodule Instantiations
    // -----------------------------------------------------------------------
    sa_engine #(
        .NUM_LINES(NUM_LINES),
        .DIE_WIDTH(DIE_WIDTH),
        .DIE_HEIGHT(DIE_HEIGHT),
        .T_INIT(T_INIT),
        .T_MIN(T_MIN),
        .COOL_SHIFT(COOL_SHIFT),
        .INNER_ITERS(INNER_ITERS),
        .MAX_ITERS(MAX_ITERS),
        .W_WL(W_WL),
        .W_AREA(W_AREA),
        .W_BOUNDARY(W_BOUNDARY),
        .AREA_SCALE_SHIFT(AREA_SCALE_SHIFT),
        .LFSR_SEED(LFSR_SEED)
    ) sa_inst (
        .clk(clk),
        .rst(rst),
        .start(sa_start),
        .done(sa_done),
        .final_cost(final_cost),
        .final_temp(final_temp),
        .total_iters(total_iters),
        .accepted_count(accepted_count),
        .ext_mem_addr(sa_ext_addr),
        .ext_mem_rdata(sa_ext_rdata)
    );

    legalizer_fsm #(
        .NUM_LINES(NUM_LINES),
        .DIE_WIDTH(DIE_WIDTH),
        .DIE_HEIGHT(DIE_HEIGHT)
    ) clean_inst (
        .clk(clk),
        .rst(rst),
        .start(clean_start),
        .done(clean_done),
        .ext_we(clean_ext_we),
        .ext_waddr(clean_ext_waddr),
        .ext_wdata(clean_ext_wdata),
        .ext_rdata(clean_ext_rdata)
    );

    // -----------------------------------------------------------------------
    // Top-Level Orchestration FSM
    // -----------------------------------------------------------------------
    localparam S_IDLE            = 3'd0;
    localparam S_RUN_SA          = 3'd1;
    localparam S_COPY_TO_CLEAN   = 3'd2;
    localparam S_RUN_CLEAN       = 3'd3;
    localparam S_COPY_TO_FINAL   = 3'd4;
    localparam S_DONE            = 3'd5;

    reg [2:0]  state;
    reg [31:0] copy_idx;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state           <= S_IDLE;
            done            <= 1'b0;
            sa_start        <= 1'b0;
            sa_ext_addr     <= 32'd0;
            clean_start     <= 1'b0;
            clean_ext_we    <= 1'b0;
            clean_ext_waddr <= 32'd0;
            clean_ext_wdata <= 32'd0;
            copy_idx        <= 32'd0;
        end else begin
            case (state)
                S_IDLE: begin
                    clean_ext_we <= 1'b0;
                    if (start) begin
                        done <= 1'b0;
                        if (ENABLE_SA) begin
                            sa_start <= 1'b1;
                            state    <= S_RUN_SA;
                        end else begin
                            clean_start <= 1'b1;
                            state       <= S_RUN_CLEAN;
                        end
                    end
                end

                S_RUN_SA: begin
                    sa_start <= 1'b0;
                    if (sa_done) begin
                        copy_idx    <= 32'd0;
                        sa_ext_addr <= 32'd0;
                        state       <= S_COPY_TO_CLEAN;
                    end
                end

                S_COPY_TO_CLEAN: begin
                    // Stream SA layout into greedy legalizer memory
                    clean_ext_we    <= 1'b1;
                    clean_ext_waddr <= copy_idx;
                    clean_ext_wdata <= sa_ext_rdata;

                    if (copy_idx + 1 >= MEM_DEPTH) begin
                        sa_ext_addr <= 32'd0;
                        state       <= S_RUN_CLEAN;
                    end else begin
                        copy_idx    <= copy_idx + 1;
                        sa_ext_addr <= copy_idx + 1;
                    end
                end

                S_RUN_CLEAN: begin
                    clean_ext_we <= 1'b0;
                    clean_start  <= 1'b1; // Trigger greedy cleanup pass
                    state        <= S_COPY_TO_FINAL;
                end

                S_COPY_TO_FINAL: begin
                    clean_start <= 1'b0;
                    if (clean_done) begin
                        // Copy legalized layout to top-level layout_mem
                        copy_idx        <= 32'd0;
                        clean_ext_waddr <= 32'd0;
                        state           <= S_DONE;
                    end
                end

                S_DONE: begin
                    // Write legalized coordinates to top-level layout_mem
                    layout_mem[copy_idx] <= clean_ext_rdata;
                    if (copy_idx + 1 >= MEM_DEPTH) begin
                        done  <= 1'b1;
                        state <= S_IDLE;
                    end else begin
                        copy_idx        <= copy_idx + 1;
                        clean_ext_waddr <= copy_idx + 1;
                    end
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
