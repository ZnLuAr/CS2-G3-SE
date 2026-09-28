"""业务存储模型。当前仅声明字段与签名，方法尚未实现。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, kw_only=True)
class GymEntry:
    """对应 gym_entries 表的存储字段；同一会员每个门店日期最多一条。"""

    id: int
    member_id: int
    duration_gym_card_id: int | None
    visit_gym_card_id: int | None
    booking_id: int | None
    business_date: date
    entered_at: datetime
    source_kind: str
    operator_id: int
