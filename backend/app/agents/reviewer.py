"""Model-assisted semantic checking follows deterministic evidence ownership gates."""
import json
from pathlib import Path
from pydantic import ValidationError
from ..errors import ServiceError
from .planner import execution_metadata
from .schemas import CultureReview, canonical_ids, evidence_aliases, model_evidence

PROMPT_VERSION = 'agent_reviewer_v3'
PROMPT = Path(__file__).resolve().parents[2] / 'prompts' / (PROMPT_VERSION + '.txt')


def garment_reference_issues(design: dict, evidence: list[dict]) -> list[dict]:
    """A narrow conservative safeguard, not a general semantic classifier.

    A face/voice excerpt cannot support a concrete unmentioned garment. These
    lexemes name details to check for absence; they contain no hardcoded answer.
    Broader paraphrase/role/version validity still needs model and human review.
    """
    by_id = {item['id']: item for item in evidence}
    lexemes = ('宽肩', '长袍', '蟒袍', '大靠', '靠旗', '厚底靴', '薄底靴', '短打衣', '官衣', '硬靠', '盔头')
    issues = []
    for index, item in enumerate(design['costume']):
        if item['interpretation'] != 'evidence_based':
            continue
        cited_text = '\n'.join(by_id[cid]['excerpt'] for cid in item['evidenceIds'])
        missing = [term for term in lexemes if term in item['description'] and term not in cited_text]
        if missing:
            issues.append({'field': f'costume[{index}].description',
                           'reason': '所引用片段未提及服饰细节「' + '、'.join(missing) + '」；请删除或明确改为原创。',
                           'evidenceIds': item['evidenceIds']})
    return issues


def validate_review(content: str, evidence: list[dict], design: dict) -> dict:
    try:
        review = CultureReview.model_validate_json(content)
        aliases = evidence_aliases(evidence)
        review.checkedEvidenceIds = canonical_ids(review.checkedEvidenceIds, aliases)
        for issue in review.issues:
            issue.evidenceIds = canonical_ids(issue.evidenceIds, aliases)
            if not set(issue.evidenceIds).issubset(review.checkedEvidenceIds):
                raise ValueError('Issue references must have been checked')
        if review.verdict == 'pass':
            if review.issues or not set(design['usedEvidenceIds']).issubset(review.checkedEvidenceIds):
                raise ValueError('Cannot pass unresolved or unchecked facts')
        elif not review.issues:
            raise ValueError('Non-passing review must identify the reason')
    except (ValidationError, ValueError, TypeError, KeyError):
        raise ServiceError('AGENT_REVIEW_INVALID', '文化审校格式或引用未通过校验，方案保持未确认。', 502)
    return review.model_dump()


async def review_culture(brief: dict, plan: dict, research: dict, design: dict, provider, request_id: str) -> dict:
    prompt = PROMPT.read_text(encoding='utf-8')
    reverse = {canonical: alias for alias, canonical in evidence_aliases(research['evidence']).items()}
    model_design = {key: value for key, value in design.items() if key != 'execution'}
    # Clone before aliasing; never mutate the upstream canonical design artifact.
    model_design = json.loads(json.dumps(model_design))
    model_design['usedEvidenceIds'] = [reverse[cid] for cid in model_design['usedEvidenceIds']]
    for element in model_design['costume'] + model_design['colors'] + model_design['visualElements']:
        element['evidenceIds'] = [reverse[cid] for cid in element['evidenceIds']]
    payload = {'USER_BRIEF': brief,
               'PLAN': {key: value for key, value in plan.items() if key != 'execution'},
               'DESIGN': model_design, 'EVIDENCE': model_evidence(research['evidence']),
               'LIMITATIONS': research['limitations']}
    result = await provider.generate([{'role': 'system', 'content': prompt},
                                      {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)}],
                                     request_id, max_output=400)
    review = validate_review(result['content'], research['evidence'], design)
    guard_issues = garment_reference_issues(design, research['evidence'])
    if guard_issues:
        review['verdict'] = 'needs_revision'
        review['issues'] = (guard_issues + review['issues'])[:4]
        review['suggestions'] = (['具体服饰细节须有对应资料；无资料的造型只可明确标为原创。'] + review['suggestions'])[:4]
        review['checkedEvidenceIds'] = list(dict.fromkeys(review['checkedEvidenceIds'] + [cid for issue in guard_issues for cid in issue['evidenceIds']]))
    return {**review,
            'programmaticChecks': {'garmentReferenceGuard': 'conservative_literal_absence', 'issuesFound': len(guard_issues)},
            'execution': execution_metadata(result, request_id, PROMPT_VERSION, prompt)}
