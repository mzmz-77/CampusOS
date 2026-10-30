def test_task_lifecycle(client):
    response = client.post('/api/tasks',json={'title':'提交材料','deadline':'2026-11-02T18:00:00+08:00'})
    assert response.status_code == 201
    url = f'/api/tasks/{response.json()["id"]}'
    assert client.patch(url,json={'status':'doing'}).json()['status'] == 'doing'
    assert client.patch(url,json={'status':'done','deadline':None}).json()['deadline'] is None
    assert client.patch(url,json={'status':'unknown'}).status_code == 422
    assert client.patch(url,json={'title':None}).status_code == 422
    assert client.post('/api/tasks',json={'title':'  '}).status_code == 422
    assert client.patch('/api/tasks/999',json={'status':'done'}).status_code == 404
    assert client.get('/api/tasks').json()[0]['status'] == 'done'


def test_task_notification_link(client):
    raw = client.post('/api/messages',json={'source':'手工测试','content':'考试通知'}).json()
    n = client.post(f'/api/messages/{raw["id"]}/parse').json()
    payload = {'title':n['title'],'notification_id':n['id']}
    assert client.post('/api/tasks',json=payload).status_code == 201
    assert client.post('/api/tasks',json=payload).status_code == 409
    assert client.post('/api/tasks',json={'title':'x','notification_id':999}).status_code == 404


def test_deadline_round_trip_preserves_instant(client):
    response = client.post('/api/tasks',json={'title':'时间测试','deadline':'2026-11-02T18:00:00+08:00'})
    assert response.json()['deadline'] == '2026-11-02T10:00:00+00:00'
    assert client.get('/api/tasks').json()[0]['deadline'] == '2026-11-02T10:00:00+00:00'
    assert client.post('/api/tasks',json={'title':'时间测试','deadline':'2026-11-02T18:00:00'}).status_code == 422
