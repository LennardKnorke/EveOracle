# worker/tasks/shipstats.py

import json
import time
from datetime import date, timedelta
from pathlib import Path

from shared.zkillphone import ZkillPhone
from shared.config import SHIP_STATS_DIR, logger
from shared.static_loader import load_ship_ids


ship_init_file = SHIP_STATS_DIR / "_init_.json"
key_date = 'last_updated'
outdated_after_days = 7
download_delay_seconds = 5.0    # download maximum every 5 seconds

def init_shipstats():
    SHIP_STATS_DIR.mkdir(parents=True, exist_ok=True)

    ship_ids = load_ship_ids()
    assert ship_ids and len(ship_ids) > 0, "SOMETHING WENT WRONG LOADING SHIP IDS"


    if not ship_init_file.exists() or is_shipinit_outdated():
        logger.info("STARTING: Init Ship Stats")
        
        for id in ship_ids:
            stats = download_ship_stats(id)
            logger.info(f"DOWNLOADED: Ship Stats: {id}")
            time.sleep(download_delay_seconds)
        update_init_file()
        logger.info("FINISH: Init Ship Stats")
    return


def download_ship_stats(ship_typeid: int | str):
    SHIP_STATS_DIR.mkdir(parents=True, exist_ok=True)
    stat_file = SHIP_STATS_DIR / f"{ship_typeid}.json"
    stats = ZkillPhone.fetch_statistics("shipTypeID", str(ship_typeid))
    with open(stat_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    return stats


def is_shipinit_outdated():
    if not ship_init_file.exists():
        return True
    
    with open(ship_init_file, 'r') as file:
        data = json.load(file)
    last_date = date.fromisoformat(data[key_date])
    return date.today() - last_date > timedelta(days=outdated_after_days)

def update_init_file():
    data = {key_date : date.today()}
    with open(ship_init_file, 'w') as file:
        json.dump(data, file, default=date.isoformat, indent=4)
    return


def update_ship_stats():
    if is_shipinit_outdated():
        ship_ids = load_ship_ids()
        assert ship_ids and len(ship_ids) > 0, "SOMETHING WENT WRONG LOADING SHIP IDS"

        logger.info(f"STARTING: Updating Ship Stats - n:{len(ship_ids)}")
        
        for id in ship_ids:
            stats = download_ship_stats(id)
            logger.info(f"DOWNLOADED: Ship Stats: {id}")
            time.sleep(download_delay_seconds)
        update_init_file()
        logger.info(f"FINISH: Updating Ship Stats - n:{len(ship_ids)}")