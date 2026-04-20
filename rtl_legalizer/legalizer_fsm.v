module legalizer_fsm (
    input wire clk,
    input wire rst,
    input wire start,
    output reg done
);

    // --- 1. Memory Setup ---
    reg [31:0] layout_mem [0:1023]; 
    
    initial begin
        // Loads the real GCD chip data Ratik just generated
        $readmemh("dummy_layout.hex", layout_mem); 
    end

    // --- 2. Macro Registers & Pointers ---
    reg [9:0] ptr_a; 
    reg [9:0] ptr_b; 
    
    reg [31:0] x1, y1, w1, h1;
    reg [31:0] x2, y2, w2, h2;

    // --- 3. Collision Checker Instantiation ---
    wire is_overlapping;
    
    collision_check checker (
        .x1(x1), .y1(y1), .w1(w1), .h1(h1),
        .x2(x2), .y2(y2), .w2(w2), .h2(h2),
        .overlap(is_overlapping)
    );

    // --- 4. FSM States ---
    parameter IDLE    = 3'b000;
    parameter FETCH   = 3'b001;
    parameter CHECK   = 3'b010;
    parameter RESOLVE = 3'b011;
    parameter FINISH  = 3'b100;

    reg [2:0] current_state, next_state;

    // --- 5. State Machine: Clocked Update ---
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            current_state <= IDLE;
            ptr_a <= 0;
            ptr_b <= 4;
            done <= 0;
        end else begin
            current_state <= next_state;
            
            // Datapath actions based on state
            if (current_state == FETCH) begin
                // Load coordinates from RAM using pointers
                x1 <= layout_mem[ptr_a];
                y1 <= layout_mem[ptr_a + 1];
                w1 <= layout_mem[ptr_a + 2];
                h1 <= layout_mem[ptr_a + 3];

                x2 <= layout_mem[ptr_b];
                y2 <= layout_mem[ptr_b + 1];
                w2 <= layout_mem[ptr_b + 2];
                h2 <= layout_mem[ptr_b + 3];
            end
        end
    end

    // --- 6. State Machine: Combinational Next-State Logic ---
    always @(*) begin
        next_state = current_state; 

        case (current_state)
            IDLE:    
                if (start) next_state = FETCH;
            
            FETCH:   
                next_state = CHECK;
            
            CHECK:   
                if (is_overlapping) 
                    next_state = RESOLVE; 
                else 
                    next_state = FINISH; // Simplified for now
            
            RESOLVE: 
                next_state = CHECK; 
            
            FINISH:  
                next_state = IDLE;
                
            default: 
                next_state = IDLE;
        endcase
    end

endmodule