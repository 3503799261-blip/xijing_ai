# 戏境 AI · 部署、私有资源与恢复说明

核对日期：2026-10-22（Asia/Shanghai）。WP5只读核对基线：`61064b0842e5f3789c01b107dd0b2a3f45c55adb`。本文件是当前代码和历史实测的交付说明；本轮没有安装、下载、启动、重建数据库或访问供应商。

**已完成同机隔离副本验证；跨机器完整恢复尚未验证。** Git克隆不包含私有任务、预算、全局额度账本、概念图、两个真实GLB和BGE缓存，不能承诺空白电脑10分钟完整恢复成品。

## 1. 依据与实际验证范围

| 核对项目 | 实际依据 | 能说明什么 / 不能说明什么 |
|---|---|---|
| 当前配置和服务 | [config.py](../../backend/app/config.py)、[main.py](../../backend/app/main.py)、[README](../../README.md)、[配置模板](../../.env.example) | 原生多页前端和API由同一FastAPI进程提供；没有前端构建步骤 |
| 普通隔离venv安装 | [原始安装结果](../evidence/test-results/phase-05-wp4/cold-install-attempt03-result.json)、[导入验证](../evidence/test-results/phase-05-wp4/cold-env-attempt03-runtime-verification.json) | 2026-10-20同机Python 3.11.1，`include-system-site-packages=false`；pip安装348.549秒，66个实际包，11个顶层固定依赖导入和pip check通过；不是跨机空白系统计时 |
| 受控资源恢复 | [资源复制清单](../evidence/test-results/phase-05-wp4/resource-copy-manifest.json)、[隔离HTTP](../evidence/test-results/phase-05-wp4/http-isolated-restored.json)、[冷环境模型浏览器](../evidence/test-results/phase-05-wp4/models-cold-browser.json) | 停止源服务后，受控副本、已有BGE、空Key配置可在同机另一父目录运行并读取真实模型；没有公开资源包或一键跨机恢复工具 |
| 修复后的数据库安全 | [WP4测试报告第10节](../evidence/test-results/phase-05-wp4-test-report.md)、[显式初始化9项](../evidence/test-results/phase-05-wp4-db-repair/explicit-init-cli.json)、[现场恢复42项](../evidence/test-results/phase-05-wp4-db-repair/field-final-summary.json) | 严格已有库打开、显式全新初始化、Agent故障隔离与恢复实测；不能用旧启动建库行为指导当前运行 |
| 原始数据与模型保护 | [修复后物理核对](../evidence/test-results/phase-05-wp4-db-repair/physical-final-comparison.json)、[关联核对](../evidence/test-results/phase-05-wp4-db-repair/provenance-after.json) | 原数据库、索引、BGE、模型和谱系保持不变；不是额外一次供应商连通性测试 |

WP4有原始失败和修复记录。专项41项包含在最终后端754项中，不相加为795；初始化CLI9项和现场42项分别是不同验证口径。完整统计见[测试证据索引](phase-05-evidence-index.md)。

## 2. 环境与依赖

- 实际验证平台：Windows / Python **3.11.1**。其他Python版本、Linux/macOS、另一台电脑未完成本项目完整恢复验证。
- 后端依赖固定于[backend/requirements.txt](../../backend/requirements.txt)：FastAPI 0.143.0、uvicorn 0.54.0、pydantic-settings 2.15.0、httpx 0.28.1、qdrant-client 1.19.1、sentence-transformers 6.1.0、CPU torch 2.11.0+cpu、numpy 2.4.4、pytest 9.1.1、Pillow 12.2.0、portalocker 3.2.0。安装还会解析间接依赖；这11项不是完整66包锁文件。
- 本机原`.venv`复用system-site-packages；WP4另建普通venv验证了独立安装。新机器应按requirements安装，不复制开发机venv作为通用环境。
- 页面运行不需要Node/npm。Node只用于已有离线前端测试；浏览器应支持ES Module和WebGL。现有浏览器证据主要为Chrome/headless WebGL，手机CDP模拟不等于实体手机或Safari认证。
- 默认单进程端口 **8000**。使用`--workers 1`，不在已有实例上叠加第二个进程；Qdrant local、Agent owner和建模管理器都有本地锁。

## 3. 配置与目录：使用仓库父目录，而非固定盘符

以下`<repo>`为所选代码目录，`<parent>`为其父目录；例如本开发机分别是`D:\京剧\京剧`与`D:\京剧`，但这不是公共服务地址或新机器必须复刻的路径。

```text
<parent>/
├── <repo>/                       # Git代码、knowledge摘要、文档、测试
├── .private-config/.env          # 私有配置，禁止提交或截图
└── .runtime/
    ├── models/bge-small-zh-v1.5/  # 固定revision模型和model-manifest.json
    ├── neural4d-usage.sqlite3    # 固定全项目额度账本，必须保留原历史
    └── xijing-ai/               # RAG_DATA_DIR默认值
        ├── active.json
        ├── generations/<id>/   # knowledge.sqlite3、qdrant/、manifest.json
        ├── agent-tasks.sqlite3
        ├── api-budget.sqlite3
        └── assets/             # catalog.sqlite3、图片、模型、原文件隔离区
```

配置由[Settings](../../backend/app/config.py)读取，浏览器不读取私有env：

| 配置名 | 用途与限制 |
|---|---|
| `XIJING_ENV_FILE` | 进程环境覆盖私有env位置；默认`<parent>/.private-config/.env`。使用仓库外明确路径，不覆盖已有配置 |
| `RAG_DATA_DIR` | 默认`<parent>/.runtime/xijing-ai`，包含知识与业务存储；覆盖时用仓库外绝对路径，不写空等号 |
| `EMBEDDING_MODEL_PATH` | 默认父目录缓存；必须在仓库外、已经准备好，运行时不隐式下载 |
| `EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5`；固定revision见模型准备脚本 |
| `DEEPSEEK_API_KEY` | 后端秘密；只查看现有历史/GLB无需调用DeepSeek |
| `DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`、`DEEPSEEK_THINKING_ENABLED` | 代码限制官方HTTPS地址、`deepseek-flash`和false；是已实现配置，不是WP5对当前供应商产品的重新核验 |
| `DEEPSEEK_MAX_OUTPUT_TOKENS`、`RAG_TEST_BUDGET_CNY`、`AGENT_TEST_BUDGET_CNY` | 默认800 / 3 / 0.5；持久化预算是本地估算保护，不是供应商硬扣费上限，不通过改目录或重启增加预算 |
| `AGENT_WORKFLOW_ENABLED` | 真实任务入口配置；只读演示不需新任务。页面备用模式仅保护本页，不改变服务端配置 |
| `ALLOWED_ORIGINS` | 精确loopback白名单；现代码只允许localhost/127.0.0.1的8000、8877来源。主演示使用8000同源；非本机公开部署未在本次验证范围 |
| `NEURAL4D_GENERATION_ENABLED` | **保持false**；第三次已取消，剩余1次不是继续建模授权 |
| `NEURAL4D_API_KEY`、`NEURAL4D_ADMIN_TOKEN` | 后端秘密；已有模型浏览不需要供应商请求，不为演示重新配置或验证付费接口 |

Neural4D账本由`main.py`固定为`<parent>/.runtime/neural4d-usage.sqlite3`，不随`RAG_DATA_DIR`选择新额度池。迁移代码父目录时必须连同真实账本受控保留；缺失时保持未知/创建关闭，不能从0初始化来替代。

## 4. 已准备环境的比赛启动

先确认现有资源与对应数据库已恢复、8000无重复实例，再在代码根目录执行：

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

访问地址均是操作这台电脑的本地地址：

- 首页：`http://127.0.0.1:8000/index.html`。
- 工坊及导览：`http://127.0.0.1:8000/about.html#ai-workshop-demo`。
- 历史档案：`http://127.0.0.1:8000/about.html#ai-workshop-history`；手动读取已有记录，不新建任务。
- 已有写实资产：`http://127.0.0.1:8000/about.html?assetId=9e2b42e1-bbad-4a2f-ab1b-aeda18015dee#ai-workshop-model`。
- 内部Q版Viewer：`http://127.0.0.1:8000/api/v1/assets/internal-models/3777a880-fc8c-4766-aade-948d20c6b8f0/viewer`，仅内部非公开验证，不直接纳入公开比赛传播。
- 免费本地检查：`/api/v1/health`、`/api/v1/capabilities`、`/api/v1/assets/usage`。健康状态不证明今天外部API连通、余额或权限；模型登记可读也不等于浏览器GLB加载成功。

停止时在启动终端Ctrl+C并等待退出。不要删锁文件或强开多worker。普通启动可能按原机制标记已保存中断任务，不是纯只读；不会因此自动重跑Agent、调用LLM或生成模型。

静态服务采用[公开白名单](../../backend/app/static_frontend.py)，只提供8个HTML及css/js/images/audio/media。不要替换成将仓库根完整暴露的通用HTTP服务器，否则可能泄露docs、`.git`或私有文件。

## 5. 全新安装：与恢复既有项目严格区分

以下是有条件的准备步骤，本WP5没有执行。先取得用户确认的实际交付分支/提交；最新本地提交未推送，不能假定远端已含本材料或此前修复。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

把[无密钥模板](../../.env.example)复制到所选仓库外私有位置，**仅文件不存在时创建**。手工设置路径；秘密只在本地编辑器填写，不发聊天，不放前端或公共终端输出。确认确实没有应恢复的历史、预算、资产或账本后，才执行：

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.initialize_business_databases --initialize-new-installation
```

[初始化实现](../../backend/scripts/initialize_business_databases.py)只建立Agent、预算、资产三个业务库；先检查所有已有库，遇损坏或不完整Schema停止。不会创建全局Neural4D账本、知识索引、BGE或真实模型。旧版仅含calls表的预算库不自动升级，不应按新安装覆盖。

只有首次模型/知识资源缺失时，按已有准备入口显式执行：

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.download_model
.\.venv\Scripts\python.exe -m backend.scripts.ingest --corpus knowledge
```

[模型下载](../../backend/scripts/download_model.py)使用固定revision`7999e1d3359715c523056ef9478215996d62a620`，保存模型Hash清单；BGE模型卡标注MIT。权重约95.8MB还不含PyTorch及间接依赖。首次外网下载速度和空白机器总耗时未在WP4/5完整计时，不承诺10分钟。

[入库](../../backend/scripts/ingest.py)从Git中的原创事实摘要建实际SQLite/Qdrant generation，512维；同语料/模型/分块参数重复执行返回unchanged。明确重建才使用`--rebuild`。运行前先停应用，避免local索引锁冲突；失败保留旧active，不换随机向量。不因现场检索失败自动执行下载/重建。

## 6. 私有资源清单与恢复边界

| 类别 | 资源和存储位置 | 恢复来源 / 当前边界 |
|---|---|---|
| Git已跟踪 | 8页、CSS/JS、backend、固定requirements、knowledge原创摘要、文档/文本证据、合法Duck测试夹具 | 从实际交付提交取得。原网页媒体虽已跟踪，公开权利仍待逐项核查；见[许可清单](phase-05-asset-provenance-and-permissions.md) |
| 本地私有 | `.private-config/.env`及秘密 | 用户在目标本机自行配置；不复制到公开交付，不截图，不在恢复清单保存秘密值 |
| 外部下载 | BGE缓存、模型卡和model-manifest；Python依赖 | 保留固定版本/Hash及许可证，或按明确下载命令准备；首次下载不是现有成品恢复证据 |
| 本地可重建知识 | `RAG_DATA_DIR/active.json`选择`generations/<id>/knowledge.sqlite3`与`qdrant/` | 同机已验证受控副本；也可由当前knowledge显式构建新索引。不能把RAG根下另建空knowledge.sqlite3当恢复 |
| 不可由Git重建的业务历史 | `agent-tasks.sqlite3`、`api-budget.sqlite3`、`assets/catalog.sqlite3` | 需经核对的私有备份；保持任务/人审/引用/资产ID一致。没有备份就没有可靠历史恢复方式，不重跑付费任务伪造旧结果 |
| 用户提供/授权范围有限 | `assets/candidate-originals/`、`candidate-images/`、`images/`中的概念图及授权记录 | 受控保留原文件/标准化图片和Hash，按真实许可范围恢复；不默认可公开随代码分发 |
| 供应商历史模型 | `assets/models/<sha256>.glb`及`recovery-quarantine/`原文件 | 两模型已有受控文件；不通过新建任务恢复。兼容GLB内嵌纹理，原件及转换谱系一起保留 |
| 固定额度历史 | `<parent>/.runtime/neural4d-usage.sqlite3` | 保留已用2/3、剩1未使用、累计60历史积分与任务ID；不得清零、换池、自动对账或生成第三模型 |
| 尚无可靠通用自动恢复 | 跨机器完整私有成果分发、缺失备份的业务历史、一键资产迁移 | 同机副本曾通过；没有一键公开包或跨机器完整演练。不要只clone后声称已恢复两成品 |

实际文件谱系：

| 文件 | 位置（相对`RAG_DATA_DIR/assets/`） | 字节数 / SHA-256 |
|---|---|---|
| Q版Viewer兼容GLB | `models/bf9c808c15dbf5464ee67df1cdb3f64f9b2c6b3cd4ee41ecb8a6470a0554654a.glb` | 8,827,324 / `bf9c808c15dbf5464ee67df1cdb3f64f9b2c6b3cd4ee41ecb8a6470a0554654a` |
| 写实Viewer兼容GLB | `models/5a021ac6338009615e6ea232c5b9001eef6f4cc91d9d87c3eeeb5307526bdfd5.glb` | 15,158,668 / `5a021ac6338009615e6ea232c5b9001eef6f4cc91d9d87c3eeeb5307526bdfd5` |
| Q版供应商原件 | `recovery-quarantine/`中Hash命名文件 | 26,600,184 / `8ef5de8a2f96fbbee9eea66737187e4a2087f88867830891a41464a473d47885` |
| 写实供应商原件 | `recovery-quarantine/`中Hash命名文件 | 18,266,484 / `51fc687e0bde5fdb9074ba4560601057e17e9239f111fd2bc9e0d6601c26260e` |

兼容处理保留原几何与对应纹理谱系，不作为任意新模型转换教程。文件格式、纹理、ID和来源关联详见[Phase4最终报告](phase-04-final-acceptance.md)，不是完整Khronos认证或游戏生产规格认证。

## 7. 数据库安全与现场恢复

[统一连接层](../../backend/app/database.py)在普通运行使用`mode=rw`或`mode=ro`，不创建缺失文件，检查文件、quick_check、所需表列与对象。不会自动迁移、删坏库、补表或用空库遮盖丢失历史。结构检查不等于全部业务语义、触发器SQL正文或真实数据库身份认证。

| 故障 | 当前实际行为 | 合理恢复步骤 |
|---|---|---|
| 错误数据路径或Agent缺库 | 不在错误位置创建空库；Agent接口503，健康检查区分降级 | 停服务，核对配置及预期任务ID/数量，恢复确切原库，再重启；不能运行“新安装”制造空历史 |
| Agent库损坏/结构不完整 | 不重建，不覆盖；历史/相关Agent操作503，静态页面仍可响应 | 保留损坏文件及证据，在隔离副本检验备份，人工选定有效库后受控恢复并重启 |
| 预算库不可用 | 停止真实付费调用，不显示虚假0用量 | 核对原预算备份及数据身份，不改路径重置额度；恢复后重启 |
| 资产catalog不可用 | 资产接口不可用，不能绕过catalog直接暴露私有目录 | 恢复catalog与文件的同一套关联；不许拿Duck补成品或重新建模 |
| BGE/知识SQLite/Qdrant缺失 | 分类提示未就绪；可用历史/独立GLB继续展示 | 检查缓存/active/generation及锁，按确切备份恢复；只有另行明确准备时才重建知识 |
| 额度账本不可用 | 已有catalog/文件可读时仍可看模型，创建锁定/状态未知 | 保留并恢复原全局账本，不另建额度池，不消费剩余1次 |
| GLB加载失败 | Error提示，允许重读同一已保存文件 | 检查文件Hash/路径/材质/浏览器；修复后重载，不访问Neural4D、不重新生成 |

Agent库故障下已有GLB可看，以**独立资产catalog和文件完好**为前提，不保证所有数据库同时损坏仍能展示。恢复Agent/预算后当前设计需**重启服务**；误指向另一份Schema有效数据库，程序无法自动认出它不是本项目正确数据，仍须人工核对库身份、任务ID与资源清单。

备份时先正常停止服务，避免Qdrant local锁及复制不一致；SQLite使用受控一致性备份或停机全套保留，注意WAL/SHM状态，不在运行中随意只复制主文件。WP4证据中的SQLite online backup可能物理Hash与源不同，但逻辑数据与Schema核对一致；停机原文件Hash核对和逻辑核对分别解释，不混为一项。

## 8. 交付前安全检查与未验证项

- 不提交私有env、API Key、管理Token、签名URL、完整业务DB、原概念图或成品GLB；[.gitignore](../../.gitignore)不是万能秘密扫描，提交前仍检查实际diff和文件清单。
- 不在公开日志/视频中展示个人信息、数据库内容、私有路径或完整供应商响应。公开材料只使用必要ID、Hash、脱敏证据；原素材含图截图需单独核查传播许可。
- 两次模型累计历史60积分，已用2/3、剩1未使用；第三次是用户决定不执行，不是失败。保持创建false，不为演示重查余额、不运行供应商探测或付费回归。
- 本地HTTP、健康检查、原始测试证据不能证明外部API今日可用。实时问答/Agent需要密钥、预算、外网和显式提交；只读备用演示仍需要本地服务、数据库与文件，不是离线大模型。
- 未验证：实体手机、真实Windows ACL变化、另一台空白电脑完整恢复、公开部署安全边界、当前外部付费API连通、真人录制成片。已完成同机普通venv及受控副本演练不能替代这些项目。

与[演示脚本](phase-05-demo-script.md)、[最终提交检查表](phase-05-submission-checklist.md)配合使用；不得因为本说明已编写就把尚未核实的官方格式、素材权利或部署能力标为完成。
