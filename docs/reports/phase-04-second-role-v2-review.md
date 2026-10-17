# 第二次写实主展示：四Agent角色方案人工审核

整理日期：2026-10-17。状态：**ROLE_REVIEW_PASSED_WAITING_HUMAN_ACCEPTANCE**。

用户已允许按修订稿运行一次现有Agent流程。该任务实际于2026-10-14 22:53:29～22:53:35（北京时间）完成四个阶段；本次恢复只读取原任务，没有重跑、重试或新增付费调用。第二次Neural4D模型尚未提交。

## 1. 本次待确认的具体方案

| 项目 | 实际角色JSON内容 |
|---|---|
| 名称 | 绛绣·戏韵 |
| 定位 | 原创京剧风格写实数字角色，用于比赛主展示；非历史人物或传统实体 |
| 比例与姿态 | 自然真人比例、完整站姿 |
| 服装 | 红金长袍，金色花鸟式纹理，下摆拖地 |
| 袖布 | 白色长袖布延展，手部部分遮挡 |
| 冠饰 | 蓝银冠饰、红色绒球、珠帘与两侧垂饰 |
| 原创边界 | 上述服饰、配色、冠饰标记为creative；不认证具体传统服制、行当或历史身份，不增加武器 |
| 有据文化介绍 | 一般京剧生、旦、净、丑分类与唱念做打知识，不用于认证上述原创外观 |

完整原结果见 [角色JSON快照](../evidence/phase-04/modeling/02-realistic/second-role-v2-result.json)，包含模型实际输出、引用与限制，尚未人工接受；没有将其改写成已发布资产。

## 2. 实际流程与文化审校

任务ID：`ca7007e7-e535-4b1f-a9b6-1932f10e20b4`；父任务：`a2a43828-773f-4f81-8908-5ff762ced750`。

| 阶段 | 实际结果 |
|---|---|
| Planner | completed；requiredEntities为空，原创名不再被当作传统实体 |
| Research | completed；真实本地RAG，一条一般行当查询取得一条有效证据 |
| Designer | completed；外观标原创，文化事实绑定实际证据ID |
| Culture Reviewer | completed；verdict=pass，issues/suggestions为空，needsHumanReview=true |

四份实际产物的Hash核对通过，父任务产物未改变。程序Schema与引用检查通过，不等于京剧专家审查、图像识别认证或版权审计。最初Planner误列原创名造成研究暂停的结果保留在 [执行记录](phase-04-second-model-execution.md)，没有删除、覆盖或假称原任务重试成功。

唯一引用为福建省文化和旅游厅公开问答 [《京剧的行当分类是什么？》](https://wlt.fujian.gov.cn/hdjl/wdxd/202112/t20211208_5790384.htm)。项目原创事实摘要及来源元数据已与当前知识库交叉核对，sourceId=`fujian-roles`，chunkId=`chunk_bb68cff95f29c3f7eece71c7e429050bdb95e603abe03cc46369d45dbae607a6`。它支持一般行当说明，不证明冠式、白色袖布、纹样或人物身份；未经京剧专家审核。

原任务现为`awaiting_confirmation`、sequence=11、canAccept=true，`userConfirmed=false`、`publicationAllowed=false`。只有用户接受这份具体结果后，才通过既有确认接口登记人审并进入正式资产关联；不直接改数据库状态。

## 3. 原图与冻结版本保持

输入仍为用户已选的 `D:\京剧\概念图1.jpg`，JPEG 793×1400，535664字节；2026-10-17重新计算的SHA-256：

`0170077ef813f95b2e0da4666f0a7919078d0a811ac04d61613e69a31a621095`

候选ID：`92e3d09f-57ce-49b2-8d57-1c0664a72689`，`realistic_showcase_candidate_v1`。没有替换图片、修改背景、复用旧Q版图或覆盖其他风格资产。

继续保留原 [冻结Prompt realistic_model_v1.0](../prompts/phase-04/realistic-model-v1.md)，正文文本Hash仍为 `777afaa81b1e696d98dac00e695727e17c40f38983691786d52b69a40f62fad2`。它与本次Designer输出的中文`visualPrompt`是两个记录，不能混称同一版本。

**差异说明：**本次中文角色描述有“舞台光效”，原冻结英文Prompt使用干净棚拍背景。本次不据此修改原图或英文冻结Prompt，不额外生成概念图；普通图生3D接口也不发送该文本Prompt，实际输入保持上述原图及无损规范化图。后续正式资产中的风格Prompt需独立记录其真实版本/Hash，不能冒用本英文冻结Hash。

来源为用户声明的“百度公开数据”。用户已声明允许比赛展示、上传Neural4D及3D衍生处理；具体作者/原始URL未提供，商业销售、公开模型再分发没有据此获准。旧候选初始许可记录保持历史状态，新增许可声明另存，不追溯改写。

## 4. 已发生费用、全局额度与风险

这次v2流程实际调用DeepSeek三次，共3253输入+474输出=**3727 Token**；依据既有保守价格快照估算 **0.0090436元**，不是供应商实时账单。本次2026-10-17恢复新增LLM调用0、Neural4D请求0、真实建模预留/提交0。

Neural4D固定全项目额度仍为 **已用1/3，剩余2次**。唯一第1次任务SUCCEEDED，无UNKNOWN/在途模型；本次没有申请或消耗第2次预留。创建默认关闭，3次SQL硬限制与幂等保护保留。

用户此前的“批准第二次真实生成”与“账户报价30积分，最高30积分”继续有效，不要求重复同一建模批准。实际提交前仍要重新核对当前官方参数、余额、模型状态、锁、配额和已确认输入；单次`modelCount=1`，不得自动重试创建。

已知视觉风险仍为：冠饰细杆/珠帘融合或缺失、白色袖布与身体融合、手部遮挡、长袍背面由模型推测、下摆和鞋履结构不完整。文化pass不会消除这些图生3D风险，也不代表已经取得第二次模型。

## 5. 本次人工审核事项与停止条件

- [ ] 接受上述实际角色JSON及“外观原创、一般文化事实有据”的边界。
- [ ] 保留已选原图及`realistic_model_v1.0`，不以中文角色描述另行更换图片或冻结Prompt。

当前两项没有代用户勾选。需要这次确认的依据是用户允许补齐角色JSON后“再由你确认”，以及实际任务的final_acceptance门禁；此前建模授权不被撤销。收到角色接受后，才继续已有单次授权范围内的正式资产与提交前检查。若要求修改，保留此快照，先评估修改是否需要额外文本调用及重新冻结输入。

详细只读验证与调用记录见 [原任务恢复证据](../evidence/phase-04/modeling/02-realistic/second-role-workflow-v2-outcome.json)。本轮仅归档实际结果，未创建第二次Neural4D模型；完成第二次后也必须停止等待验收，不进入第三次或Phase 5。

## 6. 本次归档检查

2026-10-17实际运行：`.venv\Scripts\python.exe -m pytest backend/tests/test_phase4_prompt_export.py -q`，**3 passed**；[JUnit](../evidence/phase-04/modeling/02-realistic/second-role-prompt-export-tests.xml)保留。这三项为离线脱敏测试，不是新的角色生成或第二次Viewer测试。

另外核对原提交时brief文件Hash、请求JSON未改变、原图Hash、冻结英文Prompt、54个本地Markdown链接、原任务待人审状态及Neural账本，见 [本地归档检查](../evidence/phase-04/modeling/02-realistic/second-role-v2-archive-checks.json)。临时检查脚本起初将目录链接错当文件，并假定通用账本表名；读取实际路径/Schema后修正检查脚本，失败原因保留，没有修改产品代码、业务数据库或安全规则来通过检查。
