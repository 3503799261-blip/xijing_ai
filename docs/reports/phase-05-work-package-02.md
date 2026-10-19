# Phase 5 WP2：Agent历史只读查看与可追溯展示

日期：2026-10-19（Asia/Shanghai）。状态：**`PHASE_5_WP2_WAITING_ACCEPTANCE`**。

WP1已由用户验收，本包按用户完整附件实施。功能及本包测试已完成，等待人工验收；不代表Phase 5整体完成，不进入WP3。没有付费或外部供应商调用，没有新增模型或重跑历史任务。

## 1. 起点、保护范围与完成内容

实际仓库为`D:\京剧\京剧`，起点分支`feature/phase5-competition-delivery`，HEAD `ea0f4fcfc1f1bf60e395c6a4abd71762a8380658`，工作区干净；WP1的`f58888b`与`ea0f4fc`均在祖先链。没有切分支、重写历史、合并main或推送。

本包完成：

- 独立只读历史列表、稳定分页、真实状态/类型/完整ID筛选。
- 单任务详情：保存需求、四Agent顺序/公开摘要/最新保存产物、真实引用、角色JSON、文化审校、人审及分页事件。
- 显著历史快照标识；无自动轮询、SSE回放或实时进度动画。
- 缺失输入/时间/产物诚实提示；加载、空、未找到、数据库/格式错误和手动重读恢复。
- 已有资产链接及模型来源标签；不创建或重新登记资产，不借用其他角色的Q版。
- 安全文本、引用链接白名单、错误不回显敏感内容、展示长度限制及旧响应竞态保护。

没有新增依赖、框架或数据库结构。没有修改原Agent执行/人工确认/配额业务。8页中只在`about.html`增加局部历史区，其他7页字节不变；旧报告、模型及历史记录保留。

## 2. 历史数据盘点与真实性边界

执行前先用SQLite只读连接盘点，未导入应用或执行工作流。盘点与执行后全字段对比见[before](../evidence/test-results/phase-05-wp2/before-state.json)、[最终after](../evidence/test-results/phase-05-wp2/after-final-state.json)及[来源补充](../evidence/test-results/phase-05-wp2/provenance-and-originals-before.json)。最终快照为北京时间17:54:42，涵盖最终服务重启与HTTP/浏览器确认；早一轮after保留。数据库在仓库外`.runtime`，不复制进Git。

| 数据类别 | 实际来源 | 数量/情况 | 持久化、任务关联及只读展示 |
|---|---|---|---|
| Agent任务 | `agent-tasks.sqlite3 / agent_tasks` | 22；completed 2、awaiting_confirmation 15、failed 3、cancelled 2 | 是；task_id主关联 |
| Agent执行阶段 | `agent_steps` | 88，任务各4阶段 | 是；阶段状态、摘要、开始/结束/错误，不含完整输入 |
| 阶段产物 | `agent_artifacts` | 59：planner 20、researcher 19、designer 10、reviewer 10 | 是；task_id+agent_id+version，详情显示最新保存版本及Hash |
| RAG研究结果 | researcher保存产物及result引用 | 19份researcher产物 | 是；仅读取已保存片段，不重新检索 |
| 角色JSON | tasks.result_json及designer产物 | 19任务保存部分/完整result，其中10份有design | 是；不把部分result当完整角色 |
| 文化审校 | result.review及reviewer产物 | 10份 | 是；AI辅助审校，不冒充专业人员认证 |
| 人工确认 | confirmation_json、result.userConfirmed/publicationAllowed及completed事件 | 2份已接受 | 是；原记录与事件时间，不修改确认状态 |
| Timeline | `agent_events` | 194，各任务序号连续 | 是；按真实序号分页，无Meeting/Decision/Timeline独立表 |
| 资产关联 | `assets/catalog.sqlite3 / character_assets、asset_models` | 以sourceTaskId/assetId关联 | 是；不能按名称相似推断关联 |

无waiting/running任务。已有16条带`eval-*`标识的持久化评测任务、6条其他创作任务；全部22条可关联本地费用台账中43条阶段成功调用元数据。这些证明保存记录及台账关系，不能仅凭数据库独立认证供应商，也不能把评测记录当本次真实调用或静态Mock。

现存资产目录4条模型记录，其中2条明确为`local_test_fixture`，另2条为既有Neural4D真实模型；**不是4个真实生成模型**。前端逐条显示来源。测试临时库/Fetch替身与现存数据分开，测试没有向生产库写入夹具。

没有保存的独立Agent详细请求输入统一返回null并显示“历史记录未保存该信息”。任务类型没有独立列，`character_creation`是依据既有四Agent业务的明确分类。顶层开始/结束没有独立列，只取原task事件时间；缺失则未知，绝不以updatedAt代替结束。完整性字段只说明事件序列与阶段行齐全，不承诺所有字段都有保存。

## 3. API及只读机制

| 方法/路径 | 参数及边界 | 返回/异常 |
|---|---|---|
| GET `/api/v1/agent/history` | page默认1、pageSize默认10/最大50；state/taskType/taskId选填；创建时间及ID倒序稳定排序 | 摘要items、分页、实际状态/类型选项、source、requestId；不含完整result/大产物 |
| GET `/api/v1/agent/history/{taskId}` | eventPage默认1、eventPageSize默认30/最大100 | 已保存公开详情、事件分页、资产关联、缺字段、snapshotAt；不存在404 |

未知筛选值返回200空列表；参数越界422；数据库不可读取503。错误为统一安全中文，成功响应`Cache-Control: no-store`。不存在的任务不会被创建。

选择新建小型`HistoryReader`而非复用原`TaskStore`读方法：原Store构造/连接有写初始化或恢复语义。本reader只用SQLite URI `mode=ro`、`PRAGMA query_only`及单读事务，资产库同样只读ATTACH；关闭连接结束事务，无commit、状态刷新或后台任务。没有调用任务status/result恢复方法、Agent、SearchService、Provider或资产注册服务。事件分页是保存记录读取，不是SSE重放。

详情公开字段白名单；删除秘密字段、隐藏思考、原始请求/响应/内部路径；URL不带查询串输出。限制单段JSON大小、深度/节点、数组及文字长度。前端二次结构/链接校验，只以textContent构造DOM，超长JSON折叠并限制展示长度。错误固定中文，不直接回显服务端任意message/stack。

本项目既有范围是本机可信使用，未存在可沿用的多用户登录/隔离机制，本包也未新增。不可将历史接口视为可直接公开部署的跨用户安全系统。只读事务保证一次读取的一致快照；跨页面手动查询可能读到以后真实任务的更新，不承诺跨请求快照冻结。

## 4. 使用入口与资产边界

同源服务：`http://127.0.0.1:8000`。启动方式仍见[README](../../README.md)，单worker，不公开仓库根。启动本身会初始化库并处理既有中断任务，不宣称纯只读；本包启动前无活动任务，执行后业务全表不变。

1. 打开[Agent历史档案](http://127.0.0.1:8000/about.html#ai-workshop-history)，位于协作工作台下。
2. 点击“读取历史记录”，可按真实状态、角色创作类型或完整任务ID查询。
3. 点击“查看只读详情”，展开公开产物、引用、角色JSON、审校、人审及事件。
4. 示例`ca7007e7-e535-4b1f-a9b6-1932f10e20b4`为已确认的原创“绛绣·戏韵”，已有写实资产`9e2b42e1-bbad-4a2f-ab1b-aeda18015dee`。该名称不推断为传统历史人物。
5. 该详情只链接其写实模型`1fa0b519-caf4-4009-aec2-f20b0f9a3523`；无Q版就显示未生成。内部技术Q版`3777a880-fc8c-4766-aade-948d20c6b8f0`没有正式角色/任务关联，不强行嫁接。

历史模块独立于实时创作控制器，不把查看的任务写入sessionStorage、不提供创建/接受/取消/重新执行按钮。旧实时工作台仍按原有明确操作运行，本包没有通过它发起任何任务。

## 5. 实际测试结果

完整环境、命令、原始结果、失败及修复见[WP2测试报告](../evidence/test-results/phase-05-wp2-test-report.md)。

| 验证类别 | 实际结果 | 证据边界 |
|---|---|---|
| 新后端专项 | 23通过、0失败、0跳过 | 临时SQLite、TestClient、WAL并发一致快照，不调用真实AI |
| 全部后端 | 698通过、0失败/跳过/收集错误，81.67秒 | 收集前隔离、空Key/临时账本、拒绝真实HTTP；1条既有Starlette弃用警告 |
| 新前端 | 34通过、0失败/跳过 | DOM/Fetch替身、格式/竞态/XSS/分页/来源/缺信息；不冒充浏览器 |
| 原前端回归 | 问答25、Agent25、资产36通过 | 原脚本离线测试，均0失败 |
| 本地真实GET | 最终单轮190项检查，40请求，0失败 | 全22任务/详情、筛选、分页、404/422、真实资产关联及额度读取；前一成功轮独立保留 |
| 历史浏览器 | 6组通过、0失败/跳过 | 4组真实本机读取（含8页、390×844模拟），2组明确浏览器替身故障/XSS；1920×1080桌面 |
| 两模型/8页浏览器 | 4组通过 | 原真实GLB，写实旋转325.9°、内部Q版453.7°，缩放/重置、缺风格及恢复；未生成模型 |
| 数据不变性 | 18业务表canonical Hash全部相同 | 任务集合/状态/JSON/审校/人审/事件/资产/额度/费用，四原始及兼容文件Hash一致 |

浏览器真实页面无pageerror或阻断资源错误；503仅出现在明确故障替身组，不能说所有上下文HTTP错误均为0。两个GLB回归保留切换/关闭上下文时的取消记录。截图实际保存于受控本地`.runtime`，参见[截图Hash清单](../evidence/test-results/phase-05-wp2/screenshot-manifest.json)，内部Q版含图不进公开Git；主代理实际查看了桌面/手机模拟详情与写实Viewer截图。

保留的失败：专项首次沙箱TestClient停滞后终止，不算通过；HTTP前两轮服务未完成启动、连接失败；浏览器首轮3/6、次轮5/6，均因测试选择器未对应锚点/折叠输入/提示区而修正辅助脚本，第三及最终轮6/6。集成中也发现并修复产物版本number/null、缺step/event、未提交筛选影响分页、模型来源不明确及完整性文案过宽。没有虚构生产Bug或删除失败记录。

## 6. 不变性、费用与创建锁

执行前后18个完整业务表的schema与主键元数据、完整行规范化稳定排序Hash全部一致：Agent4表、资产6表、Neural4D5表、预算3表。22任务、88阶段、59产物、194事件及所有角色/审校/人审均未变；其他7页未变，`about.html`仅新增历史区。

| 受保护文件 | 大小（字节） | 前后相同SHA-256 |
|---|---:|---|
| Q版兼容GLB | 8,827,324 | `bf9c808c15dbf5464ee67df1cdb3f64f9b2c6b3cd4ee41ecb8a6470a0554654a` |
| Q版供应商原件 | 26,600,184 | `8ef5de8a2f96fbbee9eea66737187e4a2087f88867830891a41464a473d47885` |
| 写实兼容GLB | 15,158,668 | `5a021ac6338009615e6ea232c5b9001eef6f4cc91d9d87c3eeeb5307526bdfd5` |
| 写实供应商原件 | 18,266,484 | `51fc687e0bde5fdb9074ba4560601057e17e9239f111fd2bc9e0d6601c26260e` |

LLM台账仍107条；Neural4D操作仍18条、两次SUCCEEDED、累计历史60积分。**本包外部/付费API为0、建模提交0**。全局**已用2/3、剩1未使用**，第三次为用户取消；未消费批准0，无未知/在途。现有额度接口实测`realEnabled=false`、`protocolVerified=false`，创建继续关闭；没有修改私有env或额度保护，也未对生产发送POST拒绝探针。

## 7. 修改文件、Git及Prompt

| 文件 | 变化 |
|---|---|
| `backend/app/agents/history.py` | 新增有界只读查询、脱敏、事件及严格资产关联 |
| `backend/app/api/agents.py` | 两个GET路由，保留原执行路由 |
| `backend/tests/test_agent_history.py` | 23项隔离测试 |
| `about.html`、`js/ai-workshop/main.js` | 历史区、锚点映射和隔离初始化；原模块版本链接保持以兼容旧检查，静态服务no-store |
| `css/ai-workshop-history.css` | 独立ai-workshop命名空间、折叠/响应式/焦点样式 |
| `js/ai-workshop/history-contracts.js`、`history-services.js`、`agent-history.js` | 协议、GET/超时/错误、文本UI；不影响旧问答和资产协议 |
| `scripts/phase5_wp2_frontend_test.mjs` | 可重复运行前端替身专项 |
| README、本报告、测试与Prompt目录 | 当前范围、运行/查看说明、真实证据与停止点 |

产品及测试真实提交：`9e3516dc6a7ada53d067a929383c5225368e902d`，`feat(phase5): add read-only agent history`。测试报告/证据提交：`f8a1f47126b1104f1f004a4d4a62ba6fc4ad582f`，`test(phase5): archive history regression and invariants`。本文、README及Prompt再独立归档；其最终Hash及提交后工作区状态由实际Git记录/最终回复给出，不预造自身提交Hash。未改旧提交、日期或远端。

完整原始附件逐字节保存于[06-wp2-approved-user-request.txt](../prompts/phase-05/06-wp2-approved-user-request.txt)，SHA-256 `8e79bb993d29f191d281e2fdd9c3886c99d8f50387e332c9aa341d10664c8cc6`。公开协作快照、元数据及真实修改/失败演进见[Phase 5 Prompt记录](../prompts/phase-05/README.md)，排除隐藏推理、系统信息、凭证、签名链接及内部子Agent消息，不补造用户回复。

## 8. 验收核对

- [x] 核实真实持久化历史来源，区分评测、测试夹具、当前运行与缺失数据。
- [x] 安全只读查询、列表和详情可用；状态为记录状态，与实时控制器区分。
- [x] 缺信息不重建；加载、空、404、服务/格式错误及手动恢复可用。
- [x] 读历史不重跑Agent、不调用付费API、不提交Neural4D。
- [x] 两个真实GLB及两原件未变，额度与创建锁保持。
- [x] 后端、前端、8页、真实历史及原模型回归通过，失败保留。
- [x] 全量业务不变性、测试证据、Prompt、真实Git和工作区核对完成。

没有未解决的WP2核心阻断。限制：实体手机未验证；移动端本次仅Chrome模拟。今天真实文本供应商连接未测且不获授权；空电脑依赖/私有历史/成品迁移未测。历史无法恢复从未保存的详细输入或旧版本完整视图，过大/异常/未知结构会明确降级为缺失或格式错误，不补造。无新多用户安全体系，不能直接公开历史API。

本包技术完成、等待人工验收；不自行进入WP3。WP3演示导览、最终交付包/视频/PDF均不在本包完成范围。第三次建模继续取消。
