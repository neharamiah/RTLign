// ============================================================================
// RTLign — Legalizer FSM (Phase 1: Greedy Sweep with 2D Resolution)
// ============================================================================
// This module reads an array of macro placements from a .hex memory file,
// iterates over all unique pairs, detects AABB overlaps via the collision_check
// module, and resolves them by pushing the later macro along the axis of
// minimum overlap. Die-boundary clamping prevents macros from leaving the chip.
// ============================================================================

module legalizer_fsm #(
    // Number of 32-bit LINES in the .hex file (each macro = 4 lines: X,Y,W,H)
    parameter NUM_LINES   = 672,
    // Die boundary (from the DEF DIEAREA statement, in DEF database units)
    parameter DIE_WIDTH   = 200260,
    parameter DIE_HEIGHT  = 201600
)(
    input  wire clk,
    input  wire rst,
    input  wire start,
    output reg  done
);

    // -----------------------------------------------------------------------
    // Derived constants
    // -----------------------------------------------------------------------
    localparam NUM_MACROS  = NUM_LINES / 4;
    localparam MEM_DEPTH   = NUM_LINES;       // one 32-bit word per line
    localparam PTR_WIDTH   = $clog2(MEM_DEPTH + 1);  // pointer bit-width

    // -----------------------------------------------------------------------
    // Layout Memory — loaded from the .hex file at elaboration time
    // -----------------------------------------------------------------------
    reg [31:0] layout_mem [0:MEM_DEPTH-1];
    initial $readmemh("dummy_layout.hex", layout_mem);

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
    // SEQUENTIAL LOGIC — Datapath & State Memory
    // -----------------------------------------------------------------------
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            current_state <= IDLE;
            ptr_a         <= 0;
            ptr_b         <= 4;     // second macro
            done          <= 0;
            x1 <= 0; y1 <= 0; w1 <= 0; h1 <= 0;
            x2 <= 0; y2 <= 0; w2 <= 0; h2 <= 0;
        end else begin
            current_state <= next_state;

            case (current_state)
                // ----------------------------------------------------------
                // FETCH: Load both macros from memory into registers
                // ----------------------------------------------------------
                FETCH: begin
                    x1 <= layout_mem[ptr_a];
                    y1 <= layout_mem[ptr_a + 1];
                    w1 <= layout_mem[ptr_a + 2];
                    h1 <= layout_mem[ptr_a + 3];
                    x2 <= layout_mem[ptr_b];
                    y2 <= layout_mem[ptr_b + 1];
                    w2 <= layout_mem[ptr_b + 2];
                    h2 <= layout_mem[ptr_b + 3];
                end

                // ----------------------------------------------------------
                // RESOLVE: Push macro B along the axis of MINIMUM overlap.
                //          This produces the smallest displacement needed to
                //          eliminate the collision. Then clamp to die boundary.
                // ----------------------------------------------------------
                RESOLVE: begin
                    if (overlap_x <= overlap_y) begin
                        // --- Push horizontally ---
                        if (x2 >= x1) begin
                            // B is to the right of A → push B rightward
                            layout_mem[ptr_b] <= right1;
                            x2                <= right1;
                            // Clamp: if pushed past die edge, wrap to left of A
                            if (right1 + w2 > DIE_WIDTH) begin
                                layout_mem[ptr_b] <= (x1 >= w2) ? (x1 - w2) : 0;
                                x2                <= (x1 >= w2) ? (x1 - w2) : 0;
                            end
                        end else begin
                            // B is to the left of A → push B leftward
                            if (x1 >= w2) begin
                                layout_mem[ptr_b] <= x1 - w2;
                                x2                <= x1 - w2;
                            end else begin
                                layout_mem[ptr_b] <= 0;
                                x2                <= 0;
                            end
                        end
                    end else begin
                        // --- Push vertically ---
                        if (y2 >= y1) begin
                            // B is above A → push B upward
                            layout_mem[ptr_b + 1] <= top1;
                            y2                    <= top1;
                            // Clamp
                            if (top1 + h2 > DIE_HEIGHT) begin
                                layout_mem[ptr_b + 1] <= (y1 >= h2) ? (y1 - h2) : 0;
                                y2                    <= (y1 >= h2) ? (y1 - h2) : 0;
                            end
                        end else begin
                            // B is below A → push B downward
                            if (y1 >= h2) begin
                                layout_mem[ptr_b + 1] <= y1 - h2;
                                y2                    <= y1 - h2;
                            end else begin
                                layout_mem[ptr_b + 1] <= 0;
                                y2                    <= 0;
                            end
                        end
                    end
                end

                // ----------------------------------------------------------
                // ADVANCE: Move to the next pair (ptr_a, ptr_b)
                // ----------------------------------------------------------
                ADVANCE: begin
                    if (ptr_b < last_base) begin
                        // More inner-loop pairs for this ptr_a
                        ptr_b <= ptr_b + 4;
                    end else begin
                        // Inner loop exhausted → advance outer, reset inner
                        ptr_a <= ptr_a + 4;
                        ptr_b <= ptr_a + 8;   // next macro after new ptr_a
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
            FETCH:                       next_state = CHECK;
            CHECK:   if (is_overlapping) next_state = RESOLVE;
                     else                next_state = ADVANCE;
            RESOLVE:                     next_state = CHECK;  // re-check after push
            ADVANCE: begin
                if (ptr_a >= last_base - 4)
                    next_state = FINISH;        // all pairs exhausted
                else
                    next_state = FETCH;
            end
            FINISH:                      next_state = IDLE;
            default:                     next_state = IDLE;
        endcase
    end

endmodule