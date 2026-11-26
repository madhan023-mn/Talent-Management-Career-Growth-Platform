"""Backfill SQLite employee rows for existing employee and administrator accounts."""

from __future__ import annotations

from services.db import get_connection


def _new_employee_id(cursor) -> str:
    cursor.execute("SELECT COUNT(*) FROM employees")
    candidate_number = (cursor.fetchone()[0] or 0) + 1
    while True:
        employee_id = f"EMP{candidate_number:03d}"
        cursor.execute("SELECT 1 FROM employees WHERE employee_id = ?", (employee_id,))
        if not cursor.fetchone():
            return employee_id
        candidate_number += 1


def run_backfill() -> int:
    """Create missing employee rows without duplicating linked accounts."""
    conn = get_connection()
    inserted = 0
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT u.id, u.name, u.email, u.phone, u.department, u.job_title,
                       u.employee_id, u.org_id, u.status, u.date_joined,
                       COALESCE(p.years_experience, 0) AS years_experience
                FROM users u
                LEFT JOIN profiles p ON p.user_id = u.id
                WHERE LOWER(COALESCE(u.role, '')) IN ('employee', 'admin')
                  AND NOT EXISTS (
                      SELECT 1
                      FROM employees e
                      WHERE e.user_id = u.id
                         OR (u.employee_id IS NOT NULL AND u.employee_id <> ''
                             AND e.employee_id = u.employee_id)
                         OR LOWER(COALESCE(e.email, '')) = LOWER(u.email)
                  )
                ORDER BY u.id
                """
            )
            account_rows = cursor.fetchall()

            for account in account_rows:
                employee_id = (account["employee_id"] or "").strip().upper()
                if not employee_id:
                    employee_id = _new_employee_id(cursor)

                org_id = (account["org_id"] or "ORG-TALENT-01").strip().upper()
                department = (account["department"] or "Engineering").strip()
                designation = (account["job_title"] or "Employee").strip()
                joined = account["date_joined"] or ""
                account_status = account["status"] or "Active"

                cursor.execute(
                    """
                    INSERT INTO employees (
                        employee_id, org_id, user_id, name, email, phone,
                        department, designation, joining_date, employment_status,
                        years_experience, primary_skills, account_status, created_by
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, '', ?, NULL)
                    """,
                    (
                        employee_id,
                        org_id,
                        account["id"],
                        account["name"],
                        account["email"],
                        account["phone"] or "",
                        department,
                        designation,
                        joined,
                        account["years_experience"] or 0,
                        account_status,
                    ),
                )
                if not account["employee_id"]:
                    cursor.execute(
                        "UPDATE users SET employee_id = ?, org_id = ? WHERE id = ?",
                        (employee_id, org_id, account["id"]),
                    )
                inserted += 1
    finally:
        conn.close()

    return inserted


if __name__ == "__main__":
    print(f"Backfilled {run_backfill()} account(s) into the SQLite employees table.")
