"""候补存储字段；队列位置在查询时计算，尚未配置 ORM 映射。"""

from dataclasses import dataclass
from datetime import datetime

from src.models.contracts import WaitlistStatus


@dataclass(frozen=True, kw_only=True)
class WaitlistEntry:
    """对应 waitlist_entries 表的存储字段。"""

    id: int
    member_id: int
    session_id: int
    lesson_package_id: int
    status: WaitlistStatus
    booking_id: int | None
    joined_at: datetime
    closed_at: datetime | None
