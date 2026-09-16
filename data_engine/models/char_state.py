# data_engine/models/char_state.py

from datetime import date
from typing import Dict, Optional


class CharEntry:
    __slots__ = (
        "id",
        "kills_total",
        "losses_total",
        "isk_destroyed_total",
        "isk_lost_total",
        "points_destroyed_total",
        "points_lost_total",
        "solo_kills",
        "solo_losses",
        "fights_solo",
        "fights_small_gang",
        "fights_fleet_blob",
        "total_attacker_sum",
        "first_seen_date",
        "last_active_date",
        "hull_kills",
        "hull_losses",
        "hull_isk_destroyed",
        "hull_isk_lost",
    )

    def __init__(self, char_id: int | str):
        self.id = int(char_id)
        self.kills_total: float = 0.0
        self.losses_total: float = 0.0
        self.isk_destroyed_total: float = 0.0
        self.isk_lost_total: float = 0.0
        self.points_destroyed_total: float = 0.0
        self.points_lost_total: float = 0.0

        self.solo_kills: int = 0
        self.solo_losses: int = 0
        self.fights_solo: int = 0
        self.fights_small_gang: int = 0
        self.fights_fleet_blob: int = 0
        self.total_attacker_sum: int = 0

        self.first_seen_date: Optional[date] = None
        self.last_active_date: Optional[date] = None

        # Sparse hull tracking { ship_id: value }
        self.hull_kills: Optional[Dict[int, int]] = None
        self.hull_losses: Optional[Dict[int, int]] = None
        self.hull_isk_destroyed: Optional[Dict[int, float]] = None
        self.hull_isk_lost: Optional[Dict[int, float]] = None

    def record_kill(
        self,
        isk: float,
        points: float,
        is_solo: bool,
        gang_size: int,
        day: date,
        ship_id: int = -1,
    ):
        if self.first_seen_date is None:
            self.first_seen_date = day
        self.last_active_date = day

        self.kills_total += 1.0
        self.isk_destroyed_total += isk
        self.points_destroyed_total += points
        self.total_attacker_sum += max(1, gang_size)

        if is_solo or gang_size == 1:
            self.solo_kills += 1
            self.fights_solo += 1
        elif 2 <= gang_size <= 9:
            self.fights_small_gang += 1
        else:
            self.fights_fleet_blob += 1

        if ship_id > 0:
            if self.hull_kills is None:
                self.hull_kills = {}
                self.hull_isk_destroyed = {}
            self.hull_kills[ship_id] = self.hull_kills.get(ship_id, 0) + 1
            self.hull_isk_destroyed[ship_id] = self.hull_isk_destroyed.get(ship_id, 0.0) + isk

    def record_loss(
        self,
        isk: float,
        points: float,
        is_solo: bool,
        day: date,
        ship_id: int = -1,
    ):
        if self.first_seen_date is None:
            self.first_seen_date = day
        self.last_active_date = day

        self.losses_total += 1.0
        self.isk_lost_total += isk
        self.points_lost_total += points

        if is_solo:
            self.solo_losses += 1

        if ship_id > 0:
            if self.hull_losses is None:
                self.hull_losses = {}
                self.hull_isk_lost = {}
            self.hull_losses[ship_id] = self.hull_losses.get(ship_id, 0) + 1
            self.hull_isk_lost[ship_id] = self.hull_isk_lost.get(ship_id, 0.0) + isk

    def get_features(
        self,
        current_date: date,
        ship_id: Optional[int] = None,
        recent: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        rec = recent or {}
        total_fights = self.kills_total + self.losses_total
        total_points = self.points_destroyed_total + self.points_lost_total

        # Point-Based Danger Ratio (Exact zKillboard formulation)
        if total_points > 0:
            danger_ratio = (self.points_destroyed_total / total_points) * 100.0
        elif total_fights > 0:
            danger_ratio = (self.kills_total / total_fights) * 100.0
        else:
            danger_ratio = 50.0

        # Average Gang Size
        avg_gang = (self.total_attacker_sum / self.kills_total) if self.kills_total > 0 else 1.0

        # Combat Scale Distribution (%)
        pct_solo = (self.fights_solo / self.kills_total * 100.0) if self.kills_total > 0 else 0.0
        pct_small = (self.fights_small_gang / self.kills_total * 100.0) if self.kills_total > 0 else 0.0
        pct_blob = (self.fights_fleet_blob / self.kills_total * 100.0) if self.kills_total > 0 else 0.0

        # Temporal Readiness & Pilot Age
        days_since_active = (current_date - self.last_active_date).days if self.last_active_date else 365.0
        pilot_age_days = (current_date - self.first_seen_date).days if self.first_seen_date else 0.0

        # Hull Specific Records
        hk_total = self.hull_kills.get(ship_id, 0) if (self.hull_kills and ship_id) else 0
        hl_total = self.hull_losses.get(ship_id, 0) if (self.hull_losses and ship_id) else 0
        h_isk_k = self.hull_isk_destroyed.get(ship_id, 0.0) if (self.hull_isk_destroyed and ship_id) else 0.0
        h_isk_l = self.hull_isk_lost.get(ship_id, 0.0) if (self.hull_isk_lost and ship_id) else 0.0

        return {
            "char_kills_total": float(self.kills_total),
            "char_kills_7d": float(rec.get("kills_7d", 0.0)),
            "char_kills_30d": float(rec.get("kills_30d", 0.0)),
            "char_losses_total": float(self.losses_total),
            "char_losses_7d": float(rec.get("losses_7d", 0.0)),
            "char_losses_30d": float(rec.get("losses_30d", 0.0)),
            "char_isk_destroyed_total": float(self.isk_destroyed_total),
            "char_isk_destroyed_7d": float(rec.get("isk_destroyed_7d", 0.0)),
            "char_isk_destroyed_30d": float(rec.get("isk_destroyed_30d", 0.0)),
            "char_isk_lost_total": float(self.isk_lost_total),
            "char_isk_lost_7d": float(rec.get("isk_lost_7d", 0.0)),
            "char_isk_lost_30d": float(rec.get("isk_lost_30d", 0.0)),
            # zKillboard Point & Gang Distribution
            "char_danger_ratio": float(danger_ratio),
            "char_avg_gang_size": float(avg_gang),
            "char_pct_solo": float(pct_solo),
            "char_pct_small_gang": float(pct_small),
            "char_pct_blob": float(pct_blob),
            "char_solo_kills": float(self.solo_kills),
            "char_solo_losses": float(self.solo_losses),
            # Temporal Profile
            "char_days_since_active": float(max(0.0, days_since_active)),
            "char_pilot_age_days": float(max(0.0, pilot_age_days)),
            # Hull Specific Metrics
            "char_hull_kills_total": float(hk_total),
            "char_hull_losses_total": float(hl_total),
            "char_hull_isk_destroyed": float(h_isk_k),
            "char_hull_isk_lost": float(h_isk_l),
        }