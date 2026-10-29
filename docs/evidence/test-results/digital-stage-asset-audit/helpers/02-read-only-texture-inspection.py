import json
from pathlib import Path
from PIL import Image
p=Path(r'D:\京剧\.runtime\stage-asset-audit-20261029\character-glb-audit.json');d=json.loads(p.read_text(encoding='utf-8'))
for r in d['reports']:
    print(json.dumps({'filename':r['filename'],'images':r['images'],'materials':r['materials'],'asset':r['asset'],'geometry':r['geometry']['meshes']},ensure_ascii=True))
    p=Path(r['baseColorTextureExtract']['path'])
    print(p.read_bytes()[:20].hex())
    try:
        with Image.open(p) as img:print(img.format,img.size,img.mode)
    except Exception as e:print(type(e).__name__)
