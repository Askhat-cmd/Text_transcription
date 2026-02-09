#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Archive and delete old SQLite sessions based on retention policy."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.config import config
from bot_agent.storage import SessionManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cleanup old bot sessions in SQLite storage."
    )
    parser.add_argument(
        "--active-days",
        type=int,
        default=config.SESSION_RETENTION_DAYS,
        help="Archive active sessions older than this value.",
    )
    parser.add_argument(
        "--archive-days",
        type=int,
        default=config.ARCHIVE_RETENTION_DAYS,
        help="Delete archived sessions older than this value.",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=str(config.BOT_DB_PATH),
        help="Path to SQLite DB file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.active_days < 1 or args.archive_days < 1:
        print("❌ active-days and archive-days must be >= 1")
        return 2

    manager = SessionManager(db_path=args.db_path)
    result = manager.run_retention_cleanup(
        active_days=args.active_days,
        archive_days=args.archive_days,
    )

    print("✅ Cleanup complete")
    print(f"DB: {args.db_path}")
    print(f"Archived sessions: {result['archived_count']}")
    print(f"Deleted archived sessions: {result['deleted_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
