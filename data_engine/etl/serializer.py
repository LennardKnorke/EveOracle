# data_engine/utils/serializer.py

import gzip
import pickle
from pathlib import Path
from typing import Dict, Any


def save_monthly_snapshot(snapshot_path: Path, state_payload: Dict[str, Any]):
    """Saves the state payload to a compressed pickle file."""
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = snapshot_path.with_suffix(".tmp")

    with gzip.GzipFile(tmp_path, "wb", compresslevel=6) as f:
        pickle.dump(state_payload, f, protocol=pickle.HIGHEST_PROTOCOL)

    tmp_path.replace(snapshot_path)


def load_monthly_snapshot(snapshot_path: Path) -> Dict[str, Any]:
    """Loads a state payload from a compressed pickle file."""
    with gzip.GzipFile(snapshot_path, "rb") as f:
        return pickle.load(f)