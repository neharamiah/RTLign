import os
import csv
from typing import List, Dict, Any, Tuple

class FeatureExtractor:
    """
    Extracts features and target macro placement coordinates from benchmark DEFs and LEFs
    to construct dataset tables for ML predictor training.
    """
    
    def __init__(self, summary_csv: str):
        self.summary_csv = summary_csv

    def load_dataset_summary(self, include_illegal: bool = True) -> List[Dict[str, str]]:
        """Loads entries from dataset_summary.csv, optionally filtering out failed runs."""
        entries = []
        if not os.path.exists(self.summary_csv):
            raise FileNotFoundError(f"Summary CSV not found: {self.summary_csv}")
            
        with open(self.summary_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                status = row.get("status", "")
                if status == "Legal" or (include_illegal and status == "Illegal"):
                    entries.append(row)
        return entries

    def parse_def_macros(self, def_path: str) -> List[Dict[str, Any]]:
        """Extracts macro instances and their placement coordinates from a DEF file."""
        macros = []
        if not os.path.exists(def_path):
            return macros
            
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
                    parts = line_str.split()
                    if len(parts) >= 6:
                        inst_name = parts[1]
                        cell_type = parts[2]
                        # Look for placement status e.g. ( X Y )
                        if "(" in parts and ")" in parts:
                            idx_open = parts.index("(")
                            x_coord = int(parts[idx_open + 1])
                            y_coord = int(parts[idx_open + 2])
                            macros.append({
                                "inst_name": inst_name,
                                "cell_type": cell_type,
                                "x": x_coord,
                                "y": y_coord
                            })
        return macros

    def extract_features(self, include_illegal: bool = True) -> List[Dict[str, Any]]:
        """Builds a dataset matrix containing features and target coordinates."""
        dataset = []
        entries = self.load_dataset_summary(include_illegal=include_illegal)
        
        for entry in entries:
            def_path = entry["def_path"]
            macros = self.parse_def_macros(def_path)
            
            for macro in macros:
                row_data = {
                    "design": entry["design"],
                    "aspect_ratio": float(entry["aspect_ratio"]),
                    "utilization": float(entry["utilization"]),
                    "density": float(entry["density"]),
                    "status": entry["status"],
                    "inst_name": macro["inst_name"],
                    "cell_type": macro["cell_type"],
                    "target_x": macro["x"],
                    "target_y": macro["y"]
                }
                dataset.append(row_data)
                
        return dataset

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract features for ML predictor training.")
    parser.add_argument("--summary_csv", default="data/generated_defs/dataset_summary.csv", help="Path to summary CSV")
    parser.add_argument("--output_csv", default="data/ml_features.csv", help="Output CSV path")
    parser.add_argument("--include_illegal", action="store_true", default=True, help="Include illegal placements")
    args = parser.parse_args()
    
    extractor = FeatureExtractor(args.summary_csv)
    print(f"Extracting features from {args.summary_csv}...")
    dataset = extractor.extract_features(include_illegal=args.include_illegal)
    
    if dataset:
        fieldnames = list(dataset[0].keys())
        os.makedirs(os.path.dirname(args.output_csv), exist_ok=True)
        with open(args.output_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(dataset)
        print(f"Successfully extracted {len(dataset)} samples to {args.output_csv}")
    else:
        print("No valid samples extracted.")
