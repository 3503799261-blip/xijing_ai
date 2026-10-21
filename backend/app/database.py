"""Existing-only SQLite access and an explicit, non-repairing first-install path.

Normal runtime connections use SQLite mode=rw (or ro); neither may create a
missing file. Schema/integrity preflight is read-only. Initializers are explicit
and never overwrite or repair a file that already exists.
"""
import sqlite3
from pathlib import Path

from .errors import ServiceError


def open_existing(path, *, timeout=5, readonly=False, code='DATABASE_UNAVAILABLE', message='业务数据库不可用，请检查配置或恢复已有数据库。'):
    try:
        path = Path(path).expanduser().resolve()
        if not path.is_file():
            raise OSError('Expected an existing database file')
        return sqlite3.connect(path.as_uri() + ('?mode=ro' if readonly else '?mode=rw'),
                               uri=True, timeout=timeout)
    except (OSError, sqlite3.Error, ValueError):
        raise ServiceError(code, message, 503) from None


def validate_database(path, tables, *, objects=(), code='DATABASE_UNAVAILABLE', message='业务数据库不可用，请检查配置或恢复已有数据库。'):
    """Read-only complete-file check plus the current service's required schema.

    Identifiers come only from static application schema maps, never requests.
    Extra tables/columns are allowed; no automatic migration is performed.
    """
    db = open_existing(path, readonly=True, code=code, message=message)
    try:
        db.execute('PRAGMA query_only=ON')
        checks = db.execute('PRAGMA quick_check(1)').fetchall()
        if checks != [('ok',)]:
            raise sqlite3.DatabaseError('Integrity check failed')
        actual = {(row[0], row[1]) for row in db.execute('SELECT type,name FROM sqlite_master')}
        for name, columns in tables.items():
            if ('table', name) not in actual:
                raise sqlite3.DatabaseError('Required table missing')
            present = {row[1] for row in db.execute('PRAGMA table_info("' + name + '")')}
            if not set(columns).issubset(present):
                raise sqlite3.DatabaseError('Required column missing')
        if not set(objects).issubset(actual):
            raise sqlite3.DatabaseError('Required schema object missing')
    except (OSError, sqlite3.Error, ValueError):
        raise ServiceError(code, message, 503) from None
    finally:
        db.close()


def initialize_database(path, schema, tables, *, objects=(), seed=None,
                        code='DATABASE_UNAVAILABLE', message='业务数据库不可用，请检查配置或恢复已有数据库。'):
    """Create a fresh database only; existing partial/corrupt files are untouched.

    Exclusive file creation also rejects another initializer's claim. A failed
    first initialization stays failed and requires operator inspection; it is
    never silently reinitialized on the next application start.
    """
    try:
        path = Path(path).expanduser().resolve()
    except (OSError, ValueError):
        raise ServiceError(code, message, 503) from None
    if path.exists():
        validate_database(path, tables, objects=objects, code=code, message=message)
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb'):
            pass
    except FileExistsError:
        validate_database(path, tables, objects=objects, code=code, message=message)
        return False
    except (OSError, ValueError):
        raise ServiceError(code, message, 503) from None
    db = open_existing(path, code=code, message=message)
    try:
        db.executescript(schema)
        if seed is not None:
            seed(db)
        db.commit()
    except (OSError, sqlite3.Error, ValueError):
        db.rollback()
        raise ServiceError(code, message, 503) from None
    finally:
        db.close()
    validate_database(path, tables, objects=objects, code=code, message=message)
    return True
