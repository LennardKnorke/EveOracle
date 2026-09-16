# backend/app/routers/model.py

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
import numpy as np
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

import onnxruntime as ort
from shared.config import STATIC_DIR, SHIP_FILE

router = APIRouter(prefix="/model", tags=["Model"])
MODELS_DIR = STATIC_DIR / "output" / "models"

_SESSION_CACHE: Dict[str, Tuple[ort.InferenceSession, Dict[str, Any]]] = {}


# -------------------------------------------------------------------------
# Self-Contained Combat Physics & Ship Tiers (No ml_engine dependency)
# -------------------------------------------------------------------------
HULL_CLASS_TIERS: Dict[str, int] = {
    "Corvette": 0,
    "Frigate": 1, "Assault Frigate": 1, "Covert Ops": 1, "Electronic Attack Ship": 1,
    "Interceptor": 1, "Stealth Bomber": 1, "Logistics Frigate": 1, "Expedition Frigate": 1,
    "Destroyer": 2, "Tactical Destroyer": 2, "Command Destroyer": 2, "Interdictor": 2,
    "Cruiser": 3, "Heavy Assault Cruiser": 3, "Heavy Interdiction Cruiser": 3,
    "Combat Recon Ship": 3, "Force Recon Ship": 3, "Logistics": 3, "Strategic Cruiser": 3, "Flag Cruiser": 3,
    "Combat Battlecruiser": 4, "Attack Battlecruiser": 4, "Battlecruiser": 4, "Command Ship": 4,
    "Battleship": 5, "Marauder": 5, "Black Ops": 5,
    "Dreadnought": 6, "Carrier": 6, "Force Auxiliary": 6, "Supercarrier": 6, "Titan": 6,
}


def compute_ship_ehp(ship_features: Dict[str, float]) -> float:
    struct_hp = ship_features.get("ship_hp_structure", 0.0)
    armor_hp = ship_features.get("ship_hp_armor", 0.0)
    shield_hp = ship_features.get("ship_hp_shield", 0.0)

    avg_armor_res = (
        ship_features.get("ship_armor_em_res", 1.0)
        + ship_features.get("ship_armor_therm_res", 1.0)
        + ship_features.get("ship_armor_kin_res", 1.0)
        + ship_features.get("ship_armor_exp_res", 1.0)
    ) / 4.0
    avg_armor_res = max(0.1, min(1.0, avg_armor_res))

    avg_shield_res = (
        ship_features.get("ship_shield_em_res", 1.0)
        + ship_features.get("ship_shield_therm_res", 1.0)
        + ship_features.get("ship_shield_kin_res", 1.0)
        + ship_features.get("ship_shield_exp_res", 1.0)
    ) / 4.0
    avg_shield_res = max(0.1, min(1.0, avg_shield_res))

    return struct_hp + (armor_hp / avg_armor_res) + (shield_hp / avg_shield_res)


def compute_relative_combat_physics(
    p1_char: Dict[str, float],
    p1_ship: Dict[str, float],
    p1_ship_class: str,
    p2_char: Dict[str, float],
    p2_ship: Dict[str, float],
    p2_ship_class: str,
    p2_has_char: float,
    p2_has_ship: float,
) -> Dict[str, float]:
    p1_tier = HULL_CLASS_TIERS.get(p1_ship_class, 3)
    p2_tier = HULL_CLASS_TIERS.get(p2_ship_class, 3) if p2_has_ship else p1_tier
    diff_hull_tier = float(p1_tier - p2_tier) if p2_has_ship else 0.0

    ehp1 = compute_ship_ehp(p1_ship)
    ehp2 = compute_ship_ehp(p2_ship) if p2_has_ship else ehp1
    ratio_ehp = math.log10(max(1.0, ehp1 + 1.0) / max(1.0, ehp2 + 1.0)) if p2_has_ship else 0.0

    v1 = p1_ship.get("ship_velocity", 100.0)
    v2 = p2_ship.get("ship_velocity", 100.0) if p2_has_ship else v1
    ratio_speed = math.log10((v1 + 1.0) / (v2 + 1.0)) if p2_has_ship else 0.0

    sig1 = p1_ship.get("ship_sig_radius", 100.0)
    sig2 = p2_ship.get("ship_sig_radius", 100.0) if p2_has_ship else sig1
    ratio_application = math.log10(max(0.01, (sig2 / max(1.0, sig1)) * ((v1 + 1.0) / (v2 + 1.0)))) if p2_has_ship else 0.0

    k1 = p1_char.get("char_kills_total", 0.0)
    k2 = p2_char.get("char_kills_total", 0.0) if p2_has_char else k1
    diff_log_kills = math.log10(k1 + 1.0) - math.log10(k2 + 1.0) if p2_has_char else 0.0

    d1 = p1_char.get("char_danger_ratio", 50.0)
    d2 = p2_char.get("char_danger_ratio", 50.0) if p2_has_char else d1
    diff_danger_ratio = (d1 - d2) / 100.0 if p2_has_char else 0.0

    hk1 = p1_char.get("char_hull_kills_total", 0.0)
    hk2 = p2_char.get("char_hull_kills_total", 0.0) if (p2_has_char and p2_has_ship) else hk1
    diff_hull_experience = math.log10(hk1 + 1.0) - math.log10(hk2 + 1.0) if (p2_has_char and p2_has_ship) else 0.0

    return {
        "phys_diff_hull_tier": float(diff_hull_tier),
        "phys_ratio_ehp": float(ratio_ehp),
        "phys_ratio_speed": float(ratio_speed),
        "phys_ratio_application": float(ratio_application),
        "phys_diff_log_kills": float(diff_log_kills),
        "phys_diff_danger_ratio": float(diff_danger_ratio),
        "phys_diff_hull_experience": float(diff_hull_experience),
    }


# -------------------------------------------------------------------------
# Model Session Cache
# -------------------------------------------------------------------------
def get_model_session(model_name: str) -> Tuple[ort.InferenceSession, Dict[str, Any]]:
    if model_name in _SESSION_CACHE:
        return _SESSION_CACHE[model_name]

    package_dir = MODELS_DIR / model_name
    if not package_dir.exists():
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
    p1: Dict[str, Any]
    p2: Dict[str, Any]


def extract_pilot_features(token: Dict[str, Any], prefix: str, ships_dogma: Dict[str, Any]) -> Tuple[Dict[str, float], Dict[str, float], str]:
    char_data = token.get("character") or {}
    stats = char_data.get("stats") or {}
    ship_data = token.get("ship") or {}
    ship_id = ship_data.get("id")
    ship_class = ship_data.get("shipClass", "")

    has_char = 1.0 if char_data else 0.0
    has_ship = 1.0 if ship_data else 0.0

    total_kills = float(stats.get("shipsDestroyed") or 0.0)
    total_losses = float(stats.get("shipsLost") or 0.0)
    total_isk_k = float(stats.get("iskDestroyed") or 0.0)
    total_isk_l = float(stats.get("iskLost") or 0.0)

    # Birthday estimation
    birthday_str = stats.get("info", {}).get("birthday")
    pilot_age_days = 365.0 * 3.0
    if birthday_str:
        try:
            b_dt = datetime.fromisoformat(birthday_str.replace("Z", "+00:00"))
            pilot_age_days = (datetime.now(timezone.utc) - b_dt).total_seconds() / 86400.0
        except Exception:
            pass

    # Impute weekly rates gracefully if rank block missing
    weekly_metrics = stats.get("rankings", {}).get("weekly", {}).get("all", {}).get("metrics", {})
    recent_metrics = stats.get("rankings", {}).get("recent", {}).get("all", {}).get("metrics", {})

    k_7d = float(weekly_metrics.get("shipsDestroyed") or (total_kills / max(1.0, pilot_age_days / 7.0)))
    k_30d = float(recent_metrics.get("shipsDestroyed") or (total_kills / max(1.0, pilot_age_days / 30.0)))

    l_7d = float(weekly_metrics.get("shipsLost") or (total_losses / max(1.0, pilot_age_days / 7.0)))
    l_30d = float(recent_metrics.get("shipsLost") or (total_losses / max(1.0, pilot_age_days / 30.0)))

    isk_k_7d = float(weekly_metrics.get("iskDestroyed") or (total_isk_k / max(1.0, pilot_age_days / 7.0)))
    isk_k_30d = float(recent_metrics.get("iskDestroyed") or (total_isk_k / max(1.0, pilot_age_days / 30.0)))

    isk_l_7d = float(weekly_metrics.get("iskLost") or (total_isk_l / max(1.0, pilot_age_days / 7.0)))
    isk_l_30d = float(recent_metrics.get("iskLost") or (total_isk_l / max(1.0, pilot_age_days / 30.0)))

    danger = float(stats.get("dangerRatio") or 50.0)
    avg_gang = float(stats.get("avgGangSize") or 1.0)
    solo_ratio = float(stats.get("soloRatio") or 0.0)

    recent_labels = stats.get("recentLabels") or stats.get("labels") or {}
    pct_solo = float(solo_ratio)
    pct_blob = float(recent_labels.get("#:25+", {}).get("shipsDestroyed", 0) / max(1.0, total_kills) * 100.0) if total_kills > 0 else 0.0
    pct_small = float(max(0.0, 100.0 - pct_solo - pct_blob))

    # Hull Experience
    top_ships = stats.get("topShips") or []
    hull_k = 0.0
    hull_l = 0.0
    hull_isk_k = 0.0
    hull_isk_l = 0.0
    if ship_id:
        found = next((s for s in top_ships if s.get("shipTypeID") == int(ship_id)), None)
        if found:
            hull_k = float(found.get("kills") or 0.0)
            hull_l = float(found.get("losses") or 0.0)
            hull_isk_k = float(found.get("isk") or 0.0)

    dogma = ships_dogma.get(str(ship_id), {}).get("attributes", {}) if ship_id else {}

    char_feat = {
        f"{prefix}_has_char": has_char,
        f"{prefix}_char_kills_total": total_kills,
        f"{prefix}_char_kills_7d": k_7d,
        f"{prefix}_char_kills_30d": k_30d,
        f"{prefix}_char_losses_total": total_losses,
        f"{prefix}_char_losses_7d": l_7d,
        f"{prefix}_char_losses_30d": l_30d,
        f"{prefix}_char_isk_destroyed_total": total_isk_k,
        f"{prefix}_char_isk_destroyed_7d": isk_k_7d,
        f"{prefix}_char_isk_destroyed_30d": isk_k_30d,
        f"{prefix}_char_isk_lost_total": total_isk_l,
        f"{prefix}_char_isk_lost_7d": isk_l_7d,
        f"{prefix}_char_isk_lost_30d": isk_l_30d,
        f"{prefix}_char_danger_ratio": danger,
        f"{prefix}_char_avg_gang_size": avg_gang,
        f"{prefix}_char_pct_solo": pct_solo,
        f"{prefix}_char_pct_small_gang": pct_small,
        f"{prefix}_char_pct_blob": pct_blob,
        f"{prefix}_char_solo_kills": float(stats.get("soloKills") or 0.0),
        f"{prefix}_char_solo_losses": float(stats.get("soloLosses") or 0.0),
        f"{prefix}_char_days_since_active": 7.0,
        f"{prefix}_char_pilot_age_days": float(pilot_age_days),
        f"{prefix}_char_hull_kills_total": hull_k,
        f"{prefix}_char_hull_losses_total": hull_l,
        f"{prefix}_char_hull_isk_destroyed": hull_isk_k,
        f"{prefix}_char_hull_isk_lost": hull_isk_l,
    }

    ship_feat = {
        f"{prefix}_has_ship": has_ship,
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
    }

    return char_feat, ship_feat, ship_class


@router.get("/available")
async def get_available_models():
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
    session, manifest = get_model_session(body.model_name)

    ships_dogma = {}
    if SHIP_FILE.exists():
        with open(SHIP_FILE, "r", encoding="utf-8") as f:
            ships_dogma = json.load(f)

    # 1. Extract component features
    p1_char, p1_ship, p1_cls = extract_pilot_features(body.p1, prefix="p1", ships_dogma=ships_dogma)
    p2_char, p2_ship, p2_cls = extract_pilot_features(body.p2, prefix="p2", ships_dogma=ships_dogma)

    p2_has_char = p2_char["p2_has_char"]
    p2_has_ship = p2_ship["p2_has_ship"]

    # 2. Compute Relative Combat Physics (self-contained)
    physics_ratios = compute_relative_combat_physics(
        p1_char=p1_char, p1_ship=p1_ship, p1_ship_class=p1_cls,
        p2_char=p2_char, p2_ship=p2_ship, p2_ship_class=p2_cls,
        p2_has_char=p2_has_char, p2_has_ship=p2_has_ship,
    )

    all_raw = {**p1_char, **p1_ship, **p2_char, **p2_ship, **physics_ratios}

    # 3. Vectorize and Scale using Model Manifest Schema
    input_schema = manifest.get("input_schema", {})
    feature_order: List[str] = input_schema.get("feature_order", [])
    log_keys: Set[str] = set(input_schema.get("log_transform_keys", []))
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

    # 4. ONNX Inference (< 2ms)
    outputs = session.run(None, {"input": vector})
    pred_log_isk = float(outputs[0][0][0])

    # 5. Continuous Inversion & Calibrated Win Probability
    sign = 1.0 if pred_log_isk >= 0 else -1.0
    pred_isk_trade = sign * (math.pow(10, abs(pred_log_isk)) - 1.0)
    win_prob = 1.0 / (1.0 + math.exp(-pred_log_isk / 2.0))

    return {
        "model_name": body.model_name,
        "predicted_log_isk": pred_log_isk,
        "predicted_isk_trade": pred_isk_trade,
        "p1_win_probability": round(win_prob, 4),
        "p2_win_probability": round(1.0 - win_prob, 4),
        "predicted_winner": "p1" if pred_log_isk >= 0 else "p2",
    }