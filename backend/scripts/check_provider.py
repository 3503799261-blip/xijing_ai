"""One explicitly requested low-token real API probe; secret values never printed."""
import argparse
import asyncio
import json
import uuid
from pathlib import Path
from backend.app.config import Settings
from backend.app.providers.llm import DeepSeekProvider
from backend.app.errors import ServiceError

async def probe(output: Path | None):
    provider = DeepSeekProvider(Settings())
    request_id = 'probe-' + str(uuid.uuid4())
    try:
        result = await provider.generate([{'role': 'user', 'content': '请只回复：接口连通。'}], request_id, json_mode=False, max_output=32)
        report = {'requestId': request_id, 'success': True, **result, 'budget': provider.ledger.summary()}
    except ServiceError as error:
        report = {'requestId': request_id, 'success': False, **error.public(request_id), 'budget': provider.ledger.summary()}
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))
    return 0 if report['success'] else 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(probe(args.output)))
