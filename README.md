# JC2001 Software Engineering Group Project — Group 3

## 软件工程导论 · 小组大作业

---

> 继承 OP 之意志（大雾）

## 项目简介

本仓库用于 **JC2001 Introduction to Software Engineering** 课程的小组大作业：一个软件产品开发项目（software product development project）。

**项目主题：健身房管理系统。** 面向会员、教练、前台和管理员。会员卡用于门禁，并按卡类型赠送私教课；围绕“办卡 → 约私教 → 签到 → 消课 → 评价”组织业务，提供器械管理、体测记录和营收报表。当前只做私教课，每节最长 2.5 小时。

月／季／年卡分别有效 30／90／365 天，赠送 20／64／256 节私教；赠课随来源卡到期失效，不能转到新卡。次卡无期限，包含 10 次入场、不赠私教，同一天只扣一次。期限卡续购自动接续，签到只允许在结算前更正。具体规则见[系统设计](./docs/architecture.md)。

**架构与文件骨架已建立，已写入数据字段、类和函数签名，具体实现待补充。** 目前可以按暂定分工在对应方法中实现功能；输入输出格式以设计和共用数据类型为准。

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
| 查看功能细项与暂定分工 | [`docs/功能列表.csv`](./docs/功能列表.csv) |
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

下面展示主要文件，省略各包的 `__init__.py` 和同类业务文件；模块分工见[系统设计](./docs/architecture.md#2-建议目录与模块分工)。

```
.
├── main.py                         # 参数解析与启动函数签名
├── src/                            # 应用代码包
│   ├── app.py                      # 生命周期、服务集合与登录身份
│   ├── config.py                   # 启动参数、配置字段与加载签名
│   ├── logging_config.py           # 日志配置与记录签名
│   ├── errors/                     # 异常定义与统一处理入口
│   ├── models/                     # 数据模型与固定输入输出类型
│   │   └── contracts.py            # 共用 Input、View 与 Page 字段定义
│   ├── services/                   # 业务权限、规则与事务
│   │   ├── member_service.py       # 会员服务签名
│   │   └── booking_service.py      # 预约服务签名；其余按业务分文件
│   ├── db/                         # 数据库连接与数据访问
│   │   ├── connection.py           # 连接、会话工厂与事务签名
│   │   └── member_repo.py          # 会员读写签名；其余按业务分文件
│   └── ui/                         # 交互界面
│       ├── cli/                    # 默认命令行：循环、菜单、输入与展示
│       │   ├── app.py              # 操作边界与主循环签名
│       │   ├── menus.py            # 菜单类型与构造函数签名
│       │   ├── prompts.py          # 输入、确认与取消签名
│       │   ├── formatters.py       # 文本格式化签名
│       │   └── handlers/           # 按业务模块组织交互步骤
│       └── tui/                    # 可选终端界面
│           └── app.py              # TUI 启动与关闭签名
├── tests/                          # 已有文档/源码格式检查，业务测试待补
│   ├── models/
│   ├── services/
│   ├── db/
│   ├── errors/
│   └── ui/
├── sql/                            # 建表与结构变更脚本的存放位置
│   └── 001_initial_schema.sql       # 仅注释占位，未写入可执行 SQL
├── docs/                           # 课程资料与项目文档（索引见 docs/README.md）
│   ├── README.md                   # 阅读顺序与文档索引
│   ├── project-introduction.md     # Practical 1 讲义（完整中文翻译）
│   ├── (Week1)-JC2001-...pdf       # Practical 1 原始 PDF
│   ├── 功能列表.csv               # 功能、优先级、负责人、状态与验收要点
│   ├── project-standards.md       # 代码规范、质量要求与完成标准
│   ├── architecture.md            # 系统设计与框架方案（架构已确认）
│   └── dev-materials-for-report/   # 报告素材：决策记录 / 开发日志 / 测试笔记 / 会议记录
├── .gitattributes
├── .gitignore
├── AGENTS.md                        # 持续适用的协作与说明要求
└── README.md
```

`__init__.py` 标识 Python 包，异常包还统一导出公共类型；`.gitkeep` 用来保留尚无用例的测试目录。共用的数据类型在 [contracts.py](./src/models/contracts.py)，可从 [MemberService](./src/services/member_service.py) 查看方法签名和中文说明的写法。

**当前还不能运行业务流程。** 所有手写函数、构造方法和计算属性都用 `raise NotImplementedError(...)` 占位；调用时表示该方法尚未实现，不代表数据库或环境故障。数据类只定义字段，不执行业务校验。`python main.py`（包括 `--help`、`--tui`）目前也会报未实现；依赖安装和正式运行命令在功能实现并验证后补充。

文档组织与协作方式沿用上学期 [CS2-G10-OOP](https://github.com/ZnLuAr/CS2-G10-OOP) 的经验，具体设计随本项目开发逐步补充。

## 小组协作规范

> 以下说明覆盖分支选择、日常提交、冲突处理与 PR 审阅，按当前操作查阅即可。

先认识几个会用到的词：**分支**是可以单独开发的一条版本线；**暂存（add）**是选出本次要提交的文件；**提交（commit）**是在本地记录一次修改；**推送（push）**是把本地提交传到 GitHub；**拉取（pull）**是把远程更新取回并合并；

推荐使用的是 **合并请求（PR）**，是请队友检查并合入改动。提交与推送是两步，只提交还不会让队友看到。

下面命令在仓库根目录执行，也就是能看到本 README 和 `docs/` 的目录。`<文件名>`、`<功能名>` 是占位符，执行时替换为实际名称，去掉尖括号；只复制命令行，注释用于解释。

### 核心原则

**重要：不要直接在 `main` 分支上改代码。**

`main` 分支是稳定版本，只接受经过验证的代码。日常开发请在 `dev` 分支上进行。

---

### 分支管理

| 分支 | 用途 | 谁可以直接提交 |
|------|------|----------------|
| `main` | 稳定版本，用于里程碑提交 | 仅通过合并 `dev` 更新 |
| `dev` | 日常开发分支 | 所有人 |
| `feat/<功能名>` | 个人功能分支（可选） | 创建者 |
| `fix/<功能名>` | 个人修补 bug 用分支（可选） | 创建者 |

**建议工作方式：**

- 日常小改动可直接在 `dev` 分支上完成。
- 独立功能或需要审阅的改动使用 `feat/xxx` 分支，通过 PR 合入 `dev`。

---

### 日常工作流

下面以 `dev` 分支为例；开始前用 `git status` 确认当前分支和未提交修改。个人功能分支的提交与合入步骤见[PR 工作流](#合并请求pr工作流)。

#### 第一次克隆仓库

```bash
# 1. 克隆仓库到本地
git clone git@github.com:ZnLuAr/CS2-G3-SE.git
cd CS2-G3-SE

# 2. 切换到 dev 分支（日常开发分支）
git checkout dev

# 3. 确认当前分支
git branch
# 应该看到 * dev（星号表示当前分支）
```

#### 每次开始工作前

```bash
# 拉取最新代码（避免基于过时的代码修改）
git pull origin dev
```

**为什么要先 pull？**
- 其他组员可能已经推送了新代码
- 如果你基于旧代码修改，推送时会产生冲突
- 先 pull 可以提前发现冲突，更容易解决

#### 完成修改后提交

```bash
# 1. 查看你修改了哪些文件
git status

# 2. 添加修改的文件到暂存区
git add <文件名>              # 添加单个文件
git add .                     # 添加所有修改（小心，确认没有不该提交的文件）

# 3. 提交修改（附上说明信息）
git commit -m "feat: 添加了 XXX 功能"

# 4. 推送到远程仓库
git push origin dev
```

**常见问题：**

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

### 查看项目状态的常用命令

```bash
git status              # 查看当前修改了哪些文件
git log --oneline       # 查看提交历史（简洁版）
git diff                # 查看具体修改了什么内容
git branch              # 查看所有分支，* 表示当前分支
```

### 提交信息格式（commit）

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

### 合并请求（PR）工作流

日常小改动可直接 push 到 `dev`。跨模块、数据库结构和重要业务规则变更通过 PR 复核，与[项目规范](./docs/project-standards.md#协作与完成标准)一致；以下情况也建议开 PR：

- **较大的功能**，或同时动了多个模块的改动
- 需要大家**确认 / 讨论**的内容（架构调整、接口变更、协作规范修改）
- 自己拿不准、想在合并前让人**帮忙把关**的代码

PR 用于提交前后的代码审阅，也为接口变更和讨论结果保留记录。

#### PR 的完整流程

```bash
# ① 基于 dev 创建功能分支
git checkout dev
git pull origin dev
git checkout -b feat/xxx

# ② 在分支上完成开发，commit 并推送
git push origin feat/xxx

# ③ 创建 Pull Request（feat/xxx → dev）
#    push 后 GitHub 仓库页面会出现 "Compare & pull request" 按钮，点它即可
#    命令行党也可以用 GitHub CLI：gh pr create --base dev

# ④ 组员审阅：看改了什么、有没有问题，在 PR 页面留评论

# ⑤ 确认无误后在 GitHub 上合并，然后删除功能分支
```

#### PR 标题与描述

标题沿用提交格式：`<类型>(<范围>): <简要描述>`，例如 `feat(member): 添加会员建档与查询`。

描述建议按下面的结构写（复制即用）：

```markdown
## 概述

这个 PR 做了什么、为什么做（一两句话）。

## 变更内容

- 按文件 / 模块列出改了什么
- 关键设计点、对外接口的变化（如果有的话）

## 自查清单

- [ ] 已运行相关测试（或说明为什么没有测试）
- [ ] 文档与实际代码一致（改了行为就同步改文档）
```

#### 真实示例（上学期 OOP 仓库）

以下都是 [CS2-G10-OOP](https://github.com/ZnLuAr/CS2-G10-OOP) 里真实发生过的 PR，可以直接点进去围观：

| PR | 看点 |
|----|------|
| [#2 · PR 流程示例](https://github.com/ZnLuAr/CS2-G10-OOP/pull/2) | 当年为教学专门开的 PR，演示完整流程与描述写法 |
| [#16 · feat(player)](https://github.com/ZnLuAr/CS2-G10-OOP/pull/16) | 规范的功能 PR：概述 → 背景 → 变更文件 → 功能实现，逐层展开 |
| [#13 · feat(inventory)](https://github.com/ZnLuAr/CS2-G10-OOP/pull/13) | PR + Code Review 完整案例：review 指出模块落位、接口对齐、边界条件等问题，作者迭代后才真正落地 |

#### 审阅时看什么

- **能不能跑**：导入路径、命名冲突、明显笔误
- **位置对不对**：改动是否落在约定的模块位置，接口是否与文档一致
- **边界条件**：非法输入、失败路径会不会留下副作用（改了一半才抛异常）
- **测试**：新行为有没有对应的测试覆盖

> 审阅时指出具体问题、原因和建议，帮助队友一起完善实现。
> PR 与审阅记录会留档在 GitHub 上，最终报告里可以用它们说明团队协作与质量保证过程。

### 文件管理

- **不要提交**虚拟环境目录（`venv/`、`__pycache__/` 等，已在 `.gitignore` 中配置）。
- **不要提交** IDE 配置（`.idea/`、`.vscode/`）。
- **不要提交** 运行时生成的数据文件与日志（`data/`、`*.log`）。
- **不要提交** 环境变量 / 密钥文件（`.env`，严禁入库）。
- **不要提交** ~~自己的小秘密~~。
- 每个人修改文件前，确认自己在最新的代码基础上工作。

### 注

- 如果你要修改别人负责的模块，请**提前沟通**。
- 遇到合并冲突或不确定的操作，在群里问一声，避免覆盖他人的工作。
- 如果实在想不出或懒得写 commit，可以去看看 https://github.com/AptS-1547/gcop-rs

## 技术栈

已确定 **Python 3 + MySQL**。设计语法要求 Python 3.10+、MySQL 8.0.16+（支持 CHECK 约束），具体部署版本在搭建时验证并锁定。默认使用文本菜单 CLI，`--tui` 启用可选终端界面；核心功能先在 CLI 完成。CLI 和 TUI 共用业务服务，TUI 未完成或未安装其依赖不影响 CLI。

建议使用 SQLAlchemy + PyMySQL 组织数据库读写，pytest 运行测试，venv + pip + requirements.txt 管理独立环境与依赖版本，标准库 logging 记录日志；TUI 候选库为 Textual。这些库与精确版本在搭建时验证后确定，再补实测安装命令。Git / GitHub 用于团队协作。

第一版面向可信教学终端，直接连接 MySQL；以后若面向不可信的会员设备，再增加由服务器保管数据库凭据的接口。分层与使用方式见[系统设计](./docs/architecture.md)。
