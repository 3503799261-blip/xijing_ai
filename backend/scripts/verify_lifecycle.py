"""Real CPU BGE / SQLite / Qdrant lifecycle checks in isolated runtime, no LLM."""
from pathlib import Path
import json
import shutil
import time
import uuid
from backend.app.config import Settings, WORKSPACE_ROOT
from backend.app.services.runtime import Runtime
from backend.scripts.ingest import build

def run():
    started = time.perf_counter()
    folder = WORKSPACE_ROOT / '.runtime' / ('lifecycle-' + uuid.uuid4().hex[:8])
    corpus = folder / 'knowledge'
    shutil.copytree(Path('knowledge'), corpus)
    settings = Settings(rag_data_dir=folder / 'data')
    records = []
    initial = build(corpus, settings)
    records.append({'step': 'isolated_initial', 'result': initial})
    repeat = build(corpus, settings)
    assert repeat['status'] == 'unchanged' and repeat['chunks'] == initial['chunks']
    records.append({'step': 'repeat', 'result': repeat})
    runtime = Runtime(settings)
    runtime.open()
    try:
        assert runtime.search_service
        query = runtime.search_service.search('京剧的主要行当有哪些？', 5)
        assert query['evidence']
        records.append({'step': 'reopen_and_search', 'passed': True, 'evidenceCount': len(query['evidence'])})
        try: build(corpus, settings, rebuild=True)
        except Exception as exc:
            records.append({'step': 'concurrent_writer_rejected', 'passed': True, 'exceptionType': type(exc).__name__})
        else: raise AssertionError('Concurrent writer was not blocked')
    finally:
        runtime.close_knowledge(); runtime.executor.shutdown(wait=True)
    path = corpus / 'documents' / 'ihchina-jingju.json'
    if not path.exists(): path = next((corpus / 'documents').glob('*.json'))
    doc = json.loads(path.read_text(encoding='utf-8'))
    doc['source']['document_version'] = 'lifecycle-test-2'
    # The same independently source-checked fact is prefixed by its section title;
    # this is a fixture-only content edit, never published as a new source.
    doc['sections'][0]['content'] = doc['sections'][0]['title'] + '：' + doc['sections'][0]['content']
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    updated = build(corpus, settings)
    assert updated['status'] == 'built' and updated['generation_id'] != initial['generation_id']
    assert updated['chunks'] == initial['chunks']
    records.append({'step': 'content_update', 'result': updated})
    rebuilt = build(corpus, settings, rebuild=True)
    assert rebuilt['generation_id'] != updated['generation_id'] and rebuilt['chunks'] == updated['chunks']
    records.append({'step': 'explicit_rebuild', 'result': rebuilt})
    active_before = (settings.rag_data_dir / 'active.json').read_bytes()
    doc['source']['external_llm_allowed'] = False
    path.write_text(json.dumps(doc, ensure_ascii=False)+'\n', encoding='utf-8')
    try: build(corpus, settings)
    except ValueError:
        assert (settings.rag_data_dir / 'active.json').read_bytes() == active_before
        records.append({'step': 'invalid_update_keeps_previous_active', 'passed': True})
    else: raise AssertionError('Invalid content accepted')
    return {'success': True, 'realEmbedding': 'BAAI/bge-small-zh-v1.5', 'dimension': 512, 'scope': 'isolated copy, actual CPU vectors, persistent SQLite/Qdrant; original corpus unchanged; no LLM requests', 'elapsedSeconds': round(time.perf_counter()-started, 4), 'checks': records}

if __name__ == '__main__':
    result = run()
    Path('docs/evidence/test-results/phase-02-real-lifecycle.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True))
