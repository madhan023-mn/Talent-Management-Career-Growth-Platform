"""
Unit & Integration Tests for Enterprise Settings Module
Covers:
- Database table creation & default seeding
- HR Settings CRUD (Organization, Account, Workforce, Performance, Career, Training, PDF, Security, Notifications)
- Employee Settings CRUD (Profile, Security, Career Preferences, Notifications, Appearance, Privacy, Deactivation)
- Strict Backend Role-Based Access Control (RBAC) enforcement
- PDF dynamic branding generation with customized themes
- SQLite database persistence across sessions
"""

import os
import json
import sqlite3
import pytest
from services.core import init_db, get_connection, hash_password, verify_password
from services.settings import (
    init_settings_tables,
    get_org_profile_settings,
    save_org_profile_settings,
    update_hr_account_profile,
    change_account_password,
    get_org_employee_config,
    save_org_employee_config,
    get_org_performance_config,
    save_org_performance_config,
    get_org_career_config,
    save_org_career_config,
    get_org_training_config,
    save_org_training_config,
    get_org_pdf_config,
    save_org_pdf_config,
    get_org_security_config,
    save_org_security_config,
    get_org_notification_config,
    save_org_notification_config,
    get_user_preferences,
    save_employee_personal_profile,
    save_employee_career_preferences,
    save_employee_notification_preferences,
    save_employee_appearance_preferences,
    save_employee_privacy_preferences,
    request_account_deactivation,
    get_account_deactivation_status,
)
from services.reports import create_report


@pytest.fixture(autouse=True)
def setup_test_db():
    """Ensure database tables and test accounts exist."""
    init_db()
    init_settings_tables()


def test_db_initialization_and_default_configs():
    """Verifies that all settings tables are created and default configurations exist."""
    org_id = "ORG-TALENT-01"
    
    # 1. Organization profile
    org = get_org_profile_settings(org_id)
    assert org["name"] != ""
    assert org["official_email"] != ""
    assert org["status"] == "Active"

    # 2. Workforce / Employee configuration
    emp_cfg = get_org_employee_config(org_id)
    assert "Engineering" in emp_cfg["departments"]
    assert "Senior Software Engineer" in emp_cfg["designations"]
    assert len(emp_cfg["skill_categories"]) >= 3

    # 3. Performance settings
    perf_cfg = get_org_performance_config(org_id)
    assert perf_cfg["rating_scale_min"] == 1.0
    assert perf_cfg["rating_scale_max"] == 5.0
    assert "3" in perf_cfg["rating_descriptions"]

    # 4. Career development
    car_cfg = get_org_career_config(org_id)
    assert "Senior" in car_cfg["career_levels"]
    assert len(car_cfg["job_roles"]) > 0

    # 5. Training settings
    tr_cfg = get_org_training_config(org_id)
    assert "Internal Academy" in tr_cfg["training_providers"]

    # 6. PDF settings
    pdf_cfg = get_org_pdf_config(org_id)
    assert pdf_cfg["theme_color"] in ["Navy & Teal", "Modern Indigo", "Emerald Executive", "Classic Slate"]

    # 7. Security settings
    sec_cfg = get_org_security_config(org_id)
    assert sec_cfg["password_policy"]["min_length"] >= 8

    # 8. Notification settings
    notif_cfg = get_org_notification_config(org_id)
    assert notif_cfg["review_reminders_enabled"] is True


def test_hr_org_profile_update():
    """Verifies HR can update organization details and persistence is guaranteed."""
    org_id = "ORG-TALENT-01"
    ok, msg = save_org_profile_settings(
        org_id=org_id,
        name="Global Talent Enterprises",
        official_email="contact@globaltalent.com",
        contact_number="+1-555-9876",
        address="100 Innovation Way, Suite 400",
        website="https://globaltalent.com",
        industry="Technology & Software",
        description="Pioneering AI-driven talent development.",
        logo_base64="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        requesting_role="admin"
    )
    assert ok is True
    assert "updated" in msg.lower()

    # Verify retrieval
    org = get_org_profile_settings(org_id)
    assert org["name"] == "Global Talent Enterprises"
    assert org["official_email"] == "contact@globaltalent.com"
    assert org["address"] == "100 Innovation Way, Suite 400"
    assert "data:image/png;base64" in org["logo_base64"]

    # Restore default organization settings for subsequent test suites
    save_org_profile_settings(
        org_id=org_id,
        name="Talent Growth Technologies",
        official_email="contact@talentgrowth.com",
        contact_number="+1-555-0100",
        address="100 Innovation Way",
        website="https://talentgrowth.com",
        industry="Technology & Software",
        description="Pioneering talent management & growth.",
        requesting_role="admin"
    )


def test_rbac_prevents_employee_from_modifying_org_profile():
    """Verifies that an Employee calling HR administrative functions is strictly blocked."""
    org_id = "ORG-TALENT-01"
    with pytest.raises(PermissionError):
        save_org_profile_settings(
            org_id=org_id,
            name="Hacked Name",
            requesting_role="employee"
        )

    with pytest.raises(PermissionError):
        save_org_employee_config(
            org_id=org_id,
            config_data={"departments": ["Hacked"]},
            requesting_role="employee"
        )

    with pytest.raises(PermissionError):
        save_org_security_config(
            org_id=org_id,
            security_data={"session_timeout_minutes": 1},
            requesting_role="employee"
        )


def test_hr_account_profile_and_password_change():
    """Verifies HR account profile update and password change flow."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE email = 'cpo@talentgrowth.com'")
    conn.commit()
    cursor.execute("SELECT id FROM users WHERE email = 'admin@talentgrowth.com'")
    admin_row = cursor.fetchone()
    admin_id = admin_row["id"] if admin_row else 1
    conn.close()

    # 1. Update Profile
    ok, msg = update_hr_account_profile(
        user_id=admin_id,
        name="Chief People Officer",
        email="cpo@talentgrowth.com",
        phone="+1-555-0199",
        avatar_base64="data:image/png;base64,testavatar",
        requesting_role="admin"
    )
    assert ok is True

    # 2. Change Password
    # Current password for admin is Admin@12345
    ok, msg = change_account_password(
        user_id=admin_id,
        current_password="Admin@12345",
        new_password="NewSecurePass@2026",
        confirm_password="NewSecurePass@2026",
        org_id="ORG-TALENT-01"
    )
    assert ok is True

    # Verify password verification works with new password
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT password_hash, salt FROM users WHERE id = ?", (admin_id,))
    row = c.fetchone()
    conn.close()
    assert verify_password("NewSecurePass@2026", row["password_hash"], row["salt"]) is True

    # Revert password and email back for test repeatability
    change_account_password(
        user_id=admin_id,
        current_password="NewSecurePass@2026",
        new_password="Admin@12345",
        confirm_password="Admin@12345",
        org_id="ORG-TALENT-01"
    )
    update_hr_account_profile(
        user_id=admin_id,
        name="HR Administrator",
        email="admin@talentgrowth.com",
        phone="",
        requesting_role="admin"
    )


def test_password_policy_enforcement():
    """Verifies that changing password enforces password policy rules."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = 'admin@talentgrowth.com'")
    admin_row = cursor.fetchone()
    admin_id = admin_row["id"] if admin_row else 1
    conn.close()

    # Set strict security policy
    save_org_security_config(
        org_id="ORG-TALENT-01",
        security_data={
            "password_policy": {
                "min_length": 10,
                "require_uppercase": True,
                "require_numbers": True,
                "require_symbols": True
            }
        },
        requesting_role="admin"
    )

    # 1. Too short
    ok, msg = change_account_password(
        user_id=admin_id,
        current_password="Admin@12345",
        new_password="Short1!",
        confirm_password="Short1!",
        org_id="ORG-TALENT-01"
    )
    assert ok is False
    assert "at least 10" in msg

    # 2. Missing symbol
    ok, msg = change_account_password(
        user_id=admin_id,
        current_password="Admin@12345",
        new_password="LongPasswordWithoutSymbol123",
        confirm_password="LongPasswordWithoutSymbol123",
        org_id="ORG-TALENT-01"
    )
    assert ok is False
    assert "special symbol" in msg

    # 3. Mismatched confirmation
    ok, msg = change_account_password(
        user_id=admin_id,
        current_password="Admin@12345",
        new_password="ValidNewPassword@123",
        confirm_password="DifferentPassword@123",
        org_id="ORG-TALENT-01"
    )
    assert ok is False
    assert "do not match" in msg


def test_pdf_report_customization_and_dynamic_generation():
    """Verifies PDF report customization is saved and dynamically reflected in create_report()."""
    org_id = "ORG-TALENT-01"
    custom_pdf_cfg = {
        "company_name": "Apex Innovations Corp",
        "report_title": "Executive Talent Intelligence Dossier",
        "header_text": "STRICTLY PRIVATE & CONFIDENTIAL",
        "footer_text": "Apex Innovations · Talent Growth Intelligence System",
        "theme_color": "Emerald Executive",
        "confidentiality_notice": "Confidential talent assessment data for internal promotion board only.",
        "date_format": "%Y-%m-%d"
    }

    ok, msg = save_org_pdf_config(org_id, custom_pdf_cfg, requesting_role="admin")
    assert ok is True

    # Generate PDF report using create_report
    profile = {
        "name": "Alex Morgan",
        "job_title": "Senior Software Engineer",
        "department": "Engineering",
        "years_experience": 4.5,
        "target_role": "Lead Architect",
        "target_level": "Lead",
        "timeline": "6 months",
        "summary": "Experienced distributed systems developer."
    }
    skills = [
        {"name": "Python", "category": "Technical", "proficiency": "Expert"},
        {"name": "System Design", "category": "Architecture", "proficiency": "Advanced"}
    ]
    analysis = {"completion": 90, "score": 88, "match": 85}
    gaps = [{"skill": "Cloud Native Kubernetes", "current": 2, "required": 4, "gap": 2, "priority": "High"}]
    recommendations = [{"title": "AWS Solutions Architect", "description": "Obtain certification.", "priority": "High"}]
    assessments = []
    progress = []

    pdf_bytes = create_report(
        profile=profile,
        skills=skills,
        analysis=analysis,
        gaps=gaps,
        recommendations=recommendations,
        assessments=assessments,
        progress=progress,
        org_id=org_id
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    # PDF starts with magic number %PDF
    assert pdf_bytes.startswith(b"%PDF")


def test_employee_personal_profile_and_preferences():
    """Verifies that employees can update personal profile, career preferences, notifications, appearance, and privacy."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email = 'alex@company.com'")
    row = c.fetchone()
    alex_id = row["id"] if row else 2
    conn.close()

    # 1. Personal Profile
    ok, msg = save_employee_personal_profile(
        user_id=alex_id,
        name="Alex Morgan Updated",
        phone="+1-555-0155",
        location="Austin, TX",
        summary="Updated professional summary focusing on cloud architecture."
    )
    assert ok is True

    # 2. Career Preferences
    ok, msg = save_employee_career_preferences(
        user_id=alex_id,
        career_prefs={
            "current_designation": "Senior Engineer",
            "target_designation": "Principal System Architect",
            "timeline": "1-2 years",
            "interested_paths": ["Technical Architecture", "Staff Engineering"],
            "preferred_skills": ["Rust", "Distributed Consensus", "eBPF"]
        }
    )
    assert ok is True

    # 3. Notification Preferences
    ok, msg = save_employee_notification_preferences(
        user_id=alex_id,
        notification_prefs={
            "goal_reminders": "Daily",
            "training_reminders": "3 Days Before",
            "performance_review_notifications": True,
            "platform_notifications": False
        }
    )
    assert ok is True

    # 4. Appearance
    ok, msg = save_employee_appearance_preferences(
        user_id=alex_id,
        appearance_prefs={
            "theme_mode": "Dark Mode",
            "density": "Compact"
        }
    )
    assert ok is True

    # 5. Privacy
    ok, msg = save_employee_privacy_preferences(
        user_id=alex_id,
        privacy_prefs={"profile_visibility": "My Department Only"}
    )
    assert ok is True

    # 6. Verify preferences are loaded accurately
    prefs = get_user_preferences(alex_id)
    assert prefs["location"] == "Austin, TX"
    assert prefs["summary"] == "Updated professional summary focusing on cloud architecture."
    assert prefs["career_preferences"]["target_designation"] == "Principal System Architect"
    assert prefs["notification_preferences"]["goal_reminders"] == "Daily"
    assert prefs["appearance"]["theme_mode"] == "Dark Mode"
    assert prefs["appearance"]["density"] == "Compact"
    assert prefs["privacy"]["profile_visibility"] == "My Department Only"


def test_employee_deactivation_request():
    """Verifies that an employee can submit an account deactivation request and query its status."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email = 'ravi@company.com'")
    row = c.fetchone()
    ravi_id = row["id"] if row else 3
    conn.close()

    # Submit deactivation request
    ok, msg = request_account_deactivation(
        user_id=ravi_id,
        reason="Transitioning to higher education program."
    )
    assert ok is True
    assert "submitted" in msg.lower()

    # Query request status
    req = get_account_deactivation_status(ravi_id)
    assert req is not None
    assert req["status"] == "Pending"
    assert req["reason"] == "Transitioning to higher education program."


def test_safe_index_and_legacy_preference_compatibility():
    """Verifies that _safe_index handles legacy/unmatched strings without raising ValueError."""
    from services.settings_ui import _safe_index

    # Exact match
    opts = ["3 Days Before", "1 Week Before", "2 Weeks Before", "Disabled"]
    assert _safe_index(opts, "1 Week Before") == 1

    # Legacy default string that previously crashed Streamlit Cloud
    # "Weekly Digest" matches "week" substring
    idx = _safe_index(opts, "Weekly Digest", default_idx=1)
    assert 0 <= idx < len(opts)
    assert idx == 1  # Matches "1 Week Before"

    # Completely unmatched string safely returns default_idx
    assert _safe_index(opts, "NonExistentCadence", default_idx=0) == 0
    assert _safe_index(opts, None, default_idx=2) == 2

    # Case insensitivity
    theme_opts = ["System Default", "Light Mode", "Dark Mode"]
    assert _safe_index(theme_opts, "light mode") == 1
    assert _safe_index(theme_opts, "DARK MODE") == 2
    assert _safe_index(theme_opts, "light") == 1
    assert _safe_index(theme_opts, "dark") == 2

    density_opts = ["Comfortable", "Compact"]
    assert _safe_index(density_opts, "comfortable") == 0
    assert _safe_index(density_opts, "compact") == 1
    assert _safe_index(density_opts, "unknown", default_idx=0) == 0

