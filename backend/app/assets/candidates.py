"""Local, immutable concept candidates without implied character approval.

Candidates are deliberately not asset_images: that table belongs to confirmed
Phase 3 characters. No candidate can be sent to the model service. Original
paths are labels only; previews always use independently saved hash files.
"""
import hashlib
import json
import re
import uuid

from ..errors import ServiceError
from .store import encode, now
from .validation import normalize_image
from .visual_prompt import canonical_hash


HIDDEN_FIELDS = {'storageKey', 'originalStorageKey', 'sourcePathLabel', 'historicalMetadata'}


class CandidateCatalog:
    def __init__(self, assets):
        self.assets, self.store, self.root = assets, assets.store, assets.root
        # AssetStore validates the complete current schema. Ordinary service
        # construction must not initialize or repair catalog tables.

    @staticmethod
    def _text(value, limit, label):
        if (not isinstance(value, str) or not value.strip() or len(value) > limit
                or any(ord(c) < 32 and c not in '\n\t' for c in value)):
            raise ServiceError('CANDIDATE_INPUT_INVALID', f'{label}格式无效。', 422)
        try:
            value.encode('utf-8')
        except UnicodeError:
            raise ServiceError('CANDIDATE_INPUT_INVALID', f'{label}编码无效。', 422)
        return value.strip()

    @classmethod
    def _note(cls, value, label):
        # Both plain user statements and structured audit notes are supported.
        # The note never grants rights: authoritative verification flags below
        # remain false, including when the caller claims they are true.
        if isinstance(value, str):
            return cls._text(value, 4000, label)
        if not isinstance(value, dict) or not value:
            raise ServiceError('CANDIDATE_INPUT_INVALID', f'{label}不能为空。', 422)
        try:
            encoded = encode(value)
            if len(encoded) > 12000:
                raise ValueError('note too long')
            json.loads(encoded)
            encoded.encode('utf-8')
        except (ValueError, TypeError, UnicodeError):
            raise ServiceError('CANDIDATE_INPUT_INVALID', f'{label}格式或长度无效。', 422)
        return json.loads(encoded)

    @staticmethod
    def _id(candidate_id):
        if not isinstance(candidate_id, str):
            raise ServiceError('CANDIDATE_ID_INVALID', '候选素材ID必须为UUID。', 422)
        try:
            valid = str(uuid.UUID(candidate_id)) == candidate_id
        except ValueError:
            valid = False
        if not valid:
            raise ServiceError('CANDIDATE_ID_INVALID', '候选素材ID必须为标准UUID。', 422)
        return candidate_id

    @staticmethod
    def _public(content):
        return {key: value for key, value in content.items() if key not in HIDDEN_FIELDS}

    @staticmethod
    def _locks():
        return {'characterId': None, 'assetId': None, 'sourceTaskId': None,
                'accepted': False, 'acceptedAt': None, 'imageAccepted': False,
                'modelEligible': False, 'modelCreated': False,
                'cultureAlignmentVerified': False, 'sourceVerified': False,
                'licenseVerified': False, 'commercialUseVerified': False,
                'publicRedistributionVerified': False,
                'status': 'PENDING_CHARACTER_ASSOCIATION_AND_REVIEW'}

    def _save(self, content, scope, *, force_version=None):
        signature = canonical_hash({'scope': scope, 'content': content})
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT content_json FROM concept_candidates WHERE signature=?', (signature,)).fetchone()
            if old:
                return self._public(json.loads(old[0]))
            highest = db.execute('SELECT MAX(version) FROM concept_candidates WHERE scope=?', (scope,)).fetchone()[0]
            version = (highest or 0) + 1
            if force_version is not None:
                if highest is not None:
                    raise ServiceError('CANDIDATE_HISTORY_CONFLICT', '候选版本已存在，不能补写或覆盖原历史。', 409)
                version = force_version
            saved = {**content, 'candidateId': str(uuid.uuid4()), 'scope': scope,
                     'version': version, 'createdAt': now()}
            db.execute('INSERT INTO concept_candidates VALUES (?,?,?,?,?,?)',
                       (saved['candidateId'], scope, version, signature, encode(saved), saved['createdAt']))
        return self._public(saved)

    def register(self, raw, mime, scope, sourceNote, licenseNote, promptSnapshot,
                 sourcePathLabel=None, styleMode='chibi'):
        scope = self._text(scope, 160, '候选用途范围')
        if styleMode not in ('chibi', 'realistic'):
            raise ServiceError('CANDIDATE_STYLE_INVALID', '候选风格须为Q版或写实。', 422)
        source_note, license_note = self._note(sourceNote, '来源说明'), self._note(licenseNote, '许可说明')
        if not isinstance(promptSnapshot, dict):
            raise ServiceError('CANDIDATE_PROMPT_INVALID', '候选Prompt快照必须为字典。', 422)
        version = self._text(promptSnapshot.get('version'), 160, '候选Prompt版本')
        text = self._text(promptSnapshot.get('text'), 12000, '候选Prompt内容')
        # Explicitly bounded additional snapshot fields; authority fields supplied
        # by a caller are overwritten, never treated as approval or culture facts.
        prompt = self._note(promptSnapshot, '候选Prompt快照')
        normalized, image = normalize_image(raw, mime)
        prompt = {**prompt, 'version': version, 'text': text,
                  'imageHash': image['hash'], 'sourceHash': image['sourceHash'],
                  'styleMode': styleMode, 'frozenForReview': True,
                  'approved': False, 'approvedAt': None,
                  'culturalApproval': False, 'characterId': None,
                  'sourceTaskId': None, 'snapshotKind': 'unassociated_candidate_only'}
        prompt.pop('promptHash', None)
        prompt['promptHash'] = canonical_hash(prompt)
        original_path_label = None if sourcePathLabel is None else self._text(sourcePathLabel, 1000, '原路径标签')
        content = {'candidateSchemaVersion': '1.0', 'styleMode': styleMode,
                   **image, 'originalSize': len(raw), 'originalMimeType': mime,
                   'sourceNote': source_note, 'licenseNote': license_note,
                   'licenseStatus': 'unverified_new_image',
                   'promptSnapshot': prompt, **self._locks(),
                   'sourcePathLabel': original_path_label, 'filesAvailable': True,
                   'storageKey': self.assets.save_bytes('candidate-images', normalized, image['hash'], 'png'),
                   'originalStorageKey': self.assets.save_bytes('candidate-originals', raw, image['sourceHash'], 'upload')}
        return self._save(content, scope)

    def import_history(self, metadata, scope):
        """Preserve an old audit snapshot without pretending its bytes survived.

        A same-path replacement cannot recover the earlier file. Historical
        file reads remain unavailable even if an unrelated new file is present.
        """
        scope = self._text(scope, 160, '候选用途范围')
        old = self._note(metadata, '历史候选元数据')
        source_hash = old.get('sha256', old.get('sourceHash'))
        if not isinstance(source_hash, str) or not re.fullmatch(r'[a-f0-9]{64}', source_hash):
            raise ServiceError('CANDIDATE_HISTORY_INVALID', '历史候选缺少真实SHA-256。', 422)
        style = old.get('styleMode', 'chibi')
        if style not in ('chibi', 'realistic'):
            raise ServiceError('CANDIDATE_STYLE_INVALID', '历史候选风格无效。', 422)
        content = {'candidateSchemaVersion': '1.0', 'styleMode': style,
                   'sourceHash': source_hash, 'hash': None, 'mimeType': None,
                   'originalSize': old.get('size'), 'width': old.get('width'), 'height': old.get('height'),
                   'sourceNote': old.get('source', '历史来源尚待核实'),
                   'licenseNote': old.get('licenseStatement', '历史许可尚待核实'),
                   'licenseStatus': old.get('licenseStatus', 'unverified'),
                   'promptSnapshot': None, **self._locks(),
                   'filesAvailable': False, 'historicalMetadata': old,
                   'historicalRecordedAt': old.get('recordedAt'),
                   'fileUnavailableReason': '原路径已替换，旧版本图片字节未保存；不得回读当前原路径冒充旧图。'}
        return self._save(content, scope, force_version=1)

    def _record(self, candidate_id):
        candidate_id = self._id(candidate_id)
        with self.store.connect() as db:
            row = db.execute('SELECT content_json FROM concept_candidates WHERE candidate_id=?', (candidate_id,)).fetchone()
        if row is None:
            raise ServiceError('CANDIDATE_NOT_FOUND', '未找到登记的候选概念图。', 404)
        return json.loads(row[0])

    def get(self, candidate_id):
        return self._public(self._record(candidate_id))

    def list(self, scope=None):
        if scope is not None:
            scope = self._text(scope, 160, '候选用途范围')
        with self.store.connect() as db:
            sql = 'SELECT content_json FROM concept_candidates'
            args = ()
            if scope is not None:
                sql += ' WHERE scope=?'
                args = (scope,)
            sql += ' ORDER BY created_at DESC, version DESC LIMIT 100'
            return [self._public(json.loads(row[0])) for row in db.execute(sql, args)]

    def file_path(self, candidate_id, kind='preview'):
        if kind not in ('preview', 'original'):
            raise ServiceError('CANDIDATE_FILE_KIND_INVALID', '候选文件类型无效。', 422)
        item = self._record(candidate_id)
        if item.get('filesAvailable') is not True:
            raise ServiceError('CANDIDATE_FILE_UNAVAILABLE', '旧候选只保留元数据，原图片字节不可用；不读取已被替换的原路径。', 404)
        key = 'storageKey' if kind == 'preview' else 'originalStorageKey'
        digest_key, size_key = ('hash', 'size') if kind == 'preview' else ('sourceHash', 'originalSize')
        directory, suffix = ('candidate-images', 'png') if kind == 'preview' else ('candidate-originals', 'upload')
        digest, storage_key = item.get(digest_key), item.get(key)
        if (not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest)
                or storage_key != f'{directory}/{digest}.{suffix}'):
            raise ServiceError('CANDIDATE_STORAGE_INVALID', '候选文件记录无效，停止预览。', 409)
        path = self.root / storage_key
        resolved = path.resolve()
        if (self.root not in resolved.parents or path.is_symlink() or path.parent.is_symlink()
                or not path.is_file()):
            raise ServiceError('CANDIDATE_FILE_UNAVAILABLE', '候选快照文件不可用，不能回读原路径。', 404)
        if path.stat().st_size != item.get(size_key):
            raise ServiceError('CANDIDATE_FILE_CHANGED', '候选图片长度已变化，停止预览。', 409)
        digest_actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest_actual != digest:
            raise ServiceError('CANDIDATE_FILE_CHANGED', '候选图片Hash已变化，停止预览。', 409)
        return path
