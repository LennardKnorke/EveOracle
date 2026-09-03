# data_engine/models/base_state.py

from collections import deque
from datetime import date
from typing import Dict, Tuple


def default_metrics() -> Dict[str, float]:
    return {"total": 0.0, "7d": 0.0, "30d": 0.0}


class BaseCombatState:
    """
    Modular base state tracker for entities (Pilots, Ships, Corps, Alliances).
    Tracks rolling 7d, 30d, and total metrics.
    """
    __slots__ = ("id", "ships_destroyed", "ship_lost", "isk_destroyed", "isk_lost", "km_history")

    def __init__(self, entity_id: int | str):
        self.id = int(entity_id)
        self.ships_destroyed: Dict[str, float] = default_metrics()
        self.ship_lost: Dict[str, float] = default_metrics()
        self.isk_destroyed: Dict[str, float] = default_metrics()
        self.isk_lost: Dict[str, float] = default_metrics()

        # Sliding window history: (event_date, isk, is_victim)
        self.km_history: deque[Tuple[date, float, bool]] = deque()

    def clear_old_km(self, current_day: date):
        while self.km_history:
            event_date, isk, is_victim = self.km_history[0]
            age_days = (current_day - event_date).days

            if age_days > 30:
                self.km_history.popleft()
                if is_victim:
                    self.ship_lost["30d"] = max(0.0, self.ship_lost["30d"] - 1.0)
                    self.isk_lost["30d"] = max(0.0, self.isk_lost["30d"] - isk)
                else:
                    self.ships_destroyed["30d"] = max(0.0, self.ships_destroyed["30d"] - 1.0)
                    self.isk_destroyed["30d"] = max(0.0, self.isk_destroyed["30d"] - isk)
            else:
                break

        self._recalculate_7d(current_day)

    def _recalculate_7d(self, current_day: date):
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
        self.clear_old_km(day)

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