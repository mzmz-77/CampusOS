from fastapi.testclient import TestClient
from app.main import create_app


def test_survives_restart_and_immutable(tmp_path):
    url = f'sqlite:///{tmp_path / "persist.db"}'
    first = create_app(url)
    payload = {'source':'手工测试','content':'原文\n  空白与标点！','external_id':'persist','published_at':'2026-10-30T20:00:00+08:00'}
    with TestClient(first) as client:
        message = client.post('/api/messages', json=payload).json()
    first.state.engine.dispose()
    second = create_app(url)
    with TestClient(second) as client:
        restored = client.get(f'/api/messages/{message["id"]}').json()
        assert restored['content'] == payload['content']
        assert restored['received_at'] == message['received_at']
        assert client.patch(f'/api/messages/{message["id"]}',json={'content':'改写'}).status_code == 405
        assert client.post('/api/messages',json=payload).json()['id'] == message['id']
    second.state.engine.dispose()


def test_token_enforced(monkeypatch):
    monkeypatch.setenv('CAMPUSOS_API_TOKEN','test-only-token')
    app = create_app('sqlite://')
    with TestClient(app) as client:
        assert client.get('/api/messages').status_code == 401
        assert client.get('/api/messages',headers={'Authorization':'Bearer test-only-token'}).status_code == 200
    app.state.engine.dispose()
