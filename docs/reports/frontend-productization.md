# AI戏韵工坊前端产品化改造

执行日期：2026-10-23。实现与免费回归已完成；**新增上下文的真实DeepSeek联测未执行，须单独授权**。不把离线Provider或浏览器Fetch替身当成真实模型回答。

## 审查与最小方案

实际仓库为`D:\京剧\京剧`，起始分支`feature/phase5-competition-delivery`，HEAD `c224e91afd2bc4bcf314629e67c96dd773ced978`，工作区干净。没有切分支、合并或推送。

原`/api/v1/chat`虽然接受conversationId，但未使用它，只有当前问题与当前证据；聊天只留页面内最多12轮，刷新丢失。Agent历史属于独立创作任务，不能拿来冒充聊天历史。工坊首屏还有大型页头、五项并列导航、常驻比赛导览及技术说明。导航最终生效宽度为1200px，不是早期报告的661px。

采用最小增量：保留5个功能面板及原有业务ID，用独立聊天控制器接管问答；新增仓库外JSON会话存储及三条接口，不迁移现有18业务表。前端继续原生HTML/CSS/ES Module，依赖和私有配置不变。

## 现在的使用方式

打开[AI戏韵工坊](http://127.0.0.1:8000/about.html#ai-workshop)，默认就是京剧问答。

- 左侧：真实会话列表、新建、分页、切换及恢复；手机可展开“历史会话”。没有历史时诚实显示空状态，不补造以前未保存的问答。
- 中间：按时间排列的问题与回答，逐条展开参考来源。内容全部使用文本节点，来源链接限制HTTP(S)且拒绝凭据URL。
- 底部：稳定的多行输入，Enter发送、Shift+Enter换行，中文输入法组词不误提交。错误保留输入，明确未发送的失败可手动重试同一幂等请求。
- “创作与数字资产”：保留角色创作、多Agent与独立任务档案、文化审校、人审、JSON、已有3D及企业需求。原模型深链接仍有效。
- 比赛演示导览按需展开；只读备用模式也拦截新建聊天会话，不改服务器配置。

页头压缩为名称与一句说明；服务检查移入“服务说明”；引用备查、独立测试素材和建模额度说明折叠。删除主区域的原型状态图例、重复入口、内部请求ID及冗长防御性文案。保留真实的未开放功能、历史标签、Q版内部用途、素材许可及建模关闭限制。没有删除测试、开发日志、历史报告或安全机制。

导航只修改共用`css/style.css`最后生效段：外框上限1200→1120px，布局间距22→14px，项目横向padding12→10px，列表gap3→2px、padding6→5px。1920视口实测菜单675.80→634.80px，减少41px（约6.07%），外框减少80px（6.67%）；手机宽度366.59px不变。其余7个HTML和原文化媒体文件未改。

## 真实会话与安全边界

新增`GET/POST /api/v1/chat/conversations`、`GET /api/v1/chat/conversations/{id}`。现有`POST /api/v1/chat`和四字段回答协议保持兼容；带conversationId才加载服务端持久历史，不接受前端自编历史作为上下文。

聊天保存在`RAG_DATA_DIR/chat-conversations/*.json`。读取不建目录；用户明确新建才创建会话子目录，RAG根目录必须已存在。每会话文件锁、原子替换与fsync；提交前保存pending，完成结果持久化幂等复用。未知结果不自动重试、不冒称成功，阻止该会话继续生成。损坏记录503并保留原文件，不重建。既有数据库、Qdrant、BGE和模型均不初始化或改写。

最近4轮成功问答作为有界上下文，每轮用户最多600、助手上下文最多1000字；短复指追问从这4轮回找最近完整主题补充检索。早期失败重试只能读取该轮之前的上下文。历史仅帮助理解追问，不作为新事实证据；引用ID只能来自本轮真实检索。无conversationId的旧调用仍单轮。每会话最多200轮/4MB。

沿用现有DeepSeek配置、预算与无自动重试机制；显式Origin须符合原白名单。仍为本机单用户共享实例，没有新增账号或多租户权限隔离，不宜直接公开聊天历史接口。会话记录含用户内容，应作为私有资源备份，不提交Git。

## 修改清单

| 文件 | 用途 |
|---|---|
| `about.html`、`css/ai-workshop-chat.css` | 问答优先布局、历史栏、折叠次级功能、稳定输入区 |
| `css/style.css` | 8页共用导航小幅收窄 |
| `js/ai-workshop/main.js` | 默认问答、业务面板与新聊天控制器衔接 |
| `js/ai-workshop/chat-controller.js`、`chat-contracts.js` | 会话恢复、消息/引用、安全校验、键盘与错误处理 |
| `js/ai-workshop/services.js` | 原聊天调用复用，新会话接口Fetch |
| `js/ai-workshop/demo-guide.js` | 备用演示中保护新建会话操作 |
| `backend/app/main.py`、`services/chat.py` | 原路由最小适配、有界上下文与本轮证据约束 |
| `backend/app/api/conversations.py`、`services/conversations.py` | 独立持久会话、原子保存、幂等与并发控制 |
| `backend/tests/test_conversations.py`、`scripts/phase2_frontend_test.mjs` | 新协议、安全、上下文及UI回归 |
| `README.md`、`docs/architecture/ai-workshop-contracts.md` | 当前能力、会话API和恢复/隐私边界 |
| 本报告、`docs/evidence/test-results/frontend-productization/`、`docs/prompts/frontend-productization/` | 实际证据与协作归档 |

## 测试与失败修复

实际命令、数量、截图、失败和复测见[测试报告](../evidence/test-results/frontend-productization/test-report.md)。各种脚本和工作包统计存在覆盖，不累加成所谓项目独立测试总量。

| 最终实际验证 | 结果 |
|---|---|
| 后端全量隔离测试 | 797通过、0失败、0跳过，134.31秒；已包含43项新会话测试 |
| 前端五组离线检查 | 问答32、Agent25、资产42、历史34、导览34，各组0失败；存在交叉覆盖 |
| Chrome三视口8页 | 改造前24组合、最终24组合均通过；1920×1080、1024×768、390×844 |
| 浏览器问答替身 | 13组通过，仅Mock；新建、追问、切换、刷新、引用、错误/重试、分页与手机长对话 |
| 原历史与次级能力 | Agent档案6组、导览/企业/备用入口5组通过 |
| 两个真实GLB | 桌面4组、触摸模拟2模型通过；写实鼠标349.9°/触摸392°，Q版鼠标453.7°/触摸300.7°，缩放、重置及Error恢复正常 |
| 本地HTTP与真实检索 | 20项GET通过；2题免费真实BGE/RAG各命中5片段，没有模型生成 |
| 原资源不变性 | 4业务库/18表、22任务/194事件/59产物/88步骤、109历史文本调用、Qdrant/BGE、两个兼容GLB及供应商原件/纹理均保持原基线；没有创建生产聊天目录 |

真实浏览器检查包括8页三视口、问答Mock交互、Agent档案及两个真实GLB。浏览器Mock仅替代接口响应；后端测试另外使用真实临时JSON文件和Mock Provider，验证持久化、重启、上下文隔离与并发，二者不冒充真实DeepSeek联测。

[桌面改造前](../evidence/test-results/frontend-productization/screenshots/before/about-1920x1080.png) · [桌面改造后](../evidence/test-results/frontend-productization/screenshots/after/about-1920x1080.png) · [手机改造后](../evidence/test-results/frontend-productization/screenshots/after/about-390x844.png)。Mock聊天截图另有分类；两个受限真实模型的截图保留私有证据，不随本次Git分发。

保留的真实问题：测试夹具同步异常断言使用错误；空历史加载时状态一直停留“正在检查”；分页失败恢复后按钮未恢复“更多会话”；历史读取误标知识服务ready；旧失败重试带入后续消息；模型调用后预算落账失败不能当成未发送。均按最小范围修正并保留早期结果。还根据手机截图把推荐问题改为空会话单行横滚，服务检查移出输入区，减少次要信息。

## 未执行与剩余风险

- **NOT_TESTED：本轮真实DeepSeek及新增多轮生成质量。** 旧Phase 2/3真实调用只证明历史单轮/Agent链路，不证明今天API可用，也不能替代新增上下文验收。建议另授权2次文本请求（一个问题与一次复指追问），按本地历史预算单价、两次约6000输入/1600输出Token规划约0.025元，预留0.05元；不是实时官方报价或供应商硬扣费上限，实际按Token和既有预算记录。未经授权不执行。
- **NOT_TESTED：实体手机、软键盘遮挡和真机性能。** 390px和CDP触摸/双指均为浏览器模拟。
- 有界上下文与规则式主题补全不等于长期完整记忆，超过窗口需重述主题；聊天无账号隔离。
- 两个GLB仍是不同角色/用途，不能用一个冒充另一个风格。Q版限内部技术用途；素材公开许可及已有模型细件/背面限制沿用原记录。

本轮付费API及Neural4D调用均0。建模仍已用2/3、剩1未使用，第三次取消、创建关闭。没有增加依赖、修改env、重建资源或进入其他阶段。

## Git与停止

本地提交、最终工作区检查与资源不变性见测试报告及本次协作索引。完成归档后停止，等待用户查看界面与决定是否单独授权实时上下文联测。

- `5a04491a74be88b583fdffa62284fe844b876737`：独立持久会话、服务端上下文、安全专项及接口约定。
- `cd18d85f0d265a06ebc210d77c430564294a7eb8`：问答产品布局、导航及前端测试适配。
- 报告/Prompt/证据另行本地归档；其自身Hash在实际提交后由最终`git log`提供，不预造自引用Hash。

测试服务已正常停止并释放8000端口。沿用VS Code“戏境 AI：一键运行”启动后查看上述页面；没有修改一键配置或要求重新安装。

最终文档核对：7份Markdown、121处本地链接全部有效；公开UTF-8敏感模式扫描982份、0命中；`git diff --check`通过。对应[链接检查](../evidence/test-results/frontend-productization/final-document-links.json)与[敏感模式扫描](../evidence/test-results/frontend-productization/final-secrets-scan.json)。环境文件和73份文化网页/媒体还与前一日既有基线Hash一致，见[注明日期边界的核对](../evidence/test-results/frontend-productization/invariants/env-and-culture-prior-baseline.json)。
