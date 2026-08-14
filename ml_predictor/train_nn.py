import os
import sys
import subprocess

def check_dependencies():
    try:
        import torch
        import torch_geometric
        import sklearn
        import pandas
        import pyarrow
    except ImportError:
        print("Missing dependencies. Installing via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "torch", "torch-geometric", "scikit-learn", "pandas", "pyarrow"])
        print("Dependencies installed successfully.")

check_dependencies()

import torch
import torch.nn as nn
from torch_geometric.loader import DataLoader
from sklearn.model_selection import train_test_split
from dataset import TopologicalMacroDataset
from model import TopologicalMacroGNN

def train():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    # Load dataset
    print("Loading dataset...")
    dataset = TopologicalMacroDataset(root="data")
    print(f"Total graphs loaded: {len(dataset)}")

    if len(dataset) == 0:
        print("No data available.")
        return

    # Split dataset 80/20 by unique design
    designs = [data.design for data in dataset]
    unique_designs = list(set(designs))
    
    train_designs, val_designs = train_test_split(unique_designs, test_size=0.2, random_state=42)
    
    train_dataset = [data for data in dataset if data.design in train_designs]
    val_dataset = [data for data in dataset if data.design in val_designs]
    
    print(f"Train graphs: {len(train_dataset)}, Validation graphs: {len(val_dataset)}")

    train_loader = DataLoader(train_dataset, batch_size=4, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=4, shuffle=False)

    # Initialize model
    model = TopologicalMacroGNN(hidden_channels=128).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=100)
    criterion = nn.L1Loss()

    best_val_loss = float('inf')
    num_epochs = 100

    for epoch in range(num_epochs):
        model.train()
        total_loss = 0
        total_mae_norm = 0
        total_mae_denorm = 0
        total_edges = 0

        for data in train_loader:
            data = data.to(device)
            optimizer.zero_grad()
            
            out = model(data.x, data.edge_index, data.edge_attr)
            loss = criterion(out, data.y)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item() * data.num_edges
            
            with torch.no_grad():
                mae_norm = torch.abs(out - data.y)
                total_mae_norm += mae_norm.sum().item()
                
                # Compute denormalized MAE
                # true_die_diag = raw_dist / dist_norm (where dist_norm > 0)
                # mask for valid normalization
                valid_mask = (data.y > 0).view(-1)
                if valid_mask.sum() > 0:
                    true_die_diag = data.raw_y[valid_mask] / data.y[valid_mask]
                    mae_denorm = mae_norm[valid_mask] * true_die_diag
                    total_mae_denorm += mae_denorm.sum().item()
                
            total_edges += data.num_edges

        scheduler.step()

        train_loss = total_loss / total_edges
        train_mae_norm = total_mae_norm / total_edges
        train_mae_denorm = total_mae_denorm / total_edges if total_edges > 0 else 0

        # Validation
        model.eval()
        val_loss = 0
        val_mae_norm = 0
        val_mae_denorm = 0
        val_edges = 0

        with torch.no_grad():
            for data in val_loader:
                data = data.to(device)
                out = model(data.x, data.edge_index, data.edge_attr)
                loss = criterion(out, data.y)
                
                val_loss += loss.item() * data.num_edges
                mae_norm = torch.abs(out - data.y)
                val_mae_norm += mae_norm.sum().item()
                
                valid_mask = (data.y > 0).view(-1)
                if valid_mask.sum() > 0:
                    true_die_diag = data.raw_y[valid_mask] / data.y[valid_mask]
                    mae_denorm = mae_norm[valid_mask] * true_die_diag
                    val_mae_denorm += mae_denorm.sum().item()
                    
                val_edges += data.num_edges

        val_loss = val_loss / val_edges if val_edges > 0 else 0
        val_mae_norm = val_mae_norm / val_edges if val_edges > 0 else 0
        val_mae_denorm = val_mae_denorm / val_edges if val_edges > 0 else 0

        print(f"Epoch {epoch+1:03d} | Train Loss: {train_loss:.4f} | Train MAE: {train_mae_norm:.4f} (Denorm: {train_mae_denorm:.2f}) | Val Loss: {val_loss:.4f} | Val MAE: {val_mae_norm:.4f} (Denorm: {val_mae_denorm:.2f})")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), 'topological_gnn_model.pth')

    print("Training complete. Best model saved to topological_gnn_model.pth.")

if __name__ == '__main__':
    train()
