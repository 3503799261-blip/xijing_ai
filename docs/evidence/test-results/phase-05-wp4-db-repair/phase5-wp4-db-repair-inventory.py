"""Read-only production inventory. No app/env/HTTP imports; writes new evidence only."""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
import sqlite3

ROOT=Path('D:/京剧')
parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--compare',type=Path)
args=parser.parse_args()
assert args.output.resolve().is_relative_to(ROOT/'.runtime') and not args.output.exists()

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as fh:
        for block in iter(lambda:fh.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

def tree(path):
    return {p.relative_to(path).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p)}
            for p in sorted(path.rglob('*')) if p.is_file()}

runtime=ROOT/'.runtime'
active_path=runtime/'xijing-ai/active.json'
active=json.loads(active_path.read_text('utf-8'))
generation=active['generation_id']
assert generation.startswith('gen-') and '/' not in generation and '\\' not in generation
dbs={}
for name,relative in [('agents','xijing-ai/agent-tasks.sqlite3'),('assets','xijing-ai/assets/catalog.sqlite3'),
                      ('budget','xijing-ai/api-budget.sqlite3'),('usage','neural4d-usage.sqlite3')]:
    path=runtime/relative
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        objects=[list(row) for row in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name")]
    dbs[name]={'relative':relative,'bytes':path.stat().st_size,'sha256':sha(path),
               'schemaObjects':objects,'sidecars':{suffix:{'bytes':p.stat().st_size,'sha256':sha(p)}
                  for suffix in ('-wal','-shm','-journal') if (p:=path.with_name(path.name+suffix)).is_file()}}
result={'kind':'WP4_REPAIR_READ_ONLY_PHYSICAL_DB_AND_RESOURCE_INVENTORY',
        'checkedAtUtc':datetime.now(timezone.utc).isoformat(),'clientDate':'2026-10-21',
        'appImported':False,'secretFilesRead':False,'httpRequests':0,'productionWrites':0,
        'databases':dbs,'activeManifestSha256':sha(active_path),
        'generation':generation,'generationFiles':tree(runtime/'xijing-ai/generations'/generation),
        'bgeFiles':tree(runtime/'models/bge-small-zh-v1.5'),
        'assetFiles':tree(runtime/'xijing-ai/assets')}
if args.compare:
    before=json.loads(args.compare.read_text('utf-8'))
    keys=('databases','activeManifestSha256','generation','generationFiles','bgeFiles','assetFiles')
    result['comparison']={k:result[k]==before[k] for k in keys}
args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'output':str(args.output),'generationFiles':len(result['generationFiles']),
                  'bgeFiles':len(result['bgeFiles']),'assetFiles':len(result['assetFiles']),
                  'comparison':result.get('comparison')},ensure_ascii=True))
