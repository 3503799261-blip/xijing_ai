from pathlib import Path
import json
p=Path(r'D:\京剧\.runtime\stage-asset-audit-20261029\stage-source-audit.json')
d=json.loads(p.read_text(encoding='utf-8'))
d['licenseStatus']='NOT_VERIFIED: no author, license, source-page or permission evidence present in this directory; user supplied files is not a permission grant.'
d['validationBoundaries']={'geometry':'OBJ textual structural counts and bounds only; no rendered scene or topology/UV visual verification; n-gon triangle number is sum(n-2), not proof of valid triangulation.','textures':'Image headers/dimensions/color modes only; no full pixel decoding or web material validation.','c4dSketchup':'Signatures and hashes recorded only; proprietary scene structure not opened.','originalSourceFiles':'Read only, no conversion/relink/reduction performed.'}
d['executionNotes']=[{'status':'FAIL','stage':'First shell wrapper','detail':'PowerShell syntax omitted & before quoted Python executable after pipeline; ParserError occurred before Python or audit source processing. No files or models changed.'},{'status':'PASS','stage':'Corrected shell wrapper','detail':"PowerShell here-string piped to & 'D:\\京剧\\京剧\\.venv\\Scripts\\python.exe' -B -; actual read-only scanner completed and generated this report."}]
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for item in d['files']:
 if item['relative'] in ('戏台.obj','戏台.mtl','戏台.fbx','戏台.c4d','戏台.skp'):
  print(json.dumps(item,ensure_ascii=True))
