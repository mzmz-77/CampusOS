"""Project-local migration entrypoint with backup before upgrading file SQLite."""
import argparse
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

BACKEND = Path(__file__).resolve().parents[1]
HEAD = '0002_sources'


def database_url():
    return os.getenv('DATABASE_URL', f'sqlite:///{BACKEND / "campusos.db"}')


def configuration():
    config = Config()
    config.set_main_option('script_location', str(BACKEND / 'migrations'))
    return config


def current_revision(engine):
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def validate_legacy_schema(engine):
    baseline = ScriptDirectory.from_config(configuration()).get_revision('0001_initial').module.metadata()
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if tables != set(baseline.tables):
        raise RuntimeError('Unversioned database does not match phase-one tables; no schema changes made.')
    for name, table in baseline.tables.items():
        columns = {c['name']: c for c in inspector.get_columns(name)}
        if set(columns) != set(table.columns.keys()):
            raise RuntimeError(f'Legacy schema mismatch in {name}; no schema changes made.')
        for column in table.columns:
            actual = columns[column.name]
            if actual['type']._type_affinity is not column.type._type_affinity or actual['nullable'] != column.nullable:
                raise RuntimeError(f'Legacy column mismatch in {name}.{column.name}.')
        if inspector.get_pk_constraint(name)['constrained_columns'] != [c.name for c in table.primary_key.columns]:
            raise RuntimeError(f'Legacy primary key mismatch in {name}.')
        actual_unique = {tuple(c['column_names']) for c in inspector.get_unique_constraints(name)}
        required_unique = {tuple(c.name for c in constraint.columns) for constraint in table.constraints
                           if constraint.__class__.__name__ == 'UniqueConstraint'}
        if not required_unique.issubset(actual_unique):
            raise RuntimeError(f'Legacy uniqueness mismatch in {name}.')
        actual_fks = {(tuple(fk['constrained_columns']), fk['referred_table'], tuple(fk['referred_columns']))
                      for fk in inspector.get_foreign_keys(name)}
        required_fks = {(tuple(c.parent.name for c in fk.elements), next(iter(fk.elements)).column.table.name,
                         tuple(c.column.name for c in fk.elements)) for fk in table.foreign_key_constraints}
        if not required_fks.issubset(actual_fks):
            raise RuntimeError(f'Legacy foreign key mismatch in {name}.')


def upgrade_database(engine, backup_dir=None):
    revision = current_revision(engine)
    if revision == HEAD:
        return None
    tables = inspect(engine).get_table_names()
    if revision is None and tables:
        validate_legacy_schema(engine)
    if revision is not None and revision != '0001_initial':
        raise RuntimeError('Unknown database revision; refusing to modify it.')
    backup = None
    path = engine.url.database
    if tables and engine.dialect.name == 'sqlite' and path not in (None, '', ':memory:'):
        folder = Path(backup_dir) if backup_dir else BACKEND.parent / 'work' / 'backups'
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup = folder / f'campusos-before-{HEAD}-{stamp}.db'
        with sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True) as original:
            with sqlite3.connect(backup) as destination:
                original.backup(destination)
                if destination.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise RuntimeError('SQLite backup integrity check failed; migration cancelled.')
    with engine.begin() as connection:
        config = configuration()
        config.attributes['connection'] = connection
        if revision is None and tables:
            command.stamp(config, '0001_initial')
        command.upgrade(config, 'head')
    return backup


def ensure_database(engine):
    if not inspect(engine).get_table_names():
        upgrade_database(engine)
    elif current_revision(engine) != HEAD:
        raise RuntimeError('Database migration required. Run: cd backend && ../.venv/bin/python -m app.migrate')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    from .database import make_engine
    engine = make_engine(database_url())
    try:
        if args.check:
            revision = current_revision(engine)
            print(f'Database revision: {revision or "unversioned"}; expected: {HEAD}')
            return 0 if revision == HEAD else 1
        backup = upgrade_database(engine)
        print(f'Database revision: {current_revision(engine)}')
        if backup:
            print(f'Backup saved: {backup}')
        return 0
    finally:
        engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
