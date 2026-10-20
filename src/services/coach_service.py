"""教练服务接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.contracts import Actor, CoachInput, CoachView, NamedQuery, Page
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class CoachService:
    """教练档案服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后遵守 docs/architecture/backend.md 的返回、异常、权限和事务约定。
    """

    def __init__(self, auth: AuthService) -> None:
        """接收共用身份校验服务。"""
        self._auth = auth

    def create_coach(self, session: Session, actor: Actor, data: CoachInput) -> CoachView:
        """管理员输入姓名与可空电话，创建档案并返回 CoachView。姓名或电话非法抛 InvalidInputError，越权抛 PermissionDenied；账号关联通过身份服务完成。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("CoachService.create_coach 尚未实现")

    def update_coach(self, session: Session, actor: Actor, coach_id: int, data: CoachInput) -> CoachView:
        """管理员输入编号与完整姓名、电话，在档案锁内更新后返回 CoachView。输入非法或不存在抛项目异常；历史课次保持原排期。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("CoachService.update_coach 尚未实现")

    def get_coach(self, session: Session, actor: Actor, coach_id: int) -> CoachView:
        """输入教练编号，返回 CoachView。管理员可查全部，允许浏览课次的其他角色只查启用教练；不存在或不可见抛 NotFoundError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("CoachService.get_coach 尚未实现")

    def list_coaches(self, session: Session, actor: Actor, query: NamedQuery) -> Page[CoachView]:
        """输入姓名、启用与分页条件，返回 Page[CoachView]。管理员可查全部，其他允许角色限启用教练；条件非法抛 InvalidInputError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("CoachService.list_coaches 尚未实现")

    def set_coach_active(self, session: Session, actor: Actor, coach_id: int, is_active: bool) -> CoachView:
        """管理员输入教练编号与布尔状态，锁内复核后返回 CoachView。未结束课次仍使用该教练时停用抛 InvalidState；重复目标状态复用当前结果，历史课次保留。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("CoachService.set_coach_active 尚未实现")
