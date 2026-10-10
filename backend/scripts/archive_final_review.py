"""Archive explicit primary-assistant review; no model calls or automatic grading."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean
from backend.app.config import Settings
from backend.app.providers.budget import BudgetLedger

ROOT=Path('docs/evidence/test-results')

def read(name): return json.loads((ROOT/name).read_text(encoding='utf-8'))
def save(name,value):
    path=ROOT/name
    if path.exists(): raise FileExistsError('Review evidence already exists.')
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def run():
    # The primary assistant read all actual final responses and associated
    # canonical excerpts in this development session before archiving decisions.
    prior=json.loads(Path('knowledge/evaluation/assistant-review-decisions.json').read_text(encoding='utf-8'))
    decisions=dict(prior['cases'])
    decisions['opera-q04']={'status':'supported','notes':'最终混合检索取到taxonomy、sheng-dan、chou、jing及旦行资料；四行当的角色类型与净行整体特点均由本次实际引用支持，原先部分回答的缺口已补齐。'}
    decisions['opera-q08']['notes']+=' 最终回答补充靠旗用途，对应本次kao引用。'
    final=read('phase-02-answers-rag20-final-hybrid.json')
    structural=read('phase-02-answers-rag20-final-hybrid-citation-review-review.json')
    assert all(r['status']=='response_received' for r in final['records'])
    assert structural['summary']['structuralSourceTraceabilityRate']==1
    for case in structural['cases']:
        case['assistantReview']={**decisions[case['id']],'reviewer':prior['reviewer'],'scope':'Explicit assistant assessment after reading the actual answer and canonical evidence; not human gold','humanReviewStatus':'pending'}
    structural['status']='assistant_semantic_review_completed_human_pending'
    structural['summary'].update(assistantSemanticReviewsCompleted=20,assistantFullySupportedCount=18,assistantPartialCount=0,controlledInsufficientCount=2,humanReviewsCompleted=0,humanAnswerCorrectnessRate=None)
    structural['reviewedAt']=datetime.now(timezone.utc).isoformat()
    if not (ROOT/'phase-02-answers-rag20-final-hybrid-assistant-review.json').exists():
        save('phase-02-answers-rag20-final-hybrid-assistant-review.json',structural)
    direct=read('phase-02-answers-direct-five.json')['records']
    ledger=BudgetLedger(Settings().rag_data_dir/'api-budget.sqlite3',3)
    usage={r['requestId']:r for r in ledger.records()}
    notes={
        'opera-q01':'两组均包含四班与逐渐融合。直接回答增加1790、乾隆、道光等当前证据之外的细节，本次不将未核查细节判作错误。RAG回答限制在已检得历史摘要。',
        'opera-q02':'两组核心声腔名称一致（二黄/二簧异写）。RAG额外的概括及适用限制有music摘要支持；直接组没有本项目来源引用。',
        'opera-q03':'两组核心文武场区分一致。直接组增加许多乐器名称，未在本次语料中逐项核查；RAG使用有依据的京胡/鼓板/锣概述。',
        'opera-q04':'直接组“生主要男性正面角色”是过宽概括，与资料“净丑之外的男性角色”不完全一致。最终RAG四行当完整且有本次五条引用；旧向量版明确资料不足，不能算完整回答。',
        'opera-q05':'两组均为梅兰芳开创的旦角流派。直接组增加“四大名旦之首”等评价，本次不以缺少当前证据直接判定错误；RAG区分流派和行当层级。'
    }
    pairs=[]
    for rag in final['records'][:5]:
        baseline=next(r for r in direct if r['id']==rag['id'])
        record=usage[rag['requestId']]
        pairs.append({'id':rag['id'],'question':rag['question'],'direct':{'requestId':baseline['requestId'],'answer':baseline['answer'],'seconds':baseline['elapsedSeconds'],'usage':baseline['usage'],'estimatedCostCNY':usage[baseline['requestId']]['estimatedUpperCny'],'projectCitations':0},'rag':{'requestId':rag['requestId'],'answer':rag['response']['answer'],'seconds':rag['elapsedSeconds'],'usage':record['usage'],'estimatedCostCNY':record['estimatedUpperCny'],'citationCount':len(rag['response']['citations'])},'assistantAssessment':notes[rag['id']]})
    report={'createdAt':datetime.now(timezone.utc).isoformat(),'scope':'Actual five direct DeepSeek calls versus the same five final hybrid RAG questions; not all twenty questions, human grading or statistically controlled latency benchmark. Runs occurred at different times.','promptVersion':'rag_answer_v2','records':pairs,'summary':{'pairCount':5,'directMeanSeconds':mean(p['direct']['seconds'] for p in pairs),'ragMeanSeconds':mean(p['rag']['seconds'] for p in pairs),'directEstimatedCostCNY':sum(p['direct']['estimatedCostCNY'] for p in pairs),'ragEstimatedCostCNY':sum(p['rag']['estimatedCostCNY'] for p in pairs),'directMeasuredTokens':sum(p['direct']['usage']['total_tokens'] for p in pairs),'ragMeasuredTokens':sum(p['rag']['usage']['total_tokens'] for p in pairs),'ragCanonicalCitationMappingRate':1,'humanAnswerCorrectnessRate':None},'conclusion':'RAG supplies traceable project evidence and constrains answer scope in this sample. Direct responses are not all wrong, RAG is not assumed universally better, and missing evidence is not itself proof of a false assertion.'}
    save('phase-02-direct-vs-rag-five.json',report)
    print(json.dumps({'review':structural['summary'],'comparison':report['summary']},ensure_ascii=True))

if __name__=='__main__': run()
