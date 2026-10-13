"""Local-only technical viewer; not a character or public IP showcase."""
from html import escape


def internal_viewer(model):
    def text(key):
        return escape(str(model.get(key) or '未提供'), quote=True)
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>戏境 AI · 内部3D技术验证</title>
<link rel="stylesheet" href="/css/ai-workshop.css"><style>
body{{margin:0;background:#f5f0e7;color:#362727;font-family:"Microsoft YaHei",sans-serif;line-height:1.7}}
main{{max-width:1280px;padding:24px;margin:auto}}h1{{color:#701f35;font-size:30px}}
.ai-workshop-internal-notice{{border-left:5px solid #b29155;padding:12px 18px;background:#fff8e7}}
.ai-workshop-viewer-host{{height:650px}}.ai-workshop-model-viewer{{width:100%;height:100%}}
.ai-workshop-internal-hash{{overflow-wrap:anywhere}}button{{font:inherit;padding:10px 16px;margin:6px;border:1px solid #b29155;background:#fffdf7;border-radius:8px}}
@media(max-width:720px){{main{{padding:16px}}.ai-workshop-viewer-host{{height:480px}}h1{{font-size:25px}}}}
</style></head><body><main id="ai-workshop-internal-root" data-model-id="{text('modelId')}">
<h1>戏境 AI · 内部3D技术验证</h1>
<p class="ai-workshop-internal-notice">真实Neural4D输出 · 技术验证用 · 非正式角色资产 · 不公开展示或分发。没有文化一致性通过声明。</p>
<p>供应商任务：{text('providerTaskId')} · Q版 / 单模型</p>
<p class="ai-workshop-internal-hash">模型SHA-256：{text('hash')}</p>
<p id="ai-workshop-viewer-status" role="status">等待读取已保存的模型</p>
<p id="ai-workshop-viewer-error" role="alert" hidden></p>
<div id="ai-workshop-viewer-host" class="ai-workshop-viewer-host"></div>
<div><button id="ai-workshop-viewer-zoom-in" disabled>放大</button><button id="ai-workshop-viewer-zoom-out" disabled>缩小</button>
<button id="ai-workshop-viewer-reset" disabled>重置视角</button><button id="ai-workshop-viewer-touch" disabled>进入触摸交互</button>
<button id="ai-workshop-viewer-reload" hidden>重新加载原模型</button></div>
<p id="ai-workshop-viewer-help">鼠标拖拽旋转，滚轮缩放；手机先进入触摸交互。失败只重载原文件，不创建新模型。</p>
<p>请检查≥260°连续观察、头饰/毛笔/背面；人工验收尚未完成。</p>
<script type="module" src="/js/ai-workshop/internal-viewer.js?v=phase4-internal-1"></script>
</main></body></html>'''
