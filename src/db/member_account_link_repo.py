"""会员账号关联数据访问接口。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.models.member_account_link import MemberAccountLink


class MemberAccountLinkRepository(Protocol):
    """会员账号关联数据访问。"""

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        ...

    def get_by_account(
        self, account_id: int
    ) -> MemberAccountLink | None:
        """按账号ID查询关联。"""
        raise NotImplementedError("MemberAccountLinkRepository.get_by_account 尚未实现")

    def get_by_member(
        self, member_id: int
    ) -> MemberAccountLink | None:
        """按会员ID查询关联。"""
        raise NotImplementedError("MemberAccountLinkRepository.get_by_member 尚未实现")

    def lock_by_account(
        self, account_id: int
    ) -> MemberAccountLink | None:
        """按账号ID锁定关联。"""
        raise NotImplementedError("MemberAccountLinkRepository.lock_by_account 尚未实现")

    def create(
        self,
        account_id: int,
        member_id: int,
        linked_by: int,
        linked_at: datetime,
    ) -> MemberAccountLink:
        """创建会员账号关联。"""
        raise NotImplementedError("MemberAccountLinkRepository.create 尚未实现")

    def delete(self, account_id: int) -> None:
        """删除会员账号关联。"""
        raise NotImplementedError("MemberAccountLinkRepository.delete 尚未实现")
