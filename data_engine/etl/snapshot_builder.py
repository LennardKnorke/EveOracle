# data_engine/etl/snapshot_builder.py

import json
import zipfile
import bz2
import gzip
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Tuple, Any

from tqdm import tqdm

from shared.config import KILLMAILS_DIR, SNAPSHOTS_DIR
from data_engine.etl.price_loader import ItemPriceLoader
from data_engine.models.char_state import CharEntry
from data_engine.models.ship_state import ShipEntry, init_ships_database
from data_engine.models.rolling_window import GlobalRollingWindowManager
from data_engine.etl.serializer import save_monthly_snapshot

logger = logging.getLogger("EveOracle.DataEngine")


def parse_datetime(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


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


def run_snapshot_builder(start_year: int = 2007, end_year: int = 2026, overwrite: bool = False):
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Initializing SDE Ships & Price Database...")

    price_loader = ItemPriceLoader()
    ship_store: Dict[int, ShipEntry] = init_ships_database()
    char_store: Dict[int, CharEntry] = {}
    rolling_window = GlobalRollingWindowManager()

    current_snapshot_month: Tuple[int, int] | None = None

    # Discover sources (both zip archives and folders)
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

    sources.sort(key=lambda s: s[0])

    if not sources:
        logger.error(f"No killmail sources found for {start_year}-{end_year} in {KILLMAILS_DIR}")
        return

    logger.info(f"🚀 Replaying history across {len(sources)} years: {[s[0] for s in sources]}")

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
                date_str = km_date.strftime("%Y-%m-%d")

                # Advance rolling window day
                rolling_window.advance_day(km_date)

                # Check Monthly Snapshot Boundary (1st of month)
                month_key = (km_date.year, km_date.month)
                if current_snapshot_month is not None and month_key != current_snapshot_month:
                    snapshot_filename = f"snapshot_{current_snapshot_month[0]:04d}-{current_snapshot_month[1]:02d}.pkl.gz"
                    snapshot_file = SNAPSHOTS_DIR / snapshot_filename

                    if not snapshot_file.exists() or overwrite:
                        save_monthly_snapshot(
                            snapshot_file,
                            {
                                "date": f"{current_snapshot_month[0]:04d}-{current_snapshot_month[1]:02d}-01",
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

                # 3. Update Victim
                v_entry = char_store.setdefault(vic_cid, CharEntry(vic_cid))
                v_entry.record_loss(isk=km_isk, is_solo=is_solo, ship_id=vic_sid)
                rolling_window.record_loss(vic_cid, km_isk)

                if vic_sid in ship_store:
                    ship_store[vic_sid].record_event(day=km_date, isk_destroyed=km_isk, is_victim=True)

                # 4. Update Attackers
                for att in valid_attackers:
                    att_cid = att["character_id"]
                    att_sid = att["ship_type_id"]

                    a_entry = char_store.setdefault(att_cid, CharEntry(att_cid))
                    a_entry.record_kill(isk=km_isk, is_solo=is_solo, gang_size=gang_size, ship_id=att_sid)
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