"""WP1 documentation/config/file integrity only; no API or production writes."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,re,sqlite3,subprocess,sys,xml.etree.ElementTree as ET
repo=Path.cwd(); out=repo/'docs/evidence/test-results/phase-05-wp1'
sys.path.insert(0,str(repo))
from backend.app.config import Settings
result={'checkedAtUtc':datetime.now(timezone.utc).isoformat(),'kind':'WP1_DOCUMENTATION_AND_ARCHIVE_CHECK','checks':[],'paidCalls':0,'supplierCalls':0}
def check(name,condition,**extra):
    result['checks'].append({'name':name,'passed':bool(condition),**extra})
    if not condition: raise AssertionError(name)
readme=(repo/'README.md').read_text('utf-8'); env=(repo/'.env.example').read_text('utf-8')
check('readme-current-status',all(s in readme for s in ['当前仅实施WP1','已用2/3','第三次用户决定不执行','创建保持关闭']))
check('obsolete-current-claims-removed',not any(s in readme for s in ['当前交付Phase 4的PARTIAL','项目仍占用1/3','仍已用1/3','尚未提交模型。历史仍未知']))
settings=Settings(_env_file=repo/'.env.example',deepseek_api_key='',neural4d_api_key='',neural4d_admin_token='')
check('template-uses-existing-portable-defaults',settings.rag_data_dir==repo.parent/'.runtime/xijing-ai' and settings.embedding_model_path==repo.parent/'.runtime/models/bge-small-zh-v1.5' and not re.search(r'^(?:RAG_DATA_DIR|EMBEDDING_MODEL_PATH)=',env,re.M))
check('template-real-generation-off',not settings.neural4d_generation_enabled and not settings.neural4d_protocol_verified)
modules=sorted(set(re.findall(r'-m\s+(backend\.[A-Za-z0-9_.]+)',readme)))
check('readme-python-modules-exist',all((repo/(name.replace('.','/')+'.py')).is_file() for name in modules),modules=modules)
scripts=sorted(set(re.findall(r'(scripts/[A-Za-z0-9_./-]+\.(?:py|mjs))',readme)))
check('readme-script-references-exist',all((repo/name).is_file() for name in scripts),scripts=scripts)
before=json.loads((out/'before-state.json').read_text('utf-8'));after=json.loads((out/'after-state.json').read_text('utf-8'))
for field in ['maxAttempts','used','remainingUnused','states','unconsumedApprovals','operations','realHttpRequests','recordedCredits','llmCalls','agentStates','safeFlags','modelsAndOriginals','htmlSha256']:
    check('unchanged-'+field,before[field]==after[field])
check('protected-product-and-old-reports-unchanged',not subprocess.check_output(['git','diff','8d5de53','--name-only','--','backend/app','backend/tests','js','css','*.html','knowledge','docs/reports/phase-0[1234]*'],cwd=repo))
catalog=repo.parent/'.runtime/xijing-ai/assets/catalog.sqlite3'
with sqlite3.connect(catalog.as_uri()+'?mode=ro',uri=True) as db:
    db.execute('PRAGMA query_only=ON')
    models=[json.loads(r[0]) for r in db.execute('SELECT content_json FROM asset_models')]
    assets=[json.loads(r[0]) for r in db.execute('SELECT content_json FROM character_assets')]
real=[m for m in models if m.get('origin') in ['neural4d','neural4d_technical_test']]
check('exactly-two-real-model-records',len(real)==2)
internal=next(m for m in real if m['modelId']=='3777a880-fc8c-4766-aade-948d20c6b8f0')
formal=next(m for m in real if m['modelId']=='1fa0b519-caf4-4009-aec2-f20b0f9a3523')
check('internal-role-not-forced',internal.get('assetId') is None and internal.get('characterId') is None and internal.get('internalUseOnly') is True)
asset=next(a for a in assets if a['assetId']==formal['assetId'])
check('formal-role-model-lineage',asset['assetId']=='9e2b42e1-bbad-4a2f-ab1b-aeda18015dee' and asset['sourceTaskId']=='ca7007e7-e535-4b1f-a9b6-1932f10e20b4' and asset['styleMode']=='realistic' and formal['providerTaskId']=='8735f32e-097e-488c-962f-f11e64af7741')
check('enterprise-no-fabricated-instance',all(a['mode']=='personal' and not a.get('enterpriseBrief') for a in assets),registeredPersonalAssets=len(assets),enterpriseAssets=0)
xml=ET.parse(out/'offline-final.xml'); suites=list(xml.getroot().iter('testsuite'))
check('completed-full-pytest',sum(int(s.get('tests',0)) for s in suites)==675 and sum(int(s.get('errors',0))+int(s.get('failures',0))+int(s.get('skipped',0)) for s in suites)==0)
offline=json.loads((out/'offline-run-04-isolation-result.json').read_text('utf-8'))
check('test-collection-network-and-storage-isolated',offline['pytestReturned'] and offline['pytestExitCode']==0 and all(offline['isolation'].values()) and all(v==0 for v in offline['auditCounts'].values()))
for name,count in [('phase2',25),('phase3',25),('phase4',36)]:
    data=json.loads((out/(name+'-frontend.json')).read_text('utf-8'));check(name+'-frontend',data['passed']==count and data['failed']==0)
local=json.loads((out/'local-smoke.json').read_text('utf-8'));check('local-free-checks',local['passed']==8 and local['failed']==0)
browser=json.loads((out/'browser-smoke.json').read_text('utf-8'));check('browser-four-groups',len(browser['tests'])==4 and all(v['pass'] for v in browser['tests'].values()))
meta=json.loads((repo/'docs/prompts/phase-05/05-wp1-export-metadata.json').read_text('utf-8'))
check('raw-wp1-prompt-hash',hashlib.sha256((repo/'docs/prompts/phase-05/03-wp1-approved-user-request.txt').read_bytes()).hexdigest()==meta['promptSha256'])
check('public-wp1-snapshot-hash',hashlib.sha256((repo/'docs/prompts/phase-05/04-wp1-public-conversation.jsonl').read_bytes()).hexdigest()==meta['publicSnapshotSha256'])
changed=subprocess.check_output(['git','diff','8d5de53','--name-only','-z'],cwd=repo).decode().split('\0')
new=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=repo).decode().split('\0')
paths=[repo/p for p in sorted(set(changed+new)) if p]
def allowed(path):
    name=path.relative_to(repo).as_posix()
    return name in ['README.md','.env.example','docs/reports/phase-05-work-package-01.md','docs/evidence/test-results/phase-05-wp1-test-report.md'] or name.startswith(('docs/evidence/test-results/phase-05-wp1/','docs/prompts/phase-05/'))
check('only-allowed-wp1-files',all(allowed(p) for p in paths),fileCount=len(paths))
check('no-private-binary-added',not any(p.suffix.lower() in ['.glb','.gltf','.png','.jpg','.jpeg','.sqlite','.sqlite3','.db','.bin'] for p in paths))
for p in paths:
    raw=p.read_bytes()
    check('no-sensitive-pattern-'+p.name,not re.search(rb'\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{16,}',raw) and not re.search(rb'https?://cos\.(?:neural4d\.com|zmkj\.com)/[^\s"\\<>]*\?',raw) and not re.search(rb'C:[/\\](?:Users|users)[/\\]35037',raw))
result['passed']=len(result['checks']);result['failed']=0;result['skipped']=0
target=out/'static-and-archive-check.json'
target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8')
links=0
for path in paths:
    if path.suffix!='.md':continue
    for link in re.findall(r'\]\(([^)]+)\)',path.read_text('utf-8')):
        if link.startswith(('http:','https:','#')):continue
        assert (path.parent/link.split('#',1)[0]).resolve().exists(), f'Missing local link in {path.name}: {link}'
        links+=1
result['localLinksVerified']=links
target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps({'documentationChecks':result['passed'],'failed':0,'skipped':0,'localLinksVerified':links,'codeAndHistoricalReportsUnchanged':True,'newPaidCalls':0}))
