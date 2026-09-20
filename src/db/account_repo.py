"""服务内部的数据访问接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.account import Account
from src.models.contracts import AccountView, Actor, NamedQuery, Page, Role

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class AccountRepository:
    """账号数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("AccountRepository.__init__ 尚未实现")

    def get(self, account_id: int) -> Account | None:
        """按编号读取账号；包含密码哈希，仅供服务内部使用。

        返回：Account | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("AccountRepository.get 尚未实现")

    def lock(self, account_id: int) -> Account | None:
        """在当前事务锁定账号并读取最新 Account，不存在返回 None。

        协调停用、绑定与业务写入；不提交。当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("AccountRepository.lock 尚未实现")

    def find_by_username(self, username: str) -> Account | None:
        """按规范化用户名查账号；未找到返回 None。

        返回：Account | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("AccountRepository.find_by_username 尚未实现")

    def get_actor(self, account_id: int) -> Actor | None:
        """读取账号角色及关联档案编号，供身份复核。

        返回：Actor | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("AccountRepository.get_actor 尚未实现")

    def create(self, *, username: str, password_hash: str, role: Role) -> Account:
        """保存已哈希密码和角色；不自行提交。

        返回：Account；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("AccountRepository.create 尚未实现")

    def list(self, query: NamedQuery) -> Page[AccountView]:
        """分页查询可展示账号资料，不返回密码哈希。

        返回：Page[AccountView]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("AccountRepository.list 尚未实现")

    def set_active(self, account_id: int, active: bool) -> AccountView:
        """写启用状态并返回账号详情；不提交。

        返回：AccountView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("AccountRepository.set_active 尚未实现")
