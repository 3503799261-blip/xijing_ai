"""OFFLINE: only temporary saved tasks; no recovered production tasks or AI calls."""
import hashlib
import json
import sqlite3
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from backend.app.agents.history import HistoryReader, public_value
from backend.app.agents.store import TaskStore, AGENTS
from backend.app.api.agents import register_agents
from backend.app.errors import ServiceError

BRIEF = {'requirements': '离线测试夹具，不是真实历史AI运行。', 'style': '京剧写意'}


def saved_tasks(tmp_path, count=3):
    store = TaskStore(tmp_path / 'tasks.sqlite3', create=True)
    ids = []
    for index in range(count):
        task_id, _ = store.create(BRIEF, 'history-fixture-' + str(index), queue_limit=5)
        store.start(task_id)
        for aid in AGENTS:
            store.emit(task_id, aid, 'running', '离线开始')
            output = {'theme': '测试规划'} if aid == 'planner' else {'evidence': []} if aid == 'researcher' else {'name': '测试角色'} if aid == 'designer' else {'verdict': 'pass'}
            store.emit(task_id, aid, 'completed', '离线结束', output)
        store.finish(task_id, {'design': {'name': '测试角色'}, 'review': {'verdict': 'pass'}, 'citations': [], 'uncertain': False})
        if index % 2 == 0:
            status = store.status(task_id)
            store.confirm(task_id, status['confirmation']['id'], status['lastSequence'])
        ids.append(task_id)
    return store, ids


def http_client(store):
    app = FastAPI()
    # Isolated router fixture supplies the new supervisor read-preflight
    # contract without running a worker. Full app safety tests exercise its
    # real database guard against missing/corrupt configured files.
    supervisor = SimpleNamespace(store=store, store_path=store.path,
                                 require_database=lambda: store)
    # A route read must not access supervisor methods or mutate TaskStore.
    def forbidden(*args, **kwargs):
        raise AssertionError('History invoked a task mutation or workflow')
    supervisor.create = forbidden
    for name in ('status', 'result', 'artifacts', 'recover', 'create', 'start', 'finish', 'confirm', 'cancel', 'emit'):
        setattr(store, name, forbidden)
    @app.middleware('http')
    async def request_id(request, call_next):
        request.state.request_id = 'offline-history-request'
        return await call_next(request)
    @app.exception_handler(ServiceError)
    async def handle(request, exc):
        return JSONResponse(exc.public(request.state.request_id), status_code=exc.status)
    register_agents(app, supervisor)
    return TestClient(app)


def dump(path):
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        return '\n'.join(db.iterdump())


def test_list_reads_real_saved_rows_and_no_large_fields(tmp_path):
    store, ids = saved_tasks(tmp_path)
    items = HistoryReader(store.path).list()['items']
    assert {row['taskId'] for row in items} == set(ids)
    assert all(row['sourceType'] == 'persisted_history' for row in items)
    assert all(row['completedSteps'] == 4 and row['resultReadable'] for row in items)
    assert all(not {'brief', 'result', 'agents', 'events', 'idempotency_key', 'signature'} & row.keys() for row in items)
    assert all(row['executionType'] == 'unknown' for row in items)


def test_pagination_and_stable_tied_created_at_sort(tmp_path):
    store, ids = saved_tasks(tmp_path, 4)
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE agent_tasks SET created_at='2026-01-01T00:00:00+00:00'")
    reader = HistoryReader(store.path)
    first, second = reader.list(1, 2), reader.list(2, 2)
    assert [row['taskId'] for row in first['items'] + second['items']] == sorted(ids, reverse=True)
    assert first['total'] == 4 and first['totalPages'] == 2
    assert reader.list(100, 2)['items'] == []


@pytest.mark.parametrize('state,count', [('completed', 2), ('awaiting_confirmation', 1), ('failed', 0)])
def test_state_filter(tmp_path, state, count):
    store, _ = saved_tasks(tmp_path)
    answer = HistoryReader(store.path).list(state=state)
    assert answer['total'] == count
    assert all(row['state'] == state for row in answer['items'])


def test_type_and_exact_task_id_filters_are_parameterized(tmp_path):
    store, ids = saved_tasks(tmp_path)
    reader = HistoryReader(store.path)
    assert reader.list(task_type='character_creation')['total'] == 3
    assert reader.list(task_type='not_a_saved_type')['items'] == []
    assert reader.list(task_id=ids[0])['items'][0]['taskId'] == ids[0]
    assert reader.list(task_id="' OR 1=1--")['total'] == 0
    assert reader.list(state="' OR 1=1--")['total'] == 0


def test_detail_returns_saved_result_steps_events_human_record(tmp_path):
    store, ids = saved_tasks(tmp_path)
    result = HistoryReader(store.path).detail(ids[0])
    assert result['task']['state'] == 'completed'
    assert result['task']['startedAt'] and result['task']['finishedAt']
    assert result['result']['design']['name'] == '测试角色'
    assert result['culturalReview']['verdict'] == 'pass'
    assert result['humanConfirmation']['userConfirmed'] is True
    assert result['humanConfirmation']['confirmedAt']
    assert [agent['id'] for agent in result['agents']] == list(AGENTS)
    assert all(agent['input'] is None and '未保存' in agent['inputNote'] for agent in result['agents'])
    assert result['eventTotal'] == len(result['events'])
    assert result['source']['readOnly'] is True


def test_event_pagination_does_not_drop_or_replay_saved_events(tmp_path):
    store, ids = saved_tasks(tmp_path, 1)
    reader = HistoryReader(store.path)
    pages = [reader.detail(ids[0], page, 3) for page in range(1, 5)]
    sequences = [e['sequence'] for page in pages for e in page['events']]
    assert sequences == list(range(1, pages[0]['eventTotal'] + 1))
    assert all(page['eventTotalPages'] == 4 for page in pages)


def test_missing_database_is_empty_and_is_not_created(tmp_path):
    path = tmp_path / 'missing' / 'tasks.sqlite3'
    reader = HistoryReader(path)
    assert reader.list()['total'] == 0
    assert not path.parent.exists()
    with pytest.raises(ServiceError) as error:
        reader.detail(str(uuid4()))
    assert error.value.status == 404
    assert not path.exists()


def test_empty_existing_database(tmp_path):
    store = TaskStore(tmp_path / 'empty.sqlite3', create=True)
    result = HistoryReader(store.path).list()
    assert result['items'] == [] and result['availableStates'] == [] and result['totalPages'] == 0


def test_missing_detail_is_404(tmp_path):
    store, _ = saved_tasks(tmp_path, 1)
    with pytest.raises(ServiceError) as error:
        HistoryReader(store.path).detail(str(uuid4()))
    assert error.value.code == 'AGENT_TASK_NOT_FOUND' and error.value.status == 404


def test_partial_failed_artifact_is_available_without_final_design(tmp_path):
    store = TaskStore(tmp_path / 'tasks.sqlite3', create=True)
    task_id, _ = store.create(BRIEF, 'partial-fixture')
    store.start(task_id)
    store.emit(task_id, 'planner', 'running')
    store.emit(task_id, 'planner', 'completed', artifact={'theme': '已保存的部分规划'})
    store.fail(task_id, ServiceError('OFFLINE_FAILURE', '离线失败夹具'))
    result = HistoryReader(store.path).detail(task_id)
    assert result['task']['state'] == 'failed'
    assert result['result'] is None and result['culturalReview'] is None
    assert result['humanConfirmation']['userConfirmed'] is None
    assert result['agents'][0]['output']['theme'] == '已保存的部分规划'
    assert result['agents'][1]['output'] is None and 'output' in result['agents'][1]['missingFields']
    assert 'result' in result['missingFields']


def test_missing_optional_tables_and_corrupt_json_are_truthful(tmp_path):
    store, ids = saved_tasks(tmp_path, 1)
    with sqlite3.connect(store.path) as db:
        db.execute('DROP TABLE agent_steps')
        db.execute('DROP TABLE agent_artifacts')
        db.execute('UPDATE agent_tasks SET result_json=?', ('not JSON',))
        db.execute('UPDATE agent_events SET payload_json=? WHERE sequence=1', ('not JSON',))
    detail = HistoryReader(store.path).detail(ids[0])
    assert detail['task']['historyCompleteness'] == 'incomplete'
    assert detail['task']['startedAt'] is not None
    assert detail['result'] is None
    assert detail['events'][0]['incomplete'] is True
    assert all(agent['state'] is None and agent['output'] is None for agent in detail['agents'])
    assert 'agentSteps' in detail['missingFields']


def test_event_sequence_gap_is_not_complete(tmp_path):
    store, ids = saved_tasks(tmp_path, 1)
    with sqlite3.connect(store.path) as db:
        db.execute('DELETE FROM agent_events WHERE sequence=3')
    result = HistoryReader(store.path).detail(ids[0])
    assert result['task']['historyCompleteness'] == 'incomplete'
    assert 'eventSequence' in result['missingFields']


def test_object_event_with_missing_fields_is_flagged_not_reconstructed(tmp_path):
    store, ids = saved_tasks(tmp_path, 1)
    with sqlite3.connect(store.path) as db:
        db.execute('UPDATE agent_events SET payload_json=? WHERE sequence=1', (json.dumps({'summary': '保存不完整'}),))
    detail = HistoryReader(store.path).detail(ids[0])
    first = detail['events'][0]
    assert first['incomplete'] is True and first['sequence'] == 1
    assert 'occurredAt' in first['missingFields'] and 'occurredAt' not in first
    assert 'kind' in first['missingFields'] and 'kind' not in first


def test_read_transaction_keeps_task_snapshot_during_concurrent_fixture_update(tmp_path):
    store, ids = saved_tasks(tmp_path, 1)
    with sqlite3.connect(store.path) as db:
        db.execute('PRAGMA journal_mode=WAL')
    reader = HistoryReader(store.path)
    with reader.snapshot() as (db, _, __):
        first = db.execute('SELECT state FROM agent_tasks WHERE task_id=?', (ids[0],)).fetchone()[0]
        with sqlite3.connect(store.path) as writer:
            writer.execute("UPDATE agent_tasks SET state='failed' WHERE task_id=?", (ids[0],))
        again = db.execute('SELECT state FROM agent_tasks WHERE task_id=?', (ids[0],)).fetchone()[0]
        assert first == again == 'completed'
    assert reader.list()['items'][0]['state'] == 'failed'


def test_corrupt_database_and_schema_return_safe_error(tmp_path):
    path = tmp_path / 'broken.sqlite3'
    path.write_text('not SQLite; secret=do-not-leak', encoding='utf-8')
    with pytest.raises(ServiceError) as error:
        HistoryReader(path).list()
    public = error.value.public('request')
    assert public['error']['code'] == 'AGENT_HISTORY_UNAVAILABLE'
    assert 'secret' not in json.dumps(public) and str(path) not in json.dumps(public)
    with sqlite3.connect(tmp_path / 'other.sqlite3'):
        pass
    with pytest.raises(ServiceError, match='AGENT_HISTORY_UNAVAILABLE'):
        HistoryReader(tmp_path / 'other.sqlite3').list()


def test_snapshot_connection_is_read_only_even_for_accidental_mutations(tmp_path):
    store, _ = saved_tasks(tmp_path, 1)
    with HistoryReader(store.path).snapshot() as (db, _, __):
        assert db.execute('PRAGMA query_only').fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError):
            db.execute("UPDATE agent_tasks SET state='failed'")


def test_reads_never_mutate_bytes_rows_or_call_store_workflow(tmp_path):
    store, ids = saved_tasks(tmp_path, 2)
    before = dump(store.path)
    before_hash = hashlib.sha256(store.path.read_bytes()).hexdigest()
    with http_client(store) as client:
        assert client.get('/api/v1/agent/history').status_code == 200
        for task_id in ids:
            assert client.get('/api/v1/agent/history/' + task_id).status_code == 200
    assert dump(store.path) == before
    assert hashlib.sha256(store.path.read_bytes()).hexdigest() == before_hash


def test_http_get_only_no_store_requestid_and_query_validation(tmp_path):
    store, ids = saved_tasks(tmp_path, 1)
    with http_client(store) as client:
        response = client.get('/api/v1/agent/history', params={'taskId': ids[0], 'taskType': 'character_creation'})
        assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
        assert response.json()['requestId'] == 'offline-history-request'
        detail = client.get('/api/v1/agent/history/' + ids[0], params={'eventPageSize': 2})
        assert len(detail.json()['events']) == 2 and detail.headers['cache-control'] == 'no-store'
        for query in ({'page': 0}, {'pageSize': 51}, {'state': 'x' * 65}, {'taskId': 'x' * 129}):
            assert client.get('/api/v1/agent/history', params=query).status_code == 422
        assert client.get('/api/v1/agent/history/' + ids[0], params={'eventPageSize': 101}).status_code == 422
        assert client.post('/api/v1/agent/history').status_code == 405
        assert client.post('/api/v1/agent/history/' + ids[0]).status_code == 405


def test_redaction_never_exposes_keys_signed_queries_paths_or_hidden_reasoning(tmp_path):
    store, ids = saved_tasks(tmp_path, 1)
    secret = 'sk-1234567890abcdefgh'
    output = {'theme': '需要脱敏 ' + secret + ' Authorization=Bearer123',
              'researchQueries': ['https://trusted.example/doc?X-Amz-Signature=secretvalue'],
              'systemPrompt': 'hidden system prompt', 'reasoning_content': 'hidden reasoning',
              'execution': {'model': 'offline-fixture', 'usage': {'total_tokens': 0}, 'authorization': secret}}
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE agent_artifacts SET content_json=? WHERE agent_id='planner'", (json.dumps(output),))
        db.execute('UPDATE agent_steps SET summary=?', ('C:\\private\\secret.env ' + secret,))
    result = HistoryReader(store.path).detail(ids[0])
    text = json.dumps(result, ensure_ascii=False)
    assert secret not in text and 'secretvalue' not in text and 'hidden system prompt' not in text and 'hidden reasoning' not in text
    assert 'C:' not in text and 'Bearer123' not in text
    assert 'https://trusted.example/doc' in text
    assert result['task']['executionType'] == 'model_metadata_recorded'


def test_length_limits_and_untrusted_html_remain_inert_text():
    script = '<img src=x onerror=alert(1)><script>alert(2)</script>'
    value = public_value({'text': script, 'long': 'a' * 20000, 'items': list(range(300)), 'api_key': 'secret'})
    assert value['text'] == script
    assert len(value['long']) == 12000 and len(value['items']) == 200
    assert 'api_key' not in value


def test_asset_links_only_from_saved_matching_task_and_asset_ids(tmp_path):
    store, ids = saved_tasks(tmp_path, 2)
    catalog = tmp_path / 'assets' / 'catalog.sqlite3'
    catalog.parent.mkdir()
    asset_id, wrong_asset, internal_model, model_id = [str(uuid4()) for _ in range(4)]
    with sqlite3.connect(catalog) as db:
        db.executescript('CREATE TABLE character_assets(asset_id TEXT,content_json TEXT,created_at TEXT); CREATE TABLE asset_models(model_id TEXT,asset_id TEXT,content_json TEXT,created_at TEXT);')
        asset = {'assetId': asset_id, 'sourceTaskId': ids[0], 'characterId': str(uuid4()), 'name': '离线资产', 'styleMode': 'realistic', 'styleVersion': 1}
        db.execute('INSERT INTO character_assets VALUES (?,?,?)', (asset_id, json.dumps(asset), '2026-01-01'))
        db.execute('INSERT INTO asset_models VALUES (?,?,?,?)', (model_id, asset_id, json.dumps({'modelId': model_id, 'assetId': asset_id, 'origin': 'local_test_fixture', 'format': 'glb'}), '2026-01-01'))
        db.execute('INSERT INTO asset_models VALUES (?,?,?,?)', (internal_model, None, json.dumps({'modelId': internal_model, 'assetId': None, 'origin': 'neural4d_internal_test'}), '2026-01-01'))
        db.execute('INSERT INTO asset_models VALUES (?,?,?,?)', (str(uuid4()), asset_id, json.dumps({'modelId': str(uuid4()), 'assetId': wrong_asset}), '2026-01-01'))
    reader = HistoryReader(store.path, catalog)
    asset = reader.detail(ids[0])['assets'][0]
    assert asset['assetId'] == asset_id and asset['modelIds'] == [model_id]
    assert asset['models'][0]['origin'] == 'local_test_fixture'
    assert asset['viewerUrl'] == '/about.html?assetId=' + asset_id + '#ai-workshop-model'
    assert reader.detail(ids[1])['assets'] == []
    assert reader.detail(ids[1])['assetAssociationStatus'] == 'not_linked'
    assert internal_model not in json.dumps(reader.detail(ids[0]))
    with reader.snapshot() as (db, _, available):
        assert available
        with pytest.raises(sqlite3.OperationalError):
            db.execute('DELETE FROM asset_catalog.asset_models')
