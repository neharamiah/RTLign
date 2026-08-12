#!/usr/bin/env python3
"""
Feature Extractor for RTLign ML Predictor Pipeline

Bridges OpenROAD physical design sweeps with PyTorch / PyTorch Geometric ML
pipelines by parsing DEF layout files to extract:
  - Node features: macro/component placement coordinates (COMPONENTS section)
  - Edge connectivity: macro-to-macro wiring topology (NETS section)

Outputs two snappy-compressed Parquet datasets:
  - ml_features.parquet      — node feature matrix
  - edge_index.parquet       — weighted adjacency list for GNN message passing
"""

import os
import re
import glob
import csv
import argparse
from typing import List, Dict, Any, Set, Optional, Tuple
from collections import defaultdict
from itertools import combinations
import pandas as pd
from tqdm import tqdm


class FeatureExtractor:
    """
    Extracts placement features, target macro coordinates, and inter-macro wiring
    connectivity from OpenROAD DEF layouts and library LEFs to build ML training
    datasets for both MLP and GNN architectures.
    """

    def __init__(self, summary_csv: str = "data/generated_defs/dataset_summary.csv"):
        self.summary_csv = summary_csv
        self.base_dir = os.path.dirname(os.path.abspath(summary_csv))

    # ──────────────────────────────────────────────────────────────────────────
    # Filename Parsing
    # ──────────────────────────────────────────────────────────────────────────

    def parse_def_filename(self, def_path: str) -> Dict[str, Any]:
        """
        Parses physical design constraints and parameters from a DEF filename.

        Handles:
        1. RTL sweep format: {design}_s{seed}_t{threshold}_ar{ar}_u{util}_d{density}.def
        2. ISPD/SweRV format: {design}_ar{ar}_u{util}_d{density}.def
        3. Seed+Density format: {design}_s{seed}_d{density}.def
        4. Fallback default parsing
        """
        fname = os.path.basename(def_path)
        dir_design = os.path.basename(os.path.dirname(def_path))

        # 1. RTL sweep pattern
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

        # 2. ISPD/SweRV pattern
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

        # 3. Seed + Density pattern
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

        # Fallback
        return {
            "design": dir_design,
            "seed": "N/A",
            "snapshot_threshold": "N/A",
            "aspect_ratio": 1.0,
            "utilization": 60.0,
            "density": 0.6,
            "def_path": def_path
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Directory Discovery & CSV Rebuilding
    # ──────────────────────────────────────────────────────────────────────────

    def discover_all_defs(self, include_swerv: bool = True) -> List[Dict[str, Any]]:
        """Scans workspace directories to discover all generated DEF files."""
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
        """
        Rebuilds or extends dataset_summary.csv to ensure all discovered DEFs are cataloged.
        Preserves existing metadata (status, hpwl) if present.
        """
        existing_map = {}
        if os.path.exists(self.summary_csv):
            with open(self.summary_csv, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_map[row["def_path"]] = row

        discovered = self.discover_all_defs(include_swerv=include_swerv)
        merged_entries = []
        seen_paths = set()

        # Update existing records
        for path, row in existing_map.items():
            merged_entries.append(row)
            seen_paths.add(path)

        # Append newly discovered records
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

    # ──────────────────────────────────────────────────────────────────────────
    # LEF Parsing — Macro Cell Type Identification
    # ──────────────────────────────────────────────────────────────────────────

    def find_lef_file(self, design: str) -> Optional[str]:
        """Locates the corresponding LEF file for a given design name."""
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

    def load_macro_filter(self, designs: Set[str], area_threshold: float = 1000.0) -> Dict[str, Set[str]]:
        """
        Parses cell libraries (LEF files) for the specified designs to identify macro/large-block
        cell types exceeding the area threshold (in LEF square microns/units).
        """
        macro_map = {}
        for design in designs:
            lef_path = self.find_lef_file(design)
            macro_cells = set()
            if lef_path and os.path.exists(lef_path):
                current_macro = None
                with open(lef_path, 'r') as f:
                    for line in f:
                        line_str = line.strip()
                        if line_str.startswith('MACRO '):
                            parts = line_str.split()
                            if len(parts) >= 2:
                                current_macro = parts[1]
                        elif line_str.startswith('SIZE ') and current_macro:
                            m = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', line_str)
                            if m:
                                w = float(m.group(1))
                                h = float(m.group(2))
                                if w * h >= area_threshold:
                                    macro_cells.add(current_macro)
                        elif line_str.startswith('END ') and current_macro:
                            if line_str.split()[-1] == current_macro:
                                current_macro = None
            macro_map[design] = macro_cells
        return macro_map

    # ──────────────────────────────────────────────────────────────────────────
    # DEF COMPONENTS Parsing — Node Features
    # ──────────────────────────────────────────────────────────────────────────

    def parse_def_components(self, def_path: str, macro_filter: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
        """
        Parses the COMPONENTS section of a DEF file and returns placed cell instances.
        If macro_filter is supplied, only instances matching macro cell types are returned.
        """
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

                        if macro_filter is not None and cell_type not in macro_filter:
                            continue

                        x_coord = int(coord_match.group(1))
                        y_coord = int(coord_match.group(2))

                        components.append({
                            "inst_name": inst_name,
                            "cell_type": cell_type,
                            "target_x": x_coord,
                            "target_y": y_coord
                        })

        return components

    # ──────────────────────────────────────────────────────────────────────────
    # DEF NETS Parsing — Edge Connectivity for GNN
    # ──────────────────────────────────────────────────────────────────────────

    def parse_def_nets(self, def_path: str, macro_inst_names: Set[str]) -> Dict[Tuple[str, str], int]:
        """
        Parses the NETS section of a DEF file and extracts macro-to-macro connectivity.

        For each net, identifies which connected instances are macros. If a net connects
        two or more macros, creates pairwise undirected edges between them. Edge weights
        are aggregated across all nets (weight = number of shared nets between a pair).

        Args:
            def_path: Path to the DEF file.
            macro_inst_names: Set of instance names identified as macros from COMPONENTS.

        Returns:
            Dictionary mapping (source_inst, target_inst) tuples (sorted alphabetically)
            to their aggregated shared-net weight.
        """
        edge_counts: Dict[Tuple[str, str], int] = defaultdict(int)

        if not os.path.exists(def_path) or not macro_inst_names:
            return dict(edge_counts)

        in_nets = False
        current_net_insts: Set[str] = set()

        def _flush_net():
            """Process accumulated net instances and record macro-macro edges."""
            macro_hits = current_net_insts & macro_inst_names
            if len(macro_hits) >= 2:
                for a, b in combinations(sorted(macro_hits), 2):
                    edge_counts[(a, b)] += 1

        with open(def_path, 'r') as f:
            for line in f:
                stripped = line.strip()

                if stripped.startswith("NETS "):
                    in_nets = True
                    continue
                if stripped.startswith("END NETS"):
                    # Flush the last net before exiting
                    _flush_net()
                    break
                if not in_nets:
                    continue

                # New net definition starts with "- net_name"
                if stripped.startswith("- "):
                    # Flush previous net
                    _flush_net()
                    current_net_insts = set()

                # Extract all ( inst_name pin_name ) connection pairs from this line
                for match in re.finditer(r'\(\s*(\S+)\s+\S+\s*\)', stripped):
                    current_net_insts.add(match.group(1))

        return dict(edge_counts)

    # ──────────────────────────────────────────────────────────────────────────
    # DEF Path Resolution Helper
    # ──────────────────────────────────────────────────────────────────────────

    def _resolve_def_path(self, raw_def_path: str) -> Optional[str]:
        """Resolves a DEF path from the CSV (possibly relative) to an absolute path."""
        if os.path.isabs(raw_def_path):
            return raw_def_path if os.path.exists(raw_def_path) else None

        # Try relative to CSV directory first
        def_path = os.path.normpath(os.path.join(self.base_dir, raw_def_path))
        if os.path.exists(def_path):
            return def_path

        # Try relative to CWD
        def_path = os.path.normpath(raw_def_path)
        return def_path if os.path.exists(def_path) else None

    # ──────────────────────────────────────────────────────────────────────────
    # Main Extraction Orchestrators
    # ──────────────────────────────────────────────────────────────────────────

    def extract_all(
        self,
        output_parquet: str = "data/ml_features.parquet",
        edge_parquet: str = "data/edge_index.parquet",
        skip_illegal: bool = False,
        macro_only: bool = False,
        area_threshold: float = 1000.0,
        include_swerv: bool = True,
        rebuild_csv: bool = False
    ) -> Tuple[str, str]:
        """
        Extracts placement node features and inter-macro edge connectivity,
        exporting both to snappy-compressed Parquet files.

        Returns:
            Tuple of (node_parquet_path, edge_parquet_path).
        """
        if rebuild_csv or not os.path.exists(self.summary_csv):
            self.rebuild_summary_csv(include_swerv=include_swerv)

        df_summary = pd.read_csv(self.summary_csv)
        if df_summary.empty:
            raise ValueError(f"Summary CSV '{self.summary_csv}' is empty.")

        if skip_illegal and "status" in df_summary.columns:
            df_summary = df_summary[df_summary["status"] != "Illegal"]

        # Build macro filter from LEF files
        unique_designs = set(df_summary["design"].dropna().unique())
        macro_map = None
        if macro_only:
            print(f"Building LEF macro filter (area threshold >= {area_threshold} µm²)...")
            macro_map = self.load_macro_filter(unique_designs, area_threshold=area_threshold)
            macro_counts = {d: len(m) for d, m in macro_map.items() if len(m) > 0}
            print(f"Macro cell types identified per design: {macro_counts}")

        # Accumulators
        node_dataset: List[Dict[str, Any]] = []
        edge_dataset: List[Dict[str, Any]] = []
        files_processed = 0
        files_missing = 0
        total_edges = 0

        print(f"\nExtracting {'macro' if macro_only else 'all'} features from {len(df_summary)} layout DEFs...")
        for _, row in tqdm(df_summary.iterrows(), total=len(df_summary), desc="Processing DEFs"):
            def_path = self._resolve_def_path(row["def_path"])
            if def_path is None:
                files_missing += 1
                continue

            design_name = str(row["design"])
            filter_set = macro_map.get(design_name) if macro_map else None

            # ── Phase 1: Parse COMPONENTS (node features) ──
            components = self.parse_def_components(def_path, macro_filter=filter_set)
            files_processed += 1

            # Build row metadata shared across all components in this DEF
            row_meta = {
                "design": design_name,
                "seed": str(row.get("seed", "N/A")),
                "snapshot_threshold": str(row.get("snapshot_threshold", "N/A")),
                "aspect_ratio": float(row["aspect_ratio"]),
                "utilization": float(row["utilization"]),
                "density": float(row["density"]),
                "status": str(row.get("status", "Legal")),
            }

            for comp in components:
                record = {**row_meta}
                record["inst_name"] = comp["inst_name"]
                record["cell_type"] = comp["cell_type"]
                record["target_x"] = comp["target_x"]
                record["target_y"] = comp["target_y"]
                node_dataset.append(record)

            # ── Phase 2: Parse NETS (edge connectivity) ──
            # Only extract edges when macros were found in this DEF
            if components and macro_only:
                macro_inst_names = {c["inst_name"] for c in components}
                edges = self.parse_def_nets(def_path, macro_inst_names)
                for (src, tgt), weight in edges.items():
                    edge_dataset.append({
                        "design": design_name,
                        "source_inst": src,
                        "target_inst": tgt,
                        "weight": weight,
                    })
                    total_edges += 1

        # ── Write Node Features Parquet ──
        if not node_dataset:
            print("Warning: No matching components extracted!")
        else:
            print(f"\nConstructing node DataFrame with {len(node_dataset):,} rows...")
            df_nodes = pd.DataFrame(node_dataset)

            cat_cols = ["design", "seed", "snapshot_threshold", "status", "cell_type"]
            for col in cat_cols:
                if col in df_nodes.columns:
                    df_nodes[col] = df_nodes[col].astype("category")

            os.makedirs(os.path.dirname(os.path.abspath(output_parquet)), exist_ok=True)
            df_nodes.to_parquet(output_parquet, engine="pyarrow", compression="snappy", index=False)
            node_size_mb = os.path.getsize(output_parquet) / (1024 * 1024)
        
        # ── Write Edge Index Parquet ──
        if not edge_dataset:
            print("Note: No macro-macro edges found (edge_index.parquet will not be created).")
            edge_size_mb = 0.0
        else:
            print(f"Constructing edge DataFrame with {len(edge_dataset):,} rows...")
            df_edges = pd.DataFrame(edge_dataset)
            df_edges["design"] = df_edges["design"].astype("category")
            df_edges["weight"] = df_edges["weight"].astype("int64")

            os.makedirs(os.path.dirname(os.path.abspath(edge_parquet)), exist_ok=True)
            df_edges.to_parquet(edge_parquet, engine="pyarrow", compression="snappy", index=False)
            edge_size_mb = os.path.getsize(edge_parquet) / (1024 * 1024)

        # ── Summary ──
        print("\n================ Extraction Summary ================")
        print(f"Processed DEFs:       {files_processed} successfully ({files_missing} missing)")
        if node_dataset:
            print(f"Node Rows Extracted:  {len(node_dataset):,}")
            print(f"Node Parquet:         {output_parquet} ({node_size_mb:.2f} MB)")
        if edge_dataset:
            print(f"Edge Rows Extracted:  {len(edge_dataset):,}")
            print(f"Edge Parquet:         {edge_parquet} ({edge_size_mb:.4f} MB)")
        print("====================================================\n")

        return output_parquet, edge_parquet


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Bridge OpenROAD physical design sweeps with PyTorch / PyTorch Geometric ML pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract macro nodes + edges for GNN training:
  python ml_predictor/feature_extractor.py --macro_only --rebuild_csv --include_swerv

  # Extract all components (standard cells + macros), no edge extraction:
  python ml_predictor/feature_extractor.py --output_parquet data/ml_features_all.parquet
        """
    )
    parser.add_argument("--summary_csv", default="data/generated_defs/dataset_summary.csv",
                        help="Path to summary CSV index file")
    parser.add_argument("--output_parquet", default="data/ml_features.parquet",
                        help="Path to output node features Parquet dataset")
    parser.add_argument("--edge_parquet", default="data/edge_index.parquet",
                        help="Path to output edge connectivity Parquet dataset")
    parser.add_argument("--skip_illegal", action="store_true",
                        help="Skip designs with status 'Illegal'")
    parser.add_argument("--rebuild_csv", action="store_true",
                        help="Auto-discover all generated DEFs and update dataset_summary.csv")
    parser.add_argument("--include_swerv", action="store_true",
                        help="Include SweRV DEFs during directory scanning")
    parser.add_argument("--macro_only", action="store_true",
                        help="Filter and extract macro instances only (ignoring standard logic cells)")
    parser.add_argument("--area_threshold", type=float, default=1000.0,
                        help="Min LEF area threshold for macro classification (default: 1000.0 µm²)")

    args = parser.parse_args()

    extractor = FeatureExtractor(summary_csv=args.summary_csv)
    extractor.extract_all(
        output_parquet=args.output_parquet,
        edge_parquet=args.edge_parquet,
        skip_illegal=args.skip_illegal,
        macro_only=args.macro_only,
        area_threshold=args.area_threshold,
        include_swerv=args.include_swerv,
        rebuild_csv=args.rebuild_csv
    )
