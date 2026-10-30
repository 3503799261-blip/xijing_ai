r"""Archive of the successful inline structural QA executed on 2026-10-30.

ACTUAL EXECUTION FORM
---------------------
The Python body below was executed as a PowerShell single-quoted here-string,
piped to the bundled interpreter with the parser result as argv[1]:

    @'
    <the Python body below, starting with its imports>
    '@ | & 'C:/Users/35037/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B - $parserJson

This file was saved afterward for traceability; it was not the original entry
point and was not executed at archival time. The prior failed QA JSON was copied
before the successful rerun, using the following separate PowerShell prelude:

    $qa = 'tmp/pdfs/technical-report-28/structural-qa.json'
    $before = 'tmp/pdfs/technical-report-28/structural-qa-before-glyph-fix.json'
    if (Test-Path -LiteralPath $before) {
      if ((Get-FileHash -LiteralPath $before).Hash -ne (Get-FileHash -LiteralPath $qa).Hash) {
        throw 'Historical QA copy already exists and differs; refusing to overwrite.'
      }
    } else {
      Copy-Item -LiteralPath $qa -Destination $before
    }

The actual command parsed ONLY the page-26 PowerShell startup snippet. It did
not execute that snippet. Parser JSON was supplied by this prelude:

    $doc = Get-Content -LiteralPath 'docs/reports/technical-report-28.json' -Raw | ConvertFrom-Json
    $startup = @($doc.pages | Where-Object number -eq 26 | ForEach-Object { $_.blocks } | Where-Object { $_.type -eq 'code' -and $_.text -match 'uvicorn' })
    $tokenList = $null
    $parserErrors = $null
    $null = [System.Management.Automation.Language.Parser]::ParseInput($startup[0].text, [ref]$tokenList, [ref]$parserErrors)
    $parserJson = [pscustomobject]@{
      kind='PowerShellParserStaticOnly'
      startupSnippetCount=$startup.Count
      snippet=$startup[0].text
      errors=@($parserErrors | ForEach-Object { $_.Message })
      errorCount=$parserErrors.Count
      executed=$false
    } | ConvertTo-Json -Depth 4 -Compress
    $env:PYTHONIOENCODING='utf-8'

REPRODUCING WITH THIS ARCHIVED ENTRY POINT
----------------------------------------
Run from D:\京剧\京剧, with the parser prelude above, then replace the original
here-string invocation with:

    & 'C:/Users/35037/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B 'tmp/pdfs/technical-report-28/check_structure.py' $parserJson

The original failed result is already preserved; do not repeat the copy prelude
against a successful current result. The script reads the final PDF/source JSON
and writes structural-qa.json only. It intentionally checks the exact final
2,628,079-byte artifact and retains the earlier failure and resolution. It does
not import the application, open databases/models, contact APIs, or modify the
PDF, source JSON, or generator. Text-coordinate checks do not replace visual QA.
"""

import collections, datetime, hashlib, json, re, sys, unicodedata
from pathlib import Path
import pdfplumber, pypdf
from pypdf import PdfReader
from pypdf.generic import IndirectObject
root=Path(r'D:\京剧\京剧')
pdf_path=root/'output/pdf/xijing-ai-technical-report-28.pdf'
json_path=root/'docs/reports/technical-report-28.json'
out_path=root/'tmp/pdfs/technical-report-28/structural-qa.json'
before_path=root/'tmp/pdfs/technical-report-28/structural-qa-before-glyph-fix.json'
old=json.loads(before_path.read_text(encoding='utf-8'))
parser_result=json.loads(sys.argv[1])
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
pdf_before,json_before=sha(pdf_path),sha(json_path)
content=json.loads(json_path.read_text(encoding='utf-8-sig'))
reader=PdfReader(str(pdf_path),strict=True)
checks,errors,notes=[],[],[]
def check(name,ok,details):
 checks.append({'name':name,'status':'PASS' if ok else 'FAIL','details':details})
 if not ok:errors.append({'check':name,'details':details})
check('exact_page_count',len(reader.pages)==28 and content.get('pageCount')==28 and len(content.get('pages',[]))==28,{'pdf':len(reader.pages),'jsonPageCount':content.get('pageCount'),'jsonPages':len(content.get('pages',[]))})
check('ordered_json_pages',[p['number'] for p in content['pages']]==list(range(1,29)),[p['number'] for p in content['pages']])
check('expected_final_pdf_size',pdf_path.stat().st_size==2628079,{'actualBytes':pdf_path.stat().st_size,'expectedBytes':2628079})
ref_page={}
for i,p in enumerate(reader.pages):
 r=p.indirect_reference
 if r:ref_page[(r.idnum,r.generation)]=i+1

def dest_page(dest):
 if dest is None:return None
 if isinstance(dest,(str,bytes)):
  d=reader.named_destinations.get(str(dest))
  return reader.get_destination_page_number(d)+1 if d else None
 if isinstance(dest,IndirectObject):dest=dest.get_object()
 if hasattr(dest,'get') and dest.get('/Page') is not None:dest=[dest.get('/Page')]
 if isinstance(dest,(list,tuple)) and dest:
  d=dest[0]
  if isinstance(d,IndirectObject):return ref_page.get((d.idnum,d.generation))
  if isinstance(d,int):return d+1
  r=getattr(d,'indirect_reference',None)
  if r:return ref_page.get((r.idnum,r.generation))
 return None
bookmarks=[]
def walk(items,depth=0):
 for d in items:
  if isinstance(d,list):walk(d,depth+1)
  else:
   try:target=reader.get_destination_page_number(d)+1
   except Exception:target=None
   bookmarks.append({'title':str(d.get('/Title','')),'targetPage':target,'depth':depth})
walk(reader.outline)
check('bookmarks_28_valid_targets',len(bookmarks)==28 and [b['targetPage'] for b in bookmarks]==list(range(1,29)),bookmarks)
links=[]
for i,p in enumerate(reader.pages,1):
 for ar in p.get('/Annots',[]):
  a=ar.get_object()
  if a.get('/Subtype')!='/Link':continue
  action=a.get('/A')
  if isinstance(action,IndirectObject):action=action.get_object()
  target=dest_page(a.get('/Dest') or (action or {}).get('/D'))
  uri=(action or {}).get('/URI')
  links.append({'sourcePage':i,'targetPage':target,'uri':str(uri) if uri else None,'rect':[float(x) for x in a.get('/Rect',[])],'internal':target is not None})
internal=[l for l in links if l['internal']]
invalid=[l for l in links if not l['internal'] and not l['uri']]
check('toc_26_internal_links',len(internal)==26 and all(l['sourcePage']==2 for l in internal) and sorted(l['targetPage'] for l in internal)==list(range(3,29)) and not invalid,{'internalCount':len(internal),'targets':sorted(l['targetPage'] for l in internal),'invalid':invalid,'allLinks':links})
font_records={}; seen=set()
def resources(res):
 if isinstance(res,IndirectObject):res=res.get_object()
 if not res or id(res) in seen:return
 seen.add(id(res))
 fonts=res.get('/Font',{})
 if isinstance(fonts,IndirectObject):fonts=fonts.get_object()
 for alias,raw in fonts.items():
  f=raw.get_object();name=str(f.get('/BaseFont','')).lstrip('/');des=[]
  if f.get('/FontDescriptor'):des.append(f['/FontDescriptor'].get_object())
  for df in f.get('/DescendantFonts',[]):
   d=df.get_object()
   if d.get('/FontDescriptor'):des.append(d['/FontDescriptor'].get_object())
  emb=any(any(k in d for k in ('/FontFile','/FontFile2','/FontFile3')) for d in des)
  rec=font_records.setdefault(name,{'baseFont':name,'subtype':str(f.get('/Subtype')),'embedded':emb,'toUnicode':bool(f.get('/ToUnicode')),'resourceAliases':[]})
  rec['embedded']=rec['embedded'] or emb
  if str(alias) not in rec['resourceAliases']:rec['resourceAliases'].append(str(alias))
 xobs=res.get('/XObject',{})
 if isinstance(xobs,IndirectObject):xobs=xobs.get_object()
 for val in xobs.values():
  obj=val.get_object()
  if obj.get('/Subtype')=='/Form':resources(obj.get('/Resources'))
for p in reader.pages:resources(p.get('/Resources'))
han_re=re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002FA1F]')
allowed_hanging=set('、，。；：！？％）》】”’．…')
per_page=[];used_fonts=set();suspicious=[];outside=[];margin=[];hangs=[];missing_cjk=[];replacement_count=0;null_count=0;page19_text=''
def source_strings(page):
 r=[page['title']]
 for b in page['blocks']:
  t=b['type']
  if t in ('p','h','lead','small','note','code'):r.append(b['text'])
  elif t=='table':r.extend(map(str,b['headers']));r.extend(str(c) for row in b['rows'] for c in row)
  elif t=='image':r.append(b['caption'])
  elif t=='steps':
   for it in b['items']:
    if isinstance(it,list):r.extend(map(str,it))
    else:r.append(str(it))
 return r
with pdfplumber.open(str(pdf_path)) as pdf:
 check('pdfplumber_page_count_agrees',len(pdf.pages)==28,len(pdf.pages))
 for i,p in enumerate(pdf.pages,1):
  w,h=float(p.width),float(p.height);chars=p.chars;txt=p.extract_text(layout=False) or ''
  if i==19:page19_text=txt
  replacement_count+=txt.count('\ufffd');null_count+=txt.count('\x00')
  used_fonts.update(c['fontname'] for c in chars if c.get('text','').strip())
  bad=[];over=[];allowed=[]
  for c in chars:
   t=c.get('text','')
   if not t.strip():continue
   e={'page':i,'text':t,'font':c['fontname'],'size':round(float(c['size']),3),'x0':round(float(c['x0']),3),'x1':round(float(c['x1']),3),'top':round(float(c['top']),3),'bottom':round(float(c['bottom']),3)}
   if '\ufffd' in t or '\x00' in t or '(cid:' in t or any(unicodedata.category(a)=='Cc' and a not in '\t\n\r' for a in t):suspicious.append(e)
   if c['x0']<-.1 or c['x1']>w+.1 or c['top']<-.1 or c['bottom']>h+.1:bad.append(e)
   if c['x1']>w-44+.75:
    if len(t)==1 and t in allowed_hanging and c['x0']<=w-44+.75 and c['x1']<=w+.1:allowed.append(e)
    else:over.append(e)
  groups=collections.defaultdict(list)
  for e in allowed:groups[round(e['top'],1)].append(e)
  for g in groups.values():
   if len(g)>1:over.extend(g);allowed=[e for e in allowed if e not in g]
  outside.extend(bad);margin.extend(over);hangs.extend(allowed)
  expected=collections.Counter(han_re.findall('\n'.join(source_strings(content['pages'][i-1]))));actual=collections.Counter(han_re.findall(txt));missing=expected-actual
  if missing:missing_cjk.append({'page':i,'characters':dict(missing),'count':sum(missing.values())})
  per_page.append({'page':i,'widthPt':round(w,4),'heightPt':round(h,4),'rotation':int(reader.pages[i-1].get('/Rotate',0)),'a4':abs(w-595.2755905511812)<.05 and abs(h-841.8897637795277)<.05,'extractedCharacters':len(txt),'nonWhitespaceCharacters':len(re.sub(r'\s+','',txt)),'chineseCharacters':len(han_re.findall(txt)),'glyphCount':len(chars),'bounds':{'x0':round(min(c['x0'] for c in chars),3),'x1':round(max(c['x1'] for c in chars),3),'top':round(min(c['top'] for c in chars),3),'bottom':round(max(c['bottom'] for c in chars),3)},'outsidePaperCount':len(bad),'disallowedRightMarginCount':len(over),'allowedHangingPunctuationCount':len(allowed),'expectedSourceCjkCount':sum(expected.values()),'missingSourceCjkCount':sum(missing.values())})
check('all_28_pages_A4_unrotated',all(p['a4'] and p['rotation']==0 for p in per_page),[{'page':p['page'],'widthPt':p['widthPt'],'heightPt':p['heightPt'],'rotation':p['rotation']} for p in per_page])
check('no_text_glyph_outside_paper',not outside,outside)
check('right_margin_only_single_CJK_hanging_punctuation',not margin,{'violations':margin,'allowed':hangs,'policy':'44pt right margin; one CJK punctuation glyph per line may hang inside page'})
check('no_replacement_or_suspicious_extracted_glyphs',not suspicious,suspicious)
check('all_source_CJK_characters_represented_per_page',not missing_cjk,missing_cjk)
check('all_pages_have_substantial_extractable_text',all(p['chineseCharacters']>150 and p['nonWhitespaceCharacters']>250 for p in per_page),{'minimumChinese':min(p['chineseCharacters'] for p in per_page),'minimumNonWhitespace':min(p['nonWhitespaceCharacters'] for p in per_page)})
for n,r in font_records.items():r['usedInExtractedText']=n in used_fonts
unembedded=[n for n in sorted(used_fonts) if n not in font_records or not font_records[n]['embedded']]
check('all_actually_used_text_fonts_embedded',not unembedded,{'usedFonts':sorted(used_fonts),'missingOrUnembedded':unembedded,'fonts':list(font_records.values())})
unused=[r['baseFont'] for r in font_records.values() if not r['embedded'] and not r['usedInExtractedText']]
if unused:notes.append({'kind':'unused_default_font_resources','fonts':unused,'meaning':'No extracted text glyph uses these resource-only fonts; not an embedding failure.'})
rows=next(b for b in content['pages'][-1]['blocks'] if b['type']=='table')['rows'];ids={r[0] for r in rows};paths=[]
for row in rows:
 for token in re.split('[；、]',row[2]):
  token=re.sub('等8页$','',token.strip())
  if token:
   p=root/token;paths.append({'sourceId':row[0],'path':token,'exists':p.exists(),'kind':'directory' if p.is_dir() else 'file' if p.is_file() else 'missing'})
check('all_reference_index_paths_exist',all(p['exists'] for p in paths),paths)
missing_ids=sorted({s for p in content['pages'] for s in p.get('sources',[]) if s not in ids});inline=set(re.findall(r'\[([A-Z]\d{2})\]',json.dumps(content,ensure_ascii=False)));bad_inline=sorted(inline-ids)
check('reference_ids_resolve',not missing_ids and not bad_inline,{'undefinedPageSourceIds':missing_ids,'undefinedInlineSourceIds':bad_inline,'definedIds':sorted(ids)})
images=[{'page':p['number'],'path':b['path'],'exists':(root/b['path']).is_file()} for p in content['pages'] for b in p['blocks'] if b['type']=='image']
check('all_source_image_paths_exist',all(p['exists'] for p in images),images)
check('startup_snippet_PowerShell_static_parse_only',parser_result.get('startupSnippetCount')==1 and parser_result.get('errorCount')==0 and parser_result.get('executed') is False,parser_result)
boxes=[]
for i,p in enumerate(reader.pages,1):
 m=[float(v) for v in p.mediabox];c=[float(v) for v in p.cropbox];boxes.append({'page':i,'mediaBox':m,'cropBox':c,'cropMatchesPaper':all(abs(a-b)<.05 for a,b in zip(m,c))})
check('crop_boxes_match_A4_media_boxes',all(p['cropMatchesPaper'] for p in boxes),boxes)
source19='\n'.join(source_strings(content['pages'][18]));pypdf19=reader.pages[18].extract_text()
fix={'priorResult':str(before_path),'priorResultSha256':sha(before_path),'priorStatus':old['status'],'priorPdfBytes':old['pdfBytes'],'priorPdfSha256':old['pdfSha256'],'priorErrors':old['errors'],'priorDiagnosis':old.get('glyphDiagnosis'),'currentSourceContainsAsciiNMinus2':'n-2' in source19,'currentSourceContainsUnsupportedMathematicalMinus':'\u2212' in source19,'pdfplumberExtractsAsciiNMinus2':'n-2' in page19_text,'pypdfExtractsAsciiNMinus2':'n-2' in pypdf19,'currentPage19NullCount':page19_text.count('\x00'),'sourceOrPdfModifiedByThisQa':False}
check('previous_page19_missing_minus_resolved',fix['currentSourceContainsAsciiNMinus2'] and not fix['currentSourceContainsUnsupportedMathematicalMinus'] and fix['pdfplumberExtractsAsciiNMinus2'] and fix['pypdfExtractsAsciiNMinus2'] and fix['currentPage19NullCount']==0,fix)
check('source_and_PDF_unchanged_during_readonly_QA',pdf_before==sha(pdf_path) and json_before==sha(json_path),{'pdfSha256':pdf_before,'jsonSha256':json_before})
result={'kind':'OFFLINE_FINAL_PDF_STRUCTURAL_QA','checkedAtUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pdf':str(pdf_path),'sourceJson':str(json_path),'output':str(out_path),'pdfBytes':pdf_path.stat().st_size,'pdfSha256':pdf_before,'jsonSha256':json_before,'runtime':{'python':sys.executable,'pypdf':pypdf.__version__,'pdfplumber':pdfplumber.__version__},'scope':'Read PDF/JSON, PDF font/text/link structures and evidence path existence only. No app import/start, business/API/browser tests, database/model writes, or startup snippet execution. Prior structural QA is preserved before this rerun.','limitations':['Text extraction and glyph-coordinate checks cannot replace final visual review or prove correctness of screenshot pixels.','CJK coverage compares extracted characters per source page, not cultural or semantic correctness.','Evidence-path existence is not a re-execution or correctness audit of the referenced historical runs.'],'status':'PASS' if not errors else 'FAIL','checks':checks,'errors':errors,'notes':notes,'previousFailureAndResolution':fix,'totals':{'pages':len(per_page),'extractedCharacters':sum(p['extractedCharacters'] for p in per_page),'nonWhitespaceCharacters':sum(p['nonWhitespaceCharacters'] for p in per_page),'chineseCharacters':sum(p['chineseCharacters'] for p in per_page),'bookmarks':len(bookmarks),'internalLinks':len(internal),'actuallyUsedFonts':len(used_fonts),'referencePaths':len(paths),'sourceImages':len(images),'allowedHangingPunctuationGlyphs':len(hangs),'replacementCharacterGlyphs':replacement_count,'nullCodePointGlyphs':null_count},'pages':per_page}
out_path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':result['status'],'checks':len(checks),'passed':sum(c['status']=='PASS' for c in checks),'errors':errors,'pdfBytes':result['pdfBytes'],'pdfSha256':pdf_before,'jsonSha256':json_before,'totals':result['totals'],'beforeQa':str(before_path),'output':str(out_path)},ensure_ascii=False))
