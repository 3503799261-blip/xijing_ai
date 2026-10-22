# Phase 5 WP5 · 材料、证据与交付一致性核查

日期：2026-10-22。范围仅本轮文档与只读证据审查；不是新一轮应用/浏览器/付费API测试。实际WP4应用回归仍按[原始报告](phase-05-wp4-test-report.md)读取。

## 1. 环境、基线和保护范围

实际仓库`D:\京剧\京剧`，分支`feature/phase5-competition-delivery`，起点`61064b0842e5f3789c01b107dd0b2a3f45c55adb`干净。使用已有Windows PowerShell和`.venv/Scripts/python.exe`，未安装依赖或启动业务服务。执行辅助仅Python标准库和已有敏感模式扫描，不导入`backend.app.main`、Settings或Provider。

起点保存263个非docs已跟踪文件Hash，核对WP1～4关键16个Git祖先。通过已归档[只读资源盘点辅助](phase-05-wp4-db-repair/phase5-wp4-db-repair-inventory.py)两次读取实际数据库/资源：SQLite URI mode=ro、query_only=ON，输出仅写新的私有.runtime文件。真实库未初始化/迁移/写入，测试没有故障注入。

两个Neural4D创建相关非秘密布尔字段单独白名单提取，均为false；不提取或输出API Key/管理Token字段。[安全标记](phase-05-wp5/safety-flags.json)只保存两个布尔值。没有访问供应商鉴权、余额、查询、下载或建模接口。

## 2. 实际核查结果

| 执行 | 结果 | 真实含义 |
|---|---|---|
| [首轮](phase-05-wp5/validation-attempt-01.json) | 960 PASS / 1 FAIL / 0跳过 | BGE的40位Model Hub revision被辅助误当本仓库Git提交；不是模型缺失、应用Bug或业务测试失败 |
| [修正后第二轮](phase-05-wp5/validation-attempt-02.json) | 974 PASS / 0 FAIL / 0跳过；445个本地链接 | 模型revision独立对照真实下载脚本，所有真正的Git引用逐一验证祖先；新增原执行辅助等文件也进入检查 |
| [最终一致性复核](phase-05-wp5/validation-result.json) | 1004 PASS / 0 FAIL / 0跳过；463处本地链接引用检查 | 数量含新增README单行保护检查；链接按引用次数而非去重文件数。不同轮次不相加为测试总量 |
| JUnit与统计口径 | PASS | 实际解析full754，含全部targeted41节点；CLI9和现场42分别核对，不宣称新增795项或累加各WP |
| 旧证据完整性 | PASS | 逐一核对WP4追加archive-manifest的86份原始文字Hash；旧失败和复测没有改写 |
| [本轮资源完整性](phase-05-wp5/resource-integrity.json) | PASS | 4业务库字节/对象/sidecar、5知识/Qdrant文件、26BGE文件、14资产文件与起点及WP4最终均一致 |
| 263个非docs已跟踪文件 | PASS | 262个逐字节不变；README仅第5行从WP4待验收校准为WP5待验收，其余内容/换行保留；业务代码/模板/依赖/媒体不变 |
| 两个真实GLB/原件 | PASS | 字节和SHA-256保持原值，内嵌纹理资源无变动；未下载/转换/覆盖。四Hash见[许可清单](../../reports/phase-05-asset-provenance-and-permissions.md) |
| 多份材料交叉审读 | PASS（AI审读） | 依据当前代码和原报告核对事实、许可边界、历史/实时区别、计数及入口；不是用户验收或文化/法律专家审核 |
| 公开敏感信息模式与文件范围 | PASS，具体扫描数量见最终JSON | 模式扫描只覆盖已跟踪/非忽略UTF-8文件，检查大文件/二进制/签名链接；不声称绝对排除未知秘密 |

以上是**材料核查**，不是本轮新增应用测试。754/41/9/42属于已执行历史结果，本轮只解析其原始产物；没有重新跑后端、浏览器、手机或完整演示排练。

## 3. 真实发现、修正和保留证据

1. 首轮辅助用通用40位十六进制表达式抽取Git引用，误纳入BGE固定revision `7999e1d3359715c523056ef9478215996d62a620`。保留[原执行辅助](phase-05-wp5/validation-attempt-01-executed-helper.py)与960/1原结果；修正为单独与[download_model.py](../../../backend/scripts/download_model.py)固定revision核对，其他真实项目提交仍必须存在并为祖先。没有删除失败或跳过未知提交。
2. AI交叉审读发现新演示稿把内部访问拒绝举例为403；实际[资产路由](../../../backend/app/api/assets.py)使用404。已改准确描述“访问拒绝/资源错误（当前门禁404）”，没有改业务门禁或为公开展示解除限制。
3. 新简介记录计数口径：汉字104/294/754，包含标点/英数的非空白字符122/353/973。后续官方若按全字符限字须裁剪；这些是文本长度，不是项目效果指标。
4. 提交前发现README顶部当前状态仍为WP4待验收/WP5未执行，与本次用户确认不一致。仅修正第5行，保留原文件换行与其余全部字节；校验将README这一处允许的事实修正单独检查，其他262个非docs文件仍须原Hash，未无差别放宽保护。

没有检索调参、模型重建、图片重新授权或虚构Bug；仅修正真实材料/核查辅助问题。原盘点辅助沿用`clientDate=2026-10-21`字面量，实际两次执行以资源证据`beforeAtUtc/afterAtUtc`为准，未改旧辅助伪造日期。

## 4. 实际命令和复查方法

下列路径是本机本轮真实命令，不作为通用部署路径要求。只读盘点必须选择新的仓库外输出路径；不要把旧脚本当恢复/重建命令：

```powershell
Set-Location -LiteralPath 'D:\京剧\京剧'
git status --short
git branch --show-current
git rev-parse HEAD
git log -12 --oneline
.\.venv\Scripts\python.exe ..\.runtime\phase5-wp4-db-repair-inventory.py --output D:\京剧\.runtime\phase5-wp5-physical-before-20261022.json --compare D:\京剧\.runtime\phase5-wp4-db-repair-physical-after-02.json
.\.venv\Scripts\python.exe ..\.runtime\phase5-wp4-db-repair-inventory.py --output D:\京剧\.runtime\phase5-wp5-physical-after-20261022.json --compare D:\京剧\.runtime\phase5-wp5-physical-before-20261022.json
.\.venv\Scripts\python.exe docs/evidence/test-results/phase-05-wp5/validate_materials.py --output docs/evidence/test-results/phase-05-wp5/validation-attempt-01.json
# 上一条实际使用的是保留的首轮原辅助，修正后执行：
.\.venv\Scripts\python.exe docs/evidence/test-results/phase-05-wp5/validate_materials.py --output docs/evidence/test-results/phase-05-wp5/validation-attempt-02.json
.\.venv\Scripts\python.exe docs/evidence/test-results/phase-05-wp5/validate_materials.py
git diff --check
```

首轮/第二轮JSON是原记录，复跑不要覆盖它们；改用新的`--output`，默认最终文件只由本轮最终归档执行更新。辅助依赖本机私有只读基线、并不随Git取得所有私有资产；缺这些输入不能宣称新机器已通过此核查。其他机器需要先按[部署与恢复说明](../../reports/phase-05-deployment-and-recovery.md)准备合法资源和独立只读盘点。

最终辅助：[validate_materials.py](phase-05-wp5/validate_materials.py)。公开的是Hash/结果和允许的文字记录，没有DB、GLB、概念图或新截图。原始Prompt23950字节/公开快照26条见[元信息](../../prompts/phase-05/20-wp5-delivery-export-metadata.json)；排除内部推理/协作，快照不伪称包含后来提交和回复。

## 5. 未执行、待确认与停止

| 项目 | 状态/原因 |
|---|---|
| 本轮应用754项/41专项、CLI9、现场42、8页/两GLB浏览器复测 | NOT_TESTED（本轮）；历史证据已逐项核实，没有业务代码变化，不无意义重跑 |
| 新讲稿真人计时、MP4成片、正式PDF/PPT | NOT_TESTED / 尚未制作；仅交文本，规则和公开范围未确认 |
| 实体手机、跨机器/空白系统完整恢复、真实ACL | NOT_VERIFIED；保留前包边界，未用Mock伪装真实 |
| 当前DeepSeek/Neural4D连通、鉴权、余额/权限 | NOT_VERIFIED；本轮供应商请求禁止且实际为0 |
| 官方比赛名/赛道/截止/格式、素材完整公开许可 | PENDING；[规则对应表](../../reports/phase-05-requirements-evidence-map.md)和[许可清单](../../reports/phase-05-asset-provenance-and-permissions.md)给出缺口 |
| 第三次建模 | NOT_APPLICABLE：用户取消，未使用剩余1次，不是失败 |

材料提交`2472284b220b65b56b29aa280516a38021d13a8e`已实际形成；测试/Prompt/总结独立本地归档，自身Hash及最终工作区以真实Git与[WP5总结](../../reports/phase-05-work-package-05.md)及最后回复核实，不预造自引用Hash。

本轮**付费API0、真实外部AI0、Neural4D全部请求0、生产业务写入0**。两个模型和历史数据原样，2/3已用、余1未使用、创建关闭；不合并main、不推送、不自动创建新工作包。
