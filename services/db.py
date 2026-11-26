"""
Enterprise Dual-Engine Database Layer (MySQL 8.0 Primary + SQLite Fallback)
Provides seamless transparent MySQL connectivity for Talent Growth Platform
while preserving full compatibility with existing SQLite-style queries and tests.
"""

from __future__ import annotations
import os
import re
import sqlite3
import tempfile
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

try:
    import pymysql
    import pymysql.cursors
    import pymysql.err
    PYMYSQL_AVAILABLE = True
except ImportError:
    pymysql = None  # type: ignore
    PYMYSQL_AVAILABLE = False


# ------------------------------------------------------------------------------
# CONFIGURATION & ENGINE DETECTION
# ------------------------------------------------------------------------------
def _get_db_setting(key: str, default: str = "") -> str:
    """Reads a database setting from os.environ, falling back to Streamlit secrets."""
    val = os.getenv(key)
    if val is not None and str(val).strip() != "":
        return str(val).strip()
    try:
        import streamlit as st
        if key in st.secrets and str(st.secrets[key]).strip() != "":
            return str(st.secrets[key]).strip()
        if key.lower() in st.secrets and str(st.secrets[key.lower()]).strip() != "":
            return str(st.secrets[key.lower()]).strip()
        for section in ("mysql", "database", "db"):
            if section in st.secrets:
                sec = st.secrets[section]
                sub_key = key.replace("DB_", "").replace("MYSQL_", "").lower()
                if sub_key in sec and str(sec[sub_key]).strip() != "":
                    return str(sec[sub_key]).strip()
    except Exception:
        pass
    return default


def get_mysql_config() -> Dict[str, Any]:
    """Returns MySQL connection settings from environment variables or Streamlit secrets."""
    host = _get_db_setting("DB_HOST", _get_db_setting("MYSQL_HOST", "127.0.0.1"))
    port_str = _get_db_setting("DB_PORT", _get_db_setting("MYSQL_PORT", "3306"))
    try:
        port = int(port_str)
    except (ValueError, TypeError):
        port = 3306
    user = _get_db_setting("DB_USER", _get_db_setting("MYSQL_USER", ""))
    password = _get_db_setting("DB_PASSWORD", _get_db_setting("MYSQL_PASSWORD", ""))
    database = _get_db_setting("DB_NAME", _get_db_setting("MYSQL_DATABASE", ""))
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
    }


def _is_temp_sqlite_test_override() -> bool:
    """
    Detects when unit tests explicitly override DATABASE_PATH to a temporary
    SQLite file so SQLite-specific unit tests remain isolated from production MySQL.
    """
    if os.getenv("FORCE_MYSQL_TESTS") == "1":
        return False
    db_path = os.getenv("DATABASE_PATH", "")
    if not db_path:
        return False
    norm = os.path.normcase(os.path.abspath(db_path))
    tmp_root = os.path.normcase(os.path.abspath(tempfile.gettempdir()))
    if norm.startswith(tmp_root) or "test_" in Path(db_path).name.lower():
        return True
    return False


def is_mysql_expected() -> bool:
    """Returns True if MySQL is explicitly configured via DB_ENGINE or environment credentials."""
    if _is_temp_sqlite_test_override():
        return False
    engine = _get_db_setting("DB_ENGINE", "").lower()
    if engine == "sqlite":
        return False
    if engine == "mysql":
        return True
    cfg = get_mysql_config()
    return bool(cfg.get("user") and cfg.get("database"))


def is_mysql_mode() -> bool:
    """Returns True when MySQL should be used as the active database engine."""
    if not PYMYSQL_AVAILABLE:
        return False
    if _is_temp_sqlite_test_override():
        return False
    engine = _get_db_setting("DB_ENGINE", "").lower()
    if engine == "sqlite":
        return False
    cfg = get_mysql_config()
    if engine == "mysql":
        return bool(cfg["user"] and cfg["database"])
    # Auto-enable MySQL if DB_USER and DB_NAME are configured
    return bool(cfg["user"] and cfg["database"])


def test_mysql_connection() -> Dict[str, Any]:
    """
    Tests direct MySQL connectivity and returns non-sensitive status metrics.
    Never exposes passwords.
    """
    if not PYMYSQL_AVAILABLE:
        return {
            "success": False,
            "engine": "MySQL",
            "error": "The 'pymysql' package is not installed. Run 'pip install pymysql' to enable MySQL connectivity.",
            "message": "The 'pymysql' package is missing. Please run 'pip install pymysql'."
        }
    cfg = get_mysql_config()
    if not cfg["user"] or not cfg["database"]:
        return {
            "success": False,
            "engine": "MySQL",
            "host": cfg["host"],
            "port": cfg["port"],
            "database": cfg["database"],
            "error": "MySQL configuration incomplete: DB_USER or DB_NAME is missing.",
            "message": "MySQL credentials incomplete in .env. Please provide DB_USER and DB_NAME."
        }
    try:
        raw_conn = pymysql.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
            charset="utf8mb4",
            autocommit=False,
            connect_timeout=5,
            read_timeout=10,
            write_timeout=10,
        )
        try:
            with raw_conn.cursor() as cur:
                cur.execute("SELECT VERSION(), DATABASE()")
                row = cur.fetchone()
                version = row[0] if row else "Unknown"
                db_name = row[1] if row and len(row) > 1 else cfg["database"]
            return {
                "success": True,
                "engine": "MySQL",
                "host": cfg["host"],
                "port": cfg["port"],
                "database": db_name,
                "version": version,
                "message": f"Successfully connected to MySQL database '{db_name}' at {cfg['host']}:{cfg['port']} (MySQL {version})."
            }
        finally:
            raw_conn.close()
    except Exception as exc:
        return {
            "success": False,
            "engine": "MySQL",
            "host": cfg["host"],
            "port": cfg["port"],
            "database": cfg["database"],
            "error": str(exc),
            "message": f"Failed to connect to MySQL database '{cfg['database']}' at {cfg['host']}:{cfg['port']}: {exc}"
        }


def get_db_path() -> Path:
    """Returns the SQLite database path (used in SQLite mode or for migration)."""
    env_path = os.getenv("DATABASE_PATH")
    if env_path:
        p = Path(env_path)
        db_file = p if p.is_absolute() else (BASE_DIR / p)
    else:
        db_file = BASE_DIR / "data" / "talentsphere.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    return db_file.resolve()


# ------------------------------------------------------------------------------
# FLEXIBLE ROW WRAPPER (Supports both row["col"] and row[0] like sqlite3.Row)
# ------------------------------------------------------------------------------
def _normalize_value(val: Any) -> Any:
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(val, date):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, Decimal):
        return float(val)
    return val


class FlexRow(dict):
    """
    Dict-like database row that also supports integer indexing (row[0]) and
    normalizes MySQL datetime/Decimal values to match SQLite string/float semantics.
    """

    def __init__(self, columns: Sequence[str], values: Sequence[Any]):
        normalized = [_normalize_value(v) for v in values]
        super().__init__(zip(columns, normalized))
        self._values = tuple(normalized)

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, (int, slice)):
            return self._values[key]
        return super().__getitem__(key)


# ------------------------------------------------------------------------------
# SQLITE -> MYSQL QUERY TRANSLATOR
# ------------------------------------------------------------------------------
def _replace_qmarks_with_percent_s(sql: str, has_params: bool) -> str:
    """
    Replaces SQLite `?` parameter placeholders with MySQL `%s` outside of
    single-quoted string literals, while escaping literal `%` when params exist.
    """
    out: List[str] = []
    in_single = False
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if ch == "'":
            out.append(ch)
            if in_single and i + 1 < n and sql[i + 1] == "'":
                out.append("'")
                i += 2
                continue
            in_single = not in_single
        elif ch == "%" and has_params:
            out.append("%%")
        elif ch == "?" and not in_single:
            out.append("%s")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def _translate_sql_to_mysql(sql: str, has_params: bool = False) -> Tuple[str, Optional[str]]:
    """
    Translates SQLite-dialect queries into valid MySQL 8.0 SQL.
    Returns (translated_sql, special_mode) where special_mode handles PRAGMA emulation.
    """
    stripped = sql.strip()
    upper = stripped.upper()

    # 1. PRAGMA handling
    if upper.startswith("PRAGMA"):
        m_ti = re.match(r"PRAGMA\s+table_info\s*\(\s*([a-zA-Z0-9_]+)\s*\)", stripped, re.I)
        if m_ti:
            tbl = m_ti.group(1)
            return (
                f"SELECT COLUMN_NAME AS name, "
                f"IF(IS_NULLABLE = 'NO', 1, 0) AS `notnull`, "
                f"DATA_TYPE AS type, "
                f"COLUMN_DEFAULT AS dflt_value, "
                f"IF(COLUMN_KEY = 'PRI', 1, 0) AS pk "
                f"FROM INFORMATION_SCHEMA.COLUMNS "
                f"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{tbl}' "
                f"ORDER BY ORDINAL_POSITION",
                None,
            )
        if "INTEGRITY_CHECK" in upper:
            return ("SELECT 'ok' AS integrity_check", None)
        if "FOREIGN_KEYS" in upper:
            if "OFF" in upper or "= 0" in upper or "=0" in upper:
                return ("SET FOREIGN_KEY_CHECKS = 0", None)
            return ("SET FOREIGN_KEY_CHECKS = 1", None)
        # WAL / synchronous / busy_timeout -> no-op in MySQL
        return ("", "noop")

    # 2. sqlite_master table lookup
    if "SQLITE_MASTER" in upper:
        m_tbl = re.search(r"name\s*=\s*'([^']+)'", stripped, re.I)
        if m_tbl:
            tbl = m_tbl.group(1)
            return (
                f"SELECT TABLE_NAME AS name FROM INFORMATION_SCHEMA.TABLES "
                f"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{tbl}'",
                None,
            )
        return (
            "SELECT TABLE_NAME AS name FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE()",
            None,
        )

    # 3. CREATE TABLE IF NOT EXISTS email_logs (inline calls from email_service.py)
    if upper.startswith("CREATE TABLE") and "EMAIL_LOGS" in upper and "AUTOINCREMENT" in upper:
        return (MYSQL_EMAIL_LOGS_DDL, None)

    q = sql

    # 4. INSERT OR IGNORE / UPDATE OR IGNORE -> INSERT IGNORE / UPDATE IGNORE
    q = re.sub(r"\bINSERT\s+OR\s+IGNORE\s+INTO\b", "INSERT IGNORE INTO", q, flags=re.I)
    q = re.sub(r"\bUPDATE\s+OR\s+IGNORE\b", "UPDATE IGNORE", q, flags=re.I)

    # 5. INSERT OR REPLACE -> REPLACE
    q = re.sub(r"\bINSERT\s+OR\s+REPLACE\s+INTO\b", "REPLACE INTO", q, flags=re.I)

    # 6. ON CONFLICT(...) DO UPDATE SET ... excluded.col -> ON DUPLICATE KEY UPDATE ... VALUES(col)
    if re.search(r"\bON\s+CONFLICT\b", q, re.I):
        q = re.sub(
            r"\bON\s+CONFLICT\s*\([^)]+\)\s*DO\s+UPDATE\s+SET\b",
            "ON DUPLICATE KEY UPDATE",
            q,
            flags=re.I,
        )
        q = re.sub(r"\bexcluded\.([a-zA-Z_][a-zA-Z0-9_]*)", r"VALUES(\1)", q, flags=re.I)

    # 7. Placeholders ? -> %s
    q = _replace_qmarks_with_percent_s(q, has_params=has_params)

    return (q, None)


# ------------------------------------------------------------------------------
# MYSQL CURSOR & CONNECTION WRAPPERS
# ------------------------------------------------------------------------------
class MySQLCursorWrapper:
    """Wraps a pymysql cursor with SQLite-compatible API, translation, and FlexRow results."""

    def __init__(self, raw_cursor: Any):
        self._cur = raw_cursor
        self._noop_rows: Optional[List[FlexRow]] = None

    @property
    def lastrowid(self) -> int:
        return self._cur.lastrowid

    @property
    def rowcount(self) -> int:
        return self._cur.rowcount

    @property
    def description(self) -> Any:
        return self._cur.description

    def execute(self, sql: str, params: Optional[Union[Sequence[Any], Dict[str, Any]]] = None) -> "MySQLCursorWrapper":
        self._noop_rows = None
        has_params = params is not None and len(params) > 0 if isinstance(params, (list, tuple, dict)) else (params is not None)
        translated, mode = _translate_sql_to_mysql(sql, has_params=has_params)
        if mode == "noop":
            self._noop_rows = [FlexRow(["status"], ["ok"])]
            return self
        try:
            if has_params:
                self._cur.execute(translated, tuple(params) if not isinstance(params, dict) else params)
            else:
                self._cur.execute(translated)
        except Exception as exc:
            if PYMYSQL_AVAILABLE and isinstance(exc, pymysql.err.IntegrityError):
                raise sqlite3.IntegrityError(str(exc)) from exc
            raise
        return self

    def executemany(self, sql: str, seq_of_params: Iterable[Sequence[Any]]) -> "MySQLCursorWrapper":
        self._noop_rows = None
        translated, mode = _translate_sql_to_mysql(sql, has_params=True)
        if mode == "noop":
            return self
        try:
            self._cur.executemany(translated, list(seq_of_params))
        except Exception as exc:
            if PYMYSQL_AVAILABLE and isinstance(exc, pymysql.err.IntegrityError):
                raise sqlite3.IntegrityError(str(exc)) from exc
            raise
        return self

    def _columns(self) -> List[str]:
        desc = self._cur.description
        if not desc:
            return []
        return [d[0] for d in desc]

    def fetchone(self) -> Optional[FlexRow]:
        if self._noop_rows is not None:
            return self._noop_rows.pop(0) if self._noop_rows else None
        row = self._cur.fetchone()
        if row is None:
            return None
        return FlexRow(self._columns(), row)

    def fetchall(self) -> List[FlexRow]:
        if self._noop_rows is not None:
            rows = list(self._noop_rows)
            self._noop_rows = []
            return rows
        rows = self._cur.fetchall()
        if not rows:
            return []
        cols = self._columns()
        return [FlexRow(cols, r) for r in rows]

    def fetchmany(self, size: Optional[int] = None) -> List[FlexRow]:
        if self._noop_rows is not None:
            if size is None:
                size = 1
            res = self._noop_rows[:size]
            self._noop_rows = self._noop_rows[size:]
            return res
        rows = self._cur.fetchmany(size) if size is not None else self._cur.fetchmany()
        if not rows:
            return []
        cols = self._columns()
        return [FlexRow(cols, r) for r in rows]

    def close(self) -> None:
        try:
            self._cur.close()
        except Exception:
            pass

    def __enter__(self) -> "MySQLCursorWrapper":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def __iter__(self):
        return iter(self.fetchall())


class MySQLConnectionWrapper:
    """
    Wraps a pymysql connection to match sqlite3.Connection transaction & helper semantics:
    - `with conn:` commits on normal exit and rolls back on exception (without closing).
    - `conn.execute(...)` and `conn.executescript(...)` work directly.
    """

    is_mysql: bool = True

    def __init__(self, raw_conn: Any):
        self._conn = raw_conn
        self._closed = False

    def cursor(self) -> MySQLCursorWrapper:
        return MySQLCursorWrapper(self._conn.cursor())

    def execute(self, sql: str, params: Optional[Union[Sequence[Any], Dict[str, Any]]] = None) -> MySQLCursorWrapper:
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def executescript(self, script: str) -> None:
        cur = self.cursor()
        try:
            for stmt in _split_sql_statements(script):
                if stmt.strip():
                    cur.execute(stmt)
        finally:
            cur.close()

    def commit(self) -> None:
        if not self._closed:
            self._conn.commit()

    def rollback(self) -> None:
        if not self._closed:
            self._conn.rollback()

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            try:
                self._conn.close()
            except Exception:
                pass

    def __del__(self) -> None:
        self.close()

    def __enter__(self) -> "MySQLConnectionWrapper":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False


def _split_sql_statements(script: str) -> List[str]:
    """Splits a SQL script on semicolons outside single-quoted literals."""
    stmts: List[str] = []
    buf: List[str] = []
    in_single = False
    i = 0
    n = len(script)
    while i < n:
        ch = script[i]
        if ch == "'":
            buf.append(ch)
            if in_single and i + 1 < n and script[i + 1] == "'":
                buf.append("'")
                i += 2
                continue
            in_single = not in_single
        elif ch == ";" and not in_single:
            s = "".join(buf).strip()
            if s:
                stmts.append(s)
            buf = []
        else:
            buf.append(ch)
        i += 1
    rem = "".join(buf).strip()
    if rem:
        stmts.append(rem)
    return stmts


# ------------------------------------------------------------------------------
# CONNECTION FACTORY
# ------------------------------------------------------------------------------
def ensure_mysql_database_exists() -> None:
    """Ensures the configured MySQL database exists (creates it if missing)."""
    if not is_mysql_mode():
        return
    cfg = get_mysql_config()
    try:
        conn = pymysql.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            charset="utf8mb4",
            connect_timeout=10,
            autocommit=True,
        )
        try:
            with conn.cursor() as cur:
                db_safe = re.sub(r"[^a-zA-Z0-9_]", "", cfg["database"])
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{db_safe}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
        finally:
            conn.close()
    except Exception:
        # If the user doesn't have CREATE DATABASE privilege, proceed to connect directly
        pass


def get_connection() -> Union[MySQLConnectionWrapper, sqlite3.Connection]:
    """
    Returns an active database connection.
    Uses MySQL when MySQL is configured. If MySQL is expected (DB_ENGINE=mysql) but fails,
    raises a meaningful error instead of silently falling back to SQLite.
    """
    if _is_temp_sqlite_test_override():
        conn = sqlite3.connect(get_db_path(), timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    engine_setting = _get_db_setting("DB_ENGINE", "").lower()
    if engine_setting == "mysql" or is_mysql_mode():
        if not PYMYSQL_AVAILABLE:
            raise RuntimeError(
                "MySQL engine is configured (DB_ENGINE=mysql), but the 'pymysql' package is not installed. "
                "Please run 'pip install pymysql' to enable MySQL support."
            )
        cfg = get_mysql_config()
        if not cfg["user"] or not cfg["database"]:
            raise RuntimeError(
                "MySQL engine is configured (DB_ENGINE=mysql), but DB_USER or DB_NAME is missing in configuration (.env). "
                "Please configure DB_USER and DB_NAME to connect to MySQL."
            )
        try:
            raw_conn = pymysql.connect(
                host=cfg["host"],
                port=cfg["port"],
                user=cfg["user"],
                password=cfg["password"],
                database=cfg["database"],
                charset="utf8mb4",
                autocommit=False,
                connect_timeout=10,
                read_timeout=30,
                write_timeout=30,
            )
            return MySQLConnectionWrapper(raw_conn)
        except Exception as exc:
            raise RuntimeError(
                f"MySQL Connection Error: Failed to connect to MySQL database '{cfg['database']}' at {cfg['host']}:{cfg['port']}. "
                f"Details: {exc}. Please verify that your local MySQL server is running on port {cfg['port']} and your password is correct."
            ) from exc

    conn = sqlite3.connect(get_db_path(), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA wal_autocheckpoint = 1")
    return conn


# ------------------------------------------------------------------------------
# NATIVE MYSQL 8.0 SCHEMA DEFINITIONS (ALL 26 TABLES)
# ------------------------------------------------------------------------------
MYSQL_EMAIL_LOGS_DDL = """
CREATE TABLE IF NOT EXISTS email_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    to_email VARCHAR(255) NOT NULL,
    user_name VARCHAR(255) DEFAULT '',
    role VARCHAR(100) DEFAULT '',
    org_name VARCHAR(255) DEFAULT '',
    subject VARCHAR(500) DEFAULT '',
    status VARCHAR(50) NOT NULL DEFAULT 'Sent',
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

MYSQL_CORE_SCHEMA_STATEMENTS: List[str] = [
    """
    CREATE TABLE IF NOT EXISTS organizations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        org_id VARCHAR(100) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        official_email VARCHAR(255) DEFAULT '',
        contact_number VARCHAR(100) DEFAULT '',
        status VARCHAR(50) NOT NULL DEFAULT 'Active',
        logo_base64 LONGTEXT,
        address TEXT,
        website VARCHAR(500) DEFAULT '',
        industry VARCHAR(255) DEFAULT 'Technology',
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT chk_org_status CHECK (status IN ('Active', 'Pending', 'Suspended'))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        salt VARCHAR(255) NOT NULL,
        role VARCHAR(50) NOT NULL DEFAULT 'employee',
        employee_id VARCHAR(100) DEFAULT NULL,
        org_id VARCHAR(100) DEFAULT NULL,
        account_type VARCHAR(50) NOT NULL DEFAULT 'Organization',
        department VARCHAR(255) DEFAULT '',
        job_title VARCHAR(255) DEFAULT '',
        status VARCHAR(50) DEFAULT 'Active',
        date_joined VARCHAR(50) DEFAULT '',
        avatar_base64 LONGTEXT,
        phone VARCHAR(100) DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS invitation_codes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        org_id VARCHAR(100) NOT NULL,
        code_hash VARCHAR(255) UNIQUE NOT NULL,
        code_prefix VARCHAR(50) NOT NULL,
        expires_at DATETIME NOT NULL,
        max_uses INT NOT NULL DEFAULT 1,
        used_count INT NOT NULL DEFAULT 0,
        status VARCHAR(50) NOT NULL DEFAULT 'Active',
        created_by VARCHAR(255) DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT chk_inv_status CHECK (status IN ('Active', 'Revoked', 'Expired', 'Depleted')),
        FOREIGN KEY (org_id) REFERENCES organizations(org_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS membership_requests (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        org_id VARCHAR(100) NOT NULL,
        user_name VARCHAR(255) NOT NULL,
        user_email VARCHAR(255) NOT NULL,
        department VARCHAR(255) DEFAULT '',
        designation VARCHAR(255) DEFAULT '',
        status VARCHAR(50) NOT NULL DEFAULT 'Pending',
        reviewed_by INT DEFAULT NULL,
        reviewed_at DATETIME DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT chk_mem_status CHECK (status IN ('Pending', 'Approved', 'Rejected')),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (org_id) REFERENCES organizations(org_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS employees (
        id INT AUTO_INCREMENT PRIMARY KEY,
        employee_id VARCHAR(100) UNIQUE NOT NULL,
        org_id VARCHAR(100) NOT NULL DEFAULT 'ORG-TALENT-01',
        user_id INT DEFAULT NULL,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE DEFAULT NULL,
        phone VARCHAR(100) DEFAULT '',
        department VARCHAR(255) NOT NULL,
        designation VARCHAR(255) NOT NULL,
        joining_date VARCHAR(50) DEFAULT '',
        employment_status VARCHAR(50) NOT NULL DEFAULT 'Active',
        years_experience DOUBLE NOT NULL DEFAULT 0.0,
        primary_skills TEXT NOT NULL,
        account_status VARCHAR(50) NOT NULL DEFAULT 'Active',
        created_by INT DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT chk_emp_status CHECK (employment_status IN ('Active', 'On Leave', 'Terminated')),
        CONSTRAINT chk_emp_exp CHECK (years_experience >= 0),
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS performance_reviews (
        id INT AUTO_INCREMENT PRIMARY KEY,
        employee_id VARCHAR(100) NOT NULL,
        org_id VARCHAR(100) NOT NULL DEFAULT 'ORG-TALENT-01',
        review_period VARCHAR(100) NOT NULL,
        performance_score DOUBLE NOT NULL,
        achievements TEXT,
        strengths TEXT,
        improvements TEXT,
        manager_feedback TEXT,
        reviewer_id INT DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT chk_perf_score CHECK (performance_score >= 1.0 AND performance_score <= 5.0),
        FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE,
        FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS employee_skills (
        id INT AUTO_INCREMENT PRIMARY KEY,
        employee_id VARCHAR(100) NOT NULL,
        org_id VARCHAR(100) NOT NULL DEFAULT 'ORG-TALENT-01',
        user_id INT DEFAULT NULL,
        skill_name VARCHAR(255) NOT NULL,
        category VARCHAR(150) DEFAULT 'Technical',
        proficiency_level VARCHAR(50) NOT NULL,
        years_exp DOUBLE DEFAULT 0.0,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT chk_emp_skill_prof CHECK (proficiency_level IN ('Beginner', 'Intermediate', 'Advanced', 'Expert')),
        FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS career_goals (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        employee_id VARCHAR(100) DEFAULT NULL,
        org_id VARCHAR(100) NOT NULL DEFAULT 'ORG-TALENT-01',
        title VARCHAR(500) NOT NULL,
        target_designation VARCHAR(255) DEFAULT '',
        description TEXT,
        target_date VARCHAR(50) NOT NULL,
        progress INT NOT NULL DEFAULT 0,
        status VARCHAR(50) NOT NULL DEFAULT 'Not Started',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT chk_cg_prog CHECK (progress IN (0, 25, 50, 75, 100)),
        CONSTRAINT chk_cg_status CHECK (status IN ('Not Started', 'In Progress', 'Completed', 'Overdue')),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS training_records (
        id INT AUTO_INCREMENT PRIMARY KEY,
        employee_id VARCHAR(100) NOT NULL,
        org_id VARCHAR(100) NOT NULL DEFAULT 'ORG-TALENT-01',
        course_name VARCHAR(500) NOT NULL,
        provider VARCHAR(255) DEFAULT 'Internal Academy',
        target_skill VARCHAR(255) NOT NULL,
        target_completion_date VARCHAR(50) DEFAULT '',
        status VARCHAR(50) NOT NULL DEFAULT 'Enrolled',
        score DOUBLE DEFAULT 0.0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT chk_tr_status CHECK (status IN ('Enrolled', 'In Progress', 'Completed')),
        FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS profiles (
        user_id INT PRIMARY KEY,
        phone VARCHAR(100) DEFAULT '',
        location VARCHAR(255) DEFAULT '',
        job_title VARCHAR(255) DEFAULT '',
        company VARCHAR(255) DEFAULT '',
        department VARCHAR(255) DEFAULT '',
        industry VARCHAR(255) DEFAULT '',
        employment_type VARCHAR(100) DEFAULT 'Full-time',
        years_experience DOUBLE DEFAULT 0.0,
        linkedin VARCHAR(500) DEFAULT '',
        github VARCHAR(500) DEFAULT '',
        portfolio VARCHAR(500) DEFAULT '',
        education TEXT,
        certifications TEXT,
        summary TEXT,
        experience LONGTEXT,
        projects LONGTEXT,
        resume_text LONGTEXT,
        target_role VARCHAR(255) DEFAULT '',
        target_level VARCHAR(100) DEFAULT 'Senior',
        timeline VARCHAR(100) DEFAULT '6-12 months',
        target_industry VARCHAR(255) DEFAULT '',
        career_goal TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS skills (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        name VARCHAR(255) NOT NULL,
        category VARCHAR(150) NOT NULL,
        proficiency VARCHAR(50) NOT NULL,
        years DOUBLE DEFAULT 0.0,
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS assessments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        employee_id VARCHAR(100) DEFAULT '',
        org_id VARCHAR(100) NOT NULL DEFAULT 'ORG-TALENT-01',
        category VARCHAR(150) NOT NULL,
        skill_name VARCHAR(255) DEFAULT '',
        score DOUBLE NOT NULL,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS progress (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        item VARCHAR(500) NOT NULL,
        percent DOUBLE NOT NULL DEFAULT 0.0,
        status VARCHAR(100) NOT NULL DEFAULT 'In Progress',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS goals (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        employee_id VARCHAR(100) DEFAULT NULL,
        org_id VARCHAR(100) NOT NULL DEFAULT 'ORG-TALENT-01',
        title VARCHAR(500) NOT NULL,
        description TEXT,
        target_date VARCHAR(50) NOT NULL,
        progress INT NOT NULL DEFAULT 0,
        status VARCHAR(50) NOT NULL DEFAULT 'Not Started',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT chk_goals_prog CHECK (progress IN (0, 25, 50, 75, 100)),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS resumes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        org_id VARCHAR(100) NOT NULL DEFAULT 'ORG-TALENT-01',
        summary TEXT,
        skills_json LONGTEXT,
        experience_json LONGTEXT,
        education_json LONGTEXT,
        certifications_json LONGTEXT,
        projects_json LONGTEXT,
        links_json LONGTEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    MYSQL_EMAIL_LOGS_DDL,
]

MYSQL_SETTINGS_SCHEMA_STATEMENTS: List[str] = [
    """
    CREATE TABLE IF NOT EXISTS org_settings (
        org_id VARCHAR(100) PRIMARY KEY,
        org_name VARCHAR(255) NOT NULL,
        logo_base64 LONGTEXT,
        official_email VARCHAR(255) DEFAULT '',
        contact_number VARCHAR(100) DEFAULT '',
        address TEXT,
        website VARCHAR(500) DEFAULT '',
        industry VARCHAR(255) DEFAULT 'Technology',
        description TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS org_employee_config (
        org_id VARCHAR(100) PRIMARY KEY,
        departments LONGTEXT,
        designations LONGTEXT,
        employee_categories LONGTEXT,
        employment_statuses LONGTEXT,
        skill_categories LONGTEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS org_performance_config (
        org_id VARCHAR(100) PRIMARY KEY,
        rating_scale_min INT DEFAULT 1,
        rating_scale_max INT DEFAULT 5,
        rating_descriptions LONGTEXT,
        evaluation_criteria LONGTEXT,
        review_periods LONGTEXT,
        performance_categories LONGTEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS org_career_config (
        org_id VARCHAR(100) PRIMARY KEY,
        career_levels LONGTEXT,
        job_roles LONGTEXT,
        role_skill_requirements LONGTEXT,
        progression_paths LONGTEXT,
        default_timelines LONGTEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS org_training_config (
        org_id VARCHAR(100) PRIMARY KEY,
        training_categories LONGTEXT,
        training_providers LONGTEXT,
        certification_types LONGTEXT,
        completion_criteria LONGTEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS org_pdf_config (
        org_id VARCHAR(100) PRIMARY KEY,
        company_name VARCHAR(255) DEFAULT 'Talent Growth Technologies',
        logo_base64 LONGTEXT,
        header_text VARCHAR(500) DEFAULT 'Confidential - Enterprise Career & Competency Evaluation Dossier',
        footer_text VARCHAR(500) DEFAULT 'Talent Growth Platform - Confidential & Proprietary - Authorized Reviewers Only',
        theme_color VARCHAR(100) DEFAULT 'Navy & Teal',
        report_title VARCHAR(500) DEFAULT 'Employee Career & Competency Intelligence Report',
        confidentiality_notice TEXT,
        date_format VARCHAR(50) DEFAULT '%B %d, %Y',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS org_security_config (
        org_id VARCHAR(100) PRIMARY KEY,
        min_password_length INT DEFAULT 8,
        require_uppercase INT DEFAULT 1,
        require_number INT DEFAULT 1,
        require_special_char INT DEFAULT 1,
        session_timeout_minutes INT DEFAULT 60,
        mfa_enforced INT DEFAULT 0,
        force_pwd_change INT DEFAULT 0,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS org_notification_config (
        org_id VARCHAR(100) PRIMARY KEY,
        review_reminders INT DEFAULT 1,
        training_reminders INT DEFAULT 1,
        goal_deadline_reminders INT DEFAULT 1,
        employee_registration_alerts INT DEFAULT 1,
        report_generation_alerts INT DEFAULT 1,
        reminder_frequency VARCHAR(50) DEFAULT 'Weekly',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id INT PRIMARY KEY,
        profile_photo LONGTEXT,
        phone VARCHAR(100) DEFAULT '',
        location VARCHAR(255) DEFAULT '',
        professional_summary TEXT,
        interested_career_paths LONGTEXT,
        preferred_technical_skills LONGTEXT,
        career_timeline VARCHAR(100) DEFAULT '6-12 months',
        goal_reminders VARCHAR(100) DEFAULT 'Weekly',
        training_notifications VARCHAR(100) DEFAULT '1 Week Before',
        review_notifications INT DEFAULT 1,
        platform_notifications INT DEFAULT 1,
        theme_mode VARCHAR(50) DEFAULT 'Light Mode',
        view_density VARCHAR(50) DEFAULT 'Comfortable',
        profile_visibility VARCHAR(100) DEFAULT 'Organization-Wide',
        deactivation_requested INT DEFAULT 0,
        deactivation_reason TEXT,
        deactivation_requested_at DATETIME DEFAULT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS account_deactivations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        employee_id VARCHAR(100) DEFAULT '',
        org_id VARCHAR(100) DEFAULT '',
        user_name VARCHAR(255) DEFAULT '',
        user_email VARCHAR(255) DEFAULT '',
        reason TEXT,
        status VARCHAR(50) DEFAULT 'Pending',
        requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        processed_by VARCHAR(255) DEFAULT '',
        processed_at DATETIME DEFAULT NULL,
        CONSTRAINT chk_deact_status CHECK (status IN ('Pending', 'Approved', 'Rejected', 'Cancelled'))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]
