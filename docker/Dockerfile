# KAGE - Multi-stage build

# === Builder ===
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy source and install
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

# === Runtime ===
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash kage

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/kage /usr/local/bin/kage

# Copy source and prompts
COPY src/ ./src/
COPY prompts/ ./prompts/
COPY README.md ./

# Set ownership
RUN chown -R kage:kage /app

# Switch to non-root user
USER kage

# Create data directories
RUN mkdir -p /home/kage/.kage/memory \
    /home/kage/.kage/chroma \
    /home/kage/.kage/docs_cache

# Environment
ENV KAGE_LOG_FORMAT=console
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from kage.config.settings import settings; print('OK')"

ENTRYPOINT ["kage"]
CMD ["--help"]
