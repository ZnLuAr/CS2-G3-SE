"""通知仓储合同；只使用调用方 Session，SQL 方法尚未实现。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.models.contracts import NotificationKind, NotificationQuery, NotificationView, Page

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class NotificationRepository:
    """所有本人查询及已读写入带会员范围；存储故障抛 StorageError。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, notification_id: int, member_id: int) -> NotificationView | None:
        """范围内详情，未找到返回 None，不修改数据。"""
        raise NotImplementedError

    def list(self, member_id: int, query: NotificationQuery) -> Page[NotificationView]:
        """按created_at/id倒序分页，未读数与列表使用同一快照。"""
        raise NotImplementedError

    def create(
        self, member_id: int, session_id: int, kind: NotificationKind,
        title: str, body: str, created_at: datetime,
    ) -> NotificationView:
        """写入服务生成的固定正文，与候补状态共用事务，返回通知View。"""
        raise NotImplementedError

    def mark_read(
        self, notification_id: int, member_id: int, read_at: datetime,
    ) -> NotificationView:
        """会员已加锁后锁目标行，重复已读返回当前View；未找到抛NotFoundError。"""
        raise NotImplementedError

    def mark_all_read(self, member_id: int, read_at: datetime) -> int:
        """会员已加锁后按通知id升序锁定并标记未读，返回实际更新数。"""
        raise NotImplementedError
