# ml_engine/dataset/torch_dataset.py

import json
from pathlib import Path
from typing import List, Tuple, Dict, Any, Set

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader

LOG_TRANSFORM_PATTERNS = (
    "kills_total", "losses_total", "isk_destroyed", "isk_lost",
    "mass", "powergrid", "cpu", "hp_structure", "hp_armor", "hp_shield"
)

# Columns to exclude from input features X
METADATA_COLUMNS = {
    "killmail_id", "date", "solar_system_id", "y_isk_destroyed",
    "y_log_isk", "outcome", "variant",
    "p1_char_id", "p1_ship_id", "p2_char_id", "p2_ship_id",
}


class FeatureScaler:
    def __init__(self):
        self.feature_names: List[str] = []
        self.log_transform_keys: Set[str] = set()
        self.means: Dict[str, float] = {}
        self.stds: Dict[str, float] = {}

    def fit(self, df: pd.DataFrame, feature_cols: List[str]):
        self.feature_names = feature_cols

        # Identify log-transform candidates (ignoring binary flags)
        for col in feature_cols:
            if col.endswith("_has_char") or col.endswith("_has_ship"):
                continue
            if any(pattern in col for pattern in LOG_TRANSFORM_PATTERNS):
                self.log_transform_keys.add(col)

        # Compute scaling parameters
        for col in feature_cols:
            vals = df[col].to_numpy(dtype=np.float32)
            if col in self.log_transform_keys:
                vals = np.log10(np.maximum(vals, 0.0) + 1.0)

            # Do not scale binary mask flags
            if col.endswith("_has_char") or col.endswith("_has_ship"):
                self.means[col] = 0.0
                self.stds[col] = 1.0
            else:
                mean_val = float(np.mean(vals))
                std_val = float(np.std(vals))
                self.means[col] = mean_val
                self.stds[col] = std_val if std_val > 1e-7 else 1.0

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        matrix = np.zeros((len(df), len(self.feature_names)), dtype=np.float32)
        for i, col in enumerate(self.feature_names):
            vals = df[col].to_numpy(dtype=np.float32)
            if col in self.log_transform_keys:
                vals = np.log10(np.maximum(vals, 0.0) + 1.0)
            matrix[:, i] = (vals - self.means[col]) / self.stds[col]
        return matrix

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_order": self.feature_names,
            "log_transform_keys": sorted(list(self.log_transform_keys)),
            "scaler": {
                "means": self.means,
                "stds": self.stds,
            },
        }


class Eve1v1Dataset(Dataset):
    def __init__(self, X: np.ndarray, y_log: np.ndarray):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y_log = torch.tensor(y_log, dtype=torch.float32).unsqueeze(1)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return {"x": self.X[idx], "y": self.y_log[idx]}


def load_dataset_splits(
    parquet_path: Path,
    batch_size: int = 256,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
) -> Tuple[DataLoader, DataLoader, DataLoader, FeatureScaler, List[str]]:
    df = pd.read_parquet(parquet_path)

    feature_cols = [c for c in df.columns if c not in METADATA_COLUMNS]

    # Chronological sort for temporal train/val/test split
    df = df.sort_values(by=["date", "killmail_id"]).reset_index(drop=True)

    n = len(df)
    n_train = int(n * train_ratio)
    n_val = int(n * (train_ratio + val_ratio))

    train_df = df.iloc[:n_train]
    val_df = df.iloc[n_train:n_val]
    test_df = df.iloc[n_val:]

    scaler = FeatureScaler()
    scaler.fit(train_df, feature_cols)

    train_ds = Eve1v1Dataset(scaler.transform(train_df), train_df["y_log_isk"].to_numpy())
    val_ds = Eve1v1Dataset(scaler.transform(val_df), val_df["y_log_isk"].to_numpy())
    test_ds = Eve1v1Dataset(scaler.transform(test_df), test_df["y_log_isk"].to_numpy())

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

    return train_loader, val_loader, test_loader, scaler, feature_cols