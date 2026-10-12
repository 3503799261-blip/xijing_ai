"""One explicitly requested read-only balance probe; never creates a model."""
import argparse
import asyncio
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

from ..app.config import Settings, WORKSPACE_ROOT, PROJECT_ROOT
from ..app.assets.usage import UsageManager
from ..app.providers.neural4d import Neural4DProvider
from ..app.errors import ServiceError


async def probe(settings, usage, transport=None):
    if settings.neural4d_generation_enabled:
        raise ServiceError('VERIFY_REQUIRES_CREATION_OFF', '只读验证前请保持真实建模关闭。', 403)
    provider = Neural4DProvider(settings, usage, transport)
    if not provider.configured:
        raise ServiceError('NEURAL4D_KEY_MISSING', '本地密钥未配置，未发出请求。', 503)
    # A single provider read; no retry, fallback, model service or create call.
    data = await provider.read_operation('queryPointsInfo', {}, 'verify')
    value = data.get('data', {}).get('total_points') if isinstance(data.get('data'), dict) else None
    if (type(data.get('statusType')) is not int or data['statusType'] != 0
            or type(value) not in (int, float) or not math.isfinite(value) or value < 0):
        raise ServiceError('NEURAL4D_BALANCE_UNVERIFIED', '余额响应无法核实，保持创建关闭。', 502)
    return {'authenticated': True, 'balanceVerified': True,
            'creationPermissionVerified': False, 'modelSubmitted': False,
            'balanceCredits': value}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acknowledge-read-only', action='store_true', required=True)
    parser.add_argument('--output', type=Path, default=PROJECT_ROOT / '.runtime/neural4d-balance-public.json')
    args = parser.parse_args()
    started = time.perf_counter()
    record = {'checkedAt': datetime.now(timezone.utc).isoformat(),
              'kind': 'ACTUAL_SUPPLIER_READ_ONLY_BALANCE_PROBE',
              'modelSubmissionAttempts': 0, 'automaticRetry': False,
              'exactBalanceExcludedFromPublicRecord': True}
    try:
        settings = Settings()
        if settings.neural4d_generation_enabled:
            raise ServiceError('VERIFY_REQUIRES_CREATION_OFF', '只读验证前请保持真实建模关闭。', 403)
        if not settings.neural4d_api_key.get_secret_value():
            raise ServiceError('NEURAL4D_KEY_MISSING', '本地密钥未配置，未发出请求。', 503)
        usage = UsageManager(WORKSPACE_ROOT / '.runtime/neural4d-usage.sqlite3')
        result = asyncio.run(probe(settings, usage))
        private = PROJECT_ROOT / '.runtime/neural4d-balance-private.json'
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_text(json.dumps(result) + '\n', encoding='utf-8')
        record.update({key: value for key, value in result.items() if key != 'balanceCredits'})
        record['result'] = 'VERIFIED'
    except ServiceError as error:
        record.update(result='FAILED', errorCode=error.code, authenticated=False,
                      creationPermissionVerified=False, modelSubmitted=False)
    except Exception:
        # Do not print exception repr/headers/private settings even on bad config.
        record.update(result='FAILED', errorCode='NEURAL4D_BALANCE_PROBE_ERROR',
                      authenticated=False, creationPermissionVerified=False, modelSubmitted=False)
    record['durationMs'] = round((time.perf_counter() - started) * 1000, 2)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record))
    return 0 if record['result'] == 'VERIFIED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
