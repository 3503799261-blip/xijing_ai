# Phase 5 WP2实际测试报告

日期：2026-10-19，时区Asia/Shanghai；JSON和JUnit时间戳按各自保存的UTC/时区读取。状态：测试完成，`PHASE_5_WP2_WAITING_ACCEPTANCE`。

## 1. 环境与范围

Windows，仓库`D:\京剧\京剧`，原venv Python3.11.1；Node v24.19.0；实际Google Chrome155.0.8059.84，Playwright驱动，桌面1920×1080、手机模拟390×844。复用现有依赖，没有安装或升级。Chrome使用SwiftShader是本次自动化渲染环境，不等于实体设备GPU测试。

本包只读取既有历史和模型，不发新创作/问答/确认/取消/建模。所有本机浏览器上下文拦截外部请求与非GET/HEAD请求，实际触发数均0；两组故障注入只改浏览器响应，不写生产数据。没有真实供应商API或今日余额探测。

## 2. 命令与原始结果

以下是实际执行命令；执行时helper位于仓库外`.runtime`，归档副本Hash见[archive-manifest.json](phase-05-wp2/archive-manifest.json)。执行已完成，不要覆盖旧输出；复现时使用新路径。全量pytest必须从仓库根、全新进程、收集前隔离，不能直接裸跑而接触生产全局应用。

```powershell
# 实际完整后端运行；同一已执行helper归档于phase-05-wp2/offline-bootstrap.py
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp2-offline-bootstrap.py --run-root D:\京剧\.runtime\phase5-wp2-offline-20261019-01 --junitxml D:\京剧\.runtime\phase5-wp2-offline-20261019-01\pytest.xml --basetemp D:\京剧\.runtime\phase5-wp2-offline-20261019-01\pytest-temp

# 已实际执行的前端检查；node为本机已有运行时
node scripts/phase5_wp2_frontend_test.mjs --output D:\京剧\.runtime\phase5-wp2-frontend-final.json
node scripts/phase2_frontend_test.mjs --output D:\京剧\.runtime\phase5-wp2-original-qa.json
node scripts/phase3_frontend_test.mjs --output D:\京剧\.runtime\phase5-wp2-original-agents.json
node scripts/phase4_frontend_test.mjs --output D:\京剧\.runtime\phase5-wp2-original-assets.json

# 服务启动完成后，真实GET + 只读SQLite对照
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp2-http-smoke.py --output D:\京剧\.runtime\phase5-wp2-http-smoke-03.json
# 最终提交版本服务重启后再次确认：
.\.venv\Scripts\python.exe D:\京剧\.runtime\phase5-wp2-http-smoke.py --output D:\京剧\.runtime\phase5-wp2-http-smoke-04.json

# XIJING_PLAYWRIGHT_PACKAGE指向本机已有playwright/package.json，不安装新包
node D:\京剧\.runtime\phase5-wp2-browser.mjs D:\京剧\.runtime\phase5-wp2-browser-final
node D:\京剧\.runtime\phase5-wp2-browser.mjs D:\京剧\.runtime\phase5-wp2-browser-verified
node D:\京剧\.runtime\phase5-wp2-model-browser.mjs
```

专项后端实际使用`backend/tests/test_agent_history.py --noconftest -p no:cacheprovider`、全新临时basetemp、`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`与不写pyc。最终23项2.82秒；首次Windows沙箱TestClient停滞被终止，其后在获准本机测试权限下完整复测。该23项已包含于698全量，不相加成721项。

隔离全量的Key为空、临时RAG/模型/账本、模块级app在收集前隔离、正式文件/SQLite访问审计、拒绝真实HTTP且只允许测试MockTransport；全量698通过、0失败/跳过/收集错误，81.67秒，1条既有StarletteDeprecationWarning，pytest与bootstrap均exit0。[隔离结果](phase-05-wp2/isolation-result.json)、[输出](phase-05-wp2/pytest-output.redacted.txt)、[JUnit](phase-05-wp2/pytest.xml)。JUnit仅脱敏机器名/个人目录，源Hash和归档Hash分别保存，不声称脱敏文件字节未变。

| 类别 | 通过 | 失败 | 跳过 | 实际证据 |
|---|---:|---:|---:|---|
| 全部隔离后端（含新23） | 698 | 0 | 0 | isolation-result、pytest.xml |
| 新前端DOM/Fetch专项 | 34 | 0 | 0 | [frontend-history](phase-05-wp2/frontend-history.json) |
| 原问答/Agent/资产前端 | 25/25/36 | 0 | 0 | [问答](phase-05-wp2/frontend-qa.json)、[Agent](phase-05-wp2/frontend-agents.json)、[资产](phase-05-wp2/frontend-assets.json) |
| 真实本机HTTP检查（最终单轮） | 190 | 0 | 0 | [40次GET](phase-05-wp2/http-attempt-04.json)；[前一成功轮](phase-05-wp2/http-attempt-03.json)独立保留 |
| 历史Chrome最终 | 6组 | 0 | 0 | [browser-verified](phase-05-wp2/browser-attempt-verified.json)；[前一成功轮](phase-05-wp2/browser-attempt-final.json)独立保留 |
| 两GLB与8页Chrome | 4组 | 0 | 未设跳过分支 | [existing-models-browser](phase-05-wp2/existing-models-browser.json) |

前端Node JSON未记录完整启动器绝对路径，不将通用`node`命令冒充额外运行；实际使用本机缓存Node。全量offline输出是测试桩/临时库证据，不是付费AI或真实模型生成证据。

## 3. 测试覆盖

新后端23项覆盖：正常列表/详情、稳定排序、分页/状态/类型/ID过滤、空数据、不存在、缺字段/表、SQLite错误、摘要不含大result、源字节不变、所有任务方法禁止调用、输出脱敏、引用/URL安全、资产ID/角色/风格一致、事件缺字段、WAL并发读快照。没有使用生产TaskStore来“验证只读”。

新前端34项覆盖：结构/返回版本及nullable、明确incomplete事件、只GET、空/404/服务/格式/网络/超时、手动恢复、旧响应取消和竞态、双向分页沿用提交条件、XSS文字/长字段、来源标签、正确资产ID和测试模型区分。Mock只在测试DOM/Fetch或浏览器路由层，不写正式库。

真实GET读取本机22任务，遍历列表和22份详情，对照只读SQLite，检查实际4阶段、来源、事件分页不重叠、404与422、参数稳定、摘要范围、绛绣写实关联、内部Q版不误链、no-store和额度。每个成功轮40次HTTP请求均为本机GET，不做RAG/LLM生成；为确认服务加载最终提交，重启后再次运行并单独保存，不把多轮相加称更多独立用例。

历史浏览器6组明确区分：

1. 真实本机：8页200、导航、图片、桌面不溢出。
2. 真实本机：手动加载、分页、completed=2筛选、绛绣详情/缺输入/人审/文化依据、只读模型链接与只读按钮。
3. 真实本机：不存在完整ID的空列表，手动改为真实ID恢复。
4. 真实本机手机模拟：390×844详情可读、无水平溢出；非实体手机。
5. 明确HTTP故障替身：503、异常结构，手动恢复真实GET；未存入数据库。
6. 明确响应替身：在真实详情的浏览器副本插入恶意HTML文字和超长中文；只显示文本，无img/script执行，无溢出，未改保存结果。

真实组无pageerror/阻断资源错误；故障组的预期503原样保留。不是“所有日志绝对零错误”。桌面/手机详情截图已实际查看，文件及Hash见[截图清单](phase-05-wp2/screenshot-manifest.json)。

两模型回归使用原兼容GLB，写实325.9°、内部Q版453.7°实际鼠标连续观察，缩放/Reset通过；绛绣切chibi为未生成、再切realistic恢复通过。8页实际打开，图片/导航/宽度通过。Loading/Error本次没有另做GLB故障注入，相关前端离线状态测试通过且Phase 4历史浏览器证据保留，不把旧浏览器结果称本轮实测。上下文关闭/模型切换时取消请求有保存，不冒称所有资源从未取消。

## 4. 真实失败、修复与复测

| 实际情况 | 处理 | 结果/证据 |
|---|---|---|
| 后端专项第一次沙箱TestClient停滞 | 终止，不计完整结果；获准本机测试权限后重新执行同一临时库专项 | 最终23通过；未扩大生产权限或放宽只读规则 |
| HTTP第一轮连接拒绝，默认启动进程未持续；第二轮启动尚未complete | 核对已启动的同一服务进程及日志，等待BGE本地载入，不再启动第二worker | [01](phase-05-wp2/http-attempt-01.json)、[02](phase-05-wp2/http-attempt-02.json)均0成功；03通过190项 |
| 浏览器第一轮3通过/3失败 | 选择器错误：导航本来带锚点；缺输入说明在折叠Agent内；空状态在提示区 | [01失败](phase-05-wp2/browser-attempt-01.json)保留，不改产品来迎合脚本 |
| 第二轮5通过/1失败 | 首个details实际是保存需求，改为明确`data-history-agent`展开后核对缺输入 | [02](phase-05-wp2/browser-attempt-02.json)保留；[03](phase-05-wp2/browser-attempt-03.json)及最终6/6 |
| 前后端联查发现产物版本number/null与缺step/event不一致 | 协议按真实整数/nullable及incomplete标记修复，加入测试 | 34项专项及真实22详情可读；没有补造缺失字段 |
| 分页返回首页会采用尚未提交的新筛选 | 分页沿用最近提交条件，保留输入供下次手动查询 | 双向分页专项通过 |
| 资产来源和完整性文案过宽 | 按保存origin标明测试/真实/未知；完整性仅指事件和阶段 | 独立前后端交叉审查及最终34项通过 |

失败日志与最终运行分别保留，不合并为一次“全绿”。本地路径查找/读取脚本纠正不称生产Bug。没有为凑Prompt链制造虚构故障。

## 5. 生产数据与模型不变性

执行前后同一只读辅助分别扫描18个完整业务表，比较schema与主键元数据、完整行规范化稳定排序Hash；除运行时间等证据元数据外，保护项全部相同。不是仅比较行数。

- Agent4表：22任务ID集合与状态、88阶段、59产物、194事件，角色/审校/人审JSON全部不变。
- 资产6表：角色/图片/模型/Prompt及关联全部不变；4条目录记录中仅2条真实模型。
- Neural4D5表：全局2/3余1、2 SUCCEEDED、未消费批准0、18条操作、历史60Credit均不变。
- 预算3表：LLM107条不变。
- 两兼容GLB、两供应商原件的Hash/大小/GLB头一致；详见[来源/原件最终after](phase-05-wp2/provenance-and-originals-after-final.json)。
- 7个非工坊HTML字节不变；about仅本包局部改造。

原始快照：[before](phase-05-wp2/before-state.json)、[最终after比较](phase-05-wp2/after-final-state.json)。最终after为北京时间17:54:42，晚于最终服务重启、HTTP及浏览器确认，先前after仍保留。额度真实GET返回`realEnabled=false`、`protocolVerified=false`，创建保持关闭。本包没有更改env、批准记录、配额或真实锁，没有发生产POST探针。完整隔离回归中的配额/并发用例只操作临时账本。

## 6. 未测试和限制

实体手机/实体双指未测试；本次手机仅Chrome模拟历史UI。没有付费DeepSeek/Neural4D、RAG生成、新Agent、真实创建并发或新角色生成。没有安装冷机环境、迁移私有成品或做公网/多用户权限验收。不存在历史字段不能恢复；非法/未知结构会显示格式错误，不能声称所有未来损坏记录都可部分展示。

截图保存在本地受控目录，含内部Q版图像不推入公开仓库；公开Git只保存Hash、脱敏结果及执行辅助。数据库、GLB、Key没有复制进Git。

产品变更`git diff --check`通过。执行过的offline-bootstrap证据副本逐字节保留，包含原文件结尾空白，归档diff检查仅提示该EOF空行；这是证据格式提示，不是测试失败或功能问题。没有为了消除提示而改写已执行证据字节。

[归档检查](phase-05-wp2/documentation-checks.json)实际236项通过、0失败：本地文档链接、归档Hash、JSON/JUnit、Prompt原文/公开快照、已知凭证与个人路径模式、WP1祖先及最终快照时序。该结果是文档/证据检查，不冒称236项应用测试；模式扫描也不等于对任意未知秘密的绝对保证。

结论：本包测试未发现未解决核心阻断。**外部API0、付费0、新建任务0、新模型0；已用2/3、剩1未使用，第三取消。** 等待WP2人工验收，不进入WP3。
