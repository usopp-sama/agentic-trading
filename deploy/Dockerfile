# Multi-arch (amd64/arm64) image. Build with: docker buildx build --platform linux/amd64,linux/arm64
FROM python:3.12-slim AS base

# Security: run as non-root, no bytecode pyc surprises, no buffering.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    NODE_ENV=production

WORKDIR /app

# Install deps first for layer caching. Use deterministic install.
# Set INSTALL_EXTRAS=true to add Postgres/Redis drivers for the scaled stack.
ARG INSTALL_EXTRAS=false
COPY requirements.txt deploy/requirements-prod.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && if [ "$INSTALL_EXTRAS" = "true" ]; then pip install -r requirements-prod.txt; fi

# Copy application code.
COPY quant ./quant
COPY ats ./ats
COPY pyproject.toml ./

# Non-root user; own the writable data dir only.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/var \
    && chown -R appuser:appuser /app/var
USER appuser

EXPOSE 8000

# Healthcheck hits the control API.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import httpx,sys; sys.exit(0 if httpx.get('http://127.0.0.1:8000/api/health').status_code==200 else 1)"

CMD ["uvicorn", "ats.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
