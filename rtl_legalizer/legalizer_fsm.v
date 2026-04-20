// --- MODULE 1: The Math Engine ---
module collision_check (
    input [31:0] x1, y1, w1, h1,  
    input [31:0] x2, y2, w2, h2,  
    output overlap
);
    wire [31:0] right1 = x1 + w1;
    wire [31:0] top1   = y1 + h1;
    wire [31:0] right2 = x2 + w2;
    wire [31:0] top2   = y2 + h2;

    assign overlap = (x1 < right2) && (right1 > x2) &&
                     (y1 < top2)   && (top1 > y2);
endmodule

// --- MODULE 2: The FSM Brain ---
module legalizer_fsm (
    input wire clk,
    input wire rst,
    input wire start,
    output reg done
);
    // Virtual Memory
    reg [31:0] layout_mem [0:1023]; 
    initial $readmemh("dummy_layout.hex", layout_mem); 

    // Registers and Pointers
    reg [9:0] ptr_a; 
    reg [9:0] ptr_b; 
    reg [31:0] x1, y1, w1, h1;
    reg [31:0] x2, y2, w2, h2;

    // Collision Math Wiring
    wire is_overlapping;
    collision_check col_inst (
        .x1(x1), .y1(y1), .w1(w1), .h1(h1),
        .x2(x2), .y2(y2), .w2(w2), .h2(h2),
        .overlap(is_overlapping)
    );

    // State Parameters
    parameter IDLE    = 3'b000, FETCH   = 3'b001, CHECK   = 3'b010;
    parameter RESOLVE = 3'b011, ADVANCE = 3'b100, FINISH  = 3'b101;
    
    // Safety limit for the dummy layout file
    parameter MAX_LINES = 8; 

    reg [2:0] current_state, next_state;

    // --- SEQUENTIAL LOGIC (Datapath & State Memory) ---
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            current_state <= IDLE;
            ptr_a <= 0; ptr_b <= 4;
            done <= 0;
        end else begin
            current_state <= next_state;
            
            if (current_state == FETCH) begin
                x1 <= layout_mem[ptr_a]; y1 <= layout_mem[ptr_a + 1];
                w1 <= layout_mem[ptr_a + 2]; h1 <= layout_mem[ptr_a + 3];
                x2 <= layout_mem[ptr_b]; y2 <= layout_mem[ptr_b + 1];
                w2 <= layout_mem[ptr_b + 2]; h2 <= layout_mem[ptr_b + 3];
            end 
            else if (current_state == RESOLVE) begin
                // Update short-term register for the next CHECK
                x2 <= x1 + w1; 
                
                // COMMIT TO RAM: Overwrite Macro B's X coordinate!
                layout_mem[ptr_b] <= x1 + w1; 
            end
            else if (current_state == ADVANCE) begin
                if (ptr_b < MAX_LINES - 4) begin
                    ptr_b <= ptr_b + 4;
                end else begin
                    ptr_a <= ptr_a + 4;
                    ptr_b <= ptr_a + 8;
                end
            end
            else if (current_state == FINISH) begin
                done <= 1;
            end
        end
    end

    // --- COMBINATIONAL LOGIC (Decision Routing) ---
    always @(*) begin
        next_state = current_state; 
        case (current_state)
            IDLE:    if (start) next_state = FETCH;
            FETCH:   next_state = CHECK;
            CHECK:   if (is_overlapping) next_state = RESOLVE; else next_state = ADVANCE;
            RESOLVE: next_state = CHECK; 
            ADVANCE: if (ptr_a >= MAX_LINES - 8) next_state = FINISH; else next_state = FETCH;
            FINISH:  next_state = IDLE;
            default: next_state = IDLE;
        endcase
    end
endmodule