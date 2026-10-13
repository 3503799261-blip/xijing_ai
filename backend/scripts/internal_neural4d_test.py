"""Trusted one-shot internal test. Submit once; each refresh queries that job only.

Private .env remains creation-disabled. The one-shot process uses ephemeral
admin authorization and the original global owner lock, ledger and ModelService.
No auto polling, creation retries, conversion, public promotion or history reset.
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
from backend.app.assets.service import AssetService
from backend.app.assets.neural_service import ModelService
from backend.app.assets.usage import UsageManager
from backend.app.assets.technical_test import freeze_technical_candidate
from backend.app.errors import ServiceError


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', 'utf-8')


def checked_request(path):
    request = json.loads(path.read_text('utf-8'))
    for key, hash_key in [('authorizationEvidenceFile', 'authorizationEvidenceHash'),
                          ('permissionEvidenceFile', 'permissionEvidenceHash'), ('costEvidenceFile', 'costEvidenceHash')]:
        source = (ROOT / request[key]).resolve()
        if ROOT not in source.parents or hashlib.sha256(source.read_bytes()).hexdigest() != request[hash_key]:
            raise ServiceError('APPROVAL_EVIDENCE_CHANGED', '用户授权或账户报价记录已变化，禁止发送。', 409)
    if hashlib.sha256(Path(request['sourcePath']).read_bytes()).hexdigest() != request['sourceImageHash']:
        raise ServiceError('NEURAL4D_INPUT_CHANGED', '当前原路径图片已变化，未提交。', 409)
    if request['estimatedCredits'] != 30:
        raise ServiceError('NEURAL4D_COST_UNVERIFIED', '本次仅按已提供的带贴图30积分报价准备。', 409)
    fields = ('candidateId', 'sourceImageHash', 'imageHash', 'promptHash', 'purpose', 'styleMode',
              'modelCount', 'authorizationEvidenceHash', 'permissionEvidenceHash', 'action', 'estimatedCredits', 'parameters')
    return {key: request[key] for key in fields}


async def run(args, record):
    base = Settings()
    if base.neural4d_generation_enabled:
        raise ServiceError('CREATION_MUST_DEFAULT_OFF', '私有配置真实创建必须保持关闭。', 403)
    token = secrets.token_urlsafe(32)
    # The allowlist is the current official retrieveModel documentation host.
    # Unlisted URLs fail without a fallback or another model creation.
    settings = base.model_copy(update={'neural4d_generation_enabled': args.action == 'submit',
        'neural4d_protocol_verified': True, 'neural4d_expected_credits': 30,
        'neural4d_admin_token': SecretStr(token), 'neural4d_download_hosts': ['cos.zmkj.com']})
    usage = UsageManager(WORKSPACE_ROOT / '.runtime/neural4d-usage.sqlite3')
    assets = AssetService(settings, None)
    service = ModelService(settings, assets, usage)
    assets.usage, assets.model_service = usage, service
    service.start()
    try:
        if service.owner is None:
            raise ServiceError('SENDER_LOCK_UNAVAILABLE', '发送者锁未取得，停止；不绕过现有服务。', 409)
        service.authorize(token)
        record['senderLockAcquired'] = True
        record['usageBefore'] = usage.summary()
        if args.action == 'submit':
            if args.state.is_file() or record['usageBefore']['occupied_attempts'] != 0:
                raise ServiceError('FIRST_SUBMISSION_ALREADY_RECORDED', '已有记录或占用；只允许读取原任务，禁止重复创建。', 409)
            data = checked_request(args.request)
            payload = freeze_technical_candidate(assets, data)
            record['frozenPayload'] = payload
            record['sourceHashCurrent'] = data['sourceImageHash']
            # Save the preparation before even the read-only supplier request.
            save(args.state, record)
            verification = await service.verify()
            record['authenticated'] = verification['authenticated']
            record['balanceSufficient'] = service.balance >= 30
            if not record['balanceSufficient']:
                raise ServiceError('NEURAL4D_BALANCE_LOW', '实际余额不足本次30积分，未创建。', 403)
            approval = service.approve_technical_candidate(data)
            record['approval'] = approval
            record['idempotencyKey'] = 'internal-chibi-first-' + approval['approvalId']
            save(args.state, record)
            record['result'] = await service.submit({'approvalId': approval['approvalId'], 'modelCount': 1}, record['idempotencyKey'])
        elif args.action == 'refresh':
            previous = json.loads(args.state.read_text('utf-8'))
            job = previous.get('result', {}).get('jobId') or previous.get('jobId')
            if not job:
                raise ServiceError('NO_RELIABLE_JOB_ID', '未记录可靠任务，先人工核查，不创建。', 409)
            old = usage.get_attempt(job)
            if old['state'] in ('UNKNOWN', 'PENDING_RECONCILIATION', 'FAILED'):
                raise ServiceError('NEURAL4D_RECONCILIATION_REQUIRED', '原任务未知或失败，停止自动操作并人工核查。', 409)
            if old['state'] == 'SUCCEEDED':
                record['result'] = service.status(job)
                record['alreadyCompletedNoSupplierCall'] = True
            else:
                record['result'] = await service.refresh(job)
        else:
            record['result'] = {'status': 'LOCAL_ONLY_NO_SUPPLIER_CALLS'}
        record['usageAfter'] = usage.summary()
    finally:
        service.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=('submit', 'refresh', 'report'), required=True)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    record = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'action': args.action,
              'kind': 'ACTUAL_INTERNAL_TECHNICAL_TEST', 'autoRetry': False,
              'publicExhibitionAllowed': False, 'formalCharacterAsset': False}
    try:
        asyncio.run(run(args, record))
        record['outcome'] = 'COMPLETED_OPERATION'
    except ServiceError as error:
        record.update(outcome='STOPPED', errorCode=error.code, message=error.message)
    except Exception:
        record.update(outcome='STOPPED', errorCode='LOCAL_OPERATION_OR_SAVE_ERROR',
                      message='本地操作未完成；不自动重试或创建任务，请核查固定账本。')
    save(args.output, record)
    # Preserve submit preparation and result at its private state path. Refresh
    # records are separate immutable snapshots; do not overwrite first evidence.
    if args.action == 'submit' and args.state.is_file():
        save(args.state, record)
    print(json.dumps(record, ensure_ascii=True))
    return 0 if record['outcome'] == 'COMPLETED_OPERATION' else 1


if __name__ == '__main__':
    raise SystemExit(main())
