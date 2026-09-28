"""健身房卡数据访问接口。当前仅声明签名，方法尚未实现。"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from src.models.contracts import (
    GiftedDurationGymCardCreate,
    GymCardQuery,
    GymCardStatus,
    PurchasedDurationGymCardCreate,
    PurchasedVisitGymCardCreate,
)
from src.models.gym_card import DurationGymCard, GymCard, VisitGymCard

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class GymCardRepository:
    """健身房卡数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("GymCardRepository.__init__ 尚未实现")

    def create_purchased_duration(
        self, data: PurchasedDurationGymCardCreate
    ) -> DurationGymCard:
        """创建购买的期限型健身房卡；不自行提交。

        返回：DurationGymCard；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardRepository.create_purchased_duration 尚未实现")

    def create_purchased_visit(
        self, data: PurchasedVisitGymCardCreate
    ) -> VisitGymCard:
        """创建购买的次卡型健身房卡；不自行提交。

        返回：VisitGymCard；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardRepository.create_purchased_visit 尚未实现")

    def create_gifted_duration(
        self, data: GiftedDurationGymCardCreate
    ) -> DurationGymCard:
        """创建赠送的期限型健身房卡；不自行提交。

        返回：DurationGymCard；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardRepository.create_gifted_duration 尚未实现")

    def get(self, gym_card_id: int) -> GymCard | None:
        """查询健身房卡详情；未找到返回 None，由服务转成异常。

        返回：GymCard | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardRepository.get 尚未实现")

    def lock(self, gym_card_id: int) -> GymCard | None:
        """锁定并读取最新健身房卡记录；用于服务事务。

        返回：GymCard | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardRepository.lock 尚未实现")

    def lock_duration(
        self, gym_card_id: int
    ) -> DurationGymCard | None:
        """锁定并读取期限型健身房卡；用于服务事务。

        返回：DurationGymCard | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardRepository.lock_duration 尚未实现")

    def lock_visit(
        self, gym_card_id: int
    ) -> VisitGymCard | None:
        """锁定并读取次卡型健身房卡；用于服务事务。

        返回：VisitGymCard | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardRepository.lock_visit 尚未实现")

    def lock_member_duration_cards_affecting_start(
        self, member_id: int
    ) -> list[DurationGymCard]:
        """锁定会员的所有未作废期限卡，用于计算接续起始日期。

        返回：list[DurationGymCard]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardRepository.lock_member_duration_cards_affecting_start 尚未实现")

    def latest_term_end_locked(self, member_id: int) -> date | None:
        """扫描未作废期限卡并返回最大 valid_until；用于接续计算。

        返回：date | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardRepository.latest_term_end_locked 尚未实现")

    def decrement_visit_entry(
        self, gym_card_id: int
    ) -> VisitGymCard:
        """原子减一次卡剩余次数；要求已持有行锁且 remaining_entries > 0。

        返回：VisitGymCard；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardRepository.decrement_visit_entry 尚未实现")

    def list(
        self, query: GymCardQuery
    ) -> tuple[list[GymCard], int]:
        """按条件查询并返回健身房卡列表和总数。

        返回：tuple[list[GymCard], int]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardRepository.list 尚未实现")

    def list_eligible_ids(
        self, member_id: int, business_date: date
    ) -> tuple[int, ...]:
        """查询会员在指定日期有效的健身房卡编号。

        返回：tuple[int, ...]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardRepository.list_eligible_ids 尚未实现")

    def set_status(
        self, gym_card_id: int, status: GymCardStatus
    ) -> GymCard:
        """设置健身房卡状态；不自行提交。

        返回：GymCard；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("GymCardRepository.set_status 尚未实现")
