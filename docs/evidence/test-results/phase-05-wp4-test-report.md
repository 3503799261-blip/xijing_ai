# Phase 5 WP4实际测试报告

执行：2026-10-20～21（Asia/Shanghai）。状态：**PHASE_5_WP4_WAITING_ACCEPTANCE**。10月20日完成安装、资源副本、离线/浏览器回归与自动化排练；10月21日续接，补正常退出/重启及最后不变性核对。旧结果没有冒充续接后的重新执行。

**数据库安全追加复验：2026-10-21～22，最新结论PHASE_5_WP4_WAITING_ACCEPTANCE。** 第1～9节保留此前结果和原两项FAIL；第10节记录本次经单独授权的修复、失败和真实复测，不将旧712项或旧安装/排练冒充本轮重新执行。

## 1. 环境、边界与结果分类

Windows/Python3.11.1；原venv复用system-site-packages，另建**普通隔离venv**，没有改原环境/依赖版本。Node24.19.0；10月20日Chrome155.0.8059.85，21日重启后155.0.8059.86。已有Playwright、SwiftShader。桌面1920×1080、平板768×1024、手机模拟390×844；实体手机NOT_TESTED。

后端收集前隔离：空Key、临时业务库及全局额度账本、禁止真实HTTP Transport、保护生产文件/SQLite；不是裸跑pytest。资源探针使用真实本地BGE与公开语料、临时SQLite/Qdrant、明确合成历史及合法Duck，网络被拒绝。浏览器只允许本机GET/HEAD；问答POST替身在浏览器直接响应，不转发服务器。真正的业务POST仅本地knowledge/search及输入校验，没有LLM调用。

PASS=本次实际执行通过；FAIL=实际失败；BLOCKED=权限/环境等阻断；NOT_TESTED=本次未做；NOT_APPLICABLE=明确不适用。不同层次存在重叠，**不把各行数量相加宣传端到端总数**。

## 2. 实际结果

| 执行层 | 本次结果 | 时间/范围 | 证据 |
|---|---|---|---|
| 原代码后端基线 | PASS：698/0失败/0跳过 | 69.19秒，原venv | [基线](phase-05-wp4/backend-baseline.json) |
| 修复后完整后端 | PASS：712/0/0 | 100.82秒；新增14项，不删除原698项 | [隔离结果](phase-05-wp4/backend-final.json)、[JUnit](phase-05-wp4/backend-final.xml) |
| 新venv完整后端 | PASS：712/0/0 | 74.60秒；隔离工作副本、同一最终修复 | [结果](phase-05-wp4/backend-clean-env.json)、[JUnit](phase-05-wp4/backend-clean-env.xml) |
| 问答/Agent/历史/资产/导览前端 | PASS：25/25/34/42/34项，各0失败 | DOM/Fetch替身，不是浏览器/真实AI | [执行清单](phase-05-wp4/frontend-execution-summary.json) |
| 新增资源回归 | 原版本3通过9失败；补充Qdrant前12通过2失败；最终14通过0失败 | 真实临时存储+明确合成encoder；包含在最终712内 | [原红灯](phase-05-wp4/resource-red.json)、[补充红灯](phase-05-wp4/resource-qdrant-red.json)、[最终](phase-05-wp4/resource-final.json) |
| 真实BGE与资源故障探针 | 15个观察断言PASS，0失败/跳过 | 12文档/35片段/512维；入库15.3489秒；含下述已确认缺口，不能称15种恢复均成功 | [最终探针](phase-05-wp4/resource-probe-final.json) |
| 本地检索20题×vector/hybrid | PASS：两组均20完成/0异常 | 18支持/2不足；不是新LLM问答 | [比较](phase-05-wp4/phase-02-retrieval-wp4-isolated-restored-comparison.json) |
| 本地HTTP | 最终14检查PASS，0失败 | 同一组在正常环境、恢复副本、21日重启前后分别执行；不相加成独立用例 | [恢复副本](phase-05-wp4/http-isolated-restored.json)、[重启前](phase-05-wp4/http-normal-start-04.json)、[重启后](phase-05-wp4/http-normal-restart-05.json) |
| 导览/异常Chrome | PASS：8组/0失败 | 真实历史/条件GET；7种聊天响应是明确替身 | [结果](phase-05-wp4/guide-browser.json) |
| 8页×3视口 | PASS：24/0失败/0跳过 | 逐页内容、导航、CSS/JS、图片、媒体、布局、控制台 | [最终矩阵](phase-05-wp4/layout-final.json) |
| 两真实GLB及双风格 | PASS：4组 | 鼠标写实325.9°、内部Q453.7°；缩放/Reset、缺失风格和恢复 | [20日](phase-05-wp4/models-browser.json) |
| 两模型CDP触摸/故障 | PASS：2组/0失败/跳过 | 写实382.7°、Q300.7°；双指/滚轮/按钮/Reset、Loading→Ready→Error→Ready | [触摸](phase-05-wp4/touch-final.json) |
| 新venv恢复副本Viewer | PASS：4组 | 8011端口；8页及两原GLB；未调用供应商 | [冷环境](phase-05-wp4/models-cold-browser.json) |
| 21日正常重启后Viewer | PASS：4组 | Chrome .86；原模型/风格恢复，创建disabled | [最终重启](phase-05-wp4/models-restart-browser.json) |
| 自动化流程排练 | PASS：10正常步骤+4故障步骤 | 正常300.071秒，故障40.038秒；含每步30秒阅读停留，非真人讲解/成片 | [逐步计时](phase-05-wp4/rehearsal.json) |
| 数据及资产不变性 | PASS | 18完整业务表、22任务ID、四原件/兼容文件、8个HTML、BGE/知识/向量文件Hash一致 | [完整表](phase-05-wp4/after-state.json)、[原件](phase-05-wp4/after-provenance.json)、[知识](phase-05-wp4/knowledge-after.json) |

后端两次最终全量各1条现有Starlette/httpx弃用警告，未为消警告改依赖。所有数量来自本次JSON/JUnit，而非复制WP1～3旧数量。

## 3. 正常启动与真正关闭/重启

仓库起点74b3e6e，8000实际由上轮已知Uvicorn持有。原先Get-NetTCPConnection/CIM的沙箱读取不充分；改用端口与已核实命令/PID确认，没有杀未知进程。确认无活动Agent后，以普通Ctrl+C关闭，日志完整shutdown。先保存基线，再复制资源。

文档真实命令始终是：

~~~powershell
Set-Location -LiteralPath 'D:\京剧\京剧'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1
~~~

测试辅助只负责隐藏独立控制台、计时、同一命令和免费HTTP；使用进程级外域连接守卫，不改私有env。启动不是纯只读：原实现会初始化业务库及恢复中断状态，最终以全表Hash证实没有业务变化。

| 记录 | 实际结论 |
|---|---|
| [initial-stop](phase-05-wp4/initial-stop.json) | PASS：原WP3服务正常shutdown、端口释放 |
| [normal-start-01](phase-05-wp4/normal-start-01.json) | PASS：14.131秒HTTP就绪，知识12/35 |
| [normal-stop-01](phase-05-wp4/normal-stop-01.json) | **FAIL**：控制事件已发送但端口未释放，不能把其后的http-after-restart当真正重启证据；没有强杀/删锁 |
| [normal-start-03](phase-05-wp4/normal-start-03.json) | **BLOCKED**：续接后的受限环境无法完成HTTP，WinError10013；不是模型/生产数据丢失 |
| [normal-start-04](phase-05-wp4/normal-start-04.json) | PASS：权限范围内本地运行，31.201秒就绪 |
| [normal-stop-04](phase-05-wp4/normal-stop-04.json) | PASS：正常Ctrl+C，日志shutdown complete，目标进程退出、端口释放 |
| [normal-start-05](phase-05-wp4/normal-start-05.json) | PASS：25.654秒重新启动，14项HTTP、8页/两个GLB及风格恢复通过 |
| [normal-stop-05](phase-05-wp4/normal-stop-05.json) | PASS：正常退出后读取受独占锁保护的Qdrant完整文件Hash，未强读或删除锁 |

测试启动器补显式启用控制台Ctrl+C，避免继承编排壳的忽略状态；仅改仓库外辅助，不改产品信号逻辑。初次完整Hash读取在服务持锁时被拒绝，随即按正常方式停服再核对，结果完全一致。**本包结束时服务已正常停止**，不留下测试外域拦截进程当普通运行服务。

## 4. 干净依赖安装与恢复

[安装记录](phase-05-wp4/cold-install-attempt03-result.json)保留原命令、退出码和时间；[环境导入](phase-05-wp4/cold-env-attempt03-runtime-verification.json)保留实际包位置。独立目录为仓库外.runtime/phase5-wp4/cold-env-attempt03；普通venv、include-system-site-packages=false，66个distribution，11个顶层固定依赖全部来自新venv，pip check通过。

~~~powershell
python -m venv <全新隔离环境>
<隔离环境>\Scripts\python.exe -m pip install --retries 0 --timeout 20 --index-url https://pypi.org/simple -r backend/requirements.txt
~~~

实际普通venv创建10.520秒，依赖安装348.549秒，pip check1.366秒，核心导入23.364秒。CPU torch114.4MB；原requirements及CPU源未改。前两次ensurepip扫描Python安装目录遇WinError5，改TEMP仍失败；第三次在允许读取安装目录的执行权限下通过，失败日志均保留。[安装失败](phase-05-wp4/cold-install-attempt02-result.json)、[原ensurepip诊断](phase-05-wp4/cold-install-attempt01-ensurepip-diagnostic.redacted.txt)。

这不是空白电脑完整安装计时：已有Python、网络和本地BGE/授权成品；没有执行首次BGE下载，也没有证明跨机器复制。requirements固定11个直接包，**没有全量传递依赖锁文件**，本次66包清单记录实际解析版本，不能承诺未来解析相同。

恢复顺序真实执行于独立父目录recovery-workspace：

1. git archive起点源码，加入本包同一已测试runtime修复和14项测试；与业务运行目录隔开，避免全局额度路径仍落到生产父目录。
2. 源服务停止时读取实际已有资源，SQLite以只读源backup到新目标并integrity_check；其他资源复制并Hash核对，跳过锁/WAL/SHM。这是**本轮真实建立的本地受控备份副本**，不是宣称早已存在的分发包。
3. 复制固定revision BGE、active.json对应generation/SQLite/Qdrant、Agent/预算/资产catalog、图片、两个兼容GLB及两供应商原件；完整清单[resource-copy-manifest](phase-05-wp4/resource-copy-manifest.json)。没有复制真实Key，用.env.example空Key，真实创建关闭。
4. 全局账本也复制真实2次历史，绝非新初始化零额度；隔离目录只作测试，不能成为新的实际建模额度池。
5. 用新venv同一Uvicorn命令、临时8011端口启动，17.595秒HTTP就绪；知识12/35、14项本地HTTP及两模型浏览器通过。空Key下LLM不可用是正确状态。
6. [restored-after-state](phase-05-wp4/restored-after-state.json)与原始before的18表/历史/资产/台账完整逻辑Hash相同。新venv712项全部通过。

Git本身不含这些私有资源，也没有一键私有资产分发系统。只有knowledge语料可以重建知识索引，**不能重建旧任务、人审、预算和两成品关联**。需要另一机器完整演示时必须另行受控交付，不公开整库或内部Q模型。

## 5. 私有资源故障与必要修复

探针全部在新目录注入/恢复；没有删除、重命名或迁移生产资源。原始[资源故障](phase-05-wp4/resource-probe-original.json)和[初次辅助失败](phase-05-wp4/resource-probe-initial.json)独立保留。

| 场景 | 当前结果分类与实际行为 |
|---|---|
| 缺BGE目录 | PASS：503 EMBEDDING_MODEL_MISSING；其余8页/合成历史可读；重配已有固定模型后检索恢复 |
| 已有模型损坏/加载失败 | PASS：新增隔离测试给出EMBEDDING_LOAD_FAILED；不冒称外部下载或真实推理故障已自动修复 |
| 缺知识SQLite | PASS：503 KNOWLEDGE_DATABASE_MISSING，不再创建空文件；恢复确切副本后真实搜索200 |
| 缺Qdrant目录、meta、集合声明或storage.sqlite | PASS：503 VECTOR_INDEX_MISSING，不再自动创建空目录/集合；恢复后真实搜索200 |
| GLB缺失 | PASS：合法Duck临时副本HTTP404 ASSET_FILE_UNAVAILABLE→原Hash文件恢复200；两真实模型的浏览器响应故障另行验证，不声称删除过真实模型 |
| 只读历史DB缺失/损坏 | PASS：缺失为空/详情404且不创建文件；损坏503 AGENT_HISTORY_UNAVAILABLE，无路径泄漏 |
| **可写Agent业务DB损坏** | **FAIL（整站降级体验）**：app factory在监听前抛DatabaseError，当前仍阻断启动；探针中的PASS仅表示成功观察到该已知缺口 |
| **误配到可写的新RAG目录** | **FAIL（防误配恢复保障）**：会初始化空任务/预算/资产库，历史显示真实空；不是恢复成功，没有改成假历史；仍需人工核对路径和受控备份 |

最小产品修复只涉及Runtime加载前检查及安全中文诊断、14项回归；不改资料入库的创建语义、检索算法、Agent提示词、资产结构或数据迁移。Qdrant检查针对固定1.19.1本地布局，未来升级需复测；预检查不承诺抵抗外部恶意并发删文件，仍依赖owner锁及受控恢复。

## 6. 端到端与排练

实际HTTP14项覆盖健康/能力/12来源、真实CPU检索、空/超长校验、历史分页和completed筛选、绛绣详情/不存在ID、额度及禁止静态公开backend/env。没有POST聊天或Agent。

真实本地20题×两检索模式，纯向量全部候选片段覆盖17/18支持题，混合18/18；候选片段宏平均覆盖98.61%/100%，两资料不足题均uncertain。实际来源/片段一致性46/46、63/63。标注由助手核对，**不是人工Gold Recall@5、独立盲测、回答正确率或新LLM联测**。

导览8组复用已验收真实页面和WP2只读历史；显著区分历史结果、静态说明、测试替身。成功、超时、断网、401/429/503、异常数据均为浏览器明确注入，输入保留、无自动重复/重跑。真实GLB恢复只重读原文件。企业仍是需求入口，无客户、订单或企业成品。

[排练记录](phase-05-wp4/rehearsal.json)逐步保存实际页面、操作、预期/实际、耗时、外部依赖及备用：首页→导览→RAG界面/范围→同一绛绣历史→角色/审校/人审→内部Q→写实→旋转缩放Reset→企业边界→额度关闭。10步共300.071秒，**自动化浏览器、每步最低30秒阅读停留**，不是声称真人已完成5分钟演讲。故障4步40.038秒：模拟健康503→历史→已有GLB→手动恢复真实本地条件。外网LLM从未测试或自动触发。

## 7. 失败、辅助问题与复测保留

- ensurepip两次WinError5受阻，第三次权限正确后成功；无升级/降级依赖。
- 资源探针最初过严socket审计阻断Windows asyncio本地self-pipe，保留初次失败；仅允许本地控制socket，仍拒绝真实外部HTTP。最终15个观察断言通过。
- 新增资源回归原版3/9、补充Qdrant12/2，修复后14/0；完整710中间版本及最终712均独立保留。
- 24页矩阵首轮误点桌面隐藏导航；其后15/9因媒体ERR_ABORTED，HEAD验证405也保留。最终逐元素readyState/error/duration及真实GET Range206（仅读1字节）核实资源；仅把已有metadata且无media.error的取消分类为浏览器预加载行为，最终24/0。[第二轮](phase-05-wp4/layout-failed-02.json)、[第三轮](phase-05-wp4/layout-failed-03.json)、[最终](phase-05-wp4/layout-final.json)。
- 触摸辅助初版点了Ready状态本来隐藏的reload按钮；改为同URL重载触发文件故障，Error时点击可见的恢复，2/0。[原失败](phase-05-wp4/touch-initial.json)。
- 本地HTTP辅助两次误用used字段及一次shell修正未解析；改为真实used_attempts/remaining_attempts后14/0，不改业务接口。[记录](phase-05-wp4/http-helper-initial-failure.json)。
- normal-stop-01没有退出、续接normal-start-03权限阻断均不算PASS；最终正常退出04/05及重启05已补证。一次重复输出目录被辅助拒绝，改用全新目录，未覆盖旧证据。

## 8. 保护、证据与未测范围

18张业务表schema/完整行规范化稳定排序Hash全部不变：22任务、88步骤、59产物、194事件；人审/角色/资产关联不变。LLM107条，Neural4D18操作、60历史积分，2 SUCCEEDED、0待消费批准、0未知/在途，**已用2/3、余1未使用、第三取消、创建关闭**。BGE、active generation全部文件逐字节Hash不变，8个HTML也不变。

| 文件 | 字节 | SHA-256 |
|---|---:|---|
| Q版兼容GLB | 8827324 | bf9c808c15dbf5464ee67df1cdb3f64f9b2c6b3cd4ee41ecb8a6470a0554654a |
| 写实兼容GLB | 15158668 | 5a021ac6338009615e6ea232c5b9001eef6f4cc91d9d87c3eeeb5307526bdfd5 |
| Q版供应商原件 | 26600184 | 8ef5de8a2f96fbbee9eea66737187e4a2087f88867830891a41464a473d47885 |
| 写实供应商原件 | 18266484 | 51fc687e0bde5fdb9074ba4560601057e17e9239f111fd2bc9e0d6601c26260e |

两GLB内嵌纹理，无外部贴图依赖；没有转换/覆盖。Q版仍内部非公开、无正式角色关联；写实沿原角色ca7007e7…任务、资产9e2b42e1…、模型1fa0b519…关联。两模型不是同一角色的两种风格。

[归档清单](phase-05-wp4/archive-manifest.json)区分源Hash/脱敏Hash；110份文字证据，不含私有模型/图片/DB/Key。110张实际截图仅在私有.runtime，以[Hash清单](phase-05-wp4/screenshot-manifest.json)追溯；含失败截图，不说全部画面均成功。主代理实际查看了手机工坊与重启后写实Ready截图。

归档/链接/模式/祖先/不变性核对另见[文档检查](phase-05-wp4/documentation-checks.json)，初次1015检查通过，不能计作应用测试。产品/文档diff检查通过；保留原pytest失败输出的E空行尾随空格、执行过bootstrap的原EOF空行，因此证据diff仍有对应格式提示，不通过改写原失败证据消警告。公开归档已脱敏，模式扫描不等于对任何未知秘密的绝对保证。

**本轮付费API0、真实外部AI0、Neural4D任何请求/新建0。** 依赖下载仅官方PyPI/CPU源，不是模型服务API。环境变量只检查存在性/关闭布尔，不输出值。

NOT_TESTED：实体手机、真实外部API连通/余额、真人讲解与成片、另一台机器/无缓存BGE首次下载、公网/多用户。NOT_APPLICABLE：第三次建模（用户取消，不是失败）、新付费问答或重跑Agent（本包禁止）。损坏业务DB及错误可写目录的FAIL保留，不以15个探针观察PASS覆盖。结论是已完成本包验证及最小修复，等待用户带上述限制验收；不进入WP5。

## 9. 本次实际命令与执行辅助

下列为已执行的命令，不是要求在生产目录再次运行恢复/重建。辅助及其源/归档Hash见archive-manifest；绝对路径描述本次真实环境，复跑必须选全新输出目录，不覆盖旧结果。源码zip、venv、DB和模型仍仅位于私有.runtime，不进Git。

~~~powershell
# 新增修复后的原venv全量：收集前隔离，不能裸跑pytest。
Set-Location -LiteralPath 'D:\京剧\京剧'
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp4-offline-bootstrap.py --run-root D:\京剧\.runtime\phase5-wp4-offline-final-20261020-01 --junitxml D:\京剧\.runtime\phase5-wp4-offline-final-20261020-01\pytest.xml --basetemp D:\京剧\.runtime\phase5-wp4-offline-final-20261020-01\pytest-temp

node scripts/phase2_frontend_test.mjs --output D:\京剧\.runtime\phase5-wp4-frontend-20261020-01\qa.json
node scripts/phase3_frontend_test.mjs --output D:\京剧\.runtime\phase5-wp4-frontend-20261020-01\agents.json
node scripts/phase5_wp2_frontend_test.mjs --output D:\京剧\.runtime\phase5-wp4-frontend-20261020-01\history.json
node scripts/phase4_frontend_test.mjs --output D:\京剧\.runtime\phase5-wp4-frontend-20261020-01\assets.json
node scripts/phase5_wp3_frontend_test.mjs --output D:\京剧\.runtime\phase5-wp4-frontend-20261020-01\demo.json

# 同机隔离工作副本、已有BGE和索引副本，真实免费检索；未调用LLM。
Set-Location -LiteralPath 'D:\京剧\.runtime\phase5-wp4\recovery-workspace\source'
D:\京剧\京剧\.venv\Scripts\python.exe -m backend.scripts.evaluate_retrieval --output-dir D:\京剧\.runtime\phase5-wp4\retrieval-evaluation --run-label wp4-isolated-restored

# 新venv同一套完整后端集合，收集前隔离于副本父目录。
D:\京剧\.runtime\phase5-wp4\cold-env-attempt03\Scripts\python.exe D:\京剧\.runtime\phase5-wp4-offline-bootstrap.py --run-root D:\京剧\.runtime\phase5-wp4\recovery-workspace\.runtime\phase5-wp4-offline-clean-01 --junitxml D:\京剧\.runtime\phase5-wp4\recovery-workspace\.runtime\phase5-wp4-offline-clean-01\pytest.xml --basetemp D:\京剧\.runtime\phase5-wp4\recovery-workspace\.runtime\phase5-wp4-offline-clean-01\pytest-temp
~~~

浏览器使用本机已有Node/Playwright（包定位变量XIJING_PLAYWRIGHT_PACKAGE，不安装依赖）。实际辅助执行：

~~~powershell
node D:\京剧\.runtime\phase5-wp4-browser.mjs D:\京剧\.runtime\phase5-wp4-browser-01
node D:\京剧\.runtime\phase5-wp4-layout-matrix.mjs D:\京剧\.runtime\phase5-wp4-layout-matrix-04
node D:\京剧\.runtime\phase5-wp4-touch-browser.mjs D:\京剧\.runtime\phase5-wp4-touch-browser-02
node D:\京剧\.runtime\phase5-wp4-cold-model-browser.mjs
node D:\京剧\.runtime\phase5-wp4-rehearsal.mjs D:\京剧\.runtime\phase5-wp4-rehearsal-01
# 21日最后一次重启后的浏览器实测
node D:\京剧\.runtime\phase5-wp4-model-browser.mjs D:\京剧\.runtime\phase5-wp4-restart-model-browser-01
~~~

测试启动、退出、HTTP、资源恢复/故障探针和完整Hash辅助的实际输入/输出另保存在对应JSON及源码：

- [原venv最终启动](phase-05-wp4/normal-start-05.json)：完整Uvicorn命令、cwd、PID、免费HTTP、计时。
- [干净安装](phase-05-wp4/cold-install-attempt03-result.json)：venv、pip install/check/list各完整命令及退出码。
- [冷环境启动](phase-05-wp4/cold-start-01.json)：新Python、独立源码及8011；对外云API未验证。
- [资源复制辅助](phase-05-wp4/phase5-wp4-prepare.py)、[最终资源探针](phase-05-wp4/resource-probe-final-helper.py)、[状态快照](phase-05-wp4/phase5-wp4-state.py)：只在指定受控新目录运行，不是新的资产分发或迁移功能。
- [HTTP辅助](phase-05-wp4/phase5-wp4-http-check.py)：仅允许POST本地检索；其余GET，不提供付费调用入口。
- [启动辅助](phase-05-wp4/phase5-wp4-server-control.py)、[退出辅助](phase-05-wp4/phase5-wp4-stop-console.py)：测试级网络守卫与正常控制台退出；不用于替代README普通终端启动。

## 10. 数据库安全修复与最终复验（2026-10-21～22）

### 10.1 环境、隔离和修复前执行路径

仓库D:\京剧\京剧，起点3b40aa27b3b642e3a695c60ad149678a87487ae0，分支feature/phase5-competition-delivery，实际工作区干净。Windows/Python3.11.1、原venv、Node24.19.0、Chrome155.0.8059.86、已有Playwright；本轮没有安装/升级依赖。21日执行源码复现、产品修改、后端/前端/浏览器与正常启动，22日完成隔离副本恢复/误配/恢复配置、最终不变性及归档。

生产SQLite均以mode=ro/query_only建立基线；冻结原提交源码到私有.runtime副本再运行A～D，不将后来的工作树修改误算为修复前代码。所有损坏、删除、缺表、路径误配、初始化和写入均在新建临时目录或停服核对后的独立副本；没有对生产执行迁移、初始化、清空、损坏或重建。

原问题A调用链：create_app→Runtime→DeepSeekProvider→BudgetLedger，以及Supervisor→TaskStore、AssetService→AssetStore。构造阶段普通sqlite3.connect遇缺失自动建文件，随后executescript建表。配置是直接使用RAG_DATA_DIR，没有悄悄回退；错误但可写目录被当作新安装。

原问题B调用链：create_app→Supervisor.__init__→TaskStore.__init__→executescript；坏库抛DatabaseError终止工厂，静态路由未注册。不是Neural4D或前端Viewer错误。

| 原版隔离场景 | 实际观察 | 安全含义 |
|---|---|---|
| A：不存在的错误RAG根目录 | 创建Agent40960B、预算32768B、catalog81920B；历史200/0条 | 原缺陷复现 |
| B：原有临时Agent库缺失 | 重新建空Agent库；原任务未恢复、历史0条 | 原缺陷复现 |
| C：独立坏Agent文件 | DatabaseError中断create_app；原坏字节未覆盖但无法服务静态页 | 原缺陷复现 |
| D：有效隔离数据库 | 1条明确合成历史可读，8页及合法Duck真实GLB200/Hash相符 | 正常对照 |

[最终修复前结果](phase-05-wp4-db-repair/baseline-final.json)4/0/0表示观察成功，**不是四项安全能力通过**；[执行索引](phase-05-wp4-db-repair/baseline-execution-index.json)保存原源码Hash、命令、初次环境失败和实际时间。真实京剧成品不用于破坏性测试。

### 10.2 修复机制与专项覆盖

普通连接先查文件/只读完整性和所需Schema，再以URI mode=rw/ro打开；第二次连接时文件消失仍不会创建。普通启动不建表、不补Schema、不迁移、不覆盖。独占新文件的显式初始化先预检全部已有业务库，任何旧坏库/缺表拒绝，只有明确首次安装才建3业务库；canonical全局Neural4D账本保持独立且不创建。

Supervisor保存安全故障诊断，坏库不启动worker、不持owner锁、不重跑Agent；相关历史/状态/结果/创建/确认/取消先校验并503。应用保留静态路由；独立catalog和文件有效时仍提供已有模型。预算不可用时问答/协作能力关闭且生成在HTTP前失败。健康分别反映应用、Agent库和预算库；不能把应用可用说成AI服务已恢复。

[41项专项](phase-05-wp4-db-repair/targeted-final-isolation-result.json)，5.48秒、0失败/0跳过；完整754包含同41项，不重复相加：

| 验证项 | 实际方式 | 结果 |
|---|---|---|
| 四类Store默认缺失/目标不存在 | 临时目录真实文件系统断言，父目录也不创建 | PASS，4项 |
| 路径指目录/文件损坏/不完整表/不可读 | 四Store×四故障，普通与显式打开均拒绝；文件Hash/目录不变 | PASS，16项；不可读为PermissionError Mock |
| 显式首次初始化及正常重开 | 四Store，quick_check成功，重复初始化字节不变 | PASS，4项 |
| 打开后文件丢失 | 四Store删除临时文件后连接失败且不重建 | PASS，4项 |
| 三业务库正常读写/显式初始化预检 | 实际任务写读、仅合成预算行；先拒绝坏catalog、不顺带建其他空库 | PASS，2项 |
| 错误RAG目录应用 | TestClient真实启动，8页200、历史503、能力关闭且根目录不存在 | PASS，1项 |
| Agent缺失/损坏/缺表/目录及恢复 | 四次实际临时故障，接口503、无worker、8页/Duck200、坏文件不覆盖，恢复后原任务可读 | PASS，4项 |
| 预算损坏/额度库缺失/Schema只读 | 生成先于网络拒绝，独立catalog GLB可读，未知额度不写成0/3，不补表 | PASS，3项 |
| 晚期预算/Agent库丢失、owner锁不可访问 | 已启动后删除临时库；能力/健康安全降级且不建空库；owner ACL为Mock | PASS，3项 |

只读审查另发现晚期预算丢失时available()原可抛异常，健康被拖成503；[修复前局部证据](phase-05-wp4-db-repair/late-budget-before-fix.json)保留，增加最后3项前后安全检查。没有付费调用。

[显式CLI实测](phase-05-wp4-db-repair/explicit-init-cli.json)9/0：无`--initialize-new-installation`时退出2且不建目录；带参数退出0建立3业务库；重跑退出0且只validate、3库字节不变、不建新Neural账本。子进程空Key、全部网络和非测试目录SQLite被拒绝。此结果不是对生产执行初始化。

### 10.3 完整回归、页面及两个真实GLB

| 本轮执行 | PASS | FAIL | SKIP | 证据/边界 |
|---|---:|---:|---:|---|
| 首轮完整兼容 | 710 | 3 | 0 | [初次结果](phase-05-wp4-db-repair/compatibility-initial-isolation-result.json)，保留真实失败 |
| 修复后历史/candidate局部 | 50 | 0 | 0 | [复测](phase-05-wp4-db-repair/compatibility-retest-isolation-result.json) |
| 专项初版 | 38 | 0 | 0 | [38项](phase-05-wp4-db-repair/targeted-initial-isolation-result.json) |
| 中间完整 | 751 | 0 | 0 | [751项](phase-05-wp4-db-repair/full-intermediate-isolation-result.json)，130.11秒 |
| 最终完整 | 754 | 0 | 0 | [最终结果](phase-05-wp4-db-repair/full-final-isolation-result.json)、[JUnit](phase-05-wp4-db-repair/full-final-pytest.xml)，120.20秒 |
| 最终安全专项 | 41 | 0 | 0 | 754子集，另一次实际执行5.48秒 |
| 问答/Agent/历史/资产/导览前端 | 25/25/34/42/34 | 各0 | 各0 | frontend-*.json，明确DOM/Fetch替身 |
| 正常HTTP两轮 | 各14 | 各0 | 各0 | [01](phase-05-wp4-db-repair/http-01.json)、[重启02](phase-05-wp4-db-repair/http-02.json)，本地免费知识检索，无LLM |
| 正常模型Chrome | 4组 | 0 | 0 | [正常模型/8页/风格](phase-05-wp4-db-repair/normal-model-browser.json) |
| WP2/WP3导览/历史/异常Chrome | 8组 | 0 | 0 | [导览及降级](phase-05-wp4-db-repair/guide-browser.json)，POST仅浏览器替身 |
| 手机模拟两模型 | 2组 | 0 | 0 | [CDP触摸及三态](phase-05-wp4-db-repair/touch-browser.json)，非实体手机 |

最终完整回归所有守卫拒绝计数为0：没有触生产文件/SQLite，也没有尝试真实HTTP。存在1条原TestClient依赖的非阻断warning，原输出保留；没有跳过失败用例。现有测试只把首次创建夹具改为明确create=True，普通重开仍严格，旧calls-only预算测试改为验证拒绝自动迁移且原行不变，新增当前完整Schema历史归属测试；不删历史不可变性/并发覆盖。

8页逐一浏览器200、原图片加载、AI入口链接和布局正常。正常模型鼠标：写实325.9°、Q版453.7°；手机模拟触摸：382.6°、300.7°。滚轮、双指、放大/缩小、Reset、Loading→Ready→Error→Ready均通过。Error采用拦截**既有GLB文件GET**，恢复只重新读取同一Hash，不调用供应商。风格切换无对应资产诚实空状态，切回原模型恢复。

### 10.4 停服副本、损坏与现场恢复

正常环境使用README命令在8000单worker启动：[第一次](phase-05-wp4-db-repair/normal-01.json)11.617秒、[普通Ctrl+C停](phase-05-wp4-db-repair/normal-stop-01.json)；最新代码[重启](phase-05-wp4-db-repair/normal-02.json)11.127秒、再14项HTTP通过、[停止](phase-05-wp4-db-repair/normal-stop-02.json)。两次均精确本轮PID、端口关闭、进程退出，不杀未知进程、不删owner锁。

源服务停止后，按只读基线逐字节核对4业务库、5知识/向量文件、26BGE和14资产，复制到新独立父目录。旧WP4资源副本因SQLite字节布局不同/少缓存文件主动弃用，**未覆盖旧副本或把不匹配说成成功**。[副本准备](phase-05-wp4-db-repair/field-preparation.json)记录源HEAD及当时未提交工作树全部文件Hash，不复制Key。副本启动使用空Key、Agent执行关闭、进程外网及非副本SQLite拒绝，canonical配额副本保留2次历史，不建零额度池。

| 8011场景 | PASS/FAIL/SKIP | 实际结果 |
|---|---|---|
| corrupt | 11/0/0 | [损坏探针](phase-05-wp4-db-repair/field-corrupt-probe.json)：health200/degraded、Agent故障、历史503、8页200、坏字节不变 |
| restored | 10/0/0 | [恢复有效库](phase-05-wp4-db-repair/field-restored-probe.json)：22条原历史、ID保留，正常重启，无建库 |
| misconfigured | 11/0/0 | [错误路径](phase-05-wp4-db-repair/field-misconfigured-probe.json)：不存在RAG根目录从未创建，相关数据库明确不可用，8页200 |
| recovered | 10/0/0 | [恢复配置](phase-05-wp4-db-repair/field-recovered-probe.json)：无需初始化，原库/历史正常 |

合计42观察断言/0失败/0跳过；四次各自正常Ctrl+C退出/端口释放。坏库真实GLB浏览器[4组通过](phase-05-wp4-db-repair/field-corrupt-model-browser.json)：写实324.5°、Q版453.7°、缩放/Reset/8页/风格恢复。21日完成该浏览器运行，22日[汇总](phase-05-wp4-db-repair/field-final-summary.json)确认80个产品文件与最终源码Hash相同，未声称22日重新跑该浏览器。

坏Agent文件实际71字节（旧辅助文件名写69B，不作为大小依据），SHA-256 `22ae2950531634ab5eb7f890b1fb4d75a9b23c28fe1b132d3d9c284c0201b403`，保存在私有副本，不覆盖。恢复后Agent与原有效副本逐字节相同，预算、catalog和全局额度副本各自Hash均始终不变。

### 10.5 真实不变性、失败记录及未测范围

[全表after](phase-05-wp4-db-repair/state-after.json)逐项对比[before](phase-05-wp4-db-repair/baseline-before-state.json)：18表Schema+规范化全行、22个任务及ID、88步骤、59产物、194事件、角色JSON/文化审校/人审/资产关联全部相同；[追踪盘点](phase-05-wp4-db-repair/provenance-after.json)也全相同、无孤立事件。107条LLM记录、18条Neural4D历史操作和60历史积分没有增加。2个SUCCEEDED，已用2/3、剩1未用，无UNKNOWN/在途/待消费审批，创建关闭且第三用户取消。

[物理最终对比](phase-05-wp4-db-repair/physical-final-comparison.json)4个业务DB字节、全部sqlite_master对象及sidecar状态、active版本、5知识/Qdrant文件、26BGE和14资产文件一致；8HTML也一致。两GLB及供应商原件/内嵌纹理沿用第8节四Hash并重新实测，未转换、覆盖或重建。

保留以下失败/中断，不能冒充通过：

1. 修复前复现前两轮Windows asyncio socketpair受沙箱阻断，第三轮正常对照临时写入权限失败；第四轮在相同隔离守卫下获得本地执行条件后4观察通过。
2. 首轮完整710/3：两处历史SimpleNamespace夹具缺新只读契约；一处产品连接层误吞原约束IntegrityError。补夹具并保留约束异常，50项复测及最终754通过。
3. 专项第一次38个setup error、0执行：pytest的basetemp误与TEMP共用，初始化清理探测文件触发严格目录守卫；换独立pytest-temp，不放宽生产边界，38再41通过。[原结果](phase-05-wp4-db-repair/targeted-harness-failed-isolation-result.json)保留。
4. targeted-03中断未产出正式result，NOT_TESTED/不计通过；最终targeted-04完整41通过。不用目录存在代替测试结果。
5. 首次Store辅助自身未关闭SQLite连接导致Windows清理失败；关闭辅助连接后6组通过。不是产品库损坏修复，不制造额外产品Bug。
6. 物理Hash首次综合comparison误报false：内存Schema元组与JSON列表比较。序列化后全部字段逐项相等，修正辅助为统一列表后重新只读盘点；[初次false](phase-05-wp4-db-repair/physical-first-comparison.json)和最终全true均保留，生产库未改动。

历史状态盘点辅助沿用旧clientDate常量2026-10-20/21，实际执行以checkedAtUtc和各结果时间为准；没有修改旧输出伪造日期。22日归档不代表所有测试22日重跑。

限制：真实Windows ACL更改/不可读为NOT_TESTED，权限失败映射使用明确Mock；实际坏文件/缺表/删除/误配均真实临时文件。Schema校验为quick_check+所需表/列/对象名称，不是完整业务JSON/约束SQL防篡改认证。另一个已存在且有效的数据库仍须人工核对身份；恢复后须重启；catalog本身不可用时不能绕过资产安全服务读取目录。实体手机、跨机器、公网/多用户、当日外部API连通性NOT_TESTED；冷安装、BGE首次下载和排练本轮未重跑，沿用前次已明确日期的证据。第三次建模NOT_APPLICABLE（用户取消，不是失败）。

### 10.6 实际命令、归档和停止点

下列为本轮真实执行，私有辅助源码在同目录归档，复跑必须选新的输出目录，不在生产上执行损坏测试：

~~~powershell
Set-Location -LiteralPath 'D:\京剧\京剧'
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp4-db-repair-baseline-01\executed-helper-attempt04.py
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp4-offline-bootstrap.py --run-root D:\京剧\.runtime\phase5-wp4-db-repair-full-02 --junitxml D:\京剧\.runtime\phase5-wp4-db-repair-full-02\pytest.xml --basetemp D:\京剧\.runtime\phase5-wp4-db-repair-full-02\pytest-temp
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp4-db-repair-targeted-bootstrap.py --run-root D:\京剧\.runtime\phase5-wp4-db-repair-targeted-04 --junitxml D:\京剧\.runtime\phase5-wp4-db-repair-targeted-04\pytest.xml --basetemp D:\京剧\.runtime\phase5-wp4-db-repair-targeted-04\pytest-temp
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp4-db-repair-init-cli.py

# 五个已有前端脚本分别执行，实际输出归档frontend-*.json。
node scripts/phase2_frontend_test.mjs
node scripts/phase3_frontend_test.mjs
node scripts/phase5_wp2_frontend_test.mjs
node scripts/phase4_frontend_test.mjs
node scripts/phase5_wp3_frontend_test.mjs

# 新进程按README命令启动，辅助只加测试用网络拒绝，不改变生产配置。
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp4-server-control.py --repo D:\京剧\京剧 --python D:\京剧\京剧\.venv\Scripts\python.exe --output D:\京剧\.runtime\phase5-wp4-db-repair-normal-02
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp4-http-check.py --output D:\京剧\.runtime\phase5-wp4-db-repair-http-02.json
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp4-stop-console.py 45412 D:\京剧\.runtime\phase5-wp4-db-repair-normal-stop-02.json 8000

node D:\京剧\.runtime\phase5-wp4-model-browser.mjs D:\京剧\.runtime\phase5-wp4-db-repair-model-browser-01
node D:\京剧\.runtime\phase5-wp4-browser.mjs D:\京剧\.runtime\phase5-wp4-db-repair-guide-browser-01
node D:\京剧\.runtime\phase5-wp4-touch-browser.mjs D:\京剧\.runtime\phase5-wp4-db-repair-touch-browser-01

# 隔离副本各run、probe、stop命令/PID见field启动和停止JSON，不是生产修复脚本。
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp4-db-repair-field-start.py --run misconfigured-start-01 --wrong-root
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp4-db-repair-field-probe.py --stage misconfigured
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp4-db-repair-inventory.py --output D:\京剧\.runtime\phase5-wp4-db-repair-physical-after-02.json --compare D:\京剧\.runtime\phase5-wp4-db-repair-baseline-01\physical-resources-before.json
~~~

Node实际使用已有绝对runtime路径及XIJING_PLAYWRIGHT_PACKAGE包定位；没有安装npm依赖。最终修改/祖先/敏感内容/证据Hash核对另见同目录documentation-checks.json。归档86份文字，19张截图仅私有.runtime留存，公开[截图Hash索引](phase-05-wp4-db-repair/screenshot-manifest.json)；Q版权限不扩大，不提交DB/GLB/图片/原件/Key。原失败输出/实际执行辅助不改写；归档时git diff --check报告3处原执行辅助的EOF空行，保留原始证据，产品代码与本轮文档的格式检查通过。

产品提交ae2783ee2b241d36abf34df707cca8336a414e2a、452a0c299f1c0468087ff60b8cebf01930bc938d；测试证据提交0955d0f98db5886955359e121ddbe8e544b9b9ba。最终文档Commit/干净工作区由最终git log核实，不预造自引用Hash。**本轮付费API0、真实外部AI0、Neural4D全部请求/创建0，生产业务数据写入0。** 关键安全验收通过，当前PHASE_5_WP4_WAITING_ACCEPTANCE，停止等待人工验收，不进入WP5。
