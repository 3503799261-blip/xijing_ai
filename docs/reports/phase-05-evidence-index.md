# Phase 5 WP5 · 比赛证据索引

2026-10-29新增：[数字戏台/全站内容直达真实证据](../evidence/test-results/digital-stage-delivery/README.md)与[交付解释](digital-stage-delivery.md)。后端838包含新29；前端32/25/42/34/34/23及25/32；真实戏台14组、全站/旧功能46项、转换10组。各组口径独立，不与旧754相加。9页PDF已实检，视频由用户后续录制。后文仍为WP5当时材料审查，不伪装成当天重测。

核对日期：2026-10-22（Asia/Shanghai）；源码基线 `61064b0842e5f3789c01b107dd0b2a3f45c55adb`，分支 `feature/phase5-competition-delivery`。本文件把具体能力、原始记录、范围和真实提交关联起来；**WP5进行材料与证据核对，没有重新执行754项后端、真实问答、Agent生成或建模。** 本轮文档验证单独见[WP5测试报告](../evidence/test-results/phase-05-wp5-test-report.md)。

建议核查顺序：先看[统一事实表](phase-05-project-facts.md)，再按下表打开原始JSON/XML，最后以对应日期的报告解释失败、恢复和边界。旧报告中的“未接入”“待批准”“712项”等是当时快照，不能脱离时间直接作为当前结论。

## 1. 分类与统计规则

| 分类 | 含义 |
|---|---|
| VERIFIED | 对本行明确限定的结论，有存在且可核实的证据；不扩大到未测设备或当前云服务 |
| PARTIAL | 有真实证据，但覆盖、使用权限或当前环境验证不完整 |
| NOT_VERIFIED | 没有足够实际证据，不能因代码、页面或测试文件存在就认为通过 |
| NOT_APPLICABLE | 本次范围明确不适用，并写出原因 |

原始脚本中的PASS有不同含义。例如数据库修复前“4观察PASS”是成功复现缺陷，不是安全性通过；故障注入出现503/网络错误是保留的预期现象，不能说所有日志从无错误。

后端pytest、前端DOM替身、本地HTTP断言、浏览器检查组、CLI观察与文档校验不是同一统计单位。历次全量彼此重复，专项可能已经在全量中；**不相加成项目独立用例总数，不将Mock当真实外部API调用。**

## 2. 重要能力与证据对应

表中的提交是实现或证据归档定位；完整Git演进保留在当前分支，可用 `git show <提交> -- <文件>` 和 `git log -- <文件>` 复核。相关短Hash均在WP5审查时通过Git对象与祖先关系核查。

| ID / 能力 | 证据文件、实际内容及结果 | 分类与限制 | Git提交 |
|---|---|---|---|
| E01 原有8页及文化页面 | [WP4最终24视口对](../evidence/test-results/phase-05-wp4/layout-final.json)：8页×1920×1080/768×1024/390×844；[数据库追加正常浏览器](../evidence/test-results/phase-05-wp4-db-repair/normal-model-browser.json)：8页、图片、导航和两真模型4组通过 | VERIFIED：真实本地浏览器；移动/平板是视口模拟，未认证所有浏览器/设备；媒体取消事件保留 | `834483d`、`0955d0f`；原8页基线 `04b2c57` |
| E02 真实资料、Embedding及检索 | [初次入库](../evidence/test-results/phase-02-ingest-initial.json)、[真实生命周期](../evidence/test-results/phase-02-real-lifecycle.json)、[WP4真实CPU资源探针](../evidence/test-results/phase-05-wp4/resource-probe-final.json)、[20题向量/混合比较](../evidence/test-results/phase-05-wp4/phase-02-retrieval-wp4-isolated-restored-comparison.json)：12单元/35片段/512维，本地持久化、重复/更新/重建/重开有独立记录 | VERIFIED：真实本地模型/数据库；资料为助手核对原创摘要，不是原站全文授权；20题非人工Gold，调参集非独立盲测，不称人工Recall@5 | `a95c774`、`84b1d23`、`834483d` |
| E03 真实LLM问答与引用 | [20题HTTP原记录](../evidence/test-results/phase-02-answers-rag20-final-hybrid.json)：20成功、18模型生成/2无证据控制响应；[引用/语义核查](../evidence/test-results/phase-02-answers-rag20-final-hybrid-assistant-review.json)：37引用结构映射有效，助手核查18支持/2不足，人工审核0；[5对直接LLM与RAG](../evidence/test-results/phase-02-direct-vs-rag-five.json) | PARTIAL：历史真实调用可核实；不是今日云API可用、专家准确率或20对完整对照。引用ID有效不等于每个结论的语义支持自动正确 | `f7dee30`、`8a5499e`、`a95c774` |
| E04 多Agent实际工作流 | [所有真实案例含失败](../evidence/test-results/phase-03/real-cases-summary.json)、[真实API运行](../evidence/test-results/phase-03/api-http-checks.json)、[当时浏览器](../evidence/test-results/phase-03/browser-test-report.md)；保存澄清、资料不足、审校需修改和最终待确认等实际分支 | PARTIAL：真实历史+最新离线回归，不能当当前实时执行；Researcher做真实本地检索，正常四阶段只有三次LLM；没有专家审校准确率 | `381d62e`、`903fe1d`、`81dd451`、`c89e63e` |
| E05 Agent历史档案只读 | [WP2完整JUnit](../evidence/test-results/phase-05-wp2/pytest.xml)内23专项、[34项前端](../evidence/test-results/phase-05-wp2/frontend-history.json)、[40次本地GET/190断言](../evidence/test-results/phase-05-wp2/http-attempt-04.json)、[最终6组浏览器](../evidence/test-results/phase-05-wp2/browser-attempt-verified.json)：22原任务与只读SQLite逐项比对 | VERIFIED：分页、筛选、详情、事件、产物、引用、人审、关联；缺失字段不补造，历史不重跑。698含23，不计721 | `9e3516d`、`f8a1f47`、`60e1590` |
| E06 角色JSON及文化审校 | [Phase 3已确认JSON](../evidence/test-results/phase-03/browser-confirmed-character.json)、[第二角色v2审核](phase-04-second-role-v2-review.md)、[模型关联审计](../evidence/phase-04/final-acceptance/asset-ledger-readback.json)、[WP4归属不变性](../evidence/test-results/phase-05-wp4-db-repair/provenance-after.json) | PARTIAL：保存JSON/审校/来源可核实；文化审校是模型辅助+程序门禁，非专业专家结论；原创外观不能当考据事实 | `638028e`、`60bfc38`、`0955d0f` |
| E07 人工确认记录 | [WP2真实22任务GET](../evidence/test-results/phase-05-wp2/http-attempt-04.json)、[第二次已接受角色报告](phase-04-second-role-v2-review.md)、[来源及人审不变性](../evidence/test-results/phase-05-wp4-db-repair/provenance-after.json)；确认sequence及保存状态随任务展示 | VERIFIED：证明发生过用户接受与保存，不替代专家或权利人许可；备用演示只读，不再次提交确认 | `81dd451`、`638028e`、`f8a1f47`、`0955d0f` |
| E08 Q版真实GLB | [首次真实恢复与技术验收](phase-04-first-internal-modeling.md)、[最终台账](../evidence/phase-04/final-acceptance/asset-ledger-after-free-tests.json)、[WP4原件Hash](../evidence/test-results/phase-05-wp4-db-repair/physical-final-comparison.json)；task `bb074c31-1905-45b6-b763-22d065ddc616`，30积分、只创建一次 | PARTIAL：真实生成/本地技术验收有证；内部非公开、无正式角色绑定，不能因此公开分发或纳入对外比赛录像 | `bf96dd6`、`0955d0f`；细分恢复提交见[原报告](phase-04-first-internal-modeling.md) |
| E09 写实真实GLB及角色谱系 | [第二次真实生成、30积分、兼容修复](phase-04-second-model-execution.md)、[最终关联](../evidence/phase-04/final-acceptance/asset-ledger-readback.json)：任务 `8735f32e-097e-488c-962f-f11e64af7741`，asset `9e2b42e1-bbad-4a2f-ab1b-aeda18015dee`，model `1fa0b519-caf4-4009-aec2-f20b0f9a3523` | PARTIAL：模型与绛绣原任务、确认图、Prompt版本/Hash可追溯；用户许可声明不等于原作者书面许可审计，商用/公开GLB再分发未验证 | `c873c31`、`2b08f36`、`e72d237`、`60bfc38` |
| E10 260°以上鼠标旋转、缩放、Reset | [WP4数据库修复后正常模型浏览器](../evidence/test-results/phase-05-wp4-db-repair/normal-model-browser.json)：写实325.9°、内部Q453.7°，真实GLB，按钮/滚轮缩放、Reset，缺失风格→原风格恢复均通过 | VERIFIED：真实Chrome桌面连续拖拽样本，不是视频/GIF；不是模型审美/动画/骨骼认证 | `0955d0f`；Viewer变更 `e36c1e5` |
| E11 手机触摸及双指 | [WP4追加CDP触摸JSON](../evidence/test-results/phase-05-wp4-db-repair/touch-browser.json)：390×844，两模型382.6°/300.7°、双指缩放及Reset，2组通过 | PARTIAL：实际CDP触摸事件和真GLB，但不是实体手机、Safari或移动GPU；实体手机NOT_VERIFIED | `0955d0f` |
| E12 Loading/Ready/Error与恢复 | [WP3故障浏览器](../evidence/test-results/phase-05-wp3/browser-attempt-final.json)、[WP4追加触摸/故障](../evidence/test-results/phase-05-wp4-db-repair/touch-browser.json)：拦截原GLB的文件GET产生Error，解除后显式重读同一ID/Hash到Ready | VERIFIED：文件故障是受控响应替身，真实模型Ready与恢复实际浏览器完成；不能声称所有日志零错误或供应商重试成功 | `e36c1e5`、`45d1dcc`、`0955d0f` |
| E13 双风格与缺失资产提示 | [资产前端42项](../evidence/test-results/phase-05-wp4-db-repair/frontend-phase4_frontend_test.json)、[真实风格切换](../evidence/test-results/phase-05-wp4-db-repair/normal-model-browser.json)：绛绣切chibi显示未生成，回realistic恢复原文件 | VERIFIED：风格架构与切换不生成已测；现有Q版内部模型不是绛绣Q版，不可拿两模型宣称同角色双风格均已生成 | `2bb1b69`、`e36c1e5`、`0955d0f` |
| E14 六步比赛导览 | [WP3最终34项](../evidence/test-results/phase-05-wp3/demo-exit-final-34.json)、[WP4导览8组](../evidence/test-results/phase-05-wp4-db-repair/guide-browser.json)：开始、前后/跳过/退出、目标入口、刷新、窄屏 | VERIFIED：静态步骤说明不代表AI进度，进入不触发生成；仍可直接用真实功能，不强制通关 | `e36c1e5`、`76dbba0`、`74b3e6e` |
| E15 只读备用与异常降级 | [WP3实际测试报告](../evidence/test-results/phase-05-wp3-test-report.md)、[WP4导览故障JSON](../evidence/test-results/phase-05-wp4-db-repair/guide-browser.json)：超时/断网/401/429/503/坏数据、空历史/404、资产失联与恢复；输入保留，无自动生成重发 | PARTIAL：错误响应由明确浏览器替身模拟，正常历史/GLB真实读取；不是外部API恢复。备用依赖本地后端/私有资源，只保护本页，刷新/新页退出，不停止后台任务 | `e36c1e5`、`76dbba0`、`45d1dcc`、`0955d0f` |
| E16 数据库路径与初始化安全 | [修复前真实复现4观察](../evidence/test-results/phase-05-wp4-db-repair/baseline-final.json)、[41项专项](../evidence/test-results/phase-05-wp4-db-repair/targeted-final-pytest.xml)、[显式CLI9检查](../evidence/test-results/phase-05-wp4-db-repair/explicit-init-cli.json)、[错误配置现场](../evidence/test-results/phase-05-wp4-db-repair/field-misconfigured-probe.json) | VERIFIED：误配/缺库不建空库，显式新安装仍能建三个业务库；不创建/清零全局Neural账本。有效但错误的另一份DB身份仍需人工核对 | `ae2783e`、`452a0c2`、`0955d0f`、`61064b0` |
| E17 Agent损坏隔离与恢复 | [坏库现场11观察](../evidence/test-results/phase-05-wp4-db-repair/field-corrupt-probe.json)、[坏库真GLB4组](../evidence/test-results/phase-05-wp4-db-repair/field-corrupt-model-browser.json)、[恢复10观察](../evidence/test-results/phase-05-wp4-db-repair/field-restored-probe.json)、[四场景42汇总](../evidence/test-results/phase-05-wp4-db-repair/field-final-summary.json) | VERIFIED：坏Agent保持原字节，历史503、8页200，独立catalog正常时真GLB仍可看；恢复有效库后重启读22任务；catalog坏时不绕过服务 | `452a0c2`、`0955d0f`、`61064b0` |
| E18 正常启动、重启、新venv和恢复 | [新venv实际安装](../evidence/test-results/phase-05-wp4/cold-install-attempt03-result.json)、[包实际来源](../evidence/test-results/phase-05-wp4/cold-env-attempt03-runtime-verification.json)、[受控资源副本](../evidence/test-results/phase-05-wp4/resource-copy-manifest.json)、[新venvViewer](../evidence/test-results/phase-05-wp4/models-cold-browser.json)、[修复后再启动](../evidence/test-results/phase-05-wp4-db-repair/normal-02.json)与[正常关闭](../evidence/test-results/phase-05-wp4-db-repair/normal-stop-02.json) | PARTIAL：同机隔离副本/全新普通venv实测；原机器已有Python、网络、BGE与合法成品；不是跨机器/完整空白电脑/10分钟保证；首次BGE下载未在WP4重跑 | `834483d`、`3b40aa2`、`0955d0f` |
| E19 桌面/平板/手机视口 | [8页×3视口24项](../evidence/test-results/phase-05-wp4/layout-final.json)、[最新窄屏历史/导览](../evidence/test-results/phase-05-wp4-db-repair/guide-browser.json)及[E11触摸](../evidence/test-results/phase-05-wp4-db-repair/touch-browser.json) | PARTIAL：Chrome/SwiftShader实际桌面与模拟视口；实体手机、真实平板和其他浏览器未验证 | `834483d`、`0955d0f` |
| E20 实际历史费用与当前不新增 | [Phase 2账本快照](../evidence/test-results/phase-02-api-usage.json)、[Phase 3费用](../evidence/test-results/phase-03/api-usage-final.json)、[两模型最终台账](../evidence/phase-04/final-acceptance/asset-ledger-after-free-tests.json)、[WP4全表不变性](../evidence/test-results/phase-05-wp4-db-repair/state-after.json) | PARTIAL：历史Token/估算费用和模型扣费有证；应用估算不是实时供应商账单或硬限；107文本记录/18建模相关操作是本地历史，不证明今日余额/鉴权；WP5新增调用0 | `a95c774`、`c89e63e`、`bf96dd6`、`0955d0f` |
| E21 Git与工作包演进 | [WP1](phase-05-work-package-01.md)、[WP2](phase-05-work-package-02.md)、[WP3](phase-05-work-package-03.md)、[WP4追加修复](phase-05-work-package-04.md)、[本轮总结](phase-05-work-package-05.md)；WP5审查实际核对分支/HEAD及祖先，不只读报告文字 | VERIFIED：代码/证据/文档分步本地提交保留；人工验收依据用户本次指令及已有批准原话，Git存在本身不等于评委正式验收；未推送不声称远程可审查 | WP1 `f58888b/ea0f4fc`；WP2 `9e3516d/f8a1f47/60e1590`；WP3 `e36c1e5/76dbba0/45d1dcc/74b3e6e`；WP4 `84b1d23/834483d/3b40aa2/ae2783e/452a0c2/0955d0f/61064b0` |
| E22 业务数据、模型与资源不变性 | [WP4逻辑全表](../evidence/test-results/phase-05-wp4-db-repair/state-after.json)、[角色/审校/原件](../evidence/test-results/phase-05-wp4-db-repair/provenance-after.json)、[物理Hash最终](../evidence/test-results/phase-05-wp4-db-repair/physical-final-comparison.json)；18业务表、22任务、26BGE文件、5知识/向量文件、14资产文件比较 | VERIFIED：以上是WP4历史实际比较；本次WP5前后只读完整性核对另外记入[本轮验证](../evidence/test-results/phase-05-wp5/validation-result.json)，不将本行冒称新的全套回归 | `0955d0f`、`61064b0`；WP5提交见[总结](phase-05-work-package-05.md) |
| E23 Prompt、失败及公开协作记录 | [Phase 2](../prompts/phase-02/README.md)、[Phase 3](../prompts/phase-03/README.md)、[Phase 4](../prompts/phase-04/README.md)、[Phase 5](../prompts/phase-05/README.md)；[WP4修复真实Prompt](../prompts/phase-05/15-wp4-database-repair-user-request.txt)、[原失败及修复报告](../evidence/test-results/phase-05-wp4-test-report.md) | VERIFIED：公开原话、执行记录和失败均有范围说明，排除秘密/隐藏推理；摘要不冒充完整原始对话，不推断未保存内容 | 各阶段归档 `a95c774/c89e63e/bf96dd6/0955d0f`；本WP5按实际发生再记录 |
| E24 当前云API、专家Gold、真机及跨机 | [当前已知限制](phase-05-project-facts.md)、[WP4未测说明](../evidence/test-results/phase-05-wp4-test-report.md) | NOT_VERIFIED：不得用本地health、Mock、旧供应商响应、CDP或同机恢复替代。真人讲稿排练和正式视频/PDF/PPT成品也不能由自动化停留推定已完成 | 不存在可证明完成的提交 |
| E25 图片供应商、商业交付与公开再分发 | [Phase 4最终功能边界](phase-04-final-acceptance.md)、[素材许可盘点](phase-05-asset-provenance-and-permissions.md) | NOT_VERIFIED：图像生成Provider尚未实现；没有真实企业客户/订单/收入/商业成品或完整公开分发许可审计。不得从“有企业入口”推断已交付 | 功能边界 `bf96dd6`，不是不存在能力的成功证据 |
| E26 第三次真实建模 | [用户取消原话](../prompts/phase-04/23-two-model-acceptance-third-cancelled.txt)、[最终验收](phase-04-final-acceptance.md) | NOT_APPLICABLE：用户决定不执行，未创建/不扣次数/不记失败；当前2/3余1仍关闭，不因WP5材料需要而生成 | `bf96dd6` |

## 3. 测试统计校准表

下表是**已执行历史**的口径核对，不是本轮重新运行。为避免把报告数字当事实来源，WP5另解析完整JUnit中的testcase与原JSON字段；数据库专项的 `(classname,name)` 集合在完整JUnit中缺失数为0。

| 历史阶段/实际证据 | 真实数量与范围 | 禁止的错误表述 |
|---|---|---|
| [WP1完整隔离JUnit](../evidence/test-results/phase-05-wp1/offline-final.xml) | 675通过/0失败/0跳过；前端25/25/36、HTTP8、浏览器4组另计层次 | 不与后续698/754累加，不把675当真实API次数 |
| [WP2完整JUnit](../evidence/test-results/phase-05-wp2/pytest.xml) | 698通过，其中历史专项23；前端历史34、原前端25/25/36；真实HTTP每成功轮40GET/190断言 | 698+23不能变721；多轮同组不能增加独立覆盖量 |
| [WP3完整JUnit](../evidence/test-results/phase-05-wp3/pytest.xml) | 698通过；前端问答25/Agent25/历史34/资产42/导览34，浏览器8组+模型4组 | Mock POST不是新模型回答，698不是比WP2额外698独立用例 |
| [WP4原最终712](../evidence/test-results/phase-05-wp4/backend-final.xml)及[新venv712](../evidence/test-results/phase-05-wp4/backend-clean-env.xml) | 两环境各712通过，其中资源专项14；同套测试在不同环境执行 | 不能计算712×2独立测试；14已含712 |
| [WP4数据库追加完整JUnit](../evidence/test-results/phase-05-wp4-db-repair/full-final-pytest.xml)、[隔离结果](../evidence/test-results/phase-05-wp4-db-repair/full-final-isolation-result.json) | 754 testcase，754通过/0失败/0跳过/0收集错误；120.20秒终端，JUnit120.136秒，计时范围不同 | 不是所有阶段测试总和，也不是754次真实供应商调用 |
| [数据库专项最终JUnit](../evidence/test-results/phase-05-wp4-db-repair/targeted-final-pytest.xml)、[专项隔离JSON](../evidence/test-results/phase-05-wp4-db-repair/targeted-final-isolation-result.json) | 41通过；完整754中对应类恰41，专项节点全部包含 | **不能754+41=795**；专项重跑不增加41独立场景 |
| [显式CLI](../evidence/test-results/phase-05-wp4-db-repair/explicit-init-cli.json) | 9检查通过，实际启动CLI子进程，缺参数不创建、首次3库、二次验证、原字节保持、无Neural账本 | 不是另外9项pytest，也不在生产初始化或清零 |
| [现场四场景](../evidence/test-results/phase-05-wp4-db-repair/field-final-summary.json) | corrupt11/restored10/misconfigured11/recovered10，共42观察断言，0失败/跳过 | 不是42个独立故障种类，不与754/CLI9累计为“805测试” |
| [追加五组前端JSON所在目录](../evidence/test-results/phase-05-wp4-db-repair/) | 问答25、Agent25、历史34、资产42、导览34，DOM/Fetch替身与静态检查 | 不能当五组真实API质量评价 |
| [追加浏览器与触摸](../evidence/test-results/phase-05-wp4-db-repair/touch-browser.json) | 普通模型/8页4组、导览/降级8组、触摸/故障2组；坏库真模型另4组 | 不是14/18种设备；没有实体手机结果 |
| [WP4自动化排练](../evidence/test-results/phase-05-wp4/rehearsal.json) | 正常10步300.071秒、故障4步40.038秒；正常每步至少30秒阅读停留 | 不是已验证真人5分钟讲解、MP4成片或正式比赛规定 |

修复前失败、辅助中断和格式提示仍按[WP4原始报告第10节](../evidence/test-results/phase-05-wp4-test-report.md)保留：初次710通过/3失败，后续50项复测；专项首次38 setup errors、一次中断无结果；物理比较曾因元组/列表差异误报，统一序列化后全相同。旧失败不能删掉，最终成功也不能倒写成初次即通过。

## 4. 两模型身份与文件指纹

下列来自原件/兼容文件实际盘点；Hash是标识，不是文件公开下载许可。GLB本体和概念图不在公开Git，新克隆不能仅凭Hash恢复它们。

| 模型 | 已有任务/用途 | 兼容GLB字节与SHA-256 | 供应商原件字节与SHA-256 |
|---|---|---|---|
| Q版技术模型 | task `bb074c31-1905-45b6-b763-22d065ddc616`；内部非公开；model `3777a880-fc8c-4766-aade-948d20c6b8f0`，没有正式characterId/assetId | 8,827,324；`bf9c808c15dbf5464ee67df1cdb3f64f9b2c6b3cd4ee41ecb8a6470a0554654a` | 26,600,184；`8ef5de8a2f96fbbee9eea66737187e4a2087f88867830891a41464a473d47885` |
| 写实绛绣·戏韵 | task `8735f32e-097e-488c-962f-f11e64af7741`；比赛主展示候选范围；源Agent任务 `ca7007e7-e535-4b1f-a9b6-1932f10e20b4` | 15,158,668；`5a021ac6338009615e6ea232c5b9001eef6f4cc91d9d87c3eeeb5307526bdfd5` | 18,266,484；`51fc687e0bde5fdb9074ba4560601057e17e9239f111fd2bc9e0d6601c26260e` |

两模型各一次新建、各30积分。后续修MIME/纹理兼容、原任务查询和安全下载不是重新建模；原几何和原件保留。冻结文字Prompt是用户审核及版本凭据，普通图生3D提交为图片+参数，不宣称Neural4D消费该文本。

## 5. 截图、原始记录和可访问性

- WP1 [私有截图/脚本Hash](../evidence/test-results/phase-05-wp1/browser-private-screenshot-manifest.json)、WP2 [截图清单](../evidence/test-results/phase-05-wp2/screenshot-manifest.json)、WP3 [截图清单](../evidence/test-results/phase-05-wp3/screenshot-manifest.json)、WP4 [截图清单](../evidence/test-results/phase-05-wp4/screenshot-manifest.json)、数据库追加 [19张截图Hash](../evidence/test-results/phase-05-wp4-db-repair/screenshot-manifest.json)是真实文件追踪，图像本体留私有`.runtime`。不能把清单存在描述为评委已经能在GitHub直接看到截图。
- WP4原归档110份文字、数据库追加86份文字，各[原归档清单](../evidence/test-results/phase-05-wp4/archive-manifest.json)及[追加清单](../evidence/test-results/phase-05-wp4-db-repair/archive-manifest.json)保留执行辅助、失败、源与脱敏Hash。它们不是110/86项应用测试。
- JSON/XML在Git中可核查，但本地文件链接不等于站点公开HTTP服务。`backend/docs/knowledge`等不在静态白名单；比赛可提供受控审阅材料，不能为展示而公开整个私有目录。
- 私有模型、数据库、概念图、用户需求/历史内容与签名URL不打包进公开代码。本轮敏感模式检查范围和局限见[WP5文档验证](../evidence/test-results/phase-05-wp5-test-report.md)，不宣称对任意未知秘密的绝对保证。

## 6. 证据缺口与下一步人工事项

1. **正式规则**：仓库中的用户原始需求不是独立官方通知；比赛名称/组别/截止/正式格式/公开范围仍需用户提供原通知或可信链接。见[要求与证据对应表](phase-05-requirements-evidence-map.md)。
2. **素材许可**：Q版保持内部非公开；写实用户声明、作者/原网页与可出示授权凭据须分开记录。原网页媒体/字体、GLB再分发/商用范围待核实，不能因测试PASS就公开上传。见[许可盘点](phase-05-asset-provenance-and-permissions.md)。
3. **设备与环境**：实体手机、跨机器完整恢复、当前外部API、真实ACL、公网部署未验证；数据库恢复需重启，Schema有效但身份错误的库仍需人工比对。
4. **文化质量**：专家事实复核、人工Gold、独立盲测及人物/服饰专业考据尚缺证据；不能把程序引用校验率包装成知识准确率。
5. **演示成品**：提供的是可编辑讲稿和已执行自动化排练证据，真人讲解、正式视频/PDF/PPT是否需要及其格式应先依官方规则确认；没有制作的成品不标READY。

本索引支持WP5材料审阅，不宣布未知官方要求全部满足。最终范围、待办与本轮提交见[WP5总结](phase-05-work-package-05.md)，完成后等待人工验收，不自动新建工作包或公开资源。
