from pathlib import Path
import runpy

# Forward execution to app.py
_app_file = Path(__file__).resolve().parent / "app.py"
runpy.run_path(str(_app_file), run_name="__main__")
