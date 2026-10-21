"""账号数据访问；身份复核使用的账号与档案锁定已实现。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import text

from src.models.account import Account
from src.models.contracts import AccountView, Actor, NamedQuery, Page, Role
from src.models.course import Coach
from src.models.member import Member

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _utc(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class AccountRepository:
    """账号数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        self._session = session

    def get(self, account_id: int) -> Account | None:
        """按编号读取账号；包含密码哈希，仅供服务内部使用。

        返回：Account | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("AccountRepository.get 尚未实现")

    def lock(self, account_id: int) -> Account | None:
        """在当前事务锁定账号并读取最新 Account，不存在返回 None。

        单账号流程使用本方法；多账号流程使用 lock_many 一次性取得完整锁集合。
        不提交，锁持有到调用方事务结束。"""
        statement = text("SELECT * FROM accounts WHERE id = :id")
        if self._session.get_bind().dialect.name != "sqlite":
            statement = text(str(statement) + " FOR UPDATE")
        row = self._session.execute(statement, {"id": account_id}).mappings().first()
        if row is None:
            return None
        return Account(
            id=row["id"], username=row["username"], password_hash=row["password_hash"],
            role=row["role"], is_active=bool(row["is_active"]),
            created_at=_utc(row["created_at"]), updated_at=_utc(row["updated_at"]),
        )

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
        账号关联与档案状态均使用锁定当前读。"""
        # 账号行先锁定，关联移交也须先锁该账号；再按会员、教练顺序锁档案。
        member_sql = (
            "SELECT m.* FROM members m JOIN member_account_links l ON l.member_id = m.id "
            "WHERE l.account_id = :id"
        )
        coach_sql = (
            "SELECT c.* FROM coaches c JOIN coach_account_links l ON l.coach_id = c.id "
            "WHERE l.account_id = :id"
        )
        if self._session.get_bind().dialect.name != "sqlite":
            member_sql += " FOR UPDATE"
            coach_sql += " FOR UPDATE"
        member_row = self._session.execute(text(member_sql), {"id": account_id}).mappings().first()
        coach_row = self._session.execute(text(coach_sql), {"id": account_id}).mappings().first()
        member = None if member_row is None else Member(
            id=member_row["id"], name=member_row["name"], phone=member_row["phone"],
            status=member_row["status"], archived_at=_utc(member_row["archived_at"]),
            created_at=_utc(member_row["created_at"]), updated_at=_utc(member_row["updated_at"]),
        )
        coach = None if coach_row is None else Coach(
            id=coach_row["id"], name=coach_row["name"], phone=coach_row["phone"],
            is_active=bool(coach_row["is_active"]),
            created_at=_utc(coach_row["created_at"]), updated_at=_utc(coach_row["updated_at"]),
        )
        return member, coach

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
