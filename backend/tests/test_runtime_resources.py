"""OFFLINE missing-resource guards: temporary real SQLite/Qdrant, fake encoder.

These do not prove BGE inference or supplier availability. WP4 separately runs
the actual local BGE against an isolated copy of the versioned public corpus.
"""
import asyncio
import json
from pathlib import Path

import portalocker
import pytest

from backend.app.config import Settings
from backend.app.errors import ServiceError
from backend.app.knowledge.store import KnowledgeStore
from backend.app.knowledge.vector_store import VectorStore
from backend.app.services.runtime import Runtime


REVISION = 'offline-synthetic-encoder-revision'
GENERATION = 'gen-offline-resource-fixture'
VECTOR = [1.0] + [0.0] * 511


class SyntheticEncoder:
    model_revision = REVISION

    def __init__(self, path):
        assert Path(path).is_dir()

    def encode_query(self, question):
        return VECTOR


def prepared(tmp_path, monkeypatch):
    import backend.app.knowledge.embedding as embedding
    monkeypatch.setattr(embedding, 'EmbeddingService', SyntheticEncoder)
    root = tmp_path / 'runtime'
    model = tmp_path / 'explicit-fake-encoder-directory'
    model.mkdir()
    target = root / 'generations' / GENERATION
    target.mkdir(parents=True)
    manifest = {'generation_id': GENERATION, 'model_revision': REVISION, 'documents': 1, 'chunks': 1}
    (root / 'active.json').write_text(json.dumps(manifest), encoding='utf-8')
    source = {'source_id': 'offline-source', 'title': '离线合成测试资料，非文化事实', 'category': 'offline', 'source_url': 'https://example.invalid/offline-fixture', 'document_version': '1', 'content_hash': 'offline-hash', 'content_kind': 'test_fixture', 'review_status': 'test_fixture'}
    chunk = {'chunk_id': 'offline-chunk', 'source_id': source['source_id'], 'section_id': 'offline-section', 'document_version': '1', 'content_hash': 'offline-chunk-hash', 'content': '仅用于离线资源恢复测试，不是真实AI回答。', 'locator': '离线夹具', 'entity_names': [], 'category': 'offline'}
    store = KnowledgeStore(target / 'knowledge.sqlite3', create=True)
    store.add(source, [chunk])
    store.close()
    vectors = VectorStore(target / 'qdrant')
    vectors.upsert([chunk], [VECTOR])
    vectors.close()
    settings = Settings(_env_file=None, rag_data_dir=root, embedding_model_path=model, deepseek_api_key='', neural4d_api_key='', neural4d_admin_token='', neural4d_generation_enabled=False, neural4d_protocol_verified=False)
    return settings, target


def dispose(runtime):
    runtime.close_knowledge()
    runtime.executor.shutdown(wait=True)


@pytest.mark.parametrize('kind,code', [
    ('model', 'EMBEDDING_MODEL_MISSING'),
    ('knowledge', 'KNOWLEDGE_DATABASE_MISSING'),
    ('vector_directory', 'VECTOR_INDEX_MISSING'),
    ('vector_metadata', 'VECTOR_INDEX_MISSING'),
    ('vector_storage', 'VECTOR_INDEX_MISSING'),
])
def test_missing_resources_rejected_before_any_knowledge_constructor(tmp_path, monkeypatch, kind, code):
    settings, target = prepared(tmp_path, monkeypatch)
    resource = {'model': settings.embedding_model_path, 'knowledge': target / 'knowledge.sqlite3', 'vector_directory': target / 'qdrant', 'vector_metadata': target / 'qdrant/meta.json', 'vector_storage': target / 'qdrant/collection/opera_chunks/storage.sqlite'}[kind]
    resource.rename(resource.with_name(resource.name + '.held-by-test'))
    attempted = []
    def must_not_construct(*args, **kwargs):
        attempted.append(True)
        raise AssertionError('Missing resource reached a constructor that can create files')
    import backend.app.knowledge.embedding as embedding
    import backend.app.knowledge.store as knowledge
    import backend.app.knowledge.vector_store as vectors
    monkeypatch.setattr(embedding, 'EmbeddingService', must_not_construct)
    monkeypatch.setattr(knowledge, 'KnowledgeStore', must_not_construct)
    monkeypatch.setattr(vectors, 'VectorStore', must_not_construct)
    runtime = Runtime(settings)
    try:
        runtime.open()
        assert runtime.diagnostic == code
        assert runtime.search_service is None
        assert attempted == []
        assert not resource.exists()
        with pytest.raises(ServiceError) as failure:
            asyncio.run(runtime.knowledge(lambda: None))
        assert failure.value.code == code
        assert str(tmp_path) not in failure.value.message
        assert '缺少' in failure.value.message
        assert runtime.lock is None
    finally:
        dispose(runtime)


def test_missing_qdrant_collection_declaration_is_rejected_before_constructors(tmp_path, monkeypatch):
    settings, target = prepared(tmp_path, monkeypatch)
    metadata = target / 'qdrant/meta.json'
    metadata.write_text(json.dumps({'collections': {}, 'aliases': {}}), encoding='utf-8')
    original_metadata = metadata.read_bytes()
    attempted = []
    def must_not_construct(*args, **kwargs):
        attempted.append(True)
        raise AssertionError('Undeclared collection must never reach creating constructor')
    import backend.app.knowledge.embedding as embedding
    monkeypatch.setattr(embedding, 'EmbeddingService', must_not_construct)
    runtime = Runtime(settings)
    try:
        runtime.open()
        assert runtime.diagnostic == 'VECTOR_INDEX_MISSING'
        assert attempted == [] and metadata.read_bytes() == original_metadata
    finally:
        dispose(runtime)


@pytest.mark.parametrize('module,name,code', [
    ('embedding', 'EmbeddingService', 'EMBEDDING_LOAD_FAILED'),
    ('store', 'KnowledgeStore', 'KNOWLEDGE_DATABASE_UNAVAILABLE'),
    ('vector_store', 'VectorStore', 'VECTOR_INDEX_UNAVAILABLE'),
])
def test_existing_resource_load_failure_has_safe_stage_diagnostic(tmp_path, monkeypatch, module, name, code):
    settings, target = prepared(tmp_path, monkeypatch)
    import importlib
    def broken(*args, **kwargs):
        raise ValueError('untrusted internal error including ' + str(tmp_path))
    monkeypatch.setattr(importlib.import_module('backend.app.knowledge.' + module), name, broken)
    runtime = Runtime(settings)
    try:
        runtime.open()
        assert runtime.diagnostic == code
        with pytest.raises(ServiceError) as failure:
            asyncio.run(runtime.knowledge(lambda: None))
        assert failure.value.code == code
        assert str(tmp_path) not in failure.value.message
        assert 'untrusted' not in failure.value.message
        assert runtime.lock is None and runtime.vectors is None and runtime.store is None
    finally:
        dispose(runtime)


@pytest.mark.parametrize('kind', ['model', 'knowledge', 'vector'])
def test_explicit_local_restoration_recovers_real_temp_store_and_vector_search(tmp_path, monkeypatch, kind):
    settings, target = prepared(tmp_path, monkeypatch)
    resource = {'model': settings.embedding_model_path, 'knowledge': target / 'knowledge.sqlite3', 'vector': target / 'qdrant'}[kind]
    backup = resource.with_name(resource.name + '.held-by-test')
    resource.rename(backup)
    runtime = Runtime(settings)
    try:
        runtime.open()
        assert runtime.search_service is None and not resource.exists()
        backup.rename(resource)
        runtime.open()
        assert runtime.diagnostic is None
        result = runtime.search_service.search('离线恢复测试', mode='vector')
        assert result['evidence'][0]['sourceId'] == 'offline-source'
        assert result['evidence'][0]['vectorScore'] == pytest.approx(1.0)
    finally:
        dispose(runtime)


def test_existing_index_lock_preserves_locked_diagnostic(tmp_path, monkeypatch):
    settings, _ = prepared(tmp_path, monkeypatch)
    runtime = Runtime(settings)
    with portalocker.Lock(str(settings.rag_data_dir / 'index-owner.lock'), timeout=0):
        try:
            runtime.open()
            assert runtime.diagnostic == 'KNOWLEDGE_LOCKED'
            assert runtime.search_service is None
        finally:
            dispose(runtime)


def test_vector_link_integrity_failure_retains_generic_index_validation_failure(tmp_path, monkeypatch):
    settings, target = prepared(tmp_path, monkeypatch)
    import backend.app.knowledge.vector_store as vectors
    def invalid(*args):
        raise ValueError('offline link mismatch')
    monkeypatch.setattr(vectors.VectorStore, 'validate_links', invalid)
    runtime = Runtime(settings)
    try:
        runtime.open()
        assert runtime.diagnostic == 'KNOWLEDGE_LOAD_FAILED'
        assert runtime.search_service is None
    finally:
        dispose(runtime)
