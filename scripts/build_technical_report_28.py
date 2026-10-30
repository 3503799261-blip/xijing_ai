"""Render the evidence-backed, 28-page competition report without importing the app.

Only document inputs, fonts and explicitly listed screenshots are read. No provider,
database, index, model-generation or application-start operation is performed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Flowable, Image, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import textsplit
from reportlab.platypus import paragraph as paragraph_engine

ROOT = Path(__file__).resolve().parents[1]
RED = colors.HexColor('#871b25')
GOLD = colors.HexColor('#bb9147')
INK = colors.HexColor('#302923')
MUTED = colors.HexColor('#75685c')
PAPER = colors.HexColor('#fbf7ee')
LINE = colors.HexColor('#dfd3bf')
W, H = A4
LEFT, RIGHT = 44, 44
WIDTH = W - LEFT - RIGHT

# ReportLab's default East-Asian list lacks common full-width Chinese punctuation.
# Extend it only in this authoring process, allowing one hanging punctuation mark
# within the generous page margin rather than starting a line with a comma.
CN_CANNOT_START = '，；：！？％）》】”’'
textsplit.ALL_CANNOT_START += CN_CANNOT_START
paragraph_engine.ALL_CANNOT_START += CN_CANNOT_START


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text)).replace('\n', '<br/>'), style)


def styles(body_size=10.7):
    return {
        'p': ParagraphStyle('Body', fontName='XJBody', fontSize=body_size,
                            leading=body_size * 1.67, textColor=INK, wordWrap='CJK'),
        'lead': ParagraphStyle('Lead', fontName='XJBody', fontSize=11.3,
                               leading=18.6, textColor=RED, wordWrap='CJK'),
        'h': ParagraphStyle('Subheading', fontName='XJHead', fontSize=12.1,
                            leading=19, textColor=RED, wordWrap='CJK'),
        'cell': ParagraphStyle('Cell', fontName='XJBody', fontSize=9.3,
                               leading=14.3, textColor=INK, wordWrap='CJK'),
        'th': ParagraphStyle('TableHead', fontName='XJHead', fontSize=9.4,
                             leading=14.4, textColor=RED, wordWrap='CJK'),
        'small': ParagraphStyle('Caption', fontName='XJBody', fontSize=8.6,
                                leading=13.2, textColor=MUTED, wordWrap='CJK'),
        'note': ParagraphStyle('Note', fontName='XJBody', fontSize=9.5,
                               leading=15, textColor=INK, wordWrap='CJK'),
        'code': ParagraphStyle('Code', fontName='XJMono', fontSize=8.2,
                               leading=12, textColor=INK),
    }


class ProcessCards(Flowable):
    def __init__(self, items, columns=3, title=''):
        super().__init__()
        self.items, self.columns, self.title = items, columns, title
        self.width = WIDTH
        self.row_h = 75
        self.height = ((len(items) + columns - 1) // columns) * self.row_h + 4

    def draw(self):
        c = self.canv
        gap = 11
        box_w = (self.width - gap * (self.columns - 1)) / self.columns
        st = styles()
        for i, item in enumerate(self.items):
            row, col = divmod(i, self.columns)
            x, y = col * (box_w + gap), self.height - (row + 1) * self.row_h + 9
            c.setFillColor(PAPER)
            c.setStrokeColor(LINE)
            c.roundRect(x, y, box_w, self.row_h - 13, 5, fill=1, stroke=1)
            c.setFillColor(RED)
            c.circle(x + 15, y + 46, 9, fill=1, stroke=0)
            c.setFont('XJMono', 8)
            c.setFillColor(colors.white)
            c.drawCentredString(x + 15, y + 43, str(i + 1))
            title, detail = item if isinstance(item, list) else (item, '')
            label = paragraph(title, st['th'])
            _, lh = label.wrap(box_w - 43, 36)
            label.drawOn(c, x + 32, y + 50 - lh)
            detail_p = paragraph(detail, st['small'])
            _, dh = detail_p.wrap(box_w - 18, 32)
            detail_p.drawOn(c, x + 9, y + 27 - dh)


class Architecture(Flowable):
    def __init__(self):
        super().__init__()
        self.width, self.height = WIDTH, 232

    def draw(self):
        c, st = self.canv, styles()
        def box(x, y, w, h, title, subtitle, human=False):
            c.setFillColor(colors.HexColor('#f0e3c5') if human else PAPER)
            c.setStrokeColor(GOLD if human else LINE)
            c.roundRect(x, y, w, h, 5, fill=1, stroke=1)
            p = paragraph(title, st['th'])
            _, ph = p.wrap(w - 18, h)
            p.drawOn(c, x + 9, y + h - 9 - ph)
            p = paragraph(subtitle, st['small'])
            _, ph = p.wrap(w - 18, h)
            p.drawOn(c, x + 9, y + 8)
        def arrow(x, ya, yb):
            c.setStrokeColor(GOLD); c.setLineWidth(1)
            c.line(x, ya, x, yb)
            c.line(x - 3, yb + 4, x, yb); c.line(x + 3, yb + 4, x, yb)
        box(0, 186, WIDTH, 44, '网页与交互层', '8页HTML、问答会话、数字戏台、原生ES Module')
        arrow(WIDTH / 2, 186, 174)
        box(0, 128, WIDTH, 45, 'FastAPI应用与安全边界', 'Chat / Search / Agents / Assets / Stage；静态文件白名单')
        for x in (WIDTH / 6, WIDTH / 2, WIDTH * 5 / 6): arrow(x, 128, 116)
        bw = (WIDTH - 22) / 3
        box(0, 58, bw, 57, '本地知识与记录', 'BGE + Qdrant + SQLite\n会话JSON、私有资源')
        box(bw + 11, 58, bw, 57, '外部服务依赖', 'DeepSeek真实文本\nNeural4D历史任务')
        box((bw + 11) * 2, 58, bw, 57, '人工控制环节', '资料/方案确认\n单次建模批准与验收', True)
        box(0, 0, WIDTH, 46, '文件与展示层', '受控GLB、纹理兼容谱系、Three.js戏台 / model-viewer历史资产')
        c.setStrokeColor(LINE)
        c.line(WIDTH / 2, 58, WIDTH / 2, 46)


class Toc(Flowable):
    def __init__(self, pages):
        super().__init__(); self.pages = pages; self.width = WIDTH; self.height = 330

    def draw(self):
        c, st = self.canv, styles()
        entries = self.pages[2:]
        split = (len(entries) + 1) // 2
        for i, pg in enumerate(entries):
            col, row = divmod(i, split)
            x, y, bw = col * (WIDTH / 2 + 8), self.height - 24 - row * 24, WIDTH / 2 - 12
            c.setFillColor(RED); c.setFont('XJMono', 9)
            c.drawString(x, y, f'{pg["number"]:02}')
            pp = paragraph(pg['short'], st['cell'])
            _, ph = pp.wrap(bw - 28, 25)
            pp.drawOn(c, x + 27, y + 9 - ph)
            c.setStrokeColor(LINE); c.line(x, y - 8, x + bw, y - 8)
            c.linkRect('', f'p{pg["number"]}', (x, y - 8, x + bw, y + 14), relative=1, thickness=0)


def make_block(block, st, pages, root):
    kind = block['type']
    if kind in ('p', 'h', 'lead', 'small'):
        return [paragraph(block['text'], st[kind]), Spacer(1, {'p': 9, 'h': 6, 'lead': 11, 'small': 6}[kind])]
    if kind == 'note':
        data = [[paragraph(block['text'], st['note'])]]
        t = Table(data, colWidths=[WIDTH])
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), PAPER),
                               ('BOX', (0, 0), (-1, -1), .5, LINE),
                               ('LEFTPADDING', (0, 0), (-1, -1), 10),
                               ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                               ('TOPPADDING', (0, 0), (-1, -1), 8),
                               ('BOTTOMPADDING', (0, 0), (-1, -1), 8)]))
        return [t, Spacer(1, 10)]
    if kind == 'table':
        weights = block.get('weights', [1] * len(block['headers']))
        widths = [WIDTH * w / sum(weights) for w in weights]
        cell_style = st['small'] if block.get('compact') else st['cell']
        rows = [[paragraph(x, st['th']) for x in block['headers']]]
        rows += [[paragraph(x, cell_style) for x in row] for row in block['rows']]
        t = Table(rows, colWidths=widths, hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eee1c8')),
                               ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fcfaf5')]),
                               ('LINEBELOW', (0, 0), (-1, 0), .6, GOLD),
                               ('LINEBELOW', (0, 1), (-1, -1), .35, LINE),
                               ('LEFTPADDING', (0, 0), (-1, -1), 7),
                               ('RIGHTPADDING', (0, 0), (-1, -1), 7),
                               ('TOPPADDING', (0, 0), (-1, -1), 3 if block.get('compact') else 6),
                               ('BOTTOMPADDING', (0, 0), (-1, -1), 3 if block.get('compact') else 6)]))
        return [t, Spacer(1, 11)]
    if kind == 'steps':
        return [ProcessCards(block['items'], block.get('columns', 3)), Spacer(1, 8)]
    if kind == 'architecture': return [Architecture(), Spacer(1, 11)]
    if kind == 'toc': return [Toc(pages), Spacer(1, 13)]
    if kind == 'image':
        path = (root / block['path']).resolve()
        if not path.is_file(): raise FileNotFoundError(path)
        from PIL import Image as PILImage
        with PILImage.open(path) as im: iw, ih = im.size
        ww = min(WIDTH, block.get('width', WIDTH))
        hh = ww * ih / iw
        if hh > block.get('maxHeight', 250):
            hh = block['maxHeight']; ww = hh * iw / ih
        image = Image(str(path), width=ww, height=hh, hAlign='CENTER')
        return [image, Spacer(1, 7), paragraph(block['caption'], st['small']), Spacer(1, 9)]
    if kind == 'code':
        rows = [[paragraph(line.replace(' ', '\u00a0'), st['code'])] for line in block['text'].splitlines()]
        t = Table(rows, colWidths=[WIDTH])
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), PAPER),
                               ('LEFTPADDING', (0, 0), (-1, -1), 9),
                               ('RIGHTPADDING', (0, 0), (-1, -1), 9),
                               ('TOPPADDING', (0, 0), (-1, -1), 1),
                               ('BOTTOMPADDING', (0, 0), (-1, -1), 1)]))
        return [t, Spacer(1, 11)]
    raise ValueError(f'Unknown document block: {kind}')


def page_header(c, page):
    c.setFillColor(RED); c.setFont('XJHead', 8.9)
    c.drawString(LEFT, H - 28, '戏境 AI  |  京剧文化、可信问答与数字戏台')
    c.setStrokeColor(GOLD); c.setLineWidth(.7); c.line(LEFT, H - 36, W - RIGHT, H - 36)
    c.setFillColor(MUTED); c.setFont('XJBody', 8)
    c.drawString(LEFT, 25, '比赛技术文档 · 2026-10-30 · 实现、历史证据与未测范围分别记录')
    c.setFont('XJMono', 8); c.drawRightString(W - RIGHT, 25, f'{page:02} / 28')


def render(content, output, root, body_size=10.7):
    pages = content['pages']
    if len(pages) != 28 or [p['number'] for p in pages] != list(range(1, 29)):
        raise ValueError('Exactly 28 ordered content pages are required')
    st = styles(body_size)
    c = canvas.Canvas(str(output), pagesize=A4, pageCompression=1)
    c.setTitle('戏境 AI - 京剧文化与AI数字创作平台技术文档')
    c.setAuthor('陈雯雯 / 戏境 AI 项目')
    c.setCreator('Xijing AI technical-report-28 generator / ReportLab')
    c.setSubject('28页比赛技术文档；基于真实实现、历史测试和明确边界')
    metrics = []
    for page in pages:
        page_header(c, page['number'])
        c.bookmarkPage(f'p{page["number"]}')
        c.addOutlineEntry(page['title'], f'p{page["number"]}', 0, False)
        y = H - 57
        c.setFillColor(GOLD); c.setFont('XJMono', 8.7)
        c.drawString(LEFT, y, f'{page["number"]:02}  /  {page.get("tag", "TECHNICAL REPORT")}')
        title_style = ParagraphStyle('PageTitle', fontName='XJHead', fontSize=22 if page['number'] == 1 else 19.4,
                                    leading=28, textColor=RED, wordWrap='CJK')
        title = paragraph(page['title'], title_style)
        _, th = title.wrap(WIDTH, 80); y -= 12 + th; title.drawOn(c, LEFT, y)
        y -= 15
        top = y
        source_line = '依据：' + '、'.join(page.get('sources', [])) + '。详见第28页证据索引。'
        source = paragraph(source_line, st['small'])
        _, source_h = source.wrap(WIDTH, 40)
        bottom = 51 + source_h + 7
        count = 0
        for block in page['blocks']:
            for item in make_block(block, st, pages, root):
                _, ih = item.wrap(WIDTH, H)
                if y - ih < bottom:
                    raise ValueError(f'Page {page["number"]} overflow: block={count}, need={ih:.1f}, available={y-bottom:.1f}')
                y -= ih
                x = LEFT + (WIDTH - item.drawWidth) / 2 if isinstance(item, Image) else LEFT
                item.drawOn(c, x, y)
                count += 1
        c.setStrokeColor(LINE); c.line(LEFT, 51 + source_h + 4, W - RIGHT, 51 + source_h + 4)
        source.drawOn(c, LEFT, 49)
        available = top - bottom
        used = top - y
        metrics.append({'page': page['number'], 'title': page['title'], 'usedPoints': round(used, 2),
                        'availablePoints': round(available, 2), 'fillRatio': round(used / available, 4),
                        'bodyBottom': round(y, 2), 'allowedBottom': round(bottom, 2)})
        c.showPage()
    c.save()
    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--content', type=Path, default=ROOT / 'docs/reports/technical-report-28.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'output/pdf/xijing-ai-technical-report-28.pdf')
    parser.add_argument('--font', type=Path, default=Path('C:/Windows/Fonts/simsun.ttc'))
    parser.add_argument('--heading-font', type=Path, default=Path('C:/Windows/Fonts/simhei.ttf'))
    parser.add_argument('--mono-font', type=Path, default=Path('C:/Windows/Fonts/consola.ttf'))
    parser.add_argument('--metrics', type=Path, default=ROOT / 'tmp/pdfs/technical-report-28/layout-metrics.json')
    args = parser.parse_args()
    pdfmetrics.registerFont(TTFont('XJBody', str(args.font), subfontIndex=0))
    pdfmetrics.registerFont(TTFont('XJHead', str(args.heading_font)))
    pdfmetrics.registerFont(TTFont('XJMono', str(args.mono_font)))
    pdfmetrics.registerFontFamily('XJBody', normal='XJBody', bold='XJHead')
    data = json.loads(args.content.read_text(encoding='utf-8'))
    evidence = data.get('evidenceRefs', {})
    for page in data['pages']:
        for identifier in page['sources']:
            if identifier not in evidence:
                raise ValueError(f'Unknown evidence identifier: {identifier}')
    for paths in evidence.values():
        for source in paths:
            if not (ROOT / source).exists():
                raise FileNotFoundError(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pending_output = args.output.with_name(args.output.stem + '.pending.pdf')
    metrics = render(data, pending_output, ROOT)
    reader = PdfReader(pending_output)
    if len(reader.pages) != 28: raise ValueError('Output must have exactly 28 pages')
    # Never replace the last valid PDF with a partially rendered or overflowing file.
    pending_output.replace(args.output)
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    result = {'pages': 28, 'bodyFontSize': 10.7, 'file': str(args.output),
              'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
              'pageMetrics': metrics, 'paidApiCalls': 0, 'neural4dCalls': 0,
              'visualInspection': 'PENDING; render and inspect all pages before delivery'}
    args.metrics.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'pages': 28, 'bytes': args.output.stat().st_size,
                      'minFillRatio': min(x['fillRatio'] for x in metrics)}, ensure_ascii=True))


if __name__ == '__main__':
    main()
