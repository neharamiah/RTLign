import os
import torch
import joblib
import pandas as pd
import numpy as np
from torch_geometric.data import InMemoryDataset, Data
from sklearn.preprocessing import StandardScaler

class TopologicalMacroDataset(InMemoryDataset):
    def __init__(self, root, transform=None, pre_transform=None):
        super().__init__(root, transform, pre_transform)
        self.data, self.slices = torch.load(self.processed_paths[0], weights_only=False)

    @property
    def raw_file_names(self):
        return ['ml_features.parquet', 'edge_index.parquet', 'pairwise_distances.parquet']

    @property
    def processed_file_names(self):
        return ['data.pt']

    def download(self):
        # Data is assumed to be present in self.raw_dir (which is 'data/raw' by default PyG convention)
        pass

    def process(self):
        # Load parquets. By default root='data', raw_dir='data/raw'
        # But user stores them directly in 'data/'. So we might need to override raw_dir.
        raw_dir = self.root # override or just use self.root since we want to read from 'data'
        ml_features = pd.read_parquet(os.path.join(raw_dir, 'ml_features.parquet'))
        edge_index_df = pd.read_parquet(os.path.join(raw_dir, 'edge_index.parquet'))
        pairwise_dist = pd.read_parquet(os.path.join(raw_dir, 'pairwise_distances.parquet'))

        # 1. Process node features globally
        node_feature_cols = ['width', 'height', 'area', 'aspect_ratio', 'pin_count']
        scaler = StandardScaler()
        ml_features[node_feature_cols] = scaler.fit_transform(ml_features[node_feature_cols])
        joblib.dump(scaler, os.path.join(raw_dir, 'node_scaler.joblib'))

        # 2. Build pairwise distances dictionary for fast lookup
        # Key: (design, min(inst1, inst2), max(inst1, inst2)) -> Value: (dist_norm, raw_dist)
        dist_dict = {}
        for _, row in pairwise_dist.iterrows():
            design = row['design']
            inst_i = row['inst_i']
            inst_j = row['inst_j']
            key = (design, min(inst_i, inst_j), max(inst_i, inst_j))
            dist_dict[key] = (row['dist_norm'], row['raw_dist'])

        # Edge feature columns
        edge_feature_cols = [
            'k_path_undir_1', 'shared_pins', 'net_density', 'aux_3', 'aux_4',
            'k_path_dir_1', 'k_path_dir_2', 'k_path_dir_3', 'k_path_dir_4',
            'k_path_dir_5', 'k_path_dir_6', 'k_path_dir_7', 'k_path_dir_8', 'k_path_dir_9'
        ]
        
        # Scale edge features globally
        edge_scaler = StandardScaler()
        edge_index_df[edge_feature_cols] = edge_scaler.fit_transform(edge_index_df[edge_feature_cols])
        joblib.dump(edge_scaler, os.path.join(raw_dir, 'edge_scaler.joblib'))

        data_list = []
        
        # Group by design
        grouped_features = ml_features.groupby('design')
        grouped_edges = edge_index_df.groupby('design')

        for design, node_df in grouped_features:
            if design not in grouped_edges.groups:
                continue
                
            edge_df = grouped_edges.get_group(design)
            
            if len(edge_df) == 0:
                continue

            # Create node index mapping
            node_df = node_df.reset_index(drop=True)
            inst_name_to_idx = {name: idx for idx, name in enumerate(node_df['inst_name'])}

            # Node features tensor
            x = torch.tensor(node_df[node_feature_cols].values, dtype=torch.float32)

            # Edge index and attributes
            source_indices = []
            target_indices = []
            edge_attrs = []
            targets_norm = []
            targets_raw = []

            for _, row in edge_df.iterrows():
                src = row['source_inst']
                tgt = row['target_inst']
                
                if src not in inst_name_to_idx or tgt not in inst_name_to_idx:
                    continue
                    
                src_idx = inst_name_to_idx[src]
                tgt_idx = inst_name_to_idx[tgt]
                
                # Lookup distance
                key = (design, min(src, tgt), max(src, tgt))
                if key in dist_dict:
                    d_norm, d_raw = dist_dict[key]
                    
                    source_indices.append(src_idx)
                    target_indices.append(tgt_idx)
                    edge_attrs.append(row[edge_feature_cols].values.astype(np.float32))
                    targets_norm.append(d_norm)
                    targets_raw.append(d_raw)

            if len(source_indices) == 0:
                continue

            edge_index = torch.tensor([source_indices, target_indices], dtype=torch.long)
            edge_attr = torch.tensor(np.array(edge_attrs), dtype=torch.float32)
            y = torch.tensor(targets_norm, dtype=torch.float32).unsqueeze(-1)
            raw_y = torch.tensor(targets_raw, dtype=torch.float32).unsqueeze(-1)

            # Create PyG Data object
            data = Data(x=x, edge_index=edge_index, edge_attr=edge_attr, y=y, design=design, raw_y=raw_y)
            data_list.append(data)

        if self.pre_filter is not None:
            data_list = [data for data in data_list if self.pre_filter(data)]

        if self.pre_transform is not None:
            data_list = [self.pre_transform(data) for data in data_list]

        data, slices = self.collate(data_list)
        torch.save((data, slices), self.processed_paths[0])

if __name__ == "__main__":
    dataset = TopologicalMacroDataset(root="data")
    print(f"Dataset size: {len(dataset)}")
    if len(dataset) > 0:
        print(f"First graph: {dataset[0]}")
