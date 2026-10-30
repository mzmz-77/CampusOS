def ingest_parse(client, content, source):
    raw = client.post('/api/messages',json={'source':source,'content':content}).json()
    return raw, client.post(f'/api/messages/{raw["id"]}/parse').json()


def test_duplicates_merge_without_losing_sources(client):
    a, n1 = ingest_parse(client,'提交材料\n截止 2026-11-02 18:00','手工来源A')
    b, n2 = ingest_parse(client,'  提交材料  截止 2026-11-02 18:00  ','手工来源B')
    assert n1['id'] == n2['id']
    assert len(client.get('/api/messages').json()) == 2
    assert len(client.get('/api/notifications').json()) == 1
    detail = client.get(f'/api/notifications/{n1["id"]}').json()
    assert {s['id'] for s in detail['sources']} == {a['id'],b['id']}
    assert detail['sources'][0]['content'] == a['content']
    assert len(client.post(f'/api/messages/{b["id"]}/parse').json()) > 0
    assert len(client.get(f'/api/notifications/{n1["id"]}').json()['sources']) == 2


def test_changed_deadlines_and_text_stay_separate(client):
    _, a = ingest_parse(client,'提交材料 截止 2026-11-02 18:00','A')
    _, b = ingest_parse(client,'提交材料 截止 2026-11-03 18:00','B')
    _, c = ingest_parse(client,'无需提交材料 截止 2026-11-02 18:00','C')
    assert len({a['id'],b['id'],c['id']}) == 3
