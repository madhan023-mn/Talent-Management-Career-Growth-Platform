# ==============================================================================
# Talent Growth - 24/7 Production Dockerfile
# Multi-arch compatible (Linux x86_64 and ARM64 / Apple Silicon)
# ==============================================================================

FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8501 \
    DATABASE_PATH=/app/data/talentsphere.db

WORKDIR /app

# Install lightweight system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies in separate layer for optimal Docker caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Create non-root application user for enterprise security
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser

# Copy application source code
COPY . /app

# Setup data directory with write permissions for non-root user
RUN mkdir -p /app/data /app/data/backups && \
    chmod +x /app/scripts/*.sh || true && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose default container port
EXPOSE 8501

# Healthcheck probe using internal healthcheck script
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python /app/healthcheck.py || exit 1

# Start container via production runner script
CMD ["/bin/bash", "/app/scripts/run_app.sh"]
