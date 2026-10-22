"""Read-only validated resource source -> isolated field copy. No app imports."""
import hashlib,json,os,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path('D:/京剧')
REPO=ROOT/'京剧'
DEST=ROOT/'.runtime/phase5-wp4-db-repair-field-01'
OLD=ROOT
# Execute only after parent confirms the 8000 source service is fully stopped.
assert os.environ.get('WP4_SOURCE_STOP_CONFIRMED')=='true','Source shutdown confirmation required'
BEFORE=ROOT/'.runtime/phase5-wp4-db-repair-baseline-01/physical-resources-before.json'
assert not DEST.exists()
baseline=json.loads(BEFORE.read_text('utf-8'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def tree(p):return{f.relative_to(p).as_posix():{'bytes':f.stat().st_size,'sha256':sha(f)}for f in sorted(p.rglob('*'))if f.is_file()}
generation=baseline['generation']
checks={'generationFiles':tree(OLD/'.runtime/xijing-ai/generations'/generation)==baseline['generationFiles'],
        'bgeFiles':tree(OLD/'.runtime/models/bge-small-zh-v1.5')==baseline['bgeFiles'],
        'assetFiles':tree(OLD/'.runtime/xijing-ai/assets')==baseline['assetFiles']}
for name,row in baseline['databases'].items():
 checks['db:'+name]=sha(OLD/'.runtime'/row['relative'])==row['sha256']
assert all(checks.values()),json.dumps(checks)
DEST.mkdir()
workspace=DEST/'workspace'
source=workspace/'source'
source.mkdir(parents=True)
tracked=subprocess.check_output(['git','ls-files','-z'],cwd=REPO).decode('utf-8').split('\0')
files=[p for p in tracked if p]
files+=['backend/app/database.py','backend/scripts/initialize_business_databases.py']
inventory={}
for relative in sorted(set(files)):
 p=REPO/relative
 assert p.is_file() and not relative.endswith('.env') and not relative.startswith(('.private-config/','.runtime/','.git/'))
 target=source/relative
 target.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(p,target)
 inventory[relative]={'sha256':sha(target),'bytes':target.stat().st_size}
(workspace/'.runtime/xijing-ai').mkdir(parents=True)
shutil.copytree(OLD/'.runtime/xijing-ai/assets',workspace/'.runtime/xijing-ai/assets')
shutil.copytree(OLD/'.runtime/xijing-ai/generations',workspace/'.runtime/xijing-ai/generations')
shutil.copytree(OLD/'.runtime/models/bge-small-zh-v1.5',workspace/'.runtime/models/bge-small-zh-v1.5')
for relative in ('xijing-ai/active.json','xijing-ai/agent-tasks.sqlite3','xijing-ai/api-budget.sqlite3','neural4d-usage.sqlite3'):
 shutil.copy2(OLD/'.runtime'/relative,workspace/'.runtime'/relative)
assert tree(workspace/'.runtime/xijing-ai/generations'/generation)==baseline['generationFiles']
assert tree(workspace/'.runtime/models/bge-small-zh-v1.5')==baseline['bgeFiles']
assert tree(workspace/'.runtime/xijing-ai/assets')==baseline['assetFiles']
private=workspace/'.private-config'
private.mkdir()
(private/'.env').write_text('\n'.join([
 '# Isolated field probe, no credentials, no provider access.',
 'DEEPSEEK_API_KEY=', 'NEURAL4D_API_KEY=', 'NEURAL4D_ADMIN_TOKEN=',
 'NEURAL4D_GENERATION_ENABLED=false','NEURAL4D_PROTOCOL_VERIFIED=false',
 'AGENT_WORKFLOW_ENABLED=false',
 'RAG_DATA_DIR='+str(workspace/'.runtime/xijing-ai'),
 'EMBEDDING_MODEL_PATH='+str(workspace/'.runtime/models/bge-small-zh-v1.5'),
 'HF_HUB_OFFLINE=1','TRANSFORMERS_OFFLINE=1',
])+'\n',encoding='utf-8')
agent=workspace/'.runtime/xijing-ai/agent-tasks.sqlite3'
shutil.copy2(agent,DEST/'valid-agent.sqlite3')
agent.write_bytes(b'WP4 database repair: deliberate corruption in isolated field copy only.')
record={'kind':'WP4_DB_REPAIR_FIELD_COPY_PREPARATION','atUtc':datetime.now(timezone.utc).isoformat(),
        'sourceHead':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        'currentWorkingTreeCopied':True,'resourceSource':'production runtime after controlled source service shutdown, verified byte-for-byte against readonly baseline',
        'sourceValidatedAgainstProductionReadOnlyBaseline':checks,'sourceFiles':inventory,
        'isolatedAgentCorruptSha256':sha(agent),'preservedValidAgentSha256':sha(DEST/'valid-agent.sqlite3'),
        'businessBaseline':{name:{'sha256':sha(workspace/'.runtime'/row['relative']),
                                  'relative':row['relative']}for name,row in baseline['databases'].items()},
        'scope':'All later Agent mutation confined to independent field-copy; zero production app import/write',
        'privateConfig':'new empty keys only, not copied original secrets', 'paidApiCalls':0,'neural4dCalls':0}
(DEST/'preparation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'destination':str(DEST),'sourceFiles':len(inventory),'sourceChecks':checks,
                  'corruptHash':record['isolatedAgentCorruptSha256']},ensure_ascii=True))
