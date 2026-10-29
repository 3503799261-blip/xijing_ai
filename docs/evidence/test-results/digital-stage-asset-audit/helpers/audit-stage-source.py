from pathlib import Path
from collections import Counter
import json, hashlib, struct, time
from PIL import Image
from datetime import datetime, timezone
root=Path(r'D:\京剧\京剧\中式古戏台SU模型')
out=Path(r'D:\京剧\.runtime\stage-asset-audit-20261029'); out.mkdir(parents=True,exist_ok=True)
started=time.perf_counter(); files=[]
for p in sorted(root.rglob('*')):
 if not p.is_file(): continue
 h=hashlib.sha256()
 with p.open('rb') as f:
  while chunk:=f.read(1024*1024): h.update(chunk)
 info={'relative':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':h.hexdigest()}
 with p.open('rb') as f: header=f.read(32)
 if p.suffix.lower() in ('.fbx','.c4d','.skp'): info['headerHex']=header.hex(); info['headerText']=header.decode('ascii','replace')
 if p.suffix.lower()=='.fbx' and header.startswith(b'Kaydara FBX Binary  \x00\x1a\x00'): info['fbxBinaryVersion']=struct.unpack('<I',header[23:27])[0]
 if p.suffix.lower() in ('.jpg','.jpeg','.png'):
  try:
   Image.MAX_IMAGE_PIXELS=None
   with Image.open(p) as im: info['image']={'format':im.format,'width':im.width,'height':im.height,'mode':im.mode,'pixelCount':im.width*im.height}
  except Exception as e: info['imageHeaderError']=type(e).__name__
 files.append(info)
counts=Counter(); arities=Counter(); lo=[float('inf')]*3; hi=[float('-inf')]*3; materials=set(); mtllib=[]; object_names=set(); negative_faces=0; bad_vertex_lines=0; face_min=None; face_max=0
with (root/'戏台.obj').open('r',encoding='utf-8-sig',errors='strict') as f:
 for lineno,line in enumerate(f,1):
  if line.startswith('v '):
   counts['vertices']+=1
   try:
    v=list(map(float,line.split()[1:4]))
    for i in range(3): lo[i]=min(lo[i],v[i]); hi[i]=max(hi[i],v[i])
   except (ValueError,IndexError): bad_vertex_lines+=1
  elif line.startswith('vn '): counts['normals']+=1
  elif line.startswith('vt '): counts['uvs']+=1
  elif line.startswith('f '):
   counts['faces']+=1; parts=line.split()[1:]; arities[len(parts)]+=1; counts['fanTriangulationEstimate']+=max(0,len(parts)-2)
   for term in parts:
    try:
     idx=int(term.split('/')[0]); face_max=max(face_max,idx); face_min=idx if face_min is None else min(face_min,idx)
     if idx<0: negative_faces+=1
     if idx==0: counts['zeroVertexIndices']+=1
    except ValueError: counts['invalidFaceTokens']+=1
  elif line.startswith('o '): counts['objects']+=1; object_names.add(line[2:].strip())
  elif line.startswith('g '): counts['groups']+=1
  elif line.startswith('usemtl '): materials.add(line[7:].strip())
  elif line.startswith('mtllib '): mtllib.append(line[7:].strip())
mtl=(root/'戏台.mtl').read_text(encoding='utf-8-sig'); names=[]; refs=[]; current=None
for lineno,line in enumerate(mtl.splitlines(),1):
 parts=line.split(None,1)
 if len(parts)!=2: continue
 key,value=parts
 if key=='newmtl': names.append(value); current=value
 if key.lower().startswith('map_') or key.lower() in ('bump','disp','decal','refl'):
  raw=value.strip(); direct=(root/raw); tex=(root/'tex'/raw)
  refs.append({'line':lineno,'material':current,'directive':key,'value':raw,'directRelativeExists':direct.is_file(),'texFallbackExists':tex.is_file(),'externalUrl':raw.lower().startswith(('http:','https:','file:','data:')),'absoluteOrTraversal':Path(raw).is_absolute() or '..' in Path(raw).parts})
result={'checkedAtUtc':datetime.now(timezone.utc).isoformat(),'kind':'READ_ONLY_STAGE_SOURCE_AUDIT','sourceDirectory':str(root),'elapsedSeconds':round(time.perf_counter()-started,3),'fileCount':len(files),'totalBytes':sum(x['bytes'] for x in files),'files':files,'obj':{**counts,'faceArityHistogram':dict(arities),'bounds':{'min':lo,'max':hi,'size':[hi[i]-lo[i] for i in range(3)]},'usedMaterials':sorted(materials),'distinctObjectNames':len(object_names),'mtllib':mtllib,'minVertexIndex':face_min,'maxVertexIndex':face_max,'negativeIndexTerms':negative_faces,'invalidVertexLines':bad_vertex_lines},'mtl':{'materialCount':len(names),'declaredMaterials':names,'unknownUsedMaterials':sorted(materials-set(names)),'unusedMaterials':sorted(set(names)-materials),'textureReferences':refs,'missingRelativeReferences':sum(not v['directRelativeExists'] for v in refs),'missingEvenWithTexFallback':sum(not(v['directRelativeExists'] or v['texFallbackExists']) for v in refs),'externalOrUnsafeReferences':sum(v['externalUrl'] or v['absoluteOrTraversal'] for v in refs)},'licenseOrReadmeFiles':[p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and (p.suffix.lower() in ('.txt','.md','.pdf','.doc','.docx') or any(t in p.name.lower() for t in ('license','readme','版权','许可','说明')))],'modifiedSourceFiles':False,'externalRequests':0,'paidApiCalls':0}
(out/'stage-source-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:result[k] for k in ('fileCount','totalBytes','elapsedSeconds','obj','mtl','licenseOrReadmeFiles')},ensure_ascii=True))
print(json.dumps({'largestImages':sorted([i for i in files if 'image' in i],key=lambda x:x['image']['pixelCount'],reverse=True)[:5]},ensure_ascii=True))
