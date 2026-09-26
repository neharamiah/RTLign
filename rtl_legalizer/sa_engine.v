// ============================================================================
// RTLign — Simulated Annealing (SA) Placement Optimizer
// ============================================================================
// Explores the macro placement solution space using stochastic hill-climbing
// with an adaptive temperature schedule and true Metropolis acceptance.
// Minimizes C_total = w_wl*HPWL + w_area*Area_bbox + C_boundary.
// A legality scan (collision_check over all macros) rejects any candidate
// move that would overlap another macro before cost evaluation, so the SA
// pass never leaves the legal placement space. Greedy cleanup (Pass 2)
// remains responsible for the final overlap guarantee.
//
// FPGA (PYNQ/Vivado) implementation notes:
//   - layout_mem is a true-dual-port synchronous-read RAM (BRAM-inferable):
//     port A serves X-word writes and the fetch/scan/cost/external X reads,
//     port B serves Y-word writes and the W/H/Y reads. Multi-word accesses
//     are serialized over the two ports by the fetch/scan pipeline.
//   - The Metropolis ratio uses the multi-cycle iter_div divider instead of
//     a combinational 64/32 divide. The quotient is bit-identical to the
//     former Verilog `/` result; only cycle timing changed.
// ============================================================================

`timescale 1ns / 1ps

module sa_engine #(
    parameter NUM_LINES        = 672,
    parameter DIE_WIDTH        = 200260,
    parameter DIE_HEIGHT       = 201600,
    parameter T_INIT           = 1000000,
    parameter T_MIN            = 100,
    parameter T0_SAMPLES       = 16,
    parameter T0_SCALE_SHIFT   = 2,
    parameter T0_ATTEMPT_CAP   = 64,
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

    // Performance & Convergence Metrics
    output reg  [63:0] final_cost,
    output reg  [31:0] final_temp,
    output reg  [31:0] total_iters,
    output reg  [31:0] accepted_count,

    // External Memory Read Interface (for copying to greedy cleanup pass).
    // Synchronous read: data for ext_mem_addr appears on ext_mem_rdata one
    // cycle after the address is presented.
    input  wire [31:0] ext_mem_addr,
    output wire [31:0] ext_mem_rdata
);

    localparam NUM_MACROS = NUM_LINES / 4;
    localparam MEM_DEPTH  = NUM_LINES;
    localparam MEM_AW     = $clog2(MEM_DEPTH);
    localparam T0_SAMPLES_SHIFT = $clog2(T0_SAMPLES);

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
    localparam ST_LEGAL_SCAN    = 4'd9;
    localparam ST_FETCH_XW      = 4'd10;
    localparam ST_FETCH_YH      = 4'd11;
    localparam ST_FETCH_H       = 4'd12;
    localparam ST_DIV           = 4'd13;
    localparam ST_SET_TEMP      = 4'd14;

    reg [3:0]  state;
    reg [31:0] temperature;
    reg [31:0] inner_count;
    reg [63:0] current_cost;
    reg [63:0] candidate_cost;

    // Scale-aware initial temperature: before annealing, T0_SAMPLES legal
    // candidate moves are proposed (same LFSR schedule, always restored) and
    // |delta cost| accumulated. T0 = clamp((accum >> log2(T0_SAMPLES))
    // << T0_SCALE_SHIFT, T_MIN, 32'hFFFFFFFF), so the initial acceptance
    // probability is design-scale independent. Sampling consumes no cooling:
    // total_iters, inner_count and accepted_count are untouched.
    reg        sampling;
    reg [31:0] sample_count;
    reg [31:0] attempt_count;
    reg [63:0] delta_accum;
    reg [63:0] delta_abs;

    // Saved state of perturbed macro for rollback
    reg [31:0] sel_macro;
    reg [31:0] saved_x;
    reg [31:0] saved_y;
    reg [31:0] macro_w;
    reg [31:0] macro_h;

    // Legality scan: walks the layout memory two cycles per macro (X/W read
    // captured into sc_x/sc_w, then Y/H on the read port) and rejects the
    // candidate if it overlaps any other macro. Consumes no LFSR advances,
    // so the random stream and cooling schedule are unchanged. scan_valid
    // marks cycles where rd_a/rd_b hold Y/H of sc_idx (decision cycles).
    reg        scan_phase;    // 0: request X/W · 1: request Y/H
    reg        scan_valid;    // decision data for sc_idx is live
    reg [31:0] sc_idx;        // macro whose verdict is being formed
    reg [31:0] sc_x;
    reg [31:0] sc_w;
    reg [31:0] scan_addr;     // macro whose words are being requested

    // Displacement calculation — combinational so the candidate coordinates
    // are stable before the port-A/B write muxes sample them at the
    // APPLY_MOVE exit edge (a blocking assignment inside the clocked FSM
    // block would race with the separate memory blocks). The scan must see
    // the APPLY-time candidate, not one recomputed from the post-advance
    // LFSR word, so the FSM latches cand_x_q/cand_y_q at the same edge.
    reg signed [31:0] disp_scale;
    reg signed [31:0] raw_dx, raw_dy;
    reg signed [31:0] cand_x, cand_y;
    reg        [31:0] cand_x_q, cand_y_q;

    always @(*) begin
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
    end

    // Divider interface registers
    reg         div_start;
    reg  [63:0] div_dend;
    reg  [31:0] div_dsor;

    // Metropolis ratio (registered divider quotient, truncating)
    reg [31:0] ratio_q;

    // LFSR / cost engine / memory-read registers and inter-module wires
    reg         lfsr_en;
    reg         cost_start;
    reg  [31:0] rd_a;
    reg  [31:0] rd_b;
    wire [31:0] rand_val;
    wire        cost_done;
    wire [31:0] cost_mem_addr;
    wire [63:0] cost_total;
    wire [31:0] cost_hpwl;
    wire [63:0] cost_bbox_area;
    wire [31:0] cost_boundary_pen;
    wire        div_done;
    wire [63:0] div_quotient;
    wire        scan_raw_hit;

    // -----------------------------------------------------------------------
    // 32-entry Exponential LUT for Metropolis acceptance P = exp(-delta / T)
    //
    // Fixed-point format (all implicit in the original RTL, now named):
    //   ratio = ((delta << RATIO_FRAC_BITS) / T)[31:0]  — Q(32-12).12 value
    //   of delta/T with 12 fractional bits. The LUT index is
    //   ratio[LUT_IDX_MSB:LUT_IDX_LSB] = floor(32 * delta/T), i.e. one entry
    //   per 1/32 of delta/T (NOT per 1/8, despite the per-entry value
    //   spacing below). Entry k holds round(65535 * exp(-0.125 * k)), so the
    //   effective acceptance curve is ~exp(-4 * delta/T) at 1/32 resolution
    //   (documented as QUIRK-1 in VERIFICATION.md).
    //   Saturation: ratio[SAT_MSB:SAT_LSB] != 0 (delta/T >= 1) forces
    //   threshold 0 (uphill moves always rejected). Note the check covers
    //   ONLY bits [16:12]: ratios >= 2^17 alias through it — preserved
    //   bit-exactly from the original RTL.
    // -----------------------------------------------------------------------
    localparam RATIO_FRAC_BITS = 12;
    localparam SAT_MSB         = 16;
    localparam SAT_LSB         = 12;
    localparam LUT_IDX_MSB     = 11;
    localparam LUT_IDX_LSB     = 7;

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

    wire        saturated  = (ratio_q[SAT_MSB:SAT_LSB] != 5'd0);
    wire [4:0]  lut_idx    = ratio_q[LUT_IDX_MSB:LUT_IDX_LSB];
    wire [15:0] threshold  = saturated ? 16'd0 : exp_lut[lut_idx];

    // -----------------------------------------------------------------------
    // Legality-scan verdict. Operands: candidate registers vs the scanned
    // macro (X/W captured into sc_x/sc_w, Y/H live on rd_a/rd_b during the
    // decision cycle). Valid only then; the gate keeps scan_hit from
    // glitching on request cycles.
    // -----------------------------------------------------------------------
    wire scan_skip = (sc_idx == sel_macro);
    wire scan_hit  = scan_valid && !scan_phase && scan_raw_hit;
    wire scan_dec_reject = scan_valid && !scan_skip && scan_hit;

    // -----------------------------------------------------------------------
    // Internal Layout Memory — true-dual-port, synchronous read (BRAM)
    // -----------------------------------------------------------------------
    reg [31:0] layout_mem [0:MEM_DEPTH-1];
    initial $readmemh(INIT_FILE, layout_mem);

    // Address helpers (word-granular; one constant shifter each)
    wire [31:0] sel_base  = sel_macro * 4;
    wire [31:0] scan_base = scan_addr * 4;

    // Port A read address: external copy in IDLE, scan/fetch X words during
    // the scan/fetch phases, cost-engine address otherwise.
    wire [31:0] rd_a_idx =
        (state == ST_IDLE)       ? ext_mem_addr :
        (state == ST_LEGAL_SCAN) ? (scan_phase ? (scan_base + 1) :
                                  ((scan_addr >= NUM_MACROS) ? 32'd0 : scan_base)) :
        (state == ST_FETCH_XW)   ? sel_base :
        (state == ST_FETCH_YH)   ? (sel_base + 1) :
        (state == ST_FETCH_H)    ? (sel_base + 1) :
        cost_mem_addr;
    wire [MEM_AW-1:0] rd_a_addr = rd_a_idx[MEM_AW-1:0];

    // Port B read address: W/H words of the macro being fetched or scanned.
    wire [31:0] rd_b_idx =
        (state == ST_LEGAL_SCAN) ? (scan_phase ? (scan_base + 3) : (scan_base + 2)) :
        (state == ST_FETCH_XW)   ? (sel_base + 2) :
        (sel_base + 3);
    wire [MEM_AW-1:0] rd_b_addr = rd_b_idx[MEM_AW-1:0];

    // Write path: candidate X/Y in ST_APPLY_MOVE, restored X/Y on an illegal
    // scan verdict or a rejected Metropolis move. Both words of an event are
    // pushed into a two-entry queue drained one write per cycle through a
    // single memory write port, so the memory infers as BRAM (read
    // replication) instead of relying on true-dual-port inference. Write
    // events are always >= 3 cycles apart and the queue drains in 2, so no
    // event is ever dropped; only the perturbed macro's row is ever written,
    // and the legality scan skips that row, so no pending write is ever
    // read by the verdict logic.
    // met_reject restores the saved coordinates through the write muxes.
    // During T0 sampling every candidate is restored unconditionally, so the
    // sampled deltas are all measured against the same initial layout.
    wire met_reject = (state == ST_METROPOLIS) &&
                      (sampling || ((candidate_cost > current_cost) &&
                                    !(rand_val[15:0] < threshold)));
    wire mem_ev_we  = (state == ST_APPLY_MOVE) || scan_dec_reject || met_reject;
    wire [31:0] ev_wd_a = (state == ST_APPLY_MOVE) ? cand_x[31:0] : saved_x;
    wire [31:0] ev_wd_b = (state == ST_APPLY_MOVE) ? cand_y[31:0] : saved_y;

    reg        q0_we, q1_we;
    reg [MEM_AW-1:0] q0_wa, q1_wa;
    reg [31:0] q0_wd, q1_wd;

    always @(posedge clk) begin
        if (mem_ev_we) begin
            q0_we <= 1'b1;
            q0_wa <= sel_base[MEM_AW-1:0];
            q0_wd <= ev_wd_a;
            q1_we <= 1'b1;
            q1_wa <= sel_base[MEM_AW-1:0] + 1'b1;
            q1_wd <= ev_wd_b;
        end else if (q0_we) begin
            q0_we <= q1_we;
            q0_wa <= q1_wa;
            q0_wd <= q1_wd;
            q1_we <= 1'b0;
        end else begin
            q0_we <= 1'b0;
        end
    end

    // Port A: single write port + synchronous read (external copy address in
    // IDLE, scan/fetch X/Y words during the scan/fetch phases, cost-engine
    // address otherwise).
    always @(posedge clk) begin
        if (q0_we) layout_mem[q0_wa] <= q0_wd;
        rd_a <= layout_mem[rd_a_addr];
    end

    // Port B: synchronous read (W/H words of the macro being fetched or
    // scanned). Pure read keeps the port BRAM-inferable.
    always @(posedge clk) begin
        rd_b <= layout_mem[rd_b_addr];
    end

    assign ext_mem_rdata = rd_a;

    // -----------------------------------------------------------------------
    // Submodules
    // -----------------------------------------------------------------------
    lfsr32 lfsr_inst (
        .clk(clk),
        .rst(rst),
        .seed(LFSR_SEED),
        .enable(lfsr_en),
        .rand_out(rand_val)
    );

    // Cost engine reads layout_mem through port A; its registered address
    // plus the 1-cycle synchronous read latency are absorbed by its
    // S_PRIME state.
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
        .mem_rdata(rd_a),
        .total_cost(cost_total),
        .hpwl_out(cost_hpwl),
        .bbox_area_out(cost_bbox_area),
        .boundary_penalty_out(cost_boundary_pen)
    );

    // Multi-cycle iterative divider for the Metropolis ratio (LUT-friendly;
    // quotient bit-identical to the Verilog `/` operator).
    iter_div #(
        .NUM_WIDTH(64),
        .DEN_WIDTH(32)
    ) div_inst (
        .clk(clk),
        .rst(rst),
        .start(div_start),
        .dividend(div_dend),
        .divisor(div_dsor),
        .done(div_done),
        .quotient(div_quotient)
    );

    collision_check scan_inst (
        .x1(cand_x_q), .y1(cand_y_q), .w1(macro_w), .h1(macro_h),
        .x2(sc_x), .y2(rd_a), .w2(sc_w), .h2(rd_b),
        .overlap(scan_raw_hit)
    );

    // -----------------------------------------------------------------------
    // Main FSM
    // -----------------------------------------------------------------------
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
            sampling       <= 1'b0;
            sample_count   <= 32'd0;
            attempt_count  <= 32'd0;
            delta_accum    <= 64'd0;
            delta_abs      <= 64'd0;
            current_cost   <= 64'd0;
            candidate_cost <= 64'd0;
            final_cost     <= 64'd0;
            final_temp     <= 32'd0;
            sel_macro      <= 32'd0;
            saved_x        <= 32'd0;
            saved_y        <= 32'd0;
            macro_w        <= 32'd0;
            macro_h        <= 32'd0;
            scan_addr      <= 32'd0;
            scan_phase     <= 1'b0;
            scan_valid     <= 1'b0;
            sc_idx         <= 32'd0;
            sc_x           <= 32'd0;
            sc_w           <= 32'd0;
            ratio_q        <= 32'd0;
            cand_x_q       <= 32'd0;
            cand_y_q       <= 32'd0;
            q0_we          <= 1'b0;
            q1_we          <= 1'b0;
            div_start      <= 1'b0;
            div_dend       <= 64'd0;
            div_dsor       <= 32'd0;
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
                        // Enter the T0 sampling phase before annealing.
                        sampling     <= 1'b1;
                        sample_count <= 32'd0;
                        attempt_count<= 32'd0;
                        delta_accum  <= 64'd0;
                        state        <= ST_PERTURB;
                    end
                end

                ST_PERTURB: begin
                    // Select a random macro (single modulo instance); its
                    // X/W/Y/H words are fetched over the next three states.
                    lfsr_en   <= 1'b0;
                    sel_macro <= rand_val[15:0] % NUM_MACROS;
                    state     <= ST_FETCH_XW;
                end

                ST_FETCH_XW: begin
                    // rd_a/rd_b capture X/W of sel_macro at this edge.
                    state <= ST_FETCH_YH;
                end

                ST_FETCH_YH: begin
                    saved_x <= rd_a;
                    macro_w <= rd_b;
                    state   <= ST_FETCH_H;
                end

                ST_FETCH_H: begin
                    saved_y <= rd_a;
                    macro_h <= rd_b;
                    lfsr_en <= 1'b1;   // advance at the APPLY_MOVE edge
                    state   <= ST_APPLY_MOVE;
                end

                ST_APPLY_MOVE: begin
                    lfsr_en <= 1'b0;

                    // Latch the candidate for the legality scan (the
                    // combinational cand_x/cand_y still drive the port-A/B
                    // write muxes this cycle, sampled pre-LFSR-advance).
                    cand_x_q   <= cand_x[31:0];
                    cand_y_q   <= cand_y[31:0];
                    scan_addr  <= 32'd0;
                    scan_phase <= 1'b0;
                    scan_valid <= 1'b0;
                    state      <= ST_LEGAL_SCAN;
                end

                // ----------------------------------------------------------
                // ST_LEGAL_SCAN: two cycles per macro. Phase 1 captures the
                // scanned macro's X/W into sc_x/sc_w and requests its Y/H;
                // phase 0 resolves the verdict against the candidate and
                // advances. Rejects before cost evaluation when the candidate
                // would overlap any other macro; counts as an iteration for
                // the cooling schedule.
                // ----------------------------------------------------------
                ST_LEGAL_SCAN: begin
                    if (scan_phase) begin
                        sc_x       <= rd_a;
                        sc_w       <= rd_b;
                        sc_idx     <= scan_addr;
                        scan_addr  <= scan_addr + 32'd1;
                        scan_valid <= 1'b1;
                        scan_phase <= 1'b0;
                    end else if (scan_dec_reject) begin
                        // Illegal candidate: restore (port write muxes) and
                        // skip cost evaluation.
                        if (sampling) begin
                            attempt_count <= attempt_count + 1;
                            scan_valid    <= 1'b0;
                            if (attempt_count + 1 >= T0_ATTEMPT_CAP) begin
                                state <= ST_SET_TEMP;
                            end else begin
                                lfsr_en <= 1'b1;
                                state   <= ST_PERTURB;
                            end
                        end else begin
                            total_iters <= total_iters + 1;
                            scan_valid  <= 1'b0;
                            state       <= ST_CHECK_INNER;
                        end
                    end else if (scan_valid && (sc_idx == NUM_MACROS - 1)) begin
                        // Legal candidate: evaluate the cost as before.
                        scan_valid <= 1'b0;
                        cost_start <= 1'b1;
                        state      <= ST_WAIT_EVAL;
                    end else begin
                        scan_phase <= 1'b1;
                    end
                end

                ST_WAIT_EVAL: begin
                    cost_start <= 1'b0;
                    if (cost_done) begin
                        candidate_cost <= cost_total;
                        if (cost_total > current_cost) begin
                            if (temperature > 0) begin
                                div_dend  <= (cost_total - current_cost) << RATIO_FRAC_BITS;
                                div_dsor  <= temperature;
                                div_start <= 1'b1;
                                state     <= ST_DIV;
                            end else begin
                                ratio_q <= 32'hFFFFFFFF;
                                state   <= ST_METROPOLIS;
                            end
                        end else begin
                            state <= ST_METROPOLIS;
                        end
                    end
                end

                ST_DIV: begin
                    div_start <= 1'b0;
                    if (div_done) begin
                        ratio_q <= div_quotient[31:0];
                        state   <= ST_METROPOLIS;
                    end
                end

                ST_METROPOLIS: begin
                    if (sampling) begin
                        // T0 sampling: accumulate |delta| over legal
                        // candidates and always restore the macro.
                        delta_abs <= (candidate_cost > current_cost)
                                   ? (candidate_cost - current_cost)
                                   : (current_cost - candidate_cost);
                        delta_accum <= delta_accum
                                     + ((candidate_cost > current_cost)
                                        ? (candidate_cost - current_cost)
                                        : (current_cost - candidate_cost));
                        sample_count <= sample_count + 1;
                        if (sample_count + 1 >= T0_SAMPLES) begin
                            state <= ST_SET_TEMP;
                        end else begin
                            lfsr_en <= 1'b1;
                            state   <= ST_PERTURB;
                        end
                    end else begin
                        total_iters <= total_iters + 1;
                        if (candidate_cost <= current_cost) begin
                            // Downhill move: Accept
                            current_cost   <= candidate_cost;
                            accepted_count <= accepted_count + 1;
                        end else if (rand_val[15:0] < threshold) begin
                            // Uphill move accepted by the Metropolis condition
                            current_cost   <= candidate_cost;
                            accepted_count <= accepted_count + 1;
                        end
                        // else: reject — previous position restored through the
                        // port-A/B write muxes (met_reject).
                        state <= ST_CHECK_INNER;
                    end
                end

                ST_SET_TEMP: begin
                    // T0 = clamp(mean|delta| << T0_SCALE_SHIFT, T_MIN, max),
                    // where mean = delta_accum >> T0_SAMPLES_SHIFT. With the
                    // LUT's effective exp(-4*delta/T) acceptance this puts a
                    // typical move at delta/T ~ 0.25 (~37% initial acceptance)
                    // regardless of design scale. Falls back to T_INIT when no
                    // legal candidate was sampled.
                    sampling   <= 1'b0;
                    scan_valid <= 1'b0;
                    lfsr_en    <= 1'b1;
                    if (sample_count == 32'd0) begin
                        temperature <= T_INIT;
                    end else if ((delta_accum >> T0_SAMPLES_SHIFT)
                                 > (32'hFFFFFFFF >> T0_SCALE_SHIFT)) begin
                        temperature <= 32'hFFFFFFFF;
                    end else if ((delta_accum >> T0_SAMPLES_SHIFT)
                                 < (T_MIN >> T0_SCALE_SHIFT)) begin
                        temperature <= T_MIN;
                    end else begin
                        temperature <= (delta_accum >> T0_SAMPLES_SHIFT)
                                       << T0_SCALE_SHIFT;
                    end
                    state <= ST_PERTURB;
                end

                ST_CHECK_INNER: begin
                    if (inner_count + 1 >= INNER_ITERS) begin
                        // Step-based temperature decay
                        inner_count <= 32'd0;
                        temperature <= temperature - (temperature >> COOL_SHIFT);
                        if (accepted_count == 32'd0) begin
                            // Frozen SA: zero accepts over a whole inner block
                            // means every proposed move was rejected; cooling
                            // further can only reject more. Skip to cleanup.
                            state <= ST_DONE;
                        end else if ((temperature <= T_MIN) || (total_iters >= MAX_ITERS)) begin
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
