# ml_engine/export/manifest.py

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
import torch
import torch.nn as nn
from ml_engine.dataset.torch_dataset import FeatureScaler


def export_model_package(
    model: nn.Module,
    scaler: FeatureScaler,
    model_name: str,
    arch_type: str,
    output_dir: Path,
    metrics: Dict[str, float],
    training_date_range: tuple[str, str],
) -> Path:
    """
    Exports a self-contained model package (model.onnx + manifest.json).
    Ensures model and dummy inputs are on CPU before ONNX tracing.
    """
    package_dir = output_dir / model_name
    package_dir.mkdir(parents=True, exist_ok=True)

    # 1. Move model to CPU and create dummy_input on CPU
    model = model.cpu()
    model.eval()
    dummy_input = torch.randn(1, len(scaler.feature_names), dtype=torch.float32, device="cpu")

    # 2. Export ONNX Graph using standard tracing
    onnx_path = package_dir / "model.onnx"
    
    export_kwargs = {
        "input_names": ["input"],
        "output_names": ["predicted_log_isk"],
        "dynamic_axes": {
            "input": {0: "batch_size"},
            "predicted_log_isk": {0: "batch_size"}
        },
        "opset_version": 18,
    }

    try:
        # PyTorch 2.x: explicitly disable Dynamo exporter for robust standard tracing
        torch.onnx.export(
            model,
            dummy_input,
            str(onnx_path),
            dynamo=False,
            **export_kwargs
        )
    except TypeError:
        # Fallback for older PyTorch versions where dynamo kwarg is not present
        torch.onnx.export(
            model,
            dummy_input,
            str(onnx_path),
            **export_kwargs
        )

    # 3. Build manifest.json contract
    manifest: Dict[str, Any] = {
        "model_name": model_name,
        "version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "training_date_range": list(training_date_range),
        "architecture": {
            "type": arch_type,
            "input_dim": len(scaler.feature_names),
        },
        "input_schema": scaler.to_dict(),
        "output_schema": {
            "target_name": "predicted_log_isk",
            "type": "continuous_regression",
            "interpretation": "signed_log10_isk_trade",
            "inverse_transform_formula": "sign(y) * (10^abs(y) - 1)",
            "win_threshold": 0.0,
        },
        "metrics": metrics,
    }

    manifest_path = package_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return package_dir