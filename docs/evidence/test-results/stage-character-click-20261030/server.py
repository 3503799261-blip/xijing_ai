"""Independent stage-only verification; no business app, database or provider."""
from pathlib import Path
import sys,socket
ROOT=Path(r'D:\京剧\京剧');sys.path.insert(0,str(ROOT))
def audit(event,args):
 if event=='socket.connect' and isinstance(args[1],tuple) and args[1][0] not in ('127.0.0.1','localhost','::1'):
  raise RuntimeError('Stage verification refuses nonlocal network')
sys.addaudithook(audit)
from fastapi import FastAPI
from fastapi.responses import FileResponse,JSONResponse
from backend.app.stage_assets import register_stage
app=FastAPI();register_stage(app,ROOT.parent/'.runtime/digital-stage/assets')
@app.get('/{path:path}')
async def static(path:str):
 if path.startswith('api/'):
  return JSONResponse({'error':{'code':'STAGE_ONLY_TEST','message':'独立测试仅提供戏台与静态页面。'}},status_code=503)
 if path=='favicon.ico':return JSONResponse({},status_code=204)
 p=(ROOT/(path or 'index.html')).resolve()
 allowed=p.parent==ROOT and p.name in ['index.html','history.html','roles.html','facial.html','music.html','video.html','gallery.html','about.html'] or any(p.is_relative_to(ROOT/d) for d in ['css','js','images','audio','media'])
 if not allowed or not p.is_file():return JSONResponse({},status_code=404)
 return FileResponse(p,headers={'Cache-Control':'no-store'})
if __name__=='__main__':
 import uvicorn
 uvicorn.run(app,host='127.0.0.1',port=8012,workers=1,access_log=False)
