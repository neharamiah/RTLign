# ML Predictor

This directory contains the machine learning components for the RTLign pipeline. The components extract features and infer relative topological relationships (L-flows).

## Components

- `def_parser.py`: This script parses OpenROAD `.def` files and `.lef` library files. It extracts macro placements and dimensions. It writes these topologies to a flat `.hex` file for the DAG-solver.
- `feature_extractor.py`: This script parses the generated `.def` layout files. It extracts placement data and generates Parquet files. The output includes structural node features and graph edge indices (14-channel edge vectors) to train the Graph Neural Networks (GNN) to predict L-flows.
- `hex_to_def.py`: This script reads the exact coordinates (resolved from topologies) from a `.hex` file. It writes these coordinates back into the original `.def` file.
