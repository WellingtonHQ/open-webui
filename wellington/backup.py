"""Daily, verified online backups of OpenWebUI's default SQLite database."""

import argparse
import logging
import os
import signal
import sqlite3
import threading
import time
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


LOGGER = logging.getLogger('open-webui-backup')
FILENAME_FORMAT = 'webui-%Y-%m-%d_%H-%M-%S-%fZ.sqlite3'


def backup_database(source: Path, destination: Path, retention_days: int | None) -> Path:
    """Publish only complete backups; prune this job's old files after success."""
    destination.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    output = destination / now.strftime(FILENAME_FORMAT)
    temporary = output.with_suffix('.partial')
    started = time.monotonic()

    def check_timeout(status, remaining, total):
        if time.monotonic() - started > 300:
            raise TimeoutError('SQLite backup exceeded five minutes; retrying later')

    try:
        # mode=ro also prevents accidentally creating an empty source database.
        with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)) as src:
            with closing(sqlite3.connect(temporary)) as target:
                src.backup(target, pages=256, progress=check_timeout, sleep=0.1)
                # Publish a standalone file, without requiring WAL sidecar files.
                target.execute('PRAGMA journal_mode=DELETE')
                result = target.execute('PRAGMA integrity_check').fetchall()
                if result != [('ok',)]:
                    raise RuntimeError(f'Backup integrity check failed: {result}')
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)

    LOGGER.info('Backup saved: %s (%s bytes)', output, output.stat().st_size)
    if retention_days is None:
        return output
    cutoff = now - timedelta(days=retention_days)
    for candidate in destination.glob('webui-*.sqlite3'):
        try:
            created = datetime.strptime(candidate.name, FILENAME_FORMAT).replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
        if created < cutoff:
            candidate.unlink()
            LOGGER.info('Expired backup removed: %s', candidate)
    return output


def next_backup(now: datetime, backup_time, zone: ZoneInfo) -> datetime:
    local_date = now.astimezone(zone).date()
    scheduled = datetime.combine(local_date, backup_time, tzinfo=zone)
    if scheduled.astimezone(timezone.utc) <= now:
        scheduled = datetime.combine(local_date + timedelta(days=1), backup_time, tzinfo=zone)
    return scheduled.astimezone(timezone.utc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--once', action='store_true', help='Back up now with scheduled retention')
    mode.add_argument('--manual', action='store_true', help='Back up now to manual/ without deleting backups')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    source = Path('/data/webui.db')
    destination = Path('/backups')
    if args.manual:
        backup_database(source, destination / 'manual', retention_days=None)
        return
    backup_time = datetime.strptime(os.getenv('BACKUP_TIME', '03:00'), '%H:%M').time()
    zone = ZoneInfo(os.getenv('BACKUP_TIMEZONE', 'America/Los_Angeles'))
    retention_days = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
    if retention_days < 1:
        raise ValueError('BACKUP_RETENTION_DAYS must be at least 1')
    if args.once:
        backup_database(source, destination, retention_days)
        return

    stopped = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    # Take an initial snapshot immediately, then follow the daily wall-clock schedule.
    while not stopped.is_set():
        try:
            backup_database(source, destination, retention_days)
        except Exception:
            LOGGER.exception('Backup failed; retrying in five minutes')
            stopped.wait(300)
            continue
        scheduled = next_backup(datetime.now(timezone.utc), backup_time, zone)
        LOGGER.info('Next backup: %s', scheduled.astimezone(zone).isoformat())
        while not stopped.is_set():
            remaining = (scheduled - datetime.now(timezone.utc)).total_seconds()
            if remaining <= 0:
                break
            stopped.wait(min(remaining, 60))


if __name__ == '__main__':
    main()
