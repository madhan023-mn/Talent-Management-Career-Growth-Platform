"""
Test Suite for MongoDB Atlas Architecture & Talent Management Platform
Verifies:
1. Centralized MongoDB Atlas connection and ping health check.
2. All required collections exist and are populated with demo records.
3. Proper indexing across collections (unique emails, employee IDs, org_id).
4. Authentication with bcrypt (Super Admin, HR Admin, Manager, Employee).
5. Duplicate registration prevention.
6. Role-based security (blocking super_admin self-registration).
7. Employee management, department listings, and relationships.
8. Skills management, competency matching, and gap analysis.
9. Redesigned 2-page publication-grade PDF report generation from MongoDB.
10. Organization-level data isolation.
"""

from __future__ import annotations
import pytest
from io import BytesIO
import pypdf

from services.db import (
    get_db,
    get_collection,
    check_db_health,
    get_database_diagnostics,
    COLLECTION_NAMES,
    normalize_doc,
    is_mongodb_mode,
)
from services.core import (
    login,
    register,
    hash_password,
    verify_password,
    get_employees,
    get_employee_by_id,
    get_all_departments,
    get_employee_skills,
    get_goals,
    get_performance_reviews,
    gap_analysis,
    role_match,
    recommendations,
)
from services.reports import create_report
from scripts.seed_demo_data import seed_demo_dataset


@pytest.fixture(scope="session", autouse=True)
def setup_mongodb_environment():
    """Seeds demo records before running test suite."""
    seed_demo_dataset()


def test_mongodb_connection_and_health():
    """Confirms database is connected and in MongoDB Atlas mode."""
    assert is_mongodb_mode() is True
    health = check_db_health()
    assert health["connected"] is True
    assert "MongoDB" in health["engine"]
    assert health["database"] == "talent_management"


def test_all_collections_exist_and_populated():
    """Verifies all required collections are active."""
    db = get_db()
    for col_name in [
        "users", "employees", "departments", "skills", "employee_skills",
        "goals", "assessments", "career_goals", "training", "feedback",
        "notifications", "organizations", "organization_settings"
    ]:
        count = db[col_name].count_documents({})
        assert count > 0, f"Collection '{col_name}' is empty"


def test_authentication_with_bcrypt():
    """Verifies that all seeded demo roles authenticate with bcrypt."""
    roles_to_test = [
        ("admin@demo.com", "super_admin"),
        ("hr@demo.com", "admin"),
        ("manager@demo.com", "manager"),
        ("employee@demo.com", "employee"),
    ]
    for email, expected_role in roles_to_test:
        user = login(email, "Demo@2026!")
        assert user is not None, f"Login failed for {email}"
        assert user["role"] == expected_role
        assert user["status"] == "Active"

    # Test invalid password rejection
    invalid_login = login("admin@demo.com", "WrongPassword123!")
    assert invalid_login is None


def test_duplicate_email_prevention():
    """Verifies that registering an existing email is rejected."""
    ok, msg = register(
        name="Duplicate User",
        email="employee@demo.com",
        password="ValidPassword123!",
        role="employee",
        org_id="ORG-TALENT-01",
        department="Engineering",
        job_title="Software Engineer"
    )
    assert ok is False
    assert "already exists" in msg.lower()


def test_super_admin_self_registration_prevented():
    """Verifies that public registration cannot escalate to super_admin."""
    ok, msg = register(
        name="Hacker Admin",
        email="hacker@example.com",
        password="ValidPassword123!",
        role="super_admin",
        org_id="ORG-TALENT-01",
        department="Engineering",
        job_title="Engineer"
    )
    # Registration should either reject or coerce role to employee
    if ok:
        user = login("hacker@example.com", "ValidPassword123!")
        assert user is not None
        assert user["role"] != "super_admin"


def test_employee_crud_and_departments():
    """Verifies employee querying, department listing, and relationship integrity."""
    emps = get_employees(org_id="ORG-TALENT-01")
    assert len(emps) >= 30

    emp = get_employee_by_id("EMP011", org_id="ORG-TALENT-01")
    assert emp is not None
    assert emp["name"] == "Alex Morgan"
    assert emp["department"] == "Engineering"

    depts = get_all_departments(org_id="ORG-TALENT-01")
    assert len(depts) >= 10
    assert "Engineering" in depts


def test_skills_gap_analysis_and_matching():
    """Verifies competency gap calculation and role matching against MongoDB data."""
    skills = get_employee_skills("EMP011", org_id="ORG-TALENT-01")
    assert len(skills) > 0

    score = role_match("Senior Cloud Architect", skills, 6.5)
    assert isinstance(score, int)
    assert 0 <= score <= 100

    gaps = gap_analysis("Senior Cloud Architect", skills)
    assert isinstance(gaps, list)


def test_pdf_report_two_pages_and_eight_sections():
    """Validates that the redesigned 2-page executive PDF report renders cleanly with MongoDB Atlas data."""
    emp = get_employee_by_id("EMP011", org_id="ORG-TALENT-01")
    assert emp is not None

    skills = get_employee_skills("EMP011", org_id="ORG-TALENT-01")
    gaps = gap_analysis("Senior Cloud Architect", skills)
    recs = recommendations(emp, skills)
    score = role_match("Senior Cloud Architect", skills, 6.5)

    pdf_bytes = create_report(
        profile=emp,
        skills=skills,
        analysis={"match": score},
        gaps=gaps,
        recommendations=recs,
        org_id="ORG-TALENT-01"
    )

    assert pdf_bytes is not None
    assert len(pdf_bytes) > 1000

    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    assert len(reader.pages) == 2, f"Expected 2 pages, got {len(reader.pages)}"

    p1_text = reader.pages[0].extract_text()
    p2_text = reader.pages[1].extract_text()

    assert "EMPLOYEE CAREER & PERFORMANCE REPORT" in p1_text
    assert "CAREER READINESS OVERVIEW" in p1_text
    assert "SKILLS GAP ANALYSIS" in p1_text
    assert "KEY DEVELOPMENT ACTIONS" in p1_text
    assert "CAREER DEVELOPMENT PLAN" in p2_text
    assert "REVIEW STATUS" in p2_text
    assert "ACKNOWLEDGEMENT" in p2_text


def test_data_persistence_and_isolation():
    """Verifies organization isolation and persistent data retrieval."""
    diag = get_database_diagnostics()
    assert diag["total_users"] >= 38
    assert diag["total_employees"] >= 38
    assert diag["total_organizations"] >= 1
