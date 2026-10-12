# Phase 4：角色资产、双风格与网页3D展示增量说明

记录日期：2026-10-11。本文依据当前功能代码编写，说明已实现的协议与门禁，不代替阶段验收报告。真实Neural4D建模仍需要用户逐次单独批准；平台图像生成供应商尚未接入。

## 1. 与现有系统的关系

保留8页HTML、原生ES Module架构和酒红、金色、米白样式。在 `about.html#ai-workshop-model` 内建立“AI数字IP生成中心”，复用既有RAG问答和四Agent工作流。新的资产编排在 `js/ai-workshop/digital-assets.js`，Viewer适配在 `js/ai-workshop/model-viewer-adapter.js`；新增样式仍使用 `ai-workshop-*` 命名空间。

Agent完成并经人工确认后，可以将真实 `sourceTaskId` 交给资产面板。事件 `ai-workshop-character-selected` 只传递任务ID，并读取已有资产；不自动创建资产、执行Agent或请求建模。后端 `AssetService` 再次核查任务状态、四步骤完成情况、文化审校通过、人工确认与真实引用，不信任浏览器提供的角色快照。

实际调用链：

```text
已确认的Phase 3任务
  → 本地角色资产快照与文化引用
  → 服务端固定风格模板生成视觉Prompt
  → 人工确认Prompt
  → 导入有使用权的实际概念图并确认图片Hash
  → 受保护的单次模型批准与配额预留（真实创建当前关闭）
  → 已登记GLB资源
  → model-viewer实时展示
```

当前可独立使用合法GLB测试素材验证Viewer；它不是生成的京剧角色，不属于任何角色风格版本。

## 2. 角色家族、资产与版本

资产保存在SQLite目录表，文件以受控ID登记并存放在资产存储目录。核心字段如下。

| 字段 | 实际含义 |
| --- | --- |
| `assetSchemaVersion` | 新资产为 `1.1`，历史 `1.0` 继续读取 |
| `assetId` | 一份不可覆盖的角色资产记录ID |
| `characterId` | 由 `sourceTaskId` 与 `sourceResultHash` 推导的稳定UUID5，同一文化方案的风格家族身份 |
| `sourceTaskId`、`sourceResultHash` | 权威Agent任务及其设计、审校、引用快照Hash |
| `citationHash`、`citationSnapshot` | 原文化证据及其摘要Hash，不创建新的虚构来源 |
| `characterSnapshot`、`reviewSnapshot` | 冻结的角色设计与文化审校结果 |
| `characterConfirmation` | 已确认状态及原任务序列 |
| `knowledgeGeneration`、`promptVersions` | 原知识库与Agent Prompt版本信息 |
| `mode` | `personal` 或 `enterprise`，与视觉风格独立 |
| `purpose`、`enterpriseBrief` | 用途与可选企业需求 |
| `styleMode` | `chibi`（Q版卡通）或 `realistic`（写实国风） |
| `version`、`styleVersion` | 当前资产与风格分支版本，初版为1 |
| `parentAssetId` | 编辑版本指向原资产，初版为空 |
| `culturalReviewRequired` | 自由编辑草稿为 `true`，服务器固定模板初版为 `false` |
| `visualPrompt`、`images`、`models` | 此资产版本的Prompt、图片与模型 |
| `commercialRightsVerified` | 当前为 `false`；企业模式不代表已取得商用许可 |

同一已确认任务可以登记两种风格；它们共享角色家族与文化依据，但拥有不同 `assetId`、Prompt Hash、图片与模型。个人/企业用途不会自动互换。前端选择风格时只查询已登记记录；缺少该风格时显示“当前风格尚未生成3D模型”，清除上一个风格的图片和Viewer内容，不自动创建记录或调用供应商。

历史记录读取时，缺少 `styleMode` 按 `realistic` 解释，缺少 `styleVersion` 使用历史 `version`，缺少 `characterId` 依据原任务与Hash推导，并返回 `legacyStyleDefaultsApplied`。这是读取兼容层，不修改历史存储、图片、模型、模板内容或批准Hash。

## 3. 实际视觉模板

`backend/app/assets/visual_prompt.py` 的组合模板版本为 **`opera_asset_visual_v2`**。

| 风格 | 模板版本 | 表达边界 |
| --- | --- | --- |
| `realistic` | `opera_realistic_v1` | 自然人体比例、清晰服饰与构件关系；写实外观不等于历史复原 |
| `chibi` | `opera_chibi_v1` | 可爱的比例、清晰轮廓和简洁造型；保留文化身份、服饰、配色与辨识构件 |

模板从原角色JSON提取名称、定位、服饰、配色、视觉元素与原创构思，区分“文化依据”和“原创设计”。Q版比例属于艺术表达，不自动删改靠旗、雉尾、脸谱或道具；需要简化时另行文化复核。

技术画面要求是单角色全身、双足完整、正面或轻微三分之四视角、简单背景、均匀光照、构件边界清晰。原Agent `visualPrompt` 单独保存在 `originalVisualPrompt`，避免舞台背景压过成模参考要求。模板同时保存 `negativePrompt` 与 `limitations`，明确单张图不能证明背面细节及薄构件可能成模失败。

`visualPrompt` 包含 `imagePrompt`、`negativePrompt`、`templateVersion`、`styleTemplateVersion`、`styleMode`、`styleVersion`、`styleLabel`、`limitations`、`editableDraft`、`promptHash`、`approved`、`approvedAt`。Hash使用规范化JSON的SHA-256；批准时间、批准标记与Hash自身不改变视觉输入Hash。

## 4. 自由编辑采用新版本与文化门禁

编辑接口不会覆盖旧资产：

```json
{
  "expectedPromptHash": "当前视觉Prompt的64位小写SHA-256",
  "imagePrompt": "用户编辑后的画面要求",
  "negativePrompt": "用户编辑后的负向画面约束",
  "action": "create_version"
}
```

服务器核对旧Hash，在SQLite原子事务中分配分支版本，生成新 `assetId` 与 `promptHash`，保存 `parentAssetId`；新版本 `approved=false`、图片与模型列表为空、`editableDraft=true`、`culturalReviewRequired=true`。旧版本及其素材保留，可从前端历史版本选择器读取。

全文编辑可能改动文化事实，服务器不接受客户端“仅修改画面”等自我声明解除门禁。草稿可保存与展示，但不能直接确认视觉Prompt、上传或确认概念图、真实建模。用户需要通过既有Agent工作流重新审校并确认新任务，然后从新 `sourceTaskId` 登记资产；没有自动审校或自动解除流程。

同风格、同原任务快照、同用途和企业需求分支出现新Prompt版本后，旧的未发送模型批准不能继续提交。已经发送的历史任务与同一幂等键重放仍指向原任务，不被重新解释为新风格或新参数。

前端限制 `imagePrompt` 3000字符、`negativePrompt` 1000字符，并按UTF-8检查整个JSON不超过8192字节。未变更的文本不会自动制造新版本。

## 5. 已实现的资产API

统一前缀为 `/api/v1/assets`；以下路径是项目后端接口，不是供应商接口。

| 方法与路径 | 请求与结果 |
| --- | --- |
| `POST /characters` | `{sourceTaskId,mode,styleMode,purpose,enterpriseBrief?}`；返回完整资产 |
| `GET /characters` | 可按 `characterId`、`sourceTaskId`、`mode` 筛选；返回 `{characters}` |
| `GET /characters/{assetId}` | 读取一个资产及实际素材 |
| `GET /characters/{assetId}/styles` | 返回 `{characterId,characters}` 风格家族 |
| `POST /characters/{assetId}/prompt-versions` | 保存新编辑草稿，返回新完整资产 |
| `POST /characters/{assetId}/visual-approval` | `{promptHash,action:'accept'}`，Hash匹配且文化门禁通过才接受 |
| `POST /images` | 查询参数 `assetId,provenance,licenseNote`；请求体为原始图片二进制 |
| `GET /images/{imageId}`、`GET /images/{imageId}/file` | 图片元数据与规范化PNG文件 |
| `POST /images/{imageId}/accept` | `{imageHash,action:'accept'}`，确认真实图片版本 |
| `POST /models/import` | 查询参数 `assetId,licenseNote`；请求体为实际GLB二进制 |
| `GET /models` | 可按 `assetId` 筛选，返回 `{models}` |
| `GET /models/{modelId}` | 模型登记元数据 |
| `GET /models/{modelId}/file`、`GET /models/{modelId}/download` | 已登记GLB展示与下载 |
| `GET /usage` | 本地额度、真实功能门禁与准备状态，不查询供应商 |

图片支持PNG、JPEG、WEBP，最多10MB；经实际文件检查后规范化PNG。`hash` 是规范化文件SHA-256，`sourceHash` 记录原上传文件，`normalization` 记录处理。`provenance` 仅允许 `manual_image` 或 `imported_ai_image`。前端要求许可说明、使用权确认，并且实际图片成功显示后才允许点击接受；这些用户声明不等于平台已独立认证许可。

图片元数据包括 `imageId`、`assetId`、`characterId`、`styleMode`、`styleVersion`、`assetVersion`、`hash`、`sourceHash`、宽高、大小、MIME、Prompt Hash、来源声明、许可说明、接受状态与文件URL。

GLB导入上限50MB，服务器检查GLB结构与资源边界，资源访问时再核对实际文件大小与Hash。合法导入的模型标为 `origin='licensed_import'`；供应商任务结果登记为 `origin='neural4d'` 时关联真实任务ID、概念图ID/Hash、角色/风格/版本及文化来源Hash。

独立测试夹具为 `origin='local_test_fixture'`，其 `assetId`、`characterId`、`styleMode`、`styleVersion` 为空，明确标注“本地合法GLB测试夹具（非Neural4D生成）”。它只出现在独立测试素材选择器中，不能冒充两种风格的真实角色模型。

## 6. Neural4D接入与原方案差异

当前供应商封装为 `backend/app/providers/neural4d.py`，唯一建模业务入口为 `backend/app/assets/neural_service.py` 的 `ModelService`。供应商Key仅由后端读取；浏览器不连接供应商。

依据本轮官方接口核对，当前图片建模封装使用：

```text
POST https://alb.neural4d.com:3000/api/generateModelWithImage
Content-Type: multipart/form-data
image: 已确认并经过Hash检查的实际图片文件
其他表单字段: 服务器按风格冻结的参数
```

原检查点A方案中的 `fileKey` / 图片预处理链不能直接套用到此接口。当前实现直接提交multipart图片，没有自动回退到旧接口，没有调用旧预处理链；图片规范化在本地完成，`enableImageEnhancement=false`。正式真实请求前仍需核对官方端点、字段、响应、账户权限与Credit费用，官方参考链接及本轮核对证据由阶段报告补充。本文不将代码中的封装视为已完成真实API联测。

两种风格共用上述入口，不使用可能返回多个候选模型的专用Q版接口。

| 参数 | Q版卡通 | 写实国风 |
| --- | --- | --- |
| `modelCount` | `1` | `1` |
| `mesh_quality` | `standard` | `standard` |
| `faceNum` | `100000` | `500000` |
| `disablePbr` | `0` | `0` |
| `onlyGenerateMesh` | `false` | `false` |
| `enableImageEnhancement` | `false` | `false` |

面数是技术参数，不能保证视觉风格；风格由分别确认的概念图表达。实际Credit费用尚需核实，前端不硬编码某个价格。

受保护接口已实现：`POST /neural4d/verify`（明确请求只读余额验证）、`POST /model-approvals`、`POST /model-tasks`、`GET /model-tasks/{jobId}`、`POST /model-tasks/{jobId}/refresh`、`POST /model-tasks/{jobId}/query-continuation`。供应商操作需要单独的本地 `X-Asset-Admin-Token`，不是供应商Key；真实创建还需要服务端开关、协议/余额/费用核验、历史额度核对和有效单次批准。当前网页生成按钮保持禁用，`submitModelTask()` 返回未开放状态，没有自动发送处理器。

## 7. 全项目三次硬限制

`UsageManager` 使用一个项目级SQLite账本，固定 `MAX_CREATION_ATTEMPTS=3`、`modelCount=1`。双风格、个人/企业、不同Key或不同角色不会形成新的额度池。新账本历史为未知，不默认认定使用0次；未经可信人工历史核对，`used_calls`、`remaining_calls` 可以为空且创建被拒绝。

单次批准冻结 `assetId/assetVersion/characterId/styleMode/styleVersion`、文化快照Hash、Prompt Hash、图片ID/Hash、用途、服务器参数和预计Credit。创建请求要求 `X-Idempotency-Key`；SQLite事务原子预留，唯一幂等键与一次性批准防止并发重复提交，`mark_started` 只允许一个发送者赢得HTTP提交权。独立项目发送锁配合重启恢复；数据库约束与触发器保护计数及不可覆盖的审核记录。

`FAILED`、超时或可能已经发送的请求均不返还额度。无可靠任务ID或响应不明确时进入 `UNKNOWN/PENDING_RECONCILIATION`，停止新创建并人工核查；没有自动重建或无限重试。已有任务查询使用明确操作，查询间隔、每轮次数和时长有限制；查询继续需要明确确认。查询、下载等操作单独记账，不被误记为新的建模提交尝试。

## 8. 前端资产、企业模式与安全

个人与企业模式共用资产流程。企业需求实际字段为 `organizationType`（`game/tourism/ip_design/other`）、`audience`、`useCase`、`designGoal`、`culturalBoundaries`、`deliveryScope`、`licenseStatus`（`unverified/user_authorized`）。企业摘要可以填入现有Agent需求框，用户继续手动发起原工作流；不会直接生成模型。

资产注册、Prompt版本保存、图片接受与模型导入都有显式按钮。读取风格、切换面板、恢复已保存资产仅使用本地GET；没有付费服务调用。重复本地提交在前端进行阻断，但真实额度安全由后端而非禁用按钮承担。

服务层遵循既有API地址配置，检查返回协议，错误信息以中文显示。内容用 `textContent` 和DOM节点构造，不直接插入模型或用户HTML。图片和模型文件URL限制为配置后端源及已登记ID对应的 `/images/{id}/file`、`/models/{id}/file|download`，拒绝任意外部URL、凭据、查询参数与危险协议。引用链接走独立安全校验。

## 9. model-viewer与实际状态

Viewer从本地 `js/vendor/model-viewer/model-viewer.min.js` 延迟加载，在选择有效已登记GLB后才创建组件。适配层不包含生成API。默认启用 `camera-controls`，水平角不限制，垂直范围15°～165°，默认相机 `0deg 75deg auto`、视场角35°。

支持鼠标拖拽、滚轮、触摸拖拽与双指缩放，并提供放大、缩小、重置、进入/退出触摸交互按钮。默认 `touch-action='pan-y'` 便于页面上下滚动，主动进入交互后为 `none`，退出恢复页面滚动。放大/缩小改变当前相机半径，重置返回默认视角。

状态不是计时播放：选择文件后为 `loading`，仅组件真实 `load` 事件转为 `ready`；组件 `error`、加载超时或组件加载失败转为 `error` 并显示原因。重新加载只读取原文件，不提交建模。切换资产时新加载世代屏蔽旧资源的迟到事件；缺少风格模型时 `idle` 显示明确空态。

## 10. 可验证的DOM与诊断数据

元素 `#ai-workshop-asset-summary` 暴露当前 `data-asset-id`、`data-character-id`、`data-style-mode`、`data-style-version`，用于检查切换是否显示正确资产。

元素 `#ai-workshop-viewer-host` 暴露只读观测数据：

| 属性 | 意义与单位 |
| --- | --- |
| `data-viewer-state` | `idle/loading/ready/error` |
| `data-content-mode` | `legal_test_fixture/character_style_asset/style_asset_missing` |
| `data-style-mode` | 当前实际风格；独立夹具为 `not_character_asset` |
| `data-camera-theta` | 实际相机水平角，弧度 |
| `data-camera-phi` | 实际相机垂直角，弧度 |
| `data-camera-radius` | 实际相机半径，米 |
| `data-observed-degrees` | 用户同方向连续旋转的最大已观测范围，角度 |
| `data-user-event-count` | `camera-change` 中来源为 `user-interaction` 的事件数 |

`window.xijingAssetViewerDiagnostics()` 返回当前状态、登记模型ID/Hash、相机、触摸状态、错误与最多200条相机样本，不包含Key或内部文件路径。

角度统计跨0°/360°展开，只计 `user-interaction` 来源；反向拖动重置当段统计，程序变更也不会计入连续范围。不能把往返小拖动或程序设置视角累加成260°用户验证。真实鼠标或触摸验收须有实际GLB加载、真实交互事件、至少260°同方向范围及对应截图/操作证据；DOM数字是辅助证据，不替代可见模型与实际操作。

## 11. 测试边界与待完成条件

`scripts/phase4_frontend_test.mjs` 初版实际执行 **33项离线检查通过**；修复真实浏览器发现的GLB失败缓存后增加2项重载与受控URL检查，最终保存的 [离线结果](../evidence/test-results/phase4-frontend-offline.json) 为 **35通过、0失败**（2026-10-11，Node v24.15.0；每次复测时间以JSON为准）。这些检查使用显式测试替身和静态检查，验证协议、安全URL、资产风格隔离、新版本门禁、重复提交防护、Viewer事件状态及连续角度算法；不等于浏览器GLB渲染、物理触摸、真实Neural4D或付费API联测。

实际桌面浏览器和手机宽度视口结果、真实鼠标范围、缩放、Loading事件记录、Ready/Error截图及失败修复以阶段测试报告为准。Loading已实际观测，但没有独立Loading截图；真手机触摸与双指缩放尚未验证。不能从离线替身测试推断浏览器或供应商通过，本文未单独开展供应商调用。

仍需明确的外部条件包括：图像供应商与费用、输入与输出使用许可、Neural4D历史真实提交次数、单次Credit、协议与鉴权验证，以及每次真实建模的用户单独授权。合法导入图片/模型和独立Viewer夹具可用于本地验证，但不能被报告为平台已经生成了两种风格的京剧3D角色。

## 12. 实现位置

- 前端：`about.html`、`css/ai-workshop.css`、`js/ai-workshop/{contracts,services,main,agent-workflow,digital-assets,model-viewer-adapter}.js`。
- 资产：`backend/app/assets/{schemas,visual_prompt,store,service,validation}.py`。
- 建模门禁：`backend/app/assets/{usage,neural_service}.py`、`backend/app/providers/neural4d.py`。
- 项目API：`backend/app/api/assets.py`。
- 前端离线检查：`scripts/phase4_frontend_test.mjs`。

Git、Prompt演进、失败案例与真实浏览器证据应引用实际记录，由最终阶段报告统一汇总；本文不生成提交Hash、供应商任务或虚构测试数据。
