"""LOCAL ONLY recovery for the exact SECOND, already-created formal model.

No network, provider query or creation is available through this utility. The
diagnosed supplier original stays in private quarantine. Only its two embedded
JPEGs are resized and their invalid MIME labels corrected; geometry, UVs,
materials and scene semantics stay unchanged. The ordinary GLB gate is retained.
"""
import argparse
import copy
import hashlib
import io
import json
import struct
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.agents.store import TaskStore
from backend.app.assets.neural_service import ModelService
from backend.app.assets.service import AssetService
from backend.app.assets.usage import UsageManager
from backend.app.assets.validation import validate_glb
from backend.app.assets.visual_prompt import canonical_hash
from backend.app.config import Settings, WORKSPACE_ROOT
from backend.app.errors import ServiceError

JOB_ID = 'd3367e96-02f9-453b-b331-6ed5b0ec03cd'
TASK_ID = '8735f32e-097e-488c-962f-f11e64af7741'
ASSET_ID = '9e2b42e1-bbad-4a2f-ab1b-aeda18015dee'
IMAGE_ID = '0e1e8d8d-9ab9-43bf-9d36-a4d3c7c1414d'
AGENT_TASK_ID = 'ca7007e7-e535-4b1f-a9b6-1932f10e20b4'
IMAGE_HASH = '7b8fb1a42bf79d0210c1571e65ae92d856fa73761d42d9cd044836764aad4d45'
SOURCE_IMAGE_HASH = '0170077ef813f95b2e0da4666f0a7919078d0a811ac04d61613e69a31a621095'
ORIGINAL_HASH = '51fc687e0bde5fdb9074ba4560601057e17e9239f111fd2bc9e0d6601c26260e'
ORIGINAL_SIZE = 18_266_484
CONVERSION_VERSION = 'second_formal_embedded_jpeg_textures_2048_v1'


def mismatch(message):
    raise ServiceError('RECOVERY_SOURCE_MISMATCH', message, 409)


def normalize_original(raw):
    """Accept only the diagnosed immutable original; return a validated GLB."""
    if hashlib.sha256(raw).hexdigest() != ORIGINAL_HASH or len(raw) != ORIGINAL_SIZE:
        mismatch('只接受已核实的第二次原任务模型Hash和长度。')
    try:
        magic, version, total = struct.unpack_from('<4sII', raw)
        size, kind = struct.unpack_from('<II', raw, 12)
        if (magic != b'glTF' or version != 2 or total != len(raw)
                or kind != 0x4E4F534A or size % 4 or size > 4 * 1024 * 1024):
            mismatch('第二次原任务GLB头部或JSON分块变化。')
        doc = json.loads(raw[20:20 + size])
        offset = 20 + size
        bin_size, bin_kind = struct.unpack_from('<II', raw, offset)
        if bin_kind != 0x004E4942 or bin_size % 4 or offset + 8 + bin_size != len(raw):
            mismatch('第二次原任务BIN分块变化。')
        binary = raw[offset + 8:]
        views, images = doc['bufferViews'], doc['images']
        if (len(views) != 5 or len(images) != 2 or len(doc['meshes']) != 1
                or [image.get('bufferView') for image in images] != [3, 4]
                or any(image.get('mimeType') != 'image/jpg' or 'uri' in image for image in images)
                or len(doc['buffers']) != 1 or doc['buffers'][0].get('uri') is not None):
            mismatch('第二次原任务纹理、网格或缓冲布局变化。')
        for view in views:
            start, length = view.get('byteOffset', 0), view['byteLength']
            if (type(start) is not int or type(length) is not int or start < 0
                    or length <= 0 or start + length > len(binary) or view.get('buffer') != 0):
                mismatch('第二次原任务bufferView范围无效。')
        original_doc = copy.deepcopy(doc)
        replacements, textures = {}, []
        for image in images:
            view_id = image['bufferView']
            view = views[view_id]
            if 'byteStride' in view:
                mismatch('第二次原任务纹理缓冲布局变化。')
            start, length = view.get('byteOffset', 0), view['byteLength']
            before = binary[start:start + length]
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(before)) as decoded:
                    if (decoded.format != 'JPEG' or decoded.size != (4096, 4096)
                            or getattr(decoded, 'n_frames', 1) != 1):
                        mismatch('第二次原任务必须为两张单帧4096像素JPEG。')
                    decoded.load()
                    resized = decoded.convert('RGB').resize((2048, 2048), Image.Resampling.LANCZOS)
                    clean = Image.new('RGB', resized.size)
                    clean.paste(resized)
                    output = io.BytesIO()
                    clean.save(output, 'JPEG', quality=95, subsampling=0)
            replacements[view_id] = output.getvalue()
            image['mimeType'] = 'image/jpeg'
            textures.append({'bufferView': view_id, 'format': 'JPEG',
                'originalDimensions': [4096, 4096], 'derivedDimensions': [2048, 2048],
                'originalHash': hashlib.sha256(before).hexdigest(),
                'derivedHash': hashlib.sha256(replacements[view_id]).hexdigest()})
        out_binary, geometry = bytearray(), []
        for number, view in enumerate(views):
            old = binary[view.get('byteOffset', 0):view.get('byteOffset', 0) + view['byteLength']]
            data = replacements.get(number, old)
            out_binary.extend(b'\0' * (-len(out_binary) % 4))
            view['byteOffset'], view['byteLength'] = len(out_binary), len(data)
            out_binary.extend(data)
            if number not in replacements:
                geometry.append({'bufferView': number, 'hash': hashlib.sha256(old).hexdigest(),
                    'derivedHash': hashlib.sha256(data).hexdigest(), 'byteLength': len(old),
                    'bytesUnchanged': old == data})
        doc['buffers'][0]['byteLength'] = len(out_binary)
        out_binary.extend(b'\0' * (-len(out_binary) % 4))
        # Texture MIME and buffer offsets/lengths are the sole allowed changes.
        semantic_keys = set(original_doc) - {'buffers', 'bufferViews', 'images'}
        if any(doc[key] != original_doc[key] for key in semantic_keys):
            mismatch('本地转换不得改变场景、节点、几何、UV或材质语义。')
        for old, new in zip(original_doc['bufferViews'], views):
            if {key: value for key, value in old.items() if key not in ('byteOffset', 'byteLength')} != {
                    key: value for key, value in new.items() if key not in ('byteOffset', 'byteLength')}:
                mismatch('本地转换不得改变bufferView语义。')
        out_json = json.dumps(doc, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        out_json += b' ' * (-len(out_json) % 4)
        converted = (struct.pack('<4sII', b'glTF', 2, 28 + len(out_json) + len(out_binary))
            + struct.pack('<II', len(out_json), 0x4E4F534A) + out_json
            + struct.pack('<II', len(out_binary), 0x004E4942) + out_binary)
    except ServiceError:
        raise
    except (KeyError, TypeError, ValueError, struct.error, IndexError, OSError,
            Image.DecompressionBombError, Image.DecompressionBombWarning):
        mismatch('第二次原任务不符合已诊断的安全转换范围。')
    validation = validate_glb(converted)
    provenance = {'version': CONVERSION_VERSION, 'supplierOriginalHash': ORIGINAL_HASH,
        'supplierOriginalSize': len(raw), 'derivedHash': validation['hash'], 'derivedSize': len(converted),
        'mimeCorrection': 'image/jpg -> image/jpeg', 'textureOnlyOptimization': True,
        'geometryBufferViews': geometry, 'textures': textures,
        'geometryUnchanged': all(item['bytesUnchanged'] for item in geometry),
        'sceneNodeAccessorMaterialSemanticsUnchanged': True,
        'originalPreserved': True, 'newGeneration': False, 'providerCalls': 0}
    return converted, provenance


class LocalOnlyModelService(ModelService):
    """Keep existing lock/freeze verification while denying all network actions."""
    def approve(self, *args, **kwargs):
        raise ServiceError('LOCAL_RECOVERY_NETWORK_FORBIDDEN', '本地转换不能批准创建任务。', 403)

    def approve_technical_candidate(self, *args, **kwargs):
        raise ServiceError('LOCAL_RECOVERY_NETWORK_FORBIDDEN', '本地转换不能批准内部创建。', 403)

    async def submit(self, *args, **kwargs):
        raise ServiceError('LOCAL_RECOVERY_NETWORK_FORBIDDEN', '本地转换不能提交任务。', 403)

    async def verify(self, *args, **kwargs):
        raise ServiceError('LOCAL_RECOVERY_NETWORK_FORBIDDEN', '本地转换不能查询供应商。', 403)

    async def refresh(self, *args, **kwargs):
        raise ServiceError('LOCAL_RECOVERY_NETWORK_FORBIDDEN', '本地转换不能查询原任务。', 403)


def run(record):
    settings = Settings()
    if settings.neural4d_generation_enabled:
        raise ServiceError('DEFAULT_GENERATION_MUST_BE_OFF', '本地转换要求默认真实创建关闭。', 409)
    usage = UsageManager(WORKSPACE_ROOT / '.runtime/neural4d-usage.sqlite3')
    before = usage.summary()
    record['usageBefore'] = before
    attempt = usage.get_attempt(JOB_ID)
    if (before['historical_used_attempts'] != 0 or before['occupied_attempts'] != 2
            or before['remaining_attempts'] != 1 or attempt['providerTaskId'] != TASK_ID
            or attempt['state'] not in ('PENDING_RECONCILIATION', 'SUCCEEDED')):
        raise ServiceError('RECOVERY_HISTORY_CHANGED', '第二次原任务或全项目额度不匹配，停止转换。', 409)
    assets = AssetService(settings, TaskStore(Path(settings.rag_data_dir) / 'agent-tasks.sqlite3'))
    service = LocalOnlyModelService(settings, assets, usage)
    service.start()
    try:
        if service.owner is None:
            raise ServiceError('SENDER_LOCK_UNAVAILABLE', '本地转换必须取得项目独占管理锁。', 409)
        asset = assets.verify_character_snapshot(ASSET_ID)
        image = assets.get_image(IMAGE_ID)
        payload = service.approval_payload(attempt['approvalId'])
        if (asset['sourceTaskId'] != AGENT_TASK_ID or asset['styleMode'] != 'realistic'
                or image['assetId'] != ASSET_ID or image['hash'] != IMAGE_HASH
                or image['sourceHash'] != SOURCE_IMAGE_HASH or image['accepted'] is not True
                or payload.get('assetId') != ASSET_ID or payload.get('imageId') != IMAGE_ID
                or payload.get('styleMode') != 'realistic' or payload.get('modelCount') != 1
                or payload.get('purpose') != '比赛主展示'
                or usage.frozen_payload(JOB_ID) != payload
                or service.freeze(payload) != payload):
            raise ServiceError('RECOVERY_HISTORY_CHANGED', '正式角色、图片、冻结批准或原任务谱系变化。', 409)
        source = assets.root / 'recovery-quarantine' / (ORIGINAL_HASH + '.bin')
        if source.is_symlink() or assets.root not in source.resolve().parents or not source.is_file():
            mismatch('第二次原任务受控文件缺失或路径无效。')
        raw = source.read_bytes()
        derived, provenance = normalize_original(raw)
        provenance.update(jobId=JOB_ID, providerTaskId=TASK_ID, assetId=ASSET_ID, imageId=IMAGE_ID,
            characterId=asset['characterId'], sourceResultHash=asset['sourceResultHash'],
            citationHash=asset['citationHash'], imageHash=IMAGE_HASH,
            sourceImageHash=SOURCE_IMAGE_HASH, promptHash=payload['promptHash'],
            frozenPayloadHash=canonical_hash(payload))
        provenance_raw = (json.dumps(provenance, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
        provenance_hash = hashlib.sha256(provenance_raw).hexdigest()
        provenance_key = assets.save_bytes('recovery-provenance', provenance_raw, provenance_hash, 'json')
        note = (f'用户声明允许比赛展示、Neural4D上传及3D衍生；非商业销售许可。'
                f'第二次供应商原模型SHA-256={ORIGINAL_HASH}；'
                f'本地纹理转换版本={CONVERSION_VERSION}；仅JPEG MIME与2048纹理优化，几何不变。'
                f'详细谱系SHA-256={provenance_hash}；未产生新建模或费用。')
        model = assets.register_generated_model(ASSET_ID, IMAGE_ID, derived, TASK_ID, note)
        assets.file_path('model', model['modelId'])
        if hashlib.sha256(source.read_bytes()).hexdigest() != ORIGINAL_HASH:
            mismatch('第二次原始文件在转换期间发生变化。')
        usage.finish(JOB_ID, 'SUCCEEDED', provider_task_id=TASK_ID)
        record.update(outcome='LOCAL_RECOVERY_VALIDATED', conversion=provenance, model=model,
            provenanceHash=provenance_hash, provenanceStorageKey=provenance_key,
            frozenPayloadHash=canonical_hash(payload))
    finally:
        after = usage.summary()
        record['usageAfter'] = after
        record['creationAttemptsUnchanged'] = before['occupied_attempts'] == after['occupied_attempts']
        record['realHttpRequestsUnchanged'] = before['realHttpRequests'] == after['realHttpRequests']
        service.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    record = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'kind': 'ACTUAL_SECOND_LOCAL_FORMAT_RECOVERY',
        'jobId': JOB_ID, 'providerTaskId': TASK_ID, 'networkCalls': 0, 'additionalCredits': 0}
    try:
        run(record)
    except ServiceError as error:
        record.update(outcome='STOPPED', errorCode=error.code, message=error.message)
    except Exception:
        record.update(outcome='STOPPED', errorCode='RECOVERY_LOCAL_ERROR',
            message='第二次模型本地转换失败；保留原文件，不创建或查询任务。')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(json.dumps(record, ensure_ascii=True))
    return 0 if record.get('outcome') == 'LOCAL_RECOVERY_VALIDATED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
