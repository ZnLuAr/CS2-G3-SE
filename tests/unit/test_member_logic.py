"""MemberLogic 单元测试：事务边界、提交未知、错误映射与提交后日志。

会话工厂、事务上下文和日志函数都用替身，不连接数据库；
真实回滚与并发由 MySQL 集成用例验证。
"""

from __future__ import annotations

import logging
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError

import src.logic.member_logic as member_logic_module
from src.errors import OutcomeUnknownError, StorageError
from src.errors.business import InvalidInputError
from src.logging import Operation, Outcome
from src.models.contracts import (
    Actor,
    MemberInput,
    MemberQuery,
    MemberView,
    Page,
    PageRequest,
)
from src.logic.member_logic import MemberLogic

REQUEST_ID = "6f1c1c2a-8f8f-4f6a-9d2b-2a7f4c0f5e11"
# 大写、无短横线、非 UUID、空串、非字符串：格式校验在开启会话前拒绝（合同 4.2）。
MALFORMED_REQUEST_IDS = (
    REQUEST_ID.upper(),
    "23b5e8702eab45c8aeb894858b3e8cd3",
    "not-a-uuid",
    "",
    123,
    None,
)


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
        self.request_id = request_id
        self.record_id = record_id
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
                "事务提交结果未知", request_id=self.request_id, record_id=self.record_id
            )
        return False


class _FakeService:
    """服务替身：记录每次调用；预设错误时抛出，否则返回预设视图或分页结果。"""

    def __init__(self, *, view=None, error=None):
        self._view = view
        self._error = error
        self.calls = []

    def _handle(self, call):
        self.calls.append(call)
        if self._error is not None:
            raise self._error
        return self._view

    def create_member(self, session, actor, data, request_id):
        return self._handle(("create_member", session, actor, data, request_id))

    def get_member_by_request(self, session, actor, request_id):
        return self._handle(("get_member_by_request", session, actor, request_id))

    def get_member(self, session, actor, member_id):
        return self._handle(("get_member", session, actor, member_id))

    def list_members(self, session, actor, query):
        return self._handle(("list_members", session, actor, query))

    def update_member(self, session, actor, member_id, data):
        return self._handle(("update_member", session, actor, member_id, data))


class MemberLogicTestBase(unittest.TestCase):
    def setUp(self):
        self.session = _FakeSession()
        self.opened: list[_FakeSession] = []
        self.transactions: list[_FakeTransaction] = []
        self.logged: list[dict] = []
        self.log_event_error: Exception | None = None
        self.log_event_return = None
        self._fail_commit = False

        def transaction_factory(session, *, request_id=None, record_id=None):
            tx = _FakeTransaction(
                session, request_id=request_id, record_id=record_id, fail_commit=self._fail_commit
            )
            self.transactions.append(tx)
            return tx

        def log_event(*args, **kwargs):
            self.logged.append({"args": args, "kwargs": kwargs})
            if self.log_event_error is not None:
                raise self.log_event_error
            return self.log_event_return

        self._patches = [
            patch.object(member_logic_module, "transaction", transaction_factory),
            patch.object(member_logic_module, "log_event", log_event),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)

    def _logic(self, service):
        def session_factory():
            self.opened.append(self.session)
            return self.session

        return MemberLogic(session_factory, service)


class CreateMemberTest(MemberLogicTestBase):
    def test_commits_in_one_transaction_and_logs_after_success(self):
        service = _FakeService(view=_view())
        result = self._logic(service).create_member(_actor(), MemberInput(name="张三", phone=None), REQUEST_ID)

        self.assertEqual(result.id, 7)
        self.assertEqual(len(self.transactions), 1)
        self.assertTrue(self.transactions[0].entered)
        self.assertEqual(self.transactions[0].exited_with, None)
        # 规范化后的请求编号同时传给事务（提交未知时核实）和服务（幂等键）。
        self.assertEqual(self.transactions[0].request_id, REQUEST_ID)
        self.assertEqual(service.calls[0][-1], REQUEST_ID)
        self.assertTrue(self.session.closed)
        self.assertEqual(len(self.logged), 1)
        self.assertEqual(self.logged[0]["args"], (logging.INFO,))
        kwargs = self.logged[0]["kwargs"]
        self.assertEqual(kwargs["operation"], Operation.MEMBER_CREATE.value)
        self.assertEqual(kwargs["outcome"], Outcome.SUCCESS.value)
        self.assertEqual(kwargs["actor_id"], 10)
        # 合同 11.1 / 13.9.2：成功日志带请求编号，界面按编号核实时能在日志里对上。
        self.assertEqual(kwargs["request_id"], REQUEST_ID)
        self.assertEqual(kwargs["result_id"], 7)

    def test_rejects_malformed_request_id_before_opening_session(self):
        """合同 4.2：request_id 的格式校验在进入事务前完成，非法编号不开会话、不触服务。"""
        service = _FakeService(view=_view())
        for bad in MALFORMED_REQUEST_IDS:
            with self.subTest(request_id=bad), self.assertRaises(InvalidInputError):
                self._logic(service).create_member(_actor(), MemberInput(name="张三", phone=None), bad)

        self.assertEqual(self.opened, [])
        self.assertEqual(self.transactions, [])
        self.assertEqual(service.calls, [])
        self.assertEqual(self.logged, [])

    def test_propagates_business_error_without_logging(self):
        service = _FakeService(error=InvalidInputError("姓名不能为空"))
        with self.assertRaises(InvalidInputError):
            self._logic(service).create_member(_actor(), MemberInput(name="", phone=None), REQUEST_ID)

        self.assertEqual(self.transactions[0].exited_with, InvalidInputError)
        self.assertTrue(self.session.closed)
        self.assertEqual(self.logged, [])

    def test_maps_sqlalchemy_error_to_storage_error(self):
        with self.assertRaises(StorageError):
            self._logic(_FakeService(error=SQLAlchemyError("boom"))).create_member(
                _actor(), MemberInput(name="张三", phone=None), REQUEST_ID
            )
        self.assertTrue(self.session.closed)
        self.assertEqual(self.logged, [])

    def test_commit_unknown_raises_outcome_unknown_with_request_and_record_id(self):
        self._fail_commit = True
        service = _FakeService(view=_view())
        with self.assertRaises(OutcomeUnknownError) as ctx:
            self._logic(service).create_member(_actor(), MemberInput(name="张三", phone=None), REQUEST_ID)

        # 合同 12.7.4 / 6.2：提交结果未知时带上请求编号和记录编号供核实，且不记成功日志。
        self.assertEqual(ctx.exception.request_id, REQUEST_ID)
        self.assertEqual(ctx.exception.record_id, 7)
        self.assertTrue(self.session.closed)
        self.assertEqual(self.logged, [])


class ReadPathTest(MemberLogicTestBase):
    def test_get_member_by_request_uses_short_transaction(self):
        result = self._logic(_FakeService(view=_view())).get_member_by_request(_actor(), REQUEST_ID)
        self.assertEqual(result.id, 7)
        self.assertEqual(len(self.transactions), 1)
        self.assertTrue(self.session.closed)

    def test_get_member_by_request_rejects_malformed_request_id_before_opening_session(self):
        """合同 4.2：核实接口同样在开启会话前校验请求编号。"""
        service = _FakeService(view=_view())
        for bad in MALFORMED_REQUEST_IDS:
            with self.subTest(request_id=bad), self.assertRaises(InvalidInputError):
                self._logic(service).get_member_by_request(_actor(), bad)

        self.assertEqual(self.opened, [])
        self.assertEqual(self.transactions, [])
        self.assertEqual(service.calls, [])

    def test_get_member_by_request_maps_database_error(self):
        with self.assertRaises(StorageError):
            self._logic(_FakeService(error=SQLAlchemyError("boom"))).get_member_by_request(_actor(), REQUEST_ID)
        self.assertTrue(self.session.closed)

    def test_get_member_uses_short_transaction(self):
        result = self._logic(_FakeService(view=_view())).get_member(_actor(), 7)
        self.assertEqual(result.id, 7)
        self.assertEqual(len(self.transactions), 1)
        self.assertTrue(self.session.closed)

    def test_get_member_maps_database_error(self):
        with self.assertRaises(StorageError):
            self._logic(_FakeService(error=SQLAlchemyError("boom"))).get_member(_actor(), 7)
        self.assertTrue(self.session.closed)


class ListMembersTest(MemberLogicTestBase):
    def _query(self):
        return MemberQuery(paging=PageRequest())

    def test_uses_short_transaction(self):
        page = Page(items=[_view()], total=1, page=1, page_size=20)

        result = self._logic(_FakeService(view=page)).list_members(_actor(), self._query())

        self.assertEqual(result, page)
        self.assertEqual(len(self.transactions), 1)
        self.assertTrue(self.session.closed)

    def test_maps_database_error(self):
        with self.assertRaises(StorageError):
            self._logic(_FakeService(error=SQLAlchemyError("boom"))).list_members(_actor(), self._query())
        self.assertTrue(self.session.closed)


class UpdateMemberTest(MemberLogicTestBase):
    def test_updates_in_one_transaction_and_logs(self):
        service = _FakeService(view=_view())

        result = self._logic(service).update_member(_actor(), 7, MemberInput(name="李四", phone=None))

        self.assertEqual(result.id, 7)
        self.assertEqual(len(self.transactions), 1)
        self.assertTrue(self.session.closed)
        kwargs = self.logged[0]["kwargs"]
        self.assertEqual(kwargs["operation"], Operation.MEMBER_UPDATE.value)
        self.assertEqual(kwargs["result_id"], 7)
        # 改资料没有请求编号，日志里对应字段为空。
        self.assertIsNone(kwargs["request_id"])

    def test_commit_unknown_raises_outcome_unknown_with_record_id(self):
        """合同 6.2：对既有记录的变更在提交未知时带上记录编号，供界面按编号核实。"""
        self._fail_commit = True
        service = _FakeService(view=_view())
        with self.assertRaises(OutcomeUnknownError) as ctx:
            self._logic(service).update_member(_actor(), 7, MemberInput(name="李四", phone=None))

        self.assertEqual(ctx.exception.record_id, 7)
        self.assertIsNone(ctx.exception.request_id)
        self.assertTrue(self.session.closed)
        self.assertEqual(self.logged, [])

    def test_maps_database_error(self):
        with self.assertRaises(StorageError):
            self._logic(_FakeService(error=SQLAlchemyError("boom"))).update_member(
                _actor(), 7, MemberInput(name="李四", phone=None)
            )
        self.assertTrue(self.session.closed)
        self.assertEqual(self.logged, [])


class LogFailureTest(MemberLogicTestBase):
    """合同 11.1：日志失败不回滚已提交的业务，业务结果照常返回，失败经固定提示上报。"""

    def setUp(self):
        super().setUp()
        report_patch = patch.object(member_logic_module, "report_log_failure")
        self.report = report_patch.start()
        self.addCleanup(report_patch.stop)

    def test_create_member_still_returns_view_when_log_raises(self):
        self.log_event_error = RuntimeError("disk full")

        result = self._logic(_FakeService(view=_view())).create_member(
            _actor(), MemberInput(name="张三", phone=None), REQUEST_ID
        )

        self.assertEqual(result.id, 7)
        # 固定提示只带操作名和异常类型，不带请求编号等业务字段。
        self.report.assert_called_once_with(Operation.MEMBER_CREATE.value, self.log_event_error)

    def test_update_member_still_returns_view_when_log_raises(self):
        self.log_event_error = RuntimeError("disk full")

        result = self._logic(_FakeService(view=_view())).update_member(
            _actor(), 7, MemberInput(name="李四", phone=None)
        )

        self.assertEqual(result.id, 7)
        self.report.assert_called_once_with(Operation.MEMBER_UPDATE.value, self.log_event_error)

    def test_false_return_from_log_event_is_left_to_log_module(self):
        """log_event 运行期写入失败时返回 False 并自行向标准错误提示，用例层不重复上报。"""
        self.log_event_return = False

        result = self._logic(_FakeService(view=_view())).create_member(
            _actor(), MemberInput(name="张三", phone=None), REQUEST_ID
        )

        self.assertEqual(result.id, 7)
        self.report.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
