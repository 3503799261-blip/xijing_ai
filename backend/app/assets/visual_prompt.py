"""Deterministic technical image template, never an invented cultural source."""
import hashlib
import json

TEMPLATE_VERSION = 'opera_asset_visual_v2'
STYLE_TEMPLATES = {
    'realistic': {
        'version': 'opera_realistic_v1',
        'label': '写实国风',
        'directive': '艺术表达（不是新增文化事实）：写实国风数字角色，自然人体比例，服饰与构件关系清晰；呈现原角色方案中的质感与配色，不把写实效果等同于历史复原。',
        'negative': 'Q版比例，玩具化面部，凭空增加服饰史实',
    },
    'chibi': {
        'version': 'opera_chibi_v1',
        'label': 'Q版卡通',
        'directive': '艺术表达（不是新增文化事实）：Q版卡通数字角色，头身比例偏可爱、轮廓清晰、造型简洁；服饰、配色和文化辨识元素仍依照原角色方案。比例调整属于原创表达；不得自动删改靠旗、雉尾、脸谱或道具，任何构件简化另行提出并等待人工文化复核。',
        'negative': '冒称历史复原，写实人体比例，自动删除文化辨识元素，改变脸谱或角色身份',
    },
}


def canonical_hash(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def prompt_hash(content):
    """Approval timestamps and the hash itself do not change the visual input."""
    return canonical_hash({key: value for key, value in content.items()
                           if key not in ('approved', 'approvedAt', 'promptHash')})


def visual_prompt(design, style_mode='realistic', style_version=1):
    if style_mode not in STYLE_TEMPLATES or type(style_version) is not int or style_version < 1:
        raise ValueError('Invalid visual style or version')
    style = STYLE_TEMPLATES[style_mode]
    lines = [f"角色：{design['name']}。定位：{design['positioning']}。"]
    for key, title in [('costume', '服饰'), ('colors', '配色'), ('visualElements', '视觉元素')]:
        parts = [f"{item['description']}（{'文化依据' if item['interpretation'] == 'evidence_based' else '原创设计'}）" for item in design[key]]
        lines.append(f"{title}：{'；'.join(parts)}。")
    if design['creativeElements']:
        lines.append('原创构思：' + '；'.join(design['creativeElements']) + '。')
    lines.append(style['directive'])
    # Keep the old prompt separately; its stage background must not override the
    # plain background needed for a single-view geometric reference.
    lines.append('技术拍摄要求（不是文化事实）：单个角色，全身完整并露出双足，正面或轻微三分之四视角；简洁纯色背景，均匀光照，四肢与服饰构件边界清晰，无文字、水印或多人拼贴。保留上述文化与原创元素；不要自行删除靠旗、雉尾或道具。')
    negative = '裁断头足，多人物，拼贴，复杂舞台背景，文字，水印，遮挡主要构件，静默删除文化元素；' + style['negative']
    limitations = list(design['limitations']) + ['单张图无法证明背面细节；3D背面及薄构件仍需人工核查。', '靠旗、雉尾、长枪及薄片可能出现成模缺陷；简化前必须重新确认。']
    content = {'originalVisualPrompt': design['visualPrompt'], 'imagePrompt': '\n'.join(lines),
               'negativePrompt': negative, 'templateVersion': TEMPLATE_VERSION, 'limitations': limitations,
               'styleMode': style_mode, 'styleVersion': style_version, 'styleTemplateVersion': style['version'],
               'styleLabel': style['label'], 'editableDraft': False}
    return {**content, 'promptHash': prompt_hash(content), 'approved': False, 'approvedAt': None}
