"""
Settings Module for Talent Growth Platform
Provides complete backend persistence, validation, and role-based access control
for HR Administrator Settings and Employee Personal Settings.
"""

from __future__ import annotations
import json
import re
import base64
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from services.core import (
    get_connection,
    get_db_path,
    hash_password,
    verify_password,
    _safe_add_column
)
from services.db import is_mysql_mode, MYSQL_SETTINGS_SCHEMA_STATEMENTS

# ------------------------------------------------------------------------------
# DATABASE SCHEMA INITIALIZATION FOR SETTINGS
# ------------------------------------------------------------------------------
def init_settings_tables() -> None:
    """Initializes all settings tables and safe column migrations in MySQL."""
    try:
        conn = get_connection()
    except Exception:
        return
    try:
        with conn:
            cursor = conn.cursor()

            for stmt in MYSQL_SETTINGS_SCHEMA_STATEMENTS:
                try:
                    cursor.execute(stmt)
                except Exception:
                    pass

            # Safe Column Additions to existing tables
            _safe_add_column(cursor, "organizations", "logo_base64", "TEXT DEFAULT ''")
            _safe_add_column(cursor, "organizations", "address", "TEXT DEFAULT ''")
            _safe_add_column(cursor, "organizations", "website", "TEXT DEFAULT ''")
            _safe_add_column(cursor, "organizations", "industry", "TEXT DEFAULT 'Technology'")
            _safe_add_column(cursor, "organizations", "description", "TEXT DEFAULT ''")

            _safe_add_column(cursor, "users", "avatar_base64", "TEXT DEFAULT ''")
            _safe_add_column(cursor, "users", "phone", "TEXT DEFAULT ''")
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


# Safe initialization on module load (does not fail if database is offline or unconfigured)
try:
    init_settings_tables()
except Exception:
    pass


# ------------------------------------------------------------------------------
# DEFAULT ENTERPRISE CONFIGURATION DATASETS
# ------------------------------------------------------------------------------
DEFAULT_DEPARTMENTS = [
    "Engineering", "Data & AI", "Product Management", "UX & Design",
    "Human Resources", "Marketing", "Sales", "Finance & Accounting",
    "Operations", "Legal & Compliance"
]

DEFAULT_DESIGNATIONS = [
    "Software Engineer", "Senior Software Engineer", "Tech Lead", "Principal Engineer",
    "Engineering Manager", "Data Analyst", "Data Scientist", "DevOps Engineer",
    "Cloud Architect", "Product Manager", "HR Generalist", "QA Automation Engineer"
]

DEFAULT_EMPLOYEE_CATEGORIES = [
    "Full-Time Regular", "Part-Time", "Contract / Consultant",
    "Intern / Trainee", "Executive Leadership"
]

DEFAULT_EMPLOYMENT_STATUSES = [
    "Active", "On Leave", "Probationary", "Notice Period", "Terminated", "Suspended"
]

DEFAULT_SKILL_CATEGORIES = [
    "Core Software Engineering", "Cloud & Distributed Systems",
    "Data Science & Machine Learning", "DevOps & SRE",
    "Product Strategy & Management", "UI/UX Design",
    "Leadership & People Management", "Business Communication"
]

DEFAULT_RATING_DESCRIPTIONS = {
    "1": "Unsatisfactory — Fails to meet primary role deliverables; remediation required",
    "2": "Needs Improvement — Inconsistently meets expectations; developmental support recommended",
    "3": "Meets Expectations — Consistently fulfills all standard deliverables with reliability",
    "4": "Exceeds Expectations — Regularly surpasses benchmark deliverables with high craftsmanship",
    "5": "Outstanding — Exceptional executive benchmark performer, multiplier, and strategic innovator"
}

DEFAULT_EVALUATION_CRITERIA = [
    "Technical Delivery & Craftsmanship",
    "Code Quality & Architecture Robustness",
    "Product & Business Value Impact",
    "Cross-Functional Collaboration",
    "Problem Solving & Innovation",
    "Mentorship & Team Elevation"
]

DEFAULT_REVIEW_PERIODS = [
    "Annual Performance Cycle",
    "Semi-Annual Review",
    "Quarterly Milestone Check",
    "Continuous Monthly Feedback"
]

DEFAULT_PERFORMANCE_CATEGORIES = [
    "Core Job Deliverables",
    "Competency & Skill Growth",
    "Company Values & Culture",
    "Strategic Innovation & Leadership"
]

DEFAULT_CAREER_LEVELS = [
    "Junior",
    "Mid-Level",
    "Senior",
    "Lead / Staff",
    "Principal",
    "Director / Executive"
]

DEFAULT_JOB_ROLES = [
    "Software Engineer", "Senior Software Engineer", "Tech Lead",
    "Data Scientist", "Cloud Architect", "Product Manager",
    "DevOps Engineer", "AI/ML Engineer"
]

DEFAULT_ROLE_SKILL_REQUIREMENTS = {
    "Software Engineer": {"Python": 3, "SQL": 3, "Git": 3, "API Design": 3},
    "Senior Software Engineer": {"Python": 4, "System Design": 4, "Cloud Architecture": 3, "Mentorship": 4},
    "Data Scientist": {"Python": 4, "Machine Learning": 4, "SQL": 4, "Statistics": 4},
    "Cloud Architect": {"Cloud Architecture": 5, "Kubernetes": 4, "DevOps": 4, "Security": 4},
    "Product Manager": {"Product Strategy": 4, "Agile": 4, "User Research": 3, "Data Analysis": 3}
}

DEFAULT_PROGRESSION_PATHS = {
    "Software Engineer": ["Senior Software Engineer", "Tech Lead", "Principal Engineer"],
    "Data Scientist": ["Senior Data Scientist", "Lead AI Scientist", "Chief Data Officer"],
    "DevOps Engineer": ["Senior DevOps Engineer", "Cloud Architect", "Head of Infrastructure"]
}

DEFAULT_TIMELINES = [
    "6 Months (Accelerated Sprint)",
    "12 Months (Standard Cycle)",
    "18 Months (Expanded Mastery)",
    "24 Months (Leadership Transition)"
]

DEFAULT_TRAINING_CATEGORIES = [
    "Technical Skills & Frameworks",
    "Architecture & System Design",
    "AI & Data Engineering",
    "Cloud & Security Compliance",
    "Leadership & Management Development",
    "Agile & Delivery Excellence",
    "Executive Communication"
]

DEFAULT_TRAINING_PROVIDERS = [
    "Internal Academy",
    "Internal Corporate Academy",
    "Coursera Enterprise",
    "AWS Training & Certification",
    "Pluralsight",
    "Google Cloud Skills Boost",
    "LinkedIn Learning"
]

DEFAULT_CERTIFICATION_TYPES = [
    "Professional Certification",
    "Specialty Skill Badge",
    "Accredited Foundational Degree",
    "Annual Regulatory Compliance",
    "Internal Technical Mastery Award"
]

DEFAULT_COMPLETION_CRITERIA = [
    "Score >= 80% on Final Assessment",
    "Practical Capstone Project Review",
    "100% Course Modules & Labs",
    "Instructor / Lead Sign-Off",
    "Peer-Reviewed Architecture Artifact"
]


# ------------------------------------------------------------------------------

def _check_admin_auth(requesting_user: Any = None, requesting_role: Optional[str] = None):
    """Enforces that the requesting user or role is an HR Administrator ('admin')."""
    role = None
    if requesting_role:
        role = requesting_role
    elif isinstance(requesting_user, dict):
        role = requesting_user.get("role")
    elif isinstance(requesting_user, str):
        role = requesting_user
    if role != "admin":
        raise PermissionError("Access Denied: Only HR Administrators are authorized to perform this operation.")

# 1. ORGANIZATION PROFILE SETTINGS (HR ONLY)
# ------------------------------------------------------------------------------
def get_org_profile_settings(org_id: str) -> Dict[str, Any]:
    """Retrieves organization profile settings or returns enterprise defaults."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM org_settings WHERE org_id = ?", (org_id,))
    row = cursor.fetchone()

    cursor.execute("SELECT * FROM organizations WHERE org_id = ?", (org_id,))
    org_row = cursor.fetchone()
    org_dict = dict(org_row) if org_row else {}

    res = dict(row) if row else {}
    name = res.get("org_name") or org_dict.get("name") or "Talent Growth Technologies"
    email = res.get("official_email") or org_dict.get("official_email") or "hr@talentgrowth.com"
    phone = res.get("contact_number") or org_dict.get("contact_number") or "+1 (555) 019-2834"
    addr = res.get("address") or org_dict.get("address") or "100 Innovation Way, Suite 400, San Francisco, CA 94105"
    web = res.get("website") or org_dict.get("website") or "https://www.talentgrowth.com"
    ind = res.get("industry") or org_dict.get("industry") or "Technology & Enterprise Software"
    desc = res.get("description") or org_dict.get("description") or "Enterprise talent intelligence platform."
    logo = res.get("logo_base64") or org_dict.get("logo_base64") or ""
    status = org_dict.get("status") or "Active"

    return {
        "org_id": org_id,
        "name": name,
        "org_name": name,
        "official_email": email,
        "contact_number": phone,
        "address": addr,
        "website": web,
        "industry": ind,
        "description": desc,
        "logo_base64": logo,
        "status": status,
        "updated_at": res.get("updated_at") or datetime.now().isoformat()
    }


def save_org_profile_settings(
    org_id: str,
    data: Optional[Dict[str, Any]] = None,
    requesting_user: Any = None,
    requesting_role: Optional[str] = None,
    **kwargs
) -> Tuple[bool, str]:
    """Saves organization profile settings with backend HR RBAC enforcement."""
    _check_admin_auth(requesting_user, requesting_role)
    payload = {}
    if isinstance(data, dict):
        payload.update(data)
    payload.update(kwargs)

    org_name = (payload.get("name") or payload.get("org_name") or "").strip()
    if not org_name:
        return False, "Organization Name cannot be empty."

    email = (payload.get("official_email") or "").strip()
    if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return False, "Please provide a valid official organization email address."

    logo_b64 = payload.get("logo_base64", "")
    phone = (payload.get("contact_number") or "").strip()
    addr = (payload.get("address") or "").strip()
    web = (payload.get("website") or "").strip()
    ind = (payload.get("industry") or "Technology").strip()
    desc = (payload.get("description") or "").strip()

    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO org_settings (
                org_id, org_name, logo_base64, official_email, contact_number,
                address, website, industry, description, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(org_id) DO UPDATE SET
                org_name = excluded.org_name,
                logo_base64 = excluded.logo_base64,
                official_email = excluded.official_email,
                contact_number = excluded.contact_number,
                address = excluded.address,
                website = excluded.website,
                industry = excluded.industry,
                description = excluded.description,
                updated_at = CURRENT_TIMESTAMP
        """, (
            org_id,
            org_name,
            logo_b64,
            email,
            phone,
            addr,
            web,
            ind,
            desc
        ))

        # Also sync to organizations table
        cursor.execute("""
            UPDATE organizations SET
                name = ?,
                official_email = ?,
                contact_number = ?,
                logo_base64 = ?,
                address = ?,
                website = ?,
                industry = ?,
                description = ?
            WHERE org_id = ?
        """, (
            org_name,
            email,
            phone,
            logo_b64,
            addr,
            web,
            ind,
            desc,
            org_id
        ))

    return True, "Organization profile settings successfully updated and saved."


# ------------------------------------------------------------------------------
# 2. HR ACCOUNT & SECURITY SETTINGS
# ------------------------------------------------------------------------------
def update_hr_account_profile(
    user_id: int,
    name: str,
    email: str,
    phone: str = "",
    avatar_base64: str = "",
    requesting_user: Any = None,
    requesting_role: Optional[str] = None,
    **kwargs
) -> Tuple[bool, str]:
    """Updates HR Admin account details (name, email, phone, avatar) with RBAC validation."""
    _check_admin_auth(requesting_user, requesting_role)

    clean_name = name.strip()
    if not clean_name:
        return False, "Administrator Name cannot be empty."

    clean_email = email.strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean_email):
        return False, "Please provide a valid email address."

    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (clean_email, user_id))
        if cursor.fetchone():
            return False, "An account with this email address already exists."

        cursor.execute("""
            UPDATE users SET
                name = ?,
                email = ?,
                phone = ?,
                avatar_base64 = ?
            WHERE id = ?
        """, (clean_name, clean_email, phone.strip(), avatar_base64, user_id))

        cursor.execute("""
            INSERT INTO user_preferences (user_id, profile_photo, phone, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                profile_photo = excluded.profile_photo,
                phone = excluded.phone,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, avatar_base64, phone.strip()))

    return True, "HR Account profile successfully updated."


def change_account_password(
    user_id: int,
    current_password: str,
    new_password: str,
    confirm_password: str,
    org_id: Optional[str] = None
) -> Tuple[bool, str]:
    """Securely verifies current password and applies new password with organizational policy enforcement."""
    if not current_password:
        return False, "Please enter your current password."

    if not new_password:
        return False, "New password cannot be empty."

    if new_password != confirm_password:
        return False, "New password and confirmation password do not match."

    # Validate against security requirements
    sec_cfg = get_org_security_config(org_id or "default")
    min_len = sec_cfg.get("min_password_length", 8)
    if len(new_password) < min_len:
        return False, f"Password must be at least {min_len} characters long."

    if sec_cfg.get("require_uppercase", 1) and not any(c.isupper() for c in new_password):
        return False, "Password must include at least one uppercase letter (A-Z)."

    if sec_cfg.get("require_number", 1) and not any(c.isdigit() for c in new_password):
        return False, "Password must include at least one numeric digit (0-9)."

    if sec_cfg.get("require_special_char", 1) and not any(c in "!@#$%^&*()-_=+[]{}|;:,.<>/?`~" for c in new_password):
        return False, "Password must include at least one special symbol / character (!@#$%^&*...)."

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, salt FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        return False, "User account not found."

    stored_hash = row["password_hash"]
    salt = row["salt"]

    if not verify_password(current_password, stored_hash, salt):
        return False, "Current password verification failed. Please check your credentials."

    new_hash, new_salt = hash_password(new_password)
    with conn:
        conn.execute("""
            UPDATE users SET
                password_hash = ?,
                salt = ?
            WHERE id = ?
        """, (new_hash, new_salt, user_id))

    return True, "Password successfully changed and verified."


# ------------------------------------------------------------------------------
# 3. EMPLOYEE CONFIGURATION (HR ONLY)
# ------------------------------------------------------------------------------
def get_org_employee_config(org_id: str) -> Dict[str, Any]:
    """Retrieves organizational employee configuration (departments, designations, categories, statuses, skill categories)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM org_employee_config WHERE org_id = ?", (org_id,))
    row = cursor.fetchone()
    if row:
        d = dict(row)
        return {
            "org_id": org_id,
            "departments": json.loads(d.get("departments") or "[]") or DEFAULT_DEPARTMENTS,
            "designations": json.loads(d.get("designations") or "[]") or DEFAULT_DESIGNATIONS,
            "employee_categories": json.loads(d.get("employee_categories") or "[]") or DEFAULT_EMPLOYEE_CATEGORIES,
            "employment_statuses": json.loads(d.get("employment_statuses") or "[]") or DEFAULT_EMPLOYMENT_STATUSES,
            "skill_categories": json.loads(d.get("skill_categories") or "[]") or DEFAULT_SKILL_CATEGORIES,
            "updated_at": d.get("updated_at")
        }

    return {
        "org_id": org_id,
        "departments": DEFAULT_DEPARTMENTS,
        "designations": DEFAULT_DESIGNATIONS,
        "employee_categories": DEFAULT_EMPLOYEE_CATEGORIES,
        "employment_statuses": DEFAULT_EMPLOYMENT_STATUSES,
        "skill_categories": DEFAULT_SKILL_CATEGORIES,
        "updated_at": datetime.now().isoformat()
    }


def save_org_employee_config(
    org_id: str,
    config: Optional[Dict[str, Any]] = None,
    config_data: Optional[Dict[str, Any]] = None,
    requesting_user: Any = None,
    requesting_role: Optional[str] = None,
    **kwargs
) -> Tuple[bool, str]:
    """Saves employee configuration with HR RBAC validation."""
    _check_admin_auth(requesting_user, requesting_role)
    cfg = config or config_data or kwargs or {}

    depts = [d.strip() for d in cfg.get("departments", []) if d.strip()]
    desigs = [d.strip() for d in cfg.get("designations", []) if d.strip()]
    cats = [c.strip() for c in cfg.get("employee_categories", []) if c.strip()]
    statuses = [s.strip() for s in cfg.get("employment_statuses", []) if s.strip()]
    skill_cats = [sc.strip() for sc in cfg.get("skill_categories", []) if sc.strip()]

    if not depts:
        return False, "At least one department must be configured."
    if not desigs:
        return False, "At least one designation must be configured."

    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO org_employee_config (
                org_id, departments, designations, employee_categories,
                employment_statuses, skill_categories, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(org_id) DO UPDATE SET
                departments = excluded.departments,
                designations = excluded.designations,
                employee_categories = excluded.employee_categories,
                employment_statuses = excluded.employment_statuses,
                skill_categories = excluded.skill_categories,
                updated_at = CURRENT_TIMESTAMP
        """, (
            org_id,
            json.dumps(depts),
            json.dumps(desigs),
            json.dumps(cats),
            json.dumps(statuses),
            json.dumps(skill_cats)
        ))

    return True, "Employee configuration successfully updated."


# ------------------------------------------------------------------------------
# 4. PERFORMANCE SETTINGS (HR ONLY)
# ------------------------------------------------------------------------------
def get_org_performance_config(org_id: str) -> Dict[str, Any]:
    """Retrieves performance configuration (scale, rating descriptions, criteria, periods, categories)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM org_performance_config WHERE org_id = ?", (org_id,))
    row = cursor.fetchone()
    if row:
        d = dict(row)
        return {
            "org_id": org_id,
            "rating_scale_min": d.get("rating_scale_min", 1),
            "rating_scale_max": d.get("rating_scale_max", 5),
            "rating_descriptions": json.loads(d.get("rating_descriptions") or "{}") or DEFAULT_RATING_DESCRIPTIONS,
            "evaluation_criteria": json.loads(d.get("evaluation_criteria") or "[]") or DEFAULT_EVALUATION_CRITERIA,
            "review_periods": json.loads(d.get("review_periods") or "[]") or DEFAULT_REVIEW_PERIODS,
            "performance_categories": json.loads(d.get("performance_categories") or "[]") or DEFAULT_PERFORMANCE_CATEGORIES,
            "updated_at": d.get("updated_at")
        }

    return {
        "org_id": org_id,
        "rating_scale_min": 1,
        "rating_scale_max": 5,
        "rating_descriptions": DEFAULT_RATING_DESCRIPTIONS,
        "evaluation_criteria": DEFAULT_EVALUATION_CRITERIA,
        "review_periods": DEFAULT_REVIEW_PERIODS,
        "performance_categories": DEFAULT_PERFORMANCE_CATEGORIES,
        "updated_at": datetime.now().isoformat()
    }


def save_org_performance_config(
    org_id: str,
    config: Optional[Dict[str, Any]] = None,
    config_data: Optional[Dict[str, Any]] = None,
    requesting_user: Any = None,
    requesting_role: Optional[str] = None,
    **kwargs
) -> Tuple[bool, str]:
    """Saves performance evaluation settings with HR RBAC validation."""
    _check_admin_auth(requesting_user, requesting_role)
    cfg = config or config_data or kwargs or {}

    min_scale = float(cfg.get("rating_scale_min", 1.0))
    max_scale = float(cfg.get("rating_scale_max", 5.0))
    criteria = [c.strip() for c in cfg.get("evaluation_criteria", []) if c.strip()]
    periods = [p.strip() for p in cfg.get("review_periods", []) if p.strip()]
    cats = [c.strip() for c in cfg.get("performance_categories", []) if c.strip()]
    descs = cfg.get("rating_descriptions", {})

    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO org_performance_config (
                org_id, rating_scale_min, rating_scale_max, rating_descriptions,
                evaluation_criteria, review_periods, performance_categories, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(org_id) DO UPDATE SET
                rating_scale_min = excluded.rating_scale_min,
                rating_scale_max = excluded.rating_scale_max,
                rating_descriptions = excluded.rating_descriptions,
                evaluation_criteria = excluded.evaluation_criteria,
                review_periods = excluded.review_periods,
                performance_categories = excluded.performance_categories,
                updated_at = CURRENT_TIMESTAMP
        """, (
            org_id,
            min_scale,
            max_scale,
            json.dumps(descs),
            json.dumps(criteria),
            json.dumps(periods),
            json.dumps(cats)
        ))

    return True, "Performance evaluation settings successfully updated."


# ------------------------------------------------------------------------------
# 5. CAREER DEVELOPMENT SETTINGS (HR ONLY)
# ------------------------------------------------------------------------------
def get_org_career_config(org_id: str) -> Dict[str, Any]:
    """Retrieves organizational career development settings."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM org_career_config WHERE org_id = ?", (org_id,))
    row = cursor.fetchone()
    if row:
        d = dict(row)
        return {
            "org_id": org_id,
            "career_levels": json.loads(d.get("career_levels") or "[]") or DEFAULT_CAREER_LEVELS,
            "job_roles": json.loads(d.get("job_roles") or "[]") or DEFAULT_JOB_ROLES,
            "role_skill_requirements": json.loads(d.get("role_skill_requirements") or "{}") or DEFAULT_ROLE_SKILL_REQUIREMENTS,
            "progression_paths": json.loads(d.get("progression_paths") or "{}") or DEFAULT_PROGRESSION_PATHS,
            "default_timelines": json.loads(d.get("default_timelines") or "[]") or DEFAULT_TIMELINES,
            "updated_at": d.get("updated_at")
        }

    return {
        "org_id": org_id,
        "career_levels": DEFAULT_CAREER_LEVELS,
        "job_roles": DEFAULT_JOB_ROLES,
        "role_skill_requirements": DEFAULT_ROLE_SKILL_REQUIREMENTS,
        "progression_paths": DEFAULT_PROGRESSION_PATHS,
        "default_timelines": DEFAULT_TIMELINES,
        "updated_at": datetime.now().isoformat()
    }


def save_org_career_config(
    org_id: str,
    config: Optional[Dict[str, Any]] = None,
    config_data: Optional[Dict[str, Any]] = None,
    requesting_user: Any = None,
    requesting_role: Optional[str] = None,
    **kwargs
) -> Tuple[bool, str]:
    """Saves career progression settings with HR RBAC validation."""
    _check_admin_auth(requesting_user, requesting_role)
    cfg = config or config_data or kwargs or {}

    levels = [l.strip() for l in cfg.get("career_levels", []) if l.strip()]
    roles = [r.strip() for r in cfg.get("job_roles", []) if r.strip()]
    timelines = [t.strip() for t in cfg.get("default_timelines", []) if t.strip()]

    if not levels:
        return False, "At least one career level must be configured."
    if not roles:
        return False, "At least one job role must be configured."

    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO org_career_config (
                org_id, career_levels, job_roles, role_skill_requirements,
                progression_paths, default_timelines, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(org_id) DO UPDATE SET
                career_levels = excluded.career_levels,
                job_roles = excluded.job_roles,
                role_skill_requirements = excluded.role_skill_requirements,
                progression_paths = excluded.progression_paths,
                default_timelines = excluded.default_timelines,
                updated_at = CURRENT_TIMESTAMP
        """, (
            org_id,
            json.dumps(levels),
            json.dumps(roles),
            json.dumps(config.get("role_skill_requirements", {})),
            json.dumps(config.get("progression_paths", {})),
            json.dumps(timelines)
        ))

    return True, "Career development settings successfully updated."


# ------------------------------------------------------------------------------
# 6. TRAINING SETTINGS (HR ONLY)
# ------------------------------------------------------------------------------
def get_org_training_config(org_id: str) -> Dict[str, Any]:
    """Retrieves organizational training settings."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM org_training_config WHERE org_id = ?", (org_id,))
    row = cursor.fetchone()
    if row:
        d = dict(row)
        return {
            "org_id": org_id,
            "training_categories": json.loads(d.get("training_categories") or "[]") or DEFAULT_TRAINING_CATEGORIES,
            "training_providers": json.loads(d.get("training_providers") or "[]") or DEFAULT_TRAINING_PROVIDERS,
            "certification_types": json.loads(d.get("certification_types") or "[]") or DEFAULT_CERTIFICATION_TYPES,
            "completion_criteria": json.loads(d.get("completion_criteria") or "[]") or DEFAULT_COMPLETION_CRITERIA,
            "updated_at": d.get("updated_at")
        }

    return {
        "org_id": org_id,
        "training_categories": DEFAULT_TRAINING_CATEGORIES,
        "training_providers": DEFAULT_TRAINING_PROVIDERS,
        "certification_types": DEFAULT_CERTIFICATION_TYPES,
        "completion_criteria": DEFAULT_COMPLETION_CRITERIA,
        "updated_at": datetime.now().isoformat()
    }


def save_org_training_config(
    org_id: str,
    config: Optional[Dict[str, Any]] = None,
    config_data: Optional[Dict[str, Any]] = None,
    requesting_user: Any = None,
    requesting_role: Optional[str] = None,
    **kwargs
) -> Tuple[bool, str]:
    """Saves training and learning configuration with HR RBAC validation."""
    _check_admin_auth(requesting_user, requesting_role)
    cfg = config or config_data or kwargs or {}

    cats = [c.strip() for c in cfg.get("training_categories", []) if c.strip()]
    providers = [p.strip() for p in cfg.get("training_providers", []) if p.strip()]
    cert_types = [c.strip() for c in cfg.get("certification_types", []) if c.strip()]
    criteria = [c.strip() for c in cfg.get("completion_criteria", []) if c.strip()]

    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO org_training_config (
                org_id, training_categories, training_providers,
                certification_types, completion_criteria, updated_at
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(org_id) DO UPDATE SET
                training_categories = excluded.training_categories,
                training_providers = excluded.training_providers,
                certification_types = excluded.certification_types,
                completion_criteria = excluded.completion_criteria,
                updated_at = CURRENT_TIMESTAMP
        """, (
            org_id,
            json.dumps(cats),
            json.dumps(providers),
            json.dumps(cert_types),
            json.dumps(criteria)
        ))

    return True, "Training settings successfully updated."


# ------------------------------------------------------------------------------
# 7. PDF REPORT CUSTOMIZATION (HR ONLY)
# ------------------------------------------------------------------------------
def get_org_pdf_config(org_id: str) -> Dict[str, Any]:
    """Retrieves PDF report branding and formatting configuration."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM org_pdf_config WHERE org_id = ?", (org_id,))
    row = cursor.fetchone()
    if row:
        return dict(row)

    # Check org profile for default company name and logo
    org_prof = get_org_profile_settings(org_id)
    return {
        "org_id": org_id,
        "company_name": org_prof.get("org_name") or "Talent Growth Technologies",
        "logo_base64": org_prof.get("logo_base64") or "",
        "header_text": "Confidential — Enterprise Career & Competency Evaluation Dossier",
        "footer_text": "Talent Growth Platform · Confidential & Proprietary · Authorized Reviewers Only",
        "theme_color": "Navy & Teal",
        "report_title": "Employee Career & Competency Intelligence Report",
        "confidentiality_notice": "CONFIDENTIAL & PROPRIETARY — FOR AUTHORIZED TALENT EVALUATION ONLY",
        "date_format": "%B %d, %Y",
        "updated_at": datetime.now().isoformat()
    }


def save_org_pdf_config(
    org_id: str,
    config: Optional[Dict[str, Any]] = None,
    custom_pdf_cfg: Optional[Dict[str, Any]] = None,
    requesting_user: Any = None,
    requesting_role: Optional[str] = None,
    **kwargs
) -> Tuple[bool, str]:
    """Saves PDF customization settings with HR RBAC validation."""
    _check_admin_auth(requesting_user, requesting_role)
    cfg = config or custom_pdf_cfg or kwargs or {}

    company_name = (cfg.get("company_name") or "").strip()
    if not company_name:
        return False, "Company Name on PDF cannot be empty."

    report_title = (cfg.get("report_title") or "Executive Career & Competency Dossier").strip()
    if not report_title:
        return False, "Report Title cannot be empty."

    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO org_pdf_config (
                org_id, company_name, logo_base64, header_text, footer_text,
                theme_color, report_title, confidentiality_notice, date_format, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(org_id) DO UPDATE SET
                company_name = excluded.company_name,
                logo_base64 = excluded.logo_base64,
                header_text = excluded.header_text,
                footer_text = excluded.footer_text,
                theme_color = excluded.theme_color,
                report_title = excluded.report_title,
                confidentiality_notice = excluded.confidentiality_notice,
                date_format = excluded.date_format,
                updated_at = CURRENT_TIMESTAMP
        """, (
            org_id,
            company_name,
            cfg.get("logo_base64", ""),
            (cfg.get("header_text") or "").strip(),
            (cfg.get("footer_text") or "").strip(),
            cfg.get("theme_color", "Navy & Teal"),
            report_title,
            (cfg.get("confidentiality_notice") or "").strip(),
            cfg.get("date_format", "%B %d, %Y")
        ))

    return True, "PDF report branding and layout settings successfully updated."


# ------------------------------------------------------------------------------
# 8. SECURITY SETTINGS (HR ONLY)
# ------------------------------------------------------------------------------
def get_org_security_config(org_id: str) -> Dict[str, Any]:
    """Retrieves security policy configuration."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM org_security_config WHERE org_id = ?", (org_id,))
    row = cursor.fetchone()
    d = dict(row) if row else {
        "org_id": org_id,
        "min_password_length": 8,
        "require_uppercase": 1,
        "require_number": 1,
        "require_special_char": 1,
        "session_timeout_minutes": 60,
        "mfa_enforced": 0,
        "force_pwd_change": 0,
        "updated_at": datetime.now().isoformat()
    }
    min_len = int(d.get("min_password_length") or 8)
    req_u = bool(d.get("require_uppercase", 1))
    req_n = bool(d.get("require_number", 1))
    req_s = bool(d.get("require_special_char", 1))
    d["password_policy"] = {
        "min_length": min_len,
        "require_uppercase": req_u,
        "require_numbers": req_n,
        "require_symbols": req_s
    }
    return d


def save_org_security_config(
    org_id: str,
    config: Optional[Dict[str, Any]] = None,
    security_data: Optional[Dict[str, Any]] = None,
    requesting_user: Any = None,
    requesting_role: Optional[str] = None,
    **kwargs
) -> Tuple[bool, str]:
    """Saves organization security settings with HR RBAC validation."""
    _check_admin_auth(requesting_user, requesting_role)
    cfg = config or security_data or kwargs or {}

    policy = cfg.get("password_policy") or {}
    min_len = int(policy.get("min_length") or cfg.get("min_password_length") or 8)
    if min_len < 6 or min_len > 32:
        return False, "Minimum password length must be between 6 and 32 characters."

    timeout = int(cfg.get("session_timeout_minutes", 60))
    if timeout < 5 or timeout > 1440:
        return False, "Session timeout must be between 5 and 1440 minutes."

    req_upper = 1 if (policy.get("require_uppercase") if "require_uppercase" in policy else cfg.get("require_uppercase", 1)) else 0
    req_num = 1 if (policy.get("require_numbers") if "require_numbers" in policy else cfg.get("require_number", 1)) else 0
    req_sym = 1 if (policy.get("require_symbols") if "require_symbols" in policy else cfg.get("require_special_char", 1)) else 0

    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO org_security_config (
                org_id, min_password_length, require_uppercase, require_number,
                require_special_char, session_timeout_minutes, mfa_enforced,
                force_pwd_change, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(org_id) DO UPDATE SET
                min_password_length = excluded.min_password_length,
                require_uppercase = excluded.require_uppercase,
                require_number = excluded.require_number,
                require_special_char = excluded.require_special_char,
                session_timeout_minutes = excluded.session_timeout_minutes,
                mfa_enforced = excluded.mfa_enforced,
                force_pwd_change = excluded.force_pwd_change,
                updated_at = CURRENT_TIMESTAMP
        """, (
            org_id,
            min_len,
            req_upper,
            req_num,
            req_sym,
            timeout,
            1 if cfg.get("mfa_enforced") else 0,
            1 if cfg.get("force_pwd_change") else 0
        ))

    return True, "Security policy settings successfully saved."


# ------------------------------------------------------------------------------
# 9. NOTIFICATION SETTINGS (HR ONLY)
# ------------------------------------------------------------------------------
def get_org_notification_config(org_id: str) -> Dict[str, Any]:
    """Retrieves organizational notification settings."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM org_notification_config WHERE org_id = ?", (org_id,))
    row = cursor.fetchone()
    d = dict(row) if row else {
        "org_id": org_id,
        "review_reminders": 1,
        "training_reminders": 1,
        "goal_deadline_reminders": 1,
        "employee_registration_alerts": 1,
        "report_generation_alerts": 1,
        "reminder_frequency": "Weekly",
        "updated_at": datetime.now().isoformat()
    }
    d["review_reminders_enabled"] = bool(d.get("review_reminders", 1))
    d["training_reminders_enabled"] = bool(d.get("training_reminders", 1))
    d["goal_deadline_reminders_enabled"] = bool(d.get("goal_deadline_reminders", 1))
    return d


def save_org_notification_config(
    org_id: str,
    config: Optional[Dict[str, Any]] = None,
    notification_data: Optional[Dict[str, Any]] = None,
    requesting_user: Any = None,
    requesting_role: Optional[str] = None,
    **kwargs
) -> Tuple[bool, str]:
    """Saves organizational notification settings with HR RBAC validation."""
    _check_admin_auth(requesting_user, requesting_role)
    cfg = config or notification_data or kwargs or {}

    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO org_notification_config (
                org_id, review_reminders, training_reminders, goal_deadline_reminders,
                employee_registration_alerts, report_generation_alerts,
                reminder_frequency, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(org_id) DO UPDATE SET
                review_reminders = excluded.review_reminders,
                training_reminders = excluded.training_reminders,
                goal_deadline_reminders = excluded.goal_deadline_reminders,
                employee_registration_alerts = excluded.employee_registration_alerts,
                report_generation_alerts = excluded.report_generation_alerts,
                reminder_frequency = excluded.reminder_frequency,
                updated_at = CURRENT_TIMESTAMP
        """, (
            org_id,
            1 if (cfg.get("review_reminders") or cfg.get("review_reminders_enabled")) else 0,
            1 if (cfg.get("training_reminders") or cfg.get("training_reminders_enabled")) else 0,
            1 if (cfg.get("goal_deadline_reminders") or cfg.get("goal_deadline_reminders_enabled")) else 0,
            1 if cfg.get("employee_registration_alerts") else 0,
            1 if cfg.get("report_generation_alerts") else 0,
            cfg.get("reminder_frequency", "Weekly")
        ))

    return True, "Notification settings successfully updated."


# ------------------------------------------------------------------------------
# 10. EMPLOYEE PERSONAL SETTINGS & PREFERENCES
# ------------------------------------------------------------------------------
def get_user_preferences(user_id: int) -> Dict[str, Any]:
    """Retrieves personal settings, appearance, career and privacy preferences for an employee."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, email, role, employee_id, org_id, date_joined, status FROM users WHERE id = ?", (user_id,))
    u_row = cursor.fetchone()
    user_dict = dict(u_row) if u_row else {}

    cursor.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
    p_row = cursor.fetchone()
    prof_dict = dict(p_row) if p_row else {}

    cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,))
    pref_row = cursor.fetchone()
    pref_dict = dict(pref_row) if pref_row else {}

    timeline = pref_dict.get("career_timeline") or prof_dict.get("timeline") or "6-12 months"
    paths = json.loads(pref_dict.get("interested_career_paths") or "[]")
    skills = json.loads(pref_dict.get("preferred_technical_skills") or "[]")
    goal_reminders = pref_dict.get("goal_reminders") or "Weekly"
    training_notifications = pref_dict.get("training_notifications") or "1 Week Before"
    theme_mode = pref_dict.get("theme_mode") or "Light Mode"
    view_density = pref_dict.get("view_density") or "Comfortable"
    visibility = pref_dict.get("profile_visibility") or "Organization-Wide"
    location = pref_dict.get("location") or prof_dict.get("location") or ""
    summary = pref_dict.get("professional_summary") or prof_dict.get("summary") or ""

    return {
        "user_id": user_id,
        "name": user_dict.get("name") or "",
        "email": user_dict.get("email") or "",
        "role": user_dict.get("role") or "employee",
        "employee_id": user_dict.get("employee_id") or "",
        "org_id": user_dict.get("org_id") or "",
        "date_joined": user_dict.get("date_joined") or "",
        "account_status": user_dict.get("status") or "Active",
        "profile_photo": pref_dict.get("profile_photo") or "",
        "phone": pref_dict.get("phone") or prof_dict.get("phone") or "",
        "location": location,
        "summary": summary,
        "professional_summary": summary,
        "current_designation": prof_dict.get("job_title") or "",
        "target_designation": prof_dict.get("target_role") or "",
        "career_preferences": {
            "current_designation": prof_dict.get("job_title") or "",
            "target_designation": prof_dict.get("target_role") or "",
            "timeline": timeline,
            "interested_paths": paths,
            "preferred_skills": skills
        },
        "notification_preferences": {
            "goal_reminders": goal_reminders,
            "training_reminders": training_notifications,
            "performance_review_notifications": bool(pref_dict.get("review_notifications", 1)),
            "platform_notifications": bool(pref_dict.get("platform_notifications", 1))
        },
        "appearance": {
            "theme_mode": theme_mode,
            "density": view_density
        },
        "privacy": {
            "profile_visibility": visibility
        },
        "interested_career_paths": paths,
        "preferred_technical_skills": skills,
        "career_timeline": timeline,
        "goal_reminders": goal_reminders,
        "training_notifications": training_notifications,
        "review_notifications": pref_dict.get("review_notifications", 1),
        "platform_notifications": pref_dict.get("platform_notifications", 1),
        "theme_mode": theme_mode,
        "view_density": view_density,
        "profile_visibility": visibility,
        "deactivation_requested": pref_dict.get("deactivation_requested", 0),
        "deactivation_reason": pref_dict.get("deactivation_reason") or "",
        "updated_at": pref_dict.get("updated_at")
    }


def save_employee_personal_profile(
    user_id: int,
    data: Optional[Dict[str, Any]] = None,
    requesting_user: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Tuple[bool, str]:
    """Updates employee personal profile (name, phone, location, summary, photo) with strict isolation."""
    if requesting_user is not None:
        req_id = requesting_user.get("id")
        is_admin = requesting_user.get("role") == "admin"
        if req_id != user_id and not is_admin:
            raise PermissionError("Access Denied: You are not authorized to update another employee's personal profile.")

    payload = {}
    if isinstance(data, dict):
        payload.update(data)
    payload.update(kwargs)

    name = (payload.get("name") or "").strip()
    if not name:
        return False, "Full Name cannot be empty."

    phone = (payload.get("phone") or "").strip()
    location = (payload.get("location") or "").strip()
    summary = (payload.get("summary") or payload.get("professional_summary") or "").strip()
    photo = payload.get("avatar_base64") or payload.get("profile_photo") or ""

    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET name = ?, phone = ?, avatar_base64 = ? WHERE id = ?", (name, phone, photo, user_id))
        cursor.execute("UPDATE employees SET name = ?, phone = ? WHERE user_id = ?", (name, phone, user_id))

        cursor.execute("""
            INSERT INTO profiles (user_id, phone, location, summary, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                phone = excluded.phone,
                location = excluded.location,
                summary = excluded.summary,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, phone, location, summary))

        cursor.execute("""
            INSERT INTO user_preferences (user_id, profile_photo, phone, location, professional_summary, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                profile_photo = excluded.profile_photo,
                phone = excluded.phone,
                location = excluded.location,
                professional_summary = excluded.professional_summary,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, photo, phone, location, summary))

    return True, "Personal profile successfully updated and saved."


def save_employee_career_preferences(
    user_id: int,
    data: Optional[Dict[str, Any]] = None,
    career_prefs: Optional[Dict[str, Any]] = None,
    requesting_user: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Tuple[bool, str]:
    """Updates career preferences (target designation, interested paths, preferred skills, timeline)."""
    if requesting_user is not None:
        req_id = requesting_user.get("id")
        is_admin = requesting_user.get("role") == "admin"
        if req_id != user_id and not is_admin:
            raise PermissionError("Access Denied: You cannot modify another employee's career preferences.")

    payload = {}
    if isinstance(data, dict):
        payload.update(data)
    if isinstance(career_prefs, dict):
        payload.update(career_prefs)
    payload.update(kwargs)

    target_desig = (payload.get("target_designation") or payload.get("target_role") or "").strip()
    timeline = (payload.get("timeline") or payload.get("career_timeline") or "12 Months").strip()
    paths = payload.get("interested_paths") or payload.get("interested_career_paths") or []
    skills = payload.get("preferred_skills") or payload.get("preferred_technical_skills") or []

    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO profiles (user_id, target_role, timeline, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                target_role = excluded.target_role,
                timeline = excluded.timeline,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, target_desig, timeline))

        cursor.execute("""
            INSERT INTO user_preferences (
                user_id, interested_career_paths, preferred_technical_skills, career_timeline, updated_at
            ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                interested_career_paths = excluded.interested_career_paths,
                preferred_technical_skills = excluded.preferred_technical_skills,
                career_timeline = excluded.career_timeline,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, json.dumps(paths), json.dumps(skills), timeline))

    return True, "Career preferences successfully saved."


def save_employee_notification_preferences(
    user_id: int,
    data: Optional[Dict[str, Any]] = None,
    notification_prefs: Optional[Dict[str, Any]] = None,
    requesting_user: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Tuple[bool, str]:
    """Saves employee notification preferences."""
    if requesting_user is not None:
        req_id = requesting_user.get("id")
        is_admin = requesting_user.get("role") == "admin"
        if req_id != user_id and not is_admin:
            raise PermissionError("Access Denied: You cannot update notification preferences for this account.")

    payload = {}
    if isinstance(data, dict):
        payload.update(data)
    if isinstance(notification_prefs, dict):
        payload.update(notification_prefs)
    payload.update(kwargs)

    goal_rem = payload.get("goal_reminders", "Weekly")
    train_notif = payload.get("training_reminders") or payload.get("training_notifications", "1 Week Before")
    rev_notif = 1 if (payload.get("performance_review_notifications") if "performance_review_notifications" in payload else payload.get("review_notifications", True)) else 0
    plat_notif = 1 if (payload.get("platform_notifications") if "platform_notifications" in payload else payload.get("platform_notifications", True)) else 0

    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_preferences (
                user_id, goal_reminders, training_notifications,
                review_notifications, platform_notifications, updated_at
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                goal_reminders = excluded.goal_reminders,
                training_notifications = excluded.training_notifications,
                review_notifications = excluded.review_notifications,
                platform_notifications = excluded.platform_notifications,
                updated_at = CURRENT_TIMESTAMP
        """, (
            user_id,
            goal_rem,
            train_notif,
            rev_notif,
            plat_notif
        ))

    return True, "Notification preferences successfully updated."


def save_employee_appearance_preferences(
    user_id: int,
    data: Optional[Dict[str, Any]] = None,
    appearance_prefs: Optional[Dict[str, Any]] = None,
    requesting_user: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Tuple[bool, str]:
    """Saves employee visual theme & appearance preferences."""
    if requesting_user is not None:
        req_id = requesting_user.get("id")
        is_admin = requesting_user.get("role") == "admin"
        if req_id != user_id and not is_admin:
            raise PermissionError("Access Denied: Unauthorized account operation.")

    payload = {}
    if isinstance(data, dict):
        payload.update(data)
    if isinstance(appearance_prefs, dict):
        payload.update(appearance_prefs)
    payload.update(kwargs)

    theme_mode = payload.get("theme_mode", "Light Mode")
    view_density = payload.get("density") or payload.get("view_density", "Comfortable")

    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_preferences (
                user_id, theme_mode, view_density, updated_at
            ) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                theme_mode = excluded.theme_mode,
                view_density = excluded.view_density,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, theme_mode, view_density))

    return True, "Appearance preferences saved."


def save_employee_privacy_preferences(
    user_id: int,
    data: Optional[Dict[str, Any]] = None,
    privacy_prefs: Optional[Dict[str, Any]] = None,
    requesting_user: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Tuple[bool, str]:
    """Saves employee privacy visibility preferences."""
    if requesting_user is not None:
        req_id = requesting_user.get("id")
        is_admin = requesting_user.get("role") == "admin"
        if req_id != user_id and not is_admin:
            raise PermissionError("Access Denied: Unauthorized account operation.")

    payload = {}
    if isinstance(data, dict):
        payload.update(data)
    if isinstance(privacy_prefs, dict):
        payload.update(privacy_prefs)
    payload.update(kwargs)

    visibility = (payload.get("profile_visibility") or "Organization-Wide").strip()

    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_preferences (user_id, profile_visibility, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                profile_visibility = excluded.profile_visibility,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, visibility))

    return True, "Privacy preferences updated."


def request_account_deactivation(
    user_id: int,
    reason: str,
    requesting_user: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """Submits a formal account deactivation request to HR administrators."""
    if requesting_user is not None:
        req_id = requesting_user.get("id")
        is_admin = requesting_user.get("role") == "admin"
        if req_id != user_id and not is_admin:
            raise PermissionError("Access Denied: You cannot request deactivation for another account.")

    clean_reason = reason.strip()
    if not clean_reason:
        return False, "Please provide a reason for the account deactivation request."

    conn = get_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, email, employee_id, org_id FROM users WHERE id = ?", (user_id,))
        u = cursor.fetchone()
        u_dict = dict(u) if u else {}

        # 1. Update user_preferences
        cursor.execute("""
            INSERT INTO user_preferences (
                user_id, deactivation_requested, deactivation_reason, deactivation_requested_at, updated_at
            ) VALUES (?, 1, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                deactivation_requested = 1,
                deactivation_reason = excluded.deactivation_reason,
                deactivation_requested_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, clean_reason))

        # 2. Insert into audit table
        cursor.execute("""
            INSERT INTO account_deactivations (
                user_id, employee_id, org_id, user_name, user_email, reason, status, requested_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'Pending', CURRENT_TIMESTAMP)
        """, (
            user_id,
            u_dict.get("employee_id", ""),
            u_dict.get("org_id", ""),
            u_dict.get("name", ""),
            u_dict.get("email", ""),
            clean_reason
        ))

    return True, "Account deactivation request has been successfully submitted to your HR Administrator for review."


def get_account_deactivation_status(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves the latest account deactivation request status for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM account_deactivations
        WHERE user_id = ?
        ORDER BY id DESC LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


get_account_deactivation_request = get_account_deactivation_status

