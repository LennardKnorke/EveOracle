# ml_engine/training/tuner.py

import logging
from typing import Dict, Any, Tuple
from pathlib import Path
import optuna
import torch

from ml_engine.dataset.torch_dataset import load_dataset_splits
from ml_engine.models.resnet import TabularResNet
from ml_engine.models.siamese import SiameseCombatNet
from ml_engine.training.trainer import train_model, evaluate
from ml_engine.export.manifest import export_model_package

logger = logging.getLogger("EveOracle.Tuner")


def run_hyperparameter_search(
    parquet_path: Path,
    output_dir: Path,
    n_trials: int = 20,
    epochs_per_trial: int = 40,
    final_epochs: int = 100,
    batch_size: int = 256,
    date_range: Tuple[str, str] = ("2026-06-01", "2026-08-31"),
):
    train_loader, val_loader, test_loader, scaler, feature_cols = load_dataset_splits(
        parquet_path=parquet_path,
        batch_size=batch_size,
    )
    input_dim = len(feature_cols)

    def objective(trial: optuna.Trial) -> float:
        # Architecture selection
        arch_type = trial.suggest_categorical("arch_type", ["ResNet", "Siamese"])
        
        # Expanded learning parameters
        lr = trial.suggest_float("lr", 1e-5, 1e-2, log=True)
        weight_decay = trial.suggest_float("weight_decay", 1e-6, 1e-1, log=True)
        dropout = trial.suggest_float("dropout", 0.0, 0.40)

        # Expanded architectural dimensions
        if arch_type == "ResNet":
            hidden_dim = trial.suggest_categorical("hidden_dim", [64, 128, 256, 384, 512])
            num_blocks = trial.suggest_int("num_blocks", 1, 5)
            model = TabularResNet(
                input_dim=input_dim,
                hidden_dim=hidden_dim,
                num_blocks=num_blocks,
                dropout=dropout,
            )
        else:
            embed_dim = trial.suggest_categorical("embed_dim", [32, 64, 128, 256, 384, 512])
            model = SiameseCombatNet(
                input_dim=input_dim,
                embed_dim=embed_dim,
                dropout=dropout,
            )

        trained_model, metrics = train_model(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            epochs=epochs_per_trial,
            lr=lr,
            weight_decay=weight_decay,
            model_name=f"Trial {trial.number} ({arch_type})",
            leave_pbar=False,
        )

        return metrics["val_huber_loss"]

    logger.info(f"🔍 Starting Optuna study: {n_trials} trials, {epochs_per_trial} epochs/trial...")
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    
    # Prunes hopeless trials early to save compute
    pruner = optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=10)
    study = optuna.create_study(direction="minimize", pruner=pruner)
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

    logger.info("=" * 65)
    logger.info(f"🏆 Best Trial Loss (Huber): {study.best_value:.4f}")
    logger.info(f"🏆 Best Hyperparameters: {study.best_params}")
    logger.info("=" * 65)

    # -------------------------------------------------------------
    # Retrain Best Configuration for Final 100 Epochs
    # -------------------------------------------------------------
    best_p = study.best_params
    arch_type = best_p["arch_type"]
    logger.info(f"🚀 Retraining best configuration ({arch_type}) for {final_epochs} epochs...")

    if arch_type == "ResNet":
        best_model = TabularResNet(
            input_dim=input_dim,
            hidden_dim=best_p["hidden_dim"],
            num_blocks=best_p["num_blocks"],
            dropout=best_p["dropout"],
        )
    else:
        best_model = SiameseCombatNet(
            input_dim=input_dim,
            embed_dim=best_p["embed_dim"],
            dropout=best_p["dropout"],
        )

    trained_best, metrics = train_model(
        model=best_model,
        train_loader=train_loader,
        val_loader=val_loader,
        epochs=final_epochs,
        lr=best_p["lr"],
        weight_decay=best_p["weight_decay"],
        model_name=f"Final Best {arch_type}",
        leave_pbar=True,
    )

    # Final holdout test evaluation
    device = torch.device(
        "cuda" if torch.cuda.is_available() 
        else ("mps" if torch.backends.mps.is_available() else "cpu")
    )
    test_loss, test_acc = evaluate(trained_best, test_loader, torch.nn.HuberLoss(), device)
    metrics["test_huber_loss"] = test_loss
    metrics["test_directional_accuracy"] = test_acc

    # Export Package (model.onnx + manifest.json)
    package_dir = export_model_package(
        model=trained_best,
        scaler=scaler,
        model_name=f"1v1_combat_{arch_type.lower()}_best",
        arch_type=arch_type,
        output_dir=output_dir,
        metrics=metrics,
        training_date_range=date_range,
    )

    logger.info("=" * 65)
    logger.info(f"📦 Production Model Package exported to: {package_dir}")
    logger.info(f"• Test Loss:                 {test_loss:.4f}")
    logger.info(f"• Test Directional Accuracy: {test_acc * 100:.2f}%")
    logger.info("=" * 65)