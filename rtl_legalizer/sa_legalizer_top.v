// ============================================================================
// RTLign — Top-Level Co-Design Legalizer (SA Optimizer + Greedy Cleanup)
// ============================================================================
// Two-pass heterogeneous placement optimization:
//   Pass 1: Simulated Annealing Optimizer (sa_engine.v)
//           Stochastically explores placement space minimizing HPWL, bounding
//           box area, and boundary violations.
//   Pass 2: Deterministic Greedy Cleanup (legalizer_fsm.v)
//           Guarantees 100% legal, zero-overlap layout via minimum-axis push.
//
// FPGA (PYNQ/Vivado) implementation notes:
//   - rst is synchronized (2-FF, async assert / sync release) before reaching
//     the FSMs and submodules.
//   - The legalized result stays readable on hardware through the registered
//     out_addr/out_data read port (also keeps layout_mem from being pruned).
//   - The SA->cleanup and cleanup->output copy loops absorb the one-cycle
//     synchronous-read latency of the BRAM memories with a skewed
//     address-issue / data-capture schedule.
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
    parameter LFSR_SEED        = 32'hDEAD_BEEF,
    parameter INIT_FILE        = "dummy_layout.hex"
)(
    input  wire        clk,
    input  wire        rst,
    input  wire        start,
    output reg         done,

    // Hardware read-back port for the legalized layout: registered
    // synchronous read, data for out_addr appears one cycle later.
    // Addresses past the memory alias to row 0 (keeps the read port pure
    // and BRAM-inferable).
    input  wire [9:0]  out_addr,
    output reg  [31:0] out_data,

    // SA Metrics
    output wire [63:0] final_cost,
    output wire [31:0] final_temp,
    output wire [31:0] total_iters,
    output wire [31:0] accepted_count
);

    localparam NUM_MACROS = NUM_LINES / 4;
    localparam MEM_DEPTH  = NUM_LINES;

    // -----------------------------------------------------------------------
    // Reset synchronizer: assert asynchronously, release synchronously so
    // recovery/removal timing on the reset pins is never violated.
    // -----------------------------------------------------------------------
    reg [1:0] rst_sync;
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            rst_sync <= 2'b11;
        end else begin
            rst_sync <= {1'b0, rst_sync[1]};
        end
    end
    wire rst_int = rst_sync[0];

    // -----------------------------------------------------------------------
    // Top-level memory exposed for testbench dumping & verification.
    // Write port: final copy FSM. Read port: out_addr/out_data below.
    // -----------------------------------------------------------------------
    reg [31:0] layout_mem [0:MEM_DEPTH-1] /* verilator public */;
    initial $readmemh(INIT_FILE, layout_mem);

    always @(posedge clk) begin
        if (final_we) begin
            layout_mem[final_wa] <= final_wd;
        end
        out_data <= layout_mem[out_addr < MEM_DEPTH ? out_addr : 10'd0];
    end

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
        .LFSR_SEED(LFSR_SEED),
        .INIT_FILE(INIT_FILE)
    ) sa_inst (
        .clk(clk),
        .rst(rst_int),
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
        .DIE_HEIGHT(DIE_HEIGHT),
        .INIT_FILE(INIT_FILE)
    ) clean_inst (
        .clk(clk),
        .rst(rst_int),
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
    localparam S_DONE2           = 3'd6;

    reg [2:0]  state;
    reg [31:0] copy_idx;

    // Registered memory write channel. The write lives in its own reset-free
    // always block (below) so the memory infers as BRAM; writes inside the
    // async-reset FSM block would defeat inference.
    reg        final_we;
    reg [9:0]  final_wa;
    reg [31:0] final_wd;

    always @(posedge clk or posedge rst_int) begin
        if (rst_int) begin
            state           <= S_IDLE;
            done            <= 1'b0;
            sa_start        <= 1'b0;
            sa_ext_addr     <= 32'd0;
            clean_start     <= 1'b0;
            clean_ext_we    <= 1'b0;
            clean_ext_waddr <= 32'd0;
            clean_ext_wdata <= 32'd0;
            copy_idx        <= 32'd0;
            final_we        <= 1'b0;
            final_wa        <= 10'd0;
            final_wd        <= 32'd0;
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

                // Stream the SA layout into the greedy legalizer. The SA
                // engine's read port is synchronous: the address issued in
                // one cycle yields data on sa_ext_rdata two edges later, so
                // the write for word copy_idx-1 rides the same cycle that
                // issues the address for word copy_idx.
                S_COPY_TO_CLEAN: begin
                    if (copy_idx != 32'd0) begin
                        clean_ext_we    <= 1'b1;
                        clean_ext_waddr <= copy_idx - 32'd1;
                        clean_ext_wdata <= sa_ext_rdata;
                    end
                    if (copy_idx == MEM_DEPTH) begin
                        sa_ext_addr <= 32'd0;
                        state       <= S_RUN_CLEAN;
                    end else begin
                        copy_idx    <= copy_idx + 32'd1;
                        sa_ext_addr <= copy_idx + 32'd1;
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

                // Read the legalized layout back word by word. The
                // legalizer's read port is synchronous: clean_ext_rdata
                // carries word copy_idx-1 while clean_ext_waddr presents
                // the address for word copy_idx. The write itself goes
                // through the registered final_* channel so the memory
                // stays BRAM-inferable; S_DONE2 lets the last write land
                // before asserting done.
                S_DONE: begin
                    if (copy_idx != 32'd0) begin
                        final_we <= 1'b1;
                        final_wa <= copy_idx[9:0] - 10'd1;
                        final_wd <= clean_ext_rdata;
                    end else begin
                        final_we <= 1'b0;
                    end
                    if (copy_idx == MEM_DEPTH) begin
                        state <= S_DONE2;
                    end else begin
                        copy_idx        <= copy_idx + 32'd1;
                        clean_ext_waddr <= copy_idx + 32'd1;
                    end
                end

                S_DONE2: begin
                    done  <= 1'b1;
                    state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
