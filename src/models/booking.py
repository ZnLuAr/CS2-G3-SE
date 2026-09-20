"""业务存储模型。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.models.contracts import BookingStatus


@dataclass(frozen=True, kw_only=True)
class Booking:
    """对应 bookings 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    member_id: int
    session_id: int
    membership_id: int
    status: BookingStatus
    booked_at: datetime
    checked_in_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class Consumption:
    """对应 consumptions 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    booking_id: int
    membership_id: int
    lessons_used: int
    completed_at: datetime
    operator_id: int
    created_at: datetime


@dataclass(frozen=True, kw_only=True)
class Review:
    """对应 reviews 表的存储字段；尚未配置 ORM 映射。"""

    id: int
    booking_id: int
    rating: int
    comment: str
    created_at: datetime
