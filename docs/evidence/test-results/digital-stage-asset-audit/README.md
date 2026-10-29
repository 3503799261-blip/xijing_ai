# 数字戏台素材检查证据（2026-10-29）

这是**开发前素材审查**，不是新数字戏台功能验收。没有安装、转换、建库、注册新资产或供应商调用。业务代码与原两模型保持；本次不重新运行历史809项后端回归，也不把它写成本轮测试。

| 证据 | 实际范围与结果 |
|---|---|
| [舞台源审查](stage-source-audit.json) | 33文件Hash、OBJ/MTL/贴图文本与图像头；发现路径、CMYK/超大纹理和复杂多边形问题，未转换 |
| [人物GLB审查](character-glb-audit.json) | 三个文件、两个唯一Hash，头/长度/缓冲/索引/图像等只读检查；不确认角色文化身份 |
| [首轮浏览器环境阻断](browser-first-blocked.json) | ERR_NETWORK_ACCESS_DENIED，模型未加载；不能计为通过 |
| [真实浏览器复测](browser-final.json) | 2个唯一原GLB均Ready，3836/1597毫秒，无console/page错误、外网或写请求；实际Chrome不是Mock |
| [源人物前后不变性](character-browser-source-invariants.json) | 三文件原Hash未改变 |
| [私有截图清单](private-screenshot-manifest.json) | 两张真实模型截图及Hash，未知公开许可，像素不加入Git |

JSON副本仅把顶层`sourceDirectory`从开发机绝对路径改为仓库相对位置，几何/Hash/问题/原时间没有改写。截图中要求的原图单独原样保存于[提交要求证据](../../submission-requirements/2026-10-29-user-provided.png)，与模型截图区分。

## 执行与复现边界

原执行复用项目`.venv`、Pillow/标准库、现有本地model-viewer及已安装Chrome/Playwright/Node，没有安装依赖。审查大文件采用文本/二进制读取，没有调用C4D或外部转换服务。

`helpers/`保存本次实际采用代码；Python初次以PowerShell here-string经stdin执行，事后保存对应代码，不把保存动作说成重新执行。浏览器脚本归档仅规范末尾空行，原执行副本保持；首次环境阻断，后在相同只读边界复测，启动自己的8879并在finally关闭。没有停止8000用户进程。

示意复现命令（需先核对脚本内**本机路径与新的输出目录**，不要覆盖历史证据）：

```powershell
.\.venv\Scripts\python.exe -B docs\evidence\test-results\digital-stage-asset-audit\helpers\audit-stage-source.py
.\.venv\Scripts\python.exe -B docs\evidence\test-results\digital-stage-asset-audit\helpers\01-read-only-glb-parse.py
node docs\evidence\test-results\digital-stage-asset-audit\helpers\character-browser-original-02.mjs
```

以上是归档脚本的可执行位置，不声称本次原工具命令就是这些归档路径；原实际执行副本在仓库父目录`.runtime/stage-asset-audit-20261029/`。`supplement-stage-audit.py`和`03-audit-notes-and-source-recheck.py`会追加本次审查说明，只针对副本使用，不要对历史原结果直接重放。

舞台JSON的三角数为n−2估算，尚无可靠三角化输出；模型几何可读不等于手机性能良好。舞台转换/组合、人物点击、260°交互、实体手机及八页业务回归本轮均NOT_TESTED。源素材许可NOT_VERIFIED，文件名不当作身份或授权证据。费用与Neural4D请求均0。
