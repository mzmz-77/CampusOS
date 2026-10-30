def test_ingest_and_validate(client):
    response = client.post('/api/messages', json={'source':'手工录入','content':'  原文\n保持不变  '})
    assert response.status_code == 201
    assert response.json()['content'] == '  原文\n保持不变  '
    assert client.post('/api/messages', json={'source':' ', 'content':'x'}).status_code == 422
    assert client.post('/api/messages', json={'source':'a', 'content':'x', 'source_url':'javascript:alert(1)'}).status_code == 422
    assert client.get('/api/messages/999').status_code == 404


def test_idempotency_conflict(client):
    payload = {'source':'手工录入','external_id':'test-1','content':'通知'}
    first = client.post('/api/messages', json=payload).json()
    assert client.post('/api/messages', json=payload).json()['id'] == first['id']
    assert client.post('/api/messages', json={**payload,'content':'修改后的通知'}).status_code == 409
    assert len(client.get('/api/messages').json()) == 1
