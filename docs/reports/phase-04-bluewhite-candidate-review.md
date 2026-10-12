# Phase 4 · 第一次Q版建模的新蓝白概念图准备审查

日期：2026-10-12，Asia/Shanghai。范围仅本地素材登记、已有角色对照、待审Prompt、预览与配额核查。**没有提交任何Neural4D任务，没有调用付费API。准备状态为NOT_READY；Phase 4仍为PARTIAL。**

## 1. 实际更新与Hash

读取 `D:\京剧\概念图.jpg` 当前字节并实际查看图片：蓝白Q版完整全身角色、珠状头饰、两侧延伸饰件、宽袖及细小毛笔，浅灰水墨背景。新文件1049×1398、JPEG、575200字节。

| 内容 | SHA-256 |
|---|---|
| 新原文件 | `9c737011a237de9fb589743e22b385a0c9611d33189c79b5940f8e1386047f0f` |
| 当前PNG预览快照 | `879e5daa99ce26fd77ea6d28f4049e45cd414e9416c731b7ecbbbfeedeeec703` |
| 旧绿衣图记录 | `37aaa21e1c03d9bc35bcfc995002e42a200bad987b45766d3b1497b418472c3d` |

新旧Hash、尺寸及实际可见内容均不同。[登记前记录](../evidence/test-results/phase4-bluewhite-before-registration.json)中原路径与旧元数据不匹配；[更新后只读核查](../evidence/test-results/phase4-bluewhite-preflight.json)匹配新Hash。

原始JPEG原样保存；PNG仅经过实际解码、方向规范化和元数据移除。程序验证原始保存字节一致、解码RGB逐像素一致，未裁切、改背景或改变外观。两种Hash不同是文件格式差异，不是视觉修改。证据见 [登记结果](../evidence/test-results/phase4-bluewhite-candidate-registration.json)。

## 2. 资产登记、历史和缓存

- 当前候选ID：`fa0cd555-1daf-44a3-8825-ee6f5eb8b79e`；同一首次Q版用途范围的版本2，风格`chibi`。
- 历史候选ID：`9919e663-b528-4e28-bcd6-7a7480745329`；版本1，仅保留旧元数据，`filesAvailable=false`。用户已覆盖旧原文件，不声称恢复了旧图片字节。
- [旧元数据原样归档](../evidence/test-results/phase4-concept-candidate-v1.json)，[当前候选元数据](../evidence/test-results/phase4-concept-candidate.json)更新为新Hash及新来源声明。
- 私有 `RAG_DATA_DIR/assets/catalog.sqlite3` 新增独立`concept_candidates`，按用途原子分配版本、幂等登记，UPDATE/DELETE触发器阻止覆盖历史。候选文件使用既有Hash路径及不可覆盖发布策略保存。
- 候选不写入正式`asset_images`，不绑定任何角色。登记前后正式记录均为2角色资产、0概念图、2合法GLB测试模型；原角色JSON、确认和模型均未修改。
- 预览固定读取候选ID对应的独立Hash快照，**不再读取可被替换的原路径**。返回`private, no-store`和PNG Hash ETag，历史版本文件返回404，不会把新图放在旧图ID下面。
- 候选ID不能当正式imageId使用；没有候选接受、提升为角色或创建模型接口。后续正式图生3D仍须完成原有角色、图片、Prompt、费用与单次批准门禁。不得直接拿候选ID绕过这些步骤。

本地只读预览：[版本2](http://127.0.0.1:8000/api/v1/assets/candidates/fa0cd555-1daf-44a3-8825-ee6f5eb8b79e/preview)。未重写`about.html`或其他7个文化页。图片及含图片截图保持私有，未添加到公开Git仓库。

## 3. 新来源与许可

用户本次声明为“**百度公开数据**”。仅把该原文记录为来源声明；未提供具体网页、作者、许可证明或已确认角色ID。旧图的小红书773908132来源和非商业编辑许可**不继承到新图**。

新记录`sourceVerified=false`、`licenseVerified=false`、`commercialUseVerified=false`、`publicRedistributionVerified=false`。使用、编辑、供应商处理、3D衍生及公开再分发的权限均为待确认。没有把来源声明改写成授权证书，也没有通过百度搜索结果猜测作者。

## 4. 与真实Phase 3文化JSON对照

只读核对20条实际任务及保存JSON：1条已完成且用户确认、14条待确认、2条取消、3条失败。对5个相关角色的20项Agent Artifact重新计算Hash，均与保存Hash一致；未调用LLM、重新运行Agent或改写确认状态。详见 [文化对照JSON](../evidence/test-results/phase4-bluewhite-culture-comparison.json)。

| 项目 | 已确认“青旌将·霄羽”JSON | 新蓝白图片观察 | 结论 |
|---|---|---|---|
| 定位 | 原创年轻男性将帅，武生长靠文化依据 | 无法仅凭Q版外观认定行当、性别或人物 | 不匹配，不能代填角色ID |
| 服饰 | 大靠、厚底靴、靠旗 | 蓝白宽袖袍服，当前图没有可核实的靠旗设定 | 不一致 |
| 配色 | 青金、石青、暗金，明确为原创演绎 | 蓝白 | 不是同一设计 |
| 头饰 | 没有新图珠饰及两侧宽扁延伸头饰的明确设定 | 珠饰与两侧延伸装饰可见 | 未获现有角色文化审校支持 |
| 毛笔 | 现有设计没有毛笔依据 | 手持细毛笔 | 作为待审原创道具，不声称传统角色标志 |

另4个接近的待确认角色仍包含靠、靠旗、雉尾等设定，不能因为蓝色相近就关联。对非空角色设计查找“毛笔”“水袖”“珠”没有命中；这只反映当前项目JSON，不代表对整个京剧传统作否定结论。

结论：`UNMATCHED_PENDING_REVIEW`。`characterId/assetId/sourceTaskId=null`、`imageAccepted=false`、`cultureAlignmentVerified=false`。这是一份基于现有JSON和视觉观察的工程对照，**没有京剧专家审核**。后续需形成与新图相容、经文化审校和用户确认的真实角色结果，不能修改旧角色来冒称其已通过审核。

## 5. 图生3D风险与背景决定

| 部位 | 预计风险 | 原任务生成后检查 |
|---|---|---|
| 顶部大珠及周边小珠、耳侧垂饰 | 融合、漏失、悬空或厚度不足 | 各视角检查连接、完整性、材质 |
| 两侧宽扁延伸头饰 | 单正面缺乏侧后厚度，可能成薄片、断裂或与肩融合 | 侧面/背面和旋转完整性 |
| 宽袖与手 | 袖口遮挡使手指及袖内连接难以重建 | 手与袖口穿插、粘连、双手结构 |
| 细小毛笔 | 细笔杆、笔尖易断裂、缺失或与手粘连 | 笔杆连续性、粗细和握持位置 |
| 背面 | 单张正面不能提供后脑、后衣、饰件真实结构 | 不把算法补全描述为经文化验证的背面 |
| 背景墨竹及地面阴影 | 仍可能被误入纹理/几何 | 角色轮廓与背景是否干净分离 |

**当前不建议为准备而额外简化背景**：人物完整、主体清楚，浅色低对比背景没有明显遮挡。优先保留当前原图；这不是供应商分割或成模成功保证。没有去背景、重绘、改袖、加粗毛笔或删除饰件。若后续确需改变外观，先另行确认，再登记新Hash、新版本并重做确认，不用反复创建任务试质量。

## 6. Prompt冻结与第一次人工审核表

实际生成并保存 [待审Prompt输入](../evidence/phase-04/modeling/01-chibi/bluewhite-prompt-input.json) 和 [冻结快照](../evidence/phase-04/modeling/01-chibi/bluewhite-prompt-frozen.json)。版本`candidate_bluewhite_review_v1`，Hash：

`0648259709da555ba1c7d2070b2bb1c0317b2d505796e39518d4e7f48343b315`

快照绑定当前原Hash、PNG Hash、风格、用途和实际观察；`frozenForReview=true`、`approved=false`、`culturalApproval=false`。它是新图第一个实际待审Prompt，**不是伪造的已批准角色Prompt，也不是旧图Prompt的虚构演进**。没有创建正式ModelApproval或幂等发送请求。

[第一次人工审核表](../evidence/phase-04/modeling/01-chibi/bluewhite-review-form.json)保存参数、Hash、Prompt版本、缺失项和空授权字段。角色、文化、图像接受、许可、报价、历史及单次批准未完成时不把表标成“可提交”。正式角色冻结必须在兼容Phase 3角色确定后重新完成。

## 7. 参数、费用和全局配额

本轮核对供应商[官方图生3D文档](https://docs.neural4d.com/en/api-reference/image-to-3d/generate-model-with-image)公开Markdown。Web页面读取失败后读取已下载官方资料；没有使用Key查询供应商或提交任务。公开文档访问与API请求分别统计。

拟用后端单模型普通图生3D接口：`POST https://alb.neural4d.com:3000/api/generateModelWithImage`，multipart上传后续已接受的图像。

| 参数 | 拟用值 | 核查边界 |
|---|---|---|
| `modelCount` | `1` | 显式覆盖官方默认4；全项目每次仅一个模型 |
| `mesh_quality` | `standard` | 沿用Q版预设，尚未供应商实测 |
| `faceNum` | `100000` | 技术预设，不保证质量或厂商实际归一化值 |
| `disablePbr` | `0` | 请求包含材质 |
| `onlyGenerateMesh` | `false` | 不只生成网格 |
| `enableImageEnhancement` | `false` | 不要求供应商改造输入图 |

此接口**不发送上述文本Prompt**。Prompt用于图像意图和版本追溯，不声称厂商使用了文本文化约束。当前正式概念图发送文件仍未接受；候选PNG Hash只是预计使用的规范化快照，不是“已上传Hash”。

**实际单次Credit费用：待确认。** 官方响应可能给出`pointsDeducted`，但这是提交后字段，不能替代调用前账户报价。没有把Mock80 Credit、专用多候选Q版接口价格或格式转换费用套用到普通单模型请求。`expectedCredits=null`，本次实际新增费用0。

固定全局SQLite账本核查：上限3、本地创建占用0、旧任务0、历史次数未核实、**剩余=null（未知）**。旧记录有1次只读余额鉴权；本轮新增Neural4D请求0次。其他工具/账户历史仍未核实，不能把本地0写成全项目0。真实生成关闭，无预约、批准、providerTaskId或退款操作。

原有SQLite原子预留、发送权、幂等、并发和全局UNKNOWN暂停机制保持；候选登记不触及账本。任何请求可能发送后不得自动返还次数或重建；Viewer问题先修Viewer，不创建新任务。历史未知时保持创建锁定。

## 8. 实际测试、失败与修复

环境：沿用Windows、项目Python3.11.1虚拟环境、Node24.15.0、本地FastAPI单worker和内嵌浏览器。没有安装新依赖。

| 验证 | 实际结果 | 证据 |
|---|---|---|
| 候选目录与HTTP接口首轮离线 | 48通过、1失败、1既有弃用警告；失败是测试要求显式`script-src 'none'`，实现当时仅由`default-src 'none'`禁用 | [原JUnit](../evidence/test-results/phase4-bluewhite-candidates-first.xml) |
| 后端全部离线 | 469通过，38.98秒，1既有Starlette弃用警告 | [全量JUnit](../evidence/test-results/phase4-bluewhite-full.xml) |
| 预览最终小修改后的候选专项 | 49通过，6.21秒，同一既有警告；未重复声称这是全量测试 | [专项JUnit](../evidence/test-results/phase4-bluewhite-candidates-final.xml) |
| 工坊前端离线 | 35通过、0失败；测试替身与静态检查，非真实模型生成 | [结果](../evidence/test-results/phase4-bluewhite-frontend.json) |
| 实际本地HTTP GET | 14通过、0失败：新图返回Hash/ETag、no-store、旧图404、非正式图片、创建仍锁定及8页字节一致 | [HTTP结果](../evidence/test-results/phase4-bluewhite-http.json) |
| 实际桌面预览 | 1920×1080，新ID和新Hash、1049×1398图片加载，无横向溢出 | [浏览器记录](../evidence/test-results/phase4-bluewhite-browser.json) |
| 实际手机窄视口 | 首次375×812标题版本名溢出；补`overflow-wrap:anywhere`与卡片`min-width:0`，刷新后scrollWidth360、无横向溢出，图片正确 | [修复前](../evidence/test-results/phase4-bluewhite-browser-before-mobile-fix.json)、[修复后](../evidence/test-results/phase4-bluewhite-browser.json) |
| 控制台 | 本轮候选预览捕获error列表为空，图片complete=true，页面无脚本 | 同上 |
| 原项目保护 | 7文化HTML与Phase 3基线无差异，8页本地HTTP返回字节与文件一致 | Git差异及HTTP结果 |

执行过的命令结构如下；pytest的新目录参数及工具输出以本轮公开会话原文为准，尖括号项是说明，不能直接复制为真实路径：

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp <已验证的新测试目录> --junitxml <本轮证据路径>
.\.venv\Scripts\python.exe -m pytest backend/tests/test_phase4_candidates.py backend/tests/test_phase4_candidate_api.py -q --basetemp <另一个新测试目录> --junitxml <专项证据路径>
node scripts/phase4_frontend_test.mjs --output docs/evidence/test-results/phase4-bluewhite-frontend.json
.\.venv\Scripts\python.exe backend/scripts/register_phase4_candidate.py --image 'D:\京剧\概念图.jpg' --history docs/evidence/test-results/phase4-concept-candidate-v1.json --manifest docs/evidence/phase-04/modeling/01-chibi/bluewhite-candidate-input.json --prompt docs/evidence/phase-04/modeling/01-chibi/bluewhite-prompt-input.json --output docs/evidence/test-results/phase4-bluewhite-candidate-registration.json
.\.venv\Scripts\python.exe scripts/phase4_candidate_http_check.py --output docs/evidence/test-results/phase4-bluewhite-http.json
.\.venv\Scripts\python.exe scripts/phase4_modeling_preflight.py --output docs/evidence/test-results/phase4-bluewhite-preflight.json
```

截图为本机私有 `D:\京剧\.runtime\phase4-bluewhite-screenshots\candidate-desktop-1920.png`、`candidate-mobile-before-fix.png`、`candidate-mobile-375.png`。未核实图片公开再分发许可，不将这些图片上传GitHub；公开仓库保留脱敏事实、Hash及本地路径。

首次沙箱内本地HTTP读取被权限拒绝，使用已允许的本地访问权限完成GET检查；预览重启时子进程退出使父进程同时退出，后续改为重查进程存在后终止。这些是本地验证环境问题，不是供应商失败。真实手机触摸/双指与本次角色3D旋转尚未验收；不能把此次图片预览检查代写为3D通过。

## 9. 改动与真实Git记录

功能只新增独立待审候选层、只读预览页、CLI登记和测试：`backend/app/assets/candidates.py`、`candidate_preview.py`、`backend/app/api/assets.py`、`backend/scripts/register_phase4_candidate.py`、两个候选测试文件、`scripts/phase4_candidate_http_check.py`。未修改前三阶段文化网页或Phase 3数据协议；配额、Provider与建模服务代码未修改。

真实提交 `bcc3a060190cabb7fb210205abda19382d0e1fa9`：`feat: preserve unassociated concept candidates as immutable snapshots`，包含候选层、隔离与缓存测试、CSP声明及手机标题换行修复。无空提交、历史改写或伪造时间。后续实际证据与Prompt归档另行提交，最新Hash以实际Git日志为准，不把尚未生成的文档提交Hash预填为事实。

原始更新需求、来源回复和公开开发过程由真实会话导出到`docs/prompts/phase-04/`；[Prompt索引](../prompts/phase-04/README.md)追加本轮变化，不虚构文化审核、付费调用或用户批准。

## 10. 停止条件与下一步

本次授权范围已完成：新图登记、缓存隔离、文化对照、技术风险、背景决定、待审Prompt和首次审核表。**正式角色Prompt及首次建模准备仍未就绪。**

发送前至少需要：具体来源/作者及许可范围、匹配且用户确认的Phase 3角色、图像及文化确认、全项目历史次数核查、单次账户报价、后端管理/协议条件，最后才展示完整包并取得单次明确建模批准。任何一项未知均不提交。没有自动进入第1次，也没有启动Phase 5；当前停止等待用户下一步决定。
