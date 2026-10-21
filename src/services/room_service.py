"""场地服务接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.contracts import Actor, NamedQuery, Page, RoomInput, RoomView
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class RoomService:
    """场地管理服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后遵守 docs/architecture/backend.md 的返回、异常、权限和事务约定。
    """

    def __init__(self, auth: AuthService) -> None:
        """接收共用身份校验服务。"""
        self._auth = auth

    def create_room(self, session: Session, actor: Actor, data: RoomInput) -> RoomView:
        """管理员输入场地名称与可空位置，创建后返回 RoomView。输入非法抛 InvalidInputError，越权抛 PermissionDenied；写入由 Logic 统一提交。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("RoomService.create_room 尚未实现")

    def update_room(self, session: Session, actor: Actor, room_id: int, data: RoomInput) -> RoomView:
        """管理员输入编号与完整名称、位置，锁内更新后返回 RoomView。输入非法或不存在抛项目异常；已有课次保留排期。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("RoomService.update_room 尚未实现")

    def get_room(self, session: Session, actor: Actor, room_id: int) -> RoomView:
        """输入场地编号，返回 RoomView。管理员可查全部，允许浏览课次的其他角色限启用场地；不存在或不可见抛 NotFoundError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("RoomService.get_room 尚未实现")

    def list_rooms(self, session: Session, actor: Actor, query: NamedQuery) -> Page[RoomView]:
        """输入名称、启用与分页条件，返回 Page[RoomView]。管理员可查全部，其他允许角色限启用场地；条件非法抛 InvalidInputError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("RoomService.list_rooms 尚未实现")

    def set_room_active(self, session: Session, actor: Actor, room_id: int, is_active: bool) -> RoomView:
        """管理员输入场地编号与布尔状态，锁内复核后返回 RoomView。未结束课次仍使用该场地时停用抛 InvalidState；重复目标状态复用当前结果，历史课次保留。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("RoomService.set_room_active 尚未实现")
