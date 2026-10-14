# 第二次写实主展示角色方案

日期：2026-10-14。范围：Phase 4.2资产准备与审核，不创建模型。

## 1. 角色定位

方案暂名 **绛绣·戏韵**，定位为“中国京剧风格文化数字角色候选”，风格为 **Realistic Digital Human / 写实国风**。暂名是本轮设计提议，不是历史人物、既有剧目人物或用户已批准的角色名称，也不代表原图片版权归本项目所有。

采用“原创京剧风格数字角色”的定位，不根据单张服装图片强行判为青衣、花旦或旦角。后续文化分类需要可靠资料、具体表演设定及人工核查。

视觉关键词：Chinese Peking Opera-inspired、traditional costume inspiration、digital character、cultural heritage、game character concept。游戏角色是视觉目标，不表示已获得游戏可用的绑定、拓扑或动画资产。

## 2. 图片与版本

| 项目 | 实际记录 |
|---|---|
| 当前输入 | `D:\京剧\概念图1.jpg` |
| 资产用途标签 | `realistic_showcase_candidate_v1` |
| 候选作用域 | `SECOND_REALISTIC_SHOWCASE` |
| 候选版本 | 1 |
| 候选ID | `92e3d09f-57ce-49b2-8d57-1c0664a72689` |
| 方案ID | `realistic_character_proposal_v1`，本轮本地提案标识 |
| 风格 | `realistic` |
| 原文件 | JPEG，793×1400，535664字节 |
| 原文件SHA-256 | `0170077ef813f95b2e0da4666f0a7919078d0a811ac04d61613e69a31a621095` |
| 标准化预览 | PNG，793×1400，997587字节 |
| PNG SHA-256 | `7b8fb1a42bf79d0210c1571e65ae92d856fa73761d42d9cd044836764aad4d45` |

原JPEG按字节保存独立快照。预览只进行解码、方向规范化与元数据清除；本图原图和PNG的RGB像素核对一致，没有裁切、背景简化或改变外观。原图已经是简洁白色背景，优先保留。文件仅保存在本机受控运行目录，没有将图片或含图截图加入公开仓库。

## 3. 外观分析

以下为实际看图观察和设计语言，不是已认证的传统服饰结论。

| 元素 | 可见内容 | 解释边界 |
|---|---|---|
| 戏服主体 | 红色长袍，金色花鸟式装饰与刺绣视觉纹理 | 不认定为蟒袍或特定朝代服制，不解释具体纹样含义 |
| 冠饰 | 蓝银色冠饰主体、红色绒球、珠饰和两侧长垂饰 | 可描述为凤冠意象；具体冠式未认证，不编造人物身份 |
| 袖布 | 白色长袖延展，部分覆盖双手 | 水袖式视觉表达，具体传统水袖结构未认证 |
| 长袍轮廓 | 层次较清晰，下摆铺展至地面 | 背面未显示，衣层内部不可据此确认 |
| 身体姿态 | 单人完整站姿、接近真人比例，双臂靠近身体 | 对图生3D的臂部和衣层分离存在风险 |
| 足部 | 下摆遮挡部分鞋履 | 保留可见足部，不凭空添加鞋履细节 |

## 4. Phase 3兼容与关联

复用已有 `CharacterDesign` 严格验证和写实风格适配器，以真实本地RAG片段为仅有的文化事实依据；服饰、配色和冠饰均标为 `creative`，不伪造证据。

本轮调用了现有文化审校函数一次，没有执行完整Planner→Research→Designer→Reviewer工作流，也没有代用户确认角色。实际候选的 `characterId=null`、`assetId=null`、`sourceTaskId=null`，状态为 `PENDING_CHARACTER_ASSOCIATION_AND_REVIEW`。本方案不能冒充Phase 3正式角色JSON。

正式角色资产仍需按现有流程取得完整、已审校且经用户确认的结果，再由既有资产适配层登记。候选图不会覆盖第一张Q版图、第一模型或现有双风格版本。

## 5. 来源、许可与使用范围

用户来源声明原文：**“百度公开资源”**。具体作者、原始链接、比赛公开展示、供应商上传、3D衍生处理和再分发许可均未确认。商用销售不在本轮用途范围内。

拟用于比赛展示、AI数字角色生成展示和第二次写实建模候选；这是用途计划，不是许可证明。当前 `sourceVerified=false`、`licenseVerified=false`、`imageAccepted=false`、`modelEligible=false`。第一张内部技术图的授权不适用于本图。

## 6. 当前结论

候选登记和文本提案已完成，等待角色方案、图片许可及第二次单次建模审核。关联结果见 [真实准备结果](../evidence/phase-04/modeling/02-realistic/realistic-preparation-result.json)，文化边界见 [文化审查](phase-04-realistic-cultural-review.md)，最终待审表见 [第二次授权申请](phase-04-second-model-approval.md)。本轮Neural4D请求、创建预留、新建提交均为0。
