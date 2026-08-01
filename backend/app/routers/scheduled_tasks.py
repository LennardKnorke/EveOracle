from datetime import datetime, date, timedelta
from datetime import datetime, date, timedelta
import os
import json
from pathlib import Path
import shutil
import random
import time
from urllib.request import urlretrieve, urlopen
from urllib.error import HTTPError
import requests

from fastapi import FastAPI
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger


EVEREV_BASE = "https://data.everef.net/killmails"
ZKILL_BASE = "https://r2z2.zkillboard.com/history/raw"
START_DATE = date(2007, 12, 5)


scheduler = BackgroundScheduler()


download_dir = Path("killmail_history")
download_dir.mkdir(exist_ok=True)


def update_esi_killmails():
    end_date = date.today() - timedelta(days=2)  # everef lags 2 days
    last_date = get_last_date(zkill=False)
    if last_date >= end_date:
        return
    
    next_date = last_date + timedelta(days=1)
    filename = f"killmails-{next_date:%Y-%m-%d}.tar.bz2"
    download_esi_killmails(next_date, filename)
    return

def update_zkill_killmails():
    t = random.random()
    time.sleep(10.0 * t)
    end_date = date.today() - timedelta(days=2)  # zkill also lags
    last_date = get_last_date(zkill=True)
    if last_date >= end_date:
        return

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
    # A year is complete when the last downloaded date is on or after Dec 31.
    last_date = get_last_date(zkill=True)
    if last_date < date(year, 12, 31):
        return

    print(f"Zipping completed zkill year: {year}")
    zip_folder(oldest)
    return


def get_last_date(zkill: bool = False) -> date:
    def zkill_date() -> None|date:
        dir = download_dir / "zkill"
        files = sorted(dir.rglob("*.json"))
        if not files:
            zips = sorted(dir.rglob("*.zip"))

            if zips:
                year_str = zips[-1].stem
                year_end = date(int(year_str), 12, 31)
                return year_end + timedelta(days=1)
            
            return None
        latest = files[-1].stem
        return date(int(latest[:4]), int(latest[4:6]), int(latest[6:8]))
        
    def esi_date()-> None|date:
        dir = download_dir / "esi"
        files = sorted(dir.rglob("killmails-*.tar.bz2"))
        if not files:
            return None
        latest = files[-1].stem

        date_part = latest.replace("killmails-", "")[:-4]
        return date.fromisoformat(date_part)
    
    if zkill:
        dt = zkill_date()
    else:
        dt = esi_date()
    
    if dt == None:
        return START_DATE - timedelta(days=1)
    else:
        return dt
        


def download_esi_killmails(dt : date, filename : str):
    url = f"{EVEREV_BASE}/{dt.year}/{filename}"
    year_dir = download_dir / "esi" / str(dt.year) 
    year_dir.mkdir(parents=True, exist_ok=True)
    filepath = year_dir / filename

    # RETRIEVE
    try:
        urlretrieve(url, filepath)
        print(f"Fetched Killmails from {dt}")
    except HTTPError as e:
        if e.code == 404:
            print(f"Missing: {filename}")
        else:
            print(f"HTTP {e.code}: {filename}")
    except Exception as e:
        print(f"Failed {filename}: {e}")
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



#scheduler.add_job(
#    update_esi_killmails, 
#    #IntervalTrigger(minutes=1), 
#    IntervalTrigger(seconds=30),
#    max_instances=1,
#    coalesce=True,
#    misfire_grace_time=300
#)

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