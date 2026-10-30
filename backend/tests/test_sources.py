from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import create_app
from app.database import Source


def patch(client, source_id, **values):
    current = client.get(f'/api/sources/{source_id}').json()
    return client.patch(f'/api/sources/{source_id}', json={
        'expected_revision': current['revision'], 'reason': '测试夹具，不代表真实校园授权', **values})


def grant(client, source_id=1, **values):
    return patch(client, source_id, access_method='manual_import', authorization_status='granted',
                 authorization_scope='仅限本项目合成测试消息', authorization_reference='test-fixture-only',
                 authorization_confirmed=True, **values)


def test_catalog_defaults_and_immutable_identity(client):
    sources = client.get('/api/sources').json()
    assert len(sources) == 8
    assert [s['name'] for s in sources] == ['西电学校官网', '西电计算机科学与技术学院官网', '学校微信公众号', '学校微信企业号', 'QQ 群', '微信群', '学在西电', 'XDYou']
    assert all(not s['enabled'] and not s['effective_enabled'] for s in sources)
    assert all(s['authorization_status'] == 'not_requested' for s in sources)
    assert patch(client, 1, name='伪造名称').status_code == 422
    assert client.get('/api/sources/999').status_code == 404
    assert client.get('/api/sources/999/events').status_code == 404
    assert client.delete('/api/sources/1').status_code == 405
    assert client.get('/api/sources?limit=501').status_code == 422


def test_authorization_required_to_enable_and_to_ingest(client):
    assert patch(client, 1, enabled=True).status_code == 409
    assert client.post('/api/messages', json={'source':'手工测试','source_id':1,'content':'test'}).status_code == 409
    assert client.post('/api/messages', json={'source':'手工测试','source_id':999,'content':'test'}).status_code == 404
    assert patch(client, 1, authorization_status='granted').status_code == 422
    assert patch(client, 1, authorization_status='granted', authorization_confirmed=True).status_code == 422
    assert len(client.get('/api/sources/1/events').json()) == 1
    assert client.get('/api/sources/1').json()['revision'] == 1


def test_grant_enable_revoke_and_keep_historical_snapshot(client):
    assert grant(client).status_code == 200
    assert not client.get('/api/sources/1').json()['enabled']
    enabled = patch(client, 1, enabled=True).json()
    assert enabled['effective_enabled']
    payload = {'source':'手工测试来源','source_id':1,'content':'原文不变','external_id':'test-1'}
    message = client.post('/api/messages', json=payload).json()
    assert message['authorization_snapshot']['reference'] == 'test-fixture-only'
    assert message['authorization_snapshot']['authorization_event_id']
    assert client.post('/api/messages', json=payload).json()['id'] == message['id']
    notice = client.post(f'/api/messages/{message["id"]}/parse').json()
    assert patch(client, 1, authorization_status='revoked').json()['enabled'] is False
    assert client.post('/api/messages', json={**payload,'external_id':'test-2'}).status_code == 409
    detail = client.get(f'/api/notifications/{notice["id"]}').json()
    assert detail['sources'][0]['authorization_snapshot'] == message['authorization_snapshot']
    assert detail['sources'][0]['content'] == '原文不变'
    events = client.get('/api/sources/1/events').json()
    assert len(events) == 4
    assert events[0]['before']['authorization_status'] == 'granted'
    assert events[0]['after']['authorization_status'] == 'revoked'


def test_expired_authorization_cannot_ingest(client):
    assert grant(client, authorization_expires_at=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()).status_code == 422
    assert grant(client).status_code == 200
    patch(client, 1, enabled=True)
    with Session(client.app.state.engine) as session:
        source = session.get(Source, 1)
        source.authorization_expires_at = datetime.now(timezone.utc)-timedelta(seconds=1)
        session.commit()
    assert client.get('/api/sources/1').json()['integration_status'] == 'authorization_expired'
    assert not client.get('/api/sources/1').json()['effective_enabled']
    assert client.post('/api/messages', json={'source':'test','source_id':1,'content':'x'}).status_code == 409


def test_unimplemented_collectors_stay_disabled(client):
    assert grant(client).status_code == 200
    assert patch(client, 1, access_method='public_web', authorization_status='granted', authorization_confirmed=True).status_code == 200
    assert client.get('/api/sources/1').json()['integration_status'] == 'not_implemented'
    assert patch(client, 1, enabled=True).status_code == 409
    assert patch(client, 3, access_method='public_web').status_code == 422
    assert patch(client, 1, access_method='guessed-platform-api').status_code == 422


def test_stale_update_conflict_and_registry_survives_restart(tmp_path):
    url = f'sqlite:///{tmp_path / "source-state.db"}'
    with TestClient(create_app(url)) as client:
        source = client.get('/api/sources/1').json()
        assert grant(client).status_code == 200
        assert client.patch('/api/sources/1', json={'expected_revision':source['revision'], 'enabled':True,'reason':'stale'}).status_code == 409
    with TestClient(create_app(url)) as client:
        assert len(client.get('/api/sources').json()) == 8
        assert client.get('/api/sources/1').json()['authorization_status'] == 'granted'
        assert len(client.get('/api/sources/1/events').json()) == 2


def test_all_registry_endpoints_enforce_configured_token(monkeypatch):
    monkeypatch.setenv('CAMPUSOS_API_TOKEN','test-only')
    with TestClient(create_app('sqlite://')) as client:
        for path in ['/api/sources','/api/sources/1','/api/sources/1/events']:
            assert client.get(path).status_code == 401
        assert client.patch('/api/sources/1',json={'expected_revision':1,'reason':'test','enabled':True}).status_code == 401
        assert client.get('/api/sources', headers={'Authorization':'Bearer test-only'}).status_code == 200
