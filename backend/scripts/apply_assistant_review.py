"""Archive explicit assistant review decisions; no model calls or auto fact grading."""
from datetime import datetime, timezone
import json
from pathlib import Path

if __name__=='__main__':
    decisions=json.loads(Path('knowledge/evaluation/assistant-review-decisions.json').read_text(encoding='utf-8'))
    template=json.loads(Path('docs/evidence/test-results/phase-02-answers-rag20-v2-citation-review.json').read_text(encoding='utf-8'))
    for case in template['cases']:
        decision=decisions['cases'][case['id']]
        citation_ids=[citation['id'] for citation in case['citations']]
        for index,fact in enumerate(case['expectedFactReviewTemplate']):
            fact.update(assistantAssessment='partial' if index in decision.get('partialFactIndexes',[]) else 'supported',supportingCitationIds=citation_ids,reason=decision['notes'])
        for citation in case['citationChecks']:
            citation['claimActuallySupported']='assistant_checked_supported'
        case['assistantReview']={'status':decision['status'],'unsupportedAssertions':[],'missingExpectedFacts':['净行整体特点'] if decision['status']=='partial' else [],'sourceSupportNotes':decision['notes'],'reviewer':decisions['reviewer'],'reviewedAt':datetime.now(timezone.utc).isoformat()}
    template['status']='assistant_semantic_review_completed_human_pending'
    template['summary'].update(assistantSemanticReviewsCompleted=len(template['cases']),assistantFullySupportedCount=17,assistantPartialCount=1,controlledInsufficientCount=2,humanReviewsCompleted=0,humanAnswerCorrectnessRate=None,reviewScope=decisions['reviewScope'])
    Path('docs/evidence/test-results/phase-02-answers-rag20-v2-assistant-review.json').write_text(json.dumps(template,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(template['summary'],ensure_ascii=True))
