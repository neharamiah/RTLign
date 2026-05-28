# RTLign — Monthly Progress Report

## 1. Problem Definition
During the physical design phase of VLSI development, macro placement is an NP-hard optimization problem. It is currently heavily bottlenecked by sequential CPU calculations in traditional EDA tools. Suboptimal or slow macro placement degrades a chip's Power, Performance, and Area (PPA) metrics and limits the scalability of physical design exploration.

## 2. Literature Review
The team conducted an extensive literature review covering core VLSI principles and recent ML advancements:
- **Foundations:** *VLSI Physical Design* by Kahng et al.
- **Machine Learning for EDA:** *Machine Learning for EDA: A Survey* (Huang et al., 2021).
- **Placement Algorithms:** Studied traditional Simulated Annealing (e.g., TimberWolf) and recent ML/RL-driven approaches like Google's Graph Placement (Nature, 2021), MaskPlace (NeurIPS 2022), and ChiPFormer (ICML 2023).

## 3. Existing System
The existing system relies on standard software-based EDA flows (such as OpenROAD). In these flows, macro placement and legalization are performed sequentially on standard CPUs. These software approaches (using greedy sweeps or simulated annealing) are relatively slow and fail to exploit the massively parallel nature of collision-detection logic, ultimately increasing the turnaround time for physical design.

## 4. Proposed System
**RTLign** is a hardware-software co-design accelerator. It hijacks the standard OpenROAD flow and replaces the software placer with a heterogeneous pipeline:
1. A Machine Learning predictor for approximate coordinates.
2. A deterministic Verilog RTL hardware engine for high-speed, parallel macro legalization and overlap resolution.
3. Python-based extraction and injection scripts to communicate between the OpenROAD database (DEF/LEF) and the RTL hardware.

## 5. Knowledge Gained - Tools, Technology, Courses etc.
- **EDA Tools & Formats:** Deep understanding of OpenROAD, DEF (Design Exchange Format), and LEF (Library Exchange Format) specifications.
- **Hardware Description:** Advanced Verilog HDL, including Mealy FSMs, parameterization, and memory mapping (`$readmemh`).
- **Orchestration:** Python subprocess management for hardware-software communication.
- **Concepts:** Combinational Axis-Aligned Bounding Box (AABB) collision algorithms and VLSI floorplanning.

## 6. Architectural Framework
The architectural framework consists of a 4-stage pipeline:
1. **LEF Parser:** Extracts exact macro dimensions from technology libraries.
2. **DEF Parser:** Converts OpenROAD placement files and LEF dimensions into hardware-readable hex memory format.
3. **Verilog SA / Legalizer:** RTL engine (`legalizer_fsm.v`) that iterates over macro pairs, detects AABB overlaps, and computes minimum displacement while clamping to die boundaries.
4. **HEX-to-DEF Injector:** Patches the overlap-free coordinates back into the original DEF file for subsequent routing and static timing analysis (STA).

## 7. Project Implementation
Over the past month, the team successfully built and integrated the foundational pipeline:
- **Hardware Development:** Designed the combinational collision checker (`collision_check.v`), the FSM-based greedy sweep legalizer (`legalizer_fsm.v`), and an automated audit testbench (`legalizer_tb.v`).
- **Software Development:** Created `lef_parser.py` (with full unit tests) and `def_parser.py` to bridge physical cell dimensions with coordinate data. Created `hex_to_def.py` for reintegration.
- **Orchestration:** Wired the complete system together via `master_run.py`.

## 8. Results
The pipeline successfully executes an end-to-end legalization process for benchmark designs (e.g., GCD on FreePDK45). 
- **Scale:** Handled 168 macros successfully.
- **Accuracy:** Solved with **0 overlaps** confirmed by the post-legalization hardware audit.
- **Performance:** Hardware simulation completed in 42,086 clock cycles (~0.42 ms theoretical hardware latency at 100 MHz). The complete python orchestration loop takes only ~0.22 seconds.

## 9. Conclusion and Future Work
**Conclusion:** Phase 1 (Foundations) is successfully completed. The hardware-software interaction is robust, and physically accurate cell dimensions are successfully integrated into the logic.
**Future Work:** 
- Upgrade the Verilog greedy sweep to a full Simulated Annealing (SA) engine (LFSR random perturbation, temperature schedule).
- Generate training datasets using OpenROAD batch scripts.
- Develop the Supervised ML baseline and Reinforcement Learning models to provide the initial approximate coordinates.

## 10. Research Article Preparation
Research article preparation is in its preliminary stages. The literature review is complete, and the methodology section is currently being outlined based on the successful implementation of the hardware-software co-design architecture.
