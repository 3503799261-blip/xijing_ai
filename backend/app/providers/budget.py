"""Persistent application budget, conservative CNY estimates, never a billing cap."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone
from ..errors import ServiceError
from ..database import open_existing, validate_database, initialize_database

PRICE_SOURCE = 'https://api-docs.deepseek.com/zh-cn/quick_start/pricing/'
PRICE_VERIFIED = '2026-10-11'
INPUT_MISS = 2.0
INPUT_HIT = 0.04
OUTPUT = 8.0

BUDGET_TABLES = {
    'calls': ('request_id', 'created_at', 'status', 'reserved', 'cost', 'usage_json'),
    'budget_scopes': ('name', 'budget_cny', 'created_at'),
    'call_scopes': ('request_id', 'scope'),
}
BUDGET_OBJECTS = (('index', 'call_scopes_scope'),)
BUDGET_SCHEMA = r"""CREATE TABLE calls (request_id TEXT PRIMARY KEY, created_at TEXT, status TEXT, reserved REAL, cost REAL, usage_json TEXT);
CREATE TABLE budget_scopes (name TEXT PRIMARY KEY, budget_cny REAL NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE call_scopes (request_id TEXT PRIMARY KEY REFERENCES calls(request_id), scope TEXT NOT NULL REFERENCES budget_scopes(name));
CREATE INDEX call_scopes_scope ON call_scopes(scope);
"""
BUDGET_DATABASE_MESSAGE = '模型预算数据库缺失、路径错误或不可读取，已停止付费调用；请检查配置并恢复原库。'


class BudgetLedger:
    def __init__(self, path: Path, limit: float, scope: str | None = None, scope_limit: float | None = None, *, create=False):
        if scope is not None and (not scope or scope_limit is None or scope_limit <= 0):
            raise ValueError('A named budget scope requires a positive limit.')
        self.path, self.limit, self.scope = Path(path).expanduser().resolve(), limit, scope
        options = {'objects': BUDGET_OBJECTS, 'code': 'BUDGET_DATABASE_UNAVAILABLE', 'message': BUDGET_DATABASE_MESSAGE}
        if create:
            initialize_database(self.path, BUDGET_SCHEMA, BUDGET_TABLES, **options)
        else:
            validate_database(self.path, BUDGET_TABLES, **options)
        if scope is not None:
            # Preserve the existing non-increasing scope policy on a validated
            # database. An unchanged normal start performs no write or DDL.
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT budget_cny FROM budget_scopes WHERE name=?', (scope,)).fetchone()
                if row is None:
                    db.execute('INSERT INTO budget_scopes VALUES (?,?,?)',
                               (scope, scope_limit, datetime.now(timezone.utc).isoformat()))
                elif scope_limit < row[0]:
                    db.execute('UPDATE budget_scopes SET budget_cny=? WHERE name=?', (scope_limit, scope))

    @contextmanager
    def connect(self):
        db = open_existing(self.path, timeout=5, code='BUDGET_DATABASE_UNAVAILABLE', message=BUDGET_DATABASE_MESSAGE)
        try:
            db.execute('PRAGMA foreign_keys=ON')
            with db:
                yield db
        except sqlite3.Error:
            raise ServiceError('BUDGET_DATABASE_UNAVAILABLE', BUDGET_DATABASE_MESSAGE, 503) from None
        finally:
            # sqlite3's own context commits/rolls back but does not close.
            db.close()

    def summary(self) -> dict:
        with self.connect() as db:
            # Keep total and per-scope counts from one consistent read snapshot.
            db.execute('BEGIN')
            row = db.execute('SELECT count(*),coalesce(sum(coalesce(cost,reserved)),0) FROM calls').fetchone()
            scopes = db.execute('SELECT s.name,s.budget_cny,count(c.request_id),coalesce(sum(coalesce(c.cost,c.reserved)),0) FROM budget_scopes s LEFT JOIN call_scopes a ON a.scope=s.name LEFT JOIN calls c ON c.request_id=a.request_id GROUP BY s.name,s.budget_cny').fetchall()
        by_scope = {s[0]: {'name': s[0], 'calls': s[2], 'estimatedUpperCostCny': round(s[3], 8), 'budgetCny': s[1]} for s in scopes}
        return {'calls': row[0], 'estimatedUpperCostCny': round(row[1], 8), 'budgetCny': self.limit, 'priceVerifiedAt': PRICE_VERIFIED, 'priceSource': PRICE_SOURCE, 'estimateBasis': 'conservative peak tariff; unknown outcomes retain reservation; not provider billing cap', 'activeScope': by_scope.get(self.scope), 'scopes': by_scope}

    def reserve(self, request_id: str, messages: list, max_output: int):
        import json
        # A byte-based upper estimate includes message formatting overhead.
        token_upper = len(json.dumps(messages, ensure_ascii=False).encode('utf-8')) + 256
        reserved = (token_upper * INPUT_MISS + max_output * OUTPUT) / 1_000_000
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            total = db.execute('SELECT coalesce(sum(coalesce(cost,reserved)),0) FROM calls').fetchone()[0]
            if total + reserved > self.limit:
                raise ServiceError('TEST_BUDGET_EXCEEDED', '应用累计测试预算将超出已配置上限，已暂停模型调用；需用户批准追加预算。', 429)
            if self.scope is not None:
                scope_limit = db.execute('SELECT budget_cny FROM budget_scopes WHERE name=?', (self.scope,)).fetchone()[0]
                scope_total = db.execute('SELECT coalesce(sum(coalesce(c.cost,c.reserved)),0) FROM calls c JOIN call_scopes s ON s.request_id=c.request_id WHERE s.scope=?', (self.scope,)).fetchone()[0]
                if scope_total + reserved > scope_limit:
                    raise ServiceError('PHASE_BUDGET_EXCEEDED', 'Phase 3应用增量测试预算将超出已批准范围，已暂停模型调用；需用户批准追加预算。', 429)
            db.execute('INSERT INTO calls VALUES (?,?,?,?,?,?)', (request_id, datetime.now(timezone.utc).isoformat(), 'reserved', reserved, None, None))
            if self.scope is not None:
                db.execute('INSERT INTO call_scopes VALUES (?,?)', (request_id, self.scope))

    def finish(self, request_id: str, usage: dict | None, status: str):
        import json
        cost = None
        safe_usage = None
        if isinstance(usage, dict) and usage:
            values = {k: usage[k] for k in ('prompt_tokens', 'completion_tokens', 'total_tokens', 'prompt_cache_hit_tokens', 'prompt_cache_miss_tokens') if type(usage.get(k)) is int and usage[k] >= 0}
            if 'prompt_tokens' in values and 'completion_tokens' in values:
                hit = min(values.get('prompt_cache_hit_tokens', 0), values['prompt_tokens'])
                miss = values['prompt_tokens'] - hit
                cost = (hit * INPUT_HIT + miss * INPUT_MISS + values['completion_tokens'] * OUTPUT) / 1_000_000
                safe_usage = json.dumps(values)
        # Known rejected HTTP requests incurred no generated tokens; transport/timeout are unknown.
        if status in ('http_400', 'http_401', 'http_402', 'http_404', 'http_429'):
            cost = 0.0
        with self.connect() as db:
            db.execute('UPDATE calls SET status=?,cost=?,usage_json=? WHERE request_id=?', (status, cost, safe_usage, request_id))

    def records(self):
        import json
        with self.connect() as db:
            rows = db.execute('SELECT c.request_id,c.created_at,c.status,c.reserved,c.cost,c.usage_json,a.scope FROM calls c LEFT JOIN call_scopes a ON a.request_id=c.request_id ORDER BY c.created_at').fetchall()
        return [dict(requestId=r[0],createdAt=r[1],status=r[2],reservedUpperCny=r[3],estimatedUpperCny=r[4],usage=json.loads(r[5]) if r[5] else None,scope=r[6]) for r in rows]
