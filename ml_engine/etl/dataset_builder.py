# ml_engine/etl/dataset_builder.py

import json
import zipfile
import logging
import math
import random
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
from ml_engine.models.combat_physics import compute_relative_combat_physics
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
    return {k: default_val for k in feature_dict.keys()}


def build_stale_char_features(feature_dict: Dict[str, float]) -> Dict[str, float]:
    """Zeroes out weekly and monthly fields to simulate a pilot who has been inactive recently."""
    stale = dict(feature_dict)
    stale["char_kills_7d"] = 0.0
    stale["char_kills_30d"] = 0.0
    stale["char_losses_7d"] = 0.0
    stale["char_losses_30d"] = 0.0
    stale["char_isk_destroyed_7d"] = 0.0
    stale["char_isk_destroyed_30d"] = 0.0
    stale["char_isk_lost_7d"] = 0.0
    stale["char_isk_lost_30d"] = 0.0
    stale["char_days_since_active"] = 60.0
    return stale


def build_jittered_features(feature_dict: Dict[str, float], jitter_pct: float = 0.05) -> Dict[str, float]:
    """Applies slight Gaussian variance (+-5%) to prevent overfitting to exact numbers."""
    jittered = {}
    for k, v in feature_dict.items():
        if "res" in k or "slots" in k or "turrets" in k or "launchers" in k:
            jittered[k] = v
        else:
            noise = random.uniform(1.0 - jitter_pct, 1.0 + jitter_pct)
            jittered[k] = float(max(0.0, v * noise))
    return jittered


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
    Creates 12 synthetic training samples per 1v1 encounter.
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

    if not vic_cid or not vic_sid or not att_cid or not att_sid:
        return []
    if vic_sid == 670 or att_sid == 670:
        return []

    att_ship_entry = ships_store.get(att_sid)
    vic_ship_entry = ships_store.get(vic_sid)

    if not att_ship_entry or not vic_ship_entry:
        return []

    if allowed_ship_classes != "all":
        if (
            att_ship_entry.cls not in allowed_ship_classes
            or vic_ship_entry.cls not in allowed_ship_classes
        ):
            return []

    att_char = char_store.setdefault(att_cid, CharEntry(att_cid))
    vic_char = char_store.setdefault(vic_cid, CharEntry(vic_cid))

    att_recent = rolling_window.get_recent_stats(att_cid, km_date)
    vic_recent = rolling_window.get_recent_stats(vic_cid, km_date)

    # Base Features
    att_char_feat = att_char.get_features(current_date=km_date, ship_id=att_sid, recent=att_recent)
    att_ship_feat = att_ship_entry.get_features()

    vic_char_feat = vic_char.get_features(current_date=km_date, ship_id=vic_sid, recent=vic_recent)
    vic_ship_feat = vic_ship_entry.get_features()

    # Masked & Stale Variations
    empty_vic_char = build_masked_features(vic_char_feat, default_val=0.0)
    empty_vic_ship = build_masked_features(vic_ship_feat, default_val=0.0)
    stale_vic_char = build_stale_char_features(vic_char_feat)

    empty_att_char = build_masked_features(att_char_feat, default_val=0.0)
    empty_att_ship = build_masked_features(att_ship_feat, default_val=0.0)
    stale_att_char = build_stale_char_features(att_char_feat)

    date_str = km_date.strftime("%Y-%m-%d")
    km_id = killmail.get("killmail_id", 0)
    system_id = killmail.get("solar_system_id", 0)
    log_isk = math.log10(max(km_isk_destroyed, 1.0) + 1.0)

    def assemble_row(
        p1_cid: int, p1_sid: int, p1_char: Dict[str, float], p1_ship: Dict[str, float], p1_cls: str,
        p2_cid: Optional[int], p2_sid: Optional[int], p2_char: Dict[str, float], p2_ship: Dict[str, float], p2_cls: str,
        p2_has_char: float, p2_has_ship: float, y_isk: float, y_log: float, outcome: int, variant: str,
    ) -> Dict[str, Any]:
        physics = compute_relative_combat_physics(
            p1_char, p1_ship, p1_cls, p2_char, p2_ship, p2_cls, p2_has_char, p2_has_ship
        )
        row = {
            "killmail_id": km_id,
            "date": date_str,
            "solar_system_id": system_id,
            "y_isk_destroyed": y_isk,
            "y_log_isk": y_log,
            "outcome": outcome,
            "variant": variant,
            "p1_char_id": p1_cid,
            "p1_ship_id": p1_sid,
            "p2_char_id": p2_cid if p2_has_char else None,
            "p2_ship_id": p2_sid if p2_has_ship else None,
            "p1_has_char": 1.0,
            "p1_has_ship": 1.0,
            "p2_has_char": p2_has_char,
            "p2_has_ship": p2_has_ship,
        }
        row.update(physics)
        for k, v in p1_char.items(): row[f"p1_{k}"] = v
        for k, v in p1_ship.items(): row[f"p1_{k}"] = v
        for k, v in p2_char.items(): row[f"p2_{k}"] = v
        for k, v in p2_ship.items(): row[f"p2_{k}"] = v
        return row

    samples: List[Dict[str, Any]] = []

    # -------------------------------------------------------------
    # Perspective A: Attacker = Focal (P1) -> +Y
    # -------------------------------------------------------------
    # 1. Full Intel (W2 vs W2)
    samples.append(assemble_row(att_cid, att_sid, att_char_feat, att_ship_feat, att_ship_entry.cls, vic_cid, vic_sid, vic_char_feat, vic_ship_feat, vic_ship_entry.cls, 1.0, 1.0, float(km_isk_destroyed), float(log_isk), 1, "att_full"))
    # 2. Stale Intel (P2 7d/30d zeroed)
    samples.append(assemble_row(att_cid, att_sid, att_char_feat, att_ship_feat, att_ship_entry.cls, vic_cid, vic_sid, stale_vic_char, vic_ship_feat, vic_ship_entry.cls, 1.0, 1.0, float(km_isk_destroyed), float(log_isk), 1, "att_stale_p2"))
    # 3. Ship Masked (W2 vs W1)
    samples.append(assemble_row(att_cid, att_sid, att_char_feat, att_ship_feat, att_ship_entry.cls, vic_cid, vic_sid, vic_char_feat, empty_vic_ship, "", 1.0, 0.0, float(km_isk_destroyed), float(log_isk), 1, "att_w2_vs_w1"))
    # 4. Ship Masked + Stale (W2 vs W1 stale)
    samples.append(assemble_row(att_cid, att_sid, att_char_feat, att_ship_feat, att_ship_entry.cls, vic_cid, vic_sid, stale_vic_char, empty_vic_ship, "", 1.0, 0.0, float(km_isk_destroyed), float(log_isk), 1, "att_w2_vs_w1_stale"))
    # 5. Pilot Masked (W2 vs W3)
    samples.append(assemble_row(att_cid, att_sid, att_char_feat, att_ship_feat, att_ship_entry.cls, vic_cid, vic_sid, empty_vic_char, vic_ship_feat, vic_ship_entry.cls, 0.0, 1.0, float(km_isk_destroyed), float(log_isk), 1, "att_w2_vs_w3"))
    # 6. Jittered Noise
    samples.append(assemble_row(att_cid, att_sid, build_jittered_features(att_char_feat), att_ship_feat, att_ship_entry.cls, vic_cid, vic_sid, build_jittered_features(vic_char_feat), vic_ship_feat, vic_ship_entry.cls, 1.0, 1.0, float(km_isk_destroyed), float(log_isk), 1, "att_jitter"))

    # -------------------------------------------------------------
    # Perspective B: Victim = Focal (P1) -> -Y
    # -------------------------------------------------------------
    # 7. Full Intel (W2 vs W2)
    samples.append(assemble_row(vic_cid, vic_sid, vic_char_feat, vic_ship_feat, vic_ship_entry.cls, att_cid, att_sid, att_char_feat, att_ship_feat, att_ship_entry.cls, 1.0, 1.0, float(-km_isk_destroyed), float(-log_isk), 0, "vic_full"))
    # 8. Stale Intel (P2 7d/30d zeroed)
    samples.append(assemble_row(vic_cid, vic_sid, vic_char_feat, vic_ship_feat, vic_ship_entry.cls, att_cid, att_sid, stale_att_char, att_ship_feat, att_ship_entry.cls, 1.0, 1.0, float(-km_isk_destroyed), float(-log_isk), 0, "vic_stale_p2"))
    # 9. Ship Masked (W2 vs W1)
    samples.append(assemble_row(vic_cid, vic_sid, vic_char_feat, vic_ship_feat, vic_ship_entry.cls, att_cid, att_sid, att_char_feat, empty_att_ship, "", 1.0, 0.0, float(-km_isk_destroyed), float(-log_isk), 0, "vic_w2_vs_w1"))
    # 10. Ship Masked + Stale (W2 vs W1 stale)
    samples.append(assemble_row(vic_cid, vic_sid, vic_char_feat, vic_ship_feat, vic_ship_entry.cls, att_cid, att_sid, stale_att_char, empty_att_ship, "", 1.0, 0.0, float(-km_isk_destroyed), float(-log_isk), 0, "vic_w2_vs_w1_stale"))
    # 11. Pilot Masked (W2 vs W3)
    samples.append(assemble_row(vic_cid, vic_sid, vic_char_feat, vic_ship_feat, vic_ship_entry.cls, att_cid, att_sid, empty_att_char, att_ship_feat, att_ship_entry.cls, 0.0, 1.0, float(-km_isk_destroyed), float(-log_isk), 0, "vic_w2_vs_w3"))
    # 12. Jittered Noise
    samples.append(assemble_row(vic_cid, vic_sid, build_jittered_features(vic_char_feat), vic_ship_feat, vic_ship_entry.cls, att_cid, att_sid, build_jittered_features(att_char_feat), att_ship_feat, att_ship_entry.cls, 1.0, 1.0, float(-km_isk_destroyed), float(-log_isk), 0, "vic_jitter"))

    return samples


def build_ml_dataset(config: MLDatasetConfig, force_rebuild: bool = False) -> Path:
    config.output_dir.mkdir(parents=True, exist_ok=True)

    start_date, end_date = resolve_timeframe(
        config.start_input, config.months_input, config.end_input
    )
    
    out_filename = f"1v1_dataset_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.parquet"
    out_path = config.output_dir / out_filename

    # Fast Path: Check if cached dataset exists
    if out_path.exists() and not force_rebuild:
        df_cached = pd.read_parquet(out_path)
        logger.info("=" * 65)
        logger.info(f"⚡ Found existing dataset: {out_path.name}")
        logger.info(f"• Total Dataset Rows (Datapoints): {len(df_cached):,}")
        logger.info(f"• Unique 1v1 Encounters:           {len(df_cached) // 12:,}")
        logger.info("=" * 65)
        return out_path

    logger.info(f"Target timeframe: {start_date} -> {end_date}")

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

                # Extract 12-sample augmented data points if within requested dates
                if start_date <= km_date <= end_date:
                    if len(attackers) == 1:
                        samples = create_1v1_datapoint(
                            km, char_store, ship_store, rolling_window,
                            km_isk_destroyed, km_date, config.allowed_ship_classes
                        )
                        if samples:
                            all_dataset_rows.extend(samples)
                            total_1v1_fights += 1

                # Update rolling states forward
                gang_size = len(attackers)
                is_solo = len(attackers) == 1

                v_entry = char_store.setdefault(vic_cid, CharEntry(vic_cid))
                v_entry.record_loss(isk=km_isk_destroyed, points=20.0, is_solo=is_solo, day=km_date, ship_id=vic_sid)
                rolling_window.record_loss(vic_cid, km_isk_destroyed)

                if vic_sid in ship_store:
                    ship_store[vic_sid].record_event(day=km_date, isk_destroyed=km_isk_destroyed, is_victim=True)

                for att in attackers:
                    att_cid = att.get("character_id")
                    att_sid = att.get("ship_type_id")
                    if att_cid:
                        a_entry = char_store.setdefault(att_cid, CharEntry(att_cid))
                        a_entry.record_kill(
                            isk=km_isk_destroyed, points=20.0 / max(1, gang_size), is_solo=is_solo,
                            gang_size=gang_size, day=km_date, ship_id=att_sid
                        )
                        rolling_window.record_kill(att_cid, km_isk_destroyed)

                    if att_sid and att_sid in ship_store:
                        ship_store[att_sid].record_event(day=km_date, isk_destroyed=km_isk_destroyed, is_victim=False)

    if all_dataset_rows:
        df = pd.DataFrame(all_dataset_rows)
        df.to_parquet(out_path, index=False, engine="pyarrow", compression="snappy")
        logger.info("=" * 65)
        logger.info(f"✅ Dataset generation complete: {out_path.name}")
        logger.info(f"• Total Dataset Rows (Datapoints): {len(df):,}")
        logger.info(f"• Unique 1v1 Fights Extracted:     {total_1v1_fights:,}")
        logger.info(f"• Augmented Samples per Fight:     12x")
        logger.info(f"• Total Feature Columns:           {len(df.columns) - 6}")
        logger.info("=" * 65)
    else:
        logger.warning("⚠️ No valid 1v1 encounters extracted for the requested parameters.")

    return out_path