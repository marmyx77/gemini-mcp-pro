# Dockerfile for gemini-mcp-pro
# v2.7.0 - Production-ready container

FROM python:3.11-slim AS base

# Security: non-root user
RUN useradd --create-home --shell /bin/bash gemini
WORKDIR /app

# Install dependencies first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY --chown=gemini:gemini server.py .

# Security: switch to non-root user
USER gemini

# Health check - verify server can be imported
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import server; print('healthy')" || exit 1

# Environment
ENV PYTHONUNBUFFERED=1
ENV GEMINI_SANDBOX_ROOT=/workspace
ENV GEMINI_SANDBOX_ENABLED=true
ENV GEMINI_ACTIVITY_LOG=true
ENV GEMINI_LOG_DIR=/logs

# Mount points for user files and logs
VOLUME ["/workspace", "/logs"]

# MCP server runs via stdin/stdout
ENTRYPOINT ["python", "server.py"]
