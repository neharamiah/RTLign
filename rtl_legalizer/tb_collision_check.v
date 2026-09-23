// ============================================================================
// RTLign — Unit testbench for collision_check.v
// Directed corner matrix: touching edges, minimal overlaps, containment,
// disjoint boxes, zero-size boxes. Self-checking; $fatal on any mismatch.
// ============================================================================

`timescale 1ns / 1ps

module tb_collision_check;

    reg  [31:0] x1, y1, w1, h1, x2, y2, w2, h2;
    wire        overlap;
    integer     errors;
    integer     checks;

    collision_check dut (
        .x1(x1), .y1(y1), .w1(w1), .h1(h1),
        .x2(x2), .y2(y2), .w2(w2), .h2(h2),
        .overlap(overlap)
    );

    task check(
        input [31:0] ax,  input [31:0] ay,  input [31:0] aw, input [31:0] ah,
        input [31:0] bx,  input [31:0] by,  input [31:0] bw, input [31:0] bh,
        input             expect_ov,
        input [127:0]     name
    );
    begin
        x1 = ax; y1 = ay; w1 = aw; h1 = ah;
        x2 = bx; y2 = by; w2 = bw; h2 = bh;
        #1;
        checks = checks + 1;
        if (overlap !== expect_ov) begin
            errors = errors + 1;
            $display("FAIL [%0s]: got overlap=%b expected=%b", name, overlap, expect_ov);
            $display("       A=(%0d,%0d %0dx%0d) B=(%0d,%0d %0dx%0d)", ax, ay, aw, ah, bx, by, bw, bh);
        end
    end
    endtask

    initial begin
        errors = 0;
        checks = 0;

        // Identical boxes
        check(100, 100, 50, 50, 100, 100, 50, 50, 1'b1, "identical");
        // 1-DBU overlap on each corner direction
        check(100, 100, 50, 50, 149, 100, 50, 50, 1'b1, "ov_left_edge");
        check(100, 100, 50, 50, 100, 149, 50, 50, 1'b1, "ov_bottom_edge");
        check(100, 100, 50, 50,  51, 100, 50, 50, 1'b1, "ov_right_edge");
        check(100, 100, 50, 50, 100,  51, 50, 50, 1'b1, "ov_top_edge");
        // Touching edges on all four sides — strict AABB, no overlap
        check(100, 100, 50, 50, 150, 100, 50, 50, 1'b0, "touch_right");
        check(100, 100, 50, 50,  50, 100, 50, 50, 1'b0, "touch_left");
        check(100, 100, 50, 50, 100, 150, 50, 50, 1'b0, "touch_above");
        check(100, 100, 50, 50, 100,  50, 50, 50, 1'b0, "touch_below");
        // Corner touch (diagonal)
        check(100, 100, 50, 50, 150, 150, 50, 50, 1'b0, "touch_corner");
        // Full containment
        check(100, 100, 100, 100, 120, 120, 20, 20, 1'b1, "contained");
        // Same box nested the other way
        check(120, 120, 20, 20, 100, 100, 100, 100, 1'b1, "contains");
        // Disjoint on one axis, aligned on the other
        check(0,   0, 10, 10, 500, 0, 10, 10, 1'b0, "disjoint_x");
        check(0,   0, 10, 10,   0, 500, 10, 10, 1'b0, "disjoint_y");
        // Zero-size box cannot overlap
        check(100, 100, 0, 0, 100, 100, 50, 50, 1'b0, "zero_size");
        // Plus-shaped boxes: partial overlap on both axes
        check(0, 4, 10, 2, 4, 0, 2, 10, 1'b1, "cross");

        if (errors == 0) begin
            $display("ALL COLLISION CHECKS PASSED (%0d checks)", checks);
            $finish;
        end else begin
            $fatal(1, "%0d of %0d collision checks failed", errors, checks);
        end
    end

endmodule
