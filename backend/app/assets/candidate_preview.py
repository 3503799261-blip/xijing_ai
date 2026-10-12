"""Escaped, read-only local review page. Never an image/model approval."""
from html import escape
import json


def candidate_preview(item):
    def text(value):
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False, indent=2)
        return escape(str(value if value is not None else '待确认'), quote=True)

    candidate_id = text(item['candidateId'])
    style_label = 'Q版卡通' if item.get('styleMode') == 'chibi' else '写实国风'
    image = (f'<img id="candidate-image" src="/api/v1/assets/candidates/{candidate_id}/file" '
             'alt="已登记的当前概念图快照，仅供待审预览">'
             if item.get('filesAvailable') else
             '<p id="missing-image">旧版本仅保留元数据，图片字节不可用；不会读取替换后的原路径。</p>')
    prompt = item.get('promptSnapshot') or {}
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>戏境 AI · 概念图待审预览</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f5f0e7;color:#362727;font-family:"Microsoft YaHei",sans-serif;line-height:1.7}}
main{{max-width:1240px;margin:32px auto;padding:24px}}h1{{color:#701f35;margin:0;font-size:32px}}
.ai-workshop-notice{{border-left:5px solid #b29155;padding:14px 20px;background:#fff8e7;font-size:18px}}
.ai-workshop-grid{{display:grid;grid-template-columns:minmax(280px,1fr) minmax(360px,1fr);gap:28px;margin-top:24px}}
.ai-workshop-card{{min-width:0;background:#fffdf7;border:1px solid #dbc9ae;border-radius:14px;padding:24px}}
img{{width:100%;max-height:690px;object-fit:contain;display:block}}h2{{font-size:22px;color:#701f35;overflow-wrap:anywhere}}
dl{{margin:0}}dt{{font-weight:bold;margin-top:15px}}dd{{margin:3px 0;overflow-wrap:anywhere}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-family:inherit;margin:0;font-size:16px}}
.ai-workshop-prompt{{margin-top:24px}}code{{overflow-wrap:anywhere}}
@media(max-width:720px){{main{{padding:16px;margin:12px auto}}h1{{font-size:26px}}.ai-workshop-grid{{grid-template-columns:1fr}}.ai-workshop-card{{padding:18px}}}}
</style></head><body><main>
<h1>戏境 AI · 概念图待审预览</h1>
<p class="ai-workshop-notice">{style_label}候选 · 未关联角色 · 来源与许可待核实 · 不可用于真实建模</p>
<div class="ai-workshop-grid"><section class="ai-workshop-card">{image}</section>
<section class="ai-workshop-card"><h2>当前快照 · 版本 {text(item['version'])}</h2><dl>
<dt>候选 ID</dt><dd id="candidate-id">{candidate_id}</dd>
<dt>原文件 SHA-256</dt><dd id="source-hash">{text(item.get('sourceHash'))}</dd>
<dt>预览 PNG SHA-256</dt><dd id="preview-hash">{text(item.get('hash'))}</dd>
<dt>尺寸 / 风格</dt><dd>{text(item.get('width'))} × {text(item.get('height'))} / {text(item.get('styleMode'))}</dd>
<dt>来源声明</dt><dd><pre>{text(item.get('sourceNote'))}</pre></dd>
<dt>许可状态</dt><dd><pre>{text(item.get('licenseNote'))}</pre></dd>
<dt>关联 / 图片接受 / 建模资格</dt><dd>均未批准。此页面仅查看，不发出供应商请求。</dd>
</dl></section></div>
<section class="ai-workshop-card ai-workshop-prompt"><h2>待审 Prompt · {text(prompt.get('version'))}</h2>
<p>仅冻结本候选快照；不是已批准角色Prompt，不发送给图生3D接口。</p>
<pre id="prompt-text">{text(prompt.get('text', '旧版本没有可核实的Prompt快照。'))}</pre>
</section></main></body></html>'''
