"""使用连接替身验证数据库维护命令。"""
from __future__ import annotations

from pathlib import Path
import re
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import OperationalError, ProgrammingError

from src.cmd.db import check_database_schema, init_database
from src.errors.business import InvalidState
from src.errors.storage import InitializationError, StorageError
from src.db.connection import REQUIRED_SCHEMA_TABLES, check_schema


class _InitResult:
    """提供初始化命令所需的最小 SQLAlchemy Result 接口。"""

    def __init__(self, row=None, scalar=None, rows=None):
        self._row = row
        self._scalar = scalar
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def scalar_one(self):
        return self._scalar

    def fetchall(self):
        return self._rows



class _InitConnection:
    """不连接 MySQL，只记录结构维护器交给驱动的完整语句。"""

    def __init__(
        self,
        *,
        fail_on: str | None = None,
        schema_version: int | None = None,
        existing_objects: set[tuple[str, str]] | None = None,
        actual_tables: set[str] | None = None,
    ):
        self.engine = SimpleNamespace(url=SimpleNamespace(database="gym_test"))
        self.fail_on = fail_on
        self.schema_version = schema_version
        self.existing_objects = existing_objects or set()
        self.actual_tables = set(REQUIRED_SCHEMA_TABLES) if actual_tables is None else actual_tables
        self.statements: list[str] = []
        self.committed = False
        self.invalidated = False

    def execute(self, statement, parameters=None):
        sql = str(statement).strip()
        self.statements.append(sql)
        if self.fail_on is not None and self.fail_on in sql:
            raise RuntimeError("模拟 DDL 失败")
        if "GET_LOCK" in sql:
            return _InitResult(scalar=1)
        if "information_schema.statistics" in sql:
            key = (parameters["table_name"], parameters["object_name"])
            return _InitResult(row=(int(key in self.existing_objects),))
        if "information_schema.table_constraints" in sql:
            key = (parameters["table_name"], parameters["object_name"])
            return _InitResult(row=(int(key in self.existing_objects),))
        if "information_schema.tables" in sql:
            if "SELECT table_name" in sql:
                return _InitResult(rows=[(name,) for name in sorted(self.actual_tables)])
            return _InitResult(row=(0,))
        if sql.startswith("SELECT version FROM schema_versions"):
            row = None if self.schema_version is None else (self.schema_version,)
            return _InitResult(row=row)
        if sql.startswith("INSERT INTO schema_versions"):
            self.schema_version = int(sql.rsplit("(", 1)[1].rstrip(")"))
        index_match = re.match(
            r"ALTER TABLE (\w+)\s+ADD (?:KEY|INDEX) (\w+)", sql,
        )
        constraint_match = re.match(
            r"ALTER TABLE (\w+)\s+ADD CONSTRAINT (\w+)", sql,
        )
        match = index_match or constraint_match
        if match:
            self.existing_objects.add(match.groups())
        return _InitResult()

    def commit(self):
        self.committed = True

    def invalidate(self):
        self.invalidated = True


class _SchemaEngine:
    """为连接层结构检查提供无数据库的 Engine 替身。"""

    def __init__(self, connection: _InitConnection):
        self.connection = connection

    def connect(self):
        return self

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        return False



def test_init_database_creates_v4_schema():
    """新库一次创建 v4 全部表并直接记录版本 4。"""
    connection = _InitConnection()

    result = init_database(connection)

    assert result.tables_created == 35
    assert result.schema_version == 4
    assert connection.committed is True
    assert sum(sql.startswith("CREATE TABLE") for sql in connection.statements) == 35
    assert any(sql.startswith("ALTER TABLE accounts") for sql in connection.statements)
    assert connection.schema_version == 4
    assert not any("ADD KEY" in sql or "ADD CONSTRAINT" in sql for sql in connection.statements)



def test_init_database_reports_the_failing_alter_without_losing_completed_tables():
    """ALTER 失败时只把已成功 CREATE 的表列入 completed_tables。"""
    connection = _InitConnection(fail_on="ALTER TABLE accounts MODIFY COLUMN role")

    with pytest.raises(InitializationError) as caught:
        init_database(connection)

    assert caught.value.completed_tables == ("schema_versions", "accounts")
    assert caught.value.failed_step == "accounts.alter[4]"



@pytest.mark.parametrize(
    "script_error",
    [OSError("模拟初始化脚本缺失"), UnicodeDecodeError("utf-8", b"\xff", 0, 1, "模拟编码错误")],
)
def test_init_database_reports_initial_script_read_failure(monkeypatch, script_error):
    """初始脚本无法读取时应在执行 DDL 前报告存储错误。"""
    original_read_text = Path.read_text

    def read_schema(path: Path, *args, **kwargs):
        if path.name == "001_initial_schema.sql":
            raise script_error
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_schema)
    connection = _InitConnection()

    with pytest.raises(StorageError):
        init_database(connection)

    assert connection.statements == []
    assert connection.schema_version is None



def test_check_database_schema_accepts_complete_v4_without_changing_schema():
    """必需表和结构版本核对不执行 DDL。"""
    connection = _InitConnection(schema_version=4)

    result = check_database_schema(connection)

    assert result.current_version == 4
    assert result.required_version == 4
    assert connection.schema_version == 4
    assert connection.statements == [
        "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'",
        "SELECT version FROM schema_versions ORDER BY version DESC LIMIT 1",
    ]



def test_check_database_schema_reports_missing_required_tables():
    connection = _InitConnection(
        schema_version=4,
        actual_tables=set(REQUIRED_SCHEMA_TABLES) - {"waitlist_entries"},
    )

    with pytest.raises(InvalidState, match="数据库结构不完整，缺少：waitlist_entries"):
        check_database_schema(connection)

    assert len(connection.statements) == 1


def test_connection_check_schema_reports_missing_required_tables():
    connection = _InitConnection(
        schema_version=4,
        actual_tables=set(REQUIRED_SCHEMA_TABLES) - {"waitlist_entries"},
    )

    with pytest.raises(InvalidState, match="数据库结构不完整，缺少：waitlist_entries"):
        check_schema(_SchemaEngine(connection))

    assert len(connection.statements) == 1


@pytest.mark.parametrize("schema_version", [0, 3, 5])
def test_check_database_schema_rejects_other_versions(schema_version):
    """只有 v4 属于当前结构；其他版本不得执行 DDL。"""
    connection = _InitConnection(schema_version=schema_version)

    with pytest.raises(InvalidState):
        check_database_schema(connection)

    assert connection.schema_version == schema_version
    assert len(connection.statements) == 2
    assert connection.statements[-1].startswith("SELECT version FROM schema_versions")


@pytest.mark.parametrize(
    ("driver_error", "expected_error", "safe_message"),
    [
        (
            ProgrammingError("SELECT version", None, Exception(1146, "private schema name")),
            InvalidState,
            "数据库版本记录缺失，请先运行：python -m src.cmd.db init",
        ),
        (
            OperationalError("SELECT version", None, Exception(2013, "private connection detail")),
            StorageError,
            "数据库结构检查失败",
        ),
    ],
)
def test_check_database_schema_converts_query_failures(driver_error, expected_error, safe_message):
    """空库给出初始化步骤，连接故障保留原因并隐藏底层连接信息。"""
    class FailingConnection:
        def execute(self, statement):
            if "information_schema.tables" in str(statement):
                return _InitResult(rows=[(name,) for name in REQUIRED_SCHEMA_TABLES])
            raise driver_error

    with pytest.raises(expected_error) as caught:
        check_database_schema(FailingConnection())
    assert str(caught.value) == safe_message
    assert caught.value.__cause__ is driver_error
