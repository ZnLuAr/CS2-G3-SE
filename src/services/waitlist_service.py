"""Waitlist query and membership service contract."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        Actor,
        Page,
        WaitlistInput,
        WaitlistQuery,
        WaitlistSummaryView,
        WaitlistView,
    )
    from src.services.auth_service import AuthService


class WaitlistService:
    """候补成员与队列合同；用户方法复核身份，内部方法由已持锁的 Logic 调用。"""
    def __init__(self, auth_service: AuthService) -> None:
        self._auth_service = auth_service

    def join_waitlist(
        self, session: Session, actor: Actor, data: WaitlistInput, request_id: str,
    ) -> WaitlistView:
        """本人或授权员工选择课包入队，返回waiting View，不占课节。

        满员和课包资格、时段、互斥由共享事务校验；请求UUID幂等。
        非法输入、越权、资格不足、重复或存储故障抛项目异常；Logic提交。当前仅占位。
        """
        raise NotImplementedError

    def leave_waitlist(
        self, session: Session, actor: Actor, waitlist_id: int,
    ) -> WaitlistView:
        """本人或授权员工退出waiting并返回View；重复终态返回当前结果。

        promoted抛InvalidState，越权或不存在抛NotFoundError；Logic提交cancelled状态。当前仅占位。
        """
        raise NotImplementedError

    def get_waitlist(
        self, session: Session, actor: Actor, waitlist_id: int,
    ) -> WaitlistView:
        """查询本人或员工授权范围内详情；不存在或越权抛NotFoundError，不写数据。"""
        raise NotImplementedError

    def get_waitlist_by_request(
        self, session: Session, actor: Actor, request_id: str,
    ) -> WaitlistView:
        """原操作者按join_waitlist请求核实当前View；类型冲突或不可见抛项目异常。"""
        raise NotImplementedError

    def list_waitlist(
        self, session: Session, actor: Actor, query: WaitlistQuery,
    ) -> Page[WaitlistView]:
        """会员看本人、前台管理员看授权队列，返回固定Page；教练使用人数接口。"""
        raise NotImplementedError

    def get_waitlist_summary(
        self, session: Session, actor: Actor, session_id: int,
    ) -> WaitlistSummaryView:
        """本课教练或授权员工读取waiting人数，不写数据；越权课次抛NotFoundError。"""
        raise NotImplementedError

    def list_reconciliation_session_ids(
        self, session: Session, as_of: datetime,
    ) -> tuple[int, ...]:
        """系统读取固定as_of下需递补或关闭的课次编号；失败抛StorageError。"""
        raise NotImplementedError

    def has_waiting_for_member_session(
        self, session: Session, member_id: int, session_id: int,
    ) -> bool:
        """内部互斥检查：取得会员、课次、课包和预约锁后用当前读判断waiting。

        返回固定bool，不写数据；数据库失败抛StorageError。当前仅占位。
        """
        raise NotImplementedError("候补互斥复核尚未实现")

    def list_waiting_for_session(
        self, session: Session, session_id: int,
    ) -> tuple[WaitlistView, ...]:
        """系统按joined_at/id读取课次候选，返回元组；写入前由Logic锁内复核。"""
        raise NotImplementedError

    def lock_waitlist_entry(
        self, session: Session, waitlist_id: int,
    ) -> WaitlistView:
        """系统在会员至预约锁取得后锁定候补，返回最新View；不存在抛NotFoundError。"""
        raise NotImplementedError

    def promote_waitlist(
        self, session: Session, waitlist_id: int, booking_id: int, closed_at: datetime,
    ) -> WaitlistView:
        """系统用Logic统一UTC时刻将waiting转正并关联预约，返回View。

        原状态不是waiting抛ConflictError，不存在抛NotFoundError；与预约、占用和通知同事务。当前仅占位。
        """
        raise NotImplementedError

    def close_waitlist(
        self, session: Session, waitlist_id: int, closed_at: datetime,
    ) -> WaitlistView:
        """系统用Logic统一UTC时刻关闭waiting并返回View；状态冲突抛ConflictError。

        不存在抛NotFoundError，与关闭通知同事务。当前仅占位。
        """
        raise NotImplementedError
