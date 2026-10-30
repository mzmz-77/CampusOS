def test_trace_to_exact_original(client):
    payload = {'source':'手工测试来源','external_id':'trace-1','source_url':'https://example.org/notices/1','content':'  提交材料\n请核对原文。','published_at':'2026-10-30T20:00:00+08:00'}
    raw = client.post('/api/messages',json=payload).json()
    n = client.post(f'/api/messages/{raw["id"]}/parse').json()
    task = client.post('/api/tasks',json={'title':n['title'],'notification_id':n['id']}).json()
    traced = client.get(f'/api/tasks/{task["id"]}/trace').json()
    source = traced['notification']['sources'][0]
    assert source['id'] == raw['id']
    for key in ('source','external_id','source_url','content'): assert source[key] == payload[key]
    assert source['received_at']
    assert traced['notification']['parser_version'] == 'rules-v1'
    assert client.get('/api/notifications/999').status_code == 404
    assert client.get('/api/tasks/999/trace').status_code == 404


def test_manual_task_has_no_invented_origin(client):
    task = client.post('/api/tasks',json={'title':'自行创建'}).json()
    assert client.get(f'/api/tasks/{task["id"]}/trace').json()['notification'] is None
