# JC2001 Software Engineering Group Project — Group 3

## 软件工程导论 · 小组大作业

---

> 继承 OP 之意志（大雾）

## 项目简介

本仓库用于 **JC2001 Introduction to Software Engineering** 课程的小组大作业：一个软件产品开发项目（software product development project）。

**项目主题：健身房管理系统。** 面向会员、教练、前台和管理员。系统分别销售健身房卡与私教课包；购买指定课包时可以按产品规则赠送期限健身房卡。预约消耗课包额度，入场可以使用有效健身房卡或上课当天的有效私教预约。核心流程为“会员建档 → 销售权益 → 预约或入场 → 签到与消课 → 评价与报表”，并提供器械管理和体测记录。

### 📚 文档导航

课程资料、系统设计与过程记录集中在 [`docs/`](./docs/)，完整索引见 [`docs/README.md`](./docs/README.md)。Git 协作说明与简要技术栈保留在本 README。

快速指引，可以按顺序阅览：

| 你想…… | 去哪里 |
|--------|--------|
| 查看阅读顺序与参与步骤 | [`docs/README.md` 的参与指引](./docs/README.md#从这里开始)（阅读顺序、任务分工、开发与验收示例） |
| 了解作业要求、截止时间 | [`docs/project-introduction.md`](./docs/project-introduction.md)（Practical 1 讲义中文翻译） |
| 查看负责模块的设计及与其他模块的衔接 | [系统架构总览](./docs/architecture.md)、[后端架构](./docs/architecture/backend.md)、[前端架构](./docs/architecture/frontend.md) |
| 查看代码规范和质量要求 | [`docs/project-standards.md`](./docs/project-standards.md) |
| **记录开发过程（给报告攒素材）** | [`docs/dev-materials-for-report/`](./docs/dev-materials-for-report/)，四选一：设计决策 / 开发日志 / 测试笔记 / 会议记录 |
| 学习怎么用 Git / PR 协作 | 本 README 的[小组协作规范](#小组协作规范) |
| 查看功能细项与分工 | [`docs/feature-list.csv`](./docs/feature-list.csv) |
| 了解技术栈 | 本 README 后部的[技术栈](#技术栈)（Python、MySQL、FastAPI 和 Vue，默认 CLI、可选 TUI） |

> ⚠️ **报告素材（决策记录、开发日志、测试笔记、会议记录）应该边开发边写**，不应拖到 ddl 才回忆。课程评分看的是**过程**——素材从哪积累、最终报告就有多少话可说。

---

### 课程关键时间线（2026）

| 事项 | 截止时间 |
|------|----------|
| 完成分组（MyAberdeen 自助选组） | 2026-09-14 23:59 CST |
| 提交项目提案（Project Proposal） | 2026-09-25 23:59 CST |
| 项目进展更新 / 技术报告 / PoC 软件 / 答辩 | 见 MyAberdeen 课程页 |

## 小组成员（排名不分先后）

当前分工：

| 姓名 | 负责部分 | GitHub ID |
|------|----------|-----------|
| MINGJIN LI | 体测、收款、报表 | Matthew-0223 |
| XINGZHOU PENG | 会员、会员卡 | xing-520 |
| YIHAO QIAN | 签到、评价 | - |
| TUAO SONG | 器械、体测 | - |
| JIAFENG YE | 账号与权限、异常与日志 | Kelvinvoyage |
| WEIJIE ZHOU | 教练、课程、预约 | Q123422 |
| YUXI ZHU | 课程、预约 | shaun070119 |
| Guanyu ZHOU | 文档报告编写 | - |
| Lvzhen ZHOU | 浏览器前端、整体测试与其余部分 | ZnLuAr |

## 仓库结构

下面展示主要文件，省略各包的 `__init__.py` 和同类业务文件；分层职责见[系统架构总览](./docs/architecture.md)。

```
.
├── main.py                         # 程序入口，解析参数并启动
├── src/                            # 应用代码包
│   ├── app.py                      # 应用生命周期与资源装配
│   ├── config.py                   # 配置读取：数据库、日志、时区与 Web
│   ├── cmd/                        # 数据库、测试和本机日志命令
│   │   ├── db.py                   # init：建表；check：必需表与版本核对；seed：演示数据
│   │   ├── logs.py                 # 按本机配置浏览日志快照
│   │   └── test.py                 # unit/mysql/all：统一测试入口
│   ├── security/                   # 密码格式校验、哈希与验证
│   ├── logging/                    # 日志生命周期、事件与快照合同
│   │   ├── lifecycle.py            # 配置与关闭
│   │   ├── events.py               # 固定操作名、结果与脱敏事件
│   │   └── snapshots.py            # 固定快照读取与查询
│   ├── errors/                     # 异常定义与统一处理
│   ├── models/                     # 数据模型与类型定义
│   │   └── contracts.py            # 公共类型：Input、View、Page
│   ├── logic/                      # 用例层骨架：跨服务编排、Session 与事务
│   ├── services/                   # 领域服务：权限、数据范围与业务规则
│   │   ├── auth_service.py         # 账号与权限
│   │   ├── member_service.py       # 会员档案
│   │   ├── notification_service.py # 站内通知
│   │   ├── waitlist_service.py     # 候补队列
│   │   ├── recommendation_service.py # 课程推荐
│   │   └── ...                     # 其他业务服务
│   ├── db/                         # 仓储与数据库运行工具
│   │   ├── connection.py           # 连接池管理
│   │   ├── *_repo.py               # 各模块数据访问对象（DAO）
│   │   └── ...
│   ├── ui/                         # 用户界面层
│   │   ├── cli/                    # 命令行界面（默认）
│   │   │   ├── app.py              # CLI 主循环
│   │   │   ├── menus.py            # 菜单定义
│   │   │   ├── prompts.py          # 输入收集
│   │   │   ├── formatters.py       # 结果展示
│   │   │   └── handlers/           # 业务交互处理器
│   │   └── tui/                    # 终端界面（可选）
│   │       └── app.py              # TUI 入口占位
│   ├── web/                        # FastAPI HTTP 适配与认证骨架
│   └── tasks/                      # 单线程周期调度与关闭协调
├── frontend/                       # Vue、TypeScript 浏览器前端与前端测试
├── tests/                          # 后端测试
│   ├── contracts/                  # 架构与源码声明一致性
│   ├── unit/                       # 配置、交互与资源单元测试
│   ├── api/                        # 使用 Logic 替身的 HTTP 适配测试
│   ├── integration/                # 独立 MySQL 集成测试
│   └── support/                    # 共享 CLI 与 MySQL fixture
├── sql/                            # 数据库初始结构脚本
│   └── 001_initial_schema.sql      # v4 初始结构
├── requirements/                   # 按运行场景分组的 Python 依赖
│   ├── core.txt                    # 默认 CLI 与数据库依赖
│   ├── web.txt                     # Web API 运行依赖
│   ├── dev.txt                     # 开发与测试工具
│   └── all.txt                     # 全部运行依赖，不含测试工具
├── docs/                           # 文档目录
│   ├── README.md                   # 文档索引
│   ├── architecture.md             # 系统架构总览
│   ├── architecture/backend.md     # 后端架构与接口合同
│   ├── architecture/frontend.md    # 前端架构与交互合同
│   ├── project-standards.md        # 代码与文档规范
│   ├── feature-list.csv            # 功能清单与实现状态
│   └── dev-materials-for-report/   # 报告素材（开发日志、决策记录等）
├── .gitignore
├── AGENTS.md                       # Agent 协作规范
└── README.md                       # 本文件
```

`__init__.py` 标识 Python 包，异常包还统一导出公共类型。共用的数据类型在 [contracts.py](./src/models/contracts.py)；[会员档案服务](./src/services/member_service.py)展示公开方法签名和中文说明的写法。后端测试分类与运行步骤见 [tests/README.md](./tests/README.md)，浏览器应用与测试见 [frontend/README.md](./frontend/README.md)。

**当前状态**：SYS 基础层、v4 数据库初始化与检查、Service/Logic、CLI 装配、Web 认证路由和 Worker 骨架已接入。浏览器端 `frontend/` 已建立登录表单、角色导航、身份恢复、API 客户端与测试入口；领域方法、CLI 操作和浏览器业务页仍为占位，真实 MySQL 建表和业务联调待验证。架构入口见 `docs/architecture.md`，详细合同分别见前后端分册。`--help` 和 `python -m src.cmd.test` 不连接 MySQL；正式业务流程需完成身份及业务方法实现。

默认 CLI 与 Web API 都会启动候补核对和推荐刷新的周期任务；关闭应用时先等待任务退出，再释放数据库连接池。任务调用的领域方法仍为占位。

已验证的帮助与默认测试命令（先按[安装步骤](./docs/README.md#安装与测试命令)准备依赖，在仓库根目录执行）：

```bash
python main.py --help
python -m src.cmd.test
```

数据库操作命令待专用 MySQL 环境就绪后验证。先创建空数据库，将连接信息填入本地 `config.json`，再按需执行：

```bash
python -m src.cmd.db init --config config.json
python -m src.cmd.db check --config config.json
python -m src.cmd.db seed --config config.json
```

`init` 建立 v4 表结构，`check` 核对必需表和结构版本，`seed` 交互输入四类演示密码。连接失败时检查 MySQL 服务和配置；目标库已有对象时，改用新建空库初始化。专用测试库准备与清理规则见[后端测试说明](./tests/README.md#mysql-集成测试)。

文档组织、协作步骤和技术合同见本项目的参与指引、项目规范与架构分册。

## 小组协作规范

> 以下说明覆盖日常开发流程、提交规范与 PR 审阅。下面命令在仓库根目录执行（能看到本 README 和 `docs/` 的目录）。`<文件名>`、`<功能名>` 是占位符，执行时替换为实际名称，去掉尖括号。

### 核心原则

**重要：不要直接在 `main` 分支上改代码。**

`main` 分支是稳定版本，只接受经过验证的代码。所有开发都在功能分支上进行，通过 Pull Request 合入 `dev`。

---

### 分支管理

| 分支 | 用途 | 谁可以直接提交 |
|------|------|----------------|
| `main` | 稳定版本，用于里程碑提交 | 仅通过合并 `dev` 更新 |
| `dev` | 开发集成分支 | 仅通过 PR 合入 |
| `feat/<功能名>` | 功能开发分支 | 创建者，通过 PR 合入 `dev` |
| `fix/<问题描述>` | Bug 修复分支 | 创建者，通过 PR 合入 `dev` |

---

### 标准工作流程

这是所有开发任务的统一流程，从克隆仓库到功能合并的完整步骤。

#### 第一次使用：克隆仓库

```bash
# 1. 克隆仓库到本地
git clone git@github.com:ZnLuAr/CS2-G3-SE.git
cd CS2-G3-SE

# 2. 切换到 dev 分支
git checkout dev

# 3. 确认当前分支
git branch
# 应该看到 * dev（星号表示当前分支）

# 4. 复制配置文件模板
cp config.json.example config.json
# 然后编辑 config.json，填入实际的数据库配置
# 注意：config.json 已在 .gitignore 中，不会被提交
```

#### 1. 开始新任务

```bash
# 确保 dev 是最新的
git checkout dev
git pull origin dev

# 创建功能分支（根据任务类型选择前缀）
git checkout -b feat/member-crud        # 新功能
# 或
git checkout -b fix/booking-conflict    # Bug 修复

# 确认当前在新分支上
git branch
# 应该看到 * feat/member-crud
```

#### 2. 开发和提交

```bash
# 开发代码...

# 查看修改
git status
git diff

# 提交前自查
# （如果使用 Agents，可以让 AI 遵循 .agents/skills/code-review/SKILL.md）：
# - 业务逻辑：返回类型、异常、事务、业务规则
# - 安全性：输入验证、SQL 注入、密码处理
# - 代码质量：命名、职责、复杂度、错误处理
# - 文档同步：对应架构分册、参与说明和功能清单

# 暂存和提交
git add <文件名>
git commit -m "feat(member): 实现会员建档功能"
```

#### 3. 推送并创建 Pull Request

```bash
# 推送到远程（首次推送会创建远程分支）
git push origin feat/member-crud

# 访问 GitHub 仓库页面会看到 "Compare & pull request" 提示
# 或直接访问：https://github.com/ZnLuAr/CS2-G3-SE/pulls

# 创建 PR：
# - Base: dev
# - Compare: feat/member-crud
# - 填写标题和描述（参考下文"PR 标题与描述"）
```

#### 4. 响应审阅意见

```bash
# 如果审阅者提出修改建议：

# 在本地修改代码后提交
git add <文件名>
git commit -m "fix: 根据审阅意见修改验证逻辑"

# 推送更新（PR 会自动更新）
git push origin feat/member-crud
```

#### 5. 合并后清理

```bash
# PR 合并后，切回 dev 并删除（可选）本地分支
git checkout dev
git pull origin dev
git branch -d feat/member-crud
```

---

### 查看项目状态的常用命令

```bash
git status              # 查看当前修改了哪些文件
git log --oneline       # 查看提交历史（简洁版）
git diff                # 查看具体修改了什么内容
git branch              # 查看所有分支，* 表示当前分支
```

---

### 提交信息格式

写清楚做了什么即可，建议格式：

```
<类型>: <简要描述>
```

常用类型：

| 类型 | 含义 |
|------|------|
| `feat` | 新增功能 |
| `fix` | 修复 bug |
| `docs` | 文档更新 |
| `test` | 添加或修改测试 |
| `refactor` | 重构（不改变功能） |
| `chore` | 杂项（依赖更新、配置修改等） |

示例：
- `feat: 添加用户登录功能`
- `fix: 修复表单提交时的编码错误`
- `docs: 更新 README 成员信息`

---

### PR 标题与描述

标题沿用提交格式：`<类型>(<范围>): <简要描述>`，例如 `feat(member): 添加会员建档与查询`。

描述建议按下面的结构写（复制即用）：

```markdown
## 概述

这个 PR 做了什么、为什么做（一两句话）。

## 变更内容

- 按文件 / 模块列出改了什么
- 关键设计点、对外接口的变化（如果有的话）

## 自查清单

- [ ] 已运行代码审计（参考 `.agents/skills/code-review/SKILL.md`）
- [ ] 已运行相关测试（或说明为什么没有测试）
- [ ] 文档与实际代码一致（改了行为就同步改文档）
```

**完整的 PR 示例和审阅指南**见 [`docs/pr-workflow-examples.md`](./docs/pr-workflow-examples.md)。

---

### 常见问题与解决方法

<details>
<summary><b>推送时提示 "rejected" 或 "non-fast-forward"</b></summary>

说明远程仓库有新的提交，你的本地代码不是最新的。

**解决方法：**
```bash
# 以当前功能分支 feat/member-crud 为例，先取得远程更新
git fetch origin
git merge origin/feat/member-crud

# 如果有冲突，Git 会提示哪些文件冲突了
# 打开冲突文件，找到 <<<<<<< 和 >>>>>>> 标记
# 手动保留正确的代码，删除冲突标记

# 解决冲突后，重新提交
git add <冲突文件>
git commit -m "fix: 解决合并冲突"
git push origin feat/member-crud
```

合并成功后，重新运行相关检查并推送当前功能分支，PR 会自动更新。若提示远程分支不存在，先用 `git branch -vv` 确认分支与跟踪关系；冲突含义不清楚时，与负责该模块的组员共同核对。
</details>

<details>
<summary><b>不小心在 main 分支上改了代码怎么办？</b></summary>

**还没 commit：**
```bash
# 切换到 dev 分支，Git 会带着你的修改一起过去
git checkout dev
```

**已经提交但还没推送：** 先给当前版本留一条分支，保留提交：
```bash
# 分支名可以换成一个尚未使用的名称
git switch -c rescue/main-work
```

这不会删除提交。把 `git status` 和 `git log -3 --oneline` 的结果发给协作成员，一起核对并把需要的提交移到 `dev`；不要直接复制清空或强制回退命令。

**已经 push 了：**
先与协作成员核对远程分支和提交记录，再共同处理。
</details>

<details>
<summary><b>想撤销刚才的修改</b></summary>

先用 `git diff` 看清具体改动。以下“丢弃修改”会移除未提交内容，只有确定不需要保留时才执行；拿不准就先复制文件备份或找组员一起看。

**还没暂存，想丢弃一个文件的修改：**
```bash
git restore <文件名>       # 恢复该文件，丢弃它未提交的修改
```

**已经暂存，只想撤出本次提交，保留内容：**
```bash
git restore --staged <文件名>  # 取消暂存，文件里的修改仍在
```

**已经提交但还没推送，想重做最后一次提交：**
```bash
git reset --soft HEAD~1     # 撤销最后一次提交记录，修改仍保留在暂存区
```

这条命令只用于自己尚未推送的最后一次提交。若已经推送或不清楚当前状态，先找组员协助。
</details>

---

### 文件管理

- **不要提交**虚拟环境目录（`venv/`、`__pycache__/` 等，已在 `.gitignore` 中配置）。
- **不要提交** IDE 配置（`.idea/`、`.vscode/`）。
- **不要提交** 运行时生成的数据文件与日志（`data/`、`*.log`）。
- **不要提交** 环境变量 / 密钥文件（`.env`，严禁入库）。
- **不要提交** ~~自己的小秘密~~。
- 每个人修改文件前，确认自己在最新的代码基础上工作。

### 注

- 如果你要修改别人负责的模块，应**提前沟通**。
- 遇到合并冲突或不确定的操作，在群里问一声，避免覆盖他人的工作。
- 如果实在想不出或懒得写 commit，可以去看看 https://github.com/AptS-1547/gcop-rs

---

## 技术栈

已确定 **Python 3.10+ + MySQL 8.4**。默认使用文本菜单 CLI，`--tui` 选择可选终端界面，当前会提示尚未就绪；核心功能先在 CLI 完成。CLI 与 TUI 通过相同 Logic 用例使用业务服务。

数据库访问使用 SQLAlchemy 2 + PyMySQL，密码哈希使用 argon2-cffi，Windows 环境安装 `tzdata` 提供时区数据。依赖按运行场景放在 `requirements/`：`core.txt` 是默认 CLI 的最小运行依赖，`web.txt` 在核心依赖上增加 Web API，`all.txt` 汇总全部运行依赖，`dev.txt` 放测试工具。日志使用项目约定的日志模块；TUI 依赖按可选界面单独接入。Git / GitHub 用于团队协作。

Web API 使用 FastAPI、Pydantic 2、Uvicorn 和 PyJWT。浏览器应用位于 `frontend/`，使用 Vue 3、TypeScript、Vite、Vue Router、Pinia、TanStack Query 与 Axios；Vitest 和 Playwright 分别承担单元测试与浏览器测试。安装和启动步骤见[参与指引](./docs/README.md)。

CLI 在可信教学终端连接 MySQL；Web 前端通过服务器提供的 API 访问业务，数据库凭据由后端保管。两种入口共用 Logic 用例。分层与使用方式见[系统架构总览](./docs/architecture.md)及其前后端分册。
