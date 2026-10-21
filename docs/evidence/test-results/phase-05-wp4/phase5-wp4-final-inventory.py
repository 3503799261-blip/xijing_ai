"""Read-only final knowledge/model/config inventory and controlled-copy comparison."""
import hashlib,json,os,sys
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path('D:/京剧');RUN=ROOT/'.runtime/phase5-wp4';REPO=ROOT/'京剧'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return{f.relative_to(p).as_posix():{'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(p.rglob('*')) if f.is_file()}
before=json.loads((RUN/'knowledge-before.json').read_text('utf-8'))
active=json.loads((ROOT/'.runtime/xijing-ai/active.json').read_text('utf-8'))
generation=ROOT/'.runtime/xijing-ai/generations'/active['generation_id']
from dotenv import dotenv_values
cfg=dotenv_values(ROOT/'.private-config/.env')
after={'at':datetime.now(timezone.utc).isoformat(),'active':active,'generationFiles':tree(generation),'modelFiles':tree(ROOT/'.runtime/models/bge-small-zh-v1.5'),'configurationPresenceOnly':{'privateEnvExists':True,'deepseekKeyPresent':bool(cfg.get('DEEPSEEK_API_KEY')),'neural4dKeyPresent':bool(cfg.get('NEURAL4D_API_KEY')),'generationEnabled':str(cfg.get('NEURAL4D_GENERATION_ENABLED','false')).lower()=='true','protocolVerified':str(cfg.get('NEURAL4D_PROTOCOL_VERIFIED','false')).lower()=='true','actualSecretValuesExported':False},'networkGuardFiles':[]}
after['comparison']={k:before[k]==after[k] for k in ('active','generationFiles','modelFiles')}
after['knowledgeFileDifferences']=[k for k in set(before['generationFiles'])|set(after['generationFiles']) if before['generationFiles'].get(k)!=after['generationFiles'].get(k)]
for d in ('normal-start-01','normal-start-03','normal-start-04','normal-start-05','cold-start-01'):
    p=RUN/d/'network-blocks.jsonl'
    after['networkGuardFiles'].append({'run':d,'blockedExternalEvents':len(p.read_text('utf-8').splitlines()) if p.exists() else 0})
output=RUN/'knowledge-after.json';assert not output.exists();output.write_text(json.dumps(after,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Re-use full logical row hashing to compare restored private databases, without app import.
s=(ROOT/'.runtime/phase5-wp4-state.py').read_text('utf-8')
s=s.replace("ROOT = Path(__file__).resolve().parent.parent", "ROOT = Path('D:/京剧/.runtime/phase5-wp4/recovery-workspace')").replace("REPO = ROOT / '京剧'", "REPO = ROOT / 'source'")
helper=RUN/'restored-state-check.py';assert not helper.exists();helper.write_text(s,encoding='utf-8')
print(json.dumps({'knowledgeComparisons':after['comparison'],'knowledgeFileDifferences':after['knowledgeFileDifferences'],'generationEnabled':after['configurationPresenceOnly']['generationEnabled'],'protocolVerified':after['configurationPresenceOnly']['protocolVerified'],'networkBlocks':after['networkGuardFiles']},ensure_ascii=True))
