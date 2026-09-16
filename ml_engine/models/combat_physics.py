# ml_engine/models/combat_physics.py

import math
from typing import Dict, Any

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
    """Estimates effective hitpoints considering base resistances."""
    struct_hp = ship_features.get("ship_hp_structure", 0.0)
    armor_hp = ship_features.get("ship_hp_armor", 0.0)
    shield_hp = ship_features.get("ship_hp_shield", 0.0)

    # Average resonance (resonance = 1.0 - resistance, lower resonance = higher EHP)
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
    """
    Computes relative combat advantage ratios between P1 and P2.
    Masks to 0.0 if either P2 component is unobserved.
    """
    # 1. Hull Size Tier Disparity
    p1_tier = HULL_CLASS_TIERS.get(p1_ship_class, 3)
    p2_tier = HULL_CLASS_TIERS.get(p2_ship_class, 3) if p2_has_ship else p1_tier
    diff_hull_tier = float(p1_tier - p2_tier) if p2_has_ship else 0.0

    # 2. EHP Advantage Ratio
    ehp1 = compute_ship_ehp(p1_ship)
    ehp2 = compute_ship_ehp(p2_ship) if p2_has_ship else ehp1
    ratio_ehp = math.log10(max(1.0, ehp1 + 1.0) / max(1.0, ehp2 + 1.0)) if p2_has_ship else 0.0

    # 3. Speed & Range Control Ratio
    v1 = p1_ship.get("ship_velocity", 100.0)
    v2 = p2_ship.get("ship_velocity", 100.0) if p2_has_ship else v1
    ratio_speed = math.log10((v1 + 1.0) / (v2 + 1.0)) if p2_has_ship else 0.0

    # 4. Signature vs Tracking Application Index
    sig1 = p1_ship.get("ship_sig_radius", 100.0)
    sig2 = p2_ship.get("ship_sig_radius", 100.0) if p2_has_ship else sig1
    ratio_application = math.log10(max(0.01, (sig2 / max(1.0, sig1)) * ((v1 + 1.0) / (v2 + 1.0)))) if p2_has_ship else 0.0

    # 5. Pilot Experience & Danger Differentials
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