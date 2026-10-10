import json
from pathlib import Path
from pydantic import ValidationError
from ..errors import ServiceError
from ..schemas import GeneratedAnswer

PROMPT = Path(__file__).resolve().parents[2] / 'prompts' / 'rag_answer_v1.txt'

def insufficient(request_id, message='当前京剧知识库没有足够资料支持这个问题，请调整提问方向或补充可信资料。'):
    return {'answer': message, 'citations': [], 'uncertain': True, 'requestId': request_id}

def validated_answer(content: str, evidence: list[dict], request_id: str):
    try:
        data = GeneratedAnswer.model_validate_json(content)
        if not data.answer.strip(): raise ValueError('Empty answer')
        available = {e['id']: e for e in evidence}
        ids = list(dict.fromkeys(data.usedCitationIds))
        if any(cid not in available for cid in ids) or (not data.uncertain and not ids):
            raise ValueError('Unsupported citation')
        citations = [{k: available[cid][k] for k in ('id', 'title', 'sourceId', 'locator', 'url', 'excerpt', 'contentKind')} for cid in ids]
        return {'answer': data.answer, 'citations': citations, 'uncertain': data.uncertain, 'requestId': request_id}
    except (ValueError, ValidationError, TypeError):
        raise ServiceError('ANSWER_EVIDENCE_INVALID', '模型回答未通过引用校验，已停止展示；请调整问题后重试。', 502, True)

async def grounded_answer(question: str, retrieval: dict, provider, request_id: str):
    if retrieval['uncertain']:
        return insufficient(request_id)
    evidence = retrieval['evidence'][:5]
    messages = [{'role': 'system', 'content': PROMPT.read_text(encoding='utf-8')}, {'role': 'user', 'content': json.dumps({'question': question, 'EVIDENCE': evidence}, ensure_ascii=False)}]
    result = await provider.generate(messages, request_id)
    return validated_answer(result['content'], evidence, request_id)
