"""Read-only provenance/coverage and protected original-file inventory.

No schema migration, provider requests, app imports or credential-file reads.
"""
import argparse, hashlib, json, sqlite3, struct
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--compare', type=Path)
args=parser.parse_args()
assert args.output.resolve().is_relative_to(ROOT/'.runtime') and not args.output.exists()

def read(relative):
    db=sqlite3.connect((ROOT/'.runtime'/relative).resolve().as_uri()+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    return db

with read('xijing-ai/agent-tasks.sqlite3') as db:
    tasks=[dict(r) for r in db.execute('SELECT * FROM agent_tasks ORDER BY created_at,task_id')]
    steps=[dict(r) for r in db.execute('SELECT * FROM agent_steps')]
    artifacts=[dict(r) for r in db.execute('SELECT * FROM agent_artifacts')]
    events=[dict(r) for r in db.execute('SELECT * FROM agent_events')]
with read('xijing-ai/api-budget.sqlite3') as db:
    calls=[dict(r) for r in db.execute('SELECT * FROM calls')]
by_request={row['request_id']:row for row in calls}
inventory=[]
for task in tasks:
    tid=task['task_id']
    brief=json.loads(task['brief_json'])
    result=json.loads(task['result_json']) if task['result_json'] else {}
    matches=[]
    for stage in ('planner','designer','reviewer'):
        call=by_request.get(tid+':'+stage)
        if call:
            matches.append({'agentId':stage, 'ledgerStatus':call['status'], 'tokenUsageSaved':bool(call['usage_json']),
                            'recordedCostCny':call['cost']})
    own_events=sorted((row for row in events if row['task_id']==tid),key=lambda r:r['sequence'])
    seq=[row['sequence'] for row in own_events]
    inventory.append({'taskId':tid, 'state':task['state'],
                      'sourceCategory': 'persisted_evaluation_run' if task['idempotency_key'].startswith('eval-') else 'persisted_creation_run',
                      'categoryBasis':'idempotency prefix and persisted rows; does not alone attest external provider origin',
                      'paidLedgerCorrelations':matches,'parentTaskId':brief.get('parentTaskId'),
                      'taskTypeStored':False, 'taskLevelStartedAtStored':False,'taskLevelFinishedAtStored':False,
                      'resultSaved':bool(result),'designSaved':bool(result.get('design')),
                      'cultureReviewSaved':bool(result.get('review')),'reviewVerdict':(result.get('review') or {}).get('verdict'),
                      'confirmationSaved':bool(task['confirmation_json']),'humanAccepted':result.get('userConfirmed') is True,
                      'eventCount':len(own_events),'sequenceContiguous':seq==list(range(1,task['sequence']+1)),
                      'stepCount':sum(row['task_id']==tid for row in steps),
                      'artifactAgents':[row['agent_id'] for row in artifacts if row['task_id']==tid]})
protected=[]
for digest,suffix,folder,classification in [
 ('8ef5de8a2f96fbbee9eea66737187e4a2087f88867830891a41464a473d47885','.bin','recovery-quarantine','first_provider_original'),
 ('51fc687e0bde5fdb9074ba4560601057e17e9239f111fd2bc9e0d6601c26260e','.bin','recovery-quarantine','second_provider_original'),
 ('bf9c808c15dbf5464ee67df1cdb3f64f9b2c6b3cd4ee41ecb8a6470a0554654a','.glb','models','first_compatible_viewer'),
 ('5a021ac6338009615e6ea232c5b9001eef6f4cc91d9d87c3eeeb5307526bdfd5','.glb','models','second_compatible_viewer')]:
    path=ROOT/'.runtime/xijing-ai/assets'/folder/(digest+suffix)
    raw=path.read_bytes()
    magic,version,size=struct.unpack('<4sII',raw[:12])
    actual=hashlib.sha256(raw).hexdigest()
    assert actual==digest and magic==b'glTF' and version==2 and size==len(raw)
    protected.append({'classification':classification,'sha256':actual,'sizeBytes':len(raw),'glbHeaderValid':True})
output={'checkedAtUtc':datetime.now(timezone.utc).isoformat(),'readOnly':True,'credentialFilesRead':False,'httpRequests':0,
        'kind':'WP4_PERSISTENCE_PROVENANCE_AND_ORIGINALS','taskInventory':inventory,
        'summary': {'taskCategories':dict(Counter(row['sourceCategory'] for row in inventory)),
                    'allTasksHaveLedgerCorrelation':all(row['paidLedgerCorrelations'] for row in inventory),
                    'correlatedCalls':sum(len(row['paidLedgerCorrelations']) for row in inventory),
                    'unattributedHistoricalCalls':len(calls)-sum(len(row['paidLedgerCorrelations']) for row in inventory),
                    'taskResultCount':sum(row['resultSaved'] for row in inventory),
                    'designCount':sum(row['designSaved'] for row in inventory),
                    'reviewCount':sum(row['cultureReviewSaved'] for row in inventory),
                    'humanAcceptanceCount':sum(row['humanAccepted'] for row in inventory),
                    'allEventSequencesContiguous':all(row['sequenceContiguous'] for row in inventory),
                    'allTasksHaveFourSeededSteps':all(row['stepCount']==4 for row in inventory)},
        'protectedModelsAndOriginals':protected,
        'limitations':['No authenticated per-task provider-origin discriminator is stored; ledger correlations and evaluation prefixes are evidence, not independent provider attestation.',
                       'No Meeting/Decision/Timeline tables exist; real timeline is agent_events. Step inputs are not independently persisted in agent_steps.',
                       'Research artifact in agent_artifacts is persisted; query-only history must not rerun RAG.'],
        'orphanRows': {name:sum(row['task_id'] not in {t['task_id'] for t in tasks} for row in rows)
                       for name,rows in [('steps',steps),('artifacts',artifacts),('events',events)]}}
if args.compare:
    before=json.loads(args.compare.read_text('utf-8'))
    fields=['taskInventory','summary','protectedModelsAndOriginals','orphanRows']
    output['comparison']={k:before[k]==output[k] for k in fields}
args.output.parent.mkdir(parents=True,exist_ok=True)
with args.output.open('x',encoding='utf-8') as handle:
    json.dump(output,handle,ensure_ascii=False,indent=2);handle.write('\n')
print(json.dumps({'output':str(args.output),'summary':output['summary'],'orphanRows':output['orphanRows'],'comparison':output.get('comparison')},ensure_ascii=True,indent=2))
