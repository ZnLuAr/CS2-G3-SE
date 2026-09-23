"""会员档案服务接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.models.contracts import Actor, MemberInput, MemberQuery, MemberView, Page
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class MemberService:
    """会员档案服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后的异常和事务约定见设计第 4 节。
    构造函数保存依赖；业务方法仍为占位。
    """

    def __init__(self, session_factory: Callable[[], Session], auth: AuthService) -> None:
        """接收会话工厂及共用身份校验服务。"""
        self._session_factory = session_factory
        self._auth = auth

    def create_member(self, actor: Actor, data: MemberInput) -> MemberView:
        """创建会员档案。

        返回：MemberView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("MemberService.create_member 尚未实现")

    def get_member(self, actor: Actor, member_id: int) -> MemberView:
        """查询会员详情。

        返回：MemberView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("MemberService.get_member 尚未实现")

    def list_members(self, actor: Actor, query: MemberQuery) -> Page[MemberView]:
        """分页查询会员。

        返回：Page[MemberView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("MemberService.list_members 尚未实现")

    def update_member(self, actor: Actor, member_id: int, data: MemberInput) -> MemberView:
        """修改会员资料。

        返回：MemberView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("MemberService.update_member 尚未实现")

    def set_member_active(self, actor: Actor, member_id: int, active: bool) -> MemberView:
        """停用或恢复会员。

        返回：MemberView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("MemberService.set_member_active 尚未实现")
