# RTL Legalizer Engine

This directory contains the core custom hardware logic for the RTLign pipeline. The engine is responsible for parallelized Axis-Aligned Bounding Box (AABB) collision detection and Simulated Annealing (SA) legalization.

### Current Modules

#### `collision_check.v`
This is a pure combinational logic module that acts as our hardware overlap judge. 

**Inputs:**
* Macro A: `x1, y1` (origin), `w1, h1` (dimensions) - 32-bit hex
* Macro B: `x2, y2` (origin), `w2, h2` (dimensions) - 32-bit hex

**Output:**
* `overlap`: 1-bit wire. Outputs `1` if an illegal overlap occurs, `0` if the space is clear or edges are perfectly flush.

**Data Contract:**
The Python orchestrator will feed coordinates into this engine via the `dummy_layout.hex` memory map.