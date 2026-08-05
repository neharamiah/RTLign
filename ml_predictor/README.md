# ML Predictor

This directory contains the machine learning components for the RTLign pipeline. The components extract features and predict macro coordinates.

## Components

- `def_parser.py`: This script parses OpenROAD `.def` files and `.lef` library files. It extracts macro placements and dimensions. It writes these coordinates to a flat `.hex` file.
- `feature_extractor.py`: This script parses the generated `.def` layout files. It extracts placement data and generates Parquet files. The output includes node features and graph edge indices for Graph Neural Networks (GNN).
- `hex_to_def.py`: This script reads legalized coordinates from a `.hex` file. It writes these coordinates back into the original `.def` file.
