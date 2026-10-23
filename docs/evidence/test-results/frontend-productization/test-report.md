# 前端产品化实际测试报告

执行日期：2026-10-23（Asia/Shanghai）。本轮仅本地免费测试；**没有调用真实DeepSeek或Neural4D**。浏览器中的聊天回答均由明确的隔离Fetch替身返回，不能据此声称真实LLM多轮联测通过。

实现说明见[阶段报告](../../../reports/frontend-productization.md)，原始需求与公开协作过程见[Prompt记录](../../../prompts/frontend-productization/README.md)。文件与Hash见[归档清单](archive-manifest.json)，统计口径见[summary.json](summary.json)。

## 环境与保护

- 项目：`D:\京剧\京剧`；起始HEAD `c224e91afd2bc4bcf314629e67c96dd773ced978`，原分支保持不变。
- 复用现有`.venv`，Node v24.19.0、Chrome 155.0.8059.86及已缓存Playwright；没有安装依赖。
- 实际服务由`scripts/run_local.py --no-browser`启动，单进程、127.0.0.1:8000；运行前`--check`通过35片段、2真实模型、已用2/3且创建关闭的检查。
- 启动器测试进程额外使用loopback-only网络审计；浏览器拦截非同源请求。真实页面/历史/模型回归仅放行GET/HEAD；普通聊天POST只在Fetch替身内处理，不到达真实后端。
- 离线后端测试在收集前清空密钥，使用临时资料、会话及配额目录；拒绝真实HTTP transport、真实私有资源访问。没有对真实数据库执行初始化或损坏测试。
- 最终服务已普通Ctrl+C停止，8000端口释放；没有结束未知进程。[停止记录](http/stop-final-02.json)

## 最终结果及统计口径

| 测试 | 实际结果 | 直接证据与边界 |
|---|---|---|
| 后端完整离线回归 | **797通过，0失败，0跳过**，134.31秒 | [隔离结果](backend/full-797-isolation.json)、[JUnit](backend/full-797-junit.xml)、[终端](backend/full-797-terminal.redacted.txt)；1条既有Starlette弃用警告 |
| 新聊天专项 | **43通过，0失败，0跳过**，7.50秒 | **已包含在797中，不再相加**；[专项结果](backend/chat-43-isolation.json)、[专项JUnit](backend/chat-43-junit.xml) |
| 前端问答及聊天 | **32通过，0失败** | [Node合同/服务/DOM替身](frontend/qa-final-32.json)，保留原服务安全检查 |
| Agent / 资产 / WP2档案 / WP3导览 | **25 / 42 / 34 / 34项通过，均0失败** | [Agent](frontend/agents-25.json)、[资产](frontend/assets-42.json)、[档案](frontend/history-34.json)、[导览](frontend/demo-34.json)；分别报告，不累加为独立项目测试总数 |
| 改造前导航与页面 | **24通过，0失败** | [before](browser/navigation-before.json)：8页×3视口 |
| 最终导航与页面 | **24通过，0失败** | [after-03](browser/navigation-final.json)：1920×1080、1024×768、390×844；8链接、图片、横向溢出和JS检查 |
| 聊天Chrome交互 | **13组通过，0失败** | [明确Mock替身](browser/mock-chat-final-13.json)，不是DeepSeek或真实持久化后端证据 |
| 原Agent历史Chrome | **6组通过，0失败** | [真实历史+明确HTTP故障夹具](browser/existing-agent-history-6.json)；分页、筛选、详情、文化审校、人审、关联、手机布局 |
| 次级入口、导览、备用及企业入口 | **5组通过，0失败** | [最终浏览器结果](browser/secondary-final-5.json)；全部只读，不创建任务 |
| 两个真实GLB桌面回归 | **4组通过，0失败** | [真实模型结果](browser/real-glb-desktop-4.json)，含8页、2模型及缺失风格恢复 |
| 两个真实GLB触摸回归 | **2模型通过，0失败** | [CDP触摸模拟](browser/real-glb-touch-2.json)；不等同实体手机 |
| 最终HTTP | **20通过，0失败** | [最终GET](http/final-get-20.json)：8页、健康、历史、配额、模型、来源、聊天空列表及内部Viewer；两GLB实际GET并校验SHA |
| 免费真实BGE/Qdrant检索 | **2问题通过，0失败** | [本地检索](http/free-local-retrieval.json)，各返回5条证据，未生成LLM回答 |

不同时间的复测、不同层的断言以及重复访问同一资源均不能相加为“独立测试总量”。本轮未执行真实付费模型调用。

## 聊天测试覆盖

后端43专项使用**临时目录中的真实JSON文件**和明确的检索/Provider替身，验证会话创建/列表/详情、分页、重开与应用重建恢复、UUID及参数校验、文件损坏不覆盖、原子保存、真实文件锁、跨会话隔离、上下文送入Provider、上下文检索改写、引用仅限当前证据、输入指令不提升权限、跨Origin拒绝、同幂等键恢复及未知状态不重放。最末4轮已完成对话作为受限上下文，不把失败或后来的回答倒灌进更早失败请求。

Chrome13组覆盖：空历史打开不POST；人工新建；发送加载和重复点击锁；追问携带原会话ID；消息顺序与内联来源；HTML按文本显示；两个会话与草稿隔离；刷新恢复；HTTP504/网络错误保留输入、手动同键重试、不自动POST；资料不足提示；未知结果不重试；历史503/404及分页失败恢复；390px键盘与9轮长对话、独立滚动及稳定输入区。Mock回答、引用与历史均明确含测试标签，未写入正式会话目录。

正式环境[会话只读检查](http/chat-empty-read.json)及最终GET返回真实空列表，读取前后`chat-conversations`目录均不存在；未凭空补造过去未持久化的聊天。

## 真实GLB与保留能力

- 写实桌面连续拖拽**349.9°**；Q版**453.7°**。对应的模型ID与SHA均匹配原资产记录。
- CDP触摸：写实**392.0°**、Q版**300.7°**；两者均通过触摸、双指缩放、滚轮、缩放按钮、重置、Loading/Ready/Error及原文件手动恢复。
- GLB错误由浏览器暂时返回503模拟，原文件没有改变；恢复只重读已有文件，没有调用供应商。
- 正式写实角色切换到尚无模型的Q版时显示“当前风格尚未生成3D模型”，切回恢复原写实资产，未用同一文件冒充两种生成结果。
- 原只读Agent档案实际读取22条历史，完成任务筛选为2条；“绛绣·戏韵”角色结果、文化审校、人审与资产链接均可恢复。企业入口保持需求入口和应用方向，没有提交企业任务或假称客户案例。

## 导航实测与截图

| 视口 | 外框before→after | 菜单before→after | 变化 |
|---|---|---|---|
| 1920×1080 | 1200→1120px | 675.80→634.80px | 菜单减少41px，约6.07%；外框减少80px，约6.67% |
| 1024×768 | 942.08→942.08px | 675.80→634.80px | 菜单同样减少41px，无截字 |
| 390×844 | 366.59→366.59px | 366.59→366.59px | 保持响应式宽度，完整8链接，无严重横向溢出 |

已保存17张可随本地测试材料检查的截图：6张before、6张after、5张明确Mock聊天截图。见[截图Hash与用途清单](screenshot-manifest.json)。受限的真实模型截图10张仅保存在私有测试目录，没有加入Git或公开分发。

- [工坊before桌面](screenshots/before/about-1920x1080.png) / [工坊after桌面](screenshots/after/about-1920x1080.png)
- [工坊before手机](screenshots/before/about-390x844.png) / [工坊after手机](screenshots/after/about-390x844.png)
- [Mock连续追问与引用](screenshots/mock/chat-desktop-context-references.png) / [Mock手机长对话](screenshots/mock/chat-mobile-long-thread.png)

## 发现的问题、失败与复测

1. 首版after中顶部能力已就绪，但底部“正在检查”滞留：历史加载锁错误影响就绪反馈。产品已区分历史加载与正在生成；after-02/03及Mock最终检查确认恢复，首版[证据仍保留](browser/navigation-after-01.json)。
2. 前端首次新测试**30通过、1失败**：测试将同步ID校验误写为`assert.rejects`，改为`assert.throws`；[原失败](frontend/qa-first-fixture-failure.json)保留，最终32/32。没有因此放宽产品校验。
3. 次级导览辅助首次**4通过、1失败**：已在第6步仍点击本就禁用的“跳最后”按钮。改成退至第5步再测试跳过；[原辅助失败](browser/secondary-first-helper-failure.json)保留，最终5/5。没有修改业务逻辑迁就测试。
4. 初版HTTP探针**18通过、2失败**：对只支持GET的模型文件路由使用HEAD得到405。未新增或放宽接口；改用实际GET并核验两个Hash，最终20/20。[原探针记录](http/head-method-first-attempt.json)保留。
5. 历史分页失败后的重读按钮恢复、历史读取不冒充实时服务就绪、仅最后失败轮允许同键重试等修复由合同/DOM/Chrome及后端专项回归覆盖。后端中间运行与递增的保护测试以[后端演进索引](backend/development-runs.json)记录；这些实际运行均通过，不能据此虚构红测或Bug发现历史。

正常三视口浏览器没有pageerror/consoleerror/HTTP资源错误。快速换页时已有音视频的预加载会记录`net::ERR_ABORTED`（页面离开取消），没有把它当作完整播放验证；本轮不声称音乐/视频完整播放已测。Mock网络/503场景的预期控制台错误明确属于故障注入。

## 数据与资源不变性

[业务before](invariants/business-before.json)与[业务final](invariants/business-final.json)对比8类保护字段全部一致：18业务表、22任务及ID、88步骤、59产物、194事件、角色JSON/审校/关联、109条LLM调用记录及配额台账未变。109是本轮实际基线，不沿用更早报告的107。

[物理before](invariants/physical-before.json)与[物理final](invariants/physical-final.json)对比全部一致：4个SQLite数据库及对象/sidecar、活动知识版本、5个版本资源文件、26个BGE模型文件、14个资产文件（含两个GLB、供应商原件及纹理）。其他7页HTML不变；只有`about.html`按本需求修改。根代理另将真实`.env`及73份文化HTML/媒体与2026-10-22既有基线比对，均一致；这是前一日基线，不冒称本轮开头新拍的env基线，未公开密钥或其Hash。见[独立核对](invariants/env-and-culture-prior-baseline.json)。

额度仍为**已用2/3、剩余1次不使用**；两个原任务SUCCEEDED、0未消耗授权、运营请求仍18条、历史扣费60积分，创建关闭。本轮付费API和Neural4D均0次。

复用的旧库存辅助中`clientDate`为历史固定标签；真实本轮日期以各文件`checkedAtUtc`为准，没有伪造旧日期。

## 实际执行命令

在项目目录执行，私有helper均写新输出，不覆盖历史证据。`node`指现有bundled Node；浏览器通过`XIJING_PLAYWRIGHT_PACKAGE`加载现有Playwright。没有运行pip/npm安装命令。

```powershell
.\.venv\Scripts\python.exe -B scripts/run_local.py --check
.\.venv\Scripts\python.exe -B D:\京剧\.runtime\productization-server-control.py --repo D:\京剧\京剧 --python D:\京剧\京剧\.venv\Scripts\python.exe --output D:\京剧\.runtime\productization-normal-final-02 --port 8000
node scripts/phase2_frontend_test.mjs --output D:\京剧\.runtime\productization-frontend-qa-final-03.json
node scripts/phase3_frontend_test.mjs --output D:\京剧\.runtime\productization-frontend-final-01\agents.json
node scripts/phase4_frontend_test.mjs --output D:\京剧\.runtime\productization-frontend-final-01\assets.json
node scripts/phase5_wp2_frontend_test.mjs --output D:\京剧\.runtime\productization-frontend-final-01\history.json
node scripts/phase5_wp3_frontend_test.mjs --output D:\京剧\.runtime\productization-frontend-final-01\demo.json
node D:\京剧\.runtime\productization-browser-nav.mjs D:\京剧\.runtime\productization-browser-after-03 after
node D:\京剧\.runtime\productization-chat-browser.mjs D:\京剧\.runtime\productization-mock-chat-browser-03
node docs/evidence/test-results/phase-05-wp2/history-browser-check.mjs D:\京剧\.runtime\productization-agent-history-browser-01
node D:\京剧\.runtime\productization-secondary-browser.mjs D:\京剧\.runtime\productization-secondary-browser-02
node D:\京剧\.runtime\phase5-wp4-model-browser.mjs D:\京剧\.runtime\productization-model-browser-01
node D:\京剧\.runtime\phase5-wp4-touch-browser.mjs D:\京剧\.runtime\productization-model-touch-01
.\.venv\Scripts\python.exe -B docs/evidence/test-results/phase-05-wp4-db-repair/phase5-wp4-stop-console.py 1400 D:\京剧\.runtime\productization-normal-final-02-stop.json 8000
.\.venv\Scripts\python.exe -B D:\京剧\.runtime\phase5-wp4-db-repair-inventory.py --output D:\京剧\.runtime\productization-physical-final.json --compare D:\京剧\.runtime\productization-physical-before.json
.\.venv\Scripts\python.exe -B D:\京剧\.runtime\phase5-wp4-state.py --output D:\京剧\.runtime\productization-state-final.json --compare D:\京剧\.runtime\productization-state-before.json
```

辅助源码见[helpers目录说明](helpers/README.md)。后端执行命令与空密钥/隔离边界见[backend运行索引](backend/development-runs.json)。HTTP20项与免费检索2项由Python stdlib `urllib.request`执行，原始问题、路径、响应、Hash及耗时均在对应JSON中；没有绕过Provider做真实模型请求。

## 未执行与限制

| 状态 | 项目 | 说明 |
|---|---|---|
| NOT_TESTED | 新多轮DeepSeek真实付费问答 | 未获得本轮付费测试授权；旧真实RAG报告不等同新增上下文代码实测 |
| NOT_TESTED | 实体手机 | 手机结果来自Chrome/CDP模拟 |
| NOT_TESTED | 跨机器/空白环境/真实ACL变更 | 本轮范围外，沿用已记录边界 |
| NOT_TESTED | 完整音视频播放 | 快速页面访问与静态资源检查不代表完整播放 |
| NOT_APPLICABLE | 模型HEAD | 生产模型文件路由只支持GET；实际GET与Viewer已通过 |
| NOT_APPLICABLE | 第三次建模 | 用户已取消，本轮绝不创建新任务 |

可免费验证的实现与回归均已完成。真实新增上下文LLM联测仍待单独授权，不应将本次离线与Mock通过写为真实DeepSeek已通过。最终Git提交及工作区状态由[阶段报告](../../../reports/frontend-productization.md)记录。
