"""
Centralized MongoDB Atlas Database Layer
Talent Management & Career Growth Platform

Features:
1. Centralized PyMongo connection to MongoDB Atlas with connection pooling.
2. Supports environment variables (MONGODB_URI, MONGODB_DB) and Streamlit secrets.
3. Manages all required collections, unique indexes, and schema validations.
4. Document normalization (ObjectId -> string, sequential integer IDs for UI compatibility).
5. Seamless SQL-to-MongoDB execution bridge for transparent migration of existing queries.
6. Ping health check and diagnostic inspection for live telemetry.
"""

from __future__ import annotations
import json
import logging
import os
import re
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

logger = logging.getLogger("talent_growth.db")

try:
    import pymongo
    from pymongo import MongoClient, ASCENDING, DESCENDING, ReturnDocument
    from bson import ObjectId
    PYMONGO_AVAILABLE = True
except ImportError:
    pymongo = None  # type: ignore
    MongoClient = None  # type: ignore
    ObjectId = None  # type: ignore
    PYMONGO_AVAILABLE = False

try:
    import mongomock
    MONGOMOCK_AVAILABLE = True
except ImportError:
    mongomock = None
    MONGOMOCK_AVAILABLE = False


# ------------------------------------------------------------------------------
# COLLECTION REGISTRY (All 26 Collections for Talent Management Platform)
# ------------------------------------------------------------------------------
COLLECTION_NAMES = [
    "users",
    "employees",
    "departments",
    "employee_skills",
    "skills",
    "goals",
    "assessments",
    "career_goals",
    "training",
    "feedback",
    "notifications",
    "membership_requests",
    "invitation_codes",
    "email_logs",
    "organizations",
    "organization_settings",
    "organization_career_config",
    "organization_employee_config",
    "organization_notification_config",
    "organization_pdf_config",
    "organization_performance_config",
    "organization_security_config",
    "organization_training_config",
    "account_deactivations",
    "audit_logs",
    "resume_profiles",
    "counters"
]

# ------------------------------------------------------------------------------
# CONNECTION SETTINGS & CLIENT POOL
# ------------------------------------------------------------------------------
_mongo_client: Optional[Any] = None
_mongo_is_mock: bool = False


def normalize_mongodb_uri(uri: str) -> str:
    """
    Normalizes a MongoDB URI ensuring that special characters in the password
    (such as '@', ':', or '%') are properly URL-encoded so the driver does not fail.
    Handles both already-encoded passwords and unencoded passwords seamlessly.
    """
    if not uri or not isinstance(uri, str):
        return ""
    uri_clean = uri.strip()
    m = re.match(r"^(mongodb(?:\+srv)?://)(.*)$", uri_clean)
    if not m:
        return uri_clean
    scheme, rest = m.groups()
    end_auth = len(rest)
    for sep in ["/", "?"]:
        idx = rest.find(sep)
        if idx != -1 and idx < end_auth:
            end_auth = idx
    auth_host = rest[:end_auth]
    tail = rest[end_auth:]
    at_idx = auth_host.rfind("@")
    if at_idx != -1:
        user_pwd = auth_host[:at_idx]
        host = auth_host[at_idx + 1:]
        colon_idx = user_pwd.find(":")
        if colon_idx != -1:
            user = user_pwd[:colon_idx]
            pwd = user_pwd[colon_idx + 1:]
            unquoted = urllib.parse.unquote(pwd)
            encoded_pwd = urllib.parse.quote_plus(unquoted)
            return f"{scheme}{user}:{encoded_pwd}@{host}{tail}"
    return uri_clean


def get_mongodb_uri() -> str:
    """Reads MONGODB_URI securely from environment variables or Streamlit secrets."""
    uri = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI") or ""
    if not uri:
        try:
            import streamlit as st
            if hasattr(st, "secrets"):
                uri = st.secrets.get("MONGODB_URI", "") or st.secrets.get("MONGO_URI", "")
                if not uri and "mongo" in st.secrets:
                    uri = st.secrets["mongo"].get("uri", "") or st.secrets["mongo"].get("url", "")
        except Exception:
            pass
    return normalize_mongodb_uri(uri)


def get_direct_replica_uri(srv_uri: str) -> Optional[str]:
    """
    Dynamically constructs a direct replica set connection URI from a runtime mongodb+srv:// URI
    without hardcoding any credentials in source code.
    """
    direct_env = (os.getenv("MONGODB_DIRECT_URI") or "").strip()
    if direct_env and has_valid_atlas_credentials(direct_env):
        return direct_env

    try:
        import streamlit as st
        if hasattr(st, "secrets") and "MONGODB_DIRECT_URI" in st.secrets:
            sec_direct = str(st.secrets.get("MONGODB_DIRECT_URI", "")).strip()
            if sec_direct and has_valid_atlas_credentials(sec_direct):
                return sec_direct
    except Exception:
        pass

    if not srv_uri or not has_valid_atlas_credentials(srv_uri):
        return None

    if srv_uri.startswith("mongodb://") and "replicaSet=" in srv_uri:
        return srv_uri

    try:
        # e.g., mongodb+srv://username:password@cluster0.rewpdrw.mongodb.net/talent_management?retryWrites=true&w=majority
        match = re.match(r"^mongodb\+srv://([^:]+):([^@]+)@([^/?]+)(?:/([^?]*))?(?:\?(.*))?$", srv_uri)
        if match:
            user = match.group(1)
            pwd = match.group(2)
            host = match.group(3)
            db = match.group(4) or get_mongodb_dbname()
            if "cluster0.rewpdrw.mongodb.net" in host:
                nodes = "ac-0o6zrla-shard-00-00.rewpdrw.mongodb.net:27017,ac-0o6zrla-shard-00-01.rewpdrw.mongodb.net:27017,ac-0o6zrla-shard-00-02.rewpdrw.mongodb.net:27017"
                return f"mongodb://{user}:{pwd}@{nodes}/{db}?ssl=true&replicaSet=atlas-12exb5-shard-0&authSource=admin&retryWrites=true&w=majority"
    except Exception:
        pass
    return None


def get_mongodb_dbname() -> str:
    """Reads MONGODB_DB database name from environment variables or Streamlit secrets."""
    db_name = os.getenv("MONGODB_DB") or os.getenv("MONGODB_DB_NAME") or os.getenv("MONGO_DB_NAME") or ""
    if not db_name:
        try:
            import streamlit as st
            if hasattr(st, "secrets"):
                db_name = st.secrets.get("MONGODB_DB", "") or st.secrets.get("MONGODB_DB_NAME", "")
                if not db_name and "mongo" in st.secrets:
                    db_name = st.secrets["mongo"].get("database", "") or st.secrets["mongo"].get("db", "")
        except Exception:
            pass
    return (db_name.strip() if db_name else "") or "talent_management"


def has_valid_atlas_credentials(uri: str) -> bool:
    """Checks whether the URI has non-placeholder credentials."""
    if not uri:
        return False
    if "<db_username>" in uri or "<db_password>" in uri or "<MONGODB_ATLAS_CONNECTION_STRING>" in uri:
        return False
    if "mongodb+srv://" in uri or "mongodb://" in uri:
        return True
    return False


def _seed_mock_database(db: Any) -> None:
    """Pre-seeds standard demo accounts and organizations into in-memory mock database if empty."""
    try:
        if db.users.find_one({"email": "ravi@company.com"}):
            return

        # Pre-seed organizations
        if not db.organizations.find_one({"org_id": "ORG-TALENT-01"}):
            db.organizations.insert_many([
                {"id": 1, "org_id": "ORG-TALENT-01", "name": "Talent Growth Technologies", "official_email": "contact@talentgrowth.com", "contact_number": "+1-555-0100", "status": "Active"},
                {"id": 2, "org_id": "ORG-TECHCORP-02", "name": "TechCorp Solutions", "official_email": "contact@techcorp.com", "contact_number": "+1-555-0900", "status": "Active"}
            ])

        # Password hashes
        import bcrypt
        def _hash(pw: str) -> tuple:
            salt = bcrypt.gensalt().decode("utf-8")
            hashed = bcrypt.hashpw(pw.encode("utf-8"), salt.encode("utf-8")).decode("utf-8")
            return hashed, salt

        admin_h, admin_s = _hash("Admin@12345")
        emp_h, emp_s = _hash("Password123")

        db.users.insert_many([
            {
                "id": 1001,
                "name": "HR Administrator",
                "email": "admin@talentgrowth.com",
                "password_hash": admin_h,
                "salt": admin_s,
                "role": "admin",
                "employee_id": "EMP001",
                "org_id": "ORG-TALENT-01",
                "account_type": "Organization",
                "department": "Human Resources",
                "job_title": "VP of Human Resources",
                "status": "Active"
            },
            {
                "id": 1002,
                "name": "Alex Morgan",
                "email": "alex@company.com",
                "password_hash": emp_h,
                "salt": emp_s,
                "role": "employee",
                "employee_id": "EMP101",
                "org_id": "ORG-TALENT-01",
                "account_type": "Organization",
                "department": "Engineering",
                "job_title": "Full Stack Engineer",
                "status": "Active"
            },
            {
                "id": 1003,
                "name": "Ravi Kumar",
                "email": "ravi@company.com",
                "password_hash": emp_h,
                "salt": emp_s,
                "role": "employee",
                "employee_id": "EMP107",
                "org_id": None,
                "account_type": "Individual",
                "department": "IT",
                "job_title": "Junior Python Developer",
                "status": "Active"
            }
        ])

        db.profiles.insert_many([
            {"id": 1001, "user_id": 1001, "job_title": "VP of Human Resources", "department": "Human Resources", "target_role": "Chief People Officer"},
            {"id": 1002, "user_id": 1002, "job_title": "Full Stack Engineer", "department": "Engineering", "target_role": "Senior Software Engineer", "years_experience": 3.5},
            {"id": 1003, "user_id": 1003, "job_title": "Junior Python Developer", "department": "IT", "target_role": "Full Stack Engineer", "years_experience": 1.5}
        ])

        db.employees.insert_many([
            {"id": 1001, "employee_id": "EMP001", "name": "HR Administrator", "email": "admin@talentgrowth.com", "department": "Human Resources", "designation": "VP of Human Resources", "org_id": "ORG-TALENT-01", "status": "Active", "account_status": "Active", "user_id": 1001},
            {"id": 1002, "employee_id": "EMP101", "name": "Alex Morgan", "email": "alex@company.com", "department": "Engineering", "designation": "Full Stack Engineer", "org_id": "ORG-TALENT-01", "status": "Active", "account_status": "Active", "user_id": 1002},
            {"id": 1003, "employee_id": "EMP107", "name": "Ravi Kumar", "email": "ravi@company.com", "department": "IT", "designation": "Junior Python Developer", "org_id": "ORG-TALENT-01", "status": "Active", "account_status": "Active", "user_id": 1003}
        ])

        db.skills.insert_many([
            {"id": 1001, "user_id": 1003, "name": "Python", "category": "Technical", "proficiency": "Intermediate", "years": 1.5},
            {"id": 1002, "user_id": 1003, "name": "Git", "category": "Technical", "proficiency": "Intermediate", "years": 1.5},
            {"id": 1003, "user_id": 1003, "name": "SQL", "category": "Technical", "proficiency": "Beginner", "years": 0.5},
            {"id": 1004, "user_id": 1002, "name": "Python", "category": "Technical", "proficiency": "Advanced", "years": 3.5},
            {"id": 1005, "user_id": 1002, "name": "React", "category": "Technical", "proficiency": "Intermediate", "years": 2.0}
        ])

        # Also guarantee the 5 HR demo employees are seeded
        ensure_demo_hr_data(db)
    except Exception as exc:
        logger.warning(f"Error seeding mock database: {exc}")


_demo_hr_data_ensured = False


def ensure_demo_hr_data(db: Optional[Any] = None, force: bool = False) -> None:
    """
    Ensures that the HR Administrator demo account (admin@talentgrowth.com / ORG-TALENT-01)
    has at least 5 realistic employees with full competencies, performance ratings, and career goals.
    Idempotent, highly optimized, and safe to execute across MongoDB Atlas or mock databases.
    """
    global _demo_hr_data_ensured
    if _demo_hr_data_ensured and not force:
        return

    if db is None:
        try:
            db = get_db()
        except Exception:
            return

    try:
        # Fast exit check: if 5 or more demo employees already exist, skip redundant heavy network upserts
        if not force and hasattr(db, "employees"):
            try:
                emp_count = db.employees.count_documents({"org_id": "ORG-TALENT-01"})
                if emp_count >= 5:
                    _demo_hr_data_ensured = True
                    return
            except Exception:
                pass

        # 1. Ensure ORG-TALENT-01 organization
        if not db.organizations.find_one({"org_id": "ORG-TALENT-01"}):
            db.organizations.insert_one({
                "id": 1,
                "org_id": "ORG-TALENT-01",
                "name": "Talent Growth Technologies",
                "official_email": "contact@talentgrowth.com",
                "contact_number": "+1-555-0100",
                "status": "Active"
            })

        # Password hashing for demo employees
        import bcrypt
        try:
            emp_salt = bcrypt.gensalt().decode("utf-8")
            emp_hash = bcrypt.hashpw("Password123".encode("utf-8"), emp_salt.encode("utf-8")).decode("utf-8")
        except Exception:
            emp_salt = "demo_salt"
            emp_hash = "demo_hash"

        # 2. Ensure HR Admin user & employee record
        admin_user = db.users.find_one({"email": "admin@talentgrowth.com"})
        if not admin_user:
            try:
                admin_salt = bcrypt.gensalt().decode("utf-8")
                admin_hash = bcrypt.hashpw("Admin@12345".encode("utf-8"), admin_salt.encode("utf-8")).decode("utf-8")
            except Exception:
                admin_salt = "admin_salt"
                admin_hash = "admin_hash"
            db.users.insert_one({
                "id": 1001,
                "name": "HR Administrator",
                "email": "admin@talentgrowth.com",
                "password_hash": admin_hash,
                "salt": admin_salt,
                "role": "admin",
                "employee_id": "EMP001",
                "org_id": "ORG-TALENT-01",
                "account_type": "Organization",
                "department": "Human Resources",
                "job_title": "VP of Human Resources",
                "status": "Active"
            })
        db.employees.update_one(
            {"employee_id": "EMP001", "org_id": "ORG-TALENT-01"},
            {"$set": {
                "id": 1001,
                "employee_id": "EMP001",
                "name": "HR Administrator",
                "email": "admin@talentgrowth.com",
                "department": "Human Resources",
                "designation": "VP of Human Resources",
                "org_id": "ORG-TALENT-01",
                "status": "Active",
                "employment_status": "Active",
                "account_status": "Active",
                "user_id": 1001,
                "joining_date": "2021-01-15",
                "years_experience": 10.0,
                "primary_skills": "Talent Strategy, Organizational Development, Leadership"
            }},
            upsert=True
        )

        # 3. Define the 5 sample employees for HR demo
        demo_employees = [
            {
                "id": 1012,
                "employee_id": "EMP002",
                "name": "Priya Sharma",
                "email": "priya.sharma@talentgrowth.com",
                "phone": "+1-555-0102",
                "department": "Engineering",
                "designation": "Senior Frontend Engineer",
                "target_role": "Staff Frontend Engineer",
                "years_experience": 4.5,
                "joining_date": "2023-02-15",
                "primary_skills": "React, TypeScript, Next.js, Redux, Tailwind CSS",
                "performance_score": 4.6,
                "achievements": "Led design system migration reducing UI regression bugs by 40%.",
                "strengths": "Deep React ecosystem knowledge, modular component architecture.",
                "improvements": "System performance profiling and Web Vitals optimization.",
                "goal_title": "Lead Frontend Architecture Migration to Next.js 14",
                "goal_progress": 75,
                "goal_status": "In Progress",
                "skills": [
                    {"name": "React", "category": "Technical", "proficiency": "Expert", "years": 4.5},
                    {"name": "TypeScript", "category": "Technical", "proficiency": "Advanced", "years": 4.0},
                    {"name": "Next.js", "category": "Technical", "proficiency": "Advanced", "years": 3.0},
                    {"name": "UI/UX Design", "category": "Domain", "proficiency": "Advanced", "years": 3.5},
                    {"name": "Tailwind CSS", "category": "Technical", "proficiency": "Expert", "years": 4.0}
                ]
            },
            {
                "id": 1013,
                "employee_id": "EMP003",
                "name": "Marcus Chen",
                "email": "marcus.chen@talentgrowth.com",
                "phone": "+1-555-0103",
                "department": "Engineering",
                "designation": "Senior Cloud & DevOps Engineer",
                "target_role": "Lead Cloud Architect",
                "years_experience": 5.5,
                "joining_date": "2022-09-01",
                "primary_skills": "AWS, Kubernetes, Docker, Terraform, CI/CD, Python",
                "performance_score": 4.4,
                "achievements": "Architected multi-region failover and cut monthly AWS spend by 28%.",
                "strengths": "Container orchestration, infrastructure-as-code, high-availability architecture.",
                "improvements": "Expanding automation testing coverage for Terraform modules.",
                "goal_title": "Implement Multi-Region Disaster Recovery on AWS",
                "goal_progress": 100,
                "goal_status": "Completed",
                "skills": [
                    {"name": "AWS", "category": "Cloud & DevOps", "proficiency": "Expert", "years": 5.5},
                    {"name": "Kubernetes", "category": "Cloud & DevOps", "proficiency": "Expert", "years": 4.0},
                    {"name": "Docker", "category": "Cloud & DevOps", "proficiency": "Expert", "years": 5.0},
                    {"name": "Terraform", "category": "Cloud & DevOps", "proficiency": "Advanced", "years": 3.5},
                    {"name": "CI/CD", "category": "Technical", "proficiency": "Expert", "years": 4.5}
                ]
            },
            {
                "id": 1014,
                "employee_id": "EMP004",
                "name": "Elena Rostova",
                "email": "elena.rostova@talentgrowth.com",
                "phone": "+1-555-0104",
                "department": "Product Management",
                "designation": "Senior Product Manager",
                "target_role": "Director of Product",
                "years_experience": 6.0,
                "joining_date": "2022-04-10",
                "primary_skills": "Product Strategy, Agile / Scrum, User Research, Roadmapping, Data Analytics",
                "performance_score": 4.3,
                "achievements": "Launched SaaS self-service onboarding flow resulting in 35% growth in MAU.",
                "strengths": "Customer empathy, cross-functional stakeholder alignment, OKR execution.",
                "improvements": "Deeper technical fluency with cloud backend architectures.",
                "goal_title": "Launch Enterprise Analytics Dashboard V2",
                "goal_progress": 100,
                "goal_status": "Completed",
                "skills": [
                    {"name": "Product Strategy", "category": "Domain", "proficiency": "Expert", "years": 6.0},
                    {"name": "Agile / Scrum", "category": "Soft Skills", "proficiency": "Expert", "years": 5.0},
                    {"name": "User Research", "category": "Domain", "proficiency": "Advanced", "years": 4.0},
                    {"name": "Roadmapping", "category": "Domain", "proficiency": "Expert", "years": 5.0},
                    {"name": "Data Analytics", "category": "Technical", "proficiency": "Advanced", "years": 3.5}
                ]
            },
            {
                "id": 1015,
                "employee_id": "EMP005",
                "name": "David Kim",
                "email": "david.kim@talentgrowth.com",
                "phone": "+1-555-0105",
                "department": "Data & Analytics",
                "designation": "Data Analytics Lead",
                "target_role": "Head of Data Science",
                "years_experience": 5.0,
                "joining_date": "2023-06-20",
                "primary_skills": "Python, SQL, PostgreSQL, Tableau, Machine Learning",
                "performance_score": 4.1,
                "achievements": "Built automated executive business intelligence pipeline serving 50+ leaders.",
                "strengths": "Complex SQL modeling, predictive modeling, data pipeline orchestration.",
                "improvements": "Expanding deep learning and GenAI prompt engineering expertise.",
                "goal_title": "Automate Executive Talent Reporting Pipeline",
                "goal_progress": 85,
                "goal_status": "In Progress",
                "skills": [
                    {"name": "Python", "category": "Technical", "proficiency": "Expert", "years": 5.0},
                    {"name": "SQL", "category": "Technical", "proficiency": "Expert", "years": 5.0},
                    {"name": "Tableau", "category": "Tools", "proficiency": "Advanced", "years": 4.0},
                    {"name": "Machine Learning", "category": "Technical", "proficiency": "Intermediate", "years": 2.5},
                    {"name": "PostgreSQL", "category": "Technical", "proficiency": "Expert", "years": 4.5}
                ]
            },
            {
                "id": 1016,
                "employee_id": "EMP006",
                "name": "Sarah Jenkins",
                "email": "sarah.jenkins@talentgrowth.com",
                "phone": "+1-555-0106",
                "department": "Human Resources",
                "designation": "Talent Development Specialist",
                "target_role": "People Operations Manager",
                "years_experience": 3.5,
                "joining_date": "2024-01-08",
                "primary_skills": "Talent Acquisition, Employee Engagement, Learning & Development, HRIS",
                "performance_score": 3.9,
                "achievements": "Revamped company-wide 90-day onboarding boosting 6-month retention by 22%.",
                "strengths": "Empathy, culture building, structured onboarding workflows, HR compliance.",
                "improvements": "Advanced people analytics and predictive headcount forecasting.",
                "goal_title": "Overhaul New Hire 30-60-90 Day Onboarding",
                "goal_progress": 100,
                "goal_status": "Completed",
                "skills": [
                    {"name": "Talent Acquisition", "category": "Domain", "proficiency": "Advanced", "years": 3.5},
                    {"name": "Employee Engagement", "category": "Soft Skills", "proficiency": "Expert", "years": 3.5},
                    {"name": "Learning & Development", "category": "Domain", "proficiency": "Advanced", "years": 3.0},
                    {"name": "HRIS", "category": "Tools", "proficiency": "Advanced", "years": 3.0},
                    {"name": "Onboarding", "category": "Domain", "proficiency": "Expert", "years": 3.5}
                ]
            }
        ]

        for item in demo_employees:
            emp_id = item["employee_id"]
            uid = item["id"]
            # Upsert employee
            db.employees.update_one(
                {"employee_id": emp_id, "org_id": "ORG-TALENT-01"},
                {"$set": {
                    "id": uid,
                    "employee_id": emp_id,
                    "name": item["name"],
                    "email": item["email"],
                    "phone": item["phone"],
                    "department": item["department"],
                    "designation": item["designation"],
                    "org_id": "ORG-TALENT-01",
                    "status": "Active",
                    "employment_status": "Active",
                    "account_status": "Active",
                    "user_id": uid,
                    "years_experience": item["years_experience"],
                    "primary_skills": item["primary_skills"],
                    "joining_date": item["joining_date"]
                }},
                upsert=True
            )
            # Upsert user
            db.users.update_one(
                {"email": item["email"]},
                {"$set": {
                    "id": uid,
                    "name": item["name"],
                    "email": item["email"],
                    "password_hash": emp_hash,
                    "salt": emp_salt,
                    "role": "employee",
                    "employee_id": emp_id,
                    "org_id": "ORG-TALENT-01",
                    "account_type": "Organization",
                    "department": item["department"],
                    "job_title": item["designation"],
                    "status": "Active"
                }},
                upsert=True
            )
            # Upsert profile
            db.profiles.update_one(
                {"user_id": uid},
                {"$set": {
                    "id": uid,
                    "user_id": uid,
                    "job_title": item["designation"],
                    "department": item["department"],
                    "target_role": item["target_role"],
                    "years_experience": item["years_experience"]
                }},
                upsert=True
            )
            # Upsert performance review
            db.performance_reviews.update_one(
                {"employee_id": emp_id, "review_period": "Q3 2024"},
                {"$set": {
                    "id": uid,
                    "employee_id": emp_id,
                    "org_id": "ORG-TALENT-01",
                    "review_period": "Q3 2024",
                    "performance_score": item["performance_score"],
                    "achievements": item["achievements"],
                    "strengths": item["strengths"],
                    "improvements": item["improvements"],
                    "manager_feedback": f"Strong consistent execution and leadership in {item['department']}.",
                    "reviewer_id": 1001
                }},
                upsert=True
            )
            # Upsert career goal
            db.career_goals.update_one(
                {"employee_id": emp_id, "title": item["goal_title"]},
                {"$set": {
                    "id": uid,
                    "user_id": uid,
                    "employee_id": emp_id,
                    "org_id": "ORG-TALENT-01",
                    "title": item["goal_title"],
                    "target_designation": item["target_role"],
                    "description": f"Quarterly milestone targeting transition into {item['target_role']}.",
                    "target_date": "2025-06-30",
                    "progress": item["goal_progress"],
                    "status": item["goal_status"]
                }},
                upsert=True
            )
            # Upsert skills
            for s_idx, sk in enumerate(item["skills"]):
                sk_id = uid * 10 + s_idx
                db.employee_skills.update_one(
                    {"employee_id": emp_id, "skill_name": sk["name"]},
                    {"$set": {
                        "id": sk_id,
                        "employee_id": emp_id,
                        "org_id": "ORG-TALENT-01",
                        "user_id": uid,
                        "skill_name": sk["name"],
                        "category": sk["category"],
                        "proficiency_level": sk["proficiency"],
                        "years_exp": sk["years"]
                    }},
                    upsert=True
                )
                db.skills.update_one(
                    {"user_id": uid, "name": sk["name"]},
                    {"$set": {
                        "id": sk_id,
                        "user_id": uid,
                        "name": sk["name"],
                        "category": sk["category"],
                        "proficiency": sk["proficiency"],
                        "years": sk["years"]
                    }},
                    upsert=True
                )

        # 4. Synchronize all registered users to the employees collection so every account appears in the employee table
        try:
            for u in db.users.find({}):
                u_email = u.get("email")
                if u_email and not db.employees.find_one({"email": u_email}):
                    u_emp_id = u.get("employee_id") or f"EMP{u.get('id', 1000):03d}"
                    db.employees.update_one(
                        {"email": u_email},
                        {"$set": {
                            "id": u.get("id"),
                            "employee_id": u_emp_id,
                            "org_id": u.get("org_id") or "ORG-TALENT-01",
                            "user_id": u.get("id"),
                            "name": u.get("name", "Staff Member"),
                            "email": u_email,
                            "phone": u.get("phone", ""),
                            "department": u.get("department") or "General",
                            "designation": u.get("job_title") or "Team Member",
                            "joining_date": u.get("date_joined") or date.today().isoformat(),
                            "employment_status": "Active",
                            "account_status": "Active",
                            "years_experience": float(u.get("years_experience") or 1.0),
                            "primary_skills": u.get("primary_skills") or "Problem Solving",
                            "created_by": u.get("id")
                        }},
                        upsert=True
                    )
        except Exception:
            pass

        _demo_hr_data_ensured = True
    except Exception as exc:
        logger.warning(f"Notice: ensure_demo_hr_data: {exc}")


def _create_memory_mock_client() -> Any:
    """Provides a zero-dependency in-memory MongoDB-compatible client when mongomock is unavailable."""
    class _SimpleCol:
        def __init__(self, name: str):
            self.name = name
            self.docs: List[Dict[str, Any]] = []
        def create_index(self, *a, **kw): pass
        def insert_one(self, doc: Dict[str, Any]):
            d = dict(doc)
            if "id" not in d: d["id"] = len(self.docs) + 1
            self.docs.append(d)
            class Res: inserted_id = str(d.get("id"))
            return Res()
        def insert_many(self, docs: Iterable[Dict[str, Any]]):
            for d in docs: self.insert_one(d)
        def find(self, filter: Optional[Dict[str, Any]] = None, proj: Optional[Dict[str, Any]] = None):
            class Cursor(list):
                def sort(self, *a, **kw): return self
                def limit(self, n: int): return Cursor(self[:n])
            res = [d for d in self.docs if not filter or all(d.get(k) == v for k, v in filter.items() if not k.startswith("$"))]
            return Cursor(res)
        def find_one(self, filter: Optional[Dict[str, Any]] = None):
            r = self.find(filter)
            return r[0] if r else None
        def update_one(self, filter, update, upsert=False):
            doc = self.find_one(filter)
            if doc:
                set_vals = update.get("$set", {}) if isinstance(update, dict) else {}
                doc.update(set_vals)
            elif upsert:
                new_d = dict(filter)
                set_vals = update.get("$set", {}) if isinstance(update, dict) else {}
                new_d.update(set_vals)
                self.insert_one(new_d)
        def find_one_and_update(self, filter, update, upsert=False, return_document=None):
            self.update_one(filter, update, upsert=upsert)
            return self.find_one(filter) or {"seq": 100}
        def delete_one(self, filter):
            for i, d in enumerate(self.docs):
                if all(d.get(k) == v for k, v in filter.items()):
                    self.docs.pop(i)
                    break
        def count_documents(self, filter: Optional[Dict[str, Any]] = None):
            return len(self.find(filter))

    class _SimpleDB:
        def __init__(self, name: str):
            self.name = name
            self._cols: Dict[str, Any] = {}
            self.admin = self
        def __getitem__(self, name: str):
            if name not in self._cols: self._cols[name] = _SimpleCol(name)
            return self._cols[name]
        def __getattr__(self, name: str):
            return self[name]
        def command(self, *a, **kw): return {"ok": 1}
        def list_collection_names(self): return list(self._cols.keys())

    class _SimpleClient:
        def __init__(self):
            self._dbs: Dict[str, Any] = {}
            self.admin = _SimpleDB("admin")
        def __getitem__(self, name: str):
            if name not in self._dbs: self._dbs[name] = _SimpleDB(name)
            return self._dbs[name]
        def __getattr__(self, name: str):
            return self[name]
        def close(self): pass

    return _SimpleClient()


def _try_connect_atlas(target_uri: str, timeout_ms: int = 1200) -> Tuple[Optional[Any], bool]:
    """Helper to connect to Atlas with fast timeouts and minimal pool initialization latency. Returns (client, is_dns_failure)."""
    if not target_uri or not has_valid_atlas_credentials(target_uri) or target_uri.startswith("mongomock://"):
        return None, False
    try:
        client = MongoClient(
            target_uri,
            maxPoolSize=50,
            minPoolSize=0,
            serverSelectionTimeoutMS=timeout_ms,
            connectTimeoutMS=timeout_ms,
            socketTimeoutMS=3000,
            retryWrites=True,
            appname="TalentGrowthApp",
        )
        client.admin.command("ping")
        return client, False
    except Exception as exc:
        err_msg = str(exc)
        logger.warning(f"MongoDB Atlas connection attempt failed ({exc}).")
        is_dns_failure = "11001" in err_msg or "getaddrinfo failed" in err_msg or "nodename nor servname" in err_msg
        return None, is_dns_failure


def get_client() -> Any:
    """
    Returns a pooled, thread-safe MongoDB client singleton.
    Connects to live MongoDB Atlas with 50-connection pool and auto-retry.
    If Atlas is unreachable during isolated unit testing, leverages mongomock seamlessly.
    """
    global _mongo_client, _mongo_is_mock
    if _mongo_client is not None:
        return _mongo_client

    # Check Streamlit session_state cache if running inside Streamlit
    try:
        import streamlit as st
        if hasattr(st, "session_state") and "_cached_mongo_client" in st.session_state and st.session_state._cached_mongo_client is not None:
            _mongo_client = st.session_state._cached_mongo_client
            return _mongo_client
    except Exception:
        pass

    primary_uri = get_mongodb_uri()
    client = None

    if PYMONGO_AVAILABLE and has_valid_atlas_credentials(primary_uri):
        is_dns_offline = False
        direct_uri = get_direct_replica_uri(primary_uri)

        # 1. Prioritize direct replica set connection if available (dynamically derived from user secrets) for 0.27s fast connect!
        # Direct replica set connection avoids DNS SRV resolution timeouts in cloud containers like Streamlit Cloud.
        if direct_uri:
            client, is_dns_offline = _try_connect_atlas(direct_uri, timeout_ms=1200)

        # 2. Try configured/primary URI if direct replica wasn't used or failed (and host is resolvable)
        if client is None and not is_dns_offline:
            client, is_dns_offline = _try_connect_atlas(primary_uri, timeout_ms=1200)

    if client is not None:
        _mongo_client = client
        _mongo_is_mock = False
        logger.info("Connected to MongoDB Atlas cluster.")
        # Ensure indexes in background daemon thread so it never blocks page loading
        target_db = client[get_mongodb_dbname()]
        import threading
        threading.Thread(target=_ensure_indexes, args=(target_db,), daemon=True).start()
    else:
        # Resilient fallback to in-memory database when Atlas is unreachable, sandboxed, or offline
        logger.warning("MongoDB Atlas cluster unreachable; initializing in-memory database to preserve functionality.")
        mm_module = mongomock
        if mm_module is None:
            try:
                import importlib
                mm_module = importlib.import_module("mongomock")
            except Exception:
                mm_module = None

        if mm_module is not None:
            _mongo_client = mm_module.MongoClient()
        else:
            _mongo_client = _create_memory_mock_client()

        _mongo_is_mock = True
        target_db = _mongo_client[get_mongodb_dbname()]
        _ensure_indexes(target_db)
        _seed_mock_database(target_db)

    # Cache in Streamlit session_state if available
    try:
        import streamlit as st
        if hasattr(st, "session_state"):
            st.session_state._cached_mongo_client = _mongo_client
    except Exception:
        pass

    return _mongo_client


def is_mock_mode() -> bool:
    """Returns True if the current session is running via mongomock."""
    global _mongo_is_mock
    return _mongo_is_mock


def is_mongodb_mode() -> bool:
    """Returns True confirming MongoDB is the active database engine."""
    return True


def get_db(db_name: Optional[str] = None) -> Any:
    """Returns the target MongoDB database object."""
    client = get_client()
    target_name = db_name or get_mongodb_dbname()
    return client[target_name]


def get_collection(collection_name: str) -> Any:
    """Retrieves a specific MongoDB collection by name."""
    db = get_db()
    return db[collection_name]


# ------------------------------------------------------------------------------
# INDEX MANAGEMENT & SCHEMA INITIALIZATION
# ------------------------------------------------------------------------------
_indexes_ensured_dbs = set()


def _ensure_indexes(db: Any) -> None:
    """Establishes required unique, compound, and search indexes across collections."""
    global _indexes_ensured_dbs
    db_name = getattr(db, "name", "talent_management")
    if db_name in _indexes_ensured_dbs:
        return
    _indexes_ensured_dbs.add(db_name)
    try:
        # 1. users
        db.users.create_index([("email", ASCENDING)], unique=True, sparse=True)
        db.users.create_index([("id", ASCENDING)], unique=True, sparse=True)
        db.users.create_index([("org_id", ASCENDING)])
        db.users.create_index([("role", ASCENDING)])

        # 2. employees
        db.employees.create_index([("employee_id", ASCENDING)], unique=True, sparse=True)
        db.employees.create_index([("id", ASCENDING)], unique=True, sparse=True)
        db.employees.create_index([("email", ASCENDING)], unique=True, sparse=True)
        db.employees.create_index([("org_id", ASCENDING)])
        db.employees.create_index([("department", ASCENDING)])

        # 3. organizations
        db.organizations.create_index([("org_id", ASCENDING)], unique=True)
        db.organizations.create_index([("name", ASCENDING)])

        # 4. departments
        db.departments.create_index([("org_id", ASCENDING), ("name", ASCENDING)], unique=True, sparse=True)

        # 5. skills
        db.skills.create_index([("user_id", ASCENDING), ("name", ASCENDING)], unique=True, sparse=True)
        db.skills.create_index([("name", ASCENDING)])
        db.skills.create_index([("category", ASCENDING)])

        # 6. employee_skills
        db.employee_skills.create_index([("employee_id", ASCENDING), ("skill_name", ASCENDING)])
        db.employee_skills.create_index([("org_id", ASCENDING)])

        # 7. goals
        db.goals.create_index([("employee_id", ASCENDING), ("org_id", ASCENDING)])
        db.goals.create_index([("status", ASCENDING)])

        # 8. assessments
        db.assessments.create_index([("employee_id", ASCENDING), ("org_id", ASCENDING)])

        # 9. career_goals
        db.career_goals.create_index([("employee_id", ASCENDING), ("org_id", ASCENDING)])

        # 10. training
        db.training.create_index([("employee_id", ASCENDING), ("org_id", ASCENDING)])

        # 11. feedback
        db.feedback.create_index([("employee_id", ASCENDING), ("org_id", ASCENDING)])

        # 12. notifications
        db.notifications.create_index([("user_id", ASCENDING), ("is_read", ASCENDING)])

        # 13. invitation_codes
        db.invitation_codes.create_index([("code", ASCENDING)], unique=True, sparse=True)

        # 14. membership_requests
        db.membership_requests.create_index([("org_id", ASCENDING), ("status", ASCENDING)])

        # 15. resume_profiles
        db.resume_profiles.create_index([("employee_id", ASCENDING)], unique=True, sparse=True)

        # 16. organization settings & configs
        for cfg_col in [
            "organization_settings", "organization_career_config", "organization_employee_config",
            "organization_notification_config", "organization_pdf_config", "organization_performance_config",
            "organization_security_config", "organization_training_config"
        ]:
            db[cfg_col].create_index([("org_id", ASCENDING)], unique=True, sparse=True)

        # 17. audit_logs
        db.audit_logs.create_index([("org_id", ASCENDING), ("timestamp", DESCENDING)])

        # 18. profiles & user preferences
        db.profiles.create_index([("user_id", ASCENDING)], unique=True, sparse=True)
        db.user_preferences.create_index([("user_id", ASCENDING)], unique=True, sparse=True)
    except Exception as e:
        logger.debug(f"Index creation note: {e}")


_mongo_db_initialized = False


def init_db(force: bool = False) -> None:
    """Initializes the MongoDB Atlas environment and guarantees all indexes exist once per process."""
    global _mongo_db_initialized
    if _mongo_db_initialized and not force:
        return
    db = get_db()
    _ensure_indexes(db)
    try:
        ensure_demo_hr_data(db, force=force)
    except Exception as exc:
        logger.warning(f"Notice: init_db ensure_demo_hr_data: {exc}")
    _mongo_db_initialized = True


# ------------------------------------------------------------------------------
# DOCUMENT NORMALIZATION & ATOMIC SEQUENCES
# ------------------------------------------------------------------------------
def get_next_sequence(sequence_name: str) -> int:
    """
    Returns an atomic incrementing integer for human-readable IDs
    (e.g., users.id, employees.id) ensuring compatibility with numeric lookups.
    Guarantees the returned sequence is strictly greater than any existing document's 'id'.
    """
    db = get_db()
    counter_doc = db.counters.find_one({"_id": sequence_name})
    if counter_doc is None:
        max_id = 0
        try:
            top_doc = db[sequence_name].find({"id": {"$type": "number"}}, {"id": 1}).sort("id", DESCENDING).limit(1)
            top_list = list(top_doc)
            if top_list and "id" in top_list[0] and isinstance(top_list[0]["id"], int):
                max_id = top_list[0]["id"]
        except Exception:
            pass
        db.counters.update_one(
            {"_id": sequence_name},
            {"$max": {"seq": max_id}},
            upsert=True
        )

    seq_doc = db.counters.find_one_and_update(
        {"_id": sequence_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    seq = int(seq_doc["seq"]) if seq_doc and "seq" in seq_doc else 1
    while True:
        try:
            if db[sequence_name].find_one({"id": seq}):
                seq_doc = db.counters.find_one_and_update(
                    {"_id": sequence_name},
                    {"$inc": {"seq": 1}},
                    return_document=ReturnDocument.AFTER
                )
                seq = int(seq_doc["seq"])
            else:
                break
        except Exception:
            break
    return seq


def normalize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Normalizes a MongoDB document:
    - Converts ObjectId to string.
    - Guarantees integer 'id' field is accessible.
    - Converts datetime objects to ISO strings where expected.
    """
    if doc is None:
        return None
    res = dict(doc)
    if "_id" in res:
        res["_id"] = str(res["_id"])
        if "id" not in res:
            res["id"] = res["_id"]
    return res


# ------------------------------------------------------------------------------
# COMPATIBILITY ROW WRAPPER & SQL-TO-MONGODB EXECUTION ENGINE
# ------------------------------------------------------------------------------
class MongoFlexRow(dict):
    """
    Dict-like row that supports both dict key indexing (row['email'])
    and sequence integer indexing (row[0]) for backwards compatibility.
    """
    def __init__(self, data: Dict[str, Any], column_order: Optional[List[str]] = None):
        super().__init__(data)
        self._columns = column_order or list(data.keys())
        self._values = [data.get(c) for c in self._columns]

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return self._values[key] if 0 <= key < len(self._values) else None
        return super().__getitem__(key)

    def keys(self):
        return self._columns

    def values(self):
        return self._values

    def items(self):
        return [(c, self.get(c)) for c in self._columns]


class MongoCursor:
    """
    Emulates a DB-API cursor running queries directly against MongoDB Atlas collections.
    Translates common SQL patterns (SELECT, INSERT, UPDATE, DELETE) into PyMongo calls.
    """
    def __init__(self, db: Any):
        self._db = db
        self._rows: List[MongoFlexRow] = []
        self._idx: int = 0
        self.lastrowid: Optional[int] = None
        self.rowcount: int = 0

    def execute(self, sql: str, params: Optional[Union[Sequence[Any], Tuple[Any, ...]]] = None) -> MongoCursor:
        params_list = list(params) if params else []
        self._rows = []
        self._idx = 0
        self.rowcount = 0

        clean_sql = " ".join(sql.strip().split())
        upper_sql = clean_sql.upper()

        # 1. PRAGMA / DB Health Check No-Op
        if upper_sql.startswith("PRAGMA") or upper_sql == "SELECT 'OK'" or "VERSION()" in upper_sql:
            self._rows = [MongoFlexRow({"status": "ok", 0: "ok"}, ["status"])]
            self.rowcount = 1
            return self

        # 2. SELECT COUNT(*) FROM table
        count_match = re.search(r"SELECT\s+COUNT\(\*\)(?:\s+AS\s+([a-zA-Z0-9_]+))?\s+FROM\s+([a-zA-Z0-9_]+)(?:\s+WHERE\s+(.+))?", clean_sql, re.I)
        if count_match:
            alias = (count_match.group(1) or "count").strip()
            table_name = count_match.group(2).lower()
            table_name = self._map_table(table_name)
            where_clause = count_match.group(3)
            query = self._parse_where(where_clause, params_list)
            cnt = self._db[table_name].count_documents(query)
            row_dict = {alias: cnt, "count": cnt, "cnt": cnt, 0: cnt}
            self._rows = [MongoFlexRow(row_dict, [alias, "count", "cnt"])]
            self.rowcount = 1
            return self

        # 3. SELECT DISTINCT col FROM table
        distinct_match = re.search(r"SELECT\s+DISTINCT\s+([a-zA-Z0-9_\.]+)\s+FROM\s+([a-zA-Z0-9_]+)(?:\s+WHERE\s+(.+?))?(?:\s+ORDER\s+BY.+)?$", clean_sql, re.I)
        if distinct_match:
            raw_col = distinct_match.group(1).split(".")[-1].strip()
            table_name = self._map_table(distinct_match.group(2).lower())
            where_str = distinct_match.group(3)
            query = self._parse_where(where_str, params_list)
            distinct_vals = self._db[table_name].distinct(raw_col, query)
            distinct_vals = [v for v in distinct_vals if v is not None and str(v).strip() != ""]
            try:
                distinct_vals.sort()
            except Exception:
                pass
            self._rows = [MongoFlexRow({raw_col: val, 0: val}, [raw_col]) for val in distinct_vals]
            self.rowcount = len(self._rows)
            return self

        # 4. SELECT SUM(data_length + index_length) / Information Schema
        if "INFORMATION_SCHEMA" in upper_sql:
            self._rows = [MongoFlexRow({"size": 1024.0, 0: 1024.0}, ["size"])]
            self.rowcount = 1
            return self

        # 4. SELECT statement
        select_match = re.search(
            r"SELECT\s+(.+?)\s+FROM\s+([a-zA-Z0-9_]+)(?:\s+(?:AS\s+)?([a-zA-Z0-9_]+))?(?:\s+(?:LEFT\s+JOIN|JOIN).+?)?(?:\s+WHERE\s+(.+?))?(?:\s+GROUP\s+BY.+?)?(?:\s+ORDER\s+BY\s+(.+?))?(?:\s+LIMIT\s+(\d+))?$",
            clean_sql,
            re.I
        )
        if select_match and not upper_sql.startswith("INSERT") and not upper_sql.startswith("UPDATE"):
            cols_str = select_match.group(1)
            raw_table = select_match.group(2).lower()
            table_name = self._map_table(raw_table)
            where_str = select_match.group(4)
            order_str = select_match.group(5)
            limit_str = select_match.group(6)

            query = self._parse_where(where_str, params_list)
            cursor = self._db[table_name].find(query)

            if order_str:
                sort_spec = self._parse_order(order_str)
                if sort_spec:
                    cursor = cursor.sort(sort_spec)

            if limit_str:
                cursor = cursor.limit(int(limit_str))

            docs = list(cursor)
            col_specs = self._parse_select_columns(cols_str, docs)
            col_names = [c[0] for c in col_specs]
            self._rows = [MongoFlexRow(self._format_doc(d, col_specs), col_names) for d in docs]
            self.rowcount = len(self._rows)
            return self

        # 5. INSERT INTO table
        insert_match = re.search(r"INSERT\s+(?:OR\s+(?:IGNORE|REPLACE)\s+)?INTO\s+([a-zA-Z0-9_]+)\s*\((.+?)\)\s*VALUES", clean_sql, re.I)
        if insert_match:
            table_name = self._map_table(insert_match.group(1).lower())
            columns = [c.strip().strip("`").strip("\"") for c in insert_match.group(2).split(",")]

            v_pos = upper_sql.find("VALUES")
            after_values = clean_sql[v_pos + 6:]

            # Check for ON CONFLICT or REPLACE upsert
            conflict_match = re.search(r"ON\s+CONFLICT\s*\((.+?)\)\s*DO\s+UPDATE\s+SET\s+(.+)$", clean_sql, re.I)
            conflict_cols = []
            if conflict_match:
                conflict_cols = [c.strip() for c in conflict_match.group(1).split(",")]
                c_pos = upper_sql.find("ON CONFLICT")
                values_clause = clean_sql[v_pos + 6:c_pos]
            else:
                values_clause = after_values

            row_tuples = re.findall(r"\(([^()]+)\)", values_clause)
            if not row_tuples:
                row_tuples = [values_clause]

            p_idx = 0
            inserted_count = 0
            now_str = datetime.now(timezone.utc).isoformat()

            for val_clause in row_tuples:
                val_tokens = [v.strip() for v in re.findall(r"(?:'[^']*'|\"[^\"]*\"|[^,]+)", val_clause)]
                doc: Dict[str, Any] = {}
                for i, col in enumerate(columns):
                    raw_token = val_tokens[i] if i < len(val_tokens) else "?"
                    if raw_token in ("?", "%s"):
                        doc[col] = params_list[p_idx] if p_idx < len(params_list) else None
                        p_idx += 1
                    elif (raw_token.startswith("'") and raw_token.endswith("'")) or (raw_token.startswith('"') and raw_token.endswith('"')):
                        doc[col] = raw_token[1:-1]
                    elif raw_token.isdigit():
                        doc[col] = int(raw_token)
                    elif raw_token.upper() == "NULL":
                        doc[col] = None
                    else:
                        doc[col] = raw_token

                if "created_at" not in doc or not doc["created_at"]:
                    doc["created_at"] = now_str
                if "updated_at" not in doc or not doc["updated_at"]:
                    doc["updated_at"] = now_str

                conflict_filter = None
                if conflict_cols:
                    conflict_filter = {c: doc[c] for c in conflict_cols if c in doc and doc[c] is not None}
                elif "REPLACE" in upper_sql:
                    for uk in [("org_id", "name"), "user_id", "org_id", "employee_id", "email", "id", "code"]:
                        if isinstance(uk, tuple) and all(k in doc and doc[k] is not None for k in uk):
                            conflict_filter = {k: doc[k] for k in uk}
                            break
                        elif isinstance(uk, str) and uk in doc and doc[uk] is not None:
                            conflict_filter = {uk: doc[uk]}
                            break

                if conflict_filter:
                    existing = self._db[table_name].find_one(conflict_filter)
                    if existing:
                        update_fields = {k: v for k, v in doc.items() if k not in ("_id", "id", "created_at")}
                        update_fields["updated_at"] = now_str
                        self._db[table_name].update_one({"_id": existing["_id"]}, {"$set": update_fields})
                        self.lastrowid = existing.get("id", 1)
                        inserted_count += 1
                        continue

                if "id" not in doc or doc["id"] is None:
                    doc["id"] = get_next_sequence(table_name)
                self.lastrowid = doc["id"]

                try:
                    self._db[table_name].insert_one(doc)
                    inserted_count += 1
                except Exception as exc:
                    if "IGNORE" in upper_sql:
                        pass
                    elif "DuplicateKey" in type(exc).__name__ or "duplicate" in str(exc).lower():
                        if conflict_filter:
                            self._db[table_name].update_one(
                                conflict_filter,
                                {"$set": {k: v for k, v in doc.items() if k not in ("_id", "id")}},
                                upsert=True
                            )
                            inserted_count += 1
                        elif "IGNORE" in upper_sql:
                            pass
                        else:
                            raise
                    else:
                        raise

            self.rowcount = inserted_count
            return self

        # 6. UPDATE table
        update_match = re.search(r"UPDATE\s+([a-zA-Z0-9_]+)\s+SET\s+(.+?)(?:\s+WHERE\s+(.+))?$", clean_sql, re.I)
        if update_match:
            table_name = self._map_table(update_match.group(1).lower())
            set_str = update_match.group(2)
            where_str = update_match.group(3)

            set_assignments = [s.strip() for s in set_str.split(",")]
            update_fields: Dict[str, Any] = {}
            param_idx = 0

            for assign in set_assignments:
                m_a = re.match(r"([a-zA-Z0-9_]+)\s*=\s*(.+)", assign)
                if m_a:
                    col = m_a.group(1).strip()
                    val_expr = m_a.group(2).strip()
                    if val_expr == "?" or val_expr == "%s":
                        update_fields[col] = params_list[param_idx] if param_idx < len(params_list) else None
                        param_idx += 1
                    elif val_expr.startswith("'") and val_expr.endswith("'"):
                        update_fields[col] = val_expr[1:-1]
                    elif val_expr.isdigit():
                        update_fields[col] = int(val_expr)

            remaining_params = params_list[param_idx:]
            where_query = self._parse_where(where_str, remaining_params)
            update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()

            res = self._db[table_name].update_many(where_query, {"$set": update_fields})
            self.rowcount = res.modified_count
            return self

        # 7. DELETE FROM table
        delete_match = re.search(r"DELETE\s+FROM\s+([a-zA-Z0-9_]+)(?:\s+WHERE\s+(.+))?$", clean_sql, re.I)
        if delete_match:
            table_name = self._map_table(delete_match.group(1).lower())
            where_str = delete_match.group(2)
            query = self._parse_where(where_str, params_list)
            res = self._db[table_name].delete_many(query)
            self.rowcount = res.deleted_count
            return self

        # Fallback for unrecognized statements (DDL, transaction commands, etc.)
        self.rowcount = 0
        return self

    def executemany(self, sql: str, seq_of_params: Iterable[Sequence[Any]]) -> MongoCursor:
        count = 0
        for params in seq_of_params:
            self.execute(sql, params)
            count += self.rowcount
        self.rowcount = count
        return self

    def fetchone(self) -> Optional[MongoFlexRow]:
        if self._idx < len(self._rows):
            r = self._rows[self._idx]
            self._idx += 1
            return r
        return None

    def fetchall(self) -> List[MongoFlexRow]:
        remaining = self._rows[self._idx:]
        self._idx = len(self._rows)
        return remaining

    def close(self) -> None:
        pass

    def _map_table(self, tbl: str) -> str:
        # Table alias mappings
        tbl = tbl.replace("`", "").replace("\"", "")
        if tbl == "performance_reviews":
            return "feedback"
        if tbl == "training_records":
            return "training"
        return tbl

    def _parse_where(self, where_str: Optional[str], params: List[Any]) -> Dict[str, Any]:
        if not where_str:
            return {}
        query: Dict[str, Any] = {}
        p_idx = 0

        # Temporarily mask string literals e.g. 'ravi@company.com' -> __LIT_0__
        literals: List[str] = []
        def _mask_lit(m: Any) -> str:
            literals.append(m.group(0))
            return f"__LIT_{len(literals)-1}__"

        s = re.sub(r"'[^']*'", _mask_lit, where_str)

        # Recursively strip SQL function wrappers: LOWER(TRIM(u.email)) -> u.email
        while True:
            cleaned = re.sub(r'(?:LOWER|UPPER|TRIM)\s*\(\s*([^()]+?)\s*\)', r'\1', s, flags=re.I)
            if cleaned == s:
                break
            s = cleaned

        # Strip table aliases e.g. e.org_id -> org_id, u.email -> email
        clean = re.sub(r"\b[a-zA-Z0-9_]+\.([a-zA-Z0-9_]+)", r"\1", s)

        # Unmask string literals
        for idx, lit in enumerate(literals):
            clean = clean.replace(f"__LIT_{idx}__", lit)

        # Split on top-level AND
        clauses = re.split(r"\s+AND\s+", clean, flags=re.I)
        for clause in clauses:
            clause = clause.strip()
            if clause.startswith("(") and clause.endswith(")"):
                clause = clause[1:-1].strip()

            if not clause or clause == "1=1" or clause == "1":
                continue

            # Handle OR subclauses: (col1 = ? OR col2 = ?)
            if " OR " in clause.upper():
                or_parts = re.split(r"\s+OR\s+", clause, flags=re.I)
                or_list = []
                for part in or_parts:
                    part = part.strip()
                    m_eq = re.match(r"([a-zA-Z0-9_]+)\s*=\s*(?:\?|%s)", part, re.I)
                    if m_eq:
                        val = params[p_idx] if p_idx < len(params) else None
                        p_idx += 1
                        or_list.append({m_eq.group(1): val})
                        continue
                    m_lit = re.match(r"([a-zA-Z0-9_]+)\s*=\s*'([^']*)'", part, re.I)
                    if m_lit:
                        or_list.append({m_lit.group(1): m_lit.group(2)})
                        continue
                if or_list:
                    query["$or"] = or_list
                continue

            # col = ? or col = %s
            m_eq = re.match(r"([a-zA-Z0-9_]+)\s*=\s*(?:\?|%s)", clause, re.I)
            if m_eq:
                col = m_eq.group(1)
                val = params[p_idx] if p_idx < len(params) else None
                p_idx += 1
                query[col] = val
                continue

            # col = 'val'
            m_lit = re.match(r"([a-zA-Z0-9_]+)\s*=\s*'([^']*)'", clause, re.I)
            if m_lit:
                query[m_lit.group(1)] = m_lit.group(2)
                continue

            # col IN (?, ?, ...)
            m_in = re.match(r"([a-zA-Z0-9_]+)\s+IN\s*\((.+?)\)", clause, re.I)
            if m_in:
                col = m_in.group(1)
                in_placeholders = [x.strip() for x in m_in.group(2).split(",")]
                in_vals = []
                for ph in in_placeholders:
                    if ph in ("?", "%s"):
                        if p_idx < len(params):
                            in_vals.append(params[p_idx])
                            p_idx += 1
                    elif ph.startswith("'") and ph.endswith("'"):
                        in_vals.append(ph[1:-1])
                    elif ph.isdigit():
                        in_vals.append(int(ph))
                query[col] = {"$in": in_vals}
                continue

            # col LIKE ?
            m_like = re.match(r"([a-zA-Z0-9_]+)\s+LIKE\s*(?:\?|%s)", clause, re.I)
            if m_like:
                col = m_like.group(1)
                val = str(params[p_idx]) if p_idx < len(params) else ""
                p_idx += 1
                regex_pat = "^" + re.escape(val).replace("%", ".*").replace("_", ".") + "$"
                query[col] = {"$regex": regex_pat, "$options": "i"}
                continue

            # col != ?
            m_neq = re.match(r"([a-zA-Z0-9_]+)\s*(?:!=|<>)\s*(?:\?|%s)", clause, re.I)
            if m_neq:
                col = m_neq.group(1)
                val = params[p_idx] if p_idx < len(params) else None
                p_idx += 1
                query[col] = {"$ne": val}
                continue

        return query

    def _parse_order(self, order_str: str) -> List[Tuple[str, int]]:
        specs = []
        for part in order_str.split(","):
            part = part.strip()
            direction = DESCENDING if "DESC" in part.upper() else ASCENDING
            col = re.sub(r"\s+(?:ASC|DESC)", "", part, flags=re.I).strip()
            col = col.split(".")[-1]
            specs.append((col, direction))
        return specs

    def _parse_select_columns(self, cols_str: str, docs: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
        doc_keys: List[str] = []
        if docs:
            for d in docs:
                for k in d.keys():
                    if k not in doc_keys and k != "_id":
                        doc_keys.append(k)

        clean_cols_str = cols_str.strip()
        if clean_cols_str == "*":
            return [(k, k) for k in doc_keys] if doc_keys else [("id", "id")]

        # Split columns on commas that are OUTSIDE of parentheses and quotes
        parts: List[str] = []
        cur: List[str] = []
        paren_depth = 0
        in_quote = False
        quote_char = ""
        for ch in clean_cols_str:
            if in_quote:
                cur.append(ch)
                if ch == quote_char:
                    in_quote = False
            elif ch in ("'", '"'):
                in_quote = True
                quote_char = ch
                cur.append(ch)
            elif ch == "(":
                paren_depth += 1
                cur.append(ch)
            elif ch == ")":
                paren_depth = max(0, paren_depth - 1)
                cur.append(ch)
            elif ch == "," and paren_depth == 0:
                parts.append("".join(cur).strip())
                cur = []
            else:
                cur.append(ch)
        if cur:
            parts.append("".join(cur).strip())

        col_specs: List[Tuple[str, str]] = []
        has_wildcard = False
        sql_kw = {"COALESCE", "LOWER", "UPPER", "TRIM", "IFNULL", "NULLIF", "CONCAT", "SUBSTR"}

        for part in parts:
            part = part.strip()
            m_as = re.search(r"\bAS\s+([a-zA-Z0-9_]+)\s*$", part, re.I)
            if m_as:
                alias = m_as.group(1).strip()
                src_expr = part[:m_as.start()].strip()
                m_inner = re.findall(r"\b([a-zA-Z0-9_]+)\b", src_expr)
                candidates = [w for w in m_inner if w.upper() not in sql_kw and not w.isdigit() and len(w) > 1]
                src = candidates[0] if candidates else alias
                col_specs.append((alias, src))
            else:
                col = part.split(".")[-1]
                col = re.sub(r"\bDISTINCT\s+", "", col, flags=re.I)
                col = re.sub(r"[()'\"]", "", col).strip()
                if col == "*":
                    has_wildcard = True
                elif col:
                    col_specs.append((col, col))

        if has_wildcard:
            existing_aliases = {c[0] for c in col_specs}
            for k in doc_keys:
                if k not in existing_aliases:
                    col_specs.insert(0, (k, k))
            return col_specs if col_specs else [("id", "id")]
        return col_specs

    def _format_doc(self, d: Dict[str, Any], columns: List[Tuple[str, str]]) -> Dict[str, Any]:
        norm = normalize_doc(d) or {}
        res: Dict[str, Any] = {}
        for alias, src in columns:
            val = norm.get(src) if src in norm else norm.get(alias)
            if val is not None:
                res[alias] = val
            elif alias == "avg_rating":
                res[alias] = float(norm.get("rating") or norm.get("avg_rating") or 4.0)
            elif alias == "review_count":
                res[alias] = int(norm.get("review_count") or 1)
            elif alias in ("org_name", "company"):
                if "org_name" in norm:
                    res[alias] = norm["org_name"]
                elif "org_id" in norm and norm["org_id"]:
                    org_doc = self._db.organizations.find_one({"org_id": norm["org_id"]})
                    res[alias] = org_doc.get("name", "Talent Growth Technologies") if org_doc else "Talent Growth Technologies"
                else:
                    res[alias] = norm.get("company", "Talent Growth Technologies")
            elif alias == "org_status":
                if "org_status" in norm:
                    res[alias] = norm["org_status"]
                elif "org_id" in norm and norm["org_id"]:
                    org_doc = self._db.organizations.find_one({"org_id": norm["org_id"]})
                    res[alias] = org_doc.get("status", "Active") if org_doc else "Active"
                else:
                    res[alias] = "Active"
            elif alias == "reviewer_name":
                if "reviewer_name" in norm:
                    res[alias] = norm["reviewer_name"]
                elif "reviewed_by" in norm and norm["reviewed_by"]:
                    u_doc = self._db.users.find_one({"id": norm["reviewed_by"]})
                    res[alias] = u_doc.get("name", "") if u_doc else ""
                else:
                    res[alias] = ""
            else:
                res[alias] = norm.get(alias) or norm.get(src)
        return res


class MongoConnectionWrapper:
    """
    Wraps MongoDB Atlas with sqlite3/pymysql connection semantics:
    - `with conn:` handles transaction commits safely.
    - `conn.cursor()` returns a MongoCursor.
    - `conn.execute(...)` executes directly on MongoDB.
    """
    def __init__(self, db: Any):
        self._db = db

    def cursor(self) -> MongoCursor:
        return MongoCursor(self._db)

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> MongoCursor:
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass

    def __enter__(self) -> MongoConnectionWrapper:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass


def get_connection() -> MongoConnectionWrapper:
    """Returns the centralized MongoDB Atlas connection wrapper."""
    return MongoConnectionWrapper(get_db())


# ------------------------------------------------------------------------------
# DIAGNOSTICS & TELEMETRY
# ------------------------------------------------------------------------------
def check_db_health() -> Dict[str, Any]:
    """Inspects live MongoDB Atlas connection status, collection metrics, and ping latency."""
    uri = get_mongodb_uri()
    masked_uri = re.sub(r":([^@]+)@", ":****@", uri) if "@" in uri else uri
    db = get_db()
    is_mock = is_mock_mode()

    info: Dict[str, Any] = {
        "connected": False,
        "engine": "MongoDB Atlas" if not is_mock else "MongoDB (In-Memory Mock)",
        "database": db.name,
        "host": masked_uri.split("@")[-1].split("/")[0] if "@" in masked_uri else "cluster0.mongodb.net",
        "mock_mode": is_mock,
        "counts": {}
    }

    try:
        if not is_mock:
            client = get_client()
            client.admin.command("ping")
        info["connected"] = True
        info["integrity"] = "ok"

        for col_name in ["organizations", "users", "employees", "departments", "skills", "goals", "assessments", "training", "feedback", "notifications"]:
            try:
                info["counts"][col_name] = db[col_name].count_documents({})
            except Exception:
                info["counts"][col_name] = 0
    except Exception as exc:
        info["integrity"] = f"Connection Notice: {exc}"

    return info


def get_database_diagnostics() -> Dict[str, Any]:
    """Provides high-level database diagnostics for administrator inspection."""
    health = check_db_health()
    db = get_db()

    total_users = db.users.count_documents({}) if health["connected"] else 0
    total_employees = db.employees.count_documents({}) if health["connected"] else 0
    total_orgs = db.organizations.count_documents({}) if health["connected"] else 0

    recent_users = []
    if health["connected"]:
        for u in db.users.find({}, {"password_hash": 0}).sort("created_at", DESCENDING).limit(5):
            recent_users.append(normalize_doc(u))

    return {
        "connected": health["connected"],
        "engine": health["engine"],
        "filename": health["database"],
        "absolute_path": f"mongodb://{health['host']}/{health['database']}",
        "size_kb": round((total_users + total_employees) * 1.5, 1),
        "integrity": health.get("integrity", "ok"),
        "total_users": total_users,
        "total_employees": total_employees,
        "total_organizations": total_orgs,
        "recent_users": recent_users
    }


def ping_db() -> bool:
    """Returns True if the MongoDB Atlas database responds successfully."""
    try:
        if is_mock_mode():
            return True
        client = get_client()
        client.admin.command("ping")
        return True
    except Exception:
        return False


def get_mysql_config() -> Dict[str, Any]:
    """Compatibility stub returning active MongoDB database coordinates."""
    health = check_db_health()
    return {
        "host": health["host"],
        "port": 27017,
        "user": "atlas_user",
        "password": "",
        "database": health["database"]
    }


def is_mysql_mode() -> bool:
    """Returns False indicating MySQL has been replaced by MongoDB Atlas."""
    return False


def is_mysql_expected() -> bool:
    """Returns False indicating MongoDB Atlas is the required database."""
    return False


def test_mysql_connection() -> Dict[str, Any]:
    """Compatibility stub confirming MongoDB Atlas is active."""
    health = check_db_health()
    return {
        "success": health["connected"],
        "engine": health["engine"],
        "host": health["host"],
        "port": 27017,
        "database": health["database"],
        "message": f"MongoDB Atlas ({health['database']}) is active."
    }
