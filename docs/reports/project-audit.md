# 戏境 AI：原网站只读审查报告

> 归档说明：下文是检查点 A 时的真实只读审查，描述当时状态。用户随后明确批准方案 A；本报告于开发阶段归档，原件仍保留在 `D:\京剧\phase-01-review`。批准后的改动、恢复成功的 HTTP 浏览器验证及最终结果见 [Phase 1 阶段报告](phase-01.md)。下文历史失败记录不改写为成功。

- 执行日期：2026-10-09，Asia/Shanghai。
- 被审查目录：`D:\京剧\京剧`。
- 当前检查点：A，技术方案待用户确认。
- 审查范围：读取全部 HTML、CSS、资源清单，检查链接、锚点、Git 和启动条件。
- 原项目未修改、未移动、未删除；未初始化 Git、未建立分支、未接入 AI。
- 本报告及检查证据暂存在兄弟目录 `D:\京剧\phase-01-review`。批准后才归档至项目的 `docs/`。
- 代码与资源静态检查已执行；浏览器连接失败，视觉、播放与交互验收尚未通过。此报告不代表 Phase 1 完成。

## 1. 实际目录结构

```text
D:\京剧\京剧\
├── index.html
├── history.html
├── roles.html
├── facial.html
├── music.html
├── video.html
├── gallery.html
├── about.html
├── css/
│   ├── style.css
│   ├── index.css
│   ├── history.css
│   ├── roles.css
│   ├── facial.css
│   ├── music.css
│   ├── video.css
│   ├── gallery.css
│   └── about.css
├── images/                  # 60 个 JPG，完整文件名见资源清单
├── media/
│   ├── opera-audio.mp3
│   ├── video1.mp4
│   ├── video2.mp4
│   ├── video3.mp4
│   └── video4.mp4
└── audio/
    └── 6月19日.mp3
```

图片文件名（实际枚举）：

```text
about.jpg
art1.jpg, art2.jpg, art3.jpg, art4.jpg
black.jpg, black1.jpg, blue.jpg, blue1.jpg
chou.jpg, dan.jpg, jing.jpg, sheng.jpg
gallery1.jpg, gallery2.jpg, gallery3.jpg, gallery4.jpg
gallery5.jpg, gallery6.jpg, gallery7.jpg, gallery8.jpg
gallery9.jpg, gallery10.jpg, gallery11.jpg, gallery12.jpg
glod.jpg, glod1.jpg
home-banner.jpg, home1.jpg, home2.jpg, home3.jpg
intro1.jpg, intro2.jpg, intro3.jpg, intro4.jpg
mask-black.jpg, mask-blue.jpg, mask-gold.jpg, mask-red.jpg, mask-white.jpg
opera1.jpg, opera2.jpg, opera3.jpg, opera4.jpg, opera5.jpg
red.jpg, red1.jpg, white.jpg, white1.jpg
京胡.jpg, 历史1.jpg, 历史2.jpg, 历史3.jpg, 历史4.jpg, 历史5.jpg
生.jpg, 背景1.jpg, 背景2.jpg, 背景3.jpg, 脸谱.jpg
```

总计 83 个文件、84,380,537 字节（80.47 MiB）：8 HTML、9 CSS、60 JPG、2 MP3、4 MP4。没有 JS、字体文件、`package.json`、锁文件、README、后端目录或构建配置；枚举范围内也没有 `.env`、私钥或证书文件。完整逐文件大小和 SHA256 已保存为 `../evidence/test-results/source-manifest-before.json`。

## 2. 现有技术与文件职责

网站是 **8 个独立页面的 HTML5＋CSS3 静态多页网站**，不是单页应用。主导航切换 HTML 文件，局部使用锚点。没有框架、JS 脚本或 AI 服务。

| 文件 | 实际内容与位置（原文件行号） | 页面样式 |
|---|---|---|
| index.html | Banner 52；国粹概览 67；八张入口卡 90；程式艺术 138；剧目推荐 178；音视频 224；结尾 253 | index.css |
| history.html | Banner 51；概述 63；历史时间线 85；图片 206；关键时刻 234；艺术家 277；传承 314 | history.css |
| roles.html | 概览和内部锚点 63；生 77、旦 109、净 141、丑 173；对比 205 | roles.css |
| facial.html | 概述 63；色彩卡 85；图片墙 128；纹样 156；勾脸过程 183；文化价值 228 | facial.css |
| music.html | 概述 63；西皮/二黄 85；京胡 120；打击乐 142；唱段 170；总结 190 | music.css |
| video.html | 观演介绍 63；四段视频 80、100、120、140；总结 160 | video.css |
| gallery.html | CSS 旋转图库 63；分类导航 153；演员 159、脸谱 196、戏服 233、剧照 270；总结 307 | gallery.css |
| about.html | Banner 51；制作说明 63；作者档案 85；制作路径 105；心得 150；课程成果 176；留言 211 | about.css |
| css/style.css | 色彩变量、容器、标题、按钮、导航、Banner、页脚、响应式与减少动画规则 | 全站共享 |

所有页面在 head 中先加载 `css/style.css`，再加载本页 CSS，例如 `about.html:10–11`。样式属于“公共＋按页划分”，并非全部集中在一个文件。

## 3. 导航与关于页真实位置

8 页主导航顺序一致：`index.html → history.html → roles.html → facial.html → music.html → video.html → gallery.html → about.html`。首页最后一项位于 `index.html:45`，其他页面位于第 44 行。当前页由 `aria-current="page"` 标记。

局部锚点包括首页 `#culture`，行当页 `#sheng/#dan/#jing/#chou`，画廊 `#actors/#masks/#costumes/#stage`，全页回顶 `href="#"`。

“关于我们”不是首页末尾 Section，而是独立的 `about.html`。其 `<main>` 位于 49–228 行，页面含完整课程制作说明和留言表单。首页第 8 张入口卡（130–132 行）同样通往该页面。替换时应保留独立页面结构，真正重建 about 主体，不能仅改标题。

跨页还存在这些引用：

- `index.html:98`：“从历史源流到课程创作”的入口说明。
- `index.html:130–132`：第 8 张卡片的小标签、标题、描述、图片 alt 与链接。
- `facial.html:239`：“了解网站制作说明”正文按钮。
- `facial.html:266`、`music.html:225`、`roles.html:253`：页脚“关于我们”。
- `about.html:6–8`：meta 和 title；53–58：Banner；237、260：课程相关页脚文案。

主导航当前是**顶部 sticky 导航**。公共样式存在三轮历史规则：249 行起的顶部导航、560 行起的侧栏、777–923 行的最终顶部覆盖。796–798 行隐藏 checkbox/侧栏触发器。HTML 中仍有旧开关，不表示当前存在可见侧栏。Phase 1 不应顺便清理整套导航 CSS。

## 4. 视觉风格与可复用部分

`css/style.css:1–18` 定义：

| 角色 | 原值 |
|---|---|
| 主红 / 深红 | `#8d1820` / `#3a080c` |
| 金 / 浅金 | `#c99b45` / `#f0d889` |
| 墨色 / 次级文字 | `#241918` / `#705d57` |
| 米白 / 纸白 | `#f5edde` / `#fffaf0` |

正文使用 `"Microsoft YaHei","Noto Serif SC",sans-serif`、行高 1.75（25–30 行），未下载 Web 字体。不同设备实际字体取决于系统安装情况。最大 1200px、92% 的容器，双栏与 Grid 布局，红金按钮、圆角卡片、舞台摄影、细线及浅纸色共同构成文化风格。

可以复用的 CSS 模式包括 `.container`（46）、`.section-head`（56）、`.eyebrow`（65）、`.section-title`（80）、`.split`（96）、`.btn`（167）、`.page-banner`（373）、`.tag`（439）、`.site-footer`（457）。它们是样式模式和重复 HTML，不是已组件化的代码。

应保留：首页模块顺序、12 栏入口卡布局、原品牌和导航外观、历史/行当/脸谱/音乐/视频/画廊文化内容、所有图片和媒体、页脚及回顶习惯。工坊可沿用 `images/about.jpg` 和 `intro4.jpg`、原色彩变量与字体，使用金线、浅渐变和少量光效。没有必要使用大面积青蓝科技后台视觉。

## 5. 已有交互与动画

- 文件导航、内部锚点、平滑滚动与回顶。
- 首页/音乐页原生 audio controls；首页/视频页原生 video controls，均使用 `preload="metadata"`。
- 卡片、按钮、导航的悬停缩放、位移、光带及当前页高亮。
- 行当卡片 CSS 翻面（`roles.css:45–58`）。
- 画廊 12 图 CSS 旋转环，36 秒循环，hover 暂停（`gallery.css:31–119`）；分类图片与悬停说明。
- 首页内容入场动画（`index.css:15–17`）。
- 共享减少动画规则（`style.css:548–554`）及画廊专用规则（`gallery.css:288–293`）。

画廊旋转环是 CSS 图片效果，不是 Neural4D 模型展示。关于页留言为 `method="get" action="#"`（220–221 行），没有服务端存储，不能描述为真正留言服务。

## 6. 运行方式与真实执行结果

### 已执行的读取与静态检查

```powershell
rg --files 'D:\京剧\京剧'
rg -n '<script|\bon[a-z]+=|<section|@media|nav-toggle' 'D:\京剧\京剧'
git --version
git -C 'D:\京剧\京剧' rev-parse --show-toplevel
git -C 'D:\京剧\京剧' status --short --branch
git -C 'D:\京剧\京剧' log -6 --oneline
```

Git 可执行程序可用（2.56.0.windows.1），后三条均返回 `fatal: not a git repository (or any of the parent directories): .git`。因此没有可报告的当前分支、提交 Hash 或未提交差异；不能称工作区“干净”。本轮没有初始化 Git。未发现适用的 `AGENTS.md`。

已运行审查辅助脚本（脚本及输出均在源项目外）：

```powershell
& 'C:\Users\35037\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  'D:\京剧\phase-01-review\scripts\audit_static.py' `
  'D:\京剧\京剧' `
  'D:\京剧\phase-01-review\docs\evidence\test-results\static-audit.json'
```

结果：209 条本地文件引用均存在；未发现明确失效内部锚点或同页重复 ID；script 标签、内联事件、JS 文件均为 0。该脚本检查 HTML 的 href/src/poster 与 CSS url，不是浏览器资源加载、HTML 标准合规或媒体解码测试。

### 浏览器预览尝试与限制

原网站无需构建。理论上可直接打开 HTML，也可使用静态 HTTP 服务。本轮实际尝试：

```powershell
& 'C:\Users\35037\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m http.server 8765 --bind 127.0.0.1 --directory 'D:\京剧\京剧'
```

受限环境内首次无法正常预览；授权运行临时服务后确认 127.0.0.1:8765 有监听。Codex 内置浏览器两次打开 `http://127.0.0.1:8765/index.html` 均返回 `net::ERR_CONNECTION_TIMED_OUT`。HTTP 诊断也超时；`curl.exe --noproxy '*' --max-time 5 --head 'http://127.0.0.1:8765/index.html'` 返回 code 28。直接 file URL 则被浏览器 URL 安全策略拒绝，仅允许 HTTP/HTTPS，未绕过该策略。

临时服务已核验身份后关闭。当前没有获取到原页面截图；1920×1080、平板、手机视觉与实际媒体播放均为**未执行成功**。连接失败的具体原因尚未确定，不能归因于原网页代码。实施阶段应先恢复可用 HTTP 浏览器预览，再截图并完成回归，不能只凭静态检查验收。

详细记录见 `../evidence/test-results/browser-attempts.md`。

## 7. 优点、问题及兼容风险

### 优点

1. 中文语义化结构明确，专题内容齐全，8 页链接体系简单。
2. 资源全部本地化，不依赖外部字体/CDN，有利于现场演示。
3. 公共设计变量与逐页样式便于局部增强。
4. 已具备响应式断点、按钮焦点样式和减少动画支持。
5. 独立 about 页面提供充足空间，改造不必挤入首页。

### 具体问题与处理边界

| 问题 | 代码证据 / 影响 | Phase 1 建议 |
|---|---|---|
| 首页菜单固定宽度 | `index.css:396–403` 桌面 661px；AI 名称更长可能换行 | 浏览器确认后必要时只调首页规则 |
| 多轮导航覆盖 | `style.css:249/560/777`，旧规则易被误改 | 原则保留；不全局重构 |
| 原留言非真实服务 | about 220–221，GET 参数进入 URL | 随被替换主体移除；原文与源码保存在安全备份/Git 基线 |
| hover 交互缺键盘入口 | 行当翻面、画廊暂停 | 记录现状；新增工坊使用原生按钮、details 和焦点反馈 |
| 本地资源偏大 | 最大图片约 1.34 MiB；单视频最大约 11.26 MiB | 新模块复用少量图片，不添加大型依赖；不擅自压缩/删除旧素材 |
| 缺少运行与版本文档 | 无 README、构建配置和 Git | 批准后建立真实基线、启动说明和证据目录 |
| 字体跨机差异 | 系统回退，无随项目分发字体 | 保持原字体栈，现场设备实际核验 |
| 固定顶部导航遮挡锚点 | 移动端菜单多行，实际高度需测 | 工坊锚点预留 scroll-margin，实测调整 |
| 原内容一致性 | `index.html:210–216` 图片 alt 为“穆桂英挂帅”，标题为“空城退敌计” | 作为既有问题记录，未经内容确认不据此改写剧目 |
| 关于页原有个人资料 | about 99 行含作者/班级等资料 | 基线保存前按用户要求检查敏感信息，发布远端前明确公开范围 |

两个 MP3 为相同 SHA256；有 10 个媒体文件未直接被页面引用。这些可能是备用素材，本轮仅记录，不删除。

## 8. 最佳改造位置

推荐原地升级 `about.html`：保留该 URL、页头页脚和文化视觉，替换课程说明主体为 AI 戏韵工坊。工坊内设置总览、问答、Agent、创作与 3D 四个区域，独立命名空间样式与 JS。全站入口同步改名；其他七页只动关联导航和入口文案。

技术比较、预计文件清单、接口边界、实施顺序与确认事项详见 `frontend-selection.md`。完整原始Prompt与本轮真实工具记录快照已保存至 `../prompts/phase-01/`，没有补造用户确认或修复过程。逐文件Hash复核结果见 `../evidence/test-results/source-unchanged.json`：83个文件均未变化。当前不进入代码开发，不生成虚假 Commit、不标记 Phase 1 COMPLETE。
