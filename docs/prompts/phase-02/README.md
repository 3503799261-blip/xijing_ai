# Phase 2 AI 协作证据

当前状态：**用户于2026-10-10通过V3.0明确批准检查点A，Phase 2正式开发进行中。** 初始方案的待批准状态保留为历史记录。

| 文件 | 实际内容 |
|---|---|
| 00-original-user-request.md | 本次用户完整 Phase 2 Prompt，从明确的当前会话日志单条 input_text 精确提取，未改写或补充 |
| 01-checkpoint-a-public-conversation.jsonl | 从该 Prompt 开始的公开消息、实际工具调用和对应结果的时间点快照 |
| 02-export-metadata.json | 来源快照 Hash、实际导出时间、记录数、原 Prompt 的 UTF-8 字节一致性与排除规则 |
| 03-approved-development-v3.md | 用户实际提交的完整V3.0开发批准与3元测试预算要求，原文字节保存 |
| ../../reports/phase-02-architecture-proposal.md | 本次架构选择、代码审查、实施与测试计划；状态为待批准 |
| ../../evidence/test-results/phase-02-code-audit.json | 10 个重点文件与 Phase 1 提交的字节比较、实际环境及 Git 查询，明确未执行的测试 |

原 Prompt 的实际长度为 15,443 字符，导出文件和来源文本的 UTF-8 字节一致。公开会话快照不包含隐藏推理、system/developer 消息、内部会话身份或嵌入式媒体；原日志不复制进仓库。导出复用了现有标准库脚本的过滤函数，没有修改该脚本。

快照只覆盖导出时已发生的公开操作，不伪造未来实现、测试或验收。架构方案中的指标为计划；实际运行记录分别归档到evidence。DNS/CIM查询失败、远端连接重置、证据整理命令错误与后续实际Bug按真实过程保留，不能混称应用测试通过。

已基于Phase 1验收提交建立 `feature/phase2-opera-rag`。后续以真实事件增加代码修改、Prompt版本、失败与修复、实际测试与Commit关联。用户曾将密钥发到聊天；已提示撤销，用户确认撤销并另行本地配置，公开记录只保留脱敏消息。新导出器先过滤隐藏记录，再对所有公开字符串做凭证脱敏，不复制暴露值。API测试只归档最终回答、实际用量、耗时和安全错误。

刷新公开快照命令：`python scripts/export_phase2_prompt.py --session-log '<明确的当前会话JSONL路径>' --output docs/prompts/phase-02`。导出器不会搜索其他会话。真实Key只在本机私有env中，不进入Git、前端或截图。
