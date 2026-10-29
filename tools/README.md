# 可选开发工具环境

这些工具用于离线素材转换、技术PDF生成和浏览器验证，不是站点前端运行依赖。前端使用原生HTML/CSS/ES Module，同一FastAPI进程提供页面与API，无需npm构建。后端安装仍使用[backend/requirements.txt](../backend/requirements.txt)。

本机核对基线：Windows、Python 3.11.1、Node **24.22.1**；Sharp **0.35.5**、Playwright **1.62.1**；ReportLab **4.4.9**、pypdf **6.10.0**、Pillow **12.3.0**。以下清单固定工具的直接依赖，安装器仍会解析间接依赖，不声称已提供全部传递依赖的锁文件。其他系统和版本尚未完成本项目完整验证。

## 需要时手动安装

以下命令是新工具环境的准备指南，本次补充文档没有执行安装。已有演示环境不需要重新安装、转换素材或初始化数据库。请在仓库根目录运行，只为所需工作选择相应一组命令。

PDF工具建议使用独立venv，避免把工具版Pillow覆盖到已有后端环境。venv放在仓库父目录的`.runtime/tooling/`，不复制到源码交付中：

```powershell
python -m venv ..\.runtime\tooling\.venv-docs
..\.runtime\tooling\.venv-docs\Scripts\python.exe -m pip install -r tools/requirements-docs.txt
```

Node工具单独安装在`tools/node_modules/`，不需要更改前端页面：

```powershell
npm install --prefix tools
```

此仓库当前没有工具`package-lock.json`；上述安装会在本机生成锁文件。完成并验证后可留存实际锁文件及安装结果；不能把尚未执行的安装当作复现证据。

## 舞台转换：Sharp路径与合法源素材

`scripts/prepare_digital_stage.mjs`和`scripts/verify_digital_stage.mjs`读取进程环境变量`XIJING_SHARP_PACKAGE`，值必须是已安装Sharp的`package.json`绝对路径。新机器应显式设置，避免使用脚本中的原开发机缓存路径：

```powershell
$env:XIJING_SHARP_PACKAGE = (Resolve-Path -LiteralPath 'tools/node_modules/sharp/package.json').Path
```

该变量由独立Node脚本读取，写进应用私有`.env`不会自动传给Node。设置后仅影响当前PowerShell及其子进程，不修改真实`.env`。

转换还需要具有相应使用许可的源素材：仓库下`中式古戏台SU模型/`和`3D人物模型/`。这些原件及仓库外`../.runtime/digital-stage/assets/`派生GLB均未随源码公开；仅克隆、安装工具或设置环境变量不能取得它们。缺素材时先恢复合法文件，不用测试夹具替代比赛人物。已有演示资源无需重新转换。需明确重建派生文件时，先核对原件、输出路径及已有文件，再按[交付报告](../docs/reports/digital-stage-delivery.md)的显式转换与检查步骤操作。

Three.js r180、GLTFLoader和OrbitControls已随仓库保留在`js/vendor/three/`，包含MIT许可与来源记录，不需要运行时CDN或另装Three。

## PDF：中文字体与截图

`scripts/build_competition_pdf.py`使用ReportLab、pypdf及Pillow。默认字体为Windows的`C:/Windows/Fonts/simsun.ttc`；目标机器必须已有合法可用的相应中文TrueType字体，或通过`--font`提供经验证可嵌入的字体文件。仓库不分发系统字体。更换字体、系统或排版环境后须重新检查中文、分页与表格，不能仅凭脚本退出成功判定PDF合格。

生成器默认读取开发机已有截图目录；在另一目录运行时，须通过`--screenshots`指向已取得展示许可的实际截图目录，并通过`--output`选择新的输出文件。原始截图和私有模型不会因安装PDF工具而恢复，不能用无素材的空图输出冒充现有9页技术文档。

生成示例（仅在资源和路径已核对后手动执行）：

```powershell
..\.runtime\tooling\.venv-docs\Scripts\python.exe scripts/build_competition_pdf.py --font 'C:/Windows/Fonts/simsun.ttc' --screenshots 'D:/authorized-screenshots' --output 'output/pdf/xijing-ai-technical-report-new.pdf'
```

示例截图路径应替换为本机已核对的真实目录。PDF渲染复核另需可用的Poppler命令行工具，例如`pdftoppm`；它不属于pip/npm依赖，按目标系统准备后核对版本及实际输出。本次未安装Poppler或替换字体。

## 浏览器验证与已有证据

Playwright用于浏览器验证，页面实际交互仍需可用的Chrome/Chromium和WebGL。安装npm包不等于已经安装浏览器；只有需要新的独立验证环境时，才手动下载Playwright对应的Chromium：

```powershell
.\tools\node_modules\.bin\playwright.cmd install chromium
```

已有可用浏览器不需要为查看网站再下载一份。`docs/evidence/test-results/`中的部分历史浏览器辅助脚本保留原开发机Playwright绝对路径、输出目录与当时资源条件，属于真实证据；`XIJING_SHARP_PACKAGE`只供Sharp使用，不能替换这些Playwright路径。跨机复跑须先按实际环境核对脚本入口、浏览器位置和隔离输出目录，不能把工具安装成功说成历史浏览器脚本均可直接复现。

## 数据保护与恢复边界

这些依赖清单不启动后端、不初始化数据库、不下载BGE、不调用DeepSeek或Neural4D，也不恢复私有历史。普通查看已有成果沿用[本机启动说明](../docs/reports/local-run-setup.md)；数据或模型缺失时按[部署与恢复说明](../docs/reports/phase-05-deployment-and-recovery.md)核对原备份及来源，不删除原库、清空预算或用新安装命令遮盖历史缺失。私有密钥只保存在既有仓库外配置中，Neural4D创建继续关闭。

本次仅补齐工具清单与指南，没有执行安装、素材转换、数据库初始化、浏览器下载或跨机器恢复。完整跨机恢复仍未验证。
