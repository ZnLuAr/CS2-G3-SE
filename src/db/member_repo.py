"""服务内部的数据访问接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models.contracts import MemberInput, MemberQuery, MemberView, Page
from src.models.member import Member

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class MemberRepository:
    """会员数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("MemberRepository.__init__ 尚未实现")

    def get(self, member_id: int) -> MemberView | None:
        """查询会员详情；未找到返回 None，由服务转成异常。

        返回：MemberView | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MemberRepository.get 尚未实现")

    def list(self, query: MemberQuery, *, scope_member_id: int | None) -> Page[MemberView]:
        """按服务提供的权限范围分页；None 仅用于获准查看全体的员工。

        返回：Page[MemberView]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MemberRepository.list 尚未实现")

    def create(self, data: MemberInput) -> MemberView:
        """新增会员档案并返回编号；不自行提交。

        返回：MemberView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MemberRepository.create 尚未实现")

    def update(self, member_id: int, data: MemberInput) -> MemberView:
        """更新完整可编辑字段；phone=None 表示清空。

        返回：MemberView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MemberRepository.update 尚未实现")

    def set_active(self, member_id: int, active: bool) -> MemberView:
        """写会员启用状态；业务条件由服务检查。

        返回：MemberView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MemberRepository.set_active 尚未实现")

    def set_account(self, member_id: int, account_id: int | None) -> MemberView:
        """设置或解除会员账号关联；须在服务的关联事务中调用。

        返回：MemberView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MemberRepository.set_account 尚未实现")

    def lock(self, member_id: int) -> Member | None:
        """锁定并读取最新会员记录；用于服务事务。

        返回：Member | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("MemberRepository.lock 尚未实现")
