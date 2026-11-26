import pytest
import os
import sys
import tempfile
import sqlite3
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from services.core import (
    BASE_DIR,
    get_db_path,
    get_connection,
    init_db,
    register,
    register_individual,
    login,
    verify_user_in_db,
    get_database_diagnostics,
    checkpoint_db,
    hash_password,
    verify_password
)

REQUIRED_USER_FIELDS = [
    "id",
    "name",
    "email",
    "password_hash",
    "salt",
    "role",
    "employee_id",
    "org_id",
    "account_type",
    "department",
    "job_title",
    "status",
    "date_joined"
]

@pytest.fixture
def isolated_test_db(monkeypatch):
    """Creates a fresh isolated SQLite database for testing registration and persistence."""
    temp_dir = tempfile.mkdtemp()
    temp_db = Path(temp_dir) / "test_persistence.db"
    monkeypatch.setenv("DATABASE_PATH", str(temp_db))
    init_db()
    return temp_db


def test_active_database_resolution(monkeypatch):
    """Verify that get_db_path respects DATABASE_PATH when set, and defaults to data/talentsphere.db."""
    # 1. When DATABASE_PATH is explicitly set to a relative path
    monkeypatch.setenv("DATABASE_PATH", "custom/test_path.db")
    custom_path = get_db_path()
    assert custom_path == BASE_DIR / "custom/test_path.db"

    # 2. When DATABASE_PATH is explicitly set to an absolute path
    abs_temp = Path(tempfile.gettempdir()) / "abs_talentsphere.db"
    monkeypatch.setenv("DATABASE_PATH", str(abs_temp))
    assert get_db_path() == abs_temp

    # 3. When DATABASE_PATH is unset
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    default_path = get_db_path()
    assert default_path == BASE_DIR / "data" / "talentsphere.db"


def test_individual_registration_all_13_fields(isolated_test_db):
    """Verify individual registration populates all 13 required fields and commits to database."""
    test_email = "individual.user@testdomain.com"
    ok, msg = register_individual(
        name="Aarav Sharma",
        email=test_email,
        password="SecureIndividualPass123",
        primary_skills="Python, SQL, Streamlit",
        years_experience=3.5,
        department="Engineering",
        job_title="Data Engineer"
    )
    assert ok is True, f"Registration failed: {msg}"

    # Confirm account appears in database
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE LOWER(email) = ?", (test_email.lower(),))
    row = cur.fetchone()
    conn.close()

    assert row is not None, "User record was not found in users table"
    row_dict = dict(row)

    # Verify all 13 fields are present and valid
    for field in REQUIRED_USER_FIELDS:
        assert field in row_dict, f"Missing required user field: {field}"

    assert row_dict["name"] == "Aarav Sharma"
    assert row_dict["email"] == test_email.lower()
    assert row_dict["role"] == "employee"
    assert row_dict["account_type"] == "Individual"
    assert row_dict["org_id"] is None
    assert row_dict["department"] == "Engineering"
    assert row_dict["job_title"] == "Data Engineer"
    assert row_dict["status"] == "Active"
    assert len(row_dict["password_hash"]) > 20
    assert len(row_dict["salt"]) > 10


def test_new_organization_registration_hr_admin_all_13_fields(isolated_test_db):
    """Verify new organization registration creates HR Admin with all 13 fields and links to org."""
    admin_email = "hr.leader@innovatetech.org"
    ok, msg = register(
        name="Maya Patel",
        email=admin_email,
        password="SuperSecureAdminPass456",
        role="admin",
        org_name="InnovateTech Solutions",
        department="Human Resources",
        job_title="Head of People",
        is_new_org=True,
        registration_type="new_org"
    )
    assert ok is True, f"New org registration failed: {msg}"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE LOWER(email) = ?", (admin_email.lower(),))
    row = cur.fetchone()
    conn.close()

    assert row is not None, "HR Admin user was not found in users table"
    row_dict = dict(row)

    for field in REQUIRED_USER_FIELDS:
        assert field in row_dict, f"Missing required user field: {field}"

    assert row_dict["name"] == "Maya Patel"
    assert row_dict["email"] == admin_email.lower()
    assert row_dict["role"] == "admin"
    assert row_dict["account_type"] == "Organization"
    assert row_dict["org_id"] is not None and row_dict["org_id"].startswith("ORG-")
    assert row_dict["status"] == "Active"


def test_existing_organization_employee_registration(isolated_test_db):
    """Verify employee registration under existing organization saves to users and employees."""
    # First create an organization
    emp_email = "vikram.singh@talentgrowth.com"
    ok, msg = register(
        name="Vikram Singh",
        email=emp_email,
        password="EmployeePassword2026",
        role="employee",
        org_id="ORG-TALENT-01",
        org_name="Talent Growth Technologies",
        department="Product Management",
        job_title="Product Manager",
        registration_type="join_org"
    )
    assert ok is True, f"Employee registration failed: {msg}"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE LOWER(email) = ?", (emp_email.lower(),))
    user_row = cur.fetchone()
    assert user_row is not None, "Employee user was not found in users table"
    u_dict = dict(user_row)

    for field in REQUIRED_USER_FIELDS:
        assert field in u_dict, f"Missing required user field: {field}"

    assert u_dict["role"] == "employee"
    assert u_dict["account_type"] == "Organization"
    assert u_dict["org_id"] == "ORG-TALENT-01"

    # Confirm employee is also recorded in employees table
    cur.execute("SELECT * FROM employees WHERE user_id = ?", (u_dict["id"],))
    emp_row = cur.fetchone()
    conn.close()
    assert emp_row is not None, "Employee was not found in employees table"


def test_duplicate_email_registration_prevention(isolated_test_db):
    """Verify duplicate email registration is prevented with a clear error for both types."""
    email = "duplicate.check@example.com"
    # 1. Register first time
    ok1, _ = register_individual(name="User First", email=email, password="Password12345")
    assert ok1 is True

    # 2. Attempt duplicate individual registration
    ok2, err2 = register_individual(name="User Duplicate", email=email, password="Password12345")
    assert ok2 is False
    assert "already exists" in err2.lower()

    # 3. Attempt duplicate organization registration with same email (case-insensitive)
    ok3, err3 = register(name="User Duplicate Org", email=email.upper(), password="Password12345")
    assert ok3 is False
    assert "already exists" in err3.lower()


def test_login_authentication_and_password_verification(isolated_test_db):
    """Verify login authentication works with salt, case-insensitive email, and catches bad passwords."""
    user_email = "SecurityTester@Domain.Com"
    password = "CorrectHorseBatteryStaple2026!"

    ok, msg = register_individual(
        name="Security Tester",
        email=user_email,
        password=password,
        department="Engineering",
        job_title="Security Engineer"
    )
    assert ok is True

    # 1. Successful login with lowercase email
    logged_in = login(user_email.lower(), password)
    assert logged_in is not None
    assert logged_in["email"] == user_email.lower()
    assert logged_in["name"] == "Security Tester"
    assert logged_in["account_type"] == "Individual"

    # 2. Successful login with uppercase email
    logged_in_upper = login(user_email.upper(), password)
    assert logged_in_upper is not None
    assert logged_in_upper["id"] == logged_in["id"]

    # 3. Failed login with incorrect password
    bad_login = login(user_email, "WrongPasswordTotally!")
    assert bad_login is None


def test_database_diagnostics_and_user_verification(isolated_test_db):
    """Verify database diagnostics returns correct counts, path, and confirmed user details without secrets."""
    diag_before = get_database_diagnostics()
    assert diag_before["connected"] is True
    assert diag_before["filename"] == "test_persistence.db"
    assert "password" not in str(diag_before).lower()
    assert "hash" not in str(diag_before).lower()
    assert "salt" not in str(diag_before).lower()

    # Register a user
    test_email = "diagnostics.user@test.org"
    register_individual(name="Diag User", email=test_email, password="Password999!")

    # Verify user in db helper
    verified = verify_user_in_db(test_email)
    assert verified is not None
    assert verified["email"] == test_email
    assert verified["name"] == "Diag User"
    assert "password_hash" not in verified
    assert "salt" not in verified

    # Check updated diagnostics
    diag_after = get_database_diagnostics()
    assert diag_after["total_users"] == diag_before["total_users"] + 1
    assert any(u["email"] == test_email for u in diag_after["recent_users"])


def test_wal_checkpoint_flushes_immediately(isolated_test_db):
    """Verify checkpoint_db flushes all WAL pages so SQLite file contains changes immediately."""
    register_individual(name="WAL Tester", email="wal.tester@test.org", password="Password123!")

    # Explicit checkpoint call returns non-negative page metrics
    busy, log_pages, ckpt_pages = checkpoint_db()
    assert busy == 0  # 0 indicates checkpoint completed without lock conflict

    # Connect directly with raw sqlite without WAL replay and verify table has the row
    conn = sqlite3.connect(isolated_test_db)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM users WHERE email = 'wal.tester@test.org'")
    row = cur.fetchone()
    conn.close()
    assert row is not None


def test_reinit_preserves_registered_users(isolated_test_db):
    """Verify restarting/reinitializing the database does NOT purge user accounts."""
    test_email = "preserve.me@testdomain.com"
    register_individual(name="Preserved User", email=test_email, password="SafePassword123!")

    # Simulate app restart calling init_db()
    init_db()

    # User must still exist!
    verified = verify_user_in_db(test_email)
    assert verified is not None, "User was purged or lost across init_db() restart!"


def test_production_database_10_users_intact(monkeypatch):
    """Confirm the production database data/talentsphere.db retains its 10 existing users."""
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    prod_path = BASE_DIR / "data" / "talentsphere.db"
    assert prod_path.exists(), "Production database file data/talentsphere.db is missing!"

    conn = sqlite3.connect(prod_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    conn.close()

    assert count >= 10, f"Expected at least 10 users in production database, found {count}"
