# JC2001 Software Engineering Group Project — Group 3

## 软件工程导论 · 小组大作业

---

> 继承 OP 之意志（大雾）

## 项目简介

本仓库用于 **JC2001 Introduction to Software Engineering** 课程的小组大作业：一个软件产品开发项目（software product development project）。

**项目主题：待定。** 我们正在讨论问题空间、目标用户与项目愿景，确定后将更新本节，并在 [`docs/`](./docs/) 下补充需求与设计文档。

### 📚 文档导航

所有文档都在 [`docs/`](./docs/) 下，完整索引见 [`docs/README.md`](./docs/README.md)。快速指引：

| 你想…… | 去哪里 |
|--------|--------|
| 了解作业要求、截止时间 | [`docs/project-introduction.md`](./docs/project-introduction.md)（Practical 1 讲义中文翻译） |
| 学习怎么用 Git / PR 协作 | 本 README 的[小组协作规范](#小组协作规范) |
| 写代码前看设计文档 | `docs/requirements.md` / `docs/architecture.md`（选题确定后建立） |
| **记录开发过程（给报告攒素材）** | [`docs/dev-materials-for-report/`](./docs/dev-materials-for-report/)，四选一：设计决策 / 开发日志 / 测试笔记 / 会议记录 |

> ⚠️ **报告素材（决策记录、开发日志、测试笔记、会议记录）应该边开发边写**，不应拖到 ddl 才回忆。课程评分看的是**过程**——素材从哪积累、最终报告就有多少话可说。

### 课程关键时间线（2026）

| 事项 | 截止时间 |
|------|----------|
| 完成分组（MyAberdeen 自助选组） | 2026-09-14 23:59 CST |
| 提交项目提案（Project Proposal） | 2026-09-25 23:59 CST |
| 项目进展更新 / 技术报告 / PoC 软件 / 答辩 | 见 MyAberdeen 课程页 |

## 小组成员（排名不分先后）

| 姓名 | 负责部分 | GitHub ID |
|------|----------|-----------|
| MINGJIN LI | - | Matthew-0223 |
| XINGZHOU PENG | - | xing-520 |
| YH Q | - | - |
| TUAO SONG | - | - |
| JIAFENG YE | - | Kelvinvoyage |
| WEIJIE ZHOU | - | Q123422 |
| YUXI ZHU | - | shaun070119 |
| LVZHEN ZHOU | - | ZnLuAr |

## 仓库结构

项目代码骨架尚未搭建，待确定项目范围与技术栈后再分层。当前结构：

```
.
├── docs/                           # 课程资料与项目文档（索引见 docs/README.md）
│   ├── project-introduction.md     # Practical 1 讲义（完整中文翻译）
│   ├── (Week1)-JC2001-...pdf       # Practical 1 原始 PDF
│   └── dev-materials-for-report/   # 报告素材：决策记录 / 开发日志 / 测试笔记 / 会议记录
├── .gitattributes
├── .gitignore
└── README.md
```

## 技术栈

待定。上学期 OOP 小组项目见 [CS2-G10-OOP](https://github.com/ZnLuAr/CS2-G10-OOP)（Python 3 + 标准库 + pytest）。

## 小组协作规范

> 以下规范尽量简洁实用，即使不熟悉 Git 也能快速上手。

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

**建议工作方式：**
- 如果你不太熟悉 Git，直接在 `dev` 分支上工作即可
- 如果你习惯独立开发，可以创建自己的 `feat/xxx` 分支，完成后合入 `dev`

---

### 日常工作流（新手友好版）

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

**已经 commit 但还没 push：**
```bash
# 切换到 dev 分支
git checkout dev

# 把 main 分支的最后一次提交应用到 dev
git cherry-pick main

# 回到 main 分支，撤销那次提交
git checkout main
git reset --hard HEAD~1
```

**已经 push 了：**
找熟悉 Git 的组员帮忙处理。
</details>

<details>
<summary><b>想撤销刚才的修改</b></summary>

**还没 add：**
```bash
git checkout -- <文件名>    # 撤销单个文件的修改
git checkout -- .           # 撤销所有修改
```

**已经 add 但还没 commit：**
```bash
git reset HEAD <文件名>     # 取消暂存
git checkout -- <文件名>    # 撤销修改
```

**已经 commit 但还没 push：**
```bash
git reset --soft HEAD~1     # 撤销 commit，保留修改
git reset --hard HEAD~1     # 撤销 commit，丢弃修改（危险！）
```
</details>

---

### 查看项目状态的常用命令

```bash
git status              # 查看当前修改了哪些文件
git log --oneline       # 查看提交历史（简洁版）
git diff                # 查看具体修改了什么内容
git branch              # 查看所有分支，* 表示当前分支
```

### Commit 信息格式

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

### Pull Request（PR）工作流

日常小改动直接 push 到 `dev` 即可，不必每次都走 PR。但以下情况建议开 PR：

- **较大的功能**，或同时动了多个模块的改动
- 需要大家**确认 / 讨论**的内容（架构调整、接口变更、协作规范修改）
- 自己拿不准、想在合并前让人**帮忙把关**的代码

如果熟悉 GitHub 的操作，还是建议开一下 PR 进行代码的审计。

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

# ④ 组员 Review：看改了什么、有没有问题，在 PR 页面留评论

# ⑤ 确认无误后在 GitHub 上合并，然后删除功能分支
```

#### PR 标题与描述

标题沿用 commit 格式：`<类型>(<范围>): <简要描述>`，例如 `feat(player): 补齐玩家管理 CRUD`。

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

#### Review 看什么

- **能不能跑**：导入路径、命名冲突、明显笔误
- **位置对不对**：改动是否落在约定的模块位置，接口是否与文档一致
- **边界条件**：非法输入、失败路径会不会留下副作用（改了一半才抛异常）
- **测试**：新行为有没有对应的测试覆盖

> Review 不是挑刺，是把"我看到了、我想过了"留给队友。
> 另外，PR 与 review 记录会留档在 GitHub 上——最终报告里它们就是团队协作与质量保证过程的现成证据。

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
