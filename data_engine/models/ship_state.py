# data_engine/models/ship_state.py

import json
from collections import deque
from datetime import date
from typing import Dict, Tuple, Optional
from shared.config import SHIP_FILE


def default_metrics() -> Dict[str, float]:
    return {"total": 0.0, "7d": 0.0, "30d": 0.0}


class ShipEntry:
    __slots__ = (
        "id",
        "name",
        "cls",
        "faction",
        "attributes",
        "ships_destroyed",
        "ship_lost",
        "isk_destroyed",
        "isk_lost",
        "km_history",
        "last_day",
    )

    def __init__(self, ship_id: int | str, name: str, cls: str, faction: str, attr: dict):
        self.id = int(ship_id)
        self.name = name
        self.cls = cls
        self.faction = faction
        self.attributes = attr or {}

        self.ships_destroyed: Dict[str, float] = default_metrics()
        self.ship_lost: Dict[str, float] = default_metrics()
        self.isk_destroyed: Dict[str, float] = default_metrics()
        self.isk_lost: Dict[str, float] = default_metrics()

        self.km_history: deque[Tuple[date, float, bool]] = deque()
        self.last_day: Optional[date] = None

    def clear_old_km(self, current_day: date):
        while self.km_history:
            event_date, isk, is_victim = self.km_history[0]
            if (current_day - event_date).days > 30:
                self.km_history.popleft()
                if is_victim:
                    self.ship_lost["30d"] = max(0.0, self.ship_lost["30d"] - 1.0)
                    self.isk_lost["30d"] = max(0.0, self.isk_lost["30d"] - isk)
                else:
                    self.ships_destroyed["30d"] = max(0.0, self.ships_destroyed["30d"] - 1.0)
                    self.isk_destroyed["30d"] = max(0.0, self.isk_destroyed["30d"] - isk)
            else:
                break

        self.ship_lost["7d"] = 0.0
        self.isk_lost["7d"] = 0.0
        self.ships_destroyed["7d"] = 0.0
        self.isk_destroyed["7d"] = 0.0

        for event_date, isk, is_victim in self.km_history:
            if (current_day - event_date).days <= 7:
                if is_victim:
                    self.ship_lost["7d"] += 1.0
                    self.isk_lost["7d"] += isk
                else:
                    self.ships_destroyed["7d"] += 1.0
                    self.isk_destroyed["7d"] += isk

    def record_event(self, day: date, isk_destroyed: float, is_victim: bool):
        if self.last_day != day:
            self.clear_old_km(day)
            self.last_day = day

        if is_victim:
            self.ship_lost["total"] += 1.0
            self.ship_lost["7d"] += 1.0
            self.ship_lost["30d"] += 1.0
            self.isk_lost["total"] += isk_destroyed
            self.isk_lost["7d"] += isk_destroyed
            self.isk_lost["30d"] += isk_destroyed
            self.km_history.append((day, isk_destroyed, True))
        else:
            self.ships_destroyed["total"] += 1.0
            self.ships_destroyed["7d"] += 1.0
            self.ships_destroyed["30d"] += 1.0
            self.isk_destroyed["total"] += isk_destroyed
            self.isk_destroyed["7d"] += isk_destroyed
            self.isk_destroyed["30d"] += isk_destroyed
            self.km_history.append((day, isk_destroyed, False))

    def get_features(self) -> Dict[str, float]:
        attrs = self.attributes
        return {
            "ship_hp_structure": float(attrs.get("hp", 0.0)),
            "ship_hp_armor": float(attrs.get("armorHP", 0.0)),
            "ship_hp_shield": float(attrs.get("shieldCapacity", 0.0)),
            "ship_velocity": float(attrs.get("maxVelocity", 0.0)),
            "ship_agility": float(attrs.get("agility", 0.0)),
            "ship_sig_radius": float(attrs.get("signatureRadius", 0.0)),
            "ship_scan_resolution": float(attrs.get("scanResolution", 0.0)),
            "ship_slots_hi": float(attrs.get("hiSlots", 0.0)),
            "ship_slots_med": float(attrs.get("medSlots", 0.0)),
            "ship_slots_low": float(attrs.get("lowSlots", 0.0)),
            "ship_turrets": float(attrs.get("turretSlotsLeft", 0.0)),
            "ship_launchers": float(attrs.get("launcherSlotsLeft", 0.0)),
            "ship_powergrid": float(attrs.get("powerOutput", 0.0)),
            "ship_cpu": float(attrs.get("cpuOutput", 0.0)),
            "ship_drone_bandwidth": float(attrs.get("droneBandwidth", 0.0)),
            "ship_drone_capacity": float(attrs.get("droneCapacity", 0.0)),
            "ship_armor_em_res": float(attrs.get("armorEmDamageResonance", 1.0)),
            "ship_armor_therm_res": float(attrs.get("armorThermalDamageResonance", 1.0)),
            "ship_armor_kin_res": float(attrs.get("armorKineticDamageResonance", 1.0)),
            "ship_armor_exp_res": float(attrs.get("armorExplosiveDamageResonance", 1.0)),
            "ship_shield_em_res": float(attrs.get("shieldEmDamageResonance", 1.0)),
            "ship_shield_therm_res": float(attrs.get("shieldThermalDamageResonance", 1.0)),
            "ship_shield_kin_res": float(attrs.get("shieldKineticDamageResonance", 1.0)),
            "ship_shield_exp_res": float(attrs.get("shieldExplosiveDamageResonance", 1.0)),
            "ship_meta_kills_total": float(self.ships_destroyed["total"]),
            "ship_meta_losses_total": float(self.ship_lost["total"]),
        }


def init_ships_database() -> Dict[int, ShipEntry]:
    ships: Dict[int, ShipEntry] = {}
    with open(SHIP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        for s_id, s_data in data.items():
            new_entry = ShipEntry(
                s_id,
                s_data.get("name", f"Ship {s_id}"),
                s_data.get("shipClass", "Unknown"),
                s_data.get("faction", "Unknown"),
                s_data.get("attributes", {}),
            )
            ships[int(s_id)] = new_entry
    return ships