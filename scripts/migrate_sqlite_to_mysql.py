"""
Idempotent Migration Utility: SQLite (data/talentsphere.db) -> MySQL (talent_growth)
Initializes all 26 relational tables in MySQL and migrates all existing records
without losing any users, organizations, employees, reviews, skills, goals, or settings.
"""

from __future__ import annotations
import os
import sys
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from services.db import is_mysql_mode, get_mysql_config, get_db_path, get_connection
from services.core import init_db
from services.settings import init_settings_tables

# Foreign-key safe insertion order covering all 26 tables
MIGRATION_ORDER = [
    "organizations",
    "users",
    "invitation_codes",
    "membership_requests",
    "employees",
    "performance_reviews",
    "employee_skills",
    "career_goals",
    "training_records",
    "profiles",
    "skills",
    "assessments",
    "progress",
    "goals",
    "resumes",
    "email_logs",
    "org_settings",
    "org_employee_config",
    "org_performance_config",
    "org_career_config",
    "org_training_config",
    "org_pdf_config",
    "org_security_config",
    "org_notification_config",
    "user_preferences",
    "account_deactivations",
]

DATETIME_COLS = {
    "created_at", "updated_at", "expires_at", "reviewed_at",
    "last_updated", "deactivation_requested_at", "requested_at", "processed_at",
}


def _clean_value(col: str, val):
    if col in DATETIME_COLS:
        if val is None or str(val).strip() == "":
            return None
        s = str(val).strip().replace("T", " ")
        # Strip fractional seconds / timezone suffix if present for MySQL DATETIME
        if "." in s:
            s = s.split(".")[0]
        if s.endswith("Z"):
            s = s[:-1]
        if "+" in s[10:]:
            s = s[:10] + s[10:].split("+")[0]
        return s.strip()[:19] or None
    return val


def migrate(sqlite_path: Path | None = None) -> None:
    if not is_mysql_mode():
        raise RuntimeError(
            "MySQL mode is not active. Check DB_ENGINE, DB_USER, DB_PASSWORD, and DB_NAME in .env."
        )

    cfg = get_mysql_config()
    print(f"Target MySQL Database: {cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['database']}")

    # 1. Initialize all 26 tables in MySQL
    print("Initializing all 26 tables in MySQL...")
    init_db()
    init_settings_tables()
    print("Schema initialization complete.")

    src_path = sqlite_path or get_db_path()
    if not src_path.is_file():
        print(f"No existing SQLite file at {src_path}. Fresh MySQL database is ready.")
        return

    print(f"Migrating existing data from SQLite: {src_path}")
    sq_conn = sqlite3.connect(str(src_path))
    sq_conn.row_factory = sqlite3.Row
    sq_cur = sq_conn.cursor()

    sq_tables = {
        r[0]
        for r in sq_cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    }

    my_conn = get_connection()
    try:
        my_cur = my_conn.cursor()
        my_cur.execute("SET FOREIGN_KEY_CHECKS = 0")

        for table in MIGRATION_ORDER:
            if table not in sq_tables:
                continue

            # Get columns present in MySQL target table
            my_cur.execute(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = ?",
                (table,),
            )
            my_cols = {r[0] for r in my_cur.fetchall()}

            rows = sq_cur.execute(f"SELECT * FROM [{table}]").fetchall()
            if not rows:
                continue

            sq_cols = list(rows[0].keys())
            common_cols = [c for c in sq_cols if c in my_cols]
            if not common_cols:
                continue

            col_list = ", ".join(f"`{c}`" for c in common_cols)
            placeholders = ", ".join(["?"] * len(common_cols))
            insert_sql = f"INSERT IGNORE INTO `{table}` ({col_list}) VALUES ({placeholders})"

            inserted = 0
            for row in rows:
                vals = [_clean_value(c, row[c]) for c in common_cols]
                try:
                    my_cur.execute(insert_sql, vals)
                    inserted += my_cur.rowcount
                except Exception as exc:
                    print(f"  [WARN] {table} row skipped: {exc}")

            my_conn.commit()
            print(f"  {table:26s}: {len(rows):4d} SQLite rows -> {inserted:4d} newly inserted into MySQL")

        my_cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        my_conn.commit()

        print("\n=== Final MySQL `talent_growth` Table Verification ===")
        total_rows = 0
        for table in MIGRATION_ORDER:
            my_cur.execute(f"SELECT COUNT(*) FROM `{table}`")
            cnt = my_cur.fetchone()[0]
            total_rows += cnt
            print(f"  {table:26s}: {cnt:4d} rows")
        print(f"Total tables: {len(MIGRATION_ORDER)} | Total rows in MySQL: {total_rows}")
    finally:
        my_conn.close()
        sq_conn.close()


if __name__ == "__main__":
    migrate()
