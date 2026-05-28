# RTLign Product Summary

## Product Overview

RTLign is an ML-assisted simulated annealing tool for VLSI macro placement that replaces traditional software placers with a heterogeneous hardware-software co-design pipeline. It integrates with the OpenROAD physical design flow to accelerate macro legalization using custom RTL hardware.

## Core Value Proposition

Traditional macro placement is an NP-hard optimization bottleneck in VLSI physical design. RTLign addresses this by:
- Using ML to predict approximate macro coordinates
- Resolving overlaps in parallel hardware (Verilog FSM) instead of sequential CPU calculations
- Maintaining physical design rule compliance through deterministic RTL legalization

## Pipeline Architecture

```
OpenROAD DEF → ML Predictor → RTL Legalizer → OpenROAD Import
                (Python)        (Verilog)        (Python)
```

1. **DEF Parser** - Extracts macro placements from OpenROAD `.def` files
2. **LEF Parser** - Extracts real cell dimensions from library `.lef` files  
3. **ML Predictor** - Predicts wirelength-optimized coordinates (planned)
4. **RTL Legalizer** - Custom Verilog FSM with AABB collision detection and greedy sweep resolution
5. **HEX→DEF Injector** - Patches legalized coordinates back into DEF files

## Current Status

- Phase 1 complete: End-to-end pipeline with greedy sweep legalizer
- Phase 2 in progress: Real cell dimension extraction via LEF parser
- Phase 3-6 planned: ML predictor, simulated annealing, RL agent, benchmarking

## Key Metrics

- Zero-overlap legalization guarantee
- Hardware latency: ~0.42ms for 168 macros at 100MHz
- Total pipeline runtime: <0.5 seconds

## Target Users

VLSI physical design engineers and EDA tool developers seeking to accelerate macro placement in the OpenROAD flow.
