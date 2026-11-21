# ═══════════════════════════════════════════════════════════════════════════════
# Kolang — Production Docker Image (Multi-Stage)
# ═══════════════════════════════════════════════════════════════════════════════

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency specification first (layer caching)
COPY pyproject.toml README.md ./

# Install Python dependencies
RUN pip install --no-cache-dir --prefix=/install .

# Copy source code
COPY packages/ packages/
COPY apps/ apps/

# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# OCI image labels
LABEL org.opencontainers.image.title="Kolang" \
      org.opencontainers.image.description="Agent Control Plane & MCP Gateway" \
      org.opencontainers.image.source="https://github.com/sepehr-safaeian/Kolang" \
      org.opencontainers.image.licenses="Apache-2.0"

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 kolang && \
    useradd --uid 1000 --gid kolang --shell /bin/bash --create-home kolang

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --from=builder /build/packages/ packages/
COPY --from=builder /build/apps/ apps/
COPY --from=builder /build/pyproject.toml .

# Set ownership
RUN chown -R kolang:kolang /app

# Switch to non-root user
USER kolang

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Start the application
CMD ["uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
