"""Offline generation builder. Stop the application before modifying the index."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import uuid
from urllib.parse import urlparse
import portalocker
from backend.app.config import Settings
from backend.app.knowledge.embedding import EmbeddingService
from backend.app.knowledge.chunking import Chunker
from backend.app.knowledge.store import KnowledgeStore
from backend.app.knowledge.vector_store import VectorStore

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

@contextmanager
def index_lock(data_dir: Path):
    data_dir.mkdir(parents=True, exist_ok=True)
    # Shared application/build lock is held throughout use, not just one write.
    with portalocker.Lock(str(data_dir / 'index-owner.lock'), timeout=0):
        yield

def load_documents(corpus: Path):
    documents, failures = [], []
    ids = set()
    for path in sorted((corpus / 'documents').glob('*.json')):
        try:
            doc = json.loads(path.read_text(encoding='utf-8'))
            source, sections = doc['source'], doc['sections']
            fields = ('source_id', 'title', 'category', 'author_or_organization', 'source_url', 'publication_date', 'collected_at', 'license_status', 'review_status', 'document_version', 'content_kind', 'scope', 'license_url', 'redistribution_allowed', 'external_llm_allowed')
            if any(key not in source for key in fields): raise ValueError('Missing required provenance fields')
            text_fields = [key for key in fields if key not in ('publication_date', 'redistribution_allowed', 'external_llm_allowed')]
            if any(not isinstance(source[key], str) or not source[key].strip() for key in text_fields): raise ValueError('Source metadata must contain nonempty text fields')
            if source['publication_date'] is not None and not isinstance(source['publication_date'], str): raise ValueError('Invalid publication date')
            if source['source_id'] in ids: raise ValueError('Duplicate source_id')
            if source['review_status'] != 'source_checked_by_assistant' or source['content_kind'] != 'original_fact_summary': raise ValueError('Unreviewed/unsupported content kind')
            if source['redistribution_allowed'] is not True or source['external_llm_allowed'] is not True: raise ValueError('Use permission not established')
            if not source['source_url'].startswith('https://'): raise ValueError('Source must be traceable HTTPS')
            parsed_url = urlparse(source['source_url'])
            if not parsed_url.hostname or parsed_url.username or parsed_url.password: raise ValueError('Source URL must have a host and no credentials')
            if not isinstance(sections, list) or not sections: raise ValueError('Empty sections')
            ids.add(source['source_id'])
            source['content_hash'] = digest(sections)
            documents.append({'source': source, 'sections': sections})
        except (ValueError, KeyError, TypeError) as exc:
            failures.append({'file': path.name, 'reason': str(exc)})
    if failures: raise ValueError(json.dumps(failures, ensure_ascii=False))
    if not documents: raise ValueError('No usable documents')
    return documents

def build(corpus: Path, settings: Settings, rebuild=False):
    started = time.perf_counter()
    documents = load_documents(corpus)
    model_manifest = json.loads((settings.embedding_model_path / 'model-manifest.json').read_text(encoding='utf-8'))
    params = {'target_chars': 350, 'overlap_chars': 70, 'max_tokens': 480, 'vector_text': 'content'}
    corpus_hash = digest({'documents': documents, 'model_revision': model_manifest['revision'], 'chunking': params})
    data_dir = settings.rag_data_dir
    active = data_dir / 'active.json'
    with index_lock(data_dir):
        old = json.loads(active.read_text(encoding='utf-8')) if active.exists() else None
        if old and old['corpus_hash'] == corpus_hash and not rebuild:
            return {'status': 'unchanged', 'added': 0, 'updated': 0, 'skipped': len(documents), 'failed': 0, 'generation_id': old['generation_id'], 'documents': old['documents'], 'chunks': old['chunks'], 'elapsed_seconds': round(time.perf_counter()-started, 4)}
        generation = 'gen-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
        target = data_dir / 'generations' / generation
        target.mkdir(parents=True)
        embedding = EmbeddingService(settings.embedding_model_path)
        chunker = Chunker(embedding)
        store = KnowledgeStore(target / 'knowledge.sqlite3', create=True)
        vectors = VectorStore(target / 'qdrant')
        total, duplicates = 0, 0
        hashes = set()
        try:
            for doc in documents:
                source = doc['source']
                chunks = chunker.split_sections(source['source_id'], source['document_version'], doc['sections'], source['category'])
                kept = []
                for chunk in chunks:
                    if chunk['content_hash'] in hashes:
                        duplicates += 1
                        # Don't expand repeated evidence; original source remains in source metadata.
                        continue
                    hashes.add(chunk['content_hash']); kept.append(chunk)
                store.add(source, kept)
                encoded = embedding.encode_documents([c['content'] for c in kept])
                vectors.upsert(kept, encoded)
                total += len(kept)
            if total < 1 or vectors.count() != store.count(): raise ValueError('Vector/canonical evidence count mismatch')
            vectors.validate_links(store.all_chunks())
            for chunk in store.all_chunks():
                if store.chunk(chunk['chunk_id'])['source_id'] != chunk['source_id']: raise ValueError('Broken evidence association')
        finally:
            vectors.close(); store.close()
        manifest = {'generation_id': generation, 'corpus_hash': corpus_hash, 'documents': len(documents), 'chunks': total, 'duplicates_skipped': duplicates, 'model_id': settings.embedding_model, 'model_revision': model_manifest['revision'], 'dimension': 512, 'distance': 'Cosine', 'chunking': params, 'created_at': datetime.now(timezone.utc).isoformat(), 'review_scope': 'assistant source-checked original facts; human review pending'}
        (target / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        temporary = data_dir / ('active-' + uuid.uuid4().hex + '.tmp')
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        temporary.replace(active)
        return {'status': 'built', 'added': len(documents) if not old else 0, 'updated': len(documents) if old else 0, 'skipped': 0, 'failed': 0, **manifest, 'elapsed_seconds': round(time.perf_counter()-started, 4)}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--corpus', type=Path, default=Path('knowledge'))
    parser.add_argument('--rebuild', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try: result = build(args.corpus, Settings(), args.rebuild)
    except Exception as exc:
        result = {'status': 'failed', 'failed': 1, 'error_type': type(exc).__name__, 'message': '入库未完成；旧活动索引保持不变，请检查资料、模型及应用是否已停止。'}
        if isinstance(exc, ValueError): result['validation_reason'] = str(exc)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True))
    raise SystemExit(0 if result['status'] != 'failed' else 1)
