# Phase 4.2写实主展示准备阶段总结

日期：2026-10-13～14，Asia/Shanghai；原始证据保留实际UTC时间。

状态：**PREPARED_WITH_PENDING_HUMAN_AND_RIGHTS_GATES**。用户要求的本地候选、提案、文本审校、Prompt冻结、风险、预算及授权表已完成；尚不具备第二次真实提交的全部条件。Phase 4整体保持PARTIAL，不进入Phase 5。

## 1. 实际完成内容

- 读取 `D:\京剧\概念图1.jpg`，793×1400 JPEG，535664字节，SHA-256为 `0170077ef813f95b2e0da4666f0a7919078d0a811ac04d61613e69a31a621095`。
- 在既有CandidateCatalog独立登记 `SECOND_REALISTIC_SHOWCASE` 版本1，候选ID `92e3d09f-57ce-49b2-8d57-1c0664a72689`，用途标签 `realistic_showcase_candidate_v1`。
- 保存原图快照与像素一致的PNG预览；不改背景，不复用旧Q版图片，不增加正式角色/图像/模型记录。
- 形成暂名“绛绣·戏韵”的原创京剧风格文字提案；服饰和冠饰为视觉解读，不认定历史人物、传统行当、图像作者或版权。
- 进行3次真实本地RAG检索；服饰、水袖、蟒、盔头查询没有有效证据，缺口保留。
- 按用户单独允许的一次文本调用复用现有文化Reviewer，400输出Token上限、非思考模式、无自动重试，实际返回pass且needsHumanReview=true。不是完整四Agent工作流或图像认证。
- 冻结 `realistic_model_v1.0`，正文Hash `777afaa81b1e696d98dac00e695727e17c40f38983691786d52b69a40f62fad2`，候选完整Prompt快照Hash `80a893202c9d09e508ceba0a2796a3e2b1aab54f812c6790b23177f18bde3e33`。
- 实际浏览器打开候选预览，图像正常，提示待关联/许可未核实/不可建模；当前默认窄视口319×920和1920×1080桌面均无横向溢出、控制台warn/error为空。没有实体手机或第二模型Viewer测试。

普通图生3D当前接口没有文本Prompt字段；上述冻结正文用于人工审核、版本追踪与意图记录，不宣称供应商已接收或遵循。

## 2. 交付文件

| 文件 | 内容 |
|---|---|
| [角色方案](phase-04-realistic-character-proposal.md) | 视觉观察、版本、暂名、角色/权利边界 |
| [文化审查](phase-04-realistic-cultural-review.md) | 真实RAG片段、缺口、一次Reviewer返回、Token及限制 |
| [风险评估](phase-04-realistic-model-risk.md) | 冠饰/袖布/背面高风险，手部中风险，配色低风险 |
| [预算与额度](phase-04-second-model-budget.md) | 全局1/3、剩2、首30积分、第二次报价待确认 |
| [授权申请](phase-04-second-model-approval.md) | WAITING_APPROVAL，未代用户勾选 |
| [冻结Prompt](../prompts/phase-04/realistic-model-v1.md) | 原始冻结文本与两个不同含义的Hash |
| `backend/scripts/prepare_realistic_showcase.py` | 本地准备、单次文本审校显式开关、Hash与账本检查；无Neural4D调用 |
| `backend/tests/test_phase42_preparation.py` | 离线校验未授权/重复/超时/预算/模型调用边界 |
| `scripts/export_phase4_prompt.py` | 导出本轮真实原始需求、图像路径及一次文本调用许可 |

没有修改8个HTML、CSS、浏览器JS、RAG、Agent或Neural4D业务服务。只复用已有候选登记与审校服务；Phase 1～3及双风格协议、第一图像/GLB保持。

## 3. 实际测试与失败记录

| 测试 | 真实结果与范围 |
|---|---|
| 首轮准备/候选/API离线 | 55通过，0失败；[原JUnit](../evidence/phase-04/modeling/02-realistic/preparation-offline-tests.xml) |
| 导出脱敏专项 | 3通过，0失败；[JUnit](../evidence/phase-04/modeling/02-realistic/prompt-export-offline-tests.xml) |
| 最终本轮相关专项 | 58通过，0失败，1个既有Starlette弃用警告；[最终JUnit](../evidence/phase-04/modeling/02-realistic/preparation-final-offline-tests.xml) |
| 图片/冻结/额度只读核对 | Hash、快照像素与Prompt正文一致，正式资产数量及Neural账本未变；[结果](../evidence/phase-04/modeling/02-realistic/preparation-final-readback.json) |
| 8页本机HTTP | 8项HTTP200；文件、服务返回与准备基线908d9f5逐字节一致；不是本轮8页交互浏览器验收 |
| 候选实际浏览器 | 图像natural size793×1400、complete=true，0按钮，待审文案正确，窄/大屏无横向溢出，warn/error为空；[实际DOM记录](../evidence/phase-04/modeling/02-realistic/realistic-candidate-browser.json) |
| 本轮第二次真实GLB/Viewer | 未执行，没有第二模型文件 |
| 常见秘密格式扫描 | 新准备文件和公开导出未发现常见Key/签名对象URL；不宣称涵盖所有秘密格式 |

最终实际命令记录见 [运行命令](../evidence/phase-04/modeling/02-realistic/preparation-final-test-command.json)，使用先核实的独立GUID临时目录，未删除其他数据：

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_phase42_preparation.py backend/tests/test_phase4_candidates.py backend/tests/test_phase4_candidate_api.py backend/tests/test_phase4_prompt_export.py -q --basetemp <命令记录中的独立目录> --junitxml docs/evidence/phase-04/modeling/02-realistic/preparation-final-offline-tests.xml
```

准备工具的真实一次调用以公开对话为准，输出 [真实准备结果](../evidence/phase-04/modeling/02-realistic/realistic-preparation-result.json)。**不要在复现免费测试时删除单次标记、重复运行已执行的付费审校开关或覆盖历史输出。**

实际环境故障：本轮首个shell HTTP只读检查因沙箱socket限制 `WinError 10013` 失败；当时未完成HTTP核对。[失败记录](../evidence/phase-04/modeling/02-realistic/http-check-first-sandbox-failure.json)保留，取得本机网络权限后只重跑只读核对并通过。另有本机服务在隔夜后未运行，确认无待执行/运行Agent任务、真实生成关闭后，启动既有单worker FastAPI用于本地预览；没有因此触发模型调用。

归档检查器初版把所有已跟踪GLB都认作私有模型，误拦截仓库既有合法Duck夹具。实际核对该固定文件Hash、原清单与许可后，仅精确排除此夹具；私有真实模型、数据库、env检查与秘密模式扫描不放宽。[检查失败记录](../evidence/phase-04/modeling/02-realistic/archive-check-first-failure.json)保留，没有新增业务Bug或建模调用。

截图仅本机私有：`D:\京剧\.runtime\phase42-realistic-screenshots\candidate-review-preview.jpg` 与 `candidate-review-desktop.jpg`，不公开不明许可图片。

## 4. 费用、配额与保护

本轮一次真实DeepSeek文本审校：1425输入+35输出=1460 Token，1.3201秒，应用保守估算0.00262824元；现有LLM总预算3元、Reviewer范围预算0.5元内。没有读取或宣称实际账单，已保存用量与前后预算，不再调用。

本轮Neural4D API请求0、创建预留0、新建提交0、Credit增量0。唯一原创建仍SUCCEEDED、实际30积分，全局 **1/3 used、2 remaining**，unknown=0，默认真实生成false。SQLite原子限额、幂等和并发保护未改动，未清退第一次。

第二次当前费用待官方/账户确认。暂定用途与Prompt不是费用批准。先补齐权限、角色关联、当前参数/费用和单次人工批准，才可能经既有统一服务提交 `modelCount=1`。不存在按风格分开的配额。

## 5. Git与真实Prompt演进

独立分支仍为 `feature/phase4-neural4d`，没有合并main或推送远端；保留Phase 1～3完整历史。

| 实际提交 | 对应内容 |
|---|---|
| `3182bb6b7b1732a6663bd88daf87bc52f34ce60e` | 准备工具、单次文本审校保护与离线测试，公开需求导出选择器 |

报告、测试证据与公开对话由随后真实文档提交归档，不提前填写尚不存在的自身提交Hash。实际记录可用 `git log -1 --format=%H -- docs/reports/phase-04-realistic-preparation.md` 查询；最终回复提供已产生的实际Hash。

本轮需求原文 [14](../prompts/phase-04/14-realistic-showcase-preparation-request.txt)、路径选择 [15](../prompts/phase-04/15-realistic-image-path-reply.txt)、来源与单次文本审校许可 [16](../prompts/phase-04/16-realistic-source-and-one-review-authorization.txt)由真实session导出。公开工程摘要不冒充用户逐字发言；导出排除隐藏推理、系统消息、子Agent内部记录、图片二进制与常见密钥/签名URL。源会话含历史密钥，不可直接公开。

## 6. 待确认及停止状态

1. 图片只声明“百度公开资源”，尚无作者/原链接/比赛展示/上传/衍生许可。
2. 暂名提案尚未关联正式Phase 3角色，不能写成已完成四Agent设计。
3. 文本pass不认证冠式、行当或文化匹配；服饰RAG缺口仍在。
4. 第二次正式参数、当前费用和单次批准未完成。
5. 冠饰、袖布及未知背面整体重建风险HIGH；第二模型和实体手机验收待后续执行。

**当前授权状态WAITING_APPROVAL。停止在第二次真实提交之前。** 只有收到“批准第二次Neural4D写实主展示建模”，并满足所有已有门禁后，才允许考虑第2次；不能因普通“继续”跳过逐次批准或图片许可。第2次结束仍需人工验收，不自动创建第3次，不进入Phase 5。

2026-10-14后续用户仅授权最终Preflight，实际结果见 [第二次最终检查](phase-04-second-model-final-preflight.md)。输入与额度不变，10项本轮离线安全专项通过；READY_FOR_APPROVAL是材料状态，实际提交资格仍false。本轮没有再次文化审校、供应商请求、批准或预留。
