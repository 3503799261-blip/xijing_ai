"""Authoritative local asset service; no network or implicit model generation."""
import hashlib
import os
import re
import tempfile
import uuid
from pathlib import Path
from pydantic import ValidationError
from ..agents.schemas import CharacterDesign, CultureReview
from ..errors import ServiceError
from .schemas import CreateAsset, PromptVersionRequest
from .store import AssetStore
from .visual_prompt import canonical_hash, visual_prompt, prompt_hash
from .validation import normalize_image, validate_glb

PUBLIC_IMAGE = {'imageId', 'assetId', 'hash', 'sourceHash', 'mimeType', 'width', 'height', 'size', 'normalization',
                'provenance', 'licenseNote', 'accepted', 'acceptedAt', 'promptHash', 'assetVersion', 'createdAt',
                'characterId', 'styleMode', 'styleVersion'}
PUBLIC_MODEL = {'modelId', 'assetId', 'hash', 'size', 'format', 'origin', 'licenseNote', 'title', 'validation',
                'sourceResultHash', 'citationHash', 'assetVersion', 'createdAt', 'providerTaskId', 'imageId', 'imageHash',
                'characterId', 'styleMode', 'styleVersion'}


class AssetService:
    def __init__(self, settings, task_store):
        self.settings, self.task_store = settings, task_store
        self.root = (Path(settings.rag_data_dir) / 'assets').resolve()
        self.store = AssetStore(self.root)
        self.usage = None
        self.model_service = None

    def authoritative_result(self, task_id):
        status = self.task_store.status(task_id)
        if (status['state'] != 'completed' or status['completedSteps'] != 4
                or {agent['id'] for agent in status['agents']} != {'planner', 'researcher', 'designer', 'reviewer'}
                or any(agent['state'] != 'completed' for agent in status['agents'])):
            raise ServiceError('CHARACTER_NOT_CONFIRMED', '仅能使用四Agent完成并经人工确认的角色方案。', 409)
        result = self.task_store.result(task_id)
        if (result.get('userConfirmed') is not True or result.get('publicationAllowed') is not True
                or result.get('uncertain') is not False or result.get('taskId') != task_id
                or result.get('schemaVersion') != '1.0'):
            raise ServiceError('CHARACTER_NOT_CONFIRMED', '角色确认或文化依据状态不满足资产创建要求。', 409)
        try:
            design = CharacterDesign.model_validate(result.get('design')).model_dump()
            review = CultureReview.model_validate(result.get('review')).model_dump()
        except ValidationError:
            raise ServiceError('CHARACTER_SCHEMA_INVALID', '角色方案不符合已验收的Phase 3协议。', 422)
        if review['verdict'] != 'pass':
            raise ServiceError('CULTURE_REVIEW_REQUIRED', '文化审校尚未通过，不能创建角色资产。', 409)
        citations = result.get('citations')
        fields = {'id', 'title', 'sourceId', 'locator', 'url', 'excerpt', 'contentKind'}
        if not isinstance(citations, list) or not citations or len(citations) > 10:
            raise ServiceError('ASSET_EVIDENCE_INVALID', '角色缺少可追溯的文化引用。', 422)
        if any(not isinstance(item, dict) or not fields.issubset(item)
               or any(not isinstance(item[field], str) or not item[field].strip() for field in fields)
               for item in citations):
            raise ServiceError('ASSET_EVIDENCE_INVALID', '文化引用格式不完整。', 422)
        ids = {item['id'] for item in citations}
        references = list(design['usedEvidenceIds']) + list(review['checkedEvidenceIds'])
        for key in ('costume', 'colors', 'visualElements'):
            for element in design[key]:
                references += element['evidenceIds']
                if element['interpretation'] == 'evidence_based' and not element['evidenceIds']:
                    raise ServiceError('ASSET_EVIDENCE_INVALID', '文化依据元素缺少引用。', 422)
        if len(ids) != len(citations) or not set(references).issubset(ids):
            raise ServiceError('ASSET_EVIDENCE_INVALID', '角色引用不能对应实际任务中的来源。', 422)
        citations = [{key: item[key] for key in fields} for item in citations]
        return result, design, review, citations

    def create_character(self, data):
        data = data if isinstance(data, CreateAsset) else CreateAsset.model_validate(data)
        source, design, review, citations = self.authoritative_result(data.sourceTaskId)
        metadata = data.model_dump(exclude_none=True)
        snapshot = {'design': design, 'review': review, 'citations': citations,
                    'taskId': data.sourceTaskId, 'knowledgeGeneration': source.get('knowledgeGeneration'),
                    'promptVersions': source.get('promptVersions', {}), 'schemaVersion': '1.0'}
        source_hash = canonical_hash(snapshot)
        content = {'assetSchemaVersion': '1.1', 'version': 1, 'styleVersion': 1, **metadata, 'name': design['name'],
                   'characterId': self.character_id(data.sourceTaskId, source_hash),
                   'culturalReviewRequired': False, 'parentAssetId': None,
                   'sourceResultHash': source_hash, 'characterSnapshot': design, 'reviewSnapshot': review,
                   'citationSnapshot': citations, 'citationHash': canonical_hash(citations),
                   'knowledgeGeneration': source.get('knowledgeGeneration'),
                   'promptVersions': source.get('promptVersions', {}),
                   'characterConfirmation': {'userConfirmed': True, 'taskSequence': self.task_store.status(data.sourceTaskId)['lastSequence']},
                   'visualPrompt': visual_prompt(design, data.styleMode), 'commercialRightsVerified': False}
        saved = self.store.create(content, canonical_hash({'sourceResultHash': source_hash, 'metadata': metadata}))
        return self.get_character(saved['assetId'])

    def verify_character_snapshot(self, asset_id):
        """Reject source changes instead of silently keeping an earlier approval."""
        asset = self.style_defaults(self.store.get(asset_id))
        source, design, review, citations = self.authoritative_result(asset['sourceTaskId'])
        snapshot = {'design': design, 'review': review, 'citations': citations,
                    'taskId': asset['sourceTaskId'], 'knowledgeGeneration': source.get('knowledgeGeneration'),
                    'promptVersions': source.get('promptVersions', {}), 'schemaVersion': '1.0'}
        if (canonical_hash(snapshot) != asset['sourceResultHash'] or design != asset['characterSnapshot']
                or review != asset['reviewSnapshot'] or citations != asset['citationSnapshot']
                or canonical_hash(citations) != asset['citationHash']):
            raise ServiceError('ASSET_SOURCE_CHANGED', '原角色或文化引用版本已变化，旧资产批准不能继续用于建模。', 409)
        return self.get_character(asset_id)

    def get_character(self, asset_id):
        return {**self.style_defaults(self.store.get(asset_id)), 'images': [self.public_image(item) for item in self.store.files('image', asset_id)],
                'models': [self.public_model(item) for item in self.store.files('model', asset_id)]}

    def list_characters(self, character_id=None, source_task_id=None, mode=None):
        rows = [self.style_defaults(item) for item in self.store.list()]
        return [self.get_character(item['assetId']) for item in rows
                if (character_id is None or item['characterId'] == character_id)
                and (source_task_id is None or item['sourceTaskId'] == source_task_id)
                and (mode is None or item['mode'] == mode)]

    @staticmethod
    def character_id(task_id, source_hash):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f'xijing-ai:character:{task_id}:{source_hash}'))

    @classmethod
    def style_defaults(cls, asset):
        """Additive legacy read adapter. Never rewrites old approval/file history."""
        mode, version = asset.get('styleMode', 'realistic'), asset.get('styleVersion', asset.get('version', 1))
        if mode not in ('realistic', 'chibi') or type(version) is not int or version < 1:
            raise ServiceError('ASSET_STYLE_INVALID', '资产风格记录无效，请检查原版本。', 409)
        prompt = {**asset['visualPrompt'], 'styleMode': mode, 'styleVersion': version}
        return {**asset, 'styleMode': mode, 'styleVersion': version,
                'characterId': asset.get('characterId') or cls.character_id(asset['sourceTaskId'], asset['sourceResultHash']),
                'culturalReviewRequired': asset.get('culturalReviewRequired', False),
                'parentAssetId': asset.get('parentAssetId'), 'visualPrompt': prompt,
                'legacyStyleDefaultsApplied': 'styleMode' not in asset}

    @staticmethod
    def style_metadata(asset):
        return {key: asset[key] for key in ('characterId', 'styleMode', 'styleVersion')}

    def list_styles(self, asset_id):
        asset = self.get_character(asset_id)
        return {'characterId': asset['characterId'], 'characters': self.list_characters(asset['characterId'])}

    def create_prompt_version(self, asset_id, data):
        data = data if isinstance(data, PromptVersionRequest) else PromptVersionRequest.model_validate(data)
        previous = self.verify_character_snapshot(asset_id)
        old_prompt = previous['visualPrompt']
        if old_prompt['promptHash'] != data.expectedPromptHash:
            raise ServiceError('ASSET_STALE_PROMPT', '原Prompt版本已变化，请重新查看后再编辑。', 409)
        if old_prompt['imagePrompt'] == data.imagePrompt and old_prompt['negativePrompt'] == data.negativePrompt:
            raise ServiceError('ASSET_PROMPT_UNCHANGED', 'Prompt内容未变化，不需要创建新版本。', 409)
        prompt = {**old_prompt, 'imagePrompt': data.imagePrompt, 'negativePrompt': data.negativePrompt,
                  'templateVersion': 'opera_user_visual_draft_v1', 'editableDraft': True,
                  'approved': False, 'approvedAt': None}
        prompt['promptHash'] = prompt_hash(prompt)
        ignored = {'assetId', 'createdAt', 'images', 'models', 'legacyStyleDefaultsApplied'}
        content = {key: value for key, value in previous.items() if key not in ignored}
        content.update(assetSchemaVersion='1.1', parentAssetId=previous['assetId'], visualPrompt=prompt,
                       culturalReviewRequired=True,
                       culturalReviewReason='自由编辑可能增加或改变文化表达；此版本仅为草稿。请由现有Agent重新审校并确认新任务，再登记资产。',
                       version=previous['version'] + 1, styleVersion=previous['styleVersion'] + 1)
        signature = canonical_hash({'operation': 'prompt-version-v1', 'parentAssetId': asset_id,
                                    'expectedPromptHash': data.expectedPromptHash,
                                    'imagePrompt': data.imagePrompt, 'negativePrompt': data.negativePrompt})
        saved = self.store.create(content, signature)
        return self.get_character(saved['assetId'])

    def approve_visual(self, asset_id, prompt_hash):
        asset = self.get_character(asset_id)
        if asset['culturalReviewRequired']:
            raise ServiceError('CULTURAL_REVIEW_REQUIRED', '自由编辑版本尚需Agent文化审校和新任务确认，不能仅凭视觉确认用于生成。', 409)
        self.store.approve_visual(asset_id, prompt_hash)
        return self.get_character(asset_id)

    @staticmethod
    def license_note(value):
        if not isinstance(value, str) or not value.strip() or len(value) > 1000 or any(ord(c) < 32 and c not in '\n\t' for c in value):
            raise ServiceError('ASSET_LICENSE_REQUIRED', '必须提供实际来源与使用许可说明，最多1000字。', 422)
        return value.strip()

    def save_bytes(self, kind, raw, digest, suffix):
        directory = self.root / kind
        directory.mkdir(parents=True, exist_ok=True)
        if self.root not in directory.resolve().parents or directory.is_symlink():
            raise ServiceError('ASSET_STORAGE_INVALID', '资产目录结构无效，未保存文件。', 409)
        destination = directory / f'{digest}.{suffix}'
        # Only our generated hash filenames reach the filesystem; never a caller path.
        with tempfile.NamedTemporaryFile(prefix='asset-', suffix='.part', dir=directory, delete=False) as temporary:
            temporary.write(raw)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        try:
            os.replace(temporary_path, destination)
        finally:
            temporary_path.unlink(missing_ok=True)
        return f'{kind}/{digest}.{suffix}'

    def upload_image(self, asset_id, raw, mime, provenance, license_note):
        asset = self.style_defaults(self.store.get(asset_id))
        if asset['culturalReviewRequired']:
            raise ServiceError('CULTURAL_REVIEW_REQUIRED', '此Prompt草稿尚未完成新的文化审校，不能用于概念图登记。', 409)
        if not asset['visualPrompt']['approved']:
            raise ServiceError('VISUAL_APPROVAL_REQUIRED', '请先人工确认视觉Prompt，再上传概念图。', 409)
        if provenance not in ('manual_image', 'imported_ai_image'):
            raise ServiceError('IMAGE_PROVENANCE_INVALID', '须如实标记授权图片或外部AI工具生成图片。', 422)
        note = self.license_note(license_note)
        image, metadata = normalize_image(raw, mime)
        metadata.update(storageKey=self.save_bytes('images', image, metadata['hash'], 'png'),
                        originalStorageKey=self.save_bytes('original-images', raw, metadata['sourceHash'], 'upload'),
                        provenance=provenance, licenseNote=note, accepted=False, acceptedAt=None,
                        promptHash=asset['visualPrompt']['promptHash'], assetVersion=asset['version'], **self.style_metadata(asset))
        return self.public_image(self.store.add_file('image', asset_id, metadata))

    def public_image(self, item):
        style = self.style_metadata(self.style_defaults(self.store.get(item['assetId'])))
        return {**style, **{key: value for key, value in item.items() if key in PUBLIC_IMAGE},
                'fileUrl': f"/api/v1/assets/images/{item['imageId']}/file"}

    def get_image(self, image_id):
        return self.public_image(self.store.file('image', image_id))

    def accept_image(self, image_id, image_hash):
        # Integrity remains a server check, not a trusted browser assertion.
        self.file_path('image', image_id)
        return self.public_image(self.store.accept_image(image_id, image_hash))

    def import_model(self, asset_id, raw, license_note):
        asset = self.style_defaults(self.store.get(asset_id))
        note = self.license_note(license_note)
        validation = validate_glb(raw)
        metadata = {'hash': validation['hash'], 'size': len(raw), 'format': 'glb', 'origin': 'licensed_import',
                    'licenseNote': note, 'title': asset['name'], 'validation': validation,
                    'sourceResultHash': asset['sourceResultHash'], 'citationHash': asset['citationHash'],
                    'assetVersion': asset['version'], **self.style_metadata(asset),
                    'storageKey': self.save_bytes('models', raw, validation['hash'], 'glb')}
        return self.public_model(self.store.add_file('model', asset_id, metadata))

    def register_fixture(self, raw, license_note, title='本地合法GLB测试夹具（非Neural4D生成）'):
        note, validation = self.license_note(license_note), validate_glb(raw)
        existing = [item for item in self.store.files('model') if item.get('origin') == 'local_test_fixture' and item['hash'] == validation['hash']]
        if existing:
            return self.public_model(existing[0])
        metadata = {'hash': validation['hash'], 'size': len(raw), 'format': 'glb', 'origin': 'local_test_fixture',
                    'title': title, 'licenseNote': note, 'validation': validation,
                    'sourceResultHash': None, 'citationHash': None, 'assetVersion': None,
                    'storageKey': self.save_bytes('models', raw, validation['hash'], 'glb')}
        return self.public_model(self.store.add_file('model', None, metadata))

    def register_generated_model(self, asset_id, image_id, raw, provider_task_id, license_note):
        """Internal provider completion hook; never exposed as a client upload origin."""
        asset = self.style_defaults(self.store.get(asset_id))
        image = self.store.file('image', image_id)
        if (asset['culturalReviewRequired'] or image['assetId'] != asset_id or not image['accepted'] or image['assetVersion'] != asset['version']
                or image['promptHash'] != asset['visualPrompt']['promptHash'] or not asset['visualPrompt']['approved']):
            raise ServiceError('ASSET_GENERATION_INPUT_INVALID', '原建模图片与角色确认版本不匹配。', 409)
        if not isinstance(provider_task_id, str) or not provider_task_id.strip() or len(provider_task_id) > 200:
            raise ServiceError('NEURAL4D_RESPONSE_INVALID', '供应商模型标识无效。', 502)
        self.file_path('image', image_id)
        existing = [item for item in self.store.files('model', asset_id)
                    if item.get('origin') == 'neural4d' and item.get('providerTaskId') == provider_task_id]
        validation = validate_glb(raw)
        if existing:
            if existing[0]['hash'] != validation['hash']:
                raise ServiceError('MODEL_RESULT_CONFLICT', '同一供应商任务返回了不同模型，请人工核查。', 409)
            return self.public_model(existing[0])
        metadata = {'hash': validation['hash'], 'size': len(raw), 'format': 'glb', 'origin': 'neural4d',
                    'licenseNote': self.license_note(license_note), 'title': asset['name'], 'validation': validation,
                    'sourceResultHash': asset['sourceResultHash'], 'citationHash': asset['citationHash'],
                    'assetVersion': asset['version'], 'providerTaskId': provider_task_id,
                    'imageId': image_id, 'imageHash': image['hash'], **self.style_metadata(asset),
                    'storageKey': self.save_bytes('models', raw, validation['hash'], 'glb')}
        return self.public_model(self.store.add_file('model', asset_id, metadata))

    def public_model(self, item):
        style = (self.style_metadata(self.style_defaults(self.store.get(item['assetId']))) if item.get('assetId')
                 else {'characterId': None, 'styleMode': None, 'styleVersion': None})
        return {**style, **{key: value for key, value in item.items() if key in PUBLIC_MODEL},
                'fileUrl': f"/api/v1/assets/models/{item['modelId']}/file",
                'downloadUrl': f"/api/v1/assets/models/{item['modelId']}/download"}

    def get_model(self, model_id):
        return self.public_model(self.store.file('model', model_id))

    def list_models(self, asset_id=None):
        if asset_id is not None:
            self.store.get(asset_id)
        return [self.public_model(item) for item in self.store.files('model', asset_id)]

    def file_path(self, kind, file_id):
        item = self.store.file(kind, file_id)
        pattern = r'images/[a-f0-9]{64}\.png' if kind == 'image' else r'models/[a-f0-9]{64}\.glb'
        storage_key = item.get('storageKey', '')
        if not isinstance(storage_key, str) or not re.fullmatch(pattern, storage_key):
            raise ServiceError('ASSET_STORAGE_INVALID', '资产存储记录不完整，请检查原任务。', 409)
        path = self.root / storage_key
        resolved = path.resolve()
        if self.root not in resolved.parents or path.is_symlink() or not path.is_file():
            raise ServiceError('ASSET_FILE_UNAVAILABLE', '已登记的文件无法读取，请检查本地资产。', 404)
        if path.stat().st_size != item['size']:
            raise ServiceError('ASSET_FILE_CHANGED', '资产文件长度已变化，已停止加载。', 409)
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            while block := stream.read(1024 * 1024):
                digest.update(block)
        if digest.hexdigest() != item['hash']:
            raise ServiceError('ASSET_FILE_CHANGED', '资产文件Hash已变化，已停止加载。', 409)
        return path

    def usage_summary(self):
        summary = self.usage.summary() if self.usage is not None else {'max_calls': 3, 'used_calls': None, 'remaining_calls': None, 'history_verified': False}
        configured = bool(getattr(self.settings, 'neural4d_api_key', None) and self.settings.neural4d_api_key.get_secret_value())
        return {**summary, 'max_calls': 3, 'used_calls': summary.get('occupied_attempts'), 'remaining_calls': summary.get('remaining_attempts'),
                'history_verified': summary.get('historicalUsageVerified', False),
                'realEnabled': bool(self.model_service and self.model_service.available()), 'providerConfigured': configured,
                'protocolVerified': bool(getattr(self.settings, 'neural4d_protocol_verified', False)),
                'readiness': ['真实建模默认关闭；本次开发授权不等于单次真实建模授权。', '需逐次人工确认、后端鉴权、费用及已核实的历史额度。'],
                'imageGenerationConfigured': False}

    def require_model_service(self):
        if self.model_service is None:
            raise ServiceError('NEURAL4D_GENERATION_DISABLED', '真实建模尚未获单次授权，未向供应商发送请求。', 403)
        return self.model_service
