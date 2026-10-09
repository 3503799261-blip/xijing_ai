# Phase 1 本地 HTTP 预览诊断

- 执行日期：2026-10-09，Asia/Shanghai。
- 诊断范围：只读静态预览；未修改项目源码、Git、防火墙或浏览器安全设置。
- 原项目目录：`D:\京剧\京剧`。

## 实际执行与结果

1. 沙箱内启动 `python -m http.server 8877 --bind 127.0.0.1 --directory 'D:\京剧\京剧'`，统一执行会话 `53870` 没有服务输出；沙箱内 curl 的 localhost 与 127.0.0.1 连接均返回 `Bad access`，退出码 7。
2. 已终止上述本次诊断创建的会话。使用已授权本机预览范围的 `require_escalated` 启动 `python -u -m http.server 8877 --bind 127.0.0.1 --directory 'D:\京剧\京剧'`，会话 `39727` 实际输出 `Serving HTTP on 127.0.0.1 port 8877`。
3. 提权执行 `curl.exe --noproxy '*' --connect-timeout 2 --max-time 5 -v 'http://127.0.0.1:8877/index.html' -o NUL`：退出码 0，HTTP 200，Content-Type `text/html`，Content-Length `12199`。响应日期 `Fri, 09 Oct 2026 13:47:16 GMT`。
4. 同参数请求 `http://localhost:8877/index.html`：退出码 0，HTTP 200，最终连接 IPv4 `127.0.0.1`，Content-Length `12199`。响应日期 `Fri, 09 Oct 2026 13:47:42 GMT`。

## 结论与边界

本机只读 HTTP 服务在非沙箱执行下已确认正常响应。沙箱回环连接存在执行权限限制；此结果仅证明 HTTP 连通性，不证明浏览器渲染或页面功能通过。浏览器由主代理统一控制并另行保存截图和测试结果。

服务暂留：会话 `39727`，访问 `http://127.0.0.1:8877/` 或 `http://localhost:8877/`。服务只绑定回环 IPv4，不向局域网开放。
