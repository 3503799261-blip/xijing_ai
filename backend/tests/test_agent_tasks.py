"""OFFLINE lifecycle/API tests. Simulated workflow outputs are not AI evidence."""
import asyncio
import json
import time
from types import SimpleNamespace
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.config import Settings
from backend.app.errors import ServiceError
from backend.app.main import create_app
from backend.app.agents.store import TaskStore, AGENTS
from backend.app.agents.supervisor import Supervisor

BRIEF = {'requirements': '离线任务测试：不是真实文化知识或模型结果。', 'style': '京剧写意'}

def config(tmp_path, **kwargs):
    return Settings(_env_file=None, rag_data_dir=tmp_path / 'runtime', embedding_model_path=tmp_path / 'model', **kwargs)

def result(verdict='pass'):
    return {'design': {'name': '离线假设计'}, 'review': {'verdict': verdict}, 'citations': [],
            'uncertain': verdict != 'pass', 'confirmationReason': 'final_acceptance' if verdict == 'pass' else verdict}

def complete_steps(store, task_id):
    assert store.start(task_id)
    for aid in AGENTS:
        store.emit(task_id, aid, 'running', '离线开始')
        store.emit(task_id, aid, 'completed', '离线结束', {'testDouble': True})

def test_task_idempotence_queue_and_conflict(tmp_path):
    store = TaskStore(tmp_path / 'tasks.sqlite3')
    task_id, created = store.create(BRIEF, 'submit-0001', 1)
    assert created
    assert store.create(BRIEF, 'submit-0001', 1) == (task_id, False)
    with pytest.raises(ServiceError, match='IDEMPOTENCY_CONFLICT'):
        store.create({**BRIEF, 'requirements': '不同离线输入'}, 'submit-0001')
    store.create(BRIEF, 'submit-0002', 1)
    with pytest.raises(ServiceError, match='AGENT_QUEUE_FULL'):
        store.create(BRIEF, 'submit-0003', 1)

def test_state_artifact_events_and_confirmation_are_persistent(tmp_path):
    path = tmp_path / 'tasks.sqlite3'
    store = TaskStore(path)
    task_id, _ = store.create(BRIEF, 'submit-0001')
    complete_steps(store, task_id)
    store.finish(task_id, result())
    reopened = TaskStore(path)
    status = reopened.status(task_id)
    assert status['completedSteps'] == 4 and status['state'] == 'awaiting_confirmation'
    assert reopened.result(task_id)['publicationAllowed'] is False
    assert set(reopened.artifacts(task_id)) == set(AGENTS)
    sequence = [e['sequence'] for e in status['events']]
    assert sequence == list(range(1, len(sequence) + 1))
    for event in status['events']:
        if event['kind'] == 'task':
            assert 'taskState' in event and 'state' not in event
        else:
            assert event['state'] in {'running', 'completed'}
    confirmation = status['confirmation']
    with pytest.raises(ServiceError, match='AGENT_STALE_STATE'):
        reopened.confirm(task_id, confirmation['id'], 0)
    reopened.confirm(task_id, confirmation['id'], status['lastSequence'])
    assert reopened.result(task_id)['userConfirmed'] is True
    assert reopened.result(task_id)['publicationAllowed'] is True
    final_sequence = reopened.status(task_id)['lastSequence']
    reopened.confirm(task_id, confirmation['id'], status['lastSequence'])
    assert reopened.status(task_id)['lastSequence'] == final_sequence

@pytest.mark.parametrize('verdict', ['needs_revision', 'insufficient_evidence'])
def test_review_problem_cannot_be_overridden_by_user(tmp_path, verdict):
    store = TaskStore(tmp_path / 'tasks.sqlite3')
    task_id, _ = store.create(BRIEF, 'submit-0001')
    complete_steps(store, task_id)
    store.finish(task_id, result(verdict))
    status = store.status(task_id)
    assert not status['confirmation']['canAccept']
    with pytest.raises(ServiceError, match='AGENT_CONFIRMATION_INVALID'):
        store.confirm(task_id, status['confirmation']['id'], status['lastSequence'])
    assert not store.result(task_id)['publicationAllowed']

def test_recovery_marks_only_unfinished_tasks_failed(tmp_path):
    store = TaskStore(tmp_path / 'tasks.sqlite3')
    active, _ = store.create(BRIEF, 'submit-0001')
    store.start(active)
    store.emit(active, 'planner', 'running', '离线处理')
    waiting, _ = store.create(BRIEF, 'submit-0002')
    assert store.recover() == 2
    status = store.status(active)
    assert status['state'] == 'failed'
    assert status['agents'][0]['errorCode'] == 'WORKFLOW_INTERRUPTED'
    assert status['agents'][1]['state'] == 'pending'
    assert store.status(waiting)['state'] == 'failed'
    assert store.next_waiting() is None

def test_cancel_waiting_and_running_preserves_real_steps(tmp_path):
    store = TaskStore(tmp_path / 'tasks.sqlite3')
    task_id, _ = store.create(BRIEF, 'submit-0001')
    store.start(task_id)
    store.emit(task_id, 'planner', 'running')
    store.cancel(task_id, store.status(task_id)['lastSequence'])
    assert store.status(task_id)['state'] == 'running'
    assert store.cancelled(task_id)
    store.emit(task_id, 'planner', 'completed', '真实阶段结束', {'testDouble': True})
    store.complete_cancel(task_id)
    status = store.status(task_id)
    assert status['state'] == 'cancelled' and status['agents'][0]['state'] == 'completed'
    assert all(a['state'] == 'pending' for a in status['agents'][1:])
    store.cancel(task_id, 0)
    other, _ = store.create(BRIEF, 'submit-0002')
    store.cancel(other, store.status(other)['lastSequence'])
    assert store.status(other)['state'] == 'cancelled'

def test_invalid_transition_does_not_persist_fake_completion(tmp_path):
    store = TaskStore(tmp_path / 'tasks.sqlite3')
    task_id, _ = store.create(BRIEF, 'submit-0001')
    with pytest.raises(ValueError):
        store.emit(task_id, 'planner', 'completed', artifact={})
    assert store.status(task_id)['completedSteps'] == 0
    assert store.artifacts(task_id) == {}

@pytest.mark.parametrize('brief', ['', ' ', '京' * 1201, '😀' * 601, 'bad\x00input'])
def test_api_invalid_creation_inputs_safe_errors(tmp_path, brief):
    with TestClient(create_app(config(tmp_path))) as client:
        response = client.post('/api/v1/agent/create', json={'requirements': brief, 'style': '京剧写意'}, headers={'X-Idempotency-Key': 'submit-0001'})
        assert response.status_code == 422
        assert '1200' in response.json()['error']['message']
        assert str(tmp_path) not in response.text

def test_api_missing_services_and_unknown_task(tmp_path):
    with TestClient(create_app(config(tmp_path))) as client:
        response = client.post('/api/v1/agent/create', json=BRIEF, headers={'X-Idempotency-Key': 'submit-0001'})
        assert response.status_code == 503
        assert client.get('/api/v1/agent/status/missing').status_code == 404
        assert client.get('/api/v1/agent/result/missing').status_code == 404
        assert client.get('/api/v1/capabilities').json()['agentWorkflow'] is False
        assert client.get('/agent-tasks.sqlite3').status_code == 404

def test_api_real_persistence_with_explicit_offline_runner(tmp_path):
    app = create_app(config(tmp_path))
    supervisor = app.state.agent_supervisor
    async def runner(runtime, task_id, brief, emit, cancelled):
        for aid in AGENTS:
            await emit(aid, 'running', '离线执行')
            await emit(aid, 'completed', '离线假产物', {'testDouble': True})
        return result()
    supervisor.runner = runner
    with TestClient(app) as client:
        supervisor.available = lambda: True
        headers = {'X-Idempotency-Key': 'submit-0001'}
        response = client.post('/api/v1/agent/create', json=BRIEF, headers=headers)
        assert response.status_code == 202
        task_id = response.json()['taskId']
        duplicate = client.post('/api/v1/agent/create', json=BRIEF, headers=headers)
        assert duplicate.json()['taskId'] == task_id
        for _ in range(50):
            status = client.get(f'/api/v1/agent/status/{task_id}').json()
            if status['state'] == 'awaiting_confirmation':
                break
            time.sleep(.01)
        assert status['completedSteps'] == 4
        assert client.get(f'/api/v1/agent/result/{task_id}').json()['userConfirmed'] is False
        payload = {'confirmationId': status['confirmation']['id'], 'expectedSequence': status['lastSequence'], 'action': 'accept'}
        accepted = client.post(f'/api/v1/agent/confirm/{task_id}', json=payload)
        assert accepted.status_code == 200 and accepted.json()['state'] == 'completed'
        assert client.get(f'/api/v1/agent/result/{task_id}').json()['publicationAllowed'] is True

def test_supervisor_failure_and_shutdown_do_not_retry(tmp_path):
    async def scenario():
        calls = []
        runtime = SimpleNamespace(settings=config(tmp_path))
        async def runner(runtime, task_id, brief, emit, cancelled):
            calls.append(task_id)
            await emit('planner', 'running')
            raise ServiceError('LLM_TIMEOUT', '离线超时测试', 504, True)
        supervisor = Supervisor(runtime, runner)
        await supervisor.start()
        supervisor.available = lambda: True
        task_id = supervisor.create(BRIEF, 'submit-0001')
        for _ in range(50):
            if supervisor.store.status(task_id)['state'] == 'failed':
                break
            await asyncio.sleep(.01)
        assert calls == [task_id]
        assert supervisor.store.status(task_id)['agents'][0]['errorCode'] == 'LLM_TIMEOUT'
        await supervisor.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('cursor', ['-1', str(1 << 63), str(1 << 80)])
def test_api_rejects_cursor_outside_sqlite_integer_range(tmp_path, cursor):
    app = create_app(config(tmp_path))
    task_id, _ = app.state.agent_supervisor.store.create(BRIEF, 'cursor-test-0001')
    with TestClient(app) as client:
        response = client.get(f'/api/v1/agent/status/{task_id}', params={'afterSequence': cursor})
        assert response.status_code == 422
        assert response.json()['error']['code'] == 'INVALID_REQUEST'
        assert str(tmp_path) not in response.text
        valid = client.get(f'/api/v1/agent/status/{task_id}', params={'afterSequence': (1 << 63) - 1})
        assert valid.status_code == 200 and valid.json()['events'] == []


def test_second_supervisor_cannot_recover_or_dispatch_live_owner_tasks(tmp_path):
    """Real OS owner lock and SQLite, with an explicitly offline runner."""
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        calls = []
        runtime = SimpleNamespace(settings=config(tmp_path))

        async def runner(runtime, task_id, brief, emit, cancelled):
            calls.append(task_id)
            await emit('planner', 'running', '离线锁测试')
            entered.set()
            await release.wait()
            assert not cancelled()
            for index, aid in enumerate(AGENTS):
                if index:
                    await emit(aid, 'running', '离线锁测试')
                await emit(aid, 'completed', '离线假产物', {'offline': True})
            return result()

        first, second = Supervisor(runtime, runner), Supervisor(runtime, runner)
        await first.start()
        first.available = lambda: True
        try:
            task_id = first.create(BRIEF, 'owner-lock-0001')
            await asyncio.wait_for(entered.wait(), timeout=1)
            sequence = first.store.status(task_id)['lastSequence']
            await second.start()
            assert not second.ready and second.worker is None
            assert second.diagnostic == 'AGENT_TASKS_LOCKED'
            assert second.owner_lock is None and not second.available()
            assert first.store.status(task_id)['state'] == 'running'
            assert first.store.status(task_id)['lastSequence'] == sequence
            assert not first.store.cancelled(task_id)
            with pytest.raises(ServiceError, match='AGENT_SERVICE_UNAVAILABLE'):
                second.create(BRIEF, 'owner-lock-0002')
            release.set()
            for _ in range(50):
                if first.store.status(task_id)['state'] == 'awaiting_confirmation':
                    break
                await asyncio.sleep(.01)
            assert first.store.status(task_id)['state'] == 'awaiting_confirmation'
            assert calls == [task_id]
        finally:
            release.set()
            await second.close()
            await first.close()

    asyncio.run(scenario())


def test_owner_shutdown_releases_lock_and_reopen_recovers_only_unfinished(tmp_path):
    async def scenario():
        runtime = SimpleNamespace(settings=config(tmp_path))
        entered = asyncio.Event()
        calls = []

        async def blocked_runner(runtime, task_id, brief, emit, cancelled):
            calls.append(task_id)
            await emit('planner', 'running', '离线停机测试')
            entered.set()
            await asyncio.Event().wait()

        first = Supervisor(runtime, blocked_runner)
        await first.start()
        first.available = lambda: True
        active = first.create(BRIEF, 'shutdown-owner-0001')
        await asyncio.wait_for(entered.wait(), timeout=1)
        waiting = first.create(BRIEF, 'shutdown-owner-0002')
        await first.close()
        assert first.owner_lock is None and first.worker is None and not first.ready
        assert first.store.status(active)['state'] == 'failed'
        assert first.store.status(waiting)['state'] == 'waiting'
        reopened = Supervisor(runtime, blocked_runner)
        await reopened.start()
        try:
            assert reopened.ready and reopened.owner_lock is not None
            assert reopened.store.status(waiting)['state'] == 'failed'
            assert reopened.store.status(active)['agents'][0]['errorCode'] == 'WORKFLOW_INTERRUPTED'
            await asyncio.sleep(.02)
            assert calls == [active]  # Restart performs no retry or paid dispatch.
        finally:
            await reopened.close()

    asyncio.run(scenario())


def test_failed_start_releases_owner_lock(tmp_path):
    async def scenario():
        runtime = SimpleNamespace(settings=config(tmp_path))
        first = Supervisor(runtime)

        def broken_recovery():
            raise RuntimeError('offline injected recovery failure')

        first.store.recover = broken_recovery
        with pytest.raises(RuntimeError, match='offline injected'):
            await first.start()
        assert first.owner_lock is None and first.worker is None and not first.ready
        replacement = Supervisor(runtime)
        await replacement.start()
        try:
            assert replacement.ready and replacement.owner_lock is not None
        finally:
            await replacement.close()

    asyncio.run(scenario())


@pytest.mark.parametrize('state', ['failed', 'completed', 'cancelled', 'awaiting_confirmation', 'unknown_future_state'])
def test_terminal_held_and_unknown_task_states_stop_workflow_callbacks(tmp_path, state):
    store = TaskStore(tmp_path / 'tasks.sqlite3')
    task_id, _ = store.create(BRIEF, 'stop-guard-0001')
    assert store.start(task_id) and not store.cancelled(task_id)
    with store.connect() as db:
        db.execute('UPDATE agent_tasks SET state=? WHERE task_id=?', (state, task_id))
    assert store.cancelled(task_id)
    if state in {'failed', 'completed', 'cancelled'}:
        with pytest.raises(ServiceError, match='WORKFLOW_CANCELLED'):
            store.emit(task_id, 'planner', 'running', '不得继续')
        assert store.artifacts(task_id) == {}
