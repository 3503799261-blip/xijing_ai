# 绛绣·戏韵 Agent需求修订稿 v2

初稿状态：**DRAFT_NOT_EXECUTED**（2026-10-14，保留初稿历史）。最新状态：**EXECUTED_ONCE_WAITING_ROLE_ACCEPTANCE**（2026-10-17只读恢复）。用户另行允许一次后，本稿下方请求于2026-10-14实际提交一次，四阶段完成、文化审校pass，仍需用户接受具体角色结果。

原提交时的本文文件Hash为 `848b2174097fb191ca1cc2db96ede87bf49e8aad6e1a39c6f1f702a7064154d6`，可从原提交证据及Git历史追溯。本次只更新状态说明，不改下方JSON请求。实际任务 `ca7007e7-e535-4b1f-a9b6-1932f10e20b4`；[授权原文](21-second-agent-v2-one-run-approval.txt)、[单次提交证据](../../evidence/phase-04/modeling/02-realistic/second-showcase-agent-v2-submit.json)、[具体结果人审](../../reports/phase-04-second-role-v2-review.md)分别保存，不把初稿假写成事前成功。

原任务 `a2a43828-773f-4f81-8908-5ff762ced750` 只执行了Planner和真实RAG研究；原规划把原创名称及未认证的袖布类型列入requiredEntities，研究因此停在资料不足。1条实际研究查询获得1条有效京剧行当基础证据，并非检索服务无结果；没有Designer/Reviewer结果。

本稿保留用户名称、原图Hash与realistic_model_v1.0，不改Phase 3代码、知识库、门禁、阈值或原任务记录。只有另行允许一次现有流程后才执行新子任务，不自动重试付费调用。

## 实际提交的完整请求（与初稿正文一致）

```json
{
  "style": "舞台角色",
  "parentTaskId": "a2a43828-773f-4f81-8908-5ff762ced750",
  "requirements": "创建原创京剧风格写实数字角色，名称固定为绛绣·戏韵，用途比赛主展示。此名完全是原创命名，不是历史人物或传统实体。\n本任务没有要求核实存在性的指定传统实体；TaskPlan.requiredEntities必须是空数组[]，不得放入角色名、京剧、冠饰或袖布。TaskPlan.researchQueries只使用一条：京剧行当入门分类与表演基础。研究仍需真实RAG，缺证时停止，不允许修改检索阈值或编造引用。\n以下都是参考图视觉观察和原创设定，服饰、颜色与冠饰必须标creative：自然真人比例、完整站姿，红金长袍、金色花鸟式纹理，蓝银冠饰、红色绒球、珠帘与两侧垂饰，白色长袖布延展，手部部分遮挡，下摆拖地。保持原图主体，不增加武器或其他配饰，不认证具体服制、冠式、历史身份或传统行当。\n在visualElements中只加入有真实证据的一般京剧行当知识说明作为文化介绍，并使用实际证据ID；不要把这条一般知识当作上述原创服饰的认证。严格区分evidence_based和creative，引用真实且不过度推断。\n只运行现有Planner、Research、Designer和Culture Reviewer一次，结果交给用户确认。不生成图片或3D，不调用Neural4D，不改变已冻结的realistic_model_v1.0。"
}
```

## 付费及验证边界

最多3次DeepSeek文本调用：Planner上限384、Designer上限800、Reviewer上限400输出Token；Research为已有本地RAG。仍受既有0.5元范围与3元总预算双重保护。若再次澄清、缺证、校验失败、超时或模型错误，保存原结果并停止，不自动新建或重复调用。

初稿验证目标是规划不再将原创参考元素当作传统实体、真实证据支持一般文化介绍、完整角色及审校有效；初稿时尚未验证。2026-10-17恢复显示以上结构/来源检查已通过，结果限于本次实际任务，不代表普遍解决所有Planner错误。即使流程完成，也不能代用户确认新方案，不自动提交第二次Neural4D。
