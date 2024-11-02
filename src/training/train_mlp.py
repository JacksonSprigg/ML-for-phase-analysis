import torch
import wandb
from tqdm import tqdm
import numpy as np

# TODD: Save best model in the right place

def train_mlp(model, train_loader, val_loader, test_loader, criterion, optimizer, device, num_epochs):
    best_val_loss = float('inf')
    
    for epoch in range(num_epochs):
        model.train()
        train_loss = 0.0
        num_batches = 0
        num_samples = 0
        
        for batch_idx, (data, target, _) in enumerate(tqdm(train_loader, desc=f"Epoch {epoch+1} Training")):
            # Move data to device
            data = data.to(device)
            target = target.to(device)     
            optimizer.zero_grad()
            output = model(data)
            
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            num_batches += 1
            num_samples += data.size(0)
        
        avg_train_loss = train_loss / num_batches
        
        print(f"Epoch {epoch+1} - Processed {num_samples} samples in {num_batches} batches")
        print(f"Epoch {epoch+1} - Average training loss: {avg_train_loss:.4f}")
        
        # Evaluate on validation set
        val_loss, val_metrics = evaluate(model, val_loader, criterion, device)
        
        # Log metrics to wandb
        if wandb.run is not None:
            wandb.log({
                "epoch": epoch + 1,
                "train_loss": avg_train_loss,
                "val_loss": val_loss,
                "val_mae": val_metrics['mae'],
                "val_mse": val_metrics['mse'],
                "val_r2": val_metrics['r2']
            })
        
        print(f'Epoch {epoch+1}: Train loss: {avg_train_loss:.8f}, Val loss: {val_loss:.8f}, Val MAE: {val_metrics["mae"]:.8f}')
        
        # Save the best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), 'best_model_mlp.pth')
            print(f"Saved new best model with validation loss: {best_val_loss:.4f}")
    
    # Load the best model for final evaluation
    model.load_state_dict(torch.load('best_model_mlp.pth'))
    
    # Evaluate on the test set
    test_loss, test_metrics = evaluate(model, test_loader, criterion, device)
    
    print(f'Test loss: {test_loss:.8f}, Test MAE: {test_metrics["mae"]:.8f}, Test R2: {test_metrics["r2"]:.8f}')
    
    if wandb.run is not None:
        wandb.log({
            "test_loss": test_loss,
            "test_mae": test_metrics['mae'],
            "test_mse": test_metrics['mse'],
            "test_r2": test_metrics['r2']
        })
    
    return model, test_loss, test_metrics

def evaluate(model, data_loader, criterion, device):
    model.eval()
    total_loss = 0
    all_targets = []
    all_outputs = []
    num_samples = 0
    
    with torch.no_grad():
        for data, target, _ in tqdm(data_loader, desc="Evaluation"):
            data = data.to(device)
            target = target.to(device)
            
            output = model(data)
            loss = criterion(output, target)
            total_loss += loss.item()
            
            all_targets.append(target.cpu().numpy())
            all_outputs.append(output.cpu().numpy())
            num_samples += data.size(0)
    
    all_targets = np.concatenate(all_targets)
    all_outputs = np.concatenate(all_outputs)
    
    avg_loss = total_loss / len(data_loader)
    mae = np.mean(np.abs(all_targets - all_outputs))
    mse = np.mean((all_targets - all_outputs)**2)
    r2 = 1 - np.sum((all_targets - all_outputs)**2) / np.sum((all_targets - np.mean(all_targets))**2)
    
    return avg_loss, {'mae': mae, 'mse': mse, 'r2': r2}