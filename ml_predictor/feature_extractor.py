#!/usr/bin/env python3
"""
Feature Extractor for RTLign ML Predictor Pipeline

Bridges OpenROAD physical design sweeps with PyTorch / PyTorch Geometric ML
pipelines by parsing DEF layout files to extract:
  - Node features: macro/component placement coordinates (COMPONENTS section)
  - Edge connectivity: macro-to-macro wiring topology (NETS section)

Outputs four snappy-compressed Parquet datasets:
  - ml_features.parquet        — node feature matrix (5-channel + PPA stubs)
  - raw_coords.parquet         — provenance dataset with raw (x,y)
  - edge_index.parquet         — 14-channel edge connectivity
  - pairwise_distances.parquet — L-flow dist_norm targets
"""

import os
import re
import math
import glob
import csv
import argparse
from typing import List, Dict, Any, Set, Optional, Tuple
from collections import defaultdict
from itertools import combinations
import pandas as pd
import numpy as np
from scipy.sparse import dok_matrix, csr_matrix
from scipy.spatial.distance import pdist, squareform
from tqdm import tqdm


def get_die_diagonal(def_path: str) -> float:
    """Safely extracts DIEAREA to compute the bounding box diagonal."""
    if not os.path.exists(def_path):
        return 1.0
    with open(def_path, 'r') as f:
        content = f.read()
    match = re.search(r'DIEAREA\s+(.*?)\s*;', content, re.DOTALL)
    if not match:
        return 1.0
    coords = [int(c) for c in re.findall(r'-?\d+', match.group(1))]
    if len(coords) < 4:
        return 1.0
    xs, ys = coords[0::2], coords[1::2]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    return math.sqrt(width**2 + height**2)


class FeatureExtractor:
    def __init__(self, summary_csv: str = "data/generated_defs/dataset_summary.csv"):
        self.summary_csv = summary_csv
        self.base_dir = os.path.dirname(os.path.abspath(summary_csv))

    def parse_def_filename(self, def_path: str) -> Dict[str, Any]:
        fname = os.path.basename(def_path)
        dir_design = os.path.basename(os.path.dirname(def_path))

        m = re.match(r'^(.+)_s(\d+)_t([\d.]+)_ar([\d.]+)_u([\d.]+)_d([\d.]+)\.def$', fname)
        if m:
            return {
                "design": m.group(1),
                "seed": m.group(2),
                "snapshot_threshold": m.group(3),
                "aspect_ratio": float(m.group(4)),
                "utilization": float(m.group(5)),
                "density": float(m.group(6)),
                "def_path": def_path
            }

        m = re.match(r'^(.+)_ar([\d.]+)_u([\d.]+)_d([\d.]+)\.def$', fname)
        if m:
            return {
                "design": m.group(1),
                "seed": "N/A",
                "snapshot_threshold": "N/A",
                "aspect_ratio": float(m.group(2)),
                "utilization": float(m.group(3)),
                "density": float(m.group(4)),
                "def_path": def_path
            }

        m = re.match(r'^(.+)_s(\d+)_d([\d.]+)\.def$', fname)
        if m:
            return {
                "design": m.group(1),
                "seed": m.group(2),
                "snapshot_threshold": "N/A",
                "aspect_ratio": 1.0,
                "utilization": 60.0,
                "density": float(m.group(3)),
                "def_path": def_path
            }

        return {
            "design": dir_design,
            "seed": "N/A",
            "snapshot_threshold": "N/A",
            "aspect_ratio": 1.0,
            "utilization": 60.0,
            "density": 0.6,
            "def_path": def_path
        }

    def discover_all_defs(self, include_swerv: bool = True) -> List[Dict[str, Any]]:
        search_paths = ["data/generated_defs/**/*.def"]
        if include_swerv:
            search_paths.append("data/generated_rtl_dataset/dataset/swerv/*.def")

        discovered = []
        for path_pattern in search_paths:
            for def_file in glob.glob(path_pattern, recursive=True):
                if os.path.basename(def_file) == "floorplan.def":
                    continue
                entry = self.parse_def_filename(def_file)
                entry["status"] = "Legal"
                entry["hpwl"] = "N/A"
                discovered.append(entry)
        return discovered

    def rebuild_summary_csv(self, include_swerv: bool = True) -> int:
        existing_map = {}
        if os.path.exists(self.summary_csv):
            with open(self.summary_csv, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_map[row["def_path"]] = row

        discovered = self.discover_all_defs(include_swerv=include_swerv)
        merged_entries = []
        seen_paths = set()

        for path, row in existing_map.items():
            merged_entries.append(row)
            seen_paths.add(path)

        new_count = 0
        for item in discovered:
            path = item["def_path"]
            if path not in seen_paths:
                merged_entries.append(item)
                seen_paths.add(path)
                new_count += 1

        os.makedirs(os.path.dirname(self.summary_csv), exist_ok=True)
        fieldnames = ['design', 'seed', 'snapshot_threshold', 'aspect_ratio', 'utilization', 'density', 'status', 'hpwl', 'def_path']
        with open(self.summary_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(merged_entries)

        print(f"Summary CSV rebuilt at '{self.summary_csv}': Total entries={len(merged_entries)} (Added {new_count} new DEFs)")
        return len(merged_entries)

    def find_lef_file(self, design: str) -> Optional[str]:
        candidates = [
            f"data/ispd_benchmarks/ispd2015/{design}/cells.lef",
            f"data/ispd_benchmarks/ispd2015/hidden/{design}/cells.lef",
            f"data/generated_rtl_dataset/{design}/cells.lef",
            f"data/generated_rtl_dataset/dataset/{design}/cells.lef",
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate

        matches = glob.glob(f"data/**/{design}/cells.lef", recursive=True)
        return matches[0] if matches else None

    def load_macro_data(self, designs: Set[str], area_threshold: float = 1000.0) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Parses LEFs to return macro dimensions and pin directions.
        Returns: {design: {cell_type: {width, height, area, aspect_ratio, pin_count, pins: {pin_name: direction}}}}
        """
        macro_map = {}
        for design in designs:
            lef_path = self.find_lef_file(design)
            design_data = {}
            if lef_path and os.path.exists(lef_path):
                current_macro = None
                with open(lef_path, 'r') as f:
                    for line in f:
                        line_str = line.strip()
                        if line_str.startswith('MACRO '):
                            parts = line_str.split()
                            if len(parts) >= 2:
                                current_macro = parts[1]
                                design_data[current_macro] = {
                                    'width': 0.0, 'height': 0.0, 'area': 0.0,
                                    'aspect_ratio': 0.0, 'pin_count': 0, 'pins': {}
                                }
                        elif current_macro:
                            if line_str.startswith('SIZE '):
                                m = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', line_str)
                                if m:
                                    w, h = float(m.group(1)), float(m.group(2))
                                    design_data[current_macro]['width'] = w
                                    design_data[current_macro]['height'] = h
                                    design_data[current_macro]['area'] = w * h
                                    design_data[current_macro]['aspect_ratio'] = w / h if h > 0 else 0
                            elif line_str.startswith('PIN '):
                                design_data[current_macro]['pin_count'] += 1
                                pin_name = line_str.split()[1] if len(line_str.split()) > 1 else "unknown"
                                design_data[current_macro]['pins'][pin_name] = 'INOUT' # Default
                            elif line_str.startswith('DIRECTION '):
                                dir_val = line_str.split()[1] if len(line_str.split()) > 1 else 'INOUT'
                                if design_data[current_macro]['pins']:
                                    last_pin = list(design_data[current_macro]['pins'].keys())[-1]
                                    design_data[current_macro]['pins'][last_pin] = dir_val
                            elif line_str.startswith('END ') and line_str.split()[-1] == current_macro:
                                if design_data[current_macro]['area'] < area_threshold:
                                    del design_data[current_macro]
                                current_macro = None
            macro_map[design] = design_data
        return macro_map

    def parse_def_components(self, def_path: str, macro_data: Optional[Dict[str, Dict]] = None) -> List[Dict[str, Any]]:
        components = []
        if not os.path.exists(def_path):
            return components

        in_components = False
        with open(def_path, 'r') as f:
            for line in f:
                line_str = line.strip()
                if line_str.startswith("COMPONENTS"):
                    in_components = True
                    continue
                elif line_str.startswith("END COMPONENTS"):
                    in_components = False
                    break

                if in_components and line_str.startswith("-"):
                    cell_match = re.match(r'^\s*-\s+(\S+)\s+(\S+)', line_str)
                    coord_match = re.search(r'\(\s*(-?\d+)\s+(-?\d+)\s*\)', line_str)

                    if cell_match and coord_match:
                        inst_name = cell_match.group(1)
                        cell_type = cell_match.group(2)

                        if macro_data is not None:
                            if cell_type not in macro_data:
                                continue
                            mdata = macro_data[cell_type]
                            components.append({
                                "inst_name": inst_name,
                                "cell_type": cell_type,
                                "target_x": int(coord_match.group(1)),
                                "target_y": int(coord_match.group(2)),
                                "width": mdata['width'],
                                "height": mdata['height'],
                                "area": mdata['area'],
                                "aspect_ratio": mdata['aspect_ratio'],
                                "pin_count": mdata['pin_count']
                            })
                        else:
                            components.append({
                                "inst_name": inst_name,
                                "cell_type": cell_type,
                                "target_x": int(coord_match.group(1)),
                                "target_y": int(coord_match.group(2)),
                                "width": float('nan'),
                                "height": float('nan'),
                                "area": float('nan'),
                                "aspect_ratio": float('nan'),
                                "pin_count": 0
                            })
        return components

    def parse_def_nets_kpath(self, def_path: str, macro_inst_names: Set[str], macro_data: Dict[str, Dict], max_kpath_depth: int = 4, max_fanout: int = 50) -> List[Dict[str, Any]]:
        """
        Uses sparse matrix exponentiation to extract k-path and undirected graph edges.
        """
        if not os.path.exists(def_path) or not macro_inst_names:
            return []

        # First pass: map instance names to integer IDs, counting total instances
        inst_to_id = {}
        total_insts = 0
        in_components = False
        with open(def_path, 'r') as f:
            for line in f:
                s = line.strip()
                if s.startswith("COMPONENTS"):
                    in_components = True
                elif s.startswith("END COMPONENTS"):
                    break
                elif in_components and s.startswith("-"):
                    cell_match = re.match(r'^\s*-\s+(\S+)\s+(\S+)', s)
                    if cell_match:
                        inst_name, cell_type = cell_match.group(1), cell_match.group(2)
                        inst_to_id[inst_name] = total_insts
                        total_insts += 1
                        
        if total_insts == 0:
            return []
            
        effective_depth = min(max_kpath_depth, 2) if total_insts > 1_000_000 else max_kpath_depth
        macro_ids = [inst_to_id[m] for m in macro_inst_names if m in inst_to_id]
        id_to_inst = {v: k for k, v in inst_to_id.items()}

        A_dir = dok_matrix((total_insts, total_insts), dtype=np.int32)
        A_undir = dok_matrix((total_insts, total_insts), dtype=np.int32)
        
        shared_pins = defaultdict(int)
        direct_net_count = defaultdict(int)
        total_nets = 0
        
        # Second pass: Process nets
        in_nets = False
        current_net_pins = []

        def _process_net():
            if not current_net_pins or len(current_net_pins) > max_fanout:
                return
                
            macro_hits = set([p[0] for p in current_net_pins]) & macro_inst_names
            if len(macro_hits) >= 2:
                for a, b in combinations(sorted(macro_hits), 2):
                    direct_net_count[(a, b)] += 1
                    shared_pins[(a, b)] += 1
                    
            # Build edges
            for src_inst, src_pin in current_net_pins:
                src_id = inst_to_id.get(src_inst)
                if src_id is None: continue
                for tgt_inst, tgt_pin in current_net_pins:
                    tgt_id = inst_to_id.get(tgt_inst)
                    if tgt_id is None or src_id == tgt_id: continue
                    
                    A_undir[src_id, tgt_id] = 1
                    
                    # Direction check (simplified if not in macro_data, assume standard cell flow)
                    # Without full standard cell LEF, we treat all connections outward from macros as directed
                    # If both are macros, we use LEF pin directions.
                    src_dir = 'INOUT'
                    if src_inst in macro_data and src_pin in macro_data[src_inst].get('pins', {}):
                        src_dir = macro_data[src_inst]['pins'][src_pin]
                        
                    tgt_dir = 'INOUT'
                    if tgt_inst in macro_data and tgt_pin in macro_data[tgt_inst].get('pins', {}):
                        tgt_dir = macro_data[tgt_inst]['pins'][tgt_pin]
                        
                    if (src_dir in ['OUTPUT', 'INOUT']) and (tgt_dir in ['INPUT', 'INOUT']):
                        A_dir[src_id, tgt_id] = 1

        with open(def_path, 'r') as f:
            for line in f:
                s = line.strip()
                if s.startswith("NETS "):
                    in_nets = True
                    continue
                if s.startswith("END NETS"):
                    _process_net()
                    break
                if not in_nets:
                    continue
                
                if s.startswith("- "):
                    _process_net()
                    current_net_pins = []
                    total_nets += 1
                    
                for match in re.finditer(r'\(\s*(\S+)\s+(\S+)\s*\)', s):
                    current_net_pins.append((match.group(1), match.group(2)))

        total_nets = max(total_nets, 1)

        # Convert to CSR for fast multiplication
        A_dir_csr = A_dir.tocsr()
        A_undir_csr = A_undir.tocsr()
        
        dir_powers = {1: A_dir_csr}
        curr_dir = A_dir_csr
        for k in range(2, effective_depth + 1):
            curr_dir = curr_dir.dot(A_dir_csr)
            dir_powers[k] = curr_dir
            
        edges_out = []
        macro_idx = sorted(macro_ids)
        for i, m1_id in enumerate(macro_idx):
            for j in range(i+1, len(macro_idx)):
                m2_id = macro_idx[j]
                m1_name, m2_name = id_to_inst[m1_id], id_to_inst[m2_id]
                
                # Must sort names to maintain consistent keys
                a, b = min(m1_name, m2_name), max(m1_name, m2_name)
                dnc = direct_net_count.get((a, b), 0)
                sp = shared_pins.get((a, b), 0)
                undir_1 = A_undir_csr[m1_id, m2_id] + A_undir_csr[m2_id, m1_id]
                
                if dnc == 0 and undir_1 == 0 and sp == 0:
                    continue # Skip fully disconnected pairs
                    
                edge_feat = {
                    "source_inst": a,
                    "target_inst": b,
                    "k_path_undir_1": undir_1,
                    "shared_pins": sp,
                    "net_density": dnc / total_nets,
                    "aux_3": 0.0, # BBox overlap stub
                    "aux_4": dnc
                }
                
                for k in range(1, 10):
                    if k <= effective_depth:
                        # Directed paths can go either way
                        edge_feat[f"k_path_dir_{k}"] = dir_powers[k][m1_id, m2_id] + dir_powers[k][m2_id, m1_id]
                    else:
                        edge_feat[f"k_path_dir_{k}"] = 0
                
                edges_out.append(edge_feat)

        return edges_out


    def _resolve_def_path(self, raw_def_path: str) -> Optional[str]:
        if os.path.isabs(raw_def_path):
            return raw_def_path if os.path.exists(raw_def_path) else None

        def_path = os.path.normpath(os.path.join(self.base_dir, raw_def_path))
        if os.path.exists(def_path):
            return def_path

        def_path = os.path.normpath(raw_def_path)
        return def_path if os.path.exists(def_path) else None


    def extract_all(
        self,
        output_parquet: str = "data/ml_features.parquet",
        edge_parquet: str = "data/edge_index.parquet",
        skip_illegal: bool = False,
        macro_only: bool = False,
        area_threshold: float = 1000.0,
        include_swerv: bool = True,
        rebuild_csv: bool = False,
        max_kpath_depth: int = 4,
        max_fanout: int = 50
    ) -> Tuple[str, str, str, str]:
        
        raw_coords_parquet = output_parquet.replace("ml_features.parquet", "raw_coords.parquet")
        pairwise_parquet = output_parquet.replace("ml_features.parquet", "pairwise_distances.parquet")

        if rebuild_csv or not os.path.exists(self.summary_csv):
            self.rebuild_summary_csv(include_swerv=include_swerv)

        df_summary = pd.read_csv(self.summary_csv)
        if df_summary.empty:
            raise ValueError(f"Summary CSV '{self.summary_csv}' is empty.")

        if skip_illegal and "status" in df_summary.columns:
            df_summary = df_summary[df_summary["status"] != "Illegal"]

        unique_designs = set(df_summary["design"].dropna().unique())
        macro_data_map = None
        if macro_only:
            print(f"Building LEF macro filter (area threshold >= {area_threshold} µm²)...")
            macro_data_map = self.load_macro_data(unique_designs, area_threshold=area_threshold)
            macro_counts = {d: len(m) for d, m in macro_data_map.items() if len(m) > 0}
            print(f"Macro cell types identified per design: {macro_counts}")

        node_dataset = []
        raw_coords_dataset = []
        pairwise_dataset = []
        edge_dataset = []
        files_processed = 0
        files_missing = 0

        print(f"\nExtracting {'macro' if macro_only else 'all'} features from {len(df_summary)} layout DEFs...")
        for _, row in tqdm(df_summary.iterrows(), total=len(df_summary), desc="Processing DEFs"):
            def_path = self._resolve_def_path(row["def_path"])
            if def_path is None:
                files_missing += 1
                continue

            design_name = str(row["design"])
            m_data = macro_data_map.get(design_name) if macro_data_map else None
            
            die_diag = get_die_diagonal(def_path)

            components = self.parse_def_components(def_path, macro_data=m_data)
            files_processed += 1

            row_meta = {
                "design": design_name,
                "seed": str(row.get("seed", "N/A")),
                "snapshot_threshold": str(row.get("snapshot_threshold", "N/A")),
                "ar_param": float(row["aspect_ratio"]),
                "utilization": float(row["utilization"]),
                "density": float(row["density"]),
                "status": str(row.get("status", "Legal")),
            }

            coords_for_pdist = []
            inst_names_for_pdist = []

            for comp in components:
                record = {**row_meta}
                record["inst_name"] = comp["inst_name"]
                record["width"] = comp["width"]
                record["height"] = comp["height"]
                record["area"] = comp["area"]
                record["aspect_ratio"] = comp["aspect_ratio"]
                record["pin_count"] = comp["pin_count"]
                
                # PPA stubs
                record["HPWL"] = float('nan')
                record["routing_congestion"] = float('nan')
                record["WNS"] = float('nan')
                record["TNS"] = float('nan')
                
                node_dataset.append(record)
                
                raw_coords_dataset.append({
                    "design": design_name,
                    "seed": str(row.get("seed", "N/A")),
                    "inst_name": comp["inst_name"],
                    "cell_type": comp["cell_type"],
                    "target_x": comp["target_x"],
                    "target_y": comp["target_y"]
                })
                
                coords_for_pdist.append([comp["target_x"], comp["target_y"]])
                inst_names_for_pdist.append(comp["inst_name"])

            if macro_only and len(coords_for_pdist) > 1:
                dist_matrix = squareform(pdist(coords_for_pdist, metric='euclidean'))
                for i in range(len(inst_names_for_pdist)):
                    for j in range(i + 1, len(inst_names_for_pdist)):
                        inst_i, inst_j = inst_names_for_pdist[i], inst_names_for_pdist[j]
                        a, b = min(inst_i, inst_j), max(inst_i, inst_j)
                        d = dist_matrix[i, j]
                        pairwise_dataset.append({
                            "design": design_name,
                            "seed": str(row.get("seed", "N/A")),
                            "inst_i": a,
                            "inst_j": b,
                            "raw_dist": float(d),
                            "dist_norm": float(d / die_diag)
                        })

            if components and macro_only:
                macro_inst_names = {c["inst_name"] for c in components}
                # Create macro_data lookup by instance name
                inst_macro_data = {c["inst_name"]: m_data[c["cell_type"]] for c in components} if m_data else {}
                
                edges = self.parse_def_nets_kpath(def_path, macro_inst_names, inst_macro_data, max_kpath_depth, max_fanout)
                for edge in edges:
                    e_rec = {"design": design_name, **edge}
                    edge_dataset.append(e_rec)

        os.makedirs(os.path.dirname(os.path.abspath(output_parquet)), exist_ok=True)

        def write_parquet(df, path, cat_cols=None):
            if df.empty:
                df.to_parquet(path, engine="pyarrow", compression="snappy", index=False)
                return 0.0
            if cat_cols:
                for col in cat_cols:
                    if col in df.columns:
                        df[col] = df[col].astype("category")
            df.to_parquet(path, engine="pyarrow", compression="snappy", index=False)
            return os.path.getsize(path) / (1024 * 1024)

        df_nodes = pd.DataFrame(node_dataset)
        if df_nodes.empty:
            df_nodes = pd.DataFrame(columns=["inst_name", "width", "height", "area", "aspect_ratio", "pin_count", "design", "seed", "snapshot_threshold", "ar_param", "utilization", "density", "status", "HPWL", "routing_congestion", "WNS", "TNS"])
        node_size_mb = write_parquet(df_nodes, output_parquet, ["design", "seed", "snapshot_threshold", "status"])

        df_raw = pd.DataFrame(raw_coords_dataset)
        if df_raw.empty:
            df_raw = pd.DataFrame(columns=["design", "seed", "inst_name", "cell_type", "target_x", "target_y"])
        write_parquet(df_raw, raw_coords_parquet, ["design", "seed"])

        df_pair = pd.DataFrame(pairwise_dataset)
        if df_pair.empty:
            df_pair = pd.DataFrame(columns=["design", "seed", "inst_i", "inst_j", "raw_dist", "dist_norm"])
        write_parquet(df_pair, pairwise_parquet, ["design", "seed"])

        df_edges = pd.DataFrame(edge_dataset)
        if df_edges.empty:
            df_edges = pd.DataFrame(columns=[
                "design", "source_inst", "target_inst", "k_path_dir_1", "k_path_dir_2", "k_path_dir_3", 
                "k_path_dir_4", "k_path_dir_5", "k_path_dir_6", "k_path_dir_7", "k_path_dir_8", "k_path_dir_9", 
                "k_path_undir_1", "shared_pins", "net_density", "aux_3", "aux_4"
            ])
        edge_size_mb = write_parquet(df_edges, edge_parquet, ["design"])

        print("\n================ Extraction Summary ================")
        print(f"Processed DEFs:       {files_processed} successfully ({files_missing} missing)")
        print(f"Node Parquet:         {output_parquet} ({node_size_mb:.2f} MB)")
        print(f"Edge Parquet:         {edge_parquet} ({edge_size_mb:.4f} MB)")
        print(f"Pairwise Parquet:     {pairwise_parquet}")
        print(f"Raw Coords Parquet:   {raw_coords_parquet}")
        print("====================================================\n")

        return output_parquet, edge_parquet, pairwise_parquet, raw_coords_parquet


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary_csv", default="data/generated_defs/dataset_summary.csv")
    parser.add_argument("--output_parquet", default="data/ml_features.parquet")
    parser.add_argument("--edge_parquet", default="data/edge_index.parquet")
    parser.add_argument("--skip_illegal", action="store_true")
    parser.add_argument("--rebuild_csv", action="store_true")
    parser.add_argument("--include_swerv", action="store_true")
    parser.add_argument("--macro_only", action="store_true")
    parser.add_argument("--area_threshold", type=float, default=1000.0)
    parser.add_argument("--max_kpath_depth", type=int, default=4)
    parser.add_argument("--max_fanout", type=int, default=50)

    args = parser.parse_args()

    extractor = FeatureExtractor(summary_csv=args.summary_csv)
    extractor.extract_all(
        output_parquet=args.output_parquet,
        edge_parquet=args.edge_parquet,
        skip_illegal=args.skip_illegal,
        macro_only=args.macro_only,
        area_threshold=args.area_threshold,
        include_swerv=args.include_swerv,
        rebuild_csv=args.rebuild_csv,
        max_kpath_depth=args.max_kpath_depth,
        max_fanout=args.max_fanout
    )
