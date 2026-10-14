# Phase 4真实AI协作证据

本目录保存当前会话公开记录的时间快照，不包含隐藏推理、系统指令或密钥。

当前最新状态（2026-10-14）：第1次内部技术模型已恢复并获用户人工验收，仍占全局1/3、剩2。第2次写实候选、一次文本文化审校与冻结Prompt准备完成，**WAITING_APPROVAL**，许可/正式角色/费用待确认；本轮Neural4D请求0。下文初版与失败记录是时间明确的历史，最新事实见 [Phase 4.2准备总结](../../reports/phase-04-realistic-preparation.md)。

- `00-original-user-request.txt`：最初检查点A需求原文。
- `01-final-architecture-revision.txt`：最终3次模型创建尝试限制原文。
- `02-approved-development-request.txt`：正式开发授权，真实建模逐次另行批准。
- `03-public-conversation.jsonl`：实际公开对话与匹配工具证据，源行号与时间保留。
- `04-export-metadata.json`：导出范围、文件Hash和真实快照时间。
- `06-dual-style-user-request.txt`：用户实际追加的“Phase 4双风格角色生成补充开发指令V1.0”原文。
- `07-three-attempt-modeling-plan-request.txt`：用户真实追加的Q版技术验证、写实主展示、企业案例顺序和逐次停止要求。
- `08-bluewhite-concept-update-request.txt`：同路径替换新蓝白概念图、重新Hash/审核/冻结、禁止提交模型的真实需求原文。
- `09-internal-technical-submission-approval.txt`：第1次内部非公开技术验证的实际逐次批准与文化匹配豁免。
- `10-internal-history-and-image-permission-reply.txt`：用户实际核查此前全项目0次，并确认此次图像上传及衍生处理权限。
- `11-internal-account-credit-quote.txt`：用户实际提供不带贴图20、带贴图30积分的账户报价。
- `12-first-model-recovery-request.txt`：用户真实授权仅恢复原任务、安全下载及本地验收。
- `13-first-model-human-acceptance.txt`：用户真实回复“批准，第一次非常好”。
- `14-realistic-showcase-preparation-request.txt`：第二次写实候选准备完整需求，明确禁止建模。
- `15-realistic-image-path-reply.txt`：用户实际指定概念图1。
- `16-realistic-source-and-one-review-authorization.txt`：用户仅声明百度公开资源，并单独允许一次400输出Token文本审校。
- `realistic-model-v1.md`：从不可覆盖候选快照逐字导出的待审Prompt，不是批准记录。

由 `scripts/export_phase4_prompt.py` 从明确指定的当前会话导出，后续开发结束再更新快照。导出器剔除非公开内容并脱敏常见凭证；比赛材料发布前仍需检查。

2026-10-11开始正式开发：保留Phase 3基线，创建独立Phase 4分支。当前未获得任何一次真实模型创建授权。历史调用次数等待用户核实，首次账本保持UNKNOWN。

真实失败记录：首次下载免费Viewer时受网络连接重置影响，未取得文件；使用已授权的网络权限后完成固定版本下载。首次脚本启动使用错误的虚拟环境路径，改用项目根 `.venv` 后运行。均非Neural4D API失败，没有占用真实建模次数。

2026-10-12三次计划补充：按真实用户新指令保存 [建模执行计划](../../reports/phase-04-real-modeling-plan.md) 和只读准备快照。用户回复“就用这个图片”和“仍待核查”，因此记录图片拟用于第1次Q版，但不把选择代写为角色/概念图最终接受；历史仍未知，没有单次真实建模授权。用户指出私有env没有填写项，检查确认字段确实缺失，追加空字段且保留旧配置；用户本地填写Key后执行一次真实只读余额鉴权，成功626.13毫秒，未提交模型或预留次数。公开证据不含Key或具体余额。

此次只读安全审查发现初版UNKNOWN保护仅阻止相同输入重建，跨角色/风格的新输入仍可预约，不能满足全局停止要求。保留修复前6项真实离线失败，新增全局暂停与事务内检查。后续测试环境错误（沙箱禁止硬链接、测试父目录未创建）亦另存原始JUnit，不改用不安全替换来制造通过。最终全量420通过、1既有弃用警告；只读余额脚本的5项Mock也真实通过。实际供应商鉴权与生成Mock证据分开保存，首个创建仍未就绪。

## 快照范围与阅读方法

上述原始文本、公开JSONL和导出元数据保留，不以本文的整理摘要替换。本次整理时读取的 `04-export-metadata.json` 快照时间为2026-10-11 12:52:44 UTC，包含237条公开记录；这是该次快照范围，不代表后续对话已经全部收录。之后更新的实际范围以元数据字段为准。后续导出应由原导出脚本基于真实会话更新并核对Hash，不能补写未发生的用户发言、模型回答、工具输出或提交。

下文为对实际实现、失败和测试文件的**工程摘要**，不是逐字对话或虚构用户修复Prompt。公开对话原文以JSONL中的源时间和源行号为准；单独的测试证据以各文件自己的执行时间和测试方式为准。截图、离线测试、真实本地HTTP、真实浏览器与供应商请求是不同证据，不能混称。

## 用户双风格补充与实际落地

需求原文见 [06-dual-style-user-request.txt](06-dual-style-user-request.txt)。本次补充仍属于Phase 4，核心要求是同一已审校京剧角色可选择“Q版卡通”和“写实国风”，共享文化研究依据，分别保存视觉Prompt、概念图和模型。两种风格共同受全项目3次新建模型HTTP提交尝试限制，风格切换不能绑定付费建模。

实际实现为 `styleMode='chibi'|'realistic'`、`styleVersion`、稳定 `characterId` 与独立 `assetId`。前端选择风格读取已登记资产；没有素材时显示未生成空态，不把独立合法GLB夹具复制成两个京剧角色模型。用户自由编辑Prompt保存新版本，旧版图片和模型保留；新草稿需现有Agent重新文化审校，不能由客户端声明解除门禁。

实现字段、API和模板版本详见 [资产与双风格架构说明](../../architecture/phase4-assets-and-styles.md)。个人/企业用途独立于视觉风格，不产生额外建模额度池。

## 已提供但尚待关联与核验的概念图

历史候选文件曾为 `D:\京剧\概念图.jpg`，用户指定Q版风格，600×750、87358字节，SHA-256为 `37aaa21e1c03d9bc35bcfc995002e42a200bad987b45766d3b1497b418472c3d`。原元数据保存在 [版本1历史记录](../../evidence/test-results/phase4-concept-candidate-v1.json)；当前原路径已被用户替换，不能继续将这段历史描述称为当前图片。

该记录是用户对小红书账号来源、非商业使用及修改权限的声明；独立许可证据、公开再分发和商用许可尚未核实。其 `sourceTaskId=null`、`imageAccepted=false`、`cultureAlignmentVerified=false`，状态为 `PENDING_CHARACTER_ASSOCIATION_AND_REVIEW`。它尚未关联并确认实际角色，不能称为通过文化审校的最终概念图，也没有创建模型。本索引没有复制该图片进公开仓库或把许可声明改成“已认证”。

## 新蓝白概念图的真实增量过程

用户替换同一原路径后，本轮实际读取1049×1398的新蓝白Q版图并计算原SHA-256 `9c737011a237de9fb589743e22b385a0c9611d33189c79b5940f8e1386047f0f`。用户仅回复“百度公开数据”，因此记录原文但不继承旧图许可，不猜测作者或已确认角色。真实角色JSON对照发现唯一已确认“青旌将·霄羽”与新图服饰、配色、头饰及毛笔不一致，保留未关联状态。

增量实现独立`concept_candidates`、不可覆盖图片快照、历史只保留元数据以及只读预览，不修改Phase 3协议或模型额度。候选版本2的原JPEG与无损PNG解码像素一致，没有改背景；`candidate_bluewhite_review_v1`是第一个实际待审草稿，绑定图像Hash，`approved=false`。没有虚构已批准Prompt、文化审校或供应商返回。

真实首轮离线48通过/1失败：测试要求显式禁止脚本的CSP声明，补齐后全量469通过。实际手机预览发现Prompt版本名横向溢出，增加标题换行和卡片最小宽度约束，保存修复前后证据，专项49通过，手机刷新后无溢出。实际本地HTTP14通过、前端离线35通过；本轮供应商调用0、配额预留0。证据、命令、风险、Hash和真实功能提交见 [本轮报告](../../reports/phase-04-bluewhite-candidate-review.md)。

新图与包含图片的本机截图没有复制到公开Git仓库；文化对照、脱敏Hash与测试记录可归档。真实原始对话仍由导出器保存，而不是以此摘要替代。

## 第1次内部技术验证的真实供应商调用

2026-10-13仅对这一次采用用户明确批准的内部技术豁免；旧角色文化审核不修改，候选仍未关联正式角色，文化/发布许可false。用户明确核实的历史0次按既有可信CLI一次性登记，不以本地0推断账户历史，也不重置账本。沿用同ModelService、固定UsageManager、原子预留、独占锁与Provider单次发送，私有配置默认关闭。

实际提交HTTP200，原任务UUID `bb074c31-1905-45b6-b763-22d065ddc616`，返回实际扣费30积分。前两次查询PROCESSING，第三次进入完成分支但模型URL被本地未核实下载域名门禁阻止；无下载HTTP、无GLB、无本次真实模型Viewer结果。立即停止，不重查、重试或创建，计占用1次、剩余2次且创建暂停。没有把首个提交成功写成完整3D技术验证成功。

开发中真实发现查询未知状态仅抛错而不触发全局暂停，修订后4个旧断言失败（4失败/127通过），保留失败记录并增强断言；修订专项131通过，内部集成52通过。真实创建与Mock供应商数据分开归档；[首次内部报告](../../reports/phase-04-first-internal-modeling.md)提供输入、授权、参数、实际费用、失败原因、提交与停止证据及未完成验收项。当前没有第2/3次批准，也不进入Phase 5。

## 真实失败、修复与证据索引

| 事项 | 实际发现与原因 | 实际修复或当前状态 | 证据 |
| --- | --- | --- | --- |
| GLB失败缓存与恢复 | 浏览器临时缺失合法测试GLB时正确进入Error；恢复真实文件后，同URL新组件仍复用失败加载缓存 | 正常加载保留受控原URL；只有用户主动重载才在先校验的同源同ID路径加内部缓存更新参数。没有自动重试、外链放宽或建模请求。真实浏览器后来恢复为Ready | [Error记录](../../evidence/test-results/phase4-browser-error.json)、[恢复记录](../../evidence/test-results/phase4-browser-recovery.json)、`viewer-load-error.jpg` / `viewer-recovered.jpg` |
| Phase 3已确认结果登记兼容 | 浏览器首次登记已有“青旌将·霄羽”任务失败，提示角色Schema无效。Phase 3文化JSON验证后附加 `execution` 和部分 `programmaticChecks`，直接重验纯文化Schema误拒绝这些服务端追踪字段 | 资产适配层单独识别并严格验证已知追踪字段，再验证文化JSON；未知字段仍拒绝，不修改旧任务或放松文化协议。增加真实旧结果脱敏导出的离线回归 | [首次浏览器失败](../../evidence/test-results/phase4-browser-style-first-failure.json)、`style-registration-before-fix.jpg`、`backend/tests/test_phase4_assets.py` |
| Windows同Hash文件并发发布 | 实际离线测试出现 `PermissionError: [WinError 5]`，4线程登记同一结果时反复 `os.replace` 同Hash文件，与Windows读取者冲突。该次结果为1失败/190通过 | 已有文件核对大小和Hash后复用；新文件flush/fsync后用同目录不覆盖硬链接原子发布，竞争失败方核对赢家并清理临时文件；损坏文件拒绝自动修复。对应4文件复测193通过 | [完整问题说明与真实工具摘录](../../evidence/test-results/phase4-windows-file-race.md)、`backend/tests/test_phase4_assets.py` |
| 费用漂移与旧版本确认失效 | 服务门禁检查发现未发送批准需要再次核对费用和风格/版本：批准后费用变化、旧批准缺少风格绑定、同分支出现新Prompt，都不能按旧确认发送 | 提交前核对当前费用与冻结批准、余额、角色/风格/图片Hash及最新版本；失败前不预留、不发送。已发送旧任务的幂等读取仍保留原来源 | `backend/tests/test_phase4_neural4d.py` 中费用变化、旧风格批准与新Prompt版本回归；这是离线Mock证据，不是供应商真实费用变化或真实建模失败 |
| HTTP检查工具错误断言 | 首轮实际本地HTTP为11通过/2失败；服务已返回 `status='ready'`，工具误读 `health.ready`，并把未知历史次数应为null错误期望为0 | 修正检查脚本字段与期望，服务协议保持不变；重跑13通过。保留原失败报告，不覆盖为通过 | [原失败报告](../../evidence/test-results/phase4-http-assets-before-harness-fix.json)、[修正后报告](../../evidence/test-results/phase4-http-assets.json) |
| 真实手机触摸与双指缩放 | 已完成窄视口浏览器布局、模型Ready、进入/退出触摸模式的检查；现有工具操作未证明真实手机手指拖动或双指缩放 | `physicalTouchDragVerified=false`、`pinchVerified=false`，继续作为待人工设备验收项；不能把离线控制检查或桌面鼠标称为手机触摸通过 | [手机窄视口记录](../../evidence/test-results/phase4-browser-mobile.json)、`viewer-mobile-375.jpg` |

GLB缓存原因可对照 [官方CachingGLTFLoader源码](https://raw.githubusercontent.com/google/model-viewer/master/packages/model-viewer/src/three-components/CachingGLTFLoader.ts)：资源按完整URL缓存，失败时生成空GLTF实例留在缓存。修复只变更明确用户重载的本地文件加载键，未修改vendor发行文件。

截图目录为 [docs/evidence/screenshots/phase-04](../../evidence/screenshots/phase-04)。实际鼠标旋转范围、缩放、加载/错误、8页回归以 [浏览器报告](../../evidence/test-results/phase4-browser-test-report.md) 及其时间明确的原始JSON为准；不同轮次测量不能合并成一次。

## 测试与付费调用边界

前端初版为33项离线检查；修复真实浏览器发现的失败缓存后增加2项，已保存的 [最终前端离线结果](../../evidence/test-results/phase4-frontend-offline.json) 为35通过/0失败（Node v24.15.0）。该报告明确声明使用测试替身与静态检查，不是实际GLB渲染、物理触摸或供应商联测。

后端离线测试使用明确的Agent容器、程序化模型、Mock HTTP与模拟Credit值。测试中的80等Credit数是夹具，不是已核实的Neural4D报价；不能将Mock成功任务写成真实模型。Windows并发问题报告的193项仅为指定4个Phase 4后端文件的那次结果，不替代最终全项目测试。

本轮真实Neural4D新建任务未获单独授权；本地账本未知历史保持锁定，不将未知历史写成0。用户已声明持有Key不等于当前本地配置、鉴权、费用或建模权限已验证。最终供应商连通、余额/费用、真实生成与下载、输入许可核验和手机手势仍需分别提供实际证据。

完整Git提交、最新公开会话导出、最后全量测试结果和检查点B状态由阶段报告汇总。本文不填造Commit Hash、不把待办写成完成，也不自动启动Phase 5。

## 第1次原模型恢复的真实演进

需求全文见 [12-first-model-recovery-request.txt](12-first-model-recovery-request.txt)。用户只授权原任务查询、安全下载修复及本地验证，明确不允许新建或清退次数。本次真实增量过程：

1. 读取原失败代码、日志、固定SQLite与Git状态；原次数1/3、UUID保持。
2. 实际鉴权查询定位host不匹配；验证公开DNS及原host/SNI证书，未打印签名URL。
3. 编写精确host/逐跳/固定DNS TCP/TLS/流式边界下载器及只恢复工具。离线gzip夹具和2条旧断言失败，保留并修正测试，不放宽门禁。
4. 原26.6MB GLB安全传输成功但纹理门禁拒绝；新增受控隔离保存，再查原任务并安全取回文件。诊断真实`image/jpg`和两张4K纹理。没有自动创建或调用付费格式转换。
5. 保留原Hash文件，仅固定来源的本地MIME规范化/2K纹理优化，原几何/场景保持，原验证器通过，原任务SUCCEEDED。脚本ImportError和转换夹具参数错误如实记录，没有伪造用户修复指令。
6. 真实Viewer鼠标476.8°、滚轮/按钮、重置；限时移走原文件触发Error，finally恢复同Hash后主动重载为Ready。控制台发现本地WASM CSP错误，限定内部页修复后新页面无warn/error；原错误不删除。
7. 全后端652离线通过，前端25+25+36通过；8页浏览器、14本机HTTP+62资源GET复核。手机宽度/触摸按钮通过，实体手机拖拽/双指缩放未测试。

以上为实际工程摘要，不是逐字用户对话。公开JSONL由真实session导出；脱敏API、Hash、失败JUnit和交互事实见 [恢复报告](../../reports/phase-04-first-internal-modeling.md)。含图截图、原/衍生模型仅本机私有。新增3原查询+2安全下载、创建0/增量Credit0，仍已用1/剩2。第1次桌面技术PASS、用户人工验收PENDING，Phase 4仍PARTIAL；没有第2次授权。

归档脱敏检查发现早期官方文档示例含签名对象URL，导出器已整体替换为脱敏标记，3项专项通过。本次实际模型下载URL从未写入日志/证据。最新公开快照为1039条，以`04-export-metadata.json`的时间、范围与文件Hash为准；源会话仍原样保留于用户本机，禁止公开原始含密钥会话。此处不宣称此快照含导出完成后的最终回复和文档Commit输出。

## 第1次真实模型用户验收

用户实际回复 **“批准，第一次非常好”**，已认定第1次内部技术验证人工验收通过，原文见 [13-first-model-human-acceptance.txt](13-first-model-human-acceptance.txt)。仅登记验收，不创建第二次、不推进Phase 5，也不把用户反馈变成未执行的手机手势或文化许可测试。上述1039条是上一导出快照；当前公开记录数与文件Hash以更新后的导出元数据为准。

## Phase 4.2写实准备的实际演进

用户指定 `D:\京剧\概念图1.jpg`，实际读到793×1400红金写实全身图。来源只声明“百度公开资源”，作者、许可与正式角色仍空，不能继承旧图内部技术许可。现有RAG的3次检索有真实服饰缺口，形成谨慎文字提案而不编造冠式、行当或历史人物。

按用户单独授权，仅调用现有文本文化Reviewer一次，400输出Token上限，无自动重试：真实输入1425、输出35、耗时1.3201秒、保守估算0.00262824元，pass且needsHumanReview=true。没有完整四Agent运行，没有把图片上传LLM或Neural4D。

通过既有CandidateCatalog独立存SECOND_REALISTIC_SHOWCASE版本1，原图/无损PNG像素一致，正式资产计数及Neural账本不变。冻结 `realistic_model_v1.0` 供审核，明确普通图生3D不发送该文本。新增准备工具单次领取保护与离线测试；首轮55、最终专项58通过。一次shell本机HTTP因WinError10013失败，权限恢复后只读重测8页HTTP200且字节一致；浏览器候选在窄/1920大屏正常。没有将测试替身称为真实审校，没有第二模型GLB或Viewer结果。

本轮Neural4D API0、预留0、创建0，仍1/3；第二次费用未确认。来源、图像许可、文化关联与批准flags均保持false。实际请求、返回、Hash、失败、测试与冻结材料见 [准备总结](../../reports/phase-04-realistic-preparation.md)和原始JSON/JUnit。当前公开导出为其时间快照，不承诺包含之后的最终回复或归档提交。
