# 录屏证据预览：技术、人机协同与应用价值

**真实历史开发记录节选；本次不重新调用API，不实时生成代码或模型。** 所有节选可回到原文件和Git核对，不是仿制聊天截图。代码摘录仅去掉公共缩进，长行可横向滚动；讲解字段摘要和原始记录明确分开。

推荐在VS Code按Ctrl+Shift+V打开本文预览，Ctrl+B收起侧栏、Ctrl+J收起终端。录制时从A到G依次滚动，无需运行命令、填密钥或点击生成。

## A．人的要求 → DeepSeek服务端实现（04:00—04:35）

需求要点整理：真实知识库检索、真实API、可追溯引用、密钥仅后端保存。原始完整要求：[docs/prompts/phase-02/00-original-user-request.md](../../docs/prompts/phase-02/00-original-user-request.md)；批准开发版本：[docs/prompts/phase-02/03-approved-development-v3.md](../../docs/prompts/phase-02/03-approved-development-v3.md)。这是需求摘要，不冒充逐字AI对话。

当时AI公开回复的原文节选（2026-10-09T15:23:50.531Z，公开导出记录source_line=1182；不是本次新生成）：

> 代码中的问答仍只返回未接入提示；现有加载、错误和引用位置可以复用，但接入真实 API 时需要补上请求锁、超时、响应校验，以及每轮回答与引用的关联。

原始公开消息：[Phase 2公开协作快照](../prompts/phase-02/01-checkpoint-a-public-conversation.jsonl)。

只展示无密钥模板字段：
```dotenv
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
DEEPSEEK_THINKING_ENABLED=false
```

以上来自[.env.example](../../.env.example)；不要打开实际私有.env。

实际请求代码（已有实现，不在录制时执行）：
```python
self.ledger.reserve(request_id, messages, limit)
payload = {'model': self.settings.deepseek_model, 'messages': messages, 'thinking': {'type': 'disabled'}, 'stream': False, 'max_tokens': limit, 'temperature': 0.2}
```
```python
async with httpx.AsyncClient(timeout=self.settings.deepseek_timeout_seconds, transport=self.transport) as client:
    response = await client.post(self.settings.deepseek_base_url + '/chat/completions', headers={'Authorization': 'Bearer ' + self.settings.deepseek_api_key.get_secret_value()}, json=payload)
```
来源：[backend/app/providers/llm.py](../../backend/app/providers/llm.py)。`limit`为服务端受控输出上限，不把它当作下方首探实际输出Token数。

## B．真实首探 → 检索证据与引用校验（04:35—05:05）

以下为**2026-10-10历史小请求**字段节选；仅证明当时连通和真实用量，不代表今天新调用，也不代表完整RAG质量评价。
```json
{
  "model": "deepseek-flash",
  "success": true,
  "httpStatus": 200,
  "usage": {
    "prompt_tokens": 11,
    "completion_tokens": 3,
    "total_tokens": 14,
    "prompt_tokens_details": {
      "cached_tokens": 0
    },
    "prompt_cache_hit_tokens": 0,
    "prompt_cache_miss_tokens": 11
  },
  "elapsedSeconds": 1.5959,
  "thinkingRequested": "disabled",
  "reasoningContentPresent": false
}
```
原始脱敏文件：[docs/evidence/test-results/phase-02-provider-probe-success.json](../../docs/evidence/test-results/phase-02-provider-probe-success.json)。

已有问答链路：网页 → FastAPI → BGE/SQLite/Qdrant检索 → DeepSeek组织回答 → 后端引用ID校验 → 网页。

实际引用别名校验：
```python
if any(alias not in aliases for alias in generated.usedCitationIds): raise ValueError('Unknown citation alias')
generated.usedCitationIds = [aliases[alias] for alias in generated.usedCitationIds]
canonical_content = generated.model_dump_json()
```
来源：[backend/app/services/chat.py](../../backend/app/services/chat.py)。Prompt和检索调优的真实演进见[docs/prompts/phase-02/04-development-evolution.md](../../docs/prompts/phase-02/04-development-evolution.md)，不把一次连通探测当作所有答案正确的证明。

## C．人工批准 → Neural4D异步任务与安全额度（05:05—05:50）

用户当时批准原话：

> 批准第二次真实生成

出处：[docs/prompts/phase-04/18-second-model-user-approval.txt](../../docs/prompts/phase-04/18-second-model-user-approval.txt)；角色、图片、Prompt、费用确认过程见[docs/reports/phase-04-second-model-execution.md](../../docs/reports/phase-04-second-model-execution.md)。

流程：确认输入与费用 → SQLite原子预留 → 创建单模型任务 → 查询原任务 → 安全下载 → 本地GLB/Viewer验证。

真实原子事务与幂等检查（摘自reserve方法）：
```python
db.execute('BEGIN IMMEDIATE')
policy = self._policy(db)
previous = db.execute('SELECT * FROM neural4d_creation_attempts WHERE idempotency_key=?', (key,)).fetchone()
if previous:
    if previous['payload_hash'] != digest or previous['purpose'] != purpose or previous['approval_id'] != approval_id:
        raise ServiceError('NEURAL4D_IDEMPOTENCY_CONFLICT', '相同幂等键绑定不同输入或批准，已拒绝。', 409)
    return self._record(previous, newly_reserved=False)
if policy['historical_used'] is None:
    raise ServiceError('NEURAL4D_HISTORY_UNVERIFIED', '全项目历史占用尚未核实，禁止创建真实模型。', 403)
```
来源：[backend/app/assets/usage.py](../../backend/app/assets/usage.py)；全局硬上限为3次**新建模型HTTP提交尝试**，不是全部状态查询也只准3次。

实际供应商发送路径：
```python
self.usage.mark_started(attempt_id)
started, status, error, actual_credits = time.perf_counter(), None, None, None
try:
    async with self.client() as client:
        response = await client.post(BASE + '/generateModelWithImage', headers=headers,
                                     data=parameters, files={'image': ('concept.png', image, mime)})
```
来源：[backend/app/providers/neural4d.py](../../backend/app/providers/neural4d.py)。展示代码不会执行它；真实创建目前关闭，用户取消了第三次。

以下是多份已脱敏原始文件的选定字段汇总，**不是一份伪造的供应商原始响应**：
```json
{
  "recordScope": "2026-10-17 historical records; merged selected fields, not one raw API response",
  "character": "绛绣·戏韵",
  "modelCount": 1,
  "providerTaskId": "8735f32e-097e-488c-962f-f11e64af7741",
  "creationResponseState": "SUBMITTED",
  "recordedCreditsForSecondModel": 30,
  "laterLocalRecoveryOutcome": "LOCAL_RECOVERY_VALIDATED",
  "laterAttemptStates": {
    "SUCCEEDED": 2
  },
  "usedCreationAttempts": 2,
  "remainingCreationAttempts": 1,
  "generationDefaultEnabled": false
}
```
原始提交：[docs/evidence/phase-04/modeling/02-realistic/second-real-submission.json](../../docs/evidence/phase-04/modeling/02-realistic/second-real-submission.json)；后续恢复：[docs/evidence/phase-04/modeling/02-realistic/second-local-glb-recovery.json](../../docs/evidence/phase-04/modeling/02-realistic/second-local-glb-recovery.json)；最终核对：[docs/evidence/phase-04/modeling/02-realistic/second-final-readback.json](../../docs/evidence/phase-04/modeling/02-realistic/second-final-readback.json)。

`SUBMITTED`仅是提交成功；完成由后续恢复/验收记录支持。30积分为当时第二次实际扣费，不是今日报价。第二次模型是“绛绣·戏韵”，**不是第一部分戏台里的杜丽娘、穆桂英或周瑜**；后者为用户提供素材。这里不展示内部Q版图片。

## D．人的反馈 → AI修复 → 实测 → Git（05:50—06:30）

真实用户反馈：

> 现在这个项目有一个问题，就是3D模型互动只能互动舞台。人物模型不能点击

来源：[docs/prompts/stage-character-click-fix/README.md](../../docs/prompts/stage-character-click-fix/README.md)。原代码并非所有三角拾取失效；确定问题为卡片无聚焦反馈、远景目标小、触摸点选与旧测试覆盖不足。AI协助定位并实施修复，用户决定需求与验收。

实际卡片点击修复：
```javascript
button.addEventListener('click', () => {
  showCharacter(character.id);
  if (state === 'ready' && character.available) renderer?.focusCharacter(character.id);
  if (!character.available) renderState('error', '这位人物的本地模型暂不可用，请恢复对应已有文件后重新读取。');
});
```
来源：[js/ai-workshop/digital-stage.js](../../js/ai-workshop/digital-stage.js)；另在[js/ai-workshop/stage-viewer.js](../../js/ai-workshop/stage-viewer.js)加入姓名入口、按下锁定、整段拖动/多指取消。原模型、数据库、遮挡判断及配额不变。

真实检查结果字段汇总：
```json
{
  "realBrowserInteraction": {
    "passed": 26,
    "failed": 0,
    "physicalPhone": "NOT_TESTED; CDP touch simulation"
  },
  "stateAndPageRegression": {
    "passed": 13,
    "failed": 0
  },
  "scope": "Two separate test groups; not an independent project-wide total"
}
```
原始浏览器记录：[docs/evidence/test-results/stage-character-click-20261030/browser-result.json](../../docs/evidence/test-results/stage-character-click-20261030/browser-result.json)；补测：[docs/evidence/test-results/stage-character-click-20261030/guard-result.json](../../docs/evidence/test-results/stage-character-click-20261030/guard-result.json)。不是现场重新执行的进度，未用Mock冒充真实GLB。

实际Git提交输出：
```text
91aa556 fix(stage): make character selection visible and touch reliable
8ce2cfe test(stage): archive real character click and touch regression
```
完整修复及失败记录：[docs/reports/stage-character-click-fix.md](../../docs/reports/stage-character-click-fix.md)。

**人的需求/批准/反馈和验收 → AI辅助实现 → 真实测试 → 版本留痕。** 这是一条已经发生的协作链，不把本文现在的排版说成当时的原始聊天界面。

---

## E．应用对象与现有功能基础（06:30—06:55）

| 应用对象 | 现有功能基础 | 可开展的试点任务 |
|---|---|---|
| 文化机构 | 八个主题页面、底部内容直达、带来源问答 | 用机构核定资料组织线上科普入口，让访客寻找栏目、提问并核对来源 |
| 学校与研学 | 行当、脸谱、音视频与已保存问答，可展示资料不足提示 | 围绕一个主题安排“观察—提问—查来源”，辅助教师讲解 |
| 文旅展陈 | 人物近看、场景旋转缩放、剧目说明与问题带入 | 使用获准素材制作互动展项原型，观察访客能否完成指定探索任务 |

**试点目标：** 用真实内容、明确受众与任务完成情况检验价值；当前已有可操作流程，尚未开展客户效果评估。

依据：[首页主题入口](../../index.html)、[工坊界面](../../about.html)、[问答与会话实现](frontend-productization.md)、[戏台交付记录](digital-stage-delivery.md)。

## F．三项有据的整合特色（06:55—07:25）

| 整合特色 | 已实现的具体行为 | 代码或报告证据 |
|---|---|---|
| 统一内容入口 | 全站底部关键词及同义词直达；文化栏目和人物分类共用入口，未知内容可转问答草稿 | [站内导航代码](../../js/site-navigator.js)、[交付报告](digital-stage-delivery.md) |
| 有依据的问答与受审创作 | 本地检索、回答与引用按会话保存；Agent分工规划/研究/设计/审校，人工确认保留结果，不等于文化零错误 | [回答校验](../../backend/app/services/chat.py)、[会话保存](../../backend/app/services/conversations.py)、[Agent架构与实际验收](phase-03.md)、[问答界面报告](frontend-productization.md) |
| 从三维观察回到知识探索 | 人物本体、姓名和卡片可近看；人物介绍与关联问题同步，点击后只预填问题，由用户决定发送 | [戏台交互代码](../../js/ai-workshop/digital-stage.js)、[人物点击实测](stage-character-click-fix.md) |

**工程依据：** 人工确认、失败记录、实际测试与Git版本支持核对和持续修订。以上按本项目已实现的整合特色表述。底部导航使用本地匹配；三维人物保持静态，镜头观察不等于人物表演。

## G．商业路径方案、工程基础与落地待办（07:25—07:50）

| 商业路径（方案） | 已完成工程基础 | 正式落地待办 |
|---|---|---|
| 机构内容定制 | 可复用的主题网页、知识来源记录、带引用问答和历史会话 | 核定客户资料与答复范围，完成内容审核和使用授权 |
| 展项与网页适配 | 真实GLB展示、分类及近看交互；有独立浏览器与状态回归记录 | 取得可商用素材，按目标设备验证体验并明确交付范围 |
| 部署与内容维护 | 源码与Git历史、无密钥模板、依赖清单、运行恢复指南及实际测试 | 验证目标部署与恢复，补齐账号隔离等安全要求，按客户约定验收 |

**当前定位：** 具备进一步交付验证的工程基础，可面向上述方向开展小范围试点；目前没有客户、订单或收入案例。

**授权与验收：** 当前新舞台及杜丽娘、穆桂英、周瑜仅限比赛、非商用。正式商业项目需更换或补齐合法授权；当前本地单用户环境仍需目标部署、安全及客户验收验证。

依据：[需求与企业入口现状](phase-05-project-facts.md)、[源码与运行说明](../../README.md)、[配置模板](../../.env.example)、[后端依赖](../../backend/requirements.txt)、[可选工具依赖](../../tools/README.md)、[部署与恢复说明](phase-05-deployment-and-recovery.md)、[当前素材与测试范围](digital-stage-delivery.md)、[最新交互实测](stage-character-click-fix.md)。

**让文化有据，让数字入戏。**
