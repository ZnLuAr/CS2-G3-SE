"""账号与权限服务接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.models.contracts import (
    AccountInput,
    AccountLinkInput,
    AccountView,
    Actor,
    NamedQuery,
    Page,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class AuthService:
    """账号与权限服务。

    actor 来自可信登录会话，方法仍须检查权限与数据归属。
    输入字段见 models/contracts.py；实现后的异常和事务约定见设计第 4 节。
    当前所有方法仅占位，调用会抛 NotImplementedError。
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        """接收会话工厂。"""
        raise NotImplementedError("AuthService.__init__ 尚未实现")

    def login(self, username: str, password: str) -> Actor:
        """校验凭据并取得当前操作者。

        密码原样处理，允许 A–Z、a–z、0–9、短横线和下划线，共 1–32 位；不做强度检测。
        返回：Actor。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("AuthService.login 尚未实现")

    def create_account(self, actor: Actor, data: AccountInput) -> AccountView:
        """创建账号。

        密码字符与长度规则见设计第 3.1 节，不要求字符组合；实现时仍须哈希保存。
        返回：AccountView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("AuthService.create_account 尚未实现")

    def get_account(self, actor: Actor, account_id: int) -> AccountView:
        """查询账号详情。

        返回：AccountView。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("AuthService.get_account 尚未实现")

    def list_accounts(self, actor: Actor, query: NamedQuery) -> Page[AccountView]:
        """分页查询账号。

        返回：Page[AccountView]。不修改业务数据。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("AuthService.list_accounts 尚未实现")

    def set_account_active(self, actor: Actor, account_id: int, active: bool) -> AccountView:
        """停用或恢复账号。

        返回：AccountView。在同一服务事务中修改对应记录，失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("AuthService.set_account_active 尚未实现")

    def link_profile(self, actor: Actor, account_id: int, data: AccountLinkInput) -> AccountView:
        """将 data 指定的档案移交给 account_id 指定的目标账号。

        返回：目标账号的 AccountView；同一档案重复关联不变，目标占用其他档案则拒绝。
        同事务直接更改档案外键，不先清空教练的非空账号字段；失败清理后抛异常。
        异常：当前为 NotImplementedError；实现后遵守设计第 4.1 节的输入、权限和数据库异常约定。"""
        raise NotImplementedError("AuthService.link_profile 尚未实现")

    def verify_actor(self, session: Session, actor: Actor) -> Actor:
        """内部共用方法：在调用方的事务中重验账号和档案关联；不自行提交。"""
        raise NotImplementedError("AuthService.verify_actor 尚未实现")
