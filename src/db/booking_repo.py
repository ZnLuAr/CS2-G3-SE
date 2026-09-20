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

        返回：Page[BookingView]；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("BookingRepository.list 尚未实现")

    def find_for_member_session(self, member_id: int, session_id: int) -> Booking | None:
        """读取同会员同课次的预约，包含已取消状态。

        返回：Booking | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("BookingRepository.find_for_member_session 尚未实现")

    def create(self, data: BookingInput, booked_at: datetime) -> BookingView:
        """保存预约，不在此处检查权益或提交事务。

        返回：BookingView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("BookingRepository.create 尚未实现")

    def restore(self, booking_id: int, *, membership_id: int, booked_at: datetime) -> BookingView:
        """恢复已取消预约并清空旧签到和结束时间。

        返回：BookingView；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("BookingRepository.restore 尚未实现")

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
        """统计该课次未取消预约数。

        返回：int；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("BookingRepository.count_occupied 尚未实现")

    def has_member_conflict(self, member_id: int, window: DateWindow) -> bool:
        """检查会员未取消预约是否与目标时间重叠。

        返回：bool；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("BookingRepository.has_member_conflict 尚未实现")

    def has_current_coaching_booking(
        self, member_id: int, coach_id: int, *, at: datetime,
    ) -> bool:
        """检查体测录入所需的当前授课关系；at 由服务生成。

        要求预约 reserved/checked_in、课次 scheduled，且 booked_at <= at < ends_at。
        返回固定 bool，不写数据；历史体测查看不用此条件，按设计第 3.6 节保留截止。
        当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("BookingRepository.has_current_coaching_booking 尚未实现")

    def lock(self, booking_id: int) -> Booking | None:
        """锁定并读取最新预约记录。

        返回：Booking | None；当前仅占位，调用抛 NotImplementedError。"""
        raise NotImplementedError("BookingRepository.lock 尚未实现")
