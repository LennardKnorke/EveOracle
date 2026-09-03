# backend/app/routers/ship.py

import json
from typing import List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from shared.config import SHIP_FILE, SHIP_STATS_DIR

router = APIRouter(prefix="/ship", tags=["Ships"])


class ShipStatsBatchRequest(BaseModel):
    ship_ids: List[int | str]


def load_all_ships_dogma() -> Dict[str, Any]:
    if not SHIP_FILE.exists():
        return {}
    with open(SHIP_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/stats")
async def get_batch_ship_stats(body: ShipStatsBatchRequest):
    """
    Returns dogma attributes and global zKillboard statistics for a list of ship IDs.
    """
    ships_dogma = load_all_ships_dogma()
    results = {}

    for sid in body.ship_ids:
        s_str = str(sid)
        dogma = ships_dogma.get(s_str, {})

        # Check cached zKill stats from worker
        zkill_stats = {}
        stat_file = SHIP_STATS_DIR / f"{s_str}.json"
        if stat_file.exists():
            try:
                with open(stat_file, "r", encoding="utf-8") as f:
                    zkill_stats = json.load(f)
            except Exception:
                pass

        results[s_str] = {
            "ship_id": int(sid),
            "name": dogma.get("name", f"Ship {sid}"),
            "shipClass": dogma.get("shipClass", "Unknown"),
            "faction": dogma.get("faction", "Unknown"),
            "attributes": dogma.get("attributes", {}),
            "zkill_stats": zkill_stats,
        }

    return results