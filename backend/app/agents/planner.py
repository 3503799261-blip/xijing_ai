"""Intent parsing, never a source of opera facts."""
import hashlib
import json
import re
from pathlib import Path
from pydantic import ValidationError
from ..errors import ServiceError
from .schemas import TaskPlan

PROMPT_VERSION = 'agent_planner_v2'
PROMPT = Path(__file__).resolve().parents[2] / 'prompts' / (PROMPT_VERSION + '.txt')


def execution_metadata(result: dict, request_id: str, version: str, prompt: str) -> dict:
    return {'requestId': request_id, 'model': result.get('model'),
            'usage': result.get('usage'), 'elapsedSeconds': result.get('elapsedSeconds'),
            'promptVersion': version, 'promptHash': hashlib.sha256(prompt.encode()).hexdigest()}


async def plan_creation(brief: dict, provider, request_id: str) -> dict:
    prompt = PROMPT.read_text(encoding='utf-8')
    result = await provider.generate([
        {'role': 'system', 'content': prompt},
        {'role': 'user', 'content': json.dumps({'USER_BRIEF': brief}, ensure_ascii=False)},
    ], request_id, max_output=256)
    try:
        plan = TaskPlan.model_validate_json(result['content'])
        if plan.style != brief['style']:
            raise ValueError('User style changed')
        if [item.id for item in plan.requirements] != [f'R{i}' for i in range(1, len(plan.requirements) + 1)]:
            raise ValueError('Requirement IDs must be ordered')
        if len(set(plan.researchQueries)) != len(plan.researchQueries):
            raise ValueError('Duplicate queries')
        # Explicit historical names are lexical prerequisites, not facts the
        # planner may invent. A narrow actor phrase guard also protects against
        # a model omitting the literal name from its structured output.
        actor_names = re.findall(r'(?:京剧)?演员([\u4e00-\u9fff·]{2,12}?)(?=在|于|的)', brief['requirements'])
        entities = list(dict.fromkeys(plan.requiredEntities + actor_names))
        if any(entity not in brief['requirements'] for entity in entities) or len(entities) > 3:
            raise ValueError('Required factual entity is not from the user brief')
        plan.requiredEntities = entities
    except (ValidationError, ValueError, KeyError, TypeError):
        raise ServiceError('AGENT_PLAN_INVALID', '任务计划格式或用户风格约束未通过校验，未继续创作。', 502)
    return {**plan.model_dump(), 'execution': execution_metadata(result, request_id, PROMPT_VERSION, prompt)}
