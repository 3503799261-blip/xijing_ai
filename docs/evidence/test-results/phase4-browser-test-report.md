# Phase 4真实浏览器与HTTP测试报告

日期：2026-10-11～12，Asia/Shanghai。主要Viewer/8页验收在11日执行，双风格与重启后复测在12日执行，各JSON保留实际UTC时间。使用项目HTTP服务 `http://127.0.0.1:8000`、Codex内置Chromium浏览器及实际GLB。不是截图模拟、file://预览或Neural4D生成证据。

## 测试范围与结果

| 检查 | 实际结果 | 证据 |
|---|---|---|
| 桌面1920×1080真实GLB加载 | Ready，可见模型 | `phase4-browser-camera-final.json`、`../screenshots/phase-04/viewer-final-desktop-ready.jpg` |
| Loading | 选择原Duck时实际出现loading/75%及“正在加载真正的3D模型” | 公开工具记录、camera报告loadingObserved；未截到独立Loading图片 |
| 连续水平鼠标拖拽≥260° | 同一次拖拽(418,660)→(1014,660)，用户事件记录391.8° | `phase4-browser-camera-final.json`、`viewer-final-desktop-drag.jpg` |
| 旋转跨360° | 相机theta可跨整圈；无水平角度夹断 | 同上；不是将往返拖动相加 |
| 放大/缩小按钮 | 半径3.441173→2.757279→3.436835 | camera报告 |
| 鼠标滚轮 | 真实用户事件增加，半径变化到2.190201 | camera报告wheelZoomAfterActualWheel；最初一轮滚轮落点未完成缩放，重新核对后实际验证 |
| 重置视角 | theta回0、半径回3.441173 | camera报告resetAfterWheel |
| 实际资源失败 | 临时改名专用测试GLB，后端404，Viewer显示Error与中文说明 | `phase4-browser-error.json`、`viewer-load-error.jpg` |
| 恢复原文件后手动重载 | 首次失败暴露缓存Bug；修复后同登记模型恢复Ready | `phase4-browser-recovery.json`、`viewer-recovered.jpg` |
| 375×812布局 | 文档宽360≤375，无水平溢出，真实GLB可见 | `phase4-browser-mobile.json`、`viewer-mobile-375.jpg` |
| 触摸模式开/关 | aria-pressed true/false；touch-action none/pan-y，中文帮助同步 | mobile报告 |
| 真手机单指旋转、双指缩放 | **未实测**。工具只提供窄视口与鼠标，不能冒充物理触摸 | 后续必须由真机补验 |
| 8页导航、图片、标题 | 实际逐页打开；本地图片均complete且naturalWidth>0 | `phase4-browser-eight-pages.json` |
| 8页HTTP/62本地资源 | 成功，6个受保护路径均404 | `phase4-http-regression.json` |
| 原7文化HTML | 与Phase 1和Phase 3逐字节一致 | HTTP报告、`phase4-local-continuity-audit.json` |
| 原问答与Agent基础回归 | 本地真实RAG检索成功；原任务、引用、人工确认门禁仍可见；未再调用LLM | `phase4-http-assets.json`、`agent-regression.jpg` |

摄像机DOM数据来自model-viewer的真实`camera-change`；程序缩放/重置不能被计入用户260°拖拽。`phase4-browser-drag.json`是较早一次448.1°拖拽记录，最终界面复测391.8°，分别保留，不能混写成一个测量。

## 模型身份与许可

原测试文件为Khronos样例Duck，120484字节，SHA-256：
`65bf938f54d6073e619e76e007820bbf980cdc3dc0daec0d94830ffc4ae54ab5`。

©2006 Sony，SCEA Shared Source License1.0；完整许可随fixture保存。这不是CC0、京剧角色或Neural4D输出。网页将它放在独立“Viewer测试素材”选择器，不将同一文件冒充Q版/写实两份角色模型。

故障夹具仅增加GLB extras标识，Hash为`782e30557f2e958ff6e29594c011cf3eb3a20ad84835f7a5840b6e7b531512df`。测试仅临时改名这个私有文件，随后原样恢复；没有损坏原Duck或正式角色素材。`scripts/phase4_browser_failure_fixture.py`保留明确prepare/missing/restore流程。

## 双风格联调与失败修复

已确认的真实Phase 3任务 `0a808e2b-182e-4457-b0bb-5e4f39a66263`（青旌将·霄羽）用于本地资产联调，用途明确写为“非最终建模素材”，没有重新运行Agent。

初次实际登记返回`CHARACTER_SCHEMA_INVALID`，保留 [首次失败](phase4-browser-style-first-failure.json) 和 [对应截图](../screenshots/phase-04/style-registration-before-fix.jpg)。原因是Phase 3在严格文化JSON验证后附加`execution`及部分`programmaticChecks`追踪字段，资产层直接重验文化Schema而误拒绝。修复只识别并验证这些已有服务端字段，其他未知字段仍拒绝；没有改写旧TaskStore或放松Phase 3协议。

最终真实复测见 [双风格浏览器结果](phase4-browser-styles.json) 与 [HTTP快照核对](phase4-style-http-readback.json)：角色ID同为`120653e0-6775-511a-9bf5-53d5307275e0`；Q版资产`e9fd199c-65b6-4bb0-a930-9d03d749930a`、写实资产`ba26e5fb-4881-4754-8222-94305eb90109`各为v1。两者角色、审校和引用快照完全相同，Prompt Hash不同；没有图片或模型。未登记写实时明确显示空态，显式登记后切回Q版恢复原Prompt与资产ID。企业入口显示独立需求字段，风格自由选择；没有提交新Agent任务。

对应截图：[Q版](../screenshots/phase-04/dual-style-chibi.jpg)、[写实](../screenshots/phase-04/dual-style-realistic.jpg)、[企业入口](../screenshots/phase-04/enterprise-entry.jpg)。这些本地登记不是用户对视觉Prompt或概念图的最终确认；用户提供的绿色概念图仍待关联，不代为绑定此蓝金武生。

中断后本地服务退出，12日第一次打开与过早HTTP检查返回连接拒绝；恢复服务、确认startup complete后，实际HTTP13项全部通过。新浏览器页加载合法Duck为Ready，重置按钮可用，未捕获warn/error。见 [重启后的真实GLB](../screenshots/phase-04/viewer-post-restart-ready.jpg)；没有将未就绪的请求写成通过。

输入图片、GLB各自绑定风格与版本，离线Service/API检查包括图片分别保存、GLB分别保存和不存在模型空态。这些测试不等于已生成两个京剧3D模型。

## 控制台与API

8页正常导航这轮未捕获警告/错误。缺失文件测试产生明确的一条404加载错误，是有意故障注入，不能写成“全程零错误”；文件已恢复。旧角色格式错误是后端422，不是浏览器脚本崩溃。没有观测到阻断性JS错误。

实际本地资产/API13项检查包括health、capabilities、历史未知锁定、Range206、鉴权拒绝、重复未授权提交拒绝、modelCount2拒绝、JSON8KB限制、精确CORS和本地检索。首次脚本11通过/2失败是测试脚本误读`health.ready`及将未知全局次数期望为0；修正为实际`status=ready`和null后13通过，原失败文件保留为`phase4-http-assets-before-harness-fix.json`，没有修改服务伪造通过。

本轮未请求Neural4D或DeepSeek。真实Neural4D连通、Credit费用、生成质量、下载主机与真手机手势尚待完成，不能将本报告用于宣称Phase 4 COMPLETE。

## 关键证据入口

- [桌面相机实际测量](phase4-browser-camera-final.json)、[桌面Ready截图](../screenshots/phase-04/viewer-final-desktop-ready.jpg)
- [错误状态](phase4-browser-error.json)、[恢复验证](phase4-browser-recovery.json)
- [375×812视口](phase4-browser-mobile.json)、[移动端截图](../screenshots/phase-04/viewer-mobile-375.jpg)
- [8页浏览器检查](phase4-browser-eight-pages.json)、[整站HTTP与资源](phase4-http-regression.json)
- [资产/API13项](phase4-http-assets.json)、[固定账本只读审计](phase4-local-continuity-audit.json)
