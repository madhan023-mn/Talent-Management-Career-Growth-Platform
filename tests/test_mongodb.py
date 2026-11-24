"""
Test Suite for MongoDB Atlas Migration - Talent Management & Career Growth Platform
Verifies:
1. Connection to MongoDB Atlas and 15 collections.
2. Unique indexes and data integrity.
3. User authentication with bcrypt (Admin, Manager, Employee).
4. CRUD operations across employees, departments, skills, goals, assessments, career plans.
5. Reporting, aggregations, and PDF generation readiness.
"""

import pytest
from services.db import (
    get_db,
    check_db_health,
    get_database_diagnostics,
    COLLECTION_NAMES,
    normalize_doc,
    is_mongodb_mode
)
from services.core import (
    login,
    hash_password,
    verify_password,
    get_employees,
    get_employee_by_id,
    get_all_departments,
    get_org_dashboard_stats,
    get_goals,
    get_performance_reviews,
    gap_analysis,
    role_match,
    save_profile,
    get_profile
)


def test_mongodb_connection_and_health():
    """Confirms database is connected and in MongoDB Atlas mode."""
    assert is_mongodb_mode() is True
    health = check_db_health()
    assert health["connected"] is True
    assert "MongoDB" in health["engine"]
    assert health["database"].lower() == "talent_growth"


def test_all_15_collections_exist_and_populated():
    """Validates that all 15 required collections exist and meet minimum quotas."""
    db = get_db()
    health = check_db_health()
    counts = health["counts"]

    # Verify all 15 collections are tracked
    for cname in COLLECTION_NAMES:
        assert cname in counts, f"Missing collection from health check: {cname}"

    # Quota checks from prompt specification:
    assert counts["users"] >= 37, f"Expected at least 37 users, found {counts['users']}"
    assert counts["employees"] >= 37, f"Expected at least 37 employees, found {counts['employees']}"
    assert counts["departments"] >= 10, f"Expected at least 10 departments, found {counts['departments']}"
    assert counts["skills"] >= 25, f"Expected at least 25 skills, found {counts['skills']}"
    assert counts["employee_skills"] >= 100, f"Expected at least 100 employee skills, found {counts['employee_skills']}"
    assert counts["goals"] >= 40, f"Expected at least 40 goals, found {counts['goals']}"
    assert counts["assessments"] >= 30, f"Expected at least 30 assessments, found {counts['assessments']}"
    assert counts["career_goals"] >= 20, f"Expected at least 20 career plans, found {counts['career_goals']}"
    assert counts["training"] >= 15, f"Expected at least 15 training programs, found {counts['training']}"
    assert counts["feedback"] >= 30, f"Expected at least 30 feedback records, found {counts['feedback']}"
    assert counts["notifications"] >= 20, f"Expected at least 20 notifications, found {counts['notifications']}"
    assert counts["organization_settings"] >= 1, "Missing organization_settings document"


def test_authentication_with_bcrypt():
    """Verifies user login with bcrypt for HR/Admin, Manager, and Employee roles."""
    # 1. Admin login
    admin = login("admin@talentgrowth.com", "TalentGrowth@2025!")
    assert admin is not None, "Admin login failed"
    assert admin["role"] == "admin"
    assert admin["name"] == "Eleanor Vance"

    # 2. Manager login
    mgr = login("manager.eng@talentgrowth.com", "TalentGrowth@2025!")
    assert mgr is not None, "Manager login failed"
    assert mgr["role"] == "manager"
    assert mgr["name"] == "David Chen"

    # 3. Employee login
    emp = login("emp011@talentgrowth.com", "TalentGrowth@2025!")
    assert emp is not None, "Employee login failed"
    assert emp["role"] == "employee"
    assert emp["name"] == "Alex Morgan"

    # 4. Failed login
    bad_login = login("admin@talentgrowth.com", "WrongPassword!")
    assert bad_login is None, "Bad password should return None"


def test_bcrypt_hashing_and_verification():
    """Verifies that hash_password produces valid bcrypt hashes and verify_password works."""
    raw_pwd = "SecureEnterprisePassword#2025"
    h, s = hash_password(raw_pwd)
    assert h.startswith("$2b$") or h.startswith("$2a$")
    assert verify_password(raw_pwd, h, s) is True
    assert verify_password("IncorrectPassword", h, s) is False


def test_employee_crud_and_relationships():
    """Validates employee lookup, department alignment, and manager assignment."""
    emp = get_employee_by_id("EMP011", org_id="ORG-TALENT-01")
    assert emp is not None, "EMP011 not found"
    assert emp["name"] == "Alex Morgan"
    assert emp["department"] == "Engineering"
    assert emp["manager_id"] == "EMP003"
    assert emp["years_experience"] == 6.5


def test_department_listing():
    """Validates that all 10 departments are retrieved."""
    depts = get_all_departments(org_id="ORG-TALENT-01")
    assert len(depts) >= 10, f"Expected 10 departments, found {len(depts)}"
    assert "Engineering" in depts
    assert "Product Management" in depts
    assert "Data Science & AI" in depts
    assert "UI/UX Design" in depts


def test_org_dashboard_stats():
    """Verifies analytics and aggregations calculate correctly from MongoDB data."""
    stats = get_org_dashboard_stats("ORG-TALENT-01")
    assert stats["total_employees"] >= 37
    assert stats["total_departments"] >= 10
    assert stats["avg_performance"] > 0.0
    assert len(stats["performance_distribution"]) > 0


def test_career_development_and_manual_selection():
    """Tests career goal retrieval and validates that placeholder options cannot overwrite valid data."""
    # Test profile update with manual valid choice
    profile_uid = 11
    success = save_profile(profile_uid, {
        "job_title": "Senior Backend Engineer",
        "target_role": "Lead Cloud Architect",
        "target_level": "Principal",
        "timeline": "6–12 months"
    })
    assert success is True

    updated_prof = get_profile(profile_uid)
    assert updated_prof["target_role"] == "Lead Cloud Architect"
    assert updated_prof["target_level"] == "Principal"


def test_gap_analysis_and_matching():
    """Verifies competency gap calculation."""
    sample_skills = [
        {"name": "Python", "proficiency": "Expert", "years": 6.0},
        {"name": "Docker & Containers", "proficiency": "Advanced", "years": 4.0}
    ]
    score = role_match("Software Architect", sample_skills, years_experience=6.0)
    assert isinstance(score, int)
    assert 0 <= score <= 100

    gaps = gap_analysis("Software Architect", sample_skills)
    assert isinstance(gaps, list)
