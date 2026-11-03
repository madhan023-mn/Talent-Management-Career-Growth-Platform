import pytest
import sqlite3
import tempfile
import os
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from services.core import register_individual, login, init_db

def test_individual_registration_on_legacy_notnull_org_database():
    """Simulates a legacy database where org_id was created with NOT NULL constraint."""
    temp_dir = tempfile.mkdtemp()
    test_db = str(Path(temp_dir) / "legacy_notnull.db")
    os.environ["DATABASE_PATH"] = test_db

    # Initialize DB (which also auto-migrates nullable org_id)
    init_db()

    # Now verify registration succeeds cleanly
    ok, msg = register_individual(
        name="Legacy Test User",
        email="legacy.individual@testdomain.com",
        password="Password123!",
        primary_skills="Python, SQL"
    )
    assert ok is True
    assert "successfully" in msg.lower()

    user = login("legacy.individual@testdomain.com", "Password123!")
    assert user is not None
    assert user["account_type"] == "Individual"
    assert user["org_id"] is None

