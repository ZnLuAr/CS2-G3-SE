"""会员用例入口及会话、事务生命周期。

Logic 负责创建与关闭 Session、决定事务边界，并在提交成功后写操作日志。
权限与业务规则在 MemberService 内校验；本层不直接操作 SQL。
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Callable

from sqlalchemy.exc import SQLAlchemyError

from src.db.connection import transaction
from src.errors import OutcomeUnknownError, StorageError
from src.logging import Operation, Outcome, log_event

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        Actor,
        MemberInput,
        MemberQuery,
        MemberStatus,
        MemberView,
        Page,
    )
    from src.services.member_service import MemberService


class MemberLogic:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        member_service: MemberService,
    ) -> None:
        self._session_factory = session_factory
        self._member_service = member_service

    def create_member(self, actor: Actor, data: MemberInput, request_id: str) -> MemberView:
        """提交一次会员建档；失败回滚，提交未知时附上请求编号供核实。"""
        result = None
        try:
            with self._session_factory() as session:
                try:
                    with transaction(session, request_id=request_id):
                        result = self._member_service.create_member(session, actor, data, request_id)
                except OutcomeUnknownError as exc:
                    if result is not None:
                        exc.record_id = result.id
                    raise
        except SQLAlchemyError as exc:
            raise StorageError("保存会员档案失败") from exc
        _log_operation(Operation.MEMBER_CREATE, actor, result.id)
        return result

    def get_member_by_request(self, actor: Actor, request_id: str) -> MemberView:
        """按请求编号核实建档结果；只读，使用短事务。"""
        try:
            with self._session_factory() as session, transaction(session):
                return self._member_service.get_member_by_request(session, actor, request_id)
        except SQLAlchemyError as exc:
            raise StorageError("查询会员档案失败") from exc

    def get_member(self, actor: Actor, member_id: int) -> MemberView:
        """读取授权范围内的会员详情；只读，使用短事务。"""
        try:
            with self._session_factory() as session, transaction(session):
                return self._member_service.get_member(session, actor, member_id)
        except SQLAlchemyError as exc:
            raise StorageError("查询会员档案失败") from exc

    def list_members(self, actor: Actor, query: MemberQuery) -> Page[MemberView]:
        """分页查询会员；只读，使用短事务并在结束时释放身份锁。"""
        try:
            with self._session_factory() as session, transaction(session):
                return self._member_service.list_members(session, actor, query)
        except SQLAlchemyError as exc:
            raise StorageError("查询会员列表失败") from exc

    def update_member(self, actor: Actor, member_id: int, data: MemberInput) -> MemberView:
        """修改会员资料；同一事务内锁档案、写入并返回最新值。"""
        result = None
        try:
            with self._session_factory() as session:
                with transaction(session):
                    result = self._member_service.update_member(session, actor, member_id, data)
        except SQLAlchemyError as exc:
            raise StorageError("保存会员资料失败") from exc
        _log_operation(Operation.MEMBER_UPDATE, actor, result.id)
        return result

    def set_member_status(self, actor: Actor, member_id: int, status: MemberStatus) -> MemberView:
        """设置会员状态；属于 MEM-06，尚未实现。"""
        raise NotImplementedError("MemberLogic.set_member_status 尚未实现")


def _log_operation(operation: Operation, actor: Actor, result_id: int) -> None:
    """提交成功后写操作日志；日志失败不回滚已提交的业务。"""
    try:
        log_event(
            logging.INFO,
            operation=operation.value,
            outcome=Outcome.SUCCESS.value,
            actor_id=actor.account_id,
            result_id=result_id,
        )
    except Exception:
        print("操作日志记录失败", file=sys.stderr)
