# Phase 5 WP3实际测试报告

实施日期：2026-10-19～20（Asia/Shanghai）；交付2026-10-20。状态：`PHASE_5_WP3_WAITING_ACCEPTANCE`。仅本包导览/降级及相关回归，不是WP4最终完整验收。

## 1. 环境与费用隔离

Windows，原venv Python3.11.1，Node v24.19.0；10月20日Chrome实测155.0.8059.85，Playwright及SwiftShader，桌面1920×1080、窄屏模拟390×844；没有实体手机。复用已安装依赖、BGE/索引、现有任务和两个真实GLB，无安装/升级/下载模型。

全量后端在10月19日已用全新进程收集前隔离：空私有env/Key、临时RAG/模型/账本、生产文件及SQLite审计、禁止真实HTTP、仅允许明确MockTransport。10月20日继续本包时读取既有完整结果，不把它说成重新运行。所有测试时间以JSON/JUnit原始时间为准。

真实浏览器网络仅允许同源本地GET/HEAD。问答POST由更具体的浏览器路由直接fulfill/abort，明确列为SYNTHETIC，不转发后端；每个上下文记录syntheticRequests、blockedWrites及blockedExternal。最终真实拦截到的意外写/外域请求均0，不代表没有预期的模拟HTTP错误。

## 2. 实际运行与结果

| 执行 | 通过 | 失败 | 跳过 | 证据 |
|---|---:|---:|---:|---|
| 后端全量（10月19日） | 698 | 0 | 0 | [隔离结果](phase-05-wp3/isolation-result.json)、[JUnit](phase-05-wp3/pytest.xml)、[终端](phase-05-wp3/pytest-output.redacted.txt)；79.36秒，1条既有弃用警告 |
| 新导览DOM/Fetch（最终） | 34 | 0 | 0 | [退出分支最终复测](phase-05-wp3/demo-exit-final-34.json)，[前轮34通过](phase-05-wp3/demo-final-34.json)保留 |
| 问答/Agent前端（最终） | 25/25 | 0 | 无跳过分支 | [问答](phase-05-wp3/qa-final-25.json)、[Agent](phase-05-wp3/agents-final-25.json) |
| WP2历史前端 | 34 | 0 | 0 | [history-final-34](phase-05-wp3/history-final-34.json) |
| 资产/Viewer前端（最终） | 42 | 0 | 无跳过分支 | [assets-final-42](phase-05-wp3/assets-final-42.json)，原36场景保留，新增6 |
| 导览及故障Chrome（最终） | 8组 | 0 | 0 | [browser-final](phase-05-wp3/browser-attempt-final.json) |
| 8页/两真实GLB Chrome | 4组 | 0 | 无跳过分支 | [existing-models-browser](phase-05-wp3/existing-models-browser.json) |
| 18完整业务表/四原始兼容模型 | 全不变 | 0 | 不适用 | [最终after](phase-05-wp3/after-acceptance-state.json)、[原件比较](phase-05-wp3/provenance-and-originals-after-acceptance.json) |

这些层次有重叠，不相加宣传为新的独立端到端用例总数。JSON未设跳过分支的脚本不能靠删除用例跳过失败。

实际命令如下，Node使用本机已有运行时；执行helper在仓库外`.runtime`，归档副本及Hash见[archive-manifest](phase-05-wp3/archive-manifest.json)。复测使用全新输出路径，不能覆盖旧证据。普通启动与本轮测试分别看待：

```powershell
# 已完成的10月19日后端隔离进程；不要裸跑pytest触及模块级生产app
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp3-offline-bootstrap.py --run-root D:\京剧\.runtime\phase5-wp3-offline-20261019-01 --junitxml D:\京剧\.runtime\phase5-wp3-offline-20261019-01\pytest.xml --basetemp D:\京剧\.runtime\phase5-wp3-offline-20261019-01\pytest-temp

node scripts/phase5_wp3_frontend_test.mjs --output D:\京剧\.runtime\phase5-wp3-demo-final.json
# 检查中退出的提示收尾后，原34项再次复测：
node scripts/phase5_wp3_frontend_test.mjs --output D:\京剧\.runtime\phase5-wp3-demo-exit-final.json
node scripts/phase2_frontend_test.mjs --output D:\京剧\.runtime\phase5-wp3-qa-frontend-final.json
node scripts/phase3_frontend_test.mjs --output D:\京剧\.runtime\phase5-wp3-agents-frontend-final.json
node scripts/phase5_wp2_frontend_test.mjs --output D:\京剧\.runtime\phase5-wp3-history-frontend.json
node scripts/phase4_frontend_test.mjs --output D:\京剧\.runtime\phase5-wp3-assets-final-42-retest.json

# 使用已安装Playwright包，XIJING_PLAYWRIGHT_PACKAGE仅定位运行时，不安装依赖
node D:\京剧\.runtime\phase5-wp3-browser.mjs D:\京剧\.runtime\phase5-wp3-browser-final
node D:\京剧\.runtime\phase5-wp3-model-browser.mjs

# 真实业务只读快照，无app/env/HTTP导入
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp3-state.py --output D:\京剧\.runtime\phase5-wp3-invariants\after-acceptance-state.json --compare D:\京剧\.runtime\phase5-wp3-invariants\before-state.json
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp3-provenance.py --output D:\京剧\.runtime\phase5-wp3-invariants\provenance-and-originals-after-acceptance.json --compare D:\京剧\.runtime\phase5-wp3-invariants\provenance-and-originals-before.json
```

10月20日续接时本地服务不可连接，确认8000没有监听后才启动原venv的`uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1`，等待本地BGE载入和startup complete。没有杀未知进程、第二worker或删除锁。启动本身会初始化/恢复状态，不宣称纯只读；前后生产快照证实本包没有改变业务表。

## 3. 各层实际覆盖

新34项导览测试覆盖：初始化零请求、六步骤/前后跳过退出、原输入保持、明确目标动作才滚动、历史ID仅明确点击填写不查询、两模型精确身份及新页边界、内部Q回环限制、企业定位不提交、备用capture拦现有写按钮/非历史表单、允许历史/Viewer操作、退出不覆盖disabled、刷新退出、安全文本、响应式/焦点/减少动画。4诊断GET覆盖正常、空历史、知识缺失、401/403/404/429/503、格式异常、网络、真实AbortController缩时超时、手动恢复、错误不回显/旧结果不覆盖。诊断GET禁止重定向，绝不把本地配置当供应商实时验证。

资产42项保留原协议/样式分离/相机/限额/错误/重载/导入门禁36场景，新增：链接资产首读失败后同IDGET恢复、原Ready/图片保留且stale、重复手动重读合并/未知额度、归档费用与未来报价区别、风格查询失败未知/恢复、空任务不查询且不假加载。原问答25/Agent25继续验证输入/原标识保留、超时/网络/坏结构、防重复/不自动重跑；WP2历史34验证只读/错误/空/详情/关联。

最终Chrome8组：

1. **真实本地**六步骤、上/下/跳过/退出、目标链接、刷新默认退出、问题及需求保留；导览不发写请求。
2. **真实本地**备用模式捕获实际按钮事件，历史表单放行；手动4条件GET反映12资料/35片段、22任务、真实模型登记与创建关闭；真实绛绣JSON/文化审校可读。
3. **真实本地窄屏模拟**390×844导览无水平溢出，企业入口及“无真实企业客户”边界可见，不提交。
4. **HTTP故障替身→真实GET**健康503固定提示、无敏感哨兵回显；用户手动再查恢复。本组通过结果中的`error`字段保存的是预期故障文案，不是失败断言。
5. **7种问答POST响应替身**成功/504超时/断网/401/429/503/坏结构，各一次模拟POST，无自动重复；失败保留输入、结束等待、有中文错误。成功内容显著“非真实AI回答”，不作为RAG质量证据。
6. **历史GET替身→真实恢复**空列表不造记录，原任务详情404后手动读取原真实JSON/审校。
7. **资产GET替身→真实恢复**首读404没有自动重试，按钮再次只读同一ID成功；后续元数据失联标stale，已有Ready模型保留。
8. **真实GLB+文件HTTP故障替身**先Loading、模拟文件503后Error/提示，再手动重新加载原真实模型Ready，同模型ID，无新建模。

独立模型浏览器4组：实际8页导航/图片/宽度；写实GLB真实加载并连续鼠标321.6°、缩放/Reset；切无Q版显示未生成、切回原写实；内部Q版真实加载并连续453.7°、缩放/Reset、内部用途说明保留。创建按钮全程disabled。

手机本包只做布局模拟，未重新做触摸旋转/双指模拟，更未做实体手机；保留原Phase 4相关历史证据但不当本轮结果。GLB的Loading/Error在本包已实际注入和恢复，不是仅代码阅读。真实正常上下文没有阻断pageerror；故障组预期HTTP/网络/GLB错误及关闭页取消记录都保留，不能写成“控制台永远零错误”。

## 4. 保留的失败与修复过程

| 原结果 | 原因与处理 | 复测 |
|---|---|---|
| 导览32通过/1失败 | UI说新页“不会继承”，新测试精确断言“不继承”；统一明确新页边界，未改变保护行为 | [初次](phase-05-wp3/demo-initial-failure.json)→[33通过](phase-05-wp3/demo-retest-33.json)→[34通过](phase-05-wp3/demo-final-34.json)，增加目标动作不自动滚动测试 |
| 旧资产代码36通过/4失败 | 从Git基线代码内存导入运行新增回归，不替换磁盘产品/生产库；确证丢失原资产ID、快照/新文案等缺口 | [旧代码红灯](phase-05-wp3/assets-old-code-red.json)→40通过，后续独立审查加未知风格与空ID场景至42 |
| 资产空ID新增测试41通过/1失败 | DOM替身textContent不聚合子节点，断言读到空串；只修测试读取聚合，不改产品来迎合 | [失败](phase-05-wp3/assets-empty-stub-failure.json)→[42通过](phase-05-wp3/assets-final-42.json) |
| Agent24通过/1失败 | 原静态测试要求过期“等待单独授权”文本；实际已关闭/第三取消 | [失败](phase-05-wp3/agents-initial-failure.json)→[25通过](phase-05-wp3/agents-final-25.json)，加强disabled/第三取消断言，未删场景 |
| 浏览器5通过/3失败 | 测试填写隐藏面板、空列表替身缺来源note、从错误DOM位置取模型ID | [首轮](phase-05-wp3/browser-attempt-01.json)保留 |
| 浏览器7通过/1失败 | 第二轮模型ID仍从非权威dataset读；改为原有只读Viewer diagnostics | [第二轮](phase-05-wp3/browser-attempt-02.json)→[最终8通过](phase-05-wp3/browser-attempt-final.json)；产品模型一直成功恢复 |

真实产品修复与辅助脚本失败区分：资产首读ID丢失、失联快照/未知风格状态是业务UI问题；后几项为测试/旧文本断言问题，不伪装生产Bug。失败文件均独立保留，没有覆盖。完整后端698本包首轮已通过，不因前端修复重复跑或伪造更多后端执行次数。

## 5. 生产数据、模型与费用不变性

对照[before](phase-05-wp3/before-state.json)、跨日[continuation](phase-05-wp3/continuation-state.json)及最终[after](phase-05-wp3/after-acceptance-state.json)，18完整业务表schema、主键元数据、完整行规范化稳定排序Hash全部不变：Agent4、资产6、Neural4D5、预算3。不只比较数量。

22任务ID/状态、88阶段、59产物、194事件及角色JSON、审校、人审、关联记录不变。LLM仍107条，Neural4D仍18操作、60历史积分、2 SUCCEEDED、待消费批准0。全局2/3余1，第三用户取消，创建关闭；不清零或消耗剩余1次。4目录模型中2是真实成品、2是测试夹具，不混淆。

四文件Hash/大小/GLB头前后一致（[原件比较](phase-05-wp3/provenance-and-originals-after-acceptance.json)）：Q版兼容8,827,324字节、写实兼容15,158,668字节；供应商原件分别26,600,184与18,266,484字节。完整Hash保存在证据及原Phase 4报告。其余7个HTML字节未变。

本包真实外部API调用0、付费0、Neural4D调用/创建0。浏览器响应替身不是服务器或供应商调用；没有新Agent/确认/取消/资产注册/模型生成。没有改env、LLM预算、额度策略、模型或真实知识数据。

## 6. 截图、证据及未完成事项

[截图清单](phase-05-wp3/screenshot-manifest.json)记录16份实际本地PNG的路径/大小/Hash。截图位于工作区父目录`.runtime`，内部Q版和私有图像不上传公开Git；文档不把不存在的远端截图当公开成品。主代理已查看桌面/窄屏导览及Viewer Error/Ready真实截图。

JUnit仅脱敏机器名/个人目录，源Hash及归档Hash分别记录。执行过的offline-bootstrap保留原EOF空行以保持字节证据，归档diff仅该格式提示；产品diff检查通过。辅助副本用于追溯已执行版本，不是新增自动部署/生产数据恢复工具。

[文档/归档检查](phase-05-wp3/documentation-checks.json)实际296项通过、0失败，覆盖本地链接、归档/截图Hash、JSON/JUnit、Prompt范围/Hash、已知秘密和个人路径模式、WP1/WP2祖先及最终快照时间。它们不是296项应用测试，模式扫描也不是对任意未知秘密的绝对保证。

未测：实体手机、真实云API连通/余额/付费重试、冷机完整安装与10分钟保证、跨机器私有资产恢复、公网/多用户安全、视频录制/演示排练计时。备用需要本地后端与私有文件，只保护本页且不停止既有后台任务；新页/刷新退出。不能仅凭此声称全功能离线或真实外部API已恢复。

结论：范围内测试没有未解决核心阻断。状态为`PHASE_5_WP3_WAITING_ACCEPTANCE`，停止等待用户验收，不进入WP4。
