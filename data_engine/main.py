# data_engine/main.py

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from data_engine.etl.snapshot_builder import run_snapshot_builder


def parse_args():
    parser = argparse.ArgumentParser(
        description="EveOracle Data Engine - Historical Combat State & Monthly Snapshot Builder"
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=2007,
        help="Start year to begin historical replay (default: 2007)",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=2026,
        help="End year of historical replay (default: 2026)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing monthly snapshot checkpoints",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 65)
    print("🛰️  Starting EveOracle Data Engine (Monthly Universe Snapshots)")
    print(f"• Year Range:   {args.start_year} -> {args.end_year}")
    print(f"• Overwrite:    {args.overwrite}")
    print("=" * 65)

    run_snapshot_builder(
        start_year=args.start_year,
        end_year=args.end_year,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()