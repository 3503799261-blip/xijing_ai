# 测试辅助说明

这里保存本轮执行过的辅助源码，供审查，不是产品启动入口。

- `browser-navigation.mjs`：同源GET/HEAD，8页×3视口、before/after宽度及截图。
- `mock-chat-browser.mjs`：只在浏览器Fetch路由中保存隔离测试会话，明确MOCK，不发送真实聊天POST。
- `secondary-browser.mjs`：次级导航、六步导览、只读备用、真实历史及企业需求入口。
- `guarded-server-control.py`：复用现有`.venv`及安全本地启动器，测试进程限制外部DNS/connect，写新输出目录。
- `conversation-offline-bootstrap.py`：收集前清空密钥与隔离路径，仅运行新会话专项。
- `full-offline-bootstrap.py`：同样保护边界运行完整后端回归。

真实GLB桌面、CDP触摸、WP2历史及库存辅助复用仓库/本机已有脚本，实际执行路径见[报告](../test-report.md)。真实模型图片不在此归档，仅保存Hash与私有证据位置；不要将Q版内部技术验证图转作公开比赛素材。

Python完整离线辅助保留`phase5-wp4-`新目录名前缀约束；这是已有安全边界，不代表本轮发生在WP4日期。每次输出须新建目录，不能覆盖历史结果。
