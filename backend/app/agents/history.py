"""Bounded, read-only views of persisted Agent records; never runs a workflow.

This reader deliberately does not instantiate TaskStore or AssetStore. Every
connection uses mode=ro + query_only and a single transaction for a snapshot.
"""
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from ..errors import ServiceError

AGENTS = ('planner', 'researcher', 'designer', 'reviewer')
NAMES = {'planner': '任务规划Agent', 'researcher': '京剧研究Agent',
         'designer': '角色设计Agent', 'reviewer': '文化审校Agent'}
TASK_TYPE = 'character_creation'
TASK_STATES = {'waiting', 'running', 'awaiting_confirmation', 'completed', 'failed', 'cancelled'}
SOURCE = {'kind': 'persisted_history', 'readOnly': True,
          'note': '真实持久化历史记录；仅展示保存内容，不重新执行。模型执行元数据不是本次API调用证明。'}
MAX_JSON_BYTES = 262144
ARTIFACT_FIELDS = {
    'planner': {'theme', 'target', 'style', 'requirements', 'researchQueries', 'clarificationQuestions', 'requiredEntities', 'execution'},
    'researcher': {'queries', 'evidence', 'requirementCoverage', 'limitations', 'knowledgeGeneration', 'missingEntities', 'uncertain', 'policyVersion'},
    'designer': {'schemaVersion', 'name', 'positioning', 'costume', 'colors', 'visualElements', 'creativeElements', 'visualPrompt', 'usedEvidenceIds', 'limitations', 'execution'},
    'reviewer': {'verdict', 'issues', 'suggestions', 'checkedEvidenceIds', 'needsHumanReview', 'programmaticChecks', 'execution'},
}
RESULT_FIELDS = {'schemaVersion', 'taskId', 'design', 'review', 'citations', 'uncertain', 'publicationAllowed',
                 'userConfirmed', 'knowledgeGeneration', 'promptVersions', 'limitations', 'confirmationReason'}
EXECUTION_FIELDS = {'requestId', 'model', 'usage', 'elapsedSeconds', 'promptVersion', 'promptHash'}
SECRET_KEYS = {'apikey', 'authorization', 'accesstoken', 'refreshtoken', 'token', 'secret', 'password',
               'systemprompt', 'developerprompt', 'reasoning', 'reasoningcontent', 'chainofthought',
               'rawresponse', 'rawrequest', 'headers', 'storagekey', 'filepath', 'localpath',
               'system', 'developer', 'messages', 'prompt', 'systeminstructions', 'developerinstructions'}
KEY_PATTERN = re.compile(r'(?i)\bsk-[a-z0-9_-]{8,}\b|\bBearer\s+[^\s,;]+')
SECRET_ASSIGNMENT = re.compile(r'(?i)\b(?:[a-z0-9_]*api[_-]?key|authorization|[a-z0-9_]*(?:access[_-]?)?token|password|secret)\s*[:=]\s*[^\s,;]+')
PRIVATE_PATH = re.compile(r'(?:(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\r\n<>"|]+|/(?:home|Users|tmp|var|etc)/[^\s<>"|]+)')
URL = re.compile(r'https?://[^\s<>"\\]+', re.I)


def _text(value):
    value = KEY_PATTERN.sub('[已脱敏]', value)
    value = SECRET_ASSIGNMENT.sub('[敏感配置已脱敏]', value)
    value = PRIVATE_PATH.sub('[本地路径已隐藏]', value)
    def public_url(match):
        try:
            parts = urlsplit(match.group(0))
            if parts.username or parts.password or parts.scheme not in ('http', 'https'):
                return '[敏感链接已隐藏]'
            # Even unfamiliar signed query parameters never cross this endpoint.
            return urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))
        except ValueError:
            return '[无效链接已隐藏]'
    return URL.sub(public_url, value)[:12000]


def public_value(value, depth=0, budget=None):
    """Defence in depth for old free-form text; frontend still uses textContent."""
    budget = [2000] if budget is None else budget
    budget[0] -= 1
    if budget[0] < 0 or depth > 12:
        return '[历史展示长度已限制]'
    if isinstance(value, str):
        return _text(value)
    if isinstance(value, list):
        return [public_value(item, depth + 1, budget) for item in value[:200]]
    if isinstance(value, dict):
        result = {}
        for key, item in list(value.items())[:100]:
            normal = re.sub(r'[^a-z0-9]', '', str(key).lower())
            if normal in SECRET_KEYS or normal.endswith(('apikey', 'password', 'secret', 'token')):
                continue
            result[_text(str(key))[:200]] = public_value(item, depth + 1, budget)
        return result
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        return value if value == value and abs(value) != float('inf') else None
    return None


def _json(value, missing, field):
    if value is None:
        missing.append(field)
        return None
    if not isinstance(value, str) or len(value.encode('utf-8')) > MAX_JSON_BYTES:
        missing.append(field + ':展示长度超限')
        return None
    try:
        result = json.loads(value)
    except (ValueError, RecursionError):
        missing.append(field + ':保存格式异常')
        return None
    if not isinstance(result, dict):
        missing.append(field + ':保存格式异常')
        return None
    return result


def _pick(value, fields):
    return public_value({key: val for key, val in value.items() if key in fields})


def _uuid(value):
    try:
        return str(UUID(str(value))) == str(value).lower()
    except (TypeError, ValueError, AttributeError):
        return False


class HistoryReader:
    def __init__(self, task_path, asset_path=None):
        self.path = Path(task_path)
        self.asset_path = Path(asset_path) if asset_path is not None else None

    @contextmanager
    def snapshot(self):
        if not self.path.is_file():
            yield None, set(), False
            return
        db = None
        try:
            db = sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True, timeout=3)
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA query_only=ON')
            # A read-only attachment lets task/asset associations be read in the
            # same connection and transaction without catalog constructors.
            asset_available = False
            if self.asset_path is not None and self.asset_path.is_file():
                try:
                    db.execute('ATTACH DATABASE ? AS asset_catalog', (self.asset_path.resolve().as_uri() + '?mode=ro',))
                    asset_available = True
                except sqlite3.Error:
                    asset_available = False
            db.execute('BEGIN')
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'agent_tasks' not in tables:
                raise ServiceError('AGENT_HISTORY_UNAVAILABLE', '历史任务存储结构不可读取，请联系维护者检查。', 503, True)
            yield db, tables, asset_available
        except sqlite3.Error:
            raise ServiceError('AGENT_HISTORY_UNAVAILABLE', '历史记录暂时无法读取，请稍后重新查询。', 503, True) from None
        finally:
            if db is not None:
                db.close()  # rolls back the read transaction; no commit or state recovery

    @staticmethod
    def _summary(db, tables, row):
        missing = []
        task_id = row['task_id']
        brief = _json(row['brief_json'], missing, 'brief') or {}
        steps = list(db.execute('SELECT agent_id,state,started_at,finished_at FROM agent_steps WHERE task_id=?', (task_id,))) if 'agent_steps' in tables else []
        if len(steps) != 4 or {s['agent_id'] for s in steps} != set(AGENTS):
            missing.append('agentSteps')
        stats = db.execute("""SELECT count(*) AS total, min(sequence) AS first, max(sequence) AS last,
            sum(CASE WHEN json_valid(payload_json) THEN json_extract(payload_json,'$.sequence')=sequence ELSE 0 END) AS valid,
            min(CASE WHEN json_valid(payload_json) AND json_extract(payload_json,'$.kind')='task'
                AND json_extract(payload_json,'$.taskState')='running' THEN json_extract(payload_json,'$.occurredAt') END) AS started,
            max(CASE WHEN json_valid(payload_json) AND json_extract(payload_json,'$.kind')='task'
                AND json_extract(payload_json,'$.taskState') IN ('completed','failed','cancelled') THEN json_extract(payload_json,'$.occurredAt') END) AS finished
            FROM agent_events WHERE task_id=?""", (task_id,)).fetchone() if 'agent_events' in tables else None
        sequence = row['sequence']
        event_count = stats['total'] if stats else 0
        complete = bool(stats and sequence > 0 and event_count == sequence and stats['first'] == 1
                        and stats['last'] == sequence and stats['valid'] == sequence)
        if not complete:
            missing.append('eventSequence')
        started = stats['started'] if stats else None
        finished = stats['finished'] if stats else None
        # UpdatedAt is never silently presented as the execution start/end.
        if started is None:
            missing.append('taskStartedAt')
        if finished is None and row['state'] in ('completed', 'failed', 'cancelled'):
            missing.append('taskFinishedAt')
        evidence_of_execution = False
        if 'agent_artifacts' in tables:
            evidence_of_execution = bool(db.execute("""SELECT 1 FROM agent_artifacts WHERE task_id=? AND json_valid(content_json)
                AND json_type(content_json,'$.execution')='object' LIMIT 1""", (task_id,)).fetchone())
        title = row['design_name'] or brief.get('requirements') or '角色创作任务'
        return public_value({'taskId': task_id, 'taskType': TASK_TYPE, 'title': str(title)[:160], 'state': row['state'],
            'createdAt': row['created_at'], 'updatedAt': row['updated_at'], 'startedAt': started, 'finishedAt': finished,
            'executedAgents': [aid for aid in AGENTS if any(s['agent_id'] == aid and s['started_at'] is not None for s in steps)],
            'completedSteps': sum(s['state'] == 'completed' for s in steps), 'totalSteps': 4,
            'resultReadable': bool(row['result_readable']), 'hasSavedResult': bool(row['has_result']),
            'eventCount': event_count, 'lastSequence': sequence,
            'historyCompleteness': 'complete' if complete and 'agentSteps' not in missing else 'incomplete',
            'missingFields': missing, 'sourceType': 'persisted_history',
            'executionType': 'model_metadata_recorded' if evidence_of_execution else 'unknown'})

    @staticmethod
    def _task_sql():
        return """SELECT task_id,state,sequence,created_at,updated_at,substr(brief_json,1,8192) AS brief_json,
            result_json IS NOT NULL AS has_result,
            CASE WHEN json_valid(result_json) THEN json_type(result_json,'$.design')='object'
                AND json_type(result_json,'$.review')='object' ELSE 0 END AS result_readable,
            CASE WHEN json_valid(result_json) THEN substr(json_extract(result_json,'$.design.name'),1,160) END AS design_name
            FROM agent_tasks"""

    def list(self, page=1, page_size=10, state=None, task_type=None, task_id=None):
        with self.snapshot() as (db, tables, _):
            if db is None:
                return {'items': [], 'page': page, 'pageSize': page_size, 'total': 0, 'totalPages': 0,
                        'availableStates': [], 'availableTaskTypes': [], 'source': SOURCE}
            conditions, args = [], []
            if state is not None:
                conditions.append('state=?'); args.append(state)
            if task_id is not None:
                conditions.append('task_id=?'); args.append(task_id)
            if task_type is not None and task_type != TASK_TYPE:
                conditions.append('0=1')
            where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
            total = db.execute('SELECT count(*) FROM agent_tasks' + where, args).fetchone()[0]
            rows = db.execute(self._task_sql() + where + ' ORDER BY created_at DESC,task_id DESC LIMIT ? OFFSET ?',
                              (*args, page_size, (page - 1) * page_size)).fetchall()
            states = [r[0] for r in db.execute('SELECT DISTINCT state FROM agent_tasks ORDER BY state')]
            return {'items': [self._summary(db, tables, r) for r in rows], 'page': page, 'pageSize': page_size,
                    'total': total, 'totalPages': (total + page_size - 1) // page_size,
                    'availableStates': public_value(states), 'availableTaskTypes': [TASK_TYPE] if states else [], 'source': SOURCE}

    def detail(self, task_id, event_page=1, event_page_size=30):
        with self.snapshot() as (db, tables, assets_available):
            row = db.execute(self._task_sql() + ' WHERE task_id=?', (task_id,)).fetchone() if db is not None else None
            if row is None:
                raise ServiceError('AGENT_TASK_NOT_FOUND', '未找到这个历史任务，请检查任务标识。', 404)
            summary = self._summary(db, tables, row)
            missing = list(summary['missingFields'])
            raw = db.execute('SELECT brief_json,confirmation_json,result_json FROM agent_tasks WHERE task_id=?', (task_id,)).fetchone()
            brief = _json(raw['brief_json'], missing, 'brief')
            result = _json(raw['result_json'], missing, 'result')
            confirmation = _json(raw['confirmation_json'], missing, 'confirmation')
            agents = []
            for aid in AGENTS:
                step = db.execute('SELECT * FROM agent_steps WHERE task_id=? AND agent_id=?', (task_id, aid)).fetchone() if 'agent_steps' in tables else None
                artifact = db.execute('SELECT * FROM agent_artifacts WHERE task_id=? AND agent_id=? ORDER BY version DESC LIMIT 1', (task_id, aid)).fetchone() if 'agent_artifacts' in tables else None
                absent = ['input']
                output = _json(artifact['content_json'], absent, 'output') if artifact else None
                if artifact is None:
                    absent.append('output')
                if step is None:
                    absent.append('step')
                selected = {key: val for key, val in (output or {}).items() if key in ARTIFACT_FIELDS[aid]}
                if isinstance(selected.get('execution'), dict):
                    selected['execution'] = {key: val for key, val in selected['execution'].items() if key in EXECUTION_FIELDS}
                agents.append(public_value({'id': aid, 'name': NAMES[aid], 'state': step['state'] if step else None,
                    'summary': step['summary'] if step else None, 'startedAt': step['started_at'] if step else None,
                    'finishedAt': step['finished_at'] if step else None, 'errorCode': step['error_code'] if step else None,
                    'input': None, 'inputNote': '历史记录未保存该信息；下方仅展示原任务需求与已保存产物。',
                    'output': public_value(selected) if output is not None else None,
                    'outputVersion': artifact['version'] if artifact else None, 'outputHash': artifact['content_hash'] if artifact else None,
                    'outputSavedAt': artifact['created_at'] if artifact else None, 'missingFields': absent}))
            event_rows = list(db.execute('SELECT sequence,payload_json FROM agent_events WHERE task_id=? ORDER BY sequence LIMIT ? OFFSET ?',
                              (task_id, event_page_size, (event_page - 1) * event_page_size))) if 'agent_events' in tables else []
            events = []
            for event in event_rows:
                saved = _json(event['payload_json'], missing, 'event:' + str(event['sequence']))
                if saved is None:
                    events.append({'sequence': event['sequence'], 'summary': '历史事件保存格式异常，未重建事件。', 'incomplete': True})
                else:
                    public_event = _pick(saved, {'kind', 'runId', 'sequence', 'occurredAt', 'summary', 'agentId', 'state', 'taskState', 'confirmationId', 'errorCode'})
                    required = {'kind', 'runId', 'sequence', 'occurredAt', 'summary'}
                    required.update({'agentId', 'state'} if saved.get('kind') == 'agent' else {'taskState'})
                    absent = sorted(required - saved.keys())
                    if (absent or saved.get('kind') not in ('agent', 'task')
                            or saved.get('sequence') != event['sequence']):
                        # The SQL sequence is actually saved; no missing event
                        # timestamp, state or execution output is reconstructed.
                        public_event.update(sequence=event['sequence'], incomplete=True, missingFields=absent)
                        missing.append('event:' + str(event['sequence']) + ':字段不完整')
                    events.append(public_event)
            confirmed_at = None
            if result and result.get('userConfirmed') is True and 'agent_events' in tables:
                stamp = db.execute("""SELECT json_extract(payload_json,'$.occurredAt') FROM agent_events
                    WHERE task_id=? AND json_valid(payload_json) AND json_extract(payload_json,'$.kind')='task'
                    AND json_extract(payload_json,'$.taskState')='completed' ORDER BY sequence DESC LIMIT 1""", (task_id,)).fetchone()
                confirmed_at = stamp[0] if stamp else None
            assets, asset_status = self._assets(db, assets_available, task_id)
            safe_result = _pick(result, RESULT_FIELDS) if result is not None else None
            # A present JSON result is not assumed complete or accepted.
            review = safe_result.get('review') if safe_result else None
            citations = safe_result.get('citations', []) if safe_result else []
            if not citations:
                research_output = next((a['output'] for a in agents if a['id'] == 'researcher'), None)
                citations = research_output.get('evidence', []) if research_output else []
            if review is None:
                review = next((a['output'] for a in agents if a['id'] == 'reviewer'), None)
            return public_value({'task': summary, 'brief': _pick(brief, {'requirements', 'style', 'parentTaskId'}) if brief else None,
                    'agents': agents, 'result': safe_result, 'citations': citations, 'culturalReview': review,
                    'humanConfirmation': {'record': _pick(confirmation, {'id', 'reason', 'canAccept'}) if confirmation else None,
                        'userConfirmed': result.get('userConfirmed') if result and isinstance(result.get('userConfirmed'), bool) else None,
                        'publicationAllowed': result.get('publicationAllowed') if result and isinstance(result.get('publicationAllowed'), bool) else None,
                        'confirmedAt': confirmed_at},
                    'events': events, 'eventPage': event_page, 'eventPageSize': event_page_size,
                    'eventTotal': summary['eventCount'], 'eventTotalPages': (summary['eventCount'] + event_page_size - 1) // event_page_size,
                    'assets': assets, 'assetAssociationStatus': asset_status, 'missingFields': list(dict.fromkeys(missing)),
                    'source': SOURCE, 'snapshotAt': datetime.now(timezone.utc).isoformat()})

    def _assets(self, db, available, task_id):
        if not available:
            return [], 'unavailable'
        try:
            tables = {r[0] for r in db.execute("SELECT name FROM asset_catalog.sqlite_master WHERE type='table'")}
            if not {'character_assets', 'asset_models'}.issubset(tables):
                return [], 'unavailable'
            # json_valid guards malformed legacy content, never calls asset services.
            rows = db.execute("""SELECT asset_id,content_json FROM asset_catalog.character_assets
                WHERE json_valid(content_json) AND json_extract(content_json,'$.sourceTaskId')=?
                ORDER BY created_at DESC,asset_id DESC LIMIT 100""", (task_id,)).fetchall()
            found = []
            for row in rows:
                if len(row['content_json'].encode('utf-8')) > MAX_JSON_BYTES:
                    continue
                content = json.loads(row['content_json'])
                aid = row['asset_id']
                if not isinstance(content, dict) or not _uuid(aid) or content.get('assetId') != aid:
                    continue
                models = []
                for model in db.execute('SELECT model_id,content_json FROM asset_catalog.asset_models WHERE asset_id=? ORDER BY created_at DESC', (aid,)):
                    try:
                        if len(model['content_json'].encode('utf-8')) > MAX_JSON_BYTES:
                            continue
                        metadata = json.loads(model['content_json'])
                        if (isinstance(metadata, dict) and metadata.get('assetId') == aid
                                and metadata.get('modelId') == model['model_id'] and _uuid(model['model_id'])
                                and metadata.get('characterId', content.get('characterId')) == content.get('characterId')
                                and metadata.get('styleMode', content.get('styleMode')) == content.get('styleMode')):
                            models.append({'modelId': model['model_id'], 'origin': metadata.get('origin'),
                                           'format': metadata.get('format'), 'title': metadata.get('title')})
                    except (ValueError, TypeError):
                        continue
                found.append({'assetId': aid, 'characterId': content.get('characterId'), 'name': content.get('name'),
                              'styleMode': content.get('styleMode'), 'styleVersion': content.get('styleVersion'),
                              'modelIds': [m['modelId'] for m in models[:100]], 'models': models[:100],
                              'viewerUrl': '/about.html?assetId=' + aid + '#ai-workshop-model'})
            return public_value(found), 'linked' if found else 'not_linked'
        except (sqlite3.Error, ValueError, TypeError):
            return [], 'unavailable'
