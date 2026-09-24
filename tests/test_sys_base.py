from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
import re
from types import SimpleNamespace
import tempfile
from unittest import mock

import pytest

from main import parse_args
from src.config import load_config
from src.cmd.db import init_database, migrate_database
from src.errors.storage import InitializationError, MigrationError
from src.models.contracts import MemberView, Page
from src.ui.cli.formatters import format_member, format_members
from src.ui.cli.prompts import prompt_confirm, prompt_decimal, prompt_int, prompt_text
from src.errors.business import InputCancelled


def _config(path: Path, *, password: str = "file-pass") -> Path:
    path.write_text(json.dumps({
        "database": {"host": "localhost", "port": 3306, "database": "gym", "username": "u", "password": password},
        "timezone_name": "Asia/Shanghai",
    }), encoding="utf-8")
    return path


def test_parse_args_keeps_cli_default_and_config():
    assert parse_args([]).tui is False
    options = parse_args(["--tui", "--config", "custom.json"])
    assert options.tui is True
    assert options.config_path == "custom.json"


def test_load_config_environment_empty_password_overrides_file(monkeypatch):
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", dir=Path.cwd(), encoding="utf-8", delete=False
    ) as file:
        path = Path(file.name)
    try:
        _config(path)
        monkeypatch.setenv("DB_PASSWORD", "")
        settings = load_config(str(path))
        assert settings.database.password == ""
        assert settings.log.directory == (Path.cwd() / "logs").resolve()
    finally:
        path.unlink(missing_ok=True)


def test_prompt_text_cancel_and_decimal_integer_validation(monkeypatch):
    monkeypatch.setattr("builtins.input", mock.Mock(side_effect=["", "  ok  "]))
    assert prompt_text("值：") == "ok"
    monkeypatch.setattr("builtins.input", mock.Mock(side_effect=["x", "2"]))
    assert prompt_int("数：", minimum=1, maximum=3) == 2
    monkeypatch.setattr("builtins.input", mock.Mock(side_effect=["1.234", "2.50"]))
    assert prompt_decimal("金额：", minimum=Decimal("0")) == Decimal("2.50")
    monkeypatch.setattr("builtins.input", mock.Mock(return_value="q"))
    with pytest.raises(InputCancelled):
        prompt_confirm("继续？")


def test_formatter_masks_phone_and_reports_page():
    member = MemberView(id=1, account_id=None, name="张三", phone="13812345678", is_active=True)
    text = format_member(member, timezone_name="Asia/Shanghai")
    assert "138****5678" in text
    assert "12345678" not in text
    page = Page(items=[member], total=1, page=1, page_size=20)
    assert "第 1/1 页，共 1 条" in format_members(page, timezone_name="Asia/Shanghai")


class _InitResult:
    """提供初始化命令所需的最小 SQLAlchemy Result 接口。"""

    def __init__(self, row=None, scalar=None):
        self._row = row
        self._scalar = scalar

    def fetchone(self):
        return self._row

    def scalar_one(self):
        return self._scalar


class _InitConnection:
    """不连接 MySQL，只记录结构维护器交给驱动的完整语句。"""

    def __init__(
        self,
        *,
        fail_on: str | None = None,
        schema_version: int | None = None,
        existing_objects: set[tuple[str, str]] | None = None,
    ):
        self.engine = SimpleNamespace(url=SimpleNamespace(database="gym_test"))
        self.fail_on = fail_on
        self.schema_version = schema_version
        self.existing_objects = existing_objects or set()
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


def test_init_database_applies_version_one_then_migrates_to_current_version():
    """新库先按版本 1 建表，再应用版本 2 的八个结构步骤。"""
    connection = _InitConnection()

    result = init_database(connection)

    assert result.tables_created == 18
    assert result.schema_version == 2
    assert connection.committed is True
    assert sum(sql.startswith("CREATE TABLE") for sql in connection.statements) == 18
    assert any(sql.startswith("ALTER TABLE memberships") for sql in connection.statements)
    assert connection.schema_version == 2
    assert len(connection.existing_objects) == 8


def test_init_database_reports_the_failing_alter_without_losing_completed_tables():
    """ALTER 失败时只把已成功 CREATE 的表列入 completed_tables。"""
    connection = _InitConnection(fail_on="ALTER TABLE accounts MODIFY COLUMN role")

    with pytest.raises(InitializationError) as caught:
        init_database(connection)

    assert caught.value.completed_tables == ("schema_versions", "accounts")
    assert caught.value.failed_step == "accounts.alter[4]"


@pytest.mark.parametrize(
    "script_error",
    [OSError("模拟迁移脚本缺失"), UnicodeDecodeError("utf-8", b"\xff", 0, 1, "模拟编码错误")],
)
def test_init_database_reports_version_two_script_failure_after_version_one(
    monkeypatch, script_error,
):
    """002 无法读取时应准确指出版本 2 迁移脚本步骤。"""
    original_read_text = Path.read_text

    def read_schema(path: Path, *args, **kwargs):
        if path.name == "002_query_indexes_and_equipment_location.sql":
            raise script_error
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_schema)
    connection = _InitConnection()

    with pytest.raises(InitializationError) as caught:
        init_database(connection)

    assert len(caught.value.completed_tables) == 18
    assert caught.value.failed_step == "migration[2].script"
    assert caught.value.outcome_unknown is False
    assert connection.schema_version == 1


def test_migrate_database_skips_completed_ddl_and_records_version_two():
    """DDL 部分成功后重试时跳过同名结构，只执行剩余步骤。"""
    existing = {
        ("accounts", "ix_account_role_active"),
        ("memberships", "ix_membership_member_term"),
    }
    connection = _InitConnection(schema_version=1, existing_objects=existing)

    result = migrate_database(connection)

    assert result.previous_version == 1
    assert result.schema_version == 2
    assert result.steps_applied == 6
    assert connection.schema_version == 2
    assert len(connection.existing_objects) == 8
    assert not any(
        sql.startswith("ALTER TABLE accounts") for sql in connection.statements
    )


def test_migrate_database_reports_confirmed_steps_before_failure():
    """DDL 失败时报告已确认结构和具体失败步骤，版本保持为 1。"""
    connection = _InitConnection(
        schema_version=1,
        fail_on="ADD KEY ix_payment_member_time",
    )

    with pytest.raises(MigrationError) as caught:
        migrate_database(connection)

    assert caught.value.completed_steps == (
        "accounts.ix_account_role_active",
        "memberships.ix_membership_member_term",
        "memberships.ix_membership_status_expiry",
    )
    assert caught.value.failed_step == "payments.ix_payment_member_time"
    assert caught.value.outcome_unknown is False
    assert connection.schema_version == 1

    connection.fail_on = None
    retried = migrate_database(connection)

    assert retried.schema_version == 2
    assert retried.steps_applied == 5
    assert len(connection.existing_objects) == 8
