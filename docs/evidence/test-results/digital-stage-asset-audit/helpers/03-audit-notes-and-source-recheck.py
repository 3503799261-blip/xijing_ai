from pathlib import Path
import json,hashlib
from PIL import Image
root=Path(r'D:\京剧\.runtime\stage-asset-audit-20261029')
p=root/'character-glb-audit.json';d=json.loads(p.read_text(encoding='utf-8'))
for r in d['reports']:
    r['issues'].extend(['Embedded JPEG is declared image/jpg instead of glTF core image/jpeg; compatibility normalization in a derived copy may be needed.','No NORMAL attribute; renderer will need generated normals or derive normals before final scene integration.'])
    r['warnings']=['Approximately one million triangles per model; multi-character mobile scene requires measured rendering/performance checks.','Embedded base-color texture is 4096x4096; decoded GPU memory exceeds JPEG file size.']
    item=r['baseColorTextureExtract'];old=Path(item['path']);dest=old.with_suffix('.jpg')
    if not dest.exists():dest.write_bytes(old.read_bytes())
    item['path']=str(dest);item['originalDeclaredMimeType']='image/jpg';item['detectedMimeType']='image/jpeg'
    with Image.open(dest) as img:item['width'],item['height']=img.size;item['mode']=img.mode;img.verify()
    # Originals remain untouched. Confirm source bytes still match initial baseline.
    original=Path(d['sourceDirectory'])/r['filename'];r['sourceHashRecheckedUnchanged']=hashlib.sha256(original.read_bytes()).hexdigest()==r['sha256']
d['finalNotes']=['Two filenames are byte-for-byte identical; they are one unique model, not independently verified Du Liniang and Zhou Yu identities.','No cultural identity or opera attribution was asserted from filename alone.','Read-only container/accessor/texture checks are not browser rendering evidence.','No source file, business database, environment config or generation ledger was changed.']
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'report':str(p),'identicalFiles':d['identicalFiles'],'extracts':[r['baseColorTextureExtract']['path'] for r in d['reports']],'allSourcesUnchanged':all(r['sourceHashRecheckedUnchanged'] for r in d['reports'])},ensure_ascii=True))
