"""OperationRepository 单元测试：普通读、写入回读与回读失败。

会话用替身记录语句；真实唯一约束与并发行为由 MySQL 用例
tests/integration/test_member_idempotency.py 覆盖。
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from src.db.operation_repo import OperationRepository
from src.errors.storage import StorageError
from tests.support.clock import AWARE_NOW, UtcClock

REQUEST_ID = "6f1c1c2a-8f8f-4f6a-9d2b-2a7f4c0f5e11"
NAIVE_UTC = datetime(2026, 10, 30, 1, 0, 0)
SELECT_SQL = (
    "SELECT id, request_id, actor_id, operation, payload_hash, result_id, created_at "
    "FROM operation_records WHERE request_id = :request_id"
)
INSERT_SQL = (
    "INSERT INTO operation_records "
    "(request_id, actor_id, operation, payload_hash, result_id, created_at) "
    "VALUES (:request_id, :actor_id, :operation, :payload_hash, :result_id, :created_at)"
)


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
        self.assertEqual(sql, SELECT_SQL)
        self.assertNotIn("FOR UPDATE", sql)
        self.assertEqual(params, {"request_id": REQUEST_ID})

    def test_maps_row_and_attaches_utc(self):
        record = OperationRepository(_FakeSession({REQUEST_ID: _row()})).get_by_request(REQUEST_ID)

        self.assertEqual(record.request_id, REQUEST_ID)
        self.assertEqual(record.actor_id, 10)
        self.assertEqual(record.payload_hash, "a" * 64)
        self.assertEqual(record.operation, "create_member")
        self.assertEqual(record.result_id, 7)
        self.assertEqual(record.created_at, NAIVE_UTC.replace(tzinfo=timezone.utc))


class CreateTest(unittest.TestCase):
    def test_inserts_all_columns_and_returns_back_read_row(self):
        """返回值取自回读的行：记录编号只有库里有，INSERT 参数里没有。"""
        session = _FakeSession()
        record = OperationRepository(session).create(
            request_id=REQUEST_ID,
            actor_id=10,
            operation="create_member",
            payload_hash="a" * 64,
            result_id=7,
        )

        sql, params = session.calls[0]
        self.assertEqual(sql, INSERT_SQL)
        self.assertEqual(params["request_id"], REQUEST_ID)
        self.assertEqual(params["actor_id"], 10)
        self.assertEqual(params["operation"], "create_member")
        self.assertEqual(params["payload_hash"], "a" * 64)
        self.assertEqual(params["result_id"], 7)
        self.assertNotIn("id", params)
        self.assertEqual(session.calls[1][0], SELECT_SQL)
        self.assertEqual(session.calls[1][1], {"request_id": REQUEST_ID})
        self.assertEqual(record.id, 1)
        self.assertEqual(record.result_id, 7)
        self.assertEqual(record.created_at, params["created_at"].replace(tzinfo=timezone.utc))

    def test_created_at_comes_from_utc_clock(self):
        """合同 12.6：业务时刻按 UTC 写入，不依赖本机时区。"""
        session = _FakeSession()
        with patch("datetime.datetime", UtcClock):
            OperationRepository(session).create(
                request_id=REQUEST_ID,
                actor_id=10,
                operation="create_member",
                payload_hash="a" * 64,
                result_id=7,
            )
        self.assertEqual(session.calls[0][1]["created_at"], AWARE_NOW.replace(tzinfo=None))

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
