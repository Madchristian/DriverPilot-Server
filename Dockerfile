# DriverPilot Ferndiagnose-Server. Laeuft als Nicht-root, braucht keinen Docker-Socket.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

RUN groupadd --gid 10001 driverpilot && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin driverpilot

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY driverpilot_server ./driverpilot_server
COPY contract ./contract
COPY privacy_notice.txt .
RUN mkdir -p /downloads

RUN mkdir -p /data && chown driverpilot:driverpilot /data
USER driverpilot
ENV DP_DATA_DIR=/data DP_DOWNLOADS_DIR=/downloads
EXPOSE 8140 8141

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8140/readyz', timeout=3).status == 200 else 1)"

CMD ["python", "-m", "driverpilot_server.main"]
