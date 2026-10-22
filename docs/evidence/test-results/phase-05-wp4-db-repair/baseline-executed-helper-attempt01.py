"""WP4 database defects, frozen HEAD source, isolated files and denied HTTP only."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import sqlite3
import sys
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True
WORKSPACE = Path('D:/京剧')
BASE = WORKSPACE / '.runtime/phase5-wp4-db-repair-baseline-01'
REPO = BASE / 'source'
ROOT = BASE / 'isolated'
if ROOT.exists():
    raise RuntimeError('NEW_ISOLATED_ROOT_REQUIRED')
ROOT.mkdir()
(ROOT / 'empty.env').write_text('# no credentials\n', encoding='utf-8')
(ROOT / 'tmp').mkdir()
for key in list(os.environ):
    if key.upper().startswith(('DEEPSEEK_', 'NEURAL4D_', 'RAG_', 'AGENT_', 'EMBEDDING_')):
        os.environ.pop(key, None)
os.environ.update(XIJING_ENV_FILE=str(ROOT / 'empty.env'), RAG_DATA_DIR=str(ROOT / 'module-default'),
    EMBEDDING_MODEL_PATH=str(ROOT / 'missing-model'), DEEPSEEK_API_KEY='', NEURAL4D_API_KEY='',
    NEURAL4D_GENERATION_ENABLED='false', NEURAL4D_PROTOCOL_VERIFIED='false',
    HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_DATASETS_OFFLINE='1',
    TEMP=str(ROOT/'tmp'), TMP=str(ROOT/'tmp'), TMPDIR=str(ROOT/'tmp'))
platform.platform()
counts = {'blockedNetwork': 0, 'blockedFile': 0, 'blockedSqlite': 0,
          'allowedAsyncioLoopbackControlSockets': 0}

def inside(path, parent):
    return path == parent or parent in path.parents

def normalize(value):
    if isinstance(value, int):
        return None
    try:
        return Path(os.fsdecode(value)).resolve()
    except (TypeError, ValueError, OSError):
        return None

def guard_file(value, write=False):
    path = normalize(value)
    if path is None:
        return
    forbidden = inside(path, WORKSPACE / '.private-config')
    other_runtime = inside(path, WORKSPACE / '.runtime') and not inside(path, BASE)
    if forbidden or other_runtime or (write and not inside(path, ROOT)):
        counts['blockedFile'] += 1
        raise RuntimeError('BASELINE_FILE_BOUNDARY_BLOCKED')

def audit(event, values):
    if event == 'open':
        mode = values[1] or ''
        flags = values[2] if len(values) > 2 else 0
        write = isinstance(mode, str) and any(c in mode for c in 'wax+')
        write = write or bool(isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        guard_file(values[0], write)
    elif event == 'sqlite3.connect' and values[0] != ':memory:':
        value = values[0]
        if isinstance(value, str) and value.startswith('file:'):
            value = unquote(urlsplit(value).path)
            if len(value)>2 and value[0]=='/' and value[2]==':':
                value=value[1:]
        path=normalize(value)
        if path is None or not inside(path,ROOT):
            counts['blockedSqlite'] += 1
            raise RuntimeError('BASELINE_SQLITE_BOUNDARY_BLOCKED')
    elif event in ('os.mkdir','os.remove','os.rmdir','os.chmod','os.utime'):
        guard_file(values[0],True)
    elif event in ('os.rename','os.link'):
        guard_file(values[0],event=='os.rename')
        guard_file(values[1],True)
    elif event=='os.symlink':
        guard_file(values[1],True)
    elif event in ('socket.connect','socket.getaddrinfo'):
        address=values[1] if event=='socket.connect' else values[0]
        host=address[0] if isinstance(address,tuple) else address
        if host in ('127.0.0.1','::1','localhost'):
            counts['allowedAsyncioLoopbackControlSockets'] += 1
            return
        counts['blockedNetwork'] += 1
        raise RuntimeError('BASELINE_NETWORK_BLOCKED')

sys.addaudithook(audit)
sys.path.insert(0,str(REPO))
import httpx
def deny(*args,**kwargs):
    counts['blockedNetwork'] += 1
    raise RuntimeError('BASELINE_HTTP_TRANSPORT_BLOCKED')
async def deny_async(*args,**kwargs):
    return deny()
httpx.HTTPTransport.handle_request=deny
httpx.AsyncHTTPTransport.handle_async_request=deny_async
config=importlib.import_module('backend.app.config')
config.WORKSPACE_ROOT=ROOT/'workspace'
main=importlib.import_module('backend.app.main')
from fastapi.testclient import TestClient
from backend.app.agents.store import TaskStore
from backend.app.errors import ServiceError
assert main.USAGE_LEDGER_PATH.is_relative_to(ROOT)

def settings(root):
    return config.Settings(_env_file=None,rag_data_dir=root,embedding_model_path=ROOT/'missing-model',agent_workflow_enabled=False)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def files(root):
    return {p.relative_to(root).as_posix(): {'bytes':p.stat().st_size,'sha256':sha(p)}
            for p in root.rglob('*') if p.is_file()}

def statuses(app):
    with TestClient(app) as client:
        health=client.get('/api/v1/health')
        history=client.get('/api/v1/agent/history')
        pages={name:client.get('/'+name+'.html').status_code for name in
               ('index','history','roles','facial','music','video','gallery','about')}
        return {'healthStatus':health.status_code,'knowledgeDiagnostic':health.json().get('diagnostic'),
                'historyStatus':history.status_code,'historyTotal':history.json().get('total'),
                'pageStatuses':pages}

results=[]
def case(name,fn):
    try:
        detail=fn()
        row={'name':name,'status':'PASS','meaning':'baseline behavior observed, not repaired acceptance','detail':detail}
    except BaseException as exc:
        row={'name':name,'status':'FAIL','errorType':type(exc).__name__,
             'error':str(exc) if isinstance(exc,AssertionError) else 'ISOLATED_BASELINE_ERROR'}
    results.append(row)
    print(json.dumps(row,ensure_ascii=True))

def wrong_path():
    path=ROOT/'A-wrong-nonexistent-path'/'runtime-typo'
    assert not path.exists()
    app=main.create_app(settings(path))
    checks=statuses(app)
    created=files(path)
    assert (path/'agent-tasks.sqlite3').is_file()
    assert (path/'api-budget.sqlite3').is_file()
    assert (path/'assets/catalog.sqlite3').is_file()
    assert checks['historyTotal']==0
    return {'vulnerabilityReproduced':True,'configuredRootPreviouslyExisted':False,
            'createdFiles':created,'app':checks}

def missing_agent():
    path=ROOT/'B-missing-existing-agent'
    store=TaskStore(path/'agent-tasks.sqlite3')
    tid,_=store.create({'requirements':'isolated baseline fixture, no model execution'},'baseline-missing-history')
    store.fail(tid,ServiceError('FIXTURE_CLOSED','测试夹具不执行AI',503))
    original=path/'saved-original-agent.sqlite3'
    store.path.rename(original)
    before=sha(original)
    app=main.create_app(settings(path))
    checks=statuses(app)
    assert checks['historyTotal']==0 and (path/'agent-tasks.sqlite3').is_file()
    assert sha(original)==before
    return {'vulnerabilityReproduced':True,'preservedOriginalHash':before,
            'savedTaskId':tid,'newEmptyAgentDatabase':True,
            'createdFiles':files(path),'app':checks}

def corrupt_agent():
    path=ROOT/'C-corrupt-agent'
    store=TaskStore(path/'agent-tasks.sqlite3')
    preserved=path/'valid-original.sqlite3'
    preserved.write_bytes(store.path.read_bytes())
    store.path.write_bytes(b'WP4 repair deliberate corrupt SQLite fixture, no real data.')
    before=sha(store.path)
    try:
        main.create_app(settings(path))
    except sqlite3.DatabaseError as exc:
        assert sha(store.path)==before
        return {'vulnerabilityReproduced':True,'factoryRaises':type(exc).__name__,
                'failureLocation':'create_app -> Supervisor.__init__ -> TaskStore.__init__ -> executescript',
                'staticAndGlbUnavailableBecauseNoAppConstructed':True,
                'corruptHashUnchanged':True,'corruptSha256':before,'createdFiles':files(path)}
    raise AssertionError('corrupt baseline expected factory failure')

def normal_valid():
    path=ROOT/'D-valid-isolated-db'
    store=TaskStore(path/'agent-tasks.sqlite3')
    tid,_=store.create({'requirements':'isolated baseline fixture, not genuine AI'},'baseline-valid-history')
    store.fail(tid,ServiceError('FIXTURE_CLOSED','测试夹具不执行AI',503))
    app=main.create_app(settings(path))
    glb=(REPO/'backend/tests/fixtures/phase4/Duck.glb').read_bytes()
    model=app.state.asset_service.register_fixture(glb,'Licensed Duck, baseline isolated fixture only; not Neural4D.')
    with TestClient(app) as client:
        history=client.get('/api/v1/agent/history')
        loaded=client.get(model['fileUrl'])
        page=client.get('/about.html')
        assert history.status_code==200 and history.json()['total']==1
        assert page.status_code==200 and loaded.status_code==200
        assert hashlib.sha256(loaded.content).hexdigest()==hashlib.sha256(glb).hexdigest()
    return {'vulnerabilityReproduced':False,'validHistoryTaskId':tid,'historyTotal':1,
            'aboutStatus':200,'actualLicensedGlbStatus':200,'glbHash':hashlib.sha256(glb).hexdigest(),
            'glbBytes':len(glb),'viewerBrowserTestClaimed':False,'noKnowledgeResourcesRequired':True}

case('A_wrong_nonexistent_business_path_creates_empty_databases',wrong_path)
case('B_missing_existing_agent_database_recreated_as_empty',missing_agent)
case('C_corrupt_agent_database_blocks_whole_app_factory',corrupt_agent)
case('D_valid_isolated_database_history_and_real_glb_http',normal_valid)
output={'kind':'WP4_DATABASE_REPAIR_PRECHANGE_BASELINE','frozenSourceCommit':'3b40aa2',
        'sourceLocation':'source-at-3b40aa2.zip','results':results,
        'passed':sum(r['status']=='PASS' for r in results),'failed':sum(r['status']=='FAIL' for r in results),
        'skipped':0,'auditCounts':counts,'paidApiCalls':0,'neural4dCalls':0,
        'productionDatabaseAccess':'none; separate readonly snapshot executed before harness',
        'scope':'TestClient in-process HTTP, actual isolated SQLite and licensed test GLB; no browser or real model creation'}
(ROOT/'baseline-result.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
raise SystemExit(1 if output['failed'] else 0)
