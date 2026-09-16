# data_engine/etl/snapshot_builder.py

import json
import zipfile
import bz2
import gzip
import logging
import re
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

from tqdm import tqdm

from shared.config import KILLMAILS_DIR, SNAPSHOTS_DIR
from data_engine.etl.price_loader import ItemPriceLoader
from data_engine.models.char_state import CharEntry
from data_engine.models.ship_state import ShipEntry, init_ships_database
from data_engine.models.rolling_window import GlobalRollingWindowManager
from data_engine.etl.serializer import save_monthly_snapshot, load_monthly_snapshot

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


def find_latest_saved_snapshot(snapshots_dir: Path) -> Tuple[Optional[date], Optional[Path]]:
    if not snapshots_dir.exists():
        return None, None

    files = list(snapshots_dir.glob("snapshot_*.pkl.gz"))
    if not files:
        return None, None

    snapshots: List[Tuple[date, Path]] = []
    for f in files:
        if "final" in f.name:
            continue
        match = re.search(r"snapshot_(\d{4})-(\d{2})", f.name)
        if match:
            y, m = int(match.group(1)), int(match.group(2))
            snapshots.append((date(y, m, 1), f))

    if not snapshots:
        return None, None

    snapshots.sort(key=lambda s: s[0], reverse=True)
    return snapshots[0]


def run_snapshot_builder(start_year: int = 2007, end_year: int = 2026, overwrite: bool = False):
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Initializing SDE Ships & Price Database...")

    price_loader = ItemPriceLoader()
    ship_store: Dict[int, ShipEntry] = init_ships_database()
    char_store: Dict[int, CharEntry] = {}
    rolling_window = GlobalRollingWindowManager()

    resume_after_date: Optional[date] = None
    current_snapshot_month: Tuple[int, int] | None = None

    if not overwrite:
        latest_date, latest_path = find_latest_saved_snapshot(SNAPSHOTS_DIR)
        if latest_path and latest_path.exists():
            logger.info(f"⚡ Found existing checkpoint: {latest_path.name}")
            logger.info("Hydrating state from checkpoint (takes ~1-2 seconds)...")
            state = load_monthly_snapshot(latest_path)
            char_store = state.get("chars", {})
            ship_store = state.get("ships", init_ships_database())
            rolling_window = state.get("rolling_window", GlobalRollingWindowManager())

            resume_after_date = latest_date
            current_snapshot_month = (latest_date.year, latest_date.month)
            logger.info(f"✅ Resuming historical replay starting from {resume_after_date} forward.")
            logger.info(f"• Pre-warmed pilots in state: {len(char_store):,}")
    else:
        logger.info("⚠️ Overwrite enabled: starting fresh replay from scratch.")

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

    sources.sort(key=lambda s: s[0])

    if resume_after_date:
        sources = [s for s in sources if s[0] >= resume_after_date.year]

    if not sources:
        logger.info("✅ All monthly snapshots up to date! Nothing new to process.")
        return

    logger.info(f"🚀 Processing {len(sources)} year source(s): {[s[0] for s in sources]}")

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