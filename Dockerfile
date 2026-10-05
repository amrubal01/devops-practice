# ---- Build stage ----
# Installs dependencies into a virtual environment so the runtime
# stage doesn't need build tools or pip caches baked into the image.
FROM python:3.12-slim AS builder

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Runtime stage ----
FROM python:3.12-slim AS runtime

# Run as a non-root user — a small but real security best practice
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY app ./app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Gunicorn manages multiple Uvicorn worker processes — this is the
# standard production setup (plain `uvicorn app.main:app` is fine for
# local dev, but doesn't give you worker management/restarts on its own).
# WEB_CONCURRENCY controls worker count; 2 is a reasonable default for
# a small container, bump it based on CPU cores in real deployments.
ENV WEB_CONCURRENCY=2
CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w ${WEB_CONCURRENCY} -b 0.0.0.0:8000"]
