"""AUTH-01/LOG-02：用例层事务包装与提交后的成功日志。"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.errors import InvalidState, OutcomeUnknownError, StorageError
from src.logic.auth_logic import AuthLogic
from src.models.contracts import (
    AccountInput,
    Actor,
    CoachAccountLinkInput,
    LogQuery,
    MemberAccountLinkInput,
)

ADMIN = Actor(account_id=1, role="admin", member_id=None, coach_id=None)


class FakeSession:
    """记录事务调用顺序；提交失败时按合同回滚并抛出。"""

    def __init__(self, events, commit_error: Exception | None = None) -> None:
        self.events = events
        self.commit_error = commit_error

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def flush(self) -> None:
        self.events.append("flush")

    def commit(self) -> None:
        self.events.append("commit")
        if self.commit_error is not None:
            raise self.commit_error

    def rollback(self) -> None:
        self.events.append("rollback")


class FakeService:
    def __init__(self, events, result=None, error: Exception | None = None) -> None:
        self.events = events
        self.result = result if result is not None else SimpleNamespace(id=5)
        self.error = error

    def _result(self):
        self.events.append("service")
        if self.error is not None:
            raise self.error
        return self.result

    def create_account(self, session, actor, data):
        return self._result()

    def login(self, session, username, password):
        self.events.append("service")
        return ADMIN

    def set_account_active(self, session, actor, account_id, active):
        return self._result()

    def link_member(self, session, actor, data):
        return self._result()

    def link_coach(self, session, actor, data):
        return self._result()

    def relink_member(self, session, actor, account_id, member_id):
        return self._result()

    def relink_coach(self, session, actor, account_id, coach_id):
        return self._result()


def _logic(events, *, commit_error=None, service=None) -> AuthLogic:
    return AuthLogic(lambda: FakeSession(events, commit_error), service or FakeService(events))


def _record(events):
    def record(level, *, operation, outcome, actor_id, result_id=None, **_):
        events.append(("log", operation, outcome, actor_id, result_id))

    return record


def test_success_log_is_written_after_commit(monkeypatch):
    events = []
    monkeypatch.setattr("src.logic.auth_logic.log_event", _record(events))
    view = _logic(events).create_account(
        ADMIN, AccountInput(username="new_user", password="secret_1", role="member"),
    )
    assert view.id == 5
    assert events == [
        "service", "flush", "commit",
        ("log", "account.create", "success", 1, 5),
    ]


def test_known_business_failure_does_not_log_success(monkeypatch):
    events = []
    monkeypatch.setattr("src.logic.auth_logic.log_event", _record(events))
    logic = _logic(events, service=FakeService(events, error=InvalidState("不能执行")))
    with pytest.raises(InvalidState):
        logic.create_account(
            ADMIN, AccountInput(username="new_user", password="secret_1", role="member"),
        )
    assert events == ["service", "rollback"]


def test_unknown_commit_keeps_result_id_and_skips_success_log(monkeypatch):
    events = []
    monkeypatch.setattr("src.logic.auth_logic.log_event", _record(events))
    logic = _logic(events, commit_error=RuntimeError("连接中断"))
    with pytest.raises(OutcomeUnknownError) as caught:
        logic.create_account(
            ADMIN, AccountInput(username="new_user", password="secret_1", role="member"),
        )
    assert caught.value.record_id == 5
    assert events == ["service", "flush", "commit", "rollback"]


def test_storage_failure_is_wrapped_with_safe_message(monkeypatch):
    events = []
    monkeypatch.setattr("src.logic.auth_logic.log_event", _record(events))
    cause = SQLAlchemyError("password=secret")
    logic = _logic(events, service=FakeService(events, error=cause))
    with pytest.raises(StorageError) as caught:
        logic.create_account(
            ADMIN, AccountInput(username="new_user", password="secret_1", role="member"),
        )
    assert str(caught.value) == "创建账号失败"
    assert caught.value.__cause__ is cause
    assert events == ["service", "rollback"]


def test_login_logs_after_commit(monkeypatch):
    events = []
    monkeypatch.setattr("src.logic.auth_logic.log_event", _record(events))
    actor = _logic(events).login("admin_1", "secret_1")
    assert actor == ADMIN
    assert events == ["service", "flush", "commit", ("log", "auth.login", "success", 1, None)]


@pytest.mark.parametrize(("action", "operation"), [
    (lambda logic: logic.set_account_active(ADMIN, 5, True), "account.activate"),
    (lambda logic: logic.set_account_active(ADMIN, 5, False), "account.deactivate"),
    (
        lambda logic: logic.link_member(
            ADMIN, MemberAccountLinkInput(account_id=5, member_id=10),
        ),
        "account.link",
    ),
    (
        lambda logic: logic.link_coach(
            ADMIN, CoachAccountLinkInput(account_id=5, coach_id=20),
        ),
        "account.link",
    ),
    (lambda logic: logic.relink_member(ADMIN, 5, 10), "account.link"),
    (lambda logic: logic.relink_coach(ADMIN, 5, 20), "account.link"),
])
def test_each_write_operation_logs_its_registered_name(monkeypatch, action, operation):
    """停用、恢复、关联和移交在提交后分别记录对应操作名。"""
    events = []
    monkeypatch.setattr("src.logic.auth_logic.log_event", _record(events))
    action(_logic(events))
    assert events == ["service", "flush", "commit", ("log", operation, "success", 1, 5)]


def test_log_failure_does_not_change_committed_result(monkeypatch):
    """日志写入抛异常时业务结果照常返回，只向 stderr 输出固定提示。"""
    events = []
    reported = []

    def broken_log(*args, **kwargs):
        raise OSError("磁盘已满")

    monkeypatch.setattr("src.logic.auth_logic.log_event", broken_log)
    monkeypatch.setattr(
        "src.logic.auth_logic.report_log_failure",
        lambda operation, exc: reported.append((operation, type(exc).__name__)),
    )
    view = _logic(events).create_account(
        ADMIN, AccountInput(username="new_user", password="secret_1", role="member"),
    )
    assert view.id == 5
    assert events == ["service", "flush", "commit"]
    assert reported == [("account.create", "OSError")]


class FakeLogService(FakeService):
    """记录 Logic 传入的快照对象，验证筛选和翻页沿用同一份快照。"""

    def __init__(self, events):
        super().__init__(events)
        self.snapshots = []

    def open_log_snapshot(self, session, actor):
        self.events.append("open")
        return SimpleNamespace(entries=(), captured_at=None, skipped_lines=0)

    def query_logs(self, session, actor, query, *, snapshot):
        self.events.append("query")
        self.snapshots.append(snapshot)
        return SimpleNamespace(items=[], total=0, page=1, page_size=20)


def test_query_logs_passes_the_given_snapshot_through(monkeypatch):
    """AuthLogic.query_logs 把调用方传入的快照原样交给服务层，不自行重读。"""
    events = []
    service = FakeLogService(events)
    logic = _logic(events, service=service)
    opened = logic.open_log_snapshot(ADMIN)
    external = SimpleNamespace(entries=(), captured_at=None, skipped_lines=0)
    logic.query_logs(ADMIN, LogQuery(), snapshot=external)
    logic.query_logs(ADMIN, LogQuery(), snapshot=opened)
    assert service.snapshots[0] is external
    assert service.snapshots[1] is opened
    assert events == ["open", "flush", "commit", "query", "flush", "commit", "query", "flush", "commit"]
