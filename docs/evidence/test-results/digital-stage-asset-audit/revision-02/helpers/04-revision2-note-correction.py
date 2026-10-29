from pathlib import Path
import json
root=Path(r'D:\京剧\.runtime\stage-asset-audit-20261029-revision2')
p=root/'character-glb-audit.json'
d=json.loads(p.read_text(encoding='utf-8'))
d['finalNotes']=[
    'Revision2 contains three distinct file hashes and distinct decoded geometry hashes; no duplicate-file pairs remain.',
    'Only Zhou Yu was replaced by the user since the first audit; prior Du Liniang and Mu Guiying bytes remain unchanged.',
    'No cultural identity or opera attribution was asserted from filename alone.',
    'Read-only container/accessor/texture checks are not browser rendering evidence.',
    'No source file, business database, environment config or generation ledger was changed.',
    'User states public resources used for competition only, non-commercial; no broader rights inferred.'
]
assert not d['identicalFiles'] and not d['identicalDecodedGeometry']
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'revision2NotesCorrected':True,'duplicateFiles':d['identicalFiles'],'originalRoundUnmodified':True}))
