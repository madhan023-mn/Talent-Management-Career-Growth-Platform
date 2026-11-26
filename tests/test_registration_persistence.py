import pytest
import os
import sys
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
    verify_password,
)
from services.db import get_db, is_mongodb_mode, check_db_health
from scripts.seed_demo_data import seed_demo_dataset

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
    "date_joined",
]


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Ensure database is seeded and ready for testing."""
    seed_demo_dataset()


def test_mongodb_database_resolution():
    """Verify that MongoDB Atlas is the active database engine and resolves properly."""
    assert is_mongodb_mode() is True
    health = check_db_health()
    assert health["connected"] is True
    assert "MongoDB" in health["engine"]
    assert health["database"] == "talent_management"


def test_individual_registration_all_13_fields():
    """Verify individual registration populates all 13 required fields and commits to database."""
    test_email = "aarav.test.individual@testdomain.com"
    ok, msg = register_individual(
        name="Aarav Sharma",
        email=test_email,
        password="SecureIndividualPass123",
        primary_skills="Python, SQL, Streamlit",
        years_experience=3.5,
        department="Engineering",
        job_title="Data Engineer",
    )
    assert ok is True, f"Registration failed: {msg}"

    # Confirm account appears in database via wrapper connection
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
    assert row_dict["employee_id"] is not None
    assert row_dict["department"] == "Engineering"
    assert row_dict["job_title"] == "Data Engineer"
    assert row_dict["status"] == "Active"
    assert len(row_dict["password_hash"]) > 20
    assert len(row_dict["salt"]) > 10

    # Confirm that credentials and account also appear in employees table
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employees WHERE LOWER(email) = ?", (test_email.lower(),))
    emp_record = cur.fetchone()
    conn.close()
    assert emp_record is not None, "Newly registered individual account must appear in employees table"
    assert emp_record["name"] == "Aarav Sharma"


def test_new_organization_registration_hr_admin_all_13_fields():
    """Verify new organization registration creates HR Admin with all 13 fields and links to org."""
    admin_email = "maya.hr.leader@innovatetech.org"
    ok, msg = register(
        name="Maya Patel",
        email=admin_email,
        password="SuperSecureAdminPass456",
        role="admin",
        org_name="InnovateTech Solutions",
        department="Human Resources",
        job_title="Head of People",
        is_new_org=True,
        registration_type="new_org",
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


def test_existing_organization_employee_registration():
    """Verify employee registration under existing organization saves to users and employees."""
    emp_email = "vikram.joiner@talentgrowth.com"
    ok, msg = register(
        name="Vikram Singh",
        email=emp_email,
        password="EmployeePassword2026",
        role="employee",
        org_id="ORG-TALENT-01",
        org_name="Talent Growth Technologies",
        department="Product Management",
        job_title="Product Manager",
        registration_type="join_org",
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

    # Confirm employee is also recorded in employees collection
    cur.execute("SELECT * FROM employees WHERE user_id = ?", (u_dict["id"],))
    emp_row = cur.fetchone()
    conn.close()
    assert emp_row is not None, "Employee was not found in employees table"


def test_duplicate_email_registration_prevention():
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


def test_login_authentication_and_password_verification():
    """Verify login authentication works with salt, case-insensitive email, and catches bad passwords."""
    user_email = "SecurityTester@Domain.Com"
    password = "CorrectHorseBatteryStaple2026!"

    ok, msg = register_individual(
        name="Security Tester",
        email=user_email,
        password=password,
        department="Engineering",
        job_title="Security Engineer",
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


def test_database_diagnostics_and_user_verification():
    """Verify database diagnostics returns correct counts, db name, and confirmed user details without secrets."""
    diag_before = get_database_diagnostics()
    assert diag_before["connected"] is True
    assert "talent_management" in diag_before["filename"]
    assert "password" not in str(diag_before).lower()
    assert "hash" not in str(diag_before).lower()

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


def test_write_persistence_flushes_immediately():
    """Verify writes are immediately queryable via both Mongo wrapper and native collection."""
    test_email = "instant.write@test.org"
    register_individual(name="Instant Writer", email=test_email, password="Password123!")

    # checkpoint_db acknowledges synchronous commit
    res = checkpoint_db()
    assert res == (0, 0, 0)

    # Query directly from collection
    db = get_db()
    user_doc = db["users"].find_one({"email": test_email.lower()})
    assert user_doc is not None
    assert user_doc["name"] == "Instant Writer"


def test_reinit_preserves_registered_users():
    """Verify restarting/reinitializing the database does NOT purge user accounts."""
    test_email = "preserve.me@testdomain.com"
    register_individual(name="Preserved User", email=test_email, password="SafePassword123!")

    # Simulate app restart calling init_db()
    init_db()

    # User must still exist!
    verified = verify_user_in_db(test_email)
    assert verified is not None, "User was purged or lost across init_db() restart!"


def test_mongodb_production_users_intact():
    """Confirm the MongoDB database retains all users."""
    db = get_db()
    count = db["users"].count_documents({})
    assert count >= 8, f"Expected at least 8 users in database, found {count}"
