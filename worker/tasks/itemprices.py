# worker/tasks/itemprices.py
import json
import time
from datetime import date, timedelta
from pathlib import Path

from shared.zkillphone import ZkillPhone
from shared.config import PRICES_DIR, logger
from shared.static_loader import load_types

# Price init file. Tracks the last update and uninformative ids
price_init_file = PRICES_DIR / "_init_.json"
key_date = 'last_updated'
key_ignores = 'ignores'

outdated_after_days = 7         # Consider Itemprice history outdated after 7 days
download_delay_seconds = 5.0    # download maximum every 5 seconds

def init_prices():
    """
    On boot, runs the download once if outdated or not initiated.
    """
    PRICES_DIR.mkdir(parents=True, exist_ok=True)
    
    item_ids = load_types()
    assert item_ids and len(item_ids) > 0, "FAULTY ITEM IDS LOADED"

    # Initiate Prices
    if not price_init_file.exists() or is_priceinit_outdated():
        logger.info(f"STARTING: Init Prices - n:{len(item_ids)}")
        download_all_item_prices(item_ids)
        logger.info(f"FINISH: Init Prices - n:{len(item_ids)}")
    return


def download_price(item_id: int | str, filepath: Path):
    """
    Download price history of a specific item
    """
    PRICES_DIR.mkdir(parents=True, exist_ok=True)
    price_data = ZkillPhone.fetch_price_history(item_id)
    with filepath.open("w", encoding="utf-8") as file:
        json.dump(price_data, file, indent=4)
    return price_data


def is_priceinit_outdated():
    if not price_init_file.exists():
        return True
    
    with open(price_init_file, 'r') as file:
        data = json.load(file)
    last_date = date.fromisoformat(data[key_date])
    return date.today() - last_date > timedelta(days=outdated_after_days)


def get_ignored_prices():
    if not price_init_file.exists():
        return []

    with open(price_init_file, 'r') as file:
        data = json.load(file)
    return data[key_ignores]


def update_init_file(init_data : dict):
    with open(price_init_file, 'w') as file:
        json.dump(init_data, file, default=date.isoformat, indent=4)
    return


def download_all_item_prices(ids : list):
    today_date = date.today()
    to_ignore : list = get_ignored_prices()

    # Iterate over items and download.
    for i_id in ids:
        if i_id not in to_ignore:
            #Download politely
            filepath = PRICES_DIR / f"{i_id}.json"
            item_price_history : dict = download_price(i_id, filepath)
            logger.info(f"DOWNLOADED: Item Price History: {i_id}")
            time.sleep(download_delay_seconds)

            # If item has no historic data
            if len(item_price_history.keys()) == 1:
                to_ignore.append(i_id)
    
    new_init_dicts = {
        key_date : date(today_date.year, today_date.month, today_date.day),
        key_ignores : to_ignore
    }
    update_init_file(new_init_dicts)
    return


def update_prices():
    if is_priceinit_outdated():
        item_ids = load_types()
        assert item_ids and len(item_ids) > 0, "FAULTY ITEM IDS LOADED"

        logger.info(f"STARTING: Updating Item Prices - n:{len(item_ids)}")
        download_all_item_prices(item_ids)
        logger.info(f"FINISHED: Updating Item Prices - n:{len(item_ids)}")
    return