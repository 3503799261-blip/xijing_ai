"""SQLite is the canonical source of evidence, never generated model citations."""
import json
import re
import sqlite3
from pathlib import Path
from ..database import open_existing, validate_database, initialize_database

def lexical_tokens(text: str) -> str:
    tokens = re.findall(r'[a-z0-9]+', text.lower())
    for run in re.findall(r'[\u4e00-\u9fff]+', text):
        tokens.extend(run)
        tokens.extend(run[i:i+2] for i in range(len(run)-1))
    return ' '.join(dict.fromkeys(tokens))

KNOWLEDGE_TABLES = {
    'sources': ('source_id', 'data_json'),
    'documents': ('document_id', 'source_id', 'version', 'content_hash'),
    'chunks': ('chunk_id', 'source_id', 'section_id', 'content_hash', 'data_json'),
    'chunk_terms': ('chunk_id', 'tokens'),
}
KNOWLEDGE_SCHEMA = r"""
            CREATE TABLE sources (source_id TEXT PRIMARY KEY, data_json TEXT NOT NULL);
            CREATE TABLE documents (document_id TEXT PRIMARY KEY, source_id TEXT, version TEXT, content_hash TEXT);
            CREATE TABLE chunks (chunk_id TEXT PRIMARY KEY, source_id TEXT, section_id TEXT, content_hash TEXT, data_json TEXT NOT NULL);
            CREATE VIRTUAL TABLE chunk_terms USING fts5(chunk_id UNINDEXED, tokens);
            """
KNOWLEDGE_DATABASE_MESSAGE = '活动知识库SQLite缺失或不可读取，请恢复配套资料版本；未自动创建或修复。'

class KnowledgeStore:
    def __init__(self, path: Path, create=False):
        options = {'code': 'KNOWLEDGE_DATABASE_UNAVAILABLE', 'message': KNOWLEDGE_DATABASE_MESSAGE}
        if create:
            initialize_database(path, KNOWLEDGE_SCHEMA, KNOWLEDGE_TABLES, **options)
        else:
            validate_database(path, KNOWLEDGE_TABLES, **options)
        self.db = open_existing(path, **options)
        self.db.row_factory = sqlite3.Row

    def add(self, source: dict, chunks: list[dict]):
        sid = source['source_id']
        self.db.execute('INSERT INTO sources VALUES (?,?)', (sid, json.dumps(source, ensure_ascii=False)))
        self.db.execute('INSERT INTO documents VALUES (?,?,?,?)', ('doc-' + sid, sid, source['document_version'], source['content_hash']))
        for chunk in chunks:
            self.db.execute('INSERT INTO chunks VALUES (?,?,?,?,?)', (chunk['chunk_id'], sid, chunk['section_id'], chunk['content_hash'], json.dumps(chunk, ensure_ascii=False)))
            text = chunk['content'] + ' ' + ' '.join(chunk['entity_names'])
            self.db.execute('INSERT INTO chunk_terms VALUES (?,?)', (chunk['chunk_id'], lexical_tokens(text)))
        self.db.commit()

    def chunk(self, chunk_id: str) -> dict:
        row = self.db.execute('SELECT c.data_json,s.data_json AS source_json FROM chunks c JOIN sources s USING(source_id) WHERE chunk_id=?', (chunk_id,)).fetchone()
        if not row: raise ValueError('Evidence ID does not exist in canonical database')
        chunk, source = json.loads(row['data_json']), json.loads(row['source_json'])
        return {**chunk, 'source': source}

    def lexical_search(self, question: str, limit=10, entity_terms=None) -> list[dict]:
        terms = lexical_tokens(question).split() if entity_terms is None else list(dict.fromkeys(token for entity in entity_terms for token in ([entity] if len(entity) <= 2 else [entity[i:i+2] for i in range(len(entity)-1)])))
        if not terms: return []
        # Tokens are generated alphanumerics/Chinese, quoted and bound; no user MATCH syntax.
        expression = ' OR '.join('"' + term + '"' for term in terms[:100])
        rows = self.db.execute('SELECT chunk_id,bm25(chunk_terms) AS score FROM chunk_terms WHERE chunk_terms MATCH ? ORDER BY score LIMIT ?', (expression, limit)).fetchall()
        return [{'chunk_id': r['chunk_id'], 'keyword_score': float(r['score'])} for r in rows]

    def sources(self) -> list[dict]:
        return [json.loads(r[0]) for r in self.db.execute('SELECT data_json FROM sources ORDER BY source_id')]

    def all_chunks(self) -> list[dict]:
        return [json.loads(r[0]) for r in self.db.execute('SELECT data_json FROM chunks ORDER BY chunk_id')]

    def count(self):
        return self.db.execute('SELECT count(*) FROM chunks').fetchone()[0]

    def close(self): self.db.close()
