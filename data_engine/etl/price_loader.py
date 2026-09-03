# data_engine/etl/price_loader.py

import json
from pathlib import Path
from typing import Dict, Any, Optional
from shared.config import PRICES_DIR


class ItemPriceLoader:
    def __init__(self):
        self.prices_dir = PRICES_DIR
        self._price_cache: Dict[int, Dict[str, float]] = {}
        self._missing_items: set[int] = set()

    def _load_item_history(self, item_type_id: int | str) -> Dict[str, float]:
        try:
            tid = int(item_type_id)
        except (ValueError, TypeError):
            return {}

        if tid in self._price_cache:
            return self._price_cache[tid]

        if tid in self._missing_items:
            return {}

        price_file = self.prices_dir / f"{tid}.json"
        if not price_file.exists():
            self._missing_items.add(tid)
            return {}

        try:
            with open(price_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            history: Dict[str, float] = {}
            for date_key, val in raw_data.items():
                if isinstance(val, (int, float)):
                    history[str(date_key)] = float(val)
                elif isinstance(val, dict):
                    p = val.get("average") or val.get("price") or val.get("adjusted") or 0.0
                    history[str(date_key)] = float(p)

            self._price_cache[tid] = history
            return history
        except Exception:
            self._missing_items.add(tid)
            return {}

    def get_price(self, item_type_id: int | str, date_str: str) -> Optional[float]:
        history = self._load_item_history(item_type_id)
        if not history:
            return None

        if date_str in history:
            return history[date_str]

        alt_date = date_str.replace("-", "")
        if alt_date in history:
            return history[alt_date]

        return None

    def estimate_killmail_isk(self, km: Dict[str, Any], date_str: str) -> float:
        # Fast path: Use zKillboard precalculated totalValue if present (>95% of kills)
        zkb = km.get("zkb", {})
        if "totalValue" in zkb and zkb["totalValue"] > 0:
            return float(zkb["totalValue"])

        total_isk = 0.0
        victim = km.get("victim", {})

        # 1. Hull value
        ship_id = victim.get("ship_type_id")
        if ship_id:
            ship_price = self.get_price(ship_id, date_str)
            if ship_price:
                total_isk += ship_price

        # 2. Items & Cargo
        for item in victim.get("items", []):
            item_id = item.get("item_type_id")
            qty_dest = item.get("quantity_destroyed") or 0
            qty_drop = item.get("quantity_dropped") or 0
            qty = qty_dest + qty_drop

            if item_id:
                item_price = self.get_price(item_id, date_str)
                if item_price:
                    total_isk += item_price * max(qty, 1)

        return max(total_isk, 1_000_000.0)