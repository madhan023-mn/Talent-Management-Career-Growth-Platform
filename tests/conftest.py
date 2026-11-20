import os
import sys
import tempfile
from pathlib import Path

# Ensure root directory is on sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Configure isolated temporary SQLite database for unit tests
temp_test_dir = tempfile.mkdtemp()
temp_db_path = str(Path(temp_test_dir) / "test_suite.db")
os.environ["DATABASE_PATH"] = temp_db_path
os.environ["DB_ENGINE"] = "sqlite"
os.environ["SMTP_HOST"] = ""
os.environ["SMTP_PORT"] = "0"
