from app.parser import parse


def test_explicit_deadline():
    result = parse('奖学金材料提交\n截止时间：2026年11月2日 18:00，逾期不受理。')
    assert result['category'] == '奖助评优'
    assert result['priority'] == 'high'
    assert result['deadline'].isoformat() == '2026-11-02T18:00:00+08:00'


def test_uncertain_dates_are_not_invented():
    assert parse('请明天前提交作业')['deadline'] is None
    assert parse('截止 2026-02-30 12:00')['deadline'] is None
    assert parse('截止 2026-11-01 12:00 或 2026-11-02 12:00')['deadline'] is None


def test_parse_api_idempotent(client):
    message = client.post('/api/messages',json={'source':'手工测试','content':'课程作业\n截止 2026-11-02 12:00'}).json()
    url = f'/api/messages/{message["id"]}/parse'
    parsed = client.post(url)
    assert parsed.status_code == 200
    assert parsed.json()['id'] == client.post(url).json()['id']
    assert len(client.get('/api/notifications').json()) == 1
    assert client.post('/api/messages/999/parse').status_code == 404


def test_parsed_deadline_storage_preserves_instant(client):
    raw = client.post('/api/messages',json={'source':'手工测试','content':'提交材料\n截止 2026-11-02 18:00'}).json()
    n = client.post(f'/api/messages/{raw["id"]}/parse').json()
    assert n['deadline'] == '2026-11-02T10:00:00+00:00'
