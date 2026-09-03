# ml_engine/training/trainer.py

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from typing import Dict, Any, Tuple, Optional
from tqdm import tqdm


def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device
) -> Tuple[float, float]:
    """
    Evaluates model on a DataLoader.
    Returns (average_huber_loss, directional_accuracy).
    """
    model.eval()
    total_loss = 0.0
    correct_direction = 0
    total_samples = 0

    with torch.no_grad():
        for batch in loader:
            x = batch["x"].to(device)
            y = batch["y"].to(device)

            pred = model(x)
            loss = criterion(pred, y)

            total_loss += loss.item() * len(x)
            # Directional accuracy: did it predict the correct winner? (sign match)
            correct_direction += ((pred > 0) == (y > 0)).sum().item()
            total_samples += len(x)

    avg_loss = total_loss / total_samples if total_samples > 0 else float("inf")
    dir_acc = correct_direction / total_samples if total_samples > 0 else 0.0
    return avg_loss, dir_acc


def train_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    epochs: int = 40,
    lr: float = 1e-3,
    weight_decay: float = 1e-4,
    device_name: str = "auto",
    model_name: str = "Model",
    leave_pbar: bool = True,
) -> Tuple[nn.Module, Dict[str, float]]:
    """
    Trains model with live tqdm progress bar tracking metrics per epoch.
    """
    if device_name == "auto":
        device = torch.device(
            "cuda" if torch.cuda.is_available() 
            else ("mps" if torch.backends.mps.is_available() else "cpu")
        )
    else:
        device = torch.device(device_name)

    model = model.to(device)
    criterion = nn.HuberLoss(delta=1.0)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_loss = float("inf")
    best_weights = None
    best_dir_acc = 0.0

    # Main Epoch Progress Bar
    pbar = tqdm(range(1, epochs + 1), desc=f"🧠 Training {model_name}", unit="epoch", leave=leave_pbar)

    for epoch in pbar:
        model.train()
        running_train_loss = 0.0
        train_samples = 0

        for batch in train_loader:
            x = batch["x"].to(device)
            y = batch["y"].to(device)

            optimizer.zero_grad()
            pred = model(x)
            loss = criterion(pred, y)
            loss.backward()
            optimizer.step()

            running_train_loss += loss.item() * len(x)
            train_samples += len(x)

        scheduler.step()

        # Epoch Metrics
        avg_train_loss = running_train_loss / train_samples if train_samples > 0 else 0.0
        val_loss, val_acc = evaluate(model, val_loader, criterion, device)
        current_lr = optimizer.param_groups[0]["lr"]

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_dir_acc = val_acc
            best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        # Live Progress Bar Telemetry
        pbar.set_postfix({
            "train_loss": f"{avg_train_loss:.4f}",
            "val_loss": f"{val_loss:.4f}",
            "val_acc": f"{val_acc * 100:.1f}%",
            "best_val": f"{best_val_loss:.4f}",
            "lr": f"{current_lr:.1e}",
        })

    # Restore best checkpoint weights
    if best_weights:
        model.load_state_dict(best_weights)

    return model, {
        "val_huber_loss": best_val_loss,
        "val_directional_accuracy": best_dir_acc,
    }