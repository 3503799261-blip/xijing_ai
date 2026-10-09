# Phase 1 实际浏览器测试报告

日期：2026-10-09，Asia/Shanghai。最终结果：本阶段要求的测试通过；保留中途失败与修复记录。测试由 CUA 实际操作 Codex In-app Browser（IAB），只读 DOM 用于核对界面和媒体状态。

## 环境与运行

Windows PowerShell，本地 Python HTTP Server（Python 3.11.1），只绑定回环 IPv4：

```powershell
python -u -m http.server 8877 --bind 127.0.0.1 --directory 'D:\京剧\京剧'
```

本机沙箱内初次服务/请求出现 `Bad access`；按已批准的本地运行范围启用非沙箱服务后，`127.0.0.1` 和 `localhost` 均实际 HTTP 200。未改防火墙或浏览器安全设置。过程保留在 [HTTP 诊断](http-diagnosis.md)。此前审查的 8765 失败记录作为历史证据保留，不当作本次测试结果。

浏览器实际检查视口：1920×1080、1440×900、768×1024、390×844。手机和平板是浏览器视口适配测试，未使用真实手机硬件；未运行跨浏览器内核矩阵。最终捕获的警告/错误列表为 `[]`，见 [控制台记录](browser-console.json)。

## 实际验证结果

| 范围 | 真实操作/观察 | 结果 |
|---|---|---|
| 八页回归 | 逐页公共导航点击；核对八项名称/目标、h1、图片加载与1920布局 | 通过，8页均无坏图或横向溢出 |
| 原资源 | 浏览器图片可见；音频媒体状态；四视频 readyState/时长/error | 通过；与静态 SHA256 核验互补 |
| 原交互 | 音乐页原生播放/暂停；视频首段播放/暂停；生角锚点/悬停翻转；画廊自动旋转/悬停暂停/分类锚点 | 通过；其余三视频仅验证加载与媒体元数据 |
| 工坊入口 | 总览两卡片点击，问答与角色区分别显示；内部导航；浏览器后退；回顶 | 通过 |
| 问答 | 空值/空白/601字提交，推荐按钮/键盘填入，有效提交 | 通过；有效提交仅出现准确未接入通知，无AI回答或引用 |
| Agent | 四卡片待执行；职责 Enter 展开/收起；摘要待接入提示 | 通过；无模拟进度、任务或执行摘要 |
| 角色草稿 | 空值/1201字拒绝；选择风格、文本整理、清空、刷新 | 通过；`<img src=x onerror=alert(1)>` 显示为文字，没有创建图片节点 |
| 图生3D | 状态未提交；生成与下载禁用；查看器空容器 | 通过；没有图片冒充3D、没有canvas或伪模型 |
| 手机 | 五面板实际点击切换；宽度与单一可见面板；问答发送和Agent键盘展开；首页导航/图片 | 通过，390×844无横向溢出 |
| 平板/桌面 | 768×1024 Agent双列；1440×900无溢出；1920×1080演示布局 | 通过 |

页面逐项 DOM 证据：[browser-page-regression.json](browser-page-regression.json)。响应式检查：[responsive-checks.json](responsive-checks.json)。全部交互尝试：[browser-interactions.json](browser-interactions.json)。后者保留原始 `passed: false`，不能简单将原始记录全部计为通过；需要结合以下修复与复测映射。

本次共保存50条浏览器检查记录，47条当次通过、3条初始或瞬时失败；3条均有实际通过的后续检查对应，最终未解决项为0。可机器核查的原记录→复测映射见 [最终测试摘要](final-test-summary.json)。

## 失败、原因与最终处理

| 原始现象 | 原因与处理 | 最终验证与证据 |
|---|---|---|
| 首页旧661px导航中AI标签换行、页头约99.7px | 已将首页限定宽度改为 `max-content`，但浏览器仍加载缓存版本；为已变更的首页样式增加版本参数 | 导航高度约55.0px、总宽668.5px，最后项恢复单行；`nav-before-width-fix-1920.jpg` → `after-home-1920.jpg` |
| 点击执行摘要后，通知top约−21.9px，被82px固定页头挡住 | 动态读取页头高度，给通知与区标题设置 `scroll-margin-top`；工坊CSS/入口脚本增加版本参数 | 滚动完成后通知top约106.1px，页头82px；`before-notice-scroll-fix-1920.jpg` → `after-notice-scroll-fix-1920.jpg`；提交 `ad66d49` |
| `fill(601字)` 后长度仍是601，原“maxlength自动截断”断言失败 | 自动化fill可绕过浏览器原生键入限制；该断言不足以证明提交校验失败 | 实际点击发送被JS拒绝，`aria-invalid=true`、最多600字错误、用户消息未增加；保留失败并更正测试结论，没有伪造截断通过 |
| 修复后立即读取通知top约76.8px，首次断言仍失败 | 页面轻量平滑滚动尚未结束，立即观测为中间位置 | 后续实际截图与DOM稳定位置为106.1px，最终“摘要通知滚动完成后无遮挡”通过；保留中间断言 |

另外，测试工具曾用不存在的「工坊首页」名称定位（实际为「工坊总览」），以及用 role=button 定位原生 summary 超时；读取新 AX 后改为实际名称/summary 定位，操作成功。它们是测试定位失败，未据此虚构网站 Bug 或修改代码。

## 截图

截图均为真实本地 HTTP 浏览器捕获，位于 `docs/evidence/screenshots/`：

- 改造前：`before-home-1920.jpg`、`before-about-1920.jpg`。
- 改造后：`after-workshop-overview-1920.jpg`、`after-qa-interface-1920.jpg`、`after-agents-1920.jpg`、`after-creation-1920.jpg`、`after-model-1920.jpg`。
- 原站：`regression-{index,history,roles,facial,music,video,gallery,about}-1920.jpg`；音视频播放、翻转卡片和画廊悬停另有截图。
- 手机/平板：`mobile-{overview,qa,agents,create,model}-390.jpg`、`mobile-qa-feedback-390.jpg`、`mobile-home-390.jpg`、`tablet-agents-768.jpg`。
- 修复前后：上述导航/通知对应截图。

`mobile-agents-390.jpg` 为长页截图，包含固定页头随滚动捕获的表现，不单独用于判断首屏遮挡。最终总览截图位于页面顶部（scrollY=0）；问答反馈以单独的手机反馈截图核对。

## 静态及语法辅助检查

实际运行 Python 标准库脚本（Python 3.12.14）：

```powershell
& 'C:\Users\35037\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'D:\京剧\京剧\scripts\verify_phase1_static.py' 'D:\京剧\京剧' 'D:\京剧\backups\phase-01-original-20261009-214442' 'D:\京剧\京剧\docs\evidence\test-results\static-regression.json'
```

退出0，7项检查通过：66项原资源相同，旧共享样式和文化正文按允许范围保留，212本地引用与2模块导入存在，无重复ID/失效片段/ARIA引用，无网络伪调用/危险HTML注入/前端密钥。见 [静态回归原始结果](static-regression.json)。该结果本身不证明浏览器渲染。

开发时对三个模块实际执行 `node --check js/ai-workshop/main.js`、`node --check js/ai-workshop/contracts.js`、`node --check js/ai-workshop/services.js`，语法检查通过。静态脚本和对话导出器仅用 Python 标准库，网站运行不需要 Node。

新增工坊CSS包含 `prefers-reduced-motion` 与键盘焦点样式；本次仅审阅该规则，没有切换系统动画偏好或使用屏幕阅读器作全面辅助技术测试。
