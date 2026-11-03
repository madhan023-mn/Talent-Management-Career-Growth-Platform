import pytest
import tempfile
import os
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

temp_db_dir = tempfile.mkdtemp()
os.environ["DATABASE_PATH"] = str(Path(temp_db_dir) / "test_delete_user.db")

from services.core import (
    init_db, register, register_individual, login, get_user_by_id,
    delete_user_by_email, get_connection
)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_delete_user_by_email_success():
    """Verify delete_user_by_email removes the user from users and related tables."""
    ok, _ = register_individual(
        name="Delete Me",
        email="delete.me@example.com",
        password="Password123!",
        primary_skills="Python, SQL"
    )
    assert ok is True

    # User exists
    user = login("delete.me@example.com", "Password123!")
    assert user is not None
    uid = user["id"]

    # Delete the user
    del_ok, del_msg = delete_user_by_email("delete.me@example.com")
    assert del_ok is True
    assert "successfully purged" in del_msg

    # User cannot log in anymore
    assert login("delete.me@example.com", "Password123!") is None
    assert get_user_by_id(uid) is None

    # Check related tables
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM profiles WHERE user_id = ?", (uid,))
    assert cur.fetchone() is None
    cur.execute("SELECT id FROM skills WHERE user_id = ?", (uid,))
    assert cur.fetchone() is None
    conn.close()

def test_delete_user_protected_accounts():
    """Verify protected system demo accounts cannot be deleted."""
    for protected in ["admin@talentgrowth.com", "admin@talentsphere.com", "alex@company.com", "ravi@company.com"]:
        del_ok, del_msg = delete_user_by_email(protected)
        assert del_ok is False
        assert "protected" in del_msg.lower()

def test_delete_nonexistent_user():
    """Verify deleting a nonexistent user returns a clean error."""
    del_ok, del_msg = delete_user_by_email("nonexistent.user.2026@example.com")
    assert del_ok is False
    assert "no user account found" in del_msg.lower()
