#!/usr/bin/env python3
"""
Talent Growth - Automated Online Database Backup & Recovery Utility.

Uses SQLite's online backup API to take clean, consistent snapshots of the
production database while the application is actively running 24/7 without downtime.

Usage:
    python scripts/db_backup.py                 # Create timestamped snapshot
    python scripts/db_backup.py --restore <file> # Restore database from snapshot
    python scripts/db_backup.py --list          # List existing backups
"""

import os
import sys
import shutil
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Resolve root directory
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from services.core import get_db_path, check_db_health


def get_backup_dir() -> Path:
    """Returns the backup directory inside the persistent data folder."""
    db_path = get_db_path()
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def create_backup(retention_count: int = 14) -> Path:
    """
    Creates a non-blocking online snapshot of the database.
    Retains up to `retention_count` recent backups and purges older ones.
    """
    source_db = get_db_path()
    if not source_db.exists():
        raise FileNotFoundError(f"Source database not found at {source_db}")

    backup_dir = get_backup_dir()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"talentsphere_backup_{timestamp}.db"

    # SQLite native online backup: does not lock writers or block live users
    src_conn = sqlite3.connect(str(source_db), timeout=30.0)
    dst_conn = sqlite3.connect(str(backup_file))
    try:
        with dst_conn:
            src_conn.backup(dst_conn, pages=100)
    finally:
        dst_conn.close()
        src_conn.close()

    # Prune older backups if exceeding retention_count
    existing_backups = sorted(backup_dir.glob("talentsphere_backup_*.db"), key=os.path.getmtime)
    if len(existing_backups) > retention_count:
        for old in existing_backups[:-retention_count]:
            try:
                old.unlink()
            except OSError:
                pass

    return backup_file


def restore_backup(backup_file: Path) -> bool:
    """Safely restores the production database from a specified backup file."""
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")

    target_db = get_db_path()
    # Step 1: Create a safety copy of current DB before replacing
    safety_copy = target_db.parent / f"talentsphere_before_restore_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.db"
    if target_db.exists():
        shutil.copy2(target_db, safety_copy)

    # Step 2: Use SQLite online backup API to copy from backup to target
    src_conn = sqlite3.connect(str(backup_file))
    dst_conn = sqlite3.connect(str(target_db), timeout=30.0)
    try:
        with dst_conn:
            src_conn.backup(dst_conn, pages=100)
    finally:
        dst_conn.close()
        src_conn.close()

    return True


def list_backups():
    """Lists all available snapshots and file sizes."""
    backup_dir = get_backup_dir()
    backups = sorted(backup_dir.glob("talentsphere_backup_*.db"), key=os.path.getmtime, reverse=True)
    return [
        {
            "filename": b.name,
            "path": str(b),
            "size_kb": round(b.stat().st_size / 1024, 1),
            "created_at": datetime.fromtimestamp(b.stat().st_mtime).isoformat()
        }
        for b in backups
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Talent Growth Database Backup Utility")
    parser.add_argument("--backup", action="store_true", help="Create an online backup now (default)")
    parser.add_argument("--restore", type=str, help="Restore database from specified backup file path")
    parser.add_argument("--list", action="store_true", help="List all backups")
    parser.add_argument("--retention", type=int, default=14, help="Number of recent backups to keep")

    args = parser.parse_args()

    if args.list:
        backups = list_backups()
        print(f"Found {len(backups)} backups in {get_backup_dir()}:")
        for b in backups:
            print(f"  - {b['filename']} ({b['size_kb']} KB) | {b['created_at']}")
    elif args.restore:
        target = Path(args.restore)
        print(f"Restoring database from {target}...")
        restore_backup(target)
        health = check_db_health()
        print(f"Restore complete! DB Health: Connected={health['connected']}, Integrity={health['integrity']}")
    else:
        print("Creating online database snapshot...")
        bk_path = create_backup(retention_count=args.retention)
        print(f"Backup created successfully: {bk_path} ({round(bk_path.stat().st_size / 1024, 1)} KB)")
