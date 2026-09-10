# JC2001 Software Engineering Group Project — Group 3

## 软件工程导论 · 小组大作业

---

> 继承 OP 之意志（大雾）

## 项目简介

本仓库用于 **JC2001 Introduction to Software Engineering** 课程的小组大作业：一个软件产品开发项目（software product development project）。

**项目主题：待定。** 我们正在讨论问题空间、目标用户与项目愿景，确定后将更新本节，并在 [`docs/`](./docs/) 下补充需求与设计文档。

### 课程关键时间线（2026）

| 事项 | 截止时间 |
|------|----------|
| 完成分组（MyAberdeen 自助选组） | 2026-09-14 23:59 CST |
| 提交项目提案（Project Proposal） | 2026-09-25 23:59 CST |
| 项目进展更新 / 技术报告 / PoC 软件 / 答辩 | 见 MyAberdeen 课程页 |

> 课程讲义的完整中文翻译见 [`docs/project-introduction.md`](./docs/project-introduction.md)。

## 小组成员（排名不分先后）

| 姓名 | 负责部分 | GitHub ID |
|------|----------|-----------|
| *待填写* | — | — |

## 仓库结构

项目骨架尚未搭建，待确定项目范围与技术栈后再分层。当前结构：

```
.
├── docs/                       # 课程资料与项目文档
│   ├── project-introduction.md # Practical 1 讲义（完整中文翻译）
│   └── (Week1)-JC2001-...pdf   # Practical 1 原始 PDF
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
git clone <仓库地址>
cd <项目目录>

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
