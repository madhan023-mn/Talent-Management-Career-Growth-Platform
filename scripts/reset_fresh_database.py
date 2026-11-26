"""
Fresh MySQL Database Reset and Demo Seeder
Resets the 'talent_growth' MySQL database to a completely clean state
with only essential enterprise demo data.
"""

import json
import os
import secrets
import hashlib
from datetime import datetime, date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
import sys
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pymysql

from services.db import (
    get_mysql_config,
    MYSQL_CORE_SCHEMA_STATEMENTS,
    MYSQL_SETTINGS_SCHEMA_STATEMENTS
)
from services.core import hash_password

def run_fresh_reset():
    cfg = get_mysql_config()
    print(f"Connecting to MySQL '{cfg['database']}' at {cfg['host']}:{cfg['port']} as user '{cfg['user']}'...")
    
    conn = pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        charset="utf8mb4",
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor
    )
    
    cur = conn.cursor()
    
    # 1. Backup existing data
    backup_dir = BASE_DIR / "data" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"mysql_backup_{timestamp}.json"
    
    cur.execute("SHOW TABLES")
    table_rows = cur.fetchall()
    tables = [list(r.values())[0] for r in table_rows]
    
    backup_data = {}
    for tbl in tables:
        try:
            cur.execute(f"SELECT * FROM `{tbl}`")
            rows = cur.fetchall()
            backup_data[tbl] = rows
        except Exception:
            pass
            
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, default=str, indent=2)
    print(f"Backed up existing {len(tables)} tables to: {backup_file.name}")
    
    # 2. Drop all existing tables
    print("Dropping all existing tables...")
    cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
    for tbl in tables:
        cur.execute(f"DROP TABLE IF EXISTS `{tbl}`;")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
    print("All tables dropped successfully.")
    
    # 3. Create fresh tables
    print("Creating fresh 26 MySQL tables...")
    for stmt in MYSQL_CORE_SCHEMA_STATEMENTS + MYSQL_SETTINGS_SCHEMA_STATEMENTS:
        cur.execute(stmt)
    print("All schema statements executed successfully.")
    
    # 4. Seed clean demo data
    print("Seeding fresh demo data...")
    
    # Default organization
    org_id = "ORG-TALENT-01"
    org_name = "Talent Growth Technologies"
    cur.execute(
        """
        INSERT INTO organizations (org_id, name, official_email, contact_number, status)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (org_id, org_name, "contact@talentgrowth.com", "+1-555-0100", "Active")
    )
    
    # Demo Users
    demo_users = [
        {
            "name": "HR Administrator",
            "email": "admin@talentgrowth.com",
            "password": "Password123!",
            "role": "admin",
            "employee_id": "EMP001",
            "department": "Human Resources",
            "job_title": "HR Director",
            "years_exp": 8.0,
            "target_role": "Engineering Manager",
            "target_lvl": "Director",
            "timeline": "1–2 years",
            "skills": [("Leadership", 4), ("People Management", 4), ("Strategic Planning", 3)]
        },
        {
            "name": "Alex Morgan",
            "email": "alex@company.com",
            "password": "Password123!",
            "role": "employee",
            "employee_id": "EMP101",
            "department": "Engineering",
            "job_title": "Software Engineer",
            "years_exp": 2.5,
            "target_role": "Senior Software Engineer",
            "target_lvl": "Senior",
            "timeline": "6–12 months",
            "skills": [("Python", 3), ("SQL", 2), ("Git", 2), ("REST APIs", 2), ("Docker", 2)]
        },
        {
            "name": "Sarah Connor",
            "email": "sarah@company.com",
            "password": "Password123!",
            "role": "employee",
            "employee_id": "EMP102",
            "department": "Engineering",
            "job_title": "Senior Software Engineer",
            "years_exp": 5.0,
            "target_role": "Engineering Manager",
            "target_lvl": "Lead",
            "timeline": "1–2 years",
            "skills": [("Python", 4), ("System Design", 3), ("Cloud Architecture", 3), ("Leadership", 2), ("CI/CD", 3)]
        },
        {
            "name": "Ravi Kumar",
            "email": "ravi@company.com",
            "password": "Password123!",
            "role": "employee",
            "employee_id": "EMP103",
            "department": "Data & Analytics",
            "job_title": "Data Scientist",
            "years_exp": 3.0,
            "target_role": "Machine Learning Engineer",
            "target_lvl": "Senior",
            "timeline": "6–12 months",
            "skills": [("Python", 3), ("Machine Learning", 3), ("SQL", 3), ("Statistics", 3), ("Data Visualization", 2)]
        }
    ]
    
    for u in demo_users:
        pwd_hash, salt = hash_password(u["password"])
        cur.execute(
            """
            INSERT INTO users (name, email, password_hash, salt, role, employee_id, org_id, account_type, department, job_title, status, date_joined)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (u["name"], u["email"], pwd_hash, salt, u["role"], u["employee_id"], org_id, "Organization", u["department"], u["job_title"], "Active", date.today().isoformat())
        )
        user_id = cur.lastrowid
        
        # Employee record
        cur.execute(
            """
            INSERT INTO employees (employee_id, org_id, user_id, name, email, phone, department, designation, joining_date, employment_status, years_experience, primary_skills, account_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (u["employee_id"], org_id, user_id, u["name"], u["email"], "+1-555-0199", u["department"], u["job_title"], "2024-01-15", "Active", u["years_exp"], ", ".join(s[0] for s in u["skills"]), "Active")
        )
        
        # Profile record
        cur.execute(
            """
            INSERT INTO profiles (user_id, phone, job_title, company, department, years_experience, target_role, target_level, timeline, career_goal, summary)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, "+1-555-0199", u["job_title"], org_name, u["department"], u["years_exp"], u["target_role"], u["target_lvl"], u["timeline"], f"Advance career towards {u['target_role']} and drive high technical excellence.", f"Experienced {u['job_title']} specializing in modern software development and cloud systems.")
        )
        
        # Preferences record
        cur.execute(
            """
            INSERT INTO user_preferences (user_id, phone)
            VALUES (%s, %s)
            """,
            (user_id, "+1-555-0199")
        )
        
        # Skills records
        prof_names = ["Beginner", "Intermediate", "Advanced", "Expert"]
        for sk_name, sk_lvl in u["skills"]:
            prof_str = prof_names[min(3, max(0, sk_lvl - 1))]
            cur.execute(
                """
                INSERT INTO skills (user_id, name, category, proficiency, years, description)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, sk_name, "Technical", prof_str, float(u["years_exp"]), f"Proficient in {sk_name}")
            )
            cur.execute(
                """
                INSERT INTO employee_skills (employee_id, org_id, user_id, skill_name, category, proficiency_level, years_exp)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (u["employee_id"], org_id, user_id, sk_name, "Technical", prof_str, float(u["years_exp"]))
            )
            cur.execute(
                """
                INSERT INTO assessments (user_id, employee_id, org_id, category, skill_name, score, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, u["employee_id"], org_id, "Technical Assessment", sk_name, 75.0 + (sk_lvl * 5.0), f"Verified proficiency in {sk_name}")
            )

    # Sample performance reviews
    cur.execute(
        """
        INSERT INTO performance_reviews (employee_id, org_id, review_period, performance_score, achievements, strengths, improvements, manager_feedback)
        VALUES 
        ('EMP101', 'ORG-TALENT-01', '2025 Annual Review', 4.5, 'Built core APIs and microservices on schedule', 'Clean code, proactive problem solving', 'System design depth', 'Excellent performance and collaboration across the team.'),
        ('EMP102', 'ORG-TALENT-01', '2025 Annual Review', 4.8, 'Led migration to cloud architecture and CI/CD', 'Technical leadership, architectural vision', 'Delegation to junior team members', 'Outstanding architectural leadership and technical excellence.'),
        ('EMP103', 'ORG-TALENT-01', '2025 Annual Review', 4.3, 'Developed predictive analytics models with 92% accuracy', 'Statistical modeling, Python optimization', 'Cross-functional presentation skills', 'Strong analytical mindset and consistent delivery.')
        """
    )

    # Sample career goals
    cur.execute(
        """
        INSERT INTO career_goals (user_id, employee_id, org_id, title, target_designation, description, target_date, status, progress)
        VALUES 
        (2, 'EMP101', 'ORG-TALENT-01', 'Attain Senior Software Engineer', 'Senior Software Engineer', 'Demonstrate architectural proficiency and complete AWS Solutions Architect certification.', '2026-12-31', 'In Progress', 50),
        (3, 'EMP102', 'ORG-TALENT-01', 'Transition to Engineering Leadership', 'Engineering Manager', 'Mentor 3 junior engineers and lead cross-department technical roadmap.', '2027-06-30', 'In Progress', 50),
        (4, 'EMP103', 'ORG-TALENT-01', 'Deploy Production MLOps Pipeline', 'Machine Learning Engineer', 'Containerize machine learning models using Docker and Kubernetes.', '2026-10-31', 'In Progress', 75)
        """
    )
    
    # Sample invitation code
    inv_code = "TALENT-DEMO-2026"
    code_hash = hashlib.sha256(inv_code.encode("utf-8")).hexdigest()
    cur.execute(
        """
        INSERT INTO invitation_codes (org_id, code_hash, code_prefix, expires_at, max_uses, used_count, status, created_by)
        VALUES (%s, %s, %s, '2028-12-31 23:59:59', 100, 0, 'Active', 'admin@talentgrowth.com')
        """,
        (org_id, code_hash, "TALENT")
    )
    
    # Org Settings
    cur.execute(
        """
        INSERT INTO org_settings (org_id, org_name, official_email, contact_number, industry, description)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (org_id, org_name, "contact@talentgrowth.com", "+1-555-0100", "Technology", "Enterprise Talent Management & Career Growth Solutions")
    )
    cur.execute(
        """
        INSERT INTO org_pdf_config (org_id, company_name, theme_color, report_title)
        VALUES (%s, %s, %s, %s)
        """,
        (org_id, org_name, "Navy & Teal", "Employee Career & Competency Intelligence Report")
    )
    cur.execute(
        """
        INSERT INTO org_security_config (org_id, min_password_length, require_uppercase, require_number)
        VALUES (%s, 8, 1, 1)
        """,
        (org_id,)
    )

    print("--- RESET & SEEDING COMPLETED SUCCESSFULLY ---")
    
    # Verification
    cur.execute("SELECT id, name, email, role, employee_id FROM users")
    print("\nVerified Users in MySQL:")
    for r in cur.fetchall():
        print(f"  ID {r['id']}: {r['name']} ({r['email']}) - Role: {r['role']} [Emp ID: {r['employee_id']}]")
        
    cur.execute("SELECT id, org_id, name FROM organizations")
    print("\nVerified Organizations in MySQL:")
    for r in cur.fetchall():
        print(f"  ID {r['id']}: {r['name']} ({r['org_id']})")
        
    conn.close()

if __name__ == "__main__":
    run_fresh_reset()
