# ml_engine/etl/timeframe_resolver.py

import calendar
import re
from datetime import datetime, date
from pathlib import Path
from typing import Tuple, Optional, List


def add_months_to_date(source_date: date, months: int) -> date:
    """Adds N months to a date without external dependencies."""
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def parse_flexible_date(date_str: str, is_end_of_month: bool = False) -> date:
    """
    Parses 'YYYY-MM' or 'YYYY-MM-DD'. If 'YYYY-MM' is passed for an end date,
    it resolves to the last day of that month.
    """
    clean_str = date_str.strip()

    # Match YYYY-MM
    if re.match(r"^\d{4}-\d{2}$", clean_str):
        year, month = map(int, clean_str.split("-"))
        if is_end_of_month:
            last_day = calendar.monthrange(year, month)[1]
            return date(year, month, last_day)
        return date(year, month, 1)

    # Match YYYY-MM-DD
    try:
        return datetime.strptime(clean_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: '{date_str}'. Expected 'YYYY-MM' or 'YYYY-MM-DD'.")


def resolve_timeframe(
    start_input: str,
    months_input: Optional[int] = None,
    end_input: Optional[str] = None,
) -> Tuple[date, date]:
    """
    Resolves start and end dates with validation.
    """
    start_date = parse_flexible_date(start_input, is_end_of_month=False)

    if months_input is not None and end_input is not None:
        raise ValueError("Cannot specify both --months and --end-date. Choose one.")

    if months_input is not None:
        if months_input <= 0:
            raise ValueError("--months must be a positive integer.")
        raw_end = add_months_to_date(start_date, months_input)
        # End on the day before the start day of the next cycle
        end_date = date.fromordinal(raw_end.toordinal() - 1)
    elif end_input is not None:
        end_date = parse_flexible_date(end_input, is_end_of_month=True)
    else:
        # Default: 12 months duration
        raw_end = add_months_to_date(start_date, 12)
        end_date = date.fromordinal(raw_end.toordinal() - 1)

    if start_date > end_date:
        raise ValueError(f"Start date ({start_date}) cannot be after end date ({end_date}).")

    if start_date < date(2007, 12, 1):
        raise ValueError("Start date cannot precede EVE historical logging inception (2007-12-01).")

    return start_date, end_date


def find_nearest_preceding_snapshot(snapshots_dir: Path, target_date: date) -> Tuple[date, Path]:
    """
    Finds the latest snapshot file whose date is <= target_date.
    Returns (snapshot_date, snapshot_path).
    """
    if not snapshots_dir.exists():
        raise FileNotFoundError(f"Snapshots directory does not exist: {snapshots_dir}")

    snapshot_files = list(snapshots_dir.glob("snapshot_*.pkl.gz"))
    if not snapshot_files:
        raise FileNotFoundError(f"No snapshot files (.pkl.gz) found in {snapshots_dir}. Run data_engine first!")

    parsed_snapshots: List[Tuple[date, Path]] = []

    for path in snapshot_files:
        stem = path.name.replace("snapshot_", "").replace(".pkl.gz", "")
        parts = stem.split("-")
        try:
            year, month = int(parts[0]), int(parts[1])
            snap_date = date(year, month, 1)
            parsed_snapshots.append((snap_date, path))
        except Exception:
            continue

    eligible = [s for s in parsed_snapshots if s[0] <= target_date]
    if not eligible:
        parsed_snapshots.sort(key=lambda s: s[0])
        return parsed_snapshots[0]

    eligible.sort(key=lambda s: s[0], reverse=True)
    return eligible[0]