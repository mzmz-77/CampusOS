from fastapi.testclient import TestClient
from app.main import create_app


def test_full_workflow_survives_restart(tmp_path):
    url = f'sqlite:///{tmp_path / "workflow.db"}'
    app = create_app(url)
    with TestClient(app) as client:
        notifications = []
        for source in ('手工测试A','手工测试B'):
            response = client.post('/api/messages',json={'source':source,'content':'课程作业\n截止 2026-11-02 18:00'})
            assert response.status_code == 201
            notifications.append(client.post(f'/api/messages/{response.json()["id"]}/parse').json())
        assert notifications[0]['id'] == notifications[1]['id']
        task = client.post('/api/tasks',json={'title':notifications[0]['title'],'deadline':notifications[0]['deadline'],'notification_id':notifications[0]['id']}).json()
        assert client.patch(f'/api/tasks/{task["id"]}',json={'status':'done','notes':'人工核对完成'}).status_code == 200
    app.state.engine.dispose()
    restarted = create_app(url)
    with TestClient(restarted) as client:
        trace = client.get(f'/api/tasks/{task["id"]}/trace').json()
        assert trace['task']['status'] == 'done'
        assert trace['task']['notes'] == '人工核对完成'
        assert trace['task']['deadline'] == '2026-11-02T10:00:00+00:00'
        assert len(trace['notification']['sources']) == 2
        assert len(client.get('/api/messages?limit=1&offset=1').json()) == 1
        assert client.get('/api/messages?limit=501').status_code == 422
        assert client.get('/api/tasks?offset=-1').status_code == 422
    restarted.state.engine.dispose()
