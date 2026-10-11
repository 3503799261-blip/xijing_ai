"""Generate a compact character with evidence-bound facts and explicit invention."""
import json
from pathlib import Path
from pydantic import ValidationError
from ..errors import ServiceError
from .planner import execution_metadata
from .schemas import CharacterDesign, canonical_ids, evidence_aliases, model_evidence

PROMPT_VERSION = 'agent_designer_v2'
PROMPT = Path(__file__).resolve().parents[2] / 'prompts' / (PROMPT_VERSION + '.txt')


def validate_design(content: str, evidence: list[dict]) -> dict:
    try:
        design = CharacterDesign.model_validate_json(content)
        aliases = evidence_aliases(evidence)
        design.usedEvidenceIds = canonical_ids(design.usedEvidenceIds, aliases)
        actual_used = set()
        for item in design.costume + design.colors + design.visualElements:
            item.evidenceIds = canonical_ids(item.evidenceIds, aliases)
            if item.interpretation == 'evidence_based' and not item.evidenceIds:
                raise ValueError('Fact requires evidence')
            if item.interpretation == 'creative' and item.evidenceIds:
                raise ValueError('Invention must not appear as a documented fact')
            actual_used.update(item.evidenceIds)
        if actual_used != set(design.usedEvidenceIds):
            raise ValueError('Declared evidence must match actual fact elements')
    except (ValidationError, ValueError, TypeError, KeyError):
        raise ServiceError('AGENT_DESIGN_INVALID', '角色方案格式或文化引用未通过校验，未交付最终方案。', 502)
    return design.model_dump()


async def design_character(brief: dict, plan: dict, research: dict, provider, request_id: str) -> dict:
    prompt = PROMPT.read_text(encoding='utf-8')
    payload = {'USER_BRIEF': brief,
               'PLAN': {key: value for key, value in plan.items() if key != 'execution'},
               'EVIDENCE': model_evidence(research['evidence']),
               'LIMITATIONS': research['limitations']}
    result = await provider.generate([{'role': 'system', 'content': prompt},
                                      {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)}],
                                     request_id, max_output=800)
    return {**validate_design(result['content'], research['evidence']),
            'execution': execution_metadata(result, request_id, PROMPT_VERSION, prompt)}
