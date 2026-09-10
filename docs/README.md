# docs/

本目录用于存放项目相关文档、设计材料与最终报告素材。

## 文档总览

### 课程资料（docs/ 根目录）

| 文件 | 用途 |
|------|------|
| [`project-introduction.md`](./project-introduction.md) | Practical 1 讲义完整中文翻译（原文 PDF 留档） |
| [`(Week1)-JC2001-Practical1-IntroductionsGroups&Projects.pdf`](./(Week1)-JC2001-Practical1-IntroductionsGroups&Projects.pdf) | Practical 1 原始 PDF |

> 后续课程的讲义 / 要求 PDF 请放入本目录，并按需补充中文翻译，命名与原有文件保持一致。

### 需求与设计文档（docs/ 根目录，随项目推进建立）

| 文件 | 用途 | 对应交付物 |
|------|------|--------------|
| `brainstorm.md` | 选题头脑风暴记录：候选方向、讨论结论 | Project Proposal |
| `requirements.md` | 需求文档：用户故事、功能 / 非功能需求、范围边界（PoC vs future work） | Project Proposal / 技术报告 |
| `architecture.md` | 系统架构：模块划分、技术选型与理由、接口约定 | 技术报告 / PoC |
| `user-research/` | 用户调研材料：访谈记录、问卷、竞品分析 | Project Proposal / 技术报告 |

> 以上文件**尚未创建**，确定选题与规模后按需建立。建立时把本表的链接补上。

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
