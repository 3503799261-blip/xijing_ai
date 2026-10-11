# Phase 3 原始需求、Prompt 与真实演进证据

更新日期：2026-10-11（Asia/Shanghai）。本目录保存公开、可核查的开发链；不包含隐藏推理、API密钥、私有配置或编造的用户反馈。测试最终数量、费用和阶段验收由正式报告归档，本文不宣布 Phase 3 COMPLETE。

## 1. 原始需求和批准

| 文件 | 内容和来源 |
|---|---|
| [00-original-user-request.txt](00-original-user-request.txt) | 用户粘贴的完整 Phase 3 请求原文；来自本次附件，未改写成后来的开发方案 |
| [01-user-approval.md](01-user-approval.md) | 真实用户回复“Phase 3检查点A批准，开始Agent开发。”，批准对象与预算边界；不是阶段检查点B验收 |
| [02-public-conversation.jsonl](02-public-conversation.jsonl) | 当前会话的一次真实公开消息/工具过程导出；每条带原记录位置和时间，可检查先审查、方案、批准、开发与运行过程 |
| [03-export-metadata.json](03-export-metadata.json) | 导出时间、来源快照及对话/原需求SHA256、记录类型数量、过滤/脱敏与导出边界 |

原需求 SHA256：`d847a24b5b7ab7585592e4bcfc247bccffbab7d7189eb1f4cb62625ce5761069`，以 metadata 中的实际值及文件为准。公开会话是导出时点快照，不自动包含导出之后的回复、子 Agent 私有记录或最终验收；新导出应保留真实边界，不能补写“用户已经确认”或未来运行结果。

设计依据：[检查点A方案](../../reports/phase-03-agent-architecture-proposal.md)、[实际Agent架构](../../architecture/phase-03-agents.md)、[前端数据协议](../../architecture/ai-workshop-contracts.md)。方案描述计划，实际架构描述源码，测试证据描述已经运行的结果，三者不能互相冒充。

## 2. 当前角色 Prompt 与研究策略

| 角色 | 当前实际版本 | 历史和用途 |
|---|---|---|
| Planner | [agent_planner_v4.txt](../../../backend/prompts/agent_planner_v4.txt) | 保留v1/v2/v3；结构化意图、原风格、必要文化检索、指定实体、澄清；当前输出上限384 tokens |
| Researcher | `agent_research_v4`，见 [researcher.py](../../../backend/app/agents/researcher.py) | 真实RAG策略版本，不是LLM Prompt；保留检索不确定性、许可、稳定证据和窄范围实体/年份守卫 |
| Designer | [agent_designer_v3.txt](../../../backend/prompts/agent_designer_v3.txt) | 保留v1/v2；原始需求与真实证据交接，事实/原创拆项、用途与服饰类别正确、紧凑角色JSON |
| Reviewer | [agent_reviewer_v3.txt](../../../backend/prompts/agent_reviewer_v3.txt) | 保留v1/v2；逐断言核查，读取完整原创声明、不能编造遗漏；公开意见，不输出思维链或固定分数 |

模型执行记录只保留实际模型、usage、耗时、请求ID、Prompt版本/hash。版本不是随意改一个编号：Git保留真实文件演进，实际案例产物带采用的版本，旧错误记录不删除或改成新版本的结果。

## 3. 实际发生的演进和Bug

下表描述已发生的技术问题和采用的修正，不把助手检查写成用户反馈，不从失败记录推导出未经测量的“提高百分比”。

| 问题与发现方式 | 原因和实际修改 | 可核查位置 |
|---|---|---|
| 首版错误人物/1932年前提检索到相似人物和1959年相关资料 | 相似检索不等于用户前提真实。Planner增加必须从用户原文提取的requiredEntities；Research增加指定人物/年份缺失时暂停，不能替代 | [false-person首轮](../../evidence/test-results/phase-03/real-false-person-first.json)、[后续记录](../../evidence/test-results/phase-03/real-false-person-v2.json)；Planner/Research源码与v2 Prompt |
| 首版脸谱方案把宽肩等服饰细节绑定不支持它的净行资料，审校仍pass | 引用ID校验只能保证归属。Designer v2要求有据细节/创意拆项；Reviewer v2逐断言检查，另加保守服饰引用缺口守卫 | [脸谱首轮原始记录](../../evidence/test-results/phase-03/real-face-first.json)，v1/v2 Prompt与reviewer.py；未将这个误判当成正确性通过 |
| v2 Reviewer对已经声明原创的造型又声称“未标原创” | 只盯单个描述，忽略visualPrompt/creativeElements/limitations及interpretation。v3要求检查完整方案后准确定位实际冲突，不凭喜好拒绝明确的创意 | [脸谱v2记录](../../evidence/test-results/phase-03/real-face-v2.json)、[v3记录](../../evidence/test-results/phase-03/real-face-v3.json)；Designer/Reviewer v3 Prompt |
| 蟒/靠等单字实体被计划Schema拒绝，坏计划难定位 | requiredEntities最短长度原设2，不适合真实单字术语。改为1；Planner v3明确保留单字，384-token上限容纳紧凑结构；诊断只保存白名单路径/类型和脱敏usage，不保存raw文本 | [服饰首轮](../../evidence/test-results/phase-03/real-costume-first.json)、[v2](../../evidence/test-results/phase-03/real-costume-v2.json)、[v3](../../evidence/test-results/phase-03/real-costume-v3.json)；schemas.py、planner.py、planner v3/v4 |
| 模糊需求应先澄清，却因空researchQueries或空主题字段失败 | Schema原要求每次至少一查询，和“不要自行补定”的意图冲突。只有clarificationQuestions存在时允许空查询；Planner v4要求非空“待补充”和至少一条需求，比较多个术语时保留一个完整比较查询 | [澄清原记录](../../evidence/test-results/phase-03/real-clarify-v3.json)；TaskPlan条件校验与planner v4，不伪造原始模型错误内容 |
| 第二应用进程可能恢复第一进程仍在运行的任务 | 只有知识库锁不能保护任务恢复。新增agent-tasks-owner.lock，未获锁的进程diagnostic=AGENT_TASKS_LOCKED，不启动消费者或恢复他人任务；startup/exit finally清理资源 | supervisor.py、main.py与对应离线/进程回归测试；序号同时限制0～2^63-1，避免超大整数引发内部异常 |
| SQLite上下文只提交/回滚，连接没有因此自动关闭 | TaskStore和BudgetLedger使用明确contextmanager/finally close，避免连接/句柄泄漏。账本保留原历史，不靠重建绕过预算 | store.py、budget.py与连接释放测试；真实Git差异保存修复 |
| 已即时取消任务仍短暂显示“正在收尾” | cancelRequested对终结任务仍为true，反馈条件先判断该标志。改为优先判定state=cancelled；仅真实running取消才提示等待当前阶段结束 | agent-workflow.js的mutate反馈分支与离线取消测试；任务状态保持后端真实结果 |
| 创建响应丢失后原任务已推进，前端曾只接受waiting | 幂等重放合法返回当前状态。Creation校验接纳全部Task枚举；手动重试固定原body/key；事件游标与确认序号分开，旧状态不回退 | contracts.js/services.js/agent-workflow.js及明确离线测试；不是由用户发起的虚构Bug反馈 |

以上修复未把窄范围词汇守卫写成通用文化真值判断。已知有据ID合法但语义不符的失败保留；已明确原创的元素也不应无条件被拒绝。模型辅助审校、助手对照来源和专业人员审核分别记录，当前不得宣称已经京剧专家认证。

## 4. 怎样复核真实协作

1. 先核对原需求与用户批准，确认没有在检查点A前开发。
2. 对照架构、角色Prompt与Git差异，检查四角色实际输入/产物交接及Research调用真实RAG，而不是第四个模型聊天。
3. 查看真实案例的pollSamples、artifacts、Prompt版本、providerCalls、token/费用记录和引用映射，区分四阶段运行、文化审校与用户确认。
4. 保留first/v2/v3等旧案例，不只挑最终成功画面。资料不足、Schema失败、模型误判和受控暂停都在质量讨论范围内。
5. 离线pytest/DOM双桩只证明对应程序逻辑，不能替代真实模型或浏览器；浏览器截图、资源/控制台及阶段实测报告另行归档。
6. 以最终阶段报告记录实际执行范围和限制；不把一次辅助审校pass写成独立专家正确率，也不把测试工具接受一个案例写成用户已通过Phase 3正式验收。

## 5. 最后实际复测与边界

Planner v4的真实澄清复测保留在real-clarify-v4.json：提出问题后暂停，没有把空query当失败或继续虚构角色。Research v4在既有实体目录/语料元数据内有界补查，计划与补查合计最多三次；real-costume-v4-research-v4.json保留原漏检、实际分数及补查来源。靠的资料补齐后进入真实设计/审校，最终仍needs_revision，未强迫模型pass或开启下载。此前v1～v4漏检/Schema失败均保留。

最终网页任务1a18ff2c-93bb-47fb-8060-3de45378a721使用Planner v4、Research v4、Designer/Reviewer v3，四阶段已执行、当前待人工确认；手机刷新没有重发模型。最终后端213项、两套前端各25项、真实API14项与浏览器证据见阶段报告。测试执行者曾接受另一个测试任务并下载JSON，仅验证确认通路，不代表用户检查点B已通过。

私有Key文件不会用于对话导出，也不在本目录展示。当前开发没有伪造外部用户修改意见、隐藏思维链、Git时间或模型答案。最终检查点B通过之前，不自动开发Phase 4。
