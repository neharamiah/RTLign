module collision_check (
    input [31:0] x1, y1, w1, h1,  // Macro A
    input [31:0] x2, y2, w2, h2,  // Macro B
    output overlap
);

    // Calculate the right and top edges
    wire [31:0] right1 = x1 + w1;
    wire [31:0] top1   = y1 + h1;
    wire [31:0] right2 = x2 + w2;
    wire [31:0] top2   = y2 + h2;

    // AABB Collision Logic: Overlap exists if ALL these are true
    assign overlap = (x1 < right2) && (right1 > x2) &&
                     (y1 < top2)   && (top1 > y2);

endmodule