"""MemberLogic 单元测试：事务边界、提交未知与错误映射。

会话工厂、事务上下文和日志函数都用替身，不连接数据库。
"""

from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime, timezone
from unittest.mock import patch


def _install_sqlalchemy_stub() -> None:
    """仓库环境装了 sqlalchemy 时用真包；只在缺依赖的本机注入带标记的替身。

    `import src.logic.member_logic` 会先执行 `src/logic/__init__.py`，它 import LogicBundle，
    进而把全部 Logic、Service、仓储拉进来；其中 measurement_repo 与 payment_repo 在顶层
    `from sqlalchemy import Numeric, DateTime, bindparam, text`，所以替身必须提供这些名字。
    """
    existing = sys.modules.get("sqlalchemy")
    if existing is not None and not getattr(existing, "__dsh_stub__", False):
        return
    if existing is None:
        try:
            import sqlalchemy as existing  # noqa: F401
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

        exc.SQLAlchemyError = SQLAlchemyError
        sys.modules["sqlalchemy.exc"] = exc
        existing.exc = exc


_install_sqlalchemy_stub()

import src.logic.member_logic as member_logic_module  # noqa: E402
from src.errors import OutcomeUnknownError, StorageError  # noqa: E402
from src.logging import Operation, Outcome  # noqa: E402
from src.models.contracts import Actor, MemberInput, MemberView  # noqa: E402
from src.logic.member_logic import MemberLogic  # noqa: E402  # noqa: E402

REQUEST_ID = "6f1c1c2a-8f8f-4f6a-9d2b-2a7f4c0f5e11"


def _actor():
    return Actor(account_id=10, role="receptionist", member_id=None, coach_id=None)


NOW = datetime(2026, 10, 23, 3, 0, 0, tzinfo=timezone.utc)


def _view(member_id=7):
    return MemberView(
        id=member_id, name="张三", phone=None, status="active",
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
    def __init__(self, session, *, request_id=None, record_id=None, fail_commit=False):
        self._session = session
        self._request_id = request_id
        self._record_id = record_id
        self._fail_commit = fail_commit
        self.entered = False
        self.exited_with = None

    def __enter__(self):
        self.entered = True
        return self._session

    def __exit__(self, exc_type, exc, tb):
        self.exited_with = exc_type
        if exc_type is None and self._fail_commit:
            raise OutcomeUnknownError(
                "事务提交结果未知", request_id=self._request_id, record_id=self._record_id
            )
        return False


class _FakeService:
    def __init__(self, *, view=None, error=None):
        self._view = view
        self._error = error
        self.calls = []

    def create_member(self, session, actor, data, request_id):
        self.calls.append((session, actor, data, request_id))
        if self._error is not None:
            raise self._error
        return self._view

    def get_member_by_request(self, session, actor, request_id):
        if self._error is not None:
            raise self._error
        return self._view

    def get_member(self, session, actor, member_id):
        if self._error is not None:
            raise self._error
        return self._view


class MemberLogicTestBase(unittest.TestCase):
    def setUp(self):
        self.session = _FakeSession()
        self.transactions: list[_FakeTransaction] = []
        self.logged: list[dict] = []
        self._fail_commit = False

        def transaction_factory(session, *, request_id=None, record_id=None):
            tx = _FakeTransaction(
                session, request_id=request_id, record_id=record_id, fail_commit=self._fail_commit
            )
            self.transactions.append(tx)
            return tx

        def log_event(*args, **kwargs):
            self.logged.append({"args": args, "kwargs": kwargs})

        self._patches = [
            patch.object(member_logic_module, "transaction", transaction_factory),
            patch.object(member_logic_module, "log_event", log_event),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)

    def _logic(self, service):
        return MemberLogic(lambda: self.session, service)


class CreateMemberTest(MemberLogicTestBase):
    def test_commits_in_one_transaction_and_logs_after_success(self):
        service = _FakeService(view=_view())
        result = self._logic(service).create_member(_actor(), MemberInput(name="张三", phone=None), REQUEST_ID)

        self.assertEqual(result.id, 7)
        self.assertEqual(len(self.transactions), 1)
        self.assertTrue(self.transactions[0].entered)
        self.assertEqual(self.transactions[0].exited_with, None)
        self.assertEqual(len(service.calls), 1)
        self.assertTrue(self.session.closed)
        self.assertEqual(len(self.logged), 1)
        kwargs = self.logged[0]["kwargs"]
        self.assertEqual(kwargs["operation"], Operation.MEMBER_CREATE.value)
        self.assertEqual(kwargs["outcome"], Outcome.SUCCESS.value)
        self.assertEqual(kwargs["actor_id"], 10)
        self.assertEqual(kwargs["result_id"], 7)

    def test_propagates_business_error_without_logging(self):
        from src.errors.business import InvalidInputError

        service = _FakeService(error=InvalidInputError("姓名不能为空"))
        with self.assertRaises(InvalidInputError):
            self._logic(service).create_member(_actor(), MemberInput(name="", phone=None), REQUEST_ID)

        self.assertEqual(self.transactions[0].exited_with, InvalidInputError)
        self.assertEqual(self.logged, [])

    def test_maps_sqlalchemy_error_to_storage_error(self):
        from sqlalchemy.exc import SQLAlchemyError

        service = _FakeService(error=SQLAlchemyError("boom"))
        with self.assertRaises(StorageError):
            self._logic(service).create_member(_actor(), MemberInput(name="张三", phone=None), REQUEST_ID)
        self.assertEqual(self.logged, [])

    def test_commit_unknown_raises_outcome_unknown_with_request_id(self):
        self._fail_commit = True
        service = _FakeService(view=_view())
        with self.assertRaises(OutcomeUnknownError) as ctx:
            self._logic(service).create_member(_actor(), MemberInput(name="张三", phone=None), REQUEST_ID)

        self.assertEqual(ctx.exception.request_id, REQUEST_ID)
        # 提交未知时不记成功日志
        self.assertEqual(self.logged, [])


class ReadPathTest(MemberLogicTestBase):
    def test_get_member_by_request_uses_short_transaction(self):
        result = self._logic(_FakeService(view=_view())).get_member_by_request(_actor(), REQUEST_ID)
        self.assertEqual(result.id, 7)
        self.assertEqual(len(self.transactions), 1)
        self.assertTrue(self.session.closed)

    def test_get_member_maps_database_error(self):
        from sqlalchemy.exc import SQLAlchemyError

        with self.assertRaises(StorageError):
            self._logic(_FakeService(error=SQLAlchemyError("boom"))).get_member(_actor(), 7)


class ListMembersTest(MemberLogicTestBase):
    def test_uses_short_transaction(self):
        from src.models.contracts import MemberQuery, Page, PageRequest

        page = Page(items=[_view()], total=1, page=1, page_size=20)
        service = _FakeService()
        service.list_members = lambda session, actor, query: page

        result = self._logic(service).list_members(_actor(), MemberQuery(paging=PageRequest()))

        self.assertEqual(result.total, 1)
        self.assertEqual(len(self.transactions), 1)
        self.assertTrue(self.session.closed)

    def test_maps_database_error(self):
        from sqlalchemy.exc import SQLAlchemyError
        from src.models.contracts import MemberQuery, PageRequest

        def boom(session, actor, query):
            raise SQLAlchemyError("boom")

        service = _FakeService()
        service.list_members = boom

        with self.assertRaises(StorageError):
            self._logic(service).list_members(_actor(), MemberQuery(paging=PageRequest()))


class UpdateMemberTest(MemberLogicTestBase):
    def test_updates_in_one_transaction_and_logs(self):
        service = _FakeService()
        service.update_member = lambda session, actor, member_id, data: _view()

        result = self._logic(service).update_member(_actor(), 7, MemberInput(name="李四", phone=None))

        self.assertEqual(result.id, 7)
        self.assertEqual(len(self.transactions), 1)
        self.assertTrue(self.session.closed)
        self.assertEqual(self.logged[0]["kwargs"]["operation"], Operation.MEMBER_UPDATE.value)
        self.assertEqual(self.logged[0]["kwargs"]["result_id"], 7)

    def test_maps_database_error(self):
        from sqlalchemy.exc import SQLAlchemyError

        def boom(session, actor, member_id, data):
            raise SQLAlchemyError("boom")

        service = _FakeService()
        service.update_member = boom

        with self.assertRaises(StorageError):
            self._logic(service).update_member(_actor(), 7, MemberInput(name="李四", phone=None))
        self.assertEqual(self.logged, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
