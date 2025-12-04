# Note: This Dockerfile is for reference. On Windows, run watcher.py directly on host
# Docker containers cannot access Windows GUI APIs (pygetwindow, keyboard)

FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY watcher.py config.py ./

# Create directories
RUN mkdir -p /app/data /app/logs

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sqlite3; conn = sqlite3.connect('/app/data/activity.db'); conn.close()" || exit 1

CMD ["python", "-u", "watcher.py"]