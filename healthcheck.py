#!/usr/bin/env python3
"""
Talent Growth - Automated Health Check Utility.

Designed for Docker HEALTHCHECK, cloud platform liveness probes (Render, Railway, Fly.io,
Kubernetes, systemd), and uptime monitors.

Checks:
  1. Streamlit web server response on configured PORT (default: 8501).
  2. Database connectivity, PRAGMA integrity check, and schema readiness.
  3. Returns exit code 0 (HEALTHY) or 1 (UNHEALTHY).
  4. ZERO SENSITIVE DATA EXPOSURE: Never reveals employee names, passwords, or emails.
"""

import os
import sys
import json
import socket
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

try:
    import urllib.request
    import urllib.error
except ImportError:
    pass

from services.core import get_db_path, check_db_health


def check_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Verifies that the TCP port is listening."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        sock.close()
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def check_streamlit_health(port: int, timeout: float = 3.0) -> bool:
    """Probes Streamlit's native internal health endpoint /_stcore/health."""
    url = f"http://127.0.0.1:{port}/_stcore/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TalentGrowth-HealthCheck/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status == 200
    except Exception:
        # If /_stcore/health is not available, fallback to basic TCP port check
        return check_port_open("127.0.0.1", port, timeout=timeout)


def evaluate_health() -> dict:
    """Performs full non-blocking health assessment."""
    port_env = os.getenv("PORT") or os.getenv("STREAMLIT_SERVER_PORT") or "8501"
    try:
        port = int(port_env)
    except ValueError:
        port = 8501

    # 1. Database check
    db_info = check_db_health()
    db_ok = db_info.get("connected", False) and db_info.get("integrity", "").lower() == "ok"

    # 2. Web server check
    web_ok = check_streamlit_health(port)

    # 3. Overall status
    healthy = db_ok and web_ok

    return {
        "status": "HEALTHY" if healthy else "UNHEALTHY",
        "web_server": {
            "status": "UP" if web_ok else "DOWN",
            "port": port
        },
        "database": {
            "connected": db_ok,
            "integrity": db_info.get("integrity", "unknown"),
            "size_kb": db_info.get("size_kb", 0.0),
            "table_count": len(db_info.get("counts", {}))
        }
    }


if __name__ == "__main__":
    result = evaluate_health()
    status_code = 0 if result["status"] == "HEALTHY" else 1

    # Clean, safe summary output
    print(json.dumps(result, indent=2))
    sys.exit(status_code)
