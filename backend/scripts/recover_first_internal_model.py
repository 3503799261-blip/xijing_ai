"""Recover ONLY the previously submitted first model. No creation capability.

URLs remain in memory and are never serialized. Verified storage identity is
exact cos.neural4d.com, as returned by the authenticated original task and TLS
check. Every actual download uses the shared pinned, bounded HTTPS downloader.
"""
import argparse
import asyncio
import hashlib
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from pydantic import SecretStr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.config import Settings, WORKSPACE_ROOT
from backend.app.errors import ServiceError
from backend.app.providers.neural4d import Neural4DProvider
from backend.app.assets.neural_service import ModelService
from backend.app.assets.service import AssetService
from backend.app.assets.usage import UsageManager

JOB_ID = 'b4da5f34-4681-420e-81b6-c1e3e447722e'
TASK_ID = 'bb074c31-1905-45b6-b763-22d065ddc616'


class OriginalTaskOnlyProvider(Neural4DProvider):
    async def create_once(self, *args, **kwargs):
        raise ServiceError('RECOVERY_CREATION_FORBIDDEN', '恢复流程禁止任何新建提交。', 403)

    async def download(self, url, *, attempt_id=None):
        if attempt_id != JOB_ID or getattr(self, 'recovery_assets', None) is None:
            raise ServiceError('RECOVERY_SCOPE_INVALID', '恢复下载缺少原任务及受控存储。', 403)
        raw = await super().download(url, attempt_id=attempt_id)
        digest = hashlib.sha256(raw).hexdigest()
        # Retain bounded HTTPS-verified bytes for LOCAL format diagnosis. This
        # quarantine is not registered, served, or labeled as a usable model.
        key = self.recovery_assets.save_bytes('recovery-quarantine', raw, digest, 'bin')
        self.last_quarantine = {'hash': digest, 'size': len(raw), 'storageKey': key,
                                'providerTaskId': TASK_ID, 'validatedModel': False}
        return raw

    async def read_operation(self, path, body, operation, *, attempt_id=None):
        if (path != 'retrieveModel' or body != {'uuid': TASK_ID}
                or operation != 'query_model' or attempt_id != JOB_ID):
            raise ServiceError('RECOVERY_SCOPE_INVALID', '恢复流程只能查询指定的原任务。', 403)
        result = await super().read_operation(path, body, operation, attempt_id=attempt_id)
        self.last_result_shape = {key: type(value).__name__ for key, value in result.items()
                                  if key in ('codeStatus', 'message', 'modelUrl', 'imageUrl', 'uuid', 'data')}
        self.last_provider_state = result.get('codeStatus') if type(result.get('codeStatus')) is int else None
        return result


class RecoveryOnlyService(ModelService):
    def approve(self, *args, **kwargs):
        raise ServiceError('RECOVERY_CREATION_FORBIDDEN', '恢复流程不批准新建任务。', 403)

    def approve_technical_candidate(self, *args, **kwargs):
        raise ServiceError('RECOVERY_CREATION_FORBIDDEN', '恢复流程不批准新建任务。', 403)

    async def submit(self, *args, **kwargs):
        raise ServiceError('RECOVERY_CREATION_FORBIDDEN', '恢复流程不发送新建任务。', 403)


def cached_model(assets):
    with assets.store.connect() as db:
        row = db.execute("SELECT content_json FROM asset_models WHERE json_extract(content_json,'$.providerTaskId')=?", (TASK_ID,)).fetchone()
    if row is None:
        raise ServiceError('RECOVERY_MODEL_MISSING', '账本完成但模型登记缺失，请核查原任务；不重新建模。', 409)
    model = json.loads(row[0])
    # Verify controlled path, actual byte length and hash before cached success.
    assets.file_path('model', model['modelId'])
    return assets.public_model(model)


async def recover(record):
    settings = Settings().model_copy(update={'neural4d_generation_enabled': False,
        'neural4d_protocol_verified': True, 'neural4d_download_hosts': ['cos.neural4d.com'],
        'neural4d_admin_token': SecretStr(secrets.token_urlsafe(32))})
    usage = UsageManager(WORKSPACE_ROOT / '.runtime/neural4d-usage.sqlite3')
    before = usage.summary()
    old = usage.get_attempt(JOB_ID)
    if (old['providerTaskId'] != TASK_ID or before['historical_used_attempts'] != 0
            or before['occupied_attempts'] != 1):
        raise ServiceError('RECOVERY_HISTORY_CHANGED', '原任务或全项目账本不匹配，停止恢复。', 409)
    record['usageBefore'] = before
    assets = AssetService(settings, None)
    service = RecoveryOnlyService(settings, assets, usage)
    service.provider = OriginalTaskOnlyProvider(settings, usage)
    service.provider.recovery_assets = assets
    service.start()
    try:
        if service.owner is None:
            raise ServiceError('SENDER_LOCK_UNAVAILABLE', '项目管理锁尚未取得，不绕过并发保护。', 409)
        record['ownerLockAcquired'] = True
        service.authorize(settings.neural4d_admin_token.get_secret_value())
        if old['state'] == 'SUCCEEDED':
            record['result'] = {**service.status(JOB_ID), 'model': cached_model(assets)}
            record['cachedLocalResultNoSupplierRequest'] = True
        else:
            # User explicitly authorized original-result reconciliation and a
            # new bounded query series. No quota/attempt identity is rewritten.
            service.continue_queries(JOB_ID)
            record['result'] = await service.refresh(JOB_ID)
        record['outcome'] = 'OPERATION_COMPLETED'
    finally:
        record['responseShape'] = getattr(service.provider, 'last_result_shape', None)
        record['providerCodeStatus'] = getattr(service.provider, 'last_provider_state', None)
        record['safeDownloadMetadata'] = getattr(service.provider, 'last_download_metadata', [])
        record['quarantinedResource'] = getattr(service.provider, 'last_quarantine', None)
        record['usageAfter'] = usage.summary()
        record['creationAttemptsUnchanged'] = before['occupied_attempts'] == record['usageAfter']['occupied_attempts']
        service.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    record = {'checkedAt': datetime.now(timezone.utc).isoformat(),
        'kind': 'ACTUAL_ORIGINAL_TASK_RECOVERY_NO_CREATION', 'providerTaskId': TASK_ID, 'jobId': JOB_ID,
        'creationEnabled': False, 'autoRetry': False, 'fullUrlsNotRecorded': True,
        'additionalPaidCalls': 0, 'additionalCreationAttempts': 0}
    try:
        asyncio.run(recover(record))
    except ServiceError as error:
        record.update(outcome='STOPPED', errorCode=error.code, message=error.message)
    except Exception:
        record.update(outcome='STOPPED', errorCode='RECOVERY_LOCAL_ERROR', message='恢复未完成；不新建，请核查原任务及本地受控文件。')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(json.dumps(record, ensure_ascii=True))
    return 0 if record.get('outcome') == 'OPERATION_COMPLETED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
