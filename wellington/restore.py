"""Restore a verified standalone OpenWebUI SQLite backup while services are stopped."""

import argparse
import logging
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from pathlib import Path

from backup import backup_database


def open_backup(source: Path):
    # An immutable read allows older WAL-mode snapshots to be read on a read-only
    # mount. Only standalone backups are accepted so no committed WAL is ignored.
    for suffix in ('-wal', '-journal'):
        if Path(str(source) + suffix).exists():
            raise ValueError('Backup has journal sidecars; supply a standalone SQLite backup')
    return sqlite3.connect(source.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)


def validate_backup(connection):
    result = connection.execute('PRAGMA integrity_check').fetchall()
    if result != [('ok',)]:
        raise ValueError(f'Backup integrity check failed: {result}')
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {'chat', 'user'}.issubset(tables):
        raise ValueError('This is not an OpenWebUI database (chat/user tables are missing)')


def restore_database(source: Path, target: Path, backup_directory: Path):
    with closing(open_backup(source)) as src:
        validate_backup(src)
        # Snapshot the stopped instance before replacing it. Fresh volumes have
        # no database yet and can be restored without a pre-restore snapshot.
        if target.exists():
            backup_database(target, backup_directory / 'manual', retention_days=None)
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.webui-restore-', suffix='.db', delete=False) as file:
            temporary = Path(file.name)
        try:
            with closing(sqlite3.connect(temporary)) as restored:
                src.backup(restored)
                restored.execute('PRAGMA journal_mode=DELETE')
                validate_backup(restored)
            if target.exists():
                metadata = target.stat()
                temporary.chmod(stat.S_IMODE(metadata.st_mode))
                if os.name == 'posix':
                    os.chown(temporary, metadata.st_uid, metadata.st_gid)
            # Services must be stopped before removing old journals or swapping.
            for suffix in ('-wal', '-shm', '-journal'):
                Path(str(target) + suffix).unlink(missing_ok=True)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    logging.info('Database restored from %s', source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backup', type=Path)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    if args.check_only:
        with closing(open_backup(args.backup)) as source:
            validate_backup(source)
        logging.info('Backup integrity and OpenWebUI tables verified')
    else:
        restore_database(args.backup, Path('/data/webui.db'), Path('/backups'))


if __name__ == '__main__':
    main()
