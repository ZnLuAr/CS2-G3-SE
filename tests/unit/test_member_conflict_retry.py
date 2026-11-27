"""会员建档的幂等竞态回放测试：唯一约束冲突后换新事务重试一次。

会话、事务和日志用替身；真实唯一约束与锁等待由 MySQL 用例
tests/integration/test_member_idempotency.py 覆盖。
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import src.logic.member_logic as member_logic_module
from src.errors import StorageError
from src.logic.member_logic import MemberLogic
from src.models.contracts import Actor, MemberInput, MemberView

REQUEST_ID = "6f1c1c2a-8f8f-4f6a-9d2b-2a7f4c0f5e11"
NOW = datetime(2026, 10, 30, 2, 0, 0, tzinfo=timezone.utc)


def _duplicate_key_error() -> IntegrityError:
    """驱动对唯一键重复的原始异常：args[0] 是 MySQL 错误码 1062。"""
    return IntegrityError(
        "INSERT INTO operation_records ...",
        {},
        Exception(1062, "Duplicate entry for key 'operation_records.uq_operation_request'"),
    )


def _foreign_key_error() -> IntegrityError:
    """驱动对外键失败的原始异常：错误码 1452，属于 IntegrityError 但不是唯一键冲突。

    CHECK 违反（3819）在 PyMySQL 中归入 OperationalError，走的是普通数据库错误分支，
    由 test_other_database_error_is_storage_error_without_retry 代表。
    """
    return IntegrityError(
        "INSERT INTO members ...",
        {},
        Exception(1452, "Cannot add or update a child row: a foreign key constraint fails"),
    )


def _actor():
    return Actor(account_id=10, role="receptionist", member_id=None, coach_id=None)


def _view():
    return MemberView(
        id=7, name="张三", phone=None, status="active",
        archived_at=None, created_at=NOW, updated_at=NOW,
    )


class _FakeSession:
    def __init__(self):
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.closed = True
        return False


class _FakeTransaction:
    def __init__(self, session, *, request_id=None, record_id=None):
        self._session = session
        self.request_id = request_id
        self.entered = False
        self.exited_with = None

    def __enter__(self):
        self.entered = True
        return self._session

    def __exit__(self, exc_type, exc, tb):
        self.exited_with = exc_type
        return False


class ConflictRetryTest(unittest.TestCase):
    def setUp(self):
        self.transactions = []
        self.logged = []
        self.sessions = []

        def session_factory():
            session = _FakeSession()
            self.sessions.append(session)
            return session

        def transaction_factory(s, *, request_id=None, record_id=None):
            tx = _FakeTransaction(s, request_id=request_id, record_id=record_id)
            self.transactions.append(tx)
            return tx

        def log_event(*args, **kwargs):
            self.logged.append(kwargs)

        self._patches = [
            patch.object(member_logic_module, "transaction", transaction_factory),
            patch.object(member_logic_module, "log_event", log_event),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)
        self._logic = MemberLogic(session_factory, None)

    def _run(self, service):
        self._logic._member_service = service
        return self._logic.create_member(
            _actor(), MemberInput(name="张三", phone=None), REQUEST_ID
        )

    def test_retries_once_in_new_session_after_duplicate_key(self):
        attempts = {"n": 0}

        class _ConflictOnceService:
            def create_member(self, session, actor, data, request_id):
                attempts["n"] += 1
                if attempts["n"] == 1:
                    raise _duplicate_key_error()
                return _view()

        result = self._run(_ConflictOnceService())

        self.assertEqual(result.id, 7)
        self.assertEqual(attempts["n"], 2)
        self.assertEqual(len(self.transactions), 2)
        # 合同 12.7.3 第 2 步：重试必须换新 Session，新快照才能读到胜者已提交的记录。
        self.assertEqual(len(self.sessions), 2)
        self.assertIsNot(self.sessions[0], self.sessions[1])
        self.assertTrue(all(session.closed for session in self.sessions))
        # 两次事务带同一个请求编号，提交未知时都能按原编号核实。
        self.assertEqual([tx.request_id for tx in self.transactions], [REQUEST_ID, REQUEST_ID])
        self.assertEqual(len(self.logged), 1)

    def test_second_duplicate_key_becomes_storage_error(self):
        attempts = {"n": 0}

        class _AlwaysConflictService:
            def create_member(self, session, actor, data, request_id):
                attempts["n"] += 1
                raise _duplicate_key_error()

        with self.assertRaises(StorageError) as ctx:
            self._run(_AlwaysConflictService())

        # 合同 12.7.3：只重试一次；重试的事务仍是唯一键冲突时转 StorageError，不记成功日志。
        self.assertEqual(attempts["n"], 2)
        self.assertIsInstance(ctx.exception.__cause__, IntegrityError)
        self.assertEqual(len(self.sessions), 2)
        self.assertTrue(all(session.closed for session in self.sessions))
        self.assertEqual(self.logged, [])

    def test_other_integrity_error_is_storage_error_without_retry(self):
        attempts = {"n": 0}

        class _ForeignKeyFailedService:
            def create_member(self, session, actor, data, request_id):
                attempts["n"] += 1
                raise _foreign_key_error()

        with self.assertRaises(StorageError) as ctx:
            self._run(_ForeignKeyFailedService())

        self.assertIsInstance(ctx.exception.__cause__, IntegrityError)
        self.assertEqual(attempts["n"], 1)
        self.assertEqual(len(self.sessions), 1)
        self.assertTrue(self.sessions[0].closed)
        self.assertEqual(self.logged, [])

    def test_other_database_error_is_storage_error_without_retry(self):
        attempts = {"n": 0}

        class _BrokenService:
            def create_member(self, session, actor, data, request_id):
                attempts["n"] += 1
                raise SQLAlchemyError("boom")

        with self.assertRaises(StorageError):
            self._run(_BrokenService())

        self.assertEqual(attempts["n"], 1)
        self.assertEqual(len(self.sessions), 1)
        self.assertTrue(self.sessions[0].closed)
        self.assertEqual(self.logged, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
