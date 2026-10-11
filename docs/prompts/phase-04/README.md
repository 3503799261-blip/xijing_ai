# Phase 4真实AI协作证据

本目录保存当前会话公开记录的时间快照，不包含隐藏推理、系统指令或密钥。

- `00-original-user-request.txt`：最初检查点A需求原文。
- `01-final-architecture-revision.txt`：最终3次模型创建尝试限制原文。
- `02-approved-development-request.txt`：正式开发授权，真实建模逐次另行批准。
- `03-public-conversation.jsonl`：实际公开对话与匹配工具证据，源行号与时间保留。
- `04-export-metadata.json`：导出范围、文件Hash和真实快照时间。

由 `scripts/export_phase4_prompt.py` 从明确指定的当前会话导出，后续开发结束再更新快照。导出器剔除非公开内容并脱敏常见凭证；比赛材料发布前仍需检查。

2026-10-11开始正式开发：保留Phase 3基线，创建独立Phase 4分支。当前未获得任何一次真实模型创建授权。历史调用次数等待用户核实，首次账本保持UNKNOWN。

真实失败记录：首次下载免费Viewer时受网络连接重置影响，未取得文件；使用已授权的网络权限后完成固定版本下载。首次脚本启动使用错误的虚拟环境路径，改用项目根 `.venv` 后运行。均非Neural4D API失败，没有占用真实建模次数。
