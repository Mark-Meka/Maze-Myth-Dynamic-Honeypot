# ============================================================
# Maze Myth Dynamic Honeypot — Production Dockerfile
#
# Two named targets in one file:
#   docker build --target honeypot  -t maze-myth-honeypot .
#   docker build --target dashboard -t maze-myth-dashboard .
#
# docker-compose.yaml uses these targets automatically.
# ============================================================

# ── Stage 1: Builder (shared by both targets) ────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Build dependencies only needed to compile certain Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements and install into /install so we can COPY them into runtime stage
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install gunicorn \
 && pip install --prefix=/install --no-cache-dir -r requirements.txt \
 && pip install --prefix=/install gunicorn


# ── Stage 2: Runtime base (shared by both targets) ───────
FROM python:3.11-slim AS base

# Non-root user for security
RUN groupadd --gid 1001 honeypot \
 && useradd  --uid 1001 --gid honeypot --no-create-home honeypot

# Only the runtime shared libraries — no build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi8 \
    libssl3 \
    libjpeg62-turbo \
    zlib1g \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy compiled Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source (the .dockerignore excludes venv, logs, secrets)
COPY --chown=honeypot:honeypot . .

# Create data directories that will be mounted as volumes
RUN mkdir -p log_files databases generated_files \
 && chown -R honeypot:honeypot log_files databases generated_files

USER honeypot


# ── Target: honeypot ─────────────────────────────────────
FROM base AS honeypot

EXPOSE 8001

# Health check via Flask root
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -sf http://localhost:8001/ || exit 1

# gunicorn is the production WSGI server.
# Flask's built-in server (flask run) is ONLY for development.
# 4 workers × 2 threads = handles up to 8 concurrent requests
# --timeout 120 = allow slow LLM calls to complete
CMD ["gunicorn", "honeypot:app", \
     "--bind", "0.0.0.0:8001", \
     "--workers", "4", \
     "--threads", "2", \
     "--timeout", "120", \
     "--worker-class", "gthread", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]


# ── Target: dashboard ───────────────────────────────────
FROM base AS dashboard

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -sf http://localhost:8002/ || exit 1

# dashboard/monitor.py exposes a Flask `app` object on port 8002
CMD ["gunicorn", "dashboard.monitor:app", \
     "--bind", "0.0.0.0:8002", \
     "--workers", "2", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
