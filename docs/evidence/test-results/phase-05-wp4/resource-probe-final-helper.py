"""WP4 private real-local missing/recovery probe. Never a production launcher.

Uses real local CPU BGE, genuine isolated SQLite/Qdrant and licensed Duck GLB.
Saved Agent rows are explicitly synthetic; no real provider requests permitted.
"""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import sys
import time
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True
REPO = Path.cwd().resolve()
WORKSPACE = REPO.parent
MODEL = WORKSPACE / '.runtime/models/bge-small-zh-v1.5'
HELPER = Path(__file__).resolve()


def run():
    args = argparse.ArgumentParser()
    args.add_argument('--run-root', required=True, type=Path)
    root = args.parse_args().run_root.resolve()
    if root.exists() or root.parent != WORKSPACE / '.runtime' or not root.name.startswith('phase5-wp4-resource-'):
        raise RuntimeError('NEW_PRIVATE_RUN_ROOT_REQUIRED')
    root.mkdir()
    (root / 'empty.env').write_text('# No credentials in isolated resource tests.\n', encoding='utf-8')
    (root / 'tmp').mkdir()
    for key in list(os.environ):
        if key.upper().startswith(('DEEPSEEK_', 'NEURAL4D_', 'RAG_', 'AGENT_', 'EMBEDDING_')) or key.upper() in {'ALLOWED_ORIGINS', 'REQUEST_TIMEOUT_SECONDS', 'RETRIEVAL_MIN_SCORE', 'RETRIEVAL_TOP_K', 'RETRIEVAL_MODE'}:
            os.environ.pop(key, None)
    os.environ.update({
        'XIJING_ENV_FILE': str(root / 'empty.env'), 'RAG_DATA_DIR': str(root / 'module-default'),
        'EMBEDDING_MODEL_PATH': str(root / 'missing-default-model'),
        'DEEPSEEK_API_KEY': '', 'NEURAL4D_API_KEY': '', 'NEURAL4D_ADMIN_TOKEN': '',
        'NEURAL4D_GENERATION_ENABLED': 'false', 'NEURAL4D_PROTOCOL_VERIFIED': 'false',
        'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'HF_DATASETS_OFFLINE': '1',
        'TEMP': str(root / 'tmp'), 'TMP': str(root / 'tmp'), 'TMPDIR': str(root / 'tmp'),
        'TORCH_HOME': str(root / 'torch-cache'), 'HF_HOME': str(root / 'hf-cache'),
    })
    platform.platform()
    counts = {'blockedNetwork': 0, 'blockedFile': 0, 'blockedSqlite': 0, 'allowedAsyncioLoopbackControlSockets': 0}

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
        other_runtime = inside(path, WORKSPACE / '.runtime') and not inside(path, root) and not inside(path, MODEL) and path != HELPER
        if forbidden or other_runtime or (write and not inside(path, root)):
            counts['blockedFile'] += 1
            raise RuntimeError('RESOURCE_TEST_FILE_BOUNDARY_BLOCKED')

    def audit(event, values):
        if event == 'open':
            mode = values[1] or ''
            flags = values[2] if len(values) > 2 else 0
            write = isinstance(mode, str) and any(c in mode for c in 'wax+')
            write = write or bool(isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            guard_file(values[0], write)
        elif event == 'sqlite3.connect' and values[0] != ':memory:':
            value = values[0]
            if isinstance(value, str) and value.startswith('file:'):
                value = unquote(urlsplit(value).path)
                if len(value) > 2 and value[0] == '/' and value[2] == ':':
                    value = value[1:]
            path = normalize(value)
            if path is None or not inside(path, root):
                counts['blockedSqlite'] += 1
                raise RuntimeError('RESOURCE_TEST_SQLITE_BOUNDARY_BLOCKED')
        elif event in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.utime'):
            guard_file(values[0], True)
        elif event in ('os.rename', 'os.link'):
            guard_file(values[0], event == 'os.rename')
            guard_file(values[1], True)
        elif event == 'os.symlink':
            guard_file(values[1], True)
        elif event in ('socket.connect', 'socket.getaddrinfo'):
            # Windows asyncio creates a local socketpair as its event-loop
            # wakeup pipe. Allow its loopback control channel only; actual
            # httpx network transports remain categorically denied above.
            address = values[1] if event == 'socket.connect' else values[0]
            host = address[0] if isinstance(address, tuple) else address
            if host in ('127.0.0.1', '::1', 'localhost'):
                counts['allowedAsyncioLoopbackControlSockets'] += 1
                return
            counts['blockedNetwork'] += 1
            raise RuntimeError('RESOURCE_TEST_NETWORK_BLOCKED')

    sys.addaudithook(audit)
    sys.path.insert(0, str(REPO))
    import httpx
    def deny(*unused, **kwargs):
        counts['blockedNetwork'] += 1
        raise RuntimeError('RESOURCE_TEST_REAL_HTTP_BLOCKED')
    async def deny_async(*unused, **kwargs):
        return deny()
    httpx.HTTPTransport.handle_request = deny
    httpx.AsyncHTTPTransport.handle_async_request = deny_async
    config = importlib.import_module('backend.app.config')
    config.WORKSPACE_ROOT = root / 'workspace'
    main = importlib.import_module('backend.app.main')
    from fastapi.testclient import TestClient
    from backend.scripts.ingest import build
    from backend.app.agents.store import TaskStore, AGENTS
    from backend.app.agents.history import HistoryReader
    from backend.app.errors import ServiceError
    from backend.app.assets.validation import validate_glb
    from backend.app.knowledge.embedding import EmbeddingService
    from backend.app.providers import neural4d
    assert main.USAGE_LEDGER_PATH == neural4d.CANONICAL_USAGE_LEDGER
    assert inside(main.USAGE_LEDGER_PATH, root)

    rows = []
    def case(name, fn):
        start = time.perf_counter()
        try:
            detail = fn()
            rows.append({'name': name, 'status': 'PASS', 'seconds': round(time.perf_counter() - start, 4), 'detail': detail})
        except BaseException as exc:
            rows.append({'name': name, 'status': 'FAIL', 'seconds': round(time.perf_counter() - start, 4), 'errorType': type(exc).__name__, 'assertion': str(exc) if isinstance(exc, AssertionError) or str(exc).startswith('RESOURCE_TEST_') else 'ISOLATED_PROBE_ERROR'})
        print(json.dumps(rows[-1], ensure_ascii=False))

    def settings(path, model=MODEL):
        return config.Settings(_env_file=None, rag_data_dir=path, embedding_model_path=model, agent_workflow_enabled=False)

    def response(r):
        data = r.json()
        return {'status': r.status_code, 'code': data.get('error', {}).get('code'), 'message': data.get('error', {}).get('message')}

    baseline = root / 'baseline'
    stats = None
    task_id = None
    def baseline_build():
        nonlocal stats, task_id
        stats = build(REPO / 'knowledge', settings(baseline))
        assert stats['status'] == 'built' and stats['chunks'] > 0
        store = TaskStore(baseline / 'agent-tasks.sqlite3')
        task_id, _ = store.create({'requirements': 'WP4 synthetic saved recovery fixture; not a real AI task.', 'style': '京剧写意'}, 'wp4-isolated-history-fixture')
        store.start(task_id)
        for aid in AGENTS:
            store.emit(task_id, aid, 'running', '离线测试夹具')
            store.emit(task_id, aid, 'completed', '离线测试夹具', {'fixture': True})
        store.finish(task_id, {'design': {'name': 'WP4离线保存夹具'}, 'review': {'verdict': 'pass'}, 'citations': [], 'uncertain': False})
        state = store.status(task_id)
        store.confirm(task_id, state['confirmation']['id'], state['lastSequence'])
        return {'ingest': stats, 'fixtureHistory': 'one synthetic completed task; no provider execution', 'embeddingDimension': 512}

    case('real_bge_corpus_ingestion_in_isolated_root', baseline_build)
    if not stats:
        (root / 'resource-probe-result.json').write_text(json.dumps({'results': rows, 'passed': 0, 'failed': 1, 'remaining': 'BLOCKED_BY_FAILED_SETUP', 'auditCounts': counts}, ensure_ascii=False, indent=2), encoding='utf-8')
        return 1

    def clone(name):
        target = root / name
        shutil.copytree(baseline, target)
        return target

    def check_app(path, model=MODEL, expect_ready=True):
        active = json.loads((path / 'active.json').read_text(encoding='utf-8'))
        generation_root = path / 'generations' / active['generation_id']
        metadata_path = generation_root / 'qdrant/meta.json'
        vector_metadata = json.loads(metadata_path.read_text(encoding='utf-8')) if metadata_path.is_file() else {}
        vector_present = bool(isinstance(vector_metadata.get('collections', {}).get('opera_chunks'), dict)
                              and (generation_root / 'qdrant/collection/opera_chunks/storage.sqlite').is_file())
        expected_code = ('EMBEDDING_MODEL_MISSING' if not model.is_dir() else
                         'KNOWLEDGE_DATABASE_MISSING' if not (generation_root / 'knowledge.sqlite3').is_file() else
                         'VECTOR_INDEX_MISSING' if not vector_present else
                         'KNOWLEDGE_LOAD_FAILED')
        app = main.create_app(settings(path, model))
        with TestClient(app) as client:
            health = client.get('/api/v1/health').json()
            search = client.post('/api/v1/knowledge/search', json={'question': '京剧中的生旦净丑是什么？'})
            pages = [client.get('/' + page + '.html').status_code for page in ('index', 'history', 'roles', 'facial', 'music', 'video', 'gallery', 'about')]
            history = client.get('/api/v1/agent/history').json()
            assert pages == [200] * 8
            assert history['total'] == 1
            assert history['items'][0]['taskId'] == task_id
            assert health['llmConfigured'] is False and health['llmVerified'] is False
            if expect_ready:
                assert health['knowledge'] is True and health['embedding'] is True and health['diagnostic'] is None
                assert search.status_code == 200 and search.json()['evidence']
                chat = client.post('/api/v1/chat', json={'question': '京剧中的生旦净丑是什么？'})
                assert chat.status_code == 503 and chat.json()['error']['code'] == 'LLM_KEY_MISSING'
                return {'healthKnowledge': True, 'healthOverall': health['status'], 'searchStatus': search.status_code, 'evidenceCount': len(search.json()['evidence']), 'missingKeyChat': response(chat), 'historyTotal': history['total'], 'eightPageStatuses': pages}
            assert health['knowledge'] is False and health['diagnostic'] == expected_code
            assert search.status_code == 503 and search.json()['error']['code'] == expected_code
            assert not search.json().get('evidence')
            return {'healthKnowledge': False, 'diagnostic': health['diagnostic'], 'search': response(search), 'historyTotal': history['total'], 'eightPageStatuses': pages, 'diagnosticScope': 'explicit missing resource category; no internal path or raw exception'}

    case('normal_local_cpu_search_and_missing_key_no_generation', lambda: check_app(clone('normal')))

    bge_root = clone('bge-missing')
    case('missing_bge_degrades_only_knowledge', lambda: check_app(bge_root, root / 'does-not-exist-model', False))
    case('bge_restored_by_reconfiguring_existing_local_snapshot', lambda: check_app(bge_root))

    qroot = clone('qdrant-missing')
    gen = json.loads((qroot / 'active.json').read_text(encoding='utf-8'))['generation_id']
    qpath = qroot / 'generations' / gen / 'qdrant'
    saved_q = qpath.with_name('qdrant-original-test-copy')
    qpath.rename(saved_q)
    def missing_qdrant():
        result = check_app(qroot, expect_ready=False)
        result['missingPathWasAutoCreated'] = qpath.is_dir()
        result['emptyCollectionCreatedBeforeMismatch'] = (qpath / 'meta.json').is_file()
        assert not qpath.exists()
        return result
    case('missing_qdrant_cannot_fake_evidence', missing_qdrant)
    def restore_qdrant():
        if qpath.exists():
            qpath.rename(qpath.with_name('qdrant-new-empty-failure-artifact'))
        saved_q.rename(qpath)
        return check_app(qroot)
    case('restore_qdrant_exact_isolated_copy', restore_qdrant)

    def qdrant_missing_collection():
        target = clone('qdrant-missing-collection')
        metadata = target / 'generations' / gen / 'qdrant/meta.json'
        original = metadata.read_bytes()
        metadata.write_text(json.dumps({'collections': {}, 'aliases': {}}), encoding='utf-8')
        held_metadata = metadata.read_bytes()
        missing = check_app(target, expect_ready=False)
        assert metadata.read_bytes() == held_metadata
        metadata.write_bytes(original)
        recovered = check_app(target)
        return {'missing': missing, 'metadataNotRewrittenDuringServing': True, 'restored': recovered}
    case('missing_qdrant_collection_declaration_no_autocreation_then_restore', qdrant_missing_collection)

    def qdrant_missing_storage():
        target = clone('qdrant-missing-storage')
        storage = target / 'generations' / gen / 'qdrant/collection/opera_chunks/storage.sqlite'
        backup = storage.with_suffix('.held-by-isolated-test')
        storage.rename(backup)
        missing = check_app(target, expect_ready=False)
        assert not storage.exists()
        backup.rename(storage)
        recovered = check_app(target)
        return {'missing': missing, 'storageNotRecreatedDuringServing': True, 'restored': recovered}
    case('missing_qdrant_collection_storage_no_autocreation_then_restore', qdrant_missing_storage)

    kroot = clone('knowledge-sqlite-missing')
    kpath = kroot / 'generations' / gen / 'knowledge.sqlite3'
    saved_k = kpath.with_name('knowledge-original-test-copy.sqlite3')
    kpath.rename(saved_k)
    def missing_knowledge():
        result = check_app(kroot, expect_ready=False)
        result['missingSqliteWasAutoCreated'] = kpath.is_file()
        result['autoCreatedBytes'] = kpath.stat().st_size if kpath.is_file() else None
        assert not kpath.exists()
        return result
    case('missing_knowledge_sqlite_rejected_without_creating_empty_file', missing_knowledge)
    def restore_knowledge():
        if kpath.exists():
            kpath.rename(kpath.with_name('knowledge-new-empty-failure-artifact.sqlite3'))
        saved_k.rename(kpath)
        return check_app(kroot)
    case('restore_knowledge_sqlite_exact_isolated_copy', restore_knowledge)

    def corrupt_task_db():
        target = clone('corrupt-agent-sqlite')
        path = target / 'agent-tasks.sqlite3'
        path.write_bytes(b'WP4 intentionally invalid SQLite fixture; no secrets.')
        try:
            main.create_app(settings(target))
        except sqlite3.DatabaseError as exc:
            return {'observedBehavior': 'app factory raises before HTTP listener can start', 'exceptionType': type(exc).__name__, 'limitation': 'corrupt writable Agent database blocks whole startup rather than degraded API', 'fixtureOnly': True}
        raise AssertionError('Expected corrupt agent store to block factory')
    case('corrupt_agent_sqlite_startup_gap_recorded', corrupt_task_db)

    def history_missing():
        path = root / 'history-read-only-missing' / 'tasks.sqlite3'
        reader = HistoryReader(path)
        assert reader.list()['total'] == 0 and not path.exists() and not path.parent.exists()
        try:
            reader.detail(task_id)
        except ServiceError as exc:
            assert exc.status == 404
            return {'listTotal': 0, 'detailStatus': exc.status, 'detailCode': exc.code, 'missingFileCreated': False}
        raise AssertionError('Missing history detail must be unavailable')
    case('read_only_history_missing_never_creates_database', history_missing)

    def corrupt_history():
        target = root / 'corrupt-history.sqlite3'
        target.write_bytes(b'WP4 deliberate invalid readonly history fixture.')
        try:
            HistoryReader(target).list()
        except ServiceError as exc:
            assert exc.status == 503 and exc.code == 'AGENT_HISTORY_UNAVAILABLE'
            return {'code': exc.code, 'status': exc.status, 'message': exc.message, 'sensitivePathLeaked': str(root) in exc.message}
        raise AssertionError('Corrupt history must have safe error')
    case('readonly_corrupt_sqlite_returns_safe_503', corrupt_history)

    def empty_startup():
        target = root / 'blank-runtime'
        app = main.create_app(settings(target, root / 'missing-bge'))
        with TestClient(app) as client:
            health = client.get('/api/v1/health').json()
            listing = client.get('/api/v1/agent/history').json()
            assert health['diagnostic'] == 'KNOWLEDGE_NOT_INITIALIZED' and health['knowledge'] is False
            assert listing['total'] == 0
        return {'diagnostic': health['diagnostic'], 'historyTotal': 0, 'writableAgentDbCreated': (target / 'agent-tasks.sqlite3').is_file(), 'catalogCreated': (target / 'assets/catalog.sqlite3').is_file(), 'limitation': 'new wrong-but-writable RAG_DATA_DIR initializes empty operational stores; empty is not restored history'}
    case('blank_runtime_truthful_empty_not_recovery', empty_startup)

    def glb_missing_restore():
        target = clone('glb-missing-recovery')
        app = main.create_app(settings(target))
        raw = (REPO / 'backend/tests/fixtures/phase4/Duck.glb').read_bytes()
        validation = validate_glb(raw)
        model = app.state.asset_service.register_fixture(raw, 'Khronos Duck Sony SCEA Shared Source License 1.0; WP4 isolated test fixture only, not Neural4D opera output.')
        path = app.state.asset_service.file_path('model', model['modelId'])
        saved = path.with_suffix('.held-by-isolated-test')
        before = hashlib.sha256(raw).hexdigest()
        with TestClient(app) as client:
            ok = client.get(model['fileUrl'])
            assert ok.status_code == 200 and hashlib.sha256(ok.content).hexdigest() == before
            path.rename(saved)
            bad = client.get(model['fileUrl'])
            assert bad.status_code == 404 and bad.json()['error']['code'] == 'ASSET_FILE_UNAVAILABLE'
            assert client.get('/about.html').status_code == 200
            assert client.get('/api/v1/agent/history').json()['total'] == 1
            saved.rename(path)
            restored = client.get(model['fileUrl'])
            assert restored.status_code == 200 and hashlib.sha256(restored.content).hexdigest() == before
        return {'fixture': 'licensed actual Duck GLB; not either private opera model', 'hash': before, 'bytes': len(raw), 'embeddedImages': validation['imageCount'], 'embeddedTexturePixels': validation['decodedTexturePixels'], 'missingFile': response(bad), 'restoredStatus': restored.status_code, 'hashUnchanged': True, 'viewerBrowserNotClaimed': True}
    case('actual_glb_isolated_removal_http_error_exact_restoration', glb_missing_restore)

    def finish():
        result = {'kind': 'WP4_ISOLATED_RESOURCE_MISSING_AND_RECOVERY', 'scope': 'real local CPU BGE + versioned public corpus + real temporary SQLite/Qdrant + actual licensed Duck; synthetic saved task; NOT live provider/browser proof', 'results': rows, 'passed': sum(x['status'] == 'PASS' for x in rows), 'failed': sum(x['status'] == 'FAIL' for x in rows), 'skipped': 0, 'paidApiCalls': 0, 'neural4dApiCalls': 0, 'auditCounts': counts, 'productionAccess': 'BGE snapshot read-only only; other production runtime and private config guarded', 'knownGaps': ['corrupt Agent SQLite prevents app startup', 'wrong writable data path initializes truthful but empty operation stores'], 'fixedInThisRun': ['missing BGE/SQLite/Qdrant have distinct safe diagnostics', 'missing SQLite/Qdrant prechecked before constructor and never auto-created by serving']}
        (root / 'resource-probe-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'passed': result['passed'], 'failed': result['failed'], 'auditCounts': counts}, ensure_ascii=False))
        return 1 if result['failed'] else 0
    return finish()


if __name__ == '__main__':
    raise SystemExit(run())
