# 数字戏台、内容直达与比赛材料收尾

日期：2026-10-29。状态：`WAITING_MANUAL_ACCEPTANCE`。用户要求继续完成现有项目，并新增持续显示的内容输入框；随后明确录像由用户自行完成。本轮不录屏、不进入新阶段、不发布或推送。

## 1. 打开与手动检查

在VS Code打开本项目，进入左侧“运行和调试”，选择 **戏境 AI：一键运行**，点击绿色三角形。复用现有`.venv`与私有配置，不需要安装、初始化或重建资源。正常启动后浏览器自动打开工坊。

- [问答](http://127.0.0.1:8000/about.html#ai-workshop-qa)：保留真实历史会话、连续问答和引用。**点击发送可能调用DeepSeek，本轮没有测试付费请求。**
- [数字戏台](http://127.0.0.1:8000/about.html#ai-workshop-stage)：选择剧目，拖拽/缩放，点击人物近看，点击“重置视角”回到舞台。人物是静态模型，不播放表演动作。
- 全站底部“想了解什么？”：输入“武生”“脸谱”“西皮”“周瑜”等后按回车；不唯一时选择结果。无匹配可把问题带到问答框，**不会自动发送或新建会话**。
- “更多工具”保留原Agent、历史档案、角色创作、已有模型和企业入口；旧链接继续可用。
- 停止：VS Code红色停止按钮或启动终端Ctrl+C，等待退出。排错沿用[一键运行说明](local-run-setup.md)，不要删除数据库或owner锁。

本轮只读验证实例已正常Ctrl+C退出并释放8000端口；它的GET/HEAD验证门禁不写入产品运行配置。由用户按上述入口启动正常服务。

## 2. 实际实现与文件分类

| 分类 | 主要文件 | 实际职责 |
|---|---|---|
| 工坊界面 | `about.html`、`css/ai-workshop-stage.css`、`js/ai-workshop/main.js` | 主入口只突出问答/数字戏台，旧工具移到次级入口；原164个元素ID全部保留 |
| 3D场景 | `js/ai-workshop/digital-stage.js`、`stage-viewer.js` | 剧目切换、原GLB组合、射线点选、旋转缩放重置、Loading/Ready/Error和手动恢复 |
| 只读资源 | `backend/app/stage_assets.py`、`backend/app/main.py` | 固定ID清单、文件Hash/大小/GLB头校验、安全路径与本机守卫；不打开数据库或供应商 |
| 元数据 | `stage/catalog.json`、`scripts/prepare_stage_catalog.py` | 剧目/人物事实摘要及来源、尺度/台面配置；显式生成私有清单 |
| 格式适配 | `scripts/prepare_digital_stage.mjs`、`verify_digital_stage.mjs` | OBJ/MTL/贴图→派生GLB，独立格式/面积/贴图/原件/重跑校验；不覆盖原件 |
| 第三方源码 | `js/vendor/three/` | Three.js r180与本地GLTFLoader/OrbitControls；MIT许可与来源Hash，不依赖运行时CDN |
| 内容直达 | `css/site-navigator.css`、`js/site-navigator.js`、8个HTML引用 | 固定底栏、本地同义词匹配、锚点定位、歧义选择、问答草稿；没有LLM请求 |
| 最小兼容修复 | `chat-controller.js`、`asset-library.js` | 等待会话恢复再填草稿；显式模型链接优先于上次选择，避免旧Q/写实模型混淆 |
| 测试 | `backend/tests/test_stage_assets.py`、三个前端专项脚本 | 离线隔离测试，不把Mock当真实GLB证据 |
| 文档交付 | 本报告、[证据目录](../evidence/test-results/digital-stage-delivery/README.md)、[Prompt](../prompts/digital-stage-implementation/README.md)、`scripts/build_competition_pdf.py` | 实际结果与失败、人工检查、9页PDF作者脚本 |

`.gitignore`新增源素材目录和`output/`，避免把大型比赛限定素材及生成交付包误提交。没有移动或删除原目录；`.env`没有修改。

## 3. 模型、分类与来源

四个派生文件在仓库外`../.runtime/digital-stage/assets/`，不加入业务资产数据库、不改变原资产ID。源文件及其版本见[素材审查](digital-stage-asset-audit.md)。

| 派生文件 | 字节 | SHA-256 |
|---|---:|---|
| stage.glb | 75,654,176 | `af91737e0f3e1e94c858169de09a8b99ec14b2123e9615e2e53d6d9f87548742` |
| duliniang.glb | 25,480,096 | `868fb6e6e6dab37e167baae8995b25790a36833f79ed9ce9acf5eca7349a7f53` |
| muguiying.glb | 25,452,940 | `8852fab8d2096f9021daaafef5918bb1af0ee68f637f8200808bd04e9eaaec2f` |
| zhouyu.glb | 25,580,372 | `22e4157c8570db3d53766c00db928a40040dd2905f9742e25eeb258f351b3d0c` |

人物按关联剧目分类，**杜丽娘明确标昆曲《牡丹亭》**，穆桂英/周瑜分别关联京剧《穆桂英挂帅》《群英会》。资料来自已核对的[文旅部](https://www.mct.gov.cn/ggfw/zyjzzt/yanchu/yanchuwqhg/202311/t20231117_949778.html)、[国家京剧院穆桂英条目](https://www.cnpoc.cn/cnpoc/gjkt/200902/1f3f34ac62da46e991b43cd4990c0fe0.shtml)和[群英会条目](https://www.cnpoc.cn/cnpoc/gjkt/200902/512246e869864cd9bfb5178e27f2b7fb.shtml)。简短事实摘要非逐字全文、不冒充文化专家审校，也不据模型认定流派/具体院团版本。

新素材按用户“公开资源，仅供比赛使用，不做商用，不用再问了”登记，未重复索取。声明不扩展到商业或原模型公开分发；本轮不公开原件。它们为用户提供素材，**不是新增Neural4D或本轮AI生成成果**。原Q版仍内部非公开，原写实“绛绣·戏韵”及其历史记录保留。

## 4. 实际测试结果

| 测试 | 结果与口径 | 直接证据 |
|---|---|---|
| 后端完整隔离回归 | **838通过、0失败/跳过**；包含29项新增资源专项，不重复相加 | [JUnit](../evidence/test-results/digital-stage-delivery/backend-full/junit.xml)、[隔离记录](../evidence/test-results/digital-stage-delivery/backend-full/isolation-result.json) |
| 新资源专项独立运行 | **29通过**；禁止数据库连接，真实外网被拦截 | [专项记录](../evidence/test-results/digital-stage-delivery/backend-stage/result.json) |
| 原前端六组 | **32/25/42/34/34/23通过**；最后23为补充显式模型链接修复后的结果 | [前端原始输出](../evidence/test-results/digital-stage-delivery/frontend/summary.json)、[最后23项](../evidence/test-results/digital-stage-delivery/frontend/workbench-final-23.json) |
| 新戏台/内容直达离线 | **25/32通过**；DOM及Fetch替身，不代替真实模型 | 同上前端目录 |
| 真实数字戏台浏览器 | **14组通过**；真实四GLB、三人物命中点选、三视口、三态恢复；鼠标连续**312.54°**，三人物CDP触摸各**377.16°** | [真实结果](../evidence/test-results/digital-stage-delivery/stage-browser.json) |
| 全站导航与原功能浏览器 | 最终**46通过、0失败**；8页×1920/1024/390，实际栏目定位、Agent历史/企业入口、旧Q/写实真实GLB、草稿延迟恢复及输入不遮挡 | [实际结果](../evidence/test-results/digital-stage-delivery/navigation-browser.json) |
| 派生GLB独立验证 | **10组通过**；27+5贴图完整解码，源多边形面积/绕向/顶点，四文件重跑Hash一致 | [转换验证](../evidence/test-results/digital-stage-delivery/pipeline-validation.json) |
| 业务与源文件 | 18业务表全字段/Schema、22任务、194事件、88步骤、59产物、110次历史文本调用均未变；36原素材与私有配置共37文件Hash不变 | [业务比对](../evidence/test-results/digital-stage-delivery/business-invariants.json)、[源文件](../evidence/test-results/digital-stage-delivery/source-invariants.json) |
| 既有资源 | 对2026-10-21保存的基线核对46项BGE/知识/Qdrant/旧资产/活动清单全部未变；不伪称这些为当日新建before快照 | [资源比较](../evidence/test-results/digital-stage-delivery/existing-resource-comparison.json) |
| 一键运行预检/停止 | `scripts/run_local.py --check`通过：35片段、2原真实模型、创建关闭；本轮服务正常停止、8000释放 | [停止记录](../evidence/test-results/digital-stage-delivery/verification-stop.json) |
| 技术PDF | **9页**，嵌入中文字体、逐页渲染检查，无截断；录像由用户自行完成 | [PDF检查](../evidence/test-results/digital-stage-delivery/pdf-validation.json) |

所有数字为各自测试组，不累加为“项目独立用例总量”。浏览器使用真实Chrome156.0.8078.73与本地实际FastAPI；验证包装仅允许GET/HEAD并阻断外网。可控HTTP503/元数据变更替身与实际文件加载分别记录。

## 5. 实际失败、修复与证据缺口

1. 官方Three源码首次网络连接受沙箱限制，经相同官方只读范围授权下载成功，保留固定版本与许可；没有安装框架。
2. 独立检查器初版误拒合法byteStride，之后又错误假设全部源面严格产生n−2三角，已修正检查器。最终少6三角由2个闭环重复点面和4个共线点面清理解释；原几何面积/顶点/朝向检查通过。失败JSON保留。
3. 浏览器实际发现舞台初始背向/Ready占位提示残留，修正旋转与状态CSS。首次观察截图同名被覆盖，旧失败画面缺失已说明，**不补造before图**；现有首次观察为中间版本，最终截图单独保存。
4. 初轮全站45项有4项失败：锚点被固定页头遮挡为真实缺陷；历史/旧模型查询选择器部分为测试工具错误。修正后45项仍1失败，确认上次资产覆盖显式Q模型链接为真实缺陷，补回归测试22通过1失败→23通过；最终全站46通过。三轮原始JSON均保留。
5. 专项后端早期因NUL日志/沙箱TestClient/pytest主机名探测受阻，未将中断计为通过。最终独立29与全量838都有实际JUnit及隔离结果。
6. 证据归档辅助脚本首次有Python调用语法错误，未进入归档主体；改正后完成。该错误不涉及产品或资源变更。

## 6. 使用、恢复与比赛交付

已准备本机无需转换；若另行恢复新戏台，需要同目录合法源素材及Node/Sharp工具，显式执行：

```text
node scripts/prepare_digital_stage.mjs
.venv\Scripts\python.exe scripts/prepare_stage_catalog.py
node scripts/verify_digital_stage.mjs --repeat-pipeline
```

当前Sharp复用本机已有工具，可用`XIJING_SHARP_PACKAGE`指定安装的Sharp `package.json`完整路径；不自动安装。Three固定源码已随Git保留。不同机器仍需独立恢复合法素材和既有私有资源，不能仅克隆源码即得到数据库/模型，也不承诺空白机十分钟完成。

技术PDF位于本项目`output/pdf/xijing-ai-technical-report.pdf`，生成器可复用已有ReportLab/PyPDF和中文字体环境；本轮9页已实检。比赛录像**按用户明确决定由用户后续自行录制**，本轮没有MP4/音频，不把自动化浏览器操作当成成片。5～8分钟/≥1080p/普通话及必要开发证据片段沿用[比赛要求与检查表](phase-05-submission-checklist.md)。

## 7. 边界和停止

- 实体手机、低端移动GPU性能、当日真实DeepSeek连通/余额、跨机器完整恢复、公网部署：`NOT_TESTED`；模拟触摸不是实体实测。
- 新舞台约120万三角、人物约100万三角，首次本地加载仍需等待；每次只加载一个分类人物，未宣称低端设备帧率保证。
- 实时聊天付费链路沿用既有历史证据；本轮免费离线测试与预填不等于真实API现时验证。
- 企业是应用方向与需求入口，无真实客户交付；角色不表演、未新增动画。
- 外部付费API **0次**，Neural4D全部请求 **0次**；台账已用**2/3**、剩**1**，用户取消第三次，创建继续关闭。
- 正式赛事名称、截止时间、最终上传入口与提交范围仍由用户核对。不擅自上传素材、合并main、推送或开始其他工作包。

## 8. Git与人工检查

基线`9f089097e19f459a72bb5d376c4d357a6ff15821`，分支`feature/phase5-competition-delivery`不变。按格式适配/只读服务、戏台界面、内容直达与兼容修复、交付证据分别提交。最终实际Hash和工作区状态写在交付目录的`最终版本与文件Hash.json`，避免伪造文档自身的提交Hash。原始源模型留在原位且被排除，绝不提交整个私有运行目录。

按[手动检查与打包说明](submission-manual-check.md)逐项验收。完成本轮后停止，录像留给用户，不创建新模型或新阶段。

### 已形成的真实功能提交

- `187774e`：离线格式适配、来源/Hash和本机只读资源服务。
- `3e1b16f`：数字戏台/剧目人物交互与次级工具入口。
- `02afc07`：全站持续内容输入框、会话草稿适配及旧模型显式链接修复。
- 文档、证据与打包脚本另行提交；最终完整Hash由交付目录收据和实际Git核对。

### 本轮实际命令与环境

仓库根、现有Windows Python3.11.1环境；Node/Sharp/Playwright复用已安装工具，Chrome156.0.8078.73。没有安装依赖。执行了`node scripts/verify_digital_stage.mjs --repeat-pipeline`；八个前端脚本各用已有Node执行，原始输出在frontend目录；专项由私有`stage-service-target-8274bbbabf/run-isolated.py`执行pytest；全量由既有`phase5-wp4-offline-bootstrap.py`执行带临时run-root/JUnit/basetemp的隔离pytest，结果在backend-full目录。没有直接用真实密钥环境运行未隔离测试。

真实浏览器辅助代码和对应输出目录保留；`digital-stage-browser.mjs`的fresh output为`.runtime/digital-stage-browser-final`，`site-navigation-browser-final2.mjs`的fresh output为`.runtime/site-navigation-browser-final2`。验证实例导入实际应用，只允许GET/HEAD并禁止外网。最后运行`.venv\Scripts\python.exe -B scripts/run_local.py --check`预检通过。技术PDF通过已有ReportLab生成，Poppler渲染全部9页实际检查。新增打包器只读Git/文件，不启动应用。

交付文档268个本地链接全部存在，三个Python辅助脚本语法通过，当前已提交历史1373个文本版本敏感模式检查0命中；这些是模式扫描而非全面安全审计。完整历史包会在最终提交后再次扫描。归档只复制材料，原文件不搬动；MP4保持用户待录。
