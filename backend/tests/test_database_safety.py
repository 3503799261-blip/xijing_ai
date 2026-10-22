"""OFFLINE DB lifecycle: real temporary SQLite/files + licensed Duck, no suppliers.

Production data is never a fixture. Corruption/removal affects this test's
tmp_path only. Existing catalog reads do not assert a newly generated model.
"""
import asyncio
import hashlib
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings, PROJECT_ROOT
from backend.app.errors import ServiceError
from backend.app.database import validate_database
from backend.app.agents.store import TaskStore
from backend.app.assets.store import AssetStore
from backend.app.assets.usage import UsageManager
from backend.app.assets.service import AssetService
from backend.app.providers.budget import BudgetLedger
from backend.app.main import create_app
from backend.scripts.initialize_business_databases import initialize_business_databases


PAGES = ('index','history','roles','facial','music','gallery','video','about')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def config(tmp_path):
    return Settings(_env_file=None, rag_data_dir=tmp_path/'runtime',
                    embedding_model_path=tmp_path/'missing-model',
                    deepseek_api_key='', neural4d_api_key='', neural4d_admin_token='',
                    neural4d_generation_enabled=False, neural4d_protocol_verified=False)


def construct(kind, path, *, create=False):
    if kind == 'agent':
        return TaskStore(path, create=create)
    if kind == 'budget':
        return BudgetLedger(path, 3, create=create)
    if kind == 'asset':
        assert path.name == 'catalog.sqlite3'
        return AssetStore(path.parent, create=create)
    return UsageManager(path, create=create)


@pytest.mark.parametrize('kind', ['agent','budget','asset','quota'])
def test_default_open_missing_does_not_create_file_or_parent(tmp_path, kind):
    path=tmp_path/'never-created'/'catalog.sqlite3'
    with pytest.raises(ServiceError) as failure:
        construct(kind,path)
    assert failure.value.status == 503
    assert not path.exists() and not path.parent.exists()
    assert str(tmp_path) not in failure.value.message


@pytest.mark.parametrize('kind', ['agent','budget','asset','quota'])
@pytest.mark.parametrize('fault', ['directory','corrupt','partial','unreadable'])
def test_invalid_existing_store_is_never_repaired_or_overwritten(tmp_path,monkeypatch,kind,fault):
    path=tmp_path/'catalog.sqlite3'
    if fault=='directory':
        path.mkdir()
        before=None
    elif fault=='corrupt':
        path.write_bytes(b'OFFLINE CORRUPTION FIXTURE: not a SQLite database')
        before=digest(path)
    elif fault=='partial':
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE unrelated_fixture(value)')
            db.execute("INSERT INTO unrelated_fixture VALUES ('keep me')")
        before=digest(path)
    else:
        construct(kind,path,create=True)
        before=digest(path)
        import backend.app.database as database
        def denied(*args,**kwargs):
            raise PermissionError('offline simulated ACL refusal with '+str(path))
        monkeypatch.setattr(database.sqlite3,'connect',denied)
    for create in (False,True):
        with pytest.raises(ServiceError) as failure:
            construct(kind,path,create=create)
        assert failure.value.status==503 and str(tmp_path) not in failure.value.message
        if before is not None:
            assert digest(path)==before
        else:
            assert path.is_dir() and list(path.iterdir())==[]


@pytest.mark.parametrize('kind',['agent','budget','asset','quota'])
def test_explicit_first_initialization_and_strict_reopen(tmp_path,kind):
    path=tmp_path/'fresh'/'catalog.sqlite3'
    construct(kind,path,create=True)
    before=digest(path)
    construct(kind,path)
    construct(kind,path,create=True)
    assert digest(path)==before
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA quick_check').fetchall()==[('ok',)]


@pytest.mark.parametrize('kind',['agent','budget','asset','quota'])
def test_file_removed_after_open_is_not_recreated_by_connection(tmp_path,kind):
    path=tmp_path/'catalog.sqlite3'
    store=construct(kind,path,create=True)
    path.unlink()
    with pytest.raises(ServiceError):
        with store.connect():
            pytest.fail('Missing file must never open successfully')
    assert not path.exists()


def test_valid_initialized_business_stores_keep_read_write_behavior(tmp_path):
    settings=config(tmp_path)
    outcome=initialize_business_databases(settings)
    assert set(outcome['stores'].values())=={'initialized_new'}
    store=TaskStore(settings.rag_data_dir/'agent-tasks.sqlite3')
    task_id,_=store.create({'requirements':'明确离线持久化夹具，不是AI执行','style':'京剧写意'},'offline-db-lifecycle')
    store.fail(task_id,ServiceError('OFFLINE_FIXTURE','仅用于数据读写验证',503))
    assert TaskStore(store.path).status(task_id)['state']=='failed'
    ledger=BudgetLedger(settings.rag_data_dir/'api-budget.sqlite3',3)
    ledger.reserve('offline-only-cost-row',[{'role':'user','content':'synthetic'}],32)
    ledger.finish('offline-only-cost-row',{'prompt_tokens':1,'completion_tokens':1},'success')
    assert ledger.summary()['calls']==1
    before={p.name:digest(p) for p in (store.path,ledger.path,settings.rag_data_dir/'assets/catalog.sqlite3')}
    assert set(initialize_business_databases(settings)['stores'].values())=={'validated_existing'}
    assert all(digest(p)==before[p.name] for p in (store.path,ledger.path,settings.rag_data_dir/'assets/catalog.sqlite3'))
    assert not (tmp_path/'.runtime/neural4d-usage.sqlite3').exists()


def test_explicit_initializer_preflights_all_existing_files_before_any_creation(tmp_path):
    settings=config(tmp_path)
    bad=settings.rag_data_dir/'assets/catalog.sqlite3'
    bad.parent.mkdir(parents=True)
    bad.write_bytes(b'known corrupt isolated asset catalog')
    before=digest(bad)
    with pytest.raises(ServiceError):
        initialize_business_databases(settings)
    assert digest(bad)==before
    assert not (settings.rag_data_dir/'agent-tasks.sqlite3').exists()
    assert not (settings.rag_data_dir/'api-budget.sqlite3').exists()


def test_wrong_nonexistent_rag_path_serves_static_and_reports_unavailable_without_files(tmp_path):
    settings=config(tmp_path)
    app=create_app(settings)
    with TestClient(app,base_url='http://127.0.0.1:8000') as client:
        health=client.get('/api/v1/health').json()
        assert health['application']['available'] is True
        assert health['databases']['agent']['available'] is False
        assert health['databases']['budget']['available'] is False
        assert health['agents']['diagnostic']=='AGENT_DATABASE_UNAVAILABLE'
        assert health['budget']['available'] is False and 'calls' not in health['budget']
        assert client.get('/api/v1/capabilities').json()['questionAnswering'] is False
        assert client.get('/api/v1/agent/history').status_code==503
        assert all(client.get('/'+page+'.html').status_code==200 for page in PAGES)
    assert not settings.rag_data_dir.exists()


def fixture_assets(settings):
    initialize_business_databases(settings)
    tasks=TaskStore(settings.rag_data_dir/'agent-tasks.sqlite3')
    task_id,_=tasks.create({'requirements':'已有历史的明确离线夹具','style':'京剧写意'},'offline-saved-history')
    tasks.fail(task_id,ServiceError('OFFLINE_FIXTURE','非真实模型执行',503))
    service=AssetService(settings,tasks)
    raw=(PROJECT_ROOT/'backend/tests/fixtures/phase4/Duck.glb').read_bytes()
    model=service.register_fixture(raw,'Khronos Duck合法已有测试素材，非京剧成品，非Neural4D生成','Duck·数据库隔离测试')
    return tasks,task_id,model,raw


@pytest.mark.parametrize('fault',['missing','corrupt','missing_table','directory'])
def test_agent_failure_leaves_pages_and_existing_glb_available_then_recovers(tmp_path,fault):
    settings=config(tmp_path)
    tasks,task_id,model,raw=fixture_assets(settings)
    path=tasks.path
    original=path.read_bytes()
    budget=settings.rag_data_dir/'api-budget.sqlite3'
    catalog=settings.rag_data_dir/'assets/catalog.sqlite3'
    protected={p:digest(p) for p in (budget,catalog)}
    if fault=='missing':
        path.unlink()
    elif fault=='corrupt':
        path.write_bytes(b'corrupt isolated Agent database; keep these bytes')
    elif fault=='directory':
        path.unlink();path.mkdir()
    else:
        with sqlite3.connect(path) as db:
            db.execute('DROP TABLE agent_events')
    bad_hash=digest(path) if path.is_file() else None
    app=create_app(settings)
    with TestClient(app,base_url='http://127.0.0.1:8000') as client:
        health=client.get('/api/v1/health')
        assert health.status_code==200 and health.json()['status']=='degraded'
        assert health.json()['agents']['databaseAvailable'] is False
        cap=client.get('/api/v1/capabilities').json()
        assert cap['agentWorkflow'] is False and cap['modelViewer'] is True and cap['imageToModel'] is False
        for url in ('/api/v1/agent/history','/api/v1/agent/history/'+task_id,
                    '/api/v1/agent/status/'+task_id,'/api/v1/agent/result/'+task_id):
            r=client.get(url)
            assert r.status_code==503 and r.json()['error']['code']=='AGENT_DATABASE_UNAVAILABLE'
            assert str(tmp_path) not in r.text
        r=client.post('/api/v1/agent/create',json={'requirements':'不得实际执行','style':'京剧写意'},headers={'X-Idempotency-Key':'offline-no-execution'})
        assert r.status_code==503
        assert all(client.get('/'+page+'.html').status_code==200 for page in PAGES)
        assert client.get('/api/v1/assets/models/'+model['modelId']+'/file').content==raw
        assert app.state.agent_supervisor.worker is None
        with pytest.raises(ServiceError):
            app.state.asset_service.authoritative_result(task_id)
    if bad_hash:
        assert digest(path)==bad_hash
    else:
        assert not path.exists() if fault=='missing' else path.is_dir() and not list(path.iterdir())
    assert all(digest(p)==h for p,h in protected.items())
    if path.is_dir():path.rmdir()
    path.write_bytes(original) # Restore only this temporary fixture.
    with TestClient(create_app(settings),base_url='http://127.0.0.1:8000') as client:
        assert client.get('/api/v1/health').json()['agents']['databaseAvailable'] is True
        history=client.get('/api/v1/agent/history').json()
        assert history['total']==1 and history['items'][0]['taskId']==task_id
        assert client.get('/api/v1/assets/models/'+model['modelId']+'/file').content==raw
    assert path.read_bytes()==original
    assert all(digest(p)==h for p,h in protected.items())


def test_budget_failure_isolated_and_generation_fails_before_network(tmp_path):
    settings=config(tmp_path)
    tasks,_,model,raw=fixture_assets(settings)
    path=settings.rag_data_dir/'api-budget.sqlite3'
    path.write_bytes(b'bad isolated budget DB')
    before=digest(path)
    app=create_app(settings)
    with TestClient(app,base_url='http://127.0.0.1:8000') as client:
        h=client.get('/api/v1/health').json()
        assert h['budget']['available'] is False and h['llmVerified'] is False
        assert client.get('/api/v1/agent/history').json()['total']==1
        assert client.get('/about.html').status_code==200
        assert client.get('/api/v1/assets/models/'+model['modelId']+'/file').content==raw
        with pytest.raises(ServiceError) as e:
            asyncio.run(app.state.runtime.provider.generate([], 'no-network'))
        assert e.value.code=='BUDGET_DATABASE_UNAVAILABLE'
    assert digest(path)==before


def test_catalog_reading_survives_missing_creation_ledger_without_new_quota(tmp_path,monkeypatch):
    import backend.app.main as main
    settings=config(tmp_path)
    _,_,model,raw=fixture_assets(settings)
    absent=tmp_path/'never-create-new-pool'/'quota.sqlite3'
    monkeypatch.setattr(main,'USAGE_LEDGER_PATH',absent)
    with TestClient(main.create_app(settings),base_url='http://127.0.0.1:8000') as client:
        assert client.get('/api/v1/assets/models/'+model['modelId']+'/file').content==raw
        usage=client.get('/api/v1/assets/usage').json()
        assert usage['realEnabled'] is False and usage['used_calls'] is None and usage['remaining_calls'] is None
    assert not absent.exists() and not absent.parent.exists()


def test_schema_validation_is_read_only_and_does_not_add_required_table(tmp_path):
    path=tmp_path/'partial.sqlite3'
    with sqlite3.connect(path) as db:db.execute('CREATE TABLE existing(data)')
    before=digest(path)
    with pytest.raises(ServiceError):
        validate_database(path,{'missing':('id',)})
    assert digest(path)==before


def test_late_budget_loss_keeps_health_degraded_and_blocks_generation(tmp_path, monkeypatch):
    """Local readiness is a stub; only real temporary SQLite is removed here."""
    import httpx
    from pydantic import SecretStr
    from backend.app.providers.llm import DeepSeekProvider
    settings = config(tmp_path).model_copy(update={'deepseek_api_key': SecretStr('offline-readiness-fixture-only')})
    _, _, model, raw = fixture_assets(settings)
    app = create_app(settings)
    outbound = []
    def forbidden_supplier(request):
        outbound.append(request.method)
        raise AssertionError('No provider request may follow a missing budget database')
    app.state.runtime.provider.transport = httpx.MockTransport(forbidden_supplier)
    monkeypatch.setattr(DeepSeekProvider, 'verified', property(lambda self: True))
    path = settings.rag_data_dir / 'api-budget.sqlite3'
    with TestClient(app, base_url='http://127.0.0.1:8000') as client:
        # No knowledge function is called. This sentinel exercises the same
        # availability branch as an already-loaded local index.
        app.state.runtime.search_service = object()
        assert client.get('/api/v1/capabilities').json()['agentWorkflow'] is True
        path.unlink()  # Isolated fixture only, after successful startup.
        health = client.get('/api/v1/health')
        assert health.status_code == 200 and health.json()['status'] == 'degraded'
        assert health.json()['application']['available'] is True
        assert health.json()['databases']['budget']['available'] is False
        capabilities = client.get('/api/v1/capabilities')
        assert capabilities.status_code == 200
        assert capabilities.json()['questionAnswering'] is False
        assert capabilities.json()['agentWorkflow'] is False
        assert client.get('/api/v1/agent/history').json()['total'] == 1
        assert client.get('/about.html').status_code == 200
        assert client.get('/api/v1/assets/models/' + model['modelId'] + '/file').content == raw
        with pytest.raises(ServiceError) as failure:
            asyncio.run(app.state.runtime.provider.generate([], 'late-budget-must-not-send'))
        assert failure.value.code == 'BUDGET_DATABASE_UNAVAILABLE'
        assert not outbound and not path.exists()
    assert not path.exists()


def test_late_agent_loss_is_not_reported_as_available_before_health(tmp_path, monkeypatch):
    """Capability reads must catch a disappeared task DB without a prior poll."""
    from backend.app.providers.llm import DeepSeekProvider
    settings = config(tmp_path)
    tasks, task_id, model, raw = fixture_assets(settings)
    app = create_app(settings)
    monkeypatch.setattr(DeepSeekProvider, 'verified', property(lambda self: True))
    with TestClient(app, base_url='http://127.0.0.1:8000') as client:
        app.state.runtime.search_service = object()
        assert client.get('/api/v1/capabilities').json()['agentWorkflow'] is True
        tasks.path.unlink()  # No process in this test holds a task connection.
        capabilities = client.get('/api/v1/capabilities')
        assert capabilities.status_code == 200 and capabilities.json()['agentWorkflow'] is False
        health = client.get('/api/v1/health')
        assert health.status_code == 200 and health.json()['agents']['databaseAvailable'] is False
        for url in ('/api/v1/agent/history', '/api/v1/agent/status/' + task_id):
            response = client.get(url)
            assert response.status_code == 503
            assert response.json()['error']['code'] == 'AGENT_DATABASE_UNAVAILABLE'
        assert client.get('/about.html').status_code == 200
        assert client.get('/api/v1/assets/models/' + model['modelId'] + '/file').content == raw
        assert not tasks.path.exists()
    assert not tasks.path.exists()


def test_agent_owner_lock_oserror_does_not_block_application_or_history(tmp_path, monkeypatch):
    """An explicit local lock refusal is not database repair or task execution."""
    import portalocker
    settings = config(tmp_path)
    tasks, _, model, raw = fixture_assets(settings)
    before = digest(tasks.path)
    original_acquire = portalocker.Lock.acquire
    failures = []
    def refused_agent_owner(lock, *args, **kwargs):
        if Path(lock.filename).name == 'agent-tasks-owner.lock':
            failures.append('agent_owner')
            raise PermissionError('offline owner lock ACL failure')
        return original_acquire(lock, *args, **kwargs)
    monkeypatch.setattr(portalocker.Lock, 'acquire', refused_agent_owner)
    app = create_app(settings)
    with TestClient(app, base_url='http://127.0.0.1:8000') as client:
        health = client.get('/api/v1/health')
        assert health.status_code == 200
        assert health.json()['application']['available'] is True
        assert health.json()['agents']['databaseAvailable'] is True
        assert health.json()['agents']['supervisorReady'] is False
        assert health.json()['agents']['diagnostic'] == 'AGENT_TASKS_LOCK_UNAVAILABLE'
        assert client.get('/api/v1/capabilities').json()['agentWorkflow'] is False
        assert client.get('/api/v1/agent/history').json()['total'] == 1
        assert client.get('/about.html').status_code == 200
        assert client.get('/api/v1/assets/models/' + model['modelId'] + '/file').content == raw
        assert app.state.agent_supervisor.worker is None
    assert failures == ['agent_owner'] and digest(tasks.path) == before
