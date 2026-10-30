"""Optional real PostgreSQL regression, enabled in CI with an isolated test database."""
import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.main import create_app


@pytest.mark.skipif(not os.getenv('CAMPUSOS_TEST_POSTGRES_URL'), reason='No dedicated PostgreSQL test database configured')
def test_postgres_registry_migrations_and_trace():
    url = make_url(os.environ['CAMPUSOS_TEST_POSTGRES_URL'])
    assert url.get_backend_name() == 'postgresql' and url.database.endswith('_test'), 'A dedicated *_test database is required'
    schema = 'campusos_' + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA {schema}'))
    isolated = url.update_query_dict({'options': f'-csearch_path={schema}'}).render_as_string(hide_password=False)
    try:
        with TestClient(create_app(isolated)) as client:
            assert len(client.get('/api/sources').json()) == 8
            grant = {'expected_revision':1,'reason':'CI synthetic test only','access_method':'manual_import',
                     'authorization_status':'granted','authorization_scope':'synthetic fixture messages',
                     'authorization_reference':'CI-only','authorization_confirmed':True,'enabled':True}
            assert client.patch('/api/sources/1',json=grant).status_code == 200
            raw = client.post('/api/messages',json={'source':'CI fixture','source_id':1,'content':'课程作业\n截止 2026-11-02 18:00'}).json()
            assert raw['authorization_snapshot']['reference'] == 'CI-only'
            notice = client.post(f'/api/messages/{raw["id"]}/parse').json()
            assert notice['deadline'] == '2026-11-02T10:00:00+00:00'
            task = client.post('/api/tasks',json={'title':'test','notification_id':notice['id']}).json()
            assert client.get(f'/api/tasks/{task["id"]}/trace').json()['notification']['sources'][0]['id'] == raw['id']
        with TestClient(create_app(isolated)) as client:
            assert client.get('/api/sources/1').json()['effective_enabled']
            assert len(client.get('/api/messages').json()) == 1
    finally:
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        admin.dispose()
