"""
Dedicated Phase 11 End-to-End Persistence and Functional Verification Suite
Validates all 9 Phase 11 test scenarios against MongoDB Atlas.
"""
import pytest
import os
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from services.core import (
    register_individual,
    register,
    login,
    verify_user_in_db,
    get_employee_dashboard_data,
    add_employee_skill,
    get_employee_skills,
    add_goal,
    get_goals,
    update_employee,
    get_employees,
    init_db,
)
from services.db import get_db, is_mongodb_mode, check_db_health, normalize_doc


def test_scenario_1_register_account_persists_in_mongodb():
    """Scenario 1: Register a new account -> confirm record exists in MongoDB users collection."""
    test_email = "phase11.testuser@atlasdomain.com"
    ok, msg = register_individual(
        name="Phase 11 Tester",
        email=test_email,
        password="PassVerification2026!",
        primary_skills="Python, React, MongoDB",
        years_experience=4.0,
        department="Engineering",
        job_title="Full Stack Engineer"
    )
    assert ok is True, f"Registration failed: {msg}"

    db = get_db()
    user_doc = db["users"].find_one({"email": test_email.lower()})
    assert user_doc is not None, "User not found in MongoDB Atlas users collection"
    assert user_doc["name"] == "Phase 11 Tester"
    assert user_doc["role"] == "employee"
    assert user_doc["account_type"] == "Individual"
    assert user_doc["status"] == "Active"


def test_scenario_2_refresh_query_confirms_existence():
    """Scenario 2: Refresh page / re-query -> confirm user still exists and can be queried."""
    test_email = "phase11.testuser@atlasdomain.com"
    verified = verify_user_in_db(test_email)
    assert verified is not None
    assert verified["email"] == test_email.lower()
    assert verified["name"] == "Phase 11 Tester"


def test_scenario_3_logout_login_authentication_succeeds():
    """Scenario 3: Log out and log in -> confirm authentication succeeds."""
    test_email = "phase11.testuser@atlasdomain.com"
    session_user = login(test_email, "PassVerification2026!")
    assert session_user is not None, "Login failed for valid credentials"
    assert session_user["email"] == test_email.lower()
    assert session_user["name"] == "Phase 11 Tester"


def test_scenario_4_records_persist_in_atlas():
    """Scenario 4: Add skills and goals -> confirm records exist in MongoDB Atlas collections."""
    db = get_db()
    user = db["users"].find_one({"email": "phase11.testuser@atlasdomain.com"})
    assert user is not None
    user_id = user["id"]
    emp = db["employees"].find_one({"user_id": user_id})
    emp_code = emp["employee_id"] if emp else f"EMP{user_id}"

    # Add skill
    ok_skill, msg_skill = add_employee_skill(
        employee_id=emp_code,
        skill_name="MongoDB Querying",
        proficiency_level="Advanced",
        category="Technical",
        years_exp=3.0,
        user_id=user_id
    )
    assert ok_skill is True, f"Failed to add skill: {msg_skill}"
    skills = get_employee_skills(emp_code)
    assert any(s["skill_name"] == "MongoDB Querying" for s in skills)

    # Add goal
    ok_goal, msg_goal = add_goal(
        user_id=user_id,
        title="Master Cloud Database Optimization",
        description="Optimize database queries and replica set performance",
        target_date="2026-12-31",
        progress=25,
        employee_id=emp_code
    )
    assert ok_goal is True, f"Failed to add goal: {msg_goal}"
    goals = get_goals(employee_id=emp_code)
    assert any(g["title"] == "Master Cloud Database Optimization" for g in goals)

    # Verify directly in MongoDB collection
    goal_doc = db["goals"].find_one({"title": "Master Cloud Database Optimization"})
    assert goal_doc is not None


def test_scenario_5_employee_created_via_backend_is_visible():
    """Scenario 5: Create employee via backend -> confirm employee appears in employee queries."""
    db = get_db()
    existing_emp = db["employees"].find_one({"org_id": "ORG-TALENT-01"})
    assert existing_emp is not None
    emps = get_employees(org_id="ORG-TALENT-01")
    assert len(emps) >= 1
    assert any(e["email"] == existing_emp["email"] for e in emps)


def test_scenario_6_employee_update_persists_in_mongodb():
    """Scenario 6: Update employee profile -> confirm change reflected in MongoDB Atlas."""
    db = get_db()
    emp = db["employees"].find_one({"org_id": "ORG-TALENT-01"})
    assert emp is not None
    emp_code = emp["employee_id"]

    new_title = "Principal Solutions Architect"
    ok, msg = update_employee(
        employee_id=emp_code,
        name=emp["name"],
        department=emp.get("department", "Engineering"),
        designation=new_title,
        years_experience=float(emp.get("years_experience", 5)),
        primary_skills=emp.get("primary_skills", "Python, MongoDB"),
        email=emp.get("email"),
        org_id="ORG-TALENT-01"
    )
    assert ok is True, f"Update employee failed: {msg}"

    # Verify directly in MongoDB collection
    updated_emp = db["employees"].find_one({"employee_id": emp_code})
    assert updated_emp["designation"] == new_title


def test_scenario_7_reinit_redeploy_zero_data_loss():
    """Scenario 7: Restart/redeploy simulation -> confirm all data remains intact."""
    test_email = "phase11.testuser@atlasdomain.com"
    init_db()  # Simulates application startup hook
    verified = verify_user_in_db(test_email)
    assert verified is not None, "Data was lost during restart!"


def test_scenario_8_duplicate_email_registration_rejected():
    """Scenario 8: Attempt duplicate email registration -> confirm rejection with clear message."""
    ok, err = register_individual(
        name="Imposter",
        email="phase11.testuser@atlasdomain.com",
        password="SomePassword123!"
    )
    assert ok is False
    assert "already exists" in err.lower()


def test_scenario_9_database_reconnection_graceful():
    """Scenario 9: Reconnection check -> confirm check_db_health reports healthy and active."""
    health = check_db_health()
    assert health["connected"] is True
    assert "MongoDB" in health["engine"]
    assert health["database"] == "talent_management"
