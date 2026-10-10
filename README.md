# 戏境 AI

在原有「梨园风华」8页京剧文化网站上建设AI戏韵工坊。前端保留HTML/CSS/原生ES Module与酒红、金色、米白视觉；Phase 2新增FastAPI、真实本地中文Embedding、向量检索及服务端DeepSeek问答。Agent执行、概念图、Neural4D继续未接入。

Phase 1已验收，基准提交为 `04b2c571e068ec0b26205fcce0c075395caeebce`。Phase 2工程实现与实测完成，等待用户检查点B验收；详见 [阶段报告](docs/reports/phase-02.md)。[公开仓库](https://github.com/3503799261-blip/xijing_ai)。

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

本次实际使用Windows、Python3.11.1、Node24.15.0。运行网站只需Python后端与现代浏览器；Node用于前端离线检查。已安装FastAPI0.143.0、uvicorn0.54.0、pydantic-settings2.15.0、httpx0.28.1、qdrant-client1.19.1、sentence-transformers6.1.0、numpy2.4.4、pytest9.1.1。

本机 `.venv` 实际使用 `--system-site-packages`，复用已有CPU torch（包元数据2.11.0），避免重复下载大体积依赖。这是本次环境条件；干净机器应使用普通隔离环境。`backend/requirements.txt` 指定CPU torch2.11.0+cpu及CPU wheel来源，冷机安装整套依赖尚未从零计时验证，不将复用环境当成干净锁定环境。

在包含Phase 2代码的交付分支/提交中安装；克隆后应先确认存在backend与knowledge。阶段分支是否已推送以真实Git记录为准，不能假设远端main已经包含当前工作区：

```powershell
git clone --branch feature/phase2-opera-rag https://github.com/3503799261-blip/xijing_ai.git
Set-Location -LiteralPath 'xijing_ai'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

使用本机已有项目时直接进入 `D:\京剧\京剧` 并复用已准备的 `.venv`，不需要重新创建环境。不得为了加速冷机安装无条件复用未知系统包。

## 私有配置

`.env.example` 是无密钥模板；浏览器不会读取它。默认私有env路径是仓库父目录下 `.private-config/.env`；也可通过启动环境 `XIJING_ENV_FILE` 指定仓库外路径。以下是当前本机路径示例，已存在配置不会被覆盖：

```powershell
Set-Location -LiteralPath 'D:\京剧\京剧'
New-Item -ItemType Directory -Force -Path 'D:\京剧\.private-config' | Out-Null
if (-not (Test-Path -LiteralPath 'D:\京剧\.private-config\.env')) {
  Copy-Item -LiteralPath '.env.example' -Destination 'D:\京剧\.private-config\.env'
}
```

用本机编辑器填写 `DEEPSEEK_API_KEY`；不得发到聊天、提交Git或出现在截图/日志。配置改变后重启后端。路径不同的机器应同时调整模板中的RAG_DATA_DIR、EMBEDDING_MODEL_PATH，保持它们在仓库外。

| 字段 | 当前实现 |
|---|---|
| DEEPSEEK_API_KEY | 后端秘密字段，默认空；真实问答需要有权限和余额的有效Key |
| DEEPSEEK_BASE_URL / DEEPSEEK_MODEL | 只允许官方 `https://api.deepseek.com` / `deepseek-flash` |
| DEEPSEEK_THINKING_ENABLED | 必须false；非流式，不保存隐藏思考 |
| DEEPSEEK_MAX_OUTPUT_TOKENS | 默认800且最大800 |
| RAG_TEST_BUDGET_CNY | 默认3且配置上限3；应用预算，不是供应商账单硬限 |
| RAG_DATA_DIR / EMBEDDING_MODEL_PATH | 仓库外SQLite/Qdrant/预算与本地模型目录 |
| ALLOWED_ORIGINS | JSON数组，仅明确的localhost/127.0.0.1及8000/8877端口 |
| RETRIEVAL_MIN_SCORE | 当前0.57；基于候选开发题调参，不是置信概率 |
| RETRIEVAL_MODE | 默认hybrid；可设vector对照，实际策略写入检索结果 |

后端请求总预算默认45秒、供应商默认35秒；浏览器55秒超时，超时不会自动重发模型请求。完整校验依据 `backend/app/config.py`。

## 模型下载、入库与启动

先下载固定snapshot，再入库。这里会下载约95.8MB模型权重及必要配置/tokenizer；CPU PyTorch及其他依赖不包含在这个体积中。

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

免费检查 [health](http://127.0.0.1:8000/api/v1/health)、[capabilities](http://127.0.0.1:8000/api/v1/capabilities)。没有Key仍能完成真实入库与检索；知识未就绪或模型未验证时不会显示问答已就绪。

真实权限已在本地确认、并允许小额调用时，显式运行一次连通检查：

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.check_provider --output docs/evidence/test-results/local-provider-probe.json
```

此命令会调用真实DeepSeek并计入预算，不能当免费健康检查。探测成功仅说明API连通，问答就绪还需要真实索引/Embedding。服务能力端点自身不发起付费探测。

## 接口与问答使用

| 方法/接口 | 行为 |
|---|---|
| GET /api/v1/health | 索引、Embedding、LLM配置/验证及非秘密预算摘要 |
| GET /api/v1/capabilities | questionAnswering/knowledgeSearch真实就绪状态；Agent/概念图/3D仍false |
| POST /api/v1/knowledge/search | question、可选topK/category；真实片段/来源/分数，无LLM调用 |
| POST /api/v1/chat | question、可选conversationId；answer/citations/uncertain/requestId |
| GET /api/v1/knowledge/sources | 允许公开的来源与许可元数据 |

问题上限600个UTF-16字符单位；检索模型问题加指令最多512 tokens，超限明确提示。每次提问独立检索，conversationId不代表已经实现对话记忆。推荐问题自动填入，发送后等待真实回答；引用可在对应回合展开，也可切换到资料区。最多保留12个完整页面内回合，刷新清空。模型正文和资料均按安全文本渲染。

缺Key、未入库、鉴权/余额/网络/超时、无效引用均有明确错误或资料不足状态。不返回供应商原始错误、堆栈或假AI答案。加载时禁止重复发送；手动重试沿用同一幂等标识，无自动付费重试。

## 测试与十分钟复现边界

已有依赖、模型缓存、真实权限的机器可依次入库、启动、检查状态并完成核心问答。最终版本完整重建索引、启动新后端、HTTP打开前端及一次真实RAG实测 **25.6704秒**，见 [缓存复现](docs/evidence/test-results/phase-02-cached-reproduction-final-hybrid.json)。**首次空环境需要依赖和模型下载，尚未测得整体十分钟安装结果**；缓存条件不能作为冷机复现承诺。固定模型首次实际下载12.691秒，但该值同样依赖本次网络与已有CPU依赖。

已有真实证据：初次12文档/35片段的512维向量入库约30.5013秒；隔离副本中的真实CPU首次/幂等/更新/重建/重开/写锁/失败保旧生命周期检查约16.6563秒；单次32-token上限的真实Provider探测成功。[初次入库](docs/evidence/test-results/phase-02-ingest-initial.json)、[真实生命周期](docs/evidence/test-results/phase-02-real-lifecycle.json)、[探测结果](docs/evidence/test-results/phase-02-provider-probe-success.json)。

免费离线与检索检查可重跑：

```powershell
.\.venv\Scripts\python.exe -m pytest -q backend/tests
node scripts/phase2_frontend_test.mjs --output docs/evidence/test-results/local-frontend-unit.json
# 独立评估会占用本地索引，先停止应用；默认标签使用真实时间，避免覆盖旧结果。
.\.venv\Scripts\python.exe -m backend.scripts.evaluate_retrieval
```

后端 **124项通过**、前端 **25项离线检查通过**，均明确标注fake/mock边界，不作为真实Embedding/LLM证明。实际模型、入库、检索和浏览器证据独立保存；初始失败保留。[前端离线](docs/evidence/test-results/phase-02-frontend-unit.json)、[后端最终回归](docs/evidence/test-results/phase-02-final-unit-regression.json)。

20题全部执行真实本地Embedding/向量与混合对比。最终混合候选证据覆盖为18支持题全部命中；题目由助手核对，**不是人工gold Recall@5**。同批题被用于调参；5题留出也已用于诊断，不宣传为独立盲测。错误人物仍可能命中相似材料，真实LLM应说明限制。[最终检索](docs/evidence/test-results/phase-02-retrieval-final-entity-metadata-same20-comparison.json)。

最终20题真实HTTP联测全部成功，其中18次实际DeepSeek生成、2题证据不足直接受控返回；平均HTTP耗时1.103882秒，37个引用均能映射真实片段。助手逐题核查为18个支持回答、2个资料不足，专业人工审核/人工正确率仍待完成。另5题补充联测全部成功，其中错误人物前提被明确拒答。仅 **5对**执行真实“直接DeepSeek vs RAG”对照，不能称20题完整对照。[真实20题](docs/evidence/test-results/phase-02-answers-rag20-final-hybrid.json)、[引用核查](docs/evidence/test-results/phase-02-answers-rag20-final-hybrid-assistant-review.json)、[五题对照](docs/evidence/test-results/phase-02-direct-vs-rag-five.json)。

8页浏览器/资源回归、1920×1080桌面、390×844手机及768×1024工坊Agent视口实际完成；四推荐问题、展开引用、连续提问、空输入、停机恢复、安全文字与未接入模块均已实际操作。7个文化HTML逐字节保持Phase 1版本。见 [浏览器实测报告](docs/evidence/test-results/phase-02-browser-test-report.md)。

需要额外付费联测时显式执行以下命令，会使用私有配置并计入应用预算；默认不自动重试，每次新标签保留旧结果：

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.evaluate_answers --base-url http://127.0.0.1:8000 --label my-review
# 此项重建并临时启动/关闭自己的服务进程，运行前手动停掉现有应用；需要已缓存依赖、模型及已成功的provider探测。
.\.venv\Scripts\python.exe -m backend.scripts.reproduce_smoke --label my-cached-review
```

## 费用、证据与阶段控制

本阶段默认3元**应用测试预算**。预算账本根据代码记录的峰价（输入未命中2元、命中0.04元、输出8元/百万tokens）预留上界；有usage时计算保守估算，超时/网络结果未知保留预留额。这不是官方账户硬限，也不包含其他程序使用同Key的费用；实际账单以供应商为准。追加预算须用户另行批准，勿删除账本绕过预算。

截至阶段归档，实际账本62次成功供应商请求，累计保守估算 **0.13343424元**，详见 [Token与费用证据](docs/evidence/test-results/phase-02-api-usage.json)。该数字包含连通探测、早期/修复后测试、5次直接问答、浏览器问答和两次缓存复现，不是仅最终20题的费用；不会读取或宣称账户实时余额。价格依据 [DeepSeek官方价目](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)。

目前无跨问题语义记忆、专业人工知识审校、独立盲测及公开互联网后端访问控制/限流；本地单worker运行是已验证交付范围。Agent、图像和Neural4D继续待接入。

Phase 1真实历史、备份与截图保留，见 [阶段报告](docs/reports/phase-01.md)。Phase 2方案、批准Prompt、真实工具过程、参数改动、失败与修复归档在docs；协作导出排除秘密与隐藏推理，不补造对话。历史报告描述的是当时状态，不能当作当前能力证明。

当前只开发Phase 2。完成真实测试与总结后停止，只有用户明确回复 **“Phase 2验收通过，进入Phase 3。”** 才进入多Agent引擎开发。
