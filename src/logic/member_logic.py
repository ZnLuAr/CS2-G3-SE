"""会员用例入口及会话、事务生命周期。

Logic 负责创建与关闭 Session、决定事务边界，并在提交成功后写操作日志。
权限与业务规则在 MemberService 内校验；本层不直接操作 SQL。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.db.connection import transaction
from src.errors import OutcomeUnknownError, StorageError
from src.logging import Operation, Outcome, log_event
from src.logging.events import report_log_failure
from src.services.member_service import normalize_request_id

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
        """提交一次会员建档；并发同编号时回放已提交的胜者结果（合同 12.7.3）。

        请求编号的格式校验在开启会话前完成（合同 4.2）。
        同一 `request_id` 的两个事务都查不到旧记录时，`operation_records` 的唯一约束
        是最终防线：后到者写操作记录时抛 `IntegrityError`（MySQL 1062），本次事务连同
        已建的会员行一起回滚。此时换一个新事务重试一次——新事务能读到胜者记录，
        服务据此回放结果；若操作者或内容摘要不一致则抛 `ConflictError`。
        其他完整性错误不重试，和其他数据库错误一样转成 `StorageError`。
        """
        canonical_request_id = normalize_request_id(request_id)
        try:
            return self._create_member_once(actor, data, canonical_request_id)
        except IntegrityError:
            try:
                return self._create_member_once(actor, data, canonical_request_id)
            except IntegrityError as exc:
                raise StorageError("同一请求编号并发提交，请按原编号核实结果") from exc

    def _create_member_once(self, actor: Actor, data: MemberInput, request_id: str) -> MemberView:
        """在一个新事务里尝试建档；提交未知时附上请求编号供核实。"""
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
        except IntegrityError as exc:
            # 同一 request_id 的唯一约束冲突交给 create_member 换新事务回放；
            # 其他完整性错误和其他数据库错误一样转成 StorageError。
            if _is_duplicate_key(exc):
                raise
            raise StorageError("保存会员档案失败") from exc
        except SQLAlchemyError as exc:
            raise StorageError("保存会员档案失败") from exc
        _log_operation(Operation.MEMBER_CREATE, actor, result.id, request_id)
        return result

    def get_member_by_request(self, actor: Actor, request_id: str) -> MemberView:
        """按请求编号核实建档结果；只读，使用短事务。请求编号在开启会话前校验格式。"""
        canonical_request_id = normalize_request_id(request_id)
        try:
            with self._session_factory() as session, transaction(session):
                return self._member_service.get_member_by_request(session, actor, canonical_request_id)
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
        """修改会员资料；同一事务内锁档案、写入并返回最新值。提交未知时附上会员编号供核实。"""
        result = None
        try:
            with self._session_factory() as session:
                with transaction(session, record_id=member_id):
                    result = self._member_service.update_member(session, actor, member_id, data)
        except SQLAlchemyError as exc:
            raise StorageError("保存会员资料失败") from exc
        _log_operation(Operation.MEMBER_UPDATE, actor, result.id)
        return result

    def set_member_status(self, actor: Actor, member_id: int, status: MemberStatus) -> MemberView:
        """设置会员状态；属于 MEM-06，尚未实现。"""
        raise NotImplementedError("MemberLogic.set_member_status 尚未实现")


def _is_duplicate_key(exc: IntegrityError) -> bool:
    """判断是否为 MySQL 1062（唯一键重复）；只有这类冲突才按 12.7.3 回放胜者结果。"""
    args = getattr(exc.orig, "args", ())
    return bool(args) and args[0] == 1062


def _log_operation(
    operation: Operation, actor: Actor, result_id: int, request_id: str | None = None
) -> None:
    """提交成功后写操作日志，带上请求编号供按编号核实。

    合同 11.1：日志失败不回滚已提交的业务。log_event 运行期失败会自行向标准错误
    输出固定提示；这里只兜住占位期抛出的异常并走同一提示，与评价、体测的用例层一致。
    """
    try:
        log_event(
            logging.INFO,
            operation=operation.value,
            outcome=Outcome.SUCCESS.value,
            actor_id=actor.account_id,
            request_id=request_id,
            result_id=result_id,
        )
    except Exception as exc:
        report_log_failure(operation.value, exc)
