"""账号、身份与日志用例入口，管理会话和事务。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, TypeVar

from sqlalchemy.exc import SQLAlchemyError

from src.db.connection import transaction
from src.errors import OutcomeUnknownError, StorageError
from src.logging import Operation, Outcome, log_event
from src.logging.events import report_log_failure

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        AccountInput,
        AccountView,
        Actor,
        CoachAccountLinkInput,
        LogEntry,
        LogQuery,
        LogSnapshot,
        MemberAccountLinkInput,
        NamedQuery,
        Page,
    )
    from src.services.auth_service import AuthService

T = TypeVar("T")


class AuthLogic:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        auth_service: AuthService,
    ) -> None:
        self._session_factory = session_factory
        self._auth_service = auth_service

    def login(self, username: str, password: str) -> Actor:
        """校验凭据并返回可信 Actor；成功后记录脱敏登录结果。"""
        try:
            with self._session_factory() as session, transaction(session):
                actor = self._auth_service.login(session, username, password)
        except SQLAlchemyError as exc:
            raise StorageError("登录失败") from exc
        _log_success(Operation.LOGIN.value, actor.account_id)
        return actor

    def get_current_actor(self, actor: Actor) -> Actor:
        """用短事务复核并返回数据库中的最新身份。"""
        try:
            with self._session_factory() as session, transaction(session):
                return self._auth_service.verify_actor(session, actor)
        except SQLAlchemyError as exc:
            raise StorageError("复核当前登录身份失败") from exc

    def create_account(self, actor: Actor, data: AccountInput) -> AccountView:
        """创建账号；成功提交后记录操作日志。"""
        return self._write(
            "创建账号失败",
            Operation.ACCOUNT_CREATE.value,
            actor,
            lambda session: self._auth_service.create_account(session, actor, data),
        )

    def get_account(self, actor: Actor, account_id: int) -> AccountView:
        """用短事务读取账号详情。"""
        try:
            with self._session_factory() as session, transaction(session):
                return self._auth_service.get_account(session, actor, account_id)
        except SQLAlchemyError as exc:
            raise StorageError("查询账号失败") from exc

    def list_accounts(self, actor: Actor, query: NamedQuery) -> Page[AccountView]:
        """在同一业务快照内读取授权总数和当前页。"""
        try:
            with self._session_factory() as session, transaction(session):
                return self._auth_service.list_accounts(session, actor, query)
        except SQLAlchemyError as exc:
            raise StorageError("查询账号列表失败") from exc

    def set_account_active(self, actor: Actor, account_id: int, active: bool) -> AccountView:
        """停用或恢复账号；成功提交后按操作类型记录日志。"""
        operation = (
            Operation.ACCOUNT_ACTIVATE.value
            if active else Operation.ACCOUNT_DEACTIVATE.value
        )
        return self._write(
            "停用或恢复账号失败",
            operation,
            actor,
            lambda session: self._auth_service.set_account_active(
                session, actor, account_id, active,
            ),
        )

    def link_member(self, actor: Actor, data: MemberAccountLinkInput) -> AccountView:
        """关联会员档案；成功提交后记录账号更新日志。"""
        return self._write(
            "关联会员档案失败",
            Operation.ACCOUNT_LINK.value,
            actor,
            lambda session: self._auth_service.link_member(session, actor, data),
        )

    def link_coach(self, actor: Actor, data: CoachAccountLinkInput) -> AccountView:
        """关联教练档案；成功提交后记录账号更新日志。"""
        return self._write(
            "关联教练档案失败",
            Operation.ACCOUNT_LINK.value,
            actor,
            lambda session: self._auth_service.link_coach(session, actor, data),
        )

    def relink_member(self, actor: Actor, account_id: int, member_id: int) -> AccountView:
        """移交会员账号关联；成功提交后记录账号更新日志。"""
        return self._write(
            "移交会员账号关联失败",
            Operation.ACCOUNT_LINK.value,
            actor,
            lambda session: self._auth_service.relink_member(
                session, actor, account_id, member_id,
            ),
        )

    def relink_coach(self, actor: Actor, account_id: int, coach_id: int) -> AccountView:
        """移交教练账号关联；成功提交后记录账号更新日志。"""
        return self._write(
            "移交教练账号关联失败",
            Operation.ACCOUNT_LINK.value,
            actor,
            lambda session: self._auth_service.relink_coach(
                session, actor, account_id, coach_id,
            ),
        )

    def open_log_snapshot(self, actor: Actor) -> LogSnapshot:
        """用短事务复核管理员身份，再读取固定日志快照。"""
        try:
            with self._session_factory() as session, transaction(session):
                return self._auth_service.open_log_snapshot(session, actor)
        except SQLAlchemyError as exc:
            raise StorageError("读取日志快照失败") from exc

    def query_logs(self, actor: Actor, query: LogQuery, *, snapshot: LogSnapshot) -> Page[LogEntry]:
        """每次筛选和翻页都在新的短事务中复核身份，再查询既有快照。"""
        try:
            with self._session_factory() as session, transaction(session):
                return self._auth_service.query_logs(
                    session, actor, query, snapshot=snapshot,
                )
        except SQLAlchemyError as exc:
            raise StorageError("查询日志失败") from exc

    def _write(
        self,
        failure_message: str,
        operation: str,
        actor: Actor,
        action: Callable[[Session], T],
    ) -> T:
        """执行一次写用例：成功提交后才记录成功日志。"""
        result: T | None = None
        try:
            with self._session_factory() as session, transaction(session):
                result = action(session)
        except OutcomeUnknownError as exc:
            record_id = getattr(result, "id", None)
            if record_id is not None:
                exc.record_id = record_id
            raise
        except SQLAlchemyError as exc:
            raise StorageError(failure_message) from exc
        _log_success(operation, actor.account_id, getattr(result, "id", None))
        return result


def _log_success(operation: str, actor_id: int, result_id: int | None = None) -> None:
    """记录已提交操作；日志故障不改变已完成的业务结果。"""
    try:
        log_event(
            logging.INFO,
            operation=operation,
            outcome=Outcome.SUCCESS.value,
            actor_id=actor_id,
            result_id=result_id,
        )
    except Exception as exc:
        report_log_failure(operation, exc)
