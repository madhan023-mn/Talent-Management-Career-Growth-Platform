"""SQLite-only database connection helpers for Talent Growth."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parent.parent
MYSQL_CORE_SCHEMA_STATEMENTS: List[str] = []
MYSQL_SETTINGS_SCHEMA_STATEMENTS: List[str] = []
PYMYSQL_AVAILABLE = False


def get_db_path() -> Path:
    """Return the configured SQLite file, defaulting to data/talentsphere.db."""
    configured_path = os.getenv("DATABASE_PATH")
    if configured_path:
        path = Path(configured_path)
        db_file = path if path.is_absolute() else BASE_DIR / path
    else:
        db_file = BASE_DIR / "data" / "talentsphere.db"

    db_file.parent.mkdir(parents=True, exist_ok=True)
    return db_file.resolve()


def get_connection() -> sqlite3.Connection:
    """Open the application's only database: SQLite."""
    conn = sqlite3.connect(get_db_path(), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA wal_autocheckpoint = 1")
    return conn


def is_mysql_mode() -> bool:
    """Legacy compatibility: this application no longer supports MySQL."""
    return False


def is_mysql_expected() -> bool:
    """Legacy compatibility: MySQL settings are ignored."""
    return False


def get_mysql_config() -> Dict[str, Any]:
    """Legacy compatibility: do not read or return external database settings."""
    return {}


def ensure_mysql_database_exists() -> None:
    """Legacy compatibility no-op; only SQLite is used."""
    return None


def test_mysql_connection() -> Dict[str, Any]:
    """Legacy compatibility response for the retired MySQL diagnostics action."""
    return {
        "success": False,
        "engine": "SQLite",
        "message": "SQLite is the only supported database.",
    }
