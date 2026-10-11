"""Read-only loopback HTTP regression and Phase 1 culture-file integrity check."""
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request
import urllib.error
from urllib.parse import urljoin, urlparse, unquote, quote

BASE = 'http://127.0.0.1:8000/'
PHASE1 = '04b2c571e068ec0b26205fcce0c075395caeebce'
PAGES = ['index.html','history.html','roles.html','facial.html','music.html','video.html','gallery.html','about.html']

class Links(HTMLParser):
    def __init__(self): super().__init__(); self.resources=set(); self.links=[]
    def handle_starttag(self, tag, attrs):
        data=dict(attrs)
        for attribute in ('src', 'poster'):
            if data.get(attribute): self.resources.add(data[attribute])
        if tag == 'link' and data.get('href'): self.resources.add(data['href'])
        if tag == 'a' and data.get('href'): self.links.append(data['href'])

def fetch(url, partial=False):
    try:
        req=urllib.request.Request(quote(url, safe=':/?=&%'), headers={'Range':'bytes=0-0'} if partial else {})
        with urllib.request.urlopen(req, timeout=15) as response:
            response.read(1)
            return {'status':response.status,'contentType':response.headers.get('Content-Type')}
    except urllib.error.HTTPError as exc: return {'status':exc.code}
    except (urllib.error.URLError,TimeoutError): return {'status':None,'error':'NETWORK_FAILURE'}

def run(output=None):
    root=Path(__file__).resolve().parents[1]
    resources=set(); report={'pages':[],'assets':[],'protectedPaths':[],'cultureIntegrity':[]}
    for page in PAGES:
        parser=Links(); parser.feed((root/page).read_text(encoding='utf-8'))
        local=[]
        for resource in parser.resources:
            url=urljoin(BASE+page,resource)
            if urlparse(url).netloc=='127.0.0.1:8000': resources.add(url)
        for link in parser.links:
            url=urljoin(BASE+page,link)
            if urlparse(url).netloc=='127.0.0.1:8000' and urlparse(url).path.endswith('.html'): local.append(url)
        report['pages'].append({'page':page,**fetch(BASE+page),'localPageLinks':len(local),'linkTargetsExist':all((root/unquote(urlparse(url).path).lstrip('/')).is_file() for url in local)})
        if page!='about.html':
            original=subprocess.run(['git','show',PHASE1+':'+page],cwd=root,capture_output=True,check=True).stdout
            report['cultureIntegrity'].append({'page':page,'byteIdenticalToPhase1':original==(root/page).read_bytes(),'sha256':hashlib.sha256(original).hexdigest()})
    for resource in sorted(resources): report['assets'].append({'url':resource,**fetch(resource, partial=True)})
    for path in ['.env','.git/config','backend/app/config.py','knowledge/sources.json','docs/reports/phase-02.md','.venv/pyvenv.cfg']:
        report['protectedPaths'].append({'path':path,**fetch(BASE+path)})
    report['health']=json.load(urllib.request.urlopen(BASE+'api/v1/health',timeout=15))
    report['capabilities']=json.load(urllib.request.urlopen(BASE+'api/v1/capabilities',timeout=15))
    report['success']=all(r['status']==200 and r['linkTargetsExist'] for r in report['pages']) and all(r['status'] in (200,206) for r in report['assets']) and all(r['status']==404 for r in report['protectedPaths']) and all(r['byteIdenticalToPhase1'] for r in report['cultureIntegrity'])
    report['scope']='actual loopback HTTP; public local resource GET with Range; remote embedded video playback not included'
    (output or root/'docs/evidence/test-results/phase-02-http-regression.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'success':report['success'],'pages':len(report['pages']),'assets':len(report['assets']),'protectedPaths':len(report['protectedPaths']),'cultureByteIdentical':all(r['byteIdenticalToPhase1'] for r in report['cultureIntegrity'])}))
    return report['success']

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Actual local HTTP resources and culture integrity, no paid calls')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    raise SystemExit(0 if run(args.output) else 1)
