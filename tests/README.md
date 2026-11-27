# 后端测试

测试按验证范围分类，公共资源由 `conftest.py` 装配。新增用例放入对应目录，并在开发备注中关联功能 ID，例如 `BOOK-01` 的预约用例或 `TEST-06` 的并发检查。

| 目录 | 职责 | 当前用例 |
|---|---|---|
| `contracts/` | 通过静态解析核对类型、公开签名、SQL 与架构合同 | 后端声明与 v4 结构一致性 |
| `unit/` | 使用替身隔离数据库、输入和外部资源 | 配置、CLI、数据库命令、会员档案、资源清理、Worker |
| `api/` | 使用 FastAPI TestClient 与 Logic 替身验证 HTTP 适配 | 登录、身份、退出、令牌和错误响应 |
| `integration/` | 使用独立 MySQL 测试库验证持久化与完整调用 | CLI 启停、体测、报表、课程评价、会员建档并发与档案读写、MySQL 完整性错误的异常类别 |
| `support/` | 共享 fixture 与替身（测试准备与清理资源） | CLI 子进程回收、MySQL 结构与数据清理、UTC 时间替身 |

浏览器端测试放在 [`frontend/tests/`](../frontend/tests/)，命令见[前端说明](../frontend/README.md)。

## 准备与执行

前提：Python 3.10 以上。在仓库根目录创建虚拟环境并激活，随后安装所需运行依赖和测试工具：

```bash
python -m pip install -r requirements/all.txt -r requirements/dev.txt
python -B -X utf8 -m src.cmd.test unit
```

默认入口执行契约、单元和 API 适配测试，成功返回 0。API 测试需要 Web 依赖；出现跳过时先查看原因，再按上面的命令补齐依赖。单独核对公共声明时，可只用标准库运行：

```bash
python -B -X utf8 -m unittest discover -s tests/contracts -p test_backend_contracts.py -v
```

单独定位一类测试时，使用当前虚拟环境的 pytest：

```bash
python -m pytest tests/unit -q
python -m pytest tests/api -q -rs
python -m pytest tests/contracts -q
```

测试报告列出运行数、失败数和跳过原因。断言失败时同时检查业务输入、返回值和副作用；导入失败时确认已激活虚拟环境，且终端所在目录包含 `main.py`。

完整合同目录还核对销售来源与规则版本的复合外键；单文件的标准库命令只运行公开声明检查。单元测试包含推荐快照交换期间保留新刷新请求的用例；API 测试包含 BIGINT 字符串编号和统一错误响应。实际执行结果记录在[测试笔记](../docs/dev-materials-for-report/testing-notes.md)。

## MySQL 集成测试

准备可连接的 MySQL 8.4 实例和专用的 `_test` 数据库。复制 `config.test.json.example` 为 `config.test.json`，保留 `test_database: true`，填写连接信息。PowerShell 在仓库根目录执行：

```powershell
$env:TEST_DB_PASSWORD = Read-Host '测试库密码' -MaskInput
python -m src.cmd.test mysql --config config.test.json
python -m src.cmd.test all --config config.test.json
```

`Read-Host -MaskInput` 需要 PowerShell 7.1 以上；其他终端可通过本地测试配置填写密码。测试会清理专用库的结构或业务数据，应选择仅用于测试的数据库。

统一入口先持有数据库命名锁，再启动 pytest；fixture 复核测试库名、连接和锁归属。CLI 子进程停止后才清理数据库，测试结束释放连接。配置缺失、库名不符或锁被占用时命令返回失败；先检查配置和占用测试进程，再重新执行。直接 pytest 时 MySQL 用例显示显式跳过提示。

## 推送前的数据库测试

推送分支到协作远端 `origin` 前，先取得覆盖当前提交范围的 MySQL 测试结果：在上面的本地入口运行全套测试（`mysql` 或 `all` 模式），或使用下面的 labs 测试通道，并把环境、命令、通过数与失败原因记入测试笔记。当前基线：`test_mysql_cli_reaches_login_and_exits` 因周期任务回调占位而失败，视为已知项；其余全部通过即满足。

### labs 测试通道

专用测试环境（labs）在真实 MySQL 8.4 上串行运行 `all` 模式的全套测试。通道检出并测试的是推送上去的提交，先提交再推送。

前提：向项目发起人索取 git 主机地址与 `labs` 账号密码。首次使用时在仓库根目录添加远端，随后推送待测分支：

```bash
git remote add test https://labs@<git 主机>/cs2-group3-se.git
git push test HEAD
```

首次推送按提示输入密码，之后由凭据管理器保存。推送期间远端逐行回显测试输出，结束时给出一行“完成”，带分支、提交、退出码与服务器上的报告路径。

常见失败：

- 提示“已有测试在运行”时，分支已更新但本次没有运行测试，等对方结束后重新推送；
- 认证失败时核对 `labs` 账号密码和远端地址；
- 出现基线以外的失败时，按回显中的用例名定位，修复后重新推送。

## 补充业务用例

Logic 和 Service 的正常、边界、权限拒绝测试放在 `unit/`，按领域命名文件，例如 `test_member_logic.py`；一次操作检查返回的 View、事务结果和失败后资源释放。仓储 SQL、原子写入与并发用例放在 `integration/`，该目录自动标记 `mysql`，使用 `initialized_mysql_database` fixture 准备结构。

课程评价单元测试覆盖服务校验、用例重试和 CLI 交互。评价集成测试使用预置预约，在 MySQL 中验证持久化、授权分页、账号停用、行锁、写入回滚和并发防重。

会员档案单元测试覆盖输入校验、权限、幂等命中与冲突、用例层事务和日志；集成测试使用预置账号与档案，在 MySQL 中验证建档同一请求编号并发的唯一约束回放（已随 CI 通过）；列表筛选分页、角色可见范围与改资料的用例见 `test_member_profile.py`，已在专用测试环境（labs）通过。

例如办卡与收款的原子性测试，应在收款写入处注入故障，再检查订单、付款与卡记录一同回滚。API 用例检查 HTTP 字段与错误动作，并使用替身控制业务结果。真实登录、销售、预约、事务和并发的验收随领域实现补充，结果分别记入测试笔记。
