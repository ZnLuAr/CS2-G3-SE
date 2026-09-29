"""健身房入场数据访问接口。当前仅声明签名，方法尚未实现。"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from src.models.contracts import EntrySourceKind
from src.models.gym_entry import EntryAggregate, GymEntry

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class GymEntryRepository:
    """健身房入场数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("GymEntryRepository.__init__ 尚未实现")

    def get_for_day(
        self, member_id: int, business_date: date
    ) -> GymEntry | None:
        """查询会员在指定日期的入场记录。

        返回：GymEntry | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymEntryRepository.get_for_day 尚未实现")

    def lock_for_day(
        self, member_id: int, business_date: date
    ) -> GymEntry | None:
        """锁定会员在指定日期的入场记录；用于服务事务。

        返回：GymEntry | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymEntryRepository.lock_for_day 尚未实现")

    def create(
        self,
        member_id: int,
        source_kind: EntrySourceKind,
        duration_gym_card_id: int | None,
        visit_gym_card_id: int | None,
        booking_id: int | None,
        business_date: date,
        entered_at: datetime,
        operator_id: int,
    ) -> GymEntry:
        """创建入场记录；不自行提交。

        返回：GymEntry；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymEntryRepository.create 尚未实现")

    def get(self, entry_id: int) -> GymEntry | None:
        """查询入场记录详情；未找到返回 None，由服务转成异常。

        返回：GymEntry | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymEntryRepository.get 尚未实现")

    def get_view(self, entry_id: int) -> GymEntry | None:
        """查询入场记录视图；未找到返回 None，由服务转成异常。

        返回：GymEntry | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymEntryRepository.get_view 尚未实现")

    def get_by_booking(
        self, booking_id: int
    ) -> EntryAggregate | None:
        """根据预约查询入场记录及关联数据。

        返回：EntryAggregate | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymEntryRepository.get_by_booking 尚未实现")

    def lock_by_booking(
        self, booking_id: int
    ) -> EntryAggregate | None:
        """根据预约锁定入场记录及关联数据；用于服务事务。

        返回：EntryAggregate | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymEntryRepository.lock_by_booking 尚未实现")
