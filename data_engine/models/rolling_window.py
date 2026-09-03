# data_engine/models/rolling_window.py

from collections import deque
from datetime import date
from typing import Dict, Tuple, List


class DailyCharBucket:
    __slots__ = ("kills", "losses", "isk_destroyed", "isk_lost")

    def __init__(self):
        self.kills: float = 0.0
        self.losses: float = 0.0
        self.isk_destroyed: float = 0.0
        self.isk_lost: float = 0.0


class GlobalRollingWindowManager:
    """
    Maintains a global 30-day ring buffer of daily combat summaries.
    Provides fast O(1) 7d and 30d lookups only for pilots active this month.
    """
    def __init__(self):
        # deque of (bucket_date, { char_id: DailyCharBucket })
        self.daily_buckets: deque[Tuple[date, Dict[int, DailyCharBucket]]] = deque()
        self.current_day: date | None = None
        self.current_day_bucket: Dict[int, DailyCharBucket] = {}

    def advance_day(self, new_day: date):
        """Flushes previous day's bucket and evicts buckets older than 30 days."""
        if self.current_day is not None and self.current_day != new_day:
            if self.current_day_bucket:
                self.daily_buckets.append((self.current_day, self.current_day_bucket))
                self.current_day_bucket = {}

            # Evict buckets older than 30 days
            while self.daily_buckets:
                b_date, _ = self.daily_buckets[0]
                if (new_day - b_date).days > 30:
                    self.daily_buckets.popleft()
                else:
                    break

        self.current_day = new_day

    def record_kill(self, char_id: int, isk_destroyed: float):
        bucket = self.current_day_bucket.setdefault(char_id, DailyCharBucket())
        bucket.kills += 1.0
        bucket.isk_destroyed += isk_destroyed

    def record_loss(self, char_id: int, isk_lost: float):
        bucket = self.current_day_bucket.setdefault(char_id, DailyCharBucket())
        bucket.losses += 1.0
        bucket.isk_lost += isk_lost

    def get_recent_stats(self, char_id: int, target_day: date) -> Dict[str, float]:
        """
        Sums rolling 7d and 30d activity across active buckets for a pilot.
        """
        k_7d, k_30d = 0.0, 0.0
        l_7d, l_30d = 0.0, 0.0
        isk_k_7d, isk_k_30d = 0.0, 0.0
        isk_l_7d, isk_l_30d = 0.0, 0.0

        # Include today's active bucket
        today_data = self.current_day_bucket.get(char_id)
        if today_data:
            k_7d += today_data.kills
            k_30d += today_data.kills
            l_7d += today_data.losses
            l_30d += today_data.losses
            isk_k_7d += today_data.isk_destroyed
            isk_k_30d += today_data.isk_destroyed
            isk_l_7d += today_data.isk_lost
            isk_l_30d += today_data.isk_lost

        # Sum past 30 days from ring buffer
        for b_date, b_dict in self.daily_buckets:
            p_data = b_dict.get(char_id)
            if not p_data:
                continue

            age = (target_day - b_date).days
            if age <= 30:
                k_30d += p_data.kills
                l_30d += p_data.losses
                isk_k_30d += p_data.isk_destroyed
                isk_l_30d += p_data.isk_lost

                if age <= 7:
                    k_7d += p_data.kills
                    l_7d += p_data.losses
                    isk_k_7d += p_data.isk_destroyed
                    isk_l_7d += p_data.isk_lost

        return {
            "kills_7d": k_7d,
            "kills_30d": k_30d,
            "losses_7d": l_7d,
            "losses_30d": l_30d,
            "isk_destroyed_7d": isk_k_7d,
            "isk_destroyed_30d": isk_k_30d,
            "isk_lost_7d": isk_l_7d,
            "isk_lost_30d": isk_l_30d,
        }