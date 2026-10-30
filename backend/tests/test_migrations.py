import importlib.util
from pathlib import Path
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.database import make_engine
from app.main import create_app
from app.migrate import upgrade_database, current_revision, HEAD


def legacy_database(path):
    engine = make_engine(f'sqlite:///{path}')
    revision = Path(__file__).resolve().parents[1] / 'migrations/versions/0001_initial.py'
    spec = importlib.util.spec_from_file_location('frozen_initial_schema', revision)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.metadata().create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO messages(id,source,external_id,content,received_at) VALUES(1,'test','fixture-1','  原文\n完整保留  ','2026-10-30 12:00:00')"))
        connection.execute(text("INSERT INTO notifications(id,title,summary,category,priority,warnings,parser_version,created_at) VALUES(1,'test','原文','其他','normal','','rules-v1','2026-10-30 12:00:00')"))
        connection.execute(text('INSERT INTO origins(message_id,notification_id) VALUES(1,1)'))
        connection.execute(text("INSERT INTO tasks(id,title,notes,status,priority,notification_id,created_at,updated_at) VALUES(1,'test','','done','normal',1,'2026-10-30 12:00:00','2026-10-30 12:00:00')"))
    return engine


def test_legacy_upgrade_backup_and_trace_preserves_data(tmp_path):
    engine = legacy_database(tmp_path/'legacy.db')
    backup = upgrade_database(engine, tmp_path/'backups')
    assert backup and backup.is_file()
    assert current_revision(engine) == HEAD
    assert upgrade_database(engine, tmp_path/'backups') is None
    assert len(list((tmp_path/'backups').glob('*.db'))) == 1
    assert any(fk['referred_table'] == 'sources' for fk in inspect(engine).get_foreign_keys('messages'))
    with TestClient(create_app(f'sqlite:///{tmp_path / "legacy.db"}')) as client:
        trace = client.get('/api/tasks/1/trace').json()
        source = trace['notification']['sources'][0]
        assert source['content'] == '  原文\n完整保留  '
        assert source['source_id'] is None and source['authorization_snapshot'] is None
        assert trace['task']['status'] == 'done'
        assert len(client.get('/api/sources').json()) == 8
    backup_engine = make_engine(f'sqlite:///{backup}')
    assert current_revision(backup_engine) is None
    assert 'sources' not in inspect(backup_engine).get_table_names()
    with backup_engine.connect() as connection:
        assert connection.scalar(text('SELECT content FROM messages WHERE id=1')) == '  原文\n完整保留  '
    backup_engine.dispose()
    engine.dispose()


def test_unknown_or_partial_schema_is_never_stamped(tmp_path):
    engine = make_engine(f'sqlite:///{tmp_path / "unknown.db"}')
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE messages (id INTEGER PRIMARY KEY, content TEXT)'))
    with pytest.raises(RuntimeError, match='does not match'):
        upgrade_database(engine,tmp_path/'backups')
    assert inspect(engine).get_table_names() == ['messages']
    assert not (tmp_path/'backups').exists()
    engine.dispose()


def test_startup_requires_explicit_migration_for_legacy_database(tmp_path):
    engine = legacy_database(tmp_path/'legacy.db')
    with pytest.raises(RuntimeError, match='migration required'):
        with TestClient(create_app(f'sqlite:///{tmp_path / "legacy.db"}')):
            pass
    assert 'sources' not in inspect(engine).get_table_names()
    engine.dispose()
