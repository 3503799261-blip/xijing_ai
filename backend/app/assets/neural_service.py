"""Human-gated asset orchestration, isolated from RAG and Agent execution."""
import hashlib
import hmac
import json
import math
import time
import portalocker
from ..errors import ServiceError
from ..providers.neural4d import Neural4DProvider, parameters_for_style
from .validation import validate_glb
from .visual_prompt import canonical_hash
from .technical_test import freeze_technical_candidate, technical_image_path, register_technical_model


class ModelService:
    def __init__(self, settings, assets, usage, transport=None):
        self.settings, self.assets, self.usage = settings, assets, usage
        self.provider = Neural4DProvider(settings, usage, transport)
        self.owner = None
        self.verified_until = 0
        self.balance = None
        with self.assets.store.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS neural4d_frozen_approvals (approval_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS neural4d_query_limits (job_id TEXT PRIMARY KEY, last_query REAL NOT NULL, series_start REAL NOT NULL, series_count INTEGER NOT NULL, total_count INTEGER NOT NULL)')

    def start(self):
        lock = portalocker.Lock(str(self.usage.path.with_suffix('.owner.lock')), timeout=0)
        try:
            lock.acquire()
            self.usage.recover()
            self.owner = lock
        except portalocker.exceptions.LockException:
            self.owner = None
        except Exception:
            lock.release()
            raise

    def close(self):
        if self.owner:
            self.owner.release()
            self.owner = None

    def authorize(self, token):
        expected = self.settings.neural4d_admin_token.get_secret_value()
        if len(expected) < 24 or not isinstance(token, str) or not hmac.compare_digest(expected.encode('utf-8'), token.encode('utf-8')):
            raise ServiceError('ASSET_AUTH_REQUIRED', '供应商操作需要独立的本地管理授权。', 403)

    def verified(self):
        return bool(self.provider.configured and self.settings.neural4d_protocol_verified and self.owner and
                    time.monotonic() < self.verified_until and isinstance(self.balance, (int, float)))

    def available(self):
        state = self.usage.summary()
        return bool(self.settings.neural4d_generation_enabled and self.verified() and state.get('historicalUsageVerified') and not state.get('creationHalted') and not state.get('creationPaused') and
                    (state.get('remaining_attempts') or 0) > 0 and self.settings.neural4d_expected_credits and
                    self.balance >= self.settings.neural4d_expected_credits)

    async def verify(self):
        if not self.settings.neural4d_protocol_verified:
            raise ServiceError('NEURAL4D_PROTOCOL_UNVERIFIED', '余额响应协议尚未核验，未发出供应商请求。', 403)
        data = await self.provider.read_operation('queryPointsInfo', {}, 'verify')
        value = data.get('data', {}).get('total_points') if isinstance(data.get('data'), dict) else None
        # Accept only the documented numeric balance, never treat HTTP200 as permission.
        if type(data.get('statusType')) is not int or data['statusType'] != 0 or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ServiceError('NEURAL4D_BALANCE_UNVERIFIED', '余额响应不能确认，保持真实创建关闭。', 502)
        self.balance, self.verified_until = value, time.monotonic() + 3600
        return {'authenticated': True, 'balanceCredits': value, 'creationPermissionVerified': False,
                'realEnabled': self.settings.neural4d_generation_enabled}

    def require_latest_version(self, asset):
        """Use the same version branch as AssetStore's atomic prompt edits.

        Read the complete catalog rather than the public, limited asset list.
        A new draft invalidates unsent approvals for its branch while keeping
        other styles/use contexts and historical jobs independently traceable.
        """
        fields = ('sourceTaskId', 'sourceResultHash', 'mode', 'purpose', 'enterpriseBrief')
        current = max(asset.get('version', 1), asset.get('styleVersion', 1))
        with self.assets.store.connect() as db:
            for row in db.execute('SELECT content_json FROM character_assets'):
                candidate = json.loads(row[0])
                if (candidate.get('styleMode', 'realistic') != asset.get('styleMode', 'realistic')
                        or any(candidate.get(field) != asset.get(field) for field in fields)):
                    continue
                versions = (candidate.get('version', 1), candidate.get('styleVersion', 1))
                if any(type(version) is not int or version < 1 for version in versions):
                    raise ServiceError('NEURAL4D_APPROVAL_STALE', '角色分支版本记录无效，禁止提交，请先核查。', 409)
                if max(versions) > current:
                    raise ServiceError('NEURAL4D_APPROVAL_STALE', '同风格和用途已有新Prompt版本，旧的未发送批准失效，请审校并重新确认。', 409)

    def freeze(self, data):
        asset = self.assets.get_character(data['assetId'])
        if asset.get('culturalReviewRequired') is True or asset['visualPrompt'].get('culturalReviewRequired') is True:
            raise ServiceError('ASSET_CULTURAL_REVIEW_REQUIRED', '自由编辑的Prompt尚需真实Agent审校和新角色确认，禁止真实建模。', 409)
        style_mode = asset.get('styleMode', 'realistic')
        style_version = asset.get('styleVersion', 1)
        character_id = asset.get('characterId')
        parameters = parameters_for_style(style_mode)
        if (type(style_version) is not int or style_version < 1
                or not isinstance(character_id, str) or not character_id.strip()
                or (data.get('styleVersion') is not None and type(data['styleVersion']) is not int)
                or any(data.get(field) is not None and data[field] != value
                       for field, value in [('styleMode', style_mode), ('styleVersion', style_version), ('characterId', character_id)])):
            raise ServiceError('NEURAL4D_INPUT_CHANGED', '角色、风格或风格版本不一致，请重新查看后确认。', 409)
        self.require_latest_version(asset)
        # Always recheck authoritative Phase 3, rather than trusting a browser snapshot.
        source, design, review, citations = self.assets.authoritative_result(asset['sourceTaskId'])
        current_hash = canonical_hash({'design': design, 'review': review, 'citations': citations,
            'taskId': asset['sourceTaskId'], 'knowledgeGeneration': source.get('knowledgeGeneration'),
            'promptVersions': source.get('promptVersions', {}), 'schemaVersion': '1.0'})
        if current_hash != asset['sourceResultHash']:
            raise ServiceError('NEURAL4D_INPUT_CHANGED', '原角色方案或文化依据版本已变化，必须重新确认。', 409)
        image = self.assets.get_image(data['imageId'])
        if (data['modelCount'] != 1 or asset['version'] != data['assetVersion'] or
                asset['purpose'] != data['purpose'] or asset['visualPrompt']['promptHash'] != data['promptHash'] or
                not asset['visualPrompt']['approved'] or image['assetId'] != asset['assetId'] or
                not image['accepted'] or image['hash'] != data['imageHash'] or image['promptHash'] != data['promptHash']
                or image.get('styleMode', style_mode) != style_mode
                or image.get('styleVersion', style_version) != style_version
                or image.get('characterId', character_id) != character_id):
            raise ServiceError('NEURAL4D_INPUT_CHANGED', '资产、用途、概念图或确认版本不一致，未发出请求。', 409)
        self.assets.file_path('image', data['imageId'])
        return {'modelCount': 1, 'parameters': parameters, 'assetId': asset['assetId'], 'assetVersion': asset['version'],
                'characterId': character_id, 'styleMode': style_mode, 'styleVersion': style_version,
                'sourceResultHash': asset['sourceResultHash'], 'citationHash': asset['citationHash'],
                'imageId': image['imageId'], 'imageHash': image['hash'], 'promptHash': image['promptHash'], 'purpose': data['purpose']}

    def approve(self, data):
        if not self.available():
            raise ServiceError('NEURAL4D_GENERATION_DISABLED', '真实建模门禁未通过；需要单次批准、已核实费用、鉴权与历史额度。', 403)
        if data.get('action') != 'accept' or data.get('estimatedCredits') != self.settings.neural4d_expected_credits:
            raise ServiceError('NEURAL4D_COST_UNVERIFIED', '本次费用或人工确认不匹配。', 409)
        payload = self.freeze(data)
        result = self.usage.approve(payload, data['purpose'], confirmed=True, estimated_credits=data['estimatedCredits'])
        with self.assets.store.connect() as db:
            db.execute('INSERT INTO neural4d_frozen_approvals VALUES (?,?)', (result['approvalId'], json.dumps(payload, ensure_ascii=False, sort_keys=True)))
        return result

    def approve_technical_candidate(self, data):
        """Trusted local orchestration only; never a browser approval schema.

        This scoped exception has no Phase 3 cultural identity or publication
        approval. Quota, verification, cost and the one-shot send remain shared.
        """
        if not self.available():
            raise ServiceError('NEURAL4D_GENERATION_DISABLED', '内部验证仍须鉴权、余额、已核实费用与全局历史额度。', 403)
        if data.get('action') != 'accept' or data.get('estimatedCredits') != self.settings.neural4d_expected_credits:
            raise ServiceError('NEURAL4D_COST_UNVERIFIED', '内部验证的单次费用或确认不匹配。', 409)
        payload = freeze_technical_candidate(self.assets, data)
        result = self.usage.approve(payload, payload['purpose'], confirmed=True, estimated_credits=data['estimatedCredits'])
        with self.assets.store.connect() as db:
            db.execute('INSERT INTO neural4d_frozen_approvals VALUES (?,?)',
                       (result['approvalId'], json.dumps(payload, ensure_ascii=False, sort_keys=True)))
        return result

    def approval_payload(self, approval_id):
        with self.assets.store.connect() as db:
            row = db.execute('SELECT payload_json FROM neural4d_frozen_approvals WHERE approval_id=?', (approval_id,)).fetchone()
        if not row:
            raise ServiceError('NEURAL4D_APPROVAL_NOT_FOUND', '本次批准不存在，不能创建任务。', 404)
        return json.loads(row[0])

    async def submit(self, data, key):
        if data.get('modelCount') != 1 or not self.settings.neural4d_generation_enabled or not self.verified():
            raise ServiceError('NEURAL4D_GENERATION_DISABLED', '真实建模未获有效单次授权，未发出请求。', 403)
        payload = self.approval_payload(data['approvalId'])
        # Never silently reinterpret an older one-shot approval using a new
        # mesh preset or a newly introduced style/version label.
        if not all(field in payload for field in ('styleMode', 'styleVersion', 'characterId')):
            raise ServiceError('NEURAL4D_APPROVAL_STALE', '旧批准未绑定风格和角色版本，请重新确认；未发送建模请求。', 409)
        previous = self.usage.lookup_replay(key, data['approvalId'], payload, payload['purpose'])
        if previous and previous['startedAt'] is not None:
            # Replay is a read of the original task, never a new send. Its old
            # version remains valid provenance after later prompt edits.
            return self.public(previous)
        if self.usage.approval_estimated_credits(data['approvalId']) != self.settings.neural4d_expected_credits:
            raise ServiceError('NEURAL4D_COST_CHANGED', '本次预计Credit费用已变化，请重新核实费用并明确确认；未发出建模请求。', 409)
        if not self.settings.neural4d_expected_credits or self.balance < self.settings.neural4d_expected_credits:
            raise ServiceError('NEURAL4D_GENERATION_DISABLED', '本次预计费用或已核验余额不满足条件，未发出请求。', 403)
        technical = payload.get('assetKind') == 'internal_technical_test'
        current = freeze_technical_candidate(self.assets, payload) if technical else self.freeze({**payload, 'assetVersion': payload['assetVersion']})
        if current != payload:
            raise ServiceError('NEURAL4D_INPUT_CHANGED', '批准后资产已变化。', 409)
        raw = (technical_image_path(self.assets, payload) if technical else
               self.assets.file_path('image', payload['imageId'])).read_bytes()
        if hashlib.sha256(raw).hexdigest() != payload['imageHash']:
            raise ServiceError('NEURAL4D_INPUT_CHANGED', '图片Hash不匹配。', 409)
        record = self.usage.reserve(key, data['approvalId'], payload, payload['purpose'], real_enabled=True, provider_verified=True)
        if record['newlyReserved']:
            record = await self.provider.create_once(record['attemptId'], raw)
        return self.public(record)

    def public(self, record):
        payload = self.usage.frozen_payload(record['attemptId'])
        # No provider secrets or storage paths; only the server-frozen variant
        # identifiers needed to display the selected model's actual lineage.
        style = {field: payload.get(field) for field in ('characterId', 'styleMode', 'styleVersion', 'assetId', 'assetVersion',
                                                       'assetKind', 'candidateId', 'candidateVersion', 'internalUseOnly')}
        return {**record, **style, 'jobId': record['attemptId'], 'modelCount': 1, 'modelUrl': None, 'downloadUrl': None}

    def status(self, job_id):
        return self.public(self.usage.get_attempt(job_id))

    def claim_query(self, job_id):
        now = time.time()
        with self.assets.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM neural4d_query_limits WHERE job_id=?', (job_id,)).fetchone()
            if row:
                if now - row['last_query'] < 15:
                    raise ServiceError('NEURAL4D_QUERY_TOO_SOON', '请至少间隔15秒再主动查询。', 429)
                if row['series_count'] >= 20 or now - row['series_start'] >= 1200:
                    raise ServiceError('NEURAL4D_QUERY_CONFIRMATION_REQUIRED', '本轮查询已达20次或20分钟，请人工确认继续查询。', 409)
                db.execute('UPDATE neural4d_query_limits SET last_query=?,series_count=series_count+1,total_count=total_count+1 WHERE job_id=?', (now, job_id))
            else:
                db.execute('INSERT INTO neural4d_query_limits VALUES (?,?,?,1,1)', (job_id, now, now))

    def continue_queries(self, job_id):
        self.usage.get_attempt(job_id)
        with self.assets.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE neural4d_query_limits SET series_start=?,series_count=0 WHERE job_id=?', (time.time(), job_id))
        return {'jobId': job_id, 'queryContinuationAccepted': True, 'automaticPolling': False}

    async def refresh(self, job_id):
        record = self.usage.get_attempt(job_id)
        if not record['providerTaskId']:
            raise ServiceError('NEURAL4D_RECONCILIATION_REQUIRED', '没有可靠供应商任务ID，请先人工核查，不能自动重建。', 409)
        if not self.settings.neural4d_protocol_verified:
            raise ServiceError('NEURAL4D_PROTOCOL_UNVERIFIED', '查询协议尚未核验。', 403)
        self.claim_query(job_id)
        try:
            result = await self.provider.read_operation('retrieveModel', {'uuid': record['providerTaskId']}, 'query_model', attempt_id=job_id)
        except ServiceError as error:
            self.usage.finish(job_id, 'PENDING_RECONCILIATION', provider_task_id=record['providerTaskId'], error_code=error.code)
            raise
        code = result.get('codeStatus')
        if type(code) is not int:
            self.usage.finish(job_id, 'PENDING_RECONCILIATION', provider_task_id=record['providerTaskId'], error_code='NEURAL4D_STATUS_INVALID')
            raise ServiceError('NEURAL4D_RECONCILIATION_REQUIRED', '供应商状态类型无效，请人工核查。', 502)
        if code == 1:
            self.usage.finish(job_id, 'PROCESSING', provider_task_id=record['providerTaskId'])
        elif code == 0:
            try:
                raw = await self.provider.download(result.get('modelUrl', ''), attempt_id=job_id)
                payload = self.approval_payload(record['approvalId'])
                item = (register_technical_model(self.assets, payload, raw, record['providerTaskId'])
                        if payload.get('assetKind') == 'internal_technical_test' else
                        self.assets.register_generated_model(payload['assetId'], payload['imageId'], raw, record['providerTaskId'],
                            '供应商输出；商业使用需另行核查供应商条款和输入许可。'))
            except ServiceError as error:
                self.usage.finish(job_id, 'PENDING_RECONCILIATION', provider_task_id=record['providerTaskId'], error_code=error.code)
                raise
            self.usage.finish(job_id, 'SUCCEEDED', provider_task_id=record['providerTaskId'])
            return {**self.status(job_id), 'model': item}
        elif code == -3:
            self.usage.finish(job_id, 'FAILED', provider_task_id=record['providerTaskId'], error_code='NEURAL4D_MODEL_FAILED')
        else:
            self.usage.finish(job_id, 'PENDING_RECONCILIATION', provider_task_id=record['providerTaskId'], error_code='NEURAL4D_STATUS_UNKNOWN')
            raise ServiceError('NEURAL4D_RECONCILIATION_REQUIRED', '供应商状态不能确认，请人工核查；未创建新任务。', 502)
        return self.status(job_id)
