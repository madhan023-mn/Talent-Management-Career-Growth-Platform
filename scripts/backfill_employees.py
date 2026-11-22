"""
Backfill script to ensure all existing individual and organization users
have complete, valid entries in the `employees` table in both MySQL and SQLite.
"""

import sys
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from services.db import get_connection

def run_backfill():
    m_conn = get_connection()
    m_cur = m_conn.cursor()

    m_cur.execute("""
        SELECT u.id, u.name, u.email, u.phone, u.department, u.job_title, u.date_joined,
               p.years_experience
        FROM users u
        LEFT JOIN profiles p ON u.id = p.user_id
        WHERE u.employee_id IS NULL OR u.employee_id = ''
        ORDER BY u.id ASC
    """)
    missing = m_cur.fetchall()

    sq_conn = sqlite3.connect('data/talentsphere.db')
    sq_cur = sq_conn.cursor()

    m_cur.execute("SELECT COUNT(*) FROM employees")
    cnt = m_cur.fetchone()[0]

    assigned = []
    for r in missing:
        uid = r['id']
        name = r['name']
        email = r['email']
        phone = r['phone'] or ''
        dept = r['department'] or 'Independent Professional'
        title = r['job_title'] or 'Independent Professional'
        joining = r['date_joined'] or '2026-11-04'
        exp = float(r['years_experience'] or 1.0)
        
        cnt += 1
        cand = f"EMP{cnt:03d}"
        m_cur.execute("SELECT id FROM employees WHERE employee_id = ?", (cand,))
        while m_cur.fetchone():
            cnt += 1
            cand = f"EMP{cnt:03d}"
            m_cur.execute("SELECT id FROM employees WHERE employee_id = ?", (cand,))
        
        # Update MySQL users
        m_cur.execute(
            "UPDATE users SET employee_id = ?, org_id = COALESCE(NULLIF(org_id, ''), 'ORG-TALENT-01') WHERE id = ?",
            (cand, uid)
        )
        
        # Insert into MySQL employees
        m_cur.execute("""
            INSERT INTO employees (employee_id, org_id, user_id, name, email, phone, department, designation, joining_date, employment_status, years_experience, primary_skills, account_status, created_by)
            VALUES (?, 'ORG-TALENT-01', ?, ?, ?, ?, ?, ?, ?, 'Active', ?, 'Python, SQL, Communication', 'Active', ?)
        """, (cand, uid, name, email, phone, dept, title, joining, exp, uid))
        
        # Update SQLite users
        sq_cur.execute(
            "UPDATE users SET employee_id = ?, org_id = COALESCE(NULLIF(org_id, ''), 'ORG-TALENT-01') WHERE id = ?",
            (cand, uid)
        )
        
        # Insert into SQLite employees
        sq_cur.execute("""
            INSERT OR REPLACE INTO employees (employee_id, org_id, user_id, name, email, phone, department, designation, joining_date, employment_status, years_experience, primary_skills, account_status, created_by)
            VALUES (?, 'ORG-TALENT-01', ?, ?, ?, ?, ?, ?, ?, 'Active', ?, 'Python, SQL, Communication', 'Active', ?)
        """, (cand, uid, name, email, phone, dept, title, joining, exp, uid))
        
        assigned.append((cand, uid, name, email))

    m_conn.commit()
    sq_conn.commit()
    m_conn.close()
    sq_conn.close()

    print(f"Successfully backfilled {len(assigned)} users into employees table in both MySQL and SQLite!")
    for emp_id, uid, name, email in assigned:
        print(f"  {emp_id}: {name} ({email}) [User ID: {uid}]")

if __name__ == "__main__":
    run_backfill()
