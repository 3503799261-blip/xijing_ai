"""Local task persistence. Short transactions never span model or RAG calls."""
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from ..errors import ServiceError

AGENTS = ('planner', 'researcher', 'designer', 'reviewer')
TERMINAL = {'completed', 'failed', 'cancelled'}
AGENT_STATES = {'pending', 'running', 'completed', 'failed', 'awaiting_confirmation'}

def now():
    return datetime.now(timezone.utc).isoformat()

def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))

class TaskStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS agent_tasks (
              task_id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE NOT NULL,
              signature TEXT NOT NULL, brief_json TEXT NOT NULL, state TEXT NOT NULL,
              sequence INTEGER NOT NULL, current_agent TEXT, confirmation_json TEXT,
              result_json TEXT, cancel_requested INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS agent_steps (
              task_id TEXT NOT NULL, agent_id TEXT NOT NULL, state TEXT NOT NULL,
              summary TEXT NOT NULL, started_at TEXT, finished_at TEXT, error_code TEXT,
              PRIMARY KEY(task_id,agent_id));
            CREATE TABLE IF NOT EXISTS agent_artifacts (
              task_id TEXT NOT NULL, agent_id TEXT NOT NULL, version INTEGER NOT NULL,
              content_json TEXT NOT NULL, content_hash TEXT NOT NULL, created_at TEXT NOT NULL,
              PRIMARY KEY(task_id,agent_id,version));
            CREATE TABLE IF NOT EXISTS agent_events (
              task_id TEXT NOT NULL, sequence INTEGER NOT NULL, payload_json TEXT NOT NULL,
              PRIMARY KEY(task_id,sequence));
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def signature(brief):
        return hashlib.sha256(json.dumps(brief, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()

    def _row(self, db, task_id):
        row = db.execute('SELECT * FROM agent_tasks WHERE task_id=?', (task_id,)).fetchone()
        if row is None:
            raise ServiceError('AGENT_TASK_NOT_FOUND', '未找到这个创作任务，请检查任务标识。', 404)
        return row

    def _event(self, db, task_id, kind, state, summary, agent_id=None, **extras):
        row = self._row(db, task_id)
        sequence = row['sequence'] + 1
        stamp = now()
        payload = {'kind': kind, 'runId': task_id, 'sequence': sequence, 'occurredAt': stamp,
                   'summary': summary}
        if kind == 'agent':
            payload.update(agentId=agent_id, state=state)
        else:
            payload.update(taskState=state)
        payload.update({key: value for key, value in extras.items() if value is not None})
        db.execute('INSERT INTO agent_events VALUES (?,?,?)', (task_id, sequence, encode(payload)))
        db.execute('UPDATE agent_tasks SET sequence=?,updated_at=? WHERE task_id=?', (sequence, stamp, task_id))

    def existing(self, key, brief):
        with self.connect() as db:
            row = db.execute('SELECT task_id,signature FROM agent_tasks WHERE idempotency_key=?', (key,)).fetchone()
        if row is None:
            return None
        if row['signature'] != self.signature(brief):
            raise ServiceError('IDEMPOTENCY_CONFLICT', '同一提交标识不能用于不同创作需求。', 409)
        return row['task_id']

    def create(self, brief, key, queue_limit=2):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT task_id,signature FROM agent_tasks WHERE idempotency_key=?', (key,)).fetchone()
            if existing:
                if existing['signature'] != self.signature(brief):
                    raise ServiceError('IDEMPOTENCY_CONFLICT', '同一提交标识不能用于不同创作需求。', 409)
                return existing['task_id'], False
            if brief.get('parentTaskId'):
                self._row(db, brief['parentTaskId'])
            count = db.execute("SELECT count(*) FROM agent_tasks WHERE state IN ('waiting','running')").fetchone()[0]
            if count >= queue_limit + 1:
                raise ServiceError('AGENT_QUEUE_FULL', '创作任务队列已满，请等待当前任务或稍后手动提交。', 429, True)
            task_id, stamp = str(uuid.uuid4()), now()
            db.execute('INSERT INTO agent_tasks VALUES (?,?,?,?,?,?,NULL,NULL,NULL,0,?,?)',
                       (task_id, key, self.signature(brief), encode(brief), 'waiting', 0, stamp, stamp))
            for agent_id in AGENTS:
                db.execute('INSERT INTO agent_steps VALUES (?,?,?, ?,NULL,NULL,NULL)',
                           (task_id, agent_id, 'pending', '尚未执行。'))
            self._event(db, task_id, 'task', 'waiting', '任务已保存，等待真实工作流调度。')
            return task_id, True

    def brief(self, task_id):
        with self.connect() as db:
            return json.loads(self._row(db, task_id)['brief_json'])

    def next_waiting(self):
        with self.connect() as db:
            row = db.execute("SELECT task_id FROM agent_tasks WHERE state='waiting' ORDER BY created_at LIMIT 1").fetchone()
            return row['task_id'] if row else None

    def start(self, task_id):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, task_id)
            if row['state'] != 'waiting':
                return False
            db.execute("UPDATE agent_tasks SET state='running' WHERE task_id=?", (task_id,))
            self._event(db, task_id, 'task', 'running', '工作流已实际开始。')
            return True

    def cancelled(self, task_id):
        """Workflow stop guard: no terminal, held, or unknown state can run."""
        with self.connect() as db:
            row = self._row(db, task_id)
            return bool(row['cancel_requested'] or row['state'] != 'running')

    def emit(self, task_id, agent_id, state, summary='', artifact=None, error_code=None):
        if agent_id not in AGENTS or state not in AGENT_STATES:
            raise ValueError('Invalid internal agent transition')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, task_id)
            if row['state'] in TERMINAL:
                raise ServiceError('WORKFLOW_CANCELLED', '任务已经停止，未继续执行后续阶段。', 409)
            step = db.execute('SELECT * FROM agent_steps WHERE task_id=? AND agent_id=?', (task_id, agent_id)).fetchone()
            allowed = {'pending': {'running', 'failed'}, 'running': {'completed', 'failed', 'awaiting_confirmation'},
                       'awaiting_confirmation': set(), 'completed': set(), 'failed': set()}
            if state not in allowed[step['state']]:
                raise ValueError('Invalid internal agent transition')
            stamp = now()
            started = stamp if state == 'running' else step['started_at']
            finished = stamp if state in {'completed', 'failed', 'awaiting_confirmation'} else step['finished_at']
            db.execute('UPDATE agent_steps SET state=?,summary=?,started_at=?,finished_at=?,error_code=? WHERE task_id=? AND agent_id=?',
                       (state, summary[:1000], started, finished, error_code, task_id, agent_id))
            db.execute('UPDATE agent_tasks SET current_agent=? WHERE task_id=?', (agent_id, task_id))
            if artifact is not None:
                content = encode(artifact)
                db.execute('INSERT INTO agent_artifacts VALUES (?,?,1,?,?,?)',
                           (task_id, agent_id, content, hashlib.sha256(content.encode('utf-8')).hexdigest(), stamp))
            self._event(db, task_id, 'agent', state, summary[:1000], agent_id, errorCode=error_code)

    def finish(self, task_id, result):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, task_id)
            if row['state'] in TERMINAL:
                return
            if row['cancel_requested']:
                self._terminate(db, task_id, 'cancelled', '用户取消，后续阶段未执行。')
                return
            can_accept = bool(result.get('design') and result.get('review', {}).get('verdict') == 'pass' and not result.get('uncertain', True))
            completed = db.execute("SELECT count(*) FROM agent_steps WHERE task_id=? AND state='completed'", (task_id,)).fetchone()[0]
            can_accept = can_accept and completed == 4
            confirmation = {'id': str(uuid.uuid4()), 'reason': result.get('confirmationReason', 'insufficient_evidence'), 'canAccept': can_accept}
            result = {**result, 'taskId': task_id, 'schemaVersion': '1.0', 'publicationAllowed': False, 'userConfirmed': False}
            db.execute("UPDATE agent_tasks SET state='awaiting_confirmation',confirmation_json=?,result_json=? WHERE task_id=?",
                       (encode(confirmation), encode(result), task_id))
            self._event(db, task_id, 'task', 'awaiting_confirmation',
                        '设计与辅助审校已返回，等待你确认。' if can_accept else '任务已暂停，请查看需调整的需求或文化依据。',
                        confirmationId=confirmation['id'])

    def _terminate(self, db, task_id, state, summary, error_code=None):
        db.execute('UPDATE agent_tasks SET state=? WHERE task_id=?', (state, task_id))
        self._event(db, task_id, 'task', state, summary, errorCode=error_code)

    def fail(self, task_id, error):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, task_id)
            if row['state'] in TERMINAL:
                return
            running = db.execute("SELECT agent_id FROM agent_steps WHERE task_id=? AND state='running'", (task_id,)).fetchall()
            for step in running:
                db.execute("UPDATE agent_steps SET state='failed',summary=?,finished_at=?,error_code=? WHERE task_id=? AND agent_id=?",
                           (error.message[:1000], now(), error.code, task_id, step['agent_id']))
                self._event(db, task_id, 'agent', 'failed', error.message[:1000], step['agent_id'], errorCode=error.code)
            self._terminate(db, task_id, 'failed', error.message[:1000], error.code)

    def complete_cancel(self, task_id):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, task_id)
            if row['state'] not in TERMINAL:
                self._terminate(db, task_id, 'cancelled', '取消已生效，未自动重发模型请求。')

    def recover(self):
        with self.connect() as db:
            ids = [r['task_id'] for r in db.execute("SELECT task_id FROM agent_tasks WHERE state IN ('waiting','running')")]
        for task_id in ids:
            self.fail(task_id, ServiceError('WORKFLOW_INTERRUPTED', '服务重启导致任务中断，已保存完成阶段；未自动发起新的付费调用。', 503, True))
        return len(ids)

    def status(self, task_id, after_sequence=0):
        with self.connect() as db:
            row = self._row(db, task_id)
            steps = {s['agent_id']: s for s in db.execute('SELECT * FROM agent_steps WHERE task_id=?', (task_id,))}
            events = [json.loads(e[0]) for e in db.execute('SELECT payload_json FROM agent_events WHERE task_id=? AND sequence>? ORDER BY sequence LIMIT 50', (task_id, after_sequence))]
            agents = [{'id': aid, 'state': steps[aid]['state'], 'summary': steps[aid]['summary'],
                       'startedAt': steps[aid]['started_at'], 'finishedAt': steps[aid]['finished_at'], 'errorCode': steps[aid]['error_code']} for aid in AGENTS]
            result = json.loads(row['result_json']) if row['result_json'] else None
            return {'taskId': task_id, 'runId': task_id, 'state': row['state'], 'currentAgent': row['current_agent'],
                    'agents': agents, 'completedSteps': sum(a['state'] == 'completed' for a in agents), 'totalSteps': 4,
                    'events': events, 'lastSequence': row['sequence'], 'sequence': row['sequence'],
                    'confirmation': json.loads(row['confirmation_json']) if row['confirmation_json'] and row['state'] == 'awaiting_confirmation' else None,
                    'resultReady': bool(result and result.get('design') and result.get('review')),
                    'cancelRequested': bool(row['cancel_requested']), 'createdAt': row['created_at'], 'updatedAt': row['updated_at']}

    def result(self, task_id):
        with self.connect() as db:
            row = self._row(db, task_id)
            result = json.loads(row['result_json']) if row['result_json'] else None
            if not result or not result.get('design') or not result.get('review'):
                raise ServiceError('AGENT_RESULT_NOT_READY', '尚无可展示的角色设计，请查看任务状态及资料限制。', 409)
            if row['state'] != 'completed':
                result.update(publicationAllowed=False, userConfirmed=False)
            return result

    def confirm(self, task_id, confirmation_id, expected_sequence):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, task_id)
            confirmation = json.loads(row['confirmation_json']) if row['confirmation_json'] else None
            if row['state'] == 'completed' and confirmation and confirmation['id'] == confirmation_id:
                return
            if row['sequence'] != expected_sequence:
                raise ServiceError('AGENT_STALE_STATE', '任务状态已更新，请重新查询后再确认。', 409, True)
            if row['state'] != 'awaiting_confirmation' or not confirmation or confirmation['id'] != confirmation_id or not confirmation['canAccept']:
                raise ServiceError('AGENT_CONFIRMATION_INVALID', '这个任务不能直接接受，请先解决需求或文化依据问题。', 409)
            result = json.loads(row['result_json'])
            if result.get('review', {}).get('verdict') != 'pass' or result.get('uncertain', True):
                raise ServiceError('AGENT_CONFIRMATION_INVALID', '文化审校尚未通过，不能确认发布。', 409)
            result.update(publicationAllowed=True, userConfirmed=True)
            db.execute('UPDATE agent_tasks SET result_json=? WHERE task_id=?', (encode(result), task_id))
            self._terminate(db, task_id, 'completed', '用户已明确接受最终设计；图像与3D生成仍未接入。')

    def cancel(self, task_id, expected_sequence):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, task_id)
            if row['state'] == 'cancelled':
                return
            if row['sequence'] != expected_sequence:
                raise ServiceError('AGENT_STALE_STATE', '任务状态已更新，请重新查询后再取消。', 409, True)
            if row['state'] in TERMINAL:
                raise ServiceError('AGENT_TASK_TERMINAL', '任务已经结束，不能改写执行历史。', 409)
            db.execute('UPDATE agent_tasks SET cancel_requested=1 WHERE task_id=?', (task_id,))
            if row['state'] == 'running':
                self._event(db, task_id, 'task', 'running', '已请求取消，将在当前阶段收尾后停止后续调用。')
            else:
                self._terminate(db, task_id, 'cancelled', '用户取消任务，未继续执行。')

    def artifacts(self, task_id):
        with self.connect() as db:
            self._row(db, task_id)
            return {r['agent_id']: json.loads(r['content_json']) for r in db.execute('SELECT * FROM agent_artifacts WHERE task_id=? ORDER BY version', (task_id,))}
