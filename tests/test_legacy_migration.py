import os
import sqlite3
import pytest
from pathlib import Path
from services.core import init_db, login, get_user_by_id, get_org_dashboard_stats, hash_password

def test_legacy_database_migration_resilience(tmp_path):
    test_db = str(tmp_path / "legacy_test.db")
    
    # 1. Create a simulated legacy SQLite database lacking recent columns
    conn = sqlite3.connect(test_db)
    conn.execute("""
        CREATE TABLE organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.execute("INSERT INTO organizations (org_id, name) VALUES ('ORG-TALENT-01', 'Legacy Talent Growth');")
    
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT DEFAULT 'employee',
            org_id TEXT
        );
    """)
    # Insert legacy user without account_type column
    pwd_h, salt = hash_password("Admin@12345")
    conn.execute("INSERT INTO users (name, email, password_hash, salt, role, org_id) VALUES ('Admin Legacy', 'admin@talentgrowth.com', ?, ?, 'admin', 'ORG-TALENT-01')", (pwd_h, salt))
    
    conn.commit()
    conn.close()

    # Point services to the test db
    orig_db = os.environ.get("DATABASE_PATH")
    os.environ["DATABASE_PATH"] = test_db
    try:
        # Run init_db on the legacy database
        init_db()

        # Test login as admin
        admin_user = login("admin@talentgrowth.com", "Admin@12345")
        assert admin_user is not None, "Legacy admin login failed"
        assert admin_user["email"] == "admin@talentgrowth.com"
        assert admin_user["role"] == "admin"
        assert "account_type" in admin_user
        assert admin_user["account_type"] == "Organization"

        # Test get_user_by_id
        u = get_user_by_id(admin_user["id"])
        assert u is not None
        assert u["account_type"] == "Organization"

        # Test get_org_dashboard_stats
        stats = get_org_dashboard_stats("ORG-TALENT-01")
        assert isinstance(stats, dict)
        assert "total_employees" in stats
        assert "active_invitations" in stats
        assert "goal_completion_rate" in stats

    finally:
        if orig_db:
            os.environ["DATABASE_PATH"] = orig_db
        else:
            os.environ.pop("DATABASE_PATH", None)
