# 测试与调试笔记

> 记录测试策略、发现的问题、定位过程、修复方式。
> 技术报告需要体现测试如何影响设计，PoC 提交也依赖测试质量——本文档是素材库。

---

## 测试思路与策略

### [2026-10-23] PR #9 修复与功能清单排序验证

- **环境与基线**：Windows，使用仓库 `.venv/Scripts/python.exe`。PR #9 的独立临时副本回归为 273 项通过、7 项 MySQL 用例排除、1 条 TestClient 依赖弃用提示；该结果与原测试记录一致。
- **针对性回归**：在仓库根目录执行 `.venv/Scripts/python.exe -B -X utf8 -m pytest tests/unit/db tests/unit/test_report_cli.py tests/unit/test_actor_verification.py tests/unit/test_measurement.py tests/contracts -q -p no:cacheprovider --tb=short --basetemp tmp/pr9-focused-tests`，182 项通过。
- **完整回归**：在仓库根目录执行 `.venv/Scripts/python.exe -B -X utf8 -m pytest tests -m 'not mysql' -q -rs --tb=short --basetemp tmp/pr9-regression-tests -p no:cacheprovider`，279 项通过、7 项 MySQL 用例排除，1 条 FastAPI/Starlette TestClient 的依赖弃用提示。
- **新增 6 项**：纽约夏令时回拨覆盖 UTC 正序及倒序，真实 SQL 同时验证半开结束边界；跨批次导出模拟时钟跨过课次结束时刻，验证两条课次仍使用同一统计时刻；身份复核分别在账号表、会员关联表与教练关联表查询失败时返回安全 `StorageError`，并把事务交给调用方处理。
- **调用方与清单**：合同测试核对权益导出及仓储统计签名；CLI 测试确认权益导出直接传入身份。CSV 与合并版本逐行内容核对：223 条记录、223 个唯一 ID、53 个模块，完整记录多重集合一致，同一模块连续且按 ID 自然顺序排列，UTF-8 BOM 和 LF 换行保留。
- **后续验证前提**：当前缺少专用 `config.test.json`，真实 MySQL 的事务、锁与快照仍待专用入口验证；登录和统一错误处理接入后继续运行 CLI 完整流程。

### [2026-10-21] 体测、收款和报表迁移回归

- **环境与命令**：Windows、Python 3.13.14，在仓库根目录安装 `requirements/all.txt` 与 `requirements/dev.txt` 后，执行 `.venv/Scripts/python.exe -B -X utf8 -m src.cmd.test unit`：273 项通过、7 项 MySQL 用例按模式排除。FastAPI/Starlette TestClient 的 HTTPX 弃用提示为 1 条依赖警告。
- **新增覆盖**：体测 57 项、当前身份复核 43 项、CLI 36 项、收款与报表 SQL 17 项、报表服务与会话 27 项，共新增 180 项。SQLite 用真实表和查询验证授课截止、再次预约、互斥权益分类、教练课次去重、筛选分页及当前账号关联变化。CLI 测试覆盖取消、确认、翻页、权限菜单和导出文件失败。
- **导出与事务**：验证实际 SQL 跨 500 行批次保持筛选，10,000 行成功与 10,001 行拒绝，空数据只含表头，中文与 UTF-8 BOM、文本公式前缀及负数金额、编码失败、读取错误转换和 Session 关闭释放。
- **发现与修复**：修正导出读取失败的异常类型、当前权益导出的历史时刻输入、超大分页导致驱动溢出，以及时间转换超出 UTC/MySQL 范围。体测还验证回滚与提交结果未知携带原记录编号；日志写入失败保留已提交的体测结果并给出安全提示。
- **MySQL 验证准备**：`tests/integration/test_measurements.py` 增加 2 项，`test_reports.py` 增加 4 项，覆盖体测授权和行锁、付款与订单回滚、每订单唯一付款及跨批次一致性快照。单独收集这两份文件得到 6 项显式跳过，提示使用专用测试入口。当前缺少 `config.test.json` 和专用 `_test` 数据库，真实 MySQL 尚未运行。
- **后续执行前提**：准备按 `config.test.json.example` 创建的专用测试配置与 `TEST_DB_PASSWORD`，在仓库根目录运行 `.venv/Scripts/python.exe -B -X utf8 -m src.cmd.test mysql --config config.test.json`；预期专用用例实际执行并回收测试表，配置或连接失败时先检查测试库后缀、标记与凭据。真实登录、销售与日志依赖接入后再记录完整 CLI 主流程结果。

### [2026-10-20] 架构、骨架与全文档最终审计

- **范围与方法**：按 `code-review` 分模块检查后端领域与基础设施、浏览器代码，按 `doc-audit` 双向比较总览、前后端分册、公开签名、数据字段和实际文件，再按 `doc-writing` 修正参与指引。新增功能均有入口与合同，业务占位和真实执行结果分别记录。
- **发现与修复**：补三个新仓储、内部预约与通知协作、统一候补结束时刻、消课持久化及四个销售来源复合外键；修正旧卡字段、停用限制、归档与关联说明。健身房卡详情与列表改用根记录和类型子表聚合，连接层缺表检查加入回归覆盖。补会员资料订单、签到和结束课次入口；修复退出迟到覆盖新会话、大整数编号丢精度、默认 HTTP 404/405 错误格式与空版本表错误转换。
- **后端验证**：仓库根目录执行 `.venv/Scripts/python.exe -B -X utf8 -m src.cmd.test unit`，93 项通过、1 项 MySQL 用例排除，其中 API 22 项、合同 10 项。另执行 `python -B -X utf8 -m unittest discover -s tests/contracts -p test_backend_contracts.py -v`，9 项通过。测试覆盖来源外键、35 表初始化声明、HTTP 大编号/非法编号/统一错误、Worker 默认启停及超时重试、快照交换期间刷新请求保留、聚合数据类字段和连接层缺表处理。
- **前端验证**：`frontend/` 下 `npm test` 56 项通过、`npm run build` 通过。启动 `npm run dev` 后，在另一终端设置 `PLAYWRIGHT_CHANNEL=msedge` 并执行 `npm run test:e2e -- --workers=1`，5 项通过且进程以 0 退出；认证响应使用模拟数据。浏览器端尚未覆盖身份恢复重试成功后的导航，业务认证仍未与真实后端联调。
- **静态验证**：Python `compileall` 通过。24 份 Markdown、173 处本地文件及标题链接通过，包含总览按负责人定位与后端会员建档查阅路径；CSV 223 项、12 列、ID 唯一、引用有效、依赖无环。清除 `AGENTS.md` 行尾空格后 `git diff --check` 通过。本地设计草稿不纳入提交。
- **环境提示与限制**：FastAPI TestClient 提示 HTTPX 兼容方式弃用，pytest 缓存目录权限警告均未影响断言结果。真实 MySQL DDL、CHECK/外键执行、事务回滚、锁与并发、真实登录和领域端到端流程尚未验证；生产反向代理配置明确为待部署验证示例。

### [2026-10-20] 测试迁移与认证回归

- **后端分类回归**：使用 `.venv/Scripts/python.exe -B -X utf8 -m src.cmd.test unit`，契约、单元和 API 共 72 项通过，1 项 MySQL 专用用例按默认模式排除。使用 `python -B -X utf8 -m unittest discover -s tests/contracts -p test_backend_contracts.py -v`，9 项契约测试通过。
- **JWT 回归发现**：补齐 FastAPI、PyJWT、HTTPX 后，原认证测试中正常会员令牌的 `/me` 返回 401。PyJWT `require` 对 `member_id` 或 `coach_id` 的 null 值视作缺失；代码合同要求声明存在但允许合法空档案值。
- **修复与覆盖**：JWT 必填集合只包含非空声明，应用层检查两个档案声明都存在，再按角色校验正整数或 null。API 测试现覆盖会员、教练、前台、管理员令牌往返及档案声明缺失，`tests/api` 共 10 项通过。
- **其他检查**：Python `compileall` 通过；`git diff --check` 仅报告既有 `AGENTS.md:23` 行尾空格。真实 MySQL 未连接。
- **验证边界**：API 使用 Logic 替身验证 HTTP/JWT 行为；认证 Logic 仍是占位。浏览器测试不代替真实业务 API 联调；MySQL 初始化、事务及并发用例尚未执行。

### [2026-10-20] 浏览器骨架构建与路由回归

- **安装**：在 `frontend/` 执行 `npm ci --cache ../tmp/npm-cache`，安装完成后 npm 报告 0 项漏洞；Node 支持范围与 jsdom、Vitest 要求统一。
- **构建与单元测试**：执行 `npm run build`，TypeScript 检查及 Vite 生产构建通过；执行 `npm test -- --reporter=dot`，5 个测试文件、33 项通过。
- **浏览器测试**：在一个终端执行 `npm run dev`，另一个终端设置 `PLAYWRIGHT_CHANNEL=msedge` 并执行 `npm run test:e2e -- --workers=1`；5 项 Edge 浏览器测试通过，测试进程正常退出并复用 Vite 服务。
- **发现与修复**：空 API 基址回退到同源 `/api`；令牌恢复请求遇到 `action=exit` 时，路由守卫优先保留服务不可用页面；退出错误也清除凭据并保留安全提示。新增对应单元和浏览器用例。
- **验证边界**：浏览器认证路由使用模拟响应，认证 Logic 和业务页仍为占位；真实后端登录、业务 API、MySQL 与并发验收未运行。

### [2026-10-20] requirements 分组迁移检查

- **检查范围**：`requirements/core.txt`、`web.txt`、`dev.txt`、`all.txt` 的组间引用，以及文档和测试入口中的安装路径。
- **依赖结构检查**：`all.txt` 组合 `core.txt` 与 `web.txt`；各被引用文件均存在；`web.txt` 只声明 Web 运行依赖，需和 `core.txt` 一起安装；`dev.txt` 只声明测试工具。
- **路径检查**：仓库内未发现旧根目录依赖文件路径的实际引用。
- **回归结果**：默认单元测试 62 项通过、1 项跳过、1 项排除；`compileall` 通过；`git diff --check` 除既有 `AGENTS.md` 行尾空格外无新增问题。

### [2026-10-19] Web API 与周期 Worker 骨架回归

- **检查范围**：新增 Web 登录/身份/退出路由、JWT 解析、App ASGI 生命周期、周期调度、配置解析和既有 CLI/Logic 骨架。
- **默认单元测试**：仓库根目录执行 `python -B -X utf8 -m src.cmd.test unit`，62 项通过、1 项跳过、1 项 MySQL 专用用例按模式排除。直接运行 `pytest` 会触发 MySQL fixture 的显式模式检查，不作为默认测试入口。
- **语法检查**：`python -B -X utf8 -m compileall -q main.py src tests` 通过。
- **API 测试状态**：`tests/test_web_api.py` 因环境缺少 FastAPI 与 PyJWT 而跳过；HTTPX 已安装。API 路由、令牌签发和 ASGI 生命周期尚未在当前环境执行。
- **验证限制**：未连接 MySQL，未验证真实 ASGI 服务、数据库启动关闭、并发或领域流程。

### [2026-10-19] 后端文档审计修正回归

- **检查范围**：Logic 注解名称、候补历史约束、候补系统 Service 签名、App/Worker 生命周期状态和源码文档引用。
- **审计与修复**：审计确认 119 个用户 Logic 签名、现有 Service 合同和 v4 版本声明一致；发现五个 Logic 模块缺类型导入、候补历史唯一约束固定了未确认规则、递补操作缺 Service 合同，以及生命周期描述超前于代码。已补齐导入和系统方法占位、移除唯一约束，并把 API/Worker 标为目标合同。
- **契约测试**：`python -B -X utf8 -m unittest discover -s tests -p test_contract_consistency.py -v`，9 项通过。新增检查确保 Logic 注解引用可解析，且 DDL 与后端分册都不以 `(member_id, session_id)` 唯一索引决定候补历史规则。
- **单元和语法检查**：`python -B -X utf8 -m src.cmd.test unit`，55 项通过，1 项 MySQL 专用用例排除；`python -B -m compileall -q main.py src tests` 通过。
- **验证限制**：未连接 MySQL，未验证 v4 DDL 执行、事务和并发；Web API、Worker、TUI 及真实业务流程仍未实现。

### [2026-10-19] v4 与 Logic 骨架同步回归

- **检查范围**：后端合同中的公共类型、Service/Repository 签名、Logic 映射、SQL 字段与版本；CLI 资源释放和基础交互格式化。
- **契约测试**：仓库根目录执行 `python -B -X utf8 -m unittest discover -s tests -p test_contract_consistency.py -v`，7 项全部通过。检查覆盖 16 个 Service 的 Session 参数、Logic 入口映射、v4 SQL 和公共类型。
- **单元测试**：执行 `python -B -X utf8 -m src.cmd.test unit`，53 项通过，1 项需显式 MySQL 模式的用例按测试入口规则排除。
- **静态检查**：`python -B -m compileall -q main.py src tests` 通过；格式化器所读 View 字段与 `contracts.py` 声明核对无缺失。
- **验证限制**：未连接真实 MySQL。DDL、外键、CHECK、事务隔离、锁竞争和业务流程需在独立 MySQL 测试库验证。直接运行完整 `pytest tests` 会触发 MySQL fixture 的显式模式保护；应使用 `python -m src.cmd.test unit` 或带配置的 `mysql/all` 模式。

### [2026-10-19] 架构分册迁入后的合同基线

- **检查范围**：后端分册接口与 SQL、前端功能 ID 和权限入口、CSV 编号及依赖、项目 Markdown 本地链接、契约测试文档路径。
- **清单结果**：`feature-list.csv` 共 223 行数据、12 列、223 个唯一 ID；类别分别为后端业务 96、前端 98、工程 17、测试 9、扩展 3。独立审计核对原有 100 个 ID 的负责人和状态均保留或可追溯，依赖无环。
- **文档结果**：后端 16 段 SQL 代码块迁入后保持原文；前端引用的功能 ID 均存在。17 份项目 Markdown 的本地文件和标题链接检查通过。
- **契约测试**：仓库根目录执行 `python -B -X utf8 -m unittest discover -s tests -p test_contract_consistency.py -v`，7 项运行、4 个测试方法通过、3 个测试方法中共 19 个断言失败。差异涉及新增 Logic 与领域数据类、`join_waitlist` 和 `waitlist_entry` 操作值、Service 的 Session 参数以及 v4 SQL 尚未进入源码。预约重复检查顺序、身份锁合同、结构版本消费者和当前导航测试通过；未删减这些断言。
- **其他检查**：`python -B -X utf8 -m compileall -q main.py src tests` 通过。当前 SQL 仍为结构版本 3；未连接 MySQL，未执行 v4 建表、事务、并发或业务流程验证。

### [2026-09-28] 契约测试从 10 个断言失败修复到 7/7 全通过

- **起点**：09-25 记录的基线——文档已是 v3、代码仍是 v2，`test_contract_consistency.py` 出现 10 个断言失败。本轮目标是让代码追上文档，把 7 个测试方法全部修绿。
- **定位方法**：写一次性只读诊断脚本，复用测试自身的 `parse_file`/`fields`/`sql_columns` 等辅助函数与 `setUpClass`，把三类差异（dataclass 字段、service/repo 签名、SQL 列）一次性列成清单，避免逐个跑测试试错。诊断脚本用完即删，不留在仓库。
- **逐测试修复**：
  - `test_current_schema_version`：代码 `CURRENT_SCHEMA_VERSION` 升到 3；测试原本硬编码 `2` 且只认 `ast.Assign`，改为同时支持带类型注解的 `ast.AnnAssign` 并接受 `int = 3` 字面量。
  - `test_booking_checks_duplicate_before_capacity` / `test_identity_revalidation`：v3 文档结构变了（无独立"预约规则"章节、身份锁契约写进各方法），更新测试正则匹配新结构。**注意**：中途发现自己一度误删了 4 句仍然有效的锁契约代码断言，核对到这 4 句原话在 `auth_service.py`/`account_repo.py` 里仍存在后恢复，避免放水。
  - `test_public_fields`：删除源码里文档未定义的类。
  - `test_service_repository`：拆分/新建 service 类、删 `ProductService`、逐个对齐方法签名和 repository。
  - `test_storage_fields`：删 v2 遗留表、对齐 12 张表列、修 18 个模型字段、补 11 个缺失模型。
- **命令与结果**：`python -m pytest tests/test_contract_consistency.py -v` → **7 passed**，逐条确认无放水。全量 `python -m pytest tests/` → 31 passed、19 failed、1 error。
- **验证边界**：契约测试只证明"文档=代码声明"一致，不代表 v3 SQL 在 MySQL 建表成功、并发锁正确或业务行为通过——所有业务方法仍是 `NotImplementedError`。失败的 19 项主要是 `test_sys_base.py` 按 v2 结构写的数据库迁移用例（v2→v3 大改后待同步）和 CLI 子进程用例，未连接真实 MySQL。

### [2026-09-25] v3 架构两轮静态审计

- **检查范围**：从业务场景反推会员归档、健身房卡与课包销售、赠卡、预约、取消、签到、消课、门禁、体测、评价和报表合同；从实现角度检查公共类型、SQL 复合外键、MySQL CHECK、索引、幂等负载、锁顺序和 v2→v3 历史映射。
- **第一轮发现与修正**：统一 `AccessService` 和登记权限；把入场来源改为可由数据库验证的判别字段与 XOR CHECK；补齐订单查询、赠卡规则版本、产品销售/赠送状态、课程快照、异常集合、账号关联、全局锁序和停机迁移协议。
- **第二轮发现与修正**：增加期限卡与次卡判别子类型，无损保留旧次卡总次数和剩余次数；补齐教练、课程模板和场地的公开合同与目标 SQL；限定普通签到为 `starts_at <= now < ends_at`；补充评价范围、收入分类、导出接口和体测授权索引。
- **静态结果**：最终独立复审未发现阻塞或高风险设计问题；`git diff --check` 通过，Markdown 代码围栏成对，旧混合权益接口术语扫描未发现需要处理的正式合同引用。
- **验证范围**：本轮没有执行 v3 MySQL 建表、迁移、服务行为或并发测试。后续实现需要在独立 MySQL 测试库验证三类门禁来源 XOR、最后一次次卡并发扣减、最后一节课并发预约、销售赠卡原子回滚、精确课次时长 CHECK 和迁移重跑。
- **现有契约测试结果**：在仓库根目录执行 `python -B -X utf8 -m unittest discover -s tests -p test_contract_consistency.py -v`，7 个测试方法中出现 10 个断言失败。失败集中在当前代码和测试仍要求结构版本 2、`CardKind/CardStatus`、旧 `OperationName`、`AccountLinkInput`、`ProductService` 及旧章节文本；存储字段与现有 SQL 的 v2 一致性检查仍通过。该结果作为 v3 实现同步的基线，不能表示 v3 SQL、服务或并发行为已经验证。

### [2026-09-24] 身份锁与数据库版本 2 迁移回归

- **检查范围**：核对 `verify_actor`、账号停用和档案移交的账号锁顺序、完整档案锁定行与事务持锁范围；核对版本 1 建表、版本 2 八个结构步骤、新库初始化、已有库迁移、应用启动、seed 与 fixture 的版本要求。
- **迁移用例**：替代连接覆盖新库从版本 1 连续升级到版本 2、部分索引已存在时跳过并完成剩余步骤、DDL 中途失败时保留已确认步骤，以及修复失败条件后再次执行。契约测试同时双向检查公开 Service 方法和架构签名。
- **命令与结果**：仓库根目录执行 `python -B -X utf8 -m unittest discover -s tests -p test_contract_consistency.py -v`，7 项通过；执行 `python -X utf8 -m src.cmd.test unit`，50 项通过、1 项 MySQL 用例排除；执行 `python -m compileall -q main.py src tests` 与 `git diff --check`，均通过。pytest 因工作区 `.pytest_cache` 无写权限产生 2 条缓存警告，不影响用例结果。
- **验证范围**：当前未连接真实 MySQL；DDL 隐式提交、CHECK 对已有数据的校验、索引执行计划和两个连接下的锁等待顺序仍需在独立测试库验证。账号相关业务方法仍是明确占位，契约测试只验证其签名和锁规则说明。

### [2026-09-24] 跨模块契约审计回归

- **检查范围**：按账号、会员/产品、课程/预约、签到/评价、体测/器械、报表、日志/基础框架分组，双向核对公开类型、服务与仓储签名、权限范围、状态流转、事务、锁顺序、幂等记录及统计口径。
- **发现与修复**：修正重复预约判断顺序、课次可见范围、账号档案关联当前读、课程模板快照语义、报表筛选与到课率、日志轮转/操作名/脱敏规则，并补齐任务归属和当前导航。最终语义扫描又发现“数据边界规则”的摘要仍先写容量、后写重复预约，已同步为先查重复预约，避免私教课满员时遮蔽 `ConflictError`。
- **命令与结果**：仓库根目录执行 `python -B -X utf8 -m unittest discover -s tests -p test_contract_consistency.py -v`，5 项通过；执行 `python -X utf8 -m src.cmd.test unit`，44 项通过、1 项 MySQL 用例排除；`git diff --check` 通过。pytest 因工作区 `.pytest_cache` 无写权限产生 2 条缓存警告，不影响用例结果。
- **验证范围**：契约测试只证明文档与声明一致；并发锁、权限执行、提交未知及真实 MySQL 快照行为仍需在各占位方法实现后验证。

### [2026-09-23] 文档契约与次卡空值约束复核

- **检查范围**：公共数据类字段和默认值、服务与 Repository 方法签名、SQL 列类型与可空性、功能列表 CSV 列数，以及默认测试入口。
- **命令与结果**：仓库根目录执行 `python -B -X utf8 -m unittest discover -s tests -p test_contract_consistency.py -v`，3 项通过；执行 `python -B -X utf8 -m src.cmd.test`，38 项通过、1 项 MySQL 用例排除；功能列表 88 行数据均为 9 列，`git diff --check` 通过。
- **验证范围**：本轮未连接 MySQL；次卡 CHECK 的 NULL 三值逻辑修复仍需在独立 MySQL 测试库执行建表和非法插入用例。

### [2026-09-23] 关闭失败与子进程回收回归

- **发现与修复**：从 dispose 注入异常时，原实现吞掉失败且清空 App 的引擎引用；现改为 StorageError 向上传播、失败保留引擎，命令输出原故障和安全关闭提示并返回 1。CLI 测试子进程补固定输入、超时及回收，测试库清理先回收本用例进程。
- **覆盖**：dispose 普通异常、EOF、Ctrl+C；部分启动失败与关闭失败同时发生；关闭失败后的重新清理；维护结果保留；测试库锁释放顺序；真实 CLI 帮助、管道输入、超时及中断；强制终止与非法超时参数。
- **命令与结果**：仓库根目录执行 `python -X utf8 -m src.cmd.test`，38 项通过、1 项 MySQL 用例排除；环境 Windows / Python 3.13.9 / pytest 8.2.0。`git diff --check` 通过。
- **验证范围**：真实 MySQL 登录菜单启动用例等待可用测试库；Windows 进程树强制结束与 POSIX 信号路径需要对应环境进一步实测，当前用例已核对本机强制结束的目标参数和等待顺序。

> 本节记录我们写测试时的总体思路（待项目骨架建立后补充，先占位）。

### 1. 测试分层（占位）

| 层级 | 测什么 | 工具（待定） |
|------|--------|--------------|
| 单元测试 | 独立函数 / 类的行为与边界 | — |
| 集成测试 | 模块间协作、接口契约 | — |
| 端到端测试 | 核心用户流程走通 | — |

### 2. 写法约定（占位）

- 按行为场景分组用例，而不是按被测函数罗列
- 接口格式是验收的一部分：列表零条、一条、多条均返回 Page，items 中为约定的 View；详情找不到或无权限时抛约定异常，不临时改成字典、列表、None 或错误文字。
- 涉及文件系统 / 数据库 / 网络的测试使用临时目录、独立测试库或模拟对象，不污染真实数据。模拟对象只代替某个依赖返回约定结果，例如模拟业务服务测试菜单；数据库事务仍需真实 MySQL 验证。

---

## 模板（复制以下结构添加新条目）

### [YYYY-MM-DD] 问题标题

- **现象**：观察到什么异常行为 / 测试怎么失败的
- **定位**：怎么找到根因的（日志、断点、二分、最小复现……）
- **根因**：问题的本质原因
- **修复**：怎么改的，为什么这样改
- **验证**：修复后用什么测试确认（新增了哪个回归测试）
- **教训**：（可选）下次怎么避免

---

## 问题记录

### [2026-09-20] 次卡、自动续购与 20/64/256 节赠课复核

- **变更**：有效期维持 30/90/365 天，赠课改为 20/64/256 节；次卡无期限、不赠课、每日只扣一次。新增每日入场记录和签名，SaleInput 删除手选生效日，首版结算后不再修改签到。
- **静态验证**：根目录运行 `python -B -X utf8 -m unittest discover -s tests -p test_contract_consistency.py -v`，3 项通过；65 个应用文件可按 Python 3.10 语法解析并在无第三方包路径时导入，376 个手写方法仍只抛 NotImplementedError。清单保持 88 项、9 列、编号唯一与 UTF-8 BOM。
- **SQL 样例验证**：直接提取设计中的 card_products 和 gym_entries 建表语句及续购末尾日期 SELECT，用一次性 SQLite 内存脚本核对 14 组固定配额/空值、4 组续购查询、6 组入场唯一约束/归属/扣减量场景，均通过。涵盖旧配额被拒绝、次卡不得赠课、未来卡参与接续、作废卡与次卡排除、同日换卡仍不能重复登记、隔日和不同会员可分别登记。
- **工具适配与限制**：首次试跑遇到 SQLite 不支持 MySQL 的 ON UPDATE 和 CHAR_LENGTH，检查脚本移除自动更新时间语法并补等价函数后通过；同时适配自增、索引名称及 FOR UPDATE。仓库 SQL 保留 MySQL 格式。该检查不验证 MySQL、并发或业务方法；同日最后一次再入场、跨午夜请求重试、并发续购和结算不可更正仍需后续业务测试。

### [2026-09-20] 赠课到期与永久历史查看规则复核

> 此条保留当时检查结果；赠课数量和剩余边界随后已按上方新记录调整。

- **变更**：固定月/季/年赠课 30/90/365 节，赠课随来源卡到期失效；教练提供未结算预约的补签入口；体测保留历史查看权，无有效预约时停止更新，再次预约恢复。公开返回类型保持不变，体测仓储补可信查询范围和时间参数。
- **静态检查**：根目录运行 `python -B -X utf8 -m unittest discover -s tests -p test_contract_consistency.py -v`，3 项通过；65 个应用 Python 文件可按 Python 3.10 语法解析、禁用第三方包路径时导入，363 个手写方法仍仅抛 NotImplementedError。CSV 保持 88 项、9 列、编号唯一和 UTF-8 BOM。
- **查询逻辑检查**：一次性脚本直接提取架构第 3.6 节 SELECT，在 SQLite 内存数据库注册具有相同空值规则的 LEAST 后执行；14 个场景通过，覆盖无预约、有效期间、下课自动截止、延迟消课/缺席、取消、原记录恢复预约、补录旧测量日期、多次预约、再次预约和其他教练的隔离。
- **验证边界**：上述查询检查只验证样例数据下的 SQL 筛选逻辑，不代表 MySQL 执行计划、事务隔离或整个权限流程通过。业务方法仍未实现，MySQL 建表、固定赠课 CHECK、会员行锁与并发读写尚未实测；卡到期后补签及结算需在实现后补行为测试。

### [2026-09-20] 门禁、私教赠课与 150 分钟上限复核

> 本条记录先前复核；赠课期限与数量等后续确认见上条，不能把旧待定项当作当前规则。

- **发现**：原来笼统的“次数”同时指向入场和消课；旧卡日期检查会使“不限使用期限”的赠课无法继续使用；签到原话未说明截止点。将后两项保留为待确认，未将建议写成已决定。
- **修正**：区分入场余额与私教节数；补次卡入场用尽的报表分类；私教模板为 1–150 整数分钟，排课时间差严格匹配；SQL 显式检查可空字段，避免 NULL 绕过固定天数规则；消课每次恰好 1 节，缺席不写扣课记录。
- **已执行**：仓库根目录运行 `python -B -X utf8 -m unittest discover -s tests -p test_contract_consistency.py -v`，3 项静态一致性检查通过。另用一次性脚本检查 65 个应用 Python 文件可按 Python 3.10 语法解析、禁用第三方包路径时可导入；362 个手写方法仍仅抛 NotImplementedError。
- **文档验证**：94 处本地文件及标题链接通过；私教章节改名后目录锚点确有遗漏，已修复。另修正一次性链接检查器对文件名内括号的解析，PDF 引用本身有效。功能清单为 88 项、9 列，编号唯一且保留 UTF-8 BOM；`git diff --check` 通过。
- **后续业务用例，尚未执行**：最后有效日 23:59:59.999999 与次日 00:00；30/90/365 天跨月及闰年；150 分钟与多 1 秒；空值绕过卡约束；取消/缺席只释放私教占用；体测边界及越界；最后一节赠课的并发预约。这些需要业务实现和独立 MySQL 测试库，静态通过不能代替它们。

### [2026-09-20] 数据格式的语义复核与持续检查

- **发现与修正**：空分页参数、卡提醒有效日期、档案移交、历史统计含义、课程快照、课次收尾、提交未知编号和查询入口存在缺口；修正设计并同步骨架。补充整数/Decimal/时间边界、状态对应的空值、报表口径与请求摘要格式。
- **已执行**：在仓库根目录运行 `python -B -X utf8 -m unittest discover -s tests -p test_contract_consistency.py -v`，3 项检查通过；核对公共数据字段/默认值/枚举、服务及数据访问方法签名、16 张业务表与模型的列类型和可空性。schema_versions 是结构版本元数据，不对应业务模型。
- **骨架验证**：65 个应用 Python 文件可按 Python 3.10 语法解析，并在禁用第三方包路径时导入；360 个手写方法仍仅抛 NotImplementedError，未加入业务实现。
- **当时边界**：静态检查只能发现文档与声明不一致。未执行 MySQL 建表、并发事务或业务行为测试；当时未定规则的后续确认与遗留问题见上条记录及架构第 10 节。

### [2026-09-20] 文件骨架与签名一致性检查

- **检查范围**：检查骨架结构和类型，未运行业务测试，也未执行 MySQL 建表。
- **结果**：65 个 Python 文件可在禁用第三方包路径的环境中导入；350 个手写函数或方法均有参数与返回类型注解，函数体仅抛 NotImplementedError。
- **接口对齐**：原设计中的 75 个服务及收款数据访问签名逐项匹配；50 个共用数据类的字段、默认值与装饰器匹配；全部手写函数的类型引用可解析。
- **后续验证**：这些检查只能说明骨架可导入且签名一致，不能代替未来的权限、事务、并发或 CLI 流程测试。

### [2026-09-20] 设计文档与接口格式检查

- **检查范围**：本次是文档检查，未启动应用或执行真实 MySQL 业务测试。
- **Python 示例**：19 个代码块通过语法解析，50 个数据类可在内存中加载，85 个接口方法的类型引用可解析；检查了统一异常处理的继续、重新登录、退出、结果核实，以及取消不记错、异常只记录一次、日志不含异常敏感原文、日志失败保持核实动作。
- **SQL 静态检查**：17 张表的名称不重复，外键引用的表、字段与类型匹配。尚未在 MySQL 执行，不能据此断言约束、事务与并发行为已通过。
- **功能清单**：86 行、9 列，保留全部原有 40 个 ID；负责人符合暂定分工，状态未因分配任务而改为已实现；UTF-8 BOM 与功能编号引用有效。
- **文档一致性**：核对本地链接和标题锚点，清除旧技术栈文件及 errors.py 的引用；后续改返回类型时同时更新调用方与格式测试。

### [2026-09-23] SYS 基础实现审计报告复核

> 本条记录审计当时的结果；连接池关闭行为和测试数量已由本页顶部同日记录更新。

- **复核结果**：确认初始化完成表的记录时机、只读结构检查的多余提交、连接池关闭容错、密码验证异常范围和配置路径说明需要修正。配置解析按数据库、日志和通用字段拆分，公开 `load_config()` 签名保持不变。
- **排除误报**：`gym_entries.(membership_id, member_id)` 已复合引用 `memberships.(id, member_id)`，而 `memberships.member_id` 又引用 `members.id`，不能写入不存在或不属于该卡的会员；架构规定的 5 个查询索引也都存在。空 `DB_PASSWORD` 覆盖和空数据库密码是已经确认的部署配置语义，补充到架构说明后保留。
- **当时验证**：运行 `python -m compileall -q src tests`、`python -B -X utf8 -m unittest discover -s tests -v` 和 `git diff --check`，当时 3 项契约检查通过。另用临时配置核对文件密码、显式空环境变量和相对日志目录，用模拟连接核对第三张表失败时只报告前两张已确认表；当时连接池关闭异常不会向外传播，现已改为抛出 `StorageError` 并保留引擎供重试。
- **限制**：当前环境未安装 Argon2 运行依赖，也未连接真实 MySQL；外键执行、DDL 隐式提交、连接中断和查询执行计划仍需在独立 MySQL 测试库验证。

> 后续发现问题继续追加，保留旧记录与失败的定位过程。


### [2026-09-23] SYS 基础功能检查

> 本条记录统一测试入口刚建立时的结果；当前结果见本页顶部同日记录。

- **命令**：仓库根目录执行 python -X utf8 -m src.cmd.test。
- **当时结果**：pytest 收集 3 项静态契约检查并全部通过；检查字段默认值、接口签名、SQL 列类型和可空性，不连接数据库。
- **补充检查**：python -X utf8 -m src.cmd.test --help 可在无配置时显示帮助；mysql 模式缺少 --config 返回 1；python -m compileall -q main.py src tests 通过。
- **未运行**：本机没有可用的独立 MySQL 8.4 测试服务，未执行真实建表、锁、事务、seed 或并发场景；日志和统一错误处理不在本轮范围内。


### [2026-10-26] 会员域单测发现的三个缺陷

- **命令**：`py -3 -B -X utf8 tests\unit\db\test_member_repo.py`、`tests\unit\test_member_service.py`、`tests\unit\test_member_logic.py`（本机未安装 pytest 与 sqlalchemy）。
- **缺陷 1**：`MemberView` 只传了 `id` / `name` / `phone` / `status`，漏掉 `archived_at`、`created_at`、`updated_at`，构造即 `TypeError`。修复：按 `contracts.py` 补齐 7 个字段。
- **缺陷 2**：测试里的 `sqlalchemy` 替身会遮蔽仓库已安装的真包。修复：替身加 `__dsh_stub__` 标记，检测到真包即跳过注入。
- **缺陷 3**：`import src.logic.member_logic` 会先执行 `src/logic/__init__.py`，它 import `LogicBundle`，进而把全部 Logic、Service、仓储拉进来；其中 `measurement_repo` 与 `payment_repo` 在顶层 `from sqlalchemy import Numeric, DateTime, bindparam, text`，替身只提供 `text` 时报 `ImportError: cannot import name 'Numeric'`。修复：替身补齐这四个名字。
- **结果**：三个文件分别 Ran 14 / 36 / 10，全部 OK。
- **限制**：本机未连接真实 MySQL，未验证 CHECK 约束、`DATETIME(6)` 精度与 `SELECT ... FOR UPDATE` 行锁；这些属 TEST-02、TEST-06、TEST-08。