FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WEB_HOST=0.0.0.0 \
    WEB_PORT=8080 \
    SECURITY_FILE=/data/security.json \
    OCI_DATA_DIR=/data/oci \
    OCI_CONFIG_FILE=/data/oci/config \
    SSH_KEY_DIR=/data/ssh-keys

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data \
    && chown appuser:appuser /data

COPY . .
RUN pip install --no-cache-dir .

USER appuser

EXPOSE 8080
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3)"

CMD ["python", "-m", "oracle_arm_console"]
