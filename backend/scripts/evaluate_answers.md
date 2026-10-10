# 真实问答记录与离线评价

本工具使用现有20题助手核对候选集。题目和预期事实尚待人工复核，不属于人工金标准。脚本不会自动重试、调用评判模型或计算人工回答正确率。

## 真实问答采集（可能付费）

先由有权限的执行者启动已配置真实模型的本地后端，再运行：

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.evaluate_answers --base-url http://localhost:8000 --label rag20-v1 --questions knowledge/evaluation/questions.json --output docs/evidence/test-results/phase-02-answers-rag20-v1.json
```

可用 `--limit 2` 小规模检查；未指定时执行全部题。`--timeout` 默认60秒，高于后端整体45秒超时。每题只发送一次，独立生成 `X-Idempotency-Key`，串行执行；失败会保留并继续下一题。重复运行会产生新请求并可能再次计费，已有输出文件会在任何请求前拒绝覆盖。再次调用必须由执行者根据已保存结果和后端费用账本决定。

每题保存实际回答、公开引用、HTTP状态、正文与响应头请求ID、幂等键、真实耗时和原始响应SHA256；按题落盘防止中断丢失。错误仅保存后端公开协议，非JSON响应不复制，日志只输出题号与状态。匹配凭证格式的文本会脱敏并标记 `redactionApplied`，不会保存未知错误堆栈或任意响应字段。

HTTP 200代表接口成功。知识不足的返回可以由后端直接生成，不能将20条HTTP响应当成20次真实LLM调用。实际模型调用次数、token和费用须与后端账本单独核对。候选 `uncertain` 标志一致率也不等于人工核查的合理拒答率。

## 离线引用核对（免费）

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.evaluate_answers --review-existing docs/evidence/test-results/phase-02-answers-rag20-v1.json --label rag20-v1-review --output docs/evidence/test-results/phase-02-answers-rag20-v1-review.json
```

此模式不发HTTP、Embedding或LLM请求，只以SQLite只读连接核对实际引用的ID、来源、标题、定位、URL、正文及 `contentKind`，再核对 `knowledge/documents/` 中来源元数据和原始section。换代索引后可用 `--database` 指定采集时原有的 `knowledge.sqlite3`，并用 `--documents` 指向对应资料版本。报告保存采集归档、候选题和原始资料的SHA256，不公开数据库或私有配置路径。

输出 `expectedFactReviewTemplate`、`assistantReview`、`humanReview`。初始均为未评估或待人工审核；执行者须逐条查看回答及实际片段，填写事实是否被支持、对应引用ID、缺失事实与无依据断言。结构引用映射率能证明来源一致性，不能证明引用支持回答中的每个断言。

合成人名等资料不足题必须判断回答是否拒绝无证据前提。即便资料引用ID真实，也不能据此证明它支持该人名或年份。人工审核数量为零时，`humanAnswerCorrectnessRate` 保持null。

## 工具开发时的免费检查

2026-10-10实际执行了Python语法解析、`--help`、20题解析与唯一ID、凭证模式脱敏、未知响应字段丢弃、非法引用和非JSON响应拒绝，以及实际35片段索引的只读路径解析，均通过。另用SQLite只读连接实际遍历35片段，全部可以映射到原始资料section且去除空白后的正文一致；数据库写入为0。测试夹具仅在内存中用于检查格式，不作为AI答案归档；这些检查没有HTTP或LLM请求。付费问答结果须以主代理随后实际运行的归档为准。
