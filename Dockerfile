FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data \
    SEED_ROOT=/app \
    HOST=0.0.0.0 \
    PORT=8000 \
    TZ=Asia/Shanghai \
    UPDATE_INTERVAL_SECONDS=21600 \
    RETRY_INTERVAL_SECONDS=900

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-cache-dir .

COPY data ./data
COPY docs ./docs

RUN addgroup --system --gid 10001 calendar \
    && adduser --system --uid 10001 --ingroup calendar --home /app calendar \
    && mkdir -p /data/public \
    && chown -R calendar:calendar /app /data

USER 10001:10001

EXPOSE 8000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"]

ENTRYPOINT ["mainland-movie-calendar-serve"]
