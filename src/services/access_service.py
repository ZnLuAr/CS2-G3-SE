"""门禁入场服务。"""

from __future__ import annotations

from collections.abc import Callable

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from src.services.auth_service import AuthService
    from src.models.contracts import (
        Actor,
        EntryInput,
        EntryView,
    )


class AccessService:
    """门禁入场服务。"""

    def __init__(self, session_factory: Callable[[], Session], auth: AuthService) -> None:
        """接收会话工厂与共用身份校验服务。"""
        self._session_factory = session_factory
        self._auth = auth

    def get_today_entry(
        self, actor: Actor, member_id: int
    ) -> EntryView:
        """获取会员今日入场记录。"""
        raise NotImplementedError("AccessService.get_today_entry 尚未实现")

    def register_entry(
        self,
        actor: Actor,
        data: EntryInput,
        request_id: str,
    ) -> EntryView:
        """登记入场。"""
        raise NotImplementedError("AccessService.register_entry 尚未实现")

    def get_entry_by_request(
        self, actor: Actor, request_id: str
    ) -> EntryView:
        """按请求ID获取入场记录。"""
        raise NotImplementedError("AccessService.get_entry_by_request 尚未实现")
