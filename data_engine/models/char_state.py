# data_engine/models/char_state.py

from typing import Dict, Optional


class CharEntry:
    """
    Ultra-compact in-memory representation of lifetime pilot statistics.
    Uses __slots__ to eliminate Python dict overhead per instance.
    """
    __slots__ = (
        "id",
        "kills_total",
        "losses_total",
        "isk_destroyed_total",
        "isk_lost_total",
        "solo_kills",
        "solo_losses",
        "total_attacker_sum",
        "hull_kills",
        "hull_losses",
    )

    def __init__(self, char_id: int | str):
        self.id = int(char_id)
        self.kills_total: float = 0.0
        self.losses_total: float = 0.0
        self.isk_destroyed_total: float = 0.0
        self.isk_lost_total: float = 0.0
        self.solo_kills: int = 0
        self.solo_losses: int = 0
        self.total_attacker_sum: int = 0

        # Sparse per-hull counts { ship_id: count } (None until first kill/loss)
        self.hull_kills: Optional[Dict[int, int]] = None
        self.hull_losses: Optional[Dict[int, int]] = None

    def record_kill(self, isk: float, is_solo: bool, gang_size: int, ship_id: int = -1):
        self.kills_total += 1.0
        self.isk_destroyed_total += isk
        self.total_attacker_sum += max(1, gang_size)
        if is_solo:
            self.solo_kills += 1

        if ship_id > 0:
            if self.hull_kills is None:
                self.hull_kills = {}
            self.hull_kills[ship_id] = self.hull_kills.get(ship_id, 0) + 1

    def record_loss(self, isk: float, is_solo: bool, ship_id: int = -1):
        self.losses_total += 1.0
        self.isk_lost_total += isk
        if is_solo:
            self.solo_losses += 1

        if ship_id > 0:
            if self.hull_losses is None:
                self.hull_losses = {}
            self.hull_losses[ship_id] = self.hull_losses.get(ship_id, 0) + 1

    def get_features(
        self,
        ship_id: Optional[int] = None,
        recent: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """
        Combines lifetime totals with sliding 7d/30d metrics for dataset export.
        """
        rec = recent or {}
        total_fights = self.kills_total + self.losses_total

        # Danger Ratio (%): (Kills / (Kills + Losses)) * 100
        danger_ratio = (self.kills_total / total_fights * 100.0) if total_fights > 0 else 50.0

        # Average Gang Size
        avg_gang_size = (self.total_attacker_sum / self.kills_total) if self.kills_total > 0 else 1.0

        # Solo / Gang Ratios (%)
        solo_ratio = (self.solo_kills / self.kills_total * 100.0) if self.kills_total > 0 else 0.0
        gang_ratio = 100.0 - solo_ratio

        # Hull Specific Counts
        hk_total = self.hull_kills.get(ship_id, 0) if (self.hull_kills and ship_id) else 0
        hl_total = self.hull_losses.get(ship_id, 0) if (self.hull_losses and ship_id) else 0

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
            # zKillboard Behavioral Metrics
            "char_danger_ratio": float(danger_ratio),
            "char_avg_gang_size": float(avg_gang_size),
            "char_solo_ratio": float(solo_ratio),
            "char_gang_ratio": float(gang_ratio),
            "char_solo_kills": float(self.solo_kills),
            "char_solo_losses": float(self.solo_losses),
            # Hull Specific Metrics
            "char_hull_kills_total": float(hk_total),
            "char_hull_losses_total": float(hl_total),
        }