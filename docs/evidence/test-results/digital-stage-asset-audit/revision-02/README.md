# 周瑜替换版本 · 第二轮素材复审

日期2026-10-29，基线`6aa2ff29606fbd3839cbd43278d463a7490381e8`。用户自行替换原路径`周瑜.glb`后重新读取；不覆盖第一轮审查或修改源模型。

| 证据 | 实际结论 |
|---|---|
| [当前三个GLB结构](character-glb-audit.json) | 三文件及几何Hash均不同；新周瑜30,963,320字节、999,996三角；头/缓冲/索引可读 |
| [首轮/本轮比较](source-comparison.json) | 仅周瑜变更，杜丽娘/穆桂英Hash保持；首轮原JSON未改，辅助目录冲突/旧说明修正有记录 |
| [新周瑜真实浏览器](browser-result.json) | 原文件Ready，3870毫秒；无console/page错误、外部连接或写请求；不是Mock |
| [浏览器前后源Hash](browser-source-invariant.json) | 新周瑜Hash不变，自有8879实例已关闭，无DB访问或付费调用 |
| [私有截图Hash](private-screenshot-manifest.json) | 截图实际可见不同的男性戏曲造型；像素和原模型不加入Git，文化身份按用户命名记录 |
| [本轮最终核对](final-validation.json) | 当前36源文件、原两模型Hash、文档链接与敏感文本检查；不是功能回归或舞台验收 |

三个当前模型仍约百万三角、4K贴图；原GLB的`image/jpg`声明与无NORMAL注意项未因浏览器能加载而删除。舞台转换、组合、点选、260°交互、实体手机和手机性能本轮NOT_TESTED，没有把旧模型的验收借作新场景证据。

## 来源用途与历史

用户原话：“公开资源，并且仅供比赛使用，不做商用，不用再问了”。记录为`USER_DECLARED_COMPETITION_ONLY`，不再重复索取；不扩展为原件公开分发或商用授权。作者/原网址未独立验证，不伪造凭证，也不因此阻断本地素材检查。

第一次检查时周瑜与杜丽娘确为同Hash，旧JSON是真实历史；本轮仅新版本改变了结果，不能倒改首轮记录。复用03脚本时旧的“重复文件”说明被04脚本改正，仅改本轮说明，计算字段没有伪造；共享目录的`exist_ok=False`曾保护性失败，随后各自独立文件继续，未覆盖数据。

## 实际执行与复现

实际脚本在仓库父目录`.runtime/stage-asset-audit-20261029-revision2/`，归档于`helpers/`，仅规范末尾空行，未修改逻辑。Python使用项目现有venv/Pillow，Node/Chrome/Playwright及model-viewer复用原环境，无安装。浏览器只启动127.0.0.1:8879白名单文件GET服务，finally关闭，不打开业务数据库或调用任何供应商。

以下命令是在原私有目录实际执行的代码路径，复跑前必须复制脚本并改为**新的输出目录**，不要覆盖历史证据；不直接重放03/04以修改既有结果。

```text
.venv/Scripts/python.exe -B ../.runtime/stage-asset-audit-20261029-revision2/01-read-only-glb-parse.py
.venv/Scripts/python.exe -B ../.runtime/stage-asset-audit-20261029-revision2/02-read-only-texture-inspection.py
.venv/Scripts/python.exe -B ../.runtime/stage-asset-audit-20261029-revision2/03-audit-notes-and-source-recheck.py
.venv/Scripts/python.exe -B ../.runtime/stage-asset-audit-20261029-revision2/04-revision2-note-correction.py
node ../.runtime/stage-asset-audit-20261029-revision2/character-browser-original.mjs
```

没有执行后端809项回归、没有转换舞台或上传原件。付费API、Neural4D、业务数据库写入均0。
