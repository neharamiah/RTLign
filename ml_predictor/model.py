import torch
import torch.nn as nn
from torch_geometric.nn import GATv2Conv

class TopologicalMacroGNN(nn.Module):
    def __init__(self, node_in_channels=5, edge_in_channels=14, hidden_channels=128):
        super().__init__()
        
        # 1. Node and Edge Encoders
        self.node_encoder = nn.Sequential(
            nn.Linear(node_in_channels, hidden_channels),
            nn.ReLU(),
            nn.Linear(hidden_channels, hidden_channels)
        )
        
        self.edge_encoder = nn.Sequential(
            nn.Linear(edge_in_channels, hidden_channels),
            nn.ReLU(),
            nn.Linear(hidden_channels, hidden_channels)
        )
        
        # 2. GNN Backbone (GATv2)
        # Using 2 layers of GATv2 with edge_dim
        self.conv1 = GATv2Conv(hidden_channels, hidden_channels, edge_dim=hidden_channels, add_self_loops=False)
        self.conv2 = GATv2Conv(hidden_channels, hidden_channels, edge_dim=hidden_channels, add_self_loops=False)
        
        self.dropout = nn.Dropout(p=0.1)
        
        # 3. Edge Distance Predictor
        # Input to MLP will be [h_i || h_j || e_{ij}] -> 3 * hidden_channels
        self.predictor = nn.Sequential(
            nn.Linear(3 * hidden_channels, hidden_channels),
            nn.ReLU(),
            nn.Linear(hidden_channels, hidden_channels // 2),
            nn.ReLU(),
            nn.Linear(hidden_channels // 2, 1)
        )
        
        nn.init.normal_(self.predictor[-1].weight, std=0.01)
        nn.init.zeros_(self.predictor[-1].bias)

    def forward(self, x, edge_index, edge_attr):
        """
        x: [N, node_in_channels]
        edge_index: [2, E]
        edge_attr: [E, edge_in_channels]
        """
        # Encode nodes and edges
        x = self.node_encoder(x)
        edge_attr_emb = self.edge_encoder(edge_attr)
        
        # GNN Layer 1
        h_gat1 = self.conv1(x, edge_index, edge_attr=edge_attr_emb)
        x = x + h_gat1
        x = torch.relu(x)
        x = self.dropout(x)
        
        # GNN Layer 2
        h_gat2 = self.conv2(x, edge_index, edge_attr=edge_attr_emb)
        x = x + h_gat2
        
        # Edge predictions
        # Extract embeddings for source and target nodes of each edge
        src_nodes = x[edge_index[0]]
        tgt_nodes = x[edge_index[1]]
        
        # Concatenate [h_i || h_j || e_{ij}]
        edge_repr = torch.cat([src_nodes, tgt_nodes, edge_attr_emb], dim=1)
        
        # Predict dist_norm
        dist_norm_pred = self.predictor(edge_repr)
        dist_norm_pred = torch.clamp(dist_norm_pred, 0.0, 1.0)
        
        return dist_norm_pred
