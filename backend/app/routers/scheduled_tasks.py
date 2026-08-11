# backend/app/routers/scheduled_tasks.py

from datetime import date, timedelta, datetime
import json
from pathlib import Path
import random
import requests
import shutil
import time
from urllib.request import urlretrieve
from urllib.error import HTTPError
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.services.esi_api_interface import ZkillPhone



###########################
## KILLS UPDATER
###########################
ZKILL_BASE = "https://r2z2.zkillboard.com/history/raw"
START_DATE = date(2007, 12, 5)

scheduler = BackgroundScheduler(
    timezone=ZoneInfo("Europe/Amsterdam")
)


download_dir = Path("static/killmail_history")
download_dir.mkdir(exist_ok=True)

def get_last_date() -> None|date:
    dir = download_dir / "zkill"
    files = sorted(dir.rglob("*.json"))

    # No files?
    if not files:
        zips = sorted(dir.rglob("*.zip"))

        # Is it 01.01.xxxx? and everything is zipped?
        if zips:
            year_str = zips[-1].stem
            year_end = date(int(year_str), 12, 31)
            return year_end + timedelta(days=1)

        return START_DATE - timedelta(days=1)
    
    latest = files[-1].stem
    return date(int(latest[:4]), int(latest[4:6]), int(latest[6:8]))



def update_zkill_killmails():
    
    t = random.random()
    time.sleep(10.0 * t)
    end_date = date.today() - timedelta(days=1)  # zkill also lags
    last_date = get_last_date()

    if last_date >= end_date:
        return
    print("Updating Killmails")
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
    """Zip the earliest completed year folder in the zkill download dir."""
    zkill_dir = download_dir / "zkill"
    if not zkill_dir.exists() or not zkill_dir.is_dir():
        return

    # Find all year folders (numeric directory names)
    year_folders = [
        d for d in zkill_dir.iterdir()
        if d.is_dir() and d.name.isdigit()
    ]
    if not year_folders:
        return

    # Sort by year number — earliest first
    year_folders.sort(key=lambda p: int(p.name))
    oldest = year_folders[0]
    year = int(oldest.name)

    # Safety: only zip years that are fully downloaded.
    last_date = get_last_date()
    if last_date < date(year, 12, 31):
        return

    print(f"Zipping completed zkill year: {year}")
    zip_folder(oldest)
    return



def download_zkill_killmails(dt : date):
    filename = f"{dt.year}{dt.month:02d}{dt.day:02d}.json"
    url = f"{ZKILL_BASE}/{filename}"
    year_dir = download_dir / "zkill" / str(dt.year)
    year_dir.mkdir(parents=True, exist_ok=True)
    filepath = year_dir / filename

    # RETRIEVE
    if filepath.exists():
        print(f"zKill {filename} already exists, skipping")
        return

    try:
        headers = {
            "Accept-Encoding": "gzip",
            "User-Agent": "EveOracle",
            "content-type" : "application/json"
        }
        req = requests.get(url=url, headers=headers)
        data = req.json()
        with open(filepath, 'w') as f:
            json.dump(data, fp=f,indent=4)
        print(f"Fetched Killmails from {dt}")
    except HTTPError as e:
        if e.code == 404:
            print(f"Missing: {filename}")
        else:
            print(f"HTTP {e.code}: {filename}")
    except Exception as e:
        print(f"Failed {filename}: {e}")

    return



scheduler.add_job(
    update_zkill_killmails, 
    #IntervalTrigger(minutes=1),
    IntervalTrigger(seconds=20),
    max_instances=1,
    coalesce=True,
    misfire_grace_time=1
)

scheduler.add_job(
    compress_oldest_zkill_year,
    IntervalTrigger(minutes=5),   # adjust frequency as needed
    max_instances=1,
    coalesce=True,
    misfire_grace_time=300
)




###########################
## PRICE UPDATER
###########################
def load_categories():
    path = Path("static/eve-online-static-data/categories.jsonl")
    
    allowed_categories = [
        "Material", "Accessories", 
        "Ship", "Module", "Charge", "Drone", "Fighter",
        "Blueprint", "Trading",
        "Skill", "Implant", "Deployable",
        "Reaction", "Subsystem", "Decryptors",
        "Infrastructure Upgrades", 
        "Planetary Industry", "Planetary Resources", "Planetary Commodities",
        "Placeables", "Cells", "Structure Module",
        "SKIN", "Colony Resources",
    ]

    allowed = {}
    with open(path, 'r', encoding='utf-8') as file:
        for line in file:
            if line.strip():
                obj = json.loads(line)
                name = obj['name']['en']
                if name in allowed_categories:  
                    obj['name'] = name
                    allowed[obj['_key']] = obj

    return allowed if len(allowed.keys()) > 0 else None


def load_groups(allowed_categories : dict):
    path = Path("static/eve-online-static-data/groups.jsonl")
    
    allowed = {}
    with open(path, 'r', encoding='utf-8') as file:
        for line in file:
            if line.strip():
                obj = json.loads(line)
                
                
                if obj['categoryID'] in allowed_categories.keys():
                    name = obj['name']['en']
                    obj['name'] = name
                    allowed[obj['_key']] = obj
    return allowed if len(allowed.keys()) > 0 else None

def load_types():
    cats = load_categories()
    assert cats is not None, "Something went wrongwhen loading categories"
    grp = load_groups(cats)
    assert grp is not None, "Something went wrong when loading groups"
    

    def entry_is_valid_type(entry : dict)->bool:
        entry_groupid = entry.get('groupID')
        if entry_groupid not in grp.keys():
            return False
        
        if entry.get('basePrice', False) == False:
            return False
        
        return True

    data = {}
    path = Path("static/eve-online-static-data/types.jsonl")
    with open(path, 'r', encoding='utf-8') as file:
        for i, line in enumerate(file):
            if line.strip():
                obj  : dict = json.loads(line)
                
                if entry_is_valid_type(obj):
                    name = obj['name']['en']
                    obj['name'] = name
                    key = obj['_key']

                    if 'description' in obj.keys():
                        desc = obj['description']['en']
                        obj['description'] = desc
                    data[key] = obj

    print(f"Loaded {len(data.keys())} types.")
    return data



def update_prices():
    print("Updating Prices")

    data = load_types()
    base_path = Path("static/Prices/")
    last_date = datetime.now() - timedelta(days=1)
    last_date_str = last_date.strftime("%Y-%m-%d")

    for type_id in data.keys():
        file_path = base_path / f"{type_id}.json"

        # If File exists, check if its upto date
        if file_path.exists():
            with open(file_path, 'r') as file:
                file_data : dict = json.load(file)

            # Skip if upto date
            if last_date_str in file_data.keys():
                continue
            
        try:
            price_data = ZkillPhone.fetch_price_history(type_id)
            with open(file_path, 'w') as file:
                json.dump(price_data, file, indent=4)
            time.sleep(0.2)
        except requests.RequestException as e:
            print(f"Failed to fetch {type_id}: {e}")

    return



scheduler.add_job(
    update_prices,
    CronTrigger(hour=14, minute=0),
    id="update_prices",
    max_instances=1,
    coalesce=True,
    misfire_grace_time=3600,
)