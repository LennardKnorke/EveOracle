# worker/scheduled_tasks.py
from datetime import date, timedelta, datetime
import json
from pathlib import Path
import random
import requests
import shutil
import time

from shared.zkillphone import ZkillPhone
from shared.config import STATIC_DIR, PRICES_DIR, KILLMAILS_DIR, SHIP_FILE, SHIP_STATS_DIR


###########################
# PATHS / CONSTANTS
###########################
EVE_STATIC_DATA_DIR = STATIC_DIR / "eve-online-static-data"

ZKILL_BASE = "https://r2z2.zkillboard.com/history/raw"
START_DATE = date(2007, 12, 5)


###########################
# KILLS UPDATER
###########################

def get_last_date() -> date | None:
    if not KILLMAILS_DIR.exists():
        return START_DATE - timedelta(days=1)
    
    files = sorted(KILLMAILS_DIR.rglob("*.json"))
    valid_date_files = []

    for f in files:
        clean = f.stem.replace("-", "").replace("_", "")
        if len(clean) >= 8 and clean[:8].isdigit():
            valid_date_files.append(clean[:8])

    if not valid_date_files:
        zips = sorted(KILLMAILS_DIR.rglob("*.zip"))
        if zips:
            year_str = zips[-1].stem
            if year_str.isdigit():
                year_end = date(int(year_str), 12, 31)
                return year_end + timedelta(days=1)
        return START_DATE - timedelta(days=1)

    latest = valid_date_files[-1]
    return date(int(latest[:4]), int(latest[4:6]), int(latest[6:8]))



def update_zkill_killmails():
    t = random.random()
    time.sleep(5.0 * t)

    end_date = date.today() - timedelta(days=1)
    last_date = get_last_date()

    if last_date >= end_date:
        return

    print(f"Updating Killmails from {last_date + timedelta(days=1)} to {end_date}")
    next_date = last_date + timedelta(days=1)
    download_zkill_killmails(next_date)
    return


def zip_folder(folder: Path) -> bool:
    if not folder.exists() or not folder.is_dir():
        return False

    zip_path = folder.with_suffix(".zip")

    if zip_path.exists():
        shutil.rmtree(folder)
        return True

    shutil.make_archive(
        base_name=str(folder),
        format="zip",
        root_dir=folder.parent,
        base_dir=folder.name,
    )

    shutil.rmtree(folder)
    return True


def compress_oldest_zkill_year():
    """Zip the earliest completed year folder in the zKill download dir."""
    if not KILLMAILS_DIR.exists() or not KILLMAILS_DIR.is_dir():
        return

    year_folders = [d for d in KILLMAILS_DIR.iterdir() if d.is_dir() and d.name.isdigit()]

    if not year_folders:
        return

    year_folders.sort(key=lambda p: int(p.name))
    oldest = year_folders[0]
    year = int(oldest.name)

    last_date = get_last_date()
    if last_date < date(year, 12, 31):
        return

    print(f"Zipping completed zKill year: {year}")
    zip_folder(oldest)
    return


def download_zkill_killmails(dt: date):
    filename = f"{dt.year}{dt.month:02d}{dt.day:02d}.json"

    url = f"{ZKILL_BASE}/{filename}"

    year_dir = KILLMAILS_DIR / str(dt.year)
    year_dir.mkdir(parents=True, exist_ok=True)

    filepath = year_dir / filename

    if filepath.exists():
        return

    try:
        headers = {
            "Accept-Encoding": "gzip",
            "User-Agent": "EveOracle",
            "content-type": "application/json",
        }

        req = requests.get(
            url=url,
            headers=headers,
            timeout=60,
        )
        req.raise_for_status()
        data = req.json()

        with filepath.open("w") as f:
            json.dump(data, f, indent=4)
        print(f"Fetched Killmails from {dt}")
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            print(f"Missing: {filename}")
        else:
            print(f"HTTP error: {filename}: {e}")
    except Exception as e:
        print(f"Failed {filename}: {e}")



###########################
# SHIP STATS UPDATER
###########################
def update_ship_stats():
    """
    Checks once an hour if ship stats have been updated today.
    Fetches global zKill stats for all ships in ships.json after 14:00 (2 PM).
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # Run check primarily around/after 14:00 (1 hour after downtime)
    if now.hour < 14:
        return

    if not SHIP_FILE.exists():
        print(f"[WARN] ships.json not found at: {SHIP_FILE}")
        return

    SHIP_STATS_DIR.mkdir(parents=True, exist_ok=True)

    with open(SHIP_FILE, "r", encoding="utf-8") as f:
        ships_data = json.load(f)

    ship_ids = list(ships_data.keys())
    print(f"Checking ship stats update for {len(ship_ids)} hulls...")

    updated_count = 0
    for ship_id in ship_ids:
        stat_file = SHIP_STATS_DIR / f"{ship_id}.json"

        # Check if already updated today
        if stat_file.exists():
            mod_time = datetime.fromtimestamp(stat_file.stat().st_mtime)
            if mod_time.strftime("%Y-%m-%d") == today_str:
                continue

        try:
            stats = ZkillPhone.fetch_statistics("shipTypeID", str(ship_id))
            with open(stat_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)

            updated_count += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"Failed to update ship {ship_id}: {e}")

    if updated_count > 0:
        print(f"Updated zKill stats for {updated_count} ships.")


###########################
# PRICE UPDATER
###########################

def load_categories():
    path = EVE_STATIC_DATA_DIR / "categories.jsonl"

    allowed_categories = [
        "Material",
        "Accessories",
        "Ship",
        "Module",
        "Charge",
        "Drone",
        "Fighter",
        "Blueprint",
        "Trading",
        "Skill",
        "Implant",
        "Deployable",
        "Reaction",
        "Subsystem",
        "Decryptors",
        "Infrastructure Upgrades",
        "Planetary Industry",
        "Planetary Resources",
        "Planetary Commodities",
        "Placeables",
        "Cells",
        "Structure Module",
        "SKIN",
        "Colony Resources",
    ]

    allowed = {}

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            obj = json.loads(line)

            name = obj["name"]["en"]

            if name in allowed_categories:
                obj["name"] = name
                allowed[obj["_key"]] = obj

    return allowed if allowed else None


def load_groups(allowed_categories: dict):
    path = EVE_STATIC_DATA_DIR / "groups.jsonl"

    allowed = {}

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            obj = json.loads(line)

            if obj["categoryID"] in allowed_categories:
                name = obj["name"]["en"]

                obj["name"] = name
                allowed[obj["_key"]] = obj

    return allowed if allowed else None


def load_types():
    cats = load_categories()

    assert cats is not None, (
        "Something went wrong when loading categories"
    )

    grp = load_groups(cats)

    assert grp is not None, (
        "Something went wrong when loading groups"
    )

    def entry_is_valid_type(entry: dict) -> bool:
        entry_groupid = entry.get("groupID")

        if entry_groupid not in grp:
            return False

        if entry.get("basePrice", False) == False:
            return False

        return True

    data = {}

    path = EVE_STATIC_DATA_DIR / "types.jsonl"

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            obj = json.loads(line)

            if not entry_is_valid_type(obj):
                continue

            name = obj["name"]["en"]
            obj["name"] = name

            key = obj["_key"]

            if "description" in obj:
                obj["description"] = obj["description"]["en"]

            data[key] = obj

    print(f"Loaded {len(data)} types.")

    return data


def update_prices():
    print("Updating Prices")
    PRICES_DIR.mkdir(parents=True, exist_ok=True)

    data = load_types()

    last_date = datetime.now() - timedelta(days=1)
    last_date_str = last_date.strftime("%Y-%m-%d")

    for type_id in data:
        file_path = PRICES_DIR / f"{type_id}.json"

        if file_path.exists():
            with file_path.open("r") as file:
                file_data = json.load(file)

            if last_date_str in file_data:
                continue

        try:
            price_data = ZkillPhone.fetch_price_history(type_id)

            with file_path.open("w") as file:
                json.dump(price_data, file, indent=4)

            time.sleep(0.2)

        except requests.RequestException as e:
            print(f"Failed to fetch {type_id}: {e}")


def update_ship_stats():

    return