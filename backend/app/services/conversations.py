"""Local chat history, independent of existing business SQLite databases.

Only explicit conversation creation/message submission writes this store.
Persisting admission before generation and keeping unknown outcomes prevents
an interrupted paid request from silently becoming another paid attempt.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from uuid import UUID, uuid4

import portalocker

from ..errors import ServiceError
from ..schemas import QuestionAnswer, QuestionRequest

MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TURNS = 200


def now():
    return datetime.now(timezone.utc).isoformat()


def conversation_id(value):
    try:
        identifier = str(UUID(str(value)))
        if str(value) != identifier:
            raise ValueError('noncanonical')
        return identifier
    except (ValueError, TypeError, AttributeError):
        raise ServiceError('CONVERSATION_NOT_FOUND', '未找到这段对话，请从历史列表重新选择。', 404) from None


def unavailable():
    return ServiceError('CONVERSATION_STORE_UNAVAILABLE', '对话记录暂时无法读取或保存，请检查本地资源后重试；原记录不会自动重建。', 503)


class ConversationStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, identifier):
        identifier = conversation_id(identifier)
        return self.root / f'{identifier}.json'

    def _check_root(self):
        if self.root.is_symlink() or (self.root.exists() and not self.root.is_dir()):
            raise unavailable()

    def _read(self, identifier):
        path = self._path(identifier)
        self._check_root()
        if not path.exists():
            raise ServiceError('CONVERSATION_NOT_FOUND', '未找到这段对话，请从历史列表重新选择。', 404)
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
                raise ValueError('invalid file')
            data = json.loads(path.read_text(encoding='utf-8'))
            if (not isinstance(data, dict) or data.get('version') != 1
                    or data.get('id') != str(identifier)
                    or not isinstance(data.get('title'), str)
                    or not isinstance(data.get('turns'), list)
                    or len(data['turns']) > MAX_TURNS):
                raise ValueError('invalid conversation')
            for field in ('createdAt', 'updatedAt'):
                datetime.fromisoformat(data[field])
            keys = set()
            for turn in data['turns']:
                if not isinstance(turn, dict):
                    raise ValueError('invalid turn')
                conversation_id(turn['id'])
                QuestionRequest(question=turn['question'])
                datetime.fromisoformat(turn['createdAt'])
                if turn['status'] not in ('completed', 'failed', 'unknown', 'pending'):
                    raise ValueError('invalid status')
                key = turn['idempotencyKey']
                if not isinstance(key, str) or not 8 <= len(key) <= 128 or key in keys:
                    raise ValueError('invalid request key')
                keys.add(key)
                if turn['status'] == 'completed':
                    QuestionAnswer.model_validate(turn['answer'])
                elif turn.get('answer') is not None:
                    raise ValueError('unexpected answer')
                error = turn.get('error')
                if error is not None and (not isinstance(error, dict)
                        or not isinstance(error.get('code'), str)
                        or not isinstance(error.get('message'), str)
                        or type(error.get('retryable')) is not bool):
                    raise ValueError('invalid error')
            return data
        except (OSError, ValueError, KeyError, TypeError):
            raise unavailable() from None

    def _write(self, data):
        self._check_root()
        path = self._path(data['id'])
        temporary = None
        try:
            if path.is_symlink():
                raise OSError('invalid destination')
            raw = json.dumps(data, ensure_ascii=False, allow_nan=False)
            if len(raw.encode('utf-8')) > MAX_FILE_BYTES:
                raise ServiceError('CONVERSATION_FULL', '这段对话已达到保存上限，请新建对话继续。', 409)
            fd, temporary = tempfile.mkstemp(prefix=f'.{data["id"]}-', suffix='.tmp', dir=self.root)
            with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as output:
                output.write(raw)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
            temporary = None
        except OSError:
            raise unavailable() from None
        finally:
            if temporary is not None:
                try:
                    Path(temporary).unlink()
                except OSError:
                    pass

    def create(self):
        self._check_root()
        try:
            # Chat creation may create its own subdirectory, never a missing
            # configured RAG root or any of the existing business resources.
            if self.root.parent.is_symlink() or not self.root.parent.is_dir():
                raise OSError('configured data root unavailable')
            self.root.mkdir(exist_ok=True)
        except OSError:
            raise unavailable() from None
        stamp = now()
        data = {'version': 1, 'id': str(uuid4()), 'title': '新对话',
                'createdAt': stamp, 'updatedAt': stamp, 'turns': []}
        self._write(data)
        return self.public(data)

    @staticmethod
    def public(data):
        return {key: value for key, value in data.items() if key != 'version'}

    def detail(self, identifier):
        return self.public(self._read(identifier))

    def list(self, limit=30, offset=0):
        self._check_root()
        if not self.root.exists():
            return {'items': [], 'hasMore': False}
        try:
            records = [self._read(path.stem) for path in self.root.glob('*.json')]
        except OSError:
            raise unavailable() from None
        records.sort(key=lambda value: (value['updatedAt'], value['id']), reverse=True)
        items = [{**{key: data[key] for key in ('id', 'title', 'createdAt', 'updatedAt')},
                  'turnCount': sum(turn['status'] == 'completed' for turn in data['turns'])}
                 for data in records[offset:offset + limit]]
        return {'items': items, 'hasMore': len(records) > offset + limit}

    @contextmanager
    def locked(self, identifier):
        # Read first: missing/misconfigured stores must not be created by a send.
        self._read(identifier)
        lock_path = self.root / f'.{conversation_id(identifier)}.lock'
        if lock_path.is_symlink():
            raise unavailable()
        lock = portalocker.Lock(str(lock_path), timeout=0,
                                flags=portalocker.LOCK_EX | portalocker.LOCK_NB)
        try:
            lock.acquire()
        except portalocker.exceptions.LockException:
            raise ServiceError('CONVERSATION_BUSY', '这段对话正在处理问题，请等待当前回答。', 409, True) from None
        except OSError:
            raise unavailable() from None
        try:
            yield self._read(identifier)
        finally:
            lock.release()

    def begin(self, data, question, key):
        old = next((turn for turn in data['turns'] if turn['idempotencyKey'] == key), None)
        if old:
            if old['question'] != question:
                raise ServiceError('IDEMPOTENCY_CONFLICT', '同一请求标识不能用于不同问题。', 409)
            if old['status'] == 'completed':
                return old, True
        if any(turn['status'] in ('pending', 'unknown') for turn in data['turns']):
            raise ServiceError('CHAT_OUTCOME_UNKNOWN', '这段对话有尚未确认的请求，已阻止继续生成。请查看已保存记录，或新建独立对话。', 409)
        if old:
            if old['status'] in ('pending', 'unknown'):
                raise ServiceError('CHAT_OUTCOME_UNKNOWN', '上一请求的结果尚未确认，已阻止重复生成。请查看已保存记录，不要重复提交同一问题。', 409)
            if not old.get('error', {}).get('retryable'):
                raise ServiceError('CHAT_RETRY_BLOCKED', '这个请求不能直接重试，请检查提示后调整问题。', 409)
            old.update(status='pending', error=None)
            turn = old
        else:
            if any(turn['question'] == question and turn['status'] in ('pending', 'unknown') for turn in data['turns']):
                raise ServiceError('CHAT_OUTCOME_UNKNOWN', '相同问题的上一请求尚未确认，已阻止重复生成。', 409)
            if len(data['turns']) >= MAX_TURNS:
                raise ServiceError('CONVERSATION_FULL', '这段对话已达到保存上限，请新建对话继续。', 409)
            turn = {'id': str(uuid4()), 'question': question, 'status': 'pending',
                    'answer': None, 'error': None, 'createdAt': now(), 'idempotencyKey': key}
            data['turns'].append(turn)
            if len(data['turns']) == 1:
                data['title'] = question.replace('\n', ' ')[:28]
        data['updatedAt'] = now()
        self._write(data)
        return turn, False

    def finish(self, data, turn, *, answer=None, error=None, unknown=False):
        turn['status'] = 'completed' if answer is not None else ('unknown' if unknown else 'failed')
        turn['answer'] = answer
        turn['error'] = error
        data['updatedAt'] = now()
        self._write(data)

    @staticmethod
    def context(data, before_turn_id=None):
        turns = data['turns']
        if before_turn_id is not None:
            boundary = next((index for index, turn in enumerate(turns)
                             if turn['id'] == before_turn_id), None)
            if boundary is None:
                raise unavailable()
            turns = turns[:boundary]
        return [{'question': turn['question'][:600], 'answer': turn['answer']['answer'][:1000]}
                for turn in turns if turn['status'] == 'completed'][-4:]
