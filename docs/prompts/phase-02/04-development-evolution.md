# Phase 2 真实协作与Prompt演进

日期：2026-10-09～10，Asia/Shanghai。本文件是已发生过程的说明索引，不冒充逐字对话；逐字用户Prompt和公开消息/工具快照另存。没有隐藏推理或补造用户反馈。

## 需求与授权

1. 用户最初要求先只读审查和检查点A；实际核对10个重点文件、Phase 1基准、工作区、环境及预留协议，形成方案文档。
2. 用户V3.0明确批准FastAPI、SQLite、Qdrant local、BGE small、DeepSeek flash和3元应用测试预算，授权正式开发。此后直接实现，没有重复索要架构批准。
3. 用户误发凭证后被提示撤销并仅私有env配置；用户确认撤销旧Key。首次实际检测仍为空，探测没有发出付费请求；用户再次确认保存后一次低Token探测成功。公开协作快照凭证字符串脱敏，真实新Key不被读取打印或提交。
4. 用户两次“继续”推进原Phase 2任务，没有授权Phase 3、主分支合并或真实图像/3D后端。

## 实际实现与校验

| 演进 | 实际动作 | 对应证据 |
|---|---|---|
| 后端边界 | 同源白名单静态服务，私有配置/数据库/模型移出仓库根，统一错误/真实状态/单worker锁 | startup、API离线测试、HTTP protectedPaths |
| 真正语料 | 12个公开机构来源的原创事实摘要，35短段，source_checked_by_assistant；不把来源全文或AI未经核查内容标官方 | documents、source-checks、provenance |
| 真正Embedding | 固定snapshot、CPU512维、真实tokenizer、SQLite/Qdrant稳定ID、原子generation切换 | model-download、ingest、real-lifecycle |
| 初次语义检索 | 阈值0.62漏了红色问题，开发集降低为0.57；5题补充集中仍有虚构人物误取相近证据 | first-ingest-default、threshold057比较 |
| 首版真实问答 | Probe成功后真实问答，5题首版、网页首个回答；长chunk ID进入正文、组合题证据不全 | first-five-v1、first-browser-answer、qa-first-raw-citation-id截图 |
| Prompt v2 | 正文不展示内部ID；E1–E5引用别名由程序映射；所有子项/年代/人物前提都需证据，否则uncertain；资料永不当指令 | rag_answer_v1/v2、别名错误测试、rag20-v2及holdout-five-v2 |
| 标题上下文实验 | 编码标题+章节+正文能改善行当题，却让黑色题退步；实际保留失败结果，继续用正文向量 | embedding-context-first-title-section-context057 |
| 浏览器泛问问题 | “脸谱颜色有什么寓意”只取到正净，模型诚实说明不足；不是成功回答，截图保留 | browser-missed-colours、qa-vector-missed-colours |
| 0.52/扩候选实验 | 真实向量与RRF扩候选没有修好四推荐题，未把阈值降低方案作为最终版本 | retrieval-expanded-hybrid052 |
| 最终实体混合 | 保留真实BGE/Qdrant分数，加已收录实体+BM25排序与明确接受路径；两文档只加“脸谱”实体元数据并增为1.0.1，事实正文未改 | ingest-face-entity-metadata-update、final-entity-metadata的20+5+4题比较 |
| 最终真实生成 | 20题HTTP成功：18次供应商生成、2次无证据控制响应；5题补充真实联测，包括虚构人物拒答；37条引用真实映射 | rag20-final-hybrid、holdout-final-hybrid、助手核查记录 |
| 实际对照 | 同5题各做真实直接DeepSeek和最终RAG；RAG更便于来源追溯，直接模型并非全部错误；不同时间运行不当严格延迟实验 | direct-five、direct-vs-rag-five |
| 浏览器闭环 | 四推荐题自动填入与真回答、历史回合引用、手机安全文字、8页导航/图片/控制台、平板、未接入Agent/3D | browser-test-report、DOM/JSON、真实截图 |

## 实际Bug与测试操作修复

- 后端错误处理、费用预留、引用结构、线程/幂等边界的初始离线测试为77通过/6失败，修复后再跑；后续新增测试后合并运行115通过/5失败，原因是fake encoder沿用旧方法，与实际SentenceTransformer新方法不一致，修正fake后120通过，再加实体路由测试最终124通过。离线double与真实模型结果分开记录。
- 前端网络失败后的ready缓存及过期异步结果问题，网络回归最初21通过/3失败；加缓存失效与检查代际后25通过。实际停服务后错误状态、恢复后手动重试均验证，不自动收费重试。
- 手机工坊根锚点在固定导航下遮住标题；只补独立样式scroll-margin，重新从首页进入复核。没有改其他7页的主体或CSS。
- HTTP测试脚本初次未编码中文资源URL，之后误把Range返回206当成页面200失败；这是脚本错误，保留两次真实失败输出，修正后8页/62资源/6受保护路径通过。
- 原先敏感扫描正则把检查器自身的泛化PEM模式误判，修正为精确凭证/实际私钥头扫描，后续Git门禁失败立即终止命令。没有把误报写成真实密钥泄露，也不隐藏此前命令门禁的问题。
- 整理五题对照时辅助脚本误用账本字段estimatedCostCNY，真实字段为estimatedUpperCny，出现一次KeyError；修正字段后生成真实对照，已产生的语义核查文件保留，未重发模型请求。
- 浏览器summary角色、重名页脚链接及导航文字匹配引发定位失败，按实际DOM/AX重新定位后继续。没有把定位失败伪装为网站功能Bug或未执行测试通过。

## 版本、Git与证据关联

| 实际提交 | 作用 |
|---|---|
| 84a34bab741f840c29fa4ac23b04d51ef12a3f54 | 后端、私有配置与预算、连通探测、已批准方案及初期记录 |
| 5e3e4d25b754e78ab44bfd6fa9468704491b12a5 | 真实语料、CPU BGE、持久化入库及生命周期/初期检索 |
| f7dee30d713dcd36fc76dd8d9f1a990df7a37d65 | 真实问答与别名校验、v1/v2演进、初次真实20题及五题直接组 |
| 8e6a78a6821adc8ddbc948c0e4eb0064da2aadec | 浏览器发现的检索缺口、实体混合修复、最终真实20题与回归 |
| 8a5499edf1e70629cf70034ead8c95ee109c9855 | 原生前端真实接入、网络恢复、浏览器及手机锚点修复与证据 |

阶段文档归档提交通过实际git log定位；本文不伪造包含自身最终Hash的历史。Prompt系统文件和测试文件Hash可从Git及评价metadata重新核对。

最终累计62次成功供应商调用，输入41,500、输出9,503、总51,003 tokens；保守峰价估算0.13343424元，未超过3元应用预算。测试集候选标注、助手语义复核不冒充人工gold；专业人工审核、冷机完整计时和独立盲测保留为限制。阶段结束后等待用户验收，不进入Phase 3。
