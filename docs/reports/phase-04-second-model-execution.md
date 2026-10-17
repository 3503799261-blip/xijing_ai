# 第二次写实建模执行记录

初始记录日期：2026-10-14；本次执行日期：2026-10-17。**当前结论：PASS（技术验证及用户模型人工验收）。** 用户明确回复“两次建模效果都很好，不用第三次建模了”，接受现有两次成果并取消第三次。原任务已完成、安全取得并经本地纹理兼容通过原验证，真实Chrome的桌面/手机模拟、三态、双风格及8页回归通过。实际只创建一次第2次模型、30积分，全项目已用2/3、剩1；默认关闭新建，不执行第三次或Phase 5。后文PENDING及暂停/失败/恢复描述保留为各时间点历史，当前归档以[最终验收报告](phase-04-final-acceptance.md)为准。[用户原话](../prompts/phase-04/23-two-model-acceptance-third-cancelled.txt)。

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

## 9. 原模型安全下载与真实格式阻断

第2/3次查询仍为PROCESSING；第4次查询返回`codeStatus=0`，供应商已完成。仅对该原任务下载一次，精确已核实host `cos.neural4d.com`、HTTPS、公网DNS固定、无重定向，HTTP200取得 **18,266,484字节**。没有记录完整签名URL或发送模型Key给下载CDN。[查询04及安全下载元数据](../evidence/phase-04/modeling/02-realistic/second-query-04.json)保留。

原文件SHA-256：`51fc687e0bde5fdb9074ba4560601057e17e9239f111fd2bc9e0d6601c26260e`，按Hash存于受控recovery-quarantine，未公开或伪装成已通过验证的模型。

原校验器实际报`MODEL_TEXTURE_INVALID`：两张内嵌真实JPEG的声明为非标准`image/jpg`；两张4096×4096纹理也分别超过现有单图1600万像素、合计3200万像素预算。[本地诊断](../evidence/phase-04/modeling/02-realistic/second-original-glb-diagnosis.json)确认GLB2头/总长度正确、1mesh、5个bufferView、纹理视图3和4。不是下载域名拒绝、过期链接、供应商建模失败或新建请求结果未知。

账本按既有门禁转PENDING_RECONCILIATION，跨风格新建暂停，次数仍2/3、剩1。已停止后续供应商查询；仅准备对确切原Hash的本地MIME规范化和2K纹理兼容，保留原始文件、场景和每个非纹理几何bufferView的Hash，不放宽验证器或调用付费转换/重新建模。转换完成并通过原验证及真实Viewer前，不标记技术PASS。

## 10. 本地兼容恢复与正式模型登记

新增固定范围工具 `backend/scripts/normalize_second_recovered_glb.py`，不是泛用上传处理器。它只接受第2次原Hash、18,266,484字节、已诊断两张4096 JPEG与5视图布局，绑定该任务/角色/资产/图片/冻结批准；显式禁用创建、查询和鉴权方法，要求默认创建关闭及独占owner锁。两张JPEG重采样至2048并改为`image/jpeg`，原三组非纹理bufferView逐个Hash相同，场景/节点/accessor/材质语义不变。

专项 **19 passed**（新第二次14项+首次转换5项），[JUnit](../evidence/phase-04/modeling/02-realistic/second-local-conversion-tests.xml)保留；包含固定Hash范围、几何与UV保持、禁止联网、临时正式角色登记和重复运行幂等。独立只读安全审查通过后，生产CLI只执行一次，没有运行第一次内部模型的豁免路径。

实际恢复于2026-10-17 13:20北京时间完成：[本地恢复证据](../evidence/phase-04/modeling/02-realistic/second-local-glb-recovery.json)。

| 项目 | 实际值 |
|---|---|
| 兼容版modelId | `1fa0b519-caf4-4009-aec2-f20b0f9a3523` |
| GLB字节数 | 15,158,668 |
| GLB SHA-256 | `5a021ac6338009615e6ea232c5b9001eef6f4cc91d9d87c3eeeb5307526bdfd5` |
| 三角面 / 顶点 | 500000 / 305024 |
| 网格 / 材质 / 内嵌图片 | 1 / 1 / 2 |
| 解码纹理像素 | 8,388,608 |
| 结构门禁 | xijing_glb_structural_v2有效、自包含、外部资源0；不是完整Khronos认证 |
| 原文件 | 隔离目录保持原Hash与长度，未覆盖 |
| 本地转换谱系Hash | `0934dbe65254eab9e7ade199a17fc1cb16f51e2fbecb66eff1bbfd9c1469999e` |
| 增量供应商请求 / 费用 | 0 / 0 |

正式登记保留原任务ID、引用Hash、角色sourceResultHash及图片/风格Prompt谱系；模型许可说明注明原文件Hash与本地兼容版本。原任务改SUCCEEDED，旧MODEL_TEXTURE_INVALID事件不删除，次数/18条真实HTTP记录均未增加；全局2/3、剩1，无待核查建模任务。创建开关保持false，没有第三次。

本地8000服务已以单worker运行，健康检查/真实模型元信息均HTTP200；模型Hash匹配，modelViewer=true、imageToModel=false，见 [HTTP只读结果](../evidence/phase-04/modeling/02-realistic/second-local-server-readback.json)。初次沙箱本地HTTP WinError10013保留，获准权限后只读请求成功。随后将使用真正Chrome测试，不能以服务200替代交互通过。

## 11. 真正Chrome浏览器验收

使用本机已安装 **Google Chrome155.0.8059.84**，Playwright驱动，headless/SwiftShader WebGL；桌面1920×1080，手机390×844触摸模拟。CUA浏览器工具两次报kernel assets路径不存在，未据此宣布浏览器不可测；使用已有捆绑Playwright，无安装新依赖。首次Chrome沙箱阻止本地HTTP，保存 [首轮失败](../evidence/phase-04/modeling/02-realistic/second-browser-sandbox-failure.json)，获准本地网络权限后实测通过。

| 实际检查 | 结果与证据 |
|---|---|
| 真实GLB加载 | Ready，modelId与`5a021ac6…bdfd5` Hash均与正式资产一致，不是Duck夹具 |
| 鼠标连续水平拖拽 | 单次实际拖拽 **325.920°**，49次user-interaction事件；非脚本设置相机 |
| 滚轮缩放 | 半径3.98983→3.13069 |
| 按钮缩放 | 放大至3.19187，缩小回3.98983 |
| Reset | 回0°/75°/初始半径 |
| 手机触摸模拟 | 单指同向两划累计 **382.657°**、123次真实交互事件；跨360°连续观察 |
| 手机双指模拟 | 两个同时接触点，半径3.98983→2.84145 |
| 手机布局 | 390px视口/390px页面，无横向溢出 |
| Loading→Ready | 只延迟原GLB响应，加载提示可见，随后真实文件Ready |
| Error与重载 | 仅对原GLB故障注入一次，明确Error/重载入口；解除后点击重载，GET原文件恢复同modelId/Hash |
| 双风格隔离 | 同角色切Q版：idle、无model-viewer、明确未生成；切回写实恢复原模型，未假用同一模型充当两种风格 |
| 8页回归 | 全部HTTP200、导航正常、无坏图、桌面无横溢出 |
| 正常控制台 | 桌面、手机、Loading及8页正常场景console/pageerror均0 |
| 付费与外域 | 测试拦截全部非GET/HEAD及外域；实际POST/供应商调用0，新建按钮保持禁用 |

完整实测分别见 [主套](../evidence/phase-04/modeling/02-realistic/second-browser-test-result.json)、[双风格](../evidence/phase-04/modeling/02-realistic/second-browser-style-switch-result.json)、[手机260°以上及Error恢复](../evidence/phase-04/modeling/02-realistic/second-browser-mobile-range-reload.json)。**手机为真实Chrome的CDP触摸模拟，尚未测试实体手机。** 程序设0/90/180/270°只用于质量截图，不计为用户拖拽证据。

实际执行的 [浏览器脚本快照](../evidence/phase-04/modeling/02-realistic/second-browser-harness.mjs)一并归档：使用已有捆绑Node/Playwright、本机Chrome及当前已登记模型；`--model=1fa0b519-caf4-4009-aec2-f20b0f9a3523`执行主套，另以`--only=style`、`--only=edge`、`--only=link`分次追加。脚本只有本地GET/HEAD，机器路径及资产ID固定，不是空白电脑通用安装脚本。重新测量须先为结果另存新版本，避免覆盖本机截图/原JSON；公开归档不包含模型二进制。

故障注入场景按预期保留2条console错误和原GLB的ERR_FAILED；8页切换取消未播完媒体时记录7条ERR_ABORTED，不删掉当作全零。对涉及5个原媒体追加Range读取，均HTTP206/1024字节，见 [媒体回归](../evidence/phase-04/modeling/02-realistic/second-media-range-regression.json)，不是资源404或破损。实体机性能、长期运行及其他浏览器没有用本轮Chrome结果替代。

## 12. 实际视觉观察与资产使用边界

已实际查看正面、90°侧面、180°背面及手机截图：人脸可辨认、站姿与真人比例保留；蓝银冠饰/红绒球、红金长袍纹样及白色袖布均可见，模型有可观察侧面和背面。

仍需人工接受的质量问题：冠饰珠饰/细杆有简化和融合，不能声称逐件复刻；手部仍部分受袖布遮挡，袖布与衣层部分连接；下摆/足部可见性受长袍限制。单张正面图没有背面参照，后部发型与纹样属于生成推测，不能认证为传统真实服制。未验证骨骼、动画、游戏级拓扑或商业资产规范；50万面/15.2MB在实体低性能手机上的体验仍待测。

所有含角色图像的截图及原/兼容GLB仅本机保存，不复制进公开Git仓库。截图目录：`D:\京剧\.runtime\second-realistic-screenshots\`，文件Hash清单另存最终归档核对；主要文件为`01-desktop-front.png`、`03-side-90.png`、`04-back-180.png`、`06-mobile-390x844.png`、`07-loading.png`、`08-error.png`、`12-mobile-over260.png`、`13-error-recovered-original.png`和`14-direct-review-link-empty-storage.png`。

用户提供的比赛展示/上传/衍生声明不扩大成商业销售或公开GLB再分发许可，来源作者和原URL仍未独立审计。技术PASS不替代本次模型艺术质量、文化或权利的用户验收。

## 13. 只读验收入口、代码与Git

[直接打开绛绣·戏韵写实模型](http://127.0.0.1:8000/about.html?assetId=9e2b42e1-bbad-4a2f-ab1b-aeda18015dee#ai-workshop-model)。本机服务保持运行，创建开关false。

实际工程改进：验收链接只用现有`validateAssetIdentifier`读取已登记assetId，优先于旧会话选择，走现有GET恢复，不触发注册/生成。36项现有前端离线检查通过，见 [结果](../evidence/phase-04/modeling/02-realistic/second-frontend-offline.json)；真实Chrome额外验证空存储、冲突存储、非法ID安全回退、非法且无存储4项，全部通过，见 [链接验证](../evidence/phase-04/modeling/02-realistic/second-browser-review-link.json)。没有为方便展示绕过人审或下载保护。

本轮实际代码变化为第二模型窄范围本地转换脚本、对应离线测试、前端5行只读链接支持，以及Prompt导出器识别本次真实人审原文；HTML/CSS、原文化资源、RAG/Agent业务代码未改。8页HTML与638028e逐字节一致，见 [只读连续性记录](../evidence/phase-04/modeling/02-realistic/second-post-submit-continuity.json)。

| 已发生提交 | 对应内容 |
|---|---|
| `638028e84253d200bd323dccd75ae6376c6d8d18` | v2实际完成结果、人审材料及原失败保留 |
| `c873c312b04f16cdc679c733684fae47f9caf805` | 新角色人审、正式资产、第二次实际授权提交/30积分及离线测试证据 |
| `2b08f3608d8667f456a02527b59e14b1720b8a8f` | 原模型纹理兼容工具、19项测试、原始失败与本地恢复 |
| `e72d237b5c6451267856ec2bd38bb55c20ce4945` | 已有资产只读验收链接、36项离线与4项浏览器验证 |

最终文档/浏览器归档提交由真实Git记录和最终回复提供，不预造自身Hash。不合并main、不推送、不压缩既有历史。公开Prompt22保存本次角色接受原文，JSONL由实际会话继续导出；新增工程摘要不伪称用户原始Prompt。

## 14. 费用、配额与停止结论

- 本次Neural4D实际新建1次、实际 **30积分**；加上第1次累计2次/60积分，剩 **1次全局机会**。失败/超时同样计入的固定3次限制原样保留。
- 本次余额验证1、创建1、原任务查询4、安全下载1，共7次供应商/资源HTTP操作；累计18条。公开文档GET、本地HTTP、Chrome和离线测试分别记录，不混成新建模型数。
- 原文件格式失败后只有本地处理；没有第二次创建、付费格式转换、DeepSeek新调用或额外积分。原/兼容文件、冻结Prompt、来源及人工接受链路保持可追溯。
- 原任务现SUCCEEDED，全项目无UNKNOWN/PENDING；真实生成仍默认关闭，本次批准已消费，不能复用创建另一个模型。
- **第2次技术验证PASS，等待用户人工验收。** 视觉质量与实体手机验证边界见上文；Phase 4整体仍PARTIAL。
- **停止，不执行第3次企业建模，不进入Phase 5。** 只有本次结果获人工审查、另行明确准备/审核/逐次授权后，才可讨论第3次；不因还有额度自动申请或消耗。

最终 [只读归档核对](../evidence/phase-04/modeling/02-realistic/second-final-readback.json)包含原/兼容GLB、14张本机截图Hash、8页HTML连续性、公开导出Hash、密钥/签名URL排除及最终账本状态。检查脚本最初使用错一个浏览器JSON字段名，读取实际结构后修正；未改变原测试结果、模型或产品规则。全部实际Git记录保留，最终停在本次模型人工验收前。
