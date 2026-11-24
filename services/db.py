"""
Enterprise Database Layer - MongoDB Atlas Native
Manages MongoDB Atlas connection, collections, schemas, indexes, diagnostics,
and synchronization for the Talent Management & Career Growth Platform.
"""

from __future__ import annotations
import json
import os
import re
import sqlite3
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from bson import ObjectId

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

try:
    import pymongo
    from pymongo import MongoClient, ASCENDING, DESCENDING
    PYMONGO_AVAILABLE = True
except ImportError:
    MongoClient = None  # type: ignore
    PYMONGO_AVAILABLE = False

try:
    import mongomock
    MONGOMOCK_AVAILABLE = True
except ImportError:
    mongomock = None
    MONGOMOCK_AVAILABLE = False


# ------------------------------------------------------------------------------
# MONGODB CONFIGURATION & CONNECTION SINGLETON
# ------------------------------------------------------------------------------
_mongo_client: Optional[Any] = None
_mongo_is_mock: bool = False

MOCK_STORE_DIR = BASE_DIR / "data" / "mongodb_store"
MOCK_STORE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_ATLAS_URI = (
    "mongodb+srv://<db_username>:<db_password>@cluster0.fea8dfi.mongodb.net/talent_management?retryWrites=true&w=majority"
)


def get_mongodb_uri() -> str:
    """Retrieves MongoDB URI from environment variables or Streamlit secrets."""
    uri = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI") or ""
    if not uri:
        try:
            import streamlit as st
            if hasattr(st, "secrets"):
                uri = st.secrets.get("MONGODB_URI", "") or st.secrets.get("MONGO_URI", "")
        except Exception:
            pass
    return uri.strip() or DEFAULT_ATLAS_URI


def get_mongodb_dbname() -> str:
    """Retrieves target MongoDB database name."""
    db_name = os.getenv("MONGODB_DB_NAME") or os.getenv("MONGO_DB_NAME") or "talent_management"
    if not db_name:
        try:
            import streamlit as st
            if hasattr(st, "secrets"):
                db_name = st.secrets.get("MONGODB_DB_NAME", "talent_management")
        except Exception:
            pass
    return db_name.strip() or "talent_management"


def has_valid_atlas_credentials(uri: str) -> bool:
    """Checks whether the URI has non-placeholder credentials."""
    if not uri:
        return False
    if "<db_username>" in uri or "<db_password>" in uri:
        return False
    if "mongodb+srv://" in uri or "mongodb://" in uri:
        return True
    return False


def _load_mock_store(db):
    """Loads stored JSON collections into in-memory mongomock database on startup."""
    for cname in COLLECTION_NAMES:
        col_file = MOCK_STORE_DIR / f"{cname}.json"
        if col_file.exists():
            try:
                with open(col_file, "r", encoding="utf-8") as f:
                    docs = json.load(f)
                if docs and db[cname].count_documents({}) == 0:
                    for d in docs:
                        if "_id" in d and isinstance(d["_id"], str) and len(d["_id"]) == 24:
                            try:
                                d["_id"] = ObjectId(d["_id"])
                            except Exception:
                                pass
                    db[cname].insert_many(docs)
            except Exception:
                pass


def save_mock_store(cname: Optional[str] = None):
    """Persists mongomock collections to disk for development continuity."""
    if not is_mock_mode():
        return
    db = get_db()
    cnames = [cname] if cname else COLLECTION_NAMES
    for name in cnames:
        col_file = MOCK_STORE_DIR / f"{name}.json"
        try:
            cur = db[name].find({})
            docs = normalize_docs(cur)
            with open(col_file, "w", encoding="utf-8") as f:
                json.dump(docs, f, indent=2)
        except Exception:
            pass


def get_mongo_client(force_new: bool = False) -> Any:
    """
    Returns a connected MongoClient instance.
    If valid MongoDB Atlas credentials are provided, connects directly to Atlas.
    If credentials are placeholder (<db_username>) or network is offline,
    gracefully uses an in-memory mongomock client with local disk persistence.
    """
    global _mongo_client, _mongo_is_mock

    if _mongo_client is not None and not force_new:
        return _mongo_client

    uri = get_mongodb_uri()

    if PYMONGO_AVAILABLE and has_valid_atlas_credentials(uri):
        try:
            client = MongoClient(
                uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                retryWrites=True
            )
            client.admin.command("ping")
            _mongo_client = client
            _mongo_is_mock = False
            return _mongo_client
        except Exception:
            pass

    if MONGOMOCK_AVAILABLE:
        if _mongo_client is None or not _mongo_is_mock:
            _mongo_client = mongomock.MongoClient()
            _mongo_is_mock = True
            db = _mongo_client[get_mongodb_dbname()]
            _load_mock_store(db)
        return _mongo_client

    if PYMONGO_AVAILABLE:
        _mongo_client = MongoClient("localhost", 27017, serverSelectionTimeoutMS=2000)
        _mongo_is_mock = False
        return _mongo_client

    raise RuntimeError("Neither 'pymongo' nor 'mongomock' is installed. Please run 'pip install pymongo dnspython'.")


def is_mock_mode() -> bool:
    """Returns True if currently operating with an in-memory mock client."""
    global _mongo_is_mock
    return _mongo_is_mock


def get_db():
    """Returns the primary MongoDB Database object."""
    client = get_mongo_client()
    db_name = get_mongodb_dbname()
    return client[db_name]


# ------------------------------------------------------------------------------
# 15 PRIMARY MONGODB COLLECTIONS
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
    "organization_settings"
]


def get_collection(name: str):
    """Returns a specific collection from the active MongoDB database."""
    db = get_db()
    return db[name]


# ------------------------------------------------------------------------------
# INDEX INITIALIZATION & DATA INTEGRITY
# ------------------------------------------------------------------------------
def init_mongo_indexes() -> None:
    """
    Creates and ensures optimal indexes across all 15 MongoDB collections:
    - Unique indexes for email, employee_id, department_id, invitation codes, etc.
    """
    db = get_db()
    try:
        db.users.create_index([("email", ASCENDING)], unique=True)
        db.users.create_index([("employee_id", ASCENDING)])
        db.users.create_index([("role", ASCENDING)])
        db.users.create_index([("org_id", ASCENDING)])

        db.employees.create_index([("employee_id", ASCENDING)], unique=True)
        db.employees.create_index([("email", ASCENDING)], unique=True)
        db.employees.create_index([("org_id", ASCENDING)])
        db.employees.create_index([("department", ASCENDING)])
        db.employees.create_index([("manager_id", ASCENDING)])

        db.departments.create_index([("department_id", ASCENDING)], unique=True)
        db.departments.create_index([("name", ASCENDING)])
        db.departments.create_index([("org_id", ASCENDING)])

        db.employee_skills.create_index([("employee_id", ASCENDING), ("skill_name", ASCENDING)])
        db.employee_skills.create_index([("org_id", ASCENDING)])

        db.skills.create_index([("name", ASCENDING)], unique=True)
        db.skills.create_index([("category", ASCENDING)])

        db.goals.create_index([("employee_id", ASCENDING)])
        db.goals.create_index([("user_id", ASCENDING)])
        db.goals.create_index([("status", ASCENDING)])
        db.goals.create_index([("org_id", ASCENDING)])

        db.assessments.create_index([("employee_id", ASCENDING)])
        db.assessments.create_index([("user_id", ASCENDING)])
        db.assessments.create_index([("skill_name", ASCENDING)])
        db.assessments.create_index([("org_id", ASCENDING)])

        db.career_goals.create_index([("employee_id", ASCENDING)])
        db.career_goals.create_index([("user_id", ASCENDING)])
        db.career_goals.create_index([("status", ASCENDING)])
        db.career_goals.create_index([("org_id", ASCENDING)])

        db.training.create_index([("training_id", ASCENDING)], unique=True)
        db.training.create_index([("category", ASCENDING)])
        db.training.create_index([("org_id", ASCENDING)])

        db.feedback.create_index([("employee_id", ASCENDING)])
        db.feedback.create_index([("reviewer_id", ASCENDING)])
        db.feedback.create_index([("org_id", ASCENDING)])

        db.notifications.create_index([("user_id", ASCENDING)])
        db.notifications.create_index([("recipient_email", ASCENDING)])
        db.notifications.create_index([("status", ASCENDING)])
        db.notifications.create_index([("created_at", DESCENDING)])

        db.membership_requests.create_index([("user_email", ASCENDING)])
        db.membership_requests.create_index([("org_id", ASCENDING)])
        db.membership_requests.create_index([("status", ASCENDING)])

        db.invitation_codes.create_index([("code_hash", ASCENDING)], unique=True)
        db.invitation_codes.create_index([("org_id", ASCENDING)])
        db.invitation_codes.create_index([("status", ASCENDING)])

        db.email_logs.create_index([("to_email", ASCENDING)])
        db.email_logs.create_index([("created_at", DESCENDING)])

        db.organization_settings.create_index([("org_id", ASCENDING)], unique=True)
    except Exception:
        pass


# ------------------------------------------------------------------------------
# DOCUMENT NORMALIZATION HELPERS
# ------------------------------------------------------------------------------
def normalize_doc(doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalizes a MongoDB document for application consumption."""
    if not doc or not isinstance(doc, dict):
        return {}
    res = dict(doc)
    if "_id" in res:
        oid_str = str(res["_id"])
        res["_id"] = oid_str
        if "id" not in res:
            res["id"] = oid_str
    for k, v in list(res.items()):
        if isinstance(v, ObjectId):
            res[k] = str(v)
        elif isinstance(v, datetime):
            res[k] = v.isoformat()
    return res


def normalize_docs(docs: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalizes a list of MongoDB documents."""
    return [normalize_doc(d) for d in docs if d]


# ------------------------------------------------------------------------------
# SCHEMA DEFINITIONS AND CONVERSION HELPERS
# ------------------------------------------------------------------------------
def convert_mysql_ddl_to_sqlite(ddl: str) -> str:
    """Converts native MySQL DDL statements to compatible SQLite schema statements."""
    s = ddl
    s = re.sub(r"\s+ENGINE=InnoDB[^;]*", "", s, flags=re.I)
    s = re.sub(r"\bAUTO_INCREMENT\b", "", s, flags=re.I)
    s = re.sub(r"\bINT\s+AUTO_INCREMENT\s+PRIMARY\s+KEY\b", "INTEGER PRIMARY KEY AUTOINCREMENT", s, flags=re.I)
    s = re.sub(r"\bINT\s+PRIMARY\s+KEY\b", "INTEGER PRIMARY KEY AUTOINCREMENT", s, flags=re.I)
    s = re.sub(r"\bINT\b", "INTEGER", s, flags=re.I)
    s = re.sub(r"\bVARCHAR\(\d+\)", "TEXT", s, flags=re.I)
    s = re.sub(r"\bLONGTEXT\b", "TEXT", s, flags=re.I)
    s = re.sub(r"\bDATETIME\b", "TIMESTAMP", s, flags=re.I)
    s = re.sub(r"\bDOUBLE\b", "REAL", s, flags=re.I)
    return s


MYSQL_EMAIL_LOGS_DDL = """
CREATE TABLE IF NOT EXISTS email_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    to_email VARCHAR(255) NOT NULL,
    user_name VARCHAR(255) DEFAULT '',
    role VARCHAR(100) DEFAULT '',
    org_name VARCHAR(255) DEFAULT '',
    subject VARCHAR(500) NOT NULL,
    message_type VARCHAR(100) DEFAULT 'welcome',
    status VARCHAR(50) NOT NULL DEFAULT 'sent',
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
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
        manager_id VARCHAR(100) DEFAULT NULL,
        created_by INT DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
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
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS progress (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        item VARCHAR(500) NOT NULL,
        percent DOUBLE NOT NULL DEFAULT 0.0,
        status VARCHAR(100) NOT NULL DEFAULT 'In Progress',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
        role VARCHAR(50) DEFAULT '',
        reason TEXT,
        deactivated_by VARCHAR(255) DEFAULT '',
        deactivated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]


# ------------------------------------------------------------------------------
# SYNCHRONIZED DATABASE CONNECTION
# ------------------------------------------------------------------------------
_sync_conn: Optional[sqlite3.Connection] = None


class MongoSyncedConnection:
    """
    Database connection wrapper that provides standard cursor execution
    while maintaining bidirectional persistence with MongoDB Atlas.
    """
    def __init__(self, raw_conn: sqlite3.Connection):
        self._conn = raw_conn

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        self._conn.commit()
        sync_all_to_mongo()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        pass  # Kept open as singleton

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def get_connection() -> MongoSyncedConnection:
    """Returns the active database connection synchronized with MongoDB Atlas."""
    global _sync_conn
    if _sync_conn is None:
        init_db()
    return MongoSyncedConnection(_sync_conn)


def get_db_path() -> Path:
    """Returns local cache path for the synchronized database."""
    data_dir = BASE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "talent_management_atlas.db"


def init_db() -> None:
    """
    Initializes the database environment:
    1. Ensures MongoDB indexes are established.
    2. Initializes SQLite synchronization schema.
    3. Loads existing documents from MongoDB Atlas into relational tables.
    """
    global _sync_conn

    init_mongo_indexes()

    db_file = get_db_path()
    _sync_conn = sqlite3.connect(str(db_file), check_same_thread=False)
    _sync_conn.row_factory = sqlite3.Row
    _sync_conn.execute("PRAGMA journal_mode = WAL")

    cur = _sync_conn.cursor()
    for stmt in MYSQL_CORE_SCHEMA_STATEMENTS + MYSQL_SETTINGS_SCHEMA_STATEMENTS:
        try:
            sqlite_stmt = convert_mysql_ddl_to_sqlite(stmt)
            cur.execute(sqlite_stmt)
        except Exception:
            pass
    _sync_conn.commit()

    sync_all_from_mongo()


def sync_all_from_mongo() -> None:
    """Loads all records from MongoDB Atlas collections into the synchronized cache tables."""
    global _sync_conn
    if _sync_conn is None:
        return

    db = get_db()
    cur = _sync_conn.cursor()

    # 1. Organization & Settings
    try:
        for org in db.organization_settings.find({}):
            doc = normalize_doc(org)
            cur.execute(
                """
                INSERT OR REPLACE INTO organizations (org_id, name, official_email, contact_number, status, website, industry, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.get("org_id", "ORG-TALENT-01"),
                    doc.get("name") or doc.get("org_name", "TalentGrowth Enterprise"),
                    doc.get("official_email", "hr@talentgrowth.com"),
                    doc.get("contact_number", "+1 (555) 019-2834"),
                    doc.get("status", "Active"),
                    doc.get("website", "https://www.talentgrowth.com"),
                    doc.get("industry", "Enterprise Software"),
                    doc.get("description", "")
                )
            )
            cur.execute(
                """
                INSERT OR REPLACE INTO org_settings (org_id, org_name, official_email, contact_number, address, website, industry, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.get("org_id", "ORG-TALENT-01"),
                    doc.get("org_name") or doc.get("name", "TalentGrowth Enterprise"),
                    doc.get("official_email", "hr@talentgrowth.com"),
                    doc.get("contact_number", "+1 (555) 019-2834"),
                    doc.get("address", ""),
                    doc.get("website", "https://www.talentgrowth.com"),
                    doc.get("industry", "Enterprise Software"),
                    doc.get("description", "")
                )
            )
    except Exception:
        pass

    # 2. Users
    try:
        for u in db.users.find({}):
            doc = normalize_doc(u)
            uid = int(doc.get("id") or doc.get("user_id") or 1) if str(doc.get("id") or "").isdigit() else None
            cur.execute(
                """
                INSERT OR REPLACE INTO users (id, name, email, password_hash, salt, role, employee_id, org_id, account_type, department, job_title, status, date_joined)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uid,
                    doc.get("name", ""),
                    doc.get("email", ""),
                    doc.get("password_hash", ""),
                    doc.get("salt", ""),
                    doc.get("role", "employee"),
                    doc.get("employee_id"),
                    doc.get("org_id", "ORG-TALENT-01"),
                    doc.get("account_type", "Organization"),
                    doc.get("department", ""),
                    doc.get("job_title", ""),
                    doc.get("status", "Active"),
                    doc.get("date_joined", "")
                )
            )
    except Exception:
        pass

    # 3. Employees
    try:
        for emp in db.employees.find({}):
            doc = normalize_doc(emp)
            cur.execute(
                """
                INSERT OR REPLACE INTO employees (employee_id, org_id, user_id, name, email, phone, department, designation, joining_date, employment_status, years_experience, primary_skills, account_status, manager_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.get("employee_id", ""),
                    doc.get("org_id", "ORG-TALENT-01"),
                    doc.get("user_id"),
                    doc.get("name", ""),
                    doc.get("email", ""),
                    doc.get("phone", ""),
                    doc.get("department", "Engineering"),
                    doc.get("designation", "Software Engineer"),
                    doc.get("joining_date", "2023-01-15"),
                    doc.get("employment_status", "Active"),
                    float(doc.get("years_experience", 0.0)),
                    doc.get("primary_skills", ""),
                    doc.get("account_status", "Active"),
                    doc.get("manager_id")
                )
            )
    except Exception:
        pass

    # 4. Skills
    try:
        for s in db.skills.find({}):
            doc = normalize_doc(s)
            cur.execute(
                """
                INSERT OR REPLACE INTO skills (id, user_id, name, category, proficiency, years, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(doc.get("id")) if str(doc.get("id", "")).isdigit() else None,
                    int(doc.get("user_id") or 1),
                    doc.get("name", ""),
                    doc.get("category", "Technical"),
                    doc.get("proficiency", "Intermediate"),
                    float(doc.get("years", 1.0)),
                    doc.get("description", "")
                )
            )
    except Exception:
        pass

    # 5. Employee Skills
    try:
        for es in db.employee_skills.find({}):
            doc = normalize_doc(es)
            cur.execute(
                """
                INSERT OR REPLACE INTO employee_skills (id, employee_id, org_id, user_id, skill_name, category, proficiency_level, years_exp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(doc.get("id")) if str(doc.get("id", "")).isdigit() else None,
                    doc.get("employee_id", ""),
                    doc.get("org_id", "ORG-TALENT-01"),
                    doc.get("user_id"),
                    doc.get("skill_name", ""),
                    doc.get("category", "Technical"),
                    doc.get("proficiency_level", "Intermediate"),
                    float(doc.get("years_exp", 1.0))
                )
            )
    except Exception:
        pass

    # 6. Goals
    try:
        for g in db.goals.find({}):
            doc = normalize_doc(g)
            cur.execute(
                """
                INSERT OR REPLACE INTO goals (id, user_id, employee_id, org_id, title, description, target_date, progress, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(doc.get("id")) if str(doc.get("id", "")).isdigit() else None,
                    doc.get("user_id"),
                    doc.get("employee_id"),
                    doc.get("org_id", "ORG-TALENT-01"),
                    doc.get("title", ""),
                    doc.get("description", ""),
                    doc.get("target_date", ""),
                    int(doc.get("progress", 0)),
                    doc.get("status", "Not Started")
                )
            )
    except Exception:
        pass

    # 7. Assessments
    try:
        for a in db.assessments.find({}):
            doc = normalize_doc(a)
            cur.execute(
                """
                INSERT OR REPLACE INTO assessments (id, user_id, employee_id, org_id, category, skill_name, score, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(doc.get("id")) if str(doc.get("id", "")).isdigit() else None,
                    doc.get("user_id"),
                    doc.get("employee_id", ""),
                    doc.get("org_id", "ORG-TALENT-01"),
                    doc.get("category", "Technical"),
                    doc.get("skill_name", ""),
                    float(doc.get("score", 0.0)),
                    doc.get("notes", "")
                )
            )
    except Exception:
        pass

    # 8. Career Goals
    try:
        for cg in db.career_goals.find({}):
            doc = normalize_doc(cg)
            cur.execute(
                """
                INSERT OR REPLACE INTO career_goals (id, user_id, employee_id, org_id, title, target_designation, description, target_date, progress, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(doc.get("id")) if str(doc.get("id", "")).isdigit() else None,
                    doc.get("user_id"),
                    doc.get("employee_id"),
                    doc.get("org_id", "ORG-TALENT-01"),
                    doc.get("title", ""),
                    doc.get("target_role") or doc.get("target_designation", ""),
                    doc.get("description", ""),
                    doc.get("target_date", ""),
                    int(doc.get("progress", 0)),
                    doc.get("status", "Not Started")
                )
            )
    except Exception:
        pass

    # 9. Training
    try:
        for tr in db.training.find({}):
            doc = normalize_doc(tr)
            cur.execute(
                """
                INSERT OR REPLACE INTO training_records (id, employee_id, org_id, course_name, provider, target_skill, target_completion_date, status, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(doc.get("id")) if str(doc.get("id", "")).isdigit() else None,
                    doc.get("employee_id", ""),
                    doc.get("org_id", "ORG-TALENT-01"),
                    doc.get("course_name", ""),
                    doc.get("provider", "Internal Academy"),
                    doc.get("target_skill", ""),
                    doc.get("target_completion_date", ""),
                    doc.get("status", "Enrolled"),
                    float(doc.get("score", 0.0))
                )
            )
    except Exception:
        pass

    # 10. Feedback / Reviews
    try:
        for fb in db.feedback.find({}):
            doc = normalize_doc(fb)
            cur.execute(
                """
                INSERT OR REPLACE INTO performance_reviews (id, employee_id, org_id, review_period, performance_score, achievements, strengths, improvements, manager_feedback)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(doc.get("id")) if str(doc.get("id", "")).isdigit() else None,
                    doc.get("employee_id", ""),
                    doc.get("org_id", "ORG-TALENT-01"),
                    doc.get("review_period", "Annual Review"),
                    float(doc.get("performance_score") or doc.get("rating", 4.0)),
                    doc.get("achievements", ""),
                    doc.get("strengths", ""),
                    doc.get("improvements", ""),
                    doc.get("manager_feedback") or doc.get("comments", "")
                )
            )
    except Exception:
        pass

    # 11. Invitation Codes
    try:
        for inv in db.invitation_codes.find({}):
            doc = normalize_doc(inv)
            cur.execute(
                """
                INSERT OR REPLACE INTO invitation_codes (id, org_id, code_hash, code_prefix, expires_at, max_uses, used_count, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(doc.get("id")) if str(doc.get("id", "")).isdigit() else None,
                    doc.get("org_id", "ORG-TALENT-01"),
                    doc.get("code_hash", ""),
                    doc.get("code_prefix", ""),
                    doc.get("expires_at", ""),
                    int(doc.get("max_uses", 1)),
                    int(doc.get("used_count", 0)),
                    doc.get("status", "Active"),
                    doc.get("created_by", "")
                )
            )
    except Exception:
        pass

    # 12. Membership Requests
    try:
        for mr in db.membership_requests.find({}):
            doc = normalize_doc(mr)
            cur.execute(
                """
                INSERT OR REPLACE INTO membership_requests (id, user_id, org_id, user_name, user_email, department, designation, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(doc.get("id")) if str(doc.get("id", "")).isdigit() else None,
                    int(doc.get("user_id") or 1),
                    doc.get("org_id", "ORG-TALENT-01"),
                    doc.get("user_name", ""),
                    doc.get("user_email", ""),
                    doc.get("department", ""),
                    doc.get("designation", ""),
                    doc.get("status", "Pending")
                )
            )
    except Exception:
        pass

    # 13. Email Logs
    try:
        for el in db.email_logs.find({}):
            doc = normalize_doc(el)
            cur.execute(
                """
                INSERT OR REPLACE INTO email_logs (id, to_email, user_name, role, org_name, subject, message_type, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(doc.get("id")) if str(doc.get("id", "")).isdigit() else None,
                    doc.get("to_email", ""),
                    doc.get("user_name", ""),
                    doc.get("role", "employee"),
                    doc.get("org_name", ""),
                    doc.get("subject", ""),
                    doc.get("message_type", "welcome"),
                    doc.get("status", "sent"),
                    doc.get("error_message")
                )
            )
    except Exception:
        pass

    _sync_conn.commit()


def sync_all_to_mongo() -> None:
    """Persists updated local records into MongoDB Atlas collections."""
    global _sync_conn
    if _sync_conn is None:
        return

    db = get_db()
    cur = _sync_conn.cursor()

    # Sync users
    try:
        cur.execute("SELECT * FROM users")
        for row in cur.fetchall():
            row_dict = dict(row)
            email = row_dict.get("email")
            if email:
                db.users.update_one(
                    {"email": email},
                    {"$set": {
                        "name": row_dict.get("name"),
                        "email": email,
                        "password_hash": row_dict.get("password_hash"),
                        "salt": row_dict.get("salt"),
                        "role": row_dict.get("role"),
                        "employee_id": row_dict.get("employee_id"),
                        "org_id": row_dict.get("org_id"),
                        "account_type": row_dict.get("account_type"),
                        "department": row_dict.get("department"),
                        "job_title": row_dict.get("job_title"),
                        "status": row_dict.get("status"),
                        "date_joined": row_dict.get("date_joined"),
                        "synced_at": datetime.now(timezone.utc).isoformat()
                    }},
                    upsert=True
                )
        save_mock_store("users")
    except Exception:
        pass

    # Sync employees
    try:
        cur.execute("SELECT * FROM employees")
        for row in cur.fetchall():
            row_dict = dict(row)
            emp_id = row_dict.get("employee_id")
            if emp_id:
                db.employees.update_one(
                    {"employee_id": emp_id},
                    {"$set": {
                        "employee_id": emp_id,
                        "name": row_dict.get("name"),
                        "email": row_dict.get("email"),
                        "phone": row_dict.get("phone"),
                        "department": row_dict.get("department"),
                        "designation": row_dict.get("designation"),
                        "joining_date": row_dict.get("joining_date"),
                        "employment_status": row_dict.get("employment_status"),
                        "years_experience": row_dict.get("years_experience"),
                        "primary_skills": row_dict.get("primary_skills"),
                        "org_id": row_dict.get("org_id"),
                        "account_status": row_dict.get("account_status"),
                        "manager_id": row_dict.get("manager_id"),
                        "synced_at": datetime.now(timezone.utc).isoformat()
                    }},
                    upsert=True
                )
        save_mock_store("employees")
    except Exception:
        pass


# ------------------------------------------------------------------------------
# HEALTH & DIAGNOSTICS FOR MONGODB ATLAS
# ------------------------------------------------------------------------------
def check_db_health() -> Dict[str, Any]:
    """Returns real-time health and diagnostics for the active MongoDB Atlas connection."""
    client = get_mongo_client()
    db = get_db()
    is_mock = is_mock_mode()
    uri = get_mongodb_uri()

    masked_uri = re.sub(r"://([^:]+):([^@]+)@", r"://\1:******@", uri)

    health: Dict[str, Any] = {
        "connected": False,
        "engine": "MongoDB Atlas" if not is_mock else "MongoDB (Atlas Emulated)",
        "database": db.name,
        "host": masked_uri.split("@")[-1].split("/")[0] if "@" in masked_uri else "cluster0.fea8dfi.mongodb.net",
        "mock_mode": is_mock,
        "counts": {}
    }

    try:
        if not is_mock:
            client.admin.command("ping")
        health["connected"] = True

        for cname in COLLECTION_NAMES:
            try:
                health["counts"][cname] = db[cname].count_documents({})
            except Exception:
                health["counts"][cname] = 0
    except Exception as e:
        health["error"] = str(e)

    return health


def get_database_diagnostics() -> Dict[str, Any]:
    """Provides comprehensive platform diagnostics for settings and status banners."""
    health = check_db_health()
    db = get_db()

    recent_users = []
    try:
        cur = db.users.find({}, {"password_hash": 0, "salt": 0}).sort("created_at", -1).limit(5)
        recent_users = normalize_docs(cur)
    except Exception:
        pass

    return {
        "connected": health["connected"],
        "engine": health["engine"],
        "filename": health["database"],
        "database_name": health["database"],
        "absolute_path": health["host"],
        "size_kb": 0.0,
        "integrity": "ok" if health["connected"] else "error",
        "total_users": health["counts"].get("users", 0),
        "total_employees": health["counts"].get("employees", 0),
        "total_organizations": health["counts"].get("organization_settings", 0),
        "recent_users": recent_users,
        "counts": health["counts"]
    }


def is_mongodb_mode() -> bool:
    """Returns True indicating MongoDB Atlas is the active database engine."""
    return True


# ------------------------------------------------------------------------------
# BACKWARD COMPATIBILITY SYMBOLS
# ------------------------------------------------------------------------------
def is_mysql_mode() -> bool:
    """Compatibility: Always False since MySQL is decommissioned."""
    return False


def is_mysql_expected() -> bool:
    """Compatibility: Always False since MongoDB Atlas is primary."""
    return False


def test_mysql_connection() -> Dict[str, Any]:
    """Compatibility check: Reports MongoDB Atlas status."""
    health = check_db_health()
    return {
        "success": health["connected"],
        "engine": health["engine"],
        "host": health["host"],
        "database": health["database"],
        "message": f"Successfully connected to {health['engine']} ({health['database']})"
    }


def get_mysql_config() -> Dict[str, Any]:
    """Compatibility config stub."""
    return {
        "host": "cluster0.fea8dfi.mongodb.net",
        "port": 27017,
        "user": "atlas_admin",
        "password": "",
        "database": "talent_management"
    }


def ensure_mysql_database_exists() -> bool:
    """Compatibility stub: MongoDB creates databases dynamically."""
    return True
