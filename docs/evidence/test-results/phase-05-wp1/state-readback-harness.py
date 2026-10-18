"""Read-only WP1 state snapshot. No app imports, HTTP, credentials or DB writes."""
import argparse, hashlib, json, sqlite3, struct, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

repo=Path('D:/京剧/京剧'); work=repo.parent
def database(path):
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True); db.execute('PRAGMA query_only=ON'); return db
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path,required=True); args=parser.parse_args()
assert not args.output.exists(), 'Choose a new output; preserve existing evidence'
with database(work/'.runtime/neural4d-usage.sqlite3') as db:
    policy=db.execute('SELECT max_attempts,historical_used FROM neural4d_usage_policy').fetchone()
    states=[list(r) for r in db.execute('SELECT state,count(*) FROM neural4d_creation_attempts GROUP BY state')]
    pending=db.execute('SELECT count(*) FROM neural4d_model_approvals WHERE consumed_attempt_id IS NULL').fetchone()[0]
    operations=[list(r) for r in db.execute('SELECT operation,count(*),sum(coalesce(actual_credits,0)) FROM neural4d_operational_requests GROUP BY operation ORDER BY operation')]
assert policy==(3,0) and states==[['SUCCEEDED',2]] and pending==0
with database(work/'.runtime/xijing-ai/api-budget.sqlite3') as db: calls=db.execute('SELECT count(*) FROM calls').fetchone()[0]
with database(work/'.runtime/xijing-ai/agent-tasks.sqlite3') as db: task_states=[list(r) for r in db.execute('SELECT state,count(*) FROM agent_tasks GROUP BY state')]
assert not any(state in ['waiting','running'] for state,count in task_states)
flags={}
for line in (work/'.private-config/.env').read_text('utf-8-sig').splitlines():
    if line.startswith(('NEURAL4D_GENERATION_ENABLED=','NEURAL4D_PROTOCOL_VERIFIED=')):
        name,value=line.split('=',1); flags[name]=value.strip().lower()
assert flags['NEURAL4D_GENERATION_ENABLED']=='false' and flags['NEURAL4D_PROTOCOL_VERIFIED']=='false'
files=[]
for relative, expected in [
 ('models/bf9c808c15dbf5464ee67df1cdb3f64f9b2c6b3cd4ee41ecb8a6470a0554654a.glb','bf9c808c15dbf5464ee67df1cdb3f64f9b2c6b3cd4ee41ecb8a6470a0554654a'),
 ('models/5a021ac6338009615e6ea232c5b9001eef6f4cc91d9d87c3eeeb5307526bdfd5.glb','5a021ac6338009615e6ea232c5b9001eef6f4cc91d9d87c3eeeb5307526bdfd5'),
 ('recovery-quarantine/8ef5de8a2f96fbbee9eea66737187e4a2087f88867830891a41464a473d47885.bin','8ef5de8a2f96fbbee9eea66737187e4a2087f88867830891a41464a473d47885'),
 ('recovery-quarantine/51fc687e0bde5fdb9074ba4560601057e17e9239f111fd2bc9e0d6601c26260e.bin','51fc687e0bde5fdb9074ba4560601057e17e9239f111fd2bc9e0d6601c26260e')]:
    path=work/'.runtime/xijing-ai/assets'/relative; raw=path.read_bytes(); magic,version,size=struct.unpack('<4sII',raw[:12])
    assert hashlib.sha256(raw).hexdigest()==expected and magic==b'glTF' and version==2 and size==len(raw)
    files.append({'relativeRuntimeAsset':relative,'sha256':expected,'sizeBytes':len(raw),'glbHeaderMatches':True,'privateFileNotCopied':True})
html={name:digest(repo/name) for name in ['index.html','history.html','roles.html','facial.html','music.html','gallery.html','video.html','about.html']}
record={'checkedAtUtc':datetime.now(timezone.utc).isoformat(),'clientReviewDate':'2026-10-18','kind':'WP1_READ_ONLY_STATE_SNAPSHOT','python':sys.version.split()[0], 'branch':subprocess.check_output(['git','branch','--show-current'],cwd=repo).decode().strip(),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo).decode().strip(),'maxAttempts':3,'used':2,'remainingUnused':1,'externalHistoricalUsed':0,'states':states,'unconsumedApprovals':pending,'operations':operations,'realHttpRequests':sum(r[1] for r in operations),'recordedCredits':sum(r[2] or 0 for r in operations),'llmCalls':calls,'agentStates':task_states,'safeFlags':flags,'modelsAndOriginals':files,'htmlSha256':html,'paidCallsBySnapshot':0,'databaseWritesBySnapshot':0}
args.output.parent.mkdir(parents=True,exist_ok=True)
with args.output.open('x',encoding='utf-8') as f: json.dump(record,f,ensure_ascii=False,indent=2); f.write('\n')
print(json.dumps({'output':str(args.output),'used':2,'remaining':1,'llmCalls':calls,'modelAndOriginalFilesVerified':len(files),'realHttpRequests':record['realHttpRequests']}))
