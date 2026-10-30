"""会员建档的幂等竞态回放测试：唯一约束冲突后换新事务重试一次。

本机未安装 sqlalchemy，这里注入带标记的替身；真实唯一约束与锁等待由 MySQL 用例覆盖。
"""

from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime, timezone
from unittest.mock import patch


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
    for name in ("text", "Numeric", "DateTime", "bindparam"):
        if not hasattr(existing, name):
            setattr(existing, name, lambda *args, **kwargs: None)
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

import src.logic.member_logic as member_logic_module  # noqa: E402
from src.errors import StorageError  # noqa: E402
from src.logic.member_logic import MemberLogic  # noqa: E402
from src.models.contracts import Actor, MemberInput, MemberView  # noqa: E402

REQUEST_ID = "6f1c1c2a-8f8f-4f6a-9d2b-2a7f4c0f5e11"
NOW = datetime(2026, 10, 30, 2, 0, 0, tzinfo=timezone.utc)


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
    def __init__(self, session):
        self._session = session
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
        session = _FakeSession()

        def transaction_factory(s, *, request_id=None, record_id=None):
            tx = _FakeTransaction(s)
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
        self._logic = MemberLogic(lambda: session, None)

    def _run(self, service):
        self._logic._member_service = service
        return self._logic.create_member(
            _actor(), MemberInput(name="张三", phone=None), REQUEST_ID
        )

    def test_retries_once_after_integrity_error(self):
        from sqlalchemy.exc import IntegrityError

        attempts = {"n": 0}

        class _ConflictOnceService:
            def create_member(self, session, actor, data, request_id):
                attempts["n"] += 1
                if attempts["n"] == 1:
                    raise IntegrityError("uq_operation_request", {}, Exception("dup"))
                return _view()

        result = self._run(_ConflictOnceService())

        self.assertEqual(result.id, 7)
        self.assertEqual(attempts["n"], 2)
        self.assertEqual(len(self.transactions), 2)
        self.assertEqual(len(self.logged), 1)

    def test_second_integrity_error_becomes_storage_error(self):
        from sqlalchemy.exc import IntegrityError

        class _AlwaysConflictService:
            def create_member(self, session, actor, data, request_id):
                raise IntegrityError("uq_operation_request", {}, Exception("dup"))

        with self.assertRaises(StorageError):
            self._run(_AlwaysConflictService())

        self.assertEqual(self.logged, [])

    def test_other_database_error_is_storage_error_without_retry(self):
        from sqlalchemy.exc import SQLAlchemyError

        attempts = {"n": 0}

        class _BrokenService:
            def create_member(self, session, actor, data, request_id):
                attempts["n"] += 1
                raise SQLAlchemyError("boom")

        with self.assertRaises(StorageError):
            self._run(_BrokenService())

        self.assertEqual(attempts["n"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
