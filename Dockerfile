# =============================================================================
# AI Tao - Dockerfile
# =============================================================================
# Multi-stage build for minimal production image.
#
# Build: docker build -t aitao:latest .
# Run:   docker run -p 8200:8200 aitao:latest
#
# Note: This Dockerfile will be enhanced in US-036 with full production specs.
# =============================================================================

# --- Stage 1: Builder ---
FROM python:3.13-slim AS builder

WORKDIR /build

# Install build dependencies (including C++ compiler for some packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    cmake \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Generate requirements.txt from pyproject.toml
# Exclude llama-cpp-python (Ollama handles LLM inference in Docker)
RUN pip install --no-cache-dir toml && \
    python -c "import toml; p=toml.load('pyproject.toml'); deps=[d for d in p['project']['dependencies'] if 'llama-cpp' not in d.lower()]; print('\\n'.join(deps))" > requirements.txt && \
    cat requirements.txt

# Install dependencies
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.13-slim AS runtime

# Labels
LABEL maintainer="AI Tao <phil@example.com>"
LABEL version="2.6.34"
LABEL description="AI Tao - Local-First Document Search & Translation Engine"

# Create non-root user
RUN useradd --create-home --shell /bin/bash aitao

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

# Copy application code
COPY --chown=aitao:aitao src/ ./src/
COPY --chown=aitao:aitao config/ ./config/

# Create data directories
RUN mkdir -p /app/data /app/logs && chown -R aitao:aitao /app

# Switch to non-root user
USER aitao

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV API_PORT=8200

# Expose API port
EXPOSE 8200

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8200/api/health || exit 1

# Start FastAPI server
ENTRYPOINT ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8200"]
