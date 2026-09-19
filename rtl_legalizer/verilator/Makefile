# ============================================================================
# RTLign — Verilator Build Makefile
# ============================================================================

VERILATOR ?= /home/ratik/Projects/RTLign/oss-cad-suite/bin/verilator

VERILOG_DIR = ..
VERILOG_SRCS = $(VERILOG_DIR)/collision_check.v \
               $(VERILOG_DIR)/lfsr32.v \
               $(VERILOG_DIR)/sa_cost.v \
               $(VERILOG_DIR)/sa_engine.v \
               $(VERILOG_DIR)/legalizer_fsm.v \
               $(VERILOG_DIR)/sa_legalizer_top.v

HARNESS = sa_harness.cpp
TARGET  = legalizer_sim

VERILATOR_FLAGS = -Wall -Wno-fatal \
                  -Wno-BLKSEQ \
                  -Wno-WIDTHEXPAND \
                  -Wno-UNUSEDSIGNAL \
                  -Wno-UNUSEDPARAM \
                  -O3 \
                  --cc \
                  --exe \
                  --build \
                  --top-module sa_legalizer_top \
                  -I$(VERILOG_DIR) \
                  -o $(TARGET)

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(VERILOG_SRCS) $(HARNESS)
	$(VERILATOR) $(VERILATOR_FLAGS) $(VERILOG_SRCS) $(HARNESS)
	cp obj_dir/$(TARGET) .

clean:
	rm -rf obj_dir $(TARGET) output_layout.hex

