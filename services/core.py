from __future__ import annotations
import sys
import os
import re
import json
import sqlite3
import hashlib
import secrets
from io import BytesIO
from pathlib import Path
from datetime import datetime, date, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
_BASE_STR = str(BASE_DIR)
while _BASE_STR in sys.path:
    sys.path.remove(_BASE_STR)
sys.path.insert(0, _BASE_STR)

import pandas as pd
try:
    from services.email_service import send_welcome_email, get_recent_email_logs, send_test_email, get_email_config
except ImportError:
    from .email_service import send_welcome_email, get_recent_email_logs, send_test_email, get_email_config

LEVELS = {
    "Beginner": 1,
    "Intermediate": 2,
    "Advanced": 3,
    "Expert": 4
}

ROLE_CATALOG = {
    "Junior Python Developer": {
        "min_exp": 1.0,
        "criteria": "Foundational Python programming, version control, basic relational databases, and clean code principles.",
        "skills": {"Python": 2, "Git": 2, "SQL": 1, "Communication": 1},
        "recommended_training": ["Core Python Fundamentals & OOP", "Relational Database Fundamentals & SQL", "Team Collaboration with Git"]
    },
    "Senior Python Developer": {
        "min_exp": 3.5,
        "criteria": "Advanced Python idioms, microservices architecture, complex SQL performance tuning, system design, and technical communication.",
        "skills": {"Python": 3, "SQL": 3, "Communication": 3, "REST APIs": 3, "System Design": 2},
        "recommended_training": ["Advanced SQL Optimization & Relational Modeling", "Executive & Cross-Functional Technical Communication", "Scalable Microservices Architecture with Python"]
    },
    "Software Engineer": {
        "min_exp": 1.0,
        "criteria": "Core proficiency in data structures, algorithms, version control, and at least one backend language.",
        "skills": {"Python": 2, "Git": 2, "SQL": 2, "Data Structures": 2, "REST APIs": 2},
        "recommended_training": ["Modern Python Masterclass", "Database Design & SQL Optimization", "Building Scalable RESTful APIs"]
    },
    "Senior Software Engineer": {
        "min_exp": 4.0,
        "criteria": "System design, distributed systems, architecture, CI/CD, and technical mentorship.",
        "skills": {"Python": 3, "System Design": 3, "Cloud Architecture": 2, "CI/CD": 2, "SQL": 3, "Leadership": 2},
        "recommended_training": ["Enterprise System Design Architecture", "Advanced Distributed Systems", "Kubernetes & Microservices in Production"]
    },
    "Data Scientist": {
        "min_exp": 2.0,
        "criteria": "Strong foundation in statistical modeling, machine learning, Python/R, and data visualization.",
        "skills": {"Python": 3, "Machine Learning": 3, "SQL": 2, "Statistics": 3, "Data Visualization": 2},
        "recommended_training": ["Applied Machine Learning & Statistical Inference", "Advanced Data Visualization with Plotly", "Big Data Analytics with SQL"]
    },
    "Machine Learning Engineer": {
        "min_exp": 3.0,
        "criteria": "Deep learning, MLOps, model deployment, distributed computing, and high-performance data pipelines.",
        "skills": {"Python": 3, "Machine Learning": 3, "Deep Learning": 3, "MLOps": 2, "Docker": 2, "Cloud Architecture": 2},
        "recommended_training": ["Production Deep Learning with PyTorch", "End-to-End MLOps Pipelines", "Cloud Model Deployment Architecture"]
    },
    "Frontend Developer": {
        "min_exp": 1.0,
        "criteria": "Proficiency in modern JavaScript/TypeScript, React/Vue, responsive design, and state management.",
        "skills": {"JavaScript": 3, "React": 3, "HTML/CSS": 3, "TypeScript": 2, "Git": 2},
        "recommended_training": ["Modern React & State Management", "TypeScript Deep Dive for Frontend", "Responsive UI/UX Engineering"]
    },
    "Backend Developer": {
        "min_exp": 2.0,
        "criteria": "API design, database modeling, caching, authentication, microservices architecture, and cloud platforms.",
        "skills": {"Python": 3, "SQL": 3, "REST APIs": 3, "Docker": 2, "Microservices": 2, "Git": 2},
        "recommended_training": ["High Performance Microservices Architecture", "Advanced PostgreSQL & Redis Caching", "Docker Containerization Essentials"]
    },
    "DevOps / Cloud Engineer": {
        "min_exp": 3.0,
        "criteria": "Infrastructure as Code, CI/CD pipelines, container orchestration, monitoring, and cloud security.",
        "skills": {"Docker": 3, "Kubernetes": 2, "CI/CD": 3, "Cloud Architecture": 3, "Linux": 3, "Terraform": 2},
        "recommended_training": ["AWS Certified Solutions Architect", "Terraform Infrastructure as Code", "Kubernetes Certified Administrator (CKA)"]
    },
    "Product Manager": {
        "min_exp": 3.0,
        "criteria": "Product strategy, user research, agile roadmapping, data analytics, and cross-functional stakeholder management.",
        "skills": {"Product Strategy": 3, "Agile": 3, "User Research": 2, "Data Analytics": 2, "Communication": 3},
        "recommended_training": ["Strategic Product Management Executive Certificate", "Data-Driven Product Decision Making", "Agile & Scrum Leadership"]
    },
    "Cybersecurity Analyst": {
        "min_exp": 2.0,
        "criteria": "Threat analysis, network security, vulnerability assessment, incident response, and compliance frameworks.",
        "skills": {"Network Security": 3, "Vulnerability Assessment": 3, "Linux": 2, "Incident Response": 2, "Python": 2},
        "recommended_training": ["Certified Information Systems Security Professional (CISSP)", "Practical Ethical Hacking & Pentesting", "SOC Incident Response & Threat Hunting"]
    },
    "Engineering Manager": {
        "min_exp": 6.0,
        "criteria": "People management, strategic roadmapping, technical hiring, team leadership, and cross-functional delivery.",
        "skills": {"Leadership": 4, "People Management": 4, "System Design": 3, "Agile": 3, "Communication": 4},
        "recommended_training": ["Engineering Leadership Excellence", "Strategic People Management & Mentorship", "Executive Communication & Team Scaling"]
    }
}

STANDARD_DEPARTMENTS = [
    "Engineering",
    "IT",
    "Product Management",
    "Data & Analytics",
    "Design & UX",
    "Information Security",
    "Quality Assurance",
    "DevOps & Infrastructure",
    "Human Resources",
    "Finance & Operations",
    "Marketing & Sales"
]

EMPLOYMENT_STATUSES = ["Active", "On Leave", "Terminated"]

def get_db_path() -> Path:
    env_path = os.getenv("DATABASE_PATH")
    if env_path:
        p = Path(env_path)
        db_file = p if p.is_absolute() else (BASE_DIR / p)
    else:
        db_file = BASE_DIR / "data" / "talentsphere.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    return db_file.resolve()

def check_db_health() -> Dict[str, Any]:
    """Inspects the SQLite database connection, file size, integrity, and record counts."""
    path = get_db_path()
    info = {
        "connected": False,
        "path": str(path),
        "filename": path.name,
        "size_kb": 0.0,
        "integrity": "Unknown",
        "counts": {}
    }
    if path.is_file():
        info["size_kb"] = round(path.stat().st_size / 1024, 1)
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check")
            row = cur.fetchone()
            info["integrity"] = row[0] if row else "ok"
            info["connected"] = (info["integrity"].lower() == "ok")
            for table in ["organizations", "users", "employees", "invitation_codes", "performance_reviews", "employee_skills", "assessments", "career_goals", "training_records"]:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    info["counts"][table] = cur.fetchone()[0]
                except Exception:
                    pass
            conn.close()
        except Exception as e:
            info["integrity"] = f"Error: {e}"
    return info

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path(), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn

def _safe_add_column(cursor: sqlite3.Cursor, table_name: str, col_name: str, col_def: str) -> None:
    """Safely adds a column to an existing table if it does not already exist."""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing = {row["name"] for row in cursor.fetchall()}
        if col_name not in existing and existing:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}")
    except Exception:
        pass

def init_db() -> None:
    conn = get_connection()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                official_email TEXT DEFAULT '',
                contact_number TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Pending', 'Suspended')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS invitation_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id TEXT NOT NULL,
                code_hash TEXT UNIQUE NOT NULL,
                code_prefix TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                max_uses INTEGER NOT NULL DEFAULT 1,
                used_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Revoked', 'Expired', 'Depleted')),
                created_by TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(org_id) REFERENCES organizations(org_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS membership_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                org_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                user_email TEXT NOT NULL,
                department TEXT DEFAULT '',
                designation TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'Approved', 'Rejected')),
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(org_id) REFERENCES organizations(org_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'employee',
                employee_id TEXT,
                org_id TEXT,
                account_type TEXT NOT NULL DEFAULT 'Organization',
                department TEXT DEFAULT '',
                job_title TEXT DEFAULT '',
                status TEXT DEFAULT 'Active',
                date_joined TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT UNIQUE NOT NULL,
                org_id TEXT NOT NULL DEFAULT 'ORG-TALENT-01',
                user_id INTEGER,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                phone TEXT DEFAULT '',
                department TEXT NOT NULL,
                designation TEXT NOT NULL,
                joining_date TEXT DEFAULT '',
                employment_status TEXT NOT NULL DEFAULT 'Active' CHECK(employment_status IN ('Active', 'On Leave', 'Terminated')),
                years_experience REAL NOT NULL DEFAULT 0.0 CHECK(years_experience >= 0),
                primary_skills TEXT NOT NULL,
                account_status TEXT NOT NULL DEFAULT 'Active',
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS performance_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                org_id TEXT NOT NULL DEFAULT 'ORG-TALENT-01',
                review_period TEXT NOT NULL,
                performance_score REAL NOT NULL CHECK(performance_score >= 1.0 AND performance_score <= 5.0),
                achievements TEXT DEFAULT '',
                strengths TEXT DEFAULT '',
                improvements TEXT DEFAULT '',
                manager_feedback TEXT DEFAULT '',
                reviewer_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE,
                FOREIGN KEY(reviewer_id) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS employee_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                org_id TEXT NOT NULL DEFAULT 'ORG-TALENT-01',
                user_id INTEGER,
                skill_name TEXT NOT NULL,
                category TEXT DEFAULT 'Technical',
                proficiency_level TEXT NOT NULL CHECK(proficiency_level IN ('Beginner', 'Intermediate', 'Advanced', 'Expert')),
                years_exp REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS career_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                employee_id TEXT,
                org_id TEXT NOT NULL DEFAULT 'ORG-TALENT-01',
                title TEXT NOT NULL,
                target_designation TEXT DEFAULT '',
                description TEXT DEFAULT '',
                target_date TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0 CHECK(progress IN (0, 25, 50, 75, 100)),
                status TEXT NOT NULL DEFAULT 'Not Started' CHECK(status IN ('Not Started', 'In Progress', 'Completed', 'Overdue')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS training_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                org_id TEXT NOT NULL DEFAULT 'ORG-TALENT-01',
                course_name TEXT NOT NULL,
                provider TEXT DEFAULT 'Internal Academy',
                target_skill TEXT NOT NULL,
                target_completion_date TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Enrolled' CHECK(status IN ('Enrolled', 'In Progress', 'Completed')),
                score REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS profiles (
                user_id INTEGER PRIMARY KEY,
                phone TEXT DEFAULT '',
                location TEXT DEFAULT '',
                job_title TEXT DEFAULT '',
                company TEXT DEFAULT '',
                department TEXT DEFAULT '',
                industry TEXT DEFAULT '',
                employment_type TEXT DEFAULT 'Full-time',
                years_experience REAL DEFAULT 0.0,
                linkedin TEXT DEFAULT '',
                github TEXT DEFAULT '',
                portfolio TEXT DEFAULT '',
                education TEXT DEFAULT '',
                certifications TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                experience TEXT DEFAULT '',
                projects TEXT DEFAULT '',
                resume_text TEXT DEFAULT '',
                target_role TEXT DEFAULT '',
                target_level TEXT DEFAULT 'Senior',
                timeline TEXT DEFAULT '6–12 months',
                target_industry TEXT DEFAULT '',
                career_goal TEXT DEFAULT '',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                proficiency TEXT NOT NULL,
                years REAL DEFAULT 0.0,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                employee_id TEXT DEFAULT '',
                org_id TEXT NOT NULL DEFAULT 'ORG-TALENT-01',
                category TEXT NOT NULL,
                skill_name TEXT DEFAULT '',
                score REAL NOT NULL,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item TEXT NOT NULL,
                percent REAL NOT NULL DEFAULT 0.0,
                status TEXT NOT NULL DEFAULT 'In Progress',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                employee_id TEXT,
                org_id TEXT NOT NULL DEFAULT 'ORG-TALENT-01',
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                target_date TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0 CHECK(progress IN (0, 25, 50, 75, 100)),
                status TEXT NOT NULL DEFAULT 'Not Started',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                org_id TEXT NOT NULL DEFAULT 'ORG-TALENT-01',
                summary TEXT DEFAULT '',
                skills_json TEXT DEFAULT '[]',
                experience_json TEXT DEFAULT '[]',
                education_json TEXT DEFAULT '[]',
                certifications_json TEXT DEFAULT '[]',
                projects_json TEXT DEFAULT '[]',
                links_json TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS email_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                to_email TEXT NOT NULL,
                user_name TEXT DEFAULT '',
                role TEXT DEFAULT '',
                org_name TEXT DEFAULT '',
                subject TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Sent',
                error_message TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)


        # Auto-migrate existing database tables if columns are missing
        cursor = conn.cursor()

        # 1. Migrate organizations table FIRST before any inserts
        _safe_add_column(cursor, "organizations", "official_email", "TEXT DEFAULT ''")
        _safe_add_column(cursor, "organizations", "contact_number", "TEXT DEFAULT ''")
        _safe_add_column(cursor, "organizations", "status", "TEXT NOT NULL DEFAULT 'Active'")

        # 2. Migrate users table
        _safe_add_column(cursor, "users", "account_type", "TEXT NOT NULL DEFAULT 'Organization'")
        _safe_add_column(cursor, "users", "role", "TEXT NOT NULL DEFAULT 'employee'")
        _safe_add_column(cursor, "users", "employee_id", "TEXT")
        _safe_add_column(cursor, "users", "org_id", "TEXT DEFAULT NULL")
        _safe_add_column(cursor, "users", "department", "TEXT DEFAULT ''")
        _safe_add_column(cursor, "users", "job_title", "TEXT DEFAULT ''")
        _safe_add_column(cursor, "users", "status", "TEXT DEFAULT 'Active'")
        _safe_add_column(cursor, "users", "date_joined", "TEXT DEFAULT ''")
        _safe_add_column(cursor, "users", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

        # Ensure users.org_id is nullable in existing databases to support Individual accounts
        try:
            cursor.execute("PRAGMA table_info(users)")
            u_info = {row["name"]: dict(row) for row in cursor.fetchall()}
            if u_info.get("org_id", {}).get("notnull") == 1 or u_info.get("employee_id", {}).get("notnull") == 1:
                cursor.execute("PRAGMA foreign_keys = OFF")
                cursor.execute('''
                    CREATE TABLE users_migrated (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'employee',
                        employee_id TEXT,
                        org_id TEXT,
                        account_type TEXT NOT NULL DEFAULT 'Organization',
                        department TEXT DEFAULT '',
                        job_title TEXT DEFAULT '',
                        status TEXT DEFAULT 'Active',
                        date_joined TEXT DEFAULT '',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                cursor.execute('''
                    INSERT INTO users_migrated (id, name, email, password_hash, salt, role, employee_id, org_id, account_type, department, job_title, status, date_joined, created_at)
                    SELECT id, name, email, password_hash, salt, role, employee_id, 
                           CASE WHEN org_id = '' OR account_type = 'Individual' THEN NULL ELSE org_id END,
                           COALESCE(account_type, 'Organization'), COALESCE(department, ''), COALESCE(job_title, ''), 
                           COALESCE(status, 'Active'), COALESCE(date_joined, ''), COALESCE(created_at, CURRENT_TIMESTAMP)
                    FROM users
                ''')
                cursor.execute("DROP TABLE users")
                cursor.execute("ALTER TABLE users_migrated RENAME TO users")
                cursor.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass

        # 3. Migrate employees table
        _safe_add_column(cursor, "employees", "email", "TEXT")
        _safe_add_column(cursor, "employees", "phone", "TEXT DEFAULT ''")
        _safe_add_column(cursor, "employees", "joining_date", "TEXT DEFAULT ''")
        _safe_add_column(cursor, "employees", "employment_status", "TEXT NOT NULL DEFAULT 'Active'")
        _safe_add_column(cursor, "employees", "org_id", "TEXT NOT NULL DEFAULT 'ORG-TALENT-01'")
        _safe_add_column(cursor, "employees", "user_id", "INTEGER")
        _safe_add_column(cursor, "employees", "account_status", "TEXT NOT NULL DEFAULT 'Active'")

        # 4. Migrate employee_skills table
        _safe_add_column(cursor, "employee_skills", "org_id", "TEXT NOT NULL DEFAULT 'ORG-TALENT-01'")
        _safe_add_column(cursor, "employee_skills", "user_id", "INTEGER")

        # 5. Migrate skills table
        _safe_add_column(cursor, "skills", "description", "TEXT DEFAULT ''")

        # 6. Migrate assessments table
        _safe_add_column(cursor, "assessments", "employee_id", "TEXT DEFAULT ''")
        _safe_add_column(cursor, "assessments", "org_id", "TEXT NOT NULL DEFAULT 'ORG-TALENT-01'")
        _safe_add_column(cursor, "assessments", "skill_name", "TEXT DEFAULT ''")
        _safe_add_column(cursor, "assessments", "notes", "TEXT DEFAULT ''")

        # 7. Migrate performance_reviews table
        _safe_add_column(cursor, "performance_reviews", "org_id", "TEXT NOT NULL DEFAULT 'ORG-TALENT-01'")

        # 8. Migrate career_goals table
        _safe_add_column(cursor, "career_goals", "target_designation", "TEXT DEFAULT ''")
        _safe_add_column(cursor, "career_goals", "org_id", "TEXT NOT NULL DEFAULT 'ORG-TALENT-01'")

        # 9. Migrate training_records table
        _safe_add_column(cursor, "training_records", "org_id", "TEXT NOT NULL DEFAULT 'ORG-TALENT-01'")

        # 10. Migrate resumes table
        _safe_add_column(cursor, "resumes", "org_id", "TEXT NOT NULL DEFAULT 'ORG-TALENT-01'")

        # 11. Migrate invitation_codes table if legacy schema exists or columns are missing
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invitation_codes'")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(invitation_codes)")
                inv_cols = {row["name"]: row for row in cursor.fetchall()}
                if "code_hash" not in inv_cols:
                    # Legacy schema with plaintext code - safely migrate to hashed schema
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS invitation_codes_v2 (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            org_id TEXT NOT NULL,
                            code_hash TEXT UNIQUE NOT NULL,
                            code_prefix TEXT NOT NULL,
                            expires_at TIMESTAMP NOT NULL,
                            max_uses INTEGER NOT NULL DEFAULT 1,
                            used_count INTEGER NOT NULL DEFAULT 0,
                            status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Revoked', 'Expired', 'Depleted')),
                            created_by TEXT DEFAULT '',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(org_id) REFERENCES organizations(org_id) ON DELETE CASCADE
                        )
                    ''')
                    cursor.execute("SELECT * FROM invitation_codes")
                    for row in cursor.fetchall():
                        r = dict(row)
                        raw_code = str(r.get("code") or "")
                        c_hash = hash_invitation_code(raw_code) if raw_code else secrets.token_hex(16)
                        c_prefix = raw_code[:8] if raw_code else "INV-MIGR"
                        c_exp = r.get("expires_at") or "2099-12-31 23:59:59"
                        c_max = r.get("max_uses", 1) or 1
                        c_used = r.get("used_count", 0) or 0
                        c_stat = r.get("status", "Active")
                        if c_stat not in ("Active", "Revoked", "Expired", "Depleted"):
                            c_stat = "Active"
                        c_by = str(r.get("created_by") or "")
                        c_at = r.get("created_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                        cursor.execute('''
                            INSERT OR IGNORE INTO invitation_codes_v2
                            (id, org_id, code_hash, code_prefix, expires_at, max_uses, used_count, status, created_by, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (r.get("id"), r.get("org_id", "ORG-TALENT-01"), c_hash, c_prefix, c_exp, c_max, c_used, c_stat, c_by, c_at))
                    cursor.execute("DROP TABLE invitation_codes")
                    cursor.execute("ALTER TABLE invitation_codes_v2 RENAME TO invitation_codes")
        except Exception:
            pass

        # Guarantee all columns exist in invitation_codes even for legacy databases
        try:
            _safe_add_column(cursor, "invitation_codes", "org_id", "TEXT NOT NULL DEFAULT 'ORG-TALENT-01'")
            _safe_add_column(cursor, "invitation_codes", "code_hash", "TEXT DEFAULT ''")
            _safe_add_column(cursor, "invitation_codes", "code_prefix", "TEXT NOT NULL DEFAULT 'INV-0000'")
            _safe_add_column(cursor, "invitation_codes", "expires_at", "TIMESTAMP NOT NULL DEFAULT '2099-12-31 23:59:59'")
            _safe_add_column(cursor, "invitation_codes", "max_uses", "INTEGER NOT NULL DEFAULT 1")
            _safe_add_column(cursor, "invitation_codes", "used_count", "INTEGER NOT NULL DEFAULT 0")
            _safe_add_column(cursor, "invitation_codes", "status", "TEXT NOT NULL DEFAULT 'Active'")
            _safe_add_column(cursor, "invitation_codes", "created_by", "TEXT DEFAULT ''")
            _safe_add_column(cursor, "invitation_codes", "created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        except Exception:
            pass

        # Seed default organizations (now guaranteed to have official_email, contact_number, status)
        try:
            cursor.execute("SELECT id FROM organizations WHERE org_id = 'ORG-TALENT-01'")
            if not cursor.fetchone():
                cursor.execute("INSERT OR IGNORE INTO organizations (org_id, name, official_email, contact_number, status) VALUES (?, ?, ?, ?, ?)",
                               ('ORG-TALENT-01', 'Talent Growth Technologies', 'contact@talentgrowth.com', '+1-555-0100', 'Active'))
            cursor.execute("SELECT id FROM organizations WHERE org_id = 'ORG-TECHCORP-02'")
            if not cursor.fetchone():
                cursor.execute("INSERT OR IGNORE INTO organizations (org_id, name, official_email, contact_number, status) VALUES (?, ?, ?, ?, ?)",
                               ('ORG-TECHCORP-02', 'TechCorp Solutions', 'contact@techcorp.com', '+1-555-0900', 'Active'))
        except Exception:
            pass

        # Backfill account_type and org_id safely
        try:
            cursor.execute("UPDATE users SET account_type = 'Individual' WHERE (account_type IS NULL OR account_type = '') AND org_id IS NULL")
            cursor.execute("UPDATE users SET account_type = 'Organization' WHERE (account_type IS NULL OR account_type = '') AND org_id IS NOT NULL")
            cursor.execute("UPDATE users SET account_type = 'Organization' WHERE account_type IS NULL OR account_type = ''")
            cursor.execute("UPDATE users SET org_id = 'ORG-TALENT-01' WHERE (org_id IS NULL OR org_id = '') AND account_type != 'Individual'")
            cursor.execute("UPDATE employees SET org_id = 'ORG-TALENT-01' WHERE org_id IS NULL OR org_id = ''")
            cursor.execute("UPDATE performance_reviews SET org_id = 'ORG-TALENT-01' WHERE org_id IS NULL OR org_id = ''")
            cursor.execute("UPDATE employee_skills SET org_id = 'ORG-TALENT-01' WHERE org_id IS NULL OR org_id = ''")
            cursor.execute("UPDATE career_goals SET org_id = 'ORG-TALENT-01' WHERE org_id IS NULL OR org_id = ''")
            cursor.execute("UPDATE training_records SET org_id = 'ORG-TALENT-01' WHERE org_id IS NULL OR org_id = ''")
            cursor.execute("UPDATE assessments SET org_id = 'ORG-TALENT-01' WHERE org_id IS NULL OR org_id = ''")
            cursor.execute("UPDATE users SET employee_id = 'EMP101' WHERE email = 'alex@company.com' AND (employee_id IS NULL OR employee_id = '')")
            cursor.execute("UPDATE employees SET user_id = (SELECT id FROM users WHERE users.email = employees.email) WHERE user_id IS NULL AND email IS NOT NULL")
        except Exception:
            pass

        # Database Indexes for Organization-Level Data Isolation and Performance
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_invitation_codes_org ON invitation_codes(org_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_invitation_codes_hash ON invitation_codes(code_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_employees_org ON employees(org_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_org ON users(org_id)")
        except Exception:
            pass

        # Seed initial admin user if none exists (supporting admin@talentgrowth.com)
        cursor.execute("SELECT id FROM users WHERE email IN ('admin@talentgrowth.com', 'admin@talentsphere.com')")
        admin_row = cursor.fetchone()
        if not admin_row:
            admin_pwd_hash, admin_salt = hash_password("Admin@12345")
            cursor.execute(
                "INSERT OR IGNORE INTO users (name, email, password_hash, salt, role, employee_id) VALUES (?, ?, ?, ?, ?, ?)",
                ("HR Administrator", "admin@talentgrowth.com", admin_pwd_hash, admin_salt, "admin", "EMP001")
            )
            admin_uid = cursor.lastrowid
            if admin_uid:
                cursor.execute("INSERT OR IGNORE INTO profiles (user_id, job_title, department) VALUES (?, ?, ?)",
                               (admin_uid, "VP of Human Resources", "Human Resources"))
        else:
            # Update legacy email to admin@talentgrowth.com
            cursor.execute("UPDATE OR IGNORE users SET email = 'admin@talentgrowth.com' WHERE email = 'admin@talentsphere.com'")

        # Seed initial demo employee if none exists
        cursor.execute("SELECT id FROM users WHERE email = 'alex@company.com'")
        alex_row = cursor.fetchone()
        if not alex_row:
            emp_pwd_hash, emp_salt = hash_password("Password123")
            cursor.execute(
                "INSERT OR IGNORE INTO users (name, email, password_hash, salt, role, employee_id) VALUES (?, ?, ?, ?, ?, ?)",
                ("Alex Morgan", "alex@company.com", emp_pwd_hash, emp_salt, "employee", "EMP101")
            )
            alex_uid = cursor.lastrowid
        else:
            alex_uid = alex_row["id"]

        if alex_uid:
            cursor.execute("SELECT user_id, job_title FROM profiles WHERE user_id = ?", (alex_uid,))
            p_row = cursor.fetchone()
            if not p_row or not p_row["job_title"]:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO profiles (user_id, job_title, department, years_experience, summary, target_role)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (alex_uid, "Full Stack Engineer", "Engineering", 3.5,
                     "Full stack engineer passionate about scalable cloud systems, microservices, and React frontends.",
                     "Senior Software Engineer")
                )
            cursor.execute("SELECT COUNT(*) as cnt FROM skills WHERE user_id = ?", (alex_uid,))
            if cursor.fetchone()["cnt"] == 0:
                cursor.execute(
                    """
                    INSERT INTO skills (user_id, name, category, proficiency, years)
                    VALUES (?, ?, ?, ?, ?), (?, ?, ?, ?, ?), (?, ?, ?, ?, ?)
                    """,
                    (alex_uid, "Python", "Technical", "Advanced", 3.5,
                     alex_uid, "React", "Technical", "Intermediate", 2.0,
                     alex_uid, "SQL", "Technical", "Intermediate", 3.0)
                )

        # Seed Ravi Kumar demo employee (Classroom/Viva showcase) if none exists
        cursor.execute("SELECT id FROM users WHERE email = 'ravi@company.com'")
        ravi_user = cursor.fetchone()
        if not ravi_user:
            ravi_pwd_hash, ravi_salt = hash_password("Password123")
            cursor.execute(
                "INSERT INTO users (name, email, password_hash, salt, role, employee_id) VALUES (?, ?, ?, ?, ?, ?)",
                ("Ravi Kumar", "ravi@company.com", ravi_pwd_hash, ravi_salt, "employee", "EMP107")
            )
            ravi_uid = cursor.lastrowid
            cursor.execute(
                """
                INSERT OR IGNORE INTO profiles (user_id, job_title, department, years_experience, summary, target_role)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (ravi_uid, "Junior Python Developer", "IT", 1.5,
                 "Junior Python Developer passionate about clean scripting, automation, and expanding backend mastery.",
                 "Senior Python Developer")
            )
            cursor.execute(
                """
                INSERT OR IGNORE INTO skills (user_id, name, category, proficiency, years)
                VALUES (?, ?, ?, ?, ?), (?, ?, ?, ?, ?), (?, ?, ?, ?, ?), (?, ?, ?, ?, ?)
                """,
                (ravi_uid, "Python", "Technical", "Intermediate", 1.5,
                 ravi_uid, "Git", "Technical", "Intermediate", 1.5,
                 ravi_uid, "SQL", "Technical", "Beginner", 0.5,
                 ravi_uid, "Communication", "Soft Skills", "Beginner", 1.0)
            )
        else:
            ravi_uid = ravi_user["id"]

        # Seed sample employees if not already present
        sample_employees = [
            ("EMP101", "Alex Morgan", "alex@company.com", "+1-555-0101", "Engineering", "Full Stack Engineer", "2023-03-15", "Active", 3.5, "Python, React, SQL, Docker", 1),
            ("EMP102", "Sarah Connor", "sarah.c@company.com", "+1-555-0102", "Engineering", "Senior Software Engineer", "2021-06-10", "Active", 6.0, "Python, System Design, Kubernetes, AWS, CI/CD", 1),
            ("EMP103", "David Miller", "david.m@company.com", "+1-555-0103", "Product Management", "Lead Product Manager", "2020-01-20", "Active", 7.5, "Product Strategy, Agile, User Research, Jira", 1),
            ("EMP104", "Elena Rostova", "elena.r@company.com", "+1-555-0104", "Data & Analytics", "Senior Data Scientist", "2022-09-01", "Active", 4.5, "Python, Machine Learning, Statistics, SQL, Tableau", 1),
            ("EMP105", "Marcus Vance", "marcus.v@company.com", "+1-555-0105", "Information Security", "Cybersecurity Analyst", "2024-02-15", "Active", 2.5, "Network Security, Vulnerability Assessment, Linux, Python", 1),
            ("EMP106", "Rachel Green", "rachel.g@company.com", "+1-555-0106", "Design & UX", "Senior UX Designer", "2022-11-10", "Active", 5.0, "Figma, User Research, Prototyping, Design Systems", 1),
            ("EMP107", "Ravi Kumar", "ravi@company.com", "+1-555-0107", "IT", "Junior Python Developer", "2024-01-15", "Active", 1.5, "Python, Git, SQL, Communication", 1),
        ]
        for emp in sample_employees:
            cursor.execute(
                """
                INSERT OR IGNORE INTO employees (employee_id, name, email, phone, department, designation, joining_date, employment_status, years_experience, primary_skills, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                emp
            )

        # Seed performance reviews (guarded against duplicates)
        sample_reviews = [
            ("EMP101", "2025 Annual Review", 4.2, "Delivered new microservices architecture and increased API uptime by 18%.", "Technical problem solving, proactive teamwork.", "System design for higher concurrency.", "Consistent high performer ready for senior responsibilities.", 1),
            ("EMP102", "2025 Annual Review", 4.8, "Led migration of core monolith to Kubernetes cluster with zero downtime.", "Architecture, mentorship, high reliability.", "Delegating more operational tasks to juniors.", "Exemplary technical lead across the engineering group.", 1),
            ("EMP103", "2025 Annual Review", 4.5, "Launched Q3 enterprise product roadmap on schedule with 94% customer satisfaction.", "Stakeholder alignment, strategic clarity.", "Deep dive analytics modeling.", "Outstanding product driver with strong leadership presence.", 1),
            ("EMP104", "2025 Annual Review", 4.6, "Constructed predictive customer churn model with 89% precision.", "Mathematical rigor, fast prototyping.", "Productionizing models via MLOps.", "High value technical asset to data organization.", 1),
            ("EMP105", "2025 Annual Review", 3.9, "Executed zero-breach security audit and resolved 45 CVE vulnerabilities.", "Fast response time, thorough documentation.", "Scripting automated penetration tests.", "Solid performer with growing specialization.", 1),
            ("EMP107", "2025 Annual Review", 3.8, "Delivered Python backend automation scripts and completed assigned user stories on schedule.", "Strong analytical logic, fast learner, high code quality.", "Needs deeper mastery of relational database queries (SQL) and active cross-team communication in standups.", "Promising junior developer with great potential. With targeted SQL training and communication practice, Ravi can transition towards a Senior Python Developer role.", 1),
        ]
        for rev in sample_reviews:
            cursor.execute("SELECT id FROM performance_reviews WHERE employee_id = ? AND review_period = ?", (rev[0], rev[1]))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO performance_reviews (employee_id, review_period, performance_score, achievements, strengths, improvements, manager_feedback, reviewer_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rev
                )

        # Seed employee skills matrix (guarded against duplicates)
        sample_skills = [
            ("EMP101", "Python", "Technical", "Advanced", 3.5),
            ("EMP101", "React", "Technical", "Intermediate", 2.0),
            ("EMP101", "SQL", "Technical", "Intermediate", 3.0),
            ("EMP101", "Docker", "Technical", "Intermediate", 2.0),
            ("EMP102", "Python", "Technical", "Expert", 6.0),
            ("EMP102", "System Design", "Technical", "Expert", 5.0),
            ("EMP102", "Kubernetes", "Technical", "Advanced", 4.0),
            ("EMP102", "AWS", "Technical", "Advanced", 4.5),
            ("EMP103", "Product Strategy", "Domain", "Expert", 7.0),
            ("EMP103", "Agile", "Domain", "Advanced", 6.0),
            ("EMP104", "Machine Learning", "Technical", "Advanced", 4.0),
            ("EMP104", "Statistics", "Technical", "Advanced", 4.5),
            ("EMP107", "Python", "Technical", "Intermediate", 1.5),
            ("EMP107", "Git", "Technical", "Intermediate", 1.5),
            ("EMP107", "SQL", "Technical", "Beginner", 0.5),
            ("EMP107", "Communication", "Soft Skills", "Beginner", 1.0),
        ]
        for sk in sample_skills:
            cursor.execute("SELECT id FROM employee_skills WHERE employee_id = ? AND skill_name = ?", (sk[0], sk[1]))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO employee_skills (employee_id, skill_name, category, proficiency_level, years_exp)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    sk
                )

        # Seed sample training records (guarded against duplicates)
        sample_trainings = [
            ("EMP101", "Enterprise System Design Architecture", "Internal Academy", "System Design", "2026-11-30", "In Progress", 60.0),
            ("EMP101", "Building Scalable RESTful APIs", "Coursera", "REST APIs", "2026-08-15", "Completed", 95.0),
            ("EMP102", "Executive Engineering Leadership", "Internal Academy", "Leadership", "2026-12-15", "In Progress", 40.0),
            ("EMP104", "Production Deep Learning with PyTorch", "Fast.ai", "Deep Learning", "2026-10-31", "Enrolled", 0.0),
            ("EMP107", "Advanced SQL Optimization & Relational Modeling", "Internal Academy", "SQL", "2026-11-30", "In Progress", 65.0),
            ("EMP107", "Executive & Cross-Functional Technical Communication", "Coursera", "Communication", "2026-12-15", "Enrolled", 0.0),
        ]
        for tr in sample_trainings:
            cursor.execute("SELECT id FROM training_records WHERE employee_id = ? AND course_name = ?", (tr[0], tr[1]))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO training_records (employee_id, course_name, provider, target_skill, target_completion_date, status, score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    tr
                )

        # Seed sample career goals (guarded against duplicates)
        sample_goals = [
            (2, "EMP101", "Achieve AWS Solutions Architect Associate", "Senior Software Engineer", "Study official guide and do 5 practice exams.", "2026-12-31", 50, "In Progress"),
            (2, "EMP101", "Lead System Design for Core Payment Gateway", "Senior Software Engineer", "Design high throughput event-driven microservices.", "2026-11-15", 25, "In Progress"),
            (1, "EMP001", "Implement Automated Performance Review Cycles", "HR Director", "Digitalize enterprise review workflows with analytics.", "2026-10-30", 75, "In Progress"),
            (ravi_uid, "EMP107", "Transition to Senior Python Developer", "Senior Python Developer", "Master advanced SQL database tuning, clean architecture, and lead technical discussions.", "2026-12-31", 50, "In Progress"),
        ]
        for g in sample_goals:
            cursor.execute("SELECT id FROM career_goals WHERE user_id = ? AND title = ?", (g[0], g[2]))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO career_goals (user_id, employee_id, title, target_designation, description, target_date, progress, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    g
                )
                cursor.execute(
                    """
                    INSERT INTO goals (user_id, employee_id, org_id, title, description, target_date, progress, status)
                    VALUES (?, ?, 'ORG-TALENT-01', ?, ?, ?, ?, ?)
                    """,
                    (g[0], g[1], g[2], g[4], g[5], g[6], g[7])
                )

        # Seed Organization B (TechCorp Solutions) demo users for multi-tenant isolation
        cursor.execute("SELECT id FROM users WHERE email = 'admin@techcorp.com'")
        if not cursor.fetchone():
            tc_admin_hash, tc_admin_salt = hash_password("Password123")
            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash, salt, role, employee_id, org_id, department, job_title, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("HR Admin B", "admin@techcorp.com", tc_admin_hash, tc_admin_salt, "admin", "TC001", "ORG-TECHCORP-02", "Human Resources", "HR Director", "Active")
            )
            tc_admin_uid = cursor.lastrowid
            cursor.execute(
                "INSERT OR IGNORE INTO profiles (user_id, job_title, department, company) VALUES (?, ?, ?, ?)",
                (tc_admin_uid, "HR Director", "Human Resources", "TechCorp Solutions")
            )

        cursor.execute("SELECT id FROM users WHERE email = 'jane@techcorp.com'")
        if not cursor.fetchone():
            tc_jane_hash, tc_jane_salt = hash_password("Password123")
            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash, salt, role, employee_id, org_id, department, job_title, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("Jane Smith", "jane@techcorp.com", tc_jane_hash, tc_jane_salt, "employee", "TC101", "ORG-TECHCORP-02", "Data & Analytics", "Data Engineer", "Active")
            )
            tc_jane_uid = cursor.lastrowid
            cursor.execute(
                """
                INSERT OR IGNORE INTO profiles (user_id, job_title, department, company, years_experience, target_role)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (tc_jane_uid, "Data Engineer", "Data & Analytics", "TechCorp Solutions", 3.0, "Senior Data Scientist")
            )
            cursor.execute(
                """
                INSERT OR IGNORE INTO employees (employee_id, org_id, user_id, name, email, phone, department, designation, joining_date, employment_status, years_experience, primary_skills, account_status, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("TC101", "ORG-TECHCORP-02", tc_jane_uid, "Jane Smith", "jane@techcorp.com", "+1-555-0901", "Data & Analytics", "Data Engineer", "2024-02-01", "Active", 3.0, "Python, SQL, PySpark", "Active", 1)
            )
            cursor.execute(
                """
                INSERT OR IGNORE INTO employee_skills (employee_id, org_id, user_id, skill_name, category, proficiency_level, years_exp)
                VALUES (?, ?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?, ?)
                """,
                ("TC101", "ORG-TECHCORP-02", tc_jane_uid, "Python", "Technical", "Advanced", 3.0,
                 "TC101", "ORG-TECHCORP-02", tc_jane_uid, "SQL", "Technical", "Intermediate", 2.5)
            )
            cursor.execute(
                """
                INSERT OR IGNORE INTO skills (user_id, name, category, proficiency, years)
                VALUES (?, ?, ?, ?, ?), (?, ?, ?, ?, ?)
                """,
                (tc_jane_uid, "Python", "Technical", "Advanced", 3.0,
                 tc_jane_uid, "SQL", "Technical", "Intermediate", 2.5)
            )
            cursor.execute(
                """
                INSERT OR IGNORE INTO performance_reviews (employee_id, org_id, review_period, performance_score, achievements, strengths, improvements, manager_feedback)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("TC101", "ORG-TECHCORP-02", "2025 Annual Review", 4.4, "Built core data pipelines for TechCorp.", "Data modeling, reliable ETL", "Cloud architecture", "Top performer at TechCorp.")
            )
            cursor.execute(
                """
                INSERT OR IGNORE INTO career_goals (user_id, employee_id, org_id, title, target_designation, description, target_date, progress, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tc_jane_uid, "TC101", "ORG-TECHCORP-02", "Master Apache Spark & Streaming", "Senior Data Scientist", "Complete internal big data track", "2026-11-30", 50, "In Progress")
            )

        # Automatic startup purge of requested user accounts (e.g. user re-registration cleanup)
        for purge_email in [
            "madhannetha0223@gmaill.com",
            "madhannetha0223@gmail.com",
            "vibifess6813@en2ch.com",
            "vibifes6813@en2ch.com",
            "madhannethag23@gmail.com",
            "madhannethag23@mail.com",
            "madhangosikonda2003@gmail.com",
            "madhangosikonda2003+2e1952@gmail.com"
        ]:
            try:
                cursor.execute("SELECT id, employee_id FROM users WHERE LOWER(email) = ?", (purge_email,))
                p_user = cursor.fetchone()
                if p_user:
                    p_uid = p_user["id"]
                    p_eid = p_user["employee_id"]
                    cursor.execute("DELETE FROM profiles WHERE user_id = ?", (p_uid,))
                    cursor.execute("DELETE FROM skills WHERE user_id = ?", (p_uid,))
                    cursor.execute("DELETE FROM employee_skills WHERE user_id = ? OR (employee_id IS NOT NULL AND employee_id = ?)", (p_uid, p_eid or ''))
                    cursor.execute("DELETE FROM assessments WHERE user_id = ? OR (employee_id IS NOT NULL AND employee_id = ?)", (p_uid, p_eid or ''))
                    cursor.execute("DELETE FROM career_goals WHERE user_id = ? OR (employee_id IS NOT NULL AND employee_id = ?)", (p_uid, p_eid or ''))
                    cursor.execute("DELETE FROM goals WHERE user_id = ? OR (employee_id IS NOT NULL AND employee_id = ?)", (p_uid, p_eid or ''))
                    cursor.execute("DELETE FROM resumes WHERE user_id = ?", (p_uid,))
                    cursor.execute("DELETE FROM progress WHERE user_id = ?", (p_uid,))
                    cursor.execute("DELETE FROM training_records WHERE employee_id IS NOT NULL AND employee_id = ?", (p_eid or '',))
                    cursor.execute("DELETE FROM performance_reviews WHERE employee_id IS NOT NULL AND employee_id = ?", (p_eid or '',))
                    cursor.execute("DELETE FROM membership_requests WHERE user_id = ? OR LOWER(user_email) = ?", (p_uid, purge_email))
                    cursor.execute("DELETE FROM employees WHERE user_id = ? OR LOWER(email) = ? OR (employee_id IS NOT NULL AND employee_id = ?)", (p_uid, purge_email, p_eid or ''))
                    cursor.execute("DELETE FROM email_logs WHERE LOWER(to_email) = ?", (purge_email,))
                    cursor.execute("DELETE FROM users WHERE id = ?", (p_uid,))
                cursor.execute("DELETE FROM employees WHERE LOWER(email) = ?", (purge_email,))
                cursor.execute("DELETE FROM users WHERE LOWER(email) = ?", (purge_email,))
            except Exception:
                pass

        # Also purge any disposable test accounts from en2ch.com domain
        try:
            cursor.execute("SELECT email FROM users WHERE LOWER(email) LIKE '%@en2ch.com'")
            for r in cursor.fetchall():
                e = r["email"].lower()
                cursor.execute("DELETE FROM profiles WHERE user_id IN (SELECT id FROM users WHERE LOWER(email) = ?)", (e,))
                cursor.execute("DELETE FROM skills WHERE user_id IN (SELECT id FROM users WHERE LOWER(email) = ?)", (e,))
                cursor.execute("DELETE FROM employee_skills WHERE user_id IN (SELECT id FROM users WHERE LOWER(email) = ?)", (e,))
                cursor.execute("DELETE FROM assessments WHERE user_id IN (SELECT id FROM users WHERE LOWER(email) = ?)", (e,))
                cursor.execute("DELETE FROM career_goals WHERE user_id IN (SELECT id FROM users WHERE LOWER(email) = ?)", (e,))
                cursor.execute("DELETE FROM goals WHERE user_id IN (SELECT id FROM users WHERE LOWER(email) = ?)", (e,))
                cursor.execute("DELETE FROM resumes WHERE user_id IN (SELECT id FROM users WHERE LOWER(email) = ?)", (e,))
                cursor.execute("DELETE FROM progress WHERE user_id IN (SELECT id FROM users WHERE LOWER(email) = ?)", (e,))
                cursor.execute("DELETE FROM membership_requests WHERE LOWER(user_email) = ?", (e,))
                cursor.execute("DELETE FROM employees WHERE LOWER(email) = ?", (e,))
                cursor.execute("DELETE FROM email_logs WHERE LOWER(to_email) = ?", (e,))
                cursor.execute("DELETE FROM users WHERE LOWER(email) = ?", (e,))
        except Exception:
            pass
    conn.close()

# ----------------- Organization Management -----------------

def generate_unique_org_id(name: str) -> str:
    """Generates an enterprise-standard, guaranteed-unique organization ID from the org name."""
    clean = re.sub(r"[^A-Z0-9]", "", (name or "").upper())[:8] or "CORP"
    base = f"ORG-{clean}"
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM organizations WHERE org_id = ?", (base,))
        if not cursor.fetchone():
            return base
        for i in range(1, 100):
            cand = f"{base}-{i:02d}"
            cursor.execute("SELECT id FROM organizations WHERE org_id = ?", (cand,))
            if not cursor.fetchone():
                return cand
        import secrets
        return f"{base}-{secrets.token_hex(2).upper()}"
    finally:
        conn.close()

def get_organization_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Case-insensitive lookup of an organization by its name."""
    if not name or not name.strip():
        return None
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM organizations WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))", (name.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_organization(
    org_id: Optional[str] = None,
    name: Optional[str] = None,
    official_email: Optional[str] = None,
    contact_number: Optional[str] = None,
    status: str = "Active"
) -> Tuple[bool, str]:
    """
    Creates a new organization record with case-insensitive name uniqueness,
    official email validation, contact number, and organization status tracking.
    If org_id is omitted, a unique ID is automatically generated.
    """
    if name is None and org_id is not None and not str(org_id).upper().startswith("ORG-"):
        name = org_id
        org_id = None

    name = (name or "").strip()
    if not name:
        return False, "Organization Name is required."

    official_email = (official_email or "").strip().lower()
    contact_number = (contact_number or "").strip()
    valid_statuses = ["Active", "Pending", "Suspended"]
    status = status if status in valid_statuses else "Active"

    if official_email and ("@" not in official_email or "." not in official_email):
        return False, "Please provide a valid official email address."

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            # Case-insensitive duplicate organization name check
            cursor.execute("SELECT id, org_id, name FROM organizations WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))", (name,))
            existing = cursor.fetchone()
            if existing:
                return False, f"An organization named '{existing['name']}' already exists ({existing['org_id']})."

            # Check duplicate official email if provided
            if official_email:
                cursor.execute("SELECT id, org_id, name FROM organizations WHERE LOWER(TRIM(official_email)) = ?", (official_email,))
                dup_email = cursor.fetchone()
                if dup_email:
                    return False, f"An organization with official email '{official_email}' already exists ({dup_email['org_id']})."

            if org_id and org_id.strip():
                final_org_id = org_id.strip().upper()
                cursor.execute("SELECT id FROM organizations WHERE org_id = ?", (final_org_id,))
                if cursor.fetchone():
                    return False, f"Organization ID '{final_org_id}' already exists."
            else:
                final_org_id = generate_unique_org_id(name)

            cursor.execute(
                """
                INSERT INTO organizations (org_id, name, official_email, contact_number, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (final_org_id, name, official_email, contact_number, status)
            )
        return True, f"Organization '{name}' ({final_org_id}) created successfully!"
    except Exception as e:
        return False, f"Database error creating organization: {e}"
    finally:
        conn.close()

def get_organization(org_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM organizations WHERE org_id = ?", (org_id.strip().upper(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def list_organizations() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM organizations ORDER BY name ASC")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def verify_and_activate_hr_admin(user_id: int, verification_code: str) -> Tuple[bool, str]:
    """Verifies an HR authorization key and activates a Pending Approval HR Administrator account."""
    valid_keys = ["HR2026", "TALENT-HR", "HR-AUTH-2026", "ADMIN2026", "ADMIN-2026"]
    env_key = os.getenv("HR_ADMIN_KEY", "").strip()
    if env_key:
        valid_keys.append(env_key)

    clean_code = (verification_code or "").strip().upper()
    if clean_code not in [k.upper() for k in valid_keys]:
        return False, "Invalid HR authorization verification key."

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET status = 'Active' WHERE id = ?", (user_id,))
            cursor.execute("UPDATE employees SET account_status = 'Active' WHERE user_id = ?", (user_id,))
        return True, "HR Administrator access verified and granted successfully."
    except Exception as e:
        return False, f"Database error during verification: {e}"
    finally:
        conn.close()

# ----------------- Organization Invitation Codes & Employee Mapping -----------------

def hash_invitation_code(code: str) -> str:
    """Computes SHA-256 hash of the normalized invitation code for secure storage and lookup."""
    normalized = (code or "").strip().upper()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def generate_invitation_code(
    org_id: str,
    created_by: Optional[Any] = None,
    expiry_days: int = 7,
    max_uses: int = 1
) -> Tuple[bool, Dict[str, Any]]:
    """
    Generates a secure, human-friendly invitation code for employee registration.
    Stores the SHA-256 hash in the database rather than the plaintext code.
    Returns (success, result_dict).
    """
    org_id = (org_id or "").strip().upper()
    org = get_organization(org_id)
    if not org:
        return False, {"error": f"Organization '{org_id}' not found.", "message": f"Organization '{org_id}' not found."}

    if org.get("status") == "Suspended":
        return False, {"error": f"Organization '{org_id}' is suspended. Cannot issue invitations.", "message": f"Organization '{org_id}' is suspended. Cannot issue invitations."}

    try:
        max_uses = int(max_uses)
        if max_uses <= 0:
            max_uses = 1
    except (ValueError, TypeError):
        max_uses = 1

    try:
        expiry_days = int(expiry_days)
        if expiry_days <= 0:
            expiry_days = 7
    except (ValueError, TypeError):
        expiry_days = 7

    clean_org = re.sub(r"[^A-Z0-9]", "", org_id.replace("ORG-", ""))[:4] or "CORP"
    part1 = secrets.token_hex(2).upper()
    part2 = secrets.token_hex(2).upper()
    plaintext_code = f"INV-{clean_org}-{part1}-{part2}"

    code_hash = hash_invitation_code(plaintext_code)
    code_prefix = f"INV-{clean_org}-{part1}-****"
    expires_at = (datetime.now(timezone.utc) + timedelta(days=expiry_days)).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO invitation_codes (org_id, code_hash, code_prefix, expires_at, max_uses, used_count, status, created_by)
                VALUES (?, ?, ?, ?, ?, 0, 'Active', ?)
                """,
                (org_id, code_hash, code_prefix, expires_at, max_uses, str(created_by) if created_by else None)
            )
            code_id = cursor.lastrowid
        return True, {
            "id": code_id,
            "code": plaintext_code,
            "code_prefix": code_prefix,
            "org_id": org_id,
            "org_name": org["name"],
            "expires_at": expires_at,
            "max_uses": max_uses,
            "used_count": 0,
            "status": "Active",
            "message": f"Invitation code created for {org['name']} (expires in {expiry_days} days, max uses: {max_uses})."
        }
    except Exception as e:
        return False, {"error": f"Database error generating invitation code: {e}", "message": f"Database error generating invitation code: {e}"}
    finally:
        conn.close()

def validate_invitation_code(code: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Validates an employee invitation code against hashes, expiration, usage limits, and revocation.
    Returns (is_valid, code_info_dict).
    """
    clean_code = (code or "").strip().upper()
    if not clean_code:
        return False, {"error": "Invitation code is required.", "message": "Invitation code is required."}

    code_hash = hash_invitation_code(clean_code)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT ic.*, o.name as org_name, o.status as org_status
            FROM invitation_codes ic
            JOIN organizations o ON ic.org_id = o.org_id
            WHERE ic.code_hash = ?
            """,
            (code_hash,)
        )
        row = cursor.fetchone()
        if not row:
            return False, {"error": "Invalid invitation code. Please check the code and try again.", "message": "Invalid invitation code. Please check the code and try again."}

        code_info = dict(row)

        if code_info["status"] == "Revoked":
            return False, {"error": "This invitation code has been revoked by your organization administrator.", "message": "This invitation code has been revoked by your organization administrator.", "status": "Revoked"}

        # Check expiration timestamp
        try:
            exp_dt = datetime.strptime(code_info["expires_at"], "%Y-%m-%d %H:%M:%S")
            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
            if now_utc > exp_dt:
                with conn:
                    cursor.execute("UPDATE invitation_codes SET status = 'Expired' WHERE id = ?", (code_info["id"],))
                return False, {"error": "This invitation code has expired. Please request a new code from HR.", "message": "This invitation code has expired. Please request a new code from HR.", "status": "Expired"}
        except Exception:
            pass

        # Check max usage limit
        if code_info["used_count"] >= code_info["max_uses"]:
            return False, {"error": "This invitation code has already reached its maximum usage limit.", "message": "This invitation code has already reached its maximum usage limit.", "status": "Depleted"}

        if code_info["status"] in ("Expired", "Depleted"):
            return False, {"error": "This invitation code has expired. Please request a new code from HR.", "message": "This invitation code has expired. Please request a new code from HR.", "status": "Expired"}

        if code_info.get("org_status") == "Suspended":
            return False, {"error": "This organization is currently suspended.", "message": "This organization is currently suspended.", "status": "Suspended"}

        code_info["message"] = f"Valid invitation code for {code_info['org_name']}."
        return True, code_info
    finally:
        conn.close()

def use_invitation_code(code: str, conn: Optional[sqlite3.Connection] = None) -> Tuple[bool, str]:
    """Increments the used count of an invitation code and marks as depleted if max uses reached."""
    code_hash = hash_invitation_code(code)
    manage_conn = False
    if conn is None:
        conn = get_connection()
        manage_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, max_uses, used_count FROM invitation_codes WHERE code_hash = ?", (code_hash,))
        row = cursor.fetchone()
        if not row:
            return False, "Invitation code not found."

        new_count = row["used_count"] + 1
        new_status = "Depleted" if new_count >= row["max_uses"] else "Active"

        cursor.execute(
            """
            UPDATE invitation_codes
            SET used_count = ?, status = ?
            WHERE id = ?
            """,
            (new_count, new_status, row["id"])
        )
        if manage_conn:
            conn.commit()
        return True, "Invitation code applied successfully."
    except Exception as e:
        return False, f"Error applying invitation code: {e}"
    finally:
        if manage_conn:
            conn.close()

def list_invitation_codes(org_id: str) -> List[Dict[str, Any]]:
    """Returns all invitation codes for an organization with lazy expiration evaluation."""
    org_id = (org_id or "").strip().upper()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with conn:
                cursor.execute(
                    """
                    UPDATE invitation_codes
                    SET status = 'Expired'
                    WHERE org_id = ? AND status = 'Active' AND (expires_at < ? OR used_count >= max_uses)
                    """,
                    (org_id, now_str)
                )
        except Exception:
            pass

        cursor.execute(
            """
            SELECT ic.*, u.name as creator_name
            FROM invitation_codes ic
            LEFT JOIN users u ON ic.created_by = u.id
            WHERE ic.org_id = ?
            ORDER BY ic.created_at DESC
            """,
            (org_id,)
        )
        return [dict(r) for r in cursor.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()

def revoke_invitation_code(code_id: int, org_id: str) -> Tuple[bool, str]:
    """Revokes an active invitation code, scoped strictly to the organization."""
    org_id = (org_id or "").strip().upper()
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE invitation_codes
                SET status = 'Revoked'
                WHERE id = ? AND org_id = ?
                """,
                (code_id, org_id)
            )
            if cursor.rowcount == 0:
                return False, "Invitation code not found or permission denied."
        return True, "Invitation code has been revoked successfully."
    except Exception as e:
        return False, f"Database error revoking invitation code: {e}"
    finally:
        conn.close()

def deactivate_employee(employee_id: str, org_id: Optional[str] = None) -> Tuple[bool, str]:
    """
    Deactivates an employee record by setting employment_status to 'Terminated'
    and account_status to 'Suspended'. Enforces strict organization tenancy.
    """
    employee_id = (employee_id or "").strip().upper()
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            query = """
                UPDATE employees
                SET employment_status = 'Terminated', account_status = 'Suspended', updated_at = CURRENT_TIMESTAMP
                WHERE employee_id = ?
            """
            params = [employee_id]
            if org_id:
                query += " AND org_id = ?"
                params.append(org_id.strip().upper())
            cursor.execute(query, params)
            if cursor.rowcount == 0:
                return False, f"Employee '{employee_id}' not found or permission denied."

            # Also suspend corresponding user login account if linked
            u_query = "UPDATE users SET status = 'Suspended' WHERE employee_id = ?"
            u_params = [employee_id]
            if org_id:
                u_query += " AND org_id = ?"
                u_params.append(org_id.strip().upper())
            cursor.execute(u_query, u_params)

        return True, f"Employee '{employee_id}' has been deactivated (status: Terminated / Suspended)."
    except Exception as e:
        return False, f"Database error deactivating employee: {e}"
    finally:
        conn.close()

def get_all_designations(org_id: Optional[str] = None) -> List[str]:
    """Returns a sorted list of unique designations across employees in the organization."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if org_id:
            cursor.execute("SELECT DISTINCT designation FROM employees WHERE designation IS NOT NULL AND designation != '' AND org_id = ? ORDER BY designation ASC", (org_id.strip().upper(),))
        else:
            cursor.execute("SELECT DISTINCT designation FROM employees WHERE designation IS NOT NULL AND designation != '' ORDER BY designation ASC")
        return [row["designation"] for row in cursor.fetchall()]
    finally:
        conn.close()

# ----------------- Authentication & Security -----------------

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000
    ).hex()
    return hashed, salt

def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    hashed, _ = hash_password(password, salt)
    return secrets.compare_digest(hashed, stored_hash)

def register_individual(
    name: str,
    email: str,
    password: str,
    confirm_password: Optional[str] = None,
    phone: Optional[str] = "",
    educational_qualification: Optional[str] = "",
    professional_interests: Optional[str] = "",
    primary_skills: Optional[str] = "Python, SQL, Communication",
    years_experience: float = 1.0,
    app_url: Optional[str] = None,
    education: Optional[str] = None,
    interests: Optional[str] = None,
    department: Optional[str] = None,
    job_title: Optional[str] = None,
    **kwargs: Any
) -> Tuple[bool, str]:
    """
    Registers an independent professional account without organization affiliation.
    Automatically assigns:
      - account_type = 'Individual'
      - org_id = None
      - role = 'employee'
      - employee_id = None
    Creates base user and profile records, initializes personal skills, and triggers welcome notification.
    """
    name = (name or "").strip()
    email = (email or "").strip().lower()
    password = password or ""
    phone = (phone or "").strip()
    educational_qualification = (education or educational_qualification or "").strip()
    professional_interests = (interests or professional_interests or "").strip()
    primary_skills = (primary_skills or "Python, SQL, Communication").strip()
    clean_dept = (department or educational_qualification or "Independent Professional").strip()
    clean_title = (job_title or professional_interests or "Independent Professional").strip()
    target_role_val = (professional_interests or interests or clean_title or "Junior Python Developer").strip()

    if not name:
        return False, "Full Name is required."
    if not email or "@" not in email or "." not in email:
        return False, "A valid email address is required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    if confirm_password is not None and confirm_password != password:
        return False, "Passwords do not match. Please verify your password confirmation."

    try:
        years_experience = float(years_experience)
        if years_experience < 0:
            years_experience = 0.0
    except (ValueError, TypeError):
        years_experience = 1.0

    pwd_hash, salt = hash_password(password)
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email,))
            if cursor.fetchone():
                return False, f"An account with email '{email}' already exists. Please sign in instead."

            # Automatically assign account_type='Individual', org_id=None, role='employee'
            try:
                cursor.execute(
                    """
                    INSERT INTO users (name, email, password_hash, salt, role, employee_id, org_id, account_type, department, job_title, status, date_joined)
                    VALUES (?, ?, ?, ?, 'employee', NULL, NULL, 'Individual', ?, ?, 'Active', ?)
                    """,
                    (
                        name,
                        email,
                        pwd_hash,
                        salt,
                        clean_dept,
                        clean_title,
                        date.today().isoformat()
                    )
                )
            except sqlite3.IntegrityError as ie:
                if "not null" in str(ie).lower():
                    # Fallback for legacy database with NOT NULL on org_id or employee_id
                    cursor.execute(
                        """
                        INSERT INTO users (name, email, password_hash, salt, role, employee_id, org_id, account_type, department, job_title, status, date_joined)
                        VALUES (?, ?, ?, ?, 'employee', NULL, '', 'Individual', ?, ?, 'Active', ?)
                        """,
                        (
                            name,
                            email,
                            pwd_hash,
                            salt,
                            clean_dept,
                            clean_title,
                            date.today().isoformat()
                        )
                    )
                else:
                    raise
            user_id = cursor.lastrowid

            # Insert Base Profile
            cursor.execute(
                """
                INSERT OR REPLACE INTO profiles (user_id, phone, education, summary, target_role, job_title, company, department, years_experience)
                VALUES (?, ?, ?, ?, ?, ?, '', ?, ?)
                """,
                (
                    user_id,
                    phone,
                    educational_qualification,
                    f"Interests: {professional_interests}" if professional_interests else "",
                    target_role_val,
                    clean_title,
                    clean_dept,
                    years_experience
                )
            )

            # Insert initial skills catalog for individual user
            skill_tokens = [s.strip() for s in primary_skills.split(",") if s.strip()]
            for sk in skill_tokens:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO skills (user_id, name, category, proficiency, years)
                    VALUES (?, ?, 'Technical', 'Intermediate', ?)
                    """,
                    (user_id, sk, years_experience)
                )

        try:
            send_welcome_email(
                to_email=email,
                user_name=name,
                role="Individual Professional",
                org_name="TalentSphere Personal Hub",
                app_url=app_url
            )
        except Exception:
            pass

        return True, f"Individual account registered successfully! A welcome email has been sent to {email}. You can now sign in to your personal career dashboard."
    except sqlite3.IntegrityError as ie:
        err_str = str(ie).lower()
        if "unique" in err_str and "email" in err_str:
            return False, f"An account with email '{email}' already exists. Please sign in instead."
        if "not null" in err_str:
            return False, f"Database registration error: Missing required column ({ie})."
        return False, f"Database integrity error: {ie}"
    except Exception as e:
        return False, f"Database error during individual registration: {e}"
    finally:
        conn.close()

def register(
    name: str,
    email: str,
    password: str,
    role: str = "employee",
    employee_id: Optional[str] = None,
    org_id: Optional[str] = None,
    org_name: Optional[str] = None,
    department: str = "Engineering",
    job_title: str = "Software Engineer",
    primary_skills: str = "Python, SQL, Communication",
    years_experience: float = 1.0,
    app_url: Optional[str] = None,
    is_new_org: bool = False,
    hr_verification_code: Optional[str] = None,
    require_hr_approval: bool = False,
    invitation_code: Optional[str] = None,
    official_email: Optional[str] = None,
    contact_number: Optional[str] = None,
    registration_type: Optional[str] = None,
    education: Optional[str] = None,
    interests: Optional[str] = None,
    **kwargs: Any
) -> Tuple[bool, str]:
    # Route Option 3: Individual Registration
    if registration_type == "individual" or role == "individual":
        # Only override department/title if not default or if no interests provided
        pass_dept = department if (department != "Engineering" or not (education or interests)) else None
        pass_title = job_title if (job_title != "Software Engineer" or not (education or interests)) else None
        return register_individual(
            name=name,
            email=email,
            password=password,
            phone=contact_number,
            educational_qualification=education,
            professional_interests=interests,
            primary_skills=primary_skills,
            years_experience=years_experience,
            department=pass_dept,
            job_title=pass_title,
            app_url=app_url,
            **kwargs
        )

    # Route Option 2: Register New Organization
    if registration_type == "new_org":
        is_new_org = True
        role = "admin"

    # Route Option 1: Join Existing Organization
    if registration_type == "join_org":
        role = "employee"

    name = (name or "").strip()
    email = (email or "").strip().lower()
    password = password or ""
    role = role if role in ["admin", "employee"] else "employee"
    department = (department or "Engineering").strip()
    job_title = (job_title or "Software Engineer").strip()
    primary_skills = (primary_skills or "Python, SQL, Communication").strip()
    clean_official_email = (official_email or "").strip().lower()
    clean_contact_number = (contact_number or "").strip()

    try:
        years_experience = float(years_experience)
        if years_experience < 0:
            years_experience = 0.0
    except (ValueError, TypeError):
        years_experience = 1.0

    if not name:
        return False, "Full name is required."
    if not email or "@" not in email or "." not in email:
        return False, "A valid email address is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    # Validate employee invitation code upfront if provided
    invitation_info: Optional[Dict[str, Any]] = None
    if invitation_code and invitation_code.strip():
        ok_invite, inv_data = validate_invitation_code(invitation_code.strip())
        if not ok_invite:
            return False, inv_data.get("error", "Invalid invitation code.")
        invitation_info = inv_data

    pwd_hash, salt = hash_password(password)
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()

            # Handle Organization Registration, Invitation Code Mapping, or Selection
            if invitation_info:
                # Employee joined via invitation code - strictly bound to invitation's org_id
                resolved_org_id = invitation_info["org_id"]
                resolved_org_name = invitation_info["org_name"]
            elif is_new_org:
                clean_org_name = (org_name or "").strip()
                if not clean_org_name:
                    return False, "Organization Name is required when registering a new organization."

                # Case-insensitive duplicate name check
                cursor.execute(
                    "SELECT id, org_id, name FROM organizations WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))",
                    (clean_org_name,)
                )
                existing_dup = cursor.fetchone()
                if existing_dup:
                    return False, f"An organization named '{existing_dup['name']}' already exists ({existing_dup['org_id']}). Please select it from existing organizations or enter a different name."

                # Validate and check duplicate official email if provided
                if clean_official_email:
                    if "@" not in clean_official_email or "." not in clean_official_email:
                        return False, "Please provide a valid official email address for the organization."
                    cursor.execute(
                        "SELECT id, org_id, name FROM organizations WHERE LOWER(TRIM(official_email)) = ?",
                        (clean_official_email,)
                    )
                    dup_off = cursor.fetchone()
                    if dup_off:
                        return False, f"An organization with official email '{clean_official_email}' already exists ({dup_off['org_id']})."

                # Auto-generate unique organization ID if not provided
                if not org_id or not str(org_id).strip() or str(org_id).strip().upper() == "ORG-TALENT-01":
                    final_org_id = generate_unique_org_id(clean_org_name)
                else:
                    final_org_id = str(org_id).strip().upper()
                    cursor.execute("SELECT id FROM organizations WHERE org_id = ?", (final_org_id,))
                    if cursor.fetchone():
                        return False, f"Organization ID '{final_org_id}' already exists."

                cursor.execute(
                    """
                    INSERT INTO organizations (org_id, name, official_email, contact_number, status)
                    VALUES (?, ?, ?, ?, 'Active')
                    """,
                    (final_org_id, clean_org_name, clean_official_email, clean_contact_number)
                )
                resolved_org_id = final_org_id
                resolved_org_name = clean_org_name
            elif registration_type == "join_org":
                clean_join_org = (org_name or org_id or "").strip()
                if not clean_join_org:
                    return False, "Organization Name is required to join an existing organization."
                cursor.execute(
                    "SELECT id, org_id, name FROM organizations WHERE LOWER(TRIM(name)) = LOWER(TRIM(?)) OR UPPER(org_id) = UPPER(?)",
                    (clean_join_org, clean_join_org)
                )
                org_row = cursor.fetchone()
                if not org_row:
                    return False, f"Organization '{clean_join_org}' not found. Please verify the organization name or select 'Register New Organization'."
                resolved_org_id = org_row["org_id"]
                resolved_org_name = org_row["name"]
            else:
                resolved_org_id = (org_id or "ORG-TALENT-01").strip().upper()
                cursor.execute("SELECT id, name FROM organizations WHERE org_id = ?", (resolved_org_id,))
                org_row = cursor.fetchone()
                if not org_row:
                    resolved_org_name = org_name or f"Organization {resolved_org_id}"
                    cursor.execute(
                        "INSERT INTO organizations (org_id, name) VALUES (?, ?)",
                        (resolved_org_id, resolved_org_name)
                    )
                else:
                    resolved_org_name = org_row["name"]

            # Increment invitation code usage atomically if registering via invite
            if invitation_info and invitation_code:
                use_invitation_code(invitation_code.strip(), conn=conn)

            # Role Authorization & HR Approval Verification (Requirement 9)
            user_status = "Active"
            if registration_type == "join_org":
                user_status = "Pending Approval"
            elif role == "admin":
                if require_hr_approval and not is_new_org:
                    valid_keys = ["HR2026", "TALENT-HR", "HR-AUTH-2026", "ADMIN2026", "ADMIN-2026"]
                    env_key = os.getenv("HR_ADMIN_KEY", "").strip()
                    if env_key:
                        valid_keys.append(env_key)
                    clean_code = (hr_verification_code or "").strip().upper()
                    if clean_code in [k.upper() for k in valid_keys]:
                        user_status = "Active"
                    else:
                        user_status = "Pending Approval"
                else:
                    user_status = "Active"
            else:
                user_status = "Active"

            # Auto-assign or validate employee_id
            if employee_id and employee_id.strip():
                final_emp_id = employee_id.strip().upper()
            else:
                cursor.execute("SELECT COUNT(*) FROM employees")
                cnt = cursor.fetchone()[0] + 1
                cand = f"EMP{cnt:03d}"
                cursor.execute("SELECT id FROM employees WHERE employee_id = ?", (cand,))
                while cursor.fetchone():
                    cnt += 1
                    cand = f"EMP{cnt:03d}"
                    cursor.execute("SELECT id FROM employees WHERE employee_id = ?", (cand,))
                final_emp_id = cand

            # Insert User record
            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash, salt, role, employee_id, org_id, department, job_title, status, date_joined)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name, email, pwd_hash, salt, role, final_emp_id, resolved_org_id, department, job_title, user_status, date.today().isoformat())
            )
            user_id = cursor.lastrowid

            # Insert Base Profile
            cursor.execute(
                """
                INSERT OR REPLACE INTO profiles (user_id, job_title, department, company, years_experience)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, job_title, department, resolved_org_name, years_experience)
            )

            # Insert or update employee record for seamless HR directory integration
            cursor.execute("SELECT id FROM employees WHERE employee_id = ?", (final_emp_id,))
            emp_existing = cursor.fetchone()
            if emp_existing:
                cursor.execute(
                    """
                    UPDATE employees
                    SET user_id = ?, email = COALESCE(email, ?), org_id = ?, department = ?, designation = ?, account_status = ?
                    WHERE employee_id = ?
                    """,
                    (user_id, email, resolved_org_id, department, job_title, user_status, final_emp_id)
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO employees (employee_id, org_id, user_id, name, email, department, designation, joining_date, employment_status, years_experience, primary_skills, account_status, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?, ?, ?)
                    """,
                    (final_emp_id, resolved_org_id, user_id, name, email, department, job_title, date.today().isoformat(), years_experience, primary_skills, user_status, user_id)
                )

            # Initialize INDIVIDUAL skills profile for this employee (clean, isolated, never copying another employee's assessments)
            skill_tokens = [s.strip() for s in primary_skills.split(",") if s.strip()]
            if not skill_tokens:
                skill_tokens = ["Python", "SQL", "Communication"]
            for sk in skill_tokens:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO employee_skills (employee_id, org_id, user_id, skill_name, category, proficiency_level, years_exp)
                    VALUES (?, ?, ?, ?, 'Technical', 'Intermediate', ?)
                    """,
                    (final_emp_id, resolved_org_id, user_id, sk, years_experience)
                )
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO skills (user_id, name, category, proficiency, years)
                    VALUES (?, ?, 'Technical', 'Intermediate', ?)
                    """,
                    (user_id, sk, years_experience)
                )

            # Record membership request if joining existing organization
            if registration_type == "join_org":
                cursor.execute(
                    """
                    INSERT INTO membership_requests (user_id, org_id, user_name, user_email, department, designation, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'Pending')
                    """,
                    (user_id, resolved_org_id, name, email, department, job_title)
                )

        # Trigger welcome email safely outside the database write transaction
        try:
            import inspect
            sig = inspect.signature(send_welcome_email)
            if "is_pending" in sig.parameters:
                send_welcome_email(
                    to_email=email,
                    user_name=name,
                    role=role,
                    org_name=resolved_org_name,
                    app_url=app_url,
                    is_pending=(user_status == "Pending Approval")
                )
            else:
                send_welcome_email(
                    to_email=email,
                    user_name=name,
                    role=role,
                    org_name=resolved_org_name,
                    app_url=app_url
                )
        except Exception:
            # Gracefully ignore email transport failures to avoid corrupting account creation
            pass

        if registration_type == "join_org":
            return True, f"Membership request submitted for {resolved_org_name}! A confirmation email has been sent to {email}. Your account is pending HR administrator approval."
        if registration_type == "new_org":
            return True, f"Organization {resolved_org_name} registered successfully! A welcome email has been sent to {email}. You are now the HR Administrator."
        if user_status == "Pending Approval":
            return True, f"Account created for {resolved_org_name}! A confirmation email has been sent to {email}. Your HR Administrator access is pending verification. Please sign in."
        return True, f"Account created successfully for {resolved_org_name}! A welcome email has been sent to {email}. Please sign in."
    except sqlite3.IntegrityError as ie:
        err_str = str(ie).lower()
        if "unique" in err_str and "email" in err_str:
            return False, f"An account with email '{email}' already exists. Please sign in instead."
        if "unique" in err_str and "employee_id" in err_str:
            return False, "This Employee ID is already registered in the system."
        return False, f"Database integrity error: {ie}"
    except Exception as e:
        return False, f"Database error during registration: {e}"
    finally:
        conn.close()

def login(email: str, password: str) -> Optional[Dict[str, Any]]:
    email = (email or "").strip().lower()
    if not email or not password:
        return None

    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Safe self-healing check for account_type column
        try:
            cursor.execute("PRAGMA table_info(users)")
            user_cols = {row["name"] for row in cursor.fetchall()}
            if "account_type" not in user_cols and user_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN account_type TEXT NOT NULL DEFAULT 'Organization'")
                conn.commit()
                user_cols.add("account_type")
        except Exception:
            user_cols = set()

        acc_col_sql = "u.account_type," if "account_type" in user_cols else "'Organization' as account_type,"

        cursor.execute(
            f"""
            SELECT u.id, u.name, u.email, u.password_hash, u.salt, u.role, u.employee_id,
                   u.org_id, {acc_col_sql} u.department, u.job_title, u.status, u.date_joined,
                   COALESCE(o.name, 'Talent Growth Technologies') as org_name
            FROM users u
            LEFT JOIN organizations o ON u.org_id = o.org_id
            WHERE u.email = ?
            """,
            (email,)
        )
        row = cursor.fetchone()
        if not row and email in ["admin@talentgrowth.com", "admin@talentsphere.com"]:
            alt = "admin@talentsphere.com" if email == "admin@talentgrowth.com" else "admin@talentgrowth.com"
            cursor.execute(
                f"""
                SELECT u.id, u.name, u.email, u.password_hash, u.salt, u.role, u.employee_id,
                       u.org_id, {acc_col_sql} u.department, u.job_title, u.status, u.date_joined,
                       COALESCE(o.name, 'Talent Growth Technologies') as org_name
                FROM users u
                LEFT JOIN organizations o ON u.org_id = o.org_id
                WHERE u.email = ?
                """,
                (alt,)
            )
            row = cursor.fetchone()
        if not row:
            return None
        if verify_password(password, row["password_hash"], row["salt"]):
            row_keys = row.keys() if hasattr(row, "keys") else []
            account_type = row["account_type"] if "account_type" in row_keys and row["account_type"] else ("Individual" if row["org_id"] is None else "Organization")
            is_ind = (account_type == "Individual" or row["org_id"] is None)
            resolved_org_id = None if is_ind else (row["org_id"] or "ORG-TALENT-01")
            resolved_org_name = None if is_ind else (row["org_name"] or "Talent Growth Technologies")
            return {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "role": row["role"],
                "account_type": account_type,
                "employee_id": row["employee_id"],
                "org_id": resolved_org_id,
                "org_name": resolved_org_name,
                "department": row["department"] or "",
                "job_title": row["job_title"] or "",
                "status": row["status"] or "Active",
                "date_joined": row["date_joined"] or ""
            }
        return None
    finally:
        conn.close()

def get_user_by_id(uid: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA table_info(users)")
            user_cols = {row["name"] for row in cursor.fetchall()}
            if "account_type" not in user_cols and user_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN account_type TEXT NOT NULL DEFAULT 'Organization'")
                conn.commit()
                user_cols.add("account_type")
        except Exception:
            user_cols = set()

        acc_col_sql = "u.account_type," if "account_type" in user_cols else "'Organization' as account_type,"
        created_at_col = "u.created_at," if "created_at" in user_cols else "CURRENT_TIMESTAMP as created_at,"

        cursor.execute(
            f"""
            SELECT u.id, u.name, u.email, u.role, u.employee_id, u.org_id, {acc_col_sql}
                   u.department, u.job_title, u.status, u.date_joined, {created_at_col}
                   o.name as org_name
            FROM users u
            LEFT JOIN organizations o ON u.org_id = o.org_id
            WHERE u.id = ?
            """,
            (uid,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        account_type = res.get("account_type") or ("Individual" if res.get("org_id") is None else "Organization")
        res["account_type"] = account_type
        if account_type == "Individual" or res.get("org_id") is None:
            res["org_id"] = None
            res["org_name"] = None
        else:
            res["org_id"] = res.get("org_id") or "ORG-TALENT-01"
            res["org_name"] = res.get("org_name") or "Talent Growth Technologies"
        return res
    finally:
        conn.close()

def delete_user_by_email(email: str) -> Tuple[bool, str]:
    """
    Permanently deletes a user account and all associated records across the database
    (profiles, skills, employee_skills, assessments, career_goals, goals, resumes,
    progress, training_records, performance_reviews, membership_requests, employees, and email_logs).
    Protects critical system seed accounts from accidental deletion.
    """
    clean_email = (email or "").strip().lower()
    if not clean_email:
        return False, "Email address is required."

    protected = {
        "admin@talentgrowth.com",
        "admin@talentsphere.com",
        "alex@company.com",
        "ravi@company.com",
        "admin@techcorp.com",
        "jane@techcorp.com",
    }
    if clean_email in protected:
        return False, f"Account '{clean_email}' is a protected system seed account and cannot be deleted."

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, employee_id, org_id, name FROM users WHERE LOWER(email) = ?", (clean_email,))
            user_rows = cursor.fetchall()

            cursor.execute("SELECT id, employee_id, org_id, name FROM employees WHERE LOWER(email) = ?", (clean_email,))
            emp_rows = cursor.fetchall()

            if not user_rows and not emp_rows:
                return False, f"No user account found matching '{clean_email}'."

            user_ids = [r["id"] for r in user_rows]
            emp_ids = [r["employee_id"] for r in user_rows if r["employee_id"]]
            for r in emp_rows:
                if r["employee_id"] and r["employee_id"] not in emp_ids:
                    emp_ids.append(r["employee_id"])

            if user_ids:
                placeholders = ','.join('?' for _ in user_ids)
                cursor.execute(f"SELECT employee_id FROM employees WHERE user_id IN ({placeholders})", user_ids)
                for er in cursor.fetchall():
                    if er["employee_id"] and er["employee_id"] not in emp_ids:
                        emp_ids.append(er["employee_id"])

                for uid in user_ids:
                    cursor.execute("DELETE FROM profiles WHERE user_id = ?", (uid,))
                    cursor.execute("DELETE FROM skills WHERE user_id = ?", (uid,))
                    cursor.execute("DELETE FROM employee_skills WHERE user_id = ?", (uid,))
                    cursor.execute("DELETE FROM assessments WHERE user_id = ?", (uid,))
                    cursor.execute("DELETE FROM career_goals WHERE user_id = ?", (uid,))
                    cursor.execute("DELETE FROM goals WHERE user_id = ?", (uid,))
                    cursor.execute("DELETE FROM resumes WHERE user_id = ?", (uid,))
                    cursor.execute("DELETE FROM progress WHERE user_id = ?", (uid,))
                    cursor.execute("DELETE FROM membership_requests WHERE user_id = ?", (uid,))
                    cursor.execute("DELETE FROM employees WHERE user_id = ?", (uid,))

            for eid in emp_ids:
                cursor.execute("DELETE FROM employee_skills WHERE employee_id = ?", (eid,))
                cursor.execute("DELETE FROM assessments WHERE employee_id = ?", (eid,))
                cursor.execute("DELETE FROM career_goals WHERE employee_id = ?", (eid,))
                cursor.execute("DELETE FROM goals WHERE employee_id = ?", (eid,))
                cursor.execute("DELETE FROM training_records WHERE employee_id = ?", (eid,))
                cursor.execute("DELETE FROM performance_reviews WHERE employee_id = ?", (eid,))
                cursor.execute("DELETE FROM employees WHERE employee_id = ?", (eid,))

            cursor.execute("DELETE FROM employees WHERE LOWER(email) = ?", (clean_email,))
            cursor.execute("DELETE FROM membership_requests WHERE LOWER(user_email) = ?", (clean_email,))
            cursor.execute("DELETE FROM email_logs WHERE LOWER(to_email) = ?", (clean_email,))
            cursor.execute("DELETE FROM users WHERE LOWER(email) = ?", (clean_email,))

            return True, f"Account '{clean_email}' and all associated records have been successfully purged."
    except Exception as e:
        return False, f"Failed to delete account '{clean_email}': {e}"
    finally:
        conn.close()

# ----------------- Employee Management (CRUD & Search) -----------------

def add_employee(
    employee_id: str,
    name: str,
    department: str,
    designation: str,
    years_experience: float,
    primary_skills: str,
    email: Optional[str] = None,
    phone: Optional[str] = "",
    joining_date: Optional[str] = "",
    employment_status: str = "Active",
    created_by: Optional[int] = None,
    org_id: str = "ORG-TALENT-01",
    user_id: Optional[int] = None,
    account_status: str = "Active"
) -> Tuple[bool, str]:
    employee_id = (employee_id or "").strip().upper()
    name = (name or "").strip()
    department = (department or "").strip()
    designation = (designation or "").strip()
    primary_skills = (primary_skills or "").strip()
    email = (email or "").strip().lower() if email else None
    phone = (phone or "").strip()
    joining_date = (joining_date or "").strip() or date.today().isoformat()
    employment_status = employment_status if employment_status in EMPLOYMENT_STATUSES else "Active"
    org_id = (org_id or "ORG-TALENT-01").strip().upper()
    account_status = account_status or "Active"

    # Validation: mandatory fields
    if not employee_id:
        return False, "Employee ID is required."
    if not name:
        return False, "Employee Name is required."
    if not department or department == "Select Department":
        return False, "Department is required."
    if not designation:
        return False, "Designation is required."
    if not primary_skills:
        return False, "Primary Skills are required."

    # Validation: experience range
    try:
        years_exp = float(years_experience)
        if years_exp < 0:
            return False, "Years of Experience cannot be negative."
        if years_exp > 60:
            return False, "Years of Experience cannot exceed 60 years."
    except (ValueError, TypeError):
        return False, "Years of Experience must be a valid numeric value."

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            # Prevent duplicate employee ID in organization
            cursor.execute("SELECT id FROM employees WHERE employee_id = ? AND org_id = ?", (employee_id, org_id))
            if cursor.fetchone():
                return False, f"Employee ID '{employee_id}' already exists in this organization. Please use a unique ID."

            # Prevent duplicate email if provided
            if email:
                cursor.execute("SELECT id FROM employees WHERE email = ?", (email,))
                if cursor.fetchone():
                    return False, f"An employee with email '{email}' already exists."

            cursor.execute(
                """
                INSERT INTO employees (employee_id, org_id, user_id, name, email, phone, department, designation, joining_date, employment_status, years_experience, primary_skills, account_status, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (employee_id, org_id, user_id, name, email, phone, department, designation, joining_date, employment_status, years_exp, primary_skills, account_status, created_by)
            )

            # Auto populate employee_skills from primary_skills list
            skill_list = [s.strip() for s in primary_skills.split(",") if s.strip()]
            for sk in skill_list:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO employee_skills (employee_id, org_id, user_id, skill_name, category, proficiency_level, years_exp)
                    VALUES (?, ?, ?, ?, 'Technical', 'Intermediate', ?)
                    """,
                    (employee_id, org_id, user_id, sk, years_exp)
                )

        return True, f"Employee '{name}' (ID: {employee_id}) saved successfully!"
    except sqlite3.IntegrityError as ie:
        return False, f"Database integrity error: {ie}"
    except Exception as e:
        return False, f"Database error while saving employee: {e}"
    finally:
        conn.close()

def get_sample_employee_csv() -> str:
    """Returns a standardized CSV template string for bulk employee dataset uploads."""
    return (
        "employee_id,name,email,phone,department,designation,years_experience,employment_status,joining_date,primary_skills\n"
        "EMP301,Kavita Sharma,kavita.s@company.com,+1-555-0301,Engineering,Backend Developer,3.0,Active,2024-03-01,\"Python, SQL, Django, Docker\"\n"
        "EMP302,Sita Rao,sita.r@company.com,+1-555-0302,Human Resources,HR Executive,2.5,Active,2023-11-15,\"Communication, Recruitment, Employee Engagement\"\n"
        "EMP303,Arun Kumar,arun.k@company.com,+1-555-0303,IT,Data Analyst,2.0,Active,2024-01-10,\"Python, Excel, SQL, Tableau\"\n"
        "EMP304,Vikram Patel,vikram.p@company.com,+1-555-0304,DevOps & Infrastructure,DevOps Engineer,4.0,Active,2022-08-20,\"Linux, Docker, Kubernetes, CI/CD\"\n"
        "EMP305,Ananya Sen,ananya.s@company.com,+1-555-0305,Design & UX,UI/UX Designer,3.5,Active,2023-05-12,\"Figma, Prototyping, Wireframing, CSS\"\n"
    )

def bulk_import_employees_df(df: Any, created_by: Optional[int] = None, org_id: str = "ORG-TALENT-01") -> Dict[str, Any]:
    """
    Validates and imports a dataset (DataFrame or list of dicts) into SQLite.
    Supports flexible column aliases, duplicate skipping, data type coercion,
    and comprehensive row-by-row error reporting.
    """
    if df is None:
        return {"success_count": 0, "skipped_count": 0, "total": 0, "errors": ["No dataset provided."], "imported_ids": []}

    records = df.to_dict(orient="records") if hasattr(df, "to_dict") else list(df)
    if not records:
        return {"success_count": 0, "skipped_count": 0, "total": 0, "errors": ["Uploaded dataset contains 0 records."], "imported_ids": []}

    col_aliases = {
        "employee_id": ["employee_id", "employee id", "empid", "emp_id", "id", "code"],
        "name": ["name", "employee_name", "employee name", "full_name", "fullname"],
        "email": ["email", "corporate_email", "email_address", "work_email"],
        "phone": ["phone", "contact", "mobile", "telephone", "phone_number"],
        "department": ["department", "dept", "business_unit"],
        "designation": ["designation", "role", "job_title", "title", "position"],
        "years_experience": ["years_experience", "years of experience", "experience", "exp", "years_exp", "years"],
        "primary_skills": ["primary_skills", "skills", "primary skills", "core_skills", "competencies"],
        "employment_status": ["employment_status", "status", "employment status"],
        "joining_date": ["joining_date", "joining date", "join_date", "doj", "date_of_joining"]
    }

    success_count = 0
    skipped_count = 0
    errors: List[str] = []
    imported_ids: List[str] = []

    for idx, row in enumerate(records, start=1):
        normalized_row = {}
        row_keys_lower = {str(k).strip().lower(): k for k in row.keys()}
        for std_key, aliases in col_aliases.items():
            for alias in aliases:
                if alias in row_keys_lower:
                    orig_key = row_keys_lower[alias]
                    val = row[orig_key]
                    if pd.notna(val) if hasattr(pd, "notna") else (val is not None and str(val).lower() != "nan"):
                        normalized_row[std_key] = str(val).strip()
                    break

        emp_id = normalized_row.get("employee_id", "").strip().upper()
        name = normalized_row.get("name", "").strip()
        email = normalized_row.get("email", None)
        if email:
            email = email.strip() or None
        phone = normalized_row.get("phone", "").strip()
        department = normalized_row.get("department", "Engineering").strip()
        designation = normalized_row.get("designation", "Software Engineer").strip()
        skills = normalized_row.get("primary_skills", "").strip()
        status = normalized_row.get("employment_status", "Active").strip()
        joining_date = normalized_row.get("joining_date", date.today().isoformat()).strip()

        try:
            exp_val = float(normalized_row.get("years_experience", 0.0))
        except (ValueError, TypeError):
            exp_val = 0.0

        if not emp_id or not name or not skills:
            skipped_count += 1
            errors.append(f"Row {idx}: Missing required fields (Employee ID, Name, or Skills).")
            continue

        ok, msg = add_employee(
            employee_id=emp_id,
            name=name,
            department=department,
            designation=designation,
            years_experience=exp_val,
            primary_skills=skills,
            email=email,
            phone=phone,
            joining_date=joining_date,
            employment_status=status if status in EMPLOYMENT_STATUSES else "Active",
            created_by=created_by,
            org_id=org_id
        )

        if ok:
            success_count += 1
            imported_ids.append(emp_id)
        else:
            skipped_count += 1
            errors.append(f"Row {idx} ({emp_id} - {name}): {msg}")

    return {
        "success_count": success_count,
        "skipped_count": skipped_count,
        "total": len(records),
        "errors": errors,
        "imported_ids": imported_ids
    }

def get_employees(
    search_query: Optional[str] = None,
    department_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    designation_filter: Optional[str] = None,
    created_by: Optional[int] = None,
    org_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT e.id, e.employee_id, e.org_id, e.user_id, e.name, e.email, e.phone, e.department, e.designation,
                   e.joining_date, e.employment_status, e.years_experience, e.primary_skills,
                   e.account_status, e.created_by, e.created_at, e.updated_at,
                   COALESCE(o.name, 'Talent Growth Technologies') as org_name,
                   ROUND(AVG(pr.performance_score), 2) as avg_rating,
                   COUNT(pr.id) as review_count
            FROM employees e
            LEFT JOIN organizations o ON e.org_id = o.org_id
            LEFT JOIN performance_reviews pr ON e.employee_id = pr.employee_id
            WHERE 1=1
        """
        params: List[Any] = []

        if org_id:
            query += " AND e.org_id = ?"
            params.append(org_id.strip().upper())

        if department_filter and department_filter != "All Departments":
            query += " AND e.department = ?"
            params.append(department_filter)

        if designation_filter and designation_filter != "All Designations":
            query += " AND e.designation = ?"
            params.append(designation_filter)

        if status_filter and status_filter != "All Statuses":
            query += " AND e.employment_status = ?"
            params.append(status_filter)

        if search_query:
            query += " AND (LOWER(e.name) LIKE ? OR LOWER(e.employee_id) LIKE ? OR LOWER(e.designation) LIKE ? OR LOWER(e.primary_skills) LIKE ? OR LOWER(e.email) LIKE ?)"
            pattern = f"%{search_query.strip().lower()}%"
            params.extend([pattern, pattern, pattern, pattern, pattern])

        if created_by is not None:
            query += " AND (e.created_by = ? OR e.created_by IS NULL)"
            params.append(created_by)

        query += " GROUP BY e.id ORDER BY e.id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()

def get_employee_by_id(employee_id: Any, org_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        emp_str = str(employee_id).strip()
        query = """
            SELECT e.id, e.employee_id, e.org_id, e.user_id, e.name, e.email, e.phone, e.department, e.designation,
                   e.joining_date, e.employment_status, e.years_experience, e.primary_skills,
                   e.account_status, e.created_by, e.created_at, e.updated_at,
                   COALESCE(o.name, 'Talent Growth Technologies') as org_name,
                   ROUND(AVG(pr.performance_score), 2) as avg_rating
            FROM employees e
            LEFT JOIN organizations o ON e.org_id = o.org_id
            LEFT JOIN performance_reviews pr ON e.employee_id = pr.employee_id
            WHERE (e.employee_id = ? OR UPPER(e.employee_id) = ? OR e.id = ?)
        """
        params: List[Any] = [emp_str, emp_str.upper(), emp_str]
        if org_id:
            query += " AND e.org_id = ?"
            params.append(org_id.strip().upper())
        query += " GROUP BY e.id"
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception:
        return None
    finally:
        conn.close()

def update_employee(
    employee_id: str,
    name: str,
    department: str,
    designation: str,
    years_experience: float,
    primary_skills: str,
    email: Optional[str] = None,
    phone: Optional[str] = "",
    joining_date: Optional[str] = "",
    employment_status: str = "Active",
    account_status: str = "Active",
    org_id: Optional[str] = None
) -> Tuple[bool, str]:
    employee_id = (employee_id or "").strip().upper()
    name = (name or "").strip()
    department = (department or "").strip()
    designation = (designation or "").strip()
    primary_skills = (primary_skills or "").strip()
    email = (email or "").strip().lower() if email else None
    phone = (phone or "").strip()
    joining_date = (joining_date or "").strip()
    employment_status = employment_status if employment_status in EMPLOYMENT_STATUSES else "Active"
    account_status = account_status if account_status in ["Active", "On Leave", "Terminated", "Suspended"] else "Active"

    if not employee_id:
        return False, "Employee ID is required."
    if not name:
        return False, "Employee Name is required."
    if not department or department == "Select Department":
        return False, "Department is required."
    if not designation:
        return False, "Designation is required."
    if not primary_skills:
        return False, "Primary Skills are required."

    try:
        years_exp = float(years_experience)
        if years_exp < 0 or years_exp > 60:
            return False, "Years of Experience must be between 0 and 60."
    except (ValueError, TypeError):
        return False, "Years of Experience must be a valid number."

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            query = """
                UPDATE employees
                SET name = ?, email = ?, phone = ?, department = ?, designation = ?,
                    joining_date = ?, employment_status = ?, years_experience = ?,
                    primary_skills = ?, account_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE employee_id = ?
            """
            params = [name, email, phone, department, designation, joining_date, employment_status, years_exp, primary_skills, account_status, employee_id]
            if org_id:
                query += " AND org_id = ?"
                params.append(org_id.strip().upper())
            cursor.execute(query, params)
            if cursor.rowcount == 0:
                return False, f"Employee with ID '{employee_id}' not found or permission denied."
        return True, f"Employee '{employee_id}' updated successfully!"
    except Exception as e:
        return False, f"Database error during update: {e}"
    finally:
        conn.close()

def delete_employee(employee_id: str, org_id: Optional[str] = None) -> Tuple[bool, str]:
    employee_id = (employee_id or "").strip().upper()
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            query = "DELETE FROM employees WHERE employee_id = ?"
            params = [employee_id]
            if org_id:
                query += " AND org_id = ?"
                params.append(org_id.strip().upper())
            cursor.execute(query, params)
            if cursor.rowcount == 0:
                return False, f"Employee '{employee_id}' not found or permission denied."
        return True, f"Employee '{employee_id}' and all associated records deleted successfully."
    except Exception as e:
        return False, f"Database error during deletion: {e}"
    finally:
        conn.close()

def get_all_departments(org_id: Optional[str] = None) -> List[str]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if org_id:
            cursor.execute("SELECT DISTINCT department FROM employees WHERE department IS NOT NULL AND department != '' AND org_id = ?", (org_id.strip().upper(),))
        else:
            cursor.execute("SELECT DISTINCT department FROM employees WHERE department IS NOT NULL AND department != ''")
        db_depts = [row["department"] for row in cursor.fetchall()]
        combined = sorted(list(set(STANDARD_DEPARTMENTS + db_depts)))
        return combined
    finally:
        conn.close()

# ----------------- Performance Management -----------------

def add_performance_review(
    employee_id: str,
    review_period: str,
    performance_score: float,
    achievements: str = "",
    strengths: str = "",
    improvements: str = "",
    manager_feedback: str = "",
    reviewer_id: Optional[int] = None,
    org_id: Optional[str] = None
) -> Tuple[bool, str]:
    employee_id = (employee_id or "").strip().upper()
    review_period = (review_period or "").strip()

    if not employee_id:
        return False, "Employee ID is required."
    if not review_period:
        return False, "Review Period is required (e.g. Q1 2026 or Annual 2025)."

    try:
        score = float(performance_score)
        if score < 1.0 or score > 5.0:
            return False, "Performance rating must be between 1.0 (Needs Improvement) and 5.0 (Exceptional)."
    except (ValueError, TypeError):
        return False, "Performance score must be a valid number."

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            if org_id:
                cursor.execute("SELECT id, org_id FROM employees WHERE employee_id = ? AND org_id = ?", (employee_id, org_id.strip().upper()))
            else:
                cursor.execute("SELECT id, org_id FROM employees WHERE employee_id = ?", (employee_id,))
            emp = cursor.fetchone()
            if not emp:
                return False, f"Employee ID '{employee_id}' not found or access denied."
            final_org_id = emp["org_id"] or org_id or "ORG-TALENT-01"

            cursor.execute(
                """
                INSERT INTO performance_reviews (employee_id, org_id, review_period, performance_score, achievements, strengths, improvements, manager_feedback, reviewer_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (employee_id, final_org_id, review_period, score, achievements, strengths, improvements, manager_feedback, reviewer_id)
            )
        return True, f"Performance review for '{employee_id}' ({review_period}) recorded successfully!"
    except Exception as e:
        return False, f"Error saving performance review: {e}"
    finally:
        conn.close()

def get_performance_reviews(employee_id: Optional[str] = None, org_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT pr.*, e.name as employee_name, e.department, e.designation, u.name as reviewer_name,
                   COALESCE(pr.org_id, e.org_id, 'ORG-TALENT-01') as org_id
            FROM performance_reviews pr
            JOIN employees e ON pr.employee_id = e.employee_id
            LEFT JOIN users u ON pr.reviewer_id = u.id
            WHERE 1=1
        """
        params: List[Any] = []
        if employee_id:
            query += " AND pr.employee_id = ?"
            params.append(employee_id.strip().upper())
        if org_id:
            query += " AND (pr.org_id = ? OR e.org_id = ?)"
            params.extend([org_id.strip().upper(), org_id.strip().upper()])
        query += " ORDER BY pr.created_at DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()

def get_department_performance_summary(org_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT e.department,
                   COUNT(DISTINCT e.id) as employee_count,
                   ROUND(AVG(pr.performance_score), 2) as avg_score,
                   COUNT(pr.id) as total_reviews
            FROM employees e
            LEFT JOIN performance_reviews pr ON e.employee_id = pr.employee_id
            WHERE 1=1
        """
        params: List[Any] = []
        if org_id:
            query += " AND e.org_id = ?"
            params.append(org_id.strip().upper())
        query += " GROUP BY e.department ORDER BY avg_score DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()

# ----------------- Skill Management & Gap Analysis -----------------

def add_employee_skill(
    employee_id: str,
    skill_name: str,
    proficiency_level: str,
    category: str = "Technical",
    years_exp: float = 1.0,
    org_id: Optional[str] = None,
    user_id: Optional[int] = None
) -> Tuple[bool, str]:
    employee_id = (employee_id or "").strip().upper()
    skill_name = (skill_name or "").strip()

    if not employee_id:
        return False, "Employee ID is required."
    if not skill_name:
        return False, "Skill name is required."
    if proficiency_level not in LEVELS:
        return False, f"Invalid proficiency. Choose from: {', '.join(LEVELS.keys())}."

    try:
        years_exp = float(years_exp)
        if years_exp < 0:
            return False, "Years of experience cannot be negative."
    except (ValueError, TypeError):
        return False, "Years must be a valid number."

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, org_id, user_id FROM employees WHERE employee_id = ?", (employee_id,))
            emp = cursor.fetchone()
            resolved_org = (org_id or (emp["org_id"] if emp else "ORG-TALENT-01")).strip().upper()
            resolved_uid = user_id or (emp["user_id"] if emp else None)

            cursor.execute(
                "SELECT id FROM employee_skills WHERE employee_id = ? AND LOWER(skill_name) = LOWER(?)",
                (employee_id, skill_name)
            )
            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    """
                    UPDATE employee_skills
                    SET proficiency_level = ?, category = ?, years_exp = ?, org_id = ?, user_id = COALESCE(?, user_id), last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (proficiency_level, category, years_exp, resolved_org, resolved_uid, existing["id"])
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO employee_skills (employee_id, org_id, user_id, skill_name, category, proficiency_level, years_exp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (employee_id, resolved_org, resolved_uid, skill_name, category, proficiency_level, years_exp)
                )

            # Keep legacy skills table synchronized if user_id is resolved
            if resolved_uid:
                cursor.execute("SELECT id FROM skills WHERE user_id = ? AND LOWER(name) = LOWER(?)", (resolved_uid, skill_name))
                s_exist = cursor.fetchone()
                if s_exist:
                    cursor.execute(
                        "UPDATE skills SET proficiency = ?, category = ?, years = ? WHERE id = ?",
                        (proficiency_level, category, years_exp, s_exist["id"])
                    )
                else:
                    cursor.execute(
                        "INSERT INTO skills (user_id, name, category, proficiency, years) VALUES (?, ?, ?, ?, ?)",
                        (resolved_uid, skill_name, category, proficiency_level, years_exp)
                    )
            return True, f"Skill '{skill_name}' saved for {employee_id}."
    except Exception as e:
        return False, f"Database error adding skill: {e}"
    finally:
        conn.close()

def get_employee_skills(employee_id: str, org_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        emp_id_clean = employee_id.strip().upper()
        if org_id:
            cursor.execute("SELECT org_id FROM employees WHERE employee_id = ?", (emp_id_clean,))
            emp = cursor.fetchone()
            if not emp or emp["org_id"].upper() != org_id.strip().upper():
                return []
        cursor.execute(
            """
            SELECT id, employee_id, org_id, user_id, skill_name, category, proficiency_level, years_exp, last_updated
            FROM employee_skills
            WHERE employee_id = ?
            ORDER BY id DESC
            """,
            (emp_id_clean,)
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def delete_employee_skill(skill_id: int, employee_id: Optional[str] = None, org_id: Optional[str] = None) -> bool:
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            if org_id and employee_id:
                cursor.execute(
                    "DELETE FROM employee_skills WHERE id = ? AND employee_id = ? AND org_id = ?",
                    (skill_id, employee_id.strip().upper(), org_id.strip().upper())
                )
            elif employee_id:
                cursor.execute("DELETE FROM employee_skills WHERE id = ? AND employee_id = ?", (skill_id, employee_id.strip().upper()))
            else:
                cursor.execute("DELETE FROM employee_skills WHERE id = ?", (skill_id,))
            return cursor.rowcount > 0
    finally:
        conn.close()

def get_employee_skill_gaps(employee_id: str, target_role: str, org_id: Optional[str] = None) -> Dict[str, Any]:
    skills = get_employee_skills(employee_id, org_id=org_id)
    emp_skills_map = {s["skill_name"].strip().lower(): LEVELS.get(s["proficiency_level"], 1) for s in skills}

    if not target_role or target_role not in ROLE_CATALOG:
        return {"gaps": [], "match_percentage": 0, "recommendations": []}

    role_info = ROLE_CATALOG[target_role]
    required_skills = role_info["skills"]

    gaps = []
    match_scores = []
    for req_name, req_level in required_skills.items():
        curr_level = emp_skills_map.get(req_name.strip().lower(), 0)
        gap = max(0, req_level - curr_level)
        match_scores.append(min(1.0, curr_level / max(1, req_level)))
        priority = "High" if gap >= 2 or curr_level == 0 else ("Medium" if gap == 1 else "Met")
        gaps.append({
            "skill": req_name,
            "current_level": curr_level,
            "required_level": req_level,
            "gap": gap,
            "priority": priority
        })

    match_percent = round((sum(match_scores) / len(match_scores)) * 100) if match_scores else 0
    order = {"High": 0, "Medium": 1, "Met": 2}
    gaps.sort(key=lambda x: order.get(x["priority"], 3))

    return {
        "gaps": gaps,
        "match_percentage": match_percent,
        "criteria": role_info["criteria"],
        "recommended_training": role_info.get("recommended_training", [])
    }

# ----------------- Career Development & Goal Tracking -----------------

ALLOWED_PROGRESS = [0, 25, 50, 75, 100]

def calculate_goal_status(progress: int, target_date_str: Optional[str] = None) -> str:
    if progress >= 100:
        return "Completed"
    if target_date_str:
        try:
            target_d = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            if target_d < date.today() and progress < 100:
                return "Overdue"
        except Exception:
            pass
    if progress > 0:
        return "In Progress"
    return "Not Started"

def add_goal(
    user_id: int,
    title: str,
    description: str,
    target_date: str,
    progress: int = 0,
    employee_id: Optional[str] = None,
    target_designation: str = "",
    org_id: Optional[str] = None
) -> Tuple[bool, str]:
    title = (title or "").strip()
    description = (description or "").strip()
    target_date = (target_date or "").strip()
    target_designation = (target_designation or "").strip()

    if not title:
        return False, "Goal title is required."
    if not target_date:
        return False, "Target completion date is required."

    try:
        progress = int(progress)
        if progress not in ALLOWED_PROGRESS:
            return False, f"Progress must be one of: {ALLOWED_PROGRESS}."
    except (ValueError, TypeError):
        return False, "Invalid progress value."

    status = calculate_goal_status(progress, target_date)

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            resolved_org = org_id
            if not resolved_org:
                cursor.execute("SELECT org_id FROM users WHERE id = ?", (user_id,))
                urow = cursor.fetchone()
                if urow and urow["org_id"]:
                    resolved_org = urow["org_id"]
                elif employee_id:
                    cursor.execute("SELECT org_id FROM employees WHERE employee_id = ?", (employee_id.strip().upper(),))
                    erow = cursor.fetchone()
                    if erow and erow["org_id"]:
                        resolved_org = erow["org_id"]
            resolved_org = (resolved_org or "ORG-TALENT-01").strip().upper()

            cursor.execute(
                """
                INSERT INTO career_goals (user_id, employee_id, org_id, title, target_designation, description, target_date, progress, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, employee_id, resolved_org, title, target_designation, description, target_date, progress, status)
            )
            # Maintain backward compatibility in goals table
            cursor.execute(
                """
                INSERT INTO goals (user_id, employee_id, title, description, target_date, progress, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, employee_id, title, description, target_date, progress, status)
            )
        return True, f"Career goal '{title}' created successfully!"
    except Exception as e:
        return False, f"Database error while creating goal: {e}"
    finally:
        conn.close()

def get_goals(
    user_id: Optional[int] = None,
    employee_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    org_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT id, user_id, employee_id, org_id, title, target_designation, description, target_date, progress, status, created_at, updated_at FROM career_goals WHERE 1=1"
        params: List[Any] = []

        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        elif employee_id is not None:
            query += " AND employee_id = ?"
            params.append(employee_id.strip().upper())

        if org_id:
            query += " AND org_id = ?"
            params.append(org_id.strip().upper())

        if status_filter and status_filter != "All Statuses":
            query += " AND status = ?"
            params.append(status_filter)

        query += " ORDER BY target_date ASC, id DESC"
        cursor.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        # Recalculate Overdue status dynamically
        for r in rows:
            r["status"] = calculate_goal_status(r["progress"], r["target_date"])
        return rows
    finally:
        conn.close()

def get_goal_by_id(goal_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if user_id is not None:
            cursor.execute("SELECT * FROM career_goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
        else:
            cursor.execute("SELECT * FROM career_goals WHERE id = ?", (goal_id,))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            d["status"] = calculate_goal_status(d["progress"], d["target_date"])
            return d
        return None
    finally:
        conn.close()

def update_goal(
    goal_id: int,
    user_id: int,
    title: str,
    description: str,
    target_date: str,
    progress: int,
    target_designation: str = ""
) -> Tuple[bool, str]:
    title = (title or "").strip()
    description = (description or "").strip()
    target_date = (target_date or "").strip()

    if not title:
        return False, "Goal title cannot be empty."
    if not target_date:
        return False, "Target date is required."

    try:
        progress = int(progress)
        if progress not in ALLOWED_PROGRESS:
            return False, f"Progress must be one of: {ALLOWED_PROGRESS}."
    except (ValueError, TypeError):
        return False, "Invalid progress value."

    status = calculate_goal_status(progress, target_date)

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE career_goals
                SET title = ?, target_designation = ?, description = ?, target_date = ?, progress = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
                """,
                (title, target_designation, description, target_date, progress, status, goal_id, user_id)
            )
            if cursor.rowcount == 0:
                return False, "Goal not found or permission denied."
        return True, "Goal updated successfully!"
    except Exception as e:
        return False, f"Database error during goal update: {e}"
    finally:
        conn.close()

def update_goal_progress(goal_id: int, user_id: int, progress: int) -> Tuple[bool, str]:
    try:
        progress = int(progress)
        if progress not in ALLOWED_PROGRESS:
            return False, f"Progress must be one of: {ALLOWED_PROGRESS}."
    except (ValueError, TypeError):
        return False, "Invalid progress value."

    goal = get_goal_by_id(goal_id, user_id)
    if not goal:
        return False, "Goal not found or permission denied."

    status = calculate_goal_status(progress, goal["target_date"])

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE career_goals
                SET progress = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
                """,
                (progress, status, goal_id, user_id)
            )
        return True, f"Goal progress updated to {progress}% ({status})."
    except Exception as e:
        return False, f"Database error during progress update: {e}"
    finally:
        conn.close()

def delete_goal(goal_id: int, user_id: int) -> Tuple[bool, str]:
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM career_goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
            r1 = cursor.rowcount
            cursor.execute("DELETE FROM goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
            r2 = cursor.rowcount
            if r1 == 0 and r2 == 0:
                return False, "Goal not found or permission denied."
        return True, "Career goal deleted successfully."
    except Exception as e:
        return False, f"Database error during goal deletion: {e}"
    finally:
        conn.close()

def get_goal_stats(
    user_id: Optional[int] = None,
    employee_id: Optional[str] = None,
    org_id: Optional[str] = None
) -> Dict[str, Any]:
    goals = get_goals(user_id=user_id, employee_id=employee_id, org_id=org_id)
    total = len(goals)
    if total == 0:
        return {"total": 0, "completed": 0, "in_progress": 0, "not_started": 0, "overdue": 0, "avg_progress": 0}

    completed = sum(1 for g in goals if g["status"] == "Completed")
    in_prog = sum(1 for g in goals if g["status"] == "In Progress")
    not_started = sum(1 for g in goals if g["status"] == "Not Started")
    overdue = sum(1 for g in goals if g["status"] == "Overdue")
    avg_prog = round(sum(g["progress"] for g in goals) / total)

    return {
        "total": total,
        "completed": completed,
        "in_progress": in_prog,
        "not_started": not_started,
        "overdue": overdue,
        "avg_progress": avg_prog
    }

# ----------------- Training Records -----------------

def add_training_record(
    employee_id: str,
    course_name: str,
    target_skill: str,
    provider: str = "Internal Academy",
    target_completion_date: str = "",
    status: str = "Enrolled",
    score: float = 0.0,
    org_id: Optional[str] = None
) -> Tuple[bool, str]:
    employee_id = (employee_id or "").strip().upper()
    course_name = (course_name or "").strip()
    target_skill = (target_skill or "").strip()

    if not employee_id or not course_name or not target_skill:
        return False, "Employee ID, Course Name, and Target Skill are required."

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            resolved_org = org_id
            if not resolved_org:
                cursor.execute("SELECT org_id FROM employees WHERE employee_id = ?", (employee_id,))
                erow = cursor.fetchone()
                if erow and erow["org_id"]:
                    resolved_org = erow["org_id"]
            resolved_org = (resolved_org or "ORG-TALENT-01").strip().upper()

            cursor.execute(
                """
                INSERT INTO training_records (employee_id, org_id, course_name, provider, target_skill, target_completion_date, status, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (employee_id, resolved_org, course_name, provider, target_skill, target_completion_date, status, score)
            )
        return True, f"Training course '{course_name}' assigned to {employee_id}."
    except Exception as e:
        return False, f"Database error adding training: {e}"
    finally:
        conn.close()

def get_training_records(employee_id: Optional[str] = None, org_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT tr.*, e.name as employee_name, e.department,
                   COALESCE(tr.org_id, e.org_id, 'ORG-TALENT-01') as org_id
            FROM training_records tr
            JOIN employees e ON tr.employee_id = e.employee_id
            WHERE 1=1
        """
        params: List[Any] = []
        if employee_id:
            query += " AND tr.employee_id = ?"
            params.append(employee_id.strip().upper())
        if org_id:
            query += " AND (tr.org_id = ? OR e.org_id = ?)"
            params.extend([org_id.strip().upper(), org_id.strip().upper()])
        query += " ORDER BY tr.id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

# ----------------- Legacy Profile, Skills & Analysis Support -----------------

def get_profile(uid: Optional[int] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
    target_id = uid if uid is not None else user_id
    if target_id is None:
        target_id = 1
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE user_id = ?", (target_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        try:
            with conn:
                conn.execute("INSERT OR IGNORE INTO profiles (user_id) VALUES (?)", (target_id,))
            cursor.execute("SELECT * FROM profiles WHERE user_id = ?", (target_id,))
            res = cursor.fetchone()
            return dict(res) if res else {}
        except Exception:
            return {}
    finally:
        conn.close()

def save_profile(uid: Optional[int] = None, data: Optional[Dict[str, Any]] = None, user_id: Optional[int] = None) -> bool:
    target_id = uid if uid is not None else user_id
    if target_id is None:
        target_id = 1
    data = data or {}
    allowed_cols = {
        "phone", "location", "job_title", "company", "department", "industry",
        "employment_type", "years_experience", "linkedin", "github", "portfolio",
        "education", "certifications", "summary", "experience", "projects",
        "resume_text", "target_role", "target_level", "timeline", "target_industry",
        "career_goal"
    }
    updates = {k: v for k, v in data.items() if k in allowed_cols}
    if not updates:
        return True

    set_clause = ", ".join(f"{col} = ?" for col in updates.keys())
    values = list(updates.values()) + [target_id]

    conn = get_connection()
    try:
        with conn:
            conn.execute(
                f"UPDATE profiles SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                values
            )
        return True
    finally:
        conn.close()

def list_skills(uid: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category, proficiency, years, COALESCE(description, '') as description, created_at FROM skills WHERE user_id = ? ORDER BY id DESC", (uid,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def add_skill(uid: int, name: str, category: str, proficiency: str, years: float, description: str = "") -> Tuple[bool, str]:
    name = (name or "").strip()
    category = (category or "Technical").strip()
    description = (description or "").strip()
    if not name:
        return False, "Skill name cannot be empty."
    if proficiency not in LEVELS:
        return False, f"Invalid proficiency. Choose from: {', '.join(LEVELS.keys())}."
    try:
        years = float(years)
        if years < 0:
            return False, "Years of experience cannot be negative."
    except (ValueError, TypeError):
        return False, "Years must be a valid number."

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM skills WHERE user_id = ? AND LOWER(name) = LOWER(?)", (uid, name))
            if cursor.fetchone():
                return False, f"Skill '{name}' is already in your profile."
            cursor.execute(
                "INSERT INTO skills (user_id, name, category, proficiency, years, description) VALUES (?, ?, ?, ?, ?, ?)",
                (uid, name, category, proficiency, years, description)
            )
        return True, f"Skill '{name}' added successfully."
    except Exception as e:
        return False, f"Error saving skill: {e}"
    finally:
        conn.close()

def update_skill(uid: int, skill_id: int, proficiency: str, years: float, category: Optional[str] = None, description: Optional[str] = None) -> Tuple[bool, str]:
    if proficiency not in LEVELS:
        return False, f"Invalid proficiency. Choose from: {', '.join(LEVELS.keys())}."
    try:
        years = float(years)
        if years < 0:
            return False, "Years of experience cannot be negative."
    except (ValueError, TypeError):
        return False, "Years must be a valid number."

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            fields = ["proficiency = ?", "years = ?"]
            vals = [proficiency, years]
            if category:
                fields.append("category = ?")
                vals.append(category.strip())
            if description is not None:
                fields.append("description = ?")
                vals.append(description.strip())
            vals.extend([skill_id, uid])
            query = f"UPDATE skills SET {', '.join(fields)} WHERE id = ? AND user_id = ?"
            cursor.execute(query, vals)
            if cursor.rowcount == 0:
                return False, "Skill not found or access denied."
        return True, "Skill updated successfully."
    except Exception as e:
        return False, f"Error updating skill: {e}"
    finally:
        conn.close()

def delete_skill(uid: int, skill_id: int) -> bool:
    conn = get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM skills WHERE id = ? AND user_id = ?", (skill_id, uid))
        return True
    finally:
        conn.close()

def add_assessment(
    uid: Optional[int] = None,
    category: str = "Technical",
    score: float = 0.0,
    employee_id: Optional[str] = None,
    org_id: Optional[str] = None,
    skill_name: str = "",
    notes: str = ""
) -> bool:
    category = (category or "Technical").strip()
    skill_name = (skill_name or "").strip()
    notes = (notes or "").strip()
    try:
        score = float(score)
    except (ValueError, TypeError):
        score = 0.0

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            resolved_uid = uid
            resolved_emp_id = (employee_id or "").strip().upper() if employee_id else None
            resolved_org = (org_id or "").strip().upper() if org_id else None

            if not resolved_uid and resolved_emp_id:
                cursor.execute("SELECT user_id, org_id FROM employees WHERE employee_id = ?", (resolved_emp_id,))
                erow = cursor.fetchone()
                if erow:
                    resolved_uid = erow["user_id"]
                    resolved_org = resolved_org or erow["org_id"]
                if not resolved_uid:
                    cursor.execute("SELECT id, org_id FROM users WHERE employee_id = ?", (resolved_emp_id,))
                    urow = cursor.fetchone()
                    if urow:
                        resolved_uid = urow["id"]
                        resolved_org = resolved_org or urow["org_id"]

            if not resolved_emp_id and resolved_uid:
                cursor.execute("SELECT employee_id, org_id FROM users WHERE id = ?", (resolved_uid,))
                urow = cursor.fetchone()
                if urow:
                    resolved_emp_id = urow["employee_id"]
                    resolved_org = resolved_org or urow["org_id"]

            if not resolved_uid:
                resolved_uid = 1

            resolved_org = resolved_org or "ORG-TALENT-01"
            cursor.execute(
                """
                INSERT INTO assessments (user_id, employee_id, org_id, category, skill_name, score, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (resolved_uid, resolved_emp_id, resolved_org, category, skill_name, score, notes)
            )
        return True
    except Exception:
        return False
    finally:
        conn.close()

def get_assessments(
    uid: Optional[int] = None,
    employee_id: Optional[str] = None,
    org_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT a.id, a.user_id, a.employee_id, a.org_id, a.category, a.skill_name, a.score, a.notes, a.created_at,
                   u.name as user_name, e.name as employee_name
            FROM assessments a
            LEFT JOIN users u ON a.user_id = u.id
            LEFT JOIN employees e ON a.employee_id = e.employee_id
            WHERE 1=1
        """
        params: List[Any] = []
        if uid is not None:
            query += " AND a.user_id = ?"
            params.append(uid)
        elif employee_id is not None:
            query += " AND a.employee_id = ?"
            params.append(employee_id.strip().upper())

        if org_id:
            query += " AND (a.org_id = ? OR e.org_id = ?)"
            params.extend([org_id.strip().upper(), org_id.strip().upper()])

        query += " ORDER BY a.created_at DESC, a.id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def save_progress(uid: int, item: str, percent: float) -> bool:
    item = (item or "").strip()
    if not item:
        return False
    percent = max(0.0, min(100.0, float(percent)))
    status = "Completed" if percent >= 100 else ("Not Started" if percent == 0 else "In Progress")

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM progress WHERE user_id = ? AND LOWER(item) = LOWER(?)", (uid, item))
            existing = cursor.fetchone()
            if existing:
                conn.execute(
                    "UPDATE progress SET percent = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (percent, status, existing["id"])
                )
            else:
                conn.execute(
                    "INSERT INTO progress (user_id, item, percent, status) VALUES (?, ?, ?, ?)",
                    (uid, item, percent, status)
                )
        return True
    finally:
        conn.close()

def get_progress(uid: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, item, percent, status, updated_at FROM progress WHERE user_id = ? ORDER BY updated_at DESC", (uid,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def profile_completion(profile: Dict[str, Any], skills: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
    checkpoints = [
        ("Current job title", bool(profile.get("job_title"))),
        ("Department & Company", bool(profile.get("department") or profile.get("company"))),
        ("Years of experience", float(profile.get("years_experience") or 0) > 0),
        ("Professional summary", bool(profile.get("summary"))),
        ("Detailed experience", bool(profile.get("experience"))),
        ("Education background", bool(profile.get("education"))),
        ("Target career role", bool(profile.get("target_role"))),
        ("Skills added (at least 3)", len(skills) >= 3),
        ("Contact details", bool(profile.get("phone") or profile.get("location"))),
        ("Portfolio/LinkedIn links", bool(profile.get("linkedin") or profile.get("github") or profile.get("portfolio")))
    ]
    completed = sum(1 for _, ok in checkpoints if ok)
    total = len(checkpoints)
    percent = round((completed / total) * 100)
    missing = [name for name, ok in checkpoints if not ok]
    return percent, missing

def role_match(target_role: str, skills: List[Dict[str, Any]], years_experience: float = 0.0) -> int:
    if not target_role or target_role not in ROLE_CATALOG:
        return 0
    role_info = ROLE_CATALOG[target_role]
    required_skills = role_info["skills"]
    min_exp = role_info["min_exp"]

    user_skills_map = {s["name"].strip().lower(): LEVELS.get(s["proficiency"], 1) for s in skills}

    match_scores = []
    for req_name, req_level in required_skills.items():
        curr_level = user_skills_map.get(req_name.strip().lower(), 0)
        skill_score = min(1.0, curr_level / max(1, req_level))
        match_scores.append(skill_score)

    skills_fit = (sum(match_scores) / len(match_scores)) if match_scores else 0.0
    exp_fit = min(1.0, float(years_experience) / max(0.5, min_exp))

    overall = (skills_fit * 0.75) + (exp_fit * 0.25)
    return max(0, min(100, round(overall * 100)))

def gap_analysis(target_role: str, skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not target_role or target_role not in ROLE_CATALOG:
        return []
    required_skills = ROLE_CATALOG[target_role]["skills"]
    user_skills_map = {s["name"].strip().lower(): LEVELS.get(s["proficiency"], 1) for s in skills}

    gaps = []
    for req_name, req_level in required_skills.items():
        curr_level = user_skills_map.get(req_name.strip().lower(), 0)
        gap = max(0, req_level - curr_level)
        if gap == 0:
            priority = "Met"
        elif gap >= 2 or curr_level == 0:
            priority = "High"
        else:
            priority = "Medium"
        gaps.append({
            "skill": req_name,
            "current": curr_level,
            "required": req_level,
            "gap": gap,
            "priority": priority
        })
    order = {"High": 0, "Medium": 1, "Met": 2}
    gaps.sort(key=lambda x: order.get(x["priority"], 3))
    return gaps

def profile_analysis(profile: Dict[str, Any], skills: List[Dict[str, Any]]) -> Dict[str, Any]:
    completion, missing = profile_completion(profile, skills)
    target = profile.get("target_role", "")
    years = float(profile.get("years_experience") or 0)
    match_score = role_match(target, skills, years)

    skill_count_factor = min(1.0, len(skills) / 6.0)
    summary_factor = 1.0 if len(profile.get("summary", "")) > 50 else (0.5 if profile.get("summary") else 0.0)
    exp_factor = 1.0 if len(profile.get("experience", "")) > 50 else (0.5 if profile.get("experience") else 0.0)

    score = round(
        (completion * 0.40) +
        (skill_count_factor * 30) +
        (summary_factor * 15) +
        (exp_factor * 15)
    )
    score = max(5, min(100, score))

    strengths = []
    weaknesses = []

    if len(skills) >= 5:
        strengths.append(f"Comprehensive skill set ({len(skills)} skills cataloged)")
    elif len(skills) > 0:
        strengths.append(f"{len(skills)} skills recorded")
    else:
        weaknesses.append("No technical or domain skills added yet")

    if years >= 3:
        strengths.append(f"Solid career foundation ({years:g} years experience)")
    elif years > 0:
        strengths.append(f"Early career momentum ({years:g} years experience)")
    else:
        weaknesses.append("Years of experience not specified")

    if profile.get("summary"):
        strengths.append("Professional executive summary completed")
    else:
        weaknesses.append("Missing professional executive summary")

    if target:
        strengths.append(f"Clear target role selected: {target}")
    else:
        weaknesses.append("Target role not selected yet")

    return {
        "completion": completion,
        "score": score,
        "match": match_score,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "missing": missing
    }

def recommendations(profile: Dict[str, Any], skills: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    target = profile.get("target_role", "")
    gaps = gap_analysis(target, skills) if target else []
    recs = []

    if not target:
        recs.append({
            "priority": "High Priority",
            "title": "Define Your Target Career Direction",
            "description": "Select a target role under Career Direction to unlock your personalized competency gap analysis and recommended training roadmap."
        })
    elif gaps:
        high_gaps = [g["skill"] for g in gaps if g["priority"] == "High"]
        med_gaps = [g["skill"] for g in gaps if g["priority"] == "Medium"]
        if high_gaps:
            recs.append({
                "priority": "High Priority",
                "title": f"Bridge Priority Skill Gaps ({', '.join(high_gaps[:2])})",
                "description": f"Acquire intermediate to advanced competency in {', '.join(high_gaps)} through structured courses or internal projects."
            })
        if med_gaps:
            recs.append({
                "priority": "Medium Priority",
                "title": f"Advance Practical Competency in {', '.join(med_gaps[:2])}",
                "description": f"Elevate your practical experience in {', '.join(med_gaps)} to meet senior role requirements."
            })

    if not profile.get("summary") or len(profile.get("summary", "")) < 40:
        recs.append({
            "priority": "Medium Priority",
            "title": "Refine Professional Summary",
            "description": "Craft an elevator pitch articulating your core expertise, achievements, and unique engineering/domain value."
        })

    if len(skills) < 4:
        recs.append({
            "priority": "Medium Priority",
            "title": "Expand Your Skills Portfolio",
            "description": "Catalog at least 4-6 technical, domain, and soft skills with verified proficiency ratings and experience durations."
        })

    if not recs:
        recs.append({
            "priority": "Next Step",
            "title": "Maintain Growth & Goal Tracking",
            "description": "Set SMART career milestones, schedule quarterly performance check-ins, and update goal progress regularly."
        })

    return recs

def export_user_data(uid: int) -> Dict[str, Any]:
    user = get_user_by_id(uid)
    profile = get_profile(uid)
    skills = list_skills(uid)
    assessments = get_assessments(uid)
    progress = get_progress(uid)
    goals = get_goals(user_id=uid)
    emp_id = user.get("employee_id") if user else None
    employee = get_employee_by_id(emp_id) if emp_id else None
    reviews = get_performance_reviews(emp_id) if emp_id else []
    trainings = get_training_records(emp_id) if emp_id else []

    return {
        "user": user,
        "employee_profile": employee,
        "profile": profile,
        "skills": skills,
        "assessments": assessments,
        "growth_progress": progress,
        "career_goals": goals,
        "performance_reviews": reviews,
        "training_records": trainings,
        "exported_at": datetime.utcnow().isoformat() + "Z"
    }

# ----------------- Multi-Tenant Dashboard Analytics -----------------

def get_org_dashboard_stats(org_id: str) -> Dict[str, Any]:
    org_id = (org_id or "ORG-TALENT-01").strip().upper()
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Total employees
        try:
            cursor.execute("SELECT COUNT(*) as cnt FROM employees WHERE org_id = ?", (org_id,))
            total_employees = cursor.fetchone()["cnt"]
        except Exception:
            total_employees = 0

        # Active employees
        try:
            cursor.execute("SELECT COUNT(*) as cnt FROM employees WHERE org_id = ? AND employment_status = 'Active' AND account_status = 'Active'", (org_id,))
            active_employees = cursor.fetchone()["cnt"]
        except Exception:
            active_employees = 0

        # Pending / On leave employees
        try:
            cursor.execute("SELECT COUNT(*) as cnt FROM employees WHERE org_id = ? AND (account_status IN ('Pending', 'Pending Approval') OR employment_status = 'On Leave')", (org_id,))
            pending_employees = cursor.fetchone()["cnt"]
        except Exception:
            pending_employees = 0

        # Active invitations
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor.execute("SELECT COUNT(*) as cnt FROM invitation_codes WHERE org_id = ? AND status = 'Active' AND expires_at >= ? AND used_count < max_uses", (org_id, now_str))
            active_invitations = cursor.fetchone()["cnt"]
        except Exception:
            active_invitations = 0

        # Total departments
        try:
            cursor.execute(
                "SELECT COUNT(DISTINCT department) as cnt FROM employees WHERE org_id = ? AND department IS NOT NULL AND department != ''",
                (org_id,)
            )
            total_departments = cursor.fetchone()["cnt"]
        except Exception:
            total_departments = 0

        # Average performance score
        try:
            cursor.execute(
                """
                SELECT ROUND(AVG(pr.performance_score), 2) as avg_score
                FROM performance_reviews pr
                JOIN employees e ON pr.employee_id = e.employee_id
                WHERE e.org_id = ?
                """,
                (org_id,)
            )
            avg_score_row = cursor.fetchone()
            avg_performance = avg_score_row["avg_score"] if (avg_score_row and avg_score_row["avg_score"] is not None) else 0.0
        except Exception:
            avg_performance = 0.0

        # Assessments completed
        try:
            cursor.execute("SELECT COUNT(*) as cnt FROM assessments WHERE org_id = ?", (org_id,))
            total_assessments = cursor.fetchone()["cnt"]
        except Exception:
            total_assessments = 0

        # Employees assessed percentage
        try:
            cursor.execute("SELECT COUNT(DISTINCT employee_id) as cnt FROM assessments WHERE org_id = ?", (org_id,))
            assessed_employees = cursor.fetchone()["cnt"]
            assessment_completion_rate = round((assessed_employees / max(1, total_employees)) * 100) if total_employees else 0
        except Exception:
            assessment_completion_rate = 0

        # Career goals completion rate
        try:
            cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed FROM career_goals WHERE org_id = ?", (org_id,))
            goal_row = cursor.fetchone()
            total_goals = goal_row["total"] if goal_row else 0
            completed_goals = (goal_row["completed"] or 0) if goal_row else 0
            goal_completion_rate = round((completed_goals / max(1, total_goals)) * 100) if total_goals else 0
        except Exception:
            total_goals = 0
            goal_completion_rate = 0

        # Department distribution
        try:
            cursor.execute(
                """
                SELECT department, COUNT(*) as count
                FROM employees
                WHERE org_id = ? AND department IS NOT NULL AND department != ''
                GROUP BY department
                ORDER BY count DESC
                """,
                (org_id,)
            )
            department_distribution = [dict(r) for r in cursor.fetchall()]
        except Exception:
            department_distribution = []

        # Recent joiners
        try:
            cursor.execute(
                """
                SELECT employee_id, name, email, department, designation, joining_date, employment_status, account_status
                FROM employees
                WHERE org_id = ?
                ORDER BY joining_date DESC, id DESC
                LIMIT 5
                """,
                (org_id,)
            )
            recent_joiners = [dict(r) for r in cursor.fetchall()]
        except Exception:
            recent_joiners = []

        # Performance score distribution
        try:
            cursor.execute(
                """
                SELECT
                    SUM(CASE WHEN pr.performance_score >= 4.5 THEN 1 ELSE 0 END) as exceptional,
                    SUM(CASE WHEN pr.performance_score >= 3.5 AND pr.performance_score < 4.5 THEN 1 ELSE 0 END) as exceeds,
                    SUM(CASE WHEN pr.performance_score >= 3.0 AND pr.performance_score < 3.5 THEN 1 ELSE 0 END) as meets,
                    SUM(CASE WHEN pr.performance_score < 3.0 THEN 1 ELSE 0 END) as needs_improvement
                FROM performance_reviews pr
                JOIN employees e ON pr.employee_id = e.employee_id
                WHERE e.org_id = ?
                """,
                (org_id,)
            )
            perf_row = cursor.fetchone()
            performance_distribution = {
                "Exceptional (4.5-5.0)": perf_row["exceptional"] or 0 if perf_row else 0,
                "Exceeds Expectations (3.5-4.4)": perf_row["exceeds"] or 0 if perf_row else 0,
                "Meets Expectations (3.0-3.4)": perf_row["meets"] or 0 if perf_row else 0,
                "Needs Improvement (<3.0)": perf_row["needs_improvement"] or 0 if perf_row else 0,
            }
        except Exception:
            performance_distribution = {
                "Exceptional (4.5-5.0)": 0,
                "Exceeds Expectations (3.5-4.4)": 0,
                "Meets Expectations (3.0-3.4)": 0,
                "Needs Improvement (<3.0)": 0,
            }

        # Organization skill distribution / gap highlights
        try:
            cursor.execute(
                """
                SELECT skill_name, COUNT(*) as count, ROUND(AVG(CASE
                    WHEN proficiency_level = 'Expert' THEN 4
                    WHEN proficiency_level = 'Advanced' THEN 3
                    WHEN proficiency_level = 'Intermediate' THEN 2
                    ELSE 1 END), 1) as avg_level
                FROM employee_skills
                WHERE org_id = ?
                GROUP BY skill_name
                ORDER BY count DESC
                LIMIT 6
                """,
                (org_id,)
            )
            skill_distribution = [dict(r) for r in cursor.fetchall()]
        except Exception:
            skill_distribution = []

        return {
            "org_id": org_id,
            "total_employees": total_employees,
            "active_employees": active_employees,
            "pending_employees": pending_employees,
            "active_invitations": active_invitations,
            "total_departments": total_departments,
            "avg_performance": avg_performance,
            "total_assessments": total_assessments,
            "assessment_completion_rate": assessment_completion_rate,
            "total_goals": total_goals,
            "goal_completion_rate": goal_completion_rate,
            "department_distribution": department_distribution,
            "dept_counts": {d["department"]: d["count"] for d in department_distribution},
            "recent_joiners": recent_joiners,
            "performance_distribution": performance_distribution,
            "skill_distribution": skill_distribution
        }
    except Exception:
        return {
            "org_id": org_id,
            "total_employees": 0,
            "active_employees": 0,
            "pending_employees": 0,
            "active_invitations": 0,
            "total_departments": 0,
            "avg_performance": 0.0,
            "total_assessments": 0,
            "assessment_completion_rate": 0,
            "total_goals": 0,
            "goal_completion_rate": 0,
            "department_distribution": [],
            "dept_counts": {},
            "recent_joiners": [],
            "performance_distribution": {
                "Exceptional (4.5-5.0)": 0,
                "Exceeds Expectations (3.5-4.4)": 0,
                "Meets Expectations (3.0-3.4)": 0,
                "Needs Improvement (<3.0)": 0,
            },
            "skill_distribution": []
        }
    finally:
        conn.close()

def get_employee_dashboard_data(user_id: int, employee_id: Optional[str] = None, org_id: Optional[str] = None) -> Dict[str, Any]:
    user = get_user_by_id(user_id)
    resolved_org = org_id or (user.get("org_id") if user else "ORG-TALENT-01")
    resolved_emp_id = employee_id or (user.get("employee_id") if user else None)

    profile = get_profile(user_id)
    employee = get_employee_by_id(resolved_emp_id, org_id=resolved_org) if resolved_emp_id else None
    skills = get_employee_skills(resolved_emp_id, org_id=resolved_org) if resolved_emp_id else []
    assessments = get_assessments(uid=user_id, employee_id=resolved_emp_id, org_id=resolved_org)
    goals = get_goals(user_id=user_id, employee_id=resolved_emp_id, org_id=resolved_org)
    goal_stats = get_goal_stats(user_id=user_id, employee_id=resolved_emp_id, org_id=resolved_org)
    reviews = get_performance_reviews(employee_id=resolved_emp_id, org_id=resolved_org) if resolved_emp_id else []
    trainings = get_training_records(employee_id=resolved_emp_id, org_id=resolved_org) if resolved_emp_id else []

    legacy_skills = list_skills(user_id)
    if skills:
        all_skills_formatted = [
            {
                "skill_name": s.get("skill_name") or s.get("name") or "Skill",
                "proficiency_level": s.get("proficiency_level") or s.get("proficiency") or "Intermediate",
                "years_exp": s.get("years_exp") or s.get("years") or 0.0,
                "category": s.get("category") or "Technical"
            }
            for s in skills
        ]
    else:
        all_skills_formatted = [
            {
                "skill_name": s.get("name") or s.get("skill_name") or "Skill",
                "proficiency_level": s.get("proficiency") or s.get("proficiency_level") or "Intermediate",
                "years_exp": s.get("years") or s.get("years_exp") or 0.0,
                "category": s.get("category") or "Technical"
            }
            for s in legacy_skills
        ]
    comp_skills = [{"name": s.get("skill_name") or s.get("name"), "proficiency": s.get("proficiency_level") or s.get("proficiency")} for s in all_skills_formatted]

    completion, missing = profile_completion(profile, comp_skills)
    target_role = profile.get("target_role") or (employee.get("designation") if employee else "Senior Software Engineer")
    skill_gaps = get_employee_skill_gaps(resolved_emp_id, target_role, org_id=resolved_org) if resolved_emp_id else {"gaps": [], "match_percentage": 0}

    return {
        "user": user,
        "employee": employee,
        "profile": profile,
        "skills": all_skills_formatted,
        "assessments": assessments,
        "goals": goals,
        "goal_stats": goal_stats,
        "reviews": reviews,
        "trainings": trainings,
        "completion": completion,
        "missing": missing,
        "target_role": target_role,
        "skill_gaps": skill_gaps
    }

# ==============================================================================
# RESUME STUDIO BACKEND OPERATIONS & MULTI-TENANT ISOLATION
# ==============================================================================

def validate_url(url: str) -> bool:
    """Validates URL format (http/https or valid web address). Empty/whitespace is considered valid/optional."""
    url = (url or "").strip()
    if not url:
        return True
    pattern = re.compile(
        r"^(https?:\/\/)?([a-zA-Z0-9\-_]+\.)+[a-zA-Z]{2,}(:\d+)?(\/[^\s]*)?$",
        re.IGNORECASE
    )
    return bool(pattern.match(url))

def validate_date_range(start_date: str, end_date: str, is_current: bool = False) -> Tuple[bool, str]:
    """Validates that start date is not after end date. Supports YYYY-MM-DD, YYYY-MM, or YYYY."""
    if is_current:
        return True, ""
    s = (start_date or "").strip()
    e = (end_date or "").strip()
    if not s or not e:
        return True, ""
    if e.lower() in ["present", "current", "ongoing", "now"]:
        return True, ""

    d1, d2 = None, None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            d1 = datetime.strptime(s, fmt)
            break
        except ValueError:
            pass

    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            d2 = datetime.strptime(e, fmt)
            break
        except ValueError:
            pass

    if d1 and d2:
        if d1 > d2:
            return False, f"Start date ({s}) cannot be after end date ({e})."
    elif s.isdigit() and e.isdigit():
        if int(s) > int(e):
            return False, f"Start year ({s}) cannot be after end year ({e})."

    return True, ""

def get_resume(user_id: int, org_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves the structured resume for an employee with strict multi-tenant authorization.
    If no resume record exists yet, initializes it from the employee's existing profile and skills.
    """
    user = get_user_by_id(user_id)
    if not user:
        return None

    # Strict organization isolation check
    if org_id and user.get("org_id") != org_id:
        return None

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM resumes WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if row:
            try:
                skills = json.loads(row["skills_json"] or "[]")
            except Exception:
                skills = []
            try:
                exp = json.loads(row["experience_json"] or "[]")
            except Exception:
                exp = []
            try:
                edu = json.loads(row["education_json"] or "[]")
            except Exception:
                edu = []
            try:
                certs = json.loads(row["certifications_json"] or "[]")
            except Exception:
                certs = []
            try:
                projs = json.loads(row["projects_json"] or "[]")
            except Exception:
                projs = []
            try:
                links = json.loads(row["links_json"] or "[]")
            except Exception:
                links = []

            return {
                "id": row["id"],
                "user_id": user_id,
                "org_id": row["org_id"],
                "summary": row["summary"] or "",
                "skills": skills,
                "experience": exp,
                "education": edu,
                "certifications": certs,
                "projects": projs,
                "links": links,
                "updated_at": row["updated_at"]
            }

        # Initialize from existing profile and legacy skills without losing data
        profile = get_profile(user_id)
        legacy_skills = list_skills(user_id)
        emp_skills = get_employee_skills(user.get("employee_id"), org_id=user.get("org_id"))

        # Build initial skills list
        initial_skills = []
        seen_skills = set()
        for s in emp_skills:
            sname = s["skill_name"].strip()
            if sname.lower() not in seen_skills:
                seen_skills.add(sname.lower())
                initial_skills.append({"name": sname, "proficiency": s.get("proficiency_level", "Intermediate")})
        for s in legacy_skills:
            sname = s["name"].strip()
            if sname.lower() not in seen_skills:
                seen_skills.add(sname.lower())
                initial_skills.append({"name": sname, "proficiency": s.get("proficiency", "Intermediate")})

        if not initial_skills:
            initial_skills = [
                {"name": "Python", "proficiency": "Advanced"},
                {"name": "SQL", "proficiency": "Advanced"},
                {"name": "React", "proficiency": "Intermediate"}
            ]

        # Initial Summary
        initial_summary = (profile.get("summary") or "").strip()
        if not initial_summary:
            initial_summary = "Full stack engineer passionate about scalable cloud systems, microservices, and React frontends."

        # Initial Experience
        initial_exp = []
        raw_exp = (profile.get("experience") or "").strip()
        if raw_exp:
            initial_exp.append({
                "id": "exp_1",
                "job_title": profile.get("job_title") or "Senior Software Engineer",
                "company": profile.get("company") or "Talent Growth",
                "employment_type": profile.get("employment_type") or "Full-time",
                "location": profile.get("location") or "Bangalore, India",
                "start_date": "2023-01",
                "end_date": "Present",
                "is_current": True,
                "description": raw_exp
            })
        else:
            initial_exp.append({
                "id": "exp_1",
                "job_title": profile.get("job_title") or "Senior Software Engineer",
                "company": profile.get("company") or "Tech Innovations Inc.",
                "employment_type": "Full-time",
                "location": profile.get("location") or "Bengaluru, India",
                "start_date": "2023-01",
                "end_date": "Present",
                "is_current": True,
                "description": "Architected high-throughput microservices using Python and FastAPI. Optimized SQL queries to reduce latency by 35%."
            })

        # Initial Education
        initial_edu = []
        raw_edu = (profile.get("education") or "").strip()
        if raw_edu:
            initial_edu.append({
                "id": "edu_1",
                "degree": "Bachelor of Technology",
                "institution": raw_edu.split("-")[0].strip() if "-" in raw_edu else "National Institute of Technology",
                "field_of_study": "Computer Science & Engineering",
                "start_date": "2018",
                "end_date": "2022",
                "details": raw_edu
            })
        else:
            initial_edu.append({
                "id": "edu_1",
                "degree": "B.Tech in Computer Science & Engineering",
                "institution": "National Institute of Technology",
                "field_of_study": "Computer Science",
                "start_date": "2018",
                "end_date": "2022",
                "details": "First Class with Distinction (GPA 8.8/10.0)"
            })

        # Initial Certifications
        initial_certs = []
        raw_certs = (profile.get("certifications") or "").strip()
        if raw_certs:
            for idx, c_item in enumerate(raw_certs.split("\n"), 1):
                if c_item.strip():
                    initial_certs.append({
                        "id": f"cert_{idx}",
                        "name": c_item.strip(),
                        "issuing_org": "Professional Authority",
                        "issue_date": "2023-06",
                        "expiry_date": "",
                        "no_expiry": True,
                        "credential_id": "",
                        "credential_url": ""
                    })

        # Initial Projects
        initial_projs = []
        raw_projs = (profile.get("projects") or "").strip()
        if raw_projs:
            initial_projs.append({
                "id": "proj_1",
                "title": "Enterprise Cloud Migration",
                "role": "Lead Engineer",
                "technologies": "Python, Docker, AWS, PostgreSQL",
                "description": raw_projs,
                "project_url": "",
                "github_url": ""
            })

        # Initial Links
        initial_links = []
        if profile.get("linkedin"):
            initial_links.append({"id": "link_1", "label": "LinkedIn", "url": profile.get("linkedin")})
        if profile.get("github"):
            initial_links.append({"id": "link_2", "label": "GitHub", "url": profile.get("github")})
        if profile.get("portfolio"):
            initial_links.append({"id": "link_3", "label": "Portfolio", "url": profile.get("portfolio")})

        user_org = user.get("org_id", "ORG-TALENT-01")

        with conn:
            cursor.execute(
                """
                INSERT INTO resumes (user_id, org_id, summary, skills_json, experience_json, education_json, certifications_json, projects_json, links_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id, user_org, initial_summary,
                    json.dumps(initial_skills), json.dumps(initial_exp),
                    json.dumps(initial_edu), json.dumps(initial_certs),
                    json.dumps(initial_projs), json.dumps(initial_links)
                )
            )
            res_id = cursor.lastrowid

        return {
            "id": res_id,
            "user_id": user_id,
            "org_id": user_org,
            "summary": initial_summary,
            "skills": initial_skills,
            "experience": initial_exp,
            "education": initial_edu,
            "certifications": initial_certs,
            "projects": initial_projs,
            "links": initial_links,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    finally:
        conn.close()

def save_resume(user_id: int, resume_data: Dict[str, Any], org_id: Optional[str] = None) -> Tuple[bool, str]:
    """
    Saves and validates structured resume data into the database.
    Enforces multi-tenant organization authorization and backend data validation.
    Also synchronizes the updated resume content to the profiles table for seamless platform-wide compatibility.
    """
    user = get_user_by_id(user_id)
    if not user:
        return False, "User not found."

    if org_id and user.get("org_id") != org_id:
        return False, "Unauthorized: Cannot modify resume belonging to another organization."

    summary = (resume_data.get("summary") or "").strip()
    raw_skills = resume_data.get("skills", [])
    raw_exp = resume_data.get("experience", [])
    raw_edu = resume_data.get("education", [])
    raw_certs = resume_data.get("certifications", [])
    raw_projs = resume_data.get("projects", [])
    raw_links = resume_data.get("links", [])

    # Validate Skills: clean, deduplicate by lowercase name
    cleaned_skills = []
    seen_skills = set()
    for s in raw_skills:
        name = s.get("name", "").strip() if isinstance(s, dict) else str(s).strip()
        if not name:
            continue
        if name.lower() not in seen_skills:
            seen_skills.add(name.lower())
            prof = s.get("proficiency", "Intermediate") if isinstance(s, dict) else "Intermediate"
            if prof not in LEVELS:
                prof = "Intermediate"
            cleaned_skills.append({"name": name, "proficiency": prof})

    # Validate Experience: date ranges
    cleaned_exp = []
    for idx, e in enumerate(raw_exp):
        title = (e.get("job_title") or "").strip()
        comp = (e.get("company") or "").strip()
        start = (e.get("start_date") or "").strip()
        end = (e.get("end_date") or "").strip()
        is_curr = bool(e.get("is_current", False))

        if is_curr:
            end = "Present"

        # Validate date range
        ok, err = validate_date_range(start, end, is_curr)
        if not ok:
            return False, f"Experience '{title or f'#{idx+1}'}': {err}"

        cleaned_exp.append({
            "id": e.get("id") or f"exp_{idx+1}",
            "job_title": title,
            "company": comp,
            "employment_type": e.get("employment_type", "Full-time"),
            "location": (e.get("location") or "").strip(),
            "start_date": start,
            "end_date": end,
            "is_current": is_curr,
            "description": (e.get("description") or "").strip()
        })

    # Validate Education: date ranges
    cleaned_edu = []
    for idx, ed in enumerate(raw_edu):
        degree = (ed.get("degree") or "").strip()
        inst = (ed.get("institution") or "").strip()
        start = (ed.get("start_date") or "").strip()
        end = (ed.get("end_date") or "").strip()

        ok, err = validate_date_range(start, end)
        if not ok:
            return False, f"Education '{degree or f'#{idx+1}'}': {err}"

        cleaned_edu.append({
            "id": ed.get("id") or f"edu_{idx+1}",
            "degree": degree,
            "institution": inst,
            "field_of_study": (ed.get("field_of_study") or "").strip(),
            "start_date": start,
            "end_date": end,
            "details": (ed.get("details") or "").strip()
        })

    # Validate Certifications: credential URL
    cleaned_certs = []
    for idx, c in enumerate(raw_certs):
        cname = (c.get("name") or "").strip()
        curl = (c.get("credential_url") or "").strip()
        if curl and not validate_url(curl):
            return False, f"Certification '{cname or f'#{idx+1}'}': Invalid credential URL '{curl}'."

        cleaned_certs.append({
            "id": c.get("id") or f"cert_{idx+1}",
            "name": cname,
            "issuing_org": (c.get("issuing_org") or "").strip(),
            "issue_date": (c.get("issue_date") or "").strip(),
            "expiry_date": (c.get("expiry_date") or "").strip(),
            "no_expiry": bool(c.get("no_expiry", False)),
            "credential_id": (c.get("credential_id") or "").strip(),
            "credential_url": curl
        })

    # Validate Projects: project & GitHub URLs
    cleaned_projs = []
    for idx, p in enumerate(raw_projs):
        pname = (p.get("title") or "").strip()
        purl = (p.get("project_url") or "").strip()
        ghurl = (p.get("github_url") or "").strip()

        if purl and not validate_url(purl):
            return False, f"Project '{pname or f'#{idx+1}'}': Invalid project URL '{purl}'."
        if ghurl and not validate_url(ghurl):
            return False, f"Project '{pname or f'#{idx+1}'}': Invalid GitHub URL '{ghurl}'."

        cleaned_projs.append({
            "id": p.get("id") or f"proj_{idx+1}",
            "title": pname,
            "role": (p.get("role") or "").strip(),
            "technologies": (p.get("technologies") or "").strip(),
            "description": (p.get("description") or "").strip(),
            "project_url": purl,
            "github_url": ghurl
        })

    # Validate Links: URL format
    cleaned_links = []
    for idx, l in enumerate(raw_links):
        label = (l.get("label") or "Link").strip()
        lurl = (l.get("url") or "").strip()
        if not lurl:
            continue
        if not validate_url(lurl):
            return False, f"Link '{label}': Invalid web URL '{lurl}'. Must be a valid HTTP/HTTPS address or domain."

        cleaned_links.append({
            "id": l.get("id") or f"link_{idx+1}",
            "label": label,
            "url": lurl
        })

    user_org = user.get("org_id", "ORG-TALENT-01")

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM resumes WHERE user_id = ?", (user_id,))
            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    """
                    UPDATE resumes SET
                        org_id = ?,
                        summary = ?,
                        skills_json = ?,
                        experience_json = ?,
                        education_json = ?,
                        certifications_json = ?,
                        projects_json = ?,
                        links_json = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (
                        user_org, summary,
                        json.dumps(cleaned_skills), json.dumps(cleaned_exp),
                        json.dumps(cleaned_edu), json.dumps(cleaned_certs),
                        json.dumps(cleaned_projs), json.dumps(cleaned_links),
                        user_id
                    )
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO resumes (user_id, org_id, summary, skills_json, experience_json, education_json, certifications_json, projects_json, links_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id, user_org, summary,
                        json.dumps(cleaned_skills), json.dumps(cleaned_exp),
                        json.dumps(cleaned_edu), json.dumps(cleaned_certs),
                        json.dumps(cleaned_projs), json.dumps(cleaned_links)
                    )
                )

            # Synchronize to profiles table for platform-wide legacy compatibility
            exp_text = "\n\n".join(
                f"{e['job_title']} at {e['company']} ({e['start_date']} – {e['end_date']})\n{e['description']}"
                for e in cleaned_exp if e['job_title'] or e['company']
            )
            edu_text = "\n".join(
                f"{ed['degree']} – {ed['institution']} ({ed['start_date']} – {ed['end_date']})"
                for ed in cleaned_edu if ed['degree'] or ed['institution']
            )
            cert_text = "\n".join(
                f"{c['name']} – {c['issuing_org']}"
                for c in cleaned_certs if c['name']
            )
            proj_text = "\n\n".join(
                f"{p['title']} ({p['role']})\nTech: {p['technologies']}\n{p['description']}"
                for p in cleaned_projs if p['title']
            )

            li_url = next((l["url"] for l in cleaned_links if "linkedin" in l["label"].lower()), "")
            gh_url = next((l["url"] for l in cleaned_links if "github" in l["label"].lower()), "")
            port_url = next((l["url"] for l in cleaned_links if "portfolio" in l["label"].lower() or "website" in l["label"].lower()), "")

            cursor.execute(
                """
                UPDATE profiles SET
                    summary = ?,
                    experience = ?,
                    education = ?,
                    certifications = ?,
                    projects = ?,
                    linkedin = CASE WHEN ? != '' THEN ? ELSE linkedin END,
                    github = CASE WHEN ? != '' THEN ? ELSE github END,
                    portfolio = CASE WHEN ? != '' THEN ? ELSE portfolio END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (summary, exp_text, edu_text, cert_text, proj_text, li_url, li_url, gh_url, gh_url, port_url, port_url, user_id)
            )

        return True, "Resume saved successfully."
    except Exception as exc:
        return False, f"Database error while saving resume: {exc}"
    finally:
        conn.close()

def import_skills_to_resume(user_id: int, current_skills: List[Dict[str, Any]], org_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Imports verified skills from the employee's Skills & Assessment module into their Resume skills list.
    Safely merges without overwriting existing entries or creating duplicates.
    """
    user = get_user_by_id(user_id)
    if not user:
        return current_skills

    resolved_org = org_id or user.get("org_id", "ORG-TALENT-01")
    emp_skills = get_employee_skills(user.get("employee_id"), org_id=resolved_org)
    legacy_skills = list_skills(user_id)

    merged = list(current_skills)
    existing_names = {s.get("name", "").strip().lower() for s in merged if isinstance(s, dict)}

    for es in emp_skills:
        name = es.get("skill_name", "").strip()
        if name and name.lower() not in existing_names:
            existing_names.add(name.lower())
            merged.append({
                "name": name,
                "proficiency": es.get("proficiency_level", "Intermediate")
            })

    for ls in legacy_skills:
        name = ls.get("name", "").strip()
        if name and name.lower() not in existing_names:
            existing_names.add(name.lower())
            merged.append({
                "name": name,
                "proficiency": ls.get("proficiency", "Intermediate")
            })

    return merged

def format_resume_as_text(resume_data: Dict[str, Any], user_info: Optional[Dict[str, Any]] = None) -> str:
    """Formats structured resume data into clean text for AI audits, exports, or plain viewing."""
    user_info = user_info or {}
    lines = []
    lines.append(user_info.get("name", "Candidate"))
    contact_parts = [
        user_info.get("email", ""),
        user_info.get("phone", ""),
        user_info.get("location", "")
    ]
    lines.append(" | ".join(filter(None, contact_parts)))
    lines.append("=" * 60)

    if resume_data.get("summary"):
        lines.append("\nPROFESSIONAL SUMMARY")
        lines.append("-" * 30)
        lines.append(resume_data["summary"])

    skills = resume_data.get("skills", [])
    if skills:
        lines.append("\nCORE COMPETENCIES & SKILLS")
        lines.append("-" * 30)
        lines.append(", ".join(f"{s['name']} ({s.get('proficiency', 'Proficient')})" for s in skills))

    exp = resume_data.get("experience", [])
    if exp:
        lines.append("\nPROFESSIONAL EXPERIENCE")
        lines.append("-" * 30)
        for e in exp:
            lines.append(f"{e.get('job_title', 'Role')} - {e.get('company', 'Company')} ({e.get('start_date', '')} - {e.get('end_date', 'Present')})")
            if e.get("location"):
                lines.append(f"Location: {e['location']}")
            if e.get("description"):
                lines.append(e["description"])
            lines.append("")

    edu = resume_data.get("education", [])
    if edu:
        lines.append("\nEDUCATION")
        lines.append("-" * 30)
        for ed in edu:
            lines.append(f"{ed.get('degree', '')} - {ed.get('institution', '')} ({ed.get('start_date', '')} - {ed.get('end_date', '')})")
            if ed.get("details"):
                lines.append(ed["details"])

    certs = resume_data.get("certifications", [])
    if certs:
        lines.append("\nCERTIFICATIONS")
        lines.append("-" * 30)
        for c in certs:
            lines.append(f"- {c.get('name', '')} ({c.get('issuing_org', '')})")

    projs = resume_data.get("projects", [])
    if projs:
        lines.append("\nPROJECTS & ACHIEVEMENTS")
        lines.append("-" * 30)
        for p in projs:
            lines.append(f"{p.get('title', '')} ({p.get('role', '')}) - Tech: {p.get('technologies', '')}")
            if p.get("description"):
                lines.append(p["description"])
            lines.append("")

    links = resume_data.get("links", [])
    if links:
        lines.append("\nPROFESSIONAL LINKS")
        lines.append("-" * 30)
        for l in links:
            lines.append(f"{l.get('label', 'Link')}: {l.get('url', '')}")

    return "\n".join(lines)

def generate_resume_pdf(resume_data: Dict[str, Any], user_info: Dict[str, Any]) -> bytes:
    """
    Generates a professional, ATS-optimized PDF resume using ReportLab.
    Ensures zero overlapping text, elegant typography, auto text-wrapping, and clickable links.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    name_style = ParagraphStyle(
        'ResumeName',
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A'),
        alignment=0,
        spaceAfter=4
    )
    contact_style = ParagraphStyle(
        'ResumeContact',
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#475569'),
        alignment=0,
        spaceAfter=10
    )
    section_heading = ParagraphStyle(
        'ResumeSectionHead',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#1E3A8A'),
        textTransform='uppercase',
        spaceBefore=10,
        spaceAfter=4
    )
    item_title = ParagraphStyle(
        'ResumeItemTitle',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#0F172A')
    )
    item_meta = ParagraphStyle(
        'ResumeItemMeta',
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#64748B'),
        alignment=2
    )
    body_style = ParagraphStyle(
        'ResumeBody',
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6
    )
    skill_tag_style = ParagraphStyle(
        'ResumeSkillTag',
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#1E293B')
    )

    story = []

    # 1. Header (Candidate Name)
    name = user_info.get("name", "Candidate Name")
    story.append(Paragraph(name, name_style))

    # Contact line
    contact_items = []
    if user_info.get("email"):
        contact_items.append(f'<a href="mailto:{user_info["email"]}" color="#2563EB">{user_info["email"]}</a>')
    if user_info.get("phone"):
        contact_items.append(str(user_info["phone"]))
    if user_info.get("location"):
        contact_items.append(str(user_info["location"]))

    links = resume_data.get("links", [])
    for l in links:
        lbl = l.get("label", "Web")
        url = l.get("url", "")
        if url:
            href = url if url.startswith("http") else f"https://{url}"
            contact_items.append(f'<a href="{href}" color="#2563EB">{lbl}</a>')

    story.append(Paragraph(" &nbsp;&bull;&nbsp; ".join(contact_items) if contact_items else "", contact_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceBefore=2, spaceAfter=8))

    # 2. Professional Summary
    summary = (resume_data.get("summary") or "").strip()
    if summary:
        story.append(Paragraph("Professional Summary", section_heading))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceBefore=1, spaceAfter=5))
        story.append(Paragraph(summary.replace("\n", "<br/>"), body_style))
        story.append(Spacer(1, 4))

    # 3. Core Competencies & Skills
    skills = resume_data.get("skills", [])
    if skills:
        story.append(Paragraph("Core Competencies & Skills", section_heading))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceBefore=1, spaceAfter=5))
        
        # Format skills in a clean multi-column table
        skills_formatted = [f"<b>{s['name']}</b> ({s.get('proficiency', 'Proficient')})" for s in skills]
        # Arrange in 3 columns
        cols = 3
        table_data = []
        for i in range(0, len(skills_formatted), cols):
            row_skills = skills_formatted[i:i+cols]
            while len(row_skills) < cols:
                row_skills.append("")
            table_data.append([Paragraph(f"&bull; {cell}", skill_tag_style) if cell else "" for cell in row_skills])

        if table_data:
            stbl = Table(table_data, colWidths=[175, 175, 175])
            stbl.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(stbl)
        story.append(Spacer(1, 4))

    # 4. Work Experience
    exp = resume_data.get("experience", [])
    if exp:
        story.append(Paragraph("Professional Experience", section_heading))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceBefore=1, spaceAfter=5))
        for e in exp:
            title = e.get("job_title", "Role")
            company = e.get("company", "Company")
            loc = e.get("location", "")
            start = e.get("start_date", "")
            end = e.get("end_date", "Present")
            date_str = f"{start} – {end}" if (start or end) else ""
            if loc:
                date_str = f"{loc} | {date_str}"

            header_tbl = Table([
                [
                    Paragraph(f"<b>{title}</b> &mdash; {company}", item_title),
                    Paragraph(date_str, item_meta)
                ]
            ], colWidths=[360, 170])
            header_tbl.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
            ]))

            desc = e.get("description", "").strip()
            desc_p = Paragraph(desc.replace("\n", "<br/>"), body_style) if desc else Spacer(1, 2)

            story.append(KeepTogether([header_tbl, desc_p]))
            story.append(Spacer(1, 3))

    # 5. Education
    edu = resume_data.get("education", [])
    if edu:
        story.append(Paragraph("Education", section_heading))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceBefore=1, spaceAfter=5))
        for ed in edu:
            degree = ed.get("degree", "Degree")
            inst = ed.get("institution", "Institution")
            start = ed.get("start_date", "")
            end = ed.get("end_date", "")
            date_str = f"{start} – {end}" if (start or end) else ""

            header_tbl = Table([
                [
                    Paragraph(f"<b>{degree}</b> &mdash; {inst}", item_title),
                    Paragraph(date_str, item_meta)
                ]
            ], colWidths=[380, 150])
            header_tbl.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
            ]))

            details = ed.get("details", "").strip()
            details_p = Paragraph(details.replace("\n", "<br/>"), body_style) if details else Spacer(1, 2)

            story.append(KeepTogether([header_tbl, details_p]))
            story.append(Spacer(1, 2))

    # 6. Certifications
    certs = resume_data.get("certifications", [])
    if certs:
        story.append(Paragraph("Certifications & Credentials", section_heading))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceBefore=1, spaceAfter=5))
        for c in certs:
            cname = c.get("name", "Certification")
            org = c.get("issuing_org", "")
            id_str = c.get("credential_id", "")
            url = c.get("credential_url", "")
            date_str = c.get("issue_date", "")

            label_html = f"&bull; <b>{cname}</b>"
            if org:
                label_html += f" &mdash; {org}"
            if date_str:
                label_html += f" ({date_str})"
            if id_str:
                label_html += f" &bull; ID: {id_str}"
            if url:
                href = url if url.startswith("http") else f"https://{url}"
                label_html += f' &bull; <a href="{href}" color="#2563EB">Verify</a>'

            story.append(Paragraph(label_html, body_style))
        story.append(Spacer(1, 3))

    # 7. Projects
    projs = resume_data.get("projects", [])
    if projs:
        story.append(Paragraph("Projects & Achievements", section_heading))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceBefore=1, spaceAfter=5))
        for p in projs:
            title = p.get("title", "Project")
            role = p.get("role", "")
            tech = p.get("technologies", "")
            desc = p.get("description", "").strip()
            purl = p.get("project_url", "").strip()
            ghurl = p.get("github_url", "").strip()

            meta_links = []
            if purl:
                href = purl if purl.startswith("http") else f"https://{purl}"
                meta_links.append(f'<a href="{href}" color="#2563EB">Live Demo</a>')
            if ghurl:
                href = ghurl if ghurl.startswith("http") else f"https://{ghurl}"
                meta_links.append(f'<a href="{href}" color="#2563EB">Source Code</a>')

            p_title_str = f"<b>{title}</b>"
            if role:
                p_title_str += f" ({role})"

            header_tbl = Table([
                [
                    Paragraph(p_title_str, item_title),
                    Paragraph(" &bull; ".join(meta_links) if meta_links else "", item_meta)
                ]
            ], colWidths=[380, 150])
            header_tbl.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
            ]))

            content_elements = [header_tbl]
            if tech:
                content_elements.append(Paragraph(f"<i>Technologies:</i> {tech}", body_style))
            if desc:
                content_elements.append(Paragraph(desc.replace("\n", "<br/>"), body_style))

            story.append(KeepTogether(content_elements))
            story.append(Spacer(1, 3))

    doc.build(story)
    return buffer.getvalue()






# ----------------- Organization Membership Requests -----------------

def create_membership_request(
    user_id: int,
    org_id: str,
    user_name: str,
    user_email: str,
    department: str = "",
    designation: str = ""
) -> Tuple[bool, str, Optional[int]]:
    """Creates a pending membership request when an employee joins an existing organization."""
    org_id = (org_id or "").strip().upper()
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            # Check if pending request already exists
            cursor.execute(
                "SELECT id, status FROM membership_requests WHERE user_id = ? AND org_id = ? AND status = 'Pending'",
                (user_id, org_id)
            )
            existing = cursor.fetchone()
            if existing:
                return True, "A pending membership request already exists for this organization.", existing["id"]

            cursor.execute(
                """
                INSERT INTO membership_requests (user_id, org_id, user_name, user_email, department, designation, status)
                VALUES (?, ?, ?, ?, ?, ?, 'Pending')
                """,
                (user_id, org_id, user_name, user_email, department, designation)
            )
            req_id = cursor.lastrowid
        return True, "Membership request created successfully.", req_id
    except Exception as e:
        return False, f"Database error creating membership request: {e}", None
    finally:
        conn.close()

def get_membership_requests(org_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns all membership requests for an organization, optionally filtered by status."""
    org_id = (org_id or "").strip().upper()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT mr.*, o.name as org_name, u.name as reviewer_name
            FROM membership_requests mr
            JOIN organizations o ON mr.org_id = o.org_id
            LEFT JOIN users u ON mr.reviewed_by = u.id
            WHERE mr.org_id = ?
        """
        params = [org_id]
        if status_filter and status_filter != "All Statuses":
            query += " AND mr.status = ?"
            params.append(status_filter)
        query += " ORDER BY mr.created_at DESC"
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

def approve_membership_request(request_id: int, reviewer_id: Optional[int] = None) -> Tuple[bool, str]:
    """Approves a membership request, activating the user and employee records in the organization."""
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM membership_requests WHERE id = ?", (request_id,))
            req = cursor.fetchone()
            if not req:
                return False, "Membership request not found."
            if req["status"] == "Approved":
                return True, "Membership request is already approved."

            user_id = req["user_id"]
            org_id = req["org_id"]
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            # Update request
            cursor.execute(
                "UPDATE membership_requests SET status = 'Approved', reviewed_by = ?, reviewed_at = ? WHERE id = ?",
                (reviewer_id, now_str, request_id)
            )

            # Activate user
            cursor.execute(
                "UPDATE users SET status = 'Active', org_id = ?, account_type = 'Organization' WHERE id = ?",
                (org_id, user_id)
            )

            # Activate employee record
            cursor.execute(
                "UPDATE employees SET account_status = 'Active', org_id = ? WHERE user_id = ?",
                (org_id, user_id)
            )

        return True, f"Membership request approved! {req['user_name']} is now an active employee of {org_id}."
    except Exception as e:
        return False, f"Error approving membership request: {e}"
    finally:
        conn.close()

def reject_membership_request(request_id: int, reviewer_id: Optional[int] = None) -> Tuple[bool, str]:
    """Rejects a membership request, updating status to Rejected."""
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM membership_requests WHERE id = ?", (request_id,))
            req = cursor.fetchone()
            if not req:
                return False, "Membership request not found."

            user_id = req["user_id"]
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute(
                "UPDATE membership_requests SET status = 'Rejected', reviewed_by = ?, reviewed_at = ? WHERE id = ?",
                (reviewer_id, now_str, request_id)
            )
            cursor.execute(
                "UPDATE users SET status = 'Rejected' WHERE id = ?",
                (user_id,)
            )
            cursor.execute(
                "UPDATE employees SET account_status = 'Rejected' WHERE user_id = ?",
                (user_id,)
            )

        return True, f"Membership request for {req['user_name']} has been rejected."
    except Exception as e:
        return False, f"Error rejecting membership request: {e}"
    finally:
        conn.close()

def get_user_membership_request(user_id: int) -> Optional[Dict[str, Any]]:
    """Returns the most recent membership request for a user."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT mr.*, o.name as org_name
            FROM membership_requests mr
            JOIN organizations o ON mr.org_id = o.org_id
            WHERE mr.user_id = ?
            ORDER BY mr.created_at DESC LIMIT 1
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()



SKILL_ASSESSMENT_BANK: Dict[str, List[Dict[str, Any]]] = {
    "Python": [
        {
            "id": "py_1",
            "question": "What is the primary difference between a list and a tuple in Python?",
            "options": [
                "Lists are mutable; tuples are immutable",
                "Lists are immutable; tuples are mutable",
                "Lists cannot contain mixed data types",
                "Tuples have faster append operations"
            ],
            "answer": "Lists are mutable; tuples are immutable",
            "explanation": "In Python, lists can be modified after creation (mutable), whereas tuples cannot be altered once instantiated (immutable)."
        },
        {
            "id": "py_2",
            "question": "Which keyword turns a standard function into a generator in Python?",
            "options": ["yield", "return", "generator", "async"],
            "answer": "yield",
            "explanation": "The 'yield' statement suspends function execution and emits a value to the caller, turning the function into an iterable generator."
        },
        {
            "id": "py_3",
            "question": "What is the average time complexity of a key lookup in a Python dictionary?",
            "options": ["O(1)", "O(n)", "O(log n)", "O(n log n)"],
            "answer": "O(1)",
            "explanation": "Python dictionaries are built using hash tables, which provide amortized O(1) average time complexity for key lookups."
        },
        {
            "id": "py_4",
            "question": "What does the Global Interpreter Lock (GIL) in CPython enforce?",
            "options": [
                "Only one native thread can execute Python bytecode at a time",
                "Memory leaks are automatically prevented across processes",
                "Garbage collection is disabled during file operations",
                "Multi-threaded code always runs faster than single-threaded code"
            ],
            "answer": "Only one native thread can execute Python bytecode at a time",
            "explanation": "CPython's GIL is a mutex that prevents multiple native threads from executing Python bytecodes concurrently."
        },
        {
            "id": "py_5",
            "question": "What will bool([]) evaluate to in Python?",
            "options": ["False", "True", "None", "TypeError"],
            "answer": "False",
            "explanation": "Empty collections (lists, tuples, dicts, sets) evaluate to False in Python boolean truth value testing."
        },
        {
            "id": "py_6",
            "question": "Which decorator defines a method that receives the class rather than the instance as its first argument?",
            "options": ["@classmethod", "@staticmethod", "@property", "@abstractmethod"],
            "answer": "@classmethod",
            "explanation": "@classmethod passes the class 'cls' as the first parameter, whereas normal methods receive the instance 'self'."
        },
        {
            "id": "py_7",
            "question": "What is the output of `[x * 2 for x in range(3)]`?",
            "options": ["[0, 2, 4]", "[2, 4, 6]", "[0, 1, 2]", "[1, 2, 3]"],
            "answer": "[0, 2, 4]",
            "explanation": "range(3) produces 0, 1, 2. Multiplying each element by 2 yields [0, 2, 4]."
        },
        {
            "id": "py_8",
            "question": "Which built-in function pairs elements from two iterables into tuples?",
            "options": ["zip()", "enumerate()", "map()", "filter()"],
            "answer": "zip()",
            "explanation": "zip() aggregates elements from each of the iterables and returns an iterator of tuples."
        }
    ],
    "SQL": [
        {
            "id": "sql_1",
            "question": "What is the key difference between WHERE and HAVING clauses in SQL?",
            "options": [
                "WHERE filters before grouping; HAVING filters aggregated groups",
                "HAVING filters before grouping; WHERE filters aggregated groups",
                "WHERE only operates on primary key columns",
                "HAVING cannot be used alongside GROUP BY"
            ],
            "answer": "WHERE filters before grouping; HAVING filters aggregated groups",
            "explanation": "WHERE filters individual rows prior to GROUP BY aggregation; HAVING applies conditions to aggregated grouped results."
        },
        {
            "id": "sql_2",
            "question": "Which JOIN returns all records from Table A and matched records from Table B?",
            "options": ["LEFT JOIN", "INNER JOIN", "RIGHT JOIN", "CROSS JOIN"],
            "answer": "LEFT JOIN",
            "explanation": "LEFT OUTER JOIN preserves every row from the left table regardless of whether a matching row exists in the right table."
        },
        {
            "id": "sql_3",
            "question": "What does the ACID acronym guarantee in relational database transactions?",
            "options": [
                "Atomicity, Consistency, Isolation, Durability",
                "Access, Concurrency, Integrity, Distribution",
                "Authentication, Consistency, Indexing, Decoupling",
                "Availability, Coherence, Immutability, Durability"
            ],
            "answer": "Atomicity, Consistency, Isolation, Durability",
            "explanation": "ACID represents the foundational transaction properties ensuring database validity and fault tolerance."
        },
        {
            "id": "sql_4",
            "question": "What constraint uniquely identifies each row and strictly disallows NULL values?",
            "options": ["PRIMARY KEY", "UNIQUE", "FOREIGN KEY", "CHECK"],
            "answer": "PRIMARY KEY",
            "explanation": "A PRIMARY KEY uniquely identifies records and strictly forbids NULL values."
        },
        {
            "id": "sql_5",
            "question": "What aggregate function counts the total number of non-NULL values in a column?",
            "options": ["COUNT(column)", "SUM(column)", "TOTAL(column)", "DISTINCT(column)"],
            "answer": "COUNT(column)",
            "explanation": "COUNT(column) counts non-NULL entries in the specified column."
        },
        {
            "id": "sql_6",
            "question": "What is the primary trade-off of adding multiple indexes to a database table?",
            "options": [
                "Faster SELECT queries but slower INSERT/UPDATE write performance",
                "Faster writes but slower query read performance",
                "Increased CPU usage without disk storage impact",
                "Inability to perform foreign key validation"
            ],
            "answer": "Faster SELECT queries but slower INSERT/UPDATE write performance",
            "explanation": "Indexes accelerate search queries but add overhead to write operations because indexes must be updated on modification."
        }
    ],
    "React": [
        {
            "id": "react_1",
            "question": "What is the primary performance benefit of React's Virtual DOM?",
            "options": [
                "Minimizes expensive direct manipulations of the browser DOM via reconciliation diffing",
                "Replaces HTML rendering with WebGL graphics",
                "Eliminates the need for CSS style recalculations",
                "Provides native database connectivity directly from the browser"
            ],
            "answer": "Minimizes expensive direct manipulations of the browser DOM via reconciliation diffing",
            "explanation": "React diffs Virtual DOM trees in memory and applies only the minimum necessary mutations to the real browser DOM."
        },
        {
            "id": "react_2",
            "question": "When does the cleanup function in a useEffect hook execute?",
            "options": [
                "Before re-executing the effect and upon component unmounting",
                "Only when the entire application is closed",
                "Synchronously before the initial render cycle",
                "Every time a child component re-renders"
            ],
            "answer": "Before re-executing the effect and upon component unmounting",
            "explanation": "React runs the returned cleanup function before applying the effect again and when the component is unmounted."
        },
        {
            "id": "react_3",
            "question": "Why should dynamic lists rendered in React include a unique 'key' prop?",
            "options": [
                "To give elements stable identities so React can efficiently reorder, add, or remove items",
                "To automatically attach click event handlers",
                "To bind state to browser sessionStorage",
                "To enforce TypeScript type checking"
            ],
            "answer": "To give elements stable identities so React can efficiently reorder, add, or remove items",
            "explanation": "Keys help React recognize which list elements have changed, been added, or removed during reconciliation."
        },
        {
            "id": "react_4",
            "question": "Which React hook is used to memoize expensive computed values across re-renders?",
            "options": ["useMemo", "useCallback", "useRef", "useEffect"],
            "answer": "useMemo",
            "explanation": "useMemo caches calculation results and recomputes only when one of its specified dependencies changes."
        }
    ],
    "JavaScript": [
        {
            "id": "js_1",
            "question": "What is a closure in JavaScript?",
            "options": [
                "A function that retains access to variables from its outer lexical scope even after that scope has finished executing",
                "A method for instantly terminating an asynchronous loop",
                "An object that cannot be modified or frozen",
                "A syntax error in strict mode"
            ],
            "answer": "A function that retains access to variables from its outer lexical scope even after that scope has finished executing",
            "explanation": "A closure bundles a function together with references to its surrounding lexical environment."
        },
        {
            "id": "js_2",
            "question": "What is the difference between '==' and '===' in JavaScript?",
            "options": [
                "'===' checks both value and type without coercion; '==' performs type coercion",
                "'==' checks both value and type without coercion; '===' performs type coercion",
                "'===' can only be used with numeric operands",
                "There is no difference in modern ECMAScript"
            ],
            "answer": "'===' checks both value and type without coercion; '==' performs type coercion",
            "explanation": "Strict equality (===) compares operands without type conversion, whereas abstract equality (==) coerces types before comparing."
        },
        {
            "id": "js_3",
            "question": "What is the output of `typeof null` in JavaScript?",
            "options": ["'object'", "'null'", "'undefined'", "'boolean'"],
            "answer": "'object'",
            "explanation": "In JavaScript, `typeof null` returning 'object' is a legacy quirk dating back to the language's initial release in 1995."
        }
    ],
    "Git": [
        {
            "id": "git_1",
            "question": "What is the primary difference between `git merge` and `git rebase`?",
            "options": [
                "Merge creates a commit preserving branch topology; rebase reapplies commits linearly on top of the base",
                "Merge deletes old commits; rebase keeps all branches intact",
                "Rebase cannot handle conflicts between files",
                "Merge modifies commit timestamps of prior work"
            ],
            "answer": "Merge creates a commit preserving branch topology; rebase reapplies commits linearly on top of the base",
            "explanation": "Rebase rewrites project history by creating brand new commits for each commit in the original branch."
        },
        {
            "id": "git_2",
            "question": "What command undoes local uncommitted changes to a working file in modern Git?",
            "options": ["git restore <file>", "git clean -f", "git revert HEAD", "git commit --amend"],
            "answer": "git restore <file>",
            "explanation": "`git restore <file>` discards working directory changes and restores the file to the index/commit state."
        }
    ],
    "Docker": [
        {
            "id": "docker_1",
            "question": "What is the primary difference between a Docker container and a Virtual Machine?",
            "options": [
                "Containers share the host OS kernel; VMs run a dedicated guest operating system",
                "Containers require dedicated hypervisor software for hardware emulation",
                "VMs start up in milliseconds compared to minutes for containers",
                "Containers cannot run Linux applications on Windows"
            ],
            "answer": "Containers share the host OS kernel; VMs run a dedicated guest operating system",
            "explanation": "Docker containers virtualize the operating system and share the host kernel, making them lightweight and fast."
        },
        {
            "id": "docker_2",
            "question": "Which Dockerfile instruction sets the default executable and arguments for a running container?",
            "options": ["CMD", "RUN", "FROM", "EXPOSE"],
            "answer": "CMD",
            "explanation": "CMD specifies default arguments and commands to execute when a container is run."
        }
    ],
    "Machine Learning": [
        {
            "id": "ml_1",
            "question": "What is a hallmark symptom of model overfitting?",
            "options": [
                "Near-zero training error but high test error on unseen data",
                "High training error and high test error",
                "Underperforming on training data due to high bias",
                "Extreme sensitivity to missing input features"
            ],
            "answer": "Near-zero training error but high test error on unseen data",
            "explanation": "Overfitting happens when a model learns noise in the training set rather than the underlying pattern, impairing generalization."
        },
        {
            "id": "ml_2",
            "question": "Which evaluation metric is most dependable for evaluating a classifier on an imbalanced dataset?",
            "options": ["F1-Score / PR-AUC", "Accuracy", "Mean Squared Error", "R-squared"],
            "answer": "F1-Score / PR-AUC",
            "explanation": "Accuracy can be deceptively high by always predicting the majority class; F1-score balances precision and recall."
        }
    ],
    "Data Structures": [
        {
            "id": "ds_1",
            "question": "What ordering principle characterizes a Stack data structure?",
            "options": ["Last-In, First-Out (LIFO)", "First-In, First-Out (FIFO)", "Priority-Ordered", "Random Access"],
            "answer": "Last-In, First-Out (LIFO)",
            "explanation": "A stack operates on LIFO order: elements pushed last are popped first."
        },
        {
            "id": "ds_2",
            "question": "What is the average time complexity of searching a balanced Binary Search Tree?",
            "options": ["O(log n)", "O(1)", "O(n)", "O(n^2)"],
            "answer": "O(log n)",
            "explanation": "In a balanced BST, each step halves the remaining elements, yielding O(log n) search time."
        }
    ],
    "Communication": [
        {
            "id": "comm_1",
            "question": "What is the cornerstone of active listening in collaborative technical discussions?",
            "options": [
                "Paraphrasing and confirming understanding before formulating a counter-argument",
                "Interrupting immediately when an inaccurate term is mentioned",
                "Rehearsing your rebuttal while the other party is speaking",
                "Documenting minutes instead of engaging in the dialogue"
            ],
            "answer": "Paraphrasing and confirming understanding before formulating a counter-argument",
            "explanation": "Active listening requires validating and summarizing the speaker's thoughts to establish mutual understanding."
        }
    ],
    "System Design": [
        {
            "id": "sd_1",
            "question": "What does horizontal scaling (scaling out) mean in distributed systems?",
            "options": [
                "Adding more server instances to distribute load across a pool",
                "Upgrading CPU and RAM capacity on a single master machine",
                "Migrating all tables to an in-memory cache",
                "Partitioning network subnets across continents"
            ],
            "answer": "Adding more server instances to distribute load across a pool",
            "explanation": "Horizontal scaling distributes traffic across multiple server nodes rather than relying on a single increasingly powerful machine."
        }
    ]
}

def get_available_assessments() -> List[Dict[str, Any]]:
    """Returns a list of all available skill assessments with question counts and categories."""
    items = []
    for skill, qlist in SKILL_ASSESSMENT_BANK.items():
        cat = "Soft Skill" if skill == "Communication" else "Technical"
        items.append({
            "skill": skill,
            "skill_name": skill,
            "category": cat,
            "total_questions": len(qlist),
            "question_count": len(qlist),
            "estimated_minutes": max(3, len(qlist) * 2),
            "passing_score": 70
        })
    return items

def get_assessment_questions(skill_name: str) -> List[Dict[str, Any]]:
    """Returns questions for a skill without revealing correct answers."""
    questions = SKILL_ASSESSMENT_BANK.get(skill_name, [])
    return [
        {
            "id": q["id"],
            "question": q["question"],
            "options": list(q["options"])
        }
        for q in questions
    ]

def evaluate_assessment(
    uid: int,
    skill_name: str,
    submitted_answers: Dict[str, Any],
    employee_id: Optional[str] = None,
    org_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates submitted answers for a technical assessment.
    Calculates correct/incorrect scores, displays correct answers and explanations,
    and stores the verified assessment result in the database.
    """
    questions = SKILL_ASSESSMENT_BANK.get(skill_name, [])
    if not questions:
        return {"error": f"No assessment questions found for skill '{skill_name}'."}

    total_questions = len(questions)
    correct_count = 0
    breakdown = []

    for q in questions:
        raw_ans = submitted_answers.get(q["id"])
        # Support either string text answer, index int, or index string
        if isinstance(raw_ans, int) and 0 <= raw_ans < len(q.get("options", [])):
            user_ans = q["options"][raw_ans]
        elif isinstance(raw_ans, str) and raw_ans.isdigit() and int(raw_ans) < len(q.get("options", [])):
            user_ans = q["options"][int(raw_ans)]
        elif raw_ans is not None:
            user_ans = str(raw_ans).strip()
        else:
            user_ans = ""

        correct_ans = str(q["answer"]).strip()
        is_correct = (user_ans.lower() == correct_ans.lower())
        if is_correct:
            correct_count += 1
        breakdown.append({
            "id": q["id"],
            "question": q["question"],
            "user_answer": user_ans,
            "correct_answer": correct_ans,
            "is_correct": is_correct,
            "explanation": q.get("explanation", "")
        })

    score_pct = round((correct_count / total_questions) * 100, 1)
    passed = (score_pct >= 70.0)
    prof_rating = "Mastery" if score_pct >= 85 else ("Proficient" if passed else "Developing")

    if score_pct >= 85:
        feedback = f"Outstanding technical proficiency! You scored {score_pct}% ({correct_count}/{total_questions} correct). Excellent command of {skill_name} principles."
    elif passed:
        feedback = f"Solid proficiency demonstrated! You scored {score_pct}% ({correct_count}/{total_questions} correct). You have verified competency in {skill_name}."
    else:
        feedback = f"Needs improvement. You scored {score_pct}% ({correct_count}/{total_questions} correct). Review the explanations below and attempt this assessment again to boost your verified score."

    notes = f"Technical MCQ Assessment: {correct_count}/{total_questions} correct ({score_pct}%). {'Passed' if passed else 'Needs Review'}."
    add_assessment(
        uid=uid,
        category="Technical" if skill_name != "Communication" else "Soft Skill",
        score=score_pct,
        employee_id=employee_id,
        org_id=org_id,
        skill_name=skill_name,
        notes=notes
    )

    return {
        "skill_name": skill_name,
        "total_questions": total_questions,
        "correct_answers": correct_count,
        "correct_count": correct_count,
        "score_percentage": score_pct,
        "passed": passed,
        "proficiency_rating": prof_rating,
        "feedback": feedback,
        "breakdown": breakdown
    }

def get_skill_assessment_history(uid: int, skill_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves full assessment attempt history for a user, tracking score changes across attempts.
    """
    all_ass = get_assessments(uid=uid)
    if skill_name:
        all_ass = [a for a in all_ass if (a.get("skill_name") or a.get("category", "")).lower() == skill_name.lower()]

    all_ass.sort(key=lambda x: x.get("created_at", ""))
    history = []
    prev_score: Optional[float] = None
    for i, a in enumerate(all_ass, 1):
        score = float(a.get("score") or 0.0)
        delta = round(score - prev_score, 1) if prev_score is not None else 0.0
        history.append({
            "attempt": i,
            "id": a.get("id"),
            "skill_name": a.get("skill_name") or a.get("category") or "Technical",
            "score": score,
            "delta": delta,
            "score_delta": delta,
            "created_at": a.get("created_at", ""),
            "notes": a.get("notes", "")
        })
        prev_score = score

    history.reverse()
    return history

def join_organization(user_id: int, invitation_code: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Transitions an Individual user account to an Organization employee account using an invitation code.
    Preserves all existing personal profiles, skills, assessment history, and career goals.
    Creates an organization employee directory entry and links all records to the target organization.
    """
    clean_code = (invitation_code or "").strip().upper()
    if not clean_code:
        return False, "Invitation code is required.", None

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            return False, "User account not found.", None

        user_dict = dict(user_row)
        if user_dict.get("account_type") == "Organization" and user_dict.get("org_id"):
            return False, f"Account is already associated with organization '{user_dict['org_id']}'.", None

        # Validate invitation code against organization codes
        is_valid, inv_info = validate_invitation_code(clean_code)
        if not is_valid:
            return False, inv_info.get("error", "Invalid or expired invitation code."), None

        org_id = inv_info["org_id"]
        org_name = inv_info["org_name"]

        with conn:
            # Increment invitation code use
            use_invitation_code(clean_code, conn=conn)

            # Generate unique employee ID for the organization
            cursor.execute("SELECT COUNT(*) FROM employees WHERE org_id = ?", (org_id,))
            cnt = cursor.fetchone()[0] + 1
            cand = f"EMP{cnt:03d}"
            cursor.execute("SELECT id FROM employees WHERE employee_id = ? AND org_id = ?", (cand, org_id))
            while cursor.fetchone():
                cnt += 1
                cand = f"EMP{cnt:03d}"
                cursor.execute("SELECT id FROM employees WHERE employee_id = ? AND org_id = ?", (cand, org_id))
            final_emp_id = cand

            # Fetch profile to extract department, title, exp
            cursor.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
            prof_row = cursor.fetchone()
            prof_dict = dict(prof_row) if prof_row else {}

            dep = prof_dict.get("department") or "Engineering"
            desig = prof_dict.get("job_title") or prof_dict.get("target_role") or "Software Engineer"
            exp = float(prof_dict.get("years_experience") or 1.0)
            phone = prof_dict.get("phone") or ""

            # Update User record to Organization account
            cursor.execute(
                """
                UPDATE users
                SET account_type = 'Organization', org_id = ?, employee_id = ?, department = ?, job_title = ?
                WHERE id = ?
                """,
                (org_id, final_emp_id, dep, desig, user_id)
            )

            # Fetch user skills for primary_skills
            cursor.execute("SELECT name FROM skills WHERE user_id = ?", (user_id,))
            u_skill_rows = cursor.fetchall()
            prim_skills = ", ".join(r["name"] for r in u_skill_rows) if u_skill_rows else "Python, SQL, Communication"

            # Insert into employees directory
            cursor.execute(
                """
                INSERT INTO employees (employee_id, org_id, user_id, name, email, phone, department, designation, joining_date, employment_status, years_experience, primary_skills, account_status, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?, 'Active', ?)
                """,
                (final_emp_id, org_id, user_id, user_dict["name"], user_dict["email"], phone, dep, desig, date.today().isoformat(), exp, prim_skills, user_id)
            )

            # Retain and migrate existing personal skills to employee_skills
            cursor.execute("SELECT name, category, proficiency, years FROM skills WHERE user_id = ?", (user_id,))
            user_skills = cursor.fetchall()
            for s in user_skills:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO employee_skills (employee_id, org_id, user_id, skill_name, category, proficiency_level, years_exp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (final_emp_id, org_id, user_id, s["name"], s["category"], s["proficiency"], s["years"])
                )

            # Update assessments with new org_id and employee_id
            cursor.execute(
                """
                UPDATE assessments
                SET org_id = ?, employee_id = ?
                WHERE user_id = ? AND (org_id IS NULL OR org_id = '')
                """,
                (org_id, final_emp_id, user_id)
            )

            # Update career goals with new org_id and employee_id
            cursor.execute(
                """
                UPDATE career_goals
                SET org_id = ?, employee_id = ?
                WHERE user_id = ? AND (org_id IS NULL OR org_id = '')
                """,
                (org_id, final_emp_id, user_id)
            )

            # Update profile company
            cursor.execute("UPDATE profiles SET company = ? WHERE user_id = ?", (org_name, user_id))

        updated_user = get_user_by_id(user_id)
        return True, f"Successfully joined {org_name}! Your account has been upgraded to an organization employee account, and all personal skills, assessments, and goals have been preserved.", updated_user
    except Exception as e:
        return False, f"Error joining organization: {e}", None
    finally:
        conn.close()

def get_individual_dashboard_stats(user_id: int) -> Dict[str, Any]:
    """
    Returns aggregated personal statistics for an Individual user's dashboard.
    Includes:
    - Welcome details
    - Total skills added
    - Completed assessments
    - Average assessment score
    - Current skill proficiency breakdown
    - Career development progress & goals
    - Skill gap analysis vs target role
    - Recent activities timeline
    """
    user = get_user_by_id(user_id)
    skills = list_skills(user_id)
    assessments = get_assessments(uid=user_id)
    goals = get_goals(user_id=user_id)
    profile = get_profile(user_id)

    total_skills = len(skills)
    completed_assessments = len(assessments)
    avg_score = round(sum(float(a.get("score") or 0.0) for a in assessments) / len(assessments), 1) if assessments else 0.0

    proficiency_counts = {"Beginner": 0, "Intermediate": 0, "Advanced": 0, "Expert": 0}
    for s in skills:
        p = s.get("proficiency", "Intermediate")
        if p in proficiency_counts:
            proficiency_counts[p] += 1
        else:
            proficiency_counts["Intermediate"] += 1

    completed_goals = sum(1 for g in goals if g.get("status") == "Completed" or g.get("progress") == 100)
    total_goals = len(goals)
    growth_progress = round((completed_goals / total_goals) * 100) if total_goals > 0 else 0

    target_role = profile.get("target_role") or "Junior Python Developer"
    years = float(profile.get("years_experience") or 0)
    role_readiness = role_match(target_role, skills, years)
    gaps = gap_analysis(target_role, skills)

    skills_acquired = [g["skill"] for g in gaps if g.get("priority") == "Met"]
    skills_improving = [g["skill"] for g in gaps if g.get("priority") == "Medium"]
    skills_missing = [g["skill"] for g in gaps if g.get("priority") == "High"]

    assessment_map: Dict[str, float] = {}
    formatted_assessments = []
    for a in assessments:
        sk_n = (a.get("skill_name") or a.get("category") or "Technical").strip()
        sc = float(a.get("score") or 0.0)
        item_a = dict(a)
        item_a["skill_name"] = sk_n
        item_a["score"] = sc
        formatted_assessments.append(item_a)
        assessment_map[sk_n.lower()] = max(assessment_map.get(sk_n.lower(), 0.0), sc)

    enriched_gaps = []
    for g in gaps:
        sk = g.get("skill", "")
        curr = g.get("current", 0)
        req = g.get("required", 0)
        prio = g.get("priority", "High")
        status = "Acquired" if prio == "Met" else ("Needs Improvement" if prio == "Medium" else "Missing Skill")
        v_score = assessment_map.get(sk.strip().lower())
        enriched_gaps.append({
            "skill": sk,
            "current": curr,
            "required": req,
            "current_level": curr,
            "required_level": req,
            "gap": g.get("gap", 0),
            "priority": prio,
            "status": status,
            "verified_score": v_score
        })

    activities = []
    for a in assessments[:5]:
        activities.append({
            "type": "assessment",
            "title": f"Completed {a.get('skill_name') or a.get('category')} Assessment",
            "subtitle": f"Score: {a.get('score')}%",
            "date": a.get("created_at", ""),
            "timestamp": a.get("created_at", "")
        })
    for g in goals[:5]:
        activities.append({
            "type": "goal",
            "title": f"Career Goal: {g.get('title')}",
            "subtitle": f"Progress: {g.get('progress')}% &bull; Status: {g.get('status')}",
            "date": g.get("updated_at") or g.get("created_at", ""),
            "timestamp": g.get("updated_at") or g.get("created_at", "")
        })
    for s in skills[:5]:
        activities.append({
            "type": "skill",
            "title": f"Added Skill: {s.get('name')}",
            "subtitle": f"Proficiency: {s.get('proficiency')} &bull; Experience: {s.get('years')} yrs",
            "date": s.get("created_at", ""),
            "timestamp": s.get("created_at", "")
        })

    activities.sort(key=lambda x: x.get("date", ""), reverse=True)

    return {
        "user_name": user.get("name") if user else "Professional",
        "email": user.get("email") if user else "",
        "account_type": "Individual",
        "total_skills": total_skills,
        "completed_assessments": completed_assessments,
        "average_assessment_score": avg_score,
        "avg_assessment_score": avg_score,
        "proficiency_distribution": proficiency_counts,
        "career_growth_progress": growth_progress,
        "goal_avg_progress": growth_progress,
        "completed_goals": completed_goals,
        "total_goals": total_goals,
        "target_role": target_role,
        "role_readiness": role_readiness,
        "match_percentage": role_readiness,
        "skills_acquired": skills_acquired,
        "skills_improving": skills_improving,
        "skills_missing": skills_missing,
        "role_gaps": enriched_gaps,
        "assessment_history": formatted_assessments,
        "recent_activities": activities[:8]
    }



