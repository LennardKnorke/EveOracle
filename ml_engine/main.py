# ml_engine/main.py

import argparse
import sys
from pathlib import Path
from typing import List, Set

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from shared.config import STATIC_DIR
from ml_engine.etl.dataset_builder import MLDatasetConfig, build_ml_dataset
from ml_engine.dataset.torch_dataset import load_dataset_splits
from ml_engine.models.resnet import TabularResNet
from ml_engine.models.siamese import SiameseCombatNet
from ml_engine.training.trainer import train_model
from ml_engine.training.tuner import run_hyperparameter_search
from ml_engine.export.manifest import export_model_package

SUBCAPITAL_CLASSES = {
    "Corvette", "Frigate", "Assault Frigate", "Covert Ops", "Electronic Attack Ship",
    "Interceptor", "Stealth Bomber", "Logistics Frigate", "Expedition Frigate",
    "Destroyer", "Tactical Destroyer", "Command Destroyer", "Interdictor", "Cruiser",
    "Heavy Assault Cruiser", "Heavy Interdiction Cruiser", "Combat Recon Ship",
    "Force Recon Ship", "Logistics", "Strategic Cruiser", "Flag Cruiser",
    "Combat Battlecruiser", "Attack Battlecruiser", "Battlecruiser", "Command Ship",
    "Battleship", "Marauder", "Black Ops", "Mining Barge", "Exhumer", "Hauler",
    "Deep Space Transport", "Blockade Runner", "Prototype Exploration Ship",
    "Special Edition Yachts",
}


def resolve_ship_classes(user_input: List[str]) -> Set[str] | str:
    cleaned = [s.strip() for s in user_input if s.strip()]
    if not cleaned or any(s.lower() == "all" for s in cleaned):
        return "all"
    if any(s.lower() in ("subcapitals", "subcaps") for s in cleaned):
        return SUBCAPITAL_CLASSES
    return set(cleaned)


def parse_args():
    parser = argparse.ArgumentParser(
        description="EveOracle ML Engine - 1v1 Dataset Building, Training & Hyperparameter Tuning"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["dataset", "train", "tune"],
        default="tune",
        help="Execution mode: 'dataset' (extract parquet only), 'train' (single run), 'tune' (Optuna study)",
    )
    parser.add_argument(
        "--start-date",
        "--start-month",
        type=str,
        default="2026-06",
        help="Start date/month (e.g. '2026-06')",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=3,
        help="Duration in months (default: 3)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Optional explicit end date (e.g. '2026-08-31')",
    )
    parser.add_argument(
        "--ship-classes",
        nargs="+",
        default=["SubCapitals"],
        help="Allowed ship classes (default: 'SubCapitals')",
    )
    parser.add_argument(
        "--trial-epochs",
        type=int,
        default=40,
        help="Epochs per Optuna search trial (default: 40)",
    )
    parser.add_argument(
        "--final-epochs",
        type=int,
        default=100,
        help="Epochs to retrain winning model (default: 100)",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=20,
        help="Optuna search trials for --mode tune (default: 20)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=256,
        help="Batch size (default: 256)",
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force re-extraction of dataset parquet file",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    datasets_dir = STATIC_DIR / "output" / "datasets"
    models_dir = STATIC_DIR / "output" / "models"

    config = MLDatasetConfig(
        start_input=args.start_date,
        months_input=args.months,
        end_input=args.end_date,
        allowed_ship_classes=resolve_ship_classes(args.ship_classes),
        output_dir=datasets_dir,
    )

    print("=" * 65)
    print(f"🚀 EveOracle ML Engine | Mode: {args.mode.upper()}")
    print(f"• Timeframe:     {args.start_date} ({args.months} months / End: {args.end_date or 'Auto'})")
    print(f"• Search Trials: {args.trials} trials @ {args.trial_epochs} epochs each")
    print(f"• Final Retrain: {args.final_epochs} epochs on winning architecture")
    print(f"• Output Dir:    {datasets_dir}")
    print("=" * 65)

    # 1. Build or locate cached Parquet dataset
    parquet_path = build_ml_dataset(config, force_rebuild=args.force_rebuild)

    if args.mode == "dataset":
        print("✅ Dataset generation complete.")
        return

    # 2. Hyperparameter Search & Auto-Export
    if args.mode == "tune":
        run_hyperparameter_search(
            parquet_path=parquet_path,
            output_dir=models_dir,
            n_trials=args.trials,
            epochs_per_trial=args.trial_epochs,
            final_epochs=args.final_epochs,
            batch_size=args.batch_size,
            date_range=(args.start_date, args.end_date or f"{args.months} months"),
        )
    elif args.mode == "train":
        train_loader, val_loader, test_loader, scaler, feature_cols = load_dataset_splits(
            parquet_path=parquet_path,
            batch_size=args.batch_size,
        )
        input_dim = len(feature_cols)
        model = TabularResNet(input_dim=input_dim, hidden_dim=256, num_blocks=3)

        trained_model, metrics = train_model(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            epochs=args.final_epochs,
            model_name="Manual TabularResNet",
            leave_pbar=True,
        )

        package_dir = export_model_package(
            model=trained_model,
            scaler=scaler,
            model_name="1v1_manual_resnet",
            arch_type="RESNET",
            output_dir=models_dir,
            metrics=metrics,
            training_date_range=(args.start_date, args.end_date or f"{args.months} months"),
        )
        print(f"📦 Model exported successfully to: {package_dir}")


if __name__ == "__main__":
    main()