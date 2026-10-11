# AI戏韵工坊前端边界与数据约定

更新日期：2026-10-11（Asia/Shanghai）。本文根据当前前端和FastAPI实现更新。问答和Agent协作连接项目后端；真实功能/浏览器验收结果以阶段证据为准，不由协议文档宣布通过。RAG内部实现见 [Phase 2架构](phase-02-rag.md)，工作流实现见 [Phase 3架构](phase-03-agents.md)。

## Phase 1继承与历史边界

Phase 1基准 `04b2c571e068ec0b26205fcce0c075395caeebce` 的所有AI服务仅返回 `UnavailableResult`，四能力false；有效问答只追加用户文字并说明未接入，最多保留12条用户提问。它没有网络、助手回复、RAG索引或真实引用，这是当时的真实交付事实。[Phase 1报告](../reports/phase-01.md)与该提交保存原始约定。

Phase 2及Phase 3保留8页结构、about地址、原文化导航及酒红/金/米白。工坊样式仍限定 `ai-workshop-*`，模块只在about加载。Agent保留原生details；草稿最多1200字符单位、页面内暂存、刷新清空。独立的Agent提交按钮才上传需求启动协作；概念图及3D入口仍未接入。

## 模块与服务签名

| 文件 | 当前职责 |
|---|---|
| about.html | 稳定问答DOM ID、服务重查/手动重试、内部面板及缓存版本入口 |
| main.js | 面板/焦点、校验、请求锁/加载、安全消息与每回合引用、能力反馈；保留草稿与通知 |
| contracts.js | 原Agent状态/JSDoc；真实能力、QuestionAnswer及错误结构的运行时校验；安全引用URL |
| services.js | 只调用项目API，55秒聊天超时、错误映射、幂等头、能力缓存及异步恢复 |
| agent-workflow.js | Agent提交/状态/结果/确认/取消、安全文本与真实引用、任务ID恢复及有界查询；初始化异常与问答隔离 |

| 方法 | 输入 | 当前返回 |
|---|---|---|
| getServiceCapabilities() | 无 | 同步只读缓存；初始false，绝不为显示效果自行变true |
| loadServiceCapabilities() | 无 | Promise，GET真实capabilities；同时查询合并，失败置回false |
| askOperaQuestion(request, options?) | QuestionRequest；可选idempotencyKey | Promise<QuestionAnswer>，失败抛ServiceError；保留单参数调用兼容 |
| startAgentWorkflow(brief, options?) | requirements、style；可选parentTaskId/idempotencyKey | Promise<WorkflowCreated>；同键同需求重放现有任务，失败抛ServiceError |
| getAgentWorkflowStatus(taskId, options?) | taskId；可选afterSequence | Promise<WorkflowStatus>，免费查询真实任务和递增事件 |
| getAgentWorkflowResult(taskId) | taskId | Promise<WorkflowResult>，严格校验角色、审校及证据映射 |
| confirmAgentWorkflow(taskId, request) | confirmationId、expectedSequence | Promise<WorkflowStatus>，服务端最终接受门禁，无新模型调用 |
| cancelAgentWorkflow(taskId, request) | expectedSequence | Promise<WorkflowStatus>，记录真实取消意图，无假撤回费用 |
| generateConceptImage(brief) | CreationBrief | Promise<UnavailableResult> |
| submitModelTask(request) | imageId | Promise<UnavailableResult> |

能力顶层字段为questionAnswering、knowledgeSearch、agentWorkflow、conceptImage、imageToModel，均boolean。questionAnswering由后端真实索引/Embedding及同配置的成功LLM连通记录决定；agentWorkflow还要求Supervisor工作者有效、开关启用及累计/增量预算未耗尽。capabilities自身不发起付费探测。conceptImage和imageToModel始终false，即使意外收到true，前端也不展示其已接入。

初次、进入未就绪问答面板、网络恢复或用户“重新检查服务”可查询能力，无定时器假进度、自动模型重试或无限轮询。未就绪并不伪造回答；用户仍可发送并获得准确的配置/索引错误或真实资料不足状态。

## 同源请求与响应

默认meta `ai-workshop-api-base=/api/v1`。FastAPI在8000同时白名单提供页面与API；可选跨端口调试地址仅为公开API地址，绝不包含供应商Key。服务配置拒绝可执行协议和带凭证URL。主入口、services及contracts整条import链有相同缓存版本，静态后端同时采用no-store。

聊天POST `/api/v1/chat` 输入question及可选conversationId；输出保留Phase 1约定的answer、citations、uncertain、requestId。每次提问独立检索，没有服务器语义对话记忆。客户端提交标识由客户端生成用于 `X-Idempotency-Key`，不冒充后端真实requestId。

Citation字段为id、title、sourceId、locator、url、excerpt，可加contentKind。后端必须从本次真实检索证据映射来源，不采用模型生成的来源标题/URL。前端校验类型/长度及重复引用ID；确定答案无引用会被拒绝显示。`uncertain=true`的资料不足说明可有空引用。

`contentKind=original_fact_summary`显示“本项目原创事实摘要（据所列来源核对）”，不称官方逐字原文。来源网页只是核查依据。来源标题、位置、摘要与模型正文均用textContent创建；没有Markdown/HTML注入。引用链接仅允许绝对HTTP(S)，拒绝credentials和可执行协议，新窗口设noopener noreferrer。

错误结构为 `{error:{code,message,retryable},requestId}`。浏览器不显示原始第三方错误、栈或内部配置。网络/超时/HTTP/非法JSON/无效引用有分别处理；只有retryable错误提供原回合重试按钮。聊天55秒、能力检查8秒；AbortController结束本次等待，不会自行重复付费调用。

## 状态、消息与引用归属

问题拒绝空白及超过600个UTF-16字符单位；服务器还检查加检索指令后的512-token限制，不能静默截断。pending锁在发出请求前设置，禁用发送/重试并更新aria-busy；finally恢复。等待期间编辑的新问题不会被旧请求完成时清掉。

当前最多保留12个**完整页面内问答回合**，与Phase 1仅保留用户节点不同。每个回合存用户问题、助手结果、独立引用details及真实requestId。资料区明确对应的问题/请求，允许从旧答案选择其依据。新请求及错误时不会把上一次引用当成新题证据；刷新后消息清空。

服务徽章、hero文案、data-service-state与ARIA依据真实检查/请求变化，分别支持checking/ready/unavailable/loading/answered/uncertain/error。加载只反映真实请求；没有真实返回就没有助手答案和生成完成动画。

## Agent实际协议与后续模型边界

| 约定 | 字段 | 当前状态 |
|---|---|---|
| CreationBrief | requirements、style、styleLabel | 页面内草稿含风格标签；Agent上传仅requirements/style及可选parentTaskId |
| WorkflowEvent | kind、runId、sequence、occurredAt；Agent事件agentId/state，Task事件taskState；可选summary/confirmationId/errorCode | 后端SQLite事务产生的真实公开事件，不含隐藏思维链 |
| WorkflowStatus | taskId/runId/state、agents、completedSteps/totalSteps、events/lastSequence、confirmation、resultReady、cancelRequested、requestId | 状态与消息不按计时器虚构；Task和Agent枚举分开 |
| WorkflowResult | schemaVersion/taskId/design/review/citations/uncertain/publicationAllowed/userConfirmed/knowledgeGeneration/promptVersions/requestId | 来源沿用Phase 2；最终确认前不可导出为已确认方案 |
| ModelTask | taskId、status；可选progress/modelUrl/downloadUrl/errorCode | 仅未来类型，没有模型任务 |

Agent状态仍为pending/running/completed/failed/awaiting_confirmation。Task状态为waiting/running/awaiting_confirmation/completed/failed/cancelled；cancelled不塞入Agent枚举。四卡初始待执行，收到真实状态才更新；图例仍只说明含义。summary来自已校验的公开产物，时间/序号来自持久化。模型状态queued/processing/succeeded/failed仅预留，不生成伪3D taskId或百分比。

Researcher已直接复用独立SearchService和原Runtime知识线程，不依赖聊天DOM或另开本地索引。Planner/Designer/Reviewer使用既有Provider，正常流程三次真实模型调用，预算及审校不通过时停止；图像/3D仍须后续阶段批准。

Agent的create/status/result/confirm/cancel五API详见[Phase 3架构](phase-03-agents.md)。创建响应丢失时人工重试沿用原输入/幂等键；重放可返回已经结束的原任务。sessionStorage只保存taskID，刷新免费GET恢复，未找到任务不自动重建。活动任务每秒约一次GET，上一请求结束才安排下一次，单次10秒、最多180次或240秒，隐藏/终止/等待确认停止查询；断线保留最后真实状态，手动查询免费且不会重新创建任务。

最终接受要求当前confirmationID/sequence、四阶段完成、辅助审校pass、uncertain=false；之后publicationAllowed/userConfirmed才为true。前端再次检查门禁后才允许明确下载角色JSON。受文化问题限制的草案不能由按钮变成已核实事实。设计的visualPrompt只是一段文字，未生成概念图。

当前Planner为v4、最大384输出tokens，Research为v4 policy（最多三次真实查询，必要时用既有实体元数据补查，原始不足记录不覆盖），Designer/Reviewer为v3；澄清时允许researchQueries为空，非澄清必须有查询，合法单字传统术语可保留。坏计划的公开诊断仅含白名单字段路径/类型和脱敏调用元数据，不渲染原始模型JSON/异常。后端序号限制0～2^63-1；前端使用安全整数范围。Supervisor独占agent-tasks-owner.lock，未获得锁时诊断AGENT_TASKS_LOCKED且不恢复他人正在执行的任务；启动/退出finally负责释放任务与知识库资源。

取消反馈优先识别后端state=cancelled，避免已取消却仍显示“当前阶段收尾”。只有后端仍running且cancelRequested=true才显示等待收尾。v1审校漏判和v2原创声明误报保留原始证据；Prompt迭代不能被写成专家已审核或完整消除幻觉。

## 验证边界

[前端25项离线检查](../evidence/test-results/phase-02-frontend-unit.json)是服务/DOM test double和静态检查。真实浏览器8页、桌面/手机、四推荐题、连续问答、展开来源、空输入、停机恢复与安全文字已分别验证，见 [实测报告](../evidence/test-results/phase-02-browser-test-report.md)。没有以Phase 1旧截图代替真实后端证据。网络故障立即失效ready能力，旧异步检查不会恢复过期状态；免费重查保留历史与手动重试。只在工坊根元素补充锚点滚动偏移，避免手机固定导航遮挡标题。
