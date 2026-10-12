"""Read registered browser test assets over loopback; no writes or provider calls."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]


def get(path):
    with urlopen('http://127.0.0.1:8000/api/v1/assets/' + path, timeout=15) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chibi', required=True)
    parser.add_argument('--realistic', required=True)
    parser.add_argument('--output', type=Path, default=ROOT / '.runtime/phase4-styles-local.json')
    args = parser.parse_args()
    # UUID validation prevents caller-controlled URLs or path traversal.
    from uuid import UUID
    chibi = get('characters/' + str(UUID(args.chibi)))
    realistic = get('characters/' + str(UUID(args.realistic)))
    usage = get('usage')
    common = ['characterId', 'sourceTaskId', 'sourceResultHash', 'citationHash',
              'characterSnapshot', 'reviewSnapshot', 'citationSnapshot']
    checks = {
        'distinctStyleAssets': chibi['assetId'] != realistic['assetId'],
        'correctStyles': chibi['styleMode'] == 'chibi' and realistic['styleMode'] == 'realistic',
        'identicalCulturalBasis': all(chibi[key] == realistic[key] for key in common),
        'differentPrompts': chibi['visualPrompt']['promptHash'] != realistic['visualPrompt']['promptHash'],
        'noClaimedImagesOrModels': all(not row['images'] and not row['models'] for row in (chibi, realistic)),
        'sharedGlobalCapLocked': usage['max_calls'] == 3 and usage['remaining_calls'] is None
                                and usage['history_verified'] is False and usage['realEnabled'] is False,
    }
    report = {'checkedAt': datetime.now(timezone.utc).isoformat(),
              'kind': 'ACTUAL_LOCAL_HTTP_READBACK_NO_PROVIDER_CALLS', 'checks': checks,
              'assets': [{key: row[key] for key in ('assetId', 'characterId', 'sourceTaskId',
                         'styleMode', 'styleVersion', 'sourceResultHash', 'citationHash')}
                         for row in (chibi, realistic)],
              'usedCalls': usage['used_calls'], 'remainingCalls': usage['remaining_calls'],
              'paidApiCalls': 0}
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'checks': checks, 'passed': all(checks.values())}))
    raise SystemExit(0 if all(checks.values()) else 1)


if __name__ == '__main__':
    main()
