# ml_engine/etl/dataset_builder.py

import json
import zipfile
import logging
import math
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple

import pandas as pd
from tqdm import tqdm

from shared.config import KILLMAILS_DIR, STATIC_DIR, SNAPSHOTS_DIR
from data_engine.etl.serializer import load_monthly_snapshot
from data_engine.etl.price_loader import ItemPriceLoader
from data_engine.etl.snapshot_builder import parse_daily_killmails
from data_engine.models.char_state import CharEntry
from data_engine.models.ship_state import ShipEntry, init_ships_database
from data_engine.models.rolling_window import GlobalRollingWindowManager
from ml_engine.etl.timeframe_resolver import resolve_timeframe, find_nearest_preceding_snapshot

logger = logging.getLogger("EveOracle.DatasetBuilder")


@dataclass
class MLDatasetConfig:
    start_input: str
    months_input: Optional[int] = None
    end_input: Optional[str] = None
    allowed_ship_classes: Set[str] | str = "all"
    output_dir: Path = STATIC_DIR / "output" / "datasets"


def build_masked_features(feature_dict: Dict[str, float], default_val: float = 0.0) -> Dict[str, float]:
    """Creates a zeroed/neutral feature dictionary for masked modalities."""
    return {k: default_val for k in feature_dict.keys()}


def create_1v1_datapoint(
    killmail: dict,
    char_store: Dict[int, CharEntry],
    ships_store: Dict[int, ShipEntry],
    rolling_window: GlobalRollingWindowManager,
    km_isk_destroyed: float,
    km_date: date,
    allowed_ship_classes: Set[str] | str,
) -> List[Dict[str, Any]]:
    """
    Creates 6 synthetic training samples per 1v1 encounter:
    - 3 from Attacker Focal Perspective (W2 vs W2, W2 vs W1, W2 vs W3) -> +Y
    - 3 from Victim Focal Perspective (W2 vs W2, W2 vs W1, W2 vs W3)   -> -Y
    """
    victim = killmail.get("victim", {})
    vic_cid = victim.get("character_id")
    vic_sid = victim.get("ship_type_id")

    attackers = killmail.get("attackers", [])
    if len(attackers) != 1:
        return []

    att = attackers[0]
    att_cid = att.get("character_id")
    att_sid = att.get("ship_type_id")

    # Strict 1v1 player verification
    if not vic_cid or not vic_sid or not att_cid or not att_sid:
        return []
    if vic_sid == 670 or att_sid == 670:  # Skip capsules
        return []

    att_ship_entry = ships_store.get(att_sid)
    vic_ship_entry = ships_store.get(vic_sid)

    if not att_ship_entry or not vic_ship_entry:
        return []

    # Ship Class Filter Check
    if allowed_ship_classes != "all":
        if (
            att_ship_entry.cls not in allowed_ship_classes
            or vic_ship_entry.cls not in allowed_ship_classes
        ):
            return []

    att_char = char_store.setdefault(att_cid, CharEntry(att_cid))
    vic_char = char_store.setdefault(vic_cid, CharEntry(vic_cid))

    # Pull active 7d/30d stats from rolling window
    att_recent = rolling_window.get_recent_stats(att_cid, km_date)
    vic_recent = rolling_window.get_recent_stats(vic_cid, km_date)

    # 1. Full Features
    att_char_feat = att_char.get_features(ship_id=att_sid, recent=att_recent)
    att_ship_feat = att_ship_entry.get_features()

    vic_char_feat = vic_char.get_features(ship_id=vic_sid, recent=vic_recent)
    vic_ship_feat = vic_ship_entry.get_features()

    # 2. Masked Features
    empty_att_char = build_masked_features(att_char_feat, default_val=0.0)
    empty_att_ship = build_masked_features(att_ship_feat, default_val=0.0)

    empty_vic_char = build_masked_features(vic_char_feat, default_val=0.0)
    empty_vic_ship = build_masked_features(vic_ship_feat, default_val=0.0)

    date_str = km_date.strftime("%Y-%m-%d")
    km_id = killmail.get("killmail_id", 0)
    system_id = killmail.get("solar_system_id", 0)

    # Continuous signed log10 ISK trade target
    log_isk = math.log10(max(km_isk_destroyed, 1.0) + 1.0)

    def assemble_row(
        p1_cid: int,
        p1_sid: int,
        p1_char: Dict[str, float],
        p1_ship: Dict[str, float],
        p2_cid: Optional[int],
        p2_sid: Optional[int],
        p2_char: Dict[str, float],
        p2_ship: Dict[str, float],
        p2_has_char: float,
        p2_has_ship: float,
        y_isk: float,
        y_log: float,
        outcome: int,
        variant_tag: str,
    ) -> Dict[str, Any]:
        row: Dict[str, Any] = {
            "killmail_id": km_id,
            "date": date_str,
            "solar_system_id": system_id,
            "y_isk_destroyed": y_isk,
            "y_log_isk": y_log,
            "outcome": outcome,
            "variant": variant_tag,
            "p1_char_id": p1_cid,
            "p1_ship_id": p1_sid,
            "p2_char_id": p2_cid if p2_has_char else None,
            "p2_ship_id": p2_sid if p2_has_ship else None,
            # Mask Indicators
            "p1_has_char": 1.0,
            "p1_has_ship": 1.0,
            "p2_has_char": p2_has_char,
            "p2_has_ship": p2_has_ship,
        }
        for k, v in p1_char.items():
            row[f"p1_{k}"] = v
        for k, v in p1_ship.items():
            row[f"p1_{k}"] = v
        for k, v in p2_char.items():
            row[f"p2_{k}"] = v
        for k, v in p2_ship.items():
            row[f"p2_{k}"] = v

        return row

    samples: List[Dict[str, Any]] = []

    # -------------------------------------------------------------
    # Perspective A: Focal Player (P1) = Attacker (+Y)
    # -------------------------------------------------------------
    # A1: Full Intel (W2 vs W2)
    samples.append(
        assemble_row(
            p1_cid=att_cid, p1_sid=att_sid, p1_char=att_char_feat, p1_ship=att_ship_feat,
            p2_cid=vic_cid, p2_sid=vic_sid, p2_char=vic_char_feat, p2_ship=vic_ship_feat,
            p2_has_char=1.0, p2_has_ship=1.0, y_isk=float(km_isk_destroyed), y_log=float(log_isk),
            outcome=1, variant_tag="att_w2_vs_w2"
        )
    )
    # A2: Opponent Ship Unknown (W2 vs W1)
    samples.append(
        assemble_row(
            p1_cid=att_cid, p1_sid=att_sid, p1_char=att_char_feat, p1_ship=att_ship_feat,
            p2_cid=vic_cid, p2_sid=vic_sid, p2_char=vic_char_feat, p2_ship=empty_vic_ship,
            p2_has_char=1.0, p2_has_ship=0.0, y_isk=float(km_isk_destroyed), y_log=float(log_isk),
            outcome=1, variant_tag="att_w2_vs_w1"
        )
    )
    # A3: Opponent Pilot Unknown (W2 vs W3)
    samples.append(
        assemble_row(
            p1_cid=att_cid, p1_sid=att_sid, p1_char=att_char_feat, p1_ship=att_ship_feat,
            p2_cid=vic_cid, p2_sid=vic_sid, p2_char=empty_vic_char, p2_ship=vic_ship_feat,
            p2_has_char=0.0, p2_has_ship=1.0, y_isk=float(km_isk_destroyed), y_log=float(log_isk),
            outcome=1, variant_tag="att_w2_vs_w3"
        )
    )

    # -------------------------------------------------------------
    # Perspective B: Focal Player (P1) = Victim (-Y)
    # -------------------------------------------------------------
    # B1: Full Intel (W2 vs W2)
    samples.append(
        assemble_row(
            p1_cid=vic_cid, p1_sid=vic_sid, p1_char=vic_char_feat, p1_ship=vic_ship_feat,
            p2_cid=att_cid, p2_sid=att_sid, p2_char=att_char_feat, p2_ship=att_ship_feat,
            p2_has_char=1.0, p2_has_ship=1.0, y_isk=float(-km_isk_destroyed), y_log=float(-log_isk),
            outcome=0, variant_tag="vic_w2_vs_w2"
        )
    )
    # B2: Opponent Ship Unknown (W2 vs W1)
    samples.append(
        assemble_row(
            p1_cid=vic_cid, p1_sid=vic_sid, p1_char=vic_char_feat, p1_ship=vic_ship_feat,
            p2_cid=att_cid, p2_sid=att_sid, p2_char=att_char_feat, p2_ship=empty_att_ship,
            p2_has_char=1.0, p2_has_ship=0.0, y_isk=float(-km_isk_destroyed), y_log=float(-log_isk),
            outcome=0, variant_tag="vic_w2_vs_w1"
        )
    )
    # B3: Opponent Pilot Unknown (W2 vs W3)
    samples.append(
        assemble_row(
            p1_cid=vic_cid, p1_sid=vic_sid, p1_char=vic_char_feat, p1_ship=vic_ship_feat,
            p2_cid=att_cid, p2_sid=att_sid, p2_char=empty_att_char, p2_ship=att_ship_feat,
            p2_has_char=0.0, p2_has_ship=1.0, y_isk=float(-km_isk_destroyed), y_log=float(-log_isk),
            outcome=0, variant_tag="vic_w2_vs_w3"
        )
    )

    return samples


# ml_engine/etl/dataset_builder.py (check at top of build_ml_dataset)

def build_ml_dataset(config: MLDatasetConfig, force_rebuild: bool = False) -> Path:
    config.output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Resolve Target Timeframe
    start_date, end_date = resolve_timeframe(
        config.start_input, config.months_input, config.end_input
    )
    
    out_filename = f"1v1_dataset_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.parquet"
    out_path = config.output_dir / out_filename

    # Fast Path: Skip extraction if dataset already exists
    if out_path.exists() and not force_rebuild:
        logger.info(f"⚡ Found existing dataset: {out_path.name} (skipping extraction)")
        return out_path

    logger.info(f"Target timeframe: {start_date} -> {end_date}")

    # 2. Locate and Hydrate Pre-Computed Snapshot
    snap_date, snap_path = find_nearest_preceding_snapshot(SNAPSHOTS_DIR, start_date)
    logger.info(f"⚡ Hydrating state from snapshot: {snap_path.name} (Dated: {snap_date})")

    snapshot_data = load_monthly_snapshot(snap_path)
    char_store: Dict[int, CharEntry] = snapshot_data.get("chars", {})
    ship_store: Dict[int, ShipEntry] = snapshot_data.get("ships", init_ships_database())
    rolling_window: GlobalRollingWindowManager = snapshot_data.get(
        "rolling_window", GlobalRollingWindowManager()
    )

    logger.info(f"State loaded: {len(char_store):,} pre-warmed pilots, {len(ship_store):,} ship hulls.")

    price_loader = ItemPriceLoader()
    all_dataset_rows: List[Dict[str, Any]] = []
    total_1v1_fights = 0

    # 3. Stream Killmails from Snapshot Date to End Date
    years = range(snap_date.year, end_date.year + 1)

    for year in tqdm(years, desc="Streaming Years", unit="year"):
        year_dir = KILLMAILS_DIR / str(year)
        zip_path = KILLMAILS_DIR / f"{year}.zip"

        daily_files: List[Tuple[str, Any]] = []

        if year_dir.exists() and year_dir.is_dir():
            paths = sorted([p for p in year_dir.glob("*.json") if not p.name.startswith(".")])
            for p in paths:
                daily_files.append((p.name, lambda path=p: path.read_bytes()))
        elif zip_path.exists():
            zf = zipfile.ZipFile(zip_path, "r")
            names = sorted([n for n in zf.namelist() if n.endswith(".json") and not n.startswith("__MACOSX")])
            for n in names:
                daily_files.append((n, lambda name=n: zf.open(name).read()))
        else:
            continue

        for file_name, get_bytes in tqdm(daily_files, desc=f"Year {year}", unit="day", leave=False):
            raw_bytes = get_bytes()
            killmails = parse_daily_killmails(raw_bytes, file_name)

            for km in killmails:
                km_time_raw = km.get("killmail_time")
                if not km_time_raw:
                    continue

                km_dt = datetime.fromisoformat(km_time_raw.replace("Z", "+00:00"))
                km_date = km_dt.date()

                if km_date < snap_date or km_date > end_date:
                    continue

                victim = km.get("victim", {})
                vic_cid = victim.get("character_id")
                vic_sid = victim.get("ship_type_id")

                if not vic_cid or not vic_sid:
                    continue

                attackers = km.get("attackers", [])
                if not attackers or any(att.get("ship_type_id") is None for att in attackers):
                    continue

                rolling_window.advance_day(km_date)

                date_str = km_date.strftime("%Y-%m-%d")
                km_isk_destroyed = price_loader.estimate_killmail_isk(km, date_str)

                # Collect 6-point augmented dataset
                if start_date <= km_date <= end_date:
                    if len(attackers) == 1:
                        samples = create_1v1_datapoint(
                            km,
                            char_store,
                            ship_store,
                            rolling_window,
                            km_isk_destroyed,
                            km_date,
                            config.allowed_ship_classes,
                        )
                        if samples:
                            all_dataset_rows.extend(samples)
                            total_1v1_fights += 1

                # Update rolling states
                gang_size = len(attackers)
                is_solo = len(attackers) == 1

                v_entry = char_store.setdefault(vic_cid, CharEntry(vic_cid))
                v_entry.record_loss(isk=km_isk_destroyed, is_solo=is_solo, ship_id=vic_sid)
                rolling_window.record_loss(vic_cid, km_isk_destroyed)

                if vic_sid in ship_store:
                    ship_store[vic_sid].record_event(day=km_date, isk_destroyed=km_isk_destroyed, is_victim=True)

                for att in attackers:
                    att_cid = att.get("character_id")
                    att_sid = att.get("ship_type_id")
                    if att_cid:
                        a_entry = char_store.setdefault(att_cid, CharEntry(att_cid))
                        a_entry.record_kill(
                            isk=km_isk_destroyed, is_solo=is_solo, gang_size=gang_size, ship_id=att_sid
                        )
                        rolling_window.record_kill(att_cid, km_isk_destroyed)

                    if att_sid and att_sid in ship_store:
                        ship_store[att_sid].record_event(
                            day=km_date, isk_destroyed=km_isk_destroyed, is_victim=False
                        )

    # 4. Save Parquet
    if all_dataset_rows:
        df = pd.DataFrame(all_dataset_rows)
        df.to_parquet(out_path, index=False, engine="pyarrow", compression="snappy")
        logger.info("=" * 65)
        logger.info(f"✅ Dataset generated successfully: {out_path}")
        logger.info(f"• Total Unique 1v1 Fights:   {total_1v1_fights:,}")
        logger.info(f"• Total Augmented Samples:   {len(all_dataset_rows):,} (6x multiplier)")
        logger.info(f"• Feature Columns:           {len(df.columns) - 6}")
        logger.info("=" * 65)
    else:
        logger.warning("⚠️ No valid 1v1 encounters extracted for the requested parameters.")

    return out_path