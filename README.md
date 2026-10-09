# 戏境 AI

在原有「梨园风华」京剧文化网站上搭建 AI戏韵工坊，探索非遗知识传播与数字角色创作。Phase 1 已完成前端开发和实际浏览器验证，等待用户正式验收。京剧私有 RAG、多 Agent 执行、概念图生成和 Neural4D 尚未接入。

## 安装与启动

依赖仅为 Python 3 和支持 ES Module 的现代浏览器。没有 npm 依赖、构建步骤、数据库、API 密钥或数据初始化；原文化图片和音视频均随项目保留。`.env.example` 说明本阶段无必需配置，静态网站不会读取它。

在项目根目录用 PowerShell 运行：

```powershell
Set-Location -LiteralPath 'D:\京剧\京剧'
python -u -m http.server 8877 --bind 127.0.0.1
```

打开 [首页](http://127.0.0.1:8877/index.html) 或 [AI戏韵工坊](http://127.0.0.1:8877/about.html#ai-workshop)。停止服务时在启动终端按 Ctrl+C。移到其他目录运行时，只需相应修改 `Set-Location`。

必须使用 HTTP 运行；直接双击 HTML 的 `file://` 方式不能可靠加载模块脚本。端口已占用时，先检查是否已有本项目预览服务可用，或换用 8878 并同步修改访问 URL。检查终端启动错误、`127.0.0.1` 与 `localhost` 的差异，以及 `js/ai-workshop/*.js` 是否返回成功。本次 Python HTTP Server 3.11.1 下两种主机名均实际返回 200。

## 十分钟复现流程

1. 获取完整项目目录，确认包含 8 个 HTML 页面和 `images/`、`media/` 等原资源目录；如果通过 Git 获取，使用正常 clone，无需初始化额外数据。
2. 检查 `python --version`，启动上述 HTTP 服务。
3. 在首页点击「AI戏韵工坊」，依次切换总览、问答、Agent、角色创作、图生3D。
4. 点击推荐问题并发送，核对明确的未接入提示；展开 Agent 职责，输入角色需求并整理或清空草稿。
5. 核对概念图、3D 生成与下载按钮待开放，返回文化栏目检查图片、音频和视频。

这些操作已在当前机器真实执行并留有截图；没有对新机器的安装过程计时，也不声明所有设备均能在十分钟内安装 Python。已有 Python 的环境无需下载前端依赖。

## 架构与文件

```text
index.html          首页与八栏目入口
history.html        京剧发展历史
roles.html          生旦净丑与翻转卡片
facial.html         脸谱艺术
music.html          唱腔、乐器与音频
video.html          四段视频
gallery.html        画廊、自动旋转与分类锚点
about.html          AI戏韵工坊
css/style.css       原共享样式，未修改
css/index.css       首页样式，仅调整长导航宽度
css/ai-workshop.css 工坊隔离样式
js/ai-workshop/
  main.js           面板、表单、页面草稿和操作反馈
  contracts.js      能力开关、Agent 状态和未来数据约定
  services.js       当前明确未接入的服务边界
docs/               审查、选型、Prompt、截图、测试与阶段报告
scripts/            静态回归核验与公开协作证据导出
```

保留多页 HTML 结构和酒红、金色、米白视觉。新 CSS 使用 `ai-workshop-*` 命名空间，仅在工坊加载；旧 `about.css` 留在仓库中但不再被工坊引用。模块脚本仅加载到 `about.html`，其他文化页无新增脚本。

问答只记录用户问题并显示「京剧AI知识问答正在建设中，将在Phase 2接入私有知识库。」；没有 AI 答案、虚假引用或模拟任务进度。角色草稿是用户输入，仅保留在当前页面，刷新后清空。详情使用原生 `details/summary`，基础功能支持键盘，新增过渡尊重减少动画设置。

后续真实服务接入位置见 [前端数据约定](docs/architecture/ai-workshop-contracts.md)。Phase 2 经用户批准后再设计后端，第三方密钥只保存在后端，绝不写入前端资源。

## 已执行的验证

- IAB 浏览器通过 HTTP 实际访问 8 页，在 1920×1080 检查导航、文化内容、图片和资源；另检查 1440×900 工坊。
- 390×844 手机视口检查首页、工坊五个面板与基础交互；768×1024 平板视口检查 Agent 双栏布局。
- 验证问答校验/推荐/反馈、浏览器后退、Agent 键盘展开、草稿安全文本/清空/刷新、3D 禁用入口。
- 实际播放与暂停音乐页音频、视频页首段；四段视频均完成媒体元数据检查。验证行当翻转、画廊旋转/悬停暂停和分类锚点。
- 修复并复测导航缓存和固定页头遮挡提示；最终捕获的控制台警告/错误为空。

测试范围为本机 IAB、上述视口和操作，不包含真实手机硬件或多个浏览器内核。完整结果及原始失败记录见 [浏览器测试报告](docs/evidence/test-results/browser-test-report.md)，截图见 [阶段报告](docs/reports/phase-01.md)。

可复现静态保留检查（仅 Python 标准库，本次实际使用 Python 3.12.14）：

```powershell
python scripts/verify_phase1_static.py . 'D:\京剧\backups\phase-01-original-20261009-214442' docs/evidence/test-results/static-regression.json
```

其他机器需提供自己的原始备份目录，或检出原始基线作为对照；静态检查不能替代浏览器验证。结果确认 66 项原资源保持相同 SHA256、文化正文仅允许的入口修改、212 个本地文件引用和 2 个模块导入均有效。Node 仅用于开发时语法检查，运行网站不依赖 Node。

## Git、备份与协作记录

开发分支为 `feature/ai-workshop-phase1`。先验证原网站与审查清单完全一致，再建立独立备份和真实 Git 基线。备份目录为 `D:\京剧\backups\phase-01-original-20261009-214442`；恢复时可将它复制到新的目录预览和比对，无需覆盖当前开发目录。

Commit Hash、文件改动与验收清单见 [Phase 1 报告](docs/reports/phase-01.md)。[原审查](docs/reports/project-audit.md) 和 [技术选型](docs/reports/frontend-selection.md) 保留历史检查点信息，附有批准后的归档说明。当前 Git 为本地仓库，未创建远端或发布。

完整原始需求、批准开发 Prompt 及公开协作记录在 `docs/prompts/phase-01/`。导出器只读取明确指定的当前会话日志，不搜索其他会话：

```powershell
python scripts/export_phase_prompt.py --session-log '<当前会话JSONL绝对路径>' --output docs/prompts/phase-01
```

原始用户 Prompt 原文保存；公开对话和工具记录排除 system/developer、隐藏推理、内部会话信息及嵌入媒体，并对日志路径和会话标识脱敏。元数据说明源 Prompt 字节与 SHA256 比较。快照只覆盖导出时已经发生的记录；最终回复发生后需再次导出才能包含它，不补写尚未发生的对话。

阶段完成后停止，只有用户明确回复「Phase 1验收通过，进入Phase 2」才开始下一阶段。
