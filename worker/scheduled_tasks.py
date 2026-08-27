# worker/scheduled_tasks.py
from datetime import date, timedelta, datetime
import json
from pathlib import Path
import random
import requests
import shutil
import time

from shared.zkillphone import ZkillPhone
from shared.config import STATIC_DIR


###########################
# PATHS / CONSTANTS
###########################



DOWNLOAD_DIR = STATIC_DIR / "killmail_history"
PRICE_DIR = STATIC_DIR / "Prices"
EVE_STATIC_DATA_DIR = STATIC_DIR / "eve-online-static-data"

ZKILL_BASE = "https://r2z2.zkillboard.com/history/raw"
START_DATE = date(2007, 12, 5)


###########################
# KILLS UPDATER
###########################

def get_last_date() -> date | None:
    zkill_dir = DOWNLOAD_DIR / "zkill"

    files = sorted(zkill_dir.rglob("*.json"))

    if not files:
        zips = sorted(zkill_dir.rglob("*.zip"))

        if zips:
            year_str = zips[-1].stem
            year_end = date(int(year_str), 12, 31)
            return year_end + timedelta(days=1)

        return START_DATE - timedelta(days=1)

    latest = files[-1].stem

    return date(
        int(latest[:4]),
        int(latest[4:6]),
        int(latest[6:8]),
    )


def update_zkill_killmails():
    t = random.random()
    time.sleep(10.0 * t)

    end_date = date.today() - timedelta(days=1)
    last_date = get_last_date()

    if last_date >= end_date:
        return

    print("Updating Killmails")

    next_date = last_date + timedelta(days=1)

    download_zkill_killmails(next_date)


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

    zkill_dir = DOWNLOAD_DIR / "zkill"

    if not zkill_dir.exists() or not zkill_dir.is_dir():
        return

    year_folders = [
        d
        for d in zkill_dir.iterdir()
        if d.is_dir() and d.name.isdigit()
    ]

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


def download_zkill_killmails(dt: date):
    filename = f"{dt.year}{dt.month:02d}{dt.day:02d}.json"

    url = f"{ZKILL_BASE}/{filename}"

    year_dir = DOWNLOAD_DIR / "zkill" / str(dt.year)
    year_dir.mkdir(parents=True, exist_ok=True)

    filepath = year_dir / filename

    if filepath.exists():
        print(f"zKill {filename} already exists, skipping")
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

    data = load_types()

    PRICE_DIR.mkdir(parents=True, exist_ok=True)

    last_date = datetime.now() - timedelta(days=1)
    last_date_str = last_date.strftime("%Y-%m-%d")

    for type_id in data:
        file_path = PRICE_DIR / f"{type_id}.json"

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