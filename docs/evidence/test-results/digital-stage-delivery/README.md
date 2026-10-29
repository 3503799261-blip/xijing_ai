# 数字戏台与全站内容直达：实际证据

日期2026-10-29。完整解释见[交付报告](../../../reports/digital-stage-delivery.md)。

- `backend-full/`：实际838通过、0失败/跳过；包含新增29，不相加。
- `backend-stage/`：29项独立只读资源专项，无数据库连接。
- `frontend/`：八组前端原始输出。`summary.json`所指资产组原22项，之后发现显式链接缺陷补测为`workbench-final-23.json`的23项通过，保留先前输出。
- `stage-browser.json`：真实GLB与3D场景14组；Chrome/CDP触摸不是实体手机。
- `navigation-browser.json`：最终46项实际浏览器检查，含8页×3视口、已存旧GLB、历史/企业入口、导航与草稿，不发送AI请求。
- `browser-runners/`：实际浏览器辅助代码原样保存，含开发机路径；移机需适配工具位置，不是新业务依赖。
- `pipeline-validation.json`：10组实际离线转换验证。`failures/`保留检查器、导航及显式链接失败；不覆盖原失败。
- `business-invariants.json`：所有业务表与关键记录的规范化Hash。完整before/after留在本机runtime，公开记录不含用户需求正文。
- `source-invariants.json`：36原素材及私有配置Hash不变；没有配置内容。
- `existing-resource-comparison.json`：46项资源与2026-10-21已有基线一致；注明实际基线日期。
- `cultural-page-invariants.json`：其余7页仅加入2行导航CSS/JS引用，共用导航CSS不变。
- `screenshots/`：本次新戏台/人物真实截图；`screenshot-manifest.json`仅记录其他私有截图Hash，不授予公开用途。
- `verification-stop.json`：本轮服务正常Ctrl+C停止与8000端口释放。
- `pdf-validation.json`：9页PDF、Hash、大小和逐页视觉检查；PDF成品在本机ignored output中。

所有Mock、真实本地读取与历史供应商证据分开。无本轮付费API或Neural4D请求。没有录制视频。完整Git Hash以最终交付版本清单为准。
