# worker/tasks/killmails.py

import json
import random
import shutil
import time
import logging
from datetime import date, timedelta, datetime
from pathlib import Path

import requests

from shared.config import logger, KILLMAILS_DIR


ZKILL_BASE = "https://r2z2.zkillboard.com/history/raw"
START_DATE = date(2007, 12, 5)


outdated_after_days = 3
download_delay_seconds = 5.0




def init_killmails():
    KILLMAILS_DIR.mkdir(parents=True, exist_ok=True)
    first_year_zip = KILLMAILS_DIR / "2007.zip"
    if first_year_zip.exists():
        return
    
    logger.warning("No Historic Killmails found. Fetching past killmails...")

    current_date = START_DATE
    today = datetime.today().date() - timedelta(days=outdated_after_days)

    logger.info(f"STARTING: Fetching Killmails")
    while current_date <= today:
        if not killmail_date_exists(current_date):
            date_file = f"{current_date.year}{current_date.month:02d}{current_date.day:02d}.json"
            download_zkill_killmails(current_date, date_file)

            if current_date == date(year=current_date.year, month=12, day=31):
                compress_zkill_year()
            time.sleep(download_delay_seconds)
        current_date += timedelta(days=1)
    logger.info(f"FINISH: Fetching Killmails")
    return


def killmail_date_exists(dt : date, today : date):
    # Date is from previous Year and zipfile _exists
    date_year = dt.year
    dt_zip_file = KILLMAILS_DIR / f"{date_year}.zip"
    if dt.year < today.year and dt_zip_file.exists():
        return True
    
    # Date is current year and json exists
    dt_json_file = KILLMAILS_DIR / str(date_year) / f"{date_year}{dt.month}{dt.day}.json"
    if dt.year == today.year and dt_json_file.exists():
        return True
    
    logger.error(f"Killmail date does not exist - {dt}")
    return False


def compress_zkill_year(year : int):
    year_dir = KILLMAILS_DIR / str(year)
    zip_file = KILLMAILS_DIR / f"{year}.zip"
    assert year_dir.exists() and not zip_file.exists()

    zip_folder(year_dir)
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


def download_zkill_killmails(dt: date, file_name : str):
    url = f"{ZKILL_BASE}/{file_name}"

    year_dir = KILLMAILS_DIR / str(dt.year)
    year_dir.mkdir(parents=True, exist_ok=True)
    filepath = year_dir / file_name

    if filepath.exists():
        return

    try:
        headers = {
            "Accept-Encoding": "gzip",
            "User-Agent": "EveOracle - Maintainer: LocalCombatDashboard",
            "Content-Type": "application/json",
        }
        req = requests.get(url=url, headers=headers, timeout=60)
        req.raise_for_status()
        data = req.json()

        with filepath.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Fetched Killmails from {dt}")
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            logger.warning(f"Missing killmails for {dt} (404)")
        else:
            logger.error(f"HTTP error for {dt}: {e}")
    except Exception as e:
        logger.error(f"Failed to fetch {dt}: {e}")



def update_zkill_killmails():
    last_date = get_last_date()
    today = date.today()
    if not (today - last_date > timedelta(days=outdated_after_days)):
        return
    
    logger.info(f"STARTING: Fetching Killmails")
    while last_date <= today - timedelta(days=outdated_after_days):
        date_file = f"{last_date.year}{last_date.month:02d}{last_date.day:02d}.json"
        download_zkill_killmails(last_date, date_file)

        if last_date == date(year=last_date.year, month=12, day=31):
            compress_zkill_year()
        time.sleep(download_delay_seconds)
        last_date += timedelta(days=1)
    logger.info(f"FINISH: Fetching Killmails")
    return


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