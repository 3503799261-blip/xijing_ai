# Phase 2 实际浏览器回归报告

执行日期：2026-10-10，Asia/Shanghai。测试对象为本地HTTP服务 `http://127.0.0.1:8000`，Codex内置浏览器；不是file预览、DOM double或Phase 1旧截图。执行记录在公开协作快照与本目录JSON/DOM快照中。

## 实际环境与结果

| 检查 | 实际结果与证据 |
|---|---|
| 1920×1080桌面文化页面 | 首页、历史、行当、脸谱、音乐、视频、画廊实际打开，标题/导航/图片正常，无横向溢出或控制台warn/error；`phase-02-browser-observations.json` |
| 390×844手机八页主导航 | 实际点击八个主导航入口，全部进入对应URL；无破图、横向溢出或正常页面控制台warn/error；`phase-02-browser-mobile-navigation.json` |
| 工坊真实服务状态 | 索引、Embedding及供应商已验证时显示RAG已就绪；另外三个AI能力仍待接入 |
| 推荐问题 | 四个按钮均实际自动填入完整问题，发送后收到真实回答；脸谱、行当、武生、霸王别姬的最终DOM记录分别存于`phase-02-browser-final-*.txt` |
| 加载和防重复 | 真实等待期间按钮disabled、加载提示出现；离线DOM测试另验证pending锁与重复提交，未把double当真实模型 |
| 连续提问和引用 | 同页完成四轮问答；原回合可展开引用。第四轮之后点击第一轮“在资料区查看本次依据”，资料区正确回到脸谱问题及其原requestId |
| 来源展开 | 标题、sourceId、locator、项目原创摘要和真实来源链接显示；摘要明确标记非官方逐字原文 |
| 输入校验与键盘 | 空输入实际显示“不能只输入空格”；maxlength600；发送按钮以Enter成功激活。文本框Control+Enter未设提交快捷键，不列作已实现功能 |
| 手机安全文本 | 实际输入`<img src=x onerror=alert(1)>`按文字显示，消息区img/script节点数量为0，返回真实资料不足提示；无事件执行或横向溢出 |
| 停机错误与恢复 | 实际停止后端后发送，出现连接错误、取消就绪徽章、保留手动重试；没有替代AI答案。恢复服务、重新检查及手动重试成功；错误DOM和截图已保留 |
| Agent/草稿/3D | Agent说明实际展开，四Agent待执行且无假进度；页面内草稿保存功能保留；概念图与图生3D禁用、待接入，未放假模型 |
| 768×1024平板 | Agent面板实际检查，无横向溢出，保存截图 |
| HTTP资源 | `phase-02-http-regression.json`：8页面、62资源、6受保护路径通过；另外7文化HTML逐字节等于Phase 1验收提交 |

## 发现与修复

1. 首版真实回答正文夹入长chunk ID：保留`qa-first-raw-citation-id.jpg`及DOM。Prompt v2使用内部E1–E5别名、后端映射到真实ID，正文保留中文解释，最终页面不再显示长片段标识。
2. 停机后旧能力缓存可能仍显示ready：前端网络/供应商超时立即失效缓存，异步旧检查不得恢复ready，免费重新检查保留错误和手动重试；25项前端离线检查与真实停机恢复通过。保留失败回归JSON。
3. 泛问脸谱颜色只取到正净：实际回答诚实资料不足，但语料已有相关知识。最终加入经过来源核对的脸谱实体标签、真实BGE/Qdrant与实体/BM25混合排序。四推荐问题候选证据覆盖全部恢复，真实网页颜色回答及引用已重新验证。旧漏取截图和DOM保留。
4. 手机工坊根锚点会被固定主导航遮住主标题：只给`.ai-workshop`添加动态scroll-margin。重新从首页进入后标题完整。首次reload保留浏览器原滚动位置的截图也保留，最终从首页重入截图为`workshop-mobile-final.jpg`。
5. 测试定位问题：summary在DOM工具中不按button定位，页脚与页头链接重名造成strict selector错误，音乐导航标签匹配错误。依据真实DOM/AX重新限定或点击可见导航后继续；这些是测试操作问题，不作为产品缺陷。没有修改其他文化页面来迎合测试脚本。

停机测试中预期出现连接失败日志；它与正常页面控制台无错误的结果分别记录，不把故意故障伪装成正常通过。HTTP脚本最初中文URL编码、Range状态断言错误也保留在单独失败JSON，修复脚本后重跑。

## 截图

截图均为本阶段实际JPEG浏览器输出，位于`../screenshots/phase-02/`。

- `home-desktop.jpg`、`home-mobile.jpg`：首页。
- `workshop-desktop.jpg`、`workshop-mobile-final.jpg`：工坊总览。
- `agents-desktop.jpg`、`agents-mobile.jpg`、`agents-tablet.jpg`：Agent职责及未接入状态。
- `qa-final-demonstration.jpg`：最终真实回答与展开来源，requestId对应预算账本。
- `qa-final-desktop.jpg`、`qa-citations-desktop.jpg`、`qa-mobile.jpg`：真实推荐问题及引用。
- `qa-mobile-insufficient.jpg`：手机资料不足/安全文字显示。
- `network-error-desktop.jpg`：真实停机错误。
- `qa-vector-missed-colours.jpg`、`qa-first-raw-citation-id.jpg`：修复前真实失败/体验问题。

## 范围限制

只声称本次内置浏览器、指定视口和已操作路径通过；没有完成独立Chrome/Edge/Firefox多浏览器矩阵、自动可访问性审计、视觉像素对比或媒体完整播放测试。原媒体文件与文化页面内容保持不变，静态资源HTTP与浏览器加载已实际检查。前端不是跨问题记忆系统，刷新和跨页导航会清空页面内问答与草稿。阶段验收仍由用户决定。
