"""
predict.py — RTLign Hardware Handoff Bridge

Loads a trained TopologicalMacroGNN, runs inference on a single target DEF/LEF
design, breaks topological cycles to guarantee a strict DAG, and exports an
N×N 32-bit hex matrix for SystemVerilog $readmemh() initialization.

Usage:
    python ml_predictor/predict.py \
        --def_file path/to/design.def \
        --lef_file path/to/cells.lef \
        --model_path topological_gnn_model.pth \
        --output_hex data/macro_rel_constraints.hex
"""

import os
import sys
import argparse
import math
import re

import numpy as np
import torch
import joblib
import networkx as nx
from torch_geometric.data import Data

# Ensure ml_predictor is importable when run from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml_predictor.feature_extractor import FeatureExtractor, get_die_diagonal
from ml_predictor.model import TopologicalMacroGNN


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
NODE_FEATURE_COLS = ['width', 'height', 'area', 'aspect_ratio', 'pin_count']
EDGE_FEATURE_COLS = [
    'k_path_undir_1', 'shared_pins', 'net_density', 'aux_3', 'aux_4',
    'k_path_dir_1', 'k_path_dir_2', 'k_path_dir_3', 'k_path_dir_4',
    'k_path_dir_5', 'k_path_dir_6', 'k_path_dir_7', 'k_path_dir_8', 'k_path_dir_9'
]


# ---------------------------------------------------------------------------
# Feature Extraction (single DEF/LEF pair, in-memory)
# ---------------------------------------------------------------------------
def extract_features(def_file: str, lef_file: str, area_threshold: float = 1000.0):
    """
    Extracts macro node features and 14-channel edge features directly from
    a DEF+LEF pair without writing to Parquet.

    Returns:
        node_df: DataFrame with columns in NODE_FEATURE_COLS, indexed by inst_name
        edge_df: DataFrame with columns in EDGE_FEATURE_COLS + source_inst/target_inst
        inst_names: ordered list of macro instance names
    """
    ext = FeatureExtractor.__new__(FeatureExtractor)
    ext.summary_csv = ""
    ext.base_dir = os.path.dirname(os.path.abspath(def_file))

    # Parse LEF for macro dimensions
    import re
    design_name = os.path.splitext(os.path.basename(def_file))[0]
    macro_data = {}
    if lef_file and os.path.exists(lef_file):
        current_macro = None
        with open(lef_file, 'r') as f:
            for line in f:
                line_str = line.strip()
                if line_str.startswith('MACRO '):
                    parts = line_str.split()
                    if len(parts) >= 2:
                        current_macro = parts[1]
                        macro_data[current_macro] = {
                            'width': 0.0, 'height': 0.0, 'area': 0.0,
                            'aspect_ratio': 0.0, 'pin_count': 0, 'pins': {}
                        }
                elif current_macro:
                    if line_str.startswith('SIZE '):
                        m = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', line_str)
                        if m:
                            w, h = float(m.group(1)), float(m.group(2))
                            macro_data[current_macro].update({
                                'width': w, 'height': h,
                                'area': w * h,
                                'aspect_ratio': w / h if h > 0 else 0.0
                            })
                    elif line_str.startswith('PIN '):
                        macro_data[current_macro]['pin_count'] += 1
                        pin_name = line_str.split()[1] if len(line_str.split()) > 1 else 'unknown'
                        macro_data[current_macro]['pins'][pin_name] = 'INOUT'
                    elif line_str.startswith('DIRECTION '):
                        dir_val = line_str.split()[1] if len(line_str.split()) > 1 else 'INOUT'
                        if macro_data[current_macro]['pins']:
                            last_pin = list(macro_data[current_macro]['pins'].keys())[-1]
                            macro_data[current_macro]['pins'][last_pin] = dir_val
                    elif line_str.startswith('END ') and line_str.split()[-1] == current_macro:
                        current_macro = None

    # Filter macros by area threshold if specified
    if area_threshold > 0:
        filtered = {k: v for k, v in macro_data.items() if v['area'] >= area_threshold}
        if filtered:
            macro_data = filtered

    # Parse DEF for component placements
    components = ext.parse_def_components(def_file, macro_data=macro_data if macro_data else None)

    if not components:
        raise ValueError(f"No macro components found in {def_file}. Check LEF and DEF files.")

    inst_names = [c['inst_name'] for c in components]
    macro_inst_set = set(inst_names)

    # Build per-instance macro_data lookup (by inst_name, not cell_type)
    inst_macro_data = {}
    for c in components:
        cell_type = c['cell_type']
        if cell_type in macro_data:
            inst_macro_data[c['inst_name']] = macro_data[cell_type]

    # Extract 14-channel edge features
    edges = ext.parse_def_nets_kpath(def_file, macro_inst_set, inst_macro_data, max_kpath_depth=4, max_fanout=50)

    import pandas as pd
    node_records = []
    for c in components:
        node_records.append({
            'inst_name': c['inst_name'],
            'width': c['width'],
            'height': c['height'],
            'area': c['area'],
            'aspect_ratio': c['aspect_ratio'],
            'pin_count': c['pin_count'],
        })

    node_df = pd.DataFrame(node_records).set_index('inst_name')
    edge_df = pd.DataFrame(edges) if edges else pd.DataFrame(
        columns=['source_inst', 'target_inst'] + EDGE_FEATURE_COLS
    )

    return node_df, edge_df, inst_names


# ---------------------------------------------------------------------------
# Build PyG graph
# ---------------------------------------------------------------------------
def build_pyg_graph(node_df, edge_df, inst_names, node_scaler, edge_scaler):
    """Scale features and construct a torch_geometric Data object."""
    # Node features — transform (DO NOT fit_transform)
    # Use DataFrame to preserve column names expected by the fitted scaler
    import pandas as pd
    node_feats_raw = pd.DataFrame(node_df.loc[inst_names, NODE_FEATURE_COLS].values.astype(np.float32), columns=NODE_FEATURE_COLS)
    node_feats = node_scaler.transform(node_feats_raw)
    x = torch.tensor(node_feats, dtype=torch.float32)

    inst_to_idx = {name: idx for idx, name in enumerate(inst_names)}

    if edge_df.empty:
        edge_index = torch.zeros((2, 0), dtype=torch.long)
        edge_attr = torch.zeros((0, len(EDGE_FEATURE_COLS)), dtype=torch.float32)
        return Data(x=x, edge_index=edge_index, edge_attr=edge_attr), []

    src_indices, tgt_indices, edge_attrs, edge_keys = [], [], [], []
    for _, row in edge_df.iterrows():
        src, tgt = row['source_inst'], row['target_inst']
        if src not in inst_to_idx or tgt not in inst_to_idx:
            continue
        raw_feats = np.array([row[c] for c in EDGE_FEATURE_COLS], dtype=np.float32)
        src_indices.append(inst_to_idx[src])
        tgt_indices.append(inst_to_idx[tgt])
        edge_attrs.append(raw_feats)
        edge_keys.append((src, tgt))

    if not src_indices:
        edge_index = torch.zeros((2, 0), dtype=torch.long)
        edge_attr = torch.zeros((0, len(EDGE_FEATURE_COLS)), dtype=torch.float32)
        return Data(x=x, edge_index=edge_index, edge_attr=edge_attr), []

    import pandas as pd
    edge_attr_scaled = edge_scaler.transform(pd.DataFrame(np.array(edge_attrs, dtype=np.float32), columns=EDGE_FEATURE_COLS))
    edge_index = torch.tensor([src_indices, tgt_indices], dtype=torch.long)
    edge_attr = torch.tensor(edge_attr_scaled, dtype=torch.float32)

    return Data(x=x, edge_index=edge_index, edge_attr=edge_attr), edge_keys


# ---------------------------------------------------------------------------
# Cycle breaking (greedy DFS back-edge removal)
# ---------------------------------------------------------------------------
def break_cycles_dfs(G: nx.DiGraph, predictions: dict) -> nx.DiGraph:
    """
    Removes back-edges discovered during DFS traversal.
    When a back-edge is found, the edge with the lowest prediction confidence
    (smallest dist value) is removed to preserve the strongest constraints.
    Returns a DAG.
    """
    visited = set()
    in_stack = set()
    edges_to_remove = []

    def dfs(node):
        visited.add(node)
        in_stack.add(node)
        for neighbor in list(G.successors(node)):
            if neighbor in in_stack:
                # Back-edge found — remove lowest confidence edge in the cycle
                fwd = predictions.get((node, neighbor), 0.0)
                bwd = predictions.get((neighbor, node), 0.0)
                if fwd <= bwd:
                    edges_to_remove.append((node, neighbor))
                else:
                    edges_to_remove.append((neighbor, node))
            elif neighbor not in visited:
                dfs(neighbor)
        in_stack.remove(node)

    for node in list(G.nodes()):
        if node not in visited:
            dfs(node)

    G.remove_edges_from(edges_to_remove)
    return G


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def run_prediction(def_file, lef_file, model_path, output_hex, scaler_dir='data', output_coords_hex=None, area_threshold=1000.0):
    print(f"[predict] DEF: {def_file}")
    print(f"[predict] LEF: {lef_file}")

    # 1. Extract features
    print("[predict] Extracting features...")
    node_df, edge_df, inst_names = extract_features(def_file, lef_file, area_threshold=area_threshold)
    N = len(inst_names)
    print(f"[predict] Found {N} macros, {len(edge_df)} edges.")

    # 2. Load scalers
    node_scaler_path = os.path.join(scaler_dir, 'node_scaler.joblib')
    edge_scaler_path = os.path.join(scaler_dir, 'edge_scaler.joblib')
    if not os.path.exists(node_scaler_path) or not os.path.exists(edge_scaler_path):
        raise FileNotFoundError(
            f"Scalers not found in '{scaler_dir}'. "
            "Run `python ml_predictor/train_nn.py` first to generate node_scaler.joblib and edge_scaler.joblib."
        )
    node_scaler = joblib.load(node_scaler_path)
    edge_scaler = joblib.load(edge_scaler_path)
    print(f"[predict] Loaded scalers from {scaler_dir}.")

    # 3. Build PyG graph
    data, edge_keys = build_pyg_graph(node_df, edge_df, inst_names, node_scaler, edge_scaler)

    # 4. Load model and run inference
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = TopologicalMacroGNN(node_in_channels=5, edge_in_channels=14, hidden_channels=128)
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    model.eval()
    model.to(device)
    data = data.to(device)
    print(f"[predict] Running GNN inference on {device}...")

    with torch.no_grad():
        if data.edge_index.shape[1] > 0:
            preds = model(data.x, data.edge_index, data.edge_attr).cpu().numpy().flatten()
        else:
            preds = np.array([])

    # Map (src_inst, tgt_inst) -> predicted dist_norm
    pred_map = {}
    for (src, tgt), d in zip(edge_keys, preds):
        pred_map[(src, tgt)] = float(d)
        pred_map[(tgt, src)] = float(d)  # undirected lookup

    # 5. Cycle breaking
    print("[predict] Building DiGraph and breaking cycles...")
    G = nx.DiGraph()
    G.add_nodes_from(inst_names)
    for (src, tgt), d in zip(edge_keys, preds):
        G.add_edge(src, tgt, weight=float(d))

    G = break_cycles_dfs(G, pred_map)

    assert nx.is_directed_acyclic_graph(G), "Cycle breaking failed — DAG check did not pass!"
    print(f"[predict] DAG verified. Edges retained: {G.number_of_edges()} / {len(edge_keys)}.")

    # 6. Denormalize and build N×N matrix
    die_diag = get_die_diagonal(def_file)
    print(f"[predict] Die diagonal: {die_diag:.2f} DEF units.")

    inst_to_idx = {name: idx for idx, name in enumerate(inst_names)}
    matrix = np.zeros((N, N), dtype=np.uint32)

    for src, tgt, data_attr in G.edges(data=True):
        i = inst_to_idx[src]
        j = inst_to_idx[tgt]
        d_norm = data_attr['weight']
        dist_dbu = int(d_norm * die_diag)
        dist_dbu = min(dist_dbu, 0xFFFFFFFF)  # clamp to uint32
        matrix[i][j] = dist_dbu

    # 7. Export hex file (N×N topological constraint matrix)
    os.makedirs(os.path.dirname(os.path.abspath(output_hex)), exist_ok=True)
    with open(output_hex, 'w') as f:
        for i in range(N):
            for j in range(N):
                f.write(f"{matrix[i][j]:08X}\n")

    print(f"[predict] Exported {N}×{N} = {N*N} hex entries to: {output_hex}")

    # 8. Optionally resolve and export layout coordinates (X, Y, Width, Height)
    if output_coords_hex:
        die_w, die_h = get_die_bounds(def_file)
        dbu = get_def_dbu(def_file)
        resolved = resolve_topological_coordinates(G, node_df, inst_names, die_w, die_h, dbu_per_micron=dbu)
        os.makedirs(os.path.dirname(os.path.abspath(output_coords_hex)), exist_ok=True)
        with open(output_coords_hex, 'w') as f:
            for i, (x, y, w, h) in enumerate(resolved):
                name = inst_names[i]
                f.write(f"{x:08X} // X {name}\n")
                f.write(f"{y:08X} // Y {name}\n")
                f.write(f"{w:08X} // Width {name}\n")
                f.write(f"{h:08X} // Height {name}\n")
        print(f"[predict] Exported {N} resolved coordinates to: {output_coords_hex}")

    return output_hex


def get_def_dbu(def_path: str) -> int:
    """Extract UNITS DISTANCE MICRONS from DEF file, defaulting to 1000."""
    if not os.path.exists(def_path):
        return 1000
    with open(def_path, 'r') as f:
        for line in f:
            if 'UNITS DISTANCE MICRONS' in line:
                m = re.search(r'UNITS\s+DISTANCE\s+MICRONS\s+(\d+)', line)
                if m:
                    return int(m.group(1))
            if 'COMPONENTS' in line:
                break
    return 1000


def get_die_bounds(def_path: str):
    """Returns (die_width, die_height) in database units."""
    import re
    if not os.path.exists(def_path):
        return (200000, 200000)
    with open(def_path, 'r') as f:
        content = f.read()
    match = re.search(r'DIEAREA\s+(.*?)\s*;', content, re.DOTALL)
    if not match:
        return (200000, 200000)
    coords = [int(c) for c in re.findall(r'-?\d+', match.group(1))]
    if len(coords) < 4:
        return (200000, 200000)
    xs, ys = coords[0::2], coords[1::2]
    return (max(xs) - min(xs), max(ys) - min(ys))


def resolve_topological_coordinates(G: nx.DiGraph, node_df, inst_names: list, die_width: int, die_height: int, spacing: int = 1000, dbu_per_micron: int = 1) -> list:
    """
    Resolves DAG topological constraints into initial (x, y, w, h) coordinates
    for all macros, ordered by inst_names.
    """
    coords = {}
    topo_order = list(nx.topological_sort(G))
    cur_x = 0
    cur_y = 0
    row_h = 0

    for name in topo_order:
        raw_w = float(node_df.loc[name, 'width']) if (name in node_df.index and not np.isnan(node_df.loc[name, 'width'])) else 100.0
        raw_h = float(node_df.loc[name, 'height']) if (name in node_df.index and not np.isnan(node_df.loc[name, 'height'])) else 100.0
        w = max(1, int(round(raw_w * dbu_per_micron)))
        h = max(1, int(round(raw_h * dbu_per_micron)))

        in_edges = list(G.predecessors(name))
        if not in_edges:
            if cur_x + w > die_width and cur_x > 0:
                cur_x = 0
                cur_y = cur_y + row_h + spacing
                row_h = 0
            x = cur_x
            y = cur_y
            cur_x = x + w + spacing
            row_h = max(row_h, h)
        else:
            min_x = 0
            min_y = 0
            for pred in in_edges:
                pred_c = coords[pred]
                px = pred_c['x'] + pred_c['w'] + spacing
                py = pred_c['y']
                if px + w > die_width:
                    px = 0
                    py = pred_c['y'] + pred_c['h'] + spacing
                if px > min_x:
                    min_x = px
                if py > min_y:
                    min_y = py
            x = max(min_x, cur_x) if min_y <= cur_y else min_x
            y = max(min_y, cur_y)
            if x + w > die_width and x > 0:
                x = 0
                y = cur_y + row_h + spacing
                row_h = 0
            cur_x = x + w + spacing
            cur_y = y
            row_h = max(row_h, h)

        x = max(0, min(x, max(0, die_width - w)))
        y = max(0, min(y, max(0, die_height - h)))
        coords[name] = {'x': x, 'y': y, 'w': w, 'h': h}

    result = []
    for name in inst_names:
        c = coords.get(name, {'x': 0, 'y': 0, 'w': 100, 'h': 100})
        result.append((c['x'], c['y'], c['w'], c['h']))
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="RTLign GNN Predictor — Hardware Hex Export")
    parser.add_argument('--def_file', required=True, help='Path to input DEF layout file')
    parser.add_argument('--lef_file', required=True, help='Path to input LEF cell library file')
    parser.add_argument('--model_path', default='topological_gnn_model.pth', help='Path to trained .pth model')
    parser.add_argument('--output_hex', default='data/macro_rel_constraints.hex', help='Output .hex file path')
    parser.add_argument('--output_coords_hex', default=None, help='Optional output (X, Y, W, H) coordinate hex file')
    parser.add_argument('--scaler_dir', default='data', help='Directory containing node_scaler.joblib and edge_scaler.joblib')
    parser.add_argument('--area_threshold', type=float, default=1000.0, help='Minimum macro area in µm² (default: 1000.0)')
    args = parser.parse_args()

    run_prediction(
        def_file=args.def_file,
        lef_file=args.lef_file,
        model_path=args.model_path,
        output_hex=args.output_hex,
        scaler_dir=args.scaler_dir,
        output_coords_hex=args.output_coords_hex,
        area_threshold=args.area_threshold,
    )
