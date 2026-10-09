# Prompt 导出工具实际验证

- 日期：2026-10-09，Asia/Shanghai。
- 工具：`scripts/export_phase_prompt.py`，仅 Python 标准库。
- 输入：主代理明确提供的当前会话唯一 JSONL；未枚举、扫描或读取其他会话。
- 临时验证输出：`implementation/export-check/`，未写入项目源码或执行 Git。

## 实际结果

运行导出 CLI 后，保存了首条原始需求 11728 字符、开发批准需求 2544 字符。两份 Markdown 文件均由各自单个 `input_text` 文本块直接写为 UTF-8，不添加标题或换行；输出读取字节与源文本 UTF-8 字节一致，SHA256 精确匹配。

首次成功导出快照包含 127 条公开记录：13 条消息（用户 3、助手 10）、29 次 custom_tool_call 及29次对应输出、28次 function_call 及28次对应输出。快照时间为 `2026-10-09T13:57:10.124521+00:00`。这些数量只描述本次调用时点，不是最终完成记录。

会话快照 SHA256：`cf548138eeff6f2d32da18b32fbe7292c87f6883ddf1cf297e78d0760532146e`。

已解析导出的 JSONL 验证：记录种类均在公开消息或主工具调用/输出白名单；消息角色仅 user/assistant；助手 phase 仅 commentary/final/final_answer；未导出顶层内部 metadata、encrypted_content、session_meta 或 turn_context。原始首条 Prompt 与此前审查导出的文件逐字节相同。截图等嵌入媒体数据被移除，图片文件另存证据。

## 实际修复

首次调用在 Windows 沙箱的 `Path.resolve(strict=True)` 返回 `PermissionError: WinError 5`；同一明确路径的直接读取可行。工具已改为要求绝对 JSONL 路径并直接读入，不执行 realpath/目录扫描。重新运行成功，未通过提权扩大日志读取范围。

工具未补造最终回复。主代理完成阶段报告后，应再次执行同一导出命令，刷新已实际发生的公开记录；最终回复只能在其真正发生后导出。

## 项目归档时的隐私复核与收紧

2026-10-09 将工具与约定文档归档至项目后，对同一明确日志进行内存导出审查，不写新的最终对话快照。首次复核的205条公开记录未发现私有对象字段或JSON文本中的私有字段，但有3处主工具命令文本含完整日志路径及会话UUID。

工具已增加来源日志路径、文件名与会话UUID的工具文本脱敏；不改动两份原始用户Prompt。还增加嵌套私有记录过滤和JSON文本块过滤，以防工具输出包装了内部字段。用专用非私有哨兵字符串验证嵌套developer/reasoning及encrypted_content无法进入导出，检查通过。

再次内存审查时有225条实际公开记录，来源日志文件名及会话UUID均未保留，消息仍只有公开user/assistant，未包含reasoning记录。两份原始Prompt仍为11728、2544字符。上述数量属于实际读取时点；最终归档由主代理统一调用工具生成。
