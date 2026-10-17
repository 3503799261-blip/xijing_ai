# Neural4D第二次真实建模授权申请

日期：2026-10-14。状态：**WAITING_APPROVAL**。本页是待审材料，不是建模批准记录。

后续状态更新（2026-10-14）：用户已回复“批准第二次真实生成”，并声明图片有比赛展示/上传/3D衍生许可、确认账户报价30积分及最高30积分。单次生成批准已保留，无需重复索取；当前为 **HUMAN_AUTHORIZED_WAITING_VALID_ROLE**。本轮获准的一次Agent流程停在真实研究门禁，未取得正式角色结果，尚未创建后台批准或预留。原待审表保留为此前快照，最新事实见 [执行记录](phase-04-second-model-execution.md)。

最新状态（2026-10-17）：获准的v2原任务已完成四个Agent，审校pass，状态为 **ROLE_REVIEW_PASSED_WAITING_HUMAN_ACCEPTANCE**。本次只读恢复，没有重跑。具体角色JSON待用户接受，审核内容见 [新角色审核表](phase-04-second-role-v2-review.md)。下方旧待审表继续保留历史；不撤销已有单次建模批准/30积分上限，也不代用户接受尚未展示的新角色。Neural4D仍已用1/3、剩2，第二次预留/创建均未发生。

## 1. 本次准备内容

| 项目 | 待审内容 |
|---|---|
| 角色提案 | 绛绣·戏韵（暂名），原创京剧风格数字角色候选 |
| 方案ID | `realistic_character_proposal_v1` |
| 正式角色ID / 任务ID | 均未关联，不能用本轮提案冒充已确认Phase 3角色 |
| 资产版本 | `realistic_showcase_candidate_v1`，SECOND_REALISTIC_SHOWCASE版本1 |
| 候选ID | `92e3d09f-57ce-49b2-8d57-1c0664a72689` |
| 风格 | Realistic / `realistic` / 写实国风 |
| 用途 | Competition Main Showcase候选；非已授权商业IP |
| 输入原文件 | `D:\京剧\概念图1.jpg`，793×1400 JPEG |
| 原文件SHA-256 | `0170077ef813f95b2e0da4666f0a7919078d0a811ac04d61613e69a31a621095` |
| PNG预览SHA-256 | `7b8fb1a42bf79d0210c1571e65ae92d856fa73761d42d9cd044836764aad4d45` |
| Prompt版本 | `realistic_model_v1.0`，已冻结供审核，未批准 |
| 候选Prompt快照Hash | `80a893202c9d09e508ceba0a2796a3e2b1aab54f812c6790b23177f18bde3e33` |
| 当前额度 | 1/3 used，remaining=2 |
| 计划占用 | 第2次新建模型HTTP提交尝试，`modelCount=1` |
| 预计费用 | 待Neural4D当前官方或账户确认 |
| 当前第二次供应商任务ID | 无，未提交 |
| 创建开关 | false |

只读本机预览：<http://127.0.0.1:8000/api/v1/assets/candidates/92e3d09f-57ce-49b2-8d57-1c0664a72689/preview>。预览没有生成按钮，不发送图片到供应商。原图与截图仅本机私有保留。

## 2. 审核事项

- [ ] 概念图和原文件/预览Hash确认。
- [ ] 角色暂名与“原创京剧风格”定位确认，不误写传统人物或行当。
- [ ] 补齐具体作者/来源及比赛公开展示许可。
- [ ] 确认允许图片上传Neural4D与3D衍生处理，明确公开模型再分发范围。
- [ ] 通过既有流程关联正式、已审校并人工确认的Phase 3角色结果。
- [ ] 确认冻结Prompt `realistic_model_v1.0` 及其边界。
- [ ] 确认当前实际参数、输入格式与费用。
- [ ] 接受高风险：冠饰细杆/珠饰、水袖式袖布融合、长袍背面推测；中风险：手部与鞋履。
- [ ] 同意消耗全项目第2次机会，成功、失败或未知不自动返还。
- [ ] 明确单次授权：**“批准第二次Neural4D写实主展示建模”**。

所有项目当前均未代用户勾选。单次文字批准不能替代缺失的图片许可、角色关联、费用与服务端门禁。

## 3. 提交前硬检查

取得单次批准并补齐必要条件后，重新检查固定全局账本、旧任务状态、创建锁、剩余次数、图片Hash、最新冻结版本、当前价格及余额、后端鉴权与幂等键。使用同一个服务入口原子预留；单次 `modelCount=1`，禁止前端/Agent直接访问供应商。

普通图生3D接口当前没有正/负文本Prompt字段。本Prompt用于意图、版本与人工审核记录，不能把它描述为已传给Neural4D的参数。最终供应商参数须按当时官方接口核实，不通过重复创建试错。

## 4. 成模后的人工验收

- [ ] 供应商原任务完成，安全下载到真实模型，记录任务ID/格式/大小/Hash。
- [ ] GLB结构、材质与纹理通过本地检查，Viewer为Ready。
- [ ] 鼠标连续水平拖拽至少260°，缩放、按钮与重置正常。
- [ ] 实体手机拖动和双指缩放有实际证据，或如实保留未测项。
- [ ] Loading/Error提示正常；失败可诊断而非空白。
- [ ] 冠饰、袖布、手部、衣层、下摆、足部和背面达到已接受的风险范围。
- [ ] 用户人工验收后停止，不自动申请或执行第3次。

若请求未知或超时，停止、保留额度、人工核查；若模型成功但Viewer失败，先修复文件或Viewer，不再次创建。

## 5. 本轮实际检查与交付

图片可读取、原图与预览像素一致、候选版本和Prompt冻结已保存。一次真实文本Reviewer返回pass并保留 `needsHumanReview=true`。首轮55项、最终专项58项相关离线测试通过，候选浏览器预览正常；这不是第二次真实成模或Viewer验收。Neural4D请求/创建预留/提交均0，全局仍1/3。最终JUnit与8页HTTP逐字节核对见 [只读检查结果](../evidence/phase-04/modeling/02-realistic/preparation-final-readback.json)。

本轮工具及测试：`backend/scripts/prepare_realistic_showcase.py`、`backend/tests/test_phase42_preparation.py`。报告清单：[角色方案](phase-04-realistic-character-proposal.md)、[文化审查](phase-04-realistic-cultural-review.md)、[风险](phase-04-realistic-model-risk.md)、[预算](phase-04-second-model-budget.md)、[冻结Prompt](../prompts/phase-04/realistic-model-v1.md)。实际命令、测试证据与提交索引见 [准备阶段总结](phase-04-realistic-preparation.md)。

**本轮到此停止。未创建第二次任务，Phase 4仍处于未完成的检查点B前准备状态，不进入Phase 5。**
