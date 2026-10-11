# Phase 3 真实浏览器与HTTP回归报告

日期：2026-10-11（Asia/Shanghai）。环境：Windows、Codex In-app Browser；本地单进程FastAPI，`http://127.0.0.1:8000`。本报告记录实际操作，离线测试双桩另列，不把后端读取200叫作角色创作成功。

## 实际执行范围

| 检查 | 结果与证据 |
|---|---|
| 八页打开、主导航逐一点击、图片加载 | 首页/历史/行当/脸谱/音乐/视频/画廊/工坊均实际访问；DOM与导航URL保存在browser-observations.json |
| 原文化内容保留 | 最终HTTP检查8页、62资源成功；七个文化HTML逐字节等同Phase 1，6个敏感/内部路径404 |
| 空创作需求 | 页面显示校验，未创建任务 |
| 本地草稿 | 整理草稿明确显示非AI输出，只有独立Agent提交才调用后端 |
| 桌面真实协作 | 实际观察Planner运行，再读取四阶段完成；任务0a808e2b…与最终1a18ff2c…各有真实产物、来源和模型usage |
| Agent职责展开 | 实际点击details并显示职责/交接；最终四卡截图留存 |
| 最终确认与下载 | 测试任务0a808e2b…由测试执行者点击接受、后端completed、浏览器实际下载JSON；仅为测试操作，不是用户Phase 3验收 |
| 刷新与持久化 | 浏览器刷新及实际后端进程替换后恢复同一个已确认任务，不新建模型任务 |
| 真实网络故障 | 测试中关闭自己启动的后端，再查询；显示无法获取状态，已完成阶段保留，不假推进、不自动重发 |
| 网络恢复 | 重启单worker，免费重查同一持久化任务恢复成功 |
| 手机真实创作 | 174e97bf…刀马旦任务实际完成四阶段、显示依据；未确认时下载禁用 |
| 手机资料不足与取消 | 75783c7e…虚构“量子星舰行当”实际停在Research，后两阶段pending、确认不可用；明确取消后后端cancelled |
| 取消反馈修复 | 刷新已取消任务后正确显示“任务已取消”，不再说正在收尾；before观察与after观察保留 |
| 最终代码桌面与手机 | 1a18ff2c…“蓝云”使用Planner v4/Research v4/Designer v3/Reviewer v3；四阶段完成、待确认，手机刷新保持同一ID及禁用导出 |
| Phase 2问答回归 | 实际提问“京剧武生的服饰有什么特点？”，真实回答/引用可展开；requestId=23ab1a7e-3e80-498b-9e05-76a910c1e521 |
| 未接入能力 | 概念图/Neural4D能力false，入口仍说明待开放，没有假图像或3D完成状态 |
| 控制台 | 最终读取error/warn日志为空；实际停机的网络失败通过界面处理 |

## 视口与截图

实际设置1920×1080桌面及390×844手机；截图PNG约1905×1072/375×812，捕获尺寸与浏览器滚动条、输出缩放有关，不伪称PNG像素完全等于请求视口。最终手机DOM clientWidth=375、scrollWidth=375，无页面横向溢出。已目视查看最终桌面与手机截图，四卡和中文可读；长来源ID会换行。

| 截图 | 内容 |
|---|---|
| [首页](../../screenshots/phase-03/index-desktop.png) | 原文化首页 |
| [工坊总览](../../screenshots/phase-03/about-desktop.png) | 继承视觉与功能入口 |
| [最终四Agent](../../screenshots/phase-03/agents-desktop-final-cards.png) | 四实际完成阶段、公开摘要及人工确认区 |
| [最终任务总览](../../screenshots/phase-03/agents-desktop-final.png) | 实际任务ID、4/4与待确认 |
| [最终手机](../../screenshots/phase-03/agents-mobile-final.png) | 同一任务恢复、响应式卡片 |
| [手机文化引用](../../screenshots/phase-03/agents-mobile-evidence.png) | 真实刀马旦摘要来源 |
| [真实RAG回归](../../screenshots/phase-03/qa-regression-desktop.png) | 回答和来源 |
| [停机提示](../../screenshots/phase-03/agents-network-error.png) | 通信故障保留已知状态 |

截图目录也保留早期中间捕获。`agents-desktop-running.png`实际捕获时已结束生成、待确认；`agents-mobile.png`是视口切换尚未稳定时的中间捕获，不用于最终布局结论。应以final文件及本表为准，不从文件名推断运行状态。

## 可重跑检查与证据

```powershell
.\.venv\Scripts\python.exe scripts/phase2_http_smoke.py --output docs/evidence/test-results/local-http.json
.\.venv\Scripts\python.exe -m backend.scripts.evaluate_agent_api --task-id <已有测试任务UUID> --output docs/evidence/test-results/local-agent-api.json
```

HTTP脚本不调用模型。Agent API脚本只重放已有任务的原幂等键，不创建付费任务；它检查14项真实HTTP行为，包括同键重放、异输入冲突、空/长输入、无任务、超大游标/序号、失效确认、真实Search及能力。传入任务须来自本机数据库，跨机器不能复用本报告UUID。

原始证据：[浏览器DOM/导航/控制台](browser-observations.json)、[四个实际浏览器任务及产物](browser-tasks-final.json)、[实际下载JSON](browser-confirmed-character.json)、[最终HTTP回归](http-regression-final.json)、[14项API](api-http-checks.json)。所有截图与记录来自真实浏览器或HTTP，不以离线DOM双桩替代。

边界：未逐一播放所有旧视频/音频、未跨浏览器品牌测试、未做公网部署压力测试；原七页源码/资源未变。AI辅助审校并非专业人员审核，浏览器操作通过不等于文化设计必然正确。
