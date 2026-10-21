"""会员数据访问；体测所用的会员锁定已实现，其余方法保留待实现签名。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.contracts import MemberInput, MemberQuery, MemberStatus
from src.models.member import Member

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session


class MemberRepository:
    """会员数据访问；只使用传入会话，不提交、不输出提示。

    返回领域模型 Member（非 View）；查询未命中返回 None，由服务转换异常。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        self._session = session

    def create(self, data: MemberInput) -> Member:
        """新增会员档案并返回领域模型；不自行提交。"""
        raise NotImplementedError("MemberRepository.create 尚未实现")

    def get(self, member_id: int) -> Member | None:
        """查询会员；未找到返回 None，由服务转成异常。"""
        raise NotImplementedError("MemberRepository.get 尚未实现")

    def lock(self, member_id: int) -> Member | None:
        """锁定并读取最新会员记录；用于服务事务。"""
        from datetime import timezone

        from sqlalchemy import DateTime, Integer, String, column, select, table

        members = table(
            "members", column("id", Integer), column("name", String), column("phone", String),
            column("status", String), column("archived_at", DateTime),
            column("created_at", DateTime), column("updated_at", DateTime),
        )
        row = self._session.execute(
            select(members).where(members.c.id == member_id).with_for_update(),
        ).mappings().first()
        if row is None:
            return None
        values = dict(row)
        for key in ("archived_at", "created_at", "updated_at"):
            value = values[key]
            if value is not None:
                values[key] = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        return Member(**values)

    def list(self, query: MemberQuery) -> tuple[list[Member], int]:
        """按 id 升序稳定分页，返回（当页记录, 总数）；权限范围由服务在 query 中约束。"""
        raise NotImplementedError("MemberRepository.list 尚未实现")

    def update_profile(self, member_id: int, name: str, phone: str | None) -> Member:
        """更新会员姓名与电话；phone=None 表示清空。"""
        raise NotImplementedError("MemberRepository.update_profile 尚未实现")

    def set_status(self, member_id: int, status: MemberStatus, archived_at: datetime | None) -> Member:
        """写会员状态与归档时刻；业务条件由服务检查。"""
        raise NotImplementedError("MemberRepository.set_status 尚未实现")
