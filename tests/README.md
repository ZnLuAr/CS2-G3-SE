# 后端测试

测试按验证范围分类，公共资源由 `conftest.py` 装配。新增用例放入对应目录，并在开发备注中关联功能 ID，例如 `BOOK-01` 的预约用例或 `TEST-06` 的并发检查。

| 目录 | 职责 | 当前用例 |
|---|---|---|
| `contracts/` | 通过静态解析核对类型、公开签名、SQL 与架构合同 | 后端声明与 v4 结构一致性 |
| `unit/` | 使用替身隔离数据库、输入和外部资源 | 配置、CLI、数据库命令、资源清理、Worker |
| `api/` | 使用 FastAPI TestClient 与 Logic 替身验证 HTTP 适配 | 登录、身份、退出、令牌和错误响应 |
| `integration/` | 使用独立 MySQL 测试库验证持久化与完整调用 | CLI 启动与退出 |
| `support/` | 共享 fixture（测试准备与清理资源） | CLI 子进程回收、MySQL 结构与数据清理 |

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

以下命令待专用数据库就绪后执行。前提：MySQL 8.4 可连接，已创建专用的 `_test` 数据库。复制 `config.test.json.example` 为 `config.test.json`，保留 `test_database: true`，填写连接信息。PowerShell 在仓库根目录执行：

```powershell
$env:TEST_DB_PASSWORD = Read-Host '测试库密码' -MaskInput
python -m src.cmd.test mysql --config config.test.json
python -m src.cmd.test all --config config.test.json
```

`Read-Host -MaskInput` 需要 PowerShell 7.1 以上；其他终端可通过本地测试配置填写密码。测试会清理专用库的结构或业务数据，应选择仅用于测试的数据库。

统一入口先持有数据库命名锁，再启动 pytest；fixture 复核测试库名、连接和锁归属。CLI 子进程停止后才清理数据库，测试结束释放连接。配置缺失、库名不符或锁被占用时命令返回失败；先检查配置和占用测试进程，再重新执行。直接 pytest 时 MySQL 用例显示显式跳过提示。

## 补充业务用例

Logic 和 Service 的正常、边界、权限拒绝测试放在 `unit/`，按领域命名文件，例如 `test_member_logic.py`；一次操作检查返回的 View、事务结果和失败后资源释放。仓储 SQL、原子写入与并发用例放在 `integration/`，该目录自动标记 `mysql`，使用 `initialized_mysql_database` fixture 准备结构。

例如办卡与收款的原子性测试，应在收款写入处注入故障，再检查订单、付款与卡记录一同回滚。API 用例检查 HTTP 字段与错误动作，并使用替身控制业务结果。真实登录、销售、预约、事务和并发的验收随领域实现补充，结果分别记入测试笔记。
