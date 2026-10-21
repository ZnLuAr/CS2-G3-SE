# docs/

本目录用于存放项目相关文档、设计材料与最终报告素材。

## 从这里开始

**当前状态：** SYS 基础层、v4 数据库初始化与检查、领域服务和用例层（Service/Logic）、CLI 装配、Web 认证路由及后台任务（Worker）骨架已接入。浏览器端 `frontend/` 已建立登录、角色导航、身份与 API 客户端及测试入口；领域方法和业务页仍为占位，真实 MySQL 建表和业务联调待验证。`architecture.md` 是系统总览；详细合同见前后端分册。

默认 CLI 和 Web API 都启动候补核对、推荐刷新的周期任务；应用关闭时先等待任务停止，再释放数据库资源。当前任务依赖的业务方法仍为占位。

第一次参与不需要一次读完所有设计，按这个顺序即可：

1. 看[项目简介与成员表](../README.md)，了解我们做的是健身房管理，谁在参与。
2. 看 [README 后部的技术栈](../README.md#技术栈)，了解所用工具。默认先完成 CLI，TUI 是时间允许时再做的可选界面。
3. 按 [README 的成员分工](../README.md#小组成员排名不分先后)，在[功能清单](./feature-list.csv)筛选自己的名字；共同负责的条目先商量谁实现、谁配合，并写到开发备注。P0 是核心，P1 是配套，P2 是候选。
4. 从[架构任务导航](./architecture.md#找到自己要做的功能)按负责人、功能 ID 找到领域章节和代码入口，再按任务进入[后端架构](./architecture/backend.md)或[前端架构](./architecture/frontend.md)。后端分册包含公共接口、目标 SQL、事务和领域合同；前端分册包含角色入口、页面、状态和 API 使用。
5. 看[项目规范](./project-standards.md)和 [Git 操作教程](../README.md#小组协作规范)。拿不准字段、接口或规则时先记录问题，和相关模块的组员对齐。

### 功能表怎么填

CSV 是可以用 Excel、表格软件或文本编辑器打开的表格。用表格软件时选择 UTF-8 编码；如果只显示一列，按逗号分隔导入。保存为 UTF-8 CSV，不要把扩展名改成 xlsx 后覆盖原文件。

前端由 Lvzhen ZHOU 负责，后端按领域分工。每行对应一项可独立验收的业务操作，页面可以组合多项操作。

- `交付类别` 用于筛选后端业务、前端、工程、测试或扩展。
- `关联ID` 记录前后端对应和业务协作；多个编号以英文分号分隔。
- `依赖ID` 记录本项验收所需的前置任务；多个编号以英文分号分隔。开发顺序先满足依赖，再按优先级推进。

- `ID` 是任务的固定编号，例如 `MEM-01`，讨论和提交时都可以引用，不要随意重编号。
- `负责人` 表示当前负责成员；同一格用中文分号分隔共同负责的成员。调整分工时同步 README 与功能清单。
- `状态` 表示进度，不等同于“架构是否批准”或“负责人是否确定”。规则尚未明确的条目为待确认，已确认且尚未实现的条目为待开发；有了签名不表示功能已完成。
- `验收要点` 写怎样看出功能做对了；开发时遇到不明确的规则，写到`开发备注`并讨论。
- 状态通常为“待确认 → 待开发 → 开发中 → 待验收 → 已完成”；遇到依赖未完成等情况标“阻塞”，注明等什么。
- 架构确认不等于每项功能都确认。只有该功能范围、规则和负责人明确后，才改为“待开发”。
- 功能状态以 [`feature-list.csv`](./feature-list.csv) 当前内容为准；状态表示实际实现进度，不因已有接口骨架而提前标记完成。
- 每行对应一个可独立开发和验收的操作；查任务时优先按模块和负责人筛选。
- 健身房卡、私教课包与销售权益由 Xingzhou PENG 负责，收款与报表由 Mingjin LI 负责；两人共同对齐销售订单、付款、赠卡和权益生成的同一事务。签到归 Yihao QIAN，未单列的消课和缺席处理先归 Lvzhen ZHOU。整体测试由 Lvzhen ZHOU 统筹，各模块负责人仍补本模块测试。

### 怎样在骨架中完成一个功能

以 `MEM-01 会员建档` 为例。后端开工时先以[后端架构](./architecture/backend.md)核对目标类型、SQL、权限和调用方；前端开工时再以[前端架构](./architecture/frontend.md)核对页面和 API 依赖。同步代码中的占位签名并实现方法，返回类型保持 `View` 或 `Page[T]`，未完成的方法继续保留明确占位。

| 步骤 | 要做什么 | 完成这一步时应有什么 |
|------|----------|----------------------|
| 1. 确认要求 | 读 CSV 和设计中的会员字段，确认谁能建档、哪些必填、是否允许重名 | 能用自己的话说清输入和结果；不明确的规则有讨论结论 |
| 2. 对齐数据 | 先看设计“公共接口约定”和对应领域类型，再同步 `src/models/contracts.py` 与目标表 | 姓名、联系方式、空值和返回类型只有一套约定，列表不临时改成字典 |
| 3. 实现数据访问 | 在 `src/db/member_repo.py` 补会员保存或查询 | 能用传入的数据库会话读写，不自行提交业务事务 |
| 4. 实现业务服务 | 在 `src/services/member_service.py` 使用传入的数据库会话（Session）检查权限、字段并调用仓储 | 正常返回会员详情（MemberView）；失败抛项目异常 |
| 5. 接入流程层 | 在 `src/logic/member_logic.py` 创建会话、调用会员服务并管理事务 | 成功提交、失败回滚、查询与写入后关闭会话 |
| 6. 接入交互入口 | CLI 处理器或 Web API 收集输入、取得操作者身份（Actor）、调用 Logic 并展示结果；Web 页面按 API 合同联调 | 用户能够从菜单或页面完整操作，取消输入时不创建会员 |
| 7. 验证 | 测正常建档、空姓名、无权限、用户取消、重启后查询 | 测试检查实际结果；失败原因有记录 |
| 8. 交给队友检查 | 同步文档与 CSV，说明改了什么、怎么测的，再按 Git 教程提交 | 队友不用猜就能复现；通过验收后再标“已完成” |

按“用户操作 → Logic → Service → DB”查找改动位置。例如调整列表显示时检查交互格式化；改变建档规则时同步服务和对应验收。

### 如何验证和汇报问题

测试分为：契约测试核对设计与声明，单元测试检查独立规则，API 测试验证 HTTP 适配，集成测试检查真实数据库配合，完整流程测试检查用户能否从头到尾完成任务。后端用例分别位于 `tests/contracts/`、`unit/`、`api/` 和 `integration/`，公共准备资源位于 `support/`（步骤见[后端测试说明](../tests/README.md)）。

前提：已安装 Python 3.10 或以上版本和开发依赖。在仓库根目录（能看到 main.py 的目录）执行：

```bash
python -X utf8 -m pytest tests/contracts -q
python -X utf8 -m src.cmd.test
```

第一条命令运行契约测试；第二条命令运行契约、单元及 API 适配测试并排除 MySQL 专用用例。API 测试使用 Logic 替身检查 HTTP 适配；真实业务流程使用 MySQL 集成测试验证。若出现 `FAILED`，根据报错的类、方法或表名同时核对设计和源码；若未收集到测试，检查所在目录和文件名。若找不到 python，先安装 Python 并确认终端可执行该命令。

### 启动 Web API

以下真实数据库启动步骤待 MySQL 环境验证。前提：Python 3.10 以上、Web 运行依赖、根目录的 `config.json` 和已初始化为 v4 的 MySQL 数据库。Web API 使用 `GYM_JWT_SECRET` 环境变量保存至少 32 字节的随机签名密钥；密钥只保留在当前终端环境。

在仓库根目录使用 PowerShell 执行：

```powershell
python -m pip install -r requirements/all.txt
$secretBytes = New-Object byte[] 32
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($secretBytes)
$env:GYM_JWT_SECRET = [Convert]::ToBase64String($secretBytes)
$rng.Dispose()
python -m src.web.main
```

启动成功后，Uvicorn 按 `config.json` 的 `web.host` 和 `web.port` 监听，`/docs` 提供 OpenAPI 页面。Ctrl+C 关闭 Worker 与数据库连接池。缺少签名密钥或密钥过短时，检查当前终端的 `GYM_JWT_SECRET`；连接失败或结构版本不符时，检查数据库配置并先执行 v4 初始化。当前登录用例仍为占位，启动结果不代表业务登录已完成。

测试至少说明“准备了什么数据、做了什么、希望结果是什么”。例如：“姓名为空时建档被拒绝，数据库会员数量不变。”不要只写“测试通过”。把未运行的检查如实标出来。

### 启动浏览器应用

前提：安装 Node.js 20.x（至少 20.19）、22.x（至少 22.12）或 24 以上版本，并使用随附 npm。后端地址由 `frontend/.env.example` 中的 `API_PROXY_TARGET` 指定，默认 `http://127.0.0.1:8000`；浏览器以 `/api` 请求开发代理。仓库根目录进入浏览器应用：

```bash
cd frontend
npm ci
npm run dev
```

开发服务器启动后访问 `http://127.0.0.1:5173`，可以看到登录页；真实登录需后端认证 Logic 就绪。自定义地址时，先复制 `.env.example` 为 `.env.local`，修改公开连接配置并重启开发服务器。安装失败时核对 Node 版本和 npm 源；代理连接失败时检查后端进程及地址。构建、单元与浏览器测试步骤见[前端说明](../frontend/README.md)。

### 安装与测试命令

在仓库根目录创建 Python 3.10 以上的虚拟环境后安装 `requirements/all.txt` 和 `requirements/dev.txt`。复制
`config.json.example` 为 `config.json` 填写日常数据库；需要 MySQL 集成测试时，再复制
`config.test.json.example` 为 `config.test.json`，将数据库名保持为 `_test` 结尾，并设置
`TEST_DB_PASSWORD`。日常密码变量 `DB_PASSWORD` 不会被测试命令传入子进程。

首次准备环境时，在仓库根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

激活成功后，`python -c "import sys; print(sys.executable)"` 应指向本仓库的 `.venv`。若 PowerShell 阻止激活脚本，将后续命令中的 `python` 替换为 `.\.venv\Scripts\python.exe`；Linux 与 macOS 使用 `source .venv/bin/activate`。本工作区的后端检查使用该虚拟环境执行。

依赖按运行场景分组：

| 文件 | 用途 | 安装命令 |
|---|---|---|
| `requirements/core.txt` | 默认 CLI、数据库和密码哈希 | `python -m pip install -r requirements/core.txt` |
| `requirements/web.txt` | Web API 运行依赖；需与核心依赖一起安装 | `python -m pip install -r requirements/core.txt -r requirements/web.txt` |
| `requirements/all.txt` | 核心与 Web 的全部运行依赖 | `python -m pip install -r requirements/all.txt` |
| `requirements/dev.txt` | pytest 和 API 测试工具 | `python -m pip install -r requirements/dev.txt` |

```bash
python -m pip install -r requirements/all.txt
python -m pip install -r requirements/dev.txt
python -m src.cmd.test                 # 运行不连接 MySQL 的测试
python -m src.cmd.test mysql --config config.test.json  # 仅 MySQL 测试
python -m src.cmd.test all --config config.test.json    # 全部测试
```

默认测试成功返回 0；测试失败、未收集到测试或测试环境不可用返回 1。`mysql` 和 `all`
模式缺少配置、测试库名不以 `_test` 结尾或数据库命名锁被占用时，在清理前返回 1。

依赖安装、默认测试和契约检查已有执行记录；`mysql`、`all` 及真实数据库启动步骤需在专用测试库就绪后验证。数据库测试会清理专用库的结构或业务数据，完整前提和失败处理见[后端测试说明](../tests/README.md#mysql-集成测试)。

如果卡住，把下面的信息发给相关组员或写进测试笔记，通常比只说“跑不了”更容易定位：

```text
功能编号：MEM-01
所在分支与文件：填写当前分支和正在改的文件
操作步骤：从哪个目录启动，依次输入了什么
预期结果：本来应该发生什么
实际结果：出现了什么，附必要的错误文字并去掉密码等敏感信息
已经尝试：检查或修改过什么
需要协助：哪条规则不清楚，或者卡在哪一步
```

## 文档总览

### 课程资料（docs/ 根目录）

| 文件 | 用途 |
|------|------|
| [`project-introduction.md`](./project-introduction.md) | Practical 1 讲义完整中文翻译（原文 PDF 留档） |
| [`(Week1)-JC2001-Practical1-IntroductionsGroups&Projects.pdf`](./(Week1)-JC2001-Practical1-IntroductionsGroups&Projects.pdf) | Practical 1 原始 PDF |

> 后续课程的讲义 / 要求 PDF 请放入本目录，并按需补充中文翻译，命名与原有文件保持一致。

### 项目文档

| 文件 | 用途 | 对应交付物 |
|------|------|--------------|
| [`feature-list.csv`](./feature-list.csv) | 功能范围、优先级、负责人、状态与验收要点 | Project Proposal / 开发与测试 |
| [根 README 的技术栈](../README.md#技术栈) | 已确定的技术方向与建议选型 | 技术报告 |
| [`project-standards.md`](./project-standards.md) | 代码规范、质量要求、协作与完成标准 | 开发与测试 |
| [`architecture.md`](./architecture.md) | 系统架构总览、公共约定和前后端分册入口 | 技术报告 / PoC |
| [`architecture/backend.md`](./architecture/backend.md) | Logic、Service、DB、类型、SQL、权限、事务、后台任务和后端验证 | 技术报告 / PoC |
| [`architecture/frontend.md`](./architecture/frontend.md) | Web 页面、路由、角色入口、状态、API 使用和前端验收 | 技术报告 / PoC |

系统总览集中在 `architecture.md`；后端和前端详细设计分别集中在两个架构分册。

功能清单中的 P0 是核心功能与必要保障，P1 是配套功能，P2 是候选。负责人按当前分工填写，状态按实际进度更新为“待开发 / 开发中 / 待验收 / 已完成”，有阻碍时标“阻塞”。完成后在开发备注中留下实现和验证说明；负责人和状态分别表示分工与实际进度。CSV 使用 UTF-8 BOM，便于 Excel 打开中文。

### 开发素材（[`dev-materials-for-report/`](./dev-materials-for-report/)）

面向最终报告与各次 project update 的过程性材料，模板与写作建议见该目录下的 [`README.md`](./dev-materials-for-report/README.md)。

| 文件 | 用途 | 对应交付物 |
|------|------|--------------|
| [`dev-materials-for-report/design-decisions.md`](./dev-materials-for-report/design-decisions.md) | 设计决策记录："为什么这么做" | 技术报告 / 答辩 |
| [`dev-materials-for-report/development-log.md`](./dev-materials-for-report/development-log.md) | 时间线式开发日志：什么时候改了什么 | Project updates / 技术报告 |
| [`dev-materials-for-report/testing-notes.md`](./dev-materials-for-report/testing-notes.md) | 测试与调试笔记：发现的 bug 与修复过程 | 技术报告 / PoC |
| [`dev-materials-for-report/meeting-notes.md`](./dev-materials-for-report/meeting-notes.md) | 会议记录：组会、与导师的 meeting | Project updates / 答辩 |

## 使用建议

- **边开发边记**：开发过程中产生的设计决策、踩坑、反思应该**当场**写进对应文档，不要拖到最后回忆 ~~（实在不行可以让 AI 帮忙）~~
- **统一风格**：每条记录建议带日期 `[YYYY-MM-DD]`，便于追溯
- **直接面向报告**：写文档时就当作是在写报告，最终可以直接复用内容
- **有话可说的秘诀**：老师评分看的是**过程**——需求从哪来、为什么这样设计、迭代中改了什么、测试发现了什么。每份课程 PDF 发下来，先过一遍"哪些点会在报告/答辩里被问到"，把答案的素材积累到对应文档里。

---

> 本目录中的内容随开发进度持续补充，欢迎大家补充与修订😋
