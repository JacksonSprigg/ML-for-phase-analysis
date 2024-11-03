import torch
import torch.nn as nn
import wandb
import datetime

# Config
import scripts.training.config_training as config_training

# Functions
from src.data_loading.TOPASXRD_data_loader import create_data_loaders
from src.training.train_fcn import train_fcn
from src.training.train_mlp import train_mlp
from src.training.train_mlp_2 import train_mlp_2
from src.utils.check_GPUs import check_gpus

# TODO: Setup_device() function has not been tested with multiple GPUs. I am not currently sure how it will handle multiple GPUs. These needs to be done before large training runs.

def setup_wandb():
    wandb.require("core") # This line *maybe* fixes a "retry upload" bug I was having. See: https://github.com/wandb/wandb/issues/4929
    return wandb.init(
        project=config_training.WANDB_PROJECT_NAME, 
        dir=config_training.WANDB_SAVE_DIR, 
        config={
            "model_type": config_training.MODEL_TYPE,
            "criterion_type": config_training.CRITERION_TYPE,
            "optimizer_type": config_training.OPTIMIZER_TYPE,
            "batch_size": config_training.BATCH_SIZE,
            "num_workers": config_training.NUM_WORKERS,       
            "learning_rate": config_training.LEARNING_RATE,
            "num_epochs": config_training.NUM_EPOCHS,
        }
    )

def setup_model():
    # Initialize the model, loss function, and optimiser
    model_class = config_training.MODEL_CLASS[config_training.MODEL_TYPE]
    model = model_class()
    
    criterion_class = config_training.CRITERION_CLASS[config_training.CRITERION_TYPE]
    criterion = criterion_class()
    
    optimizer_class = config_training.OPTIMIZER_CLASS[config_training.OPTIMIZER_TYPE]
    optimizer = optimizer_class(model.parameters(), lr=config_training.LEARNING_RATE)
    
    return model, criterion, optimizer

def setup_device(model):
    # Setup GPUs
    if torch.cuda.device_count() > 1:
        print(f"Using {torch.cuda.device_count()} GPUs!")
        model = nn.DataParallel(model)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return model.to(device), device

def save_model(model, final_metrics):
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Use MAE as the accuracy metric for the filename
    mae = final_metrics['test_accuracy']['mae']
    
    model_name = f"{config_training.MODEL_TYPE}_mae_{mae:.8f}_{current_time}.pth"
    full_path = f'{config_training.MODEL_SAVE_DIR}/{model_name}'
    torch.save(model.state_dict(), full_path)
    return full_path, model_name

def main():
    # Start WandB
    if config_training.USE_WANDB:
        wandb_run = setup_wandb()

    # Create data loaders
    train_loader, val_loader, test_loader = create_data_loaders(
        config_training.DATA_DIRS,
        config_training.BATCH_SIZE, config_training.NUM_WORKERS
    )

    # Setup model, loss, and optimizer
    model, criterion, optimizer = setup_model()

    # Setup device
    model, device = setup_device(model)

    # Log the model architecture
    if config_training.WANDB_LOG_ARCHITECTURE:
        wandb.watch(model)

    # Train the model
    trained_model, test_loss, test_accuracy = train_mlp(
        model, train_loader, val_loader, test_loader, criterion, optimizer, 
        device, config_training.NUM_EPOCHS
    )
    final_metrics = {'test_loss': test_loss, 'test_accuracy': test_accuracy}

    # Save the model
    save_path, model_name = save_model(trained_model, final_metrics)

    if config_training.SAVE_MODEL_TO_WANDB_SERVERS:
        wandb.save(save_path)

    print(f"Training completed. Model saved as '{model_name}'.")

    if config_training.USE_WANDB:
        wandb_run.finish()

if __name__ == "__main__":
    check_gpus()
    main()