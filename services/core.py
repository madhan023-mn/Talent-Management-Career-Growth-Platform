from __future__ import annotations
import os
import sqlite3
import hashlib
import secrets
from pathlib import Path
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from services.email_service import send_welcome_email

BASE_DIR = Path(__file__).resolve().parent.parent

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
            for table in ["organizations", "users", "employees", "performance_reviews", "employee_skills", "assessments", "career_goals", "training_records"]:
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
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db() -> None:
    conn = get_connection()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'employee',
                employee_id TEXT,
                org_id TEXT NOT NULL DEFAULT 'ORG-TALENT-01',
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
        """)

        # Auto-migrate existing database tables if columns are missing
        cursor = conn.cursor()

        # Seed default organizations
        cursor.execute("SELECT id FROM organizations WHERE org_id = 'ORG-TALENT-01'")
        if not cursor.fetchone():
            cursor.execute("INSERT OR IGNORE INTO organizations (org_id, name) VALUES (?, ?)",
                           ('ORG-TALENT-01', 'Talent Growth Technologies'))
        cursor.execute("SELECT id FROM organizations WHERE org_id = 'ORG-TECHCORP-02'")
        if not cursor.fetchone():
            cursor.execute("INSERT OR IGNORE INTO organizations (org_id, name) VALUES (?, ?)",
                           ('ORG-TECHCORP-02', 'TechCorp Solutions'))

        # Migrate users table
        cursor.execute("PRAGMA table_info(users)")
        user_cols = {row["name"] for row in cursor.fetchall()}
        if "role" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'employee'")
        if "employee_id" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN employee_id TEXT")
        if "org_id" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN org_id TEXT NOT NULL DEFAULT 'ORG-TALENT-01'")
        if "department" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN department TEXT DEFAULT ''")
        if "job_title" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN job_title TEXT DEFAULT ''")
        if "status" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'Active'")
        if "date_joined" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN date_joined TEXT DEFAULT ''")

        # Migrate employees table
        cursor.execute("PRAGMA table_info(employees)")
        emp_cols = {row["name"] for row in cursor.fetchall()}
        if "email" not in emp_cols:
            cursor.execute("ALTER TABLE employees ADD COLUMN email TEXT")
        if "phone" not in emp_cols:
            cursor.execute("ALTER TABLE employees ADD COLUMN phone TEXT DEFAULT ''")
        if "joining_date" not in emp_cols:
            cursor.execute("ALTER TABLE employees ADD COLUMN joining_date TEXT DEFAULT ''")
        if "employment_status" not in emp_cols:
            cursor.execute("ALTER TABLE employees ADD COLUMN employment_status TEXT NOT NULL DEFAULT 'Active'")
        if "org_id" not in emp_cols:
            cursor.execute("ALTER TABLE employees ADD COLUMN org_id TEXT NOT NULL DEFAULT 'ORG-TALENT-01'")
        if "user_id" not in emp_cols:
            cursor.execute("ALTER TABLE employees ADD COLUMN user_id INTEGER")
        if "account_status" not in emp_cols:
            cursor.execute("ALTER TABLE employees ADD COLUMN account_status TEXT NOT NULL DEFAULT 'Active'")

        # Migrate employee_skills table
        cursor.execute("PRAGMA table_info(employee_skills)")
        es_cols = {row["name"] for row in cursor.fetchall()}
        if "org_id" not in es_cols:
            cursor.execute("ALTER TABLE employee_skills ADD COLUMN org_id TEXT NOT NULL DEFAULT 'ORG-TALENT-01'")
        if "user_id" not in es_cols:
            cursor.execute("ALTER TABLE employee_skills ADD COLUMN user_id INTEGER")

        # Migrate assessments table
        cursor.execute("PRAGMA table_info(assessments)")
        as_cols = {row["name"] for row in cursor.fetchall()}
        if "employee_id" not in as_cols:
            cursor.execute("ALTER TABLE assessments ADD COLUMN employee_id TEXT DEFAULT ''")
        if "org_id" not in as_cols:
            cursor.execute("ALTER TABLE assessments ADD COLUMN org_id TEXT NOT NULL DEFAULT 'ORG-TALENT-01'")
        if "skill_name" not in as_cols:
            cursor.execute("ALTER TABLE assessments ADD COLUMN skill_name TEXT DEFAULT ''")
        if "notes" not in as_cols:
            cursor.execute("ALTER TABLE assessments ADD COLUMN notes TEXT DEFAULT ''")

        # Migrate performance_reviews table
        cursor.execute("PRAGMA table_info(performance_reviews)")
        pr_cols = {row["name"] for row in cursor.fetchall()}
        if "org_id" not in pr_cols:
            cursor.execute("ALTER TABLE performance_reviews ADD COLUMN org_id TEXT NOT NULL DEFAULT 'ORG-TALENT-01'")

        # Migrate career_goals table
        cursor.execute("PRAGMA table_info(career_goals)")
        cg_cols = {row["name"] for row in cursor.fetchall()}
        if "target_designation" not in cg_cols:
            cursor.execute("ALTER TABLE career_goals ADD COLUMN target_designation TEXT DEFAULT ''")
        if "org_id" not in cg_cols:
            cursor.execute("ALTER TABLE career_goals ADD COLUMN org_id TEXT NOT NULL DEFAULT 'ORG-TALENT-01'")

        # Migrate training_records table
        cursor.execute("PRAGMA table_info(training_records)")
        tr_cols = {row["name"] for row in cursor.fetchall()}
        if "org_id" not in tr_cols:
            cursor.execute("ALTER TABLE training_records ADD COLUMN org_id TEXT NOT NULL DEFAULT 'ORG-TALENT-01'")

        # Backfill existing legacy records
        cursor.execute("UPDATE users SET org_id = 'ORG-TALENT-01' WHERE org_id IS NULL OR org_id = ''")
        cursor.execute("UPDATE employees SET org_id = 'ORG-TALENT-01' WHERE org_id IS NULL OR org_id = ''")
        cursor.execute("UPDATE performance_reviews SET org_id = 'ORG-TALENT-01' WHERE org_id IS NULL OR org_id = ''")
        cursor.execute("UPDATE employee_skills SET org_id = 'ORG-TALENT-01' WHERE org_id IS NULL OR org_id = ''")
        cursor.execute("UPDATE career_goals SET org_id = 'ORG-TALENT-01' WHERE org_id IS NULL OR org_id = ''")
        cursor.execute("UPDATE training_records SET org_id = 'ORG-TALENT-01' WHERE org_id IS NULL OR org_id = ''")
        cursor.execute("UPDATE assessments SET org_id = 'ORG-TALENT-01' WHERE org_id IS NULL OR org_id = ''")
        cursor.execute("UPDATE users SET employee_id = 'EMP101' WHERE email = 'alex@company.com' AND (employee_id IS NULL OR employee_id = '')")
        cursor.execute("UPDATE employees SET user_id = (SELECT id FROM users WHERE users.email = employees.email) WHERE user_id IS NULL AND email IS NOT NULL")

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
    conn.close()

# ----------------- Organization Management -----------------

def create_organization(org_id: str, name: str) -> Tuple[bool, str]:
    org_id = (org_id or "").strip().upper()
    name = (name or "").strip()
    if not org_id:
        return False, "Organization ID is required."
    if not name:
        return False, "Organization Name is required."
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM organizations WHERE org_id = ?", (org_id,))
            if cursor.fetchone():
                return False, f"Organization ID '{org_id}' already exists."
            cursor.execute("INSERT INTO organizations (org_id, name) VALUES (?, ?)", (org_id, name))
        return True, f"Organization '{name}' ({org_id}) created successfully!"
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

def register(
    name: str,
    email: str,
    password: str,
    role: str = "employee",
    employee_id: Optional[str] = None,
    org_id: str = "ORG-TALENT-01",
    org_name: Optional[str] = None,
    department: str = "Engineering",
    job_title: str = "Software Engineer",
    primary_skills: str = "Python, SQL, Communication",
    years_experience: float = 1.0,
    app_url: Optional[str] = None
) -> Tuple[bool, str]:
    name = (name or "").strip()
    email = (email or "").strip().lower()
    password = password or ""
    role = role if role in ["admin", "employee"] else "employee"
    org_id = (org_id or "ORG-TALENT-01").strip().upper()
    org_name = (org_name or "").strip()
    department = (department or "Engineering").strip()
    job_title = (job_title or "Software Engineer").strip()
    primary_skills = (primary_skills or "Python, SQL, Communication").strip()

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

    pwd_hash, salt = hash_password(password)
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            # Ensure organization exists
            cursor.execute("SELECT id, name FROM organizations WHERE org_id = ?", (org_id,))
            org_row = cursor.fetchone()
            if not org_row:
                resolved_org_name = org_name or f"Organization {org_id}"
                cursor.execute(
                    "INSERT INTO organizations (org_id, name) VALUES (?, ?)",
                    (org_id, resolved_org_name)
                )
            else:
                resolved_org_name = org_row["name"]

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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?)
                """,
                (name, email, pwd_hash, salt, role, final_emp_id, org_id, department, job_title, date.today().isoformat())
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
                    SET user_id = ?, email = COALESCE(email, ?), org_id = ?, department = ?, designation = ?
                    WHERE employee_id = ?
                    """,
                    (user_id, email, org_id, department, job_title, final_emp_id)
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO employees (employee_id, org_id, user_id, name, email, department, designation, joining_date, employment_status, years_experience, primary_skills, account_status, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?, 'Active', ?)
                    """,
                    (final_emp_id, org_id, user_id, name, email, department, job_title, date.today().isoformat(), years_experience, primary_skills, user_id)
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
                    (final_emp_id, org_id, user_id, sk, years_experience)
                )
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO skills (user_id, name, category, proficiency, years)
                    VALUES (?, ?, 'Technical', 'Intermediate', ?)
                    """,
                    (user_id, sk, years_experience)
                )

        # Trigger welcome email safely outside the database write transaction
        try:
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

        return True, "Account created successfully! Please sign in."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."
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
        cursor.execute(
            """
            SELECT u.id, u.name, u.email, u.password_hash, u.salt, u.role, u.employee_id,
                   u.org_id, u.department, u.job_title, u.status, u.date_joined,
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
                """
                SELECT u.id, u.name, u.email, u.password_hash, u.salt, u.role, u.employee_id,
                       u.org_id, u.department, u.job_title, u.status, u.date_joined,
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
            return {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "role": row["role"],
                "employee_id": row["employee_id"],
                "org_id": row["org_id"] or "ORG-TALENT-01",
                "org_name": row["org_name"] or "Talent Growth Technologies",
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
        cursor.execute(
            """
            SELECT u.id, u.name, u.email, u.role, u.employee_id, u.org_id,
                   u.department, u.job_title, u.status, u.date_joined, u.created_at,
                   COALESCE(o.name, 'Talent Growth Technologies') as org_name
            FROM users u
            LEFT JOIN organizations o ON u.org_id = o.org_id
            WHERE u.id = ?
            """,
            (uid,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
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
        query += " GROUP BY e.department ORDER BY avg_score DESC NULLS LAST"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
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

def get_profile(uid: int) -> Dict[str, Any]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE user_id = ?", (uid,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        with conn:
            conn.execute("INSERT OR IGNORE INTO profiles (user_id) VALUES (?)", (uid,))
        cursor.execute("SELECT * FROM profiles WHERE user_id = ?", (uid,))
        return dict(cursor.fetchone())
    finally:
        conn.close()

def save_profile(uid: int, data: Dict[str, Any]) -> bool:
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
    values = list(updates.values()) + [uid]

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
        cursor.execute("SELECT id, name, category, proficiency, years, created_at FROM skills WHERE user_id = ? ORDER BY id DESC", (uid,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def add_skill(uid: int, name: str, category: str, proficiency: str, years: float) -> Tuple[bool, str]:
    name = (name or "").strip()
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
                "INSERT INTO skills (user_id, name, category, proficiency, years) VALUES (?, ?, ?, ?, ?)",
                (uid, name, category, proficiency, years)
            )
        return True, f"Skill '{name}' added successfully."
    except Exception as e:
        return False, f"Error saving skill: {e}"
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
        cursor.execute("SELECT COUNT(*) as cnt FROM employees WHERE org_id = ?", (org_id,))
        total_employees = cursor.fetchone()["cnt"]

        # Total departments
        cursor.execute(
            "SELECT COUNT(DISTINCT department) as cnt FROM employees WHERE org_id = ? AND department IS NOT NULL AND department != ''",
            (org_id,)
        )
        total_departments = cursor.fetchone()["cnt"]

        # Average performance score
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

        # Assessments completed
        cursor.execute("SELECT COUNT(*) as cnt FROM assessments WHERE org_id = ?", (org_id,))
        total_assessments = cursor.fetchone()["cnt"]

        # Employees assessed percentage
        cursor.execute("SELECT COUNT(DISTINCT employee_id) as cnt FROM assessments WHERE org_id = ?", (org_id,))
        assessed_employees = cursor.fetchone()["cnt"]
        assessment_completion_rate = round((assessed_employees / max(1, total_employees)) * 100) if total_employees else 0

        # Career goals completion rate
        cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed FROM career_goals WHERE org_id = ?", (org_id,))
        goal_row = cursor.fetchone()
        total_goals = goal_row["total"] if goal_row else 0
        completed_goals = (goal_row["completed"] or 0) if goal_row else 0
        goal_completion_rate = round((completed_goals / max(1, total_goals)) * 100) if total_goals else 0

        # Department distribution
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

        # Recent joiners
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

        # Performance score distribution
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

        # Organization skill distribution / gap highlights
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

        return {
            "org_id": org_id,
            "total_employees": total_employees,
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
    all_skills_formatted = skills if skills else [{"skill_name": s["name"], "proficiency_level": s["proficiency"], "years_exp": s["years"]} for s in legacy_skills]
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

