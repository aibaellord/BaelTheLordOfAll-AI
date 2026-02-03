# =============================================================================
# BAEL - The Lord of All AI Agents
# Dockerfile
# =============================================================================

FROM python:3.11-slim-bookworm AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app user
RUN groupadd --gid 1000 bael \
    && useradd --uid 1000 --gid bael --shell /bin/bash --create-home bael

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Builder Stage
# =============================================================================
FROM base AS builder

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

# =============================================================================
# Production Stage
# =============================================================================
FROM base AS production

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=bael:bael . .

# Create necessary directories
RUN mkdir -p memory/storage outputs logs \
    && chown -R bael:bael memory outputs logs

# Switch to non-root user
USER bael

# Expose ports
EXPOSE 8000 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "main.py", "chat"]

# =============================================================================
# Development Stage
# =============================================================================
FROM production AS development

USER root

# Install development dependencies
RUN pip install \
    debugpy \
    ipython \
    jupyter \
    watchdog

USER bael

# Enable debug mode
ENV BAEL_DEBUG=1

CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "main.py", "chat"]

# =============================================================================
# API Server Stage
# =============================================================================
FROM production AS api

# Install API server dependencies
USER root
RUN pip install uvicorn fastapi
USER bael

EXPOSE 8000

CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
