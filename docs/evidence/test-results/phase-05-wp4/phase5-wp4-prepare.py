"""WP4 private baseline and controlled local resource copy; never loads app/secrets."""
import hashlib, importlib.metadata as md, json, os, shutil, socket, sqlite3, subprocess, sys, time, zipfile
from pathlib import Path
from datetime import datetime, timezone

WORK=Path('D:/京剧'); REPO=WORK/'京剧'; RUN=WORK/'.runtime/phase5-wp4'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):
    return {f.relative_to(p).as_posix(): {'bytes': f.stat().st_size, 'sha256':digest(f)} for f in sorted(p.rglob('*')) if f.is_file()}
def write(name,data):
    p=RUN/name
    with p.open('x',encoding='utf-8') as h: json.dump(data,h,ensure_ascii=False,indent=2); h.write('\n')
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()
listeners={}
for port in (8000,8011,8012):
    with socket.socket() as s: s.settimeout(.5); listeners[str(port)]=s.connect_ex(('127.0.0.1',port))==0
assert not listeners['8000'], 'Stop and identify existing service before closed-file resource snapshot'
active=json.loads((WORK/'.runtime/xijing-ai/active.json').read_text('utf-8'))
generation=WORK/'.runtime/xijing-ai/generations'/active['generation_id']
model=WORK/'.runtime/models/bge-small-zh-v1.5'
write('environment-baseline.json',{'at':datetime.now(timezone.utc).isoformat(),'repository':str(REPO),'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'status':git('status','--porcelain'),'recentCommits':git('log','--oneline','-8').splitlines(),'python':sys.version,'normalVenvSystemPackages':True,'portsListening':listeners,'disk':{'freeD':shutil.disk_usage(WORK).free},'installedDistributions': sorted([{'name':d.metadata.get('Name'),'version':d.version,'source':'existing installed distribution; no inference of original download source'} for d in md.distributions()],key=lambda x:(x['name'] or '').lower())})
write('knowledge-before.json',{'at':datetime.now(timezone.utc).isoformat(),'active':active,'generationFiles':tree(generation),'modelFiles':tree(model)})
# Inspect only presence and validity; never serialize environment values or credentials.
from dotenv import dotenv_values
values=dotenv_values(WORK/'.private-config/.env')
fields=('DEEPSEEK_API_KEY','NEURAL4D_API_KEY','NEURAL4D_ADMIN_TOKEN')
write('configuration-presence.json',{'at':datetime.now(timezone.utc).isoformat(),'privateEnvExists':True,'secretFields':{k:bool(values.get(k)) for k in fields},'generationEnabled':str(values.get('NEURAL4D_GENERATION_ENABLED','false')).lower()=='true','protocolVerified':str(values.get('NEURAL4D_PROTOCOL_VERIFIED','false')).lower()=='true','externalProviderChecked':False,'valuesSuppressed':True})
isolated=RUN/'recovery-workspace'; isolated.mkdir(exist_ok=False)
archive=RUN/'source-at-start.zip'
subprocess.run(['git','-C',str(REPO),'archive','--format=zip','--output',str(archive),'HEAD'],check=True)
copyrepo=isolated/'source'; copyrepo.mkdir()
with zipfile.ZipFile(archive) as z: z.extractall(copyrepo)
target=isolated/'.runtime/xijing-ai'; target.mkdir(parents=True)
source=WORK/'.runtime/xijing-ai'
restored=[]
for f in sorted(source.rglob('*')):
    if not f.is_file(): continue
    relative=f.relative_to(source)
    if f.name.endswith(('-wal','-shm','-journal','.lock')) or f.name=='.lock': continue
    dest=target/relative; dest.parent.mkdir(parents=True,exist_ok=True)
    if f.suffix in ('.sqlite3','.sqlite','.db'):
        src=sqlite3.connect(f.resolve().as_uri()+'?mode=ro',uri=True)
        dst=sqlite3.connect(dest)
        try: src.backup(dst); assert dst.execute('pragma integrity_check').fetchone()[0]=='ok'
        finally: dst.close(); src.close()
        method='sqlite_online_backup_readonly_source'
    else: shutil.copy2(f,dest); method='byte_copy_while_service_down'
    restored.append({'resource':relative.as_posix(),'method':method,'sourceSha256':digest(f),'copySha256':digest(dest),'bytes':dest.stat().st_size})
ledger=WORK/'.runtime/neural4d-usage.sqlite3'; dest=isolated/'.runtime/neural4d-usage.sqlite3'
src=sqlite3.connect(ledger.resolve().as_uri()+'?mode=ro',uri=True); dst=sqlite3.connect(dest)
try: src.backup(dst); assert dst.execute('pragma integrity_check').fetchone()[0]=='ok'
finally: dst.close();src.close()
shutil.copytree(model,isolated/'.runtime/models/bge-small-zh-v1.5',ignore=shutil.ignore_patterns('.cache'))
envdir=isolated/'.private-config'; envdir.mkdir()
# Credential-free copy of the project's default settings; no production secret copied.
shutil.copyfile(REPO/'.env.example',envdir/'.env')
write('resource-copy-manifest.json',{'at':datetime.now(timezone.utc).isoformat(),'sourceCommit':git('rev-parse','HEAD'),'localRecoveryOnly':True,'crossMachineVerified':False,'secretsCopied':False,'copiedResources':restored,'canonicalLedgerCopyIntegrity':'ok','modelHashMatches':all(digest(f)==digest(isolated/'.runtime/models/bge-small-zh-v1.5'/f.relative_to(model)) for f in model.rglob('*') if f.is_file() and '.cache' not in f.relative_to(model).parts),'notes':['Real source exists and was read with service stopped. This is a new controlled local backup/copy, not a preexisting portable distribution.','SQLite logical backup may have a different binary layout; application rows are checked separately.','No environment keys copied, creation disabled, independent canonical ledger contains original used2 history, never a fresh quota pool.']})
print(json.dumps({'prepared':True,'source':str(copyrepo),'resources':len(restored),'copiedBytes':sum(r['bytes'] for r in restored)},ensure_ascii=True))
