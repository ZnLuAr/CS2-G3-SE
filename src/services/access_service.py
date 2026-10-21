"""门禁入场服务。"""

from __future__ import annotations

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

    def __init__(self, auth: AuthService) -> None:
        """接收共用身份校验服务。"""
        self._auth = auth

    def get_today_entry(
        self, session: Session, actor: Actor, member_id: int
    ) -> EntryView:
        """输入会员编号，按服务生成的门店日期返回 EntryView。会员仅查本人，前台与管理员可查；无记录或不可见抛 NotFoundError，查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("AccessService.get_today_entry 尚未实现")

    def register_entry(
        self, session: Session,
        actor: Actor,
        data: EntryInput,
        request_id: str,
    ) -> EntryView:
        """前台或管理员输入会员、带 kind 的来源和 UUID 请求编号，返回首次 EntryView。会员、来源、当日入场和操作记录按合同锁定；首次次卡入场扣一次余额，其他来源只记入场。同日与同请求复用首次记录；来源非法、资格不足或冲突抛项目异常，入场、扣次和请求记录共用调用方事务。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("AccessService.register_entry 尚未实现")

    def get_entry_by_request(
        self, session: Session, actor: Actor, request_id: str
    ) -> EntryView:
        """输入原 register_entry 请求编号，原操作者核实当前 EntryView。请求不存在或不可见抛 NotFoundError，操作类型不符抛 ConflictError；查询保持业务数据。

        当前业务方法为占位，调用抛 NotImplementedError。
        """
        raise NotImplementedError("AccessService.get_entry_by_request 尚未实现")
