// ============================================================================
// RTLign — Unit testbench for sa_cost.v
// Directed scenarios with hand-computed expected values, replicating the
// exact unsigned/signed RTL arithmetic (including the negative-coordinate
// quirks). Self-checking; $fatal on any mismatch.
//
// Config: NUM_LINES=8 (2 macros), DIE 1000x1000, W_WL=4, W_AREA=1,
//         W_BOUNDARY=8, AREA_SCALE_SHIFT=0.
// ============================================================================

`timescale 1ns / 1ps

module tb_sa_cost;

    reg         clk = 0;
    reg         rst = 1;
    reg         start = 0;
    wire        done;
    wire [31:0] mem_addr;
    reg  [31:0] mem_rdata;
    wire [63:0] total_cost;
    wire [31:0] hpwl;
    wire [63:0] area;
    wire [31:0] boundary;

    reg [31:0] mem [0:7];

    sa_cost #(
        .NUM_LINES(8),
        .DIE_WIDTH(1000),
        .DIE_HEIGHT(1000),
        .W_WL(4),
        .W_AREA(1),
        .W_BOUNDARY(8),
        .AREA_SCALE_SHIFT(0)
    ) dut (
        .clk(clk), .rst(rst), .start(start), .done(done),
        .mem_addr(mem_addr), .mem_rdata(mem_rdata),
        .total_cost(total_cost), .hpwl_out(hpwl),
        .bbox_area_out(area), .boundary_penalty_out(boundary)
    );

    always #5 clk = ~clk;
    always @(*) mem_rdata = mem[mem_addr];

    integer errors;

    task run_case(input [63:0] e_cost, input [31:0] e_hpwl,
                  input [63:0] e_area, input [31:0] e_bnd,
                  input [127:0] name);
    begin
        @(posedge clk); #1 start = 1;
        @(posedge clk); #1 start = 0;
        while (!done) @(posedge clk);
        #1;
        if (total_cost !== e_cost || hpwl !== e_hpwl ||
            area !== e_area || boundary !== e_bnd) begin
            errors = errors + 1;
            $display("FAIL [%0s]", name);
            $display("  cost=%0d (exp %0d) hpwl=%0d (exp %0d)",
                     total_cost, e_cost, hpwl, e_hpwl);
            $display("  area=%0d (exp %0d) bnd=%0d (exp %0d)",
                     area, e_area, boundary, e_bnd);
        end
    end
    endtask

    initial begin
        errors = 0;

        rst = 1;
        #20;
        rst = 0;
        #10;

        // --- Scenario A: two clean macros inside the die -------------------
        // M0=(100,200,50,60) center (125,230); M1=(300,400,100,100) center (350,450)
        // HPWL = 225+220 = 445; bbox = 300x300 = 90000; boundary = 0
        // cost = 4*445 + 1*90000 + 8*0 = 91780
        mem[0]=100; mem[1]=200; mem[2]=50;  mem[3]=60;
        mem[4]=300; mem[5]=400; mem[6]=100; mem[7]=100;
        run_case(64'd91780, 32'd445, 64'd90000, 32'd0, "clean_two");

        // --- Scenario B: macro with negative x (two's complement) ----------
        // M0=(x=-50,200,100,100): pen_x = 50 (left), s_right wraps to +50.
        // cx0 = (-50+50) wraps to 0; cx1 = 350; cy0 = 250; cy1 = 450.
        // HPWL = 350+200 = 550; min_left ends at 300 (M1 wins over 0xFFFFFFCE);
        // max_right = 400; bbox = 100x300 = 30000; boundary = 50.
        // cost = 4*550 + 30000 + 8*50 = 32600
        mem[0]=32'hFFFFFFCE; mem[1]=200; mem[2]=100; mem[3]=100;
        mem[4]=300;          mem[5]=400; mem[6]=100; mem[7]=100;
        run_case(64'd32600, 32'd550, 64'd30000, 32'd50, "negative_x");

        // --- Scenario C: macro poking out of the right die edge ------------
        // M0=(950,100,100,50): pen_x = 1050-1000 = 50. M1=(0,0,10,10).
        // HPWL = (1000-5)+(125-5) = 1115; bbox = 1050x150 = 157500.
        // cost = 4*1115 + 157500 + 8*50 = 162360
        mem[0]=950; mem[1]=100; mem[2]=100; mem[3]=50;
        mem[4]=0;   mem[5]=0;   mem[6]=10;  mem[7]=10;
        run_case(64'd162360, 32'd1115, 64'd157500, 32'd50, "right_overflow");

        // --- Scenario D: macro fully below the die (y < 0) ------------------
        // M0=(100,-40,100,50): pen_y = 40; top wraps to +10.
        // cx0=150, cy0=-40+25=0xFFFFFFF1; M1 center (5,5) wins both min_cy
        // and min_bottom. max_cy = 0xFFFFFFF1 -> span_cy = 0xFFFFFFF1-5
        // = 4294967276; hpwl = (145 + 4294967276) wraps 32-bit to 125.
        // bbox = 200x10 = 2000; boundary = 40.
        // cost = 4*125 + 2000 + 8*40 = 2820
        mem[0]=100; mem[1]=32'hFFFFFFD8; mem[2]=100; mem[3]=50;
        mem[4]=0;   mem[5]=0;            mem[6]=10;  mem[7]=10;
        run_case(64'd2820, 32'd125, 64'd2000, 32'd40, "negative_y");

        if (errors == 0) begin
            $display("ALL COST CHECKS PASSED");
            $finish;
        end else begin
            $fatal(1, "%0d cost checks failed", errors);
        end
    end

endmodule
