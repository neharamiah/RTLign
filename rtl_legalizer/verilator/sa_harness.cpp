// ============================================================================
// RTLign — Verilator C++ Simulation Harness for SA Legalizer
// ============================================================================

#include <iostream>
#include <fstream>
#include <iomanip>
#include <string>
#include <vector>
#include <cstdint>
#include <cstdlib>

#include "Vsa_legalizer_top.h"
#include "Vsa_legalizer_top_sa_legalizer_top.h"
#include "verilated.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);

    std::string output_hex = "output_layout.hex";
    if (argc >= 2) {
        output_hex = argv[1];
    }

    Vsa_legalizer_top* top = new Vsa_legalizer_top;

    // Reset sequence
    top->clk = 0;
    top->rst = 1;
    top->start = 0;

    for (int i = 0; i < 10; ++i) {
        top->clk = !top->clk;
        top->eval();
    }

    top->rst = 0;
    for (int i = 0; i < 4; ++i) {
        top->clk = !top->clk;
        top->eval();
    }

    // Pulse start
    top->start = 1;
    top->clk = 1;
    top->eval();
    top->clk = 0;
    top->eval();
    top->start = 0;

    // Main execution loop
    uint64_t cycle_count = 0;
    const uint64_t MAX_CYCLES = 100000000; // 100M cycle safety limit

    while (!top->done && cycle_count < MAX_CYCLES) {
        top->clk = 1;
        top->eval();
        top->clk = 0;
        top->eval();
        cycle_count++;
    }

    if (top->done) {
        std::cout << "========================================" << std::endl;
        std::cout << "  RTLign Legalizer — Verilator Finished" << std::endl;
        std::cout << "========================================" << std::endl;
        std::cout << "  Clock Cycles    : " << cycle_count << std::endl;
        std::cout << "  SA Iterations   : " << top->total_iters << std::endl;
        std::cout << "  Accepted Moves  : " << top->accepted_count << std::endl;
        std::cout << "  Final Cost      : " << top->final_cost << std::endl;
        std::cout << "  Final Temp      : " << top->final_temp << std::endl;
        std::cout << "========================================" << std::endl;

        // Write legalized output memory to HEX file
        std::ofstream outfile(output_hex);
        if (outfile.is_open()) {
            for (size_t i = 0; i < 672; ++i) {
                outfile << std::hex << std::uppercase << std::setw(8) << std::setfill('0')
                        << top->sa_legalizer_top->layout_mem[i] << std::endl;
            }
            outfile.close();
            std::cout << "  Output written to: " << output_hex << std::endl;
        } else {
            std::cerr << "ERROR: Failed to open output file " << output_hex << std::endl;
        }
    } else {
        std::cerr << "ERROR: Verilator simulation timed out after " << cycle_count << " cycles!" << std::endl;
        delete top;
        return 1;
    }

    delete top;
    return 0;
}
