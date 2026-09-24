"""服务内部的数据访问接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.account import Account
from src.models.contracts import AccountView, Actor, NamedQuery, Page, Role
from src.models.course import Coach
from src.models.member import Member

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

        单账号流程使用本方法；多账号流程使用 lock_many 一次性取得完整锁集合。
        不提交。当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("AccountRepository.lock 尚未实现")

    def lock_many(self, account_ids: tuple[int, ...]) -> tuple[Account, ...]:
        """去重后按账号编号升序锁定指定账号，并读取最新 Account。

        必须通过一条带 ORDER BY id 的锁定当前读取得全部行；不提交。
        返回：tuple[Account, ...]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("AccountRepository.lock_many 尚未实现")

    def lock_active_admins(
        self, account_ids: tuple[int, ...],
    ) -> tuple[Account, ...]:
        """按账号编号升序锁定指定账号与全部启用管理员的并集。

        使用一条锁定当前读，供账号停用同时锁住操作者、目标账号并复核最后一名管理员。
        返回：tuple[Account, ...]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("AccountRepository.lock_active_admins 尚未实现")

    def find_by_username(self, username: str) -> Account | None:
        """按规范化用户名查账号；未找到返回 None。

        返回：Account | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("AccountRepository.find_by_username 尚未实现")

    def get_actor(self, account_id: int) -> Actor | None:
        """读取账号角色及关联档案编号，供身份复核。

        这里只报告关联现状；角色与档案是否匹配由 AuthService 拒绝或接受。
        返回：Actor | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("AccountRepository.get_actor 尚未实现")

    def lock_profile_links(
        self, account_id: int,
    ) -> tuple[Member | None, Coach | None]:
        """账号行已加锁后，以锁定当前读取关联会员和教练的完整记录。

        先锁会员行再锁教练行，并将锁持有到调用方事务结束。
        返回：(member, coach)；未关联项为 None，调用方据此复核关联和 is_active。
        当前仅占位。"""
        raise NotImplementedError("AccountRepository.lock_profile_links 尚未实现")

    def create(self, *, username: str, password_hash: str, role: Role) -> Account:
        """保存已哈希密码和角色；不自行提交。

        返回：Account；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("AccountRepository.create 尚未实现")

    def list(self, query: NamedQuery) -> Page[AccountView]:
        """按 id 升序稳定分页查询可展示账号资料，不返回密码哈希。

        返回：Page[AccountView]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("AccountRepository.list 尚未实现")

    def set_active(self, account_id: int, active: bool) -> AccountView:
        """写启用状态并返回账号详情；不提交。

        返回：AccountView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("AccountRepository.set_active 尚未实现")
