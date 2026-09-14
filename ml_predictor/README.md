# ML Predictor

This directory contains the machine learning components for the RTLign pipeline. The components extract physical design features, train Graph Neural Networks (GNN), infer relative topological relationships (L-flows), and evaluate end-to-end placement metrics.

## Pipeline Architecture

```
OpenROAD DEF + LEF
        │
        ▼
feature_extractor.py ──▶ Parquet Datasets (Features, Connectivity, Distances)
                                │
                                ▼
                           dataset.py (PyTorch Geometric Data Loader)
                                │
                                ▼
                          train_nn.py ──▶ topological_gnn_model.pth
                                │
                                ▼
                           predict.py ──▶ DAG Cycle-Breaker ──▶ macro_rel_constraints.hex
                                                                        │
                                                                        ▼
                                                                RTL Legalizer / DAG-Solver
                                                                        │
                                                                        ▼
                                                                   hex_to_def.py
                                                                        │
                                                                        ▼
                                                    evaluate.py ◀── OpenROAD STA & HPWL
```

## Components

- **`dataset.py`**: PyTorch Geometric `InMemoryDataset` implementation (`MacroDataset`). Ingests Parquet feature tables (`macro_features.parquet`, `connectivity.parquet`, etc.), builds PyG graph representations with 14-channel edge features, and constructs training/validation splits.
- **`model.py`**: Neural network architecture definitions (`TopologicalGNN`, `SpatialEdgeConv`). Utilizes message-passing graph convolutions with edge feature conditioning to infer pairwise macro spatial displacements ($\Delta x, \Delta y$) and relative topological constraints.
- **`train_nn.py`**: Supervised training script for `TopologicalGNN`. Loads dataset batches, computes MSE / Smooth L1 loss against ground-truth OpenROAD placements, evaluates validation loss, and serializes the trained checkpoint to `topological_gnn_model.pth`.
- **`predict.py`**: Standalone inference engine. Reads candidate `.def` and `.lef` files, constructs graph features, evaluates `topological_gnn_model.pth`, applies a DFS-based cycle-breaking algorithm to guarantee a Directed Acyclic Graph (DAG), and exports an $N \times N$ 32-bit hex matrix for SystemVerilog initialization.
- **`evaluate.py`**: Automated end-to-end evaluation orchestrator. Runs inference, triggers RTL legalization, injects coordinates via `hex_to_def.py`, measures wirelength (HPWL) and legality in OpenROAD using `openroad_scripts/evaluate_layout.tcl`, and saves layout comparison plots (`evaluation_plot.png`).
- **`feature_extractor.py`**: High-throughput extraction engine. Parses `.def` layouts and extracts cell attributes, node coordinates, pin counts, 14-channel edge connectivity, and pairwise distances into snappy-compressed Parquet datasets.
- **`def_parser.py`**: Parses `.def` files and matches macro components against `.lef` libraries to generate raw `.hex` coordinate memory files for the baseline legalizer.
- **`hex_to_def.py`**: Patches legalized coordinates from `.hex` format back into the original `.def` file, preserving all pin definitions, special nets, and routing information.

## Usage Examples

### 1. Train the Topological GNN
```bash
python ml_predictor/train_nn.py --data_dir data/parquet_dataset --epochs 100 --batch_size 16
```

### 2. Run Inference on a DEF/LEF Pair
```bash
python ml_predictor/predict.py \
  --def_file openroad_scripts/mockup_export.def \
  --lef_file data/cells.lef \
  --model_path topological_gnn_model.pth \
  --output_hex data/macro_rel_constraints.hex
```
*Or use the automatic detection wrapper:*
```bash
python run_predict.py
```

### 3. Evaluate End-to-End Metrics and Generate Layout Plots
```bash
python ml_predictor/evaluate.py \
  --def_file openroad_scripts/mockup_export.def \
  --tech_lef data/tech.lef \
  --cells_lef data/cells.lef \
  --model_path topological_gnn_model.pth \
  --output_dir evaluation_output
```
