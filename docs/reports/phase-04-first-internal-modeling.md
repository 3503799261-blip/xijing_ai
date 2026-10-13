# Phase 4 · 第1次内部非公开Q版技术验证

日期：2026-10-13，Asia/Shanghai。独立分支`feature/phase4-neural4d`。本报告记录唯一一次实际模型创建，后续只查询原任务；没有授权第2/3次或进入Phase 5。

**最新恢复结论（2026-10-13）：PASS，限定于本次内部桌面技术验证；用户人工验收仍待进行。** 原任务模型已安全取得，经明确记录的本地纹理优化后通过真实Viewer加载、连续拖拽、缩放、重置及状态验证。全项目仍占用1/3，剩余2次，默认真实生成关闭。实体手机手势和完整Phase 4验收未通过，阶段仍PARTIAL。

以下第1～6节保留原提交及下载失败的历史停止快照；第7节起记录本次授权后的恢复，不能用旧快照描述当前文件状态。

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

## 7. 原任务恢复及MODEL_DOWNLOAD_BLOCKED根因

恢复授权原文见 [本次指令](../prompts/phase-04/12-first-model-recovery-request.txt)。本次只允许原UUID结果查询、经后端安全校验下载、必要本地格式优化与验证。第4节旧停止点提出的手动获取选项不用于本次恢复；没有手动浏览器下载或关闭门禁。

实际鉴权查询返回`codeStatus=0`，`modelUrl`是HTTPS临时签名GLB，实际host为 **cos.neural4d.com**。旧`Neural4DProvider.download()`白名单只有 **cos.zmkj.com**，因此在发出下载HTTP之前拒绝；不是Neural4D建模错误、链接过期、Content-Type或私有IP触发的原错误。记录仅包含脱敏字段结构和目标摘要，不保存签名URL、路径、参数值或API Key。[诊断](../evidence/phase-04/modeling/01-chibi/recovery-01-diagnostic.json)

可信目标核验采用：已鉴权的原UUID结果直接返回该host；精确主机名处于官方`neural4d.com`域下；公开DNS地址；固定IP、原SNI的验证TLS握手成功，证书SAN覆盖`*.neural4d.com`和`neural4d.com`，TLS1.3。未找到官网对该CDN的独立文字列举，不把此项说成官网显式白名单；判断依据是本次实际API响应与证书身份。[TLS身份记录](../evidence/phase-04/modeling/01-chibi/recovery-02-tls-identity.json)

新共享下载器采用精确host白名单；每跳HTTPS、443、无URL凭证、公开IP及数值TCP目标固定、原Host/SNI及证书校验；核对实际peer。禁用代理、Cookie/Authorization转发、连接重试和自动跳转，手动逐跳最多2次；总90秒、分项10/20秒、50MiB上限、Content-Type/Content-Length/压缩检查。下载任务上下文抑制会打印签名URL或Location的HTTP库日志，其他请求日志保持。恢复入口临时仅允许`cos.neural4d.com`，没有扩大私有配置或提供任意URL下载入口。

实际两次下载均HTTP200、`application/octet-stream`、**26,600,184字节**、**无重定向**、`dnsPinned=true`。第一次安全传输完成后被原格式门禁拒绝，未登记可用文件；随后同一安全路径保存不可覆盖的私有待验证Hash快照，禁止直接对外提供。没有新建、付费转换或自动重试循环。[第一次格式停止](../evidence/phase-04/modeling/01-chibi/recovery-05-original-result.json)、[受控快照](../evidence/phase-04/modeling/01-chibi/recovery-06-quarantined-result.json)

## 8. GLB原始格式、优化及资产关联

原文件是完整GLB2.0，声明长度与实际一致、无外部URI、无压缩必需扩展；两张内嵌纹理为实际JPEG和PNG，但JPEG被供应商声明为`image/jpg`。两图各4096×4096，单图16,777,216像素及总33,554,432像素超过现有16,000,000/32,000,000门禁。[格式诊断](../evidence/phase-04/modeling/01-chibi/recovery-07-glb-format-diagnostic.json)

没有放宽校验器。固定原Hash的纯本地转换将MIME规范化为`image/jpeg`，两图各缩为2048×2048，清除图像元信息并保留PNG/JPEG、UV、材质、场景和全部几何bufferView字节。输出仍需重新通过原`validate_glb()`；几何不重新生成，贴图分辨率与JPEG编码有变化，不能宣称与供应商原文件逐字节一致。原文件一直保留在私有隔离目录。

| 项目 | 实际值 |
|---|---|
| 原文件SHA-256 | `8ef5de8a2f96fbbee9eea66737187e4a2087f88867830891a41464a473d47885` |
| 原文件大小 | 26,600,184字节 |
| Viewer衍生GLB SHA-256 | `bf9c808c15dbf5464ee67df1cdb3f64f9b2c6b3cd4ee41ecb8a6470a0554654a` |
| Viewer文件大小 | 8,827,324字节，约8.42MiB |
| modelId | `3777a880-fc8c-4766-aade-948d20c6b8f0` |
| 几何/纹理 | 1网格、67,640顶点、99,997三角形、2图/2纹理/1材质 |
| 衍生纹理像素总数 | 8,388,608，原预算通过 |
| 来源关联 | 原供应商UUID、原候选2、原图片Hash、原冻结Prompt/信封Hash均保持 |
| 类型/可见性 | `neural4d_technical_test`、`chibi`、`internalUseOnly=true`、`visibility=internal` |

来源Hash、衍生Hash、每个几何和纹理Hash及优化版本保存在模型`validation.localConversion`与 [转换记录](../evidence/phase-04/modeling/01-chibi/recovery-08-local-texture-conversion.json)。原账本可靠恢复为SUCCEEDED，仍计第1次占用。临时UNKNOWN暂停解除仅表示原任务已核清；不代表用户验收或第二次授权，生成配置仍false。普通模型列表隐藏该资产，内部文件/Viewer限制本机访问。角色文化与公开/商用许可仍false，不冒称正式角色模型。

本校验是结构、资源范围及真实几何安全检查；**没有运行完整Khronos规范验证器**。实际浏览器加载也不替代完整规范认证。

## 9. 真实Viewer验证及质量观察

本机HTTP、Codex内置浏览器实测同一真实衍生GLB。私有Viewer：`http://127.0.0.1:8000/api/v1/assets/internal-models/3777a880-fc8c-4766-aade-948d20c6b8f0/viewer`。普通工坊列表继续不公开内部模型。

| 检查 | 实际结果 |
|---|---|
| 1920×1080桌面加载/材质 | Ready，实际模型及内嵌蓝白贴图可见 |
| 真实鼠标同向拖拽 | 第一段261.2°；继续同向达到**476.8°**，超过260°并完整跨360°；不是程序设置角度或往返相加 |
| 按钮缩放 | 实际相机半径3.598735→2.990195→3.541593（动画中采样），可放大/缩小 |
| 滚轮缩放 | 实际半径降至2.374087 |
| 重置 | 实际theta=0、phi=1.308997、radius=3.598735 |
| Loading/Ready | UI实际显示81%/94%加载，后进入Ready；状态记录`idle,loading,ready`。没有单独稳定Loading截图，不将Ready截图冒称Loading |
| Error | 受控临时移走该Hash文件触发本地404，显示明确错误、禁用交互并显示“重新加载原模型” |
| 文件恢复及重载 | finally/60秒超时兜底恢复原文件，Hash前后一致；主动重载同文件进入`loading,ready`，没有新任务或供应商请求 |
| 375×812手机宽度 | 无横向溢出，真实GLB仍加载；触摸模式按钮切换`touch-action=none`、提示及按下状态 |
| 实体手机拖拽/双指缩放 | **未执行**，没有真实触摸设备，不标通过 |
| 控制台 | 初版本地WASM解码器CSP错误已保留并修复；新页面最终warn/error为空。临时缺文件404是主动故障测试 |

内部页面CSP只增加`wasm-unsafe-eval`用于本地固定Viewer包，保留脚本来源self、JavaScript字符串eval禁用、远程连接阻断和本机访问约束。其范围依据 [MDN script-src说明](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/script-src#unsafe_webassembly_execution)，没有改下载安全策略。[真实交互及控制台记录](../evidence/phase-04/modeling/01-chibi/recovery-09-browser-interactions.json)

外观观察：蓝白衣饰、面部、头饰、毛笔均可辨认；小珠饰和头饰细件有简化/融合；毛笔及手袖交叠附近细节不宜作为精确拓扑交付依据。背部整体可连续观察，无明显大面积缺面，后脑与衣纹较正面简化。默认取景较紧，顶部冠饰边缘仍需用户复核；没有骨骼、动作、制作级拓扑或完整文化一致性验收结论。单图无法核验真实背面原貌。这些不阻断当前内部链路验证，但不能直接作为最终比赛或商用资产。

含模型的10张截图仅保存在`D:\京剧\.runtime\phase4-recovery-screenshots\`，不进入公开Git。清单、实际尺寸与Hash见 [截图元数据](../evidence/phase-04/modeling/01-chibi/recovery-13-private-screenshot-manifest.json)。用户人工审美/动作验收尚未发生，不代签。

## 10. 测试、失败保留及前三阶段回归

最终全后端 **652通过，49.00秒**，1条既有Starlette/TestClient弃用警告；工坊前端离线36通过，Phase 2/3前端离线各25通过。全部是明确离线Mock/夹具，与本次真实供应商恢复和浏览器证据分开。[最终JUnit](../evidence/phase-04/modeling/01-chibi/recovery-final-unit.xml)、[前端](../evidence/phase-04/modeling/01-chibi/recovery-frontend-offline.json)

实际失败均保留：

- 安全测试夹具用`content=`提前解码伪gzip导致1失败/53通过；改用原始异步流，让下载器在解码前检查压缩声明，门禁不放宽。[记录](../evidence/phase-04/modeling/01-chibi/recovery-03-offline-fixture-failure.xml)
- 2条旧回归仍期望恶意跳转泛化失败、任意自定义下载传输成功；117通过/2失败。更新为明确BLOCKED、拒绝替代DNS固定传输。[记录](../evidence/phase-04/modeling/01-chibi/recovery-04-old-contract-failures.xml)
- 原安全传输成功后真实纹理校验失败，原因及本地优化见第8节，原文件/失败JSON保留。
- 转换脚本第一次导入了错误模块的`canonical_hash`，启动ImportError，未动模型/账本；修正至既有`visual_prompt`模块，随后的纯本地转换成功。
- 转换专项首次测试夹具参数错误出现2失败/2 setup errors；纠正关键字后5项通过。缓存缺登记/缺文件/篡改Hash保护新增6项，恢复入口16项通过。[夹具失败](../evidence/phase-04/modeling/01-chibi/recovery-conversion-fixture-error.xml)
- Windows受限asyncio测试进程挂起，按已核实pytest进程身份结束并用隔离临时目录运行，没有结束其他任务或供应商进程，不将挂起写成通过。
- 静态路由HEAD检查得到405，保留试验；既有路由仅GET，改用浏览器实际GET重新验证。[HEAD记录](../evidence/phase-04/modeling/01-chibi/recovery-11-final-local-readback.json)

最终本机HTTP **14检查+62资源GET全部通过**：8页返回字节与本地文件相同、模型Hash/长度、默认生成关闭、隐藏内部模型及CSP验证。8页浏览器实际打开、导航/标题/图片检查；画廊首次立即采样有未加载图片，后复核28图全部加载，没有改旧页。[最终本地HTTP](../evidence/phase-04/modeling/01-chibi/recovery-12-final-local-readback.json)、[8页浏览器](../evidence/phase-04/modeling/01-chibi/recovery-10-eight-page-browser.json)

本轮没有修改8个HTML、文化CSS、Phase 2 RAG或Phase 3 Agent代码/数据协议；其他7文化页与Phase 3基线逐字节一致。没有付费问答回归；离线测试不能冒称新一轮真实DeepSeek联测。

复测命令（离线临时目录需在`.runtime/tests/`中新建唯一leaf并先核实路径，避免pytest自动清理实际资产）：

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp <新的隔离测试目录> --junitxml <测试结果XML>
node scripts/phase4_frontend_test.mjs --output <前端结果JSON>
node scripts/phase2_frontend_test.mjs --output <前端结果JSON>
node scripts/phase3_frontend_test.mjs --output <前端结果JSON>
```

两个恢复CLI仅针对本任务，前者可能发出原任务查询及下载，不作为普通自动化测试命令；后者固定原Hash且纯本地。服务管理锁不得绕过，未知结果仍停并人工核查。不要通过删除数据库、删除模型登记或重新建模修复文件问题。

## 11. 修改、Git及Prompt记录

真实修复提交：`2935155bc766752d5319d3529c3d6ee47f14cc4c`，`fix: safely recover original model with bounded HTTPS and local texture normalization`。没有压缩旧历史、合并main或推送。

- 下载层：新增`safe_model_download.py`；`neural4d.py`统一调用并保存脱敏逐跳操作日志；`neural_service.py`传递原job关联。
- 恢复工具：新增`recover_first_internal_model.py`（限定原UUID/账本/独占锁、覆盖禁止创建、失败后受控隔离快照、缓存成功必须验证文件）；`normalize_first_recovered_glb.py`（固定原Hash本地纹理优化）。`technical_test.py`保留原冻结技术关联并记录衍生溯源。
- Viewer：`model-viewer-adapter.js`新增统一metadata Error及实际状态历史；`internal-viewer.js`使用此入口；`api/assets.py`限定内部页WASM策略；没有改图像生成或双风格接口。
- 测试：新增安全下载、恢复入口及转换离线测试；扩展原Neural4D、内部访问和前端测试；新增限时恢复的原GLB缺失故障夹具。
- 文档/证据：本报告、阶段报告、计划、架构、README、Prompt导出及本次脱敏证据。文档归档提交Hash由实际Git读取，不预填虚构值。

真实公开对话由既有导出器保存，新增提取本次完整用户恢复指令。Key、签名URL、图像/模型二进制及隐藏推理不进入公开材料；截图仅记录元数据。导出是按时间的实际快照，后续记录不能被伪称已经导出。

归档检查发现早期公开对话中的**官网文档示例**带对象存储签名URL；不是本次模型的下载链接或用户API Key。已补导出器整条签名资源URL脱敏，并新增3项离线测试通过，保留原归档检查失败及最终检查。当前公开快照1039条，Hash按元数据核对；不删改既有Git历史、不伪造原对话。[导出脱敏测试](../evidence/phase-04/modeling/01-chibi/recovery-prompt-redaction.xml)

## 12. 费用、验收与第二次条件

本轮增量 **0次创建、3次原任务查询、2次经安全校验的资源下载**，另1次无HTTP的TLS身份核验；无付费转换、无图像/LLM调用，新增已记录Credit为0。全项目账本：创建1、查询6、下载2、余额/鉴权2，共11条真实HTTP记录；原创建实际扣费仍30积分。未另查余额，不宣称即时账户余额或其它程序账单。

**结论：PASS——原真实模型取得，当前内部桌面技术链路通过。** 计为第1次已使用及技术验证成功，不是第二个模型；用户人工验收PENDING。Phase 4总体仍PARTIAL，实体手机手势、正式文化角色、写实主展示及企业模型尚未完成。

可在用户验收第1次后申请第2次准备；不能立即发送。第二次仍须独立用户授权、已审校角色、许可和概念图确认、冻结Prompt/Hash、当前报价和配额/旧任务检查。剩余2次共享全项目，`modelCount=1`，未知不退款/不重建。当前默认生成false，没有自动批准、预约或发送第二次。恢复到此停止，等待用户人工验收。
