# data_engine/etl/snapshot_builder.py

import bz2
from datetime import datetime, date, timedelta
import gzip
import json
from pathlib import Path
import re
from typing import Dict, List, Tuple, Any, Optional
import zipfile

from tqdm import tqdm

from shared.config import KILLMAILS_DIR, SNAPSHOTS_DIR, logger
from data_engine.etl.price_loader import ItemPriceLoader
from data_engine.models.char_state import CharEntry
from data_engine.models.ship_state import ShipEntry, init_ships_database
from data_engine.models.rolling_window import GlobalRollingWindowManager
from data_engine.etl.serializer import save_monthly_snapshot, load_monthly_snapshot

def run_snapshot_builder(overwrite: bool = False):
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    price_loader = ItemPriceLoader()
    start_date, (char_storage, ship_storage, rollingwindow) = setup_trackervars(overwrite)
    start_year = start_date.year

    end_date = find_newest_killmail_date()
    end_month = end_date.month
    end_year = end_date.year


    year_pbar = tqdm(range(start_year, end_year), desc="Iterating over Years", unit='year')
    for year in year_pbar:
        # Load the data for each year
        year_data = load_raw_killmails(year, bool(year < end_year))
        
        day_date = date(year, 1, 1) if start_year != year else start_date
        day_pbar = tqdm(year_data, desc=f"Scanning - {year}", unit ='day', leave=False)
        for file_name, get_bytes in day_pbar:
            raw_bytes = get_bytes()
            killmails = parse_daily_killmails(raw_bytes, file_name)
            process_daily_killmails(killmails, char_storage, ship_storage, rollingwindow, price_loader)
            next_date = day_date + timedelta(days=1)

            # Save monthly Snapshot
            if next_date.day == 1 or day_date == end_date:
                tqdm.write(f"Creating Snapshot for Month {day_date.month:02d}/{day_date.year}")
                if day_date == end_date:
                    snapshot_path = SNAPSHOTS_DIR / f"unfinished snapshot_{day_date.year}-{day_date.month:02d}.pkl.gz"
                else:
                    snapshot_path = SNAPSHOTS_DIR / f"snapshot_{day_date.year}-{day_date.month:02d}.pkl.gz"

                payload = {
                    'chars' : char_storage,
                    'ships' : ship_storage,
                    'rolling_window' : rollingwindow
                }
                save_monthly_snapshot(snapshot_path, payload)
            
            # Progress Date
            day_date = next_date

    return

def setup_trackervars(overwrite : bool)-> tuple[date, tuple[dict[str, CharEntry], dict[str, ShipEntry], GlobalRollingWindowManager]]:
    if overwrite:
        """
        We'll overwrite the snapshots and therefore start from the beginning
        """
        return date(2007, 12, 5), ({}, {}, GlobalRollingWindowManager())
    
    # Otherwise find snapshot
    files = list(SNAPSHOTS_DIR.glob("snapshot_*.pkl.gz"))
    assert files, "No Snapshots found, shouldn't run"
    dates = []
    for file in files:
        dt = file.stem.split('-')
        year = dt[0][-4:]
        month = dt[1][:2]
        dt = date(int(year), int(month), day=1)
        dates.append(dt)
    dates.sort()

    recent_date : date = dates[-1]
    recent_date_path = SNAPSHOTS_DIR / f"snapshot_{recent_date.year}-{recent_date.month:02d}.pkl.gz" 
    start_date = recent_date + timedelta(month=1)

    # Load the last snapshopt
    state = load_monthly_snapshot(recent_date_path)
    char = state.get("chars")
    ship = state.get("ships")
    rolling_window = state.get("rolling_window")
    return start_date, (char, ship, rolling_window)


def load_raw_killmails(year : int, is_zip : bool)->list:
    daily_files = []

    # Get Json within Zip file
    if is_zip:
        zip_path = KILLMAILS_DIR / f"{year}.zip"
        zf = zipfile.ZipFile(zip_path, "r")
        names = sorted([n for n in zf.namelist() if not n.endswith("/") and not n.startswith("__MACOSX")])
        for n in names:
            daily_files.append((n, lambda name=n: zf.open(name).read()))
    # Get jsons
    else:
        json_dir = KILLMAILS_DIR / f"{year}"
        paths = sorted([p for p in json_dir.iterdir() if p.is_file() and not p.name.startswith(".")])
        for p in paths:
            daily_files.append((p.name, lambda path=p: path.read_bytes()))

    return daily_files



def find_newest_killmail_date()->date:
    jsons = list(KILLMAILS_DIR.rglob("*.json"))
    zips = list(KILLMAILS_DIR.glob("*.zip"))
    # Case 0.5 Neither jsons or zips of zkillmails. Error. Cant build a dataset
    assert len(jsons) > 0 or len(zips) > 0, "NO KILLMAILS FOUND! Run the worker first for a few hours"
    
    # Case 1. 31.12.20XX. Everything is currently zipped!
    if len(jsons) == 0 and len(zips) > 0:
        zips.sort(key=lambda path: int(path.stem))
        last_year = zips[-1]
        return date(year=last_year, month=12, day=31)

    # Case 2. new Json files exist
    jsons.sort(key=lambda path: datetime.strptime(path.stem, "%Y%m%d"))
    last_json = jsons[-1]
    last_json = last_json.stem
    year = int(last_json[:4])
    month = int(last_json[4:6])
    day = int(last_json[6:8])
    last_date = date(year, month, day)
    return last_date

def decompress_bytes(raw_bytes: bytes, file_name: str) -> bytes:
    if file_name.endswith(".bz2") or raw_bytes[:2] == b"BZ":
        try:
            return bz2.decompress(raw_bytes)
        except Exception:
            pass
    if file_name.endswith(".gz") or raw_bytes[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(raw_bytes)
        except Exception:
            pass
    return raw_bytes


def parse_daily_killmails(raw_bytes: bytes, file_name: str) -> List[Dict[str, Any]]:
    raw_bytes = decompress_bytes(raw_bytes, file_name)
    text = raw_bytes.decode("utf-8", errors="ignore").strip()
    if not text:
        return []

    kms: List[Dict[str, Any]] = []
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            if all(isinstance(v, dict) for v in data.values()):
                kms = list(data.values())
            elif "attackers" in data and "victim" in data:
                kms = [data]
            else:
                kms = [v for v in data.values() if isinstance(v, dict) and "attackers" in v]
        elif isinstance(data, list):
            kms = [item for item in data if isinstance(item, dict) and "attackers" in item]
    except Exception:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if isinstance(item, dict) and "attackers" in item:
                    kms.append(item)
            except Exception:
                continue

    kms.sort(key=lambda k: k.get("killmail_time", ""))
    return kms


def process_daily_killmails(day, chars : dict[str,CharEntry], ships : dict[str, ShipEntry], rolling_window : GlobalRollingWindowManager, price_loader : ItemPriceLoader):
    # 1. Load in Kills for the day
    killmails = []

    # 2. Iterate over each one
    for km in killmails:
        # 2.1 Extract

        # 2.2 Update Stats
        pass

    # 3. Update rolling window
    return


"""

def run_snapshot_builder(start_year: int = 2007, end_year: int = 2026, overwrite: bool = False):
    

    # Discover sources
    sources: List[Tuple[int, Path, bool]] = []
    for zip_path in sorted(KILLMAILS_DIR.glob("*.zip")):
        if zip_path.stem.isdigit():
            y = int(zip_path.stem)
            if start_year <= y <= end_year:
                sources.append((y, zip_path, True))

    for dir_path in sorted(KILLMAILS_DIR.iterdir()):
        if dir_path.is_dir() and dir_path.name.isdigit():
            y = int(dir_path.name)
            if start_year <= y <= end_year and not any(s[0] == y for s in sources):
                sources.append((y, dir_path, False))


    for year, source_path, is_zip in tqdm(sources, desc="Overall Years", unit="year"):
        daily_files: List[Tuple[str, Any]] = []

        if is_zip:
            zf = zipfile.ZipFile(source_path, "r")
            names = sorted([n for n in zf.namelist() if not n.endswith("/") and not n.startswith("__MACOSX")])
            for n in names:
                daily_files.append((n, lambda name=n: zf.open(name).read()))
        else:
            paths = sorted([p for p in source_path.iterdir() if p.is_file() and not p.name.startswith(".")])
            for p in paths:
                daily_files.append((p.name, lambda path=p: path.read_bytes()))

        pbar_days = tqdm(daily_files, desc=f"Year {year}", unit="day", leave=False)

        for file_name, get_bytes in pbar_days:
            raw_bytes = get_bytes()
            killmails = parse_daily_killmails(raw_bytes, file_name)

            for km in killmails:
                km_time_raw = km.get("killmail_time")
                if not km_time_raw:
                    continue

                km_dt = parse_datetime(km_time_raw)
                km_date = km_dt.date()

                if resume_after_date and km_date <= resume_after_date:
                    continue

                date_str = km_date.strftime("%Y-%m-%d")

                rolling_window.advance_day(km_date)

                month_key = (km_date.year, km_date.month)
                if current_snapshot_month is not None and month_key != current_snapshot_month:
                    snapshot_filename = f"snapshot_{current_snapshot_month[0]:04d}-{current_snapshot_month[1]:02d}.pkl.gz"
                    snapshot_file = SNAPSHOTS_DIR / snapshot_filename

                    if not snapshot_file.exists() or overwrite:
                        save_monthly_snapshot(
                            snapshot_file,
                            {
                                "date": f"{current_snapshot_month[0]:04d}-{current_snapshot_month[1]:02d}",
                                "chars": char_store,
                                "ships": ship_store,
                                "rolling_window": rolling_window,
                            },
                        )
                        tqdm.write(f"💾 Saved monthly checkpoint: {snapshot_filename} (Pilots: {len(char_store):,})")

                current_snapshot_month = month_key

                # 1. Victim Verification (Player Only)
                victim = km.get("victim", {})
                vic_cid = victim.get("character_id")
                vic_sid = victim.get("ship_type_id")

                is_player_victim = (
                    vic_cid is not None and vic_cid > 0 and 
                    vic_sid is not None and vic_sid > 0 and vic_sid != 670
                )
                if not is_player_victim:
                    continue

                # 2. Attackers Verification (Player Only)
                raw_attackers = km.get("attackers", [])
                valid_attackers = []
                for att in raw_attackers:
                    att_cid = att.get("character_id")
                    att_sid = att.get("ship_type_id")
                    if att_cid is not None and att_cid > 0 and att_sid is not None and att_sid > 0 and att_sid != 670:
                        valid_attackers.append(att)

                if not valid_attackers:
                    continue

                gang_size = len(raw_attackers)
                is_solo = len(valid_attackers) == 1
                km_isk = price_loader.estimate_killmail_isk(km, date_str)

                # Estimate Points for Victim and Attackers
                vic_ship = ship_store.get(vic_sid)
                km_points = get_base_hull_points(vic_ship.cls if vic_ship else "")
                attacker_points = km_points / max(1, len(valid_attackers))

                # 3. Update Victim
                v_entry = char_store.setdefault(vic_cid, CharEntry(vic_cid))
                v_entry.record_loss(
                    isk=km_isk,
                    points=km_points,
                    is_solo=is_solo,
                    day=km_date,
                    ship_id=vic_sid,
                )
                rolling_window.record_loss(vic_cid, km_isk)

                if vic_sid in ship_store:
                    ship_store[vic_sid].record_event(day=km_date, isk_destroyed=km_isk, is_victim=True)

                # 4. Update Attackers
                for att in valid_attackers:
                    att_cid = att["character_id"]
                    att_sid = att["ship_type_id"]

                    a_entry = char_store.setdefault(att_cid, CharEntry(att_cid))
                    a_entry.record_kill(
                        isk=km_isk,
                        points=attacker_points,
                        is_solo=is_solo,
                        gang_size=gang_size,
                        day=km_date,
                        ship_id=att_sid,
                    )
                    rolling_window.record_kill(att_cid, km_isk)

                    if att_sid in ship_store:
                        ship_store[att_sid].record_event(day=km_date, isk_destroyed=km_isk, is_victim=False)

            pbar_days.set_postfix({"Pilots Tracked": len(char_store)})

        if is_zip:
            zf.close()

    # Save Final Snapshot
    if current_snapshot_month is not None:
        final_filename = f"snapshot_{current_snapshot_month[0]:04d}-{current_snapshot_month[1]:02d}-final.pkl.gz"
        save_monthly_snapshot(
            SNAPSHOTS_DIR / final_filename,
            {
                "date": f"{current_snapshot_month[0]:04d}-{current_snapshot_month[1]:02d}-final",
                "chars": char_store,
                "ships": ship_store,
                "rolling_window": rolling_window,
            },
        )
        logger.info(f"💾 Final state checkpoint saved to {final_filename}")

    logger.info("=" * 65)
    logger.info(f"✅ Replay complete! Total tracked pilots: {len(char_store):,}")
    logger.info(f"Checkpoints saved in: {SNAPSHOTS_DIR}")
    logger.info("=" * 65)
    return
"""

def parse_datetime(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))





def get_base_hull_points(ship_class: str) -> float:
    """Assigns approximate zKillboard base points per hull size."""
    cls = (ship_class or "").lower()
    if "frigate" in cls or "corvette" in cls:
        return 10.0
    if "destroyer" in cls:
        return 15.0
    if "cruiser" in cls:
        return 30.0
    if "battlecruiser" in cls:
        return 50.0
    if "battleship" in cls:
        return 80.0
    if "dreadnought" in cls or "carrier" in cls or "force auxiliary" in cls:
        return 200.0
    if "titan" in cls or "supercarrier" in cls:
        return 500.0
    return 20.0





