# 数字资产与3D工作台：实际测试报告

- 日期：2026-10-24（Asia/Shanghai）。
- 起始分支：`feature/phase5-competition-delivery`；起始HEAD：`15dc0fd63aabc18b79cf996b6827229dfc8ee91e`。提交状态由[本轮总报告](../../../reports/asset-workbench-layout.md)在归档后记录。
- 范围：三栏工作台、已有资产只读发现、真实GLB展示与必要回归。没有调用外部AI、图像或建模服务。
- 汇总：[summary.json](summary.json)。各组存在行为覆盖重叠、修复后重跑，不能相加为“项目独立测试总量”。12项后端专项已包含在809项全量中。

## 环境与隔离

复用现有项目`.venv`、Python依赖、Node v24.22.1、Chrome和已有Playwright，没有安装依赖。Chrome精确版本保存在[browser-final.json](browser-final.json)及[触摸结果](cdp-touch-real-glbs.json)中。

开始时8000端口由用户的VS Code调试进程PID 4020使用，未停止或替换。为测试新只读资产接口，在8877启动专用FastAPI：只实例化已有`AssetService(create=False)`和已有额度账本；不启动Runtime、Supervisor、ModelService，不打开第二份Qdrant/BGE，不执行恢复写入。非资产GET仅转发本机8000现有服务。中间件拒绝所有非GET/HEAD，浏览器同时拒绝非GET/HEAD及外部域名，测试进程网络审计阻止外部连接。

专用服务最终已正常Ctrl+C停止，8877端口关闭、目标进程退出：[停止结果](readonly-test-server-stop.json)。用户8000服务仍正常：[最终只读HTTP检查](existing-user-server-final.json)。用户需停止并重新运行现有VS Code“戏境 AI：一键运行”，让正常服务加载新增只读列表接口。未擅自重启用户进程。

## 实际结果

| 测试组 | 通过 | 失败 | 跳过 | 证据与范围 |
|---|---:|---:|---:|---|
| 后端全量隔离回归 | 809 | 0 | 0 | [隔离证明](backend-full-isolation.json)、[JUnit](backend-full-junit.xml)、[终端输出](backend-full-output.txt)。临时数据库、空密钥、真实HTTP拒绝。 |
| 资产只读接口专项 | 12 | 0 | 0 | [专项证明](backend-workbench-12-isolation.json)、[JUnit](backend-workbench-12-junit.xml)。是809项的子集。 |
| 现有前端五组 | 32／25／42／34／34 | 各0 | 各0 | [执行结果](frontend-existing-final.json)，问答、Agent、资产Viewer、历史、导览；显式DOM/Fetch测试双。 |
| 新工作台前端专项 | 22 | 0 | 0 | [22项结果](frontend-workbench-22.json)。测试双，不是真实模型验收。 |
| 工作台真实浏览器 | 7组 | 0 | 0 | [最终结果](browser-final.json)。三视口、右库切换、鼠标旋转、缩放重置、缺失风格、GLB与列表错误恢复。 |
| 真实缩略图／本地选图／切换一致性 | 7组 | 0 | 0 | [专项结果](local-preview-library-final.json)。本地1×1 PNG测试夹具未上传或保存。 |
| 两个真实GLB的手机触摸模拟 | 2组 | 0 | 0 | [CDP结果](cdp-touch-real-glbs.json)。触摸旋转、双指缩放、滚轮、按钮、重置、Error恢复。 |
| 8页×3视口 | 24 | 0 | 0 | [结果](eight-pages-three-viewports.json)。1920×1080、1024×768、390×844；导航、图片、无横溢出。 |
| 导览／只读档案／问答与企业入口 | 5组 | 0 | 0 | [最终结果](secondary-final.json)。真实历史读取、只读保护、免费条件检查。 |

布局中左侧为概念图、风格、折叠设置；中间为主Viewer；右侧为真实资产库。1920桌面三栏同时存在，1024保留收窄三栏，390按Viewer→资产库→操作区纵排。没有改变共用导航尺寸或七个文化页面。

## 真实模型验收

[HTTP字节检查](real-glb-http-bytes.json)确认两文件均为真实GLB v2，文件总长度完整，SHA-256与登记记录一致：

| 模型 | 字节 | SHA-256 | 本轮鼠标连续旋转 | 本轮CDP触摸连续旋转 |
|---|---:|---|---:|---:|
| Q版内部技术模型 | 8,827,324 | `bf9c808c15dbf5464ee67df1cdb3f64f9b2c6b3cd4ee41ecb8a6470a0554654a` | 459.5° | 322.7° |
| 写实“绛绣·戏韵” | 15,158,668 | `5a021ac6338009615e6ea232c5b9001eef6f4cc91d9d87c3eeeb5307526bdfd5` | 459.5° | 322.7° |

每次选择均核对实际Viewer的modelId、Hash、原受控文件URL、风格及选中条目。两者不是同一角色的两份风格资产：Q版仍是内部技术模型，未强加正式文化角色关联。没有模型的真实角色/风格显示空状态，不借用另一个模型。

双指缩放及鼠标/触摸记录来自实际`model-viewer`相机事件，真实几何加载未使用Mock。仅Error场景用浏览器响应双模拟原GLB请求503；恢复后重新读取同一原GLB，没有创建、替换或重新生成模型。加载、Ready、Error状态及手动恢复均实际观察。

实体手机：**NOT_TESTED**。不能将Chrome CDP模拟描述为实体手机验证。

## 测试中发现的问题与处理

1. **改造前首次读取失败**：Chrome报告`ERR_NO_BUFFER_SPACE`，等待Ready超时，见[原始失败](before-load-buffer-failure.json)。保留失败；第二次只读打开实际在三个视口均加载原写实GLB并取得改造前截图，见[复测](before-layout.json)。没有据此改动下载安全规则或模型。
2. **缺失风格测试等待过早**：首轮综合6组通过、1组失败，见[首轮结果](browser-first-attempt.json)。诊断证明旧modelId/src已清空，而异步查询仍处于“正在读取…尚待核实”，见[诊断](missing-style-wait-diagnostic.json)。修正测试，等待最终缺失状态，不把临时idle当作查询已完成。最终7组通过，没有伪造缺失模型。
3. **导览企业入口被新折叠区隐藏**：原辅助回归4组通过、1组失败，见[失败记录](secondary-before-enterprise-fix.json)。修复第6步用户主动定位动作：展开目标最近的`details`后执行原滚动；未设置企业值或发起提交。同五组复测全部通过。
4. **新增前端测试夹具不完整**：原18通过、2失败的结果保留于[初次夹具失败](frontend-workbench-initial-fixture-failure.json)及[复核记录](frontend-workbench-fixture-review-failure.json)。测试双的characters响应校验失败，导致期望的待处理角色没有进入列表；不是供应商或真实资产生成失败。修正测试夹具后最终22项通过。

安全一致性专项还实际验证：本地选图预览不POST、不确认旧图、不替换当前GLB；换Q版再返回写实时，未保存文件、权利复选框和许可草稿清空；选择期间左侧风格控件临时禁用；离开问答再返回工作台，重复选择同一模型的modelId/Hash/选中态一致。

## 数据与费用不变性

[不变性结果](protected-invariants.json)：

- 四个业务数据库18表的内容、Schema及主键标识对比通过；22任务、88步骤、59产物、194事件未变化。
- 原LLM账本本轮实际基线和结束均为**110条**，不是旧记录中的109。未新增付费请求。
- Neural4D仍已用2/3、剩余1；两个成功任务、18条历史操作、60历史积分记录未变化；当前真实创建`realEnabled=false`。剩余次数未记成使用。
- 74份受保护文件逐文件Hash不变，包括现有聊天JSON、数据库、模型资源、原始与兼容GLB、BGE/Qdrant持久化内容、七文化HTML及`.env`（只比Hash，不公开内容）。
- 补采共享导航`style.css`与文化图片/音视频共67份文件，全部Hash不变；补采时间明确在结果中，没有冒称开工前已覆盖它们。
- 用户运行服务持有三个owner锁，锁文件不能读取；如实标记，不声称锁Hash已验证。业务库、持久化索引和模型文件另行比对通过。

本轮DeepSeek、Neural4D、其他付费服务调用均为**0**。健康接口中的历史`llmVerified`不证明今天的供应商连通性；本轮没有验证真实外部API。

## 截图与隐私

- [改造前1920截图](screenshots/before-realistic-1920.png)。
- [改造后桌面](screenshots/workbench-1920-privacy-masked.png)、[平板](screenshots/workbench-1024-privacy-masked.png)、[手机视口](screenshots/workbench-390-privacy-masked.png)。
- 公开证据截图只对右库内部Q版概念图缩略图做明显隐私遮罩，原素材、原GLB均未修改；见[遮罩说明](screenshots/privacy-manifest.json)。真实写实GLB仍是实际渲染。
- 内部Q版模型及未遮罩截图仅保留本机`.runtime`，不加入Git；其文件与Hash见[私有截图清单](private-screenshot-manifest.json)。

## 实际命令与范围

工作目录为项目根目录；以下私有辅助脚本只用于本机验证，不是普通运行所需依赖。它们写入新的`.runtime/asset-workbench-*`证据目录，不覆盖业务数据。

```text
.venv\Scripts\python.exe -B ..\.runtime\phase5-wp4-state.py --output ..\.runtime\asset-workbench-state-before.json
.venv\Scripts\python.exe -B ..\.runtime\phase5-wp4-offline-bootstrap.py --run-root ..\.runtime\phase5-wp4-asset-workbench-full-20261024 --junitxml ..\.runtime\phase5-wp4-asset-workbench-full-20261024\junit.xml --basetemp ..\.runtime\phase5-wp4-asset-workbench-full-20261024\pytest-temp
.venv\Scripts\python.exe -B ..\.runtime\phase5-wp4-asset-workbench-target-bootstrap.py --run-root ..\.runtime\phase5-wp4-asset-workbench-target3-20261024 --junitxml ..\.runtime\phase5-wp4-asset-workbench-target3-20261024\junit.xml --basetemp ..\.runtime\phase5-wp4-asset-workbench-target3-20261024\pytest-temp
node scripts\phase2_frontend_test.mjs
node scripts\phase3_frontend_test.mjs
node scripts\phase4_frontend_test.mjs
node scripts\phase5_wp2_frontend_test.mjs
node scripts\phase5_wp3_frontend_test.mjs
node scripts\asset_workbench_frontend_test.mjs --output ..\.runtime\asset-workbench-frontend-target-final.json
node ..\.runtime\asset-workbench-browser-after.mjs ..\.runtime\asset-workbench-browser-final-01
node ..\.runtime\asset-workbench-extras-final.mjs ..\.runtime\asset-workbench-extras-final-02
node ..\.runtime\asset-workbench-touch.mjs ..\.runtime\asset-workbench-touch-01
node ..\.runtime\asset-workbench-nav.mjs ..\.runtime\asset-workbench-nav-final-01 after
node ..\.runtime\asset-workbench-secondary.mjs ..\.runtime\asset-workbench-secondary-final-02
```

Node执行使用现有runtime中的Node与Playwright绝对路径；没有安装新依赖。隔离后端测试不能换成会导入真实配置的裸`pytest`运行。

## 结论

本次改造范围内最终测试**PASS**，最初失败和修复证据保留。实体设备、当前付费API、跨机器资源恢复不在本轮已验证范围；没有把它们标为通过。等待用户审阅本轮总报告，不继续开发其他功能。
