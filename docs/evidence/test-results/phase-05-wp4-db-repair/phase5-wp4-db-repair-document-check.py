"""Read-only gates for explicitly named repair evidence and protected history."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote,urlsplit
import xml.etree.ElementTree as ET
REPO=Path('D:/京剧/京剧');RUNTIME=Path('D:/京剧/.runtime')
OUT=REPO/'docs/evidence/test-results/phase-05-wp4-db-repair'
checks=[]
def check(name,condition):checks.append({'name':name,'status':'PASS' if condition else 'FAIL'})
def git(*args):return subprocess.check_output(['git',*args],cwd=REPO,text=True,encoding='utf8').strip()
manifest=json.loads((OUT/'archive-manifest.json').read_text('utf8'))
for item in manifest['files']:
 raw=(OUT/item['file']).read_bytes()
 check('archive_hash:'+item['file'],hashlib.sha256(raw).hexdigest()==item['archiveSha256'])
 check('no_private_binary:'+item['file'],(OUT/item['file']).suffix in ('.json','.jsonl','.txt','.xml','.py','.mjs'))
 if item['file'].endswith('.json'):json.loads(raw)
 elif item['file'].endswith('.jsonl'):
  for row in raw.splitlines():json.loads(row)
for item in json.loads((OUT/'screenshot-manifest.json').read_text('utf8'))['screenshots']:
 p=RUNTIME/item['privateRuntimeRelative']
 check('private_screenshot_hash:'+p.name,hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'])
prompts=REPO/'docs/prompts/phase-05'
meta=json.loads((prompts/'17-wp4-database-repair-export-metadata.json').read_text('utf8'))
check('original_prompt_hash',hashlib.sha256((prompts/'15-wp4-database-repair-user-request.txt').read_bytes()).hexdigest()==meta['requestSha256'])
data=(prompts/'16-wp4-database-repair-public-conversation.jsonl').read_bytes()
check('public_snapshot_hash',hashlib.sha256(data).hexdigest()==meta['publicSnapshotSha256'])
for line in data.splitlines():json.loads(line)
check('no_exported_hidden_reasoning',meta['hiddenReasoningExported'] is False)
for document in (REPO/'README.md',REPO/'docs/reports/phase-05-work-package-04.md',REPO/'docs/evidence/test-results/phase-05-wp4-test-report.md',prompts/'README.md'):
 text=document.read_text('utf8')
 for target in re.findall(r'\]\(([^\n)]+)\)',text):
  target=target.strip('<>')
  if urlsplit(target).scheme or target.startswith('#'):continue
  plain=unquote(target.split('#')[0])
  check('local_link:'+document.name+':'+target,(document.parent/plain).is_file())
for commit in ('04b2c571e068ec0b26205fcce0c075395caeebce','f58888b','ea0f4fc','9e3516d','f8a1f47','60e1590','84b1d23','834483d','3b40aa2','ae2783e','452a0c2'):
 check('ancestor:'+commit,subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],cwd=REPO).returncode==0)
changed=git('diff','--name-only','3b40aa2').splitlines()
check('no_frontend_or_models_modified',not any(name.endswith(('.html','.css','.js','.glb','.bin','.safetensors')) for name in changed))
check('no_dependency_or_corpus_modified',not any(name=='backend/requirements.txt' or name.startswith('knowledge/') for name in changed))
check('branch_preserved',git('branch','--show-current')=='feature/phase5-competition-delivery')
for file,total in [('full-final-isolation-result.json',754),('targeted-final-isolation-result.json',41)]:
 result=json.loads((OUT/file).read_text('utf8'))
 check('real_results:'+file,result['pytestExitCode']==0 and result['passed']==total and result['failedReports']==0 and result['skippedReports']==0 and not any(result['auditCounts'].values()))
root=ET.parse(OUT/'full-final-pytest.xml').getroot();suite=root.find('testsuite') if root.tag=='testsuites' else root
check('junit754',int(suite.attrib['tests'])==754 and int(suite.attrib['failures'])==0 and int(suite.attrib['errors'])==0)
check('all_production_logical_unchanged',json.loads((OUT/'state-after.json').read_text('utf8'))['comparison']['allProtectedUnchanged'])
check('all_physical_unchanged',all(json.loads((OUT/'physical-final-comparison.json').read_text('utf8'))['comparison'].values()))
check('field42',all(json.loads((OUT/('field-'+s+'-probe.json')).read_text('utf8'))['failed']==0 for s in ('corrupt','restored','misconfigured','recovered')))
check('source80same',json.loads((OUT/'field-final-summary.json').read_text('utf8'))['sourceComparison']['allSame'])
sys.path.insert(0,str(REPO/'scripts'))
from check_public_secrets import scan
secrets=scan(REPO);check('public_secret_patterns',secrets['success'])
result={'atUtc':datetime.now(timezone.utc).isoformat(),'scope':'documentation, hashes, ancestry and result consistency; not additional app test cases','headAtCheck':git('rev-parse','HEAD'),'branch':git('branch','--show-current'),'pendingStatusAtCheck':git('status','--short'),'passed':sum(c['status']=='PASS' for c in checks),'failed':sum(c['status']=='FAIL' for c in checks),'checks':checks,'secretScan':secrets,'mergePushPerformed':False,'paidApiCalls':0,'neural4dCalls':0}
(OUT/'documentation-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'passed':result['passed'],'failed':result['failed'],'secretFindings':len(secrets['findings'])}))
raise SystemExit(0 if not result['failed'] else 1)
