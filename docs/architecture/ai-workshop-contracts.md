# AI戏韵工坊前端边界与数据约定

状态：Phase 1 前端约定；尚未接入任何 AI 后端。本文依据 `js/ai-workshop/contracts.js`、`services.js` 和 `main.js` 的实际结构编写，具体后端地址与协议留待获准阶段确定。

## 结构

`about.html` 保留原页面地址，仅在工坊加载 `css/ai-workshop.css` 与 ES Module 入口 `js/ai-workshop/main.js`。其他七页继续使用原静态页面与资源。

- `main.js`：面板与锚点切换、焦点、问答校验、推荐填入、用户消息显示、当前页面需求草稿及服务提示。
- `contracts.js`：Agent 状态、服务能力、JSDoc 数据形状。
- `services.js`：单一服务边界。当前所有方法只返回明确的 `UnavailableResult`，不请求服务器，也不生成内容。
- Agent 卡片使用原生 `details/summary` 展开职责；没有模拟计时器、任务进度或 AI 摘要。

新增样式限定 `ai-workshop-*`，复用原网站的酒红、金色、米白与字体。工坊内部通过 `#ai-workshop-overview/qa/agents/create/model` 定位面板；页面级导航仍是独立 HTML 链接。

## 已有前端服务签名

| 方法 | 输入 | Phase 1 返回 |
|---|---|---|
| `getServiceCapabilities()` | 无 | 四项能力均为 `false` |
| `askOperaQuestion(request)` | `QuestionRequest` | `Promise<UnavailableResult>` |
| `startAgentWorkflow(brief)` | `CreationBrief` | `Promise<UnavailableResult>` |
| `generateConceptImage(brief)` | `CreationBrief` | `Promise<UnavailableResult>` |
| `submitModelTask(request)` | `{ imageId }` | `Promise<UnavailableResult>` |

`UnavailableResult` 包含 `available: false`、`status: 'unavailable'`、`capability`、`message`。问答有效提交只追加用户自己的提问，并显示“京剧AI知识问答正在建设中，将在Phase 2接入私有知识库。”；通知不伪装成 AI 回答。

输入由 `textContent` 渲染；问题最多 600 字，角色需求最多 1200 字，拒绝空白。问答区最多保留 12 条当前页面内用户提问。草稿不进入本地持久存储，刷新后清空。

## 后续数据形状（未实现能力）

| 约定 | 必要字段 | 使用条件 |
|---|---|---|
| `QuestionRequest` | `question`；可选 `conversationId` | Phase 2 接入真实问答 |
| `QuestionAnswer` | `answer, citations, uncertain, requestId` | 内容和引用来自真实后端 |
| `Citation` | `id, title, sourceId`；可选 `locator, url, excerpt` | 资料必须可核查，不填样例来源 |
| `CreationBrief` | `requirements, style, styleLabel` | 当前为用户草稿，之后才作为任务输入 |
| `WorkflowEvent` | `runId, agentId, sequence, state, occurredAt` | Phase 3 真实执行事件 |
| `ModelTask` | `taskId, status`；可选 `progress, modelUrl, downloadUrl, errorCode` | Phase 4 真实模型任务 |

Agent 的 `state` 支持 `pending/running/completed/failed/awaiting_confirmation`，对应待执行、运行中、已完成、执行失败、等待用户确认。当前四个 Agent 均为待执行且服务未接入；状态图例仅解释未来状态。

未来工作流使用 `runId` 与递增 `sequence` 处理重复或乱序事件；`summary` 必须来自实际执行；`confirmationId` 标识待人工确认项。模型状态支持 `queued/processing/succeeded/failed`；当前没有真实 `taskId`，不可创建伪任务或百分比。

## 安全与扩展

Phase 1 没有 API、RAG 索引、Agent 后端、生成图片、Neural4D 请求、3D SDK 或密钥，也不需要环境变量。后续由服务适配层访问项目后端；第三方密钥只保存在后端环境，不能放进 HTML、JS 或前端可读环境配置。

本阶段不预设未验证的 API URL、SSE 协议或模型格式。具体方案在用户批准对应阶段后，结合真实服务、引用来源、错误及取消行为确定；模型预览容器须接入真实查看器，下载须对应真实产物。
