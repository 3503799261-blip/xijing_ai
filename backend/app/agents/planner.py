"""Intent parsing, never a source of opera facts."""
import hashlib
import json
import re
from pathlib import Path
from pydantic import ValidationError
from ..errors import ServiceError
from .schemas import TaskPlan

PROMPT_VERSION = 'agent_planner_v4'
PROMPT = Path(__file__).resolve().parents[2] / 'prompts' / (PROMPT_VERSION + '.txt')


def execution_metadata(result: dict, request_id: str, version: str, prompt: str) -> dict:
    return {'requestId': request_id, 'model': result.get('model'),
            'usage': result.get('usage'), 'elapsedSeconds': result.get('elapsedSeconds'),
            'promptVersion': version, 'promptHash': hashlib.sha256(prompt.encode()).hexdigest()}


def safe_plan_diagnostic(error, location, result, request_id, prompt):
    """Keep only fixed contract paths/types and allowlisted call metadata.

    Even unknown JSON field names may contain sensitive text, so never copy
    arbitrary validation locations, messages, inputs or exception strings.
    """
    fields = {'taskPlan', 'theme', 'target', 'style', 'requirements', 'id', 'text',
              'researchQueries', 'clarificationQuestions', 'requiredEntities'}
    types = {'json_invalid', 'model_type', 'missing', 'extra_forbidden', 'string_type',
             'string_too_short', 'string_too_long', 'string_pattern_mismatch',
             'list_type', 'too_short', 'too_long', 'literal_error', 'value_error'}
    errors = error.errors(include_input=False, include_url=False, include_context=False) if isinstance(error, ValidationError) else [{'loc': location, 'type': 'constraint_mismatch'}]
    sanitized = []
    for item in errors[:8]:
        path = [part if part in fields else 'unknown_field' if isinstance(part, str)
                else str(part) if type(part) is int and 0 <= part <= 9 else 'unknown_index'
                for part in item.get('loc', ())]
        kind = item.get('type')
        sanitized.append({'field': '.'.join(path) if path else 'taskPlan',
                          'type': kind if kind in types or kind == 'constraint_mismatch' else 'validation_error'})
    metadata = execution_metadata(result, request_id, PROMPT_VERSION, prompt)
    usage = metadata.get('usage')
    metadata['usage'] = {key: usage[key] for key in ('prompt_tokens', 'completion_tokens', 'total_tokens', 'prompt_cache_hit_tokens', 'prompt_cache_miss_tokens')
                         if type(usage.get(key)) is int and usage[key] >= 0} if isinstance(usage, dict) else None
    model = metadata.get('model')
    metadata['model'] = model if isinstance(model, str) and (model == 'offline-test-double' or model == 'deepseek-flash' or model.startswith('deepseek-flash-')) else None
    elapsed = metadata.get('elapsedSeconds')
    metadata['elapsedSeconds'] = elapsed if type(elapsed) in (int, float) and 0 <= elapsed <= 3600 else None
    return {'kind': 'schema_validation_failure', 'validationErrors': sanitized, 'execution': metadata}


async def plan_creation(brief: dict, provider, request_id: str) -> dict:
    prompt = PROMPT.read_text(encoding='utf-8')
    result = await provider.generate([
        {'role': 'system', 'content': prompt},
        {'role': 'user', 'content': json.dumps({'USER_BRIEF': brief}, ensure_ascii=False)},
    ], request_id, max_output=384)
    location = ('taskPlan',)
    try:
        plan = TaskPlan.model_validate_json(result['content'])
        location = ('style',)
        if plan.style != brief['style']:
            raise ValueError('User style changed')
        location = ('requirements', 'id')
        if [item.id for item in plan.requirements] != [f'R{i}' for i in range(1, len(plan.requirements) + 1)]:
            raise ValueError('Requirement IDs must be ordered')
        location = ('researchQueries',)
        if len(set(plan.researchQueries)) != len(plan.researchQueries):
            raise ValueError('Duplicate queries')
        # Explicit historical names are lexical prerequisites, not facts the
        # planner may invent. A narrow actor phrase guard also protects against
        # a model omitting the literal name from its structured output.
        actor_names = re.findall(r'(?:京剧)?演员([\u4e00-\u9fff·]{2,12}?)(?=在|于|的)', brief['requirements'])
        entities = list(dict.fromkeys(plan.requiredEntities + actor_names))
        location = ('requiredEntities',)
        if any(entity not in brief['requirements'] for entity in entities) or len(entities) > 3:
            raise ValueError('Required factual entity is not from the user brief')
        plan.requiredEntities = entities
    except (ValidationError, ValueError, KeyError, TypeError) as error:
        failure = ServiceError('AGENT_PLAN_INVALID', '任务计划格式或用户风格约束未通过校验，未继续创作。', 502)
        failure.diagnostic_artifact = safe_plan_diagnostic(error, location, result, request_id, prompt)
        raise failure
    return {**plan.model_dump(), 'execution': execution_metadata(result, request_id, PROMPT_VERSION, prompt)}
