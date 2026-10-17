# 戏境 AI · Phase 4最终归档与验收

## 1. 结论与范围

日期：2026-10-17，Asia/Shanghai；原始测试JSON保留实际UTC时间。

**结论：PASS；按用户调整后的“两次真实模型”范围，Phase 4开发、技术验证及归档完成（COMPLETE）。检查点B最终阶段确认仍交由用户，不进入Phase 5。** 两个模型均已获用户人工验收；实体手机没有测试条件，明确标为未验证。

用户明确决定“两次建模效果都很好，不用第三次建模了”，随后要求最终免费回归与归档。[验收及取消原话](../prompts/phase-04/23-two-model-acceptance-third-cancelled.txt)、[完整收尾需求](../prompts/phase-04/24-final-archive-user-request.txt)已保存。第三次企业模型状态为 **CANCELLED_BY_USER / NOT_EXECUTED（用户决定不执行）**，没有任务ID、请求或费用，不记为失败。

全项目仍保留最多3次创建提交尝试的硬限制：**已用2/3，剩余1次未使用，累计实际60积分**。本轮供应商请求0、新建提交0、付费图像/LLM调用0；不重新下载、重新建模或改变历史次数。真实创建保持关闭，没有未消费审批。

## 2. 功能与验收清单

| 功能 | 最终状态及边界 |
|---|---|
| Phase 1～3继承 | 保留原8页、RAG、四Agent、人工确认和旧Git历史；本轮没有重新付费调用 |
| 角色及资产层 | 正式角色读取服务器权威JSON，关联来源、审校、图片和Prompt；内部技术模型单独登记 |
| Q版/写实双风格 | 独立模板、版本、图片与模型；同角色文化依据复用，切换仅本地读取 |
| 缺失风格资产 | 绛绣·戏韵没有Q版模型时明确提示未生成；不会拿第1个内部模型冒充该角色Q版 |
| 概念图 | 导入、解码、Hash、出处/许可、逐次人工确认已实现；平台图像生成Provider仍未接入 |
| Neural4D服务 | 两次实际单模型生成、原任务查询、安全下载、真实文件验证与恢复均有记录 |
| 全局额度保护 | SQLite原子预留、幂等、并发、重启、未知状态不退款/不重发、跨风格共享3次上限通过离线复测 |
| 创建门禁 | 私有配置false、能力接口imageToModel=false、前端创建按钮禁用、无未消费批准 |
| GLB Viewer | 两模型真实文件加载、鼠标/触摸模拟旋转、缩放、重置、Loading/Ready/Error与原文件恢复通过 |
| 企业模式 | 需求入口、场景/用途/边界记录保留；第三个真实企业模型取消，不宣称商业模型交付 |
| Git/Prompt/失败证据 | 完整保存，两次纹理兼容失败、修复前后文件与查询记录没有覆盖 |
| 实体手机 | **未验证**；CDP模拟结果不等同实体设备、Safari或移动GPU实测 |

## 3. 两次真实任务、费用与用途

| 项目 | 第1次 | 第2次 |
|---|---|---|
| 风格/用途 | chibi，内部非公开技术验证 | realistic，比赛主展示 |
| 角色 | 非正式技术资产；没有硬绑旧角色 | 绛绣·戏韵，原创京剧风格数字角色 |
| 供应商任务ID | `bb074c31-1905-45b6-b763-22d065ddc616` | `8735f32e-097e-488c-962f-f11e64af7741` |
| 本地attemptId | `b4da5f34-4681-420e-81b6-c1e3e447722e` | `d3367e96-02f9-453b-b331-6ed5b0ec03cd` |
| 真实modelId | `3777a880-fc8c-4766-aade-948d20c6b8f0` | `1fa0b519-caf4-4009-aec2-f20b0f9a3523` |
| 状态 | SUCCEEDED，技术及人工验收PASS | SUCCEEDED，技术及人工验收PASS |
| 参数 | standard，100000面，带材质，modelCount=1 | standard，500000面，带材质，modelCount=1 |
| 实际扣费 | 30积分 | 30积分 |
| 发布边界 | internalUseOnly=true，publicationAllowed=false | 用户声明允许比赛展示、供应商上传及3D衍生；不含商用销售或公开GLB再分发审计 |

费用来自实际创建响应的扣费记录，不以Mock报价代替。累计60积分不是本轮新增消费，也不把本地费用限制称作供应商账户硬扣费上限。[第1次报告](phase-04-first-internal-modeling.md)、[第2次执行报告](phase-04-second-model-execution.md)保留全部历史。

## 4. 文件完整性与资产谱系

| 模型文件 | 字节数 | SHA-256 |
|---|---:|---|
| 第1次供应商原GLB（隔离保留） | 26,600,184 | `8ef5de8a2f96fbbee9eea66737187e4a2087f88867830891a41464a473d47885` |
| 第1次Viewer兼容GLB | 8,827,324 | `bf9c808c15dbf5464ee67df1cdb3f64f9b2c6b3cd4ee41ecb8a6470a0554654a` |
| 第2次供应商原GLB（隔离保留） | 18,266,484 | `51fc687e0bde5fdb9074ba4560601057e17e9239f111fd2bc9e0d6601c26260e` |
| 第2次Viewer兼容GLB | 15,158,668 | `5a021ac6338009615e6ea232c5b9001eef6f4cc91d9d87c3eeeb5307526bdfd5` |

两份兼容模型在仓库外 `D:\京剧\.runtime\xijing-ai\assets\models\<SHA-256>.glb`，原文件在同级`recovery-quarantine`以Hash保存。原模型、候选图、含图截图不复制到公开Git仓库。两次均只做有精确Hash约束的本地JPEG MIME/2K纹理兼容处理，原几何及关联保留，没有重新生成模型。GLB头与文件长度、本地Hash本轮重新核对；既有结构/几何/纹理验证不是完整Khronos规范认证。

第1次刻意不关联正式characterId/assetId，沿用内部技术豁免；没有把其文化一致性改为通过。输入原图Hash为`9c737011a237de9fb589743e22b385a0c9611d33189c79b5940f8e1386047f0f`，审核Prompt为`candidate_bluewhite_review_v1`。

第2次完整链路：

- 四Agent源任务：`ca7007e7-e535-4b1f-a9b6-1932f10e20b4`，四步完成、文化审校pass且用户接受。
- characterId：`29c8a710-2760-5079-a2c6-0b6d3f1067b1`；assetId：`9e2b42e1-bbad-4a2f-ab1b-aeda18015dee`，写实v1。
- imageId：`0e1e8d8d-9ab9-43bf-9d36-a4d3c7c1414d`，已接受；原图SHA-256 `0170077ef813f95b2e0da4666f0a7919078d0a811ac04d61613e69a31a621095`，实际PNG输入Hash `7b8fb1a42bf79d0210c1571e65ae92d856fa73761d42d9cd044836764aad4d45`。
- 英文审核Prompt `realistic_model_v1.0`保留，正文Hash `777afaa81b1e696d98dac00e695727e17c40f38983691786d52b69a40f62fad2`；Style Adapter快照另有Hash，未覆盖英文冻结文本。普通图生3D请求只发送图片与参数，不声称供应商接收了文本Prompt。
- 来源结果、文化引用、图片和冻结任务信封Hash逐项匹配，详见[只读资产审计](../evidence/phase-04/final-acceptance/asset-ledger-readback.json)。一般行当知识有依据；外观是原创观察，不伪称历史人物或考据服饰。

## 5. 最新免费测试结果

环境：Windows，Python3.11.1；本轮Node24.19.0，实际Chrome155.0.8059.84。浏览器为安装的Chrome + headless WebGL/SwiftShader；1920×1080桌面和390×844 CDP手机模拟。全部浏览器请求限本地GET/HEAD，禁外域和写请求。

| 本轮实际执行 | 结果 | 证据 |
|---|---|---|
| 全后端离线回归（文案修复前） | **675通过，0失败，53.85秒，1依赖弃用警告** | [JUnit](../evidence/phase-04/final-acceptance/final-offline-tests.xml) |
| 一行内部Viewer文案修复后的相关回归 | **52通过，0失败，12.07秒，同一类警告**；与675有重叠，不相加为独立总数 | [JUnit](../evidence/phase-04/final-acceptance/internal-viewer-hint-tests.xml) |
| 问答/Agent/Phase4前端离线 | **25 / 25 / 36通过**，DOM双桩与静态检查 | [问答](../evidence/phase-04/final-acceptance/phase2-frontend-offline.json)、[Agent](../evidence/phase-04/final-acceptance/phase3-frontend-offline.json)、[资产](../evidence/phase-04/final-acceptance/phase4-frontend-offline.json) |
| 第2次GLB桌面实际拖拽 | **325.919°**连续同向观察，滚轮/按钮缩放/重置通过 | [Chrome原始结果](../evidence/phase-04/final-acceptance/browser-result.json) |
| 第2次GLB手机模拟 | **382.258°**连续观察，双指缩放及重置通过，390px无水平溢出 | 同上 |
| 第1次GLB桌面实际拖拽 | **453.7°**连续观察，滚轮/按钮缩放/重置通过 | 同上 |
| 第1次GLB手机模拟 | **300.7°**连续观察，双指缩放及重置通过 | 同上 |
| 双风格/缺失状态 | 写实→Q版显示未生成且清空模型，切回写实恢复原ID/Hash；不创建、不混用模型 | 同上 |
| 第2次三态与错误恢复 | 延迟原GLB观察Loading→Ready；故意拦截原文件显示Error，解除后重载同一模型Ready | 同上 |
| 第1次三态及修复文案实际复测 | Loading→Ready、Error→重载原文件Ready，过时“未验收”提示已消除 | [重启后Chrome结果](../evidence/phase-04/final-acceptance/post-hint-internal-browser.json) |
| 8页回归 | 8页HTTP200、图片正常、工坊导航可用、桌面无水平溢出；本轮8个HTML均与`60bfc38`一致 | [Chrome](../evidence/phase-04/final-acceptance/browser-result.json)、[文件/HTTP核对](../evidence/phase-04/final-acceptance/local-get-and-continuity.json) |
| 创建锁/并发/幂等/全局3次上限 | 全后端离线包含原子领取、同键/多进程竞争、跨风格上限、默认关闭、未知不返还等；生产锁只读非阻塞竞争被拒，未删除或改写 | [资产/锁核对](../evidence/phase-04/final-acceptance/asset-ledger-after-free-tests.json)及全量JUnit |
| 实际服务能力/资源 | imageToModel=false、conceptImage=false、modelViewer=true；5份媒体及第1模型各1024字节Range206 | [本机GET记录](../evidence/phase-04/final-acceptance/local-get-and-continuity.json) |

675项是明确MockTransport及隔离临时账本的本地测试，不是675次真实API调用。本轮没有重测付费RAG/Agent质量，未将离线测试冒充真实问答成果。真实模型成模依据是此前两次供应商任务，而非Mock或Duck。

正常模型/风格/页面场景JavaScript控制台与pageerror为0。故障注入各有预期的2条控制台错误，原始记录保留；切页取消7个媒体请求，内部页还捕获2次GLB `ERR_ABORTED`，不隐去这些记录。实际模型Ready且Hash一致，相关资源后续Range206可取，内部页重启后三态及恢复也通过。不能将故障注入描述为“全过程控制台零错误”。

## 6. 失败、修复与未完成测试

本轮真实发生并保留的情况：

1. 首次离线命令误写不存在的`test_phase4_first_recovery_conversion.py`，pytest未执行任何测试；[原始零测试XML](../evidence/phase-04/final-acceptance/initial-command-missing-test-file.xml)保留。纠正为全量`backend/tests`后675通过，不把错误命令计作通过。
2. 第一次后台启动因已有8000服务的子进程仍存活，遇到端口占用退出；随后核对现存服务健康。本地日志私有保留，没有重复启动并发模型服务。
3. 实际截图发现内部Viewer仍硬写“人工验收尚未完成”，与已接受事实冲突。最小改为“人工验收结论以项目阶段报告为准，本页仅供内部技术查看”，不硬编码任何模型验收结论、不改用途。52项回归与重启后Chrome三态通过；修复前后截图均保留。
4. 初次尝试读取owner锁内容被Windows拒绝；改为不读内容的只读非阻塞竞争，文件大小/mtime不变。证据只声明竞争被拒，不据此猜测进程身份。
5. 再执行审计时其“禁止覆盖旧证据”断言生效；改用新的`asset-ledger-after-free-tests.json`输出路径。旧证据未覆盖。

前两模型原有`MODEL_DOWNLOAD_BLOCKED`、纹理MIME/像素限制、受控本地转换及首次浏览器权限失败仍在原报告，不重写成从未失败。

未完成：实体手机、Safari/Firefox、多种真实移动GPU、骨骼/动画/游戏引擎集成、专业文化及独立版权审计。第三次取消是范围决定，不属于未解决Bug。图像生成Provider采用用户已批准的图片导入替代，未接入付费生成。

## 7. 额度、锁与费用最终核对

固定账本`D:\京剧\.runtime\neural4d-usage.sqlite3`：max=3、历史外部已核实0、两条SUCCEEDED、已用2、剩1、UNKNOWN/PENDING/在途0、未消费审批0。真实HTTP累计18条：创建2、查询10、下载3、鉴权3；费用累计60积分。LLM账本累计107条，本轮前后未增加。

[复测前只读快照](../evidence/phase-04/final-acceptance/asset-ledger-readback.json)和[复测后只读快照](../evidence/phase-04/final-acceptance/asset-ledger-after-free-tests.json)一致。SQLite以`mode=ro`及`query_only`打开；没有业务初始化、审批、预留、退款、改上限或配额写入。没有调用不可逆halt，也不声称对拥有本机管理员权限的人不可绕过。当前有效配置false、实时能力false、审批已用完，共同保持正常入口关闭；剩余1次不是任何未来自动调用授权。

## 8. 比赛演示与运行方式

在已有本地依赖、BGE、索引和私有资产已准备的环境运行：

```powershell
Set-Location -LiteralPath 'D:\京剧\京剧'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

端口已有本服务时直接打开页面，避免启动第二个worker。保持`NEURAL4D_GENERATION_ENABLED=false`，只查看已有文件无须生成Key、余额验证或供应商请求。RAG/Agent在线演示会另外产生文本API成本，本次未重新执行，不自动触发。

主展示建议依次呈现已保存的文化来源→四Agent及人工确认→角色/图片/Prompt版本→[绛绣·戏韵真实Viewer](http://127.0.0.1:8000/about.html?assetId=9e2b42e1-bbad-4a2f-ab1b-aeda18015dee#ai-workshop-model)→旋转/缩放/重置→切Q版展示诚实缺失状态→切回写实。企业入口展示需求记录及相同安全机制，不承诺第三模型。

第1次[内部技术Viewer](http://127.0.0.1:8000/api/v1/assets/internal-models/3777a880-fc8c-4766-aade-948d20c6b8f0/viewer)继续限定内部用途；不能仅因“最终资产”而自动扩展到公开视频、公开销售或模型再分发。第二图来源仍是用户声明“百度公开数据”，具体作者/原链接未独立核实；比赛展示前宜补齐授权凭证。

私有GLB不随Git分发，空环境应按[README](../../README.md)导入合法Duck验证Viewer；不能把它说成比赛角色。冷机依赖/模型首次下载没有十分钟承诺。

## 9. 截图、Prompt与复现证据

本轮实际截图17张位于[本机最终浏览器截图](../../../.runtime/phase4-final-browser/)；文案修复后三态4张位于[本机补充截图](../../../.runtime/phase4-final-internal-states/)。为保留既有内部用途和图片许可边界，仅本地保存，公开Git归档保存文件名、大小及SHA-256：[截图清单](../evidence/phase-04/final-acceptance/screenshot-manifest.json)。旧两轮截图未覆盖。

浏览器执行脚本[主复测](../evidence/phase-04/final-acceptance/browser-harness.mjs)、[内部三态补测](../evidence/phase-04/final-acceptance/internal-state-harness.mjs)随证据归档，固定模型ID、只允许本地GET/HEAD；不是模型生成脚本。后端命令为`python -m pytest backend/tests -q --basetemp <新的私有临时目录> --junitxml <新的结果文件>`；修复后仅重跑相关52项，未重复付费或无关测试。

[公开Prompt目录](../prompts/phase-04/README.md)保存原需求、逐次批准、原失败与真实公开对话；导出排除隐藏推理、系统内容、密钥及签名下载URL。原始用户话语与助手工程摘要分开，不补造未发生的对话。

## 10. 修改文件与Git归档

本轮唯一产品代码修改：`backend/app/assets/internal_viewer.py`一行过时文案；8个HTML、前端JS/CSS、角色JSON、供应商调用和额度逻辑均保持不变。导出工具`scripts/export_phase4_prompt.py`新增真实用户验收/最终收尾需求的选择器。

更新README、Phase4报告、两次/三次计划及第二次批准/费用/执行报告、Prompt索引与实际公开导出；新增本最终报告及`docs/evidence/phase-04/final-acceptance/`测试、只读审计、脚本和截图Hash清单。没有提交私有env、数据库、概念图或GLB。

| 实际Commit | 对应工作 |
|---|---|
| `c873c312b04f16cdc679c733684fae47f9caf805` | 已获授权第二次真实提交记录 |
| `2b08f3608d8667f456a02527b59e14b1720b8a8f` | 原模型纹理本地兼容，未重新生成 |
| `e72d237b5c6451267856ec2bd38bb55c20ce4945` | 已有资产只读验收链接 |
| `60bfc38a64d794982bb73a67ac5ee6bdaa1e29cf` | 第二模型技术验收与证据归档 |
| `251b90e85200ca513484e8e04405aa020f5f5713` | 本轮内部Viewer过时人工验收提示修复 |

本报告与最终证据以随后真实归档提交保存；包含该报告的提交无法在自身内容中写入自己的Hash，以`git log -1`及最终用户回复为准。[归档前核对](../evidence/phase-04/final-acceptance/archive-validation.json)记录实际审查时分支和状态；最终提交后再次核对工作区。保持`feature/phase4-neural4d`，不重写历史、不合并main、不推送。

## 11. 已知风险与检查点B停止

- 两模型的珠饰/细杆存在简化或融合；第1次毛笔与手袖、第2次手部/白袖布及鞋履可能连接或遮挡，背面由单图推测。用户已接受当前效果，但不把它们标为可直接生产的动画或游戏资产。
- 第2模型50万三角、约15.2MB，实体设备性能未测；移动模拟使用桌面GPU软件路径，不能外推手机帧率。
- 权利声明不等同独立版权审计；第1次仅内部使用，第2次没有商业销售/公开GLB再分发审计。
- 应用层3次保护不等于供应商账户总限额；不能因剩余1次而自动调用。

本阶段无已知阻断性交互Bug，已完成当前授权的归档工作。**停止在Phase 4检查点B，第三次不执行，不创建新模型，不进入Phase 5。** 后续仅在新的明确阶段指令下继续项目工作。
