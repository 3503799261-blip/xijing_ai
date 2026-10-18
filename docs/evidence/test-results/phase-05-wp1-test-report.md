# Phase 5 WP1 · 实际测试报告

日期：2026-10-18（Asia/Shanghai）。范围：当前状态/运行文档校准及必要免费验证；不是WP4完整最终测试工作包。

## 1. 环境与边界

Windows、Python3.11.1、Node24.19.0、已安装Chrome155.0.8059.84；原有venv/BGE/索引与私有真实资产，无安装、升级或下载依赖。本地8000/127.0.0.1单worker提供前端及API。Chrome为headless WebGL/SwiftShader，1920×1080；本轮没有实体手机或CDP移动模拟。

执行前后只读快照：[before](phase-05-wp1/before-state.json)、[after](phase-05-wp1/after-state.json)。两者均保留：Neural4D已用2/3、剩1、两条SUCCEEDED、无待消费审批；操作累计18条，LLM累计107条。两个原始供应商文件及两个兼容GLB的SHA-256/大小/GLB头均核对，未覆盖。

没有POST聊天、Agent创建/确认/取消或任何Neural4D创建/查询/余额接口。唯一业务POST是**本地知识检索**与其空输入校验，真实BGE/Qdrant/SQLite执行，不调用LLM。浏览器只允许本地GET/HEAD，外域和写请求被拦截保护；实际此类尝试0。

## 2. 实际执行及数量

各表行是不同层次，可能重叠，不能相加称为独立端到端用例总数。历史Phase 4的675/52不拿来替代本轮结果。

| 实际执行 | 通过 | 失败 | 跳过 | 时间/说明 | 证据 |
|---|---:|---:|---:|---|---|
| 完整后端离线集合，最终run04 | 675 | 0 | 0 | pytest终端77.29秒，JUnit77.221秒；1条已有Starlette/httpx弃用警告 | [JUnit](phase-05-wp1/offline-final.xml)、[隔离/退出码](phase-05-wp1/offline-run-04-isolation-result.json)、[终端](phase-05-wp1/offline-run-04-pytest-output.redacted.txt) |
| 问答前端DOM/Fetch双桩及静态 | 25 | 0 | 0 | Node记录2026-10-18T13:09:43.008Z | [JSON](phase-05-wp1/phase2-frontend.json) |
| Agent前端DOM/Fetch双桩及静态 | 25 | 0 | 0 | 2026-10-18T13:09:42.754Z | [JSON](phase-05-wp1/phase3-frontend.json) |
| 资产/双风格前端双桩及静态 | 36 | 0 | 0 | 2026-10-18T13:09:42.740Z | [JSON](phase-05-wp1/phase4-frontend.json) |
| 本地HTTP/真实检索/历史结果 | 8 | 0 | 0 | 包含1题实际BGE检索及SQLite来源逐字段核对；不是新LLM问答 | [JSON](phase-05-wp1/local-smoke.json) |
| Chrome必要浏览器检查组 | 4 | 0 | 0 | 2026-10-18 21:03:20～21:03:58；4组含8页、写实、缺失风格/恢复、内部Q版 | [JSON](phase-05-wp1/browser-smoke.json) |
| 文档/配置/归档静态核对 | 68 | 0 | 0 | 含生产不变性、范围及敏感模式核对，另核验94个本地Markdown链接 | [JSON](phase-05-wp1/static-and-archive-check.json) |

JUnit timestamp原文为`2026-10-18T21:16:01.848080+08:00`；公开XML只对机器名脱敏，不改测试数量、状态、时间或节点。原XML在私有run04目录保留。日志与JSON的不同计时范围不混为一个精准耗时。

## 3. 后端离线隔离与真实失败

### 3.1 为什么不能直接称原pytest完全生产隔离

代码审查发现`backend/app/main.py`模块级`app=create_app()`会在测试收集import时初始化默认配置/库；原autouse夹具随后才替换应用工厂账本。原Mock测试并非故意调用供应商，但不能据此承诺导入期不读本机私有env、不触生产库。

本轮**不修改产品或既有测试代码**，使用独立进程[测试专用bootstrap](phase-05-wp1/offline-bootstrap.py)：收集前设置新空env、空Key、临时RAG/BGE/TEMP；仅本测试进程把config.WORKSPACE_ROOT指向临时workspace，核对main与Provider的固定canonical账本一致；禁真实httpx同步/异步transport，保留显式Mock；禁止读取生产私有配置/其他runtime、隔离目录外写入和SQLite连接。生产没有新增覆盖环境变量、重置或放宽配额入口。

### 3.2 实际失败与修复，不删除或算作成功

| 尝试 | 实际结果 | 原因/处理 |
|---|---|---|
| run01 | pytest退出3；0项执行，未通过 | pytest配置日志默认打开Windows空设备，被严格写入守卫拒绝。[原日志](phase-05-wp1/offline-run-01-pytest-output.redacted.txt)和[结果](phase-05-wp1/offline-run-01-isolation-result.json)保留。将pytest日志显式指定到隔离目录，没有放开空设备或生产路径 |
| run02 | bootstrap被守卫中断，未得到最终结果；**具体测试数量未知，不计通过** | 当时辅助未在异常时保存buffer；存在不完整JUnit。保存[实际中断说明](phase-05-wp1/offline-run-02-interrupted-result.json)和[残缺文件](phase-05-wp1/offline-run-02-incomplete-junit.txt)，没有倒推伪造精确堆栈 |
| run03 | 已观察675个call通过、0失败/跳过，但pytest未返回，整体退出3，**不算完成成功回归** | 新增脱敏诊断及finally后定位：JUnit收尾调用`platform.platform()`→Windows subprocess DEVNULL触发守卫。[完整诊断](phase-05-wp1/offline-run-03-isolation-result.json)保留；只在守卫启用前预缓存标准库OS元数据，避免收尾子进程，不放宽目录/网络规则 |
| run04 | pytest/辅助退出0，675通过、0失败/跳过，完整JUnit | 最终守卫拦截计数均0，空Key/临时路径/canonical一致/真实HTTP拒绝均有记录；没有跳过失败测试、修改产品或删测试 |

标准库平台元数据缓存不读取应用配置、Key、模型或账本，不是解除创建锁。以上为测试辅助/框架兼容问题，不伪称产品RAG或供应商失败。

## 4. 实际命令

### 4.1 全后端（最终成功尝试）

从仓库根执行，真实参数如下；实际运行的是私有原件，归档副本字节一致：

```powershell
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp1-offline-bootstrap.py --run-root D:\京剧\.runtime\phase5-wp1-offline-20261018-04 --junitxml D:\京剧\.runtime\phase5-wp1-offline-20261018-04\pytest.xml --basetemp D:\京剧\.runtime\phase5-wp1-offline-20261018-04\pytest-temp
```

辅助实际调用`pytest.main`完整`backend/tests`，参数为`-q --tb=short -p no:cacheprovider -o log_file=<隔离目录>/pytest.log --basetemp=<隔离目录>/pytest-temp --junitxml=<隔离目录>/pytest.xml`，没有`-k`筛选或跳过测试。复现须更换全新run-root，不能覆盖run01～04；可用README中已归档副本，前提是CWD为仓库根。

### 4.2 前端与本地验证

```powershell
node scripts/phase2_frontend_test.mjs --output docs/evidence/test-results/phase-05-wp1/phase2-frontend.json
node scripts/phase3_frontend_test.mjs --output docs/evidence/test-results/phase-05-wp1/phase3-frontend.json
node scripts/phase4_frontend_test.mjs --output docs/evidence/test-results/phase-05-wp1/phase4-frontend.json
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp1-local-smoke.py
node D:\京剧\.runtime\phase5-wp1-browser-smoke.mjs
```

Node实际使用本机既有bundled可执行文件，具体用户主目录工具路径不公开；版本/参数如上。[本地HTTP辅助](phase-05-wp1/local-smoke-harness.py)与[只读状态辅助](phase-05-wp1/state-readback-harness.py)归档。浏览器原脚本留本机，实际Hash `f890cb1dff61111b6a01affdb1a550f84c1de3746827a404a3d769ebeb7c96d9`见[截图/脚本清单](phase-05-wp1/browser-private-screenshot-manifest.json)，不公开含用户主目录的工具硬编码。

本地HTTP辅助首轮因`check(name, ..., name=角色名)`参数重名而未写最终报告；保留[失败说明](phase-05-wp1/local-smoke-initial-failure.json)。仅将辅助字段改为characterName后8项复测通过，没有修改业务或新增付费调用。

### 4.3 启动与浏览器失败

既有服务起初未运行，默认沙箱还拒绝本地套接字；后经允许的本地网络权限复核、确认uvicorn startup complete后health200。启动命令为既有`.venv`的`-m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1`，以Hidden方式启动，日志在本机`.runtime/phase5-wp1-server-*.log`。没有把启动前拒绝连接计作通过；[前置失败记录](phase-05-wp1/browser-preflight-failures.json)保留。

## 5. 浏览器与免费HTTP实际覆盖

- 8页均200，无坏图，工坊导航正确，1920px无横向溢出；未修改任何HTML/CSS/JS。
- 写实GLB Ready，modelId/Hash正确；鼠标一次323.6°、缩放/Reset通过。切Q版显示未生成、idle/modelId=null，再切回原写实模型；不混用内部Q版。
- 内部Q版GLB Ready，modelId/Hash正确；一次453.7°、缩放/Reset通过；内部/非公开提示保留。
- 创建按钮disabled；所有context的consoleErrors/pageErrors/httpErrors为0。切页7个媒体`ERR_ABORTED`、内部GLB1个`ERR_ABORTED`原样保留，不能写“网络事件全部为0”。
- 8项本地检查：health、capabilities、usage、12来源GET、1题真实BGE/Qdrant检索及canonical关联、空搜索422、真实历史任务status、已确认绛绣result。该任务没有重跑、人审没有再次提交。

4张截图在私有`.runtime/phase5-wp1-browser/`，公开Git仅保留Hash清单和脱敏JSON。模型/概念图及含图截图未复制到Git；原阶段失败/截图也未覆盖。

## 6. 静态检查与不变性

静态检查覆盖README链接/模块及脚本真实存在、关键参数与源码一致、环境字段/模板默认、当前状态、不含凭证/签名URL、产品/旧报告未改、前后HTML及4个模型文件Hash/台账相同。最终结果见[归档与静态核对](phase-05-wp1/static-and-archive-check.json)，这是文档/文件校验，不是额外真实模型测试。

提交前`git diff --cached --check`报告两处归档辅助的EOF空行提示（local-smoke-harness.py与offline-bootstrap.py）；为保留实际执行脚本副本字节，没有改写。两处均不涉及业务代码或测试失败，不将此命令记为零提示通过。

## 7. 明确未执行

- 新DeepSeek回答、真实新Agent、供应商鉴权/余额/价格/模型请求：禁止付费，本轮不执行；历史真实证据仍有效，但不是今日连通保证。
- 新模型、Neural4D创建拒绝探针、旧任务刷新/恢复/转换、历史初始化/配额修改：均不执行。
- 安装依赖、首次BGE下载、生产入库/重建、私有资产迁移：命令仅核对，未执行。
- 实体手机、CDP移动、Loading/Error故障注入、完整商业案例或交付：不在本次必要smoke中，留后续独立验收，不冒充WP4完成。

WP1本身以文档/流程校准、相关免费验证和如实记录为完成范围。最终状态为`PHASE_5_WP1_WAITING_ACCEPTANCE`，不进入WP2。
