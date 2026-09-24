"""服务内部的数据访问接口。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.models.booking import Booking
from src.models.contracts import (
    BookingInput,
    BookingQuery,
    BookingStatus,
    BookingView,
    DateWindow,
    Page,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class BookingRepository:
    """预约数据访问；只使用传入会话，不提交、不输出提示。

    返回 None 的查询由服务转换异常；写入失败交由服务清理事务。
    """

    def __init__(self, session: Session) -> None:
        """接收业务服务当前事务所用的数据库会话。"""
        raise NotImplementedError("BookingRepository.__init__ 尚未实现")

    def get(self, booking_id: int) -> BookingView | None:
        """查询预约详情；未找到返回 None。

        返回：BookingView | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("BookingRepository.get 尚未实现")

    def list(
        self,
        query: BookingQuery,
        *,
        scope_member_id: int | None,
        scope_coach_id: int | None,
    ) -> Page[BookingView]:
        """按服务明确给出的会员或教练范围分页查询。

        会员调用只传 scope_member_id，教练调用只传 scope_coach_id；
        只有前台或管理员可以同时传 None，两个范围不能同时非空。
        按关联课次 starts_at 降序、预约 id 降序稳定分页。
        返回：Page[BookingView]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("BookingRepository.list 尚未实现")

    def find_for_member_session(self, member_id: int, session_id: int) -> Booking | None:
        """锁定当前读同会员同课次的预约，包含已取消状态。

        调用方须先锁定会员和课次；不得沿用等锁前的一致性读快照。
        返回：Booking | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("BookingRepository.find_for_member_session 尚未实现")

    def has_open_for_member(self, member_id: int) -> bool:
        """检查会员是否仍有 reserved 或 checked_in 预约。

        调用方须先锁定会员，并使用锁定当前读，不能沿用事务先前的一致性读快照。
        返回固定 bool，不提交事务。当前仅占位。"""
        raise NotImplementedError("BookingRepository.has_open_for_member 尚未实现")

    def list_open_for_session(self, session_id: int) -> tuple[Booking, ...]:
        """读取课次的 reserved/checked_in 预约，供取消课次比较候选快照。

        按 member_id、membership_id、id 升序返回，不加锁、不提交。当前仅占位。"""
        raise NotImplementedError("BookingRepository.list_open_for_session 尚未实现")

    def has_open_for_session(self, session_id: int) -> bool:
        """课次已加锁后，以锁定当前读检查 reserved/checked_in 预约。

        不得沿用等待课次锁前建立的一致性读快照；不提交事务。当前仅占位。"""
        raise NotImplementedError("BookingRepository.has_open_for_session 尚未实现")

    def create(self, data: BookingInput, booked_at: datetime) -> BookingView:
        """保存预约，不在此处检查权益或提交事务。

        返回：BookingView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("BookingRepository.create 尚未实现")

    def set_state(
        self,
        booking_id: int,
        *,
        status: BookingStatus,
        checked_in_at: datetime | None,
        closed_at: datetime | None,
    ) -> BookingView:
        """写入状态和时间，私教节数结算由服务协调。

        返回：BookingView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("BookingRepository.set_state 尚未实现")

    def count_occupied(self, session_id: int) -> int:
        """锁定当前读取得该课次未取消预约记录并统计数量。

        调用方须先锁定课次；不得沿用事务先前的一致性读快照。
        返回：int；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("BookingRepository.count_occupied 尚未实现")

    def has_member_conflict(self, member_id: int, window: DateWindow) -> bool:
        """锁定当前读检查会员未取消预约是否与目标时间重叠。

        调用方须先锁定会员；不得沿用事务先前的一致性读快照。
        返回：bool；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("BookingRepository.has_member_conflict 尚未实现")

    def has_current_coaching_booking(
        self, member_id: int, coach_id: int, *, at: datetime,
    ) -> bool:
        """检查体测录入所需的当前授课关系；at 由服务生成。

        调用方已经持有会员行锁；实现须在该事务中锁定匹配预约并重读状态。
        要求预约 reserved/checked_in、课次 scheduled，且 booked_at <= at < ends_at。
        返回固定 bool，不写数据；历史体测查看不用此条件，按架构“体测权限规则”保留截止。
        当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("BookingRepository.has_current_coaching_booking 尚未实现")

    def lock(self, booking_id: int) -> Booking | None:
        """锁定并读取最新预约记录。

        返回：Booking | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("BookingRepository.lock 尚未实现")
