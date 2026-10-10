"""Persistent application budget, conservative CNY estimates, never a billing cap."""
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from ..errors import ServiceError

PRICE_SOURCE = 'https://api-docs.deepseek.com/zh-cn/quick_start/pricing/'
PRICE_VERIFIED = '2026-10-10'
INPUT_MISS = 2.0
INPUT_HIT = 0.04
OUTPUT = 8.0

class BudgetLedger:
    def __init__(self, path: Path, limit: float):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path, self.limit = path, limit
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS calls (request_id TEXT PRIMARY KEY, created_at TEXT, status TEXT, reserved REAL, cost REAL, usage_json TEXT)')

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def summary(self) -> dict:
        with self.connect() as db:
            row = db.execute('SELECT count(*),coalesce(sum(coalesce(cost,reserved)),0) FROM calls').fetchone()
        return {'calls': row[0], 'estimatedUpperCostCny': round(row[1], 8), 'budgetCny': self.limit, 'priceVerifiedAt': PRICE_VERIFIED, 'priceSource': PRICE_SOURCE, 'estimateBasis': 'conservative peak tariff; unknown outcomes retain reservation; not provider billing cap'}

    def reserve(self, request_id: str, messages: list, max_output: int):
        import json
        # A byte-based upper estimate includes message formatting overhead.
        token_upper = len(json.dumps(messages, ensure_ascii=False).encode('utf-8')) + 256
        reserved = (token_upper * INPUT_MISS + max_output * OUTPUT) / 1_000_000
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            total = db.execute('SELECT coalesce(sum(coalesce(cost,reserved)),0) FROM calls').fetchone()[0]
            if total + reserved > self.limit:
                raise ServiceError('TEST_BUDGET_EXCEEDED', '本阶段应用测试预算将超出3元，已暂停模型调用；需用户批准追加预算。', 429)
            db.execute('INSERT INTO calls VALUES (?,?,?,?,?,?)', (request_id, datetime.now(timezone.utc).isoformat(), 'reserved', reserved, None, None))

    def finish(self, request_id: str, usage: dict | None, status: str):
        import json
        cost = None
        safe_usage = None
        if isinstance(usage, dict) and usage:
            values = {k: usage[k] for k in ('prompt_tokens', 'completion_tokens', 'total_tokens', 'prompt_cache_hit_tokens', 'prompt_cache_miss_tokens') if isinstance(usage.get(k), int) and usage[k] >= 0}
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
            rows = db.execute('SELECT request_id,created_at,status,reserved,cost,usage_json FROM calls ORDER BY created_at').fetchall()
        return [dict(requestId=r[0],createdAt=r[1],status=r[2],reservedUpperCny=r[3],estimatedUpperCny=r[4],usage=json.loads(r[5]) if r[5] else None) for r in rows]
