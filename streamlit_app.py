import sys
import os
from pathlib import Path
import runpy

# Ensure repository root is on sys.path and is current working directory
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    os.chdir(str(_ROOT))
except Exception:
    pass

def handler(*args, **kwargs):
    return "OK"

app = handler
application = handler

if __name__ == "__main__":
    # Forward execution to app.py
    _app_file = _ROOT / "app.py"
    runpy.run_path(str(_app_file), run_name="__main__")
