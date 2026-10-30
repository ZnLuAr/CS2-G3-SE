"""OperationRepository 单元测试：查询、锁定读取、写入回读与最后防线。

本机未安装 sqlalchemy，这里注入带标记的替身；真实唯一约束与并发行为由 MySQL 用例覆盖。
"""

from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime, timezone


class _Text:
    """替身：只保留 SQL 文本，便于断言语句内容。"""

    def __init__(self, sql: str) -> None:
        self.sql = sql

    def __str__(self) -> str:
        return self.sql


def _install_sqlalchemy_stub() -> None:
    """仓库环境装了 sqlalchemy 时用真包；只在缺依赖的本机注入带标记的替身。"""
    existing = sys.modules.get("sqlalchemy")
    if existing is not None and not getattr(existing, "__dsh_stub__", False):
        return
    if existing is None:
        try:
            import sqlalchemy as existing  # noqa: F401

            return
        except ModuleNotFoundError:
            existing = None
        if existing is not None:
            return
    if existing is None:
        existing = types.ModuleType("sqlalchemy")
        existing.__dsh_stub__ = True
        existing.__path__ = []
        sys.modules["sqlalchemy"] = existing
    for name in ("Numeric", "DateTime", "bindparam"):
        if not hasattr(existing, name):
            setattr(existing, name, lambda *args, **kwargs: None)
    existing.text = lambda sql: _Text(sql)
    if not hasattr(existing, "exc"):
        exc = types.ModuleType("sqlalchemy.exc")

        class SQLAlchemyError(Exception):
            pass

        class IntegrityError(SQLAlchemyError):
            pass

        exc.SQLAlchemyError = SQLAlchemyError
        exc.IntegrityError = IntegrityError
        sys.modules["sqlalchemy.exc"] = exc
        existing.exc = exc


_install_sqlalchemy_stub()

from src.db.operation_repo import OperationRepository  # noqa: E402
from src.errors.storage import StorageError  # noqa: E402

REQUEST_ID = "6f1c1c2a-8f8f-4f6a-9d2b-2a7f4c0f5e11"
NAIVE_UTC = datetime(2026, 10, 30, 1, 0, 0)


def _row(**overrides):
    values = {
        "id": 1,
        "request_id": REQUEST_ID,
        "actor_id": 10,
        "operation": "create_member",
        "payload_hash": "a" * 64,
        "result_id": 7,
        "created_at": NAIVE_UTC,
    }
    values.update(overrides)
    return values


class _FakeResult:
    def __init__(self, row=None, lastrowid=None) -> None:
        self._row = row
        self.lastrowid = lastrowid

    def mappings(self):
        return self

    def first(self):
        return self._row


class _FakeSession:
    """按语句形状返回预设行；INSERT 会把参数记成一行，模拟回读。"""

    def __init__(self, rows=None) -> None:
        self.rows = dict(rows or {})
        self.calls: list[tuple[str, dict | None]] = []

    def execute(self, statement, params=None) -> _FakeResult:
        sql = str(statement)
        self.calls.append((sql, params))
        if sql.lstrip().upper().startswith("INSERT"):
            self.rows[params["request_id"]] = {"id": 1, **params}
            return _FakeResult(lastrowid=1)
        return _FakeResult(row=self.rows.get(params["request_id"]))


class _NeverReadableSession(_FakeSession):
    """INSERT 成功但回读不到，用来覆盖异常分支。"""

    def execute(self, statement, params=None) -> _FakeResult:
        sql = str(statement)
        self.calls.append((sql, params))
        if sql.lstrip().upper().startswith("INSERT"):
            return _FakeResult(lastrowid=1)
        return _FakeResult(row=None)


class GetByRequestTest(unittest.TestCase):
    def test_returns_none_when_missing(self):
        session = _FakeSession()
        self.assertIsNone(OperationRepository(session).get_by_request(REQUEST_ID))
        sql, params = session.calls[0]
        self.assertIn("FROM operation_records", sql)
        self.assertNotIn("FOR UPDATE", sql)
        self.assertEqual(params["request_id"], REQUEST_ID)

    def test_maps_row_and_attaches_utc(self):
        record = OperationRepository(_FakeSession({REQUEST_ID: _row()})).get_by_request(REQUEST_ID)

        self.assertEqual(record.request_id, REQUEST_ID)
        self.assertEqual(record.operation, "create_member")
        self.assertEqual(record.result_id, 7)
        self.assertEqual(record.created_at.tzinfo, timezone.utc)


class LockByRequestTest(unittest.TestCase):
    def test_uses_for_update(self):
        session = _FakeSession({REQUEST_ID: _row()})
        record = OperationRepository(session).lock_by_request(REQUEST_ID)

        self.assertEqual(record.result_id, 7)
        sql = session.calls[0][0]
        self.assertIn("WHERE request_id = :request_id FOR UPDATE", sql)

    def test_returns_none_when_missing(self):
        self.assertIsNone(OperationRepository(_FakeSession()).lock_by_request(REQUEST_ID))


class CreateTest(unittest.TestCase):
    def test_inserts_all_columns_and_returns_back_read_row(self):
        session = _FakeSession()
        record = OperationRepository(session).create(
            request_id=REQUEST_ID,
            actor_id=10,
            operation="create_member",
            payload_hash="a" * 64,
            result_id=7,
        )

        sql, params = session.calls[0]
        self.assertIn("INSERT INTO operation_records", sql)
        self.assertEqual(params["request_id"], REQUEST_ID)
        self.assertEqual(params["actor_id"], 10)
        self.assertEqual(params["operation"], "create_member")
        self.assertEqual(params["payload_hash"], "a" * 64)
        self.assertEqual(params["result_id"], 7)
        self.assertIsNone(params["created_at"].tzinfo)
        self.assertIn("FROM operation_records", session.calls[1][0])
        self.assertEqual(record.result_id, 7)
        self.assertEqual(record.created_at.tzinfo, timezone.utc)

    def test_raises_storage_error_when_row_cannot_be_read_back(self):
        with self.assertRaises(StorageError):
            OperationRepository(_NeverReadableSession()).create(
                request_id=REQUEST_ID,
                actor_id=10,
                operation="create_member",
                payload_hash="a" * 64,
                result_id=7,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
