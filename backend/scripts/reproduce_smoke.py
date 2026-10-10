"""Explicit cached-environment rebuild/start/real-QA reproduction, not cold install."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
import uuid

def run():
    started=time.perf_counter()
    with socket.socket() as sock:
        if sock.connect_ex(('127.0.0.1',8000)) == 0:
            raise RuntimeError('Stop the existing application before this reproduction check.')
    ingestion=subprocess.run([sys.executable,'-m','backend.scripts.ingest','--rebuild'],capture_output=True,check=True)
    index=json.loads(ingestion.stdout.decode('utf-8').strip().splitlines()[-1])
    process=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8000','--workers','1'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        deadline=time.perf_counter()+60
        health=None
        while time.perf_counter()<deadline:
            if process.poll() is not None: raise RuntimeError('Application process exited during startup.')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health',timeout=2) as response:
                    health=json.load(response)
                break
            except (urllib.error.URLError,TimeoutError): time.sleep(0.25)
        if not health or health['status']!='ready': raise RuntimeError('Health did not report actual readiness.')
        with urllib.request.urlopen('http://127.0.0.1:8000/about.html',timeout=5) as response:
            frontend={'status':response.status,'bytes':len(response.read())}
        request=urllib.request.Request('http://127.0.0.1:8000/api/v1/chat',json.dumps({'question':'京剧主要使用哪两种声腔？'},ensure_ascii=False).encode(),{'Content-Type':'application/json','X-Idempotency-Key':'reproduce-'+str(uuid.uuid4())})
        with urllib.request.urlopen(request,timeout=55) as response: answer=json.load(response)
        assert answer['answer'] and answer['citations'] and not answer['uncertain']
        result={'success':True,'elapsedSeconds':round(time.perf_counter()-started,4),'conditions':['existing verified .venv dependencies','fixed BGE snapshot already downloaded','local private API configuration and previously successful provider probe','application stopped before test','network access to DeepSeek'],'scope':'actual full index rebuild, fresh FastAPI process, HTTP frontend and one real RAG request; dependency installation/model download not included','ingestion':index,'health':health,'frontend':frontend,'answer':answer}
        Path('docs/evidence/test-results/phase-02-cached-reproduction.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'success':True,'elapsedSeconds':result['elapsedSeconds'],'documents':index['documents'],'chunks':index['chunks'],'realAnswerRequestId':answer['requestId']},ensure_ascii=True))
    finally:
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        # All server log fields are status/request ID/timing, never headers or config.
        logs=process.stdout.read().decode('utf-8',errors='replace')
        Path('docs/evidence/test-results/phase-02-cached-reproduction-server.txt').write_text(logs,encoding='utf-8')

if __name__=='__main__': run()
