# Phase 4真实AI协作证据

本目录保存当前会话公开记录的时间快照，不包含隐藏推理、系统指令或密钥。

- `00-original-user-request.txt`：最初检查点A需求原文。
- `01-final-architecture-revision.txt`：最终3次模型创建尝试限制原文。
- `02-approved-development-request.txt`：正式开发授权，真实建模逐次另行批准。
- `03-public-conversation.jsonl`：实际公开对话与匹配工具证据，源行号与时间保留。
- `04-export-metadata.json`：导出范围、文件Hash和真实快照时间。
- `06-dual-style-user-request.txt`：用户实际追加的“Phase 4双风格角色生成补充开发指令V1.0”原文。
- `07-three-attempt-modeling-plan-request.txt`：用户真实追加的Q版技术验证、写实主展示、企业案例顺序和逐次停止要求。

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

本地候选文件为 `D:\京剧\概念图.jpg`，用户指定Q版风格，600×750、87358字节，SHA-256为 `37aaa21e1c03d9bc35bcfc995002e42a200bad987b45766d3b1497b418472c3d`。来源与许可声明记录在 [候选图片元数据](../../evidence/test-results/phase4-concept-candidate.json)。

该记录是用户对小红书账号来源、非商业使用及修改权限的声明；独立许可证据、公开再分发和商用许可尚未核实。其 `sourceTaskId=null`、`imageAccepted=false`、`cultureAlignmentVerified=false`，状态为 `PENDING_CHARACTER_ASSOCIATION_AND_REVIEW`。它尚未关联并确认实际角色，不能称为通过文化审校的最终概念图，也没有创建模型。本索引没有复制该图片进公开仓库或把许可声明改成“已认证”。

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
