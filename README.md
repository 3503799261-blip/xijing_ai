# 戏境 AI

**28页比赛技术文档（2026-10-30）：** 已按当前代码与原始证据扩写，覆盖京剧内容、连续问答、RAG、四Agent与人审、两次历史建模、当前数字戏台、人物点选、内容定位、数据库安全、测试与部署。正式PDF位于本机`output/competition-submission/最终提交版-2026-10-30/02-技术文档/戏境AI-技术文档-28页.pdf`；[可编辑正文](docs/reports/technical-report-28.json)、[生成与核验说明](docs/reports/technical-report-28.md)、[生成器](scripts/build_technical_report_28.py)随源码保留。28页含封面和目录，旧9页PDF已另行归档；PDF与私有素材不随Git分发。

**2026-10-30人物交互修复：** 点击3D人物、人物上方“姓名 · 近看”或左侧人物卡片会切到人物近景，重置回戏台；鼠标/触摸点选与拖拽已区分。浏览器Ctrl+F5读取最新版本。[修复与实测](docs/reports/stage-character-click-fix.md)。本轮26项真实3D点击/触摸与13项补测通过，模型和业务数据不变，无付费调用。最新完整分类副本为`output/competition-submission/最终提交版-2026-10-30/`，旧日期目录保留为历史快照。

**比赛代码入口：** [GitHub项目](https://github.com/3503799261-blip/xijing_ai) · [当前交付分支](https://github.com/3503799261-blip/xijing_ai/tree/feature/phase5-competition-delivery)。**已按用户授权上传完整历史，仓库Public，默认分支已切换到本交付分支，匿名读取与SHA一致性实测通过**；未合并或改写main。见[代码托管检查](docs/reports/submission-platform-check.md)。最终分类副本使用`output/competition-submission/最终提交版-2026-10-30/`，旧日期目录保留为先前快照。源码/环境/技术文档由项目整理，录像由用户自行完成。下文旧报告中的“未推送”是当时事实，不代表本节最新托管状态。

## 团队信息

项目名称：**戏境 AI**。已确认成员：**陈雯雯**，Git维护者。其他真实分工、成员及报名资料以本人核实的信息为准，不补写未经确认的职责或经历。

站点运行依赖见下文及[后端依赖清单](backend/requirements.txt)；素材转换、PDF生成和浏览器验证的可选工具见[工具环境与安装说明](tools/README.md)。

## 当前查看与比赛文件（2026-10-30）

主工坊现只突出 **京剧问答、数字戏台**；旧Agent、历史、创作、原模型和企业入口在“更多工具”。VS Code“运行和调试”选择 **戏境 AI：一键运行**，点击绿色三角。查看[数字戏台](http://127.0.0.1:8000/about.html#ai-workshop-stage)或[问答](http://127.0.0.1:8000/about.html#ai-workshop-qa)。全站底部输入“武生”“脸谱”“周瑜”等后回车可直达；未知内容可带到问答框，不自动发送。

舞台与杜丽娘/穆桂英/周瑜是用户提供的比赛限定素材，已适配GLB、按剧目分类，可点选、旋转、缩放和重置。杜丽娘标昆曲，人物不表演，不代表新调用Neural4D。原两个生成模型与历史保持不变。派生资源在仓库外`../.runtime/digital-stage/assets/`，源码克隆不自带这些模型。

[交付与测试](docs/reports/digital-stage-delivery.md) · [分类和手动检查](docs/reports/submission-manual-check.md) · [证据索引](docs/evidence/test-results/digital-stage-delivery/README.md)。技术PDF为`output/pdf/xijing-ai-technical-report-28.pdf`（28页）；最终分类副本在`output/competition-submission/最终提交版-2026-10-30/`。**用户已提供视频成片，未由助手录制或改动。** 已核对时长7分51.972秒、1796×1080；标准1920×1080画幅、完整普通话及敏感画面检查仍待用户最终确认。输出与原模型不进Git，不含真实密钥。

当前已知参与者：陈雯雯（用户提供的Git提交姓名）；其他团队/报名信息由用户核对，不虚构成员。本轮无付费/新建模；Neural4D仍2/3、余1但第三取消，创建关闭。实体手机、当天API与跨机恢复未测。下文历史按日期阅读，以本节为最新界面状态。

在原有「梨园风华」8页京剧文化网站上建设AI戏韵工坊。前端保留HTML/CSS/原生ES Module与酒红、金色、米白视觉；Phase 2提供真实RAG问答，Phase 3加入规划、文化研究、角色设计、文化审校的真实协作与人工确认。Phase 4提供双风格资产与真实GLB查看器，已逐次批准并实际提交Q版技术模型与写实主展示模型各一次；平台图像生成仍未接入。

当前状态（2026-10-22）：Phase 1～3、Phase 4两模型范围及Phase 5 WP1～4已获用户验收。**WP5已完成比赛材料底稿、证据索引和交付一致性核查，等待人工验收（PHASE_5_WP5_WAITING_ACCEPTANCE）；正式规则和素材公开许可仍有待确认事项，不代表全部参赛要求已满足。** 分支feature/phase5-competition-delivery保留原历史，未合并main、未推送；不能假设远端克隆已包含最新本地成果。

两个真实Neural4D模型均已人工验收，累计实际60积分；**已用2/3、剩1未使用，第三次用户决定不执行，创建保持关闭**。平台图像生成仍未接入，现有图片来自导入。首个Q版仅内部技术用途；写实“绛绣·戏韵”为已生成主展示资产，不是每次新需求即时生成的结果。实体手机未验证。私有GLB、图片、任务及资产数据库不随Git分发，空环境只能先使用合法测试夹具验证Viewer，不能用Duck冒充京剧成品。

[公开仓库](https://github.com/3503799261-blip/xijing_ai) · [Phase 4最终验收](docs/reports/phase-04-final-acceptance.md) · [WP1流程](docs/reports/phase-05-work-package-01.md) · [WP2历史档案](docs/reports/phase-05-work-package-02.md) · [WP3导览及降级报告](docs/reports/phase-05-work-package-03.md) · [WP3实际测试](docs/evidence/test-results/phase-05-wp3-test-report.md)。历史阶段与测试仍由其原报告保留，不把旧状态混作当前状态。

## 工坊问答界面更新（2026-10-23）

打开[AI戏韵工坊](http://127.0.0.1:8000/about.html#ai-workshop)即进入问答：左侧新建/切换真实会话，中间连续消息与逐条引用，底部多行输入（Enter发送，Shift+Enter换行）。角色创作、Agent档案、已有3D和企业需求保留在“创作与数字资产”；比赛导览可以按需展开。

普通聊天与Agent档案分开保存。会话由后端写入`RAG_DATA_DIR/chat-conversations/*.json`，按会话文件锁和原子替换持久化，不迁移或改写既有SQLite。读取空历史不创建文件；首次明确新建对话才创建会话子目录，RAG根目录必须已存在。旧版未保存的页面内问答无法追溯恢复。

服务端从同一会话最近4轮成功问答提取有界上下文，短指代追问补足最近主题进行真实检索；引用仍只允许本轮检索所得资料。已完成请求可按同一幂等标识恢复；模型请求结果未知时阻止重复生成，需查看记录或新建独立会话，不自动重付费。最多200轮，达到上限后新建对话。本地单用户实例没有新增登录或多租户账号隔离，不应直接公开部署聊天历史接口。

[本次改造与实际测试](docs/reports/frontend-productization.md)。本轮只执行免费隔离测试与已有资产检查；新增上下文的真实DeepSeek联测仍需单独授权，不把Mock结果描述为真实AI回答。一键运行入口与私有配置继续沿用[既有配置](docs/reports/local-run-setup.md)。

## 数字资产与3D工作台（2026-10-24）

[工作台](http://127.0.0.1:8000/about.html#ai-workshop-model)现为左操作栏、中间真实Viewer、右侧已有资产库；保持酒红/金/米白，手机纵向排列。右库可选择原写实模型和仅本机内部查看的Q版技术模型，缩略图明确为各自登记概念图。二者不是同一角色的两个风格；没有对应模型的角色仍显示空态。

新增内部列表是原`GET /assets/models?includeInternal=true`的受本机守卫保护选项，默认公开列表仍隐藏Q；文件及创建门禁不变。若当前VS Code服务在改造前已启动，先停止再运行“戏境 AI：一键运行”加载新后端，不需要安装或初始化资源。本轮仅本地免费验证、没有新建模或付费生成；[实际报告与证据](docs/reports/asset-workbench-layout.md)。

## WP4实际启动与恢复结果

[WP4报告](docs/reports/phase-05-work-package-04.md) · [本次测试与命令](docs/evidence/test-results/phase-05-wp4-test-report.md)。2026-10-20～21重新验证，而非仅引用旧报告：

- 原环境与全新普通venv各712项后端通过；前端25/25/34/42/34项；8页×桌面/平板/手机模拟24组合、两个真实GLB及故障恢复通过。真实外部API未验证，本轮调用0。
- 新venv不复用system-site-packages；按原requirements安装348.549秒，11个顶层固定依赖、66个实际包，pip check及实际导入通过。前两次沙箱权限失败保留。没有改变现有venv、requirements或依赖版本。
- 使用已有本地BGE、停止源服务后建立的受控SQLite/索引/资产副本及空Key配置，在独立父目录/8011启动成功；历史、完整台账和原GLB均可读取。这是同机不同目录验证，**不是Git克隆自带私有资源或另一台空白电脑十分钟保证**。没有首次重新下载BGE，没有一键私有资产分发包。
- 缺BGE、知识SQLite或Qdrant时服务明确分类503，不创建空知识文件/集合；恢复确切资源后检索正常。首次WP4复验还发现“损坏Agent业务DB阻断启动、错误但可写的数据目录初始化空业务库”两项问题，原失败证据保留。**2026-10-21已追加安全修复：普通启动只打开已有业务库，Agent数据库故障受控降级，独立资产catalog可用时仍可读取已有GLB**；追加复测以[WP4测试报告](docs/evidence/test-results/phase-05-wp4-test-report.md)为准。
- 18业务表、22任务ID、8个HTML、BGE/知识/向量文件和四原始/兼容模型Hash不变；全局仍2/3余1、第三取消、创建关闭。
- 自动化流程排练正常300.071秒、故障40.038秒，包含明确阅读停留；不是已录真人讲解或合格比赛MP4。实体手机、真人讲解/成片、今日付费API和跨机器交付未测。

本包Hash核对后已按正常方式停止测试服务。下方“已准备本机”命令可启动正常服务；不需要运行安装、重建或供应商探测。后文明确标为WP1～3/旧阶段的“本轮未安装”等描述属于当时边界；当前安装/恢复证据以本节及WP4报告为准。

## 已准备本机：免费启动与已有成果

本机已有venv、BGE、活动索引及私有资产时，只需在仓库根运行以下命令；已有本服务则直接访问，避免第二个进程抢占端口/本地索引：

```powershell
Set-Location -LiteralPath 'D:\京剧\京剧'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

- [首页](http://127.0.0.1:8000/index.html)、[AI工坊](http://127.0.0.1:8000/about.html)。同一8000端口提供安全静态资源与API，不用`file://`或把整个仓库公开的静态服务器。
- [Agent历史档案](http://127.0.0.1:8000/about.html#ai-workshop-history)：在协作区点击“读取历史记录”，按状态、类型或完整任务ID筛选。查看详情、阶段公开产物、引用、文化审校、人审和事件均只发GET，不重跑任务、不恢复实时监控。详情中的资产入口只打开已有模型。
- [比赛演示导览](http://127.0.0.1:8000/about.html#ai-workshop-demo)：六步说明→手动进入对应功能；可以跳步、退出。只读备用模式会拦截当前页面的问答/Agent提交、确认/取消和资产写操作，允许历史GET与Viewer操作；刷新或新页退出，本页保护不是后端权限或全站开关。
- [已有写实模型](http://127.0.0.1:8000/about.html?assetId=9e2b42e1-bbad-4a2f-ab1b-aeda18015dee#ai-workshop-model)：只GET已登记资产/GLB；绛绣切Q版会诚实显示未生成，不会取别人的Q版模型。
- [内部Q版技术Viewer](http://127.0.0.1:8000/api/v1/assets/internal-models/3777a880-fc8c-4766-aade-948d20c6b8f0/viewer)：仅loopback/内部用途，没有正式角色关联，不用于公开或商用交付。
- [health](http://127.0.0.1:8000/api/v1/health)、[capabilities](http://127.0.0.1:8000/api/v1/capabilities)、[全局额度](http://127.0.0.1:8000/api/v1/assets/usage)：本地免费读取；问答“就绪”包含既往探测/配置指纹状态，不是实时余额/外网连通测试。

普通启动校验已有业务数据库，不创建缺失数据库或自动补表；仍会按既有机制处理已保存的中断状态，因此不是纯只读操作，但不会自动重新执行Agent、探测外部API或建模。健康检查分别报告应用、Agent数据库和预算数据库；Agent数据库故障不会阻断静态文化页面，资产catalog和文件完好时已有GLB仍可查看；预算数据库不可用时停止付费调用。修复配置或恢复原库后重启，不能把降级状态当成数据恢复成功。停止时在启动终端按Ctrl+C，等进程退出；不要删除owner锁或强开第二个worker。**WP1～WP3均不发送真实问答、不提交Agent，不运行任何供应商探测、建模或图像生成工具；WP3故障测试仅用明确的浏览器响应替身。**

## WP3比赛导览与免费备用路线

导览顺序：认识戏境AI → 京剧问答及引用 → 已保存Agent历史 → 角色JSON/审校/人审 → 两个已有真实模型 → 企业应用方向。步骤变化只是导航，不代表AI任务完成；先阅读说明，再点击“前往这一步对应的功能”。历史步骤可明确点击填入绛绣任务ID，然后由用户手动读取WP2记录，不自动查询或执行。

“检查本地演示条件”只手动GET健康、历史摘要、写实模型登记与额度四项。初始未检查，每项独立成功/错误；知识就绪不等于当天DeepSeek可用，模型登记可读不等于GLB已加载。没有外网LLM时可以看本机历史和GLB，但仍需要本地后端与私有文件，不是离线大模型。后端本身不可用时保留文化页面及静态说明，不补造答案或历史。

备用模式仅当前页面有效，不停止已经在后台运行的任务。两个模型链接打开新页，原备用页仍保留；新页不继承保护，应只查看已有Viewer。Q版仍限内部非公开回环用途，公开主展示优先写实。企业为需求入口和应用方向，无真实企业客户或交付案例。

问答失败保留输入，结束等待并允许手动重试，不自动重复模型调用；历史为空/404/异常时按真实状态提示。资产首次读取失败可通过“读取本地模型与额度”按钮重读相同资产ID；失联时已有模型标为加载快照，风格读取失败显示状态未知。GLB Error只重新加载原文件，绝不重新建模。详细失败与复测见[WP3测试报告](docs/evidence/test-results/phase-05-wp3-test-report.md)。

## 架构与数据边界

`about.html → services.js → FastAPI /api/v1/chat → 独立SearchService → 本地BGE/SQLite/Qdrant → 获准证据 → DeepSeek → 后端引用校验 → 安全文本回复与引用`。

- 同一FastAPI进程在8000端口提供前端与API，默认同源，无前端构建或npm依赖。
- 静态服务仅允许8个HTML及css/js/images/audio/media；不公开仓库根、backend、docs、.git、env、知识资料或运行数据。
- SQLite保存来源与实际片段；Qdrant Client local保存真实512维余弦向量。默认混合检索先执行真实BGE/Qdrant，再以已收录实体、FTS5/BM25及RRF补充和排序；每条证据保留实际向量分数、词项分数与接受路径。实体命中低于语义阈值时明确标记，不冒充高相似度。纯向量模式仍可用于实验。
- 模型：CPU `BAAI/bge-small-zh-v1.5`，固定revision `7999e1d3359715c523056ef9478215996d62a620`；服务运行时仅从本地载入，不隐式下载或退化为假Embedding。
- 语料是12份有真实核查来源的**本项目原创事实摘要**，初次实际入库35片段；不是官方全文或官方逐字原文。来源核查由助手完成，用户/专业人员人工复核待完成。许可仅覆盖获准摘要用途，见 [知识来源与范围](docs/architecture/knowledge-provenance.md)。
- 私有环境文件默认 `D:\京剧\.private-config\.env`；索引/预算默认 `D:\京剧\.runtime\xijing-ai\`；模型默认 `D:\京剧\.runtime\models\bge-small-zh-v1.5\`。三者均在本仓库之外。

详细实现见 [RAG架构](docs/architecture/phase-02-rag.md) 与 [前端约定](docs/architecture/ai-workshop-contracts.md)。

## 环境与依赖

既有验证环境为Windows/Python3.11.1；Node用于前端离线检查，网站运行不需要前端构建。Phase 2/3的Node24.15.0是历史版本，Phase 4最终记录为Node24.19.0/Chrome155.0.8059.84；WP1本轮实际版本以测试报告为准。依赖固定在`backend/requirements.txt`，原环境包括FastAPI0.143.0、uvicorn0.54.0、pydantic-settings2.15.0、httpx0.28.1、qdrant-client1.19.1、sentence-transformers6.1.0、numpy2.4.4、pytest9.1.1、Pillow12.2.0和portalocker3.2.0。

本机 `.venv` 实际使用 `--system-site-packages`，复用已有CPU torch（包元数据2.11.0），避免重复下载大体积依赖。这是本次环境条件；干净机器应使用普通隔离环境。`backend/requirements.txt` 指定CPU torch2.11.0+cpu及CPU wheel来源，冷机安装整套依赖尚未从零计时验证，不将复用环境当成干净锁定环境。

以下是**新环境准备说明，本次WP1没有执行克隆或安装**。克隆后先核对交付分支/提交以及backend、knowledge是否存在；未推送的WP1代码不能从远端自动取得。不要使用旧Phase 3分支克隆命令来声称拿到了最新交付：

```powershell
git clone https://github.com/3503799261-blip/xijing_ai.git
Set-Location -LiteralPath 'xijing_ai'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

使用本机已有项目时直接进入 `D:\京剧\京剧` 并复用已准备的 `.venv`，不需要重新创建环境。不得为了加速冷机安装无条件复用未知系统包。

## 私有配置

`.env.example` 是无密钥模板；浏览器不会读取它。默认私有env路径是仓库父目录下 `.private-config/.env`；也可通过启动环境 `XIJING_ENV_FILE` 指定仓库外路径。以下是当前本机路径示例，已存在配置不会被覆盖：

```powershell
Set-Location -LiteralPath 'D:\京剧\京剧'
$projectParent = Split-Path -Parent (Get-Location).Path
$privateDirectory = Join-Path $projectParent '.private-config'
$privateEnvFile = Join-Path $privateDirectory '.env'
New-Item -ItemType Directory -Force -Path $privateDirectory | Out-Null
if (-not (Test-Path -LiteralPath $privateEnvFile)) {
  Copy-Item -LiteralPath '.env.example' -Destination $privateEnvFile
}
```

仅在确需真实文本问答/Agent且已有授权时，用本机编辑器填写`DEEPSEEK_API_KEY`；不得发到聊天、提交Git或出现在截图/日志。仅查看已有GLB不需要调用供应商。配置改变后重启后端。模板中的RAG_DATA_DIR/EMBEDDING_MODEL_PATH默认注释，采用代码按仓库父目录推导的路径；如需覆盖，填写仓库外绝对路径，**不要写空等号**。`XIJING_ENV_FILE`若覆盖也应指向仓库外绝对路径。现有私有.env不被模板修改覆盖。

| 字段 | 当前实现 |
|---|---|
| DEEPSEEK_API_KEY | 后端秘密字段，默认空；真实问答需要有权限和余额的有效Key |
| DEEPSEEK_BASE_URL / DEEPSEEK_MODEL | 只允许官方 `https://api.deepseek.com` / `deepseek-flash` |
| DEEPSEEK_THINKING_ENABLED | 必须false；非流式，不保存隐藏思考 |
| DEEPSEEK_MAX_OUTPUT_TOKENS | 默认800且最大800 |
| RAG_TEST_BUDGET_CNY | 默认3且配置上限3；应用预算，不是供应商账单硬限 |
| AGENT_TEST_BUDGET_CNY | Phase 3增量默认0.5元；持久化后只能收紧，不能靠重启增额 |
| AGENT_WORKFLOW_ENABLED / AGENT_QUEUE_LIMIT | true / 2；单工作流执行，最多两个等待任务 |
| AGENT_WORKFLOW_TIMEOUT_SECONDS | 150秒执行期限；不包含人工确认等待 |
| RAG_DATA_DIR / EMBEDDING_MODEL_PATH | 仓库外SQLite/Qdrant/预算与本地模型目录 |
| ALLOWED_ORIGINS | JSON数组，仅明确的localhost/127.0.0.1及8000/8877端口 |
| RETRIEVAL_MIN_SCORE | 当前0.57；基于候选开发题调参，不是置信概率 |
| RETRIEVAL_MODE | 默认hybrid；可设vector对照，实际策略写入检索结果 |

后端请求总预算默认45秒、供应商默认35秒；浏览器55秒超时，超时不会自动重发模型请求。完整校验依据 `backend/app/config.py`。

## 业务数据库：首次安装与故障恢复

2026-10-21数据库安全修复后，普通服务使用SQLite已有文件模式，检查文件、当前Schema与完整性；路径错误、文件缺失、目录误作文件或损坏均不会创建替代空库，也不会自动迁移、删库或补齐损坏结构。没有符合当前Schema的Agent/预算数据库时，相应接口明确返回服务不可用，不伪装成空历史或可付费状态。

**仅确认是全新安装且没有需要恢复的既有业务数据时**，先核对仓库外 `RAG_DATA_DIR`，再显式创建Agent、预算和资产三类业务数据库：

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.initialize_business_databases --initialize-new-installation
```

- 该命令先检查所有已存在的业务库；遇到损坏或不完整Schema即停止，不覆盖或修复原文件。已有合法数据库保留原记录；旧版仅含`calls`表的预算库不会自动升级，需人工核对原数据与备份后另行制定迁移方案。
- **已有项目出现数据库缺失、路径错误或损坏时，停止服务、核对配置并恢复对应原备份；不要运行上述新安装命令制造空历史或空预算。** 不要删除损坏文件、清空业务表，或通过改目录规避原预算。
- 该命令不创建、重置或对账全局Neural4D额度账本，不恢复私有模型、图片或任务成果。已有项目必须保留其真实账本和资产；缺失时保持状态未知、创建关闭，不能初始化为0次或用测试资产替代成品。
- RAG知识库仍通过下文独立、显式的模型准备与资料入库流程构建；业务初始化不下载BGE、不创建Qdrant索引、不调用供应商。正常启动和本地健康检查也不证明当天DeepSeek或Neural4D连通、余额或付费权限。

## 不随Git取得的资源及缺失行为

下表的“仓库父目录”在本机为`D:\京剧`，不是必须使用同一个盘符；历史任务ID/模型ID仅对已恢复对应资产的环境有效。

| 资源 | 当前位置/用途 | 准备方式及缺失时行为 |
|---|---|---|
| Python/venv与依赖 | 仓库`.venv`，本机存在 | 新机器按真实requirements安装；WP1当时未安装；WP4实测范围见顶部 |
| 私有env/Key | 仓库父目录`.private-config/.env` | 本机手工配置，绝不入Git；没有Key时实时问答/Agent不可用，不生成假答案 |
| BGE缓存 | 父目录`.runtime/models/bge-small-zh-v1.5` | 固定revision下载见下节；缺失则知识能力降级，不换成随机向量 |
| SQLite知识/Qdrant | 父目录`.runtime/xijing-ai/active.json`选择`generations/<generation>/knowledge.sqlite3`及`qdrant/` | 从knowledge入库；不能误找RAG根下不存在的knowledge.sqlite3；缺失/锁冲突会提示未就绪 |
| Agent与预算记录 | RAG_DATA_DIR中的`agent-tasks.sqlite3`、`api-budget.sqlite3` | 普通启动只打开已有库；缺失/损坏返回明确503，不自动初始化。新任务仅明确提交时写入；不复制整库公开、不删除预算。合法库中缺历史UUID返回未找到，不自动重跑 |
| 真实图片/模型及资产关联 | RAG_DATA_DIR下`assets/catalog.sqlite3`、`images/`、`models/` | 需受控保留本机授权文件与关联记录；Git不含它们。catalog不可用时报告资产服务未就绪；合法catalog中缺记录/文件显示未找到、未生成或Viewer Error，可重载原文件；不自动下载/重建 |
| 两份供应商原文件 | 同assets目录的`recovery-quarantine/` | 保留原Hash及本地兼容谱系，不作为普通重新转换命令执行；当前兼容GLB均内嵌纹理，无需额外外链贴图 |
| 全局三次账本 | 父目录`.runtime/neural4d-usage.sqlite3` | 保留真实2次历史与固定上限3；缺失只能保持历史未知/创建锁定，不能自动填0或换新额度池 |

已有真实GLB：Q版8,827,324字节，SHA-256 `bf9c808c15dbf5464ee67df1cdb3f64f9b2c6b3cd4ee41ecb8a6470a0554654a`；写实15,158,668字节，SHA-256 `5a021ac6338009615e6ea232c5b9001eef6f4cc91d9d87c3eeeb5307526bdfd5`。文件位于`assets/models/<Hash>.glb`，角色/图片/Prompt/任务关联与原文件Hash见[Phase 4最终报告](docs/reports/phase-04-final-acceptance.md)。跨机器受控资产迁移还没有实现一键导入，不能承诺仅clone即可完整展示两成品。

## 模型下载、入库与启动

以下仅在新环境缓存/索引缺失时准备，**不是本机每次启动必跑，本次WP1未下载、重建或恢复生产数据**。先下载固定snapshot，再入库；约95.8MB权重及配置/tokenizer不含CPU PyTorch/其他依赖体积。

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.download_model
.\.venv\Scripts\python.exe -m backend.scripts.ingest --corpus knowledge --output docs/evidence/test-results/local-ingest.json
```

模型文件Hash及revision保存于仓库外 `model-manifest.json`；相同语料/参数/revision重复入库会返回unchanged，不重复追加。更新资料或明确重建时使用 `--rebuild`，构建新generation后切换active.json，失败保留旧活动索引。

**先停止应用再运行入库、重建或独立检索评估。** 应用/入库共享独占锁；Qdrant local禁止多进程共同打开同一目录。后端只用一个worker：

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

打开 [首页](http://127.0.0.1:8000/index.html) 或 [京剧问答](http://127.0.0.1:8000/about.html#ai-workshop-qa)。当前前后端均为8000，默认相对 `/api/v1`；不要继续使用把整个目录公开的Python HTTP Server代替安全静态服务。停止时在启动终端按Ctrl+C。

免费检查[health](http://127.0.0.1:8000/api/v1/health)、[capabilities](http://127.0.0.1:8000/api/v1/capabilities)。没有Key仍能完成本地入库/检索；知识未就绪或没有同配置成功探测记录时问答不就绪。已保存成功探测只表示最近记录与配置相符，不保证今天外网/余额有效。

`backend.scripts.check_provider`运行即调用真实DeepSeek并计入预算，不是免费健康检查；WP1禁止执行。需要真实文本联测时必须另获授权，再参考[Phase 2历史运行说明](docs/reports/phase-02.md)。本地能力端点自身不进行供应商探测。

## 接口与问答使用

| 方法/接口 | 行为 |
|---|---|
| GET /api/v1/health | 索引、Embedding、LLM配置/验证及非秘密预算摘要 |
| GET /api/v1/capabilities | 问答、检索、Agent依据实际服务与预算就绪；conceptImage仍false，imageToModel按真实建模门禁返回、当前false；assetManagement/modelViewer反映本地资产服务可用性 |
| POST /api/v1/knowledge/search | question、可选topK/category；真实片段/来源/分数，无LLM调用 |
| POST /api/v1/chat | question、可选conversationId；answer/citations/uncertain/requestId |
| GET /api/v1/knowledge/sources | 允许公开的来源与许可元数据 |

问题上限600个UTF-16字符单位；检索模型问题加指令最多512 tokens，超限明确提示。不带conversationId的兼容请求仍独立检索；工坊使用后端持久化会话与有界上下文，刷新可恢复。推荐问题只自动填入，由用户发送；引用在对应回答下展开。会话最多200轮，模型只取最近4轮成功问答作为上下文。模型正文和资料均按安全文本渲染。

缺Key、未入库、鉴权/余额/网络/超时、无效引用均有明确错误或资料不足状态。不返回供应商原始错误、堆栈或假AI答案。加载时禁止重复发送；手动重试沿用同一幂等标识，无自动付费重试。

## Phase 3角色协作与验证

同一后端运行 `用户需求 → Planner → Researcher真实RAG → Designer → Reviewer → 人工确认`。没有新增框架依赖。正常路径三次DeepSeek调用；研究使用原BGE/Qdrant/SQLite，没有第四次模型聊天。“整理我的草稿”仍是本地功能；点击“提交Agent创作”才上传必要需求和获准证据到云模型。

Agent模块管理严格JSON交接、任务SQLite、单消费者与独占进程锁。计划查询与实体补查合计最多三次、最终最多五片段；保留原分数与不足记录。事实标为据资料设计，新增形制/姓名/配色标为原创，所有引用由程序映射到本次真实证据。模型审校不能代替京剧专家。

| 方法/接口 | 行为 |
|---|---|
| POST /api/v1/agent/create | requirements、style、可选parentTaskId；X-Idempotency-Key防重复 |
| GET /api/v1/agent/status/{taskId} | 四阶段、公开摘要、事件序号、确认原因；免费读取 |
| GET /api/v1/agent/result/{taskId} | 实际方案、引用、审校、版本；未生成方案为409 |
| POST /api/v1/agent/confirm/{taskId} | 当前confirmationId、expectedSequence、action=accept；不调用模型 |
| POST /api/v1/agent/cancel/{taskId} | expectedSequence；运行阶段收尾后停止后续调用 |

输入最多1200个UTF-16字符单位，三种已有风格；等待/运行/待确认/完成/失败/取消均来自后端。资料不足、澄清或审校问题会暂停，不能绕过门禁导出。四阶段完成、审校pass、无资料不足且明确确认后才能下载角色JSON。费用不因取消撤回；无自动付费重试或循环修改。

打开 [角色创作](http://127.0.0.1:8000/about.html#ai-workshop-create)，例如填写：“为京剧科普展设计原创青年男性武生，说明大靠、厚底靴和靠旗依据；蓝金与云纹是原创，不称统一传统配色。”提交后阅读阶段、方案和引用，再自行核查并确认。文字视觉Prompt不等于图片。

刷新只恢复task ID并免费查询，不重新提交。重启保留已完成/待确认任务；意外中断的运行任务标失败且不重发模型。调整需求明确创建新任务，关联前一任务、保留历史。只使用一个worker；索引锁与Agent任务锁分别保护数据和调度。任务数据库与两级预算账本均位于仓库外RAG_DATA_DIR。

### WP2：读取持久化历史

历史档案独立于实时创作控制器。先进入[历史档案](http://127.0.0.1:8000/about.html#ai-workshop-history)，手动读取；列表默认每页10条，详情事件默认每页30条。筛选条件变化后点击查询，上一页/下一页沿用上次已提交条件。缺少详细输入、产物或时间会显示“历史记录未保存该信息”，不自动补写。历史状态始终标为记录状态，不播放过去事件冒充实时执行。

| 方法/接口 | 只读行为 |
|---|---|
| GET /api/v1/agent/history | page/pageSize（最多50）、state、taskType、taskId；创建时间倒序及ID稳定排序，只返回摘要 |
| GET /api/v1/agent/history/{taskId} | 已保存公开产物、RAG引用、角色JSON、审校、人审、分页事件及明确资产关联；eventPage/eventPageSize（最多100） |

读库使用独立SQLite `mode=ro`、`query_only`事务；不调用任务执行/恢复服务。两接口无缓存；只展示受限公开字段，正文按文本渲染，凭证、内部路径、隐藏思考及URL查询参数不会作为历史内容返回。当前项目仅有本机可信使用边界，没有新建跨用户权限系统，不能据此直接公开部署历史接口。

本机实际22任务/194事件，其中16条带持久化评测标识；这些是已有执行记录，不是本次生成，也不把评测记录称为独立供应商认证。单个阶段的完整请求输入没有保存。任务类型`character_creation`按既有工作流派生，开始/结束仅取已有事件，缺失则未知。新克隆没有这些私有数据库时不造历史；空库显示无记录，无法读取显示错误。

示例完整任务ID：`ca7007e7-e535-4b1f-a9b6-1932f10e20b4`（绛绣·戏韵）。其详情只链接已关联的写实资产；内部Q版没有正式角色关联，不会借用。目录中的测试GLB会标“测试夹具”，不按目录数量宣称真实模型数量。完整数据盘点、API、测试边界及不变性证据见[WP2报告](docs/reports/phase-05-work-package-02.md)。

Phase 3历史检查：后端213项；Agent前端25项、原问答前端25项离线检查；真实HTTP API14项；8页/62资源及6个受保护路径；桌面/手机模拟浏览器。16次脚本工作流加4次浏览器创作包含失败与暂停，不能称20个成功方案或独立盲测。该阶段“武生约4秒、待确认”描述的是当时任务，不是今日重新执行。见[历史浏览器报告](docs/evidence/test-results/phase-03/browser-test-report.md)、[Agent架构](docs/architecture/phase-03-agents.md)、[真实案例汇总](docs/evidence/test-results/phase-03/real-cases-summary.json)。

```powershell
# 以下为前端双桩/本机GET检查，不是实际模型证据；使用新输出文件。
node scripts/phase3_frontend_test.mjs --output docs/evidence/test-results/local-agent-frontend.json
node scripts/phase2_frontend_test.mjs --output docs/evidence/test-results/local-qa-frontend.json
.\.venv\Scripts\python.exe scripts/phase2_http_smoke.py --output docs/evidence/test-results/local-http-regression.json
```

缓存依赖/模型/索引/有效API权限是本次前提，Phase 3没有重新安装依赖、下载模型或重建未变化语料。首次空电脑完整安装时间未验证；下方Phase 2缓存实测不能当作Phase 3冷机十分钟承诺。

## 已验收的数字IP中心与两份历史真实模型

两次真实建模均已完成并获人工验收：Q版内部技术验证与写实绛绣·戏韵。全局2/3、剩1未用、累计60积分；无UNKNOWN/在途或待消费批准；[原三次计划](docs/reports/phase-04-real-modeling-plan.md)中的第三次已由用户取消，不是失败。创建保持关闭，不通过查看、测试或风格切换重新生成模型。早期PARTIAL、历史未知或仅1次的快照保存在原报告，不再作为当前状态。

打开 [数字IP中心](http://127.0.0.1:8000/about.html#ai-workshop-model)。本阶段复用已确认的Phase 3角色任务，不迁移前端框架，也不重新执行Agent。`Q版卡通(chibi)` 与 `写实国风(realistic)` 是资产视觉风格；个人/企业是用途模式，两者独立。相同文化方案的两种风格共享characterId和文化来源快照，各自保存assetId、styleVersion、Prompt、图片和模型记录。切换风格只读取已登记版本，不自动生成、不覆盖另一种风格。

已实现本地角色登记、固定模板视觉Prompt、人工视觉确认、实际图片导入/Hash/接受、合法已有GLB导入与查看、SQLite资产记录，以及真实建模服务的默认关闭门禁和离线Mock测试。自由编辑Prompt会新建不可覆盖版本，并锁为待文化复核草稿；必须经既有Agent流程重新审校并确认新任务，不能靠客户端声明或单纯视觉确认解除文化门禁。旧图片、模型和已发送任务保留历史归属。

**本节初版搭建时未调用真实Neural4D建模或平台图像供应商API。** 后来逐次批准的两次真实建模以本文开头及执行报告为准，平台图像生成仍未接入。许可与文化确认按每个实际资产记录，不能推定商业授权、文化专家审核或本平台真实图像生成。企业模式只记录机构、受众、用途和边界，不承诺商业交付、骨骼绑定或游戏可用规格。

`model-viewer 4.4.0` 已在本地保存，加载真实GLB，不用图片/GIF/视频伪装3D。Duck是附有原许可的已有合法Viewer测试素材，独立于角色风格资产，也不是Neural4D输出或京剧数字IP。查看器提供水平旋转、缩放按钮、重置视角、Loading/Ready/Error和显式失败重载。两份真实角色GLB均已完成桌面浏览器验证，第二模型另有CDP触摸及双指手势模拟证据；它们与早期Duck的391.8°记录分开保存。**实体手机单指拖动、双指缩放和性能未验证，移动模拟不能替代真机**。见[最终验收报告](docs/reports/phase-04-final-acceptance.md)及[早期浏览器记录](docs/evidence/test-results/phase4-browser-test-report.md)。

### 本机准备与免费启动

复用上文已准备的Windows Python环境、BGE模型和索引。新增依赖Pillow12.2.0、portalocker3.2.0已列入 `backend/requirements.txt`；对环境缺失的安装仍使用上文依赖命令。**不承诺空白电脑十分钟完成依赖、模型下载、知识库初始化和全部验收。**

项目已包含本地Viewer及Duck文件。先停止应用，再将合法测试GLB登记到仓库外资产目录；该命令不调用任何模型或供应商：

```powershell
Set-Location -LiteralPath 'D:\京剧\京剧'
.\.venv\Scripts\python.exe -m backend.scripts.prepare_phase4_assets
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

进入数字IP中心，展开“其他已登记素材”，在“独立校验素材（非角色资产）”中选择Duck，检查真实模型、拖拽、放大/缩小和重置。这只验证已登记GLB查看器，不会创建角色模型。角色登记则需要实际已完成四Agent、审校pass、无资料不足且用户确认的taskId；不要把测试夹具登记成真实服务器任务。

如果交付文件确实缺少本地Viewer或Duck，以下脚本才从免费公开地址下载缺失文件，并记录Hash；不读取API Key、不调用Neural4D。它不是图像/模型生成器，下载后仍应运行离线检查和浏览器验收：

```powershell
.\.venv\Scripts\python.exe scripts/prepare_phase4_viewer_fixture.py
```

资产SQLite和Hash文件默认在 `D:\京剧\.runtime\xijing-ai\assets\`；图片实际解码并移除元信息。GLB检查真实几何、内嵌PNG/JPEG、引用范围、大小和像素预算，禁止外部URI；这是结构与资源安全门禁，**不是完整Khronos规范认证**。同Hash文件不会被重复发布覆盖，损坏时停止加载并要求人工核查。

### 免费检查与测试隔离

后端测试使用明确Mock与临时账本，但直接导入`backend.app.main`会先构造默认app；WP1核查发现旧版在收集阶段早于autouse夹具，可能初始化本机默认库。2026-10-21修复后普通构造只校验已有库，测试仍须避免读取或处理生产状态。为严格免费且不触生产资源，继续使用**收集前测试专用隔离**：空env/Key、临时RAG与canonical账本、真实HTTP transport拒绝、生产文件/SQLite访问守卫；测试成功场景显式初始化隔离业务库，缺失/损坏用例不自动初始化。不改变生产配置入口或额度算法。复现时从仓库根执行以下已归档辅助，选择全新的临时目录：

```powershell
$projectParent = Split-Path -Parent (Get-Location).Path
$testRun = Join-Path $projectParent '.runtime\phase5-wp1-local-review-01'
.\.venv\Scripts\python.exe docs/evidence/test-results/phase-05-wp1/offline-bootstrap.py --run-root $testRun --junitxml (Join-Path $testRun 'pytest.xml') --basetemp (Join-Path $testRun 'pytest-temp')
```

该脚本只能在独立测试进程使用，新目录内保存JUnit及真实退出码；目录已存在会拒绝，不能用来改生产账本。离线测试不是真实Neural4D/DeepSeek成功证据。前端DOM双桩不替代浏览器/GLB/触摸测试；以下只读GET和前端脚本仍可分别验证：

```powershell
node scripts/phase4_frontend_test.mjs --output docs/evidence/test-results/local-phase4-frontend.json
# 服务已启动时，这两个接口仅读取本地状态，不发起供应商请求。
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/assets/usage'
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/assets/models'
```

WP1本轮命令、隔离失败/修正、数量及浏览器结果以[测试报告](docs/evidence/test-results/phase-05-wp1-test-report.md)为准；Phase 4的675通过及52项重叠专项是历史，不相加成独立727项。保留[历史Windows文件并发失败与修复](docs/evidence/test-results/phase4-windows-file-race.md)。不能用旧结果掩盖本轮失败，也不能通过删除/跳过测试做成全绿。

### 已实现的创建保护（历史能力，当前禁止新建）

全项目累计最多 **3次新建模型任务HTTP提交尝试**，每次 `modelCount=1`；失败、超时、未知结果也占用次数，禁止自动重发或返还。固定账本是 `D:\京剧\.runtime\neural4d-usage.sqlite3`，与风格、用途、RAG目录和服务重启无关。SQLite原子预留、幂等与发送者独占保护共同生效，浏览器和Agent不能绕过服务入口调用供应商。

用户此前已明确核实项目外部历史为0，随后两次实际创建均已入账；目前已用2/3、剩1、无UNKNOWN或在途任务，无未消费审批。第三次为用户取消且未执行，不占次数。`backend.scripts.neural4d_history` 是一次性可信人工对账工具，既有账本不能再次初始化、清零或迁移到新的额度池；它不属于普通复现步骤。

原服务的保护检查包括以下项目，它们是历史实现说明，**不是当前申请生成的操作指引**：

- 用户分别批准本次任务；阶段开发批准不等于任何一次真实建模授权。
- 核对当前官方接口和账户Credit费用，真实API Key只填仓库外私有env；不发到聊天、前端、日志或Git。余额验证也是供应商请求，不能作为免费本地健康检查自动运行。
- 确认角色文化来源、风格版本、最终Prompt、已经接受的真实概念图及其Hash、参数、用途、预计Credit、已用/剩余额度和许可。
- 使用独立后端管理授权、已核实历史额度、有效余额/协议验证；本地配置默认 `NEURAL4D_GENERATION_ENABLED=false`、`NEURAL4D_PROTOCOL_VERIFIED=false`，费用为空、下载域名白名单为空。不要为普通Viewer或免费测试开启真实创建。
- 对超时或未知状态先核查供应商已有任务；有可靠任务ID时才主动查询，不能通过重新生成解决未知结果。下载只允许人工核验的HTTPS域名，生成结果需继续通过GLB与浏览器验证。

第2次已完成并获人工验收，两份批准均已消费；用户决定取消第3次并禁止再提交。Phase 5 WP1只梳理状态/流程与免费验证，不调用任何新建、供应商刷新或付费生成接口；不进入WP2～WP5。

## Phase 2历史测试与十分钟复现边界

已有依赖、模型缓存、真实权限的机器可依次入库、启动、检查状态并完成核心问答。最终版本完整重建索引、启动新后端、HTTP打开前端及一次真实RAG实测 **25.6704秒**，见 [缓存复现](docs/evidence/test-results/phase-02-cached-reproduction-final-hybrid.json)。**首次空环境需要依赖和模型下载，尚未测得整体十分钟安装结果**；缓存条件不能作为冷机复现承诺。固定模型首次实际下载12.691秒，但该值同样依赖本次网络与已有CPU依赖。

已有真实证据：初次12文档/35片段的512维向量入库约30.5013秒；隔离副本中的真实CPU首次/幂等/更新/重建/重开/写锁/失败保旧生命周期检查约16.6563秒；单次32-token上限的真实Provider探测成功。[初次入库](docs/evidence/test-results/phase-02-ingest-initial.json)、[真实生命周期](docs/evidence/test-results/phase-02-real-lifecycle.json)、[探测结果](docs/evidence/test-results/phase-02-provider-probe-success.json)。

Phase 2历史评价可按需复查；本次不重建索引。离线pytest请使用上方收集前隔离命令，前端检查与独立检索使用新输出路径/标签：

```powershell
node scripts/phase2_frontend_test.mjs --output docs/evidence/test-results/local-frontend-unit.json
# 独立评估会占用本地索引，先停止应用；默认标签使用真实时间，避免覆盖旧结果。
.\.venv\Scripts\python.exe -m backend.scripts.evaluate_retrieval
```

Phase 2当时后端124项、前端25项通过，均标注fake/mock边界，不是当前全部测试数，也不作为真实Embedding/LLM证明。真实模型、入库、检索和浏览器证据独立保存；初始失败保留。[历史前端离线](docs/evidence/test-results/phase-02-frontend-unit.json)、[历史后端回归](docs/evidence/test-results/phase-02-final-unit-regression.json)。

20题全部执行真实本地Embedding/向量与混合对比。最终混合候选证据覆盖为18支持题全部命中；题目由助手核对，**不是人工gold Recall@5**。同批题被用于调参；5题留出也已用于诊断，不宣传为独立盲测。错误人物仍可能命中相似材料，真实LLM应说明限制。[最终检索](docs/evidence/test-results/phase-02-retrieval-final-entity-metadata-same20-comparison.json)。

最终20题真实HTTP联测全部成功，其中18次实际DeepSeek生成、2题证据不足直接受控返回；平均HTTP耗时1.103882秒，37个引用均能映射真实片段。助手逐题核查为18个支持回答、2个资料不足，专业人工审核/人工正确率仍待完成。另5题补充联测全部成功，其中错误人物前提被明确拒答。仅 **5对**执行真实“直接DeepSeek vs RAG”对照，不能称20题完整对照。[真实20题](docs/evidence/test-results/phase-02-answers-rag20-final-hybrid.json)、[引用核查](docs/evidence/test-results/phase-02-answers-rag20-final-hybrid-assistant-review.json)、[五题对照](docs/evidence/test-results/phase-02-direct-vs-rag-five.json)。

8页浏览器/资源回归、1920×1080桌面、390×844手机及768×1024工坊Agent视口实际完成；四推荐问题、展开引用、连续提问、空输入、停机恢复、安全文字与未接入模块均已实际操作。7个文化HTML逐字节保持Phase 1版本。见 [浏览器实测报告](docs/evidence/test-results/phase-02-browser-test-report.md)。

`check_provider`、`evaluate_answers`、`evaluate_baseline`、`evaluate_agent_workflow`及`reproduce_smoke`会使用真实文本模型，**不在WP1执行范围**；其中reproduce_smoke还会重建索引、启停服务。它们不是一键免费启动/验收命令，需将来另获明确授权后按对应历史报告使用。

## 费用、证据与阶段控制

全站默认3元应用测试预算，现有Provider另沿用phase3增量范围0.5元；不能靠重启或删除账本增额。代码保存的是历史核对价格用于估算，不声称为今天官方实时价格或账户硬扣费上限；未来付费测试必须另行确认，本WP1不调用付费API。

Phase 2归档时62次成功文本请求、保守估算0.13343424元是历史快照，包含探测/调优/比较/浏览器等，不是今天全站累计或官方账单，见[原usage证据](docs/evidence/test-results/phase-02-api-usage.json)。价格核查日期和来源留在原阶段报告，不在WP1重新访问供应商。

Phase 3实际40次供应商请求、39986 tokens，增量保守估算 **0.10777464元**（批准0.5元内）；与Phase 2合计102次、**0.24120888元**。包含失败、调优和一次问答回归，不等于供应商实时余额或实际账单。[本阶段费用](docs/evidence/test-results/phase-03/api-usage-final.json)。

2026-10-23改造前本机账本累计109次历史文本调用，本轮不产生新调用；各阶段差量见原测试报告，不相加伪装实时扣费。普通问答现已增加有界会话上下文；尚无专家知识审校、独立盲测或完整公网部署体系；辅助审校可能漏判，失败保留。企业需求入口与共用Agent流程存在，**没有真实企业客户/订单/收入/企业模型或完整商业交付认证**；企业模型取消而不是生成失败。

Phase 1真实历史、备份与截图保留，见 [阶段报告](docs/reports/phase-01.md)。Phase 2方案、批准Prompt、真实工具过程、参数改动、失败与修复归档在docs；协作导出排除秘密与隐藏推理，不补造对话。历史报告描述的是当时状态，不能当作当前能力证明。

当前Phase 4两模型范围、WP1～3已验收；WP4最终回归与受控恢复已执行，等待验收，详见本文顶部。本地资料/成品、设备和外网限制仍按实际报告保留；比赛交付材料WP5尚未执行。

### 第1次内部真实模型恢复（2026-10-13）

历史过程：原任务`bb074c31-1905-45b6-b763-22d065ddc616`仅一次提交、30积分；下载/纹理门禁失败后恢复原26.6MB GLB，保留原件，本地修MIME及2K纹理后8.42MiB模型技术PASS，随后用户人工验收。原476.8°等是当时浏览器样本，实体手机仍未测；不是本轮重新生成。[完整恢复、Hash及失败报告](docs/reports/phase-04-first-internal-modeling.md)。

本机已有私有资产可打开：`http://127.0.0.1:8000/api/v1/assets/internal-models/3777a880-fc8c-4766-aade-948d20c6b8f0/viewer`。该模型、原图及含图截图不在公开仓库；新克隆环境不会凭README自动下载或生成同一内部模型，也不得将它当作公开/商用角色交付。

恢复当时只用了1次；后来已完成第2次，**当前始终以2/3、剩1为准**。恢复/本地转换CLI可能查询供应商或写资产状态，不是WP1普通测试，本次不执行。旧652项等记录保留在原报告，不称今天最终测试数。

### 第2次写实主展示准备（2026-10-14）

历史过程：红金图独立登记`realistic_showcase_candidate_v1`，冻结`realistic_model_v1.0`，最初一次授权审校后仍待角色/许可/费用确认。随后逐次授权、正式四Agent及人审、真实模型生成和技术/人工验收均已完成；早期WAITING_APPROVAL不是当前状态。文字审校不等于图片冠式、行当或版权认证。

早期58项候选检查不替代成模验收；完整演进见[准备报告](docs/reports/phase-04-realistic-preparation.md)、[当时待审表](docs/reports/phase-04-second-model-approval.md)、[冻结Prompt](docs/prompts/phase-04/realistic-model-v1.md)、[最终实际执行](docs/reports/phase-04-second-model-execution.md)。原报告、Prompt、失败和真实Git不重写。

## 常见运行问题

| 现象 | 检查与处理 |
|---|---|
| localhost/127.0.0.1连接拒绝 | 先确认本服务已startup complete，访问同源8000；检查端口归属，不重复启动、不杀未知进程 |
| 知识未就绪/锁冲突 | 检查active.json指向的generation、BGE缓存和单worker；独立入库/评价前先停止应用，不删除锁强开 |
| API Key/鉴权/网络/预算错误 | 显示真实错误，不用固定回答替代；本轮不做付费探测；历史JSON/已有GLB可以独立查看 |
| 新会话看不到旧Agent任务 | 到Agent历史档案手动读取或按完整ID筛选；这不会恢复实时控制器或重跑任务。配置库缺失/损坏时返回503；只有合法空库或筛选无匹配时显示空结果 |
| Agent/预算/资产数据库不可用 | 停服核对RAG_DATA_DIR及原备份，恢复配套已有库后重启；不要用新安装命令生成替代空库，不自动迁移或重建损坏文件。独立catalog正常时仍可看已有GLB |
| 缺真实资产或某风格无模型 | 核对catalog与本地文件；无授权资产包时明确缺失，不自动生成，合法Duck仅技术夹具 |
| GLB Error | 核对Hash和已登记资源，显式重载原文件；不能重跑Neural4D或关掉验证门禁 |
| 手机访问内部模型失败 | 内部Q版限定loopback，后端也绑定127.0.0.1；实体设备尚未验收，不为测试解除此边界 |

旧`phase4_http_smoke`会按早期未知历史断言并POST拒绝探针，`evaluate_agent_api`会做旧任务变更，`phase4_modeling_preflight/phase4_local_audit`也包含早期状态假设；**不要将它们当当前只读预检运行**。不使用任何建模提交、恢复、余额或历史清零工具来完成WP1。

## 阶段证据索引

[Phase 1](docs/reports/phase-01.md) · [Phase 2](docs/reports/phase-02.md) · [Phase 3](docs/reports/phase-03.md) · [Phase 4最终](docs/reports/phase-04-final-acceptance.md) · [Phase 5检查点A](docs/reports/phase-05-project-audit.md) · [WP1](docs/reports/phase-05-work-package-01.md) · [WP2](docs/reports/phase-05-work-package-02.md) · [WP3](docs/reports/phase-05-work-package-03.md)。

真实协作与Prompt：[Phase 1](docs/prompts/phase-01/README.md)、[Phase 2](docs/prompts/phase-02/README.md)、[Phase 3](docs/prompts/phase-03/README.md)、[Phase 4](docs/prompts/phase-04/README.md)、[Phase 5](docs/prompts/phase-05/README.md)。不把摘要冒充原始对话，不删除失败记录；历史报告中的当时状态须结合日期阅读。
