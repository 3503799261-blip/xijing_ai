# 第二次写实建模执行记录

初始记录日期：2026-10-14；最新更新：2026-10-17。当前状态：**SECOND_MODEL_SUBMITTED_PROCESSING**。用户已接受新角色并要求保留原图与冻结Prompt继续；第2次真实提交HTTP200、实际扣费30积分，原任务正在生成，未创建第3次。前7节保留各时间点事实，第8节记录实际发送与后续恢复。

## 1. 已收到的真实批准与补充

- 用户回复“批准第二次真实生成”，已接受为对当前绛绣·戏韵、写实风格、第二次单模型的单次批准，不机械要求重说完整短语。
- 用户声明已取得本图比赛公开展示、上传Neural4D及3D衍生处理许可；来源补充为“百度公开数据”。这是用户权限声明，不是独立版权审计；具体作者/原链接仍未提供，不自动取得商用销售或公开模型再分发许可。
- 用户确认“账户报价30积分，最高30积分”。用于当前standard、500000面、带材质、modelCount=1的单次费用确认；尚未请求余额或发生扣费。
- 用户允许一次现有Agent流程，为原创候选补齐正式角色结果，再由用户确认。

上述原文分别保存在 [生成批准](../prompts/phase-04/18-second-model-user-approval.txt)、[许可及Agent授权](../prompts/phase-04/19-second-image-permission-and-agent-reply.txt)、[当前报价与最高消耗](../prompts/phase-04/20-second-account-credit-limit-reply.txt)。不会将用户声明改写成供应商正式报价、许可专家认证或后台已冻结批准。

## 2. 第一次实际Agent流程（历史失败保留）

通过已有本机 `/api/v1/agent/create` 单次提交，独占领取标记和固定幂等键保留。任务ID：`a2a43828-773f-4f81-8908-5ff762ced750`。

| 阶段 | 实际状态 |
|---|---|
| Planner | completed；1次真实DeepSeek调用 |
| Research | awaiting_confirmation / insufficient_evidence |
| Designer | pending，未调用 |
| Culture Reviewer | pending，未调用 |
| 完整角色JSON | 无 |
| 人工接受资格 | canAccept=false，不可代用户确认 |

规划输出 `requiredEntities=["绛绣·戏韵","京剧","水袖"]`。尽管需求明确原创名和具体袖布形制不要求传统认证，模型仍将它们列为需资料支持的实体。本次真实查询“京剧行当入门分类与表演基础”得到1条有效依据、query uncertain=false；总研究状态因缺失原创名称和具体袖布实体而为uncertain。

因此这不是所有检索无结果，也不能拿一般行当证据认证服饰。研究按既有门禁停止，没有生成或伪造Designer/Reviewer结果、没有套用青旌将·霄羽作为新角色。已使用的Planner调用保留，费用保守估算0.00213512元。后续新工作流仍需用户额外允许，当前没有自动重跑。

原提交与真实结果见 [单次提交](../evidence/phase-04/modeling/02-realistic/second-showcase-agent-submit.json)、[实际暂停结果与用量](../evidence/phase-04/modeling/02-realistic/second-role-workflow-first-outcome.json)。

## 3. 已准备的修订

本节记录初稿时的待执行状态；用户后续已允许一次v2，实际结果见第6节。原任务与修订请求正文不改写。

[Agent需求修订稿v2](../prompts/phase-04/second-agent-brief-v2.md)只修订本次需求表达：明确本任务没有待证明存在性的传统实体，requiredEntities应为空；研究保留已经实际有结果的行当基础查询。服饰、配色和冠饰标原创，一般文化事实才引用真实资料。

初稿记录时尚未执行或验证。Phase 3代码、协议、资料、阈值和旧任务不修改；新流程若获允许会保留parentTaskId链路和实际失败历史，最多3次DeepSeek调用，仍在既有0.5元范围预算内，不自动重试。完成后新角色结果还需用户人审，第二次生成批准与30积分限制继续保留，不重复索取同一建模批准。

## 4. Neural4D当前事实与停止

输入原Hash仍 `0170077ef813f95b2e0da4666f0a7919078d0a811ac04d61613e69a31a621095`，冻结Prompt仍 `realistic_model_v1.0`。候选历史不可覆盖，不会为了新增许可声明修改旧版本或将未关联候选伪装成正式资产。

本轮Neural4D请求0、创建预留0、新建HTTP提交0、Neural4D新增扣费0。唯一第一次模型SUCCEEDED，实际30积分历史保留，全局仍 **1/3 used、2 remaining**。默认真实生成false，没有UNKNOWN或未完成建模任务。

当前只等待有效、已人工确认的正式角色结果。不会创建内部技术任务来绕过比赛主展示的正式资产要求，也不会提交第3次。实际提交前仍检查供应商当前协议、余额、已确认输入/参数/费用、全局配额、旧任务、锁与幂等；modelCount=1，失败/未知不退还、不自动重发。

## 5. 当前官方接口只读核对

公开文档GET已完成，没有使用Token或管理API。[当前图生3D文档](https://docs.neural4d.com/en/api-reference/image-to-3d/generate-model-with-image.md)说明standard支持100000～500000面，multipart二进制image要求image类型；modelCount默认4，项目必须明确发送1。现有standard/500000面/带材质预设在该范围内，不采用默认多模型或自动图像增强。

[余额文档](https://docs.neural4d.com/en/api-reference/account-and-validation/query-remaining-balance.md)的statusType和total_points字段与既有验证器对应；只读取文档，没有实际查询账户。文档Hash和取得时间见 [接口核对记录](../evidence/phase-04/modeling/02-realistic/current-second-api-doc-check.json)。本轮没有复制全文进仓库，也不将历史余额当作当前值。

## 6. 已获准v2的原任务恢复（2026-10-17）

用户实际回复 [“允许按修订稿再运行一次”](../prompts/phase-04/21-second-agent-v2-one-run-approval.txt) 后，2026-10-14 22:53:29（北京时间）只提交一次现有流程，任务 `ca7007e7-e535-4b1f-a9b6-1932f10e20b4`，保留parentTaskId与固定幂等键。22:53:35四阶段完成；用户中断后本次仅只读恢复该任务，没有重跑或重复付费。

Planner、Research、Designer、Reviewer均completed；审校pass、needsHumanReview=true。实际原创方案为绛绣·戏韵：红金长袍、花鸟式纹理、蓝银冠饰/红绒球/珠帘、白色长袖布、真人比例。外观全标creative，一般行当事实才引用真实fujian-roles片段。当前知识库交叉核对及四份产物Hash通过，旧任务产物Hash不变；Phase 3代码、协议、阈值和资料未修改。

实际DeepSeek三次共3727 Token，保守估算0.0090436元；最初暂停任务809 Token/0.00213512元仍单独保留，不混成一次调用。恢复读取新增LLM/Neural4D请求0、真实预留/创建0；Neural全局仍已用1/3、剩2，无UNKNOWN或在途建模任务。

任务停在`awaiting_confirmation`、sequence=11、canAccept=true；userConfirmed/publicationAllowed仍false。人审要求见 [具体新方案审核表](phase-04-second-role-v2-review.md)，准确JSON、费用与来源检查见 [结果](../evidence/phase-04/modeling/02-realistic/second-role-v2-result.json) 和 [恢复记录](../evidence/phase-04/modeling/02-realistic/second-role-workflow-v2-outcome.json)。需要用户确认的是这份首次展示的新角色结果，不重复要求同一建模批准。未进行资产确认、后台建模批准或第二次提交。

## 7. 用户接受角色与正式资产登记（2026-10-17）

用户实际回复 [“接受角色方案，保留原图与冻结Prompt继续”](../prompts/phase-04/22-second-role-human-acceptance.txt)。经既有TaskStore.confirm原子门禁登记，任务变为completed，userConfirmed/publicationAllowed=true；这是本次真实人审，不覆盖此前未接受的JSON快照。正式资产使用既有AssetService，不沿用第1次内部技术豁免。

- characterId：`29c8a710-2760-5079-a2c6-0b6d3f1067b1`
- assetId：`9e2b42e1-bbad-4a2f-ab1b-aeda18015dee`，realistic/styleVersion=1，比赛主展示。
- imageId：`0e1e8d8d-9ab9-43bf-9d36-a4d3c7c1414d`；实际上传规范化PNG Hash `7b8fb1a42bf79d0210c1571e65ae92d856fa73761d42d9cd044836764aad4d45`，与原JPEG解码像素一致。
- 原JPEG Hash仍 `0170077ef813f95b2e0da4666f0a7919078d0a811ac04d61613e69a31a621095`，原图未编辑。
- 冻结审核正文仍`realistic_model_v1.0`/`777afaa81b1e696d98dac00e695727e17c40f38983691786d52b69a40f62fad2`。
- 已接受角色的确定性技术适配Prompt独立Hash为 `441bcedf8a656275909bdab20d90b5f4b4c2cbc9cb2e1ea778ea5b828a91fcd8`；仅并列保存谱系，不替换原冻结Prompt。供应商实际只接收图像，无文本Prompt字段。

[登记结果](../evidence/phase-04/modeling/02-realistic/second-formal-asset-human-acceptance.json)和[人审后角色JSON](../evidence/phase-04/modeling/02-realistic/second-role-v2-human-accepted-result.json)保留。初次图片写入因沙箱禁止原子硬链接失败；使用获准环境权限后按同一原子写入机制完成，没有改成覆盖写入或放宽文件校验。Neural账本前后不变，未发出建模请求。

本次重新通过公开官方文档GET核对参数，文档Hash见 [当前接口核对](../evidence/phase-04/modeling/02-realistic/second-current-api-doc-check.json)。初次沙箱DNS失败保留于公开对话，获得网络权限后读取成功；没有用历史文档冒充当前检查。

固定参数：standard、500000面、disablePbr=0、onlyGenerateMesh=false、enableImageEnhancement=false、modelCount=1。用户账户报价与最高授权均30积分。**官方创建协议没有maxPrice字段：本地只能锁定参数/人工报价并验证余额，不能保证供应商外部硬扣费上限。**记录真实pointsDeducted；如异常超过30，停止后续操作并报告，不再建模。

发送前仍须实际取得独占管理锁、余额鉴权、固定账本原子预留及单次幂等发送权。当前已用1/3、剩2；无UNKNOWN或未完成模型。冠饰珠帘、袖布融合、手部和背面推测风险不变。仅对本次单模型发送，未知/失败不自动重试，不返还次数；成功但Viewer失败先修复原模型链路，不创建另一个模型。

## 8. 第2次实际提交与原任务查询

2026-10-17 13:09:56（北京时间）经固定ModelService完成SQLite原子预留、ATTEMPT_STARTED单次发送领取，HTTP200后保存唯一供应商任务：

- 项目attemptId/jobId：`d3367e96-02f9-453b-b331-6ed5b0ec03cd`
- Neural4D任务UUID：`8735f32e-097e-488c-962f-f11e64af7741`
- 后端批准ID：`bba8a00c-223a-4753-865f-85e6e50ed495`；仅用于此固定输入。
- 幂等键：`second-realistic-showcase-0170077e-v1`
- 单次modelCount=1，参数与第7节相同，实际带材质；创建响应实际扣费 **30积分**。
- 全局已用 **2/3，剩余1次**；第1次30积分历史保留，合计已记60积分。

[真实提交脱敏记录](../evidence/phase-04/modeling/02-realistic/second-real-submission.json)包含前后额度、冻结角色/文化来源/图片/Prompt Hash、独占锁和原子事件。先独立查询余额验证鉴权及本次30积分充足，公开材料只保存充足布尔值、不公开具体余额或密钥；私有env创建开关始终false，仅本次可信进程临时启用。

首次原任务查询 `codeStatus=1`、PROCESSING，见 [查询01](../evidence/phase-04/modeling/02-realistic/second-query-01.json)。这是已知进行中状态，不是UNKNOWN；没有重发或重新创建。后续仅允许查询/安全下载该UUID及本地Viewer验证。模型结果尚未取得前不标记技术PASS。

发送前两文件离线回归 **109 passed**，保留 [JUnit](../evidence/phase-04/modeling/02-realistic/second-send-offline-tests.xml) 与 [沙箱失败](../evidence/phase-04/modeling/02-realistic/second-send-offline-tests-sandbox-failure.xml)。失败根因为WinError5硬链接限制，获准权限后原测试通过，没有为测试放宽原子保存。另3项脱敏导出测试通过；测试没有使用真实配额。包装器静态复核发现重复启动可能覆盖提交状态文件，已在任何创建前改为仅本次独占领取标记的进程允许更新，原文件存在时拒绝发送且不覆盖；固定账本保护原样保留。
