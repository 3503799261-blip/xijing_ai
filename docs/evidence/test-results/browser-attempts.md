# 原网站浏览器预览尝试

日期：2026-10-09，Asia/Shanghai。目标：改造前截图与实际原页面检查。

| 操作 | 真实结果 |
|---|---|
| 受限执行环境启动 Python 静态服务，访问 127.0.0.1:8765/index.html | 未成功预览；本地请求报告套接字访问限制，浏览器超时 |
| 经执行审批启动同一只读本机服务 | 获得执行会话 96935；确认 127.0.0.1:8765 正在监听，服务 PID 51996 |
| Codex 内置浏览器再次导航 HTTP 首页 | `net::ERR_CONNECTION_TIMED_OUT` |
| 本机 Invoke-WebRequest 诊断 | 5 秒请求超时 |
| 本机 curl，排除 HTTP 代理 | `curl: (28) Connection timed out after 5004 milliseconds` |
| 内置浏览器打开 file URL | 浏览器安全策略拒绝，仅允许 HTTP/HTTPS；未绕过策略 |
| 核验服务命令行并停止 PID 51996 | 成功关闭本次临时预览服务 |

服务实际命令：

```powershell
& 'C:\Users\35037\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m http.server 8765 --bind 127.0.0.1 --directory 'D:\京剧\京剧'
curl.exe --noproxy '*' --max-time 5 --head 'http://127.0.0.1:8765/index.html'
```

结论：未取得原网页截图。视觉、资源浏览器加载、音视频播放、响应式和控制台检查不能标为通过。HTTP 超时根因尚未定位，不能断言网站本身有运行 Bug。下一次实施须先恢复可用浏览器预览，再完成原站基准截图与改造后的回归检查。

本轮未安装浏览器、修改防火墙或安全设置，未修改网页，未使用截图或静态内容冒充成功运行。
