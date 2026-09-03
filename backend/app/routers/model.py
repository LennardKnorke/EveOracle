# backend/app/routers/model.py

import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

import onnxruntime as ort
from shared.config import STATIC_DIR, SHIP_FILE, MODELS_DIR

router = APIRouter(prefix="/model", tags=["Model"])



# In-memory session cache: { model_name: (InferenceSession, manifest_dict) }
_SESSION_CACHE: Dict[str, tuple[ort.InferenceSession, Dict[str, Any]]] = {}


def get_model_session(model_name: str) -> tuple[ort.InferenceSession, Dict[str, Any]]:
    """Loads and caches an ONNX InferenceSession and its manifest.json."""
    if model_name in _SESSION_CACHE:
        return _SESSION_CACHE[model_name]

    package_dir = MODELS_DIR / model_name
    if not package_dir.exists():
        # Also check direct models directory
        package_dir = STATIC_DIR / "models" / model_name

    onnx_file = package_dir / "model.onnx"
    manifest_file = package_dir / "manifest.json"

    if not onnx_file.exists() or not manifest_file.exists():
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' or its manifest was not found.")

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    session = ort.InferenceSession(str(onnx_file), providers=["CPUExecutionProvider"])
    _SESSION_CACHE[model_name] = (session, manifest)
    return session, manifest


class PredictMatchupRequest(BaseModel):
    model_name: str
    p1: Dict[str, Any]  # TeamToken (character, ship)
    p2: Dict[str, Any]  # TeamToken (character, ship)


def extract_pilot_features(token: Dict[str, Any], prefix: str, ships_dogma: Dict[str, Any]) -> Dict[str, float]:
    """Extracts raw numeric pilot stats and ship dogma from a TeamToken."""
    char_data = token.get("character") or {}
    stats = char_data.get("stats") or {}
    ship_data = token.get("ship") or {}
    ship_id = ship_data.get("id")

    has_char = 1.0 if char_data else 0.0
    has_ship = 1.0 if ship_data else 0.0

    # 1. Pilot Stats
    weekly_metrics = stats.get("rankings", {}).get("weekly", {}).get("all", {}).get("metrics", {})
    recent_metrics = stats.get("rankings", {}).get("recent", {}).get("all", {}).get("metrics", {})

    total_kills = float(stats.get("shipsDestroyed") or 0.0)
    total_losses = float(stats.get("shipsLost") or 0.0)
    danger = float(stats.get("dangerRatio") or 50.0)
    avg_gang = float(stats.get("avgGangSize") or 1.0)
    solo_ratio = float(stats.get("soloRatio") or 0.0)
    gang_ratio = float(stats.get("gangRatio") or (100.0 - solo_ratio))

    # Hull experience
    top_ships = stats.get("topShips") or []
    hull_k = 0.0
    hull_l = 0.0
    if ship_id:
        found = next((s for s in top_ships if s.get("shipTypeID") == int(ship_id)), None)
        if found:
            hull_k = float(found.get("kills") or 0.0)
            hull_l = float(found.get("losses") or 0.0)

    # 2. Ship Dogma
    dogma = ships_dogma.get(str(ship_id), {}).get("attributes", {}) if ship_id else {}

    feat = {
        f"{prefix}_has_char": has_char,
        f"{prefix}_has_ship": has_ship,
        f"{prefix}_char_kills_total": total_kills,
        f"{prefix}_char_kills_7d": float(weekly_metrics.get("shipsDestroyed") or 0.0),
        f"{prefix}_char_kills_30d": float(recent_metrics.get("shipsDestroyed") or 0.0),
        f"{prefix}_char_losses_total": total_losses,
        f"{prefix}_char_losses_7d": float(weekly_metrics.get("shipsLost") or 0.0),
        f"{prefix}_char_losses_30d": float(recent_metrics.get("shipsLost") or 0.0),
        f"{prefix}_char_isk_destroyed_total": float(stats.get("iskDestroyed") or 0.0),
        f"{prefix}_char_isk_destroyed_7d": float(weekly_metrics.get("iskDestroyed") or 0.0),
        f"{prefix}_char_isk_destroyed_30d": float(recent_metrics.get("iskDestroyed") or 0.0),
        f"{prefix}_char_isk_lost_total": float(stats.get("iskLost") or 0.0),
        f"{prefix}_char_isk_lost_7d": float(weekly_metrics.get("iskLost") or 0.0),
        f"{prefix}_char_isk_lost_30d": float(recent_metrics.get("iskLost") or 0.0),
        f"{prefix}_char_danger_ratio": danger,
        f"{prefix}_char_avg_gang_size": avg_gang,
        f"{prefix}_char_solo_ratio": solo_ratio,
        f"{prefix}_char_gang_ratio": gang_ratio,
        f"{prefix}_char_solo_kills": float(stats.get("soloKills") or 0.0),
        f"{prefix}_char_solo_losses": float(stats.get("soloLosses") or 0.0),
        f"{prefix}_char_hull_kills_total": hull_k,
        f"{prefix}_char_hull_losses_total": hull_l,
        # Ship Dogma
        f"{prefix}_ship_hp_structure": float(dogma.get("hp", 0.0)),
        f"{prefix}_ship_hp_armor": float(dogma.get("armorHP", 0.0)),
        f"{prefix}_ship_hp_shield": float(dogma.get("shieldCapacity", 0.0)),
        f"{prefix}_ship_velocity": float(dogma.get("maxVelocity", 0.0)),
        f"{prefix}_ship_agility": float(dogma.get("agility", 0.0)),
        f"{prefix}_ship_sig_radius": float(dogma.get("signatureRadius", 0.0)),
        f"{prefix}_ship_scan_resolution": float(dogma.get("scanResolution", 0.0)),
        f"{prefix}_ship_slots_hi": float(dogma.get("hiSlots", 0.0)),
        f"{prefix}_ship_slots_med": float(dogma.get("medSlots", 0.0)),
        f"{prefix}_ship_slots_low": float(dogma.get("lowSlots", 0.0)),
        f"{prefix}_ship_turrets": float(dogma.get("turretSlotsLeft", 0.0)),
        f"{prefix}_ship_launchers": float(dogma.get("launcherSlotsLeft", 0.0)),
        f"{prefix}_ship_powergrid": float(dogma.get("powerOutput", 0.0)),
        f"{prefix}_ship_cpu": float(dogma.get("cpuOutput", 0.0)),
        f"{prefix}_ship_drone_bandwidth": float(dogma.get("droneBandwidth", 0.0)),
        f"{prefix}_ship_drone_capacity": float(dogma.get("droneCapacity", 0.0)),
        f"{prefix}_ship_armor_em_res": float(dogma.get("armorEmDamageResonance", 1.0)),
        f"{prefix}_ship_armor_therm_res": float(dogma.get("armorThermalDamageResonance", 1.0)),
        f"{prefix}_ship_armor_kin_res": float(dogma.get("armorKineticDamageResonance", 1.0)),
        f"{prefix}_ship_armor_exp_res": float(dogma.get("armorExplosiveDamageResonance", 1.0)),
        f"{prefix}_ship_shield_em_res": float(dogma.get("shieldEmDamageResonance", 1.0)),
        f"{prefix}_ship_shield_therm_res": float(dogma.get("shieldThermalDamageResonance", 1.0)),
        f"{prefix}_ship_shield_kin_res": float(dogma.get("shieldKineticDamageResonance", 1.0)),
        f"{prefix}_ship_shield_exp_res": float(dogma.get("shieldExplosiveDamageResonance", 1.0)),
        f"{prefix}_ship_meta_kills_total": 0.0,
        f"{prefix}_ship_meta_losses_total": 0.0,
    }
    return feat


@router.get("/available")
async def get_available_models():
    """Returns all available model packages on disk with their manifest metadata."""
    models = []
    search_dirs = [MODELS_DIR, STATIC_DIR / "models"]

    for d in search_dirs:
        if d.exists():
            for manifest_file in d.glob("*/manifest.json"):
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    models.append(manifest)
                except Exception:
                    continue
    return models


@router.post("/predict")
async def predict_matchup(body: PredictMatchupRequest):
    """
    Evaluates a 1v1 encounter between P1 (Focal) and P2 (Opponent) using the requested model.
    """
    session, manifest = get_model_session(body.model_name)

    # Load static ships
    ships_dogma = {}
    if SHIP_FILE.exists():
        with open(SHIP_FILE, "r", encoding="utf-8") as f:
            ships_dogma = json.load(f)

    # 1. Extract raw features for P1 and P2
    p1_feat = extract_pilot_features(body.p1, prefix="p1", ships_dogma=ships_dogma)
    p2_feat = extract_pilot_features(body.p2, prefix="p2", ships_dogma=ships_dogma)
    all_raw = {**p1_feat, **p2_feat}

    # 2. Vectorize and scale according to manifest contract
    input_schema = manifest.get("input_schema", {})
    feature_order: List[str] = input_schema.get("feature_order", [])
    log_keys: set[str] = set(input_schema.get("log_transform_keys", []))
    scaler_means: Dict[str, float] = input_schema.get("scaler", {}).get("means", {})
    scaler_stds: Dict[str, float] = input_schema.get("scaler", {}).get("stds", {})

    vector = np.zeros((1, len(feature_order)), dtype=np.float32)

    for i, key in enumerate(feature_order):
        val = all_raw.get(key, 0.0)
        if key in log_keys:
            val = math.log10(max(val, 0.0) + 1.0)
        mean_val = scaler_means.get(key, 0.0)
        std_val = scaler_stds.get(key, 1.0)
        vector[0, i] = (val - mean_val) / (std_val if std_val > 1e-7 else 1.0)

    # 3. Execute ONNX Inference
    outputs = session.run(None, {"input": vector})
    pred_log_isk = float(outputs[0][0][0])

    # 4. Transform output (Signed log10 ISK -> Raw ISK & Calibrated Win Probability)
    sign = 1.0 if pred_log_isk >= 0 else -1.0
    pred_isk_trade = sign * (math.pow(10, abs(pred_log_isk)) - 1.0)

    # Calibrated Sigmoid with temperature tau = 2.0
    win_prob = 1.0 / (1.0 + math.exp(-pred_log_isk / 2.0))

    return {
        "model_name": body.model_name,
        "predicted_log_isk": pred_log_isk,
        "predicted_isk_trade": pred_isk_trade,
        "p1_win_probability": round(win_prob, 4),
        "p2_win_probability": round(1.0 - win_prob, 4),
        "predicted_winner": "p1" if pred_log_isk >= 0 else "p2",
    }