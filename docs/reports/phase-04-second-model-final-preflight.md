# 第二次真实建模最终检查

后续实际状态（2026-10-17）：本页READY_FOR_APPROVAL为当时材料快照。之后用户已批准生成/费用/图像使用并接受新角色，真实第2次单模型完成、30积分，Viewer技术PASS，人工验收PENDING。固定全局已用2/3、剩1；本页不能再次授予创建权，参见 [最终执行报告](phase-04-second-model-execution.md)。

检查日期：2026-10-14，Asia/Shanghai。实际只读记录时间：2026-10-14T13:39:41.954916+00:00。

**结论：READY_FOR_APPROVAL（人工审核材料就绪）。** 此状态不代表 `READY_FOR_SUBMISSION`，不授予任何发送权。当前 `submissionEligible=false`、真实生成开关false；许可、正式角色关联、费用和逐次授权仍需补齐。

## 1. 本次内容

| 项目 | 当前记录 |
|---|---|
| 角色名称 | 绛绣·戏韵，用户本轮选定的名称；不是已登记的Phase 3角色ID |
| 用途 | 比赛主展示 / Competition Main Showcase |
| 模型类型 | Realistic Digital Character |
| 风格 | `realistic` / 写实国风 |
| 资产版本 | `realistic_showcase_candidate_v1` |
| 候选ID | `92e3d09f-57ce-49b2-8d57-1c0664a72689` |
| 预计消耗 | 第2次Neural4D新建模型HTTP提交尝试，未预留 |
| 当前额度 | used=1/3，remaining=2，next=2 |
| 单次模型数量 | `modelCount=1`；正式发送前仍须服务端核对 |
| 当前第二次任务ID | 无，未提交 |
| 当前Credit余额 | 本轮没有查询，无法确认；1/3是次数，不是Credit余额 |
| 第二次预计费用 | 待当前官方/账户确认，`neural4d_expected_credits=null`，不套用第一次30积分 |

## 2. 图片和Prompt检查

当前实际读取 `D:\京剧\概念图1.jpg`：793×1400 JPEG，535664字节。

```text
原文件SHA-256：0170077ef813f95b2e0da4666f0a7919078d0a811ac04d61613e69a31a621095
预览PNG SHA-256：7b8fb1a42bf79d0210c1571e65ae92d856fa73761d42d9cd044836764aad4d45
Prompt版本：realistic_model_v1.0
候选Prompt快照Hash：80a893202c9d09e508ceba0a2796a3e2b1aab54f812c6790b23177f18bde3e33
Prompt正文UTF-8 Hash：777afaa81b1e696d98dac00e695727e17c40f38983691786d52b69a40f62fad2
```

检查结果：原图Hash符合用户指定值，原始不可覆盖快照相同；无损PNG解码像素一致，没有修改背景或外观。冻结Prompt版本未变，文档正文与数据库快照逐字一致，`frozenForReview=true`、`approved=false`。

原JPEG与标准化PNG是不同字节文件，Hash不能混用。未来正式批准包必须明确实际上传文件及其Hash；本轮没有上传、预处理或自动替换输入。普通图生3D现有接口没有正/负文本Prompt字段，冻结文本用于人工审核与追踪，不声称已经传给供应商。

## 3. 全局额度、旧任务与重复保护

使用固定 `D:\京剧\.runtime\neural4d-usage.sqlite3`，SQLite `mode=ro` 与 `query_only=ON`，未实例化生产UsageManager或执行recover/approve/reserve。

| 检查 | 实际结果 |
|---|---|
| 硬上限 | 数据库max_attempts=3，代码MAX_CREATION_ATTEMPTS=3，SQL触发器保留 |
| 已核查的外部历史 | 0，保留此前用户核查与一次性登记，不重置 |
| 本地创建记录 | 1，SUCCEEDED |
| 原任务ID | `bb074c31-1905-45b6-b763-22d065ddc616` |
| 占用 / 已发起 / 预留 | 1 / 1 / 0 |
| 剩余 / 下一次序号 | 2 / 2 |
| 未完成建模任务 | 0 |
| UNKNOWN / PENDING_RECONCILIATION | 0 / 0 |
| creation_halted | 0；默认生成仍关闭，不等于有发送许可 |
| 单次批准记录 | 仅1条，已用于第一次；未消费批准0条 |
| 当前候选已有创建 | 0，没有第二次任务或预留 |
| 真实HTTP操作历史 | create1、query6、download2、verify2，合计11条；本轮新增0 |
| 已记录建模费用 | 第一次实际30积分；本轮新增0 |

重复保护实现保持：SQLite `BEGIN IMMEDIATE` 原子预留，幂等键与批准ID唯一、同输入重复检查、不可重置发送权、失败/未知不返还、未知状态跨风格全局暂停、固定账本及3次硬限。没有替本次生成幂等发送权、持久化新批准或占用新次数。

## 4. 创建锁检查

现有 `neural4d-usage.owner.lock` 通过只读 `rb` 句柄进行非阻塞独占竞争，返回 `HELD_BY_ANOTHER_HANDLE_EXPECTED_EXCLUSION`。证明当前竞争无法绕过已有锁；没有释放其他进程的锁，文件大小/修改时间及账本前后相同。

本轮离线专项同时验证第二worker被拒、重启不重发、同attempt并发只产生一次Mock请求、跨风格共享3次上限、同幂等键返回原记录、发送权原子领取、费用变化/未核实阻断。**10项通过，0失败，1个既有Starlette弃用警告**。测试仅使用临时SQLite、显式MockTransport和禁止DNS的夹具，不是供应商真实调用或生产配额预留。

可选CIM进程身份检查被沙箱拒绝，因此不声称核实了持锁进程身份；正式执行时仍须由既有授权服务取得其自身owner锁及有效鉴权。首次校验工具尝试Hash锁文件内容被Windows拒读，改为不读写内容的锁探测，保留 [原失败记录](../evidence/phase-04/modeling/02-realistic/second-preflight-harness-failure.json)，没有放宽锁或恢复生产任务。

## 5. 拟定参数与尚未完成的门禁

从现有写实服务端预设只读取得以下参数，**尚未批准、冻结为真实发送包或发送**：

```json
{
  "modelCount": "1",
  "mesh_quality": "standard",
  "faceNum": "500000",
  "disablePbr": "0",
  "onlyGenerateMesh": "false",
  "enableImageEnhancement": "false"
}
```

以下事项仍未通过，不因本报告或角色命名自动解除：

1. 图片仅声明“百度公开资源”；具体作者及比赛展示、供应商上传、3D衍生、再分发范围尚未确认。现有非空许可说明与人工图片接受不等于程序已证明权利。
2. 候选 `characterId/assetId/sourceTaskId=null`，未关联完整四Agent、审校通过且人工确认的正式结果；`imageAccepted=false`、`modelEligible=false`。第一模型的内部验证豁免不适用于比赛主展示。
3. 本次当前费用、余额、接口与参数仍需按官方/账户核实；本轮没有鉴权/余额请求，未使用历史余额作新确认。
4. 尚未取得本次单独批准、有效后端管理授权及正式发送者鉴权；生成开关false。不创建批准或额度记录来假装已就绪。

在上述条件和人工授权完成前，**真实提交保持阻断**。未来批准后仍须重新执行最新输入/状态/费用检查，不能直接复用本报告绕过门禁。

## 6. 视觉风险与提交后验收计划

重点风险：凤冠意象细杆及珠饰融合/缺失，水袖式袖布与身体融合，未知背面推测。另检查袖口遮挡的双手、下摆和鞋履。整体重建风险HIGH；详细边界见 [风险报告](phase-04-realistic-model-risk.md)。

第二次任务提交后必须逐项实际记录，不预填为通过：

- [ ] 原任务生成成功、任务ID及实际Credit记录完整。
- [ ] 安全获得模型，保存格式、大小、SHA-256；GLB结构、纹理、材质完整。
- [ ] Viewer真实加载为Ready，Loading和Error有清晰提示。
- [ ] 鼠标连续拖拽超过260°，缩放及Reset正常。
- [ ] 实体手机触摸拖动及双指缩放，保存实际设备证据；窄视口不能替代手势。
- [ ] 人脸、凤冠意象、红金服饰、水袖式袖布、身体比例、手部和背面人工验收。
- [ ] 用户验收后停止，不进入第三次。

请求未知、超时或失败：停止，不自动重试、不返还次数，不新建第二个任务。模型成功而Viewer失败：先修复下载/文件/Viewer，禁止再次建模。

## 7. 证据、Git与停止

实际只读输入、政策、旧任务、锁与前后账本见 [Preflight JSON](../evidence/phase-04/modeling/02-realistic/second-final-preflight.json)；本轮离线结果见 [JUnit](../evidence/phase-04/modeling/02-realistic/second-final-preflight-offline-tests.xml)。上一轮候选/审校/58项测试仍在 [准备总结](phase-04-realistic-preparation.md)，不是本轮重新执行。

原代码与Phase 1～3不修改；本轮仅增加报告、脱敏检查/离线证据与真实Prompt归档。保持 `feature/phase4-neural4d`，不合并main或推送。报告提交的实际Hash用 `git log -1 --format=%H -- docs/reports/phase-04-second-model-final-preflight.md` 查询，最终回复提供已产生的提交，不预填自身Hash。

本轮Neural4D请求0、DeepSeek请求0、真实预留0、新建提交0、费用增量0。全局仍已用1/3、剩2，未创建第二次任务。

**第二次Neural4D真实建模已准备完成，等待人工授权。** 此处指审核材料完成。必须取得“批准第二次Neural4D写实主展示建模”并满足第5节全部门禁后才能执行。现在停止，不自动提交，不进入第3次或Phase 5。
