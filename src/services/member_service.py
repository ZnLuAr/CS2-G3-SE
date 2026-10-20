"""会员档案服务接口。构造函数已实现，业务操作仍为占位。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.contracts import Actor, MemberInput, MemberQuery, MemberStatus, MemberView, Page
from src.services.auth_service import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class MemberService:
    """会员档案服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后遵守 docs/architecture/backend.md的返回、异常、权限和事务约定。
    构造函数保存依赖；业务方法仍为占位。
    """

    def __init__(self, auth: AuthService) -> None:
        """接收共用身份校验服务。"""
        self._auth = auth

    def create_member(self, session: Session, actor: Actor, data: MemberInput, request_id: str) -> MemberView:
        """创建会员档案（幂等）。

        返回：MemberView；相同 request_id 重试返回原会员的当前 View。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("MemberService.create_member 尚未实现")

    def get_member_by_request(self, session: Session, actor: Actor, request_id: str) -> MemberView:
        """按幂等请求编号查会员。

        返回：MemberView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("MemberService.get_member_by_request 尚未实现")

    def get_member(self, session: Session, actor: Actor, member_id: int) -> MemberView:
        """查询会员详情。

        返回：MemberView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("MemberService.get_member 尚未实现")

    def list_members(self, session: Session, actor: Actor, query: MemberQuery) -> Page[MemberView]:
        """分页查询会员。

        返回：Page[MemberView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("MemberService.list_members 尚未实现")

    def update_member(self, session: Session, actor: Actor, member_id: int, data: MemberInput) -> MemberView:
        """修改会员资料。

        返回：MemberView。数据变更由调用方 Logic 在本次事务中提交；失败时由 Logic 回滚并传播异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("MemberService.update_member 尚未实现")

    def set_member_status(self, session: Session, actor: Actor, member_id: int, status: MemberStatus) -> MemberView:
        """设置会员状态（启用/归档）。

        管理员输入会员编号与 active/archived 目标状态，在会员锁内维护 status 和 archived_at。
        归档保留已有预约与历史；新销售、新预约和卡来源入场依据该状态校验。
        归档前已有的开放预约继续按授权处理签到、结算和当日预约来源入场。
        返回：MemberView。数据变更由调用方 Logic 在本次事务中提交；失败时由 Logic 回滚并传播异常。
        异常：当前为 NotImplementedError；实现后遵守 docs/architecture/backend.md的输入、权限、异常和事务约定。"""
        raise NotImplementedError("MemberService.set_member_status 尚未实现")
