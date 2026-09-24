# JC2001 Software Engineering Group Project — Group 3

## 软件工程导论 · 小组大作业

---

> 继承 OP 之意志（大雾）

## 项目简介

本仓库用于 **JC2001 Introduction to Software Engineering** 课程的小组大作业：一个软件产品开发项目（software product development project）。

**项目主题：健身房管理系统。** 面向会员、教练、前台和管理员。提供私教课产品（附赠门禁权限）和入场次卡；围绕”购买产品 → 约私教 → 签到 → 消课 → 评价”组织业务，提供器械管理、体测记录和营收报表。

### 📚 文档导航

课程资料、系统设计与过程记录集中在 [`docs/`](./docs/)，完整索引见 [`docs/README.md`](./docs/README.md)。Git 协作说明与简要技术栈保留在本 README。

快速指引，可以按顺序阅览：

| 你想…… | 去哪里 |
|--------|--------|
| 查看阅读顺序与参与步骤 | [`docs/README.md` 的参与指引](./docs/README.md#从这里开始)（阅读顺序、任务分工、开发与验收示例） |
| 了解作业要求、截止时间 | [`docs/project-introduction.md`](./docs/project-introduction.md)（Practical 1 讲义中文翻译） |
| 查看负责模块的设计及与其他模块的衔接 | [系统设计详细目录](./docs/architecture.md#目录)（数据格式、SQL、服务接口、CLI 与异常处理） |
| 查看代码规范和质量要求 | [`docs/project-standards.md`](./docs/project-standards.md) |
| **记录开发过程（给报告攒素材）** | [`docs/dev-materials-for-report/`](./docs/dev-materials-for-report/)，四选一：设计决策 / 开发日志 / 测试笔记 / 会议记录 |
| 学习怎么用 Git / PR 协作 | 本 README 的[小组协作规范](#小组协作规范) |
| 查看功能细项与暂定分工 | [`docs/feature-list.csv`](./docs/feature-list.csv) |
| 了解技术栈 | 本 README 后部的[技术栈](#技术栈)（Python、MySQL，默认 CLI、可选 TUI） |

> ⚠️ **报告素材（决策记录、开发日志、测试笔记、会议记录）应该边开发边写**，不应拖到 ddl 才回忆。课程评分看的是**过程**——素材从哪积累、最终报告就有多少话可说。

---

### 课程关键时间线（2026）

| 事项 | 截止时间 |
|------|----------|
| 完成分组（MyAberdeen 自助选组） | 2026-09-14 23:59 CST |
| 提交项目提案（Project Proposal） | 2026-09-25 23:59 CST |
| 项目进展更新 / 技术报告 / PoC 软件 / 答辩 | 见 MyAberdeen 课程页 |

## 小组成员（排名不分先后）

暂定分工（2026-09-20）：

| 姓名 | 暂定负责部分 | GitHub ID |
|------|----------|-----------|
| MINGJIN LI | 体测、收款、报表 | Matthew-0223 |
| XINGZHOU PENG | 会员、会员卡 | xing-520 |
| YIHAO QIAN | 签到、评价 | - |
| TUAO SONG | 器械、体测 | - |
| JIAFENG YE | 账号与权限、异常与日志 | Kelvinvoyage |
| WEIJIE ZHOU | 教练、课程、预约 | Q123422 |
| YUXI ZHU | 课程、预约 | shaun070119 |
| Guanyu ZHOU | 文档报告编写 | - |
| Lvzhen ZHOU | 其余部分 | ZnLuAr |

## 仓库结构

下面展示主要文件，省略各包的 `__init__.py` 和同类业务文件；模块分工见[系统设计](./docs/architecture.md#系统架构与目录结构)。

```
.
├── main.py                         # 程序入口，解析参数并启动
├── src/                            # 应用代码包
│   ├── app.py                      # 应用协调层：服务管理、登录状态
│   ├── config.py                   # 配置读取：数据库连接、日志、时区
│   ├── cmd/                        # 数据库、测试和本机日志命令
│   │   ├── db.py                   # init：建表；migrate：迁移；seed：演示数据
│   │   ├── logs.py                 # 按本机配置浏览日志快照
│   │   └── test.py                 # unit/mysql/all：统一测试入口
│   ├── utils/                      # 工具模块（基础设施）
│   │   └── logging_config.py       # 日志系统：配置、记录、脱敏、查询
│   ├── errors/                     # 异常定义与统一处理
│   ├── models/                     # 数据模型与类型定义
│   │   └── contracts.py            # 公共类型：Input、View、Page
│   ├── services/                   # 业务服务层（权限、规则、事务）
│   │   ├── auth_service.py         # 账号与权限
│   │   ├── member_service.py       # 会员档案
│   │   ├── product_service.py      # 产品销售与门禁
│   │   └── ...                     # 其他业务服务
│   ├── db/                         # 数据访问层
│   │   ├── connection.py           # 连接池管理
│   │   ├── *_repo.py               # 各模块数据访问对象（DAO）
│   │   └── ...
│   └── ui/                         # 用户界面层
│       ├── cli/                    # 命令行界面（默认）
│       │   ├── app.py              # CLI 主循环
│       │   ├── menus.py            # 菜单定义
│       │   ├── prompts.py          # 输入收集
│       │   ├── formatters.py       # 结果展示
│       │   └── handlers/           # 业务交互处理器
│       └── tui/                    # 终端界面（可选）
│           └── app.py              # TUI 启动与关闭
├── tests/                          # pytest 测试与 MySQL fixture
│
├── sql/                            # SQL 脚本（如果不用 ORM 迁移工具）
│   ├── 001_initial_schema.sql      # 版本 1 的 18 张表建表脚本
│   └── 002_query_indexes_and_equipment_location.sql # 版本 2 迁移脚本
├── docs/                           # 文档目录
│   ├── README.md                   # 文档索引
│   ├── architecture.md             # 系统设计与架构方案
│   ├── project-standards.md        # 代码与文档规范
│   ├── feature-list.csv            # 功能清单与实现状态
│   └── dev-materials-for-report/   # 报告素材（开发日志、决策记录等）
├── .gitignore
├── AGENTS.md                       # Agent 协作规范
└── README.md                       # 本文件
```

`__init__.py` 标识 Python 包，异常包还统一导出公共类型；`.gitkeep` 用来保留尚无用例的测试目录。共用的数据类型在 [contracts.py](./src/models/contracts.py)，可从 [MemberService](./src/services/member_service.py) 查看方法签名和中文说明的写法。

**当前状态**：SYS 基础层已经提供参数解析、配置读取、资源装配、公共 CLI 输入/分页和统一测试入口；业务服务、账号登录、日志与统一错误处理仍按分工逐步接入。未实现的方法继续用 `NotImplementedError` 明确标记。`--help` 和 `python -m src.cmd.test` 不需要 MySQL；正式业务启动需要配置文件、MySQL 结构和已接入的登录服务。

常用命令（均在仓库根目录执行）：

```bash
python main.py --help
python -m src.cmd.db init --config config.json
python -m src.cmd.db migrate --config config.json
python -m src.cmd.db seed --config config.json
python -m src.cmd.test
python -m src.cmd.test mysql --config config.test.json
```

文档组织与协作方式沿用上学期 [CS2-G10-OOP](https://github.com/ZnLuAr/CS2-G10-OOP) 的经验，具体设计随本项目开发逐步补充。

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
# - 文档同步：architecture.md 是否需要更新

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
# 先拉取远程代码
git pull origin dev

# 如果有冲突，Git 会提示哪些文件冲突了
# 打开冲突文件，找到 <<<<<<< 和 >>>>>>> 标记
# 手动保留正确的代码，删除冲突标记

# 解决冲突后，重新提交
git add <冲突文件>
git commit -m "fix: 解决合并冲突"
git push origin dev
```

**不确定怎么解决？先找组员帮忙，不要用 `--force` 强制推送！**
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

已确定 **Python 3.10+ + MySQL 8.4**。默认使用文本菜单 CLI，`--tui` 启用可选终端界面；核心功能先在 CLI 完成。CLI 和 TUI 共用业务服务，TUI 未完成或未安装其依赖不影响 CLI。

数据库访问使用 SQLAlchemy 2 + PyMySQL，密码哈希使用 argon2-cffi，测试使用 pytest；依赖分别列在 `requirements.txt` 和 `requirements-dev.txt`，Windows 环境安装 `tzdata` 提供时区数据。日志使用项目约定的日志模块；TUI 依赖按可选界面单独接入。Git / GitHub 用于团队协作。

第一版面向可信教学终端，直接连接 MySQL；以后若面向不可信的会员设备，再增加由服务器保管数据库凭据的接口。分层与使用方式见[系统设计](./docs/architecture.md)。
