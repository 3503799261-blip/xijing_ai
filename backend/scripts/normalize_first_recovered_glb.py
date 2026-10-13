"""LOCAL ONLY: normalize the exact quarantined original task's two textures.

No provider/network code. Preserve original bytes, geometry and task identity;
the existing GLB safety gate remains unchanged. This is a derived technical
asset, not a second model generation and not full Khronos certification.
"""
import argparse
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
from backend.app.assets.service import AssetService
from backend.app.assets.technical_test import register_technical_model
from backend.app.assets.validation import validate_glb
from backend.app.config import Settings, WORKSPACE_ROOT
from backend.app.errors import ServiceError
from backend.app.assets.usage import UsageManager
from backend.app.assets.visual_prompt import canonical_hash
from backend.scripts.recover_first_internal_model import JOB_ID, TASK_ID, RecoveryOnlyService

ORIGINAL_HASH = '8ef5de8a2f96fbbee9eea66737187e4a2087f88867830891a41464a473d47885'
CONVERSION_VERSION = 'first_internal_embedded_textures_2048_v1'


def normalize_original(raw):
    if hashlib.sha256(raw).hexdigest() != ORIGINAL_HASH:
        raise ServiceError('RECOVERY_SOURCE_MISMATCH', '本地转换只接受已核实的原任务模型Hash。', 409)
    # Exact hash binds the diagnosed original GLB and its bounded resource
    # layout; this utility is not an upload endpoint or a generic lax validator.
    size, kind = struct.unpack_from('<II', raw, 12)
    if raw[:4] != b'glTF' or kind != 0x4E4F534A:
        raise ServiceError('MODEL_INVALID', '原任务文件结构变化。', 409)
    doc = json.loads(raw[20:20+size])
    bin_offset = 20 + size
    bin_size, bin_kind = struct.unpack_from('<II', raw, bin_offset)
    if bin_kind != 0x004E4942:
        raise ServiceError('MODEL_INVALID', '原任务缺少BIN数据。', 409)
    binary = raw[bin_offset+8:bin_offset+8+bin_size]
    replacements, texture_report = {}, []
    images = doc['images']
    if len(images) != 2:
        raise ServiceError('RECOVERY_SOURCE_MISMATCH', '原任务纹理数量变化。', 409)
    for image in images:
        view_id = image['bufferView']
        view = doc['bufferViews'][view_id]
        start, length = view.get('byteOffset', 0), view['byteLength']
        before = binary[start:start+length]
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(before)) as decoded:
                if (decoded.format not in ('PNG', 'JPEG') or decoded.size != (4096, 4096)
                        or getattr(decoded, 'n_frames', 1) != 1):
                    raise ServiceError('RECOVERY_SOURCE_MISMATCH', '原任务纹理格式或尺寸变化。', 409)
                decoded.load()
                output_format = decoded.format
                image['mimeType'] = 'image/jpeg' if output_format == 'JPEG' else 'image/png'
                resized = decoded.resize((2048, 2048), Image.Resampling.LANCZOS)
                clean = Image.new(resized.mode, resized.size)
                clean.paste(resized)
                output = io.BytesIO()
                if output_format == 'JPEG':
                    clean.convert('RGB').save(output, 'JPEG', quality=95, subsampling=0)
                else:
                    clean.save(output, 'PNG')
                replacements[view_id] = output.getvalue()
                texture_report.append({'bufferView': view_id, 'format': output_format,
                    'originalDimensions': [4096, 4096], 'derivedDimensions': [2048, 2048],
                    'originalHash': hashlib.sha256(before).hexdigest(),
                    'derivedHash': hashlib.sha256(replacements[view_id]).hexdigest()})
    out_binary, geometry_hashes = bytearray(), []
    for number, view in enumerate(doc['bufferViews']):
        old = binary[view.get('byteOffset', 0):view.get('byteOffset', 0)+view['byteLength']]
        data = replacements.get(number, old)
        out_binary.extend(b'\0' * (-len(out_binary) % 4))
        view['byteOffset'], view['byteLength'] = len(out_binary), len(data)
        out_binary.extend(data)
        if number not in replacements:
            geometry_hashes.append({'bufferView': number, 'hash': hashlib.sha256(old).hexdigest(),
                                    'byteLength': len(old), 'bytesUnchanged': old == data})
    doc['buffers'][0]['byteLength'] = len(out_binary)
    out_binary.extend(b'\0' * (-len(out_binary) % 4))
    out_json = json.dumps(doc, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    out_json += b' ' * (-len(out_json) % 4)
    converted = (struct.pack('<4sII', b'glTF', 2, 12+8+len(out_json)+8+len(out_binary))
                 + struct.pack('<II', len(out_json), 0x4E4F534A) + out_json
                 + struct.pack('<II', len(out_binary), 0x004E4942) + out_binary)
    validation = validate_glb(converted)
    provenance = {'version': CONVERSION_VERSION, 'supplierOriginalHash': ORIGINAL_HASH,
        'supplierOriginalSize': len(raw), 'derivedHash': validation['hash'],
        'derivedSize': len(converted), 'mimeCorrection': 'image/jpg -> image/jpeg',
        'textureOnlyOptimization': True, 'geometryBufferViews': geometry_hashes,
        'textures': texture_report, 'geometryUnchanged': all(item['bytesUnchanged'] for item in geometry_hashes),
        'originalPreserved': True, 'newGeneration': False, 'providerCalls': 0}
    return converted, provenance


def run(record):
    settings = Settings().model_copy(update={'neural4d_generation_enabled': False})
    usage = UsageManager(WORKSPACE_ROOT / '.runtime/neural4d-usage.sqlite3')
    assets = AssetService(settings, None)
    service = RecoveryOnlyService(settings, assets, usage)
    before = usage.summary()
    record['usageBefore'] = before
    attempt = usage.get_attempt(JOB_ID)
    if attempt['providerTaskId'] != TASK_ID or before['occupied_attempts'] != 1:
        raise ServiceError('RECOVERY_HISTORY_CHANGED', '原任务或配额不匹配。', 409)
    service.start()
    try:
        if service.owner is None:
            raise ServiceError('SENDER_LOCK_UNAVAILABLE', '本地资产恢复必须取得原管理锁。', 409)
        source = assets.root / 'recovery-quarantine' / (ORIGINAL_HASH + '.bin')
        if source.is_symlink() or assets.root not in source.resolve().parents or not source.is_file():
            raise ServiceError('RECOVERY_SOURCE_MISMATCH', '原任务受控文件缺失或路径无效。', 409)
        raw = source.read_bytes()
        derived, provenance = normalize_original(raw)
        payload = service.approval_payload(attempt['approvalId'])
        # Original frozen technical lineage is retained. The derived asset's
        # validation metadata explicitly records this local conversion.
        model = register_technical_model(assets, payload, derived, TASK_ID, local_conversion=provenance)
        assets.file_path('model', model['modelId'])
        if hashlib.sha256(source.read_bytes()).hexdigest() != ORIGINAL_HASH:
            raise ServiceError('RECOVERY_SOURCE_MISMATCH', '原文件在处理期间变化。', 409)
        usage.finish(JOB_ID, 'SUCCEEDED', provider_task_id=TASK_ID)
        record.update(outcome='LOCAL_RECOVERY_VALIDATED', conversion=provenance, model=model,
                      frozenPayloadHash=canonical_hash(payload))
    finally:
        record['usageAfter'] = usage.summary()
        record['creationAttemptsUnchanged'] = record['usageAfter']['occupied_attempts'] == before['occupied_attempts']
        service.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    record = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'kind': 'ACTUAL_LOCAL_FORMAT_RECOVERY',
              'jobId': JOB_ID, 'providerTaskId': TASK_ID, 'networkCalls': 0, 'additionalCredits': 0}
    try:
        run(record)
    except ServiceError as error:
        record.update(outcome='STOPPED', errorCode=error.code, message=error.message)
    except Exception:
        record.update(outcome='STOPPED', errorCode='RECOVERY_LOCAL_ERROR', message='本地转换失败；原文件保留，不新建任务。')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', 'utf-8')
    print(json.dumps(record, ensure_ascii=True))
    return 0 if record.get('outcome') == 'LOCAL_RECOVERY_VALIDATED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
