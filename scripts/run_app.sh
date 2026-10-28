#!/usr/bin/env bash
set -e

# ==============================================================================
# Talent Growth - 24/7 Production Startup Script
# ==============================================================================

echo "========================================================"
echo "Starting Talent Growth Platform..."
echo "Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "========================================================"

# Determine port (Host-provided $PORT or fallback to 8501)
APP_PORT="${PORT:-${STREAMLIT_SERVER_PORT:-8501}}"
APP_HOST="${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}"

echo "Configuring network bindings:"
echo "  - Host: ${APP_HOST}"
echo "  - Port: ${APP_PORT}"

# Ensure data directory exists and has proper permissions
DB_DIR="${DATABASE_DIR:-/app/data}"
mkdir -p "${DB_DIR}"
mkdir -p "${DB_DIR}/backups"

# Run database initialization and pre-flight checks
echo "Executing database pre-flight checks..."
python -c "
from services.core import init_db, check_db_health
init_db()
health = check_db_health()
print(f'Database pre-flight check complete: Connected={health[\"connected\"]}, Integrity={health[\"integrity\"]}')
"

echo "Launching Streamlit application on http://${APP_HOST}:${APP_PORT}..."
exec streamlit run app.py \
    --server.port="${APP_PORT}" \
    --server.address="${APP_HOST}" \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    --browser.gatherUsageStats=false \
    --client.toolbarMode=minimal
