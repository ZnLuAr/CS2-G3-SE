"""场地服务接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.models.contracts import Actor, NamedQuery, Page, RoomInput, RoomView
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class RoomService:
    """场地管理服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后遵守 docs/architecture.md 的返回、异常、权限和事务约定。
    """

    def __init__(self, session_factory: Callable[[], Session], auth: AuthService) -> None:
        """接收会话工厂及共用身份校验服务。"""
        self._session_factory = session_factory
        self._auth = auth

    def create_room(self, actor: Actor, data: RoomInput) -> RoomView:
        """创建场地。"""
        raise NotImplementedError("RoomService.create_room 尚未实现")

    def update_room(self, actor: Actor, room_id: int, data: RoomInput) -> RoomView:
        """修改场地资料。"""
        raise NotImplementedError("RoomService.update_room 尚未实现")

    def get_room(self, actor: Actor, room_id: int) -> RoomView:
        """查询场地详情。"""
        raise NotImplementedError("RoomService.get_room 尚未实现")

    def list_rooms(self, actor: Actor, query: NamedQuery) -> Page[RoomView]:
        """分页查询场地。"""
        raise NotImplementedError("RoomService.list_rooms 尚未实现")

    def set_room_active(self, actor: Actor, room_id: int, is_active: bool) -> RoomView:
        """停用或恢复场地。"""
        raise NotImplementedError("RoomService.set_room_active 尚未实现")
