"""Small paid direct-LLM comparison, explicit invocation, approved provider budget."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import uuid
from backend.app.config import Settings
from backend.app.providers.llm import DeepSeekProvider
from backend.app.errors import ServiceError

async def run(args):
    if args.output.exists(): raise ValueError('Refusing to overwrite experiment evidence')
    questions = json.loads(args.questions.read_text(encoding='utf-8'))[:args.limit]
    provider = DeepSeekProvider(Settings())
    result = {'scope': 'real direct DeepSeek without retrieval; comparison only, not RAG production data', 'startedAt': datetime.now(timezone.utc).isoformat(), 'records': []}
    for item in questions:
        request_id = 'baseline-' + str(uuid.uuid4())
        started = time.perf_counter()
        record = {'id': item['id'], 'question': item['question'], 'requestId': request_id, 'attempts': 1}
        try:
            response = await provider.generate([{'role': 'system', 'content': '你是面向普通大众的京剧文化讲解助手，用准确通俗的中文回答，不清楚时如实说明。'}, {'role': 'user', 'content': item['question']}], request_id, json_mode=False)
            record.update(success=True, answer=response['content'], model=response['model'], usage=response['usage'])
        except ServiceError as exc:
            record.update(success=False, errorCode=exc.code)
        record['elapsedSeconds'] = round(time.perf_counter()-started, 4)
        result['records'].append(record)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({'id': item['id'], 'success': record['success']}, ensure_ascii=True), flush=True)
        if record.get('errorCode') == 'TEST_BUDGET_EXCEEDED': break
    result['finishedAt'] = datetime.now(timezone.utc).isoformat()
    result['budget'] = provider.ledger.summary()
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--questions', type=Path, default=Path('knowledge/evaluation/questions.json'))
    parser.add_argument('--limit', type=int, choices=range(1, 21), default=5)
    parser.add_argument('--output', type=Path, required=True)
    asyncio.run(run(parser.parse_args()))
