"""Asset preparation only; no Neural4D imports, requests or model creation.

The optional existing text Culture Reviewer requires explicit CLI opt-in and a
persisted single-use marker. No automatic paid retry, full workflow or approval.
"""
import argparse
import asyncio
import hashlib
import io
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageChops, ImageOps

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.agents import reviewer
from backend.app.assets.service import AssetService
from backend.app.assets.candidates import CandidateCatalog
from backend.app.assets.visual_prompt import canonical_hash
from backend.app.config import Settings, WORKSPACE_ROOT
from backend.app.errors import ServiceError
from backend.app.providers.llm import DeepSeekProvider


def stamp():
    return datetime.now(timezone.utc).isoformat()


def neural_readback():
    path = WORKSPACE_ROOT / '.runtime/neural4d-usage.sqlite3'
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        return {'attempts': db.execute('SELECT count(*) FROM neural4d_creation_attempts').fetchone()[0],
                'attemptStates': db.execute('SELECT state,count(*) FROM neural4d_creation_attempts GROUP BY state').fetchall(),
                'operations': db.execute('SELECT operation,count(*),sum(coalesce(actual_credits,0)) FROM neural4d_operational_requests GROUP BY operation').fetchall()}


class Captured(Exception):
    pass


class CaptureProvider:
    async def generate(self, messages, request_id, *, max_output):
        self.messages, self.max_output = messages, max_output
        raise Captured()


async def review_once(data, settings, allow_paid):
    captured = CaptureProvider()
    try:
        await reviewer.review_culture(data['brief'], data['plan'], data['research'], data['design'], captured, 'preflight-only')
    except Captured:
        pass
    if captured.max_output != 400:
        raise ServiceError('REVIEW_OUTPUT_POLICY_CHANGED', '审校输出限制变化，停止。', 409)
    peak_upper = ((len(json.dumps(captured.messages, ensure_ascii=False).encode('utf-8')) + 256) * 2 + 400 * 8) / 1_000_000
    if not allow_paid:
        return {'status': 'NOT_CALLED', 'estimatedUpperCny': peak_upper, 'maxOutputTokens': 400}, None
    directory = WORKSPACE_ROOT / '.runtime/realistic-preparation'
    directory.mkdir(parents=True, exist_ok=True)
    marker = directory / ('reviewer-once-' + data['image']['sourceHash'] + '.json')
    if marker.exists():
        raise ServiceError('REVIEW_ALREADY_CLAIMED', '本图一次审校已领取或运行；本命令不自动重发。', 409)
    provider = DeepSeekProvider(settings)
    if not provider.verified:
        raise ServiceError('REVIEW_PROVIDER_UNVERIFIED', '现有文本服务未验证，本轮不额外探测或重试。', 409)
    before = provider.ledger.summary()
    if (before['estimatedUpperCostCny'] + peak_upper > before['budgetCny']
            or before['activeScope']['estimatedUpperCostCny'] + peak_upper > before['activeScope']['budgetCny']):
        raise ServiceError('REVIEW_BUDGET_BLOCKED', '现有预算不足，本轮停止审校调用。', 409)
    receipt = {'status': 'CLAIMED', 'requestId': 'phase4-realistic-review-' + str(uuid.uuid4()),
               'inputHash': canonical_hash(data), 'sourceHash': data['image']['sourceHash'],
               'claimedAt': stamp(), 'maxOutputTokens': 400, 'estimatedUpperCny': peak_upper,
               'automaticRetry': False, 'budgetBefore': before}
    with marker.open('x', encoding='utf-8') as file:
        file.write(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
        file.flush()
        os.fsync(file.fileno())
    result = None
    try:
        result = await reviewer.review_culture(data['brief'], data['plan'], data['research'], data['design'], provider, receipt['requestId'])
        receipt.update(status='RETURNED_VALIDATED', review=result)
    except ServiceError as error:
        receipt.update(status='STOPPED_NO_RETRY', errorCode=error.code, message=error.message)
    finally:
        receipt['budgetAfter'] = provider.ledger.summary()
        receipt['finishedAt'] = stamp()
        marker.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    return receipt, result


async def prepare(args):
    data = json.loads(args.input.read_text('utf-8'))
    settings = Settings()
    if settings.neural4d_generation_enabled:
        raise ServiceError('PREPARATION_CREATION_ENABLED', '准备阶段要求真实建模关闭。', 409)
    image = Path(data['image']['sourcePathLabel'])
    raw = image.read_bytes()
    if hashlib.sha256(raw).hexdigest() != data['image']['sourceHash']:
        raise ServiceError('PREPARATION_IMAGE_CHANGED', '图片已变化，不能沿用旧审核输入。', 409)
    before = neural_readback()
    if before['attempts'] != 1 or before['attemptStates'] != [('SUCCEEDED', 1)]:
        raise ServiceError('PREPARATION_HISTORY_CHANGED', '原建模历史不匹配，先人工核查。', 409)
    record = {'checkedAt': stamp(), 'kind': 'ACTUAL_REALISTIC_ASSET_PREPARATION_ONLY',
              'sourceHash': data['image']['sourceHash'], 'neural4dBefore': before,
              'neural4dApiCalls': 0, 'newModelSubmissions': 0, 'newModelReservations': 0,
              'fullFourAgentWorkflowRun': False, 'reviewerIsTextOnly': True}
    receipt, review = await review_once(data, settings, args.allow_one_cultural_review)
    record['textCultureReviewReceipt'] = receipt
    # Immutable candidate, never a confirmed Character Asset or model approval.
    assets = AssetService(settings, None)
    catalog = CandidateCatalog(assets)
    with assets.store.connect() as db:
        counts_before = {table: db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
                         for table in ('character_assets', 'asset_images', 'asset_models')}
    candidate = catalog.register(raw, 'image/jpeg', data['scope'], data['sourceNote'], data['licenseNote'],
                                 data['promptSnapshot'], str(image.resolve()), 'realistic')
    if catalog.file_path(candidate['candidateId'], 'original').read_bytes() != raw:
        raise ServiceError('PREPARATION_IMAGE_CHANGED', '原始快照不一致。', 409)
    with Image.open(io.BytesIO(raw)) as original, Image.open(catalog.file_path(candidate['candidateId'])) as preview:
        original_rgb = ImageOps.exif_transpose(original).convert('RGB')
        preview_rgb = preview.convert('RGB')
        pixels_equal = original_rgb.size == preview_rgb.size and ImageChops.difference(original_rgb, preview_rgb).getbbox() is None
    with assets.store.connect() as db:
        counts_after = {table: db.execute('SELECT count(*) FROM ' + table).fetchone()[0] for table in counts_before}
    after = neural_readback()
    if not pixels_equal or before != after or counts_before != counts_after:
        raise ServiceError('PREPARATION_INVARIANT_FAILED', '快照、已有资产或额度变化，停止。', 409)
    record.update(candidate=candidate, assetLabel=data['assetLabel'], reviewerResult=review,
                  neural4dAfter=after, neural4dLedgerUnchanged=before == after,
                  formalAssetsBefore=counts_before, formalAssetsAfter=counts_after,
                  sourceAndPreviewPixelsEqual=pixels_equal, backgroundEdited=False,
                  imageUploadedToSupplier=False, creationEnabled=False,
                  status='PREPARED_WITH_PENDING_HUMAN_AND_RIGHTS_GATES')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-one-cultural-review', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Existing evidence output; no automatic overwrite or paid replay.')
    try:
        result = asyncio.run(prepare(args))
    except ServiceError as error:
        result = {'checkedAt': stamp(), 'status': 'STOPPED', 'errorCode': error.code,
                  'message': error.message, 'newModelSubmissions': 0}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(json.dumps({key: result.get(key) for key in ('status', 'sourceHash', 'neural4dLedgerUnchanged')}, ensure_ascii=True))
    return 0 if result['status'] == 'PREPARED_WITH_PENDING_HUMAN_AND_RIGHTS_GATES' else 1


if __name__ == '__main__':
    raise SystemExit(main())
