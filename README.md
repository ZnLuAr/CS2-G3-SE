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

## 小组协作规范（简版）

详细规范随项目骨架一起确定，先约定几条底线：

- **不要直接在 `main` 分支上开发。** `main` 只接受经过验证的代码，日常开发走 `dev` 分支（或个人功能分支 `feat/<名称>`）。
- **开工前先 `git pull`**，避免基于过时代码修改产生冲突。
- **Commit 信息格式**：`<类型>: <简要描述>`，常用类型如下：

  | 类型 | 含义 |
  |------|------|
  | `feat` | 新增功能 |
  | `fix` | 修复 bug |
  | `docs` | 文档更新 |
  | `test` | 添加或修改测试 |
  | `refactor` | 重构（不改变功能） |
  | `chore` | 杂项（依赖更新、配置修改等） |

- **不应提交**虚拟环境、IDE 配置、运行时数据、密钥等（见 [`.gitignore`](./.gitignore)）。
- 修改别人负责的模块前**提前沟通**；遇到冲突或不确定的操作在群里问，不要 `--force` 强推。
