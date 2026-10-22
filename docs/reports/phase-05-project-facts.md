# Phase 5 WP5 · 项目事实与能力状态表

核对日期：2026-10-22（Asia/Shanghai）。这是当前比赛材料的统一事实底稿。审查起点为本地分支 `feature/phase5-competition-delivery`、HEAD `61064b0842e5f3789c01b107dd0b2a3f45c55adb`，工作区起点干净。WP5仅核对源码、原始证据与文档，不重新运行付费问答、Agent或Neural4D，也不把旧测试当作当天新执行。

## 1. 读法与状态定义

| 状态 | 在本文中的含义 |
|---|---|
| IMPLEMENTED_AND_TESTED | 当前实现有可追溯的实际测试证据；测试日期、层次和范围仍按原文件读取，不代表所有运行环境均验证 |
| IMPLEMENTED_LIMITED | 已实现，但存在功能、资料、外部服务或使用范围限制 |
| HISTORICAL_EVIDENCE | 保存过真实任务/回答/资产；可以核查历史，不代表现在再次执行成功 |
| DEMO_ONLY | 静态说明或明确测试素材，不是当前真实AI产物 |
| NOT_VERIFIED | 尚无足够实际验证证据 |
| NOT_IMPLEMENTED | 尚未实现，不能以页面或接口占位宣称完成 |

证据分类另见[证据索引](phase-05-evidence-index.md)。能力状态与证据分类用途不同：一个历史结果可以具有VERIFIED历史证据，但不因此变成今天已验证的实时外部API。用户接受角色方案不等于专业文化认证，程序的 `publicationAllowed` 也不等于著作权许可。

## 2. 能力、实现位置和可核查证据

本表Git栏列真实实现或归档提交，不声称某一提交包含此功能的全部历史。相关提交均在审查起点历史中保留；完整演进查看 `git log -- <对应路径>`。

| ID | 能力及当前状态 | 当前代码或入口 | 测试/历史证据与Git |
|---|---|---|---|
| F01 | 8页京剧文化网站、AI戏韵工坊：IMPLEMENTED_AND_TESTED | [index.html](../../index.html)、[about.html](../../about.html)、其余history/roles/facial/music/gallery/video页面；[静态白名单](../../backend/app/static_frontend.py) | WP4 [24页视口对](../evidence/test-results/phase-05-wp4/layout-final.json)、数据库修复后[8页及模型](../evidence/test-results/phase-05-wp4-db-repair/normal-model-browser.json)；Phase 1验收基线 `04b2c57`、WP3 `e36c1e5` |
| F02 | 本地中文Embedding、资料入库与混合检索：IMPLEMENTED_AND_TESTED | [Embedding](../../backend/app/knowledge/embedding.py)、[SQLite](../../backend/app/knowledge/store.py)、[Qdrant](../../backend/app/knowledge/vector_store.py)、[SearchService](../../backend/app/services/search.py)、[入库CLI](../../backend/scripts/ingest.py)；POST `/api/v1/knowledge/search` | [真实入库](../evidence/test-results/phase-02-ingest-initial.json)、[生命周期](../evidence/test-results/phase-02-real-lifecycle.json)、WP4 [20题检索](../evidence/test-results/phase-05-wp4/phase-02-retrieval-wp4-isolated-restored-comparison.json)；`a95c774`、`84b1d23` |
| F03 | 京剧RAG实时问答与引用校验：IMPLEMENTED_LIMITED | [chat.py](../../backend/app/services/chat.py)、[LLM Provider](../../backend/app/providers/llm.py)、[前端services](../../js/ai-workshop/services.js)、[main](../../js/ai-workshop/main.js)；`#ai-workshop-qa`、POST `/api/v1/chat` | [历史20题HTTP](../evidence/test-results/phase-02-answers-rag20-final-hybrid.json)、[逐题引用核查](../evidence/test-results/phase-02-answers-rag20-final-hybrid-assistant-review.json)、WP4 [问答前端](../evidence/test-results/phase-05-wp4-db-repair/frontend-phase2_frontend_test.json)；`f7dee30`、`8a5499e` |
| F04 | 历史真实RAG回答：HISTORICAL_EVIDENCE | 仓库中的[真实20题记录](../evidence/test-results/phase-02-answers-rag20-final-hybrid.json)；工坊历史Agent研究证据可另行只读查看，但不是聊天历史系统 | 2026-10-10共20次HTTP成功，18次模型生成、2次无足够证据受控返回；37条引用结构可追溯。不能把此结果称今日连通性或专家正确率；`a95c774` |
| F05 | 四Agent创作工作流：IMPLEMENTED_LIMITED | [Supervisor](../../backend/app/agents/supervisor.py)、[workflow](../../backend/app/agents/workflow.py)、[Planner](../../backend/app/agents/planner.py)、[Researcher](../../backend/app/agents/researcher.py)、[Designer](../../backend/app/agents/designer.py)、[Reviewer](../../backend/app/agents/reviewer.py)、[前端](../../js/ai-workshop/agent-workflow.js)；`#ai-workshop-agents` | [真实案例含失败](../evidence/test-results/phase-03/real-cases-summary.json)、[Phase 3浏览器](../evidence/test-results/phase-03/browser-test-report.md)、[最新完整离线](../evidence/test-results/phase-05-wp4-db-repair/full-final-isolation-result.json)；`381d62e`、`903fe1d`、`81dd451` |
| F06 | 角色JSON、AI文化审校与人工确认：IMPLEMENTED_AND_TESTED | [严格Schema](../../backend/app/agents/schemas.py)、[任务存储](../../backend/app/agents/store.py)、[任务API](../../backend/app/api/agents.py)；确认需服务端状态与sequence，不能仅凭前端声明 | [真实已确认角色](../evidence/test-results/phase-03/browser-confirmed-character.json)、[第二角色审核](phase-04-second-role-v2-review.md)、[WP2实际GET](../evidence/test-results/phase-05-wp2/http-attempt-04.json)；`903fe1d`、`638028e`、`60e1590` |
| F07 | Agent历史档案只读恢复：IMPLEMENTED_AND_TESTED | [HistoryReader](../../backend/app/agents/history.py)、[GET API](../../backend/app/api/agents.py)、[history UI](../../js/ai-workshop/agent-history.js)及[协议](../../js/ai-workshop/history-contracts.js)；`#ai-workshop-history` | WP2 [23项专项已含698全量](../evidence/test-results/phase-05-wp2/pytest.xml)、[真实22任务逐项对照](../evidence/test-results/phase-05-wp2/http-attempt-04.json)、WP4 [历史前端](../evidence/test-results/phase-05-wp4-db-repair/frontend-phase5_wp2_frontend_test.json)；`9e3516d`、`f8a1f47`、`60e1590` |
| F08 | 同一文化角色的Q版/写实风格资产版本：IMPLEMENTED_LIMITED | [Asset Schema](../../backend/app/assets/schemas.py)、[资产服务](../../backend/app/assets/service.py)、[Style Adapter](../../backend/app/assets/visual_prompt.py)、[数字资产UI](../../js/ai-workshop/digital-assets.js)；`#ai-workshop-model` | [资产前端42项](../evidence/test-results/phase-05-wp4-db-repair/frontend-phase4_frontend_test.json)、[风格缺失/恢复浏览器](../evidence/test-results/phase-05-wp4-db-repair/normal-model-browser.json)；`2bb1b69`、`e36c1e5` |
| F09 | 概念图导入、Hash、许可记录与Prompt版本：IMPLEMENTED_LIMITED | [图片校验](../../backend/app/assets/validation.py)、[资产服务](../../backend/app/assets/service.py)、[Prompt模板](../../backend/app/assets/visual_prompt.py)、[冻结英文审核稿](../prompts/phase-04/realistic-model-v1.md) | [Phase 4资产谱系](phase-04-final-acceptance.md)、[真实资产审计](../evidence/phase-04/final-acceptance/asset-ledger-readback.json)；`2bb1b69`、`60bfc38`、`bf96dd6` |
| F10 | 两次真实Neural4D创建及受控恢复：HISTORICAL_EVIDENCE | [Neural4D Service](../../backend/app/assets/neural_service.py)、[Provider](../../backend/app/providers/neural4d.py)、[安全下载器](../../backend/app/providers/safe_model_download.py)；当前创建关闭 | [第一次全过程](phase-04-first-internal-modeling.md)、[第二次全过程](phase-04-second-model-execution.md)、[最终台账](../evidence/phase-04/final-acceptance/asset-ledger-after-free-tests.json)；`c873c31`、`2b08f36`、`60bfc38`、`bf96dd6` |
| F11 | 原子配额、幂等与未知状态保护：IMPLEMENTED_AND_TESTED | [UsageManager](../../backend/app/assets/usage.py)、[创建服务](../../backend/app/assets/neural_service.py)；固定全局SQLite，跨风格共用最大3次创建尝试 | [Phase 4锁与台账](../evidence/phase-04/final-acceptance/asset-ledger-after-free-tests.json)、[最新完整离线JUnit](../evidence/test-results/phase-05-wp4-db-repair/full-final-pytest.xml)；`ee90f14`、`e371019`、`374df8c` |
| F12 | Q版内部技术GLB：HISTORICAL_EVIDENCE | modelId `3777a880-fc8c-4766-aade-948d20c6b8f0`；[内部Viewer](../../backend/app/assets/internal_viewer.py)，loopback只读入口 | [原件与兼容文件Hash](phase-04-final-acceptance.md)、[最新真实GLB浏览器](../evidence/test-results/phase-05-wp4-db-repair/normal-model-browser.json)；`bf96dd6`、`0955d0f` |
| F13 | 写实主展示“绛绣·戏韵”：HISTORICAL_EVIDENCE | assetId `9e2b42e1-bbad-4a2f-ab1b-aeda18015dee`，modelId `1fa0b519-caf4-4009-aec2-f20b0f9a3523`；`about.html?assetId=…#ai-workshop-model` | [正式源任务/角色/图片/模型关联](phase-04-final-acceptance.md)、[第二次技术结果](phase-04-second-model-execution.md)、[WP4模型浏览器](../evidence/test-results/phase-05-wp4-db-repair/normal-model-browser.json)；`e72d237`、`60bfc38`、`bf96dd6` |
| F14 | 真GLB Viewer、旋转/缩放/Reset/三态/恢复：IMPLEMENTED_AND_TESTED | 本地model-viewer；[adapter](../../js/ai-workshop/model-viewer-adapter.js)、[内部UI](../../js/ai-workshop/internal-viewer.js)、[资产API](../../backend/app/api/assets.py) | WP4 [鼠标4组](../evidence/test-results/phase-05-wp4-db-repair/normal-model-browser.json)、[CDP触摸2组](../evidence/test-results/phase-05-wp4-db-repair/touch-browser.json)、[坏Agent库下真GLB](../evidence/test-results/phase-05-wp4-db-repair/field-corrupt-model-browser.json)；`e36c1e5`、`452a0c2`、`0955d0f` |
| F15 | 企业需求模式及共用角色资产机制：IMPLEMENTED_LIMITED | [数字资产UI](../../js/ai-workshop/digital-assets.js)、[Schema](../../backend/app/assets/schemas.py)，工坊个人/企业用途选择 | [WP3导览浏览器](../evidence/test-results/phase-05-wp3/browser-attempt-final.json)、[WP4导览](../evidence/test-results/phase-05-wp4-db-repair/guide-browser.json)；`2bb1b69`、`e36c1e5` |
| F16 | 六步比赛导览：IMPLEMENTED_AND_TESTED | [demo-guide.js](../../js/ai-workshop/demo-guide.js)、[demo CSS](../../css/ai-workshop-demo.css)、`#ai-workshop-demo` | [WP3最终34项](../evidence/test-results/phase-05-wp3/demo-exit-final-34.json)、[WP4导览8组](../evidence/test-results/phase-05-wp4-db-repair/guide-browser.json)；`e36c1e5`、`76dbba0`、`74b3e6e` |
| F17 | 只读备用模式、真实条件GET与失败反馈：IMPLEMENTED_LIMITED | [demo-guide](../../js/ai-workshop/demo-guide.js)、[demo-status](../../js/ai-workshop/demo-status.js)、原问答/历史/资产模块；手动免费检查 | [WP3测试](../evidence/test-results/phase-05-wp3-test-report.md)、[WP4明确故障替身及恢复](../evidence/test-results/phase-05-wp4-db-repair/guide-browser.json)；`e36c1e5`、`76dbba0` |
| F18 | 数据库严格打开、显式首次初始化：IMPLEMENTED_AND_TESTED | [database.py](../../backend/app/database.py)、[初始化CLI](../../backend/scripts/initialize_business_databases.py)、各TaskStore/BudgetLedger/AssetStore/UsageManager | [41专项](../evidence/test-results/phase-05-wp4-db-repair/targeted-final-isolation-result.json)、[CLI9项](../evidence/test-results/phase-05-wp4-db-repair/explicit-init-cli.json)、[现场42观察](../evidence/test-results/phase-05-wp4-db-repair/field-final-summary.json)；`ae2783e`、`452a0c2`、`61064b0` |
| F19 | Agent/预算库故障隔离与受控恢复：IMPLEMENTED_AND_TESTED | [main](../../backend/app/main.py)、[Supervisor](../../backend/app/agents/supervisor.py)、[Runtime](../../backend/app/services/runtime.py)、[Agent API](../../backend/app/api/agents.py) | [损坏503/8页200](../evidence/test-results/phase-05-wp4-db-repair/field-corrupt-probe.json)、[恢复22任务](../evidence/test-results/phase-05-wp4-db-repair/field-restored-probe.json)、[坏库真GLB](../evidence/test-results/phase-05-wp4-db-repair/field-corrupt-model-browser.json)；`452a0c2`、`0955d0f` |
| F20 | 同机隔离依赖安装与私有资源恢复：IMPLEMENTED_LIMITED | [requirements](../../backend/requirements.txt)、[README](../../README.md)、[WP4恢复记录](../evidence/test-results/phase-05-wp4/resource-copy-manifest.json) | [新venv安装](../evidence/test-results/phase-05-wp4/cold-install-attempt03-result.json)、[环境包来源](../evidence/test-results/phase-05-wp4/cold-env-attempt03-runtime-verification.json)、[恢复副本Viewer](../evidence/test-results/phase-05-wp4/models-cold-browser.json)；`834483d`、`3b40aa2` |
| F21 | Duck及静态流程说明：DEMO_ONLY | [合法测试GLB](../../backend/tests/fixtures/phase4/Duck.glb)、[来源](../../backend/tests/fixtures/phase4/Duck-README.md)、[许可](../../backend/tests/fixtures/phase4/SCEA-LICENSE.txt)、导览静态六步说明 | 独立Viewer技术夹具，不是Neural4D输出，不是京剧IP，不算第三模型。静态导览进度不是Agent执行进度；相关Viewer/导览离线测试见F14/F16 |
| F22 | 平台内付费概念图生成：NOT_IMPLEMENTED | [能力协议](../../js/ai-workshop/contracts.js)、[Runtime能力](../../backend/app/services/runtime.py)保留 `conceptImage=false`；真实使用路径为授权图片导入 | [Phase 4最终范围](phase-04-final-acceptance.md)、[当前源码](../../backend/app/services/runtime.py)；没有图像生成商API成功证据 |
| F23 | 今日外部API连通、实体手机、跨机完整恢复、真实ACL、专家Gold及商用交付：NOT_VERIFIED | 现有代码不构成这些验证；不可将本地health、CDP、Mock、有效源ID或企业入口当作相应证明 | [WP4未测边界](../evidence/test-results/phase-05-wp4-test-report.md)、[Phase 2人工审核待完成](../evidence/test-results/phase-02-answers-rag20-final-hybrid-assistant-review.json)、[许可说明](phase-05-asset-provenance-and-permissions.md) |

## 3. 演示动作、依赖和现场适合度

“免费本地”只表示不向模型供应商发请求，不等于无需本地服务、文件或授权。下表按F编号对应上表，不省略使用边界。

| ID | 演示动作与类型 | 外部/私有依赖 | 限制及现场建议 |
|---|---|---|---|
| F01 | 打开首页及任意文化页，再进入工坊；实时本地功能 | HTTP服务、仓库网页及媒体；正常查看无外部AI | 适合；素材公开许可仍需另核对，源码可用不代表所有媒体可再分发 |
| F02 | 可选手动本地knowledge/search或查看已存研究引用；实时本地检索 | 私有BGE缓存、active generation、SQLite与Qdrant；无LLM费用 | 适合已准备本机；当前12资料/35片段，助手核查摘要，非专家Gold |
| F03 | 仅在未来另有付费授权且条件就绪时手动发送；可选实时生成 | DeepSeek网络/Key/费用账本、F02资源 | 本WP5不执行；失败保留输入，不自动付费重试，不能保证当日供应商可用 |
| F04 | 在文档查看保存问题、回答、requestId、真实引用；历史证据 | Git已跟踪的脱敏JSON，不需付费；UI未实现统一聊天历史列表 | 适合说明历史结果；不要把归档JSON叙述为刚生成回答 |
| F05 | 现场优先看F07历史；新任务需另行付费授权 | 正常完整路径为Planner/Designer/Reviewer三次LLM；Researcher真实本地检索；私有Agent库 | 不自动执行；澄清、资料不足、审校失败可能停在中间，不能播放假进度 |
| F06 | 展开同一已保存任务的角色JSON、审校及用户确认；历史查看 | 私有Agent库；新确认是业务写入，本演示不提交 | 适合只读展示；人审是用户接受，不是历史人物/服装考据或版权认证 |
| F07 | 手动读历史、筛选完整任务ID、展开详情与事件/产物 | 本地后端、既有任务库；不需DeepSeek/BGE重新执行 | 适合；缺失字段保留未知，不拼接不同任务；坏库503，合法空库才真实空状态 |
| F08 | 写实切chibi查看明确“未生成”，再切回原写实 | 本地资产catalog与对应文件；切换无供应商调用 | 适合；双风格结构已实现，但现有两个真模型不属于同一角色双风格 |
| F09 | 只读展示图片Hash/版本、冻结Prompt与人审记录；不新导入 | 私有图像/catalog/授权信息；无平台图像生成 | 适合解释谱系；冻结Prompt是审核/版本依据，普通图生3D请求不发送该英文正文 |
| F10 | 展示两次既有任务、费用与恢复过程 | 既有私有台账和脱敏报告 | 只读适合；创建永久按用户当前决定关闭，不能为演示再发第三次 |
| F11 | 展示本地用量GET及已有并发/幂等测试证据 | 固定私有全局账本；本地GET不发供应商请求 | 已用2/3、余1未用；第三取消；未知结果不返还且不自动重建；不在生产探测创建接口 |
| F12 | 内部loopback Viewer查看Q版真实GLB；已保存真实资产 | 私有模型/catalog/本地Viewer；无外网生成 | 仅内部技术查看；非正式角色资产、没有公开许可审计，不能当公开比赛模型默认播放 |
| F13 | 打开带assetId的绛绣工坊；已保存真实资产 | 私有catalog、兼容GLB、原任务关联；无生成费用 | 技术适合主展示；公开范围仍需来源与授权凭证核对，不默认允许上传GLB到公开仓库 |
| F14 | 鼠标拖拽、滚轮/按钮缩放、Reset；需要时显式重读原文件 | 本地model-viewer及真GLB，文件和元数据服务 | 桌面适合；CDP旋转/双指为模拟，非实体手机；Error恢复只重读，不重新建模 |
| F15 | 选择企业用途，阅读机构/受众/用途表单，不提交 | 页面与现有资产/文化流程；没有CRM/订单/客户系统 | 适合说明方向；没有真实企业客户、收入、商业模型或交付认证，不把风格强绑用户类型 |
| F16 | 开始六步、前后跳转/跳过/退出、进入真实对应功能 | 页面原生JS；加载导览不发AI请求 | 适合；静态导览步骤不等于AI完成状态，退出/刷新不锁全站 |
| F17 | 进入只读备用，手动查看历史和已存模型；静态说明明确标识 | 本地后端、私有库/GLB；不需要新LLM，但不是完整离线AI | 适合在外网失败时使用；只保护当前页，不停止已有后台任务，新页/刷新退出，不是全站费用开关 |
| F18 | 只展示CLI及隔离测试结果；不对真实环境初始化 | 私有业务库或受控新安装目录；CLI不建Neural额度账本 | 错路径不建空库；现有库缺损须恢复备份，不能用初始化代替恢复 |
| F19 | 展示坏库→相关503/页面GLB可用→恢复后重启的证据 | 隔离测试副本；真库不做故障注入 | 适合讲述可靠性；catalog也坏则模型不可用；不承诺全部组件无条件降级，恢复后必须重启 |
| F20 | 按指南启动已有准备环境；展示隔离恢复计时和结果 | Python/依赖、授权私有资源副本，首次安装另需下载网络 | 已完成同机隔离副本验证；跨机器完整恢复尚未验证，不保证空白电脑10分钟 |
| F21 | 只在明确技术测试场景展示Duck或静态图示 | Git中的合法测试素材/网页说明；无需外部AI | 标签必须“测试数据/静态说明”；不得冒充京剧数字资产或第三次真实任务 |
| F22 | 显示尚未接入，并说明当前采取导入图片 | 没有已接入图像供应商 | 不演示生成，不展示伪造成功状态 |
| F23 | 在讲稿末说明未测/待核查，不操作未知范围 | 外部账户、实体设备、另一机器、专家或许可材料待补 | 不列为现场已验证能力，不以Mock补成真实结果 |

## 4. 统一数值与统计口径

| 事实 | 核查依据与表述限制 |
|---|---|
| 八个HTML | index/about/history/roles/facial/music/gallery/video。保留多页网站，未迁移React/Vue/Next.js |
| 当前知识内容 | 12资料单元、35片段、BGE-small-zh-v1.5真实512维，Qdrant本地持久化；资料为有来源的原创事实摘要，不是原站全文授权 |
| 18业务表 | Agent4、资产6、全局建模5、预算3；知识库自己的表不纳入这个18表不变性统计 |
| 历史任务 | WP4盘点22任务、88步骤、59产物、194事件；不是22次全流程成功，不推导角色正确率 |
| 本机模型目录 | 4条模型目录记录中2条真实Neural4D成品，另2条测试夹具；不能说已有4个真实生成角色 |
| 全局Neural4D | 两次创建提交尝试均SUCCEEDED、各30积分，累计60；used=2/max=3、remaining=1未用、第三次用户取消且创建关闭 |
| 文本模型历史 | 当前账本107条调用记录。Phase 2/3自己的62次/40次及费用是各自历史窗口，不据此重算当前账单；WP5新增付费调用0 |
| 最新完整后端历史 | WP4数据库修复后754通过、0失败/跳过。其41项数据库安全专项已全部包含；不能写754+41=795个独立用例 |
| CLI与现场恢复 | CLI9个独立脚本检查；现场42个观察断言来自11+10+11+10四场景。可以分层列示，不能与754累加成项目独立用例总数 |
| WP1～4历次全量 | 675、698、698、712及修复后754是不同版本/轮次，具有重叠；不能相加作为项目总测试量 |
| 演示排练 | WP4自动化浏览器正常10步300.071秒，含每步至少30秒停留；不是真人演讲计时或已制作5分钟成片 |
| 旋转指标 | WP4修复后桌面写实325.9°/Q453.7°；CDP触摸写实382.6°/Q300.7°；是具体运行样本，不是模型质量评分 |

## 5. 不能淡化的边界

专业文化审校、人工Gold Recall@5/回答正确率、独立盲测均未完成；引用ID真实只证明结构溯源，不等于语义结论自动正确。角色外观中的原创元素不能冒充传统人物考证。

外部API今日连通性、实体手机、另一台机器完整部署、真实Windows ACL修改、公网多用户安全均未验证。已有同机新venv/隔离资源副本证据不能替代这些项目。

数据库缺损不自动重建，恢复有效库后需重启；配置误指向另一份Schema有效的库仍须人工核对身份。Schema校验是quick_check及所需表/列/对象检查，不是全部业务语义或约束SQL防篡改认证。知识索引需要单进程锁，worker=1，不能通过删锁并发强开。

图片“公开可访问”、用户许可声明、文化审校pass、技术PASS和公共再分发权是不同事项。Q版保留内部非公开边界；写实公开展示及衍生范围按已有声明记录，作者/原始网页/书面凭证仍待核对。原网站媒体与字体等许可另查[素材来源与公开范围](phase-05-asset-provenance-and-permissions.md)。

正式比赛通知、组别、截止、强制格式等尚无独立官方材料；原始用户Prompt中的评分/视频/PDF设想不自动升级为已核实官方规则。见[要求对应表](phase-05-requirements-evidence-map.md)。

使用本表撰写的[项目简介](phase-05-competition-submission-brief.md)、[演示脚本](phase-05-demo-script.md)、[部署恢复指南](phase-05-deployment-and-recovery.md)与[提交检查表](phase-05-submission-checklist.md)，应保留上述状态和边界。WP5最终文档检查结果另记，不把本表的历史证据描述为WP5重新执行的应用测试。
