"""Project-wide Neural4D creation-attempt ledger. Never calls a provider.

All reservations survive failure, cancellation and recovery. The fixed cap is
three HTTP creation attempts, not three successful models. A missing/new ledger
has UNKNOWN history and cannot create models until a trusted human reconciliation.
The service must hold its project-wide sender lock while recovering/sending;
constructing another UsageManager intentionally does not recover live workers.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time
import uuid

from ..errors import ServiceError
from ..database import open_existing, validate_database, initialize_database


PROJECT_ID = 'xijing-ai-neural4d-project-v4'
POLICY_VERSION = 'phase4-generation-attempts-v4'
MAX_CREATION_ATTEMPTS = 3
STATES = {'RESERVED', 'ATTEMPT_STARTED', 'SUBMITTED', 'PROCESSING', 'SUCCEEDED',
          'FAILED', 'UNKNOWN', 'PENDING_RECONCILIATION'}
UNRECONCILED_STATES = {'UNKNOWN', 'PENDING_RECONCILIATION'}
OPERATIONS = {'verify', 'preprocess', 'preprocess_status', 'create_model',
              'query_model', 'download', 'convert_format'}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _identifier(value, field):
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise ServiceError('NEURAL4D_INPUT_INVALID', f'{field}不能为空或超过长度限制。', 422)
    return value


def _payload(payload):
    if not isinstance(payload, dict) or type(payload.get('modelCount')) is not int or payload['modelCount'] != 1:
        raise ServiceError('NEURAL4D_MODEL_COUNT_INVALID', '每次真实建模必须且只能生成一个模型。', 422)
    try:
        data = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    except (ValueError, TypeError):
        raise ServiceError('NEURAL4D_INPUT_INVALID', '建模参数不是可冻结的有效JSON。', 422) from None
    if len(data.encode('utf-8')) > 32768:
        raise ServiceError('NEURAL4D_INPUT_INVALID', '建模参数超过长度限制。', 422)
    return data, hashlib.sha256(data.encode('utf-8')).hexdigest()


def _credits(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ServiceError('NEURAL4D_COST_UNVERIFIED', '必须先核实本次预计Credit费用。', 422)
    return float(value)


USAGE_TABLES = {
    'neural4d_usage_policy': ('project_id', 'policy_version', 'max_attempts', 'historical_used', 'historical_note', 'historical_verified_at', 'creation_halted', 'halt_code', 'created_at'),
    'neural4d_model_approvals': ('approval_id', 'payload_hash', 'purpose', 'estimated_credits', 'confirmed_at', 'expires_at', 'consumed_attempt_id'),
    'neural4d_creation_attempts': ('attempt_id', 'project_id', 'idempotency_key', 'approval_id', 'payload_hash', 'payload_json', 'purpose', 'estimated_credits', 'state', 'reserved_at', 'started_at', 'updated_at', 'provider_task_id', 'error_code', 'http_status'),
    'neural4d_attempt_events': ('sequence', 'attempt_id', 'state', 'recorded_at', 'provider_task_id', 'error_code', 'http_status'),
    'neural4d_operational_requests': ('request_id', 'operation', 'attempt_id', 'is_mock', 'recorded_at', 'http_status', 'duration_ms', 'actual_credits', 'error_code'),
}
USAGE_OBJECTS = tuple(('trigger', name) for name in (
    'neural4d_attempts_no_delete', 'neural4d_attempt_inputs_immutable', 'neural4d_send_claim_immutable',
    'neural4d_approval_no_delete', 'neural4d_approval_immutable', 'neural4d_usage_no_delete',
    'neural4d_usage_immutable', 'neural4d_attempts_cap', 'neural4d_events_no_delete',
    'neural4d_events_no_update', 'neural4d_requests_no_delete', 'neural4d_requests_no_update')) + (
    ('index', 'neural4d_attempt_payload'), ('index', 'neural4d_one_real_create_request'))
USAGE_SCHEMA = r"""
                CREATE TABLE IF NOT EXISTS neural4d_usage_policy (
                    project_id TEXT PRIMARY KEY,
                    policy_version TEXT NOT NULL,
                    max_attempts INTEGER NOT NULL CHECK(max_attempts=3),
                    historical_used INTEGER CHECK(historical_used BETWEEN 0 AND 3),
                    historical_note TEXT,
                    historical_verified_at TEXT,
                    creation_halted INTEGER NOT NULL DEFAULT 0 CHECK(creation_halted IN (0,1)),
                    halt_code TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS neural4d_model_approvals (
                    approval_id TEXT PRIMARY KEY,
                    payload_hash TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    estimated_credits REAL NOT NULL CHECK(estimated_credits>0),
                    confirmed_at TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    consumed_attempt_id TEXT UNIQUE
                );
                CREATE TABLE IF NOT EXISTS neural4d_creation_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES neural4d_usage_policy(project_id),
                    idempotency_key TEXT NOT NULL UNIQUE,
                    approval_id TEXT NOT NULL UNIQUE REFERENCES neural4d_model_approvals(approval_id),
                    payload_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    estimated_credits REAL NOT NULL CHECK(estimated_credits>0),
                    state TEXT NOT NULL CHECK(state IN ('RESERVED','ATTEMPT_STARTED','SUBMITTED','PROCESSING','SUCCEEDED','FAILED','UNKNOWN','PENDING_RECONCILIATION')),
                    reserved_at TEXT NOT NULL,
                    started_at TEXT,
                    updated_at TEXT NOT NULL,
                    provider_task_id TEXT,
                    error_code TEXT,
                    http_status INTEGER
                );
                CREATE INDEX IF NOT EXISTS neural4d_attempt_payload ON neural4d_creation_attempts(payload_hash);
                CREATE TABLE IF NOT EXISTS neural4d_attempt_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id TEXT NOT NULL REFERENCES neural4d_creation_attempts(attempt_id),
                    state TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    provider_task_id TEXT,
                    error_code TEXT,
                    http_status INTEGER
                );
                CREATE TABLE IF NOT EXISTS neural4d_operational_requests (
                    request_id TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    attempt_id TEXT REFERENCES neural4d_creation_attempts(attempt_id),
                    is_mock INTEGER NOT NULL CHECK(is_mock IN (0,1)),
                    recorded_at TEXT NOT NULL,
                    http_status INTEGER,
                    duration_ms REAL,
                    actual_credits REAL,
                    error_code TEXT
                );
                CREATE UNIQUE INDEX IF NOT EXISTS neural4d_one_real_create_request
                    ON neural4d_operational_requests(attempt_id)
                    WHERE operation='create_model' AND is_mock=0;
                CREATE TRIGGER IF NOT EXISTS neural4d_attempts_no_delete
                    BEFORE DELETE ON neural4d_creation_attempts
                    BEGIN SELECT RAISE(ABORT,'creation history is immutable'); END;
                CREATE TRIGGER IF NOT EXISTS neural4d_attempt_inputs_immutable
                    BEFORE UPDATE ON neural4d_creation_attempts
                    WHEN NEW.attempt_id != OLD.attempt_id OR NEW.project_id != OLD.project_id
                     OR NEW.idempotency_key != OLD.idempotency_key OR NEW.approval_id != OLD.approval_id
                     OR NEW.payload_hash != OLD.payload_hash OR NEW.payload_json != OLD.payload_json
                     OR NEW.purpose != OLD.purpose OR NEW.estimated_credits != OLD.estimated_credits
                     OR NEW.reserved_at != OLD.reserved_at
                    BEGIN SELECT RAISE(ABORT,'creation inputs are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS neural4d_send_claim_immutable
                    BEFORE UPDATE ON neural4d_creation_attempts
                    WHEN (OLD.started_at IS NOT NULL AND NEW.started_at IS NOT OLD.started_at)
                     OR (OLD.state!='RESERVED' AND NEW.state='RESERVED')
                     OR (NEW.state='ATTEMPT_STARTED' AND OLD.state!='RESERVED')
                     OR (OLD.provider_task_id IS NOT NULL AND NEW.provider_task_id IS NOT OLD.provider_task_id)
                    BEGIN SELECT RAISE(ABORT,'send claim cannot be reset'); END;
                CREATE TRIGGER IF NOT EXISTS neural4d_approval_no_delete
                    BEFORE DELETE ON neural4d_model_approvals
                    BEGIN SELECT RAISE(ABORT,'approval history is immutable'); END;
                CREATE TRIGGER IF NOT EXISTS neural4d_approval_immutable
                    BEFORE UPDATE ON neural4d_model_approvals
                    WHEN NEW.approval_id != OLD.approval_id OR NEW.payload_hash != OLD.payload_hash
                     OR NEW.purpose != OLD.purpose OR NEW.estimated_credits != OLD.estimated_credits
                     OR NEW.confirmed_at != OLD.confirmed_at OR NEW.expires_at != OLD.expires_at
                     OR (OLD.consumed_attempt_id IS NOT NULL AND NEW.consumed_attempt_id IS NOT OLD.consumed_attempt_id)
                    BEGIN SELECT RAISE(ABORT,'approval cannot be edited or reused'); END;
                CREATE TRIGGER IF NOT EXISTS neural4d_usage_no_delete
                    BEFORE DELETE ON neural4d_usage_policy
                    BEGIN SELECT RAISE(ABORT,'usage history is immutable'); END;
                CREATE TRIGGER IF NOT EXISTS neural4d_usage_immutable
                    BEFORE UPDATE ON neural4d_usage_policy
                    WHEN NEW.project_id != OLD.project_id OR NEW.policy_version != OLD.policy_version
                     OR NEW.max_attempts != OLD.max_attempts OR NEW.created_at != OLD.created_at
                     OR (OLD.historical_used IS NOT NULL AND (
                         NEW.historical_used IS NOT OLD.historical_used
                         OR NEW.historical_note IS NOT OLD.historical_note
                         OR NEW.historical_verified_at IS NOT OLD.historical_verified_at))
                     OR NEW.creation_halted < OLD.creation_halted
                    BEGIN SELECT RAISE(ABORT,'usage policy cannot be reset'); END;
                CREATE TRIGGER IF NOT EXISTS neural4d_attempts_cap
                    BEFORE INSERT ON neural4d_creation_attempts
                    WHEN (SELECT historical_used FROM neural4d_usage_policy WHERE project_id=NEW.project_id) IS NULL
                     OR (SELECT creation_halted FROM neural4d_usage_policy WHERE project_id=NEW.project_id)=1
                     OR (SELECT historical_used FROM neural4d_usage_policy WHERE project_id=NEW.project_id)
                          + (SELECT count(*) FROM neural4d_creation_attempts) >= 3
                    BEGIN SELECT RAISE(ABORT,'unknown history or exhausted quota'); END;
                CREATE TRIGGER IF NOT EXISTS neural4d_events_no_delete
                    BEFORE DELETE ON neural4d_attempt_events
                    BEGIN SELECT RAISE(ABORT,'audit events are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS neural4d_events_no_update
                    BEFORE UPDATE ON neural4d_attempt_events
                    BEGIN SELECT RAISE(ABORT,'audit events are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS neural4d_requests_no_delete
                    BEFORE DELETE ON neural4d_operational_requests
                    BEGIN SELECT RAISE(ABORT,'request history is immutable'); END;
                CREATE TRIGGER IF NOT EXISTS neural4d_requests_no_update
                    BEFORE UPDATE ON neural4d_operational_requests
                    BEGIN SELECT RAISE(ABORT,'request history is immutable'); END;
            """
USAGE_DATABASE_MESSAGE = '建模账本缺失、路径错误或异常，已关闭真实创建；请恢复并核查原历史记录，未自动重建。'


class UsageManager:
    """One authoritative SQLite ledger, deliberately not keyed by API credentials.

    ``initialize_history`` is a trusted CLI operation, never a browser endpoint.
    ``reserve`` returns ``newlyReserved=False`` on a replay; callers must never
    send that record. Only the winner of ``mark_started`` may attempt one HTTP
    submission. There is no refund, delete, retry or cap-raising method.
    """

    def __init__(self, path: Path, *, create=False):
        self.path = Path(path).expanduser().resolve()
        options = {'objects': USAGE_OBJECTS, 'code': 'NEURAL4D_LEDGER_UNAVAILABLE', 'message': USAGE_DATABASE_MESSAGE}
        if create:
            def seed(db):
                db.execute('INSERT INTO neural4d_usage_policy(project_id,policy_version,max_attempts,created_at) VALUES (?,?,?,?)',
                           (PROJECT_ID, POLICY_VERSION, MAX_CREATION_ATTEMPTS, _now()))
            initialize_database(self.path, USAGE_SCHEMA, USAGE_TABLES, seed=seed, **options)
        else:
            validate_database(self.path, USAGE_TABLES, **options)
        with self.connect() as db:
            self._policy(db)

    @contextmanager
    def connect(self):
        db = None
        try:
            db = open_existing(self.path, timeout=10, code='NEURAL4D_LEDGER_UNAVAILABLE', message=USAGE_DATABASE_MESSAGE)
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('PRAGMA busy_timeout=10000')
            db.execute('PRAGMA synchronous=FULL')
            with db:
                yield db
        except sqlite3.DatabaseError:
            raise ServiceError('NEURAL4D_LEDGER_UNAVAILABLE', '建模账本异常，已关闭真实创建；请核查历史记录。', 503) from None
        finally:
            if db is not None:
                db.close()

    def _policy(self, db):
        rows = db.execute('SELECT * FROM neural4d_usage_policy').fetchall()
        if len(rows) != 1 or rows[0]['project_id'] != PROJECT_ID or rows[0]['policy_version'] != POLICY_VERSION or rows[0]['max_attempts'] != MAX_CREATION_ATTEMPTS:
            raise ServiceError('NEURAL4D_LEDGER_INCONSISTENT', '建模账本与固定项目政策不符，已关闭真实创建。', 503)
        policy = rows[0]
        count = db.execute('SELECT count(*) FROM neural4d_creation_attempts').fetchone()[0]
        if policy['historical_used'] is not None and policy['historical_used'] + count > MAX_CREATION_ATTEMPTS:
            raise ServiceError('NEURAL4D_LEDGER_INCONSISTENT', '建模账本占用异常，已关闭真实创建。', 503)
        return policy

    @staticmethod
    def _require_reconciled(db):
        """Global temporary gate inside the caller's write transaction.

        Resolving an existing attempt is an audited service operation. It may
        remove this gate, but never grants send rights or refunds a reservation.
        Do not use the irreversible policy halt for an ordinary unknown result.
        """
        if db.execute("SELECT 1 FROM neural4d_creation_attempts WHERE state IN ('UNKNOWN','PENDING_RECONCILIATION') LIMIT 1").fetchone():
            raise ServiceError('NEURAL4D_RECONCILIATION_REQUIRED', '存在结果未知或待核查的旧建模任务，已暂停全项目新批准和新建；请先人工核查原任务，次数不返还。', 409)

    def initialize_history(self, used_attempts: int, note: str):
        if type(used_attempts) is not int or not 0 <= used_attempts <= MAX_CREATION_ATTEMPTS:
            raise ServiceError('NEURAL4D_HISTORY_INVALID', '历史建模提交次数必须是0至3之间的整数。', 422)
        if not isinstance(note, str) or not note.strip() or len(note) > 1000:
            raise ServiceError('NEURAL4D_HISTORY_INVALID', '核实历史需要明确的脱敏说明。', 422)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            policy = self._policy(db)
            if policy['historical_used'] is not None:
                raise ServiceError('NEURAL4D_HISTORY_ALREADY_VERIFIED', '历史占用已登记，不允许重置或再次初始化。', 409)
            if db.execute('SELECT count(*) FROM neural4d_creation_attempts').fetchone()[0]:
                raise ServiceError('NEURAL4D_LEDGER_INCONSISTENT', '历史未核实却存在创建记录，需人工核查。', 503)
            db.execute('UPDATE neural4d_usage_policy SET historical_used=?,historical_note=?,historical_verified_at=? WHERE project_id=?',
                       (used_attempts, note.strip(), _now(), PROJECT_ID))
        return self.summary()

    def summary(self):
        with self.connect() as db:
            db.execute('BEGIN')
            policy = self._policy(db)
            states = {r['state']: r['n'] for r in db.execute('SELECT state,count(*) AS n FROM neural4d_creation_attempts GROUP BY state')}
            reservations = states.get('RESERVED', 0)
            count = sum(states.values())
            historical = policy['historical_used']
            operational = db.execute('SELECT is_mock,count(*) AS n,coalesce(sum(actual_credits),0) AS credits FROM neural4d_operational_requests GROUP BY is_mock').fetchall()
        known = historical is not None
        unreconciled = sum(states.get(state, 0) for state in UNRECONCILED_STATES)
        return {'projectId': PROJECT_ID, 'policyVersion': POLICY_VERSION,
                'max_creation_attempts': MAX_CREATION_ATTEMPTS, 'max_models': 3, 'modelCount': 1,
                'historicalUsageVerified': known, 'historical_used_attempts': historical,
                'used_attempts': historical + count - reservations if known else None,
                'reserved_attempts': reservations if known else None,
                'occupied_attempts': historical + count if known else None,
                'remaining_attempts': MAX_CREATION_ATTEMPTS - historical - count if known else None,
                'attemptStates': states, 'creationHalted': bool(policy['creation_halted']),
                'haltCode': policy['halt_code'], 'automaticGenerationRetry': False,
                'creationPaused': bool(unreconciled),
                'pauseCode': 'NEURAL4D_RECONCILIATION_REQUIRED' if unreconciled else None,
                'unreconciled_attempts': unreconciled,
                'realHttpRequests': sum(r['n'] for r in operational if not r['is_mock']),
                'mockHttpRequests': sum(r['n'] for r in operational if r['is_mock']),
                'recordedActualCredits': sum(r['credits'] for r in operational if not r['is_mock'])}

    def approve(self, payload: dict, purpose: str, confirmed: bool = False,
                estimated_credits: float | None = None, ttl_seconds: int = 900):
        if confirmed is not True:
            raise ServiceError('NEURAL4D_CONFIRMATION_REQUIRED', '每次真实建模都需要用户明确确认。', 403)
        _, digest = _payload(payload)
        purpose = _identifier(purpose, '本次生成用途')
        credits = _credits(estimated_credits)
        if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 86400:
            raise ServiceError('NEURAL4D_APPROVAL_INVALID', '批准有效期无效。', 422)
        approval_id = str(uuid.uuid4())
        expires_at = time.time() + ttl_seconds
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self._policy(db)
            self._require_reconciled(db)
            db.execute('INSERT INTO neural4d_model_approvals VALUES (?,?,?,?,?,?,NULL)',
                       (approval_id, digest, purpose, credits, _now(), expires_at))
        return {'approvalId': approval_id, 'payloadHash': digest, 'purpose': purpose,
                'estimatedCredits': credits, 'expiresAt': expires_at, 'consumed': False}

    def lookup_replay(self, key: str, approval_id: str, payload: dict, purpose: str):
        """Read an exact prior attempt without reserving or granting send rights.

        The caller may return an already-started immutable attempt even if a
        newer asset version now exists. A different approval/payload cannot use
        the same key to bypass the current version gate.
        """
        key = _identifier(key, '幂等键')
        approval_id = _identifier(approval_id, '单次批准ID')
        purpose = _identifier(purpose, '本次生成用途')
        _, digest = _payload(payload)
        with self.connect() as db:
            self._policy(db)
            previous = db.execute('SELECT * FROM neural4d_creation_attempts WHERE idempotency_key=?', (key,)).fetchone()
            if previous is None:
                return None
            if previous['payload_hash'] != digest or previous['purpose'] != purpose or previous['approval_id'] != approval_id:
                raise ServiceError('NEURAL4D_IDEMPOTENCY_CONFLICT', '相同幂等键绑定不同输入或批准，已拒绝。', 409)
            return self._record(previous, newly_reserved=False)

    def approval_estimated_credits(self, approval_id: str):
        """Read the immutable human-approved estimate, not current config."""
        approval_id = _identifier(approval_id, '单次批准ID')
        with self.connect() as db:
            self._policy(db)
            row = db.execute('SELECT estimated_credits FROM neural4d_model_approvals WHERE approval_id=?', (approval_id,)).fetchone()
        if row is None:
            raise ServiceError('NEURAL4D_APPROVAL_NOT_FOUND', '本次批准不存在，不能创建任务。', 404)
        return row['estimated_credits']

    def reserve(self, key: str, approval_id: str, payload: dict, purpose: str,
                real_enabled: bool = False, provider_verified: bool = False):
        if real_enabled is not True:
            raise ServiceError('NEURAL4D_GENERATION_DISABLED', '真实建模默认关闭；请先取得单次授权。', 403)
        if provider_verified is not True:
            raise ServiceError('NEURAL4D_PROVIDER_UNVERIFIED', '供应商鉴权、权限与费用尚未验证。', 403)
        key = _identifier(key, '幂等键')
        approval_id = _identifier(approval_id, '单次批准ID')
        purpose = _identifier(purpose, '本次生成用途')
        data, digest = _payload(payload)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            policy = self._policy(db)
            previous = db.execute('SELECT * FROM neural4d_creation_attempts WHERE idempotency_key=?', (key,)).fetchone()
            if previous:
                if previous['payload_hash'] != digest or previous['purpose'] != purpose or previous['approval_id'] != approval_id:
                    raise ServiceError('NEURAL4D_IDEMPOTENCY_CONFLICT', '相同幂等键绑定不同输入或批准，已拒绝。', 409)
                return self._record(previous, newly_reserved=False)
            if policy['historical_used'] is None:
                raise ServiceError('NEURAL4D_HISTORY_UNVERIFIED', '全项目历史占用尚未核实，禁止创建真实模型。', 403)
            if policy['creation_halted']:
                raise ServiceError('NEURAL4D_CREATION_HALTED', '建模账本已停止新建，请先人工核查异常。', 403)
            self._require_reconciled(db)
            if policy['historical_used'] + db.execute('SELECT count(*) FROM neural4d_creation_attempts').fetchone()[0] >= MAX_CREATION_ATTEMPTS:
                raise ServiceError('NEURAL4D_QUOTA_EXHAUSTED', '全项目最多3次真实建模提交尝试，额度已用完。', 429)
            approval = db.execute('SELECT * FROM neural4d_model_approvals WHERE approval_id=?', (approval_id,)).fetchone()
            if not approval or approval['payload_hash'] != digest or approval['purpose'] != purpose:
                raise ServiceError('NEURAL4D_APPROVAL_INVALID', '批准不匹配当前图片、角色、参数或用途。', 409)
            if approval['consumed_attempt_id'] is not None:
                raise ServiceError('NEURAL4D_APPROVAL_CONSUMED', '本次批准已使用，不能再次创建。', 409)
            if approval['expires_at'] <= time.time():
                raise ServiceError('NEURAL4D_APPROVAL_EXPIRED', '本次生成批准已过期，请重新确认。', 409)
            duplicate = db.execute("SELECT state FROM neural4d_creation_attempts WHERE payload_hash=? AND state!='FAILED' LIMIT 1", (digest,)).fetchone()
            if duplicate:
                raise ServiceError('NEURAL4D_DUPLICATE_INPUT', '相同输入已有任务或未知结果，不能换幂等键重新创建。', 409)
            attempt_id = str(uuid.uuid4())
            now = _now()
            db.execute('INSERT INTO neural4d_creation_attempts(attempt_id,project_id,idempotency_key,approval_id,payload_hash,payload_json,purpose,estimated_credits,state,reserved_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                       (attempt_id, PROJECT_ID, key, approval_id, digest, data, purpose,
                        approval['estimated_credits'], 'RESERVED', now, now))
            db.execute('UPDATE neural4d_model_approvals SET consumed_attempt_id=? WHERE approval_id=? AND consumed_attempt_id IS NULL',
                       (attempt_id, approval_id))
            self._event(db, attempt_id, 'RESERVED')
            row = db.execute('SELECT * FROM neural4d_creation_attempts WHERE attempt_id=?', (attempt_id,)).fetchone()
        return self._record(row, newly_reserved=True)

    def mark_started(self, attempt_id: str):
        """Durably claim the sole send right before touching the network."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            policy = self._policy(db)
            if policy['creation_halted']:
                raise ServiceError('NEURAL4D_CREATION_HALTED', '真实创建已停止，不能发送已预约请求。', 403)
            row = self._get(db, attempt_id)
            if row['state'] != 'RESERVED':
                raise ServiceError('NEURAL4D_ATTEMPT_ALREADY_STARTED', '该提交已领取或等待核查，禁止再次发送。', 409)
            # A different attempt may have become unknown after this reservation
            # was committed. Recheck while claiming, before any network send.
            self._require_reconciled(db)
            now = _now()
            db.execute("UPDATE neural4d_creation_attempts SET state='ATTEMPT_STARTED',started_at=?,updated_at=? WHERE attempt_id=? AND state='RESERVED'", (now, now, attempt_id))
            self._event(db, attempt_id, 'ATTEMPT_STARTED')
            row = self._get(db, attempt_id)
        return self._record(row)

    def finish(self, attempt_id: str, state: str, provider_task_id: str | None = None,
               error_code: str | None = None, http_status: int | None = None):
        if state not in STATES - {'RESERVED', 'ATTEMPT_STARTED'}:
            raise ServiceError('NEURAL4D_STATE_INVALID', '提交状态无效，禁止重新预约。', 422)
        if provider_task_id is not None:
            _identifier(provider_task_id, '供应商任务ID')
        if error_code is not None:
            _identifier(error_code, '脱敏错误标识')
        if http_status is not None and (type(http_status) is not int or not 100 <= http_status <= 599):
            raise ServiceError('NEURAL4D_STATE_INVALID', 'HTTP状态无效。', 422)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self._policy(db)
            row = self._get(db, attempt_id)
            if row['state'] == 'RESERVED':
                raise ServiceError('NEURAL4D_STATE_INVALID', '未领取发送权的预约只能等待核查，不可视为已调用。', 409)
            if row['state'] in {'FAILED', 'SUCCEEDED'} and state != row['state']:
                raise ServiceError('NEURAL4D_STATE_INVALID', '终态记录不可覆盖；重新创建需新的批准和次数。', 409)
            known_id = row['provider_task_id']
            if known_id and provider_task_id and known_id != provider_task_id:
                raise ServiceError('NEURAL4D_TASK_ID_CONFLICT', '同一次提交不能绑定另一个供应商模型。', 409)
            final_id = provider_task_id or known_id
            if state in {'SUBMITTED', 'PROCESSING', 'SUCCEEDED'} and not final_id:
                raise ServiceError('NEURAL4D_TASK_ID_MISSING', '供应商任务标识缺失，不能认定提交成功。', 422)
            db.execute('UPDATE neural4d_creation_attempts SET state=?,provider_task_id=?,error_code=?,http_status=?,updated_at=? WHERE attempt_id=?',
                       (state, final_id, error_code, http_status, _now(), attempt_id))
            self._event(db, attempt_id, state, final_id, error_code, http_status)
            row = self._get(db, attempt_id)
        return self._record(row)

    def recover(self):
        """Called only under the service's exclusive owner lock on startup.

        Even a RESERVED crash is conservative: it cannot be sent on restart.
        A known submitted UUID remains queryable and never becomes a send queue.
        """
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self._policy(db)
            rows = db.execute("SELECT * FROM neural4d_creation_attempts WHERE state IN ('RESERVED','ATTEMPT_STARTED','UNKNOWN')").fetchall()
            for row in rows:
                db.execute("UPDATE neural4d_creation_attempts SET state='PENDING_RECONCILIATION',error_code='PROCESS_RESTART_RECONCILIATION',updated_at=? WHERE attempt_id=?", (_now(), row['attempt_id']))
                self._event(db, row['attempt_id'], 'PENDING_RECONCILIATION', row['provider_task_id'], 'PROCESS_RESTART_RECONCILIATION')
        return {'recoveredAttempts': len(rows), 'summary': self.summary()}

    def halt(self, code: str):
        """Fail closed on provider contract anomalies; no automatic reset."""
        code = _identifier(code, '脱敏停止标识')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self._policy(db)
            db.execute('UPDATE neural4d_usage_policy SET creation_halted=1,halt_code=? WHERE project_id=?', (code, PROJECT_ID))

    def get_attempt(self, attempt_id: str):
        with self.connect() as db:
            self._policy(db)
            row = self._get(db, attempt_id)
            events = db.execute('SELECT * FROM neural4d_attempt_events WHERE attempt_id=? ORDER BY sequence', (attempt_id,)).fetchall()
        result = self._record(row)
        result['events'] = [{'sequence': e['sequence'], 'state': e['state'], 'recordedAt': e['recorded_at'],
                             'providerTaskId': e['provider_task_id'], 'errorCode': e['error_code'],
                             'httpStatus': e['http_status']} for e in events]
        return result

    def frozen_payload(self, attempt_id: str):
        """Trusted service-only input; never include this in a public API response.

        Return a newly decoded copy and recheck the approved canonical hash.
        This is not an authorization to send; only mark_started grants a send.
        """
        with self.connect() as db:
            self._policy(db)
            row = self._get(db, attempt_id)
            try:
                data = json.loads(row['payload_json'])
                _, digest = _payload(data)
            except (ValueError, TypeError, ServiceError):
                raise ServiceError('NEURAL4D_LEDGER_INCONSISTENT', '冻结建模参数损坏，已拒绝发送。', 503) from None
            if digest != row['payload_hash']:
                raise ServiceError('NEURAL4D_LEDGER_INCONSISTENT', '冻结建模参数Hash不一致，已拒绝发送。', 503)
        return data

    def record_request(self, operation: str, *, attempt_id: str | None = None,
                       http_status: int | None = None, duration_ms: float | None = None,
                       actual_credits: float | None = None, is_mock: bool = False,
                       request_id: str | None = None, error_code: str | None = None):
        """Record only safe metadata, never bodies, URLs, tokens or headers."""
        if operation not in OPERATIONS:
            raise ServiceError('NEURAL4D_OPERATION_UNKNOWN', '供应商操作类型未核实，禁止记录为合法调用。', 422)
        if type(is_mock) is not bool:
            raise ServiceError('NEURAL4D_REQUEST_INVALID', '请求类型无效。', 422)
        for value in (duration_ms, actual_credits):
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
                raise ServiceError('NEURAL4D_REQUEST_INVALID', '脱敏请求统计无效。', 422)
        if error_code is not None:
            _identifier(error_code, '脱敏错误标识')
        if http_status is not None and (type(http_status) is not int or not 100 <= http_status <= 599):
            raise ServiceError('NEURAL4D_REQUEST_INVALID', 'HTTP状态无效。', 422)
        request_id = _identifier(request_id, '请求ID') if request_id is not None else str(uuid.uuid4())
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self._policy(db)
            if attempt_id is not None:
                attempt = self._get(db, attempt_id)
            else:
                attempt = None
            if operation == 'create_model' and not is_mock:
                if attempt is None or attempt['started_at'] is None:
                    raise ServiceError('NEURAL4D_UNRESERVED_REQUEST', '真实建模请求必须先取得持久化发送权。', 403)
                if db.execute("SELECT 1 FROM neural4d_operational_requests WHERE attempt_id=? AND operation='create_model' AND is_mock=0", (attempt_id,)).fetchone():
                    raise ServiceError('NEURAL4D_DUPLICATE_REQUEST', '一次提交禁止记录或发送第二次真实建模请求。', 409)
            db.execute('INSERT INTO neural4d_operational_requests VALUES (?,?,?,?,?,?,?,?,?)',
                       (request_id, operation, attempt_id, int(is_mock), _now(), http_status, duration_ms, actual_credits, error_code))
        return {'requestId': request_id, 'operation': operation, 'attemptId': attempt_id, 'mock': is_mock}

    @staticmethod
    def _get(db, attempt_id):
        row = db.execute('SELECT * FROM neural4d_creation_attempts WHERE attempt_id=?', (attempt_id,)).fetchone()
        if row is None:
            raise ServiceError('NEURAL4D_ATTEMPT_NOT_FOUND', '建模提交记录不存在。', 404)
        return row

    @staticmethod
    def _event(db, attempt_id, state, provider_task_id=None, error_code=None, http_status=None):
        db.execute('INSERT INTO neural4d_attempt_events(attempt_id,state,recorded_at,provider_task_id,error_code,http_status) VALUES (?,?,?,?,?,?)',
                   (attempt_id, state, _now(), provider_task_id, error_code, http_status))

    @staticmethod
    def _record(row, newly_reserved=False):
        # Do not expose frozen provider input JSON to browser logs or screenshots.
        return {'attemptId': row['attempt_id'], 'projectId': row['project_id'],
                'idempotencyKey': row['idempotency_key'], 'approvalId': row['approval_id'],
                'payloadHash': row['payload_hash'], 'purpose': row['purpose'],
                'estimatedCredits': row['estimated_credits'], 'state': row['state'],
                'reservedAt': row['reserved_at'], 'startedAt': row['started_at'],
                'updatedAt': row['updated_at'], 'providerTaskId': row['provider_task_id'],
                'errorCode': row['error_code'], 'httpStatus': row['http_status'],
                'newlyReserved': newly_reserved}
