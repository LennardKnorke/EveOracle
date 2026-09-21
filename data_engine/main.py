# data_engine/main.py

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from data_engine.etl.snapshot_builder import run_snapshot_builder
from shared.config import logger


def parse_args():
    parser = argparse.ArgumentParser(
        description="EveOracle Data Engine - Historical Combat State & Monthly Snapshot Builder"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing monthly snapshot checkpoints",
    )

    return parser.parse_args()


def main():
    args = parse_args()
    logger.info("Starting EveOracle Data Engine (Monthly Universe Snapshots)")
    logger.info(f"• Overwrite:    {args.overwrite}")

    run_snapshot_builder(
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()