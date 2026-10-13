# Phase 4 · 第1次内部非公开Q版技术验证

日期：2026-10-13，Asia/Shanghai。独立分支`feature/phase4-neural4d`。本报告记录唯一一次实际模型创建，后续只查询原任务；没有授权第2/3次或进入Phase 5。

## 1. 授权与范围

用户明确批准本次用途为**内部非公开技术验证**，允许忽略与既有“青旌将·霄羽”的文化匹配及最终公开资产适用性。用户随后明确核实全项目此前创建HTTP尝试为0次（包含全部工具、失败及超时），并确认允许此次图片上传和3D衍生处理。

原始批准、历史/输入许可确认及账户报价分别保存在 [批准原文](../prompts/phase-04/09-internal-technical-submission-approval.txt)、[核查回复](../prompts/phase-04/10-internal-history-and-image-permission-reply.txt)、[账户报价](../prompts/phase-04/11-internal-account-credit-quote.txt)。这是本次具体豁免，不放宽其他正式角色的文化门禁，也不提供商用或公开再分发许可。

用户提供带贴图30积分、不带贴图20积分的账户报价。本文不把会员每月积分数当作已核实余额，实际发送前通过供应商余额响应验证足够本次30积分，具体余额不写公开证据。

## 2. 实际输入与单次参数

| 项目 | 值 |
|---|---|
| 风格/用途 | `chibi` / 技术验证 |
| 候选/版本 | `fa0cd555-1daf-44a3-8825-ee6f5eb8b79e` / 2 |
| 原图Hash | `9c737011a237de9fb589743e22b385a0c9611d33189c79b5940f8e1386047f0f` |
| 实际上传PNG Hash | `879e5daa99ce26fd77ea6d28f4049e45cd414e9416c731b7ecbbbfeedeeec703` |
| 冻结Prompt | `candidate_bluewhite_review_v1` |
| Prompt Hash | `0648259709da555ba1c7d2070b2bb1c0317b2d505796e39518d4e7f48343b315` |
| 冻结信封Hash | `d023b5a3a3a3f65be6dd0ec0f9798b72cd3e105c99dfecd42c914bdd6a89d686` |
| 参数 | modelCount=1、mesh_quality=standard、faceNum=100000、disablePbr=0、onlyGenerateMesh=false、enableImageEnhancement=false |
| 文化角色身份 | characterId/assetId/sourceTaskId=null，非正式角色资产 |
| 可公开/文化审校 | publicationAllowed=false、cultureAlignmentVerified=false |

图像保持原外观及背景，PNG与原图解码RGB一致。发送使用独立Hash快照，发送前再次核对当前原路径Hash。文本Prompt用于图像意图与版本追溯；普通图生3D请求只上传图像与参数，不宣称供应商使用了该文本。

## 3. 保护与提交结果

以用户明确核实为依据，仅一次性登记原固定账本历史0，没有重置已有记录。发送前本地尝试0、未知0、剩余3。安全停止已核实身份的预览服务，取得原项目独占owner锁；经`ModelService → UsageManager.reserve → Provider.create_once`完成SQLite原子预留和发送权领取。私有.env始终保持真实生成关闭，仅该一次性进程临时启用，退出即恢复关闭。没有新增浏览器创建入口或Agent绕行路径。

实际提交成功：

- 北京时间2026-10-13 **17:30:43**取得发送权，**17:30:45**收到HTTP200及唯一供应商UUID。
- 本地attempt/job ID：`b4da5f34-4681-420e-81b6-c1e3e447722e`。
- Neural4D任务ID：`bb074c31-1905-45b6-b763-22d065ddc616`。
- 实际创建HTTP提交尝试：**1次**；供应商返回`pointsDeducted=30`，已保存实际扣费**30积分**。
- 全项目已占用1、剩余2；没有自动返还、重复创建或第2次批准。

见 [真实提交证据](../evidence/phase-04/modeling/01-chibi/internal-submission.json)、[真实冻结输入](../evidence/phase-04/modeling/01-chibi/internal-technical-frozen-input.json) 和 [脱敏操作日志](../evidence/phase-04/modeling/01-chibi/internal-supplier-request-log.json)。这些为真实供应商记录，与离线Mock分开。

## 4. 当前生成与文件状态

当前状态：**STOPPED / PENDING_RECONCILIATION**。前两次查询正常PROCESSING；北京时间17:36:11第三次查询进入`codeStatus=0`完成分支，但返回下载资源未通过本地安全门禁，抛出`MODEL_DOWNLOAD_BLOCKED`。本次只允许官方文档示例`cos.zmkj.com`，同一门禁还检查HTTPS、域名、端口及URL凭证；未保存签名URL及实际host，**错误码无法单独确认具体是哪项未通过**，需要继续核查原任务。没有发出模型下载HTTP请求、没有模型文件或GLB登记。

该完成分支由实际异常位置和代码路径确认；第三次公开记录只保存错误码，不声称保留了供应商原始完整响应。没有推断模型视觉质量或实际精确生成耗时。收到门禁错误后立即停止，**未重查、未重试下载、未重新创建**。

| 用户要求的结果 | 本次实际结论 |
|---|---|
| 提交成功 | 是，HTTP200及唯一UUID |
| 原供应商任务完成 | 第三次查询进入完成分支，文件未取得 |
| 模型文件/GLB Hash/模型ID | 未取得、未登记，不编造 |
| 项目Viewer加载 | 未运行本次模型，缺少文件 |
| 拖拽≥260°、缩放、重置 | 本次模型未测试；不能用旧Duck或Mock结果代替 |
| Loading/Ready/Error | 组件已有离线与旧GLB证据，本次模型未验收 |
| 头饰、毛笔、背面 | 未能观察，仍待真实模型检查 |
| 第1次使用 | 已计占用1次，实际扣费30积分 |
| 第1次成功技术闭环 | **尚未完成**；用户人工验收PENDING |

已保留 [第1次查询](../evidence/phase-04/modeling/01-chibi/internal-query-01.json)、[第2次查询](../evidence/phase-04/modeling/01-chibi/internal-query-02.json)、[停止记录](../evidence/phase-04/modeling/01-chibi/internal-query-03-stopped.json)及 [停止后只读账本](../evidence/phase-04/modeling/01-chibi/internal-final-stop-readback.json)。账本保留原UUID，创建全局暂停；已用1/剩余2，不返还、不归零。创建1、查询3、本轮余额1；此前余额1，共真实供应商请求6，没有下载或格式转换请求。

本地网页服务已恢复，默认生成关闭。停止后仅对127.0.0.1执行11项本地HTTP检查，8页字节完整、健康及暂停状态正常、普通模型列表未暴露内部模型；[结果](../evidence/phase-04/modeling/01-chibi/internal-local-site-after-stop.json)。这些没有供应商请求。

后续需人工核验并获取**原UUID**的模型下载资源，或由用户从供应商控制台取得原任务GLB再作本地导入/Viewer检查；此步骤须在本次停止报告后另获继续指示。不能开放任意下载域名、使用备用创建接口或发起第2次来解决下载问题。

## 5. 已实际执行的免费测试与修复

- 全部后端离线 **535通过**，45秒，1条既有Starlette/TestClient弃用警告。这一轮在最后查询保护修订前执行。
- 查询保护修订后，既有Neural4D服务和新候选技术层专项 **131通过**，20.23秒。
- 新内部集成专项 **52通过**，12.16秒：共享3次配额、一次发送、并发/幂等、跨正式/内部UNKNOWN暂停、4类查询异常、内部模型列表隐藏、本机文件/Viewer访问及正式Schema不能被候选绕过。
- 工坊前端离线 **35通过**。这些是离线/Mock证据，不是实际角色GLB或真实触摸验收。

实际发现并修复：查询超时/未知状态原来只抛错，旧任务仍为SUBMITTED或PROCESSING，不能触发全局暂停。现在持久化PENDING_RECONCILIATION、保留原UUID和次数；4条旧测试仍期望SUBMITTED导致4失败/127通过，保留 [失败JUnit](../evidence/phase-04/modeling/01-chibi/internal-query-old-expectation-failure.xml)，按新停止要求更新断言并增强全局暂停/UUID/占用检查后131项通过。

证据：[初次全量](../evidence/phase-04/modeling/01-chibi/internal-free-unit.xml)、[最终专项](../evidence/phase-04/modeling/01-chibi/internal-query-final.xml)、[内部集成](../evidence/phase-04/modeling/01-chibi/internal-integration.xml)、[前端离线](../evidence/phase-04/modeling/01-chibi/internal-free-frontend.json)。

功能真实提交 `374df8c4567c79c06f28f085d9b404f0b7e079b7`：`feat: scope internal technical generation to shared one-shot quota`。包含非正式技术信封、共享发送路径、只读本机Viewer和异常持久化保护；正式Phase 3协议与文化页面未修改。真实调用前已提交代码，不伪造提交时间或空提交。

## 6. 验收边界与停止条件

提交成功已经**计为第1次额度使用**。技术闭环未完成，报告状态**PARTIAL**。用户人工验收未发生，不代签通过。

待模型完成后检查：加载与真正GLB、连续拖拽≥260°、滚轮/按钮缩放、重置视角、Loading/Ready/Error及原文件恢复、头饰/毛笔/袖口/背面质量。真实手机手势仍须实际设备证据。模型、概念图及含图截图仅保留本机私有，不复制到公开Git仓库；公开文档只记录脱敏Hash与事实。

已按门禁错误后的立即停止要求结束供应商操作，等待用户审查；绝不自动进行第2/3次、合并main或启动Phase 5。Phase 4总体仍为PARTIAL。
