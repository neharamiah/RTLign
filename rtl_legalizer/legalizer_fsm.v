// ============================================================================
// RTLign — Legalizer FSM (Phase 1: Greedy Sweep with 2D Resolution)
// ============================================================================
// This module reads an array of macro placements from a .hex memory file,
// iterates over all unique pairs, detects AABB overlaps via the collision_check
// module, and resolves them by pushing the later macro along the axis of
// minimum overlap. Die-boundary clamping prevents macros from leaving the chip.
//
// FPGA (PYNQ/Vivado) implementation notes: layout_mem is a true-dual-port
// synchronous-read RAM (BRAM-inferable). Port A serves the external word
// interface (write + registered read). Port B serves the FSM: FETCH streams
// both macros' words over five phases (X→Y→W→H per port), and RESOLVE writes
// one word per attempt. The word-granular external protocol is unchanged;
// ext_rdata gained one cycle of read latency.
// ============================================================================

module legalizer_fsm #(
    // Number of 32-bit LINES in the .hex file (each macro = 4 lines: X,Y,W,H)
    parameter NUM_LINES   = 672,
    // Die boundary (from the DEF DIEAREA statement, in DEF database units)
    parameter DIE_WIDTH   = 200260,
    parameter DIE_HEIGHT  = 201600,
    parameter INIT_FILE   = "dummy_layout.hex"
)(
    input  wire clk,
    input  wire rst,
    input  wire start,
    output reg  done,

    // External Memory Interface (ext_rdata is a registered synchronous read)
    input  wire        ext_we,
    input  wire [31:0] ext_waddr,
    input  wire [31:0] ext_wdata,
    output wire [31:0] ext_rdata
);

    // -----------------------------------------------------------------------
    // Derived constants
    // -----------------------------------------------------------------------
    localparam NUM_MACROS  = NUM_LINES / 4;
    localparam MEM_DEPTH   = NUM_LINES;       // one 32-bit word per line
    localparam PTR_WIDTH   = $clog2(MEM_DEPTH + 1);  // pointer bit-width
    localparam MEM_AW      = $clog2(MEM_DEPTH);

    // -----------------------------------------------------------------------
    // Pointers (index into layout_mem; each macro starts at ptr * 4 implicitly
    // but we store the raw line index: macro i starts at i*4)
    // -----------------------------------------------------------------------
    reg [PTR_WIDTH-1:0] ptr_a;   // outer loop — base address of macro A
    reg [PTR_WIDTH-1:0] ptr_b;   // inner loop — base address of macro B

    // -----------------------------------------------------------------------
    // Registers fed to / read from the collision checker
    // -----------------------------------------------------------------------
    reg [31:0] x1, y1, w1, h1;
    reg [31:0] x2, y2, w2, h2;

    reg        resolved_any;
    reg [3:0]  pass_count;

    // Per-pair resolve attempt counter. Caps the RESOLVE->CHECK retry loop so
    // an unresolvable pair (e.g. two die-wide macros that cannot separate on
    // any axis) can never hang the FSM. Normal pairs resolve in 1-2 tries.
    localparam MAX_RESOLVE_TRIES = 16;
    reg [5:0]  resolve_tries;

    // FETCH phase counter: phases 0-3 request words 0-3 of both macros,
    // phases 1-4 capture the word requested by the previous phase.
    reg [2:0]  fetch_phase;

    // Port-B write channel (driven by the FSM case below)
    reg        fsm_we_b;
    reg [MEM_AW-1:0] fsm_wa_b;
    reg [31:0] fsm_wd_b;

    // Memory read registers (synchronous reads; intentionally not reset —
    // their contents are don't-care until first used)
    reg [31:0] rd_a;
    reg [31:0] rd_b;

    // -----------------------------------------------------------------------
    // Collision checker instantiation
    // -----------------------------------------------------------------------
    wire is_overlapping;
    collision_check col_inst (
        .x1(x1), .y1(y1), .w1(w1), .h1(h1),
        .x2(x2), .y2(y2), .w2(w2), .h2(h2),
        .overlap(is_overlapping)
    );

    // -----------------------------------------------------------------------
    // Overlap geometry — used to decide push direction
    // -----------------------------------------------------------------------
    wire [31:0] right1 = x1 + w1;
    wire [31:0] top1   = y1 + h1;
    wire [31:0] right2 = x2 + w2;
    wire [31:0] top2   = y2 + h2;

    // Overlap extents on each axis
    wire [31:0] overlap_x = (right1 < right2 ? right1 : right2) -
                            (x1 > x2 ? x1 : x2);
    wire [31:0] overlap_y = (top1 < top2 ? top1 : top2) -
                            (y1 > y2 ? y1 : y2);

    // -----------------------------------------------------------------------
    // FSM States
    // -----------------------------------------------------------------------
    localparam IDLE    = 3'd0;
    localparam FETCH   = 3'd1;
    localparam CHECK   = 3'd2;
    localparam RESOLVE = 3'd3;
    localparam ADVANCE = 3'd4;
    localparam FINISH  = 3'd5;

    reg [2:0] current_state, next_state;

    // -----------------------------------------------------------------------
    // Last valid base address (macro index * 4)
    // -----------------------------------------------------------------------
    wire [PTR_WIDTH-1:0] last_base = (NUM_MACROS - 1) * 4;

    // -----------------------------------------------------------------------
    // Memory — true-dual-port, synchronous read (BRAM)
    // -----------------------------------------------------------------------
    reg [31:0] layout_mem [0:MEM_DEPTH-1];
    initial $readmemh(INIT_FILE, layout_mem);

    // FETCH word offset: phase p requests word p (0-3); phase 4 re-requests
    // word 0 (harmless, unused).
    wire [2:0]  fetch_off = (fetch_phase < 3'd4) ? fetch_phase : 3'd0;
    wire [PTR_WIDTH-1:0] fa_idx = ptr_a + fetch_off;
    wire [PTR_WIDTH-1:0] fb_idx = ptr_b + fetch_off;

    // Port A read address: external read address while the FSM is idle,
    // macro A's fetch stream otherwise.
    wire [MEM_AW-1:0] ext_rd_idx = (ext_waddr < MEM_DEPTH) ? ext_waddr[MEM_AW-1:0] :
                                                   {MEM_AW{1'b0}};
    wire [MEM_AW-1:0] rd_a_addr = (current_state == IDLE) ? ext_rd_idx :
                                                            fa_idx[MEM_AW-1:0];
    wire [MEM_AW-1:0] rd_b_addr = fb_idx[MEM_AW-1:0];

    // Single memory write port. The external interface and the FSM's RESOLVE
    // writes never coincide: the top-level FSM drives ext writes only before
    // asserting start (and after done), while fsm_we_b pulses only during the
    // sweep. Merging keeps the memory single-write-port (BRAM-inferable as a
    // replicated simple-dual-port RAM; a separate 2-write-port structure
    // would rely on true-dual-port inference).
    wire ext_we_v = ext_we && (ext_waddr < MEM_DEPTH);
    wire        mem_we = ext_we_v || fsm_we_b;
    wire [MEM_AW-1:0] mem_wa = ext_we_v ? ext_waddr[MEM_AW-1:0] : fsm_wa_b;
    wire [31:0] mem_wd = ext_we_v ? ext_wdata : fsm_wd_b;

    // Port A: synchronous read (external copy address while idle, macro A's
    // fetch stream otherwise).
    always @(posedge clk) begin
        if (mem_we) begin
            layout_mem[mem_wa] <= mem_wd;
        end
        rd_a <= layout_mem[rd_a_addr];
    end

    // Port B: synchronous read (macro B's fetch stream). Pure read keeps the
    // port BRAM-inferable; the FETCH captures zero the words whenever ptr_b
    // addresses past the memory — only possible when NUM_MACROS == 1, where
    // the nonexistent second macro must read as a zero-size box so the sweep
    // terminates without touching memory.
    always @(posedge clk) begin
        rd_b <= layout_mem[rd_b_addr];
    end

    assign ext_rdata = rd_a;

    // -----------------------------------------------------------------------
    // SEQUENTIAL LOGIC — Datapath & State Memory
    // -----------------------------------------------------------------------
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            current_state <= IDLE;
            ptr_a         <= 0;
            ptr_b         <= 4;     // second macro
            done          <= 0;
            resolved_any  <= 1'b0;
            pass_count    <= 4'd0;
            resolve_tries <= 6'd0;
            fetch_phase   <= 3'd0;
            fsm_we_b      <= 1'b0;
            fsm_wa_b      <= {MEM_AW{1'b0}};
            fsm_wd_b      <= 32'd0;
            x1 <= 0; y1 <= 0; w1 <= 0; h1 <= 0;
            x2 <= 0; y2 <= 0; w2 <= 0; h2 <= 0;
        end else begin
            fsm_we_b     <= 1'b0;   // default: no RESOLVE write this cycle
            current_state <= next_state;

            case (current_state)
                IDLE: begin
                    done <= 1'b0;
                    if (start) begin
                        ptr_a        <= 0;
                        ptr_b        <= 4;
                        fetch_phase  <= 3'd0;
                        resolved_any <= 1'b0;
                        pass_count   <= 4'd0;
                    end
                end

                // ----------------------------------------------------------
                // FETCH: stream both macros' words through the two read
                // ports over five phases (request X/W/Y/H, capture one
                // phase behind the request).
                // ----------------------------------------------------------
                FETCH: begin
                    if (fetch_phase == 3'd1) begin
                        x1 <= rd_a;             // word 0 (X), requested in phase 0
                        x2 <= (fb_idx < MEM_DEPTH) ? rd_b : 32'd0;
                    end else if (fetch_phase == 3'd2) begin
                        y1 <= rd_a;             // word 1 (Y)
                        y2 <= (fb_idx < MEM_DEPTH) ? rd_b : 32'd0;
                    end else if (fetch_phase == 3'd3) begin
                        w1 <= rd_a;             // word 2 (W)
                        w2 <= (fb_idx < MEM_DEPTH) ? rd_b : 32'd0;
                    end else if (fetch_phase == 3'd4) begin
                        h1 <= rd_a;             // word 3 (H)
                        h2 <= (fb_idx < MEM_DEPTH) ? rd_b : 32'd0;
                        resolve_tries <= 6'd0;
                    end
                    if (fetch_phase != 3'd4) begin
                        fetch_phase <= fetch_phase + 3'd1;
                    end
                end

                // ----------------------------------------------------------
                // RESOLVE: Push macro B along the axis of MINIMUM overlap.
                //          This produces the smallest displacement needed to
                //          eliminate the collision. Then clamp to die boundary.
                //          The moved word reaches layout_mem through port B.
                // ----------------------------------------------------------
                RESOLVE: begin
                    resolved_any  <= 1'b1;
                    resolve_tries <= resolve_tries + 6'd1;
                    fsm_we_b      <= 1'b1;
                    if ((pass_count[0] == 1'b0) ?
                        ((overlap_x < overlap_y) || ((overlap_x == overlap_y) && (ptr_b[2] == 1'b0))) :
                        ((overlap_y < overlap_x) || ((overlap_x == overlap_y) && (ptr_b[2] == 1'b1)))) begin
                        // --- Push horizontally ---
                        fsm_wa_b <= ptr_b[MEM_AW-1:0];
                        if (x2 >= x1) begin
                            // B is to the right of A → push B rightward
                            fsm_wd_b <= right1;
                            x2       <= right1;
                            // Clamp: if pushed past die edge, wrap to left of A
                            if (right1 + w2 > DIE_WIDTH) begin
                                fsm_wd_b <= (x1 >= w2) ? (x1 - w2) : 0;
                                x2       <= (x1 >= w2) ? (x1 - w2) : 0;
                            end
                        end else begin
                            // B is to the left of A → push B leftward
                            if (x1 >= w2) begin
                                fsm_wd_b <= x1 - w2;
                                x2       <= x1 - w2;
                            end else begin
                                fsm_wd_b <= 0;
                                x2       <= 0;
                            end
                        end
                    end else begin
                        // --- Push vertically ---
                        fsm_wa_b <= ptr_b + 1;
                        if (y2 >= y1) begin
                            // B is above A → push B upward
                            fsm_wd_b <= top1;
                            y2       <= top1;
                            // Clamp
                            if (top1 + h2 > DIE_HEIGHT) begin
                                fsm_wd_b <= (y1 >= h2) ? (y1 - h2) : 0;
                                y2       <= (y1 >= h2) ? (y1 - h2) : 0;
                            end
                        end else begin
                            // B is below A → push B downward
                            if (y1 >= h2) begin
                                fsm_wd_b <= y1 - h2;
                                y2       <= y1 - h2;
                            end else begin
                                fsm_wd_b <= 0;
                                y2       <= 0;
                            end
                        end
                    end
                end

                // ----------------------------------------------------------
                // ADVANCE: Move to the next pair (ptr_a, ptr_b)
                // ----------------------------------------------------------
                ADVANCE: begin
                    fetch_phase <= 3'd0;   // re-arm the fetch pipeline
                    if (ptr_b < last_base) begin
                        // More inner-loop pairs for this ptr_a
                        ptr_b <= ptr_b + 4;
                    end else if ((ptr_a + 4) < last_base) begin
                        // Inner loop exhausted → advance outer, reset inner.
                        // Written as (ptr_a + 4) < last_base instead of
                        // ptr_a < last_base - 4: the subtraction wraps in a
                        // 32-bit context when NUM_MACROS == 1 and hung the
                        // FSM. Identical semantics for NUM_MACROS >= 2.
                        ptr_a <= ptr_a + 4;
                        ptr_b <= ptr_a + 8;   // next macro after new ptr_a
                    end else begin
                        // Sweep exhausted: if any overlap resolved, repeat pass up to 8 times
                        if (resolved_any && (pass_count < 8)) begin
                            ptr_a        <= 0;
                            ptr_b        <= 4;
                            resolved_any <= 1'b0;
                            pass_count   <= pass_count + 1;
                        end
                    end
                end

                // ----------------------------------------------------------
                // FINISH: Signal completion
                // ----------------------------------------------------------
                FINISH: begin
                    done <= 1;
                end

                default: ; // IDLE, CHECK — no datapath action
            endcase
        end
    end

    // -----------------------------------------------------------------------
    // COMBINATIONAL LOGIC — Next-State Routing
    // -----------------------------------------------------------------------
    always @(*) begin
        next_state = current_state;
        case (current_state)
            IDLE:    if (start)          next_state = FETCH;
            FETCH:                       next_state = (fetch_phase == 3'd4) ? CHECK : FETCH;
            CHECK:   if (is_overlapping && (resolve_tries < MAX_RESOLVE_TRIES))
                                     next_state = RESOLVE;
                     else                next_state = ADVANCE;
            RESOLVE:                     next_state = CHECK;  // re-check after push
            ADVANCE: begin
                if (ptr_b < last_base || (ptr_a + 4) < last_base)
                    next_state = FETCH;
                else if (resolved_any && (pass_count < 8))
                    next_state = FETCH;
                else
                    next_state = FINISH;        // all pairs exhausted with zero overlaps
            end
            FINISH:                      next_state = IDLE;
            default:                     next_state = IDLE;
        endcase
    end

endmodule
