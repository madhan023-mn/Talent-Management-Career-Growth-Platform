import sys
import os
from pathlib import Path
import runpy

# Ensure repository root is at the very front of sys.path and is working directory
_ROOT = str(Path(__file__).resolve().parent)
while _ROOT in sys.path:
    sys.path.remove(_ROOT)
sys.path.insert(0, _ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(_ROOT) / ".env")
except Exception:
    pass

try:
    os.chdir(_ROOT)
except Exception:
    pass

_DATABASE_INITIALIZED = False

def handler(*args, **kwargs):
    return "OK"

app = handler
application = handler

if __name__ == "__main__":
    if not _DATABASE_INITIALIZED:
        try:
            from services.core import init_db
            init_db()
            _DATABASE_INITIALIZED = True
        except Exception as _db_err:
            print(f"Pre-startup database migration note: {_db_err}")

    # Execute app.py directly within Streamlit context
    _app_file = Path(_ROOT) / "app.py"
    with open(_app_file, "r", encoding="utf-8") as _f:
        _code = compile(_f.read(), str(_app_file), "exec")
        _g = globals()
        _g["__file__"] = str(_app_file)
        exec(_code, _g, _g)
