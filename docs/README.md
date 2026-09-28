# docs/

本目录用于存放项目相关文档、设计材料与最终报告素材。

## 从这里开始

**当前状态：SYS 基础层已实现参数解析、配置、资源装配、公共 CLI 输入与统一测试入口。** 业务服务、账号登录、日志与统一错误处理按分工继续接入；其它占位方法调用仍会抛 `NotImplementedError`。

第一次参与不需要一次读完所有设计，按这个顺序即可：

1. 看[项目简介与成员表](../README.md)，了解我们做的是健身房管理，谁在参与。
2. 看 [README 后部的技术栈](../README.md#技术栈)，了解所用工具。默认先完成 CLI，TUI 是时间允许时再做的可选界面。
3. 按 [README 的暂定分工](../README.md#小组成员排名不分先后)，在[功能清单](./feature-list.csv)筛选自己的名字；共同负责的条目先商量谁实现、谁配合，并写到开发备注。P0 是核心，P1 是配套，P2 是后续候选。
4. 从[系统设计的详细目录](./architecture.md#目录)按需跳转：先看系统架构与目录结构，再读开发前必读中的固定数据格式，最后进入自己负责模块的接口、SQL 和业务规则。基础框架与公共 CLI、账号与日志分别说明启动交互和统一错误处理。
5. 看[项目规范](./project-standards.md)和 [Git 操作教程](../README.md#小组协作规范)。拿不准字段、接口或规则时先记录问题，和相关模块的组员对齐。

### 功能表怎么填

CSV 是可以用 Excel、表格软件或文本编辑器打开的表格。用表格软件时选择 UTF-8 编码；如果只显示一列，按逗号分隔导入。保存为 UTF-8 CSV，不要把扩展名改成 xlsx 后覆盖原文件。

- `ID` 是任务的固定编号，例如 `MEM-01`，讨论和提交时都可以引用，不要随意重编号。
- `负责人` 已按 2026-09-20 的暂定分工填写；同一格用中文分号分隔两个人，表示共同负责，不表示各写一份。调整分工时同步 README 与功能清单。
- `状态` 表示进度，不等同于“架构是否批准”或“负责人是否确定”。规则尚未明确的条目为待确认，已确认且尚未实现的条目为待开发；有了签名不表示功能已完成。
- `验收要点` 写怎样看出功能做对了；开发时遇到不明确的规则，写到`开发备注`并讨论。
- 状态通常为“待确认 → 待开发 → 开发中 → 待验收 → 已完成”；遇到依赖未完成等情况标“阻塞”，注明等什么。
- 架构确认不等于每项功能都确认。只有该功能范围、规则和负责人明确后，才改为“待开发”。
- 功能状态以 [`feature-list.csv`](./feature-list.csv) 当前内容为准；状态表示实际实现进度，不因已有接口骨架而提前标记完成。
- 每行尽量对应一个可独立开发和验收的操作。原有 ID 保留，拆出的子功能追加编号，开发备注注明来源；查任务时优先按模块和负责人筛选。
- 办卡由Xingzhou PENG负责、收款由Mingjin LI负责，两人共同对齐一次办卡的事务与字段。签到归Yihao QIAN，未单列的消课和缺席处理先归 Lvzhen ZHOU。整体测试由 Lvzhen ZHOU 统筹，各模块负责人仍补本模块测试。

### 怎样在骨架中完成一个功能

以 `MEM-01 会员建档` 为例。下表中的具体文件已有字段或签名，开工时先核对设计和数据格式，再把自己负责的方法中的 `raise NotImplementedError(...)` 替换成实现。返回类型不要随意改动，未完成的方法继续保留明确占位。

| 步骤 | 要做什么 | 完成这一步时应有什么 |
|------|----------|----------------------|
| 1. 确认要求 | 读 CSV 和设计中的会员字段，确认谁能建档、哪些必填、是否允许重名 | 能用自己的话说清输入和结果；不明确的规则有讨论结论 |
| 2. 对齐数据 | 先看设计“公共类型定义”，再核对 `src/models/contracts.py` 的输入输出类型与会员表 | 姓名、联系方式、空值和返回类型只有一套约定，列表不临时改成字典 |
| 3. 实现数据访问 | 在 `src/db/member_repo.py` 补会员保存或查询 | 能用传入的数据库会话读写，不自行提交业务事务 |
| 4. 实现业务服务 | 在 `src/services/member_service.py` 检查权限和字段，再调用数据访问 | 合法操作提交成功，失败时没有残留会员记录 |
| 5. 接入命令行 | 在 `src/ui/cli/handlers/member.py` 收集输入、调用服务、展示编号，补菜单入口 | 用户能够从菜单完整操作；取消时不创建会员 |
| 6. 验证 | 测正常建档、空姓名、无权限、用户取消、重启后查询 | 测试检查实际结果；失败原因有记录 |
| 7. 交给队友检查 | 同步文档与 CSV，说明改了什么、怎么测的，再按 Git 教程提交 | 队友不用猜就能复现；通过验收后再标“已完成” |

一个功能通常涉及多个文件，但不是每次都要修改所有层。比如只调整列表显示，往往改格式化方法和相关测试即可；不确定时先沿着“用户操作 → 业务服务 → 数据库”看调用过程。

### 如何验证和汇报问题

测试分为：单元测试检查一个规则，集成测试检查多个模块或真实数据库配合，完整流程测试检查用户从头到尾能否完成任务。当前已有静态格式检查，业务测试随实现补充。

前提：已安装 Python 3.10 或以上版本和开发依赖。在仓库根目录（能看到 main.py 的目录）执行：

```bash
python -B -X utf8 -m unittest discover -s tests -p test_contract_consistency.py -v
python -X utf8 -m src.cmd.test
```

第一条命令运行契约测试；第二条命令运行统一测试入口。当前静态检查不会连接数据库，也不代表业务流程已经可运行。若出现 `FAILED`，根据报错的类、方法或表名同时核对设计和源码，不要只删掉断言；若显示 `Ran 0 tests`，检查所在目录和文件名。若找不到 python，先安装 Python 并确认终端可执行该命令。

测试至少说明“准备了什么数据、做了什么、希望结果是什么”。例如：“姓名为空时建档被拒绝，数据库会员数量不变。”不要只写“测试通过”。把未运行的检查如实标出来。

### 安装与测试命令

在仓库根目录创建 Python 3.10 以上的虚拟环境后安装 `requirements-dev.txt`。复制
`config.json.example` 为 `config.json` 填写日常数据库；需要 MySQL 集成测试时，再复制
`config.test.json.example` 为 `config.test.json`，将数据库名保持为 `_test` 结尾，并设置
`TEST_DB_PASSWORD`。日常密码变量 `DB_PASSWORD` 不会被测试命令传入子进程。

```bash
python -m pip install -r requirements-dev.txt
python -m src.cmd.test                 # 运行不连接 MySQL 的测试
python -m src.cmd.test mysql --config config.test.json  # 仅 MySQL 测试
python -m src.cmd.test all --config config.test.json    # 全部测试
```

默认测试成功返回 0；测试失败、未收集到测试或测试环境不可用返回 1。`mysql` 和 `all`
模式缺少配置、测试库名不以 `_test` 结尾或数据库命名锁被占用时，在清理前返回 1。

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
| [`architecture.md`](./architecture.md) | 系统设计：固定数据类型、MySQL 建表 SQL、接口声明与实现示例、事务、CLI、统一异常处理 | 技术报告 / PoC |

设计细节集中在 `architecture.md`。

功能清单中的 P0 是核心功能与必要保障，P1 是配套功能，P2 是后续候选。负责人已按暂定分工填写，状态按实际进度更新为“待开发 / 开发中 / 待验收 / 已完成”，有阻碍时标“阻塞”。完成后在开发备注中留下实现和验证说明；分配了负责人不代表功能已完成。CSV 使用 UTF-8 BOM，便于 Excel 打开中文。

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
