"""Optional competition PDF authoring. Does not import or start the application."""
import argparse
import json
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle, KeepTogether
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RED = colors.HexColor('#8d1820')
GOLD = colors.HexColor('#ba8c3e')
INK = colors.HexColor('#33251e')
PAPER = colors.HexColor('#fffaf0')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'output/pdf/xijing-ai-technical-report.pdf')
    parser.add_argument('--screenshots', type=Path, default=ROOT.parent / '.runtime/site-navigation-browser-final2')
    parser.add_argument('--font', type=Path, default=Path('C:/Windows/Fonts/simsun.ttc'))
    args = parser.parse_args()
    pdfmetrics.registerFont(TTFont('XijingCN', str(args.font), subfontIndex=0))
    base = dict(fontName='XijingCN', textColor=INK, wordWrap='CJK')
    styles = {
        'title': ParagraphStyle('TitleCN', fontSize=29, leading=42, textColor=RED, fontName='XijingCN', wordWrap='CJK', spaceAfter=18),
        'h1': ParagraphStyle('H1CN', fontSize=20, leading=30, textColor=RED, fontName='XijingCN', spaceAfter=18, wordWrap='CJK'),
        'h2': ParagraphStyle('H2CN', fontSize=13, leading=21, textColor=RED, fontName='XijingCN', spaceBefore=12, spaceAfter=7),
        'body': ParagraphStyle('BodyCN', fontSize=10.5, leading=18, spaceAfter=10, **base),
        'small': ParagraphStyle('SmallCN', fontSize=8.5, leading=14, spaceAfter=8, **base),
        'cell': ParagraphStyle('CellCN', fontSize=9, leading=15, **base),
        'note': ParagraphStyle('NoteCN', fontSize=9, leading=16, backColor=colors.HexColor('#f3ead9'), borderPadding=10, spaceBefore=8, spaceAfter=14, **base),
    }
    story = []
    def p(text, style='body'):
        story.append(Paragraph(escape(text), styles[style]))
    def heading(text): p(text, 'h2')
    def page(title):
        if story: story.append(PageBreak())
        p(title, 'h1')
    def table(rows, widths):
        data = [[Paragraph(escape(str(value)), styles['cell']) for value in row] for row in rows]
        item = Table(data, colWidths=widths, hAlign='LEFT', repeatRows=1)
        item.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#ead9b9')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.7,GOLD),('LINEBELOW',(0,1),(-1,-1),.35,colors.HexColor('#e0d0b6')),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        story.append(item); story.append(Spacer(1,12))
    def picture(name, caption):
        path = args.screenshots / name
        if path.exists():
            from PIL import Image as PILImage
            with PILImage.open(path) as image: width,height=image.size
            story.append(Image(str(path), width=505, height=505*height/width)); p(caption,'small')

    p('戏境 AI', 'title')
    p('文化有据，数字入戏', 'h1')
    p('京剧私有知识库、多Agent协作与交互式数字戏台', 'h2')
    p('比赛技术文档 · 本地交付版 · 2026-10-29')
    p('作品以京剧文化网站为基础，将有来源的知识问答、文化研究与静态3D人物展示衔接。用户可以从剧目分类走近人物，轻点查看介绍，再带着问题回到知识问答。')
    picture('stage-with-content-finder.png', '真实本地浏览器画面：舞台、静态人物与全站内容直达；不代表页面正在重新生成模型。')
    p('本文件覆盖现有实现、实际测试与边界。当前付费API连通性、实体手机及跨机器完整复现仍未验证；演示视频按用户决定由用户后续录制。', 'note')
    p('实施基线：9f089097e19f459a72bb5d376c4d357a6ff15821。正式交付提交以仓库Git记录及交付报告为准。','small')

    page('01 需求与产品路径')
    heading('目标用户与问题')
    p('面向希望了解戏曲的普通观众与文化体验者。传统介绍页能够呈现图片文字，但人物与剧目之间的关系不够直观；通用聊天又容易失去资料依据。作品通过可追溯问答和可操作的数字戏台降低理解门槛。')
    table([['主入口','用户操作','实际边界'],['京剧问答','提问、连续追问、切换已保存会话、展开引用','真实生成依赖DeepSeek；本轮没有付费调用'],['数字戏台','选择剧目、旋转缩放、点击静态人物、查看资料','加载已保存GLB；不触发建模或人物表演'],['全站内容直达','输入“武生”“脸谱”“周瑜”等并按回车','本地关键词与同义词导航；不使用LLM'],['更多工具','查看既有Agent档案、角色方案、资产及企业入口','保留已有能力；企业方向不包装成客户交付']], [90,175,240])
    heading('体验闭环')
    p('进入数字戏台 → 按人物关联剧目选择 → 真实3D浏览与点选 → 阅读人物介绍和参考来源 → 点击“问问这个人物” → 问题进入现有输入框 → 用户自行确认发送。跳转和点选不会自动创建会话或执行AI任务。')
    heading('文化分类')
    p('杜丽娘以《牡丹亭》昆曲题材单独标识；穆桂英关联京剧《穆桂英挂帅》；周瑜关联京剧《群英会》。分类依据已核查的机构介绍，不据模型外观认定某院团、流派或指定舞台版本。')

    page('02 系统架构与资源边界')
    table([['层','已实现组件','数据/调用边界'],['前端','8页HTML、独立CSS、原生ES Module、Three.js r180','不迁移框架；供应商密钥不进入浏览器'],['业务后端','FastAPI、既有聊天/Agent/资产接口','保留鉴权、长度限制、超时及统一错误'],['知识检索','BGE-small-zh-v1.5、SQLite、Qdrant本地持久化','真实512维Embedding和向量检索；私有资源不随Git自动恢复'],['生成解释','DeepSeek服务端调用、证据ID映射与校验','外部依赖；本轮未重新验证真实供应商'],['角色创作','Planner → Research → Designer → Reviewer → 人工确认','真实历史记录与当前执行分开展示'],['数字戏台','本地只读catalog、固定ID文件路由、Three场景/射线点选','不打开业务数据库；文件大小和Hash校验；仅本机访问']], [65,200,240])
    heading('本次新增路径')
    p('浏览器 → GET /api/v1/stage/catalog → 受控本地manifest → GET /api/v1/stage/files/{id} → GLB解析 → 舞台与当前人物组 → Raycaster点选 → 资料面板。文件入口只接受清单内ID及受控目录，拒绝路径穿越、目录逃逸与不匹配文件。')
    p('角色和舞台源文件、派生GLB、真实任务/资产数据库、BGE和Qdrant均保留在本地。Git提交代码、固定第三方源码/许可、模板、Prompt和测试证据，不自动提交大模型文件、个人历史或.env。', 'note')

    page('03 AI技术与意图控制')
    heading('私有RAG')
    p('资料经过来源登记与事实摘要处理，分块后生成BGE向量并持久化。检索与问答服务分离：前者返回结构化证据，后者将有限证据交给DeepSeek解释。引用ID须属于实际命中记录，资料不足按不确定状态处理。当前语料规模与评价边界由Phase 2报告保留，不宣称具有专家金标准准确率。')
    heading('多轮会话与Agent')
    p('普通问答按独立会话持久化，服务端使用有界上下文，历史会话与Agent任务档案不是同一数据。多Agent流程包含任务规划、真实RAG文化研究、角色JSON设计、文化审校和人工确认；历史查看不自动恢复实时执行。')
    heading('人审与费用门禁')
    p('文化审校不能代替文化专家或用户确认。模型创建采用既有SQLite原子预留与幂等保护；项目已用2/3次真实Neural4D建模，剩余1次由用户决定不使用，创建入口继续关闭。本次新舞台和三人物为用户提供素材，不计为新的平台AI生成成果。')
    heading('工程与应用特色')
    p('特色在于证据可追溯、研究/设计/审校分工、人审和创建配额门禁、历史与实时诚实区分，以及从文化页面到数字戏台的渐进整合。这些是有实现依据的工程和产品设计，不宣称行业首创或未经比较的领先性。')

    page('04 模型适配与3D实现')
    p('舞台源为C4D/SKP/ASCII FBX以及OBJ/MTL/27张贴图。使用OBJ路线生成独立派生GLB：按Newell法线主轴投影，Earcut三角化，按材质合并，适配纹理相对路径、CMYK色彩及最大2048像素纹理。不覆盖原件，不使用AI重绘。')
    table([['资产','实际适配','可验证结果'],['舞台','75,654,176字节；46材质合并','1,199,710三角；面积/朝向/原顶点核查通过'],['杜丽娘','原几何缓冲字节保留，贴图规范化','25,480,096字节；源Hash保留'],['穆桂英','原几何缓冲字节保留，贴图规范化','25,452,940字节；源Hash保留'],['周瑜','采用用户替换后独立文件，规范化贴图','25,580,372字节；与其余模型不重复']], [65,225,215])
    p('源面n−2估算与最终相差6三角：2面清理闭环重复点、4面Earcut移除共线点。独立校验未发现面积反向、非原顶点或剩余索引。实际重跑四文件Hash保持一致，36份源文件Hash保持不变。', 'note')
    heading('场景操作')
    p('舞台按包围盒尺度归一化，按实际台面高度放置人物脚底；每个剧目分类默认载入一个人物，减少一次加载全部高面数模型。OrbitControls支持鼠标和触摸旋转、滚轮及双指缩放；射线命中人物后更新资料并近看，舞台遮挡检测避免隔墙点选。Reset返回舞台全貌。')
    p('场景按模型ID与Hash识别版本，失效/过期结果不覆盖新选择；失败释放本轮新建资源。Loading/Ready/Error及手动恢复明确，重新加载仍读取原本地文件。')

    page('05 测试与失败修复')
    table([['实际测试组','结果/口径','说明'],['后端隔离回归','838通过，0失败/跳过','包含新增29项只读戏台资源专项，不重复累加'],['前端原六组','32 / 25 / 42 / 34 / 34 / 23通过','离线DOM/Fetch检查，不代替真实模型'],['新戏台UI与导航','25项 / 32项通过','本地契约与路由测试'],['真实戏台浏览器','14组通过','三人物点选/切换、鼠标、CDP触摸、缩放重置、三视口、HTTP503恢复'],['全站导航与旧功能','46项通过','8页×3视口、直达、问答草稿、历史和两个旧GLB'],['转换独立验证','10组通过','完整GLB、纹理解码、源面朝向/面积、原件不变与重复运行']], [110,155,240])
    heading('真实失败和修正')
    p('保留了网络/沙箱环境限制、检查器对合法byteStride和多边形输出数量的错误假设，以及本地视觉检查发现的舞台朝向、占位提示问题。修正只针对实际根因，不放宽建模保护；新旧结果和工具输出分别归档。首次观察截图同名覆盖的缺口在报告中说明，不补造旧图片证据。')
    p('全站检查进一步发现锚点被固定页头遮挡、记忆的旧资产选择覆盖显式模型链接，均已最小修复并复测。前两轮45项检查分别有4项及1项失败，其中错误测试选择器已与产品缺陷区分；最终46项通过，原失败文件保留。')
    heading('未测项')
    p('实体手机与移动GPU表现、当前DeepSeek真实连通/余额、跨机器完整复现、公网演示与多用户部署不在本轮通过范围。新舞台及人物面数较高；本机浏览器或模拟视口通过不等于低端设备性能保证。')

    page('06 启动、恢复与安全')
    heading('已准备本机')
    p('在VS Code选择“戏境 AI：一键运行”启动现有venv与FastAPI，同一8000端口提供页面与API。问答入口 /about.html#ai-workshop-qa；数字戏台 /about.html#ai-workshop-stage。全站底部输入内容后按回车直达已有栏目。')
    heading('数字戏台资源恢复')
    p('有合法源素材和工具环境时，显式运行node scripts/prepare_digital_stage.mjs，再用Python运行scripts/prepare_stage_catalog.py。转换不初始化业务数据库；在不同机器需提供源文件、Sharp工具与既有BGE/数据库等资源。已准备机器与首次空白机器条件不同，不能承诺完整空白机十分钟完成。')
    heading('数据库与费用安全')
    p('普通服务只打开预期存在的数据库，首次安装使用明确初始化命令；缺失、误配或损坏不自动建空业务库。Agent库异常时相关接口503，独立静态页面与已有资产尽可能可用；恢复正确库后重启。不能用另一份有效但错误数据库冒充原库。')
    p('密钥仅由后端环境变量/本地私有配置读取，不打印Authorization或签名URL。本轮验证实例拦截写请求和外网；没有调用付费API、执行Agent、上传图片或创建模型。资源Hash与业务表比对的最终结果见交付证据。')

    page('07 比赛交付与证据索引')
    p('提交要求依据用户2026-10-29提供的通知截图：GitHub/Gitee Public或评委可访问；README包含简介/架构/运行/团队信息；完整真实Git历史和环境说明；5～8分钟MP4、≥1080p、普通话讲解；技术PDF≤30页，说明需求、架构、AI选型/集成/优化、实现、测试部署、创新与展望。在线演示为可选加分项。')
    p('本PDF属于技术文档交付；录像按用户随后明确指令由用户自行完成，本轮未录制MP4。真实AI协作开发材料已按阶段保存；原项目至少2分钟AI协作片段目标可以从真实Prompt、失败修复与Git中选取，不冒充当日重新付费生成。')
    table([['材料','仓库位置'],['本轮实现和运行','docs/reports/digital-stage-delivery.md'],['本轮真实测试与失败','docs/evidence/test-results/digital-stage-delivery/'],['素材初审与周瑜替换','docs/reports/digital-stage-asset-audit.md'],['提交规格与检查表','docs/reports/phase-05-submission-checklist.md'],['资料与许可范围','docs/reports/phase-05-asset-provenance-and-permissions.md'],['开发Prompt链','docs/prompts/phase-02/、phase-03/、phase-04/及本轮目录']], [145,360])
    p('素材按用户声明仅比赛、非商用；不因此公开全部原件或扩展商业许可。正式赛事全称、截止时间、上传入口与团队最终名单由报名材料核对，本项目不编造这些信息。提交前应冻结版本和文件Hash，人工检查后上传。')

    page('08 资料依据与后续边界')
    for title,url in [
        ('文化和旅游部：上海昆剧团昆剧全本《牡丹亭》','https://www.mct.gov.cn/ggfw/zyjzzt/yanchu/yanchuwqhg/202311/t20231117_949778.html'),
        ('国家京剧院：《穆桂英挂帅》讲了怎样的故事？','https://www.cnpoc.cn/cnpoc/gjkt/200902/1f3f34ac62da46e991b43cd4990c0fe0.shtml'),
        ('国家京剧院：《群英会》讲了怎样的故事？','https://www.cnpoc.cn/cnpoc/gjkt/200902/512246e869864cd9bfb5178e27f2b7fb.shtml'),
        ('Three.js官方源码r180与MIT许可','https://github.com/mrdoob/three.js/tree/r180'),
    ]: heading(title);p(url,'small')
    p('角色资料是据来源核对的简短事实摘要，非机构合作背书或逐字全文复制。人物模型来源为用户提供，其扮相不作为流派或历史服饰的唯一依据。杜丽娘题材明确标注昆曲，避免文化分类混淆。')
    heading('本次完成与后续')
    p('已实现静态3D戏台、人物交互和内容直达；问答、Agent和历史继续复用既有系统。后续如扩充剧目，可增加有来源的人物条目和合法模型版本，不必新增Agent或触发建模。用户已经取消第三次Neural4D任务；未来开发不得绕过该决定。')
    p('文档日期为2026-10-29。技术验证与视频公开提交是不同环节；本地可运行不等于公网已部署，也不代表未测事项已经通过。', 'note')

    args.output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(args.output), pagesize=A4, rightMargin=45, leftMargin=45, topMargin=48, bottomMargin=47,
                                 title='戏境AI 技术文档', author='戏境AI项目', pageCompression=1)
    def decorate(canvas, doc):
        canvas.saveState(); width,height=A4
        canvas.setStrokeColor(GOLD);canvas.setLineWidth(.7);canvas.line(45,height-31,width-45,height-31)
        canvas.setFont('XijingCN',8);canvas.setFillColor(RED);canvas.drawString(45,height-24,'戏境 AI · 技术文档')
        canvas.setFillColor(colors.HexColor('#806c57'));canvas.drawString(45,25,'仅供比赛使用 · 真实证据与已知边界分别记录')
        canvas.drawRightString(width-45,25,str(doc.page));canvas.restoreState()
    document.build(story,onFirstPage=decorate,onLaterPages=decorate)
    reader=PdfReader(args.output);count=len(reader.pages)
    if count>30:raise SystemExit('PDF超过30页')
    metadata={'file':str(args.output),'pages':count,'pageLimit':30,'font':'Embedded SimSun TrueType subset','createdBy':'local ReportLab; no paid API','video':'USER_WILL_RECORD; no MP4 generated'}
    args.output.with_suffix('.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,ensure_ascii=True))


if __name__=='__main__':main()
