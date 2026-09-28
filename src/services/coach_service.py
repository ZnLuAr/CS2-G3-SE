"""教练服务接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.models.contracts import Actor, CoachInput, CoachView, NamedQuery, Page
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class CoachService:
    """教练档案服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后遵守 docs/architecture.md 的返回、异常、权限和事务约定。
    """

    def __init__(self, session_factory: Callable[[], Session], auth: AuthService) -> None:
        """接收会话工厂及共用身份校验服务。"""
        self._session_factory = session_factory
        self._auth = auth

    def create_coach(self, actor: Actor, data: CoachInput) -> CoachView:
        """创建教练档案。"""
        raise NotImplementedError("CoachService.create_coach 尚未实现")

    def update_coach(self, actor: Actor, coach_id: int, data: CoachInput) -> CoachView:
        """修改教练资料。"""
        raise NotImplementedError("CoachService.update_coach 尚未实现")

    def get_coach(self, actor: Actor, coach_id: int) -> CoachView:
        """查询教练详情。"""
        raise NotImplementedError("CoachService.get_coach 尚未实现")

    def list_coaches(self, actor: Actor, query: NamedQuery) -> Page[CoachView]:
        """分页查询教练。"""
        raise NotImplementedError("CoachService.list_coaches 尚未实现")

    def set_coach_active(self, actor: Actor, coach_id: int, is_active: bool) -> CoachView:
        """停用或恢复教练。"""
        raise NotImplementedError("CoachService.set_coach_active 尚未实现")
