"""Notification query and read-state service contract."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.contracts import (
        Actor,
        NotificationQuery,
        NotificationKind,
        NotificationReadResultView,
        NotificationView,
        Page,
    )
    from src.services.auth_service import AuthService


class NotificationService:
    """本人通知查询和已读，以及候补事务内的固定通知生成；方法仍为占位。"""
    def __init__(self, auth_service: AuthService) -> None:
        self._auth_service = auth_service

    def list_notifications(
        self, session: Session, actor: Actor, query: NotificationQuery,
    ) -> Page[NotificationView]:
        """会员本人按时间倒序分页查询，空结果为空 Page；角色拒绝抛 PermissionDenied。"""
        raise NotImplementedError

    def mark_read(
        self, session: Session, actor: Actor, notification_id: int,
    ) -> NotificationView:
        """将本人通知标记已读，重复返回当前 View；越权或不存在抛 NotFoundError。"""
        raise NotImplementedError

    def mark_all_read(
        self, session: Session, actor: Actor,
    ) -> NotificationReadResultView:
        """按会员、通知编号锁序标记全部未读，返回实际更新数及UTC时刻；Logic提交。"""
        raise NotImplementedError

    def create_waitlist_notification(
        self, session: Session, member_id: int, session_id: int,
        kind: NotificationKind, created_at: datetime,
    ) -> NotificationView:
        """内部候补事务生成固定标题正文并写通知，返回 NotificationView。

        输入为会员、课次、固定种类及UTC时刻；不存在抛 NotFoundError，非法输入抛
        InvalidInputError，存储失败抛 StorageError。状态及通知由 Logic 一起提交或回滚。
        当前仅占位。
        """
        raise NotImplementedError("候补通知生成尚未实现")
