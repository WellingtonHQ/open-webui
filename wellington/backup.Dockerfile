FROM python:3.12-slim

# ZoneInfo uses the system timezone database, including Pacific daylight saving.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY backup.py /backup.py
ENTRYPOINT ["python", "-u", "/backup.py"]
