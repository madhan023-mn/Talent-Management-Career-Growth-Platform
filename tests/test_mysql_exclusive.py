import os
import sys
from pathlib import Path
import pytest

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from services.db import get_connection, is_mysql_mode, is_mysql_expected, test_mysql_connection as check_mysql_conn
from services.core import (
    check_db_health,
    get_database_diagnostics,
    get_profile,
    save_profile,
    register_individual,
)


def test_mysql_connection_and_mode():
    """Validates that MySQL is the exclusive active database engine."""
    assert is_mysql_mode() is True
    assert is_mysql_expected() is True

    res = check_mysql_conn()
    assert res.get("success") is True, f"Connection failed: {res}"
    assert res.get("database") == "talent_growth"

    conn = get_connection()
    assert getattr(conn, "is_mysql", False) is True
    cur = conn.cursor()
    cur.execute("SELECT DATABASE()")
    assert cur.fetchone()[0] == "talent_growth"
    conn.close()


def test_mysql_health_and_diagnostics():
    """Validates MySQL diagnostics and health reporting."""
    health = check_db_health()
    assert health.get("engine") == "MySQL"
    assert health.get("connected") is True

    diag = get_database_diagnostics()
    assert diag.get("engine") == "MySQL"
    assert diag.get("connected") is True
    assert diag.get("filename") == "talent_growth"


def test_registration_and_profile_in_mysql():
    """Validates that registration and profile management write directly to MySQL."""
    test_email = "test_pytest_mysql@example.com"
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM profiles WHERE user_id IN (SELECT id FROM users WHERE email = ?)", (test_email,))
        conn.execute("DELETE FROM employees WHERE email = ?", (test_email,))
        conn.execute("DELETE FROM users WHERE email = ?", (test_email,))
    conn.close()

    ok, msg = register_individual(
        name="Pytest MySQL User",
        email=test_email,
        password="Password@123",
        confirm_password="Password@123",
        job_title="Full Stack Engineer",
        department="Engineering",
        phone="+1-555-0987",
        years_experience=4.0,
        primary_skills="Python, SQL, React",
    )
    assert ok is True, f"Registration failed: {msg}"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email FROM users WHERE email = ?", (test_email,))
    user = cur.fetchone()
    assert user is not None
    uid = user["id"]
    conn.close()

    # Update career direction
    save_res = save_profile(uid, {
        "job_title": "Full Stack Engineer",
        "target_role": "Senior Software Engineer",
        "target_level": "Senior",
        "timeline": "6–12 months",
    })
    assert save_res is True

    prof = get_profile(uid)
    assert prof.get("target_role") == "Senior Software Engineer"
    assert prof.get("target_level") == "Senior"

    # Cleanup
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM profiles WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM employees WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM users WHERE id = ?", (uid,))
    conn.close()


def test_zero_sqlite_files_exist():
    """Ensures no SQLite database files exist in data/ or root directory."""
    db_files = list(Path(".").glob("**/*.db")) + list(Path(".").glob("**/*.sqlite")) + list(Path(".").glob("**/*.sqlite3"))
    db_files = [f for f in db_files if not str(f).startswith(".venv")]
    assert len(db_files) == 0, f"Found SQLite files: {db_files}"
    assert not Path("data/talentsphere.db").exists()
